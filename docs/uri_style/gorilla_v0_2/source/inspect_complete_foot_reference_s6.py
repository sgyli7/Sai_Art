"""Native inspection of detailed foot reconstruction, before adopting it."""
from pathlib import Path
import sys, math, hashlib, json, time
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'generated/complete_foot_reference_s6_00001_.glb'
START=time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
m=bpy.data.materials.new('foot_reference_clay');m.use_nodes=True
p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(.36,.40,.43,1)
p.inputs['Roughness'].default_value=.55
records=[];points=[]
for index,o in enumerate(meshes):
    o.name=f'complete_foot_highpoly_{index}'
    o.data.materials.clear();o.data.materials.append(m)
    for f in o.data.polygons:f.use_smooth=True
    v=np.empty(len(o.data.vertices)*3,dtype=np.float32)
    o.data.vertices.foreach_get('co',v);v=v.reshape(-1,3)
    mt=np.asarray(o.matrix_world);w=v@mt[:3,:3].T+mt[:3,3]
    points.append(w)
    records.append({'name':o.name,'vertices':len(v),'faces':len(o.data.polygons),
                    'bounds_xyz':[w.min(0).tolist(),w.max(0).tolist()]})
world=np.concatenate(points);lo,hi=world.min(0),world.max(0)
np.savez_compressed(ROOT/'source/complete_foot_vertex_sample_s6.npz',vertices=world[::max(1,len(world)//200000)])
center=Vector(((lo+hi)/2).tolist())
scene=bpy.context.scene;scene.render.engine='CYCLES'
scene.cycles.samples=20;scene.cycles.use_denoising=False
scene.render.use_persistent_data=True
scene.render.resolution_x=1000;scene.render.resolution_y=1100
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=True
scene.view_settings.view_transform='Standard';scene.view_settings.exposure=-.15
scene.world=bpy.data.worlds.new('reference_world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
for name,location,energy,size in [('key',(2,-3,4),150,3),('fill',(-2,-1,2),70,3),('rim',(1,3,3),100,3)]:
    bpy.ops.object.light_add(type='AREA',location=location)
    lamp=bpy.context.object;lamp.name=name;lamp.data.energy=energy;lamp.data.size=size
    lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object
camera.data.type='ORTHO';camera.data.ortho_scale=float(max(hi-lo)*1.22);scene.camera=camera
views=[]
for name,yaw in [('input_direction',0),('turn_45',45),('turn_90',90),('turn_180',180)]:
    a=math.radians(yaw);camera.location=center+Vector((math.sin(a),-math.cos(a),.08))*3
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    out=ROOT/'images'/f'complete_foot_reference_{name}_s6.png'
    scene.render.filepath=str(out);bpy.ops.render.render(write_still=True)
    views.append({'name':name,'image':str(out.relative_to(ROOT)),
                  'camera_eye':list(camera.location),'camera_target':list(center)})
    print('DETAILED_FOOT_REFERENCE_VIEW',name,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/complete_foot_reference_highpoly_s6.blend'),compress=True)
record={
 'source_glb':str(SOURCE.relative_to(ROOT)),
 'source_glb_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'native_import_transform':'glTF(x,y,z)->Blender(x,-z,y)',
 'parts':records,'bounds_xyz':[lo.tolist(),hi.tolist()],'views':views,
 'geometry_edits':[],'all_views_same_native_geometry':True,
 'scope':'Raw detailed reference reconstruction inspection; no adoption or Gorilla thigh replacement',
 'appearance_accepted':False,'engineering_ready':False,
 'elapsed_seconds':time.time()-START,
}
(ROOT/'complete_foot_native_inspection_s6.json').write_text(json.dumps(record,indent=2)+'\n')
print('DETAILED_FOOT_NATIVE_INSPECTION_COMPLETE',json.dumps(records),flush=True)
