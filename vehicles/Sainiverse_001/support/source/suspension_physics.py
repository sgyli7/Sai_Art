"""Native independent suspension candidate with 48 sprung road-wheel bodies.

Joint springs transfer load through eight articulated bogies. Ground/belt
contact is a reduced unilateral compliant patch model, not link-level physics.
"""
from pathlib import Path
import argparse,json,math,time,hashlib
import xml.etree.ElementTree as E
import numpy as np
import mujoco

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'design/suspension_candidate.json').read_text())
A=json.loads((ROOT/'design/articulation_candidate.json').read_text())
V=json.loads((ROOT/'design/vehicle.json').read_text());U=V['undercarriage']
OLD=json.loads((ROOT/'assets/physics.json').read_text())
OUT=ROOT/'candidates/r015_articulation/physics'
WHEEL_MASS=C['road_wheel_effective_mass_kg']
HULL_MASS=(C['total_mass_kg']-8*(C['bogie_total_frame_mass_kg']+6*WHEEL_MASS)-sum(A['moving_carrier_mass_kg']))/2
UPPER_LOAD=(HULL_MASS+sum(A['moving_carrier_mass_kg'])/2)/4*9.81
WHEEL_SPRING_LOAD=(UPPER_LOAD+C['bogie_total_frame_mass_kg']*9.81)/6
NOMINAL_LOAD=WHEEL_SPRING_LOAD+WHEEL_MASS*9.81
HEAVE_K=UPPER_LOAD/C['heave_preload_deflection_m']
HEAVE_D=2*C['heave_damping_ratio']*math.sqrt(HEAVE_K*UPPER_LOAD/9.81)
WHEEL_K=WHEEL_SPRING_LOAD/C['wheel_preload_deflection_m']
WHEEL_D=2*C['wheel_damping_ratio']*math.sqrt(WHEEL_K*WHEEL_MASS)
CONTACT_K=NOMINAL_LOAD/C['contact_deflection_at_nominal_load_m']
CONTACT_D=2*C['contact_damping_ratio']*math.sqrt(CONTACT_K*WHEEL_MASS)
fmt=lambda values:' '.join(str(float(x)) for x in values)

def ground_height(x,y,terrain):
    x,y=np.asarray(x),np.asarray(y)
    def bump(center,width,height):
        q=np.clip((x-center)/width,-1,1)
        return height*.5*(1+np.cos(np.pi*q))
    if terrain=='flat':return np.zeros_like(x,dtype=float)
    if terrain=='alternating':
        left=.5*(1+np.tanh(y/2))
        return left*(bump(30,2,.35)+bump(70,2,.3))+(1-left)*(bump(45,2,.35)+bump(85,2,.3))
    if terrain=='ditch':return bump(60,3,-.4)
    if terrain=='ramp':return np.clip(x-20,0,30)*math.tan(math.radians(8))
    if terrain=='rough':
        window=np.clip((x-10)/5,0,1)*np.clip((145-x)/5,0,1)
        return window*(.15*np.sin(2*np.pi*x/9)+.10*np.sin(2*np.pi*x/4+np.tanh(y/2)*np.pi/2))
    raise ValueError(terrain)

def ground(x,y,terrain):
    h=ground_height(x,y,terrain);eps=.01
    dx=(ground_height(x+eps,y,terrain)-ground_height(x-eps,y,terrain))/(2*eps)
    dy=(ground_height(x,y+eps,terrain)-ground_height(x,y-eps,terrain))/(2*eps)
    normal=np.column_stack((-dx,-dy,np.ones_like(dx)));normal/=np.linalg.norm(normal,axis=1)[:,None]
    return h,normal

