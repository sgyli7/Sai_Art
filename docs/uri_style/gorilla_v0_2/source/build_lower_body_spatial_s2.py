"""Inspect a source-retained Pixal3D lower body with complete reference feet.

No upper body is rebuilt. Native G2's clear-side leg surface is retained,
mirrored for a paired appearance candidate, and capped by native remeshing.
The generated half-foot is replaced by a connected toe/ankle/heel appearance
assembly. It is not a machining, load, mass, or articulation qualification.
"""
from pathlib import Path
import sys
import math
import json
import hashlib
import time

sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
START = time.time()
SOURCE = ROOT/'source/gorilla_clean_g2.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
source = bpy.data.objects['gorilla_reference_body_g2']
vertices = np.empty(len(source.data.vertices)*3, dtype=np.float32)
source.data.vertices.foreach_get('co', vertices)
vertices = vertices.reshape(-1,3)
triangles = []
source.data.calc_loop_triangles()
for t in source.data.loop_triangles:
    triangles.append(tuple(t.vertices))
triangles = np.asarray(triangles, dtype=np.int32)

def segment_distance(points, a, b):
    a,b = np.asarray(a),np.asarray(b)
    v = b-a
    u = np.clip((points-a)@v/(v@v),0,1)
    return np.linalg.norm(points-a-u[:,None]*v,axis=1)

# Ownership is a spatial mask, independent of all old paint assignments.
thigh = segment_distance(vertices,(.17,.008,.075),(.178,-.155,-.165))/.116
return_link = segment_distance(vertices,(.178,-.155,-.165),(.19,.032,-.232))/.085
shank = segment_distance(vertices,(.19,.032,-.232),(.19,-.028,-.377))/.076
nearest = np.minimum.reduce([thigh,return_link,shank])
x,y,z = vertices.T
mask = ((x>.069)&(x<.264)&(z<.080)&(z>-.387)&(y<.13)&(nearest<1.30))
# Exclude the hanging hand in front of the thigh.
mask &= ~((x>.225)&(y<-.210)&(z>-.180))
kept = triangles[mask[triangles].all(axis=1)]
used,inv = np.unique(kept.reshape(-1),return_inverse=True)
leg_vertices = vertices[used].copy()
leg_faces = inv.reshape(-1,3)

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj,do_unlink=True)

def material(name,color,metallic=0,roughness=.48):
    m = bpy.data.materials.new(name)
    m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Metallic'].default_value=metallic
    p.inputs['Roughness'].default_value=roughness
    return m

mat = {
    'shell':material('neutral_source_shell',(.56,.61,.65)),
    'foot':material('neutral_integrated_foot',(.73,.76,.77)),
    'frame':material('neutral_support_frame',(.18,.22,.25),.25),
    'metal':material('neutral_joint_face',(.38,.43,.46),.45),
}

def finish(o,key,bevel=0):
    o.data.materials.append(mat[key])
    o['scope']='appearance_geometry_candidate_not_engineering_cad'
    for p in o.data.polygons:p.use_smooth=True
    if bevel:
        mod=o.modifiers.new('surface_edge_radius','BEVEL')
        mod.width=bevel;mod.segments=4
        mod.limit_method='ANGLE';mod.angle_limit=math.radians(20)
        o.data.use_auto_smooth=True
        o.data.auto_smooth_angle=math.radians(50)
        mod=o.modifiers.new('weighted_surface_normals','WEIGHTED_NORMAL')
        mod.keep_sharp=True
    return o

def mesh_object(name,v,f,key,bevel=0):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(v,[],f);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
    finish(o,key,bevel)
    return o

def cylinder(name,center,radius,width,key):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=radius,depth=width,location=center)
    o=bpy.context.object;o.name=name
    o.rotation_euler=(0,math.pi/2,0)
    finish(o,key,.0015)
    return o

def foot_prism(name,center_x,plan,bottom,tops,key,bevel=.004):
    n=len(plan)
    v=[(center_x+a,b,bottom) for a,b in plan]
    v += [(center_x+a,b,c) for (a,b),c in zip(plan,tops)]
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    f += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh_object(name,v,f,key,bevel)

