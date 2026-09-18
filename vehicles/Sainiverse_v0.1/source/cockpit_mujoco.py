"""MuJoCo counterpart of finite-force pilot controls, SI source Z-up."""
import numpy as np
import mujoco
class Cockpit:
 def __init__(self,m,d,spec,cargo_handler=None):
  self.cargo_handler=cargo_handler
  self.m,self.d,self.spec=m,d,spec;self.targets={c['id']:0. for c in spec['controls']};self.values={};self.pressed={};self.events=[];self.physical_mode=False;self.parking=False;self.working=False;self.doors_open=False;self.lift_requested=[False]*6;self.carrier_speed_m_s=0.
 def __call__(self,dt):
  for c in self.spec['controls']:
   name=c['name'];id=c['id'];j=self.m.joint(name);body=self.m.body(name).id;q=float(self.d.qpos[j.qposadr[0]]);v=float(self.d.qvel[j.dofadr[0]]);axis=self.d.xaxis[j.id];anchor=self.d.xanchor[j.id]
   goal=self.targets[id];lo,hi=c['limits']
   if self.physical_mode:goal=round(q/hi*(c['detents']-1))*hi/(c['detents']-1) if c['detents']>1 else 0.
   gravity=np.array([0,0,-9.81*c['mass_kg']]);load=np.dot(gravity,axis) if c['kind']=='slide' else np.dot(np.cross(self.d.xipos[body]-anchor,gravity),axis)
   coupling=0.
   if id in ['steer','steer_copilot']:
    other=self.m.joint('cockpit_'+('steer_copilot' if id=='steer' else 'steer'))
    coupling=28.*(self.d.qpos[other.qposadr[0]]-q)+1.2*(self.d.qvel[other.dofadr[0]]-v)
   self.d.ctrl[self.m.actuator(name).id]=np.clip(c['kp']*(goal-q)-c['kd']*v-load+coupling,-c['effort_cap'],c['effort_cap'])
   self.values[id]=float(np.clip(q/hi,-1 if lo<0 else 0,1))
   if c['kind']=='slide':
    if q>.007 and not self.pressed.get(id,False):
     self.pressed[id]=True;accepted=abs(self.carrier_speed_m_s)<.10 if id in ['work','lift','lifts_all'] else True
     if id=='emergency':self.parking=not self.parking
     if id=='doors':self.doors_open=not self.doors_open
     if id=='cargo':accepted=bool(self.cargo_handler()) if self.cargo_handler is not None else False
     if accepted and id=='work':self.working=not self.working
     if accepted and id in ['lift','lifts_all']:
      selected=round(self.values.get('lift_select',0)*5);goal=not self.lift_requested[selected]
      if id=='lifts_all':self.lift_requested=[goal]*6
      else:self.lift_requested[selected]=goal
     self.events.append(dict(time=float(self.d.time),control=id,accepted=accepted))
    if q<.003:self.pressed[id]=False
 def command(self):
  v={k:0 if abs(x)<.015 else x for k,x in self.values.items()};t=v.get('throttle',0)
  return dict(speed_m_s=0. if self.parking else (t*(27.777778 if v.get('high_range',0)>.5 else 12) if t>=0 else t*5)*(1-v.get('brake',0)),curvature_m_inv=v.get('steer',0)*.012,crane_index=round(v.get('crane_select',0)*7),lift_index=round(v.get('lift_select',0)*5),parking=self.parking,working=self.working,doors_open=self.doors_open,lift_requested=list(self.lift_requested),axes={k:v.get(k,0) for k in ['crane_slew','crane_luff','crane_extend','crane_winch','panel_slew','panel_fold']})
