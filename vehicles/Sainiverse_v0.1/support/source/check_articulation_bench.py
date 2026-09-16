"""Compare independently integrated fixture traces; no driving acceptance."""
from pathlib import Path
import hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/articulation_r015/bench'
a=json.loads((OUT/'mujoco.json').read_text())
b=json.loads((OUT/'godot.json').read_text())
at=np.array([s['time'] for s in a['samples']]);bt=np.array([s['time'] for s in b['samples']])
av=np.array([s['position'] for s in a['samples']]);bv=np.array([s['position'] for s in b['samples']])
units=np.array([1,180/np.pi,180/np.pi,180/np.pi])
err=np.column_stack([np.interp(bt,at,av[:,i])-bv[:,i] for i in range(4)])*units
rmse=np.sqrt(np.mean(err**2,axis=0))
ends=[]
for end in [15,75,135,175,195,215,235,255,275,300]:
    s=min(b['samples'],key=lambda s:abs(s['time']-(end-.5)))
    ends.append(dict(end_s=end,actual=(np.array(s['position'])*units).tolist(),
                     target=(np.array(s['target'])*units).tolist()))
q=bv*units
caps=np.array([5e6,5e7,5e7,3e7])
checks=dict(native_jolt=b['physics_engine']=='Jolt Physics',
            full_fixture_duration=a['simulation_s']>=299.99 and b['simulation_s']>=299.99,
            finite=bool(np.isfinite(q).all() and np.isfinite(av).all()),
            sampled_actuator_caps=bool(np.all(np.abs([s['force'] for s in b['samples']])<=caps*1.000001)),
            left_45_reached=ends[1]['actual'][1]>=44.5,
            right_45_reached=ends[2]['actual'][1]<=-44.5,
            sampled_range=bool(np.all(q.min(0)>=[-.01,-45.25,-8.25,-6.25]) and np.all(q.max(0)<=[4.01,45.25,8.25,6.25])),
            fixture_trace_agreement=bool(np.all(rmse<=[.01,.25,.25,.25])))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(passed=all(checks.values()),overall_vehicle_goal_complete=False,checks=checks,
            coordinates=['extension_m','yaw_deg','pitch_deg','roll_deg'],
            rmse=rmse.tolist(),peak_sampled_difference=np.abs(err).max(0).tolist(),
            endpoint_samples=ends,max_sampled_anchor_error_m=max(max(s['anchor_errors_m']) for s in b['samples']),
            native_solver=dict(godot_velocity_steps=64,godot_position_steps=8,mujoco_iterations=50,timestep_s=.005),
            sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'source/articulation_bench.py',ROOT/'godot/articulation_bench.gd',ROOT/'design/articulation_candidate.json',ROOT/'assets/physics.json',OUT/'fixture.xml',OUT/'mujoco.json',OUT/'godot.json']},
            scope='Offset-axis zero-gravity fixture only. Output sampled every 0.5 s, not all-step limit proof. '
                  'Yaw/pitch/roll bearing anchors follow articulation_candidate.json. No visual collision, '
                  'rough ground, full vehicle, safety interlock, strength or FPS validation. '
                  '64/8 Jolt solver settings were applied only to generated runtime for this bench, restored to 12/4 afterward. '
                  '12-step result oscillated and is retained as a failed candidate, not accepted.')
(OUT/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(4,1,figsize=(11,8),sharex=True,constrained_layout=True)
for i,ax in enumerate(axes):
    ax.plot(at,av[:,i]*units[i],label='MuJoCo',color='#315c80',linewidth=1.8)
    ax.plot(bt,bv[:,i]*units[i],label='Godot / Jolt',color='#cf752d',linewidth=1.1,linestyle='--')
    ax.set_ylabel(report['coordinates'][i]);ax.grid(alpha=.25)
axes[0].legend();axes[-1].set_xlabel('Simulation time (s)')
fig.suptitle('r015 articulation fixture — zero gravity, finite actuators; not a driving test')
fig.savefig(OUT/'comparison.png',dpi=140)
print(json.dumps({k:v for k,v in report.items() if k not in ['sha256','endpoint_samples']},indent=2))
raise SystemExit(0 if report['passed'] else 1)
