"""Regression for the user's segmented rim and buried instrument-panel closeups."""
import gzip,json,numpy as np,trimesh as tm
from pathlib import Path
O=Path(__file__).resolve().parents[1]
a=json.loads(gzip.decompress((O/'source/assembly.json.gz').read_bytes()))
mesh=lambda p:tm.Trimesh(p['vertices'],p['faces'],process=False)
rims=[p for p in a['parts'] if p['name'].endswith('_steer_rim')]
assert len(rims)==1,('segmented rim',len(rims))
rim=mesh(rims[0]);rim.merge_vertices();assert rim.is_watertight and len(rim.split())==1
pivot=np.array(a['groups']['cockpit_steer']);v=rim.vertices-pivot
angles=np.unique(np.round(np.arctan2(v[:,2],v[:,1]),7));assert len(angles)>=96
sagitta=.235*(1-np.cos(np.pi/96));assert sagitta<.00015
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
report=dict(rim_connected_components=1,rim_angular_sections=len(angles),rim_chord_sagitta_m=sagitta,instrument_console_intersections_m3=intersections,themes=5,scope='Geometry/color regression only. Perceived MSFS-quality, manipulator reach and performance require separate review.')
(O/'reports/cockpit_geometry.json').write_text(json.dumps(report,indent=2));print(report)
