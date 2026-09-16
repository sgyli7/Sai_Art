"""Actual crane placement, rigid slew pose and preservation against r012."""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def read(path):
 with gzip.open(path,'rt') as f:return json.load(f)
r=read(ROOT/'source/assembly.json.gz');old=read(ROOT/'revisions/r012/source/assembly.json.gz')
bogie=json.loads((ROOT/'reports/bogie_structure_validation.json').read_text())
assert bogie['passed'] and bogie['source_sha256']==hashlib.sha256((ROOT/'source/assembly.json.gz').read_bytes()).hexdigest()
changed_bogies=set(bogie['changed_existing_names'])
assert len(r['parts'])==len(old['parts'])+len(bogie['added_names']) and r['groups']==old['groups']
counts={'fixed_crane':0,'slewed_crane':0,'unchanged':0,'separately_verified_bogie':0};centers=[[-56.7,-11,0],[-27.3,-11,0]]
for p,q in zip(old['parts'],r['parts']):
 if q['name'] in changed_bogies:
  counts['separately_verified_bogie']+=1;continue
 for key in ['name','group','material','faces','motion']:assert p[key]==q[key],(p['name'],key)
 assembly=q.get('assembly','');a=np.array(p['vertices']);b=np.array(q['vertices']);name=q['name'].split('_',1)[1]
 if not assembly.startswith('crane_'):
  assert np.array_equal(a,b),q['name'];counts['unchanged']+=1;continue
 i=int(assembly.split('_')[1]);expected=a+[0,-22 if i else 0,0]
 if assembly.endswith('_upper'):
  angle=np.pi/2*(1 if i else -1);c,s=np.cos(angle),np.sin(angle);rot=np.array([[c,-s,0],[s,c,0],[0,0,1]])
  expected=(expected-centers[i])@rot.T+centers[i];counts['slewed_crane']+=1
  if q.get('surface_paint'):
   normal=rot@np.array([0,p['surface_paint']['paint_side'],0]);assert np.allclose(normal,q['surface_paint']['paint_normal'])
   center=(np.array(p['surface_paint']['paint_center'])+[0,-22 if i else 0,0]-centers[i])@rot.T+centers[i]
   assert np.allclose(center,q['surface_paint']['paint_center'])
 else:
  counts['fixed_crane']+=1
  if name=='crane_pedestal_window' or (name=='crane_pedestal_handle' and a[:,2].mean()<10):
   old_y=-11 if i==0 else 11;side=np.sign(a[:,1].mean()-old_y)
   desired=-11+side*(1.735+(.055 if name.endswith('window') else .06))
   expected[:,1]=a[:,1]+desired-a[:,1].mean()
  if i and name=='crane_column_cover':expected[:,1]-=2.22
  if i and name.startswith('service_ladder_'):expected[:,1]-=3.76
 assert np.allclose(expected,b,atol=1e-10,rtol=0),q['name']
rows=[]
for i,center in enumerate(centers):
 upper=[p for p in r['parts'] if p.get('assembly')==f'crane_{i}_upper']
 fixed=[p for p in r['parts'] if p.get('assembly')==f'crane_{i}_fixed']
 def vertices(parts,name):return np.vstack([p['vertices'] for p in parts if p['name'].endswith('_'+name)])
 head=vertices(upper,'crane_turning_head');hc=(head.min(0)+head.max(0))/2
 pedestal=vertices(fixed,'crane_pedestal');pc=(pedestal.min(0)+pedestal.max(0))/2
 assert np.allclose(hc[:2],center[:2]) and np.allclose(pc[:2],center[:2])
 tip=vertices(upper,'crane_tip_cheek');tc=(tip.min(0)+tip.max(0))/2;delta=tc-hc
 assert abs(delta[0])<1e-8 and 11<delta[1]<11.7
 neck=vertices(fixed,'crane_neck');assert head[:,2].min()<neck[:,2].max()
 for p in fixed:
  name=p['name'].split('_',1)[1];v=np.array(p['vertices'])
  if name=='crane_pedestal_window' or (name=='crane_pedestal_handle' and v[:,2].mean()<10):
   side=np.sign(v[:,1].mean()-center[1]);out=(v[:,1]-center[1])*side
   assert out.max()>1.8 and out.min()<1.775,p['name']
 rows.append(dict(index=i,pedestal_center_m=pc.tolist(),slew_center_m=hc.tolist(),tip_center_m=tc.tolist(),boom_heading_degrees=float(np.degrees(np.arctan2(delta[1],delta[0]))),fixed_parts=len(fixed),upper_parts=len(upper)))
assert len(rows)==2
for name in ['assets/physics.json','training/policy.json','godot/runtime.gd']:
 assert (ROOT/name).read_bytes()==(ROOT/'revisions/r012'/name).read_bytes()
report=dict(passed=True,source_sha256=hashlib.sha256((ROOT/'source/assembly.json.gz').read_bytes()).hexdigest(),parts=counts,cranes=rows,physics_policy_runtime_unchanged=True,scope='Static transport pose based on refs2/5. Complete upper assemblies rotate with rigging and paint; front pedestal moves to the flat-cover edge. Bogie changes separately verified in bogie_structure_validation.json. No lifted load, motor actuation, sweep or structural rating.')
(ROOT/'reports/crane_pose_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
