"""Native editable four-crane packaging assembly and neutral review views."""
import bpy,gzip,json
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]/'candidates/r016_modular'
a=json.loads(gzip.decompress((ROOT/'source/assembly.json.gz').read_bytes()))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
materials={}
for name,h in a['colors'].items():
    rgb=[int(h[i:i+2],16)/255 for i in [0,2,4]];rgba=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]+[1.]
    mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=rgba
    bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=rgba
    bsdf.inputs['Metallic'].default_value=.6 if name in ['silver','steel'] else .08
    bsdf.inputs['Roughness'].default_value=.38 if name=='silver' else .55;materials[name]=mat
parents={}
for group,pivot in a['groups'].items():
    obj=bpy.data.objects.new(group,None);bpy.context.collection.objects.link(obj);obj.location=pivot;parents[group]=obj
for part in a['parts']:
    pivot=Vector(a['groups'][part['group']]);mesh=bpy.data.meshes.new(part['name'])
    mesh.from_pydata([Vector(v)-pivot for v in part['vertices']],[],part['faces']);mesh.materials.append(materials[part['material']]);mesh.update()
    obj=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(obj);obj.parent=parents[part['group']]
    obj['assembly']=part['assembly'];obj['motion_group']=part['group']
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False
scene.render.resolution_x=1440;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.world.use_nodes=True;bg=scene.world.node_tree.nodes['Background'];bg.inputs[0].default_value=(.55,.62,.70,1);bg.inputs[1].default_value=.65
scene.view_settings.view_transform='Filmic';scene.view_settings.look='Medium High Contrast'
for pos,energy,size in [((-10,-20,40),18000,25),((-50,20,40),22000,28)]:
    data=bpy.data.lights.new('StudioArea','AREA');data.energy=energy;data.shape='DISK';data.size=size
    obj=bpy.data.objects.new('StudioArea',data);bpy.context.collection.objects.link(obj);obj.location=pos
    obj.rotation_euler=(Vector((-35,0,10))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('ReviewCamera');camera=bpy.data.objects.new('ReviewCamera',data);bpy.context.collection.objects.link(camera);scene.camera=camera;data.type='ORTHO'
def view(pos,target,scale):
    camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
scene['scope']='Static four-crane packaging candidate. Existing inner stages retracted 1.7 m, service ladders relocated inboard. No operating reach, lifting dynamics, container trailer or manufacturing rating claim.'
view((-112,-122,116),(-15,0,11),112)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/Leviathan_003_four_cranes.blend'))
scene.render.filepath=str(ROOT/'reports/four_cranes_whole.png');bpy.ops.render.render(write_still=True)
view((-90,-70,75),(-42,0,12),65)
scene.render.filepath=str(ROOT/'reports/four_cranes_rear.png');bpy.ops.render.render(write_still=True)
print('FOUR_CRANE_NATIVE_REVIEW_COMPLETE')
