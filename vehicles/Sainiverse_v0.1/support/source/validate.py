"""Acceptance against actual native traces; no implementation-mirroring tests."""
from pathlib import Path
import json,statistics,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports'
training=json.loads((R/'training_validation.json').read_text())
checks={};comparisons={}
for mode in ['straight','turn']:
    mj=json.loads((R/f'mujoco_{mode}_200.json').read_text());gd=json.loads((R/f'godot_{mode}_r011'/'result.json').read_text())
    native_source=json.loads((R/f'godot_{mode}_r011'/'source.json').read_text())
    checks[mode+'_current_physics_policy_runtime']=all(native_source['sha256'][name]==hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['assets/physics.json','training/policy.json','godot/runtime.gd'])
    mt=np.array([s['t'] for s in mj['samples']]);gt=np.array([s['time'] for s in gd['samples']]);valid=(gt>=1)&(gt<=99)
    error={}
    for mk,gk in [('speed','speed_m_s'),('yaw','yaw')]:
        a=np.interp(gt[valid],mt,[s[mk] for s in mj['samples']]);b=np.array([s[gk] for s in gd['samples']])[valid]
        error[mk+'_rmse']=float(np.sqrt(np.mean((a-b)**2)))
    comparisons[mode]=error
    checks[mode+'_mujoco_jolt_speed_match']=error['speed_rmse']<.06
    checks[mode+'_mujoco_jolt_yaw_match']=error['yaw_rmse']<.001
    checks[mode+'_native_upright']=gd['state']['min_upright']>.99
    if mode=='straight':checks['native_100_kmh']=gd['state']['max_speed_kmh']>=99.9
    else:
        checks['native_stop']=abs(gd['state']['speed_m_s'])<.01
        checks['native_turn_occurred']=max(abs(s['yaw']) for s in gd['samples'])>.005
checks['holdout_10_episodes']=training['passed'] and len(training['holdout'])==10
p=json.loads((R/'godot_polar_r014/result.json').read_text());s=[v for v in p['samples'] if v['time']>=10]
steady_ratio=(s[-1]['time']-s[0]['time'])/(s[-1]['wall_seconds']-s[0]['wall_seconds'])
fps=statistics.median(v['fps'] for v in s)
snapshot=json.loads((R/'godot_polar_r014/source.json').read_text())
checks['rendered_current_mesh']=snapshot['sha256']['assets/leviathan003.glb']==hashlib.sha256((ROOT/'assets/leviathan003.glb').read_bytes()).hexdigest()
checks['rendered_current_runtime']=snapshot['sha256']['godot/runtime.gd']==hashlib.sha256((ROOT/'godot/runtime.gd').read_bytes()).hexdigest()
checks['rendered_current_scene']=all(snapshot['sha256'][name]==hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('godot/drive_scene.gd','godot/belt.gdshader','godot/terrain.gd','assets/physics.json','training/policy.json'))
checks['rendered_180s_1080p']=not p['headless'] and p['sim_seconds']>=180 and p['resolution']==[1920,1080]
checks['rendered_frame_budget']=fps>=60 and p['p95_frame_ms']<=16.667
checks['rendered_realtime']=steady_ratio>=.98
checks['polar_stability']=p['state']['min_upright']>.99 and p['state']['max_speed_kmh']>=99.9
terrain_validation=json.loads((R/'terrain_validation.json').read_text())
checks['terrain_readback_regression']=terrain_validation['passed'] and terrain_validation['adapter_sha256']==hashlib.sha256((ROOT/'godot/terrain.gd').read_bytes()).hexdigest()
checks['trained_physics_matches']=training['policy']['physics_sha256']==hashlib.sha256((ROOT/'assets/physics.json').read_bytes()).hexdigest()
report={'passed':all(checks.values()),'scope':'Existing reduced transport baseline only; excludes new articulated suspension, +/-45 degree turn and indoor robot requirements.','overall_user_goal_complete':False,'checks':checks,'cross_engine':comparisons,'rendered':{'terrain':'existing game polar grid; identical collision vertices through 003 CPU adapter','seconds':p['sim_seconds'],'resolution':p['resolution'],'median_fps_counter':fps,'median_frame_ms':p['median_frame_ms'],'p95_frame_ms':p['p95_frame_ms'],'steady_sim_wall_ratio':steady_ratio,'including_startup_sim_wall_ratio':p['sim_wall_ratio'],'physics_cpu_ms':p['state']['physics_cpu_ms'],'max_speed_kmh':p['state']['max_speed_kmh'],'hardware':'NVIDIA GB10 / Linux aarch64 / driver580.173.02 / Godot4.7.2 Forward+','capture':'single automatic screenshot in run; separate close-up review not used for FPS','measurement_interval':'Begins after scene and vehicle creation. Including-startup ratio includes vehicle acceleration from rest, not engine launch or asset import.'},'limits':['Geometry is reconstructed, not original CAD or pixel-exact 1:1.','Two rigid hulls and 32 reduced compliant patches; no independently dynamic bogies or track links.','No Sai agent spawned in this performance run; original F7/Sai boarding not integrated.','No hardware or structural qualification.','Steering rate under-tracks the requested rate (~0.00750 measured for 0.018 requested in turn test); cross-engine agreement is not command tracking accuracy.']}
(R/'ACCEPTANCE.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(0 if report['passed'] else 1)
