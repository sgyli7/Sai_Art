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
 for key,label,color in [('black','黑色','202124'),('desert','沙漠','B29A77'),('white','白色','D9DCD7'),('blue','蓝色','315B78'),('yellow','黄色','C7A047')]:
  palette=dict(style['palette']);palette['ivory']=color;palette['finish_202124']=color;palette['art_workbay_wall']=color
  # Exterior livery is a cue, not a flood fill: matte cool panels / warm or
  # complementary textiles / dark structure / pale low-glare headlining.
  interior={
   'black':('343D43','907354','51483F','242C32','C5C6BE','AF2635'),
   'white':('56656B','657D84','344B55','303A40','D5D3C9','AF774F'),
   'blue':('394952','A38565','645345','26343E','CCD0C8','8CABB7'),
   'yellow':('444C4D','687777','354749','2B3438','CFCCBC','C8A657'),
   'desert':('4E5651','718079','43564F','303C37','D0C8B7','B49A70')
  }[key]
  palette.update(zip(['cabin_console','cabin_upholstery','cabin_bolster','cabin_frame','cabin_lining','cabin_trim'],interior))
  palette['cabin_panel']=interior[4]
  palette.update(cabin_metal='879194',cabin_grip='202324',cabin_lounge={'black':'776C60','white':'60747D','blue':'A28D70','yellow':'74766A','desert':'796A58'}[key])
  for name in list(palette):
   for prefix in ['art_','wear_','logo_','warn_']:
    if name.startswith(prefix):palette[name]=palette.get(name[len(prefix):],palette[name])
  for name in list(palette):
   if name.startswith('decal_'):palette[name]=palette.get(name.split('_',2)[2],palette[name])
  out=dict(id=key,name=label,vehicle_name_en='Sainiverse_v0.1',palette=palette,deck_color='61676B',crane_color='D5AD3D')
  (O/'themes'/f'{key}.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