# Native surface cleaning preserves the reconstructed Z-shaped leg outline.
base=mesh_object('pixal_clear_side_leg',leg_vertices.tolist(),leg_faces.tolist(),'shell')
bpy.context.view_layer.objects.active=base;base.select_set(True)
mod=base.modifiers.new('cap_extraction_boundaries','REMESH')
mod.mode='SMOOTH';mod.octree_depth=8;mod.scale=.97
mod.use_remove_disconnected=True;mod.threshold=.01;mod.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=mod.name)
mod=base.modifiers.new('suppress_scan_grain','SMOOTH');mod.factor=.46;mod.iterations=6
bpy.ops.object.modifier_apply(modifier=mod.name)
base['source']='G2 clear-side native Pixal3D leg surface; upper source not adopted'
base['source_vertex_count_before_cleanup']=len(leg_vertices)
base['source_original_glb_sha256']='60ba19b16ac5d6fdbe9d341502931ff52c49e2741b1087c366e05ba8f7fed971'

leg_other=base.copy();leg_other.data=base.data.copy()
leg_other.name='pixal_mirrored_leg';bpy.context.collection.objects.link(leg_other)
for v in leg_other.data.vertices:v.co.x=-v.co.x
# Reflection reverses orientation.
bpy.context.view_layer.objects.active=leg_other
base.select_set(False);leg_other.select_set(True)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.flip_normals();bpy.ops.object.mode_set(mode='OBJECT')
leg_other.select_set(False)

feet=[]
for side in (-1,1):
    cx=side*.185
    ankle_y=-.029
    ankle_z=-.375
    # One broad sole and fork carry the shank into a low axle in the foot.
    # A whole foot, not an isolated toe or a stack of tiny ankle links.
    plan=[(-.057,-.203),(.057,-.203),(.070,-.169),(.067,.054),
          (.048,.082),(-.048,.082),(-.067,.054),(-.070,-.169)]
    sole=foot_prism(f'whole_contact_sole_{side}',cx,plan,-.445,[-.432]*8,'frame',.003)
    feet.append(sole)
    heel_plan=[(-.062,-.102),(.062,-.102),(.067,.045),(.045,.075),(-.045,.075),(-.067,.045)]
    foot_prism(f'load_cradle_{side}',cx,heel_plan,-.432,
               [-.393,-.393,-.389,-.407,-.407,-.389],'foot',.005)
    # The lateral cheek plates are a continuous triangular support mass.
    cheek_yz=[(-.111,-.426),(-.117,-.399),(-.072,-.358),
              (.013,-.352),(.065,-.421),(.051,-.432)]
    for cheek in (-1,1):
        xa=cx+cheek*.052
        xb=cx+cheek*.065
        v=[(xx,yy,zz) for xx in (xa,xb) for yy,zz in cheek_yz]
        n=len(cheek_yz)
        f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
        f += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        foot_prt=mesh_object(f'integrated_ankle_cheek_{side}_{cheek}',v,f,'foot',.004)
        # Maintain outward-facing normals even on the negative-X extrusion.
        if xb<xa:
            bpy.context.view_layer.objects.active=foot_prt
            foot_prt.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.flip_normals();bpy.ops.object.mode_set(mode='OBJECT')
            foot_prt.select_set(False)
    cylinder(f'low_ankle_cross_axle_{side}',(cx,ankle_y,ankle_z),.038,.141,'frame')
    for rim in (-1,1):
        cylinder(f'low_ankle_face_{side}_{rim}',(cx+rim*.072,ankle_y,ankle_z),.029,.005,'metal')
        cylinder(f'low_ankle_center_{side}_{rim}',(cx+rim*.075,ankle_y,ankle_z),.012,.007,'frame')
    toe_plan=[(-.056,-.199),(.056,-.199),(.061,-.171),(.052,-.112),(-.052,-.112),(-.061,-.171)]
    foot_prism(f'complete_forefoot_armor_{side}',cx,toe_plan,-.429,
               [-.416,-.416,-.399,-.396,-.396,-.399],'foot',.004)
    toe_pad=[(-.050,-.207),(.050,-.207),(.056,-.183),(-.056,-.183)]
    foot_prism(f'toe_contact_guard_{side}',cx,toe_pad,-.442,[-.419]*4,'frame',.003)
    heel_pad=[(-.045,.049),(.045,.049),(.041,.084),(-.041,.084)]
    foot_prism(f'heel_contact_guard_{side}',cx,heel_pad,-.442,[-.405,-.405,-.424,-.424],'frame',.003)

