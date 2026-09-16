"""Editable full assembly plus clearly identified mechanical inspection views."""
import bpy,gzip,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'candidates/r023_interior'
a=json.loads(gzip.decompress((OUT/'source/assembly.json.gz').read_bytes()))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mats={}
for name,h in a['colors'].items():
    rgb=[int(h[i:i+2],16)/255 for i in [0,2,4]];rgba=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]+[1.]
    mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=rgba
    shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=rgba;shader.inputs['Metallic'].default_value=.5 if name in ['silver','steel'] else .08;shader.inputs['Roughness'].default_value=.4 if name=='silver' else .55
    props=a.get('material_properties',{}).get(name,{})
    if 'alpha' in props:shader.inputs['Transmission Weight'].default_value=.8;shader.inputs['IOR'].default_value=1.45;shader.inputs['Roughness'].default_value=props['roughness']
    if 'emissive' in props:shader.inputs['Emission Color'].default_value=[*props['emissive'],1];shader.inputs['Emission Strength'].default_value=2.0
    mats[name]=mat
parents={};world_origins={};wheel_parents={}
for name,pivot in a['groups'].items():
    obj=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(obj);obj.location=pivot;obj['physical_body']=name;parents[name]=obj;world_origins[name]=Vector(pivot)
    if '_bogie_' in name:
        for side in [-1,1]:
            for index,(x,z) in enumerate([(-2.55,1.15),(0,1.18),(2.55,1.15),(4.15,2.4)],start=1):
                key=name+(f'_idler_{"left" if side>0 else "right"}' if index==4 else f'_wheel_{"left" if side>0 else "right"}_{index}')
                w=bpy.data.objects.new(key,None);bpy.context.collection.objects.link(w);w.parent=obj;w.location=(x,side*1.75,z-pivot[2]);w['physical_body']=key;w['joint']='X slide, -0.32 to +0.24 m' if index==4 else 'vertical slide, -0.35 to +0.35 m';w['neutral_local_z']=w.location.z;wheel_parents[key]=w;parents[key]=w;world_origins[key]=Vector((pivot[0]+x,pivot[1]+side*1.75,z))
for p in a['parts']:
    owner=p['group'];motion=p['motion'];index=motion.get('index',0)
    if motion['kind'] in ['wheel','wheel_slide'] and index in [1,2,3]:
        side='left' if sum(v[1] for v in p['vertices'])/len(p['vertices'])>a['groups'][owner][1] else 'right'
        owner+=f'_wheel_{side}_{index}'
    if p.get('physical_body','').find('_idler_')>=0:owner=p['physical_body']
    mesh=bpy.data.meshes.new(p['name']);mesh.from_pydata([Vector(v)-world_origins[owner] for v in p['vertices']],[],p['faces']);mesh.materials.append(mats[p['material']]);mesh.update()
    obj=bpy.data.objects.new(p['name'],mesh);bpy.context.collection.objects.link(obj);obj.parent=parents[owner];obj['physical_body']=owner;obj['motion_kind']=motion['kind'];obj['source_group']=p['group'];obj['interior_category']=p.get('interior_category','');obj['source_name']=p['name']
    if any(t in p['name'] for t in ['barrel','piston','gland','clamp']):
        mesh.use_auto_smooth=True;mesh.auto_smooth_angle=math.radians(40)
        for face in mesh.polygons:face.use_smooth=True
# Robot figures are actual source meshes. Kept in an explicitly separate
# inspection collection and excluded from the vehicle neutral export.
figures=json.loads(gzip.decompress((OUT/'source/robot_scale_figures.json.gz').read_bytes()))
inspection=bpy.data.collections.new('INSPECTION / actual robots at home pose');bpy.context.scene.collection.children.link(inspection)
placements={'sai':(20.55,1.75,11.35),'microduck':(21.30,1.85,11.35)}
for name,figure in figures.items():
    x,y,z=placements[name];z-=figure['bounds_root_m'][0][2]
    base=bpy.data.objects.new('SCALE ONLY / '+name,None);inspection.objects.link(base);base.location=(x,y,z);base.rotation_euler.z=math.pi/2;base['scope']='Actual robot visual home pose, not trained or simulated here'
    for i,p in enumerate(figure['parts']):
        mesh=bpy.data.meshes.new(f'{name}_{i}');mesh.from_pydata(p['vertices'],[],p['faces']);mesh.update()
        mat=bpy.data.materials.new(f'{name}_{i}');mat.diffuse_color=p['rgba'];mat.use_nodes=True;shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=p['rgba'];shader.inputs['Roughness'].default_value=.55;mesh.materials.append(mat)
        obj=bpy.data.objects.new(f'{name}_{i}',mesh);inspection.objects.link(obj);obj.parent=base
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False;scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.6,.7,.8,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
scene.view_settings.view_transform='Filmic';scene.view_settings.look='Medium High Contrast'
def light(name,pos,target,power,size):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size;obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
for x in [19.8,24.5,29.2]:light('Cabin area light',(x,0,14.40),(x,0,11.4),190,3.5)
light('Studio',(-10,-50,80),(-20,0,9),95000,70)
data=bpy.data.cameras.new('InteriorReview');camera=bpy.data.objects.new('InteriorReview',data);bpy.context.collection.objects.link(camera);scene.camera=camera;data.clip_end=3000

def view(pos,target,lens=28):
    data.type='PERSP';data.lens=lens;camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
view((18.6,-.45,12.30),(32.7,0,12.05),25)
scene['scope']='Complete three-module neutral model with hollow bridge and robot-height interior. Doors closed transport geometry. Inspection robots are real home-pose visuals only; no boarding, reach or policy claim.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'source/Leviathan_003_interior.blend'))
scene.render.filepath=str(OUT/'reports/cabin_aisle.png');bpy.ops.render.render(write_still=True)
view((23.15,-.1,12.12),(20.95,2.45,11.82),34);scene.render.filepath=str(OUT/'reports/cabin_robot_workbench.png');bpy.ops.render.render(write_still=True)
# A clearly identified roof cutaway, without deleting anything from the source.
for obj in bpy.data.objects:
    if obj.type!='MESH':continue
    name=obj.get('source_name','');cat=obj.get('interior_category','')
    if name.endswith(('bridge_shell','bridge_roof')) or 'bridge_roof_' in name or cat=='ceiling':obj.hide_render=True
view((29,-18,28),(25,0,11.7),43);data.type='ORTHO';data.ortho_scale=23
scene.render.filepath=str(OUT/'reports/cabin_plan_cutaway.png');bpy.ops.render.render(write_still=True)
print('INTERIOR_NATIVE_MODEL_COMPLETE')
