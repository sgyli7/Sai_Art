"""Boolean occupied volumes against every fixed source mesh through a lift cycle."""
import json,gzip,sys
from pathlib import Path
import numpy as np
import trimesh as tm
O=Path(sys.argv[1]);a=json.loads(gzip.decompress((O/'source/assembly.json.gz').read_bytes()))
fixed=[]
for p in a['parts']:
 if p['group'] not in ['front','rear','tail']:continue
 m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
 fixed.append((p,m,m.bounds))
fail=[]
for p in a['parts']:
 if not p['name'].endswith('_boarding_floor'):continue
 g=p['group'];hull=g.split('_')[1];side=1 if 'left' in g else -1
 for out,down in [(0,0),(.7,0),(1.4,0),(2.1,0),(2.7,0),(2.7,1),(2.7,2),(2.7,3),(2.7,4),(2.7,5),(2.7,6),(2.7,7)]:
  moving=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False);moving.apply_translation([0,side*out,-down]);lo,hi=moving.bounds
  for q,m,(l,h) in fixed:
   if q['group']!=hull or np.any(np.minimum(hi,h)-np.maximum(lo,l)<1e-5):continue
   if not m.is_volume:continue
   volume=abs(tm.boolean.intersection([moving,m],engine='manifold').volume)
   if volume>1e-5:fail.append({'lift':g,'fixed':q['name'],'out_m':out,'down_m':down,'overlap_m3':volume})
report={'sampled_poses_per_lift':12,'failure_count':len(fail),'failures':fail,'scope':'Source solid floor against fixed hull geometry at deployed/stowed and swept samples; excludes moving guides and robot contacts.'};print(json.dumps(report,indent=2));raise SystemExit(bool(fail))
