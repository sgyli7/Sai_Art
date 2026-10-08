"""Rigidly level the actual dense foot source at its broad underside facet.

Only foot placement changes. Primary leg vertices, dense foot shape, uniform
scale and attachment centre are preserved. This is appearance registration,
not a claim about loads, dynamic contact, or engineering support margins.
"""
from pathlib import Path
import sys, math, json, hashlib
ROOT = Path(__file__).resolve().parents[1]
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy
import numpy as np
from scipy.spatial import ConvexHull
from mathutils import Vector

source_report = json.loads((ROOT / 'lower_dense_assembly_s8.json').read_text())
p = np.load(ROOT / 'source/complete_foot_vertex_sample_s6.npz')['vertices']
sole = p[p[:, 2] < -.17][::3]
hull = ConvexHull(sole)
triangles = sole[hull.simplices]
areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                triangles[:, 2] - triangles[:, 0]), axis=1) / 2
eligible = np.flatnonzero(hull.equations[:, 2] < -.8)
facet = int(eligible[np.argmax(areas[eligible])])
up = -hull.equations[facet, :3]
up /= np.linalg.norm(up)
z_axis = np.array([0., 0., 1.])
v = np.cross(up, z_axis)
k = np.array([[0., -v[2], v[1]], [v[2], 0., -v[0]], [-v[1], v[0], 0.]])
level = np.eye(3) + k + k @ k / (1 + up @ z_axis)
assert np.linalg.norm(level @ up - z_axis) < 1e-8
levelled = sole @ level.T
values, axes = np.linalg.eigh(np.cov(levelled[:, :2].T))
long_axis = axes[:, -1]
if long_axis[0] < 0:
    long_axis = -long_axis
yaw = math.pi / 2 - math.atan2(long_axis[1], long_axis[0])
yaw_matrix = np.array([[math.cos(yaw), -math.sin(yaw), 0.],
                       [math.sin(yaw), math.cos(yaw), 0.], [0., 0., 1.]])
new_rotation = yaw_matrix @ level
old_yaw = math.radians(source_report['foot_transform']['yaw_degrees'])
old_rotation = np.array([[math.cos(old_yaw), -math.sin(old_yaw), 0.],
                        [math.sin(old_yaw), math.cos(old_yaw), 0.], [0., 0., 1.]])
delta = new_rotation @ old_rotation.T
connector = np.array([.190, -.028, source_report['foot_transform']['connector_plane_z']])

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'source/lower_dense_assembled_s8.blend'))


def points(obj):
    data = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', data)
    return data.reshape(-1, 3)


leg_names = ['pixal_clear_side_leg', 'pixal_mirrored_leg']
leg_hashes_before = {n: hashlib.sha256(points(bpy.data.objects[n]).tobytes()).hexdigest()
                     for n in leg_names}
left = bpy.data.objects['complete_reference_foot_left']
before = points(left)
after = (before - connector) @ delta.T + connector
left.data.vertices.foreach_set('co', after.astype(np.float32).ravel()); left.data.update()
right = bpy.data.objects['complete_reference_foot_right']
mirrored = after.copy(); mirrored[:, 0] *= -1
right.data.vertices.foreach_set('co', mirrored.astype(np.float32).ravel()); right.data.update()
leg_hashes_after = {n: hashlib.sha256(points(bpy.data.objects[n]).tobytes()).hexdigest()
                    for n in leg_names}
assert leg_hashes_before == leg_hashes_after

