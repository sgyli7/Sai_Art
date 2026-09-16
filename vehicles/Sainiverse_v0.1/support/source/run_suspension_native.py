"""Run the candidate in the existing Godot runtime, restoring its settings."""
from pathlib import Path
import argparse,hashlib,json,signal,subprocess,sys
from export_suspension_native import main as export

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=Path('/home/ethan/Projects/Robot_Godot_Sim2Sim/main/results/leviathan003/runtime')
OUT=ROOT/'candidates/r015_articulation/reports/suspension'

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--terrain',default='flat');p.add_argument('--speed',type=float,default=0.);p.add_argument('--seconds',type=float,default=30.);p.add_argument('--rigid',action='store_true');p.add_argument('--train',action='store_true');p.add_argument('--containers-first',action='store_true');p.add_argument('--brake-at',type=float,default=-1.);p.add_argument('--velocity-steps',type=int,default=64);p.add_argument('--position-steps',type=int,default=8);p.add_argument('--start-x',type=float,default=0.);p.add_argument('--rebase-distance',type=float,default=-1.);p.add_argument('--turning',action='store_true');p.add_argument('--curvature',type=float,default=0.);p.add_argument('--spec',type=Path);p.add_argument('--output-root',type=Path);args=p.parse_args()
    assert bool(args.spec)==bool(args.output_root),'Supply both readonly spec and output root.'
    if args.spec:
        assert not (args.turning or args.train or args.rigid)
        args.spec=args.spec.resolve();args.output_root=args.output_root.resolve()
    if args.turning:args.train=True;args.containers_first=True;assert not args.rigid
    assert args.label.replace('_','').isalnum()
    assert not args.containers_first or args.train,'Container order applies to the three-section train.'
    train_root=ROOT/'candidates/r016_modular'/('train_containers_first' if args.containers_first else 'train')
    if args.turning:train_root=ROOT/'candidates/r017_turning'
    output_root=args.output_root if args.spec else train_root/'reports' if args.train else OUT
    log_path=output_root/(args.label+'.log');result_path=output_root/(args.label+'.json')
    assert not log_path.exists() and not result_path.exists(),'Use a fresh label; retain earlier evidence.'
    project=RUNTIME/'project.godot';saved=project.read_bytes();text=saved.decode()
    assert 'velocity_steps=12' in text and 'position_steps=4' in text,'Inspect unexpected runtime settings before changing them.'
    spec_path=args.spec or ROOT/'candidates/r015_articulation/physics/native_spec.json'
    if args.spec:pass
    elif args.turning:
        from turning_physics import environment
        from export_suspension_native import export_environment
        spec_path=train_root/'physics/native_spec.json';export_environment(environment(args.terrain),spec_path)
    elif args.train:
        from train_physics import environment
        from export_suspension_native import export_environment
        spec_path=train_root/'physics/native_spec.json';export_environment(environment(args.terrain,args.rigid,out=train_root),spec_path)
    else:export()
    files=[ROOT/'godot/suspension_native.gd',ROOT/'godot/physics_origin_frame.gd',Path(__file__),ROOT/'source/suspension_physics.py',spec_path]+([ROOT/'source/train_physics.py',train_root/'source/payload_registry.json'] if args.train else [])
    files += [ROOT/'godot/hydraulic_suspension.gd',ROOT/'source/hydraulic_suspension.py',ROOT/'godot/track_tension.gd',ROOT/'source/track_tension.py',ROOT/'godot/train_steering.gd']+([ROOT/'source/turning_physics.py',ROOT/'source/turning_control.py',ROOT/'design/turning_candidate.json'] if args.turning else [])
    source_hashes={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    archive=output_root/(args.label+'_source_files')
    for f in files:
        target=archive/f.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(f.read_bytes())
    def terminate(signum,frame):raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM,terminate)
    proc=None;tested=b'';code=None
    try:
        tested=text.replace('velocity_steps=12',f'velocity_steps={args.velocity_steps}').replace('position_steps=4',f'position_steps={args.position_steps}').encode();project.write_bytes(tested)
        with log_path.open('w') as log:
            proc=subprocess.Popen(['/home/ethan/.local/bin/godot','--headless','--fixed-fps','200','--path',str(RUNTIME),'--script',str(ROOT/'godot/suspension_native.gd'),'--',f'terrain={args.terrain}',f'speed={args.speed}',f'curvature={args.curvature}',f'seconds={args.seconds}',f'rigid={str(args.rigid).lower()}',f'brake_at={args.brake_at}',f'start_x={args.start_x}',f'rebase_distance={args.rebase_distance}',f'spec={spec_path}',f'output_root={output_root}',f'output={result_path.name}'],stdout=log,stderr=subprocess.STDOUT)
            code=proc.wait()
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate();proc.wait()
        project.write_bytes(saved)
        sha=lambda b:hashlib.sha256(b).hexdigest()
        (output_root/(args.label+'_source.json')).write_text(json.dumps(dict(runtime_before_sha256=sha(saved),runtime_tested_sha256=sha(tested),runtime_restored=project.read_bytes()==saved,returncode=code,arguments=vars(args),
            source_sha256=source_hashes,source_changed_during_run=[str(f.relative_to(ROOT)) for f in files if sha(f.read_bytes())!=source_hashes[str(f.relative_to(ROOT))]]),indent=2,default=str)+'\n')
    print(log_path.read_text()[-6000:])
    assert code==0,f'Godot exited {code}; log retained'
    assert result_path.exists(),'No native result'
    assert 'ERROR:' not in log_path.read_text(),'Native error; inspect log'

if __name__=='__main__':main()
