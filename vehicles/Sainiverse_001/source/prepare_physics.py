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
# Strengthened deck collision boxes for native review/player and MuJoCo.
for hull in ['front','rear','tail']:
 node=root.find(f'.//body[@name="{hull}"]')
 for i,(center,size) in enumerate([([0,0,-3.05],[34,24.3,1.]),([-9.32,0,-3.05],[15.36,27,1.]),([9.32,0,-3.05],[15.36,27,1.])]):
  E.SubElement(node,'geom',name=hull+f'_boarding_deck_{i}',type='box',size=fmt(np.array(size)/2),pos=fmt(center),mass='0',contype='8',conaffinity='16')
s['config']['total_mass_kg']=sum(x['mass'] for x in s['bodies']);s['contact']['total_mass_kg']=s['config']['total_mass_kg'];params['total_mass_kg']=s['config']['total_mass_kg'];params['boarding_lifts']=lifts
s['contact']['boarding_controller']=dict(force_cap_N=60000,kp=80000,kd=14000,slide_speed_m_s=.55,vertical_speed_m_s=.7,park_speed_max_m_s=.08,ground_platform_height_m=.245)
params['boarding_controller']=s['contact']['boarding_controller']
b.update(native_blend=str(O/'source/Sainiverse_001.blend'),glb=str(O/'assets/sainiverse001.glb'),expected_groups=build['groups'],expected_meshes=build['render_meshes'],style=str(O/'style.json'),scope='Sainiverse 001 authored skin and native movable robot boarding lifts. Same finite-force suspension and traction; manually controlled candidate. Provisional mass, not hardware qualification.')
# Keep original interior contacts/figures by source path, with compatible assets
# copied alongside the new GLB. Native access proxy data itself is unchanged.
for path,val in [(O/'physics/native_spec.json',s),(O/'physics/parameters.json',params),(O/'bindings.json',b),(O/'reports/mass_changes.json',dict(additions=mass_records,moving_lift_mass_kg=sum(sum(x['masses']) for x in lifts),total_mass_kg=s['config']['total_mass_kg'],scope='Provisional closed-box web and mechanism allocation; no detailed hardware load certification.'))]:path.write_text(json.dumps(val,indent=2)+'\n')
E.indent(root);xml.write(O/'physics/suspended.xml',encoding='unicode')
# XML references original collision meshes relative to physics folder.
for p in (A/'physics').iterdir():
 if p.is_dir():shutil.copytree(p,O/'physics'/p.name,dirs_exist_ok=True)
print('Native bodies',len(s['bodies']),'joints',len(s['joints']),'mass',s['config']['total_mass_kg'])
