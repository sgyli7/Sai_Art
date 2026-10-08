"""Import actual Pixal3D geometry into Blender and inspect four fixed rotations.

All cameras use the same untouched imported mesh. No generated texture,
image retouching, arbitrary panel tracing or geometric cleanup is used here.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'generated' / 'reference_raw_geometry_00001_.glb'
SOURCE_SHA = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(SOURCE))
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
clay = bpy.data.materials.new('reference_geometry_clay')
clay.use_nodes = True
shader = clay.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value = (.39, .40, .41, 1.)
shader.inputs['Roughness'].default_value = .72
for index, obj in enumerate(objects):
    obj.name = 'reference_highpoly_' + str(index)
    obj['source_sha256'] = SOURCE_SHA
    obj['geometry_status'] = 'generated reconstruction input; not accepted or mechanically verified'
    obj['physical_scale'] = 'unassigned; normalized generator coordinates'
    obj.data.materials.clear()
    obj.data.materials.append(clay)
    for face in obj.data.polygons:
        face.use_smooth = True
corners = [obj.matrix_world @ Vector(c) for obj in objects for c in obj.bound_box]
lo = Vector(tuple(min(c[i] for c in corners) for i in range(3)))
hi = Vector(tuple(max(c[i] for c in corners) for i in range(3)))
center = (lo + hi) / 2
extent = hi - lo
scene = bpy.context.scene
scene.unit_settings.system = 'NONE'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 12
scene.cycles.use_denoising = False
scene.render.use_persistent_data = True
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = True
scene.view_settings.view_transform = 'Standard'
scene.render.resolution_x = 1000
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
for name, location, energy, size in [('key', (2, -3, 4), 180, 3),
                                      ('fill', (-2, -1, 2), 100, 3),
                                      ('rim', (1, 3, 3), 150, 2)]:
    bpy.ops.object.light_add(type='AREA', location=location)
    lamp = bpy.context.object
    lamp.name = name
    lamp.data.energy = energy
    lamp.data.size = size
    lamp.rotation_euler = (center - lamp.location).to_track_quat('-Z', 'Y').to_euler()
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.name = 'fixed_geometry_inspection_camera'
camera.data.type = 'ORTHO'
camera.data.ortho_scale = max(extent) * 1.30
scene.camera = camera
record = {'source_glb_sha256': SOURCE_SHA,
          'native_import_transform': 'glTF (x,y,z) -> Blender (x,-z,y)',
          'mesh_objects': len(objects),
          'vertices': sum(len(o.data.vertices) for o in objects),
          'faces': sum(len(o.data.polygons) for o in objects),
          'geometry_edits': [], 'all_views_same_native_geometry': True,
          'native_bounds': [list(lo), list(hi)],
          'geometry_accepted': False, 'imagegen_used': False, 'views': []}
print('NATIVE_IMPORT_COMPLETE', record['vertices'], record['faces'], flush=True)
for name, yaw in [('reference_direction', 0), ('turn_45', 45),
                  ('turn_90', 90), ('turn_180', 180)]:
    a = math.radians(yaw)
    eye = center + Vector((math.sin(a), -math.cos(a), .08)) * 3
    camera.location = eye
    camera.rotation_euler = (center-eye).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(ROOT / 'images' / (name + '_g1.png'))
    bpy.ops.render.render(write_still=True)
    record['views'].append({'file': str(Path(scene.render.filepath).relative_to(ROOT)),
                            'camera_eye': list(eye), 'camera_target': list(center),
                            'yaw_degrees': yaw})
    (ROOT / 'source' / 'highpoly_import_record.json').write_text(json.dumps(record, indent=2)+'\n')
    print('NATIVE_REFERENCE_VIEW', name, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'source' / 'reference_highpoly.blend'), compress=True)
print('NATIVE_BLENDER_SOURCE_SAVED', flush=True)
