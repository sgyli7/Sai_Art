"""Blender renders actual candidate triangles; no AI correction or source edits."""
from pathlib import Path
import json, hashlib, math,sys
import bpy
from mathutils import Vector,Matrix

ROOT=Path(__file__).resolve().parent
SCENE=ROOT/(sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'candidate_scene.json')
PREFIX='assembled_' if SCENE.name=='assembled_scene.json' else ''
s=json.loads(SCENE.read_text());sha=hashlib.sha256(SCENE.read_bytes()).hexdigest()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for part in s['parts']:
    mesh=bpy.data.meshes.new(part['name']);mesh.from_pydata(part['vertices_world_m'],[],part['faces']);mesh.update()
    obj=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(obj)
    mat=bpy.data.materials.new(part['name']+'_material');mat.diffuse_color=part['rgba'];mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=part['rgba']
    shader.inputs['Metallic'].default_value=.35 if part['role']!='contact_pad' else 0
    shader.inputs['Roughness'].default_value=.43
    obj.data.materials.append(mat);obj['body_owner']=part['body'];obj['source_sha256']=sha
    for p in obj.data.polygons:p.use_smooth=False

scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False
scene.render.resolution_x=1000;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.world.color=(.8,.8,.8);scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.75,.80,.86,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
scene.view_settings.view_transform='Standard'
def area(name,location,power,size):
    bpy.ops.object.light_add(type='AREA',location=location);o=bpy.context.object;o.name=name
    o.data.energy=power;o.data.shape='DISK';o.data.size=size
    o.rotation_euler=(Vector((0,.5,.8))-o.location).to_track_quat('-Z','Y').to_euler()
area('key',(3,-2,4),450,3);area('fill',(-2,3,3),300,3)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.002));ground=bpy.context.object;ground.name='render_floor_only'
m=bpy.data.materials.new('floor');m.diffuse_color=(.92,.94,.96,1);ground.data.materials.append(m)
allv=[v for p in s['parts'] for v in p['vertices_world_m']]
cz=(min(v[2] for v in allv)+max(v[2] for v in allv))/2
cx=(min(v[0] for v in allv)+max(v[0] for v in allv))/2
bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=(max(v[2] for v in allv)-min(v[2] for v in allv))*1.18;scene.camera=cam
views={'left':((cx,6,cz),(cx,.5,cz)),'front':((6,.5,cz),(cx,.5,cz)),
       'three_quarter':((3.3,4.5,2.3),(cx,.5,cz))}
manifest={'source_sha256':sha,'render_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'no_modified_meshes':True,'physical_accepted':False,'renders':[]}
for name,(location,target) in views.items():
    cam.location=location;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(ROOT/(PREFIX+name+'.png'));bpy.ops.render.render(write_still=True)
    manifest['renders'].append({'name':name,'camera':location,'target':target,'orthographic_scale_m':cam.data.ortho_scale})
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(PREFIX+'candidate.blend')))
probe=json.loads((ROOT/'grounded_crouch_report.json').read_text())
if probe['source_sha256']!=s.get('parent_geometry_sha256',sha):raise ValueError('Crouch source hash differs')
T=probe['poses'][-1]['body_transforms']
for d in s.get('drivers',[]):
    A=Vector(d['A_neutral_world_m']);B=Vector(d['B_neutral_world_m'])
    a=Matrix(T[d['parent']])@A;b=Matrix(T[d['child']])@B
    R=(B-A).normalized().rotation_difference((b-a).normalized()).to_matrix().to_4x4()
    for owner,now,old in ((d['barrel_body'],a,A),(d['rod_body'],b,B)):
        tt=R.copy();tt.translation=now-(R@old);T[owner]=[list(row) for row in tt]
for obj in bpy.data.objects:
    if obj.get('body_owner') in T:obj.matrix_world=Matrix(T[obj['body_owner']])
cam.location=views['left'][0];cam.rotation_euler=(Vector(views['left'][1])-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(ROOT/(PREFIX+'deep_crouch_left.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(PREFIX+'deep_crouch.blend')))
manifest['deep_crouch_report_sha256']=hashlib.sha256((ROOT/'grounded_crouch_report.json').read_bytes()).hexdigest()
manifest['renders'].append({'name':'deep_crouch_left','body_transforms':T,'scope':'Same finite frame at grounded FK endpoint; drives and loads NOT passed.'})
(ROOT/(PREFIX+'render_manifest.json')).write_text(json.dumps(manifest,indent=2)+'\n')
