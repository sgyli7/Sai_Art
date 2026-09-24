"""Default Sainiverse_v0.1 native driving entry in the existing game runtime."""
from pathlib import Path
import argparse,subprocess,os,re,json,time,fcntl,signal
O=Path(__file__).resolve().parents[1];R=O/'support'
p=argparse.ArgumentParser();p.add_argument('--game',type=Path,default=Path(os.environ.get('SAI_GODOT_PROJECT','.')));p.add_argument('--mode',choices=['manual','ui_test','lift_preview_cycle','parked','straight','turn','lift_cycle','traverse','hill_turn','cabin_patrol','cockpit_patrol','deck_patrol','sai_board','sai_board_002','sai_cockpit','worksite','equipment_cycle','cockpit_test','cargo_cycle'],default='manual');p.add_argument('--terrain',choices=['flat','rough','ramp','ditch','hills','polar'],default='flat');p.add_argument('--seconds',type=float,default=0);p.add_argument('--view',default='whole');p.add_argument('--theme',choices=['black','desert','white','blue','yellow'],default='black');p.add_argument('--headless',action='store_true');p.add_argument('--prepare-only',action='store_true');p.add_argument('--pv',action='store_true');p.add_argument('--pv-fps',type=int,default=15);p.add_argument('--capture',action='store_true');p.add_argument('--clean-capture',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
runtime=a.game/'results/leviathan003/runtime';project=runtime/'project.godot';assert project.exists()
lock=open(runtime/'sainiverse.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
out=a.output or O/'reports'/('drive_'+time.strftime('%Y%m%d_%H%M%S'));out=out.resolve();out.mkdir(parents=True,exist_ok=True)
text=project.read_text();modified=text
sai60=bool(os.environ.get('SAINIVERSE_SAI60_POLICY',''))
physics_defaults=[('jolt_physics_3d/simulation/velocity_steps',os.getenv('LEVIATHAN_VELOCITY_STEPS','12')),('jolt_physics_3d/simulation/position_steps','8'),('common/max_physics_steps_per_frame','32')]
if sai60:physics_defaults.append(('common/physics_ticks_per_second','60'))
for key,value in physics_defaults:modified,n=re.subn('^'+re.escape(key)+'=.*$',key+'='+value,modified,flags=re.M);assert n==1,key
key='jolt_physics_3d/simulation/body_pair_contact_cache_enabled'
if key+'=' not in modified:modified=modified.replace('[physics]','[physics]\n'+key+'=false')
else:modified=re.sub('^'+re.escape(key)+'=.*$',key+'=false',modified,flags=re.M)
if a.prepare_only:print(runtime);raise SystemExit()
terrain=a.terrain
cmd=[os.environ.get('GODOT_BIN','godot'),'--path',str(runtime),'--script',str(O/'runtime/drive.gd')]
# Acceptance for 60/60 coworld must not use --fixed-fps 200.
if a.headless:cmd+=['--headless','--fixed-fps','60' if sai60 else '200']
if a.pv:cmd+=['--fixed-fps',str(a.pv_fps),'--resolution','1280x720']
speed=27.777778 if a.mode=='straight' else 7. if a.mode=='turn' else 4.5 if a.mode=='hill_turn' else 8. if a.mode=='traverse' else 0.
cmd+=['--',f'spec={O}/physics/native_spec.json',f'bindings={O}/bindings.json',f'output_root={out}',f'output=run.json',f'seconds={a.seconds or 86400}',f'speed={speed}',f'curvature={.01 if a.mode=="turn" else 0}',f'terrain={terrain}',f'view={a.view}',f'mode={a.mode}',f'theme={a.theme}',f'pv={str(a.pv).lower()}',f'capture={str(a.capture).lower()}',f'clean_capture={str(a.clean_capture).lower()}']
proc=None
try:
 project.write_text(modified)
 with (out/'run.log').open('w') as log:
  proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'DISPLAY':os.getenv('DISPLAY',':1'),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
  code=proc.wait()
finally:
 if proc is not None and proc.poll() is None:proc.terminate();proc.wait()
 project.write_text(text)
 (out/'launch.json').write_text(json.dumps(dict(args=vars(a),command=cmd,project_restored=project.read_text()==text),default=str,indent=2))
print(out)
print((out/'run.log').read_text()[-1800:])
raise SystemExit(code)
