"""Connected load paths, closed skins, service windows and an electric-drive layout.
Geometry and provisional component mass are authored together; not a fabrication rating.
"""
import copy,json,math
import numpy as np
import trimesh as tm

def mesh(p):return tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
def replace(p,m):p.update(vertices=m.vertices.tolist(),faces=m.faces.tolist())
def boxmesh(c,s):
 m=tm.creation.box(s);m.apply_translation(c);return m
def cyl(p,q,r,sections=16):
 p=np.array(p);q=np.array(q);m=tm.creation.cylinder(radius=r,height=np.linalg.norm(q-p),sections=sections);m.apply_transform(tm.geometry.align_vectors([0,0,1],q-p));m.apply_translation((p+q)/2);return m

def apply(a,add,box,rod,role,O):
 masses=[];proof={}
 def structural(n,m,mat,g,density=7850.):
  add(n,m,mat,g);masses.append({'name':a['parts'][-1]['name'],'body':g,'mass_kg':abs(m.volume)*density,'center_source_m':m.center_mass.tolist(),'inertia_source_diag_kg_m2':(np.diag(m.moment_inertia)*density).tolist()})
 def beam(n,p,q,w,h,wall,mat='steel',g='front'):
  p=np.array(p);q=np.array(q);L=np.linalg.norm(q-p)
  outer=tm.creation.box([w,h,L]);inner=tm.creation.box([w-2*wall,h-2*wall,L+.02]);m=tm.boolean.difference([outer,inner],engine='manifold')
  m.apply_transform(tm.geometry.align_vectors([0,0,1],q-p));m.apply_translation((p+q)/2);structural(n,m,mat,g)
 # One closed deck/fascia skin: colour is a paint band on this skin, never stacked faces.
 removed=[]
 for g in ['front','rear','tail']:
  deck=next(p for p in a['parts'] if p['group']==g and p['name'].endswith(('_front_deck','_rear_deck')))
  donors=[p for p in a['parts'] if p['group']==g and any(p['name'].endswith('_'+n) for n in ['front_side_fascia','rear_side_fascia','front_lower_chord','rear_lower_chord','front_lower_web','rear_lower_web'])]
  combined=tm.boolean.union([mesh(deck)]+[mesh(p) for p in donors],engine='manifold');replace(deck,combined);removed+=donors
 a['parts']=[p for p in a['parts'] if p not in removed];proof['unified_fascia_parts']=len(removed)
 # Open the complete fixed walkway stack over the lift pocket, not just the main slab.
 for p in a['parts']:
  n=p['name'];g=p['group']
  if g not in ['front','rear','tail']:continue
  cx=a['groups'][g][0]
  if any(t in n for t in ['walk_plate','walkplate','_front_deck','_rear_deck','paint_access_tab']):
   m=mesh(p)
   for side in [-1,1]:
    if not len(m.faces):break
    cut=boxmesh([cx,side*13.35,7.70],[3.40,2.45,1.30]);m=tm.boolean.difference([m,cut],engine='manifold')
   replace(p,m)
  if n.endswith('_boarding_bridge'):
   v=np.array(p['vertices']);sgn=np.sign(v[:,1].mean());replace(p,boxmesh([cx,sgn*12.05,7.42],[3.10,.27,.06]))
 a['parts']=[p for p in a['parts'] if p['faces']]
 # Actual welded root frame connects the cabin's existing lower girders to the deck.
 for side in [-1,1]:
  y=side*2.8
  structural('cabin_root_foot',boxmesh([14.55,y,7.50],[1.15,1.05,.10]),'steel','front')
  beam('cabin_root_column',[14.55,y,7.50],[14.55,y,9.52],.62,.62,.025)
  beam('cabin_root_haunch',[12.2,y,7.40],[18.3,y,9.50],.46,.58,.025)
  beam('cabin_underfloor_girder',[14.4,y,9.33],[32.0,y,9.33],.48,.54,.022)
 for x in [14.55,18.3,24.,30.8]:beam('cabin_cross_bearer',[x,-3.55,9.36],[x,3.55,9.36],.28,.30,.018)
 # Replace the two capped pipe segments with a single watertight bent pipe skin.
 pipes=[p for p in a['parts'] if p['name'].endswith(('_roof_machine_pipe','_roof_machine_pipe_down'))]
 a['parts']=[p for p in a['parts'] if p not in pipes]
 for side in [-1,1]:
  if side==1:
   mirrored=cooling_pipe.copy();mirrored.apply_scale([1,-1,1]);add('continuous_cooling_elbow',mirrored,role('778686'),'front');continue
  y=side*1.4;points=[[7.8,y,13.36],[7.8,y,13.91]]
  # Centreline tangent quarter circle, 0.29 m bend radius.
  for t in np.linspace(math.pi,math.pi/2,7):points.append([8.09+.29*math.cos(t),y,13.91+.29*math.sin(t)])
  points.append([8.80,y,14.20]);pieces=[cyl(p,q,.18,20) for p,q in zip(points,points[1:]) if np.linalg.norm(np.array(q)-p)>1e-6]
  for p in points[1:-1]:
   b=tm.creation.icosphere(subdivisions=2,radius=.18);b.apply_translation(p);pieces.append(b)
  pipe=tm.boolean.union(pieces,engine='manifold');add('continuous_cooling_elbow',pipe,role('778686'),'front');assert pipe.is_watertight;cooling_pipe=pipe.copy()
 # Remove opaque little port blocks. Actual openings + glazing at equipment-room sides.
 a['parts']=[p for p in a['parts'] if not p['name'].endswith('_fore_service_small_port')]
 shell=next(p for p in a['parts'] if p['name'].endswith('_fore_service_shell'));m=mesh(shell)
 for side in [-1,1]:
  for x in [5.5,8.4,11.3]:
   m=tm.boolean.difference([m,boxmesh([x,side*8.,11.78],[1.18,.90,.72])],engine='manifold')
   outer=boxmesh([x,side*8.015,11.78],[1.30,.10,.84]);cut=boxmesh([x,side*8.015,11.78],[1.10,.2,.64]);frame=tm.boolean.difference([outer,cut],engine='manifold');add('equipment_window_frame',frame,'edge','front')
   box('equipment_window_glass',[x,side*7.98,11.78],[1.16,.025,.70],'cabin_glass','front')
 replace(shell,m)
 # Visible electric drive path: under-deck distribution spine, motor/reducer per belt,
 # shaft into the existing fixed drive sprocket. No axle links independent roadwheels.
 for g in ['front','rear','tail']:
  cx=a['groups'][g][0]
  beam('underdeck_power_spine',[cx-14.,0,6.30],[cx+14.,0,6.30],.65,.45,.015,'steel',g)
  for x in [-10.5,10.5]:
   for side in [-1,1]:beam('underdeck_distribution_branch',[cx+x,0,6.30],[cx+x,side*11.8,6.30],.26,.20,.010,'steel',g)
 for g,pivot in list(a['groups'].items()):
  if '_bogie_' not in g:continue
  cx,cy,_=pivot;x=cx-4.15
  for side in [-1,1]:
   # Housing is hollow; rotor and shaft have their own physical mass.
   p=[x,cy+side*.10,2.40];q=[x,cy+side*.95,2.40]
   housing=tm.boolean.difference([cyl(p,q,.53),cyl([x,cy+side*.125,2.4],[x,cy+side*.925,2.4],.49)],engine='manifold')
   structural('traction_motor_housing',housing,role('485658'),g)
   structural('traction_motor_rotor',cyl([x,cy+side*.15,2.4],[x,cy+side*.88,2.4],.31),'steel',g)
   structural('final_drive_shaft',cyl([x,cy+side*.65,2.4],[x,cy+side*1.62,2.4],.15),'silver',g)
   gearbox=tm.boolean.difference([cyl([x,cy+side*.86,2.4],[x,cy+side*1.22,2.4],.60),cyl([x,cy+side*.88,2.4],[x,cy+side*1.20,2.4],.54)],engine='manifold');structural('planetary_reducer_case',gearbox,'steel',g)
   beam('motor_cradle',[x,cy+side*.42,2.7],[x,cy+side*.42,3.15],.24,.30,.015,'steel',g)
   rod('traction_power_conduit',[x,cy+side*.38,2.94],[cx,cy+side*.38,2.94],.055,'black',g)
 # Bottom skin is paint/steel, never deck tread. Upper face remains grey steel.
 a['mechanical_mass_additions']=masses
 proof['added_mass_kg']=sum(x['mass_kg'] for x in masses);proof['mass_note']='Explicit provisional metal volumes and rotor solids. Not a selected manufacturer assembly or certified cantilever rating.'
 (O/'reports/mechanical_revision.json').write_text(json.dumps(proof,indent=2))
