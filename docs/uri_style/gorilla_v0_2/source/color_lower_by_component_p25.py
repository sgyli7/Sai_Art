"""Assign one color per existing B7 component, preserving its mesh and pose.

The original user-selected B7 gray model is retained separately. This derivative
adds module materials only, and exports a matching GLB. It does not repair or
qualify B7's previously recorded topology defects.
"""
from pathlib import Path
import sys, json, hashlib, math
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy, numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/lower_modular_components_b7.blend'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith(('L_','R_'))]
left=[o for o in objects if o.name.startswith('L_')]

def identity(o):
    v=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',v)
    loops=np.empty(len(o.data.loops),np.int32);o.data.loops.foreach_get('vertex_index',loops)
    count=np.empty(len(o.data.polygons),np.int32);o.data.polygons.foreach_get('loop_total',count)
    return hashlib.sha256(v.tobytes()+loops.tobytes()+count.tobytes()).hexdigest()

def world(o):
    v=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',v)
    m=np.asarray(o.matrix_world);return v.reshape(-1,3)@m[:3,:3].T+m[:3,3]

prior={o.name:identity(o) for o in left}
prior_pose={o.name:np.asarray(o.matrix_world).copy() for o in objects}
palette={'blue':'098FE0','orange':'FFB128','ivory':'F3ECDF','frame':'27343F','metal':'8999A4','rubber':'202830'}
def linear(s):
    q=int(s,16)/255;return q/12.92 if q<=.04045 else ((q+.055)/1.055)**2.4
materials={}
for name,hx in palette.items():
    rgb=tuple(linear(hx[k:k+2]) for k in (0,2,4))
    m=bpy.data.materials.new('uri_module_'+name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*rgb,1)
    p.inputs['Roughness'].default_value=.38 if name in ('blue','orange','ivory') else .42
    p.inputs['Metallic'].default_value=.55 if name=='metal' else .08
    m.diffuse_color=(*rgb,1);materials[name]=m

def allocation(name):
    part=name[2:]
    if part in ('knee_front_shield','hock_rear_guard','hock_rear_service_panel'):return 'orange'
    if any(q in part for q in ('main_shell','lateral_panel','hip_cover','hip_panel','thigh_front_service_panel','shank_front_side_shell','shank_front_service_panel')):return 'blue'
    if 'side_cover_rim' in part:return 'orange'
    if 'side_cover' in part or 'common_axle' in part or 'rod' in part:return 'metal'
    return 'frame'

allocation_rows=[]
for o in left:
    key=allocation(o.name);o.data.materials.clear();o.data.materials.append(materials[key])
    # A single whole-component slot, never a threshold in height or face band.
    slots=np.zeros(len(o.data.polygons),np.int32);o.data.polygons.foreach_set('material_index',slots)
    o['uri_color_module']=key;o['uri_color_rule']='Entire named component; no horizontal face/height band'
    o.color=materials[key].diffuse_color
    twin=bpy.data.objects[o.name.replace('L_','R_',1)]
    assert twin.data==o.data,(o.name,'original shared mirror lost')
    twin.color=o.color;twin['uri_color_module']=key;twin['uri_color_rule']=o['uri_color_rule']
    allocation_rows.append({'left':o.name,'right':twin.name,'color_module':key,'srgb_hex':palette[key],
                            'mesh_shared':True,'mesh_geometry_sha256':prior[o.name],
                            'kinematic_owner':o.get('kinematic_owner'),'role':o.get('component_role'),
                            'whole_component_material_slot_count':len(o.data.materials)})
assert all(identity(o)==prior[o.name] for o in left)
assert all(np.array_equal(np.asarray(o.matrix_world),prior_pose[o.name]) for o in objects)
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
for o in bpy.context.scene.objects:
    if o.type=='EMPTY' and o.name.startswith(('L_','R_')):o.select_set(True)
bpy.context.view_layer.objects.active=left[0]
export=ROOT/'exports/lower_modular_components_color_p25.glb';export.parent.mkdir(exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(export),export_format='GLB',use_selection=True,
                          export_yup=True,export_apply=False,export_materials='EXPORT',
                          export_cameras=False,export_lights=False)
out=ROOT/'source/lower_modular_components_color_p25.blend'
scene=bpy.context.scene;scene['source_B7_sha256']=sha(SOURCE)
scene['revision_scope']='Whole component color assignment only; original B7 geometry/pose retained'
scene['physics_accepted']=False;scene['engineering_ready']=False
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
print('MODULE_COLORS_AND_EXPORT_SAVED',len(left),flush=True)

# A native CPU render of only the knee assemblies illustrates the color rule.
# Upper body and rejected P22 assembly are never used here.
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=20
scene.cycles.use_denoising=False
scene.render.film_transparent=False;scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(1,1,1,1)
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.7
scene.view_settings.view_transform='Standard';scene.view_settings.exposure=0
scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
for o in list(scene.objects):
    if o.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(o,do_unlink=True)
for o in objects:o.hide_render=o.name.startswith('R_')
allv=np.concatenate([world(o)[::max(1,len(o.data.vertices)//16000)] for o in left])
center=Vector(((allv.min(0)+allv.max(0))/2).tolist())
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO'
camera.location=center+Vector((.80,-1.35,.65));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=.68;scene.camera=camera
for location,energy,size in [((1,-2,3),170,2),((-1,-1,1),75,1.8),((0,2,2),90,2)]:
    bpy.ops.object.light_add(type='AREA',location=center+Vector(location));l=bpy.context.object
    l.data.energy=energy;l.data.shape='DISK';l.data.size=size
    l.rotation_euler=(center-l.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(ROOT/'images/lower_module_color_guide_p25.png')
bpy.ops.render.render(write_still=True)
report={'revision':'p25','scope':'B7 material-only derivative; no geometry or articulation modification',
        'original_user_selected_model':'source/lower_modular_components_b7.blend','original_sha256':sha(SOURCE),
        'colored_source':str(out.relative_to(ROOT)),'colored_source_sha256':sha(out),
        'glb':str(export.relative_to(ROOT)),'glb_sha256':sha(export),
        'module_color_guide':'images/lower_module_color_guide_p25.png',
        'geometry_bytes_unchanged':True,'pose_matrices_unchanged':True,
        'paired_components_shared_mesh':True,'allocation':allocation_rows,'palette':palette,
        'known_original_geometry_report':'lower_modular_components_b7.json',
        'existing_topology_defects_repaired':False,'engineering_ready':False,'whole_v0_2_qualified':False}
(ROOT/'lower_component_color_p25.json').write_text(json.dumps(report,indent=2)+'\n')
print('WHOLE_COMPONENT_COLOR_GUIDE_SAVED',flush=True)
