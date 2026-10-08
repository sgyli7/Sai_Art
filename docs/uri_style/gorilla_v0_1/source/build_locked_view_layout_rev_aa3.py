"""Compose the selected source views in native SVG; render the page with librsvg.
No painting, recoloring, mirroring, or shape warping is performed by this script.
Imagegen supplies the authorized local corrections and the LEFT/TOP artwork.
"""
from pathlib import Path
import base64, ctypes as C, ctypes.util, hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'images/original_wedge_rebuild_rev_z1.png'
LOCAL = ROOT/'images/locked_front_rear_local_corrections_rev_aa1.png'
ANGLES = ROOT/'images/locked_machine_left_top_rev_aa2.png'
EDGE = ROOT/'images/top_lamp_edge_only_rev_aa3.png'
SVG = ROOT/'images/locked_four_view_review_rev_aa3.svg'
PNG = ROOT/'images/locked_four_view_review_rev_aa3.png'

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def raster_definition(name, path):
    data = base64.b64encode(path.read_bytes()).decode('ascii')
    return f'<image id="{name}" width="1536" height="1024" href="data:image/png;base64,{data}"/>'

# Only these regions may replace pixels from the user-selected FRONT/REAR.
patches = {
 'front_radiators': '<rect x="169" y="188" width="74" height="115"/><rect x="362" y="188" width="78" height="115"/>',
 'front_hip_interior': '<path d="M 227,337 L 282,339 L 281,374 L 260,390 L 260,464 L 238,464 L 231,419 Z"/><path d="M 379,337 L 324,339 L 325,374 L 346,390 L 346,464 L 368,464 L 375,419 Z"/>',
 'rear_shoulder_interior': '<path d="M 1072,173 L 1113,166 L 1113,215 L 1127,278 L 1124,327 L 1092,333 L 1075,280 Z"/><path d="M 1402,173 L 1361,166 L 1361,215 L 1347,278 L 1350,327 L 1382,333 L 1399,280 Z"/>',
 'top_lamp_edge': '<rect x="1053" y="630" width="69" height="46"/>',
}
clips = ''.join(f'<clipPath id="{name}" clipPathUnits="userSpaceOnUse">{shape}</clipPath>' for name,shape in patches.items())
clips += '''<clipPath id="front_crop"><rect x="0" y="75" width="620" height="846"/></clipPath>
<clipPath id="rear_crop"><rect x="934" y="75" width="602" height="846"/></clipPath>
<clipPath id="left_crop"><rect x="125" y="15" width="510" height="921"/></clipPath>
<clipPath id="top_crop"><rect x="642" y="164" width="893" height="674"/></clipPath>'''

