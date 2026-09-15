"""Preserve exact source, editable model, neutral export and measured scope."""
from pathlib import Path
import hashlib,json,shutil
from suspension_physics import ROOT
OUT=ROOT/'candidates/r021_track_tension'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    inputs=list((ROOT/'source').glob('*.py'))+list((ROOT/'godot').glob('*.gd'))+list((ROOT/'godot').glob('*.gdshader'))+list((ROOT/'design').glob('*.json'))
    inputs+=[ROOT/'assets/physics.json',ROOT/'assets/running_gear.json']+[ROOT/'candidates/r020_hydraulics/physics'/n for n in ['suspended.xml','parameters.json']]
    for p in inputs:
        target=OUT/'source_files'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    files=[OUT/'README.md',OUT/'bindings.json']+[p for p in (OUT/'reports').iterdir() if p.is_file()]
    for folder in ['source','assets','physics','source_files']:files.extend(p for p in (OUT/folder).rglob('*') if p.is_file() and p.suffix!='.blend1')
    dependencies=[ROOT/'candidates/r019_running_gear/source/assembly.json.gz',ROOT/'candidates/r019_running_gear/source/payload_registry.json']
    report=dict(candidate='r021_track_tension',status='finite idler/belt mechanism and exterior fixture validated within documented scope; full vehicle incomplete',installed_bundle_replaced=False,
        order=['command','containers','energy'],trailer_deck_m=[33,27],dynamic_bodies=153,dofs=158,
        performance='71 FPS rough-patch exterior / 93 FPS flat 100 km/h exterior on GB10 at 1080p; materially slower than r020, complete-game gate open',
        artifact_sha256={str(p.relative_to(OUT)):sha(p) for p in sorted(files)},external_dependency_sha256={str(p.relative_to(ROOT)):sha(p) for p in dependencies},
        source_snapshot_scope='Broad source snapshot, not evidence that every script was tested. Exact per-run subsets and native specifications are archived with raw reports.',
        pending=['reduce runtime cost before complete-game workload','unsupported belt-span ground contact and slack/self-contact behavior','hardware mass/thermal/recoil qualification','main-bogie finite suspension and shock agreement','interiors and robot lifts/boarding','operating cranes','high-speed maneuver transitions','main-game integration and full-scene performance'])
    (OUT/'candidate_manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(len(inputs),'source inputs;',len(files),'artifacts hashed')
if __name__=='__main__':main()
