"""Complete carrier + one 8 t container: real equality hook and ground set-down."""
from pathlib import Path
import sys,json,time,argparse,xml.etree.ElementTree as E
import numpy as np,mujoco
O=Path(__file__).resolve().parents[1];R=O/'support';sys.path.insert(0,str(R/'source'))
from suspension_physics import Env
from equipment_mujoco import Equipment
from lift_servo import efforts
from cockpit_mujoco import Cockpit
ap=argparse.ArgumentParser();ap.add_argument('--seconds',type=float,default=240);args=ap.parse_args()
p=json.loads((O/'physics/parameters.json').read_text());rig=p['equipment'];load=rig['cargo'][0];crane=rig['cranes'][0]
root=E.parse(O/'physics/suspended.xml').getroot();eq=root.find('equality')
E.SubElement(eq,'connect',name='cargo_hook_pin',body1=crane['hook'],body2=load['name'],anchor='0 0 -.48',active='false')
path=O/'reports/cargo_test.xml';E.ElementTree(root).write(path)
e=Env('flat',False,True,path,p);m,d=e.m,e.d;c=Equipment(m,d,rig);cockpit=Cockpit(m,d,p['cockpit'])
pin=m.equality('cargo_hook_pin').id;lock=m.equality(load['name']+'_deck_lock').id;bid=m.body(load['name']).id;hook=m.body(crane['hook']).id
initial=d.xpos[bid].copy();phase='secured';phase_start=0.;events=[];rows=[];peak=0.;supported_time=0.;started=time.monotonic();next_pulse=0.;pulse_end=0.
def hook_eye():return d.xpos[hook]+d.xmat[hook].reshape(3,3)@np.array([0,0,-.48])
def eye():return d.xpos[bid]+d.xmat[bid].reshape(3,3)@load['eye_local']
def speed(i):
 v=np.zeros(6);mujoco.mj_objectVelocity(m,d,mujoco.mjtObj.mjOBJ_BODY,i,v,0);return np.linalg.norm(v[3:])
def change(name):
 global phase,phase_start
 phase=name;phase_start=float(d.time);events.append(dict(time=float(d.time),phase=phase));print(events[-1],flush=True)
def request_hook():
 # Dispatch only from the physical cockpit joint crossing its press threshold.
 if speed(m.body('front').id)>.10 or not cockpit.working:return False
 if d.eq_active[pin]:
  if supported_time<=.35 or speed(bid)>=.12:return False
  d.eq_active[pin]=0;c.attached_cargo=None;c.attached_crane=None
  events.append(dict(time=float(d.time),action='release'));return True
 if np.linalg.norm(hook_eye()-eye())>=.32 or speed(hook)>=.30:return False
 m.eq_data[pin,:3]=[0,0,-.48];m.eq_data[pin,3:6]=d.xmat[bid].reshape(3,3).T@(hook_eye()-d.xpos[bid]);d.eq_active[pin]=1;d.eq_active[lock]=0
 c.attached_cargo=load['name'];c.attached_crane=crane['name']
 events.append(dict(time=float(d.time),action='attach'));return True
cockpit.cargo_handler=request_hook
def pulse_hook():
 global next_pulse,pulse_end
 if d.time>=next_pulse:next_pulse=d.time+1.;pulse_end=d.time+.30
def controls(dt):
 global phase,peak,supported_time
 peak=max(peak,float(d.xpos[bid,2]-initial[2]));supported=False
 for contact in d.contact:
  bs={int(m.geom_bodyid[contact.geom1]),int(m.geom_bodyid[contact.geom2])}
  if bid in bs and 0 in bs and contact.pos[2]<d.xpos[bid,2]-.7:supported=True
 supported_time=supported_time+dt if supported else 0.
 if d.time>=12 and phase=='secured':change('align')
 goal=dict(yaw=-.374,luff=.30,extend=3.94,rope=3.5)
 if phase=='align':
  goal['rope']=float(np.clip(c.paid[crane['name']]+hook_eye()[2]-eye()[2],1.3,24))
  if d.eq_active[pin]:change('lift')
  elif np.linalg.norm(hook_eye()-eye())<.28 and speed(hook)<.25:pulse_hook()
 elif phase=='lift':
  pitch=c.state(crane['luff'])[0]
  goal.update(luff=min(.60,.30+(d.time-phase_start)*.015),rope=1.3,extend=(10.42810649+.34*np.sin(pitch))/np.cos(pitch)-7.08)
  if pitch>.59 and speed(bid)<.15:change('clearance')
 elif phase=='clearance':
  goal.update(luff=.60,extend=7.20,rope=1.3)
  if sum(c.state(n)[0] for n in crane['stages'])>7.12 and speed(bid)<.15:change('swing')
 elif phase=='swing':
  goal.update(luff=.60,extend=7.20,rope=1.3,yaw=-2.95)
  if abs(c.state(crane['slew'])[0]+2.95)<.025 and speed(bid)<.20:change('lower')
 elif phase=='lower':
  goal.update(luff=.60,extend=7.20,rope=24.,yaw=-2.95)
  if not d.eq_active[pin]:change('released')
  elif supported_time>.35 and speed(bid)<.12:pulse_hook()
 elif phase=='released':goal.update(luff=.60,extend=7.20,rope=1.3,yaw=-2.95)
 if d.time>=12:c.goals[crane['name']]=goal
 cockpit.working=d.time>=12;cockpit.targets['cargo']=.012 if d.time<pulse_end else 0.
 c(dt);cockpit(dt)
e.mechanism_control=controls
for step in range(round(args.seconds/.005)):
 for lift in p['boarding_lifts']:
  names=lift['groups'];h=m.body(lift['hull']).id;vertical=d.xmat[h].reshape(3,3)[2,2]
  states=np.array([c.state(n) for n in names]);forces=efforts(states[:,0],states[:,1],np.zeros(4),lift['masses'],lift['ramp']['mass_kg'],.005)
  for i,n in enumerate(names):
   q,v=states[i];gravity=0 if i==0 else -9.81*(sum(lift['masses'][i:])+lift['ramp']['mass_kg'])*vertical
   d.ctrl[m.actuator(n).id]=np.clip(forces[i]+gravity,-60000,60000)
  n=lift['ramp']['name'];q,v=c.state(n);d.ctrl[m.actuator(n).id]=np.clip(-10000*q-2000*v-lift['ramp']['mass_kg']*9.81*np.sin(q),-3000,3000)
 e.substep(0.)
 assert np.isfinite(d.qpos).all() and np.max(np.abs(d.qvel))<100
 if step%20==0:rows.append(dict(time=float(d.time),phase=phase,position=d.xpos[bid].tolist(),speed_m_s=speed(bid),hook_eye_error_m=float(np.linalg.norm(hook_eye()-eye())),supported_time_s=supported_time,hook_connected=bool(d.eq_active[pin])))
report=dict(seconds=float(d.time),wall_seconds=time.monotonic()-started,mass_kg=float(m.body_mass[bid]),max_lift_m=peak,released=phase=='released',events=events,cockpit_events=cockpit.events,samples=rows)
(O/'reports/mujoco_cargo.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='samples'});assert report['released'] and peak>3.3 and speed(bid)<.05
