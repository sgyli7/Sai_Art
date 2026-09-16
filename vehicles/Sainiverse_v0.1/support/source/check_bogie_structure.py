"""Check actual new bogie solids, connected wheel supports and belt swept clearance."""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
import trimesh as tm
import manifold3d as mf
from scipy.spatial import ConvexHull,cKDTree
ROOT=Path(__file__).resolve().parents[1]
def read(p):
 with gzip.open(p,'rt') as f:return json.load(f)
r=read(ROOT/'source/assembly.json.gz');old=read(ROOT/'revisions/r013/source/assembly.json.gz')
assert r['groups']==old['groups']
changed=[];added=r['parts'][len(old['parts']):]
allowed={'bogie_road_arm','bogie_end_housing','bogie_end_hatch_seal','bogie_end_hatch_leaf','bogie_end_hatch_handle'}
for p,q in zip(old['parts'],r['parts']):
 assert p['name']==q['name'] and p['group']==q['group']
 if q.get('assembly')=='bogie_structure':
  assert q['name'].endswith('_track_inner_frame') and '_bogie_' in q['group'];changed.append(q['name']);continue
 for key in ['vertices','faces','material','motion','surface_paint','assembly']:assert p[key]==q[key],(p['name'],key)
assert len(changed)==32 and len(added)==112
assert {p['name'].split('_',1)[1] for p in added}==allowed
assert all(p.get('assembly')=='bogie_structure' and p['motion']['kind']=='static' and '_bogie_' in p['group'] for p in added)
for name in ['assets/physics.json','training/policy.json','godot/runtime.gd','godot/belt.gdshader','assets/running_gear.json']:
 assert (ROOT/name).read_bytes()==(ROOT/'revisions/r013'/name).read_bytes(),name

def local(p,pivot):
 v=np.array(p['vertices'])-[pivot[0],pivot[1],0]
 return tm.Trimesh(vertices=v,faces=p['faces'],process=False)
def overlap(a,b):
 if np.any(np.minimum(a.bounds[1],b.bounds[1])-np.maximum(a.bounds[0],b.bounds[0])<=1e-8):return 0.
 c=tm.boolean.intersection([a,b],engine='manifold');return float(c.volume) if len(c.faces) else 0.
def project(v):
 xz=np.unique(np.round(v[:,[0,2]],9),axis=0);return mf.CrossSection([xz[ConvexHull(xz).vertices]],mf.FillRule.EvenOdd)
rows=[];representative=None;baseline=[];max_copy_delta=0.
for group,pivot in r['groups'].items():
 if '_bogie_' not in group:continue
 items=[(p,local(p,pivot)) for p in r['parts'] if p['group']==group]
 owned=[(p,m) for p,m in items if p.get('assembly')=='bogie_structure']
 assert len(owned)==18
 if representative is None:representative=items;baseline=owned
 else:
  for (p,m),(q,n) in zip(owned,baseline):
   assert p['name'].split('_',1)[1]==q['name'].split('_',1)[1]
   distance,index=cKDTree(n.vertices).query(m.vertices);max_copy_delta=max(max_copy_delta,float(distance.max()))
   assert distance.max()<1e-5 and len(np.unique(index))==len(n.vertices),(p['name'],float(distance.max()))
   a=np.sort(index[m.faces],axis=1);b=np.sort(n.faces,axis=1)
   assert np.array_equal(a[np.lexsort(a.T)],b[np.lexsort(b.T)]),p['name']
 for p,m in owned:assert m.is_volume and m.volume>0,p['name']
 frames=[m for p,m in items if p['name'].endswith('_track_inner_frame')]
 assert all(m.convex_hull.volume-m.volume>.1 for m in frames)
 platform=next(m for p,m in items if p['name'].endswith('_bogie_center_platform'))
 housings=[m for p,m in items if p['name'].endswith('_bogie_end_housing')]
 for m in housings:
  assert m.bounds[0,2]>=1.29 and abs(m.bounds[:,1]).max()<=.721
  assert overlap(m,platform)>.1
 arms=[m for p,m in items if p['name'].endswith('_bogie_road_arm')]
 assert len(arms)==6 and all(max(overlap(a,f) for f in frames)>1e-5 for a in arms)
 axles=[m for p,m in items if p['name'].endswith('_wheel_axle')]
 assert len(axles)==10
 axle_contacts=[max(overlap(a,b) for b in frames+arms) for a in axles]
 assert min(axle_contacts)>1e-5,(group,axle_contacts)
 rows.append(dict(group=group,verified_parts=len(owned),minimum_axle_support_overlap_m3=min(axle_contacts),end_housing_platform_overlaps_m3=[overlap(m,platform) for m in housings]))
