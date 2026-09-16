"""r027 editable authored assembly; baked per-part colors and boarding mechanisms."""
from pathlib import Path
import sys,json,gzip,copy,hashlib,math,shutil
import numpy as np
import trimesh as tm
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
O=Path(__file__).resolve().parents[1];R=O/'support';sys.path.insert(0,str(R/'source'))
from art_export import export
from texture_factory import build as build_textures
build_textures(json.loads((O/'source/texture_recipe.json').read_text()),O/'assets/generated')
from mesh_profiles import extrude_xz
A=O/'baseline';P=O/'baseline/finish'
a=json.loads(gzip.decompress((A/'source/assembly.json.gz').read_bytes()));theme=json.loads((P/'palettes/E2.json').read_text())
changes=[];added=[];removed=[];serial=0
# Store original colors and moving vertex metadata. Assign semantic color roles
# before export, never world-space masks on a moving model.
a['colors'].update(theme['palette'])
def role(h):
 k='finish_'+h.lower();a['colors'][k]=h;return k
red=role('A51B2B');silver=role('899292');dark=role('454E50');logo=role('C4C8BF')
region={p['name']:p for p in json.loads((P/'body_paint_selection.json').read_text())['parts']}
for p in a['parts']:
 original=p['material'];key=p['group']+'__'+original
 h=theme['node_palette_overrides'].get(key)
 if p['name'] in region:h=region[p['name']]['color']
 label=p['name'].split('_',1)[-1]
 if label in ['rooftop_receiver','vent_roof','roof_machine_case']:h='596264'
 if p['group']=='front' and (label.startswith('paint_') and any(k in label for k in ['tab','trim','outline','corner'])):h='A51B2B'
 if label in ['crane_pedestal','crane_slew','crane_neck_ring','crane_column_cover']:h={'crane_pedestal':'424B4D','crane_slew':'606C70','crane_neck_ring':'889294','crane_column_cover':'596468'}[label]
 if h:p['material']=role(h)
# Editable additions use closed geometry, grouped by physical body.
def add(label,m,mat,group,category='detail'):
 global serial
 name=f'r027_{serial:04d}_{label}';serial+=1
 a['parts'].append(dict(name=name,group=group,material=mat,vertices=m.vertices.tolist(),faces=m.faces.tolist(),motion={'kind':'static'},physical_body=group,assembly=category));added.append(name);return name
def box(label,c,size,mat,group,category='detail'):
 m=tm.creation.box(size);m.apply_translation(c);return add(label,m,mat,group,category)
def rod(label,p,q,r,mat,group):
 p=np.array(p);q=np.array(q);m=tm.creation.cylinder(radius=r,height=np.linalg.norm(q-p),sections=10);m.apply_transform(tm.geometry.align_vectors([0,0,1],q-p));m.apply_translation((p+q)/2);return add(label,m,mat,group)
# Thicken boxed deck/fascia downward; top contact/door datum remains unchanged.
for p in a['parts']:
 label=p['name'].split('_',1)[-1]
 if label in ['front_deck','rear_deck','front_side_fascia','rear_side_fascia']:
  v=np.array(p['vertices']);top=v[:,2].max();depth=np.ptp(v[:,2]);extra=.4 if label.endswith('_deck') else .50
  v[:,2]=top-(top-v[:,2])*(depth+extra)/depth;p['vertices']=v.tolist();changes.append(dict(name=p['name'],change='downward boxed-platform depth',old_depth=depth,new_depth=depth+extra))
# Offset access ladders alongside the inward doors. Preserve their plane/roof reach.
for group in ['rear','tail']:
 pedestal=[p for p in a['parts'] if p['group']==group and p['name'].endswith('_crane_pedestal')]
 for p in a['parts']:
  if p['group']!=group or not p['name'].endswith(('_service_ladder_rail','_service_ladder_rung')):continue
  v=np.array(p['vertices']);center=v.mean(0);base=min(pedestal,key=lambda q:np.linalg.norm(np.array(q['vertices']).mean(0)[:2]-center[:2]));cx=np.array(base['vertices']).mean(0)[0]
  # All ladder geometry receives same +X shift; clear door +/-0.55 and margin.
  v[:,0]+=1.04;p['vertices']=v.tolist();changes.append(dict(name=p['name'],change='ladder moved +1.04m along pedestal face'))
# Lift access gaps: perimeter rail segments crossing the boarding opening are cut.
keep=[]
for p in a['parts']:
 label=p['name'].split('_',1)[-1];v=np.array(p['vertices']);lo=v.min(0);hi=v.max(0);g=p['group'];cx=a['groups'].get(g,[999,0,0])[0]
 if g in ['front','rear','tail'] and ('walk_rail' in label or 'walk_post' in label) and lo[2]>7.4 and hi[2]<9.3 and abs(v[:,1].mean())>12.7 and lo[0]<cx+1.75 and hi[0]>cx-1.75:
  if np.ptp(v[:,0])>3.5:
   for j,(l,h) in enumerate([(lo[0],cx-1.78),(cx+1.78,hi[0])]):
    if h-l>.08:
     q=copy.deepcopy(p);vv=v.copy();vv[:,0]=l+(vv[:,0]-lo[0])*(h-l)/max(hi[0]-lo[0],1e-6);q['vertices']=vv.tolist();q['name']+=f'_boarding_split{j}';keep.append(q)
  removed.append(p['name']);continue
 keep.append(p)
