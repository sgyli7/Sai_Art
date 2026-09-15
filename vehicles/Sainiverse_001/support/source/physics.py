"""Two native rigid hulls + ball hitch + 32 unilateral suspension/traction patches.
Reduced transport model: belts/bogies do not resolve individual link inertia.
Forces are computed at ground patches; native MuJoCo integrates every pose.
"""
from pathlib import Path
import json,math,time
import numpy as np
import mujoco
ROOT=Path(__file__).resolve().parents[1]
from layout import UNDER,LAYOUT
CFG=dict(id='Leviathan_003',schema=1,coordinates='SI X front Y left Z up',mass_kg=[5000000.,5000000.],com_z=10.,hull_centers_x=UNDER['hull_centers_x'],hitch_x=LAYOUT['hitch_x'],hitch_z=LAYOUT['hitch_z'],dt=.005,control_dt=.05,max_speed=100/3.6,reverse_speed=5.,max_accel=.65,max_brake=1.,lateral_accel=.65,max_yaw=.06,friction=.7,suspension_travel=1.5,rest_height=10.65,power_w=180e6,rolling=.012,patches_per_hull=16)
OFFSETS=np.array([[x+dx,y+dy,-10.] for x in UNDER['bogie_offsets_x'] for y in UNDER['bogie_offsets_y'] for dx in (-3.1,3.1) for dy in UNDER['belt_offsets_y']])
DEFAULT=np.array([.8,2.,2.5]) # speed response, yaw response, lateral relaxation

def build():
    import xml.etree.ElementTree as E
    root=E.Element('mujoco',model='Leviathan_003');E.SubElement(root,'compiler',angle='radian',autolimits='true')
    E.SubElement(root,'option',timestep=str(CFG['dt']),gravity='0 0 -9.81',integrator='implicitfast',iterations='20',tolerance='1e-8')
    world=E.SubElement(root,'worldbody');E.SubElement(world,'geom',name='ground',type='plane',size='0 0 .1',rgba='.7 .75 .78 1',contype='0',conaffinity='0')
    def hull(parent,name,pos,joint):
        b=E.SubElement(parent,'body',name=name,pos=' '.join(map(str,pos)))
        if joint=='free':E.SubElement(b,'freejoint',name='root')
        else:E.SubElement(b,'joint',name='hitch',type='ball',pos=f"{CFG['hitch_x']-CFG['hull_centers_x'][1]} 0 {CFG['hitch_z']-CFG['com_z']}",damping='20000000',limited='true',range='0 .6')
        mass=5e6;inertia=mass/12*np.array([27**2+18**2,34**2+18**2,34**2+27**2])
        E.SubElement(b,'inertial',pos='0 0 0',mass=str(mass),diaginertia=' '.join(map(str,inertia)))
        E.SubElement(b,'geom',name=name+'_proxy',type='box',pos='0 0 -2.8',size='17 13.5 .3',rgba='.65 .7 .65 1',contype='0',conaffinity='0',mass='0')
        return b
    f=hull(world,'front',[CFG['hull_centers_x'][0],0,CFG['com_z']],'free');r=hull(f,'rear',[CFG['hull_centers_x'][1]-CFG['hull_centers_x'][0],0,0],'ball')
    visual_manifest=ROOT/'assets/visual_meshes.json'
    if visual_manifest.exists():
        asset=E.SubElement(root,'asset')
        for item in json.loads(visual_manifest.read_text()):
            E.SubElement(asset,'mesh',name=item['name'],file=item['file'])
            E.SubElement(f if item['hull']=='front' else r,'geom',name=item['name']+'_visual',type='mesh',mesh=item['name'],rgba=' '.join(map(str,item['color'])),contype='0',conaffinity='0',mass='0',group='2')
        for b in [f,r]:
            g=b.find("geom[@type='box']");g.set('rgba','0 0 0 0');g.set('group','3')
    E.SubElement(root,'statistic',center='-12 0 12',extent='90')
    visual=E.SubElement(root,'visual');E.SubElement(visual,'global',offwidth='1600',offheight='1000')
    E.SubElement(visual,'headlight',ambient='.4 .4 .4',diffuse='.6 .6 .6',specular='.15 .15 .15')
    E.SubElement(world,'light',pos='0 -40 70',dir='0 .5 -1',diffuse='.6 .6 .6',directional='true')
    (ROOT/'assets/vehicle.xml').write_text(E.tostring(root,encoding='unicode'))
    (ROOT/'assets/physics.json').write_text(json.dumps({**CFG,'patch_offsets':OFFSETS.tolist(),'inertia_diagonal':(5e6/12*np.array([27**2+18**2,34**2+18**2,34**2+27**2])).tolist(),'assumptions':'10,000 tonne numerical benchmark, estimated mass/inertia; not CAD-derived or hardware-rated','reduction':'2 dynamic hulls / ball articulation / 32 compliant contact patches; 8 bogies visually follow suspension; equipment locked'},indent=2))

