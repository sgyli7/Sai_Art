"""Editable full assembly plus clearly identified mechanical inspection views."""
import bpy,gzip,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'candidates/r021_track_tension'
a=json.loads(gzip.decompress((OUT/'source/assembly.json.gz').read_bytes()))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mats={}
for name,h in a['colors'].items():
    rgb=[int(h[i:i+2],16)/255 for i in [0,2,4]];rgba=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]+[1.]
    mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=rgba
    shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=rgba;shader.inputs['Metallic'].default_value=.5 if name in ['silver','steel'] else .08;shader.inputs['Roughness'].default_value=.4 if name=='silver' else .55;mats[name]=mat
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
    obj=bpy.data.objects.new(p['name'],mesh);bpy.context.collection.objects.link(obj);obj.parent=parents[owner];obj['physical_body']=owner;obj['motion_kind']=motion['kind'];obj['source_group']=p['group']
    if any(t in p['name'] for t in ['barrel','piston','gland','clamp']):
        mesh.use_auto_smooth=True;mesh.auto_smooth_angle=math.radians(40)
        for face in mesh.polygons:face.use_smooth=True
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False
scene.render.resolution_x=1440;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.62,.70,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
scene.view_settings.view_transform='Filmic';scene.view_settings.look='Medium High Contrast'
for pos,energy,size in [((10,-22,15),5500,10),((15,-8,15),3500,8)]:
    data=bpy.data.lights.new('InspectionLight','AREA');data.energy=energy;data.size=size;obj=bpy.data.objects.new('InspectionLight',data);bpy.context.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(Vector((10.5,-13.55,2.))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('InspectionCamera');camera=bpy.data.objects.new('InspectionCamera',data);bpy.context.collection.objects.link(camera);scene.camera=camera;data.type='ORTHO'
def view(pos,target,scale):camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
scene['scope']='Editable complete neutral three-section assembly: 72 road-wheel and 24 idler physical parents. Recoil hardware is provisional packaging. Dynamic elastic belt path is driven in native Godot; neutral Blender cleats retain original authored path.'
view((24,-30,12),(10.5,-11.8,2.5),17)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'source/Leviathan_003_tensioned_tracks.blend'))

group='front_bogie_fore_right';pivot=Vector(a['groups'][group])
for obj in bpy.data.objects:
    if obj.type!='MESH':continue
    obj.hide_render=obj.get('source_group')!=group
    if obj.hide_render:continue
    center=obj.matrix_world@(sum((v.co for v in obj.data.vertices),Vector())/len(obj.data.vertices))
    if center.y>=pivot.y-.7:obj.hide_render=True
    if obj.get('motion_kind')=='belt':obj.hide_render=True
    if any(k in obj.name for k in ['fender','service_rail','center_platform','bogie_end_housing']):obj.hide_render=True
    if '_idler_' in obj.get('physical_body','') and obj.get('motion_kind')=='wheel':obj.hide_render=True
    if obj.name.endswith('track_inner_frame') and center.y>pivot.y-1.75:obj.hide_render=True
view((20,-6,6),(14,-12.6,2.4),6.5)
scene['inspection_view']='Belts, idler drums, central covers, opposite belt and near frame plate hidden to expose recoil cartridges, rods, yoke and guide. Neutral packaging, not dynamic simulation.'
scene.render.filepath=str(OUT/'reports/idler_recoil_cutaway.png');bpy.ops.render.render(write_still=True)
print('IDLER_NATIVE_MODEL_COMPLETE')
