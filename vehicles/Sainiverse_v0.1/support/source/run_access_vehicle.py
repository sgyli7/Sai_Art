"""Full carrier drive request while doors cycle; native counterpart runs separately."""
from pathlib import Path
import argparse
import hashlib
import json
import time
import numpy as np
from suspension_physics import ROOT, Env, C
from access_probes import probe

OUT = ROOT / 'candidates/r025_access'


def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--seconds',type=float,default=45.);p.add_argument('--mode',choices=['cycle','parked'],default='cycle');p.add_argument('--speed',type=float,default=5.);p.add_argument('--terrain',default='flat');args=p.parse_args()
    output=OUT/'reports'/(args.label+'.json');assert not output.exists()
    path=OUT/'physics/suspended.xml';parameters=json.loads((OUT/'physics/parameters.json').read_text());env=Env(args.terrain,False,True,path,parameters)
    start=time.monotonic();samples=[];peak=0.;door_peak=np.zeros(6);ray_results=[]
    rays=json.loads((OUT/'source/access_probes.json').read_text())
    for step in range(round(args.seconds/C['dt_s'])):
        env.access.requests[:]=args.mode=='cycle' and 5.<=env.d.time<28.
        speed=env.substep(args.speed if env.d.time>=10. else 0.)
        if len(ray_results)<3 and env.d.time>=[4.,24.,44.][len(ray_results)]:ray_results.append(probe(env,rays))
        peak=max(peak,abs(speed));door_peak=np.maximum(door_peak,abs(env.access.q))
        if step%20==19:
            row=env.record(speed);row['access']=env.access.state();samples.append(row)
        assert np.isfinite(env.d.qpos).all() and min(env.d.xmat[h].reshape(3,3)[2,2] for h in env.hulls)>.5
    paths=[path,OUT/'physics/parameters.json',OUT/'source/access_probes.json',ROOT/'source/access_probes.py',ROOT/'source/suspension_physics.py',ROOT/'source/cabin_access.py',Path(__file__)]
    result=dict(engine='MuJoCo',failed=False,seconds=float(env.d.time),wall_seconds=time.monotonic()-start,samples=samples,ray_results=ray_results,peak_speed_kmh=peak*3.6,maximum_door_angles_deg=np.degrees(door_peak).tolist(),total_mass_kg=env.total_mass,
                scope='Actual full 159-body carrier with wall/window/door contacts and finite door servos. Drive requested during open-door interval; controller gates traction. No robot policy or hardware qualification.',arguments=vars(args),source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['samples','source_sha256','ray_results']},indent=2))


if __name__=='__main__':main()
