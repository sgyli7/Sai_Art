"""Three-module steering dynamics using actual bogie/coupler actuators."""
from pathlib import Path
import argparse,hashlib,json,math,time
import xml.etree.ElementTree as E
import mujoco,numpy as np
from train_physics import build as train_build
from suspension_physics import Env,ROOT,C,U,fmt

OUT=ROOT/'candidates/r017_turning'
T=json.loads((ROOT/'design/turning_candidate.json').read_text())
def build():
    source=ROOT/'candidates/r016_modular/train_containers_first/source/payload_registry.json'
    (OUT/'source').mkdir(exist_ok=True);(OUT/'source/payload_registry.json').write_bytes(source.read_bytes())
    path,manifest=train_build(out=OUT);root=E.parse(path).getroot();actuators=root.find('actuator')
    names=[];positions=[]
    for name in manifest['bogies']:
        joint_name=name+'_yaw';j=root.find(f".//joint[@name='{joint_name}']");j.set('stiffness','0');j.set('damping','0')
        E.SubElement(actuators,'motor',joint=joint_name,ctrllimited='true',ctrlrange=fmt([-T['bogie_yaw_torque_limit_Nm'],T['bogie_yaw_torque_limit_Nm']]))
        names.append(joint_name);positions.append([max(U['bogie_offsets_x']) if '_fore_' in name else min(U['bogie_offsets_x']),max(U['bogie_offsets_y']) if '_left' in name else min(U['bogie_offsets_y'])])
    manifest['steering_joints']=names;manifest['steering_positions_local_xy_m']=positions;manifest['turning_control']=T
    path.write_text(E.tostring(root,encoding='unicode'));m=mujoco.MjModel.from_xml_path(str(path));assert m.nu==20 and m.nv==134 and m.nbody==130
    (OUT/'physics/parameters.json').write_text(json.dumps(manifest,indent=2)+'\n');return path,manifest
def environment(terrain='flat'):
    path,manifest=build();return Env(terrain,False,True,path,manifest)
def main():
    p=argparse.ArgumentParser();p.add_argument('--speed',type=float,default=3.);p.add_argument('--curvature',type=float,default=.005);p.add_argument('--seconds',type=float,default=150.);p.add_argument('--brake-at',type=float,default=-1.);p.add_argument('--output',required=True,type=Path);args=p.parse_args()
    assert not args.output.exists(),'Use a fresh report path.'
    env=environment();samples=[];peak_cross=0.;peak_lateral=0.;peak_hitch=0.;peak_speed=0.;failed=False;started=time.monotonic()
    for step in range(round(args.seconds/C['dt_s'])):
        command=args.speed if env.d.time>=10 else 0.;curvature=args.curvature if env.d.time>=10 else 0.
        if args.brake_at>=0 and env.d.time>=args.brake_at:command=0.
        speed=env.substep(command,curvature_request=curvature)
        peak_speed=max(peak_speed,abs(speed))
        if env.d.time>=10:
            peak_cross=max(peak_cross,abs(env.steering.state['cross_track_error_m']))
            for i,h in enumerate(env.hulls):peak_lateral=max(peak_lateral,abs(float(env.imu_acceleration[i]@env.d.xmat[h].reshape(3,3)[:,1])))
            peak_hitch=max(peak_hitch,float(np.max(abs(env.record_qpos[env.hitch_q][1::4]))))
        if step%20==19:samples.append(env.record(speed))
        if not np.isfinite(env.d.qpos).all() or min(env.d.xmat[h].reshape(3,3)[2,2] for h in env.hulls)<.5:failed=True;break
    mujoco.mj_forward(env.m,env.d);neutral=mujoco.MjData(env.m);neutral.qpos[2]=10.;mujoco.mj_forward(env.m,neutral)
    names=env.hull_names+env.manifest['bogies']+['hitch_slide','hitch_yaw','hitch_pitch','tail_hitch_slide','tail_hitch_yaw','tail_hitch_pitch']
    final_poses={n:dict(position_source_m=env.d.xpos[env.m.body(n).id].tolist(),rotation_row_major=env.d.xmat[env.m.body(n).id].tolist(),neutral_body_position_source_m=neutral.xpos[env.m.body(n).id].tolist()) for n in names}
    report=dict(engine='MuJoCo '+mujoco.__version__,failed=failed,seconds=float(env.d.time),wall_seconds=time.monotonic()-started,command_speed_m_s=args.speed,command_curvature_m_inv=args.curvature,brake_at_s=args.brake_at,peak_speed_kmh=peak_speed*3.6,final_motion_groups=final_poses,
        control_leader='tail' if args.speed<0 else 'front',maximum_all_step_control_path_error_m=peak_cross,maximum_all_step_body_lateral_accel_m_s2=peak_lateral,maximum_all_step_hitch_yaw_deg=math.degrees(peak_hitch),samples=samples,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'source/suspension_physics.py',ROOT/'source/turning_control.py',ROOT/'design/turning_candidate.json',OUT/'physics/suspended.xml']},
        scope='Independent finite bogie/coupler steering on reduced hard-ground contacts. Constant curvature path, provisional actuator ratings. Four feedback gains may be calibrated by the recorded CEM run. No neural robot/crane policy, arbitrary-terrain, handling, render or safety qualification.')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['samples','source_sha256','final_motion_groups']},indent=2))
    raise SystemExit(1 if failed else 0)
if __name__=='__main__':main()
