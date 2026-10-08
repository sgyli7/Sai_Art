"""Combine the user-selected dense legs with the foot-only dense reference.

Leg positions are unchanged. Foot triangles are clipped at the proximal
interface, then positioned by one rigid rotation and one uniform scale.
No box/loft replacement, inferred new leg, or engineering qualification.
"""
from pathlib import Path
import sys, json, math, hashlib, time
ROOT = Path(__file__).resolve().parents[1]
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

START = time.time()
LEG_SOURCE = ROOT / 'source/lower_dense_surface_s7.blend'
FOOT_SOURCE = ROOT / 'source/complete_foot_reference_highpoly_s6.blend'
CUT_Z = -.135
FOOT_SCALE = .40
CONNECTOR_Z = -.365


def coordinates(obj):
    values = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', values)
    values = values.reshape(-1, 3)
    matrix = np.asarray(obj.matrix_world)
    return values @ matrix[:3, :3].T + matrix[:3, 3]


def clip_triangles(vertices, triangles, cut_z):
    """Exact plane clip. New vertices lie on source edges, below-cut ones stay."""
    inside = vertices[:, 2] <= cut_z
    flags = inside[triangles]
    count = flags.sum(axis=1)
    full = triangles[count == 3]
    crossing = triangles[(count > 0) & (count < 3)]
    raw_edges = np.concatenate([crossing[:, [0, 1]], crossing[:, [1, 2]],
                                crossing[:, [2, 0]]])
    raw_edges = raw_edges[inside[raw_edges[:, 0]] != inside[raw_edges[:, 1]]]
    edges = np.unique(np.sort(raw_edges, axis=1), axis=0)
    t = (cut_z - vertices[edges[:, 0], 2]) / (
        vertices[edges[:, 1], 2] - vertices[edges[:, 0], 2])
    edge_vertices = vertices[edges[:, 0]] + t[:, None] * (
        vertices[edges[:, 1]] - vertices[edges[:, 0]])
    edge_vertices[:, 2] = cut_z
    original_ids = np.flatnonzero(inside)
    remap = np.full(len(vertices), -1, dtype=np.int32)
    remap[original_ids] = np.arange(len(original_ids), dtype=np.int32)
    edge_base = len(original_ids)
    # Sorted integer pair keys permit vectorized original-edge lookup.
    edge_key = edges[:, 0].astype(np.int64) * len(vertices) + edges[:, 1]

    def intersection(a, b):
        key = np.minimum(a, b).astype(np.int64) * len(vertices) + np.maximum(a, b)
        return edge_base + np.searchsorted(edge_key, key)

    output = [remap[full]]
    for j in range(3):
        one = triangles[(count == 1) & flags[:, j]]
        if len(one):
            a, b, c = one[:, j], one[:, (j + 1) % 3], one[:, (j + 2) % 3]
            output.append(np.column_stack((remap[a], intersection(a, b),
                                           intersection(c, a))))
        two = triangles[(count == 2) & ~flags[:, j]]
        if len(two):
            a, b, c = two[:, j], two[:, (j + 1) % 3], two[:, (j + 2) % 3]
            ca, ab = intersection(c, a), intersection(a, b)
            output.append(np.column_stack((remap[b], remap[c], ca)))
            output.append(np.column_stack((remap[b], ca, ab)))
    return np.concatenate((vertices[original_ids], edge_vertices)), np.concatenate(output), {
        'original_retained_vertices': int(len(original_ids)),
        'new_cut_edge_vertices': int(len(edge_vertices)),
        'original_below_plane_coordinates_unchanged': True,
        'removed_scope': 'Reference shank and all upper leg geometry above the foot interface',
    }


bpy.ops.wm.open_mainfile(filepath=str(LEG_SOURCE))
legs = [o for o in bpy.data.objects if o.type == 'MESH']
leg_hashes_before = {o.name: hashlib.sha256(coordinates(o).tobytes()).hexdigest() for o in legs}
with bpy.data.libraries.load(str(FOOT_SOURCE), link=False) as (source, target):
    target.objects = ['complete_foot_highpoly_0']
