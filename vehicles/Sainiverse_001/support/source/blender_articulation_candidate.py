"""Editable candidate with grouped motion previews; no simulated pose claim."""
import bpy,gzip,json,math
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1]/'candidates/r015_articulation'
a=json.loads(gzip.decompress((ROOT/'source/assembly.json.gz').read_bytes()))
poses=json.loads((ROOT/'source/preview_poses.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mats={}
for name,hex_ in a['colors'].items():
    rgb=[int(hex_[i:i+2],16)/255 for i in (0,2,4)]
    rgba=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]+[1.]
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=rgba
    bsdf=m.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=rgba
    bsdf.inputs['Metallic'].default_value=.6 if name in ['silver','steel'] else .08
    bsdf.inputs['Roughness'].default_value=.38 if name=='silver' else .55;mats[name]=m
parents={}
for group,pivot in a['groups'].items():
    obj=bpy.data.objects.new(group,None);bpy.context.collection.objects.link(obj);obj.location=pivot
    obj.empty_display_type='PLAIN_AXES';obj.empty_display_size=.5;parents[group]=obj
objects=[]
for p in a['parts']:
    pivot=Vector(a['groups'][p['group']]);mesh=bpy.data.meshes.new(p['name'])
    mesh.from_pydata([Vector(v)-pivot for v in p['vertices']],[],p['faces']);mesh.materials.append(mats[p['material']]);mesh.update()
    obj=bpy.data.objects.new(p['name'],mesh);bpy.context.collection.objects.link(obj);obj.parent=parents[p['group']]
    obj['motion_group']=p['group'];obj['assembly']=p['assembly'];objects.append(obj)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False
scene.render.resolution_x=1440;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.world.use_nodes=True;bg=scene.world.node_tree.nodes['Background'];bg.inputs[0].default_value=(.55,.62,.70,1);bg.inputs[1].default_value=.65
scene.view_settings.view_transform='Filmic';scene.view_settings.look='Medium High Contrast'
for pos,energy,size in [((-10,-20,40),18000,25),((-40,12,30),14000,20)]:
    data=bpy.data.lights.new('StudioArea','AREA');data.energy=energy;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new('StudioArea',data);bpy.context.collection.objects.link(obj);obj.location=pos
    obj.rotation_euler=(Vector((-22,0,6.5))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('CandidateCamera');camera=bpy.data.objects.new('CandidateCamera',data);bpy.context.collection.objects.link(camera);scene.camera=camera;data.type='ORTHO'
def set_pose(name):
    for group,obj in parents.items():
        motion=group if group in poses[name] else 'front' if group.startswith('front') else 'rear'
        obj.matrix_world=Matrix(poses[name][motion])@Matrix.Translation(Vector(a['groups'][group]))
def view(pos,target,scale):
    camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
def render(name):
    scene.render.filepath=str(ROOT/'reports'/f'{name}.png');bpy.ops.render.render(write_still=True)
for frame,name in [(1,'retracted'),(50,'extended'),(100,'left45'),(150,'right45'),(200,'terrain_pose')]:
    set_pose(name)
    for obj in parents.values():
        obj.keyframe_insert('location',frame=frame);obj.keyframe_insert('rotation_euler',frame=frame)
scene.frame_end=200;scene.frame_set(1);set_pose('retracted')
scene['preview_scope']='Kinematic assembly preview, not a driving simulation. Independent native bench evidence is in reports/articulation_r015.'
view((-7,-16,14),(-20,0,6.5),22)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/Leviathan_003_r015_candidate.blend'))
# Mechanism only: avoid deck occlusion while preserving a complete native file.
for obj in objects:obj.hide_render=obj['assembly']!='articulation_r015' and not obj.name.endswith('_coupling_deck_mount')
view((-31,-18,13),(-20,0,6.5),20);render('coupling_retracted')
scene.frame_set(100);set_pose('left45');bpy.context.view_layer.update()
relative=parents['front'].matrix_world.inverted()@parents['rear'].matrix_world
assert abs(math.degrees(math.atan2(relative[1][0],relative[0][0]))-45)<1e-4
assert abs(parents['hitch_slide'].matrix_world.translation.x+25)<1e-4
view((-34,-20,14),(-24,0,6.5),23);render('coupling_left45')
for obj in objects:obj.hide_render=False
view((-110,-110,120),(-15,0,10),115);render('whole_left45')
print('ARTICULATION_CANDIDATE_RENDER_COMPLETE')
