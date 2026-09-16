"""Source-space regression signals for the user's close-range defects."""
from pathlib import Path
import gzip,json,argparse
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
O=Path(__file__).resolve().parents[1]
a=json.loads(gzip.decompress((O/'source/assembly.json.gz').read_bytes()))
fail=[];details={}
# Pedestal windows may not straddle the top edge of opaque service hatches.
windows=[p for p in a['parts'] if p['name'].endswith('_crane_pedestal_window')];hatches=[p for p in a['parts'] if p['name'].endswith('_crane_pedestal_hatch')]
for p in windows:
 v=np.array(p['vertices']);lo,hi=v.min(0),v.max(0)
 for q in hatches:
  w=np.array(q['vertices']);l,h=w.min(0),w.max(0)
  if p['group']==q['group'] and abs(v[:,1].mean()-w[:,1].mean())<.2 and min(hi[0],h[0])-max(lo[0],l[0])>.01 and lo[2]<h[2]<hi[2]:fail.append('window straddles hatch '+p['name'])
if any('wiper' in p['name'] for p in a['parts']):fail.append('windscreen wipers still present')
for p in a['parts']:
 if p['name'].endswith('_workbench_top'):
  height=np.max(np.array(p['vertices'])[:,2])-11.35
  if height<.70:fail.append('workbench height %.3f m'%height)
# Exact coplanar source facets near front-right lift: different parts, >1 cm².
planes={}
for p in a['parts']:
 g=p['group'];hull=g if g in ['front','rear','tail'] else g.split('_')[1] if g.startswith('lift_') else None
 if hull is None:continue
 cx=a['groups'][hull][0]
 v=np.array(p['vertices']);lo,hi=v.min(0),v.max(0)
 if hi[0]<cx-2 or lo[0]>cx+2 or (hi[1]<11.5 and lo[1]>-11.5) or hi[2]<7.2 or lo[2]>11.3:continue
 fs=v[np.array(p['faces'])]
 for axis in range(3):
  ij=[i for i in range(3) if i!=axis]
  flat=np.ptp(fs[:,:,axis],axis=1)<1e-6
  for tri in fs[flat]:
   if axis==2 and not 7.2<tri[0,axis]<7.6:continue
   poly=Polygon(tri[:,ij]);
   if poly.area>1e-6:planes.setdefault((axis,round(float(tri[0,axis]),5),int(np.sign(np.cross(tri[1]-tri[0],tri[2]-tri[0])[axis]))),{}).setdefault(p['name'],[]).append(poly)
pairs=[]
for key,parts in planes.items():
 rows=[(n,unary_union(polys)) for n,polys in parts.items()]
 for i,(n,p) in enumerate(rows):
  for m,q in rows[i+1:]:
   area=p.intersection(q).area
   if area>1e-4:pairs.append(dict(a=n,b=m,axis=key[0],plane=key[1],area=area))
details['lift_coplanar_pairs']=pairs
fail.extend('lift coplanar '+p['a']+' / '+p['b'] for p in pairs)
manifest=O/'source/habitable.json'
if not manifest.exists():fail.append('no authored cabin/lounge indoor connection')
# Fixed rails and moving arms must overlap at full horizontal stroke.
rails=[p for p in a['parts'] if p['name'].endswith('_fixed_slide_cassette')]
arms=[p for p in a['parts'] if p['name'].endswith('_moving_slide_arm')]
laps=[]
for arm in arms:
 v=np.array(arm['vertices']);side=np.sign(v[:,1].mean());v[:,1]+=side*2.7;lo,hi=v.min(0),v.max(0);cx=v[:,0].mean()
 candidates=[q for q in rails if abs(np.array(q['vertices'])[:,0].mean()-cx)<.1 and np.sign(np.array(q['vertices'])[:,1].mean())==side]
 assert len(candidates)==1
 w=np.array(candidates[0]['vertices']);lap=min(hi[1],w[:,1].max())-max(lo[1],w[:,1].min());laps.append(float(lap))
 if lap<1.0:fail.append('insufficient full-extension rail overlap')
details['rail_overlap_at_2_7m_extension_m']=laps
details['stage_overlap_at_2_45m_stroke_m']=3.9-2.45
details['cylinder_rod_overlap_at_limit_m']=10.65-2.45-7.70
r=dict(failures=fail,details=details,scope='Specific source geometry checks; full visual and native contact review required separately.')
path=O/'reports'/('r032_review_after.json' if manifest.exists() else 'r032_review_before.json');path.write_text(json.dumps(r,indent=2));print('failures',len(fail));print('\n'.join(fail[:12]));print('coplanar',json.dumps(pairs[:8]));raise SystemExit(bool(fail))
