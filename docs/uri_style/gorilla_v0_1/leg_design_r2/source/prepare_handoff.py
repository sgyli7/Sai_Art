"""Assemble source-bound Art review pages and a leg-only handoff package."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import zipfile
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[3]
OLD = ROOT.parent/'leg_redesign_r1'
IMAGEGEN_SOURCE = Path('/home/ethan/.codex/generated_images/01a0f3ab-7a57-7172-b8c5-e517aa2973da/exec-fa8a4cca-abdf-4099-bf26-fe67a68f4376.png')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sheet(filename, panels, columns, width, title, subtitle):
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    large, small = ImageFont.truetype(font, 32), ImageFont.truetype(font, 20)
    cell_w, cell_h = width//columns, 980
    rows = (len(panels)+columns-1)//columns
    page = Image.new('RGB', (width, rows*cell_h+136), 'white')
    draw = ImageDraw.Draw(page)
    draw.text((28, 18), title, fill='#203c5a', font=large)
    draw.text((28, 62), subtitle, fill='#506174', font=small)
    for k, (file, label) in enumerate(panels):
        x, y = (k%columns)*cell_w, 104+(k//columns)*cell_h
        picture = ImageOps.contain(Image.open(ROOT/'images'/file).convert('RGB'), (cell_w-32, cell_h-65))
        page.paste(picture, (x+(cell_w-picture.width)//2, y))
        draw.rectangle((x+8, y-6, x+cell_w-8, y+cell_h-13), outline='#bdc7d0', width=1)
        draw.text((x+20, y+cell_h-49), label, fill='#203c5a', font=small)
    page.save(ROOT/'images'/filename)


def main():
    source = ROOT/'source'/'leg_design_scene.json'
    s = json.loads(source.read_text()); source_sha = sha(source)
    check = json.loads((ROOT/'source'/'articulation_check.json').read_text())
    render = json.loads((ROOT/'source'/'render_manifest.json').read_text())
    exchange = json.loads((ROOT/'source'/'exchange_check.json').read_text())
    assert check['source_sha256'] == render['source_sha256'] == exchange['source_sha256'] == source_sha
    assert check['sampled_appearance_geometry_clear'] and len(render['renders']) == 9
    for r in render['renders']:
        assert (ROOT/'images'/r['file']).exists()
    shutil.copy2(IMAGEGEN_SOURCE, ROOT/'images'/'uri_leg_concept.png')
    refs = ROOT/'references'; refs.mkdir(exist_ok=True)
    for n in ('current_design_reference_01.jpg', 'current_design_reference_02.jpg'):
        shutil.copy2(OLD/'references'/n, refs/n)
    shutil.copy2(ROOT.parent/'images'/'locked_four_view_review_rev_aa3.png', refs/'approved_upper_aa3.png')
    style_root = PROJECT/'.agents'/'skills'/'uri-style'/'assets'
    styles = [style_root/'style_01_race_car_hangar.png', style_root/'style_03_tracked_mobile_station.png',
              style_root/'style_05_white_blue_racer.png']
    generation = {'tool': 'built_in_image_gen', 'mode': 'geometry_grounded_style_transfer',
                  'source_output': str(IMAGEGEN_SOURCE), 'saved_output': 'images/uri_leg_concept.png',
                  'source_output_sha256': sha(IMAGEGEN_SOURCE), 'prompt_file': 'source/uri_art_prompt.txt',
                  'prompt_sha256': sha(ROOT/'source'/'uri_art_prompt.txt'),
                  'geometry_source_sha256': source_sha,
                  'inputs': [{'path': str(ROOT/'images'/'leg_three_quarter.png'),
                              'role': 'EDIT_TARGET/GEOMETRY/COMPOSITION',
                              'sha256': sha(ROOT/'images'/'leg_three_quarter.png')}]+
                            [{'path': str(p), 'role': 'STYLE', 'sha256': sha(p)} for p in styles],
                  'reference_choice': 'Reserve the actual single-leg edit target; use URI v5 anchors 1/3/5 for color and line quality.',
                  'visual_review': {'four_main_axes_three_load_links': True,
                                    'crouched_pose_retained': True,
                                    'low_ankle_continuous_sole_retained': True,
                                    'blue_orange_ivory_palette_retained': True,
                                    'new_external_drives_added': False},
                  'limits': 'Concept seams and surface treatments are illustrations. Native meshes/axes remain the geometry reference; image is not CAD or load evidence.',
                  'appearance_accepted': False, 'physical_accepted': False}
    (ROOT/'source'/'generation_record.json').write_text(json.dumps(generation, indent=2)+'\n')
    sheet('four_view.png', [('front.png', 'FRONT'), ('left.png', 'LEFT'), ('rear.png', 'REAR'), ('top.png', 'TOP')],
          2, 1600, 'GORILLA / R2 LEG DESIGN / NATIVE CONTEXT',
          'Reference H 2.264 m | 3 load links | Upperbody reconstruction is fit context')
    sheet('leg_review.png', [('leg_left.png', 'LEFT / REFERENCE CROUCH'),
                            ('leg_three_quarter.png', 'THREE QUARTER / SAME GEOMETRY'),
                            ('leg_deep_crouch_left.png', 'LEFT / DEEPER CROUCH')],
          3, 2400, 'GORILLA / R2 LEG AND FOOT / NATIVE SOURCE',
          '680 / 680 / 500 mm | Four main axes | Low ankle and continuous toe-heel support')
    right = copy.deepcopy(s['left_stations_m'])
    for p in right.values(): p[1] = -p[1]
    layout = {'revision': s['revision'], 'source_sha256': source_sha,
              'role': 'appearance_layout_candidate_not_active_SI_contract',
              'coordinate_frame': s['coordinate_frame'], 'left_stations_m': s['left_stations_m'],
              'right_stations_m': right, 'joint_axis': [0, 1, 0],
              'link_lengths_m': s['link_lengths_m'],
              'reference_pitches_from_down_vertical_deg': s['reference_pitches_from_down_vertical_deg'],
              'deep_crouch_pitches_from_down_vertical_deg': s['deep_crouch_pitches_from_down_vertical_deg'],
              'reference_height_with_upper_context_m': s['reference_height_m'],
              'deep_crouch_height_with_upper_context_m': s['deep_crouch_height_m'],
              'old_height_lock_released': True, 'physical_accepted': False}
    (ROOT/'source'/'joint_layout.json').write_text(json.dumps(layout, indent=2)+'\n')
    readme = """# Gorilla R2 腿部造型交接包

