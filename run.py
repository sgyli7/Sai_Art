#!/usr/bin/env python3
"""Materialize portable source paths and launch in an existing Sim2Sim checkout."""
from pathlib import Path
import argparse,gzip,hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'vehicles/Sainiverse_v0.1'
CACHE=ROOT/'.runtime/Sainiverse_v0.1'
TEXT={'.py','.gd','.gdshader','.json','.gdextension','.xml','.txt','.md'}
def materialize():
    CACHE.mkdir(parents=True,exist_ok=True)
    for src in SOURCE.rglob('*'):
        if not src.is_file():continue
        rel=src.relative_to(SOURCE);dst=CACHE/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        if src.suffix in TEXT:
            data=src.read_text().replace('@SAI_ROOT@',str(CACHE))
            if not dst.exists() or dst.read_text()!=data:dst.write_text(data)
        elif not dst.exists() or dst.stat().st_size!=src.stat().st_size or dst.stat().st_mtime_ns!=src.stat().st_mtime_ns:shutil.copy2(src,dst)
    (CACHE/'reports').mkdir(exist_ok=True)
    return CACHE

def sync_current_robots(game, runtime):
    """Use the game's prepared robot models and controllers in this review world."""
    source=game/'results/workshop-hub/runtime'
    if not (source/'robot.gd').is_file() or not (source/'runtime_assets/deployment.json').is_file():
        raise RuntimeError('Prepare the current game runtime with ./run-workshop.sh --prepare-only before launching Sainiverse')
    changed=False
    game_sources=game/'godot'
    if not game_sources.is_dir():game_sources=game/'Godot_Sim2Sim/godot'
    groups=[(source,name) for name in ('robot.gd','sai','sai_policy','native','generated','runtime_assets','standalone','visuals')]
    if game_sources.is_dir():groups += [(game_sources,name) for name in ('sai','hub/sai.gd','hub/sai_materials.gd')]
    selected={}
    for base,name in groups:
        item=base/name
        files=[item] if item.is_file() else item.rglob('*') if item.is_dir() else []
        for src in files:
            if not src.is_file() or src.is_symlink() or src.suffix in ('.import','.uid'):continue
            selected[src.relative_to(base)]=src
    family_root=Path(os.environ.get('SAI_ROBOTS_ROOT','/home/ethan/Projects/RobotDesign/delivery/Sai_Rotbots'))
    sai002=family_root/'robots/Sai_Agent_002/models/full'
    if not (sai002/'robot.json').is_file():
        raise RuntimeError('Sai 002 model is missing; set SAI_ROBOTS_ROOT to the Sai_Rotbots release checkout')
    for src in [sai002/'robot.json',*(sai002/'assets').glob('*.glb')]:
        selected[Path('sai_robots/Sai_Agent_002')/src.relative_to(sai002)]=src
    for rel,src in selected.items():
        if rel==Path('visuals/microduck/style.gd'):
            continue  # This release supplies the avatar-only styling API.
        dst=runtime/rel
        data=src.read_bytes()
        if rel==Path('robot.gd'):
            old=b'\tapply_cargo(s)\n'
            if data.count(old)!=1:raise RuntimeError('Sai robot adapter changed; inspect its cargo actuation before loading Sai 002')
            data=data.replace(old,b'\tif drives.size() >= 25:apply_cargo(s)\n')
        elif rel==Path('sai/native_controller.gd'):
            old=b'state.get("robot_id") != "Sai_Agent_001"'
            if data.count(old)!=1:raise RuntimeError('Sai controller identity contract changed')
            data=data.replace(old,b'state.get("robot_id") not in ["Sai_Agent_001","Sai_Agent_002"]')
        elif rel==Path('sai_robots/Sai_Agent_002/robot.json'):
            if b'res://sai_agent/assets/' not in data:raise RuntimeError('Sai 002 asset paths changed')
            data=data.replace(b'res://sai_agent/assets/',b'res://sai_robots/Sai_Agent_002/assets/')
        if dst.is_file() and dst.read_bytes()==data:continue
        dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data);changed=True
    return changed

