"""Seeded CEM calibration of finite feedback gains in real MuJoCo rollouts.

This learns four controller parameters, not a neural locomotion policy. Body
mass, torque/power caps, mechanical stops and rate limits are never optimized.
"""
from pathlib import Path
import concurrent.futures,copy,hashlib,json,math,time
import numpy as np
from turning_physics import build,OUT,T
from suspension_physics import Env,C,ROOT

KEYS=['path_heading_gain_per_s','path_cross_track_gain_per_s','hitch_yaw_kp_Nm_rad','hitch_yaw_kd_Nms_rad']
BOUNDS=np.array([[.25,1.5],[.06,.4],[8e7,5e8],[4e8,1.6e9]])
CASES=[(3.,.02),(-2.,.005),(3.,.005)]
def evaluate(job):
    ident,params,path,manifest=job;manifest=copy.deepcopy(manifest);manifest['turning_control'].update(dict(zip(KEYS,params)))
    results=[]
    for speed,curvature in CASES:
        env=Env('flat',False,True,path,manifest);sq=0.;peak=0.;lateral=0.;hitch=0.;n=0;last_speeds=[];failed=False
        for i in range(round(100/C['dt_s'])):
            v=env.substep(speed if env.d.time>=10 else 0.,curvature_request=curvature if env.d.time>=10 else 0.)
            if env.d.time>=10:
                e=abs(env.steering.state['cross_track_error_m']);sq+=e*e;peak=max(peak,e);n+=1
                lateral=max(lateral,max(abs(float(env.imu_acceleration[j]@env.d.xmat[h].reshape(3,3)[:,1])) for j,h in enumerate(env.hulls)))
                hitch=max(hitch,float(np.max(abs(env.record_qpos[env.hitch_q][1::4]))))
            if env.d.time>=80:last_speeds.append(v)
            if not np.isfinite(env.d.qpos).all() or min(env.d.xmat[h].reshape(3,3)[2,2] for h in env.hulls)<.9:failed=True;break
        rms=math.sqrt(sq/max(n,1));speed_error=abs(float(np.mean(last_speeds or [0]))-speed)
        cost=rms+.3*peak+10*speed_error+100*max(lateral-.8,0)+100*max(math.degrees(hitch)-29.8,0)+(10000 if failed else 0)
        results.append(dict(speed=speed,curvature=curvature,rms_error_m=rms,peak_error_m=peak,peak_lateral_m_s2=lateral,peak_hitch_deg=math.degrees(hitch),steady_speed_error=speed_error,failed=failed,cost=cost))
    return dict(id=ident,parameters=dict(zip(KEYS,params)),cost=sum(c['cost'] for c in results),cases=results)
def main():
    target=OUT/'training';target.mkdir(exist_ok=True);assert not (target/'cem_trials.json').exists()
    path,manifest=build();rng=np.random.default_rng(17003);low,high=np.log(BOUNDS[:,0]),np.log(BOUNDS[:,1]);mu=np.log([T[k] for k in KEYS]);sigma=(high-low)/3
    trials=[];started=time.monotonic();best=None
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
        for generation in range(3):
            samples=np.clip(rng.normal(mu,sigma,(8,4)),low,high);samples[0]=mu
            jobs=[(f'g{generation}_{i}',np.exp(x).tolist(),str(path),manifest) for i,x in enumerate(samples)]
            results=list(pool.map(evaluate,jobs));trials.extend(results);ranked=sorted(results,key=lambda r:r['cost']);elite=ranked[:3]
            params=np.log([[e['parameters'][k] for k in KEYS] for e in elite]);mu=params.mean(0);sigma=np.maximum(params.std(0),.08*(high-low))
            if best is None or ranked[0]['cost']<best['cost']:best=ranked[0]
            (target/'cem_progress.json').write_text(json.dumps(dict(generation=generation,trials=trials,best=best),indent=2)+'\n')
            print('generation',generation,'best cost',best['cost'],'parameters',best['parameters'],flush=True)
    result=dict(method='Cross-entropy parameter calibration on real MuJoCo dynamics',seed=17003,generations=3,candidates_per_generation=8,rollouts_per_candidate=3,total_simulated_seconds=7200,wall_seconds=time.monotonic()-started,
        selected=best,all_trials=trials,parameter_bounds={k:b.tolist() for k,b in zip(KEYS,BOUNDS)},source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'source/turning_control.py',ROOT/'source/suspension_physics.py',ROOT/'design/turning_candidate.json',path]},
        scope='Four learned feedback gains; unchanged finite torque/power, mass, rate and mechanical limits. Training cases are not holdouts; selected gains still require new speeds/radii and independent native Godot validation. No goal-completion or learned robot/crane claim.')
    (target/'cem_trials.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['all_trials','source_sha256']},indent=2))
if __name__=='__main__':main()
