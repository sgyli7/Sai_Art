"""Isolated twelve-second display/contact-cache ablations, preserving project bytes."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import shutil
from suspension_physics import ROOT
from run_suspension_visual import RUNTIME

OUT = ROOT / 'candidates/r023_interior'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['baseline', 'no_lights', 'opaque_glass', 'no_displays', 'cache_enabled'])
    args = parser.parse_args()
    label = 'cost_' + args.mode
    target = OUT / 'reports' / label
    assert not target.with_suffix('.log').exists()
    sources = list((ROOT / 'godot').glob('*.gd')) + [ROOT / 'godot/debug/interior_cost_probe.gd', Path(__file__), OUT / 'bindings.json', OUT / 'physics/native_spec.json']
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    for p in sources:
        archive = OUT / 'reports' / (label + '_source') / p.relative_to(ROOT)
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, archive)
    project = RUNTIME / 'project.godot'
    saved = project.read_bytes()
    original = saved.decode()
    assert 'velocity_steps=12' in original and 'position_steps=4' in original
    text = original.replace('velocity_steps=12', 'velocity_steps=64').replace('position_steps=4', 'position_steps=8')
    if args.mode != 'cache_enabled':
        text = text.replace('[physics]', '[physics]\njolt_physics_3d/simulation/body_pair_contact_cache_enabled=false')
    process = None
    try:
        project.write_text(text)
        with target.with_suffix('.log').open('w') as log:
            process = subprocess.Popen(['/home/ethan/.local/bin/godot', '--path', str(RUNTIME), '--script', str(ROOT / 'godot/debug/interior_cost_probe.gd'), '--',
                f'spec={OUT}/physics/native_spec.json', f'bindings={OUT}/bindings.json', f'output_root={OUT}/reports',
                f'output={label}.json', 'seconds=12', 'speed=5', 'terrain=rough', 'curvature=0', 'capture=false', 'view=whole', f'probe_mode={args.mode}'], stdout=log, stderr=subprocess.STDOUT)
            code = process.wait(timeout=120)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait()
        project.write_bytes(saved)
    changed = [str(p) for p in sources if hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))]]
    (OUT / 'reports' / (label + '_source.json')).write_text(json.dumps(dict(mode=args.mode, returncode=code, runtime_restored=project.read_bytes() == saved, changed_sources=changed, source_sha256=hashes), indent=2) + '\n')
    assert code == 0 and not changed
    print(label)


if __name__ == '__main__':
    main()
