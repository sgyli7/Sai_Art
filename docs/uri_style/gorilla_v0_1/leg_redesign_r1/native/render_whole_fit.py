"""Render the same finite whole-fit source from orthographic cameras."""
from pathlib import Path
import hashlib
import json
import bpy
from mathutils import Matrix, Vector

O=Path(__file__).resolve().parent
P=O/'whole_fit_scene.json'
s=json.loads(P.read_text());sha=hashlib.sha256(P.read_bytes()).hexdigest()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for p in s['parts']:
    mesh=bpy.data.meshes.new(p['name']);mesh.from_pydata(p['vertices_world_m'],[],p['faces']);mesh.update()
    obj=bpy.data.objects.new(p['name'],mesh);bpy.context.collection.objects.link(obj)
    mat=bpy.data.materials.new(p['name']+'_material');mat.diffuse_color=p['rgba'];mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=p['rgba']
    shader.inputs['Metallic'].default_value=.30 if p['role']!='contact_pad' else 0
    shader.inputs['Roughness'].default_value=.48
    obj.data.materials.append(mat)
    obj['body_owner']=p['body'];obj['source_sha256']=sha
    for f in mesh.polygons:f.use_smooth=False
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=False
scene.render.resolution_x=1000;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.86,.9,.94,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.75
scene.view_settings.view_transform='Standard'
lo,hi=s['reference_bounds_m'];cx=(lo[0]+hi[0])/2;cz=(lo[2]+hi[2])/2
def area(name,location,power,size):
    bpy.ops.object.light_add(type='AREA',location=location);o=bpy.context.object;o.name=name
    o.data.energy=power;o.data.shape='DISK';o.data.size=size
    o.rotation_euler=(Vector((cx,0,cz))-o.location).to_track_quat('-Z','Y').to_euler()
area('key',(3,-3,5),700,4);area('fill',(-3,3,4),550,4)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.002));floor=bpy.context.object;floor.name='render_floor_only'
m=bpy.data.materials.new('render_floor');m.diffuse_color=(.96,.97,.98,1);floor.data.materials.append(m)
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';scene.camera=cam
scale=max(hi[2]-lo[2],(hi[1]-lo[1])*1.2)*1.20
views={'front':((6,0,cz),(cx,0,cz)), 'left':((cx,6,cz),(cx,0,cz)),
       'rear':((-6,0,cz),(cx,0,cz)), 'top':((cx,0,7),(cx,0,0)),
       'three_quarter':((3.5,5,3),(cx,0,cz))}
manifest={'source_sha256':sha,'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'same_source_for_all_views':True,'no_mesh_shape_edits':True,
          'physical_accepted':False,'appearance_accepted':False,
          'upperbody_is_unaccepted_C15_approximation':True,'renders':[]}
for name,(location,target) in views.items():
    cam.location=location;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=scale
    if name=='top':
        cam.data.ortho_scale=max(hi[1]-lo[1],(hi[0]-lo[0])*1.2)*1.2
    scene.render.filepath=str(O/('whole_fit_'+name+'.png'));bpy.ops.render.render(write_still=True)
    manifest['renders'].append({'name':name,'camera':location,'target':target,
                                'orthographic_scale_m':cam.data.ortho_scale,'pose_sample':0})
bpy.ops.wm.save_as_mainfile(filepath=str(O/'whole_fit_candidate.blend'))
T=s['poses'][-1]['body_transforms']
for obj in bpy.data.objects:
    if obj.get('body_owner') in T:obj.matrix_world=Matrix(T[obj['body_owner']])
location,target=views['left'];cam.location=location;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.ortho_scale=scale
scene.render.filepath=str(O/'whole_fit_deep_crouch_left.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'whole_fit_deep_crouch.blend'))
manifest['renders'].append({'name':'deep_crouch_left','pose_sample':s['poses'][-1]['sample'],
                            'camera':location,'target':target,'orthographic_scale_m':scale})
(O/'whole_fit_render_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
