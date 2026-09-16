"""Actual joints + colliders extracted unchanged, fixed-parent control bench.
Tests finite-force motion/commands and an unactuated falling contact probe. Does
not pretend a trained Sai arm is installed or prove full-vehicle transfer.
"""
from pathlib import Path
import copy,json,xml.etree.ElementTree as E
import numpy as np,mujoco
from cockpit_mujoco import Cockpit
O=Path(__file__).resolve().parents[1];source=E.parse(O/'physics/suspended.xml').getroot();spec=json.loads((O/'physics/parameters.json').read_text())['cockpit']
r=E.Element('mujoco');E.SubElement(r,'compiler',angle='radian');E.SubElement(r,'option',timestep='.005',gravity='0 0 -9.81',integrator='implicitfast')
asset=E.SubElement(r,'asset');world=E.SubElement(r,'worldbody');act=E.SubElement(r,'actuator')
for c in spec['controls']:
 name=c['name'];world.append(copy.deepcopy(source.find('.//body[@name="'+name+'"]')))
 act.append(copy.deepcopy(source.find('.//actuator/motor[@name="'+name+'"]')))
 for mesh in source.findall('asset/mesh'):
  if mesh.get('name','').startswith(name+'_contact_'):asset.append(copy.deepcopy(mesh))
def env(root):
 m=mujoco.MjModel.from_xml_string(E.tostring(root,encoding='unicode'));d=mujoco.MjData(m);mujoco.mj_forward(m,d);return m,d,Cockpit(m,d,spec)
def step(m,d,c,seconds):
 for _ in range(round(seconds/m.opt.timestep)):
  mujoco.mj_step1(m,d);c(m.opt.timestep);mujoco.mj_step2(m,d)
  assert np.isfinite(d.qpos).all()
m,d,c=env(r)
for x in spec['controls']:c.targets[x['id']]=x['limits'][1]*(.8 if x['kind']=='hinge' else 1.)
step(m,d,c,3.)
errors={x['id']:abs(float(d.qpos[m.joint(x['name']).qposadr[0]])-c.targets[x['id']]) for x in spec['controls']}
assert max(errors.values())<.006,errors
assert {e['control'] for e in c.events}=={'doors','work','lift','lifts_all','emergency'}
pressed_events=copy.deepcopy(c.events)
for key in c.targets:c.targets[key]=0.
step(m,d,c,3.);assert max(abs(v) for v in c.values.values())<.02,c.values
# A free .5 kg sphere presses WORK by collision alone, with user/servo input off.
r2=copy.deepcopy(r);button=r2.find('worldbody/body[@name="cockpit_work"]');pos=np.fromstring(button.get('pos'),sep=' ')+[0,0,.12]
probe=E.SubElement(r2.find('worldbody'),'body',name='contact_probe',pos=' '.join(map(str,pos)));E.SubElement(probe,'freejoint');E.SubElement(probe,'geom',name='probe',type='sphere',size='.025',mass='.5',contype='16',conaffinity='128',friction='.8 .005 .0001')
m2,d2,c2=env(r2);c2.physical_mode=True;step(m2,d2,c2,2.)
assert any(e['control']=='work' and e['accepted'] for e in c2.events),c2.events
assert c2.working and np.linalg.norm(d2.qvel)<.2
probe_q=float(d2.qpos[m2.joint('cockpit_work').qposadr[0]])
assert .007<probe_q<.014,probe_q
out=dict(joints=len(spec['controls']),max_servo_error=max(errors.values()),errors=errors,events=pressed_events,passive_contact_probe=dict(mass_kg=.5,button_travel_m=probe_q,events=c2.events),scope=__doc__)
(O/'reports/cockpit_mujoco.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k not in ['errors','scope']})
