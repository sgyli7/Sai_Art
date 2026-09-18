"""Source geometry checks for the six 2026-09-18 acceptance screenshots."""
from pathlib import Path
import gzip,json,numpy as np,trimesh as tm
from mechanical_revision import mesh
O=Path(__file__).resolve().parents[1]
a=json.load(gzip.open(O/'source/assembly.json.gz'))
parts=a['parts'];out={}
def selected(suffix):return [p for p in parts if p['name'].endswith(suffix)]
for p in parts:
 if any(t in p['name'] for t in ['roof_machine_','_fore_vent_']):
  lo,hi=mesh(p).bounds
  assert lo[1]>1.26 or hi[1]<-1.26,p['name']
  if '_fore_vent_' in p['name']:assert max(abs(lo[1]),abs(hi[1]))<7.56,p['name']
assert not selected('_bridge_lower_trim') and not selected('_bridge_vertical_seam')
out['stair_equipment_clearance']=True
for p in selected('_engineer_seat'):
 lo,hi=mesh(p).bounds;edge=max(abs(lo[1]),abs(hi[1]));assert 1.955-edge>.25
 contacts=next(c for c in a['habitable_revision']['contacts'] if c['name']==p['name'])
 assert np.allclose(contacts['vertices_source_m'],p['vertices'])
out['minimum_engineer_seat_gap_m']=round(1.955-edge,3)
for p in selected('_engineer_switch_surface'):
 assert bool(p['cockpit_transform'].get('rotate_uv_180'))==(mesh(p).centroid[1]<0)
out['station_text_orientation']=True
for name in ['steer','steer_copilot']:
 p=selected('_'+name+'_horns');assert len(p)==1
 m=mesh(p[0]);m.merge_vertices();assert m.is_watertight and len(m.split())==1
 pivot=np.array(a['groups']['cockpit_'+name]);assert m.bounds[1,2]>pivot[2]+.16
 column=mesh(selected('_'+name+'_column')[0]);assert column.bounds[0,0]>pivot[0]
 # Sweep at full steering deflection stays forward of seat and behind panel.
 for angle in np.linspace(-.65,.65,13):
  points=(m.vertices-pivot)@tm.transformations.rotation_matrix(angle,[1,0,0])[:3,:3].T+pivot
  assert points[:,0].min()>31.10 and points[:,0].max()<32.0
out['dual_yoke_closed_geometry_and_sweep']=True
assert len(selected('_lift_call_station_post'))==len(selected('_lift_controls'))==6
floor=mesh(selected('_enclosed_connector_floor')[0]);assert abs(floor.bounds[1,0]-16.05)<1e-8
out['landing_floor_no_coplanar_overlap']=True
assert all(p['material']=='rig_cargo_spreader' for p in parts if 'cargo_spreader_' in p['name'])
out['rigging_neutral_finish']=True
out['cargo_art_families']=len(set(p['company_sticker'] for p in parts if p.get('company_sticker','').startswith('fleet_')));assert out['cargo_art_families']==6
out['scope']='Source geometry regression. Native screenshots and control/physics evidence remain separate.'
(O/'reports/acceptance_geometry.json').write_text(json.dumps(out,indent=2));print(out)
