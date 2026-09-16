"""Actual exported-source coplanar overlap: red fascia against other fixed skin."""
from pathlib import Path
import json,gzip,sys
import numpy as np
from shapely.geometry import Polygon
P=Path(sys.argv[1]);a=json.loads(gzip.decompress((P/'source/assembly.json.gz').read_bytes()))
parts=[]
for p in a['parts']:
 if p['group'] not in ['front','rear','tail']:continue
 v=np.array(p['vertices']);parts.append((p,v,v.min(0),v.max(0)))
fail=[]
for p,v,lo,hi in parts:
 if not ('side_fascia' in p['name'] or p['name'].endswith(('_front_deck','_rear_deck'))):continue
 for q,w,l,h in parts:
  if q is p or q['group']!=p['group'] or q['material']==p['material']:continue
  if np.any(np.minimum(hi,h)-np.maximum(lo,l)<-1e-4):continue
  # Match planar facets; triangles give a reproducible area check, not bbox contact.
  for f in p['faces']:
   tri=v[f]
   if 'side_fascia' not in p['name'] and (np.max(tri[:,2])<6.0 or np.min(tri[:,2])>6.2 or abs(tri[:,1].mean())<12.65):continue
   normal=np.cross(tri[1]-tri[0],tri[2]-tri[0]);size=np.linalg.norm(normal)
   if size<1e-8:continue
   normal/=size;axis=np.argmax(abs(normal));axes=[k for k in range(3) if k!=axis]
   ts=w[np.array(q['faces'])];ds=(ts-tri[0])@normal;active=np.max(abs(ds),axis=1)<1e-4
   if not active.any():continue
   poly=Polygon(tri[:,axes]);area=sum(poly.intersection(Polygon(t[:,axes])).area for t in ts[active])
   if area>1e-4:fail.append({'red':p['name'],'other':q['name'],'plane_axis':int(axis),'overlap_m2':float(area)});break
print(json.dumps({'coplanar_pairs':len(fail),'pairs':fail},indent=2))
raise SystemExit(bool(fail))
