"""Optimistic source-space reach screen; no collision-free path claim."""
from pathlib import Path
import gzip,json,re,math
import numpy as np
O=Path(__file__).resolve().parents[1]
a=json.loads(gzip.decompress((O/'source/assembly.json.gz').read_bytes()));rig=a['equipment_actuation'];cranes=[c for c in rig['cranes'] if c['hull']=='rear'];rows=[]
for p in a['parts']:
 if not re.search(r'container_b\d+_r\d+_t2_roof$',p['name']):continue
 v=np.array(p['vertices']);point=(v.min(0)+v.max(0))/2;point[2]+=1.15 # lifting eye
 reachable=[];nearest=1e9
 for c in cranes:
  pivot=np.array(a['groups'][c['luff']]);d=np.array(c['direction']);delta=point-pivot;radius=np.linalg.norm(delta[:2]);nearest=min(nearest,float(radius))
  yaw=math.atan2(d[0]*delta[1]-d[1]*delta[0],np.dot(d[:2],delta[:2]))
  if abs(yaw)>math.radians(170):continue
  for pitch in np.linspace(0,math.radians(35),141):
   extension=(radius+c['tip']['local'][2]*math.sin(pitch))/math.cos(pitch)-np.linalg.norm(np.array(c['tip']['local'])[:2])
   tip_z=pivot[2]+(np.linalg.norm(np.array(c['tip']['local'])[:2])+extension)*math.sin(pitch)+c['tip']['local'][2]*math.cos(pitch)
   paid=tip_z-point[2]-.80
   if c['extension_range_m'][0]<=extension<=c['extension_range_m'][1] and 1.3<=paid<=24:reachable.append(c['name']);break
 rows.append(dict(container=re.search(r'container_b\d+_r\d+_t2',p['name'])[0],lifting_eye=point.tolist(),nearest_slew_radius_m=nearest,reachable_cranes=reachable))
report=dict(top_tier_slots=len(rows),reachable_slots=sum(bool(r['reachable_cranes']) for r in rows),unreachable=[r['container'] for r in rows if not r['reachable_cranes']],slots=rows,scope=__doc__)
(O/'reports/crane_coverage.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='slots'})
