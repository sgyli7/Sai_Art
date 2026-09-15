"""Full new MuJoCo vehicle movement; no posed robot or scene substitution."""
from pathlib import Path
import json,time,hashlib
import numpy as np
from suspension_physics import ROOT,Env,C
OUT=ROOT/'candidates/r023_interior'
def main():
    path=OUT/'physics/suspended.xml';manifest=json.loads((OUT/'physics/parameters.json').read_text());env=Env('rough',False,True,path,manifest)
    output=OUT/'reports/rough_mujoco.json';assert not output.exists()
    samples=[];peak=0.;start=time.monotonic()
    for step in range(round(65/C['dt_s'])):
        active=env.d.time>=10;speed=env.substep(5. if active else 0.,curvature_request=0.);peak=max(peak,abs(speed))
        if step%20==19:samples.append(env.record(speed))
        assert np.isfinite(env.d.qpos).all() and min(env.d.xmat[h].reshape(3,3)[2,2] for h in env.hulls)>.5
    previous=json.loads((ROOT/'candidates/r021_track_tension/reports/rough_mujoco.json').read_text());delta={}
    for key in ['hull_positions','speed_m_s','wheel_travel_m','hitch_coordinates']:
        delta[key]=float(np.max(np.abs(np.array([s[key] for s in samples])-np.array([s[key] for s in previous['samples']]))))
    report=dict(engine='MuJoCo',failed=False,seconds=float(env.d.time),wall_seconds=time.monotonic()-start,samples=samples,peak_speed_kmh=peak*3.6,previous_state_max_deltas=delta,scope='Full 153-body r023 carrier with 35 new floor/fixture collision shapes, same r021 finite hydraulics, belt forces and existing trained steering gains. No real robot contact or new training.',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),path,OUT/'physics/parameters.json',ROOT/'source/suspension_physics.py',ROOT/'source/hydraulic_suspension.py',ROOT/'source/track_tension.py',ROOT/'source/turning_control.py']})
    output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'peak_kmh':peak*3.6,'state_max_deltas':delta},indent=2));assert max(delta.values())==0
if __name__=='__main__':main()