# Exact inspection data comes from the evaluated meshes, not raster extents.
scene=bpy.context.scene
meshes=[o for o in scene.objects if o.type=='MESH']
depg=bpy.context.evaluated_depsgraph_get()
all_v=[];parts=[];geometry_hash=hashlib.sha256()
for o in meshes:
    e=o.evaluated_get(depg);me=e.to_mesh()
    v=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',v);v=v.reshape(-1,3)
    m=np.asarray(o.matrix_world,dtype=np.float64)
    w=v@m[:3,:3].T+m[:3,3]
    geometry_hash.update(o.name.encode());geometry_hash.update(w.tobytes())
    parts.append({'name':o.name,'vertices':len(w),'bounds_xyz':[w.min(0).tolist(),w.max(0).tolist()]})
    all_v.append(w);e.to_mesh_clear()
world=np.concatenate(all_v)
lo,hi=world.min(0),world.max(0)
center=Vector(((lo+hi)/2).tolist())
scale=float(max(hi-lo)*1.19)

scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=False
scene.render.resolution_x=1000;scene.render.resolution_y=1000
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world=bpy.data.worlds.new('white_inspection_world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
scene.view_settings.view_transform='Standard';scene.view_settings.exposure=-.45
for name,pos,energy,size in [('main',(-1,-2,2),170,3),('fill',(2,-1,.5),90,3)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
    light=bpy.data.objects.new(name,data);scene.collection.objects.link(light)
    light.location=pos;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
cam_data=bpy.data.cameras.new('shared_orthographic_camera')
camera=bpy.data.objects.new('shared_orthographic_camera',cam_data);scene.collection.objects.link(camera)
scene.camera=camera;cam_data.type='ORTHO';cam_data.ortho_scale=scale
cam_data.clip_start=.01;cam_data.clip_end=10
views={}
for name,axis in [('front',(0,-1,0)),('left',(1,0,0)),('rear',(0,1,0)),('top',(0,0,1)),
                  ('front_oblique',(1,-1,.52)),('rear_oblique',(1,1,.52))]:
    camera.location=center+Vector(axis).normalized()*3
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    inv=np.asarray(camera.matrix_world.inverted())
    local=world@inv[:3,:3].T+inv[:3,3]
    span=np.ptp(local[:,:2],axis=0)/scale*1000
    out=ROOT/'images'/f'lower_body_native_{name}_s2.png'
    scene.render.filepath=str(out);bpy.ops.render.render(write_still=True)
    views[name]={'image':str(out.relative_to(ROOT)),'type':'ORTHO',
                 'shared_geometry_sha256':geometry_hash.hexdigest(),
                 'orthographic_scale':scale,'projected_span_px':span.tolist(),
                 'camera_matrix_world':np.asarray(camera.matrix_world).tolist()}
    print('LOWER_BODY_NATIVE_VIEW',name,json.dumps(span.tolist()),flush=True)

source_out=ROOT/'source/lower_body_spatial_s2.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source_out),compress=True)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'generated/lower_body_spatial_s2.glb'),
                         export_format='GLB',use_selection=True,export_apply=True)
projection_checks={
    'front_left_height':abs(views['front']['projected_span_px'][1]-views['left']['projected_span_px'][1])<1e-3,
    'front_rear_width':abs(views['front']['projected_span_px'][0]-views['rear']['projected_span_px'][0])<1e-3,
    'front_top_width':abs(views['front']['projected_span_px'][0]-views['top']['projected_span_px'][0])<1e-3,
    'left_top_depth':abs(views['left']['projected_span_px'][0]-views['top']['projected_span_px'][1])<1e-3,
}
report={'scope':'Lower-body source-surface inspection candidate; no upper-body redesign',
        'source':str(SOURCE.relative_to(ROOT)),
        'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'upper_body_authority':'gorilla_v0_1/images/locked_four_view_review_rev_aa3.png unchanged',
        'preserved':'Clear-side Pixal3D lower-body silhouette and bent stance',
        'changed':'Mirrored lower-body pair; generated half-feet replaced with connected complete toe/ankle/heel appearance geometry',
        'coordinate_frame':'+X lateral, -Y front, +Z up; normalized appearance units',
        'palette':'Neutral inspection only; module-based URI allocation pending',
        'bounds_xyz':[lo.tolist(),hi.tolist()],
        'geometry_sha256':geometry_hash.hexdigest(),
        'parts':parts,'views':views,'projection_identity_checks':projection_checks,
        'whole_robot_corresponding_model':False,
        'appearance_accepted':False,'engineering_ready':False,
        'mass_collision_and_strength_validation':False,
        'output_blend':str(source_out.relative_to(ROOT)),
        'elapsed_seconds':time.time()-START}
(ROOT/'lower_body_native_spatial_s2.json').write_text(json.dumps(report,indent=2)+'\n')
print('LOWER_BODY_SPATIAL_COMPLETE',json.dumps(projection_checks),flush=True)
