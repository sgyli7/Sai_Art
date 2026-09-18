"""Rebuild mounted room contacts in both native and MJCF from r032 authored geometry."""
import json
import numpy as np
import trimesh as tm
import xml.etree.ElementTree as E
from mechanical_revision import mesh,boxmesh
from convex_csg import subtract_many

def compile(a,s,b,params,root,O):
 h=a['habitable_revision'];obsolete=set(h['obsolete_door_groups']);front=root.find('.//body[@name="front"]');asset=root.find('asset')
 s['bodies']=[q for q in s['bodies'] if q['name'] not in obsolete]
 s['joints']=[q for q in s['joints'] if q['body'] not in obsolete]
 for name in obsolete:
  b['groups'].pop(name,None)
  node=front.find(f'body[@name="{name}"]')
  if node is not None:front.remove(node)
 for container in [root.find('actuator'),root.find('equality')]:
  if container is None:continue
  for node in list(container):
   if any(node.get(k) in obsolete for k in ['joint','joint1','joint2','body1','body2']):container.remove(node)
 access=s['contact']['access'];access['doors']=[q for q in access['doors'] if q['name'] not in obsolete];params['access']=access
 c=s['contact']['interior'];old=c['shapes'];shapes=[]
 aftcut=boxmesh([16.5,0,12.57],[2.0,2.20,2.50])
 for q in old:
  n=q['name']
  if n.startswith('wall_piece_'):
   m=tm.convex.convex_hull(q['vertices_source_m'])
   for i,p in enumerate(subtract_many([m],[aftcut])):shapes.append(dict(name=n+f'_r032_{i}',body='front',type='convex',vertices_source_m=p.vertices.tolist()))
  elif not n.startswith('r023_'):shapes.append(q)
 # Opaque infill round four new windows; separate glazing carries actual contact.
 for side in [-1,1]:
  for x in [23.15,25.05]:
   for i,p in enumerate(subtract_many([boxmesh([x,side*3.4,12.84],[1.48,.21,3.05])],[boxmesh([x,side*3.4,13.65],[1.12,.8,1.1])])):
    shapes.append(dict(name=f'window_infill_{side}_{x}_{i}',body='front',type='convex',vertices_source_m=p.vertices.tolist()))
 shapes+=h['contacts']
 # Partition lounge convex envelope with the same occupied core and passage cuts.
 rest=mesh(next(p for p in a['parts'] if p['name'].endswith('_fore_service_shell')))
 cuts=[boxmesh([9,0,10.28],[9.58,15.58,5.42]),boxmesh([14.1,0,12.52],[.9,2,2.4]),boxmesh([12.2,0,13.55],[4.5,2.25,1.8])]
 for side in [-1,1]:
  for x in [5.5,8.4,11.3]:cuts.append(boxmesh([x,side*8,11.78],[1.18,.90,.72]))
 for i,p in enumerate(subtract_many([rest.convex_hull],cuts)):
  shapes.append(dict(name=f'lounge_shell_{i}',body='front',type='convex',vertices_source_m=p.vertices.tolist()))
 for p in a['parts']:
  if p['name'].endswith('_equipment_window_glass'):
   shapes.append(dict(name=p['name'],body='front',type='convex',vertices_source_m=mesh(p).convex_hull.vertices.tolist()))
 from contact_primitives import compact
 shapes,compaction=compact(shapes)
 (O/'reports/contact_primitive_compaction.json').write_text(json.dumps(compaction,indent=2))
 c['shapes']=shapes;c['scope']='Mounted r032 room floor, fixtures, stairs, partitioned lounge walls and original partitioned cockpit walls with aft passage. Robot stair policy not validated.'
 params['interior']=c
 for q in list(front.findall('geom')):
  if q.get('name','').startswith(('interior_','access_')):front.remove(q)
 fmt=lambda x:' '.join(format(float(v),'.10g') for v in x)
 datum=np.array(c['datum_source_m'])
 for i,q in enumerate(shapes):
  attrs=dict(name=f'interior_r032_{i}',mass='0',group='4',contype='8',conaffinity='48',friction='.9 .002 .0002')
  if q['type']=='box':attrs.update(type='box',pos=fmt(np.array(q['center_source_m'])-datum),size=fmt(np.array(q['size_m'])/2))
  else:
   name=f'r032_room_mesh_{i}';E.SubElement(asset,'mesh',name=name,vertex=fmt((np.array(q['vertices_source_m'])-datum).ravel()));attrs.update(type='mesh',mesh=name)
  E.SubElement(front,'geom',**attrs)
 (O/'physics/interior_contacts.json').write_text(json.dumps(c,indent=2))
 accessdoc=json.loads((O/'source/access.json').read_text());accessdoc['doors']=access['doors'];accessdoc['wall_contacts']=[q for q in shapes if q['name'].startswith(('wall_piece_','window_infill','lounge_shell'))];(O/'source/access.json').write_text(json.dumps(accessdoc,indent=2))
 b.update(interior_manifest=str(O/'source/interior.json'),interior_contacts=str(O/'physics/interior_contacts.json'),access_manifest=str(O/'source/access.json'))
 print('r032 contact shapes',len(shapes),'active doors',len(access['doors']))
