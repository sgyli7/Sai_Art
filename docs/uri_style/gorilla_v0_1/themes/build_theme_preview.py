"""Compose existing theme sheets; never repaint the source rasters."""
from pathlib import Path
import base64
import ctypes as C
import ctypes.util
import hashlib
import html
import json
import shutil

ROOT = Path(__file__).resolve().parent
ASSET = ROOT.parent
PROJECT = ASSET.parents[2]
GENERATED = Path('/home/ethan/.codex/generated_images/01a0f3ab-7a57-7172-b8c5-e517aa2973da')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
plan = json.loads((ROOT / 'candidate_palette_plan.json').read_text())
catalog = json.loads((ROOT / 'theme_catalog.json').read_text())
base = ASSET / 'images/locked_four_view_review_rev_aa3.png'
assert sha(base) == catalog['source_sha256'], 'Approved URI source changed'
fixed = ROOT / 'images/black_gold_rev_2.png'
if not fixed.exists():
    shutil.copyfile(GENERATED / 'exec-eb7e6274-1afc-4aba-864e-ea1f44dfed87.png', fixed)

entries = [('uri', 'URI', 'URI', base)]
english = ['YELLOW / PURPLE', 'WHITE / ORANGE', 'BLACK / GOLD', 'DESERT']
for theme, label in zip(plan['themes'], english):
    image = fixed if theme['id'] == 'black_gold' else ROOT / 'images' / (theme['id'] + '.png')
    theme.update(image=str(image), sha256=sha(image), status='generated_candidate_awaiting_user_review',
                 prompt=str(ROOT / 'prompts' / (theme['id'] + '.txt')))
    if theme['id'] == 'black_gold':
        theme['local_fix_prompt'] = str(ROOT / 'prompts/black_gold_rear_edge_fix.txt')
    entries.append((theme['id'], theme['name'], label, image))
plan['status'] = 'four_self_designed_candidates_generated'
catalog['four_new_themes_status'] = 'four_self_designed_candidates_generated_not_verified_microduck_originals'
catalog['generated_variants'] = plan['themes']
catalog['geometry_and_composition'] = 'All four imagegen edits use approved AA3 as the subject and layout authority. Major forms visually checked; raster generation does not guarantee identical geometry or pixels. Original URI sheet remains byte-identical.'
catalog['preview'] = str(ROOT / 'index.html')
for name, obj in [('candidate_palette_plan.json', plan), ('theme_catalog.json', catalog)]:
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="3000" height="750" viewBox="0 0 3000 750">',
       '<rect width="3000" height="750" fill="white"/>',
       '<text x="35" y="45" font-family="DejaVu Sans" font-size="27" fill="#304366">GORILLA V0.1 / FIVE PALETTES</text>']
for i, (ident, name, label, path) in enumerate(entries):
    x = i * 600 + 20
    crop = '40 120 1140 1110' if ident == 'uri' else '20 62 597 581'
    size = 2400 if ident == 'uri' else 1254
    data = base64.b64encode(path.read_bytes()).decode()
    svg += [f'<text x="{x + 280}" y="100" text-anchor="middle" font-family="DejaVu Sans" font-size="24" fill="#304366">{label}</text>',
            f'<svg x="{x}" y="120" width="560" height="550" viewBox="{crop}" overflow="hidden"><image width="{size}" height="{size}" href="data:image/png;base64,{data}"/></svg>']
svg += ['<text x="35" y="720" font-family="DejaVu Sans" font-size="20" fill="#637083">URI: approved source / Four additional palettes: proposed candidates</text>', '</svg>']
svg_path = ROOT / 'theme_overview.svg'
png_path = ROOT / 'theme_overview.png'
svg_path.write_text('\n'.join(svg))
rsvg = C.CDLL(ctypes.util.find_library('rsvg-2'))
cairo = C.CDLL(ctypes.util.find_library('cairo'))
gobj = C.CDLL(ctypes.util.find_library('gobject-2.0'))
class Rectangle(C.Structure):
    _fields_ = [('x', C.c_double), ('y', C.c_double), ('width', C.c_double), ('height', C.c_double)]
rsvg.rsvg_handle_new_from_data.argtypes = [C.c_void_p, C.c_size_t, C.POINTER(C.c_void_p)]
rsvg.rsvg_handle_new_from_data.restype = C.c_void_p
rsvg.rsvg_handle_render_document.argtypes = [C.c_void_p, C.c_void_p, C.POINTER(Rectangle), C.POINTER(C.c_void_p)]
rsvg.rsvg_handle_render_document.restype = C.c_int
cairo.cairo_image_surface_create.argtypes = [C.c_int, C.c_int, C.c_int]
cairo.cairo_image_surface_create.restype = C.c_void_p
cairo.cairo_create.argtypes = [C.c_void_p]
cairo.cairo_create.restype = C.c_void_p
cairo.cairo_surface_write_to_png.argtypes = [C.c_void_p, C.c_char_p]
cairo.cairo_surface_write_to_png.restype = C.c_int
cairo.cairo_destroy.argtypes = [C.c_void_p]
cairo.cairo_surface_destroy.argtypes = [C.c_void_p]
gobj.g_object_unref.argtypes = [C.c_void_p]
raw = svg_path.read_bytes()
buf = C.create_string_buffer(raw)
err = C.c_void_p()
handle = rsvg.rsvg_handle_new_from_data(buf, len(raw), C.byref(err))
assert handle
surface = cairo.cairo_image_surface_create(0, 3000, 750)
context = cairo.cairo_create(surface)
assert rsvg.rsvg_handle_render_document(handle, context, C.byref(Rectangle(0, 0, 3000, 750)), C.byref(err))
assert cairo.cairo_surface_write_to_png(surface, str(png_path).encode()) == 0
cairo.cairo_destroy(context)
cairo.cairo_surface_destroy(surface)
gobj.g_object_unref(handle)

