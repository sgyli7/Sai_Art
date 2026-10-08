"""Package final P30 artwork and the unchanged selected gray B7 model.

SVG pages embed existing raster bytes; the overview references those sources.
No bitmap recoloring is performed.
"""
from pathlib import Path
import base64
import ctypes as C
import ctypes.util
from datetime import datetime, timezone
import hashlib
import html
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent.parent
THEMES = ROOT / 'themes'
CATALOG = json.loads((THEMES / 'theme_catalog.json').read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def render_svg(svg, png, width, height):
    rsvg = C.CDLL(ctypes.util.find_library('rsvg-2'))
    cairo = C.CDLL(ctypes.util.find_library('cairo'))
    gobj = C.CDLL(ctypes.util.find_library('gobject-2.0'))

    class Rectangle(C.Structure):
        _fields_ = [('x', C.c_double), ('y', C.c_double),
                   ('width', C.c_double), ('height', C.c_double)]

    rsvg.rsvg_handle_new_from_file.argtypes = [C.c_char_p, C.POINTER(C.c_void_p)]
    rsvg.rsvg_handle_new_from_file.restype = C.c_void_p
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
    err = C.c_void_p()
    handle = rsvg.rsvg_handle_new_from_file(str(svg).encode(), C.byref(err))
    assert handle
    surface = cairo.cairo_image_surface_create(0, width, height)
    ctx = cairo.cairo_create(surface)
    try:
        assert rsvg.rsvg_handle_render_document(handle, ctx, C.byref(Rectangle(0, 0, width, height)), C.byref(err))
        assert cairo.cairo_surface_write_to_png(surface, str(png).encode()) == 0
    finally:
        cairo.cairo_destroy(ctx)
        cairo.cairo_surface_destroy(surface)
        gobj.g_object_unref(handle)


def embedded_image(path):
    raw = base64.b64encode(Path(path).read_bytes()).decode()
    return f'<image width="1254" height="1254" href="data:image/png;base64,{raw}"/>'


assert len(CATALOG['themes']) == 5
assert {t['id'] for t in CATALOG['themes']} == {'uri', 'yellow_purple', 'white_orange', 'black_gold', 'desert'}
labels = ['URI', 'YELLOW / PURPLE', 'WHITE / ORANGE', 'BLACK / GOLD', 'DESERT']
svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="2500" height="700" viewBox="0 0 2500 700">',
       '<rect width="2500" height="700" fill="white"/>',
       '<text x="25" y="40" font-family="DejaVu Sans" font-size="28" fill="#304366">GORILLA V0.2 / P30 / FIVE PALETTES</text>']
cards = []
for i, (t, label) in enumerate(zip(CATALOG['themes'], labels)):
    image = Path(t['image'])
    assert sha(image) == t['sha256']
    page = f'<svg xmlns="http://www.w3.org/2000/svg" width="1254" height="1254" viewBox="0 0 1254 1254"><title>Gorilla P30 {html.escape(t["name"])}</title>{embedded_image(image)}</svg>'
    image.with_suffix('.svg').write_text(page)
    x = 500 * i + 15
    svg += [f'<text x="{x+235}" y="85" text-anchor="middle" font-family="DejaVu Sans" font-size="23" fill="#304366">{label}</text>',
            f'<svg x="{x}" y="105" width="470" height="555" viewBox="60 8 500 590" overflow="hidden"><image width="1254" height="1254" href="images/{image.name}"/></svg>']
    name = image.name
    cards.append(f'<section id="{t["id"]}"><h2>{html.escape(t["name"])}</h2><a href="images/{name}"><img src="images/{name}" alt="{html.escape(t["name"])} 完整四视图"></a></section>')
