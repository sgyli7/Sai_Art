"""Render one unpainted reference reconstruction from four fixed cameras."""
from pathlib import Path
import hashlib
import json
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source'/'reference_scene.json'
S=json.loads(SOURCE.read_text())
SOURCE_SHA=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
collection=bpy.data.collections.new('reference_reconstruction')
bpy.context.scene.collection.children.link(collection)
for p in S['parts']:
    mesh=bpy.data.meshes.new(p['name']);mesh.from_pydata(p['vertices'],[],p['faces']);mesh.update()
    obj=bpy.data.objects.new(p['name'],mesh);collection.objects.link(obj)
    obj['source_sha256']=SOURCE_SHA;obj['part_group']=p['body'];obj['provenance']=p['geometry_role']
    name='clay_'+str(p['shade']);mat=bpy.data.materials.get(name)
    if mat is None:
        mat=bpy.data.materials.new(name);mat.use_nodes=True
        shader=mat.node_tree.nodes.get('Principled BSDF')
        shade=p['shade']**2.2
        shader.inputs['Base Color'].default_value=(shade,shade,shade,1.)
        shader.inputs['Roughness'].default_value=.68
        shader.inputs['Metallic'].default_value=.1
    mesh.materials.append(mat)
    if 'joint' in p['name'] or 'internal' in p['name']:
        for face in mesh.polygons:face.use_smooth=True
scene=bpy.context.scene
scene.unit_settings.system='NONE'
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=True
scene.view_settings.view_transform='Standard'
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
lo,hi=S['bounds'];center=Vector(tuple((a+b)/2 for a,b in zip(lo,hi)))
for name,location,power,size in [('key',(5,-5,7),700,5),('fill',(2,5,4),450,4),('rim',(-4,0,5),350,3)]:
    bpy.ops.object.light_add(type='AREA',location=location);lamp=bpy.context.object;lamp.name=name
    lamp.data.energy=power;lamp.data.size=size
    lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera
manifest={'source_sha256':SOURCE_SHA,'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'all_views_same_native_geometry':True,'imagegen_used':False,'renders':[]}
def render(name,eye,target,scale,width,height):
    camera.location=eye;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=scale
    scene.render.resolution_x=width;scene.render.resolution_y=height;scene.render.resolution_percentage=100
    scene.render.filepath=str(ROOT/'images'/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    manifest['renders'].append({'file':name+'.png','eye':list(eye),'target':list(target),
                                'ortho_scale':scale,'width':width,'height':height,'source_sha256':SOURCE_SHA})
    (ROOT/'source'/'render_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
c=S['camera'];view=Vector(c['view_vector']);right=Vector(c['right_vector']);up=Vector(c['up_vector'])
target=Vector(c['target'])+(374-c['pixel_center'][0])/c['pixels_per_layout_unit']*right \
       +(c['pixel_center'][1]-472.5)/c['pixels_per_layout_unit']*up
render('reference_camera',target+view*8,target,945/c['pixels_per_layout_unit'],748,945)
height=hi[2]-lo[2];width=hi[1]-lo[1]
scale=max(height,width)*1.18
for name,direction in [('front',(1,0,0)),('left',(0,1,0)),('rear',(-1,0,0))]:
    render(name,center+Vector(direction)*8,center,scale,1000,1200)
render('three_quarter',center+Vector((6,-7,3)),center,scale,1000,1200)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source'/'reference_geometry.blend'))
print('REFERENCE_NATIVE_VIEWS',len(manifest['renders']),flush=True)