front = '''<g transform="translate(245.2 56) scale(1.2)" clip-path="url(#front_crop)"><use href="#selected"/><use href="#local" clip-path="url(#front_radiators)"/><use href="#local" clip-path="url(#front_hip_interior)"/></g>'''
rear = '''<g transform="translate(-868.4 1206) scale(1.2)" clip-path="url(#rear_crop)"><use href="#selected"/><use href="#local" clip-path="url(#rear_shoulder_interior)"/></g>'''
left_scale = (895-86)*1.2/(925-28)
left = f'<g transform="translate({1795-359*left_scale:.8f} {1130-925*left_scale:.8f}) scale({left_scale:.10f})" clip-path="url(#left_crop)"><use href="#angles"/></g>'
top_scale = (609-4)*1.2/(1494-681)
top = f'<g transform="translate({1795-1088*top_scale:.8f} {1835-503*top_scale:.8f}) scale({top_scale:.10f})" clip-path="url(#top_crop)"><use href="#angles"/><use href="#edge" clip-path="url(#top_lamp_edge)"/></g>'
page = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="2400" height="2400" viewBox="0 0 2400 2400">
<title>Gorilla — selected FRONT/REAR, reconstructed LEFT/TOP review</title>
<desc>Original selected raster remains the source outside three user-authorized local correction regions. Orthographic concept illustration; not measured CAD.</desc>
<defs>{raster_definition('selected',SOURCE)}{raster_definition('local',LOCAL)}{raster_definition('angles',ANGLES)}{raster_definition('edge',EDGE)}{clips}</defs>
<rect width="2400" height="2400" fill="white"/>
<g fill="none" stroke="#66778e" stroke-width="1.5"><rect x="40" y="120" width="1140" height="1110"/><rect x="1220" y="120" width="1140" height="1110"/><rect x="40" y="1270" width="1140" height="1090"/><rect x="1220" y="1270" width="1140" height="1090"/></g>
<g fill="#253f75" font-family="DejaVu Sans, sans-serif"><text x="65" y="78" font-size="34" letter-spacing="3">H 2.650 m   W 2.587 m</text></g>
{front}{left}{rear}{top}
<g font-family="DejaVu Sans, sans-serif" font-size="34" letter-spacing="4" text-anchor="middle" fill="#253f75"><text x="610" y="1191">FRONT</text><text x="1795" y="1191">LEFT</text><text x="610" y="2329">REAR</text><text x="1795" y="2329">TOP</text></g>
</svg>'''
SVG.write_text(page)

# Render a native vector page. Raster source bytes are unchanged and embedded.
rsvg = C.CDLL(ctypes.util.find_library('rsvg-2'))
cairo = C.CDLL(ctypes.util.find_library('cairo'))
gobj = C.CDLL(ctypes.util.find_library('gobject-2.0'))
rsvg.rsvg_handle_new_from_data.argtypes = [C.c_void_p,C.c_size_t,C.POINTER(C.c_void_p)]
rsvg.rsvg_handle_new_from_data.restype = C.c_void_p
class Rectangle(C.Structure):
    _fields_ = [('x',C.c_double),('y',C.c_double),('width',C.c_double),('height',C.c_double)]
rsvg.rsvg_handle_render_document.argtypes = [C.c_void_p,C.c_void_p,C.POINTER(Rectangle),C.POINTER(C.c_void_p)]
rsvg.rsvg_handle_render_document.restype = C.c_int
cairo.cairo_image_surface_create.argtypes = [C.c_int,C.c_int,C.c_int]
cairo.cairo_image_surface_create.restype = C.c_void_p
cairo.cairo_create.argtypes = [C.c_void_p]
cairo.cairo_create.restype = C.c_void_p
cairo.cairo_surface_write_to_png.argtypes = [C.c_void_p,C.c_char_p]
cairo.cairo_surface_write_to_png.restype = C.c_int
cairo.cairo_destroy.argtypes = [C.c_void_p]
cairo.cairo_surface_destroy.argtypes = [C.c_void_p]
gobj.g_object_unref.argtypes = [C.c_void_p]
raw = SVG.read_bytes()
buf = C.create_string_buffer(raw)
err = C.c_void_p()
handle = rsvg.rsvg_handle_new_from_data(buf,len(raw),C.byref(err))
if not handle: raise RuntimeError('SVG parse failed')
surface = cairo.cairo_image_surface_create(0,2400,2400)
context = cairo.cairo_create(surface)
viewport = Rectangle(0,0,2400,2400)
try:
    if not rsvg.rsvg_handle_render_document(handle,context,C.byref(viewport),C.byref(err)):
        raise RuntimeError('SVG render failed')
    status = cairo.cairo_surface_write_to_png(surface,str(PNG).encode())
    if status: raise RuntimeError(f'PNG export failed: {status}')
finally:
    cairo.cairo_destroy(context);cairo.cairo_surface_destroy(surface);gobj.g_object_unref(handle)

record = {'revision':'AA3','status':'candidate_for_user_review','layout':'2x2: FRONT LEFT / REAR TOP','selected_source':{'path':str(SOURCE),'sha256':sha(SOURCE)},'local_ai_correction_source':{'path':str(LOCAL),'sha256':sha(LOCAL)},'left_top_source':{'path':str(ANGLES),'sha256':sha(ANGLES)},'top_lamp_correction_source':{'path':str(EDGE),'sha256':sha(EDGE)},'allowed_overlay_regions':patches,'preservation':'FRONT and REAR reference the unchanged selected source raster, with clipped imagegen overlays only inside the user-authorized local regions. No warping, recoloring, redrawing or mirroring in composition. Uniform page rescaling only.','upright_scale_anchor':'Selected source top 86 / ground 895; LEFT source top 28 / ground 925; visually align overall height. No inference of measured CAD depth.','top_scale_anchor':'Match projected arm-span width to FRONT; visual illustration only.','svg':str(SVG),'svg_sha256':sha(SVG),'png':str(PNG),'png_sha256':sha(PNG)}
(ROOT/'locked_view_composition_rev_aa3.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'svg':str(SVG),'png':str(PNG),'selected_source_sha256':sha(SOURCE),'size':[2400,2400]},ensure_ascii=False))
