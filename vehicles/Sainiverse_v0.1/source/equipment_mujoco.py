"""Finite actuator/cable counterpart of runtime/equipment_control.gd, SI Z-up.
Called after mj_step1 and carrier forces, immediately before mj_step2.
"""
import numpy as np
import mujoco

class Equipment:
 def __init__(self,model,data,rig,work=False):
  self.m,self.d,self.rig,self.work=model,data,rig,work
  self.target={j['name']:0. for j in rig['joints']};self.paid={c['name']:c['paid_length_m'] for c in rig['cranes']}
  self.goals={};self.attached_cargo=None;self.attached_crane=None
  self.rows=[];self.step_count=0;self.jac=np.zeros((3,model.nv));self.zero=np.zeros(3)
 def body(self,n):return self.m.body(n).id
 def endpoint(self,p):
  i=self.body(p['body']);return self.d.xpos[i]+self.d.xmat[i].reshape(3,3)@p['local']
 def velocity(self,p,point):
  mujoco.mj_jac(self.m,self.d,self.jac,None,point,self.body(p['body']));return self.jac@self.d.qvel
 def force(self,n,force,point):
  i=self.body(n);self.d.xfrc_applied[i,:3]+=force;self.d.xfrc_applied[i,3:]+=np.cross(point-self.d.xipos[i],force)
 def state(self,n):
  j=self.m.joint(n);return self.d.qpos[j.qposadr[0]],self.d.qvel[j.dofadr[0]]
 def advance(self,n,goal,rate,dt):self.target[n]+=float(np.clip(goal-self.target[n],-rate*dt,rate*dt))
 def gravity(self,n,names):
  j=self.m.joint(n).id;axis=self.d.xaxis[j];anchor=self.d.xanchor[j];total=0.
  for name in names:
   i=self.body(name);g=np.array([0.,0.,-9.81*self.m.body_mass[i]])
   total+=np.dot(g,axis) if self.m.jnt_type[j]==mujoco.mjtJoint.mjJNT_SLIDE else np.dot(np.cross(self.d.xipos[i]-anchor,g),axis)
  return total
 def servo(self,n,goal,rate,kp,kd,cap,dt,names=()):
  self.advance(n,goal,rate,dt);q,v=self.state(n);u=np.clip(kp*(self.target[n]-q)-kd*v-self.gravity(n,names),-cap,cap)
  self.d.ctrl[self.m.actuator(n).id]=u
 def __call__(self,dt):
  t=float(self.d.time);working=self.work and 12<=t<55
  for c in self.rig['cranes']:
   pin=next(b['pivot'] for b in self.rig['bodies'] if b['name']==c['luff']);hull_x=-42 if c['hull']=='rear' else -84
   outward=-np.sign(pin[0]-hull_x)*np.sign(c['direction'][1]);yaw=outward*.2*np.sin(min(max(t-23,0)*.085,np.pi*.65)) if working else 0
   goal=self.goals.get(c['name'],{});yaw=goal.get('yaw',yaw)
   self.servo(c['slew'],yaw,.055,8e6,2.4e6,2.5e6,dt)
   self.advance(c['luff'],goal.get('luff',.30 if working else 0.),.035,dt);q,v=self.state(c['luff'])
   requested=14e6*(self.target[c['luff']]-q)-2.8e6*v-self.gravity(c['luff'],[c['luff'],c['hook']]+c['stages']+([self.attached_cargo] if self.attached_crane==c['name'] else []))
   a=self.endpoint(c['cylinder_a']);b=self.endpoint(c['cylinder_b']);direction=(b-a)/np.linalg.norm(b-a)
   j=self.m.joint(c['luff']).id;lever=np.dot(np.cross(b-self.d.xanchor[j],direction),self.d.xaxis[j]);f=np.clip(requested/max(lever,.1),-c['cylinder_force_cap_N'],c['cylinder_force_cap_N'])
   self.force(c['luff'],direction*f,b);self.force(c['slew'],-direction*f,a)
   extension_goal=np.clip(goal.get('extend',.65 if working else 0.),0.,c['extension_range_m'][1])
   for i,stage in enumerate(c['stages']):
    fraction=c['stage_strokes_m'][i]/c['extension_range_m'][1]
    self.servo(stage,extension_goal*fraction,.30*fraction,1.6e6,320e3,600e3,dt,c['stages'][i:]+[c['hook']]+([self.attached_cargo] if self.attached_crane==c['name'] else []))

   rope_goal=goal.get('rope',max(1.3,c['paid_length_m']-1.4) if working else c['paid_length_m']);self.paid[c['name']]+=np.clip(rope_goal-self.paid[c['name']],-.4*dt,.4*dt)
   top=self.endpoint(c['tip']);bottom=self.endpoint(c['hook_attach']);length=np.linalg.norm(top-bottom);unit=(top-bottom)/max(length,.001)
   speed=np.dot(self.velocity(c['tip'],top)-self.velocity(c['hook_attach'],bottom),unit)
   tension=np.clip(c['rope_stiffness_N_m']*(length-self.paid[c['name']])+c['rope_damping_N_s_m']*speed,0,c['rope_force_cap_N']) if length>self.paid[c['name']] else 0
   self.force(c['hook'],unit*tension,bottom);self.force(c['extend'],-unit*tension,top)
   if self.step_count%20==0:self.rows.append(dict(time=t,name=c['name'],slew_rad=float(self.state(c['slew'])[0]),luff_rad=float(q),extension_m=float(sum(self.state(n)[0] for n in c['stages'])),cable_force_N=float(tension),cylinder_force_N=float(f),paid_length_m=float(self.paid[c['name']])))
  p=self.rig['panel'];yaw=.28*np.sin(max(t-15,0)*.06) if working else 0;fold=-.65*(.5-.5*np.cos(min(max(t-15,0)*.09,np.pi))) if working else 0
  self.servo(p['slew'],yaw,.05,16e6,5e6,5e6,dt);self.servo(p['fold'],fold,.055,16e6,4e6,12e6,dt,[p['fold']])
  if self.step_count%20==0:self.rows.append(dict(time=t,name='receiver',slew_rad=float(self.state(p['slew'])[0]),fold_rad=float(self.state(p['fold'])[0])))
  self.step_count+=1
