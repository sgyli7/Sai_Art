"""Native Blender inspection of the existing Pixal-derived spatial reference.

This is an inspection of a historical source, not acceptance of that source
as the current P13 model. P13 does not yet have a corresponding updated mesh.
One evaluated geometry snapshot is used for all cameras and exact projection
measurements. Color bands do not define components or joint locations.
"""
from pathlib import Path
import hashlib
import json
import time
import sys

sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy
import numpy as np
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'source/gorilla_clean_g2.blend'
START = time.time()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == 'MESH' and not o.hide_render]
depsgraph = bpy.context.evaluated_depsgraph_get()
vertices = []
object_records = []
geometry_hash = hashlib.sha256()
for obj in meshes:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    local = np.empty(len(mesh.vertices)*3, dtype=np.float32)
    mesh.vertices.foreach_get('co', local)
    local = local.reshape(-1, 3)
    matrix = np.asarray(obj.matrix_world, dtype=np.float64)
    world = local.astype(np.float64) @ matrix[:3,:3].T + matrix[:3,3]
    geometry_hash.update(obj.name.encode())
    geometry_hash.update(world.tobytes())
    object_records.append({'name':obj.name, 'vertices':len(world),
                           'bounds_xyz':[world.min(0).tolist(),world.max(0).tolist()]})
    vertices.append(world)
    evaluated.to_mesh_clear()
world = np.concatenate(vertices)
lo, hi = world.min(0), world.max(0)
center = Vector(((lo+hi)/2).tolist())
scale = float(max(hi-lo)*1.19)

# Neutral material makes geometry independent of rejected transverse colors.
clay = bpy.data.materials.new('inspection_neutral_geometry_s1')
clay.use_nodes = True
shader = clay.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value = (.43,.47,.50,1)
shader.inputs['Metallic'].default_value = 0
shader.inputs['Roughness'].default_value = .68
scene.view_layers[0].material_override = clay
scene.render.engine = 'CYCLES'
scene.cycles.samples = 12
scene.cycles.use_denoising = False
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'
scene.view_settings.exposure = -.55
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (.98,.98,.98,1)
background.inputs['Strength'].default_value = .55
camera = scene.camera
camera.data.type = 'ORTHO'
camera.data.ortho_scale = scale
camera.data.shift_x = camera.data.shift_y = 0
camera.data.clip_start = .01
camera.data.clip_end = 10
views = {}
for name, direction in [('front',(0,-1,0)), ('left',(1,0,0)),
                         ('rear',(0,1,0)), ('top',(0,0,1))]:
    camera.location = center + Vector(direction)*3
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    inverse = np.asarray(camera.matrix_world.inverted(), dtype=np.float64)
    local = world @ inverse[:3,:3].T + inverse[:3,3]
    xy = local[:,:2]/scale*900 + 450
    spans = xy.max(0)-xy.min(0)
    path = ROOT/'images'/f'spatial_inspection_{name}_s1.png'
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    views[name] = {'image':str(path.relative_to(ROOT)), 'camera_type':'ORTHO',
                   'eye_xyz':list(camera.location), 'target_xyz':list(center),
                   'orthographic_scale':scale, 'projected_vertex_span_px':spans.tolist(),
                   'camera_matrix_world':np.asarray(camera.matrix_world).tolist(),
                   'shared_geometry_sha256':geometry_hash.hexdigest()}
    print('NATIVE_SPATIAL_VIEW', name, json.dumps(spans.tolist()), flush=True)

checks = {
    'front_rear_height_equal': abs(views['front']['projected_vertex_span_px'][1]
                                  - views['rear']['projected_vertex_span_px'][1]) < 1e-4,
    'front_left_height_equal': abs(views['front']['projected_vertex_span_px'][1]
                                  - views['left']['projected_vertex_span_px'][1]) < 1e-4,
    'front_width_top_width_equal': abs(views['front']['projected_vertex_span_px'][0]
                                      - views['top']['projected_vertex_span_px'][0]) < 1e-4,
    'left_depth_top_depth_equal': abs(views['left']['projected_vertex_span_px'][0]
                                     - views['top']['projected_vertex_span_px'][1]) < 1e-4,
}
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/spatial_inspection_reference_s1.blend'), compress=True)
record = {'created_from':str(SOURCE.relative_to(ROOT)),
          'source_blend_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'source_acceptance':'Historical complete G2 was rejected; lower shape reference only.',
          'scope':'Native source inspection and projection identity, not validation of P13 artwork.',
          'bounds_xyz':[lo.tolist(),hi.tolist()], 'evaluated_vertices':len(world),
          'objects':object_records, 'views':views, 'projection_identity_checks':checks,
          'current_p13_has_updated_corresponding_model':False,
          'p13_spatial_acceptance':False, 'material_color_allocation_review':'Deferred; neutral override used.',
          'mass_collision_or_load_qualification':False,
          'elapsed_seconds':time.time()-START}
(ROOT/'native_spatial_inspection_s1.json').write_text(json.dumps(record,indent=2)+'\n')
print('NATIVE_SPATIAL_INSPECTION_COMPLETE',json.dumps(checks),flush=True)
