"""Freeze authored source, executable inputs, failures and measured access evidence."""
from pathlib import Path
import hashlib,json,shutil
from suspension_physics import ROOT
OUT=ROOT/'candidates/r025_access'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    validation=json.loads((OUT/'reports/access_validation.json').read_text());assert validation['passed']
    shutil.copyfile(ROOT/'reports/HANDOFF-r025.md',OUT/'HANDOFF.md')
    for folder,pattern in [('source','*.py'),('godot','*.gd'),('godot','*.gdshader'),('design','*.json'),('design','*.md')]:
        for p in (ROOT/folder).glob(pattern):
            target=OUT/'source_files'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    binding=json.loads((OUT/'bindings.json').read_text());dependencies=[Path(binding[k]) for k in ['style','shader','path_extension']]
    dependencies+=list((Path(binding['style']).parent/'assets').glob('*.gdshader'))
    native=Path(binding['path_extension']).parent
    dependencies += [native/n for n in ['track_path.cpp','CMakeLists.txt','build_profile.json','bin/libleviathan_track_path.so']]
    for candidate,names in [('r023_interior',['source/robot_envelopes.json','physics/interior_contacts.json','source/assembly.json.gz','source/interior.json']),('r021_track_tension',['source/assembly.json.gz']),('r024_atelier',['physics/suspended.xml','physics/parameters.json','physics/interior_contacts.json','bindings.json'])]:
        dependencies += [ROOT/'candidates'/candidate/n for n in names]
    files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='candidate_manifest.json' and '__pycache__' not in p.parts)
    result=dict(candidate='r025_access',current_iteration_complete=True,original_full_scope_complete=False,installed_bundle_replaced=False,status='Frozen review delivery, per verified user request to close this iteration and defer remaining work. Full authored carrier with finite doors/latches, wall/window contacts and original-palette sim2sim style; actual native and MuJoCo evidence.',artifact_sha256={str(p.relative_to(OUT)):sha(p) for p in files},external_dependency_sha256={str(p):sha(p) for p in sorted(set(dependencies))},measurements=validation,limitations='Deferred to next stage: actual boarding robot policy/lifts, crane handling, main-scene integration and hardware safety/rating qualification. Earlier suspension/track/high-speed maneuver limitations remain.')
    (OUT/'candidate_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    verified=json.loads((OUT/'candidate_manifest.json').read_text())
    for p,h in verified['artifact_sha256'].items():assert sha(OUT/p)==h,p
    for p,h in verified['external_dependency_sha256'].items():assert sha(Path(p))==h,p
    print(len(files),'artifacts and',len(dependencies),'dependency entries verified')
if __name__=='__main__':main()
