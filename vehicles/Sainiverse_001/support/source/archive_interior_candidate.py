"""Freeze current cabin sources and all successful/failed evidence."""
from pathlib import Path
import hashlib
import json
import shutil
from suspension_physics import ROOT

OUT = ROOT / 'candidates/r023_interior'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    validation = json.loads((OUT / 'reports/interior_runtime_validation.json').read_text())
    assert validation['passed']
    for folder, pattern in [('source', '*.py'), ('godot', '*.gd'), ('godot', '*.gdshader'), ('design', '*.json'), ('design', '*.md')]:
        for path in (ROOT / folder).glob(pattern):
            target = OUT / 'source_files' / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    for path in (ROOT / 'godot/debug').glob('interior_*.gd'):
        target = OUT / 'source_files' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    bindings = json.loads((OUT / 'bindings.json').read_text())
    native = Path(bindings['path_extension']).parent
    dependencies = [p for p in native.rglob('*') if p.is_file() and 'build' not in p.relative_to(native).parts]
    dependencies += [ROOT / 'candidates/r022_runtime/assets/tensioned_tracks_texture.gdshader']
    files = [p for p in OUT.rglob('*') if p.is_file() and p.name != 'candidate_manifest.json' and p.suffix != '.blend1' and '__pycache__' not in p.parts]
    report = dict(candidate='r023_interior', passed_within_scope=True, goal_complete=False,
                  installed_bundle_replaced=False, order=['command', 'containers', 'energy'], trailer_deck_m=[33, 27],
                  status='Authored cabin, verified floor/fixture contacts and native full-carrier fixture; static robot inspection figures only.',
                  measured_fps={k: v['median_fps'] for k, v in validation['fixtures'].items() if not v['captures']},
                  artifact_sha256={str(p.relative_to(OUT)): sha(p) for p in sorted(files)},
                  external_dependency_sha256={str(p): sha(p) for p in sorted(dependencies)},
                  pending=['wall/window/door collision and actuation', 'robot lifts and actual boarding/work policies', 'moving-carrier load transfer', 'crane handling', 'full existing-game integration/performance', 'remaining track/suspension/hardware/high-speed maneuver limitations'])
    (OUT / 'candidate_manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(len(files), 'artifacts hashed')


if __name__ == '__main__':
    main()