# All eight structures are proven rigid copies above. Check their actual local
# solids against the complete shader path, not just the displayed link phases.
owned=[(p,m) for p,m in representative if p.get('assembly')=='bogie_structure']
moving=[(p,m) for p,m in representative if p['motion']['kind']!='static']
wheel_gap=min(max(a.bounds[0,1]-b.bounds[1,1],b.bounds[0,1]-a.bounds[1,1]) for _,a in owned for p,b in moving if p['motion']['kind']=='wheel')
assert wheel_gap>0,'New support interferes with rotating wheel depth'
gear=json.loads((ROOT/'assets/running_gear.json').read_text());path=np.array(gear['path_x_z']);closed=np.vstack([path,path[:1]]);delta=np.diff(closed,axis=0);lengths=np.linalg.norm(delta,axis=1);cumulative=np.r_[0,np.cumsum(lengths)]
templates={}
for p,m in moving:
 if p['motion']['kind']!='belt':continue
 k=(p['name'].split('_',1)[1],round(m.vertices[:,1].mean(),5))
 if k not in templates:templates[k]=(p,m)
max_area=0.;sweep_checks=0
for _,(p,m) in templates.items():
 phase=p['motion']['phase'];k=min(len(lengths)-1,int(np.searchsorted(cumulative,phase,side='right')-1));t=delta[k]/lengths[k];n=np.array([-t[1],t[0]]);q=closed[k]+t*(phase-cumulative[k]);v=m.vertices[:,[0,2]]-q;uv=np.column_stack([v@t,v@n])
 targets=[(p,a,project(a.vertices).offset(1e-5)) for p,a in owned if min(a.bounds[1,1],m.bounds[1,1])-max(a.bounds[0,1],m.bounds[0,1])>0]
 for k in range(len(lengths)):
  t=delta[k]/lengths[k];n=np.array([-t[1],t[0]]);offset=uv[:,0,None]*t+uv[:,1,None]*n
  pts=np.vstack([closed[k]+offset,closed[k+1]+offset]);sweep=mf.CrossSection([pts[ConvexHull(pts).vertices]],mf.FillRule.EvenOdd)
  for target,a,solid in targets:
   area=float((sweep^solid).area());max_area=max(max_area,area);sweep_checks+=1
   assert area<1e-8,(p['name'],target['name'],k,area)
report=dict(passed=True,source_sha256=hashlib.sha256((ROOT/'source/assembly.json.gz').read_bytes()).hexdigest(),changed_existing_names=changed,added_names=[p['name'] for p in added],unchanged_existing_parts=len(old['parts'])-len(changed),bogies=rows,minimum_new_structure_to_rotating_wheel_y_gap_m=wheel_gap,conservative_belt_sweep_projection_checks=sweep_checks,maximum_projected_overlap_m2=max_area,maximum_rigid_copy_vertex_error_m=max_copy_delta,sweep_clearance_test_inflation_m=1e-5,physics_policy_runtime_shader_unchanged=True,scope='Static bogie geometry reconstructed from refs1/2/4; full piecewise-linear visual belt-path clearance and positive support intersections. No dynamic suspension, manufacturing tolerances, stress or original-CAD dimensional claim.')
(ROOT/'reports/bogie_structure_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['changed_existing_names','added_names','bogies']},indent=2))
