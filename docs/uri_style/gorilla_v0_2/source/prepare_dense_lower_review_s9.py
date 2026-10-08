"""Frame complete native review images and verify the exchange asset.

Does not repair, redraw, recolour or alter the source geometry. SVG is a
layout containing untouched native render bytes. Export excludes display
ground, cameras and lamps.
"""
from pathlib import Path
import sys, json, hashlib, base64, ctypes as C, ctypes.util
ROOT = Path(__file__).resolve().parents[1]
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy
import numpy as np
from mathutils import Vector
from scipy.spatial import cKDTree

SOURCE = ROOT / 'source/lower_dense_assembled_s9.blend'
REPORT = ROOT / 'lower_dense_assembly_s9.json'
VERIFY_ONLY = '--verify-only' in sys.argv
record = json.loads(REPORT.read_text())
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
names = ['pixal_clear_side_leg', 'pixal_mirrored_leg',
         'complete_reference_foot_left', 'complete_reference_foot_right']


def coordinates(obj):
    data = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get('co', data)
    data = data.reshape(-1, 3)
    matrix = np.asarray(obj.matrix_world)
    return data @ matrix[:3, :3].T + matrix[:3, 3]


source_parts = {n: coordinates(bpy.data.objects[n]) for n in names}
world = np.concatenate(list(source_parts.values()))
center = Vector(((world.min(0) + world.max(0)) / 2).tolist())
scene = bpy.context.scene; camera = scene.camera
scene.cycles.samples = 32; scene.cycles.use_denoising = False
for name, axis in [('front_oblique', (1, -1, .52)), ('rear_oblique', (1, 1, .52))]:
    camera.location = center + Vector(axis).normalized() * 3
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    inv = np.asarray(camera.matrix_world.inverted())
    projected = world @ inv[:3, :3].T + inv[:3, 3]
    lo, hi = projected[:, :2].min(0), projected[:, :2].max(0)
    offset = (lo + hi) / 2
    basis = np.asarray(camera.matrix_world)[:3, :3]
    camera.location += Vector((basis[:, 0] * offset[0] + basis[:, 1] * offset[1]).tolist())
    camera.data.ortho_scale = float(np.max(hi - lo) * 1.17)
    bpy.context.view_layer.update()
    inv = np.asarray(camera.matrix_world.inverted())
    projected = world @ inv[:3, :3].T + inv[:3, 3]
    out = ROOT / 'images' / f'lower_dense_assembled_{name}_s9.png'
    if not VERIFY_ONLY:
        scene.render.filepath = str(out); bpy.ops.render.render(write_still=True)
    record['views'][name].update(
        span_px=(np.ptp(projected[:, :2], axis=0) / camera.data.ortho_scale * 1200).tolist(),
        camera_matrix_world=np.asarray(camera.matrix_world).tolist(),
        camera_ortho_scale=camera.data.ortho_scale,
        complete_frame_margin=.17,
    )
    print('COMPLETE_NATIVE_FRAME', name, flush=True)

