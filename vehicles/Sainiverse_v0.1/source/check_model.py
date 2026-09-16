from pathlib import Path
import gzip,json,numpy as np
O=Path(__file__).resolve().parents[1];a=json.loads(gzip.decompress((O/'source/assembly.json.gz').read_bytes()));lifts=json.loads((O/'source/lifts.json').read_text());out=[]
bounds=lambda p:np.array([np.min(p['vertices'],axis=0),np.max(p['vertices'],axis=0)])
logos=[p for p in a['parts'] if 'Sainiverse_wordmark' in p['name']]
for logo in logos:
 b=bounds(logo);conflicts=[]
 for q in a['parts']:
  if q['group']!=logo['group'] or not any(k in q['name'] for k in ['paint_','bridge_vertical_seam','bridge_square_window','bridge_side_glass','bridge_lower_hatch']):continue
  c=bounds(q)
  if abs(c[:,1].mean()-b[:,1].mean())>.25:continue
  overlap=np.minimum(b[1,[0,2]],c[1,[0,2]])-np.maximum(b[0,[0,2]],c[0,[0,2]])
  if np.all(overlap>0):conflicts.append(q['name'])
 out.append(dict(name=logo['name'],bounds=b.tolist(),overlapping_markings=conflicts));assert not conflicts,(logo['name'],conflicts)
for lift in lifts:
 parts=[p for p in a['parts'] if p['group'] in lift['groups']];v=np.concatenate([p['vertices'] for p in parts]);assert abs(v[:,1]).max()<=14.7
 # The extended inner edge clears the bogie track's widest outer edge.
 assert abs(lift['pivot'][1])+lift['stroke_out']-1.1>14.7
assert len(logos)==8 and len(lifts)==6
report=dict(logos=out,boarding_lifts=6,stowed_envelope_max_y_m=14.7,scope='Authored marking/window/hatch overlap and lift envelope checks; not a universal triangle collision or manufacturing certification.')
(O/'reports/geometry_checks.json').write_text(json.dumps(report,indent=2));print('PASS: 8 logos clear of markings/windows/hatches; 6 lifts inside track envelope and clear when extended.')