cards = []
for ident, name, label, path in entries:
    rel = '../images/locked_four_view_review_rev_aa3.png' if ident == 'uri' else 'images/' + path.name
    prompt = '' if ident == 'uri' else f'<p><a href="prompts/{ident}.txt">完整生成提示词</a></p>'
    if ident == 'black_gold':
        prompt += '<p><a href="prompts/black_gold_rear_edge_fix.txt">顶视小边缘修正提示词</a></p>'
    cards.append(f'<section id="{ident}"><h2>{html.escape(name)}</h2><a href="{rel}"><img src="{rel}" alt="{name}完整四视图"></a>{prompt}</section>')
(ROOT / 'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Gorilla 五主题配色</title>
<style>body{max-width:1300px;margin:30px auto;padding:0 20px;font:17px/1.7 system-ui;background:#f6f7f9;color:#23304a}img{width:100%;height:auto}section{background:white;margin:24px 0;padding:24px;border-radius:12px}a{color:#215d99}nav{display:flex;gap:24px;flex-wrap:wrap}</style>
<h1>Gorilla V0.1 — 五主题配色</h1><p>URI 原稿保持不变。新增黄紫、白橙、黑金、沙漠为自拟候选；目前尚未核实 MicroDuck 原四主题。黄紫参考已找到的历史石墨灰／黄／紫色板，其余三套自行拟定。</p>
<p>四套采用内置 imagegen 图像编辑模式，由同一 AA3 原稿独立改色。构图和主要结构沿用原稿，生成图仍可能存在细节差异；配色候选尚待用户审阅。</p>
<nav>''' + ''.join(f'<a href="#{ident}">{name}</a>' for ident, name, _, _ in entries) + '''</nav><p><a href="theme_catalog.json">主题与色板来源记录</a></p><img src="theme_overview.png" alt="五主题正面对比">''' + ''.join(cards) + '</html>')

sources = ['exec-75acb4dd-02da-41ec-9396-d4b5ec548d80.png', 'exec-7e76cc78-7989-40f5-b87c-900e714bcec8.png', 'exec-f33e54f8-3642-40c0-8c5d-f16014cdae13.png', 'exec-9e6e7413-cbcd-4cfc-bf80-e44fe83913cd.png', 'exec-eb7e6274-1afc-4aba-864e-ea1f44dfed87.png']
ids = ['yellow_purple', 'white_orange', 'black_gold', 'desert', 'black_gold_rear_edge_fix']
style_paths = [PROJECT / '.agents/skills/uri-style/assets' / n for n in ['style_01_headphones.png', 'style_03_waterfront.png', 'style_06_architecture.png']]
manifest_path = ASSET / 'generation_manifest.json'
manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
for n, (ident, source) in enumerate(zip(ids, sources), 47):
    if manifest is None:
        break
    prompt = ROOT / 'prompts' / (ident + '.txt')
    output = fixed if n == 51 else ROOT / 'images' / (ident + '.png')
    subject = ROOT / 'images/black_gold.png' if n == 51 else base
    call = dict(id=f'G{n}', art_revision='AA3_palette_candidates', tool='built-in imagegen', mode='image_edit', model_version='not exposed by tool', prompt=str(prompt), prompt_sha256=sha(prompt), inputs_in_order=[dict(path=str(p), role='EDIT_TARGET' if i == 0 else 'STYLE_ONLY', sha256=sha(p)) for i,p in enumerate([subject] + style_paths)], output=str(output), output_sha256=sha(output), generated_source=str(GENERATED / source), status='generated_candidate_awaiting_user_review', notes='Self-designed palette variant; not a verified MicroDuck original theme.' if n < 51 else 'Local TOP rear service-door edge color correction only.')
    if not any(c['id'] == call['id'] for c in manifest['calls']):
        manifest['calls'].append(call)
if manifest is not None:
    manifest['palette_candidates'] = dict(catalog=str(ROOT / 'theme_catalog.json'), preview=str(ROOT / 'index.html'), status='four_generated_candidates_not_user_accepted', original_uri_sha256=sha(base))
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
assert sha(base) == catalog['source_sha256']
print(json.dumps(dict(preview=str(ROOT / 'index.html'), overview=str(png_path), images=[str(e[3]) for e in entries], uri_original_unchanged=True), ensure_ascii=False, indent=2))
