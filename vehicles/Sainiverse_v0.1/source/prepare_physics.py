from pathlib import Path
import json,copy,xml.etree.ElementTree as E,shutil,hashlib
import numpy as np
O=Path(__file__).resolve().parents[1];R=O/'support';A=O/'baseline'
read=lambda p:json.loads(p.read_text());s=read(A/'physics/native_spec.json');params=read(A/'physics/parameters.json');b=read(A/'bindings.json');lifts=read(O/'source/lifts.json');build=read(O/'reports/build.json')
xml=E.parse(A/'physics/suspended.xml');root=xml.getroot()
E.SubElement(root.find('worldbody'),'geom',name='boarding_contact_ground',type='plane',size='1000 1000 .1',contype='1',conaffinity='8',friction='.9 .005 .0001')
fmt=lambda a:' '.join(str(float(v)) for v in a)
# Added boxed-section steel webs; top and bottom skins are relocated, not filled
# with solid steel. Provisional simulation mass, no certified structure claim.
web_mass=(2*(34+27)*.4*.020+8*27*.4*.014)*7850
mass_records=[]
for hull in ['front','rear','tail']:
 item=next(x for x in s['bodies'] if x['name']==hull);mass=web_mass+700
 old=item['mass'];com=np.array(item['com']);extra=np.array([0,0,-3.35]);new=(old*com+mass*extra)/(old+mass)
 item['inertia']=(np.array(item['inertia'])+mass/12*np.array([27**2+.4**2,34**2+.4**2,34**2+27**2])+old*((np.dot(com-new,com-new))-((com-new)**2))+mass*((np.dot(extra-new,extra-new))-((extra-new)**2))).tolist();item['mass']+=mass;item['com']=new.tolist()
 node=root.find(f'.//body[@name="{hull}"]/inertial');node.set('mass',str(item['mass']));node.set('pos',fmt(new));node.set('diaginertia',fmt(item['inertia']))
 mass_records.append(dict(body=hull,added_kg=mass,web_kg=web_mass,fixed_lift_mount_allowance_kg=700))
# Fixed hull source datum -> neutral physics offset is inherited exactly.
for lift in lifts:
 hull=lift['hull'];datum=np.array(b['groups'][hull]['pivot_source_m']);neutral=np.array(b['groups'][hull]['neutral_body_position_source_m']);pivot=np.array(lift['pivot']);hull_position=np.array(next(x for x in s['bodies'] if x['name']==hull)['position']);pos=pivot+hull_position-neutral
 parent=hull;xmlparent=root.find(f'.//body[@name="{hull}"]');xmlparentpos=hull_position
 for i,name in enumerate(lift['groups']):
  mass=lift['masses'][i];dims=np.array([3.2,2.2,3.9 if i<3 else .25]);inertia=mass/12*np.array([dims[1]**2+dims[2]**2,dims[0]**2+dims[2]**2,dims[0]**2+dims[1]**2]);axis=[0,lift['side'],0] if i==0 else [0,0,-1];travel=lift['stroke_out'] if i==0 else lift['stroke_stage']
  s['bodies'].append(dict(name=name,mass=mass,inertia=inertia.tolist(),com=[0,0,0],position=pos.tolist()))
  s['joints'].append(dict(name=name,body=name,parent=parent,anchor=pos.tolist(),axis=axis,kind='slide',limits=[0,travel],stiffness=0,damping=0,springref=0,lift=True))
  b['groups'][name]=dict(pivot_source_m=pivot.tolist(),neutral_body_position_source_m=pivot.tolist())
  node=E.SubElement(xmlparent,'body',name=name,pos=fmt(pos-xmlparentpos));E.SubElement(node,'inertial',mass=str(mass),pos='0 0 0',diaginertia=fmt(inertia));E.SubElement(node,'joint',name=name,type='slide',axis=fmt(axis),range=fmt([0,travel]),limited='true',damping='0',armature='20',solreflimit='.02 1')
  E.SubElement(root.find('actuator'),'motor',name=name,joint=name,ctrllimited='true',ctrlrange='-60000 60000')
  if i==3:
   E.SubElement(node,'geom',name=name+'_deck',type='box',size='1.6 1.1 .125',mass='0',contype='8',conaffinity='17',friction='.9 .005 .0001')
  xmlparent=node;xmlparentpos=pos;parent=name
 s['contact'].setdefault('boarding_lifts',[]).append(lift)
# Each ramp has its own mass, hinge, actuator and actual contact plate.
for lift in lifts:
 ramp=lift['ramp'];name=ramp['name'];parent=lift['groups'][-1]
 parent_item=next(x for x in s['bodies'] if x['name']==parent)
 pivot=np.array(ramp['pivot']);parent_pivot=np.array(lift['pivot']);pos=np.array(parent_item['position'])+pivot-parent_pivot
 dims=np.array(ramp['size_m']);mass=ramp['mass_kg'];inertia=mass/12*np.array([dims[1]**2+dims[2]**2,dims[0]**2+dims[2]**2,dims[0]**2+dims[1]**2])
 s['bodies'].append(dict(name=name,mass=mass,inertia=inertia.tolist(),com=ramp['com_source_m'],position=pos.tolist()))
 s['joints'].append(dict(name=name,body=name,parent=parent,anchor=pos.tolist(),axis=ramp['axis'],kind='hinge',limits=ramp['range_rad'],stiffness=0,damping=0,springref=0,lift=True,ramp=True))
 b['groups'][name]=dict(pivot_source_m=pivot.tolist(),neutral_body_position_source_m=pivot.tolist())
 parent_node=root.find(f'.//body[@name="{parent}"]');node=E.SubElement(parent_node,'body',name=name,pos=fmt(pivot-parent_pivot))
 E.SubElement(node,'inertial',mass=str(mass),pos=fmt(ramp['com_source_m']),diaginertia=fmt(inertia))
 E.SubElement(node,'joint',name=name,type='hinge',axis=fmt(ramp['axis']),range=fmt(ramp['range_rad']),limited='true',armature='5',damping='0')
 E.SubElement(node,'geom',name=name+'_plate',type='box',size=fmt(dims/2),pos='0 0 1',mass='0',contype='8',conaffinity='17',friction='.9 .005 .0001')
 E.SubElement(root.find('actuator'),'motor',name=name,joint=name,ctrllimited='true',ctrlrange='-3000 3000')