class Env:
    def __init__(self,policy=DEFAULT,slope=0):
        self.m=mujoco.MjModel.from_xml_path(str(ROOT/'assets/vehicle.xml'));self.d=mujoco.MjData(self.m)
        self.ids=np.array([self.m.body(n).id for n in ('front','rear')]);self.policy=np.array(policy);self.slope=slope;self.reset()
    def reset(self,seed=0,perturb=False):
        mujoco.mj_resetData(self.m,self.d);self.cmd=np.zeros(2);self.filtered=np.zeros(2);self.force=np.zeros((2,16,3));self.normal=np.zeros((2,16));self.steps=0
        if perturb:
            rng=np.random.default_rng(seed);self.d.qvel[:2]=rng.normal(0,.1,2)
        mujoco.mj_forward(self.m,self.d)
    def state(self):
        bid=self.ids[0];rot=self.d.xmat[bid].reshape(3,3);v=np.zeros(6);mujoco.mj_objectVelocity(self.m,self.d,mujoco.mjtObj.mjOBJ_BODY,bid,v,0)
        return float(v[3:]@rot[:,0]),float(v[2]),float(rot[2,2])
    def set_command(self,speed,yaw):self.cmd[:]=[np.clip(speed,-5,CFG['max_speed']),yaw]
    def substep(self):
        dt=CFG['dt'];speed,yaw,up=self.state()
        rate=CFG['max_brake'] if abs(self.cmd[0])<abs(self.filtered[0]) or self.cmd[0]*self.filtered[0]<0 else CFG['max_accel']
        self.filtered[0]+=np.clip(self.cmd[0]-self.filtered[0],-rate*dt,rate*dt)
        ymax=min(CFG['max_yaw'],CFG['lateral_accel']/max(abs(speed),1.),abs(self.filtered[0])/50.)
        self.filtered[1]+=np.clip(np.clip(self.cmd[1],-ymax,ymax)-self.filtered[1],-.02*dt,.02*dt)
        accel=np.clip((self.filtered[0]-speed)*self.policy[0],-CFG['max_brake'],CFG['max_accel'])
        # Motor power applies to total tractive work including rolling resistance.
        accel=np.clip(accel,-CFG['max_brake'],max(0,CFG['power_w']/1e7/max(abs(speed),2)-CFG['rolling']*9.81))
        self.d.xfrc_applied[:]=0
        ground_n=np.array([-self.slope,0,1.]);ground_n/=np.linalg.norm(ground_n)
        for h,bid in enumerate(self.ids):
            R=self.d.xmat[bid].reshape(3,3);pos=self.d.xpos[bid];vel=np.zeros(6);mujoco.mj_objectVelocity(self.m,self.d,mujoco.mjtObj.mjOBJ_BODY,bid,vel,0)
            offsets=OFFSETS@R.T;p=pos+offsets;contact=p.copy();contact[:,2]=self.slope*contact[:,0]
            vv=vel[3:]+np.cross(vel[:3],offsets)
            k=5e6*9.81/16/.65;c=2*.8*np.sqrt(k*5e6/16)
            normal=np.clip(k*(.65-p[:,2]+contact[:,2])-c*(vv@ground_n),0,5e6*9.81/16*3)
            # Ackermann patch heading. The aft hull gets articulation alignment;
            # this is a steering target, never a directly assigned angular velocity.
            heading=math.atan2(R[1,0],R[0,0]);frontR=self.d.xmat[self.ids[0]].reshape(3,3);fh=math.atan2(frontR[1,0],frontR[0,0])
            err=math.atan2(math.sin(fh-heading),math.cos(fh-heading))
            target_yaw=self.filtered[1]+(self.policy[1]*err if h else 0.)
            local_v=vv@R
            steer=np.arctan2(target_yaw*OFFSETS[:,0],max(abs(speed),2)-target_yaw*OFFSETS[:,1])*np.sign(self.filtered[0]+1e-9)
            steer=np.clip(steer,-.45,.45)
            forward=np.column_stack([np.cos(steer),np.sin(steer),np.zeros(16)])@R.T
            forward-=np.outer(forward@ground_n,ground_n);forward/=np.linalg.norm(forward,axis=1)[:,None]
            lateral=np.cross(ground_n,forward)
            lateral_v=np.sum(vv*lateral,axis=1)
            roll_force=-CFG['rolling']*normal*np.tanh(np.sum(vv*forward,axis=1)*2)
            fx=np.full(16,5e6/16*accel)+roll_force+5e6/16*CFG['rolling']*9.81*np.tanh(speed*2)
            # Differential traction corrects yaw lag with bounded acceleration.
            fx-=5e6/16*np.clip((target_yaw-vel[2])*self.policy[1],-.15,.15)*OFFSETS[:,1]
            fy=-5e6/16*self.policy[2]*lateral_v
            tangent=forward*fx[:,None]+lateral*fy[:,None]
            cap=CFG['friction']*normal;norm=np.linalg.norm(tangent,axis=1);tangent*=np.minimum(1,cap/np.maximum(norm,1))[:,None]
            force=normal[:,None]*ground_n+tangent
            arms=contact-pos
            self.d.xfrc_applied[bid,:3]=force.sum(0)
            self.d.xfrc_applied[bid,3:]=np.cross(arms,force).sum(0)
            self.force[h]=force;self.normal[h]=normal
        mujoco.mj_step(self.m,self.d);self.steps+=1
    def step(self,speed,yaw=0):
        self.set_command(speed,yaw)
        for _ in range(10):self.substep()
        return self.state()

