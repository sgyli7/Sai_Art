"""Blender renders and editable appearance model, all from one mesh source."""
from pathlib import Path
import hashlib
import json
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
P = ROOT/'source'/'leg_design_scene.json'
S = json.loads(P.read_text())
SOURCE_SHA = hashlib.sha256(P.read_bytes()).hexdigest()
OUT = ROOT/'images'; OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
owners = {}
collections = {}
for name in ('upper_context', 'left_leg', 'right_leg'):
    collection = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(collection)
    collections[name] = collection
objects = []
for p in S['parts']:
    collection = collections[p['source_group']]
    if p['body'] not in owners:
        empty = bpy.data.objects.new('pose_'+p['body'], None); collection.objects.link(empty)
        empty['body_owner'] = p['body']; owners[p['body']] = empty
    mesh = bpy.data.meshes.new(p['name']); mesh.from_pydata(p['vertices_world_m'], [], p['faces']); mesh.update()
    obj = bpy.data.objects.new(p['name'], mesh); collection.objects.link(obj)
    obj.parent = owners[p['body']]
    obj['appearance_source_sha256'] = SOURCE_SHA; obj['source_group'] = p['source_group']
    obj['role'] = p['role']; obj['manufacturing_part'] = False
    objects.append(obj)
    key = tuple(p['rgba'])
    name = 'rgba_'+'_'.join(str(round(c, 3)) for c in key)
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name); mat.diffuse_color = key; mat.use_nodes = True
        shader = mat.node_tree.nodes.get('Principled BSDF')
        # JSON palette values are sRGB. Convert for the linear shader input,
        # otherwise the approved blue clips into cyan under studio lighting.
        rgb = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in key[:3]]
        mat.diffuse_color = (*rgb, key[3])
        shader.inputs['Base Color'].default_value = (*rgb, key[3])
        shader.inputs['Metallic'].default_value = .28 if p['role'] not in ('armor', 'contact_pad') else .10
        shader.inputs['Roughness'].default_value = .30 if p['role'] == 'armor' else .46
    obj.data.materials.append(mat)
    for face in mesh.polygons:
        face.use_smooth = p['role'] == 'joint_cover'
scene = bpy.context.scene; scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = 1
scene.render.engine = 'CYCLES'; scene.cycles.samples = 40; scene.cycles.use_denoising = False
scene.render.resolution_x = 900; scene.render.resolution_y = 1100; scene.render.resolution_percentage = 100
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.97, .98, 1, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .35
scene.view_settings.view_transform = 'Standard'
lo, hi = S['reference_bounds_m']; cx = (lo[0]+hi[0])/2; cz = (lo[2]+hi[2])/2
def area(name, location, power, size):
    bpy.ops.object.light_add(type='AREA', location=location); obj = bpy.context.object; obj.name = name
    obj.data.energy = power; obj.data.shape = 'DISK'; obj.data.size = size
    obj.rotation_euler = (Vector((cx, 0, cz))-obj.location).to_track_quat('-Z', 'Y').to_euler()
area('key', (4, 3, 5), 400, 4)
area('fill', (-3, -4, 3), 200, 4)
area('edge', (-2, 2, 4), 160, 3)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.002)); floor = bpy.context.object
floor.name = 'render_floor_not_a_robot_part'
mat = bpy.data.materials.new('neutral_floor'); mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.92, .94, .96, 1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .9
floor.data.materials.append(mat)
bpy.ops.object.camera_add(); cam = bpy.context.object; cam.name = 'orthographic_camera'
cam.data.type = 'ORTHO'; scene.camera = cam
scale = max(hi[2]-lo[2], (hi[1]-lo[1])*1100/900)*1.12
views = {'front': ((6, 0, cz), (cx, 0, cz)),
         'left': ((cx, 6, cz), (cx, 0, cz)),
         'rear': ((-6, 0, cz), (cx, 0, cz)),
         'top': ((cx, 0, 7), (cx, 0, 0)),
         'three_quarter': ((3.4, 5, 2.8), (cx, 0, cz))}
manifest = {'source_sha256': SOURCE_SHA,
            'renderer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'same_native_source_all_views': True, 'imagegen_used': False,
            'appearance_accepted': False, 'physical_accepted': False, 'renders': []}
def render(name, location, target, view_scale, pose_sample=0):
    cam.location = location; cam.rotation_euler = (Vector(target)-cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.ortho_scale = view_scale
    scene.render.filepath = str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
    manifest['renders'].append({'file': name+'.png', 'camera_m': location, 'target_m': target,
                                'orthographic_scale_m': view_scale, 'pose_sample': pose_sample,
                                'source_sha256': SOURCE_SHA})
    (ROOT/'source'/'render_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
# The source builder exports the leg-only GLB directly; it does not depend
# on optional Blender exporter libraries on the host.
for obj in objects:
    obj.hide_render = obj['source_group'] != 'left_leg'
render('leg_left', (.1, 6, .66), (.1, .39, .66), 1.55)
render('leg_three_quarter', (3, 5, 2.2), (.1, .39, .66), 1.58)
for obj in objects:
    obj.hide_render = False
for name, (location, target) in views.items():
    render(name, location, target, scale if name != 'top' else (hi[1]-lo[1])*1.15)
    if name == 'three_quarter':
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source'/'leg_design_context.blend'))
for body, obj in owners.items():
    obj.matrix_world = Matrix(S['poses'][-1]['body_transforms'][body])
for obj in objects:
    obj.hide_render = obj['source_group'] != 'left_leg'
render('leg_deep_crouch_left', (.1, 6, .58), (.1, .39, .58), 1.55, 120)
for obj in objects:
    obj.hide_render = False
render('deep_crouch_left', *views['left'], scale, 120)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source'/'leg_design_deep_crouch.blend'))
print('ART_RENDER_DONE', len(manifest['renders']), flush=True)