# Strengthened deck collision boxes for native review/player and MuJoCo.
for hull in ['front','rear','tail']:
 node=root.find(f'.//body[@name="{hull}"]')
 for i,(center,size) in enumerate([([0,0,-3.05],[34,24.3,1.]),([-9.32,0,-3.05],[15.36,27,1.]),([9.32,0,-3.05],[15.36,27,1.])]):
  E.SubElement(node,'geom',name=hull+f'_boarding_deck_{i}',type='box',size=fmt(np.array(size)/2),pos=fmt(center),mass='0',contype='8',conaffinity='16')
# The narrow fixed bridge must carry wheel contact, matching its authored surface.
for lift in lifts:
 node=root.find(f'.//body[@name="{lift["hull"]}"]')
 E.SubElement(node,'geom',name=lift['name']+'_boarding_bridge',type='box',size='1.55 .135 .03',pos=fmt([0,lift['side']*12.05,7.42-10.]),mass='0',contype='8',conaffinity='16',friction='.9 .005 .0001')
# New authored metal/rotor volumes update their owning physical bodies and MJCF.
import gzip
assembly=json.loads(gzip.decompress((O/'source/assembly.json.gz').read_bytes()))
for item in assembly.get('mechanical_mass_additions',[]):
 body=next(b for b in s['bodies'] if b['name']==item['body']);mass=float(item['mass_kg'])
 datum=np.array(assembly['groups'][item['body']]);extra=np.array(item['center_source_m'])-datum
 # Body frame in the native source differs from visual source pivot on hulls.
 if item['body'] in b['groups']:
  extra=np.array(item['center_source_m'])-np.array(b['groups'][item['body']]['neutral_body_position_source_m'])
 old=body['mass'];oldcom=np.array(body['com']);com=(old*oldcom+mass*extra)/(old+mass)
 def shift(d):return np.dot(d,d)-d*d
 body['inertia']=(np.array(body['inertia'])+np.array(item['inertia_source_diag_kg_m2'])+old*shift(oldcom-com)+mass*shift(extra-com)).tolist();body['mass']+=mass;body['com']=com.tolist()
 node=root.find(f'.//body[@name="{item["body"]}"]/inertial')
 assert node is not None,item['body']
 node.set('mass',str(body['mass']));node.set('pos',fmt(com));node.set('diaginertia',fmt(body['inertia']))
 mass_records.append(item)
from equipment_physics import compile as compile_equipment
compile_equipment(assembly['equipment_actuation'],assembly,s,b,root)
params['equipment']=s['contact']['equipment']
from habitable_physics import compile as compile_habitable
compile_habitable(assembly,s,b,params,root,O)
from cockpit_controls import compile as compile_cockpit
compile_cockpit(assembly,s,b,params,root,O)
s['config']['total_mass_kg']=sum(x['mass'] for x in s['bodies']);s['contact']['total_mass_kg']=s['config']['total_mass_kg'];params['total_mass_kg']=s['config']['total_mass_kg'];params['boarding_lifts']=lifts
s['contact']['boarding_controller']=dict(force_cap_N=60000,kp=80000,kd=14000,slide_speed_m_s=.55,vertical_speed_m_s=.7,park_speed_max_m_s=.08,ground_platform_height_m=.245)
params['boarding_controller']=s['contact']['boarding_controller']
b.update(native_blend=str(O/'source/Sainiverse_v0.1.blend'),glb=str(O/'assets/Sainiverse_v0.1.glb'),expected_groups=build['groups'],expected_meshes=build['render_meshes'],style=str(O/'style.json'),scope='Sainiverse_v0.1 authored skin and native movable robot boarding lifts. Same finite-force suspension and traction; manually controlled candidate. Provisional mass, not hardware qualification.')
# Keep original interior contacts/figures by source path, with compatible assets
# copied alongside the new GLB. Native access proxy data itself is unchanged.
for path,val in [(O/'physics/native_spec.json',s),(O/'physics/parameters.json',params),(O/'bindings.json',b),(O/'reports/mass_changes.json',dict(additions=mass_records,moving_lift_mass_kg=sum(sum(x['masses']) for x in lifts),total_mass_kg=s['config']['total_mass_kg'],scope='Provisional closed-box web and mechanism allocation; no detailed hardware load certification.'))]:path.write_text(json.dumps(val,indent=2)+'\n')
E.indent(root);xml.write(O/'physics/suspended.xml',encoding='unicode')
# XML references original collision meshes relative to physics folder.
for p in (A/'physics').iterdir():
 if p.is_dir():shutil.copytree(p,O/'physics'/p.name,dirs_exist_ok=True)
print('Native bodies',len(s['bodies']),'joints',len(s['joints']),'mass',s['config']['total_mass_kg'])