a['parts']=[p for p in keep if 'bridge_emblem' not in p['name'] and 'frame_identifier' not in p['name']]
# Raised face paint rather than coincident decals; bump existing thin markings
# along their side-facing normal. Small intentional 8mm paint stand-off at this scale.
for p in a['parts']:
 label=p['name'].split('_',1)[-1]
 if 'paint_' in label:
  v=np.array(p['vertices']);ext=np.ptp(v,axis=0)
  if ext[1]<.04:
   v[:,1]+=math.copysign(.008,float(v[:,1].mean()));p['vertices']=v.tolist()
# Reference's stepped utility front: louvers, perimeter trims and grouped
# inspection features on broad lower side panels, not unrelated decoration.
for side in [-1,1]:
 for x in [5.5,8.4,11.3]:
  for z in np.linspace(11.25,12.25,6):box('service_louver',(x,side*8.131,z),(1.28,.045,.06),dark,'front')
 for x in [17.8,21.5,25.0]:
  for z in [11.75,12.15]:box('bridge_lower_trim',(x,side*3.63,z),(2.15,.035,.035),dark,'front')
# Add real raised wordmark geometry, font outlines triangulated in 2D. No decals.
font=FontProperties(fname='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
def lettering(word,x,y,z,height,group):
 path=TextPath((0,0),word,size=1,prop=font);verts=path.vertices;codes=path.codes
 # Text contours from to_polygons; triangulate using matplotlib's path masks
 # via manifold cross section. It preserves glyph counters/holes.
 import manifold3d as mf
 polys=path.to_polygons();cs=mf.CrossSection([np.asarray(poly,dtype=np.float64) for poly in polys],mf.FillRule.EvenOdd)
 bb=cs.bounds();scale=height/(bb[3]-bb[1]);cs=cs.scale([scale,scale]);solid=cs.extrude(.014);raw=solid.to_mesh();m=tm.Trimesh(vertices=np.asarray(raw.vert_properties)[:,:3],faces=np.asarray(raw.tri_verts),process=False)
 vv=m.vertices.copy();w=np.ptp(vv[:,0]);vv[:,0]-=(vv[:,0].min()+vv[:,0].max())*.5;vv[:,1]-=vv[:,1].min()
 # Face toward respective side, text readable from outside.
 side=1 if y>0 else -1;m.vertices=np.column_stack([x+(-side)*vv[:,0],y+side*vv[:,2],z+vv[:,1]])
 if side<0:m.faces=m.faces[:,::-1]
 return add('Sainiverse_wordmark',m,logo,group)
for side in [-1,1]:
 lettering('Sainiverse',31.8,side*3.56,11.56,.27,'front')
 for g in ['front','rear','tail']:
  cx=a['groups'][g][0];lettering('SAINIVERSE',cx+7.2,side*13.12,6.06,.30,g)
# Fine antenna segmentation and service edges follow the actual face frame.
# Split fine surface pattern into sparse cells to avoid high-frequency shimmer.
for p in a['parts']:
 if p['name'].endswith('_panel_face_pattern'):
  m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False);components=m.split(only_watertight=False)
  # retain every second authored element: source shape unchanged, lower density.
  m=tm.util.concatenate(components[::2]);p['vertices']=m.vertices.tolist();p['faces']=m.faces.tolist();changes.append(dict(name=p['name'],change='half-density physical antenna elements to reduce shimmer'))
