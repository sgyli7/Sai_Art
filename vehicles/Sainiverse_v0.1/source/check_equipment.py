from pathlib import Path
import sys,json,time,argparse
import numpy as np
O=Path(__file__).resolve().parents[1];R=O/'support';sys.path.insert(0,str(R/'source'))
from suspension_physics import Env
from equipment_mujoco import Equipment
from lift_servo import efforts
ap=argparse.ArgumentParser();ap.add_argument('--seconds',type=float,default=85);args=ap.parse_args()
p=json.loads((O/'physics/parameters.json').read_text());e=Env('flat',False,True,O/'physics/suspended.xml',p)
c=Equipment(e.m,e.d,p['equipment'],True);start=time.monotonic()
from cockpit_mujoco import Cockpit
cockpit=Cockpit(e.m,e.d,p["cockpit"])
def controls(dt):c(dt);cockpit(dt)
e.mechanism_control=controls
# Hold the existing boarding lift/ramp mechanisms through finite actuators.
from math import sin
for step in range(round(args.seconds/.005)):
 for lift in p['boarding_lifts']:
  names=lift['groups'];h=e.m.body(lift['hull']).id;vertical=e.d.xmat[h].reshape(3,3)[2,2]
  states=np.array([c.state(n) for n in names]);forces=efforts(states[:,0],states[:,1],np.zeros(4),lift['masses'],lift['ramp']['mass_kg'],.005)
  for i,n in enumerate(names):
   q,v=states[i];gravity=0 if i==0 else -9.81*(sum(lift['masses'][i:])+lift['ramp']['mass_kg'])*vertical
   e.d.ctrl[e.m.actuator(n).id]=np.clip(forces[i]+gravity,-60000,60000)
  n=lift['ramp']['name'];q,v=c.state(n);e.d.ctrl[e.m.actuator(n).id]=np.clip(-10000*q-2000*v-lift['ramp']['mass_kg']*9.81*sin(q),-3000,3000)
 e.substep(0.)
 assert np.isfinite(e.d.qpos).all() and np.max(np.abs(e.d.qvel))<100,'mechanism instability'
report=dict(seconds=float(e.d.time),wall_seconds=time.monotonic()-start,samples=c.rows,scope='Actual MuJoCo unloaded crane and receiver actuation/return; finite forces and dynamic free hooks. Source-volume provisional masses; no lifted cargo or hardware rating.')
(O/'reports/mujoco_equipment.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='samples'})
