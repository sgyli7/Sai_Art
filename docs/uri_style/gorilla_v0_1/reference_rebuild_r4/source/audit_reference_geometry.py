"""Report reconstruction failures rather than presenting a draft as delivery."""
from pathlib import Path
import hashlib
import itertools
import json
import numpy as np
import trimesh as tr
import manifold3d as mf
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source'/'reference_scene.json'
S=json.loads(SOURCE.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
solids={p['name']:mf.Manifold(mf.Mesh64(np.array(p['vertices'],dtype=np.float64,order='C'),
                                      np.array(p['faces'],dtype=np.uint64,order='C')))
        for p in S['parts']}
collisions=[]
for a,b in itertools.combinations(S['parts'],2):
    if a['body']==b['body']:continue
    volume=(solids[a['name']]^solids[b['name']]).volume()
    if volume>1e-7:
        collisions.append({'a':a['name'],'b':b['name'],'volume_layout_units_cubed':volume,
                           'joint_mating_or_external_clearance_unresolved':True})
exchange=tr.load(ROOT/'source'/'reference_geometry.glb',force='scene',process=False)
to_z_up=np.array([[1.,0.,0.,0.],[0.,0.,-1.,0.],[0.,1.,0.,0.],[0.,0.,0.,1.]])
maximum=0.
for p in S['parts']:
    imported=exchange.geometry[p['name']].copy();imported.apply_transform(to_z_up)
    tree=cKDTree(np.array(p['vertices']))
    distance=tree.query(np.array(imported.vertices))[0]
    maximum=max(maximum,float(distance.max()))
observed_controls=[]
part_by_name={p['name']:p for p in S['parts']}
camera=S['camera'];right=np.array(camera['right_vector']);up=np.array(camera['up_vector'])
target=np.array(camera['target']);center=np.array(camera['pixel_center']);scale=camera['pixels_per_layout_unit']
for observation in S['observations']:
    p=part_by_name[observation['name']]
    mesh=tr.Trimesh(p['vertices'],p['faces'],process=False)
    closest,distance,_=tr.proximity.closest_point_naive(mesh,np.array(observation['observed_control_vertices_3d']))
    rel=closest-target
    projected=np.column_stack((center[0]+scale*(rel@right),center[1]-scale*(rel@up)))
    error=np.linalg.norm(projected-np.array(observation['reference_polygon_px']),axis=1)
    observed_controls.append({'part':p['name'],'max_post_relief_control_error_px':float(error.max()),
                              'max_source_surface_distance_layout_units':float(distance.max())})
record={'revision':S['revision'],'source_sha256':sha(SOURCE),
        'source_parts':len(S['parts']),'all_parts_finite_positive':all(m.volume()>0 for m in solids.values()),
        'inter_group_static_intersections':collisions,
        'max_glb_exchange_vertex_error_layout_units':maximum,
        'exchange_coordinate_conversion':'source X-forward Y-left Z-up -> glTF Y-up',
        'post_relief_observed_controls':observed_controls,
        'observed_pixel_controls_only':True,
        'single_view_camera_and_depth_are_assumed':True,
        'native_render_manifest_source_matches':json.loads((ROOT/'source'/'render_manifest.json').read_text())['source_sha256']==sha(SOURCE),
        'reference_geometry_accepted':False,'ready_for_painting':False,'ready_for_engineering_handoff':False,
        'imagegen_used':False,
        'failure_reasons':['Side view still exposes unverified depths and component connections.',
                           'Static surface relief does not establish a valid articulated assembly.',
                           'Only one cropped reference camera is available. Rear, sole, and occluded geometry are undetermined.',
                           'Control-polygon reprojection cannot establish recovered 3D geometry.'],
        'required_reference':'Original 3D source or complete reference multiviews, especially posterior, side and foot.'}
(ROOT/'source'/'reconstruction_audit.json').write_text(json.dumps(record,indent=2)+'\n')
status={'active_task':'Reference geometry reconstruction before artwork',
        'active_directory':'reference_rebuild_r4',
        'rejected_appearance_versions':['leg_design_r2','leg_design_r3'],
        'latest_user_requirement':'Restore reference geometry before image generation; no further independent shape redesign.',
        'reference_geometry_accepted':False,'ready_for_painting':False,'ready_for_engineering_handoff':False,
        'old_handoff_zip_status':'Historical R2 proposal rejected by user; not current delivery.',
        'audit':'reference_rebuild_r4/source/reconstruction_audit.json',
        'requested_missing_reference':'Original model or complete multiview source path; async question pending.'}
(ROOT.parent/'current_design_status.json').write_text(json.dumps(status,indent=2)+'\n')
print('RECONSTRUCTION_AUDIT',len(collisions),'unresolved intersections; painting/handoff FALSE',flush=True)