def episode(policy=DEFAULT,seed=0,seconds=100,mode='straight',slope=0,record=False):
    env=Env(policy,slope);env.reset(seed,True);rows=[];cost=0;start=time.perf_counter();maxspeed=0;minup=1
    for i in range(round(seconds/.05)):
        t=i*.05
        target=CFG['max_speed'] if mode=='straight' else 10. if t<30 else 0. if t>60 else 10.
        yaw=.018 if mode=='turn' and 25<t<60 else 0.
        v,w,up=env.step(target,yaw)
        maxspeed=max(maxspeed,v);minup=min(minup,up)
        cost+=(v-env.filtered[0])**2+1000*(w-env.filtered[1])**2+10000*(1-up)**2
        if not np.isfinite(env.d.qpos).all() or up<.7:return {'loss':1e9,'failed':True},rows
        if record and i%10==0:rows.append(dict(t=t+.05,speed=v,yaw=w,up=up,command=target,position=env.d.xpos[env.ids[0]].tolist(),qpos=env.d.qpos.tolist()))
    result=dict(loss=cost/max(1,i+1),max_speed_kmh=maxspeed*3.6,final_speed_kmh=v*3.6,min_upright=minup,wall_seconds=time.perf_counter()-start,sim_seconds=seconds,policy=list(map(float,policy)),seed=seed,mode=mode,slope=slope)
    result['sim_wall_ratio']=seconds/result['wall_seconds'];return result,rows
if __name__=='__main__':
    build();r,rows=episode(record=True);(ROOT/'reports/mujoco_initial.json').write_text(json.dumps({'result':r,'samples':rows},indent=2));print(r)
