"""Actual MuJoCo runtime check, finite-effort lifts and inherited carrier controller."""
from pathlib import Path
import sys,json,time
import numpy as np
O=Path(__file__).resolve().parents[1];R=O/'support';sys.path.insert(0,str(R/'source'))
from suspension_physics import Env
p=json.loads((O/'physics/parameters.json').read_text())
e=Env('flat',False,True,O/'physics/suspended.xml',p);m,d=e.m,e.d
from equipment_mujoco import Equipment
from cockpit_mujoco import Cockpit
equipment=Equipment(m,d,p["equipment"]);cockpit=Cockpit(m,d,p["cockpit"])
def controls(dt):equipment(dt);cockpit(dt)
e.mechanism_control=controls
lifts=p['boarding_lifts'];target={n:0. for l in lifts for n in l['groups']};rows=[];start=time.monotonic();peak=0.
for step in range(15000):
 t=float(d.time);want=12<=t<47
 for lift in lifts:
  names=lift['groups'];q=np.array([d.qpos[m.joint(n).qposadr[0]] for n in names]);dq=np.array([d.qvel[m.joint(n).dofadr[0]] for n in names]);h=m.body(lift['hull']).id
  rot=d.xmat[h].reshape(3,3);pivot=np.array(lift['pivot'])-np.array(p['interior']['datum_source_m']);pivot[0]=0
  top=d.xpos[h]+rot@pivot+rot[:,2]*.125
  depth=np.clip((top[2]-.245)/max(rot[2,2],.95),0,3*lift['stroke_stage']) if want and q[0]>lift['stroke_out']-.04 else 0.
  ramp=lift['ramp'];rn=ramp['name'];rq=float(d.qpos[m.joint(rn).qposadr[0]]);rv=float(d.qvel[m.joint(rn).dofadr[0]])
  hinge_z=float(d.xpos[m.body(rn).id,2]);goal=np.pi/2+np.arcsin(np.clip((hinge_z-.02)/2,0,.18)) if want and hinge_z<.35 and q[0]>2.65 else 0.
  target.setdefault(rn,0.);target[rn]+=np.clip(goal-target[rn],-.65*.005,.65*.005)
  d.ctrl[m.actuator(rn).id]=np.clip(10000*(target[rn]-rq)-2000*rv-ramp['mass_kg']*9.81*np.sin(rq),-3000,3000)
  if not want and rq>.04:depth=q[1:].sum()
  for i,n in enumerate(names):
   goal=(lift['stroke_out'] if want or q[1:].sum()>.03 else 0.) if i==0 else depth/3
   rate=.55 if i==0 else .7/3;target[n]+=np.clip(goal-target[n],-rate*.005,rate*.005)
   gravity=0 if i==0 else -9.81*(sum(lift['masses'][i:])+ramp['mass_kg'])*rot[2,2]
   d.ctrl[m.actuator(n).id]=np.clip(80000*(target[n]-q[i])-14000*dq[i]+gravity,-60000,60000)
  if step%200==0:rows.append(dict(time=t,name=lift['name'],out=float(q[0]),depth=float(q[1:].sum()),floor_z=float(d.xpos[m.body(names[-1]).id,2]+.125),underside_gap_m=float(d.xpos[m.body(names[-1]).id,2]-.125),ramp_angle_rad=rq,ramp_target_rad=float(goal),ground_contacts=sum(1 for ct in d.contact if m.geom(names[-1]+"_deck").id in ct.geom)))
 e.substep(0.)
 assert np.isfinite(d.qpos).all() and np.isfinite(d.qvel).all()
 peak=max(peak,float(np.max(np.abs(d.qvel))))
report=dict(seconds=float(d.time),wall_seconds=time.monotonic()-start,bodies=m.nbody,dofs=m.nv,actuators=m.nu,peak_qvel=peak,rows=rows,scope='Actual MuJoCo finite-force mechanism cycle; stationary unloaded carrier. No learned robot policy or loaded boarding certification.')
(O/'reports/mujoco_cycle.json').write_text(json.dumps(report,indent=2))
assert max(r['depth'] for r in rows)>6
assert max(r['depth'] for r in rows[-6:])<.04
print({k:v for k,v in report.items() if k!='rows'})