# Six 3.2 x 2.2m robot boarding platforms, 3-stage nested guide. All moving
# pieces are authored in their own named physical groups, no runtime mesh build.
lifts=[]
for hull in ['front','rear','tail']:
 cx=float(a['groups'][hull][0])
 for side in [-1,1]:
  stem=f'lift_{hull}_{"left" if side>0 else "right"}';y=side*13.3;z=7.325
  stages=[stem+'_out']+[stem+f'_stage{i}' for i in [1,2,3]]
  for name in stages:a['groups'][name]=[cx,y,z]
  for dx in [-1.42,1.42]:
   box('lift_mount',(cx+dx,side*11.90,7.1),(.22,.6,.9),'steel',hull,'boarding_lift')
   box('lift_out_slide',(cx+dx,side*13.1,7.17),(.19,2.5,.18),'edge',stages[0],'boarding_lift')
   # Fixed plus three nested rail sizes, visibly overlapped at every extension.
   for i,g in enumerate(stages):
    sz=.26-i*.04;box('telescopic_guide',(cx+dx,side*(12.44+i*.03),9.275),(sz,sz,3.9),'steel' if i==0 else 'silver',g,'boarding_lift')
  final=stages[-1]
  box('boarding_floor',(cx,y,z),(3.2,2.2,.25),dark,final,'boarding_lift')
  for dx in [-1.48,1.48]:
   for yy in [-.95,.95]:rod('lift_guard_post',[cx+dx,y+yy,7.45],[cx+dx,y+yy,8.5],.038,'edge',final)
   rod('lift_guard_rail',[cx+dx,y-.95,8.5],[cx+dx,y+.95,8.5],.038,'edge',final)
  # Wide side gate remains an opening, permitting loading at either end.
  for dx in [-1.52,1.52]:box('lift_edge_warning',(cx+dx,y,7.458),(.07,2.15,.016),'yellow',final)
  for yy in [-.90,.90]:box('lift_non_slip',(cx,y+yy,7.46),(2.7,.10,.02),'black',final)
  box('boarding_bridge',(cx,side*12.08,7.42),(3.1,.42,.06),dark,hull)
  box('lift_controls',(cx+1.7,side*11.85,8.10),(.25,.18,.40),dark,hull)
  box('lift_call_marker',(cx+1.7,side*11.96,8.10),(.13,.025,.13),red,hull)
  lifts.append(dict(name=stem,hull=hull,side=side,pivot=[cx,y,z],groups=stages,stroke_out=2.7,stroke_stage=7.35/3,platform_size=[3.2,2.2,.25],masses=[450,180,150,600],payload_assumption_kg=500))
# Recess stowed platforms into the deck rather than overlap the solid floor.
for p in a['parts']:
 if p['name'].split('_',1)[-1] not in ['front_deck','rear_deck','front_side_fascia','rear_side_fascia']:continue
 cx=a['groups'][p['group']][0];m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
 for side in [-1,1]:
  cutter=tm.creation.box([3.24,2.26,2.4]);cutter.apply_translation([cx,side*13.3,7.0]);m=tm.boolean.difference([m,cutter],engine='manifold')
 p['vertices']=m.vertices.tolist();p['faces']=m.faces.tolist()
from architecture import refine
refine(a,box,rod,add,role,extrude_xz)
a["parts"]=[p for p in a["parts"] if not p["name"].endswith("_service_louver")]
# Contact proxies and native source carry the same new dimensions.
from refinement import refine as refine_details
refine_details(a,box,rod,add,role,O)
from boarding_ramps import author as author_ramps
author_ramps(a,lifts,add,box,rod)
from mechanical_revision import apply as mechanical_revision
mechanical_revision(a,add,box,rod,role,O)
from equipment_rig import author as author_equipment
author_equipment(a,add,rod,O)
from habitable_revision import author as author_habitable
author_habitable(a,add,box,rod,role,O)
from finish import classify,write as write_finishes
from art_finish import apply as art_finish
from cockpit_controls import author as author_controls
author_controls(a,add,O)
from interior_identity import author as author_identity
author_identity(a,add,O)
classify(a)
art_selection=art_finish(a)
from service_labels import build as build_labels,assign as assign_labels
build_labels(O/'assets/generated');assign_labels(a)
from full_surface import assign,atlas,report
assign(a);atlas(O/'assets/generated');report(a,O/'reports/surface_coverage.json')
(O/'reports/art_selection.json').write_text(json.dumps(art_selection,indent=2))
result=export(a,O/'assets/Sainiverse_v0.1.glb')
(O/'source/assembly.json.gz').write_bytes(gzip.compress(json.dumps(a,separators=(',',':')).encode(),mtime=0))
(O/'source/lifts.json').write_text(json.dumps(lifts,indent=2)+'\n')
style=json.loads((O/'baseline/atelier/style.json').read_text());style['palette']=a['colors'];style['name']='黑色';style['ground_color']='D9DDD1';style['ambient_color']='c6c3d6';style['ambient_energy']=.48;style['sun_color']='fff9ed';style['sun_energy']=.96
(O/'style.json').write_text(json.dumps(style,ensure_ascii=False,indent=2)+'\n')
for p in (O/'baseline/atelier/assets').glob('*.gdshader'):shutil.copy2(p,O/'assets'/p.name)
for name in ['sai_scale_figure.glb','microduck_scale_figure.glb']:assert (O/'assets'/name).exists()
for name in ['interior.json','access.json','access_probes.json']:shutil.copy2(A/'source'/name,O/'source'/name)
room=json.loads((O/'source/interior.json').read_text());room['screens']=a['habitable_revision']['screens'];room['doors']=[d for d in room['doors'] if d['name'] not in a['habitable_revision']['obsolete_door_groups']];room['stair_route']=a['habitable_revision']['stair_route'];(O/'source/interior.json').write_text(json.dumps(room,indent=2))
(O/'reports/build.json').write_text(json.dumps(dict(changes=changes,removed=removed,added=added,parts=len(a['parts']),groups=len(a['groups']),lifts=6,**result),indent=2)+'\n')
print(json.dumps(dict(parts=len(a['parts']),groups=len(a['groups']),**result)),flush=True)

write_finishes(O)

shutil.copy2(O/"source/track_enamel.gdshader",O/"assets/track_enamel.gdshader")