selected = [bpy.data.objects[n] for n in leg_names] + [left, right]
world = np.concatenate([points(o) for o in selected])
lo, hi = world.min(0), world.max(0)
floor_z = float(after[:, 2].min())
center = Vector(((lo + hi) / 2).tolist())
scene = bpy.context.scene
scene.cycles.samples = 48; scene.cycles.use_denoising = False
scene.view_settings.exposure = 0
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (.90, .91, .92, 1)
background.inputs['Strength'].default_value = .5
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, floor_z - .00002))
floor = bpy.context.object; floor.name = 'appearance_ground_display_only'
floor['role'] = 'Display ground, excluded from asset bounds and projection checks'
mat = bpy.data.materials.new('neutral_ground_display'); mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.68, .70, .72, 1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .85
floor.data.materials.append(mat)
camera = scene.camera; camera.data.ortho_scale = float(max(hi - lo) * 1.21)
geometry_hash = hashlib.sha256(world.tobytes()).hexdigest()
views = {}
for name, direction in [('front', (0, -1, 0)), ('left', (1, 0, 0)), ('rear', (0, 1, 0)),
                         ('top', (0, 0, 1)), ('front_oblique', (1, -1, .52)),
                         ('rear_oblique', (1, 1, .52))]:
    camera.location = center + Vector(direction).normalized() * 3
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    inv = np.asarray(camera.matrix_world.inverted())
    projected = world @ inv[:3, :3].T + inv[:3, 3]
    span = np.ptp(projected[:, :2], axis=0) / camera.data.ortho_scale * 1200
    image_path = ROOT / 'images' / f'lower_dense_assembled_{name}_s9.png'
    scene.render.filepath = str(image_path); bpy.ops.render.render(write_still=True)
    views[name] = {'image': str(image_path.relative_to(ROOT)), 'span_px': span.tolist(),
                   'shared_geometry_sha256': geometry_hash,
                   'camera_matrix_world': np.asarray(camera.matrix_world).tolist()}
    print('DENSE_FOOT_PLACEMENT_VIEW', name, flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'source/lower_dense_assembled_s9.blend'), compress=True)

foot_scale = source_report['foot_transform']['uniform_scale']
neck = np.array(source_report['foot_transform']['source_neck_center'])
contact_world = (triangles[facet] - neck) @ new_rotation.T * foot_scale + connector
report = {
    'source': 'source/lower_dense_assembled_s8.blend',
    'primary_leg_geometry_unchanged': leg_hashes_before == leg_hashes_after,
    'primary_leg_vertex_hashes': leg_hashes_after,
    'foot_shape_unchanged': True,
    'foot_placement_method': 'Rigid underside registration and yaw alignment; no mesh stretching',
    'raw_source_ground_facet': {'outward_normal': hull.equations[facet, :3].tolist(),
                              'corners': triangles[facet].tolist(), 'area': float(areas[facet])},
    'source_to_assembly_rotation': new_rotation.tolist(),
    'delta_rotation_from_s8': delta.tolist(),
    'ground_z': floor_z,
    'registered_contact_triangle_xyz': contact_world.tolist(),
    'registered_contact_triangle_height_span': float(np.ptp(contact_world[:, 2])),
    'both_feet_ground_height_equal_by_mirror': True,
    'bounds_xyz': [lo.tolist(), hi.tolist()], 'views': views,
    'shared_geometry_sha256': geometry_hash,
    'projection_checks': {
        'front_left_height': abs(views['front']['span_px'][1] - views['left']['span_px'][1]) < 1e-3,
        'front_top_width': abs(views['front']['span_px'][0] - views['top']['span_px'][0]) < 1e-3,
        'left_top_depth': abs(views['left']['span_px'][0] - views['top']['span_px'][1]) < 1e-3,
    },
    'artwork_status': 'Native lower assembly study, not whole-robot v0.2 delivery',
    'appearance_accepted': False, 'engineering_ready': False,
    'collision_mass_strength_validation': False,
    'limitations': ['Remaining source reconstruction scars require local surface repair',
                    'Interface has not been fused or qualified as a bearing/structural connection',
                    'v0.1 upper body is not part of this lower assembly study'],
}
(ROOT / 'lower_dense_assembly_s9.json').write_text(json.dumps(report, indent=2) + '\n')
print('DENSE_FOOT_PLACEMENT_COMPLETE', json.dumps(report['projection_checks']), flush=True)
