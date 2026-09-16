"""Real three-section MuJoCo candidate, using the shared suspension dynamics."""
from pathlib import Path
import argparse,copy,hashlib,json,math,time
import xml.etree.ElementTree as E
import numpy as np
import mujoco
from suspension_physics import build as base_build,Env,C,A,ROOT,HULL_MASS,fmt

OUT=ROOT/'candidates/r016_modular/train'
def rename(name):
    return 'tail' if name=='rear' else name.replace('rear_','tail_',1) if name.startswith('rear_') else 'tail_'+name

def build(rigid=False,out=OUT):
    path,manifest=base_build(rigid);root=E.parse(path).getroot();world=root.find('worldbody');front=world.find("body[@name='front']")
    slide=front.find("body[@name='hitch_slide']");rear=slide.find(".//body[@name='rear']");clone=copy.deepcopy(slide)
    for element in clone.iter():
        if 'name' in element.attrib:element.set('name',rename(element.get('name')))
        for attr in ['joint','body']:
            if attr in element.attrib:element.set(attr,rename(element.get(attr)))
    rear.append(clone);tail=clone.find(".//body[@name='tail']")
    payload_path=out/'source/payload_registry.json';payload=json.loads(payload_path.read_text())
    for hull_name,mass in payload.get('hull_mass_properties',{'tail':payload['mass']}).items():
        hull={'rear':rear,'tail':tail}[hull_name];origin=[-42 if hull_name=='rear' else -84,0,10]
        inertial=hull.find('inertial');inertial.set('mass',str(mass['combined_hull_mass_kg']))
        inertial.set('pos',fmt(np.array(mass['center_of_mass_source_m'])-origin));inertial.set('diaginertia',fmt(mass['inertia_diagonal_kg_m2']))
    actuators=root.find('actuator')
    for actuator in list(actuators):
        item=copy.deepcopy(actuator);item.set('joint',rename(item.get('joint')));actuators.append(item)
    manifest=copy.deepcopy(manifest)
    original_contacts=list(manifest['contacts']);manifest['contacts'] += [{**q,'body':rename(q['body']),'bogie':rename(q['bogie'])} for q in original_contacts if q['bogie'].startswith('rear_')]
    manifest['bogies'] += [rename(n) for n in list(manifest['bogies']) if n.startswith('rear_')]
    manifest['wheels'] += [rename(n) for n in list(manifest['wheels']) if n.startswith('rear_')]
    manifest['hulls']=['front','rear','tail'];names=['extension','hitch_yaw','hitch_pitch','hitch_roll'];manifest['hitch_joints']=names+[rename(n) for n in names]
    hull_mass={name:float(hull.find('inertial').get('mass')) for name,hull in [('front',front),('rear',rear),('tail',tail)]};calibration={}
    for hull in manifest['hulls']:
        # Each coupler's 40 t is divided between its neighboring hulls for
        # nominal preload only. Native constraints determine actual reactions.
        shared_connector_mass=sum(A['moving_carrier_mass_kg'])*(1 if hull=='rear' else .5)
        upper=(hull_mass[hull]+shared_connector_mass)/4*9.81
        wheel_spring=(upper+C['bogie_total_frame_mass_kg']*9.81)/6;normal=wheel_spring+C['road_wheel_effective_mass_kg']*9.81
        hk=upper/C['heave_preload_deflection_m'];hd=2*C['heave_damping_ratio']*math.sqrt(hk*upper/9.81)
        wk=wheel_spring/C['wheel_preload_deflection_m'];wd=2*C['wheel_damping_ratio']*math.sqrt(wk*C['road_wheel_effective_mass_kg'])
        ck=normal/C['contact_deflection_at_nominal_load_m'];cd=2*C['contact_damping_ratio']*math.sqrt(ck*C['road_wheel_effective_mass_kg'])
        calibration[hull]=dict(hull_mass_kg=hull_mass[hull],heave_k=hk,heave_d=hd,wheel_k=wk,wheel_d=wd,nominal_contact_load=normal)
        for name in manifest['bogies']:
            if not name.startswith(hull+'_'):continue
            j=root.find(f".//joint[@name='{name}_heave']");j.set('stiffness',str(hk));j.set('damping',str(hd))
        for name in manifest['wheels']:
            if not name.startswith(hull+'_'):continue
            j=root.find(f".//joint[@name='{name}']");j.set('stiffness',str(wk));j.set('damping',str(wd))
        for contact in manifest['contacts']:
            if contact['bogie'].startswith(hull+'_'):contact.update(contact_stiffness=ck,contact_damping=cd,nominal_load_N=normal)
    root.set('model','Leviathan003_three_modules_locked_containers')
    xml_path=out/'physics'/('rigid.xml' if rigid else 'suspended.xml');xml_path.parent.mkdir(parents=True,exist_ok=True);xml_path.write_text(E.tostring(root,encoding='unicode'))
    m=mujoco.MjModel.from_xml_path(str(xml_path));manifest['total_mass_kg']=float(m.body_mass.sum());manifest['preload_calibration']=calibration
    assert m.nbody-1==129 and m.nv==134 and m.nu==8
    assert abs(manifest['total_mass_kg']-14972000)<.01
    manifest['source_files']=['source/train_physics.py',str(payload_path.relative_to(ROOT))]
    manifest['native_origin_rebase_distance_m']=128.
    (out/'physics/parameters.json').write_text(json.dumps(manifest,indent=2)+'\n');return xml_path,manifest

