"""Compose local art revisions using unchanged raster assets in native SVG.

This is page layout, not bitmap painting. Images are embedded byte-for-byte;
uniform transforms and clipping control the authorized edit area. Pillow is
used only for read-only dimensions and decoded-pixel verification.
"""
from pathlib import Path
import argparse, base64, ctypes as C, ctypes.util, hashlib, json
from PIL import Image
import numpy as np

parser=argparse.ArgumentParser()
parser.add_argument('--spec',required=True)
args=parser.parse_args()
specpath=Path(args.spec).resolve(); spec=json.loads(specpath.read_text())
base=Path(spec['base']).resolve(); imagepath=Path(spec['overlay']).resolve()
out=Path(spec['output']).resolve(); svg=out.with_suffix('.svg')
w,h=Image.open(base).size; iw,ih=Image.open(imagepath).size
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def embed(name,path,width,height):
    mime=Image.MIME[Image.open(path).format]
    return f'<image id="{name}" width="{width}" height="{height}" href="data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"/>'
rects=''.join(f'<rect x="{x}" y="{y}" width="{xx-x}" height="{yy-y}"/>' for x,y,xx,yy in spec['regions'])
transform=spec.get('transform',{'scale':1,'translate':[0,0]})
scale=transform['scale'];tx,ty=transform['translate']
page=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<title>{spec['title']}</title>
<desc>Native page composition of unchanged raster source bytes; only the declared illustration regions are replaced.</desc>
<defs>{embed('original',base,w,h)}{embed('replacement',imagepath,iw,ih)}<clipPath id="local_edit" clipPathUnits="userSpaceOnUse">{rects}</clipPath></defs>
<use href="#original"/>
<g clip-path="url(#local_edit)"><rect width="{w}" height="{h}" fill="white"/><use href="#replacement" transform="translate({tx:.12f},{ty:.12f}) scale({scale:.12f})"/></g>
</svg>'''
svg.write_text(page)
rsvg=C.CDLL(ctypes.util.find_library('rsvg-2'));cairo=C.CDLL(ctypes.util.find_library('cairo'));gobject=C.CDLL(ctypes.util.find_library('gobject-2.0'))
class Rectangle(C.Structure):_fields_=[('x',C.c_double),('y',C.c_double),('width',C.c_double),('height',C.c_double)]
rsvg.rsvg_handle_new_from_data.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(C.c_void_p)];rsvg.rsvg_handle_new_from_data.restype=C.c_void_p
rsvg.rsvg_handle_render_document.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(Rectangle),C.POINTER(C.c_void_p)];rsvg.rsvg_handle_render_document.restype=C.c_int
cairo.cairo_image_surface_create.argtypes=[C.c_int,C.c_int,C.c_int];cairo.cairo_image_surface_create.restype=C.c_void_p
cairo.cairo_create.argtypes=[C.c_void_p];cairo.cairo_create.restype=C.c_void_p
cairo.cairo_surface_write_to_png.argtypes=[C.c_void_p,C.c_char_p];cairo.cairo_surface_write_to_png.restype=C.c_int
cairo.cairo_destroy.argtypes=[C.c_void_p];cairo.cairo_surface_destroy.argtypes=[C.c_void_p];gobject.g_object_unref.argtypes=[C.c_void_p]
def render_svg(data,path):
    raw=data.encode();blob=C.create_string_buffer(raw);error=C.c_void_p()
    handle=rsvg.rsvg_handle_new_from_data(blob,len(raw),C.byref(error));assert handle
    surface=cairo.cairo_image_surface_create(0,w,h);context=cairo.cairo_create(surface)
    try:
        assert rsvg.rsvg_handle_render_document(handle,context,C.byref(Rectangle(0,0,w,h)),C.byref(error))
        assert cairo.cairo_surface_write_to_png(surface,str(path).encode())==0
    finally:
        cairo.cairo_destroy(context);cairo.cairo_surface_destroy(surface);gobject.g_object_unref(handle)
render_svg(page,out)
# Compare against the same native renderer, avoiding JPEG-decoder / embedded
# color-profile differences from Pillow. The source bytes are unchanged.
baseline=out.with_name(out.stem+'_original_native_baseline.png')
baseline_page=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{embed("native_base",base,w,h)}</svg>'
render_svg(baseline_page,baseline)
source_read=np.asarray(Image.open(base).convert('RGB'))
before=np.asarray(Image.open(baseline).convert('RGB'));after=np.asarray(Image.open(out).convert('RGB'))
changed=np.any(before!=after,axis=2);authorized=np.zeros((h,w),dtype=bool)
for x,y,xx,yy in spec['regions']:authorized[y:yy,x:xx]=True
checks={}
for name,(x,y,xx,yy) in spec.get('preserve_checks',{}).items():checks[name]=bool(np.array_equal(before[y:yy,x:xx],after[y:yy,x:xx]))
result={'spec':str(specpath),'base':str(base),'base_sha256':sha(base),'overlay':str(imagepath),'overlay_sha256':sha(imagepath),
        'output':str(out),'output_sha256':sha(out),'svg':str(svg),'svg_sha256':sha(svg),
        'authorized_regions':spec['regions'],'unchanged_region_checks':checks,
        'verification_baseline':str(baseline),'source_embedded_bytes_unchanged':True,
        'native_decoder_vs_pillow_original_max_channel_difference':int(abs(before.astype(int)-source_read.astype(int)).max()),
        'changed_pixels_outside_authorized_regions':int((changed&~authorized).sum()),
        'image_editing_method':'Imagegen raster edit; native SVG layout embeds original bytes without raster painting.',
        'whole_v0_2_qualified':False,'user_accepted':False}
out.with_suffix('.verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert not (changed&~authorized).any(),result
assert all(checks.values()),checks
print(json.dumps({'output':str(out),'unchanged_region_checks':checks,'outside_changes':result['changed_pixels_outside_authorized_regions']},ensure_ascii=False))