svg += ['</svg>']
(THEMES / 'theme_overview.svg').write_text('\n'.join(svg))
render_svg(THEMES / 'theme_overview.svg', THEMES / 'theme_overview.png', 2500, 700)
(THEMES / 'index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Gorilla V0.2 五款配色</title>
<style>body{max-width:1400px;margin:30px auto;padding:0 20px;font:17px/1.7 system-ui;background:#f6f7f9;color:#23304a}img{width:100%;height:auto}section{background:white;margin:24px 0;padding:24px;border-radius:12px}a{color:#215d99}nav{display:flex;gap:24px;flex-wrap:wrap}</style>
<h1>Gorilla V0.2 — 五款配色</h1><p>P30 定稿：URI、黄紫、白橙、黑金、沙漠。五款均更新了本轮护膝、踝足、感知区、散热口和顶壳。</p><nav>'''
    + ''.join(f'<a href="#{t["id"]}">{html.escape(t["name"])}</a>' for t in CATALOG['themes'])
    + '</nav><img src="theme_overview.png" alt="五款正面配色总览">' + ''.join(cards) + '</html>')

PACKAGE = ROOT / 'delivery/gorilla_v0_2_p30'
assert not PACKAGE.exists(), 'Existing delivery snapshot must not be overwritten.'
PACKAGE.mkdir(parents=True)
records = []


def copy_file(src, rel, version):
    src = Path(src)
    dest = PACKAGE / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    assert sha(src) == sha(dest)
    records.append({'path': rel, 'source_path': str(src), 'source_repository': 'Sai_Art',
                    'source_version': version, 'sha256': sha(dest)})


for t in CATALOG['themes']:
    image = Path(t['image'])
    copy_file(image, 'themes/images/' + image.name, 'P30 palette update')
    copy_file(image.with_suffix('.svg'), 'themes/images/' + image.with_suffix('.svg').name, 'P30 native SVG page embedding')
    if t.get('prompt'):
        p = Path(t['prompt'])
        copy_file(p, 'themes/prompts/' + p.name, 'P30 exact palette prompt')
copy_file(THEMES / 'prompts/white_orange_coupler_fix_p30.txt', 'themes/prompts/white_orange_coupler_fix_p30.txt', 'P30 palette local correction')
for name in ['theme_overview.png', 'theme_overview.svg', 'index.html', 'theme_catalog.json', 'white_orange_coupler_composition_p30.json']:
    copy_file(THEMES / name, 'themes/' + name, 'P30 five-theme update')
copy_file(THEMES / 'images/white_orange_p30.verification.json', 'provenance/white_orange_local_fix_verification.json', 'P30 local edit pixel preservation')
copy_file(ROOT / 'source/lower_modular_components_b7.blend', 'model/source/lower_modular_components_b7.blend', 'B7 user-selected original gray asset, unchanged')
copy_file(ROOT / 'exports/lower_modular_components_b7.glb', 'model/exports/lower_modular_components_b7.glb', 'B7 native Blender GLB export')
for name in ['lower_modular_components_b7.json', 'selected_b7_asset_export.json', 'selected_b7_asset_validation_p30.json']:
    copy_file(ROOT / name, 'model/reports/' + name, 'B7 original geometry and P30 export verification')
for name in ['front', 'left', 'rear', 'top', 'front_oblique', 'rear_oblique', 'ankle_front_detail', 'ankle_rear_detail']:
    filename = f'lower_modular_components_{name}_b7.png'
    copy_file(ROOT / 'images' / filename, 'model/previews/' + filename, 'B7 original native inspection views')
for name in ['uri_knee_normal_perspective_p30_record.json', 'camera_frame_and_knee_marker_p29_record.json', 'top_shoulders_local_edit_p24_record.json', 'thermal_outlets_and_knee_seam_fix_p26_record.json']:
    copy_file(ROOT / name, 'provenance/' + name, 'Current art source and retained feature history')
copy_file(ROOT / 'prompts/uri_knee_normal_perspective_p30.txt', 'provenance/uri_knee_normal_perspective_p30.txt', 'P30 exact design prompt')
for name in ['style_01_race_car_hangar.png', 'style_03_tracked_mobile_station.png', 'style_05_white_blue_racer.png']:
    copy_file(ROOT.parents[2] / '.agents/skills/uri-style/assets' / name, 'provenance/style_references/' + name, 'URI v5 style-only fixed original')
copy_file(Path(__file__), 'tools/package_appearance_p30.py', 'P30 packaging source')
copy_file(ROOT / 'source/compose_four_view_revision.py', 'tools/compose_four_view_revision.py', 'Native SVG local page composition source')

# The packaged catalog uses portable paths; originals retain absolute provenance.
portable = json.loads(json.dumps(CATALOG))
portable['base'] = 'images/uri_p30.png'
portable['overview'] = 'theme_overview.png'
portable['preview'] = 'index.html'
for t in portable['themes']:
    t['image'] = 'images/' + Path(t['image']).name
    if t.get('prompt'):
        t['prompt'] = 'prompts/' + Path(t['prompt']).name
    if t.get('local_fix_prompt'):
        t['local_fix_prompt'] = 'prompts/' + Path(t['local_fix_prompt']).name
(PACKAGE / 'themes/theme_catalog.json').write_text(json.dumps(portable, ensure_ascii=False, indent=2) + '\n')

(PACKAGE / 'README.md').write_text('''# Gorilla V0.2 外观交付 · P30

本轮外观稿已按用户结束设计迭代的指示冻结。五款配色为 URI、黄紫、白橙、黑金、沙漠，完整 FRONT / LEFT / REAR / TOP 均在 `themes/images`。打开 [五款预览](themes/index.html) 或 [正面总览](themes/theme_overview.png)。

新版沿用 Gorilla 身体身份与屈曲站姿，更新腿部、完整踝足、暖白主护膝与蓝色侧盖、下缘深色机械嵌件、胸前感知舱及黄色框、踝部黄色点缀。前双口为散热进气，后背 pad 两侧为出气；顶壳为一体无缝曲面。其余四款按同一模块角色映射既定色板。

## 3D 资产

- `model/source/lower_modular_components_b7.blend`：用户指定的 B7 灰色腿部资产原文件，未因本轮配色改动。
- `model/exports/lower_modular_components_b7.glb`：同一 B7 的自包含交换副本，38 个共享几何定义、76 个左右腿部件实例、85 个层级节点。
- `model/previews/lower_modular_components_rear_oblique_b7.png`：与用户指定图对应的原始模型预览。另附四个原生视角、前斜视与两张踝部细节。
- `model/reports`：原始几何报告、导出来源和交付前 GLB 检查。

Blender 源采用外观归一化单位，+X 横向、−Y 前向、+Z 向上；GLB 由 Blender 原生导出为 +Y 向上。没有新增整机米制总高或制造尺寸。工程接入应先映射实际尺度与接口。

左右腿使用共享主网格镜像。本包保留原 B7；原报告的闭合实体资格仍为 false，三块高密度拟合罩壳的拓扑缺陷保留在报告中。绘图的法线/透视修订、配色和实际制造实体资格分别记录；本轮没有将图稿变更伪称为同版整机 CAD，也没有重做承载、运动或碰撞门禁。可编辑 3D 交付范围是选定的腿部 B7，整机四视图属于外观稿。

## 来源与维护

制作源：Sai_Art `docs/uri_style/gorilla_v0_2`。色板沿用 V0.1 的五主题定义，几何/构图以当前 P30 定稿为准。旧 AA3 的腿和 TOP 仅出现在历史色板参考中，不作为当前外观结构。`provenance` 保存准确提示词和参考角色，`manifest.json` 保存包内 SHA256 与源路径。

四视图 SVG 嵌入原始 PNG 字节，总览 SVG 引用包内相同图片，均为排版资源；Blender 文件为可编辑 3D 制作源。包内不包含被拒绝的 P22 整机拼装、C15 上半身猜测或 P25 着色实验。P31 的进一步视角草案在用户结束设计后未生成。
''')

validation = json.loads((ROOT / 'selected_b7_asset_validation_p30.json').read_text())
for row in records:
    row['source_sha256'] = sha(row['source_path'])
    row['sha256'] = sha(PACKAGE / row['path'])
    row['adapted_for_portable_paths'] = row['source_sha256'] != row['sha256']
manifest = {'asset': 'Gorilla v0.2', 'revision': 'P30', 'scope': 'Completed Art appearance delivery: five four-view palettes and original selected B7 lower-body model',
            'created_at_utc': datetime.now(timezone.utc).isoformat(), 'theme_count': 5,
            'art_design_phase_closed_by_user': True, 'whole_robot_native_CAD_qualified': False,
            'model_validation': validation, 'source_records': records,
            'exclusions': ['Rejected P22 whole assembly', 'C15 upper candidate', 'P25 colored B7 experiment', 'Unexecuted P31 art draft'],
            'files': []}
for p in sorted(PACKAGE.rglob('*')):
    if p.is_file():
        manifest['files'].append({'path': str(p.relative_to(PACKAGE)), 'bytes': p.stat().st_size, 'sha256': sha(p)})
(PACKAGE / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
archive = ROOT / 'delivery/gorilla_v0_2_appearance_handoff_p30.zip'
assert not archive.exists(), 'Existing delivery archive must not be overwritten.'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
    for p in sorted(PACKAGE.rglob('*')):
        if p.is_file():
            z.write(p, 'gorilla_v0_2_p30/' + str(p.relative_to(PACKAGE)))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for row in manifest['files']:
        raw = z.read('gorilla_v0_2_p30/' + row['path'])
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
    assert json.loads(z.read('gorilla_v0_2_p30/manifest.json'))['theme_count'] == 5
result = {'status': 'verified', 'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': sha(archive),
          'directory': str(PACKAGE), 'theme_count': 5, 'files': len(manifest['files']) + 1,
          'zip_crc_check': True, 'all_member_hashes_match': True, 'gray_B7_source_unmodified': True,
          'notification': 'pending_after_verified_package'}
(ROOT / 'delivery/delivery_verification_p30.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
