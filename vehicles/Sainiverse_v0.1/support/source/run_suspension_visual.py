"""Serial native rendered candidate run in the existing project; preserve settings."""
from pathlib import Path
import argparse,hashlib,json,signal,subprocess
from suspension_physics import ROOT
RUNTIME=Path('/home/ethan/Projects/Robot_Godot_Sim2Sim/main/results/leviathan003/runtime')
OUT=ROOT/'candidates/r018_visual_suspension'
def main():
    global OUT
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--seconds',type=float,default=30.);p.add_argument('--speed',type=float,default=5.);p.add_argument('--terrain',default='rough');p.add_argument('--curvature',type=float,default=0.);p.add_argument('--capture',action='store_true');p.add_argument('--view',choices=['whole','track','interior','workshop','controls','exterior','doorway'],default='whole');p.add_argument('--candidate',choices=['r018_visual_suspension','r019_running_gear','r020_hydraulics','r021_track_tension','r022_runtime','r023_interior','r024_atelier','r025_access'],default='r018_visual_suspension');p.add_argument('--probe-mode',choices=['normal','freeze','static','freeze_static','no_upload','cached_path'],default='normal');p.add_argument('--access-mode',choices=['parked','cycle'],default='parked');a=p.parse_args()
    OUT=ROOT/'candidates'/a.candidate
    assert a.label.replace('_','').isalnum()
    report=OUT/'reports'/a.label;assert not report.with_suffix('.log').exists()
    # Read-only use of the exact previously transferred physical spec.
    spec=ROOT/'candidates/r017_turning/physics/native_spec.json' if a.candidate=='r018_visual_suspension' else OUT/'physics/native_spec.json'
    binding_path=OUT/'bindings.json'
    review=ROOT/'godot/suspension_visual_review.gd'
    if a.candidate=='r023_interior':review=ROOT/'godot/interior_review.gd'
    if a.candidate=='r024_atelier':review=ROOT/'godot/atelier_review.gd'
    if a.candidate=='r025_access':review=ROOT/'godot/access_review.gd'
    if a.probe_mode!='normal':
        assert a.candidate=='r022_runtime'
        review=ROOT/'godot/debug/runtime_cost_probe.gd'
        if 'static' in a.probe_mode:binding_path=OUT/'debug/static_bindings.json'
        if a.probe_mode=='no_upload':review=ROOT/'godot/debug/runtime_no_upload_review.gd'
        if a.probe_mode=='cached_path':review=ROOT/'godot/debug/runtime_cached_path_review.gd'
    binding=json.loads(binding_path.read_text());glb=Path(binding['glb'])
    files=[Path(__file__),spec,binding_path,review,glb]+[ROOT/'godot'/n for n in ['suspension_native.gd','hydraulic_suspension.gd','track_tension.gd','track_path.gd','train_steering.gd','physics_origin_frame.gd','suspension_visual.gd','suspension_visual_review.gd','sprung_wheel.gdshader']]
    if 'shader' in binding:files.append(Path(binding['shader']))
    if 'path_extension' in binding:
        files.extend([Path(binding['path_extension'])]+[Path(binding['path_extension']).parent/n for n in ['track_path.cpp','CMakeLists.txt','build_profile.json','bin/libleviathan_track_path.so']])
    if 'interior_manifest' in binding:
        files.extend([Path(binding['interior_manifest']),Path(binding['interior_contacts']),ROOT/'godot/interior_contacts.gd',Path(binding['interior_manifest']).parent/'robot_scale_figures.json.gz',glb.parent/'sai_scale_figure.glb',glb.parent/'microduck_scale_figure.glb'])
    if 'style' in binding:
        files.extend([Path(binding['style']),ROOT/'godot/interior_review.gd']+list((Path(binding['style']).parent/'assets').glob('*.gdshader')))
    if 'access_manifest' in binding:
        files.extend([Path(binding['access_manifest']),Path(binding['access_manifest']).parent/'access_probes.json',ROOT/'godot/cabin_access.gd',ROOT/'godot/atelier_review.gd'])
    if a.probe_mode=='no_upload':files.append(ROOT/'godot/debug/runtime_no_upload.gd')
    if a.probe_mode=='cached_path':files.append(ROOT/'godot/debug/runtime_cached_path.gd')
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    hashes={str(f.relative_to(ROOT)):sha(f) for f in files}
    archive=OUT/'reports'/(a.label+'_source')
    for f in files:
        if f==glb:continue
        target=archive/f.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(f.read_bytes())
    project=RUNTIME/'project.godot';saved=project.read_bytes();text=saved.decode()
    assert 'velocity_steps=12' in text and 'position_steps=4' in text
    proc=None;code=None
    def stop(signum,frame):raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM,stop)
    try:
        runtime_text=text.replace('velocity_steps=12','velocity_steps=64').replace('position_steps=4','position_steps=8')
        for key,value in binding.get('native_project_settings',{}).items():
            assert key=='physics/jolt_physics_3d/simulation/body_pair_contact_cache_enabled' and value is False
            setting=key.removeprefix('physics/')
            assert setting+'=' not in runtime_text
            runtime_text=runtime_text.replace('[physics]','[physics]\n'+setting+'=false')
        project.write_text(runtime_text)
        with report.with_suffix('.log').open('w') as log:
            proc=subprocess.Popen(['/home/ethan/.local/bin/godot','--path',str(RUNTIME),'--script',str(review),'--',f'spec={spec}',f'output_root={OUT}/reports',f'output={a.label}.json',f'seconds={a.seconds}',f'speed={a.speed}',f'terrain={a.terrain}',f'curvature={a.curvature}',f'capture={str(a.capture).lower()}',f'view={a.view}',f'bindings={binding_path}',f'probe_mode={a.probe_mode}',f'access_mode={a.access_mode}'],stdout=log,stderr=subprocess.STDOUT)
            code=proc.wait(timeout=max(120,a.seconds*5))
    finally:
        if proc is not None and proc.poll() is None:proc.terminate();proc.wait()
        project.write_bytes(saved)
        metadata=dict(arguments=vars(a),native_project_settings=binding.get('native_project_settings',{}),returncode=code,source_sha256=hashes,runtime_before_sha256=hashlib.sha256(saved).hexdigest(),runtime_restored=project.read_bytes()==saved,changed_sources=[str(f) for f in files if sha(f)!=hashes[str(f.relative_to(ROOT))]])
        (OUT/'reports'/(a.label+'_source.json')).write_text(json.dumps(metadata,indent=2)+'\n')
    print(report.with_suffix('.log').read_text()[-6000:])
    assert code==0 and report.with_suffix('.json').exists()
    assert (OUT/'reports'/(a.label+'_visual.json')).exists()
    assert 'ERROR:' not in report.with_suffix('.log').read_text()
    assert not metadata['changed_sources']
if __name__=='__main__':main()