先看 `images/uri_leg_concept.png` 和 `images/leg_review.png`，再看 `design_brief.md`。

三段 Z 型、默认屈膝、低脚踝、重做的贯通脚底。常态约 2.26 m，进一步屈膝约 2.00 m；不再追求旧的 2.65 m。

孔位、轴承、材料壁厚、驱动与承载验算由「启动 Gorilla V0.1 工程方案」负责。本包交付可编辑造型提案，用户尚未验收；不代表数吨承载或制造放行。

导入使用 `source/leg_design_legs.glb`（仅新腿，glTF Y-up），或 `source/leg_design_scene.json`（米制 X 前 / Y 左 / Z 上）；关节位置独立列在 `source/joint_layout.json`。`source/leg_design_context.blend` 和下蹲版均可独立打开编辑。

原生视图严格使用同一几何，121 个指定姿态未发现有限造型体穿插或穿地。几何检查未包含新版实际驱动、载荷或结构强度。URI 原画是同源几何指导的画面润色，细缝与表面处理以概念属性使用。

上身设计依据是 `references/approved_upper_aa3.png`。整机预览的 C15 上身只用于空间与比例参照，不能替换已认可原画。

原生文件和查看本包无需原工程仓库。Python 重建脚本则依赖本 Art 工作区的 `leg_redesign_r1/native` 定位源、三角网格工具与 Blender；本包不是工程仿真启动器。

文件版本和证据绑定见 `handoff_manifest.json`。旧 R1 六缸布置在整机合装中存在干涉，不能继承其单腿通过结论或当成本版有效驱动方案。
"""
    (ROOT/'readme.md').write_text(readme)
    files = [p for p in ROOT.rglob('*') if p.is_file() and p.suffix in ('.py', '.json', '.txt', '.md', '.png', '.jpg', '.glb', '.blend')
             and '__pycache__' not in p.parts and p.name != 'handoff_manifest.json']
    manifest = {'revision': 'leg_design_r2', 'owned_deliverable': 'Art appearance/layout handoff',
                'engineering_owner': '启动 Gorilla V0.1 工程方案',
                'source_sha256': source_sha, 'files':
                [{'path': str(p.relative_to(ROOT)), 'sha256': sha(p), 'bytes': p.stat().st_size} for p in sorted(files)],
                'source_records': [
                    {'source': str(OLD/'native'/'candidate_scene.json'), 'sha256': s['source_hashes']['frame_guide'], 'use': 'Prior finite kinematic guide, not a manufacturing requirement'},
                    {'source': str(OLD/'native'/'grounded_crouch_report.json'), 'sha256': s['source_hashes']['grounded_fk'], 'use': 'Prescribed unloaded crouch FK'},
                    {'source': str(OLD/'native'/'upper_fit_interface_scene.json'), 'sha256': s['source_hashes']['upper_context'], 'use': 'Unaccepted C15 upperbody fit context, retained without rescaling'}],
                'checks': {'sampled_pose_count': check['pose_samples'],
                           'appearance_material_intersections': len(check['collision_events']),
                           'appearance_floor_events': len(check['floor_events']),
                           'source_bound_native_views': len(render['renders']),
                           'exchange_parts': exchange['part_count'],
                           'max_exchange_vertex_distance_m': exchange['max_vertex_distance_m']},
                'ready_for_engineering_review': True, 'appearance_accepted': False, 'physical_accepted': False,
                'not_frozen': s['not_frozen']}
    mf = ROOT/'handoff_manifest.json'; mf.write_text(json.dumps(manifest, indent=2)+'\n')
    files.append(mf)
    output = ROOT.parent/'gorilla_leg_design_r2_handoff.zip'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(files): z.write(p, Path('leg_design_r2')/p.relative_to(ROOT))
    with zipfile.ZipFile(output) as z: assert z.testzip() is None
    print('ART_HANDOFF', str(output), output.stat().st_size, 'bytes,', len(files), 'files', flush=True)


if __name__ == '__main__': main()
