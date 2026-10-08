"""Diagnostic page assembly; no artwork generation or image retouching."""
from pathlib import Path
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'source'/'reference_scene.json'
source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'source'/'render_manifest.json').read_text())
assert manifest['source_sha256']==source_sha
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
large=ImageFont.truetype(font,31);small=ImageFont.truetype(font,21)
def flatten(p):
    picture=Image.open(p).convert('RGBA')
    background=Image.new('RGBA',picture.size,'#eceff2')
    background.alpha_composite(picture)
    return background.convert('RGB')
page=Image.new('RGB',(2400,1130),'white');draw=ImageDraw.Draw(page)
draw.text((25,18),'REFERENCE GEOMETRY / WORKING RECONSTRUCTION',font=large,fill='#243f57')
draw.text((25,62),'Same source in all views | Geometry unaccepted | No image generation',font=small,fill='#566575')
for i,name in enumerate(('front','left','rear')):
    p=ImageOps.contain(flatten(ROOT/'images'/(name+'.png')),(770,970))
    page.paste(p,(i*800+(800-p.width)//2,103))
    draw.rectangle((i*800+10,96,(i+1)*800-10,1085),outline='#b7c1cb')
    draw.text((i*800+25,1095),name.upper(),font=small,fill='#243f57')
page.save(ROOT/'images'/'native_three_view_check.png')
comparison=Image.new('RGB',(1520,1045),'white');draw=ImageDraw.Draw(comparison)
draw.text((20,16),'USER REFERENCE                         NATIVE CAMERA / DEPTH HYPOTHESIS',font=small,fill='#243f57')
comparison.paste(Image.open(ROOT/'references'/'primary_user_reference.jpg').convert('RGB'),(6,52))
comparison.paste(flatten(ROOT/'images'/'reference_camera.png'),(766,52))
draw.text((20,1008),'The cropped sole and hidden surfaces are unverified. This is not an approved reconstruction.',font=small,fill='#566575')
comparison.save(ROOT/'images'/'reference_camera_check.png')
initial=json.loads((ROOT/'source'/'geometry_check.json').read_text())
initial['source_scene_file']='reference_scene_untrimmed.json'
initial['active_geometry_audit']='reconstruction_audit.json'
(ROOT/'source'/'geometry_check.json').write_text(json.dumps(initial,indent=2)+'\n')
record={'source_sha256':source_sha,'native_source_owns_all_turnaround_geometry':True,
        'imagegen_used':False,'page_assembly_only':True,
        'pages':['images/native_three_view_check.png','images/reference_camera_check.png'],
        'reference_geometry_accepted':False,'ready_for_engineering_handoff':False,
        'scope':'Work-in-progress geometry audit, not completed original artwork or a replacement engineering contract.'}
(ROOT/'source'/'review_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
print('GEOMETRY_REVIEW_PAGES',len(record['pages']),flush=True)
