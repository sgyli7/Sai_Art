"""Reuse the engineering C15 upper meshes verbatim for native TOP registration.

No engineering source is modified. The imported upper receives one recorded
rigid vertical pose translation; no shell is approximated or rebuilt. The
existing Art left lower master is uniformly placed and linked-mirrored for a
candidate full-body projection. These placements are appearance registration,
not an adopted joint, mass, contact, collision or manufacturing contract.
"""
from pathlib import Path
import sys, math, json, hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy,numpy as np
from mathutils import Matrix,Vector
from scipy.spatial import cKDTree

upper_source=ROOT/'source/upstream_v0_1_appearance_c15.blend'
upper_json=ROOT/'references/upstream_v0_1_appearance_c15_scene.json'
lower_source=ROOT/'source/lower_modular_components_b6.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
upstream=Path('/home/ethan/Projects/Sai_Rotbots/robots/gorilla_v0_1/cad/source')
assert sha(upper_source)==sha(upstream/'appearance_c.blend')
assert sha(upper_json)==sha(upstream/'appearance_c_scene.json')
assert sha(upper_json)=='7a1e49f45838303ca5fd86265dc9980c10cde85ed7626424136afd3863aa5886'
data=json.loads(upper_json.read_text()); parts={p['name']:p for p in data['parts']}
bpy.ops.wm.open_mainfile(filepath=str(upper_source))
assert bpy.context.scene.get('source_scene_sha256')==sha(upper_json)

def coords(obj):
    v=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',v)
    m=np.asarray(obj.matrix_world);return v.reshape(-1,3)@m[:3,:3].T+m[:3,3]

def mesh_identity(obj):
    v=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',v)
    indices=np.asarray([i for p in obj.data.polygons for i in p.vertices],dtype=np.int64)
    counts=np.asarray([len(p.vertices) for p in obj.data.polygons],dtype=np.int64)
    return hashlib.sha256(v.tobytes()+counts.tobytes()+indices.tobytes()).hexdigest()

def is_upper(body):
    return body=='torso' or any(k in body for k in ('upper_arm','forearm','palm','finger','thumb'))

native=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name in parts]
assert len(native)==len(parts),(len(native),len(parts))
upper=[o for o in native if is_upper(parts[o.name]['body'])]
identities={o.name:mesh_identity(o) for o in upper}
original_world={o.name:coords(o) for o in upper}
for obj in list(bpy.context.scene.objects):
    if obj not in upper:bpy.data.objects.remove(obj,do_unlink=True)
upper_shift=-.240
for obj in upper:
    obj.matrix_world=Matrix.Translation((0,0,upper_shift))@obj.matrix_world
    obj['source_scene_sha256']=sha(upper_json);obj['source_original_name']=obj.name
    obj['source_scope']='Exact evaluated engineering C15 upper mesh; only shared rigid Z placement'
    obj.color=tuple(parts[obj.name]['rgba'])

