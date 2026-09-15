"""Repeat the exact native polar startup that once crashed while making its shape.
Runs sequentially because all attempts share the existing generated runtime.
"""
from pathlib import Path
import argparse,subprocess,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--attempts',type=int,default=12);p.add_argument('--report',default='startup_r007');a=p.parse_args()
out=ROOT/'reports'/a.report;out.mkdir(parents=True,exist_ok=True)
launcher=Path('/home/ethan/Projects/Robot_Godot_Sim2Sim/main/run-leviathan003.sh');rows=[]
for i in range(a.attempts):
    folder=out/f'{i:03d}';folder.mkdir(exist_ok=True)
    with (folder/'engine.log').open('w') as log:
        result=subprocess.run([str(launcher),'--terrain','polar','--mode','parked','--seconds','.15','--output',str(folder)],stdout=log,stderr=subprocess.STDOUT,timeout=45)
    logfile=(folder/'engine.log').read_text();native=json.loads((folder/'result.json').read_text()) if (folder/'result.json').exists() else {}
    ok=result.returncode==0 and native.get('state',{}).get('bodies')==2 and native.get('sim_seconds',0)>=.15 and 'Program crashed' not in logfile
    rows.append(dict(attempt=i,exit_code=result.returncode,passed=ok,terrain_crash='terrain.gd:57' in logfile and 'signal 11' in logfile,sim_seconds=native.get('sim_seconds')))
    (out/'result.json').write_text(json.dumps(dict(passed=all(x['passed'] for x in rows),attempts=rows,scope='Native polar terrain initialization plus creation of the current two-body vehicle; short startup stress, not driving/performance validation.'),indent=2))
    print(json.dumps(rows[-1]),flush=True)
    if not ok:raise SystemExit(1)
