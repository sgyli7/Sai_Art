"""Contact-only revision cases using the previously trained controller."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,subprocess,sys,time
import numpy as np
from suspension_physics import ROOT,Env,C
OUT=ROOT/'candidates/r019_running_gear'
CASES={'straight100':('flat',27.77777777777778,0.,115.,75.),'rough':('rough',5.,0.,65.,-1.),'tight':('flat',3.,.02,150.,-1.),'reverse':('flat',-2.,.005,150.,-1.)}
def evaluate(name):
    terrain,speed_request,curve,seconds,brake=CASES[name]
    path=OUT/'physics/suspended.xml';manifest=json.loads((OUT/'physics/parameters.json').read_text());env=Env(terrain,False,True,path,manifest)
    output=OUT/'reports'/(name+'_mujoco.json');assert not output.exists()
    samples=[];peak=0.;cross=0.;failed=False;start=time.monotonic()
    for step in range(round(seconds/C['dt_s'])):
        command=speed_request if env.d.time>=10 and (brake<0 or env.d.time<brake) else 0.
        speed=env.substep(command,curvature_request=curve if env.d.time>=10 else 0.);peak=max(peak,abs(speed))
        cross=max(cross,abs(env.steering.state['cross_track_error_m']))
        if step%20==19:samples.append(env.record(speed))
        if not np.isfinite(env.d.qpos).all() or min(env.d.xmat[h].reshape(3,3)[2,2] for h in env.hulls)<.5:failed=True;break
    result=dict(engine='MuJoCo',failed=failed,seconds=float(env.d.time),wall_seconds=time.monotonic()-start,samples=samples,peak_speed_kmh=peak*3.6,maximum_all_step_control_path_error_m=cross,
        peak_all_step_vertical_accel_m_s2=env.peak_acceleration.tolist(),scope='Measured cleat contact radius, original trained gains; no tensioner dynamics yet.',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),path,OUT/'physics/parameters.json',ROOT/'source/suspension_physics.py']})
    output.write_text(json.dumps(result,indent=2)+'\n');return name,peak*3.6,cross,failed
def native():
    for name,(terrain,speed,curve,seconds,brake) in CASES.items():
        subprocess.run([sys.executable,str(ROOT/'source/run_suspension_native.py'),'--label',name+'_godot','--spec',str(OUT/'physics/native_spec.json'),'--output-root',str(OUT/'reports'),'--terrain',terrain,'--speed',str(speed),'--curvature',str(curve),'--seconds',str(seconds),'--brake-at',str(brake)],check=True)
def compare():
    rows={}
    for name in CASES:
        mj=json.loads((OUT/'reports'/(name+'_mujoco.json')).read_text());gd=json.loads((OUT/'reports'/(name+'_godot.json')).read_text());meta=json.loads((OUT/'reports'/(name+'_godot_source.json')).read_text())
        assert meta['runtime_restored'] and not meta['source_changed_during_run']
        assert not mj['failed'] and not gd['failed'] and len(mj['samples'])==len(gd['samples'])
        row={}
        for field in ['speed_m_s','hull_positions','wheel_travel_m','heave_m','hitch_coordinates']:
            a=np.array([s[field] for s in mj['samples']]);b=np.array([s[field] for s in gd['samples']]);row[field+'_rmse']=float(np.sqrt(np.mean((a-b)**2)))
        row.update(peak_speed_mj_kmh=mj['peak_speed_kmh'],peak_forward_speed_gd_kmh=gd['peak_speed_kmh'],peak_absolute_sampled_speed_gd_kmh=max(abs(s['speed_m_s']) for s in gd['samples'])*3.6,native_max_anchor_m=gd['maximum_all_step_joint_anchor_residual_m'],path_peak_mj_m=mj['maximum_all_step_control_path_error_m'],path_peak_gd_m=gd['maximum_all_step_control_path_error_m'])
        row['passed']=bool(row['speed_m_s_rmse']<.1 and row['hull_positions_rmse']<.1 and row['wheel_travel_m_rmse']<.04 and row['heave_m_rmse']<.02 and row['hitch_coordinates_rmse']<.01 and row['native_max_anchor_m']<.01 and row['path_peak_mj_m']<1 and row['path_peak_gd_m']<1)
        if name=='straight100':row['passed']=row['passed'] and min(row['peak_speed_mj_kmh'],row['peak_absolute_sampled_speed_gd_kmh'])>99.5
        rows[name]=row
    (OUT/'reports/contact_transfer.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2));assert all(r['passed'] for r in rows.values())
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['mujoco','godot','compare']);args=p.parse_args()
    if args.mode=='mujoco':
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
            for result in pool.map(evaluate,CASES):print(result,flush=True)
    elif args.mode=='godot':native()
    else:compare()