if not VERIFY_ONLY:
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), compress=True)
record['native_source_sha256'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()

definitions = []
panels = []
labels = [('front', 'FRONT'), ('left', 'LEFT'), ('rear', 'REAR'), ('top', 'TOP')]
for i, (name, label) in enumerate(labels):
    path = ROOT / record['views'][name]['image']
    raw = base64.b64encode(path.read_bytes()).decode('ascii')
    definitions.append(f'<image id="{name}" width="1200" height="1200" href="data:image/png;base64,{raw}"/>')
    x, y = 30 + (i % 2) * 1240, 100 + (i // 2) * 1260
    panels.append(f'<use href="#{name}" x="{x}" y="{y}"/>'
                  f'<text x="{x+600}" y="{y+1235}" text-anchor="middle">{label}</text>')
svg_path = ROOT / 'images/lower_dense_assembly_four_view_s9.svg'
png_path = svg_path.with_suffix('.png')
svg_path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="2500" height="2660" viewBox="0 0 2500 2660">'
                   '<title>Gorilla — dense primary legs and foot-only reference assembly study</title>'
                   '<desc>Four native orthographic renders from one geometry and pose. Lower assembly study only; no physical qualification.</desc>'
                   f'<defs>{"".join(definitions)}</defs><rect width="2500" height="2660" fill="white"/>'
                   '<g fill="#253f75" font-family="DejaVu Sans,sans-serif" font-size="30">'
                   '<text x="30" y="52">GORILLA — LOWER SOURCE ASSEMBLY / S9</text>'
                   f'{"".join(panels)}<text x="30" y="2632" font-size="24">PRIMARY: dense leg shape   |   FOOT ONLY: complete forefoot + heel   |   APPEARANCE STUDY</text></g></svg>')
rsvg = C.CDLL(ctypes.util.find_library('rsvg-2'))
cairo = C.CDLL(ctypes.util.find_library('cairo'))
gobj = C.CDLL(ctypes.util.find_library('gobject-2.0'))
rsvg.rsvg_handle_new_from_data.argtypes = [C.c_void_p, C.c_size_t, C.POINTER(C.c_void_p)]
rsvg.rsvg_handle_new_from_data.restype = C.c_void_p
class Rect(C.Structure):
    _fields_ = [('x', C.c_double), ('y', C.c_double), ('width', C.c_double), ('height', C.c_double)]
rsvg.rsvg_handle_render_document.argtypes = [C.c_void_p, C.c_void_p, C.POINTER(Rect), C.POINTER(C.c_void_p)]
rsvg.rsvg_handle_render_document.restype = C.c_int
cairo.cairo_image_surface_create.argtypes = [C.c_int, C.c_int, C.c_int]
cairo.cairo_image_surface_create.restype = C.c_void_p
cairo.cairo_create.argtypes = [C.c_void_p]; cairo.cairo_create.restype = C.c_void_p
cairo.cairo_surface_write_to_png.argtypes = [C.c_void_p, C.c_char_p]
cairo.cairo_surface_write_to_png.restype = C.c_int
cairo.cairo_destroy.argtypes = [C.c_void_p]; cairo.cairo_surface_destroy.argtypes = [C.c_void_p]
gobj.g_object_unref.argtypes = [C.c_void_p]
raw = svg_path.read_bytes(); buffer = C.create_string_buffer(raw); error = C.c_void_p()
handle = rsvg.rsvg_handle_new_from_data(buffer, len(raw), C.byref(error))
assert handle, 'Review SVG failed to load.'
surface = cairo.cairo_image_surface_create(0, 2500, 2660); context = cairo.cairo_create(surface)
try:
    assert rsvg.rsvg_handle_render_document(handle, context, C.byref(Rect(0, 0, 2500, 2660)), C.byref(error))
    assert cairo.cairo_surface_write_to_png(surface, str(png_path).encode()) == 0
finally:
    cairo.cairo_destroy(context); cairo.cairo_surface_destroy(surface); gobj.g_object_unref(handle)
record['four_view_layout'] = {'svg': str(svg_path.relative_to(ROOT)), 'png': str(png_path.relative_to(ROOT)),
                              'native_render_bytes_unchanged': True}

bpy.ops.object.select_all(action='DESELECT')
for n in names:
    o = bpy.data.objects[n]; o.select_set(True)
    o['appearance_scope'] = 'foot_only' if n.startswith('complete_reference_foot') else 'primary_user_selected_leg'
bpy.context.view_layer.objects.active = bpy.data.objects[names[0]]
glb = ROOT / 'generated/lower_dense_assembled_s9.glb'
if not VERIFY_ONLY or not glb.exists():
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True,
                              export_extras=True, export_apply=False)
print('DENSE_NATIVE_EXCHANGE_EXPORTED', glb.name, flush=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
imported = {o.name: o for o in bpy.data.objects if o.type == 'MESH'}
checks = []
for n in names:
    original, other = source_parts[n], coordinates(imported[n])
    source_sample = original[::max(1, len(original)//50000)]
    imported_sample = other[::max(1, len(other)//50000)]
    forward = cKDTree(other).query(source_sample, k=1)[0]
    backward = cKDTree(original).query(imported_sample, k=1)[0]
    boundary_delta = float(max(np.max(abs(original.min(0)-other.min(0))),
                               np.max(abs(original.max(0)-other.max(0)))))
    checks.append({'name': n, 'source_vertices': len(original), 'imported_vertices': len(other),
                   'source_sample_to_exchange_max_distance': float(forward.max()),
                   'exchange_sample_to_source_max_distance': float(backward.max()),
                   'bounds_max_delta': boundary_delta,
                   'appearance_scope': imported[n].get('appearance_scope'),
                   'passed_geometric_exchange_check': bool(max(forward.max(), backward.max(), boundary_delta) < 2e-6)})
record['exchange_check'] = {
    'file': str(glb.relative_to(ROOT)), 'sha256': hashlib.sha256(glb.read_bytes()).hexdigest(),
    'native_reload_performed': True, 'mesh_count': len(imported), 'parts': checks,
    'passed': len(imported) == 4 and all(c['passed_geometric_exchange_check'] for c in checks),
    'scope': 'Shape/role transfer only; not appearance acceptance, animation, collision or manufacturing readiness',
}
REPORT.write_text(json.dumps(record, indent=2) + '\n')
print('DENSE_ASSEMBLY_REVIEW_READY', record['exchange_check']['passed'], flush=True)
