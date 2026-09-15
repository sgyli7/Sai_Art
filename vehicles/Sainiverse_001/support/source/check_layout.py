"""Verify layout using authored vertices, native MuJoCo anchors and contact sites."""
from pathlib import Path
from collections import defaultdict
import gzip,json,hashlib
import numpy as np
import mujoco
ROOT=Path(__file__).resolve().parents[1]
def read(path):
 with gzip.open(path,'rt') as f:return json.load(f)
new=read(ROOT/'source/assembly.json.gz');old=read(ROOT/'revisions/r010/source/assembly.json.gz')
cfg=json.loads((ROOT/'assets/physics.json').read_text())
crane=json.loads((ROOT/'reports/crane_pose_validation.json').read_text())
assert crane['passed'] and crane['source_sha256']==hashlib.sha256((ROOT/'source/assembly.json.gz').read_bytes()).hexdigest()
bogie=json.loads((ROOT/'reports/bogie_structure_validation.json').read_text())
assert bogie['passed'] and bogie['source_sha256']==hashlib.sha256((ROOT/'source/assembly.json.gz').read_bytes()).hexdigest()
changed_bogies=set(bogie['changed_existing_names'])
def keyed(recipe):
 counts=defaultdict(int);result={}
 for p in recipe['parts']:
  k=(p['group'],p['name'].split('_',1)[1]);index=counts[k];counts[k]+=1;result[(*k,index)]=p
 return result
n,o=keyed(new),keyed(old)
shifted_static={'side_service_flange','side_service_cap','steering_collar','cast_yoke','yoke_service_frame','yoke_service_cover','yoke_cover_bolt','suspension_shoulder','paint_support_number'}
changed={'hitch_ring','coupling_link'};counts=defaultdict(int)
for key,p in o.items():
 q=n[key];name=key[1];hull=key[0].split('_')[0]
 if q['name'] in changed_bogies:
  counts['separately_verified_bogie']+=1;continue
 if q.get('assembly','').startswith('crane_'):
  counts['separately_verified_crane']+=1;continue
 if name in changed:continue
 for field in ['group','material','motion']:assert p[field]==q[field],(key,field)
 a=np.asarray(p['vertices']);b=np.asarray(q['vertices'])
 if q.get('assembly')=='reservoir_bank':
  b=b.copy();cx=new['groups']['rear'][0];x=b[:,0]-cx;y=b[:,1].copy();b[:,0]=cx+y;b[:,1]=-x

 delta=np.array(new['groups'][hull])-old['groups'][hull]
 if name.startswith('tank_side_rack') or name=='rack_column':delta[1]+=.4*np.sign(a[:,1].mean())

 if '_bogie_' in key[0]:delta=np.array(new['groups'][key[0]])-old['groups'][key[0]]
 elif name in shifted_static:
  old_local_x=a[:,0].mean()-old['groups'][hull][0]
  delta[0]+=-1 if old_local_x>0 else 1
 # Compare actual shape independent of vertex/face order; manifold extrusion may reorder.
 def triangles(vertices,faces):
  t=vertices[np.asarray(faces)];t=np.round(t,6)
  t=np.array([v[np.lexsort(v.T[::-1])] for v in t]).reshape(-1,9)
  return t[np.lexsort(t.T[::-1])]
 assert a.shape==b.shape,(key,a.shape,b.shape)
 assert np.allclose(triangles(a+delta,p['faces']),triangles(b,q['faces']),atol=2e-6,rtol=0),key
 counts['translated' if np.any(delta) else 'unchanged']+=1
added=set(n)-set(o);added={k for k in added if n[k]['name'] not in bogie['added_names']};assert {k[1] for k in added}=={'coupling_crosshead','rear_drawbar','coupling_deck_mount'} and len(added)==7
rows=sorted({float(pos[0]) for name,pos in new['groups'].items() if '_bogie_' in name})
assert np.allclose(rows,[-52.5,-31.5,-10.5,10.5]) and np.allclose(np.diff(rows),21)
# Every reduced contact rectangle must lie beneath its actual bogie envelope.
patches=np.asarray(cfg['patch_offsets']);contact_checks=[]
for hi,hull in enumerate(['front','rear']):
 for name,pivot in new['groups'].items():
  if not name.startswith(hull+'_bogie_'):continue
  local=np.array(pivot)-[cfg['hull_centers_x'][hi],0,0]
  chosen=patches[(abs(patches[:,0]-local[0])<4)&(abs(patches[:,1]-local[1])<2)]
  assert len(chosen)==4
  verts=np.vstack([p['vertices'] for p in new['parts'] if p['group']==name and p['name'].endswith('_track_link')])
  world=chosen+[cfg['hull_centers_x'][hi],0,cfg['com_z']]
  assert np.all(world[:,:2]>=verts.min(axis=0)[:2]) and np.all(world[:,:2]<=verts.max(axis=0)[:2])
  contact_checks.append(name)
m=mujoco.MjModel.from_xml_path(str(ROOT/'assets/vehicle.xml'));d=mujoco.MjData(m);mujoco.mj_forward(m,d)
j=m.joint('hitch').id;expected=np.array([cfg['hitch_x'],0,cfg['hitch_z']]);assert np.allclose(d.xanchor[j],expected)
for hull in ['front','rear']:
 names=['hitch_ring'] if hull=='front' else ['rear_drawbar']
 for p in new['parts']:
  if p['group']!=hull or p['name'].split('_',1)[1] not in names:continue
  v=np.array(p['vertices']);assert np.all(expected>=v.min(axis=0)-1e-6) and np.all(expected<=v.max(axis=0)+1e-6)
# The four roots overlap the deck and their respective drawbars in actual solid volume.
import trimesh as tm
def overlap_volume(a,b):
 cut=tm.boolean.intersection([a,b],engine='manifold')
 return float(cut.volume) if len(cut.faces) else 0.
contact_volumes=[]
for hull in ['front','rear']:
 parts=[p for p in new['parts'] if p['group']==hull]
 def solid(p):return tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
 deck=solid(next(p for p in parts if p['name'].endswith('_'+hull+'_deck')))
 bars=[solid(p) for p in parts if p['name'].split('_',1)[1]==('coupling_link' if hull=='front' else 'rear_drawbar')]
 for p in parts:
  if not p['name'].endswith('_coupling_deck_mount'):continue
  mount=solid(p);deck_volume=overlap_volume(mount,deck)
  link_volume=max(overlap_volume(mount,b) for b in bars)
  assert deck_volume>.05 and link_volume>.02,(p['name'],deck_volume,link_volume)
  contact_volumes.append(dict(name=p['name'],deck_overlap_m3=deck_volume,link_overlap_m3=link_volume))
assert len(contact_volumes)==4
report=dict(passed=True,connection_contacts=contact_volumes,source_sha256=hashlib.sha256((ROOT/'source/assembly.json.gz').read_bytes()).hexdigest(),parts=counts,reshaped_coupling_parts=3,added_coupling_parts=7,bogie_rows_x_m=rows,contact_groups=contact_checks,mujoco_hitch_anchor=d.xanchor[j].tolist(),scope='R010 triangle surfaces retained with declared rigid translations except coupling, with separately verified transverse bank rotation and 0.4 m outward rack shift; crane changes independently checked in crane_pose_validation.json. Actual contact rectangles and native anchor match visual layout. No load qualification or exact original metric dimensions.')
(ROOT/'reports/layout_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
