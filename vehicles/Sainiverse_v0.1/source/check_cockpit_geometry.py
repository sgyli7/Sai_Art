"""Regression for the user's segmented rim and buried instrument-panel closeups."""
import gzip,json,numpy as np,trimesh as tm
from pathlib import Path
O=Path(__file__).resolve().parents[1]
a=json.loads(gzip.decompress((O/'source/assembly.json.gz').read_bytes()))
mesh=lambda p:tm.Trimesh(p['vertices'],p['faces'],process=False)
horns=[p for p in a['parts'] if p['name'].endswith(('_steer_horns','_steer_copilot_horns'))]
assert len(horns)==2
for p in horns:
 m=mesh(p);m.merge_vertices();assert m.is_watertight and len(m.split())==1
intersections=[]
for p in [p for p in a['parts'] if p['name'].endswith('_flight_instruments')]:
 for q in [q for q in a['parts'] if q['name'].endswith('_pilot_console_pedestal')]:
  if np.linalg.norm(mesh(p).centroid-mesh(q).centroid)<2:
   inter=tm.boolean.intersection([mesh(p),mesh(q)],engine='manifold');vol=abs(float(inter.volume)) if len(inter.faces) else 0.
   intersections.append(vol);assert vol<1e-8,('embedded panel',p['name'],vol)
assert len(intersections)==2
for theme in ['black','white','blue','yellow','desert']:
 p=json.loads((O/'themes'/f'{theme}.json').read_text())['palette']
 rgb=lambda k:np.array(list(bytes.fromhex(p[k])))/255.
 assert np.linalg.norm(rgb('cabin_upholstery')-rgb('cabin_console'))>.10,theme
 assert p['cabin_grip']!=p['cabin_upholstery']!=p['cabin_lounge'],theme
report=dict(dual_yokes=2,connected_horn_meshes=2,instrument_console_intersections_m3=intersections,themes=5,scope='Geometry/color regression only. Perceived MSFS-quality, manipulator reach and performance require separate review.')
(O/'reports/cockpit_geometry.json').write_text(json.dumps(report,indent=2));print(report)
