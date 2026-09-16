"""Archive reproducible appearance inputs and actual native evidence."""
from pathlib import Path
import hashlib
import json
import shutil
from suspension_physics import ROOT

OUT = ROOT / 'candidates/r024_atelier'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    verification = json.loads((OUT / 'reports/style_validation.json').read_text())
    assert verification['passed']
    for folder, glob in [('godot', '*.gd'), ('godot', '*.gdshader'), ('source', '*.py'), ('design', 'VISUAL_STYLE.md')]:
        for p in (ROOT / folder).glob(glob):
            target = OUT / 'source_files' / p.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)
    bindings = json.loads((OUT / 'bindings.json').read_text())
    dependencies = [Path(bindings[k]) for k in ['glb', 'native_blend', 'shader', 'path_extension', 'interior_manifest', 'interior_contacts']]
    native = Path(bindings['path_extension']).parent
    dependencies += [native / n for n in ['track_path.cpp', 'CMakeLists.txt', 'build_profile.json', 'bin/libleviathan_track_path.so']]
    dependencies += [Path(bindings['glb']).parent / n for n in ['sai_scale_figure.glb', 'microduck_scale_figure.glb']]
    dependencies += list((ROOT / 'candidates/r023_interior/reports').glob('exterior_before_style_v3*.*'))
    files = [p for p in OUT.rglob('*') if p.is_file() and p.name != 'candidate_manifest.json' and '__pycache__' not in p.parts]
    result = dict(candidate='r024_atelier', goal_complete=False, installed_bundle_replaced=False,
                  requested_palette_preserved=True, full_geometry_reused=True, physical_states_unchanged=True,
                  status='Current complete-model Godot appearance revision with actual sim2sim enamel/ink shading and original pigments.',
                  artifact_sha256={str(p.relative_to(OUT)): sha(p) for p in sorted(files)},
                  external_dependency_sha256={str(p): sha(p) for p in dependencies},
                  measured_performance=verification['fixtures']['style_whole_180'],
                  pending='Original full-game, robot/boarding/crane and remaining physical qualification work continues.')
    (OUT / 'candidate_manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(len(files), 'artifacts hashed')


if __name__ == '__main__':
    main()
