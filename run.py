#!/usr/bin/env python3
"""Materialize portable source paths and launch in an existing Sim2Sim checkout."""
from pathlib import Path
import argparse,gzip,hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'vehicles/Sainiverse_001'
CACHE=ROOT/'.runtime/Sainiverse_001'
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
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--game',type=Path,default=Path(os.environ['SAI_GODOT_PROJECT']) if 'SAI_GODOT_PROJECT' in os.environ else None,help='Existing Robot_Godot_Sim2Sim checkout')
p.add_argument('--action',choices=['drive','mujoco','unpack-blend','prepare'],default='drive')
a,rest=p.parse_known_args();cache=materialize()
if a.action=='unpack-blend':
    out=ROOT/'Sainiverse_001.blend'
    with gzip.open(SOURCE/'source/Sainiverse_001.blend.gz','rb') as src,out.open('wb') as dst:shutil.copyfileobj(src,dst)
    print(out);raise SystemExit()
if a.action=='prepare':print(cache);raise SystemExit()
if a.action=='mujoco':
    raise SystemExit(subprocess.call([sys.executable,str(cache/'source/check_mujoco.py'),*rest]))
if a.game is None:p.error('--game is required; point it at your existing Robot_Godot_Sim2Sim checkout')
game=a.game.expanduser().resolve()
if not game.is_dir() or not ((game/'.git').exists() or (game/'project.godot').exists() or (game/'results/leviathan003/runtime/project.godot').exists()):p.error('Select the existing game checkout or its configured integration root')
runtime=game/'results/leviathan003/runtime';runtime.mkdir(parents=True,exist_ok=True)
if not (runtime/'project.godot').exists():shutil.copy2(ROOT/'integration/review_project.godot',runtime/'project.godot')
raise SystemExit(subprocess.call([sys.executable,str(cache/'source/launch.py'),'--game',str(game),*rest]))
