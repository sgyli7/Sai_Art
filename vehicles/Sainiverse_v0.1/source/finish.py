"""Semantic finishes and saved color themes, separate from mechanism bindings."""
from pathlib import Path
import json,shutil

def classify(a):
 a['colors']['deck_steel']='61676B'
 for p in a['parts']:
  n=p['name']
  if n.endswith(('raised_panel_deck','panel_gallery_roof')):
   a['colors']['roof_steel']='565E62';p['material']='roof_steel'
  if any(k in n for k in ['front_deck','rear_deck','walkdeck','walk_deck','walk_plate','walkplate','stair_tread','upper_landing','lower_landing','boarding_floor','boarding_bridge','instrument_gallery_floor']):p['material']='deck_steel'

def write(O):
 shutil.copy2(O/"source/surface.gdshader",O/"assets/surface.gdshader")
 style=json.loads((O/'style.json').read_text());style['name']='Sainiverse_v0.1';style['theme']='black';style['basis']='Hand-painted semantic panel atlas; matte toon bands and inherited dynamic track ink; no stochastic paint normal.';style['palette']['deck_steel']='61676B'
 (O/'style.json').write_text(json.dumps(style,indent=2,ensure_ascii=False))
 for key,label,color in [('black','黑色','202124'),('desert','沙漠','B29A77'),('white','白色','D9DCD7'),('blue','蓝色','315B78')]:
  palette=dict(style['palette']);palette['ivory']=color;palette['finish_202124']=color;palette['art_workbay_wall']=color
  for name in list(palette):
   for prefix in ['art_','wear_','logo_','warn_']:
    if name.startswith(prefix):palette[name]=palette.get(name[len(prefix):],palette[name])
  for name in list(palette):
   if name.startswith('decal_'):palette[name]=palette.get(name.split('_',2)[2],palette[name])
  out=dict(id=key,name=label,vehicle_name_en='Sainiverse_v0.1',palette=palette,deck_color='61676B',crane_color='D5AD3D')
  (O/'themes'/f'{key}.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
