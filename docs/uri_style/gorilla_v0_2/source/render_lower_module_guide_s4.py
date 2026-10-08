"""Color actual lower modules and render one native four-view guide.

Normal repairs and per-object URI colors only; S3 vertex positions/pose stay
fixed. Linked copies undergo camera-equivalent rigid display transforms.
The whole-robot upper body is not present and is not redesigned here.
"""
from pathlib import Path
import sys, math, hashlib, json
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy, bmesh
import numpy as np
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]
SOURCE=globals().get('SOURCE',ROOT/'source/lower_body_spatial_s3.blend')
REV=globals().get('REV','s4')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
if globals().get('DISTINCT_KNEE_GUARD',False):
    # Replaces the wide wrapping cap with a complete front shield. Color is
    # owned by this shield, never by a horizontal height interval in the thigh.
    for side in (-1,1):
        old=bpy.data.objects.get(f'knee_guard_module_{side}')
        if old:bpy.data.objects.remove(old,do_unlink=True)
        cx=side*.178
        xz=[(-.048,-.099),(.048,-.099),(.061,-.113),(.055,-.155),
            (.027,-.179),(-.027,-.179),(-.055,-.155),(-.061,-.113)]
        vv=[(cx+x,yy,z) for yy in (-.187,-.169) for x,z in xz]
        n=len(xz)
        ff=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        ff += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        mesh=bpy.data.meshes.new(f'knee_guard_module_{side}')
        mesh.from_pydata(vv,[],ff);mesh.update()
        obj=bpy.data.objects.new(f'knee_guard_module_{side}',mesh)
        scene.collection.objects.link(obj)
        obj['module']='independent_front_knee_shield_not_wrapping_paint_band'
        mod=obj.modifiers.new('guard_edge_radius','BEVEL');mod.width=.004;mod.segments=4
        obj.data.use_auto_smooth=True
        mod=obj.modifiers.new('guard_surface_normals','WEIGHTED_NORMAL')
originals=[o for o in scene.objects if o.type=='MESH']
repaired=[]
for o in originals:
    bm=bmesh.new();bm.from_mesh(o.data)
    old_volume=bm.calc_volume(signed=True)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:
        bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    if old_volume<=0:repaired.append(o.name)
    bm.to_mesh(o.data);bm.free()

def material(name,color,metallic,roughness):
    m=bpy.data.materials.new(name);m.use_nodes=True
    color=tuple(int(color[i:i+2],16)/255 for i in (1,3,5))
    linear=lambda a:a/12.92 if a<=.04045 else ((a+.055)/1.055)**2.4
    p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value=(*map(linear,color),1)
    p.inputs['Metallic'].default_value=metallic;p.inputs['Roughness'].default_value=roughness
    return m
palette={
    'blue':material('module_uri_blue','#059EEB',.16,.37),
    'amber':material('module_uri_amber','#F8B326',.12,.40),
    'white':material('module_uri_warm_white','#EFE9DB',.08,.45),
    'frame':material('module_uri_graphite','#2B343A',.32,.44),
    'metal':material('module_uri_joint_metal','#7B858B',.60,.37),
}
assignment={}
for o in originals:
    name=o.name
    if name.startswith(('proximal_thigh_shell','thigh_access_panel','continuous_shank_shell','return_guard_module')):
        key='blue'
    elif name.startswith('knee_guard_module'):
        key='amber'
    elif name.startswith(('load_cradle','integrated_ankle_cheek','complete_forefoot_armor')):
        key='white'
    elif 'side_face' in name or name.startswith(('low_ankle_face','rear_service')):
        key='metal'
    else:key='frame'
    o.data.materials.clear();o.data.materials.append(palette[key])
    assignment[name]=key