raw = target.objects[0]
bpy.context.collection.objects.link(raw)
bpy.context.view_layer.update()
raw_vertices = coordinates(raw)
counts = np.empty(len(raw.data.polygons), dtype=np.int32)
raw.data.polygons.foreach_get('loop_total', counts)
assert np.all(counts == 3), 'The imported reference must consist of triangles.'
loops = np.empty(len(raw.data.loops), dtype=np.int32)
raw.data.loops.foreach_get('vertex_index', loops)
foot_vertices, foot_faces, clip_record = clip_triangles(raw_vertices, loops.reshape(-1, 3), CUT_Z)

# The generated reference is oblique. Align its actual long footprint axis,
# with the original toe direction (-source axis) pointing to Gorilla front -Y.
sole_sample = raw_vertices[(raw_vertices[:, 2] < -.17)][::16]
eigenvalues, axes = np.linalg.eigh(np.cov(sole_sample[:, :2].T))
long_axis = axes[:, -1]
if long_axis[0] < 0:
    long_axis = -long_axis
yaw = math.pi / 2 - math.atan2(long_axis[1], long_axis[0])
rotation = np.array([[math.cos(yaw), -math.sin(yaw), 0],
                     [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
neck_points = raw_vertices[abs(raw_vertices[:, 2] - CUT_Z) < .007]
neck_center = np.median(neck_points, axis=0)
neck_center[2] = CUT_Z
rotated_neck = neck_center @ rotation.T
shift = np.array([.190, -.028, CONNECTOR_Z]) - rotated_neck * FOOT_SCALE
foot_world = foot_vertices @ rotation.T * FOOT_SCALE + shift

mesh = bpy.data.meshes.new('complete_foot_only_dense')
mesh.from_pydata(foot_world.tolist(), [], foot_faces.tolist())
mesh.update()
bm = bmesh.new(); bm.from_mesh(mesh)
cut_plane_z = CONNECTOR_Z
cut_boundary = [e for e in bm.edges if e.is_boundary and
                all(abs(v.co.z - cut_plane_z) < 2e-6 for v in e.verts)]
capped = bmesh.ops.holes_fill(bm, edges=cut_boundary, sides=0)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
if bm.calc_volume(signed=True) < 0:
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
foot_topology = {
    'cut_caps': len(capped.get('faces', [])),
    'boundary_edges': sum(e.is_boundary for e in bm.edges),
    'multi_face_edges': sum(len(e.link_faces) > 2 for e in bm.edges),
    'signed_volume': bm.calc_volume(signed=True),
}
bm.to_mesh(mesh); bm.free(); mesh.update()
for face in mesh.polygons:
    face.use_smooth = True
material = bpy.data.materials.new('complete_foot_source_clay')
material.use_nodes = True
bsdf = material.node_tree.nodes['Principled BSDF']
bsdf.inputs['Base Color'].default_value = (.31, .35, .38, 1)
bsdf.inputs['Roughness'].default_value = .55
mesh.materials.append(material)
foot = bpy.data.objects.new('complete_reference_foot_left', mesh)
bpy.context.collection.objects.link(foot)
foot['reference_role'] = 'FOOT ONLY: toe, heel, sole and integrated ankle cradle'
foot['reference_shank_adopted'] = False
mirror = foot.copy(); mirror.data = mesh.copy()
mirror.name = 'complete_reference_foot_right'
bpy.context.collection.objects.link(mirror)
for vertex in mirror.data.vertices:
    vertex.co.x = -vertex.co.x
bm = bmesh.new(); bm.from_mesh(mirror.data)
bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
bm.to_mesh(mirror.data); bm.free()
bpy.data.objects.remove(raw, do_unlink=True)

leg_hashes_after = {o.name: hashlib.sha256(coordinates(o).tobytes()).hexdigest() for o in legs}
assert leg_hashes_before == leg_hashes_after, 'The selected primary leg source changed.'
meshes = legs + [foot, mirror]
all_world = np.concatenate([coordinates(o) for o in meshes])
lo, hi = all_world.min(0), all_world.max(0)
center = Vector(((lo + hi) / 2).tolist())
scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.samples = 32
scene.cycles.use_denoising = False
scene.render.use_persistent_data = True
scene.render.resolution_x = 1200; scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'
scene.view_settings.exposure = -.2
scene.world.color = (.50, .50, .50)
if scene.world.use_nodes:
    background = scene.world.node_tree.nodes.get('Background')
    if background:
        background.inputs['Color'].default_value = (.68, .70, .72, 1)
        background.inputs['Strength'].default_value = .5
for o in list(bpy.data.objects):
    if o.type == 'LIGHT':
        bpy.data.objects.remove(o, do_unlink=True)
for name, position, power, size in [
    ('key', (2, -3, 4), 120, 3), ('fill', (-2, -1, 2), 65, 3),
    ('rim', (1, 3, 3), 100, 3),
]:
    bpy.ops.object.light_add(type='AREA', location=position)
    lamp = bpy.context.object; lamp.name = name
    lamp.data.energy = power; lamp.data.size = size
    lamp.rotation_euler = (center - lamp.location).to_track_quat('-Z', 'Y').to_euler()
camera = scene.camera
camera.data.type = 'ORTHO'; camera.data.ortho_scale = float(max(hi - lo) * 1.21)
geometry_hash = hashlib.sha256(all_world.tobytes()).hexdigest()
views = {}
for name, direction in [
    ('front', (0, -1, 0)), ('left', (1, 0, 0)), ('rear', (0, 1, 0)),
    ('top', (0, 0, 1)), ('front_oblique', (1, -1, .52)),
    ('rear_oblique', (1, 1, .52)),
]:
    camera.location = center + Vector(direction).normalized() * 3
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    inv = np.asarray(camera.matrix_world.inverted())
    projected = all_world @ inv[:3, :3].T + inv[:3, 3]
    span = np.ptp(projected[:, :2], axis=0) / camera.data.ortho_scale * 1200
    image_path = ROOT / 'images' / f'lower_dense_assembled_{name}_s8.png'
    scene.render.filepath = str(image_path); bpy.ops.render.render(write_still=True)
    views[name] = {'image': str(image_path.relative_to(ROOT)), 'span_px': span.tolist(),
                   'shared_geometry_sha256': geometry_hash,
                   'camera_matrix_world': np.asarray(camera.matrix_world).tolist()}
    print('DENSE_SOURCE_ASSEMBLY_VIEW', name, flush=True)

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'source/lower_dense_assembled_s8.blend'), compress=True)
record = {
    'primary_leg_source': str(LEG_SOURCE.relative_to(ROOT)),
    'primary_user_reference': 'references/user_primary_dense_lower_s6.jpg',
    'foot_only_source': str(FOOT_SOURCE.relative_to(ROOT)),
    'foot_only_user_reference': 'references/user_foot_only_dense_reference_s6.jpg',
    'source_leg_world_vertex_hashes_before': leg_hashes_before,
    'source_leg_world_vertex_hashes_after': leg_hashes_after,
    'selected_leg_geometry_unchanged': leg_hashes_before == leg_hashes_after,
    'foot_clip': clip_record, 'foot_topology': foot_topology,
    'foot_transform': {'yaw_degrees': math.degrees(yaw), 'uniform_scale': FOOT_SCALE,
                       'source_neck_center': neck_center.tolist(), 'translation': shift.tolist(),
                       'connector_plane_z': CONNECTOR_Z,
                       'source_foot_surface_not_stretched_or_primitive_replaced': True},
    'bounds_xyz': [lo.tolist(), hi.tolist()], 'views': views,
    'shared_geometry_sha256': geometry_hash,
    'projection_checks': {
        'front_left_height': abs(views['front']['span_px'][1] - views['left']['span_px'][1]) < 1e-3,
        'front_top_width': abs(views['front']['span_px'][0] - views['top']['span_px'][0]) < 1e-3,
        'left_top_depth': abs(views['left']['span_px'][0] - views['top']['span_px'][1]) < 1e-3,
    },
    'upper_body': 'v0.1 identity unchanged; omitted from this lower assembly study',
    'units': 'Existing normalized appearance coordinates; no mass, strength or metre conversion claimed',
    'appearance_accepted': False, 'engineering_ready': False,
    'interface_status': 'Positioned appearance candidate; inspect shank/ankle junction before adoption',
    'collision_mass_strength_validation': False,
    'elapsed_seconds': time.time() - START,
}
(ROOT / 'lower_dense_assembly_s8.json').write_text(json.dumps(record, indent=2) + '\n')
print('DENSE_SOURCE_ASSEMBLY_COMPLETE', json.dumps(record['projection_checks']), flush=True)