def build(rigid=False):
    root=E.Element('mujoco',model='Leviathan003_independent_suspension_candidate')
    E.SubElement(root,'compiler',angle='radian',autolimits='true')
    E.SubElement(root,'option',gravity='0 0 -9.81',timestep=str(C['dt_s']),integrator='implicitfast',iterations='60',tolerance='1e-9')
    world=E.SubElement(root,'worldbody');contacts=[];bogies=[];wheels=[]
    def inertial(b,mass,diagonal,pos=(0,0,0)):
        E.SubElement(b,'inertial',pos=fmt(pos),mass=str(mass),diaginertia=fmt(diagonal))
    def joint(b,name,kind,axis,limits,stiffness=0,damping=0,ref=0,locked=False,pos=(0,0,0)):
        return E.SubElement(b,'joint',name=name,type=kind,axis=fmt(axis),pos=fmt(pos),limited='true',
                            range=fmt([-.00000001,.00000001] if locked else limits),stiffness=str(stiffness),damping=str(damping),springref=str(ref),
                            solreflimit='.01 1',solimplimit='.99 .999 .001')
    front=E.SubElement(world,'body',name='front',pos=fmt([0,0,10-.21]));E.SubElement(front,'freejoint',name='root')
    inertial(front,HULL_MASS,np.array(OLD['inertia_diagonal'])*HULL_MASS/5e6)
    yaw=np.array(A['reference_anchor_m']);pitch=yaw+np.array(A['pitch_axis_offset_m']);roll=pitch+np.array(A['roll_axis_offset_from_pitch_m'])
    slide=E.SubElement(front,'body',name='hitch_slide',pos=fmt(yaw-[0,0,10]));inertial(slide,A['moving_carrier_mass_kg'][0],[A['carrier_inertia_kg_m2'][0]]*3)
    joint(slide,'extension','slide',[-1,0,0],A['extension_m'])
    rotor=E.SubElement(slide,'body',name='hitch_yaw');inertial(rotor,A['moving_carrier_mass_kg'][1],[A['carrier_inertia_kg_m2'][1]]*3)
    joint(rotor,'hitch_yaw','hinge',[0,0,1],np.radians(A['yaw_degrees']))
    carrier=E.SubElement(rotor,'body',name='hitch_pitch',pos=fmt(pitch-yaw));inertial(carrier,A['moving_carrier_mass_kg'][2],[A['carrier_inertia_kg_m2'][2]]*3)
    joint(carrier,'hitch_pitch','hinge',[0,1,0],np.radians(A['pitch_degrees']))
    rear_center=np.array([-42,0,10]);rear=E.SubElement(carrier,'body',name='rear',pos=fmt(rear_center-pitch))
    joint(rear,'hitch_roll','hinge',[1,0,0],np.radians(A['roll_degrees']),pos=roll-rear_center)
    inertial(rear,HULL_MASS,np.array(OLD['inertia_diagonal'])*HULL_MASS/5e6)
    for hull,parent in [('front',front),('rear',rear)]:
        E.SubElement(parent,'geom',type='box',size='17 13.5 .3',pos='0 0 -2.8',contype='0',conaffinity='0',mass='0')
        for x in U['bogie_offsets_x']:
            for y in U['bogie_offsets_y']:
                stem=f'{hull}_bogie_{"fore" if x>0 else "aft"}_{"left" if y>0 else "right"}'
                p=parent
                for i,(axis,kind,tag) in enumerate([([0,0,1],'slide','heave'),([0,0,1],'hinge','yaw'),([0,1,0],'hinge','pitch'),([1,0,0],'hinge','roll')]):
                    name=stem if i==3 else stem+'_'+tag
                    b=E.SubElement(p,'body',name=name,pos=fmt([x,y,C['bogie_pivot_z_m']-10]) if i==0 else '0 0 0')
                    mass=C['bogie_carrier_mass_kg'][i]
                    inertia=np.array([5.5**2+3**2,11**2+3**2,11**2+5.5**2])*mass/12 if i==3 else np.array([20000.]*3)
                    inertial(b,mass,inertia,(0,0,3-C['bogie_pivot_z_m']) if i==3 else (0,0,0))
                    limit=C['heave_range_m'] if i==0 else np.radians([-C['bogie_'+tag+'_limit_deg'],C['bogie_'+tag+'_limit_deg']])
                    k=HEAVE_K if i==0 else 3e7 if i==1 else 8e6
                    damping=HEAVE_D if i==0 else 1.2e7 if i==1 else 3e6
                    joint(b,stem+'_'+tag,kind,axis,limit,k,damping,-C['heave_preload_deflection_m'] if i==0 else 0,rigid)
                    p=b
                bogies.append(stem)
                E.SubElement(p,'geom',type='box',size='4 .7 .3',pos='0 0 -1.3',contype='0',conaffinity='0',mass='0')
                for belt_y in U['belt_offsets_y']:
                    for wi,(wx,wz,wr) in enumerate(U['wheels_x_z_radius']):
                        local=[wx,belt_y,wz-C['bogie_pivot_z_m']]
                        if wi in (1,2,3):
                            name=stem+f'_wheel_{"left" if belt_y>0 else "right"}_{wi}'
                            wheel=E.SubElement(p,'body',name=name,pos=fmt(local));inertial(wheel,WHEEL_MASS,[WHEEL_MASS*(3*wr**2+1.6**2)/12,WHEEL_MASS*wr**2/2,WHEEL_MASS*(3*wr**2+1.6**2)/12])
                            joint(wheel,name,'slide',[0,0,1],C['wheel_travel_m'],WHEEL_K,WHEEL_D,-C['wheel_preload_deflection_m'],rigid)
                            E.SubElement(wheel,'geom',type='sphere',size=str(wr),contype='0',conaffinity='0',mass='0');wheels.append(name)
                            contacts.append(dict(body=name,local=[0,0,0],radius=wr+C['track_contact_skin_m'],bogie=stem,road_wheel=True))
                        else:contacts.append(dict(body=stem,local=local,radius=wr+C['track_contact_skin_m'],bogie=stem,road_wheel=False))
    actuator=E.SubElement(root,'actuator')
    for name,f in zip(['extension','hitch_yaw','hitch_pitch','hitch_roll'],[A['extension_force_limit_N'],*A['rotation_torque_limits_Nm']]):
        E.SubElement(actuator,'motor',joint=name,ctrllimited='true',ctrlrange=fmt([-f,f]))
    OUT.mkdir(parents=True,exist_ok=True);file=OUT/('rigid.xml' if rigid else 'suspended.xml');file.write_text(E.tostring(root,encoding='unicode'))
    manifest=dict(hull_mass_kg=HULL_MASS,contacts=contacts,bogies=bogies,wheels=wheels,heave_stiffness=HEAVE_K,heave_damping=HEAVE_D,
                  wheel_stiffness=WHEEL_K,wheel_damping=WHEEL_D,contact_stiffness=CONTACT_K,contact_damping=CONTACT_D,nominal_contact_load=NOMINAL_LOAD)
    (OUT/'parameters.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return file,manifest

class Env:
    def __init__(self,terrain='flat',rigid=False,path_control=True,model_path=None,manifest=None):
        file,self.manifest=build(rigid) if model_path is None else (model_path,manifest)
        self.m=mujoco.MjModel.from_xml_path(str(file));self.d=mujoco.MjData(self.m);self.terrain=terrain
        self.contact_ids=np.array([self.m.body(q['body']).id for q in self.manifest['contacts']]);self.local=np.array([q['local'] for q in self.manifest['contacts']]);self.radius=np.array([q['radius'] for q in self.manifest['contacts']])
        self.hull_names=self.manifest.get('hulls',['front','rear']);self.hulls=[self.m.body(n).id for n in self.hull_names];nh=len(self.hulls)
        self.total_mass=float(self.m.body_mass.sum());self.contact_k=np.array([q.get('contact_stiffness',CONTACT_K) for q in self.manifest['contacts']]);self.contact_d=np.array([q.get('contact_damping',CONTACT_D) for q in self.manifest['contacts']]);self.nominal_load=np.array([q.get('nominal_load_N',NOMINAL_LOAD) for q in self.manifest['contacts']])
        self.velocity=np.zeros((self.m.nbody,6));self.filtered_speed=0.;self.normal=np.zeros(len(self.contact_ids));self.last_imu=None;self.imu_acceleration=np.zeros((nh,3));self.peak_acceleration=np.zeros(nh)
        self.hitch_names=self.manifest.get('hitch_joints',['extension','hitch_yaw','hitch_pitch','hitch_roll'])
        self.hitch_q=np.array([self.m.joint(n).qposadr[0] for n in self.hitch_names]);self.hitch_v=np.array([self.m.joint(n).dofadr[0] for n in self.hitch_names])
        self.heave_q=[self.m.joint(n+'_heave').qposadr[0] for n in self.manifest['bogies']];self.wheel_q=[self.m.joint(n).qposadr[0] for n in self.manifest['wheels']]
        self.path_control=path_control;self.requested_yaw_rate=0.;self.applied_drive_power=0.;self.requested_yaw_moment=0.
        self.hydraulics=None
        if 'hydraulics' in self.manifest:
            from hydraulic_suspension import HydraulicSuspension
            self.hydraulics=HydraulicSuspension(self.manifest['hydraulics'])
            self.hydraulic_q=np.array([self.m.joint(n).qposadr[0] for n in self.hydraulics.names]);self.hydraulic_v=np.array([self.m.joint(n).dofadr[0] for n in self.hydraulics.names])
        self.steering=None
        self.track_tension=None
        if 'track_tension' in self.manifest:
            from track_tension import TrackTension
            self.track_tension=TrackTension(self.manifest['track_tension'])
            self.track_q=np.array([self.m.joint(n).qposadr[0] for n in self.track_tension.names]);self.track_v=np.array([self.m.joint(n).dofadr[0] for n in self.track_tension.names])
        if 'turning_control' in self.manifest:
            from turning_control import Steering
            self.steering=Steering(self.manifest['turning_control'],self.manifest['steering_positions_local_xy_m'])
            self.steer_q=np.array([self.m.joint(n).qposadr[0] for n in self.manifest['steering_joints']]);self.steer_v=np.array([self.m.joint(n).dofadr[0] for n in self.manifest['steering_joints']])
        self.access=None
        if 'access' in self.manifest:
            from cabin_access import CabinAccess
            self.access=CabinAccess(self.manifest['access'])
            self.access_q=np.array([self.m.joint(n).qposadr[0] for n in self.access.names]);self.access_v=np.array([self.m.joint(n).dofadr[0] for n in self.access.names])
            self.access_act=np.array([self.m.actuator('drive_'+n).id for n in self.access.names])
        # Whole aligned train yaw inertia about its midpoint, for feedback
        # scaling only. Steering still acts exclusively through track forces.
        self.steering_inertia=2*float(OLD['inertia_diagonal'][2])+C['total_mass_kg']*21**2
        mujoco.mj_forward(self.m,self.d)
        self.neutral_hull_xy=self.d.xpos[self.hulls,:2].copy();self.control_leader=0
        if nh>2:
            centers=self.d.xipos[1:];masses=self.m.body_mass[1:];center=(centers*masses[:,None]).sum(0)/masses.sum();delta=centers-center
            self.steering_inertia=float(np.sum(self.m.body_inertia[1:,2]+masses*(delta[:,0]**2+delta[:,1]**2)))
        assert abs(self.total_mass-self.manifest.get('total_mass_kg',C['total_mass_kg']))<.01
    def substep(self,speed_request=0.,hitch_targets=None,curvature_request=0.):
        mujoco.mj_step1(self.m,self.d);dt=C['dt_s'];self.d.xfrc_applied[:]=0.
        available_power=C['power_limit_W']
        if self.hydraulics is not None or self.track_tension is not None or self.access is not None:self.d.qfrc_applied[:]=0.
        if self.hydraulics is not None:
            self.d.qfrc_applied[self.hydraulic_v]=self.hydraulics.step(self.d.qpos[self.hydraulic_q],self.d.qvel[self.hydraulic_v],dt)
            available_power=max(0.,available_power-self.hydraulics.pump_power_W)
        if self.track_tension is not None:
            np.add.at(self.d.qfrc_applied,self.track_v,self.track_tension.step(self.d.qpos[self.track_q],self.d.qvel[self.track_v],dt))
        for body in range(1,self.m.nbody):mujoco.mj_objectVelocity(self.m,self.d,mujoco.mjtObj.mjOBJ_BODY,body,self.velocity[body],0)
        ids=self.contact_ids;rot=self.d.xmat[ids].reshape(-1,3,3)
        center=self.d.xpos[ids]+np.einsum('nij,nj->ni',rot,self.local)
        height,normal=ground(center[:,0],center[:,1],self.terrain)
        penetration=self.radius-(center[:,2]-height)*normal[:,2]
        contact=center-normal*self.radius[:,None]
        v=self.velocity[ids,3:]+np.cross(self.velocity[ids,:3],contact-self.d.xipos[ids])
        loads=np.clip(self.contact_k*penetration-self.contact_d*np.sum(v*normal,axis=1),0,self.nominal_load*C['contact_max_nominal_load_factor'])
        loads=np.where(penetration>=0,loads,0.);self.normal=loads
        forward=rot[:,:,0];forward-=normal*np.sum(forward*normal,axis=1)[:,None];forward/=np.maximum(np.linalg.norm(forward,axis=1)[:,None],1e-9)
        lateral=np.cross(normal,forward)
        self.control_leader=len(self.hulls)-1 if self.steering is not None and speed_request<0 else 0
        front=self.hulls[self.control_leader];speed=float(self.velocity[front,3:]@self.d.xmat[front].reshape(3,3)[:,0])
        if self.access is not None:
            self.d.ctrl[self.access_act]=self.access.step(self.d.qpos[self.access_q],self.d.qvel[self.access_v],speed,dt)
            self.d.qfrc_applied[self.access_v]+=self.access.latch_torques
            available_power=max(0.,available_power-self.access.power)
            if not self.access.drive_permitted:speed_request=0.
        if self.steering is not None:
            heading=math.atan2(self.d.xmat[front,3],self.d.xmat[front,0])
            path_xy=self.d.xpos[front,:2]-self.neutral_hull_xy[self.control_leader]
            state=self.steering.update(speed_request,speed,curvature_request,*path_xy,heading,dt);speed_request=state['speed_request_m_s']
        rate=C['drive_accel_limit_m_s2'] if speed_request>self.filtered_speed else C['brake_accel_limit_m_s2']
        if self.steering is not None:rate=C['drive_accel_limit_m_s2'] if abs(speed_request)>abs(self.filtered_speed) and speed_request*self.filtered_speed>=0 else C['brake_accel_limit_m_s2']
        self.filtered_speed+=np.clip(speed_request-self.filtered_speed,-rate*dt,rate*dt)
        accel=np.clip(2*(self.filtered_speed-speed),-C['brake_accel_limit_m_s2'],C['drive_accel_limit_m_s2'])
        if self.steering is not None:
            error=2*(self.filtered_speed-speed);direction=-1 if speed<-.1 or self.filtered_speed<0 else 1
            cap=C['drive_accel_limit_m_s2'] if error*direction>0 else C['brake_accel_limit_m_s2'];accel=float(np.clip(error,-cap,cap))
        share=loads/max(loads.sum(),1.)
        grade=9.81*float(forward[:,2]@share)
        propulsion=self.total_mass*(accel+grade+C['rolling_resistance']*9.81*np.tanh(speed*2))
        propulsion=np.clip(propulsion,-C['friction']*float(loads.sum()),available_power/max(abs(speed),2))
        drive=propulsion*share
        self.requested_yaw_moment=0.;self.requested_yaw_rate=0.
        if self.path_control and max(abs(speed),abs(speed_request))>.1:
            heading=math.atan2(self.d.xmat[front,3],self.d.xmat[front,0])
            desired_heading=math.atan2(-C['path_cross_track_gain_per_s']*self.d.xpos[front,1],max(abs(speed),1.))
            error=math.atan2(math.sin(desired_heading-heading),math.cos(desired_heading-heading))
            limit=C['path_lateral_accel_limit_m_s2']/max(abs(speed),1.)
            self.requested_yaw_rate=float(np.clip(C['path_heading_gain_per_s']*error,-limit,limit))
            if self.steering is not None:self.requested_yaw_rate=self.steering.state['yaw_rate_request_rad_s']
            moment=self.steering_inertia*C['path_yaw_rate_gain_per_s']*(self.requested_yaw_rate-self.velocity[front,2])
            self.requested_yaw_moment=float(np.clip(moment,-C['path_yaw_moment_limit_Nm'],C['path_yaw_moment_limit_Nm']))
            leverage=np.cross(contact-self.d.xipos[front],forward)[:,2]
            leverage-=float(leverage@share)
            drive+=self.requested_yaw_moment*share*leverage/max(float((leverage**2)@share),1.)
        # Shared finite traction power also covers differential steering.
        track_speed=np.sum(v*forward,axis=1)
        power=float(np.sum(abs(drive*track_speed)))
        drive*=min(1.,available_power/max(power,1.))
        self.applied_drive_power=float(np.sum(abs(drive*track_speed)))
        fx=drive-C['rolling_resistance']*loads*np.tanh(track_speed*2)
        fy=-self.total_mass*share*C['lateral_relaxation_per_s']*np.sum(v*lateral,axis=1)
        tangent=forward*fx[:,None]+lateral*fy[:,None];tangent*=np.minimum(1,C['friction']*loads/np.maximum(np.linalg.norm(tangent,axis=1),1))[:,None]
        force=normal*loads[:,None]+tangent
        np.add.at(self.d.xfrc_applied[:,:3],ids,force)
        np.add.at(self.d.xfrc_applied[:,3:],ids,np.cross(contact-self.d.xipos[ids],force))
        count=len(self.hitch_q)//4
        kp=np.tile([A['extension_kp_N_per_m'],*A['rotation_kp_Nm_per_rad']],count);kd=np.tile([A['extension_kd_Ns_per_m'],*A['rotation_kd_Nms_per_rad']],count);caps=np.tile([A['extension_force_limit_N'],*A['rotation_torque_limits_Nm']],count)
        if self.steering is not None:
            kp[1::4]=self.steering.c['hitch_yaw_kp_Nm_rad'];kd[1::4]=self.steering.c['hitch_yaw_kd_Nms_rad']
        target=np.zeros(len(self.hitch_q)) if hitch_targets is None else np.asarray(hitch_targets,dtype=float)
        if self.steering is not None:target[1::4]=self.steering.hitch_yaw
        limits=np.array([self.m.jnt_range[self.m.joint(n).id] for n in self.hitch_names]);target=np.clip(target,limits[:,0],limits[:,1])
        self.d.ctrl[:len(self.hitch_q)]=np.clip(kp*(target-self.d.qpos[self.hitch_q])-kd*self.d.qvel[self.hitch_v],-caps,caps)
        if self.steering is not None:
            tc=self.manifest['turning_control'];effort=tc['bogie_yaw_kp_Nm_rad']*(self.steering.bogie_yaw-self.d.qpos[self.steer_q])-tc['bogie_yaw_kd_Nms_rad']*self.d.qvel[self.steer_v]
            self.d.ctrl[len(self.hitch_q):len(self.hitch_q)+len(self.steer_q)]=np.clip(effort,-tc['bogie_yaw_torque_limit_Nm'],tc['bogie_yaw_torque_limit_Nm'])
        imu=[]
        for h,offset in zip(self.hulls,[[25,0,2.5]]+[[0,0,5]]*(len(self.hulls)-1)):
            world_offset=self.d.xmat[h].reshape(3,3)@offset
            imu.append(self.velocity[h,3:]+np.cross(self.velocity[h,:3],world_offset))
        imu=np.array(imu)
        if self.last_imu is not None:self.imu_acceleration=(imu-self.last_imu)/dt
        self.last_imu=imu.copy();self.peak_acceleration=np.maximum(self.peak_acceleration,abs(self.imu_acceleration[:,2]))
        self.record_qpos=self.d.qpos.copy()
        mujoco.mj_step2(self.m,self.d)
        return speed
    def record(self,speed):
        result=dict(time=float(self.d.time-C['dt_s']),speed_m_s=speed,hull_positions=self.d.xpos[self.hulls].tolist(),
                    upright=[float(self.d.xmat[h].reshape(3,3)[2,2]) for h in self.hulls],normal_load_N=float(self.normal.sum()),supported_contacts=int((self.normal>1).sum()),
                    heave_m=self.record_qpos[self.heave_q].tolist(),wheel_travel_m=self.record_qpos[self.wheel_q].tolist(),
                    path_yaw_rate_request_rad_s=self.requested_yaw_rate,path_yaw_moment_request_Nm=self.requested_yaw_moment,
                    allocated_drive_power_W=self.applied_drive_power,
                    imu_vertical_accel_m_s2=self.imu_acceleration[:,2].tolist(),hitch_coordinates=self.record_qpos[self.hitch_q].tolist())
        if self.hydraulics is not None:result['hydraulics']=self.hydraulics.record()
        if self.track_tension is not None:result['track_tension']=self.track_tension.record()
        if self.steering is not None:
            result.update(steering=self.steering.state.copy(),bogie_yaw_rad=self.record_qpos[self.steer_q].tolist(),actuator_efforts=self.d.ctrl.tolist(),
                          hull_heading_rad=[math.atan2(self.d.xmat[h,3],self.d.xmat[h,0]) for h in self.hulls],control_leader=self.hull_names[self.control_leader])
        return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--terrain',choices=['flat','alternating','ditch','rough','ramp'],default='flat');parser.add_argument('--rigid',action='store_true');parser.add_argument('--no-path-control',action='store_true');parser.add_argument('--speed',type=float,default=0.);parser.add_argument('--seconds',type=float,default=30.);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    env=Env(args.terrain,args.rigid,not args.no_path_control);samples=[];started=time.monotonic();failed=False;peak_speed=0.
    accel_squares=np.zeros(2);accel_count=0;route_max=np.zeros(2);peak_times=np.zeros(2);prior_peak=np.zeros(2)
    for step in range(round(args.seconds/C['dt_s'])):
        v=env.substep(0. if env.d.time<10 else args.speed);peak_speed=max(peak_speed,v)
        peak_times=np.where(env.peak_acceleration>prior_peak,env.d.time-C['dt_s'],peak_times);prior_peak=env.peak_acceleration.copy()
        if env.d.time>=10:
            accel_squares+=env.imu_acceleration[:,2]**2;accel_count+=1
            route_max=np.maximum(route_max,abs(env.d.xpos[env.hulls,1]))
        if step%20==19:samples.append(env.record(v))
        if not np.isfinite(env.d.qpos).all() or min(env.d.xmat[h].reshape(3,3)[2,2] for h in env.hulls)<.5:
            failed=True;break
    report=dict(engine='MuJoCo '+mujoco.__version__,failed=failed,terrain=args.terrain,rigid=args.rigid,path_control=env.path_control,requested_speed_m_s=args.speed,seconds=float(env.d.time),wall_seconds=time.monotonic()-started,
                dynamic_bodies=env.m.nbody-1,dofs=env.m.nv,mass_kg=float(env.m.body_mass.sum()),peak_speed_kmh=peak_speed*3.6,peak_all_step_vertical_accel_m_s2=env.peak_acceleration.tolist(),samples=samples,
                rms_all_step_vertical_accel_after_settle_m_s2=np.sqrt(accel_squares/max(accel_count,1)).tolist(),peak_acceleration_times_s=peak_times.tolist(),max_all_step_lateral_path_error_m=route_max.tolist(),
                source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'source/suspension_physics.py',ROOT/'design/suspension_candidate.json',ROOT/'design/articulation_candidate.json']},
                scope='Independent native bogie and wheel dynamics with compliant reduced belt contact; finite-power differential-track path feedback, provisional mass/inertia, straight path only, no learned policy, Godot transfer, visual belt deformation or hardware rating.')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['samples','source_sha256']},indent=2))
    raise SystemExit(1 if failed else 0)
if __name__=='__main__':main()
