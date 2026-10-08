"""Local repairs on the selected actual dense lower surface.

No replacement lofts, hulls, cubes or simplification. Only the proximal cut
is made planar and capped; retained visible source positions stay exact.
Foot geometry is intentionally omitted pending detailed reference rebuilding.
"""
from pathlib import Path
import sys,math,json,hashlib
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy,bmesh
import numpy as np
from mathutils import Vector
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/lower_body_spatial_s2.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
keep=['pixal_clear_side_leg','pixal_mirrored_leg']
for o in list(bpy.data.objects):
    if o.type=='MESH' and o.name not in keep:bpy.data.objects.remove(o,do_unlink=True)
records=[]
for name in keep:
    o=bpy.data.objects[name]
    before=np.empty(len(o.data.vertices)*3,dtype=np.float32)
    o.data.vertices.foreach_get('co',before);before=before.reshape(-1,3)
    bm=bmesh.new();bm.from_mesh(o.data)
    cut=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                              plane_co=(0,0,.067),plane_no=(0,0,1),
                              clear_outer=True,clear_inner=False,dist=1e-7)
    boundary=[e for e in bm.edges if e.is_boundary]
    filled=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    topology={'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
              'signed_volume':bm.calc_volume(signed=True),
              'capped_faces':len(filled.get('faces',[]))}
    bm.to_mesh(o.data);bm.free();o.data.update()
    o['surface_method']='Source retained; proximal cut/caps only; no envelope replacement'
    for p in o.data.polygons:p.use_smooth=True
    after=np.empty(len(o.data.vertices)*3,dtype=np.float32)
    o.data.vertices.foreach_get('co',after);after=after.reshape(-1,3)
    # Exact original positions are expected outside the new cap plane.
    visible=after[:,2]<.0669
    nearest=cKDTree(before).query(after[visible],k=1)[0]
    original_kept=before[:,2]<.0669
    backward=cKDTree(after).query(before[original_kept],k=1)[0]
    records.append({'name':name,'original_vertices':len(before),'new_vertices':len(after),
                    'visible_vertices_checked':int(visible.sum()),
                    'retained_surface_max_vertex_distance':float(nearest.max()),
                    'retained_original_max_distance':float(backward.max()),
                    'exact_visible_fraction':float(np.mean(nearest<=1e-7)),
                    'original_visible_retained_fraction':float(np.mean(backward<=1e-7)),
                    'scope':'Measured retained surface away from cut; not reference-image accuracy or engineering',
                    **topology})

scene=bpy.context.scene
for name in ('neutral_source_shell','neutral_integrated_foot'):
    m=bpy.data.materials.get(name)
    if m:
        p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(.37,.42,.46,1)
        p.inputs['Roughness'].default_value=.55
for o in bpy.data.objects:
    if o.type=='LIGHT':o.data.energy*=.30
scene.cycles.samples=40;scene.cycles.use_denoising=False
scene.view_settings.exposure=-.25
world=[];h=hashlib.sha256()
for name in keep:
    o=bpy.data.objects[name]
    v=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',v);v=v.reshape(-1,3)
    m=np.asarray(o.matrix_world);w=v@m[:3,:3].T+m[:3,3]
    world.append(w);h.update(name.encode());h.update(w.tobytes())
world=np.concatenate(world);lo,hi=world.min(0),world.max(0)
center=Vector(((lo+hi)/2).tolist());scale=float(max(hi-lo)*1.19)
camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=scale
views={}
for name,axis in [('front',(0,-1,0)),('left',(1,0,0)),('rear',(0,1,0)),('top',(0,0,1)),
                 ('front_oblique',(1,-1,.52))]:
    camera.location=center+Vector(axis).normalized()*3
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    inv=np.asarray(camera.matrix_world.inverted());cv=world@inv[:3,:3].T+inv[:3,3]
    span=np.ptp(cv[:,:2],axis=0)/scale*1000
    out=ROOT/'images'/f'lower_dense_surface_{name}_s6.png'
    scene.render.filepath=str(out);bpy.ops.render.render(write_still=True)
    views[name]={'image':str(out.relative_to(ROOT)),'span_px':span.tolist(),
                 'camera_matrix_world':np.asarray(camera.matrix_world).tolist(),
                 'shared_geometry_sha256':h.hexdigest()}
    print('DENSE_SURFACE_VIEW',name,json.dumps(span.tolist()),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/lower_dense_surface_s6.blend'),compress=True)
record={
 'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'scope':'Actual source leg skin retained. Only the upper cut interface capped.',
 'whole_robot_upper_body':'Original v0.1 unchanged; absent from this lower-body study',
 'foot_scope':'Absent; rejected coarse feet are not reused as the final geometry',
 'parts':records,'views':views,'shared_geometry_sha256':h.hexdigest(),
 'bounds_xyz':[lo.tolist(),hi.tolist()],
 'projection_checks':{
   'front_left_height':abs(views['front']['span_px'][1]-views['left']['span_px'][1])<1e-3,
   'front_top_width':abs(views['front']['span_px'][0]-views['top']['span_px'][0])<1e-3,
   'left_top_depth':abs(views['left']['span_px'][0]-views['top']['span_px'][1])<1e-3,
 },
 'source_retention_checks':{
   'all_retained_visible_positions_exact':all(p['exact_visible_fraction']==1 for p in records),
   'all_original_below_cut_retained':all(p['original_visible_retained_fraction']==1 for p in records),
   'all_meshes_closed':all(p['nonmanifold_edges']==0 for p in records),
   'all_meshes_outward':all(p['signed_volume']>0 for p in records),
 },
 'appearance_accepted':False,'engineering_ready':False,
 'collision_mass_strength_validation':False,
}
(ROOT/'lower_dense_surface_s6.json').write_text(json.dumps(record,indent=2)+'\n')
print('DENSE_SURFACE_REPAIR_COMPLETE',json.dumps(record['source_retention_checks']),flush=True)
