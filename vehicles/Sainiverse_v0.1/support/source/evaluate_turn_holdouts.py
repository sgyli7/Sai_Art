"""Unseen speeds/radii for the frozen four-gain controller, without retraining."""
from pathlib import Path
import concurrent.futures,hashlib,json,math,time
import numpy as np
from suspension_physics import Env,C,ROOT

OUT=ROOT/'candidates/r017_turning'
CASES=[(2.2,.003),(3.6,-.007),(-1.5,-.003),(-2.5,.007),(4.,.009),(2.5,-.02),(5.,0.),(-3.,0.)]
def run(case):
    speed,curvature=case;manifest=json.loads((OUT/'physics/parameters.json').read_text());env=Env('flat',False,True,OUT/'physics/suspended.xml',manifest)
    peak_e=0.;sq=0.;n=0;peak_a=0.;peak_h=0.;upright=1.;failed=False;steady=[]
    for i in range(round(150/C['dt_s'])):
        v=env.substep(speed if env.d.time>=10 else 0.,curvature_request=curvature if env.d.time>=10 else 0.)
        if env.d.time>=10:
            error=abs(env.steering.state['cross_track_error_m']);peak_e=max(peak_e,error);sq+=error*error;n+=1
            peak_a=max(peak_a,max(abs(float(env.imu_acceleration[j]@env.d.xmat[h].reshape(3,3)[:,1])) for j,h in enumerate(env.hulls)))
            peak_h=max(peak_h,float(np.max(abs(env.record_qpos[env.hitch_q][1::4]))))
        upright=min(upright,min(env.d.xmat[h].reshape(3,3)[2,2] for h in env.hulls))
        if env.d.time>=130:steady.append(v)
        if not np.isfinite(env.d.qpos).all() or upright<.9:failed=True;break
    # Development gates selected before these unseen runs. Their scope is
    # these prepared-ground trajectories, not general vehicle certification.
    checks=dict(finite_and_upright=not failed and upright>math.cos(math.radians(10)),path_peak_below_1m=peak_e<1.,lateral_peak_below_1m_s2=peak_a<1.,hitch_below_30deg=peak_h<math.radians(30),steady_speed_error_below_0_1=abs(float(np.mean(steady or [0]))-speed)<.1)
    checks={k:bool(v) for k,v in checks.items()}
    return dict(command_speed_m_s=speed,command_curvature_m_inv=curvature,control_leader=env.hull_names[env.control_leader],rms_path_error_m=math.sqrt(sq/max(n,1)),peak_path_error_m=peak_e,peak_body_lateral_accel_m_s2=peak_a,peak_hitch_deg=math.degrees(peak_h),minimum_upright=float(upright),mean_steady_speed_m_s=float(np.mean(steady or [0])),checks=checks,passed=all(checks.values()))
def main():
    target=OUT/'training/holdouts.json';assert not target.exists();started=time.monotonic()
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:results=list(pool.map(run,CASES))
    report=dict(cases=results,passed=all(r['passed'] for r in results),simulated_seconds=1200,wall_seconds=time.monotonic()-started,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),OUT/'physics/suspended.xml',OUT/'physics/parameters.json',ROOT/'source/turning_control.py',ROOT/'source/suspension_physics.py']},scope='Eight unseen speed/radius combinations, 150 seconds each in MuJoCo; frozen feedback gains, no further fitting. Not a 100-seed robustness result or native Godot/terrain/robot/FPS acceptance.')
    target.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