world=[];identity=hashlib.sha256();checks=[]
deps=bpy.context.evaluated_depsgraph_get()
for o in originals:
    e=o.evaluated_get(deps);mesh=e.to_mesh()
    v=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',v);v=v.reshape(-1,3)
    m=np.asarray(o.matrix_world);w=v@m[:3,:3].T+m[:3,3]
    world.append(w);identity.update(o.name.encode());identity.update(w.tobytes())
    bm=bmesh.new();bm.from_mesh(mesh)
    checks.append({'name':o.name,'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'signed_volume':bm.calc_volume(signed=True)})
    bm.free();e.to_mesh_clear()
world=np.concatenate(world);lo,hi=world.min(0),world.max(0)
center=Vector(((lo+hi)/2).tolist())
scope_span=float(max(hi-lo))
guide_scale=scope_span*1.19
scene.render.resolution_x=scene.render.resolution_y=1000
scene.cycles.samples=40;scene.cycles.use_denoising=False
views={}
camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=guide_scale
for name,axis in [('front',(0,-1,0)),('left',(1,0,0)),('rear',(0,1,0)),('top',(0,0,1))]:
    camera.location=center+Vector(axis)*3
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    inv=np.asarray(camera.matrix_world.inverted());cv=world@inv[:3,:3].T+inv[:3,3]
    span=np.ptp(cv[:,:2],axis=0)/guide_scale*1000
    p=ROOT/'images'/f'lower_body_module_{name}_{REV}.png'
    scene.render.filepath=str(p);bpy.ops.render.render(write_still=True)
    views[name]={'image':str(p.relative_to(ROOT)),'span_px':span.tolist(),
                 'camera_matrix_world':np.asarray(camera.matrix_world).tolist(),
                 'source_geometry_sha256':identity.hexdigest()}

# Save the editable leg pair first, before adding rigid presentation copies.
native_out=ROOT/'source'/f'lower_body_spatial_{REV}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(native_out),compress=True)
bpy.ops.object.select_all(action='DESELECT')
for o in originals:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'generated'/f'lower_body_spatial_{REV}.glb'),
                         export_format='GLB',use_selection=True,export_apply=True)

display=[
 ('FRONT',Matrix(((1,0,0),(0,0,1),(0,-1,0))),(-.34,.38,0)),
 ('LEFT',Matrix(((0,1,0),(0,0,1),(1,0,0))),(.34,.38,0)),
 ('REAR',Matrix(((-1,0,0),(0,0,1),(0,1,0))),(-.34,-.38,0)),
 ('TOP',Matrix.Identity(3),(.34,-.38,0)),
]
guide_parts=[]
for name,rotation,offset in display:
    transform=Matrix.Translation(Vector(offset))@rotation.to_4x4()@Matrix.Translation(-center)
    for o in originals:
        clone=o.copy();clone.data=o.data;clone.name=f'guide_{name}_{o.name}'
        scene.collection.objects.link(clone);clone.matrix_world=transform@o.matrix_world
        guide_parts.append(clone)
    label_curve=bpy.data.curves.new('label_'+name,'FONT');label_curve.body=name
    label_curve.align_x='CENTER';label_curve.size=.034
    label=bpy.data.objects.new('label_'+name,label_curve);scene.collection.objects.link(label)
    label.location=(offset[0],offset[1]-.33,.35);label.data.materials.append(palette['frame'])
for o in originals:o.hide_render=True
camera.location=(0,0,4);camera.rotation_euler=(0,0,0);camera.data.ortho_scale=1.54
scene.render.resolution_x=scene.render.resolution_y=1800
scene.render.filepath=str(ROOT/'images'/f'lower_body_module_four_view_{REV}.png')
scene.cycles.samples=40
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source'/f'lower_body_four_view_display_{REV}.blend'),compress=True)
record={
 'source_blend':str(SOURCE.relative_to(ROOT)),
 'source_blend_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'source_geometry_sha256':identity.hexdigest(),
 'source_scope':'Lower body only; v0.1 upper-body artwork untouched',
 'changes':'Outward surface normals corrected; URI colors assigned by whole mesh module. Source pose unchanged.'+(' Wrapping knee cap replaced with a complete independent front shield.' if globals().get('DISTINCT_KNEE_GUARD',False) else ' Source vertex positions unchanged.'),
 'repaired_normals':repaired,'material_assignment_by_object':assignment,
 'module_color_rule':'Independent entire knee guard amber; proximal/shank/return shell modules blue; integrated foot cradle white; support frame graphite.',
 'topology_checks':checks,'all_meshes_closed':all(p['nonmanifold_edges']==0 for p in checks),
 'all_meshes_outward':all(p['signed_volume']>0 for p in checks),
 'views':views,
 'projection_identity_checks':{
   'front_left_height':abs(views['front']['span_px'][1]-views['left']['span_px'][1])<1e-3,
   'front_top_width':abs(views['front']['span_px'][0]-views['top']['span_px'][0])<1e-3,
   'left_top_depth':abs(views['left']['span_px'][0]-views['top']['span_px'][1])<1e-3,
 },
 'guide_render':f'images/lower_body_module_four_view_{REV}.png',
 'guide_method':'Native Blender single orthographic render of linked geometry copies with camera-equivalent rigid transforms; no edited artwork pixels',
 'appearance_accepted':False,'engineering_ready':False,
 'physical_mass_clearance_or_strength_qualification':False,
 'upper_body_geometry_validation':False,
}
(ROOT/f'lower_body_module_spatial_{REV}.json').write_text(json.dumps(record,indent=2)+'\n')
print('LOWER_MODULE_GUIDE_COMPLETE',json.dumps(record['projection_identity_checks']),flush=True)
