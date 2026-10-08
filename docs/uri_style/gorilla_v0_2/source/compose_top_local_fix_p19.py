"""Native SVG composition: replace TOP artwork, preserve the other three panels.

The exact original JPEG and exact generated raster bytes are embedded without
painting, recoloring, mirroring or warping either image. Librsvg renders the page.
Pillow is used only to read dimensions and verify unchanged decoded pixels.
"""
from pathlib import Path
import base64, ctypes as C, ctypes.util, hashlib, json, argparse
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(); parser.add_argument('--ai-sheet',required=True)
args=parser.parse_args()
original=ROOT/'references/user_four_view_top_fix_p19.jpg'; edited=Path(args.ai_sheet).resolve()
svg=ROOT/'images/gorilla_four_view_top_fixed_p19.svg'
png=ROOT/'images/gorilla_four_view_top_fixed_p19.png'
width,height=Image.open(original).size; aw,ah=Image.open(edited).size
assert width==height and aw==ah,'Full square-sheet composition required; inspect other aspect ratios first'
# Keep panel rules, labels, all three unchanged views and their backgrounds.
clip=(632,633,1250,1187)
def embed(name,path,w,h,mime):
    encoded=base64.b64encode(path.read_bytes()).decode('ascii')
    return f'<image id="{name}" width="{w}" height="{h}" href="data:{mime};base64,{encoded}"/>'
x0,y0,x1,y1=clip
page=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<title>Gorilla — local TOP white-shell projection correction P19</title>
<desc>Only TOP illustration inside the lower-right panel is replaced. The exact original source remains visible everywhere else. Native orthographic registration is a projection guide, not qualified complete CAD.</desc>
<defs>{embed('original',original,width,height,'image/jpeg')}{embed('top_edit',edited,aw,ah,'image/png')}
<clipPath id="top_only" clipPathUnits="userSpaceOnUse"><rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}"/></clipPath></defs>
<use href="#original"/>
<g clip-path="url(#top_only)"><use href="#top_edit" transform="scale({width/aw:.12f})"/></g>
</svg>'''
svg.write_text(page)
rsvg=C.CDLL(ctypes.util.find_library('rsvg-2')); cairo=C.CDLL(ctypes.util.find_library('cairo')); gobject=C.CDLL(ctypes.util.find_library('gobject-2.0'))
class Rectangle(C.Structure): _fields_=[('x',C.c_double),('y',C.c_double),('width',C.c_double),('height',C.c_double)]
rsvg.rsvg_handle_new_from_data.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_void_p)]; rsvg.rsvg_handle_new_from_data.restype=C.c_void_p
rsvg.rsvg_handle_render_document.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(Rectangle),C.POINTER(C.c_void_p)]; rsvg.rsvg_handle_render_document.restype=C.c_int
cairo.cairo_image_surface_create.argtypes=[C.c_int,C.c_int,C.c_int]; cairo.cairo_image_surface_create.restype=C.c_void_p
cairo.cairo_create.argtypes=[C.c_void_p]; cairo.cairo_create.restype=C.c_void_p
cairo.cairo_surface_write_to_png.argtypes=[C.c_void_p,C.c_char_p]; cairo.cairo_surface_write_to_png.restype=C.c_int
cairo.cairo_destroy.argtypes=[C.c_void_p]; cairo.cairo_surface_destroy.argtypes=[C.c_void_p]; gobject.g_object_unref.argtypes=[C.c_void_p]
raw=svg.read_bytes(); data=C.create_string_buffer(raw); error=C.c_void_p()
handle=rsvg.rsvg_handle_new_from_data(data,len(raw),C.byref(error)); assert handle,'SVG parse failed'
surface=cairo.cairo_image_surface_create(0,width,height); context=cairo.cairo_create(surface); viewport=Rectangle(0,0,width,height)
try:
    assert rsvg.rsvg_handle_render_document(handle,context,C.byref(viewport),C.byref(error)),'SVG render failed'
    assert cairo.cairo_surface_write_to_png(surface,str(png).encode())==0,'PNG export failed'
finally:
    cairo.cairo_destroy(context); cairo.cairo_surface_destroy(surface); gobject.g_object_unref(handle)

# Read-only verification: no raster edits or pixel writes.
before=np.asarray(Image.open(original).convert('RGB')); after=np.asarray(Image.open(png).convert('RGB'))
changed=np.any(before!=after,axis=2); outside=changed.copy(); outside[y0:y1,x0:x1]=False
panels={'FRONT':(0,0,626,631),'LEFT':(628,0,1254,631),'REAR':(0,633,626,1254),'TOP_label':(632,1187,1250,1254)}
checks={name:bool(np.array_equal(before[ya:yb,xa:xb],after[ya:yb,xa:xb])) for name,(xa,ya,xb,yb) in panels.items()}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record_path=ROOT/'top_white_shell_projection_p19_record.json'; record=json.loads(record_path.read_text())
record.update(output=str(png),output_sha256=sha(png),svg=str(svg),svg_sha256=sha(svg),
              original_sha256=sha(original),generated_source=str(edited),generated_source_sha256=sha(edited),
              allowed_top_clip_px=clip,unchanged_panel_pixel_checks=checks,
              changed_pixels_outside_authorized_top_region=int(outside.sum()),
              status='composed_pending_visual_review',user_accepted=False)
record_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
assert not outside.any(),f'Unexpected changed pixels outside TOP: {outside.sum()}'
assert all(checks.values()),'Original panel preservation failed'
print(json.dumps({'output':str(png),'preserved_panels':checks,'outside_changed_pixels':int(outside.sum())},ensure_ascii=False))
