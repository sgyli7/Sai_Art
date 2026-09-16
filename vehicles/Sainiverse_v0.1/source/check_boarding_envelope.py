"""Sampled solid clearance of platform, guards and hinged ramp against fixed hull.
Telescopic guide-to-guide engagement and intentional hinge contact are excluded.
"""
from pathlib import Path
import gzip,json
import numpy as np
import trimesh as tm
O=Path(__file__).resolve().parents[1];a=json.loads(gzip.decompress((O/'source/assembly.json.gz').read_bytes()));lifts=json.loads((O/'source/lifts.json').read_text())
fixed=[]
for p in a['parts']:
 if p['group'] not in ['front','rear','tail']:continue
 m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
 if m.is_volume:fixed.append((p,m,m.bounds))
fail=[];checks=0;poses=[(out,0.,0.) for out in np.linspace(0,2.7,10)]+[(2.7,down,0.) for down in np.linspace(0,7.2,12)]+[(2.7,7.2,q) for q in np.linspace(0,1.76,14)]
for lift in lifts:
 ps=[p for p in a['parts'] if (p['group']==lift['groups'][3] and any(s in p['name'] for s in ['boarding_floor','lift_guard'])) or p['group']==lift['ramp']['name']]
 for out,down,angle in poses:
  shift=np.array([0,lift['side']*out,-down]);pivot=np.array(lift['ramp']['pivot']);rotation=tm.transformations.rotation_matrix(angle,lift['ramp']['axis'])[:3,:3]
  for p in ps:
   v=np.array(p['vertices']);v=(v-pivot)@rotation.T+pivot if p['group']==lift['ramp']['name'] else v
   moving=tm.Trimesh(vertices=v+shift,faces=p['faces'],process=False)
   if not moving.is_volume:continue
   lo,hi=moving.bounds
   for q,m,(l,h) in fixed:
    if q['group']!=lift['hull'] or np.any(np.minimum(hi,h)-np.maximum(lo,l)<1e-5):continue
    checks+=1;volume=abs(tm.boolean.intersection([moving,m],engine='manifold').volume)
    if volume>1e-5:fail.append(dict(lift=lift['name'],moving=p['name'],fixed=q['name'],out_m=float(out),down_m=float(down),ramp_rad=float(angle),volume_m3=volume))
r=dict(lifts=6,poses_per_lift=len(poses),boolean_candidates=checks,failures=fail,scope=__doc__);(O/'reports/boarding_envelope.json').write_text(json.dumps(r,indent=2));print('failures',len(fail),'tested',checks);assert not fail,fail[:4]