def sync_sai60_runtime(runtime):
    """Install the existing 60 Hz Sai bundle used by the desktop coworld path."""
    profile_id = os.environ.get('SAINIVERSE_SAI60_POLICY', '')
    if not profile_id:
        return False
    source = ROOT / 'integration/sai60'
    profile_path = source / 'sai_policy/experimental' / f'{profile_id}.json'
    if not profile_path.is_file():
        raise RuntimeError(f'Sai 60 Hz profile is not bundled: {profile_id}')
    profile = json.loads(profile_path.read_text())
    policy_path = profile_path.parent / profile['actor']
    if hashlib.sha256(policy_path.read_bytes()).hexdigest() != profile['onnx_sha256']:
        raise RuntimeError(f'Sai 60 Hz policy hash mismatch: {profile_id}')
    changed = False
    for src in source.rglob('*'):
        if not src.is_file():
            continue
        dst = runtime / src.relative_to(source)
        data = src.read_bytes()
        if dst.is_file() and dst.read_bytes() == data:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        changed = True
    return changed
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--game',type=Path,default=Path(os.environ['SAI_GODOT_PROJECT']) if 'SAI_GODOT_PROJECT' in os.environ else None,help='Existing Robot_Godot_Sim2Sim checkout')
p.add_argument('--action',choices=['drive','mujoco','equipment-mujoco','cockpit-mujoco','record-pvs','unpack-blend','prepare'],default='drive')
a,rest=p.parse_known_args();cache=materialize()
if a.action=='unpack-blend':
    out=ROOT/'Sainiverse_v0.1.blend'
    with gzip.open(SOURCE/'source/Sainiverse_v0.1.blend.gz','rb') as src,out.open('wb') as dst:shutil.copyfileobj(src,dst)
    print(out);raise SystemExit()
if a.action=='prepare':print(cache);raise SystemExit()
if a.action in ['mujoco','equipment-mujoco','cockpit-mujoco']:
    script={'mujoco':'check_mujoco.py','equipment-mujoco':'check_equipment.py','cockpit-mujoco':'check_cockpit_mujoco.py'}[a.action]
    raise SystemExit(subprocess.call([sys.executable,str(cache/'source'/script),*rest]))
if a.game is None:p.error('--game is required; point it at your existing Robot_Godot_Sim2Sim checkout')
game=a.game.expanduser().resolve()
if not game.is_dir() or not ((game/'.git').exists() or (game/'run-native.sh').is_file() and (game/'godot').is_dir() or (game/'project.godot').exists() or (game/'results/leviathan003/runtime/project.godot').exists()):p.error('Select the existing game checkout or its configured integration root')
runtime=game/'results/leviathan003/runtime';runtime.mkdir(parents=True,exist_ok=True)
if not (runtime/'project.godot').exists():shutil.copy2(ROOT/'integration/review_project.godot',runtime/'project.godot')
# Install only into the existing review integration directory, never the game's
# source tree or its workshop/science-station runtime. Replace our old symlinks
# themselves, so copies cannot write through to another project.
robot_source=ROOT/'integration/robots'
marker=runtime/'.sainiverse_robot_snapshot'
snapshot=hashlib.sha256((robot_source/'manifest.json').read_bytes()).hexdigest()
changed=False
if not marker.exists() or marker.read_text()!=snapshot:
    for src in robot_source.iterdir():
        if src.name in ['licenses','manifest.json']:continue
        dst=runtime/src.name
        if dst.is_symlink():dst.unlink()
        if src.is_dir():shutil.copytree(src,dst,dirs_exist_ok=True)
        else:shutil.copy2(src,dst)
    changed=True
worker_source=robot_source/'standalone/carrier_worker.gd'
worker_target=runtime/'standalone/carrier_worker.gd'
if not worker_target.is_file() or worker_target.read_bytes()!=worker_source.read_bytes():
    worker_target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(worker_source,worker_target)
    changed=True
if os.environ.get('SAINIVERSE_USE_GAME_ROBOTS','')=='1':
    changed=sync_current_robots(game,runtime) or changed
changed=sync_sai60_runtime(runtime) or changed
# The release's avatar-only style API must be present even when the game's
# older prepared robot snapshot supplies the rest of the visual resources.
style_source=robot_source/'visuals/microduck/style.gd'
style_target=runtime/'visuals/microduck/style.gd'
if style_target.is_symlink():style_target.unlink()
if not style_target.is_file() or style_target.read_bytes()!=style_source.read_bytes():
    style_target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(style_source,style_target)
    changed=True
if changed:
    godot=os.environ.get('GODOT_BIN','godot')
    subprocess.run([godot,'--headless','--editor','--path',str(runtime),'--import'],check=True)
    marker.write_text(snapshot)
script='record_pvs.py' if a.action=='record-pvs' else 'launch.py'
raise SystemExit(subprocess.call([sys.executable,str(cache/'source'/script),'--game',str(game),*rest]))
