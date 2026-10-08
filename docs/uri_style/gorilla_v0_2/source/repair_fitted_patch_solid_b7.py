"""Repair only three measured self-crossing fitted armor patches.

The regular fitted masters remain in B6. This finishing pass reconstructs
their closed solids at a small voxel spacing and measures deviation from
the actual fitted surfaces. It never imports a dense reference mesh.
"""
from pathlib import Path
import sys,json,math,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

report=json.loads((ROOT/'lower_modular_components_b6.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/report['source']))
repairs=[]
for check in report['self_intersection_checks']:
    if not check['nonadjacent_triangle_pairs']:continue
    o=bpy.data.objects[check['name']]
    original=np.asarray([v.co[:] for v in o.data.vertices]);o.data.calc_loop_triangles()
    triangles=[t.vertices[:] for t in o.data.loop_triangles]
    original_tree=BVHTree.FromPolygons(original.tolist(),triangles,all_triangles=True)
    original_mesh=o.data
    o.data=o.data.copy()
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
    bpy.context.view_layer.objects.active=o
    # The bundled Blender build has no OpenVDB. Use its native sharp dual
    # contour remesher instead; no runtime or dependency installation.
    finish=o.modifiers.new('closed_patch_solid_finish','REMESH')
    finish.mode='SHARP';finish.octree_depth=9;finish.scale=.99
    finish.use_remove_disconnected=True;finish.threshold=.005
    finish.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=finish.name)
    assert len(o.data.polygons)>0,(o.name,'solid reconstruction failed')
    smooth=o.modifiers.new('small_surface_fairing','SMOOTH');smooth.factor=.18;smooth.iterations=2
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free();o.data.update()
    o.data.use_auto_smooth=True;o.data.auto_smooth_angle=math.radians(36)
    for p in o.data.polygons:p.use_smooth=True
    if not o.data.materials:
        for m in original_mesh.materials:o.data.materials.append(m)
    bpy.data.objects[o.name.replace('L_','R_',1)].data=o.data
    result=np.asarray([v.co[:] for v in o.data.vertices]);o.data.calc_loop_triangles()
    new_tree=BVHTree.FromPolygons(result.tolist(),[t.vertices[:] for t in o.data.loop_triangles],all_triangles=True)
    new_sample=result[::max(1,len(result)//12000)]
    old_sample=original[::max(1,len(original)//12000)]
    forward=np.array([original_tree.find_nearest(Vector(p.tolist()))[3] for p in new_sample])
    reverse=np.array([new_tree.find_nearest(Vector(p.tolist()))[3] for p in old_sample])
    maximum=float(max(forward.max(),reverse.max()))
    repairs.append({'name':o.name,'original_vertices':len(original),'finished_vertices':len(result),
                    'method':'Native Blender SHARP dual contour remesh',
                    'octree_depth':9,'remesh_scale':.99,'disconnected_threshold':.005,
                    'cell_spacing_estimate':float(np.ptp(original,axis=0).max()/(512*.99)),
                    'surface_fairing':{'factor':.18,'iterations':2},
                    'finished_to_fitted_surface_q95':float(np.quantile(forward,.95)),
                    'fitted_to_finished_surface_q95':float(np.quantile(reverse,.95)),
                    'bidirectional_sample_surface_max_distance':maximum,
                    'original_reported_crossing_pairs':check['nonadjacent_triangle_pairs'],
                    'scope':'Deviation from the clean fitted B6 master, not a source-percent or engineering claim'})
    print('FITTED_PATCH_SOLID_REPAIRED',o.name,len(result),maximum,flush=True)

source=ROOT/'source/lower_modular_components_b7.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source),compress=True)
report.update(revision='b7',source=str(source.relative_to(ROOT)),
              source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              local_solid_repairs=repairs,
              fitted_regular_patch_source='source/lower_modular_components_b6.blend',
              construction='Clean source-bounded fitted patches and explicit continuous joint/foot carriers; measured self-crossing patches alone finished as closed solids',
              appearance_accepted=False,engineering_ready=False)
# These records refer to B6 and must not be carried as B7 verification.
for key in ['master_topology','mirroring','pose_checks','connected_closed_master_components',
            'strict_shared_mesh_mirroring','core_intersections_observed','different_owner_intersections_observed',
            'self_intersection_checks','master_self_intersections_observed','views','projection_checks']:
    report.pop(key,None)
(ROOT/'lower_modular_components_b7.json').write_text(json.dumps(report,indent=2)+'\n')
print('FITTED_COMPONENTS_FINISH_SOURCE_SAVED',flush=True)
