"""Freeze runtime optimization source and provenance without duplicating geometry."""
from pathlib import Path
import hashlib,json,shutil,subprocess
from suspension_physics import ROOT
OUT=ROOT/'candidates/r022_runtime'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    validation=json.loads((OUT/'reports/runtime_validation.json').read_text());assert validation['passed']
    for folder,glob in [('source','*.py'),('godot','*.gd'),('godot','*.gdshader'),('design','*.json')]:
        for p in (ROOT/folder).glob(glob):
            target=OUT/'source_files'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    for p in (ROOT/'godot/debug').glob('runtime_*.gd'):
        target=OUT/'source_files'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    native=ROOT.parents[1]/'native'
    for p in [native/'api/extension_api.json',native/'.deps/godot-cpp/LICENSE.md']:
        target=OUT/'source_files/native_api'/p.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    b=json.loads((OUT/'bindings.json').read_text())
    dependencies=[Path(b['glb']),Path(b['native_blend']),ROOT/'candidates/r021_track_tension/source/assembly.json.gz',ROOT/'candidates/r021_track_tension/assets/tensioned_tracks.gdshader',native/'api/extension_api.json']
    fixtures=validation['fixtures']
    files=[p for p in OUT.rglob('*') if p.is_file() and 'build' not in p.relative_to(OUT).parts and p.name!='candidate_manifest.json']
    # Raw per-run sources are retained, including unsuccessful diagnostic probes.
    report=dict(candidate='r022_runtime',passed_within_scope=True,goal_complete=False,installed_bundle_replaced=False,
        status='Same full exterior and exact independent native dynamics; pure display-path native kernel plus batched float texture state.',order=['command','containers','energy'],trailer_deck_m=[33,27],
        physics='Byte-identical r021 native_spec.json, parameters.json, suspended.xml; no retraining or new physical model claim.',
        native_platform='Godot 4.7.2 Linux arm64 single-precision ABI, godot-cpp template_debug; other targets not built',
        godot_cpp_commit=subprocess.check_output(['git','-C',str(native/'.deps/godot-cpp'),'rev-parse','HEAD'],text=True).strip(),
        measured_fps={k:v['median_fps'] for k,v in fixtures.items() if not v['captures']},
        artifact_sha256={str(p.relative_to(OUT)):sha(p) for p in sorted(files)},external_dependency_sha256={str(p):sha(p) for p in dependencies},
        pending=['full-game integration and full-scene performance','interior and robot lifts/boarding','crane physics/handling','unsupported belt span ground contact and slack/derailment','finite main-bogie suspension and shock agreement','hardware qualification','high-speed maneuver transitions'])
    (OUT/'candidate_manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(len(files),'artifacts hashed')
if __name__=='__main__':main()