def environment(terrain='flat',rigid=False,out=OUT):
    path,manifest=build(rigid,out);return Env(terrain,rigid,True,path,manifest)

def main():
    p=argparse.ArgumentParser();p.add_argument('--terrain',default='flat');p.add_argument('--speed',type=float,default=0.);p.add_argument('--seconds',type=float,default=30.);p.add_argument('--brake-at',type=float,default=-1.);p.add_argument('--output',type=Path,required=True);p.add_argument('--containers-first',action='store_true');args=p.parse_args()
    out=ROOT/'candidates/r016_modular/train_containers_first' if args.containers_first else OUT
    env=environment(args.terrain,out=out);samples=[];started=time.monotonic();squares=np.zeros(3);n=0;max_y=np.zeros(3);peak_speed=0.;failed=False
    for step in range(round(args.seconds/C['dt_s'])):
        command=0. if env.d.time<10 or args.brake_at>=0 and env.d.time>=args.brake_at else args.speed
        speed=env.substep(command);peak_speed=max(peak_speed,speed)
        if env.d.time>=10:squares+=env.imu_acceleration[:,2]**2;n+=1;max_y=np.maximum(max_y,abs(env.d.xpos[env.hulls,1]))
        if step%20==19:samples.append(env.record(speed))
        if not np.isfinite(env.d.qpos).all() or min(env.d.xmat[h].reshape(3,3)[2,2] for h in env.hulls)<.5:failed=True;break
    report=dict(engine='MuJoCo '+mujoco.__version__,failed=failed,terrain=args.terrain,seconds=float(env.d.time),wall_seconds=time.monotonic()-started,
                dynamic_bodies=env.m.nbody-1,dofs=env.m.nv,total_mass_kg=env.total_mass,peak_speed_kmh=peak_speed*3.6,max_all_step_lateral_path_error_m=max_y.tolist(),
                peak_all_step_vertical_accel_m_s2=env.peak_acceleration.tolist(),rms_all_step_vertical_accel_after_settle_m_s2=np.sqrt(squares/max(n,1)).tolist(),samples=samples,
                source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'source/suspension_physics.py',ROOT/'design/articulation_candidate.json',out/'source/payload_registry.json']},
                scope='Three physical hulls, twelve independent bogies and two finite-actuator couplers. Locked containers aggregate into the cargo hull selected by payload_registry; its mass/inertia follow module order. Provisional bare hull mass; no handling, learned policy, turning or render-performance claim.')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['samples','source_sha256']},indent=2))
    raise SystemExit(1 if failed else 0)

if __name__=='__main__':main()
