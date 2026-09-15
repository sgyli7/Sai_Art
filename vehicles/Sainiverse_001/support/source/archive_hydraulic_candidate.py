"""Preserve candidate source/input hashes without modifying prior candidates."""
from pathlib import Path
import hashlib,json,shutil
from suspension_physics import ROOT
OUT=ROOT/'candidates/r020_hydraulics'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    inputs=list((ROOT/'source').glob('*.py'))+list((ROOT/'godot').glob('*.gd'))+list((ROOT/'godot').glob('*.gdshader'))+list((ROOT/'design').glob('*.json'))
    inputs+=[ROOT/'assets/physics.json',ROOT/'assets/running_gear.json']
    inputs+=[ROOT/'candidates/r019_running_gear/physics'/name for name in ['suspended.xml','parameters.json']]
    for path in inputs:
        target=OUT/'source_files'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
    binding=json.loads((OUT/'bindings.json').read_text())
    dependencies=[Path(binding[n]) for n in ['glb','native_blend','shader']]
    dependencies+=[ROOT/'candidates/r019_running_gear/source/assembly.json.gz',ROOT/'candidates/r019_running_gear/source/payload_registry.json']
    artifacts=[OUT/'README.md',OUT/'bindings.json']+list((OUT/'physics').glob('*'))+[p for p in (OUT/'reports').iterdir() if p.is_file()]+[p for p in (OUT/'source_files').rglob('*') if p.is_file()]
    report=dict(candidate='r020_hydraulics',status='validated hydraulic force and exterior fixture; overall vehicle incomplete',order=['command','containers','energy'],trailer_deck_m=[33,27],
        installed_bundle_replaced=False,geometry='Unchanged r019 native assembly and export, referenced by hash.',
        source_snapshot_scope='Broad source/configuration snapshot for reproducibility. Actual tested subsets are specified by each native run source manifest; snapshot inclusion alone does not mean every script was exercised.',
        artifact_sha256={str(p.relative_to(OUT)):sha(p) for p in sorted(artifacts)},external_dependency_sha256={str(p.relative_to(ROOT)):sha(p) for p in dependencies},
        pending=['physical belt tensioner and terrain coupling','hydraulic hardware/mass/thermal design','main bogie suspension finite mechanics','ride shock agreement','boarding lifts','interiors and robots','crane operations','high-speed turn entry','full-game integration and performance'])
    (OUT/'candidate_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Archived',len(inputs),'source/input files;',len(artifacts),'artifacts and',len(dependencies),'geometry dependencies hashed')
if __name__=='__main__':main()
