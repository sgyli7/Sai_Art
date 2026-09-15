"""Stage a reproducible 003 scene in the EXISTING game's generated runtime.
No new repository/worktree or source project is created. 001 remains intact.
"""
from pathlib import Path
import argparse,json,subprocess,shutil,os,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--game',type=Path,default=Path(os.environ.get('SAI_GODOT_PROJECT','.')));p.add_argument('--terrain',choices=['polar','flat'],default='polar');p.add_argument('--headless',action='store_true');p.add_argument('--prepare-only',action='store_true');p.add_argument('--mode',choices=['manual','straight','turn','parked','review'],default='manual');p.add_argument('--seconds',type=float,default=0);p.add_argument('--output',type=Path,default=ROOT/'reports/godot_manual');a=p.parse_args()
policy_record=json.loads((ROOT/'training/policy.json').read_text())
if policy_record['physics_sha256']!=hashlib.sha256((ROOT/'assets/physics.json').read_bytes()).hexdigest():
    raise RuntimeError('Physics differs from the trained policy; retrain before deployment')
engine=Path(os.environ.get('GODOT_BIN','godot'))
runtime=a.game/'results/leviathan003/runtime';runtime.mkdir(parents=True,exist_ok=True);bundle=runtime/'leviathan003';bundle.mkdir(exist_ok=True)
for f in (ROOT/'godot').iterdir():
    if f.is_file():shutil.copy2(f,bundle/f.name)
for name in ['leviathan003.glb','physics.json','vehicle.xml']:shutil.copy2(ROOT/'assets'/name,bundle/name)
shutil.copy2(ROOT/'training/policy.json',bundle/'policy.json')
shutil.copytree(ROOT/'assets/mj_meshes',bundle/'mj_meshes',dirs_exist_ok=True)
# The game config is the base; only this generated run gets its own budget.
text=(a.game/'godot/project.godot').read_text().replace('run/main_scene="res://main.tscn"','run/main_scene="res://leviathan003/main.tscn"').replace('common/max_physics_steps_per_frame=1','common/max_physics_steps_per_frame=16').replace('velocity_steps=32','velocity_steps=12').replace('position_steps=2','position_steps=4').replace('world_boundary_shape_size=200.0','world_boundary_shape_size=40000.0')
for key,value in {'common/physics_ticks_per_second':'200','common/max_physics_steps_per_frame':'16','jolt_physics_3d/simulation/velocity_steps':'12','jolt_physics_3d/simulation/position_steps':'4','jolt_physics_3d/limits/world_boundary_shape_size':'40000.0'}.items():
    text,n=re.subn(r'^'+re.escape(key)+r'=.*$',key+'='+value,text,flags=re.M)
    if n!=1:raise RuntimeError('Unexpected game physics config key: '+key)
text+='\n[threading]\nworker_pool/max_threads=1\n'
(runtime/'project.godot').write_text(text)
shutil.copytree(a.game/'integrations/leviathan/godot/polar_range',runtime/'polar_range',dirs_exist_ok=True)
# The adapter specializes build() while inheriting this exact game's height grid.
terrain_contract=re.search(r'^## Source terrain SHA256: ([0-9a-f]{64})$',(ROOT/'godot/terrain.gd').read_text(),re.M)
if terrain_contract is None or hashlib.sha256((runtime/'polar_range/terrain.gd').read_bytes()).hexdigest()!=terrain_contract.group(1):
    raise RuntimeError('Game terrain source changed; verify the 003 CPU collision adapter against the new terrain before running')
(runtime/'atelier').mkdir(exist_ok=True)
for name in ['ui_font.tres']:
    f=a.game/'godot/atelier'/name
    if f.exists():shutil.copy2(f,runtime/'atelier'/name)
shutil.copytree(a.game/'godot/atelier/fonts',runtime/'atelier/fonts',dirs_exist_ok=True)
# Font external dependencies are staged from the game's own asset folder.
for f in (a.game/'godot/atelier').glob('*.ttf'):shutil.copy2(f,runtime/'atelier'/f.name)
for f in (a.game/'godot/atelier').glob('*.otf'):shutil.copy2(f,runtime/'atelier'/f.name)
a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
(bundle/'options.json').write_text(json.dumps(dict(mode=a.mode,terrain=a.terrain,seconds=a.seconds,output=str(a.output))))
manifest={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for folder in ['assets','godot','training'] for f in (ROOT/folder).iterdir() if f.suffix in ['.gd','.gdshader','.json','.glb','.xml','.tscn']}
external_files=[runtime/'project.godot',*(runtime/'polar_range').rglob('*')]
external_hashes={str(f.relative_to(runtime)):hashlib.sha256(f.read_bytes()).hexdigest() for f in external_files if f.is_file() and f.suffix not in ('.pyc','.log')}
(a.output/'source.json').write_text(json.dumps({'sha256':manifest,'staged_environment_sha256':external_hashes,'game':str(a.game),'runtime':str(runtime),'engine':str(engine),'engine_sha256':hashlib.sha256(engine.read_bytes()).hexdigest()},indent=2))
if a.prepare_only:print(runtime);raise SystemExit()
command=[str(engine),'--path',str(runtime),'--rendering-method','forward_plus','--disable-vsync']
if a.headless:command+=['--headless','--fixed-fps','200']
raise SystemExit(subprocess.run(command).returncode)