with bpy.data.libraries.load(str(lower_source),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n.startswith('L_')]
loaded=[o for o in dst.objects if o]
for obj in loaded:bpy.context.collection.objects.link(obj)
bpy.context.view_layer.update()
left=[o for o in loaded if o.type=='MESH']
lower_matrices={o.name:o.matrix_world.copy() for o in left}
lower_world={o.name:coords(o) for o in left}
lower_low=np.concatenate(list(lower_world.values())).min(0)
hip=np.asarray(json.loads((ROOT/'lower_modular_components_b6.json').read_text())['joints']['hip'])
candidate_hip_z=1.660+upper_shift
scale=float(candidate_hip_z/(hip[2]-lower_low[2]))
# +X forward,+Y left,+Z up, matching the actual engineering model.
# The enlarged crouched thigh requires appearance spacing distinct from C15.
hip_lateral=.380
tx=-.045+scale*hip[1];ty=hip_lateral-scale*hip[0];tz=-scale*float(lower_low[2])
placement=Matrix(((0,-scale,0,tx),(scale,0,0,ty),(0,0,scale,tz),(0,0,0,1)))
reflection=Matrix.Diagonal((1,-1,1,1))
lower_pairs=[]
for obj in left:
    obj.parent=None;obj.matrix_parent_inverse=Matrix.Identity(4)
    obj.matrix_world=placement@lower_matrices[obj.name]
    obj['source_scope']='Exact Art B6 neutral component, uniform placement only; candidate registration'
    obj['source_blend_sha256']=sha(lower_source)
    # Guide module colors only; the selected artwork remains the color authority.
    if any(k in obj.name for k in ('main_shell','rear_hip_cover','front_side_shell','hock_rear_guard')):obj.color=(.015,.41,.79,1)
    elif 'foot_central' in obj.name:obj.color=(.84,.84,.80,1)
    elif any(k in obj.name for k in ('service_panel','lateral_panel','hip_panel')):obj.color=(.08,.50,.87,1)
    elif 'knee_front_shield' in obj.name:obj.color=(.99,.58,.04,1)
    else:obj.color=(.09,.115,.13,1)
    twin=obj.copy();twin.data=obj.data;twin.name=obj.name.replace('L_','R_',1)
    bpy.context.collection.objects.link(twin);twin.matrix_world=reflection@obj.matrix_world
    lower_pairs.append((obj,twin))
for obj in loaded:
    if obj.type!='MESH':bpy.data.objects.remove(obj,do_unlink=True)
bpy.context.view_layer.update()
upper_check=[]
for obj in upper:
    expected=original_world[obj.name]+[0,0,upper_shift]
    upper_check.append({'name':obj.name,'mesh_data_unchanged':mesh_identity(obj)==identities[obj.name],
                        'rigid_placement_vertex_error_max_m':float(abs(expected-coords(obj)).max())})
upper_mirror=[]
by_name={o.name:o for o in upper}
for obj in upper:
    if not obj.name.startswith('left_'):continue
    right=by_name.get(obj.name.replace('left_','right_',1))
    if not right:continue
    expected=coords(obj);expected[:,1]*=-1;actual=coords(right)
    error=float(cKDTree(actual).query(expected,k=1)[0].max())
    upper_mirror.append({'left':obj.name,'right':right.name,'maximum_nearest_vertex_mirror_error_m':error})
lower_mirror=[]
for l,r in lower_pairs:
    expected=coords(l);expected[:,1]*=-1
    lower_mirror.append({'left':l.name,'right':r.name,'shared_mesh':l.data==r.data,
                         'maximum_vertex_mirror_error_m':float(abs(expected-coords(r)).max())})
asset=upper+[o for pair in lower_pairs for o in pair]
world=np.concatenate([coords(o) for o in asset]);low=world.min(0);high=world.max(0)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO';scene.display.shading.studio_light='paint.sl'
scene.display.shading.color_type='OBJECT';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.show_object_outline=True;scene.display.shading.object_outline_color=(.07,.09,.10)
scene.display.shading.background_type='WORLD';scene.world.color=(1,1,1)
scene.render.film_transparent=False;scene.view_settings.view_transform='Standard';scene.view_settings.exposure=0
scene.render.resolution_x=scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.object.camera_add();camera=bpy.context.object;camera.name='Native_C15_upper_Art_lower_orthographic_camera'
camera.data.type='ORTHO';scene.camera=camera
center=Vector(((low+high)/2).tolist());common_scale=float(max(high-low)*1.18);views={}
for name,axis in [('top',(0,0,1)),('front',(1,0,0)),('left',(0,1,0)),('rear',(-1,0,0))]:
    camera.location=center+Vector(axis)*8
    if name=='top':camera.rotation_euler=(0,0,math.pi/2) # +X forward maps to page bottom.
    else:camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    inverse=np.asarray(camera.matrix_world.inverted());pv=world@inverse[:3,:3].T+inverse[:3,3]
    span=np.ptp(pv[:,:2],axis=0);offset=(pv[:,:2].min(0)+pv[:,:2].max(0))/2;basis=np.asarray(camera.matrix_world)[:3,:3]
    camera.location+=Vector((basis[:,0]*offset[0]+basis[:,1]*offset[1]).tolist())
    camera.data.ortho_scale=float(max(span)*1.17) if name=='top' else common_scale
    scene.render.filepath=str(ROOT/f'images/native_c15_upper_{name}_p22.png')
    bpy.ops.render.render(write_still=True)
    views[name]={'image':f'images/native_c15_upper_{name}_p22.png','camera_type':camera.data.type,
                 'camera_matrix_world':np.asarray(camera.matrix_world).tolist(),'ortho_scale':camera.data.ortho_scale,
                 'projected_geometric_span_m':span.tolist()}
    print('ACTUAL_C15_UPPER_VIEW',name,flush=True)
