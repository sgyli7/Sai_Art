"""Capture actual trained MuJoCo body frames for an authored model review."""
from pathlib import Path
import hashlib,json,math
import mujoco,numpy as np
from suspension_physics import Env,C,ROOT
OUT=ROOT/'candidates/r017_turning'
def main():
    path=OUT/'physics/suspended.xml';manifest_path=OUT/'physics/parameters.json';manifest=json.loads(manifest_path.read_text());env=Env('flat',False,True,path,manifest)
    maximum_error=0.
    for i in range(round(150/C['dt_s'])):
        active=env.d.time>=10;env.substep(3. if active else 0.,curvature_request=.02 if active else 0.)
        if active:maximum_error=max(maximum_error,abs(env.steering.state['cross_track_error_m']))
    mujoco.mj_forward(env.m,env.d);neutral=mujoco.MjData(env.m);neutral.qpos[2]=10.;mujoco.mj_forward(env.m,neutral)
    names=env.hull_names+env.manifest['bogies']+['hitch_slide','hitch_yaw','hitch_pitch','tail_hitch_slide','tail_hitch_yaw','tail_hitch_pitch']
    poses={n:dict(position_source_m=env.d.xpos[env.m.body(n).id].tolist(),rotation_row_major=env.d.xmat[env.m.body(n).id].tolist(),neutral_body_position_source_m=neutral.xpos[env.m.body(n).id].tolist()) for n in names}
    assert maximum_error<1 and len(poses)==21
    report=dict(seconds=float(env.d.time),final_motion_groups=poses,maximum_path_error_m=maximum_error,hitch_yaw_deg=np.degrees(env.d.qpos[env.hitch_q][1::4]).tolist(),
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),path,manifest_path,ROOT/'source/suspension_physics.py',ROOT/'source/turning_control.py']},
        scope='Actual 150 s trained-controller simulation. Frames for 21 existing exterior groups; road-wheel visual travel and belt deformation remain unbound and must not be claimed from this review.')
    (OUT/'reports/tight_pose_mujoco.json').write_text(json.dumps(report,indent=2)+'\n');print('pose',report['hitch_yaw_deg'],'error',maximum_error)
if __name__=='__main__':main()
