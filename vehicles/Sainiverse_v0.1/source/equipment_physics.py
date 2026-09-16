"""Compile source mechanism bodies into matching native and MJCF specifications."""
import numpy as np
from scipy.spatial import ConvexHull
import xml.etree.ElementTree as E

def compile(rig,a,s,b,root):
 fmt=lambda x:' '.join(str(float(v)) for v in x)
 def shift(d):return np.dot(d,d)-d*d
 # Remove the exact same provisional mass/inertia allocation from each hull.
 for hull in ['front','rear','tail']:
  items=[x for x in rig['bodies'] if x['hull']==hull];parent=next(x for x in s['bodies'] if x['name']==hull)
  datum=np.array(b['groups'][hull]['neutral_body_position_source_m']);old=float(parent['mass']);oldcom=np.array(parent['com']);mass=sum(x['mass'] for x in items)
  centers=[np.array(x['pivot'])+x['com']-datum for x in items];new=(old*oldcom-sum((x['mass']*c for x,c in zip(items,centers)),np.zeros(3)))/(old-mass)
  inertia=np.array(parent['inertia'])-sum((np.array(x['inertia'])+x['mass']*shift(c-oldcom) for x,c in zip(items,centers)),np.zeros(3))-(old-mass)*shift(new-oldcom)
  assert old>mass and np.all(inertia>0),(hull,mass,inertia)
  parent.update(mass=old-mass,com=new.tolist(),inertia=inertia.tolist());node=root.find(f'.//body[@name="{hull}"]/inertial');node.set('mass',str(old-mass));node.set('pos',fmt(new));node.set('diaginertia',fmt(inertia))
 joints={x['body']:x for x in rig['joints']};positions={x['name']:np.array(x['position']) for x in s['bodies']}
 for item in rig['bodies']:
  name=item['name'];hull=item['hull'];pivot=np.array(item['pivot']);pos=pivot+positions[hull]-np.array(b['groups'][hull]['neutral_body_position_source_m']);positions[name]=pos
  s['bodies'].append({'name':name,'mass':item['mass'],'com':item['com'],'inertia':item['inertia'],'position':pos.tolist()})
  b['groups'][name]={'pivot_source_m':pivot.tolist(),'neutral_body_position_source_m':pivot.tolist()}
  j=joints.get(name)
  if j:
   parent=j['parent'];node=E.SubElement(root.find(f'.//body[@name="{parent}"]'),'body',name=name,pos=fmt(pos-positions[parent]))
   E.SubElement(node,'joint',name=name,type=j['kind'],axis=fmt(j['axis']),range=fmt(j['limits']),limited='true',armature='100',damping='0')
   s['joints'].append(dict(name=name,body=name,parent=parent,anchor=pos.tolist(),axis=j['axis'],kind=j['kind'],limits=j['limits'],stiffness=0,damping=0,springref=0,equipment=True))
   E.SubElement(root.find('actuator'),'motor',name=name,joint=name,ctrllimited='true',ctrlrange='-12000000 12000000' if name=='receiver_fold' else '-5000000 5000000')
  else:
   node=E.SubElement(root.find('worldbody'),'body',name=name,pos=fmt(pos));E.SubElement(node,'freejoint',name=name+'_free')
  E.SubElement(node,'inertial',mass=str(item['mass']),pos=fmt(item['com']),diaginertia=fmt(item['inertia']))
  points=np.concatenate([p['vertices'] for p in a['parts'] if p['group']==name and not p['material'].startswith('rig_')]);lo=points.min(0)-pivot;hi=points.max(0)-pivot
  if name=='receiver_fold':
   vertices=(points-pivot)[ConvexHull(points).vertices]
   item['collision_convex']=vertices.tolist()
   asset=root.find('asset')
   if asset is None:asset=E.SubElement(root,'asset')
   E.SubElement(asset,'mesh',name='receiver_fold_contact_mesh',vertex=fmt(vertices.ravel()))
   E.SubElement(node,'geom',name=name+'_contact',type='mesh',mesh='receiver_fold_contact_mesh',mass='0',contype='64',conaffinity='9',friction='.7 .005 .0001')
   continue
  item['collision_box']={'center':((lo+hi)/2).tolist(),'size':(hi-lo).tolist()}
  E.SubElement(node,'geom',name=name+'_contact',type='box',pos=fmt((lo+hi)/2),size=fmt((hi-lo)/2),mass='0',contype='64',conaffinity='9',friction='.7 .005 .0001')
 # Conservative loaded-cargo envelopes leave side and end walkways clear.
 rig['cargo_colliders']=[]
 for hull,tag in [('rear','container_'),('tail','sealed_reservoir')]:
  ps=[p for p in a['parts'] if p['group']==hull and tag in p['name']]
  if not ps:continue
  v=np.concatenate([p['vertices'] for p in ps]);lo=v.min(0);hi=v.max(0);center=(lo+hi)/2-np.array(b['groups'][hull]['neutral_body_position_source_m'])
  box={'hull':hull,'center':center.tolist(),'size':(hi-lo).tolist()};rig['cargo_colliders'].append(box)
  E.SubElement(root.find(f'.//body[@name="{hull}"]'),'geom',name=hull+'_cargo_envelope',type='box',pos=fmt(center),size=fmt((hi-lo)/2),mass='0',contype='8',conaffinity='64')
 s['contact']['equipment']=rig