out=ROOT/'source/v0_1_upper_art_lower_registration_p22.blend'
scene['upper_source_scene_sha256']=sha(upper_json);scene['appearance_accepted']=False;scene['physics_accepted']=False
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
source_entries=[{'original_path':str(upstream/'appearance_c.blend'),'local_snapshot':str(upper_source.relative_to(ROOT)),'sha256':sha(upper_source)},
                {'original_path':str(upstream/'appearance_c_scene.json'),'local_snapshot':str(upper_json.relative_to(ROOT)),'sha256':sha(upper_json)},
                {'original_path':str(lower_source),'sha256':sha(lower_source)}]
report={'revision':'p22','source':str(out.relative_to(ROOT)),'source_sha256':sha(out),
        'upstream_task':{'thread_id':'01a0fa4c-3989-7342-8b07-da32d3a9129f','title':'Gorilla 硬件工程','read_before_reliance':True},
        'sources':source_entries,'original_source_part_count':len(parts),'upper_source_part_count':len(upper),
        'upper_rigid_z_translation_m':upper_shift,'upper_no_shape_changes':all(c['mesh_data_unchanged'] and c['rigid_placement_vertex_error_max_m']<1e-6 for c in upper_check),
        'upper_preservation_checks':upper_check,'upstream_upper_mirror_checks':upper_mirror,
        'upper_mirror_error_max_m':max(c['maximum_nearest_vertex_mirror_error_m'] for c in upper_mirror),
        'lower_source':'source/lower_modular_components_b6.blend','lower_uniform_placement_matrix':np.asarray(placement).tolist(),
        'lower_scale':scale,'lower_hip_candidate_world_m':[-.045,hip_lateral,candidate_hip_z],
        'lower_shared_mesh_mirror':all(m['shared_mesh'] and m['maximum_vertex_mirror_error_m']<1e-7 for m in lower_mirror),
        'lower_mirror_checks':lower_mirror,'bounds_world_m':[low.tolist(),high.tolist()],
        'candidate_height_m':float(high[2]-low[2]),'views':views,
        'same_source_top_front_width_error_m':abs(views['top']['projected_geometric_span_m'][0]-views['front']['projected_geometric_span_m'][0]),
        'same_source_top_left_depth_error_m':abs(views['top']['projected_geometric_span_m'][1]-views['left']['projected_geometric_span_m'][0]),
        'scope':'Appearance projection registration. Actual engineering upper meshes unchanged; existing Art lower same-source mirrored candidate. Engineering joints and physical parameters are not adopted or modified.',
        'upper_upstream_appearance_or_physics_accepted':False,'whole_body_collision_checked':False,
        'lower_known_self_surface_defects_remain':True,'whole_v0_2_qualified':False,'ready_for_engineering_handoff':False}
(ROOT/'actual_v0_1_upper_registration_p22.json').write_text(json.dumps(report,indent=2)+'\n')
print('ACTUAL_UPPER_REUSE',len(upper),report['upper_no_shape_changes'],report['upper_mirror_error_max_m'],report['lower_shared_mesh_mirror'],flush=True)
