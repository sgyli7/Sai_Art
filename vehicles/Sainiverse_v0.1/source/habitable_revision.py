"""Reference-led occupied architecture and serviceable electro-hydraulic underframe.
Dimensions are design choices for this fictional carrier, not aircraft certification.
"""
import json,re,math
import numpy as np
import trimesh as tm
from shapely.geometry import Polygon
from mechanical_revision import mesh,replace,boxmesh,cyl
from refinement import rounded_box as _rounded_box
def rounded_box(bounds,r):return _rounded_box(bounds,r,segments=8)
from cockpit_geometry import instrument_mounts,revolved

def author(a,add,box,rod,role,O):
 contacts=[];removed=[];mass=[];route=[];screens=[]
 floor=11.35;roomfloor=7.55
 a['colors'].update(cabin_lounge='776C60',cabin_console='343D43',cabin_upholstery='907354',cabin_bolster='51483F',cabin_frame='242C32',cabin_metal='879194',cabin_grip='202324',cabin_lining='C5C6BE',cabin_trim='AF2635')
 steel=role('505C60');lining=role('A9B0A7');panel='cabin_console';seat='cabin_upholstery';ivory='ivory'
 def put(n,m,mat='steel',collision=False,cat=None,g='front'):
  name=add('r032_'+n,m,mat,g)
  p=a['parts'][-1]
  if cat:p['interior_category']=cat
  if collision:contacts.append(dict(name=name,body=g,type='convex',vertices_source_m=m.vertices.tolist()))
  return p
 def bx(n,c,s,mat='steel',collision=False,cat=None,g='front'):
  return put(n,boxmesh(c,s),mat,collision,cat,g)
 def tube(n,p,q,w=.24,d=.30,wall=.012,g='front'):
  p=np.array(p);q=np.array(q);l=np.linalg.norm(q-p)
  m=tm.boolean.difference([boxmesh([0,0,0],[w,d,l]),boxmesh([0,0,0],[w-2*wall,d-2*wall,l+.02])],engine='manifold');m.apply_transform(tm.geometry.align_vectors([0,0,1],q-p));m.apply_translation((p+q)/2)
  part=put(n,m,steel,g=g)
  mass.append(dict(name=part['name'],body=g,mass_kg=abs(m.volume)*7850,center_source_m=m.center_mass.tolist(),inertia_source_diag_kg_m2=(np.diag(m.moment_inertia)*7850).tolist()))
 def rail(n,p,q,r=.03,mat='edge'):return put(n,cyl(p,q,r,10),mat)
 def panel_face(n,c,w,h,tile,axis=0,angle=0):
  m=boxmesh([0,0,0],[.035,w,h] if axis==0 else [w,.035,h] if axis==1 else [w,h,.035])
  if angle:m.apply_transform(tm.transformations.rotation_matrix(angle,[0,1,0]))
  m.apply_translation(c);p=put(n,m,panel,cat='console');p['cockpit_tile']=tile;p['cockpit_axis']=axis;p['cockpit_transform']=dict(center=c,angle=angle,axis=axis,width=w,height=h);return p
 # Rack webs form one welded side frame; remove coincident butt/overlap faces.
 for hull in ['front','rear','tail']:
  for side in [-1,1]:
   webs=[p for p in a['parts'] if p['group']==hull and p['name'].endswith('_tank_side_rack_web') and np.sign(np.array(p['vertices'])[:,1].mean())==side]
   if len(webs)>1:
    replace(webs[0],tm.boolean.union([mesh(p) for p in webs],engine='manifold'))
    a['parts']=[p for p in a['parts'] if p not in webs[1:]]
 # Drop the fake pedestal glass; replace with a recessed inspection grille above door.
 a['parts']=[p for p in a['parts'] if not p['name'].endswith('_crane_pedestal_window')]
 for p in list(a['parts']):
  if p['name'].endswith('_crane_pedestal_hatch'):
   lo,hi=mesh(p).bounds;c=(lo+hi)/2;sgn=np.sign(c[1]-a['groups'][p['group']][1]);y=c[1]+sgn*.066
   # Hatch label stays in its own reading area; grille is wholly above its top.
   bx('pedestal_inspection_bezel',[c[0],y,10.63],[.92,.06,.38],steel,g=p['group'])
   for z in np.linspace(10.50,10.76,5):bx('pedestal_inspection_slot',[c[0],y+sgn*.035,z],[.72,.012,.028],'black',g=p['group'])
 # Fixed deck and bridge share one solid; the moving platform keeps the 15 mm gap.
 for g in ['front','rear','tail']:
  p=next(p for p in a['parts'] if p['group']==g and p['name'].endswith(('_front_deck','_rear_deck')))
  bridges=[q for q in a['parts'] if q['group']==g and q['name'].endswith('_boarding_bridge')]
  replace(p,tm.boolean.union([mesh(p)]+[mesh(q) for q in bridges],engine='manifold'))
  a['parts']=[q for q in a['parts'] if q not in bridges]
 # Telescoping guides are nested open tubes, not co-capped solid bars.
 for p in a['parts']:
  if p['name'].endswith('_telescopic_guide'):
   m=mesh(p);lo,hi=m.bounds;c=(lo+hi)/2;s=hi-lo;c[1]=np.sign(c[1])*12.50
   replace(p,tm.boolean.difference([boxmesh(c,s),boxmesh(c,[s[0]-.024,s[1]-.024,s[2]+.02])],engine='manifold'))
 # Rail cassette is fixed to the hull; long inner beams retain 2.05 m overlap at full extension.
 a['parts']=[p for p in a['parts'] if not p['name'].endswith(('_lift_out_slide','_lift_mount'))]
 for hull in ['front','rear','tail']:
  cx=a['groups'][hull][0]
  for side in [-1,1]:
   stem=f'lift_{hull}_{"left" if side>0 else "right"}';outgroup=stem+'_out'
   for dx in [-1.42,1.42]:
    x=cx+dx
    # Hollow fixed guide and hollow moving arm; one authored group per physical body.
    for n,c,sz,wall,g in [('fixed_slide_cassette',[x,side*9.975,7.02],[.38,5.15,.34],.035,hull),('moving_slide_arm',[x,side*10.15,7.02],[.23,4.70,.22],.024,outgroup)]:
     m=tm.boolean.difference([boxmesh(c,sz),boxmesh(c,[sz[0]-2*wall,sz[1]+.03,sz[2]-2*wall])],engine='manifold');put(n,m,steel,g=g)
    for yy in [8.15,10.15,11.75]:
     bx('slide_attachment_plate',[x,side*yy,7.265],[.72,.45,.12],steel,g=hull)
     for xx in [-.27,.27]:put('slide_anchor_bolt',cyl([x+xx,side*yy,7.21],[x+xx,side*yy,7.33],.045,6),'silver',g=hull)
    # Replace plain Cubes with identifiable bearing blocks and opposed running rollers.
    for yy in [11.40,12.27]:
     for xx in [-.17,.17]:
      put('slide_guide_roller',cyl([x+xx-.035,side*yy,7.02],[x+xx+.035,side*yy,7.02],.105,12),'silver',g=hull)
    bx('mast_root_saddle',[x,side*12.50,7.14],[.34,.46,.10],steel,g=outgroup)
    for xx in [-.17,.17]:
     verts=[[x+xx,side*11.78,6.76],[x+xx,side*12.70,7.16],[x+xx,side*12.50,6.76]]
     # Thin triangular cheek webs carry root shear back into the slider.
     m=tm.convex.convex_hull([np.array(v)+[d,0,0] for v in verts for d in [-.025,.025]]);put('mast_root_gusset',m,steel,g=outgroup)
    for i in range(4):
     g=outgroup if i==0 else stem+f'_stage{i}'
     width=.26-i*.04
     for z in [7.58+i*.04,10.98-i*.04]:
      for xx in [-1,1]:
       put('mast_guide_pad',boxmesh([x+xx*(width/2+.003),side*12.50,z],[.006,width*.65,.12]),'black',g=g)
    # Three independent double-acting cylinders: barrel on parent, rod on child.
    # They retain 0.50 m rod/barrel overlap at the 2.45 m stage limit.
    for i in range(3):
     parent=outgroup if i==0 else stem+f'_stage{i}'
     dz=i*.17
     child=stem+f'_stage{i+1}';yy=side*(12.50+.22+i*.15)
     outer=cyl([x,yy,7.70+dz],[x,yy,10.90+dz],.065,12)
     bore=cyl([x,yy,7.68+dz],[x,yy,10.92+dz],.041,12)
     put('mast_hydraulic_barrel',tm.boolean.difference([outer,bore],engine='manifold'),steel,g=parent)
     put('mast_hydraulic_rod',cyl([x,yy,7.55+dz],[x,yy,10.65+dz],.038,12),'silver',g=child)
     for z,g in [(10.94+dz,parent),(7.52+dz,child)]:
      put('mast_cylinder_eye',cyl([x-.085,yy,z],[x+.085,yy,z],.075,12),steel,g=g)
      bx('mast_eye_bracket',[x,side*(12.50+.11+i*.075),z],[.13,.22+i*.15,.09],steel,g=g)
     bx('cylinder_load_hold_valve',[x+.09,yy,10.55+dz],[.09,.10,.18],steel,g=parent)
   bx('slide_crosshead',[cx,side*12.50,7.05],[3.10,.23,.22],steel,g=outgroup)
   # Rack on moving beam; fixed motor/gearcase identifies the horizontal drive.
   bx('slide_rack',[cx-1.42,side*10.15,6.89],[.16,4.60,.035],steel,g=outgroup)
   put('slide_drive_motor',cyl([cx-1.80,side*11.1,6.83],[cx-1.45,side*11.1,6.83],.16,14),steel,g=hull)
   bx('mast_power_unit',[cx+1.42,side*11.6,6.81],[.55,.75,.40],steel,g=hull)
   for q in a['parts']:
    if q['group']==stem+'_stage3' and q['name'].endswith('_boarding_floor'):
     m=mesh(q)
     for dx in [-1.42,1.42]:
      m=tm.boolean.difference([m,boxmesh([cx+dx,side*12.50,7.325],[.29,.29,.50])],engine='manifold')
      for i in range(3):m=tm.boolean.difference([m,boxmesh([cx+dx,side*(12.72+i*.15),7.325],[.19,.15,.50])],engine='manifold')
     replace(q,m)
 for p in a['parts']:
  if p['name'].endswith('_lift_guard_post'):
   v=np.array(p['vertices']);v[v[:,2]<7.46,2]-=.018;p['vertices']=v.tolist()
 # Keep only the first external entry on each side. Remove obsolete moving groups.
 obsolete={g for g in a['groups'] if g.startswith('cabin_door_') and not g.endswith('_1')}
 keep=[]
 for p in a['parts']:
  n=p['name'];v=np.array(p['vertices']);c=(v.min(0)+v.max(0))/2
  kill=p['group'] in obsolete or 'wiper' in n
  if p['group']=='front' and 22.1<c[0]<25.95 and abs(c[1])>3.25 and abs(c[1])<3.90 and any(x in n for x in ['bridge_door','hinge_','door_rotary','flush_threshold']):kill=True
  if n.startswith('r023_') and not any(n.endswith('_'+k) for k in ['continuous_floor','floor_crossbeam','ceiling_panel','ceiling_fastener','ceiling_cable_tray','light_housing','light_diffuser']):kill=True
  if kill:removed.append(n)
  else:keep.append(p)
 a['parts']=keep
 for g in obsolete:del a['groups'][g]
 shell=next(p for p in a['parts'] if p['name'].endswith('_bridge_shell'));m=mesh(shell)
 # Fill only the two redundant door apertures per side, then cut consistent windows.
 fillers=[]
 for side in [-1,1]:
  for x in [23.15,25.05]:fillers.append(boxmesh([x,side*3.40,12.84],[1.48,.21,3.05]))
 m=tm.boolean.union([m]+fillers,engine='manifold')
 for side in [-1,1]:
  for x in [23.15,25.05]:
   cutter=boxmesh([x,side*3.4,13.65],[1.12,.8,1.10]);m=tm.boolean.difference([m,cutter],engine='manifold')
   outer=boxmesh([x,side*3.50,13.65],[1.26,.08,1.24]);inner=boxmesh([x,side*3.5,13.65],[1.10,.3,1.08]);put('bridge_new_window_frame',tm.boolean.difference([outer,inner],engine='manifold'),'edge')
   bx('bridge_new_window_glass',[x,side*3.51,13.65],[1.12,.025,1.10],'cabin_glass',True)
 # Open a real aft bulkhead doorway into the enclosed stair connector.
 m=tm.boolean.difference([m,boxmesh([16.5,0,12.57],[2.0,2.20,2.50])],engine='manifold');replace(shell,m)
 # Extend sole plate to the inside of the actual end and corner shell. No daylight slit.
 fp=next(p for p in a['parts'] if p['name'].endswith('_continuous_floor'))
 poly=Polygon([(16.05,-3.42),(32.02,-3.42),(34.02,-2.77),(34.02,2.77),(32.02,3.42),(16.05,3.42)])
 fm=tm.creation.extrude_polygon(poly,.20,engine='earcut');fm.apply_translation([0,0,11.15]);replace(fp,fm)
 contacts.append(dict(name=fp['name'],body='front',type='convex',vertices_source_m=fm.vertices.tolist()))
 for side in [-1,1]:bx('entry_threshold',[19.15,side*3.50,11.30],[1.40,.54,.10],'cabin_floor',True,'floor')
 # Continuous kick and sill boards terminate at the shell; no floating furniture.
 for side in [-1,1]:
  bx('cabin_kickboard',[25.5,side*3.36,11.49],[16.3,.08,.28],steel,cat='wall')
 # Complete two-person driving station: shaped common instrument panel below glazing.
 for side in [-1,1]:
  y=side*1.58
  section=np.array([[32.0,11.35],[33.85,11.35],[33.85,13.04],[32.65,13.04],[32.02,12.01],[32.0,11.95]])
  verts=np.array([[x,yy,z] for yy in [y-1.12,y+1.12] for x,z in section]);m=tm.convex.convex_hull(verts);put('pilot_console_pedestal',m,panel,True,'console')
  # Face is inclined toward seated pilot, no separate screens floating above desks.
  panel_face('flight_instruments',[32.265,y,12.53],2.08,1.04,12,angle=.55)
  instrument_mounts(put,[32.265,y,12.53],.55,2.08,1.04)
  put('glare_shield',rounded_box([[32.535,y-1.15,13.04],[33.765,y+1.15,13.16]],.045),'cabin_grip',cat='console')
  # Seat aligned +X, adjustable base rails, cushions, back and arm rests.
  for dy in [-.25,.25]:bx('pilot_seat_rail',[30.70,y+dy,11.40],[1.35,.07,.10],steel,cat='seat')
  bx('pilot_seat_plinth',[30.70,y,11.64],[.48,.54,.48],steel,True,'seat')
  put('pilot_seat_cushion',rounded_box([[30.28,y-.39,11.83],[31.10,y+.39,12.01]],.075),seat,True,'seat')
  put('pilot_seat_back',rounded_box([[30.17,y-.40,11.90],[30.36,y+.40,12.85]],.07),seat,True,'seat')
  put('pilot_headrest',rounded_box([[30.21,y-.27,12.83],[30.41,y+.27,13.04]],.06),seat,cat='seat')
  # Contoured safety shell, padded bolsters, harness and adjustable seat mechanism.
  shell=rounded_box([[30.10,y-.455,11.85],[30.31,y+.455,12.88]],.065)
  cut=rounded_box([[30.17,y-.385,11.95],[30.43,y+.385,12.82]],.065)
  put('pilot_seat_shell',tm.boolean.difference([shell,cut],engine='manifold'),'cabin_frame',cat='seat')
  for dy in [-.32,.32]:
   put('seat_side_bolster',rounded_box([[30.35,y+dy-.06,11.96],[31.10,y+dy+.06,12.10]],.045),'cabin_bolster',cat='seat')
   bx('seat_back_seam',[30.16,y+dy,12.40],[.012,.014,.66],'cabin_trim',cat='seat')
  for dy in [-.18,.18]:
   bx('harness_shoulder',[30.38,y+dy,12.42],[.022,.055,.75],'black',cat='seat')
   bx('harness_lap',[30.69,y+dy,12.018],[.48,.055,.02],'black',cat='seat')
  bx('harness_buckle',[30.91,y,12.04],[.08,.18,.032],steel,cat='seat')
  for dy in [-.35,.35]:
   rail('cushion_piping',[30.40,y+dy,12.055],[30.99,y+dy,12.055],.004,'cabin_bolster')
  for zz in [12.14,12.30,12.46,12.62,12.78]:
   rail('seat_quilt_seam',[30.365,y-.27,zz],[30.365,y+.27,zz],.0025,'cabin_bolster')
  for dy in [-.34,.34]:
   rail('seat_scissor_link',[30.30,y+dy,11.47],[31.0,y+dy,11.82],.035,steel)
   rail('seat_scissor_link',[30.30,y+dy,11.82],[31.0,y+dy,11.47],.035,steel)
   put('seat_pivot',cyl([30.65,y+dy-.03,11.65],[30.65,y+dy+.03,11.65],.063,12),steel,cat='seat')
  put('seat_adjustment_knob',cyl([30.6,y-.51,11.89],[30.6,y-.43,11.89],.07,16),'black',cat='seat')
  for dy in [-.48,.48]:
   put('pilot_armrest',rounded_box([[30.355,y+dy-.055,12.155],[31.005,y+dy+.055,12.245]],.034),'cabin_grip',cat='seat')
   rail('pilot_armrest_stay',[30.48,y+dy,11.77],[30.48,y+dy,12.19],.025,'cabin_metal')
   rail('pilot_armrest_bracket',[30.48,y+np.sign(dy)*.26,11.79],[30.48,y+dy,11.79],.025,'cabin_frame')
  rail('control_column',[31.50,y,11.40],[31.45,y,12.30],.075)
  rail('yoke_bar',[31.45,y-.25,12.30],[31.45,y+.25,12.30],.04,'black')
  for dy in [-.25,.25]:rail('yoke_grip',[31.45,y+dy,12.27],[31.45,y+dy,12.48],.035,'black')
  for dy in [-.19,.19]:bx('rudder_pedal',[31.80,y+dy,11.51],[.30,.24,.06],steel,cat='console')
 # Central pedestal has a reachable row of independent traction/brake levers.
 bx('center_pedestal',[31.95,0,11.91],[2.60,.76,1.12],panel,True,'console')
 panel_face('center_navigation',[32.65,0,12.50],.68,.56,16,axis=2)
 for y in np.linspace(-.24,.24,4):
  rail('power_lever',[31.7,y,12.48],[31.49,y,12.81],.018)
  bx('power_lever_grip',[31.49,y,12.81],[.13,.085,.075],'black',cat='console')
 # Overhead panel and its return support stop above the forward seats.
 bx('overhead_support',[32.70,0,14.10],[1.65,3.35,.16],steel,cat='ceiling')
 for y in [-.82,.82]:panel_face('overhead_switches',[32.40,y,14.005],1.52,1.52,14,axis=2)
 for y in [-1.58,1.58]:
  bx('overhead_drop',[33.18,y,14.36],[.12,.12,.57],steel,cat='ceiling')
 # Rear engineer/navigator side consoles; preserve a 1.6 m clear centre aisle.
 for side in [-1,1]:
  y=side*2.48
  bx('engineer_console',[27.80,y,11.78],[2.85,1.05,.86],panel,True,'console')
  panel_face('engineer_system_panel',[27.80,side*3.00,12.71],1.70,.85,13,axis=1)
  instrument_mounts(put,[27.80,side*3.00,12.71],0,1.70,.85,axis=1)
  for xx in [-.92,0,.92]:panel_face('engineer_switch_surface',[27.80+xx,y,12.245],.84,.84,14,axis=2)
  bx('engineer_seat_floor_plate',[27.80,side*1.62,11.385],[.48,.48,.07],'cabin_frame',True,'seat')
  put('engineer_seat_suspension',cyl([27.80,side*1.62,11.42],[27.80,side*1.62,11.73],.095,32),'cabin_frame',True,'seat')
  put('engineer_seat_rod',cyl([27.80,side*1.62,11.60],[27.80,side*1.62,11.82],.05,32),'cabin_metal',True,'seat')
  put('engineer_seat_bellows',revolved([27.80,side*1.62,11.48],[0,0,1],[(0,0),(.11,0),(.115,.02),(.102,.04),(.115,.06),(.102,.08),(.115,.1),(.102,.12),(.11,.14),(0,.14),(0,0)],32),'cabin_grip',cat='seat')
  for xx in [-.18,.18]:
   for yy in [-.18,.18]:put('seat_floor_anchor',cyl([27.80+xx,side*1.62+yy,11.413],[27.80+xx,side*1.62+yy,11.429],.019,6),'cabin_metal',cat='seat')
  put('engineer_seat',rounded_box([[27.47,side*1.62-.33,11.78],[28.13,side*1.62+.33,11.96]],.06),seat,True,'seat')
  put('engineer_seat_back',rounded_box([[27.445,side*1.27-.065,11.86],[28.155,side*1.27+.065,12.61]],.060),seat,True,'seat')
  put('engineer_seat_shell',rounded_box([[27.435,side*1.19-.042,11.85],[28.165,side*1.19+.042,12.59]],.040),'cabin_frame',cat='seat')
  for zz in [12.03,12.18,12.33,12.48]:rail('engineer_seat_seam',[27.55,side*1.344,zz],[28.05,side*1.344,zz],.0025,'cabin_bolster')
  for xx in [27.40,28.20]:
   rail('engineer_arm_support',[xx,side*1.38,11.74],[xx,side*1.38,12.06],.022,'cabin_metal')
   put('engineer_arm_pad',rounded_box([[xx-.045,side*1.62-.20,12.035],[xx+.045,side*1.62+.20,12.095]],.025),'cabin_grip',cat='seat')
  for dx in [-.25,.25]:rail('engineer_seat_frame',[27.8+dx,side*1.27,11.65],[27.8+dx,side*1.27,12.52],.023,steel)
  # Human-height worktop and drawers, placed between entry and engineer console.
  bx('workbench_top',[22.45,side*2.78,12.125],[3.15,.92,.05],role('8E8774'),True,'workbench')
  for x in [21.2,23.7]:bx('desk_pedestal',[x,side*2.78,11.72],[.55,.76,.74],panel,True,'workbench')
  panel_face('workstation_chart',[22.45,side*3.20,12.54],1.30,.66,15,axis=1)
  for x in [21.2,23.7]:
   for z in [11.60,11.84,12.05]:rail('drawer_pull',[x-.15,side*2.36,z],[x+.15,side*2.36,z],.016)
  # Sparse wall frame/ceiling service routes, continuous instead of cluttered boxes.
  for x in [20.25,24.05,26.25,29.60]:bx('cabin_frame_rib',[x,side*3.28,12.78],[.07,.10,2.85],steel,cat='wall')
  for yoff in [.05,.13]:rail('ceiling_service_run',[16.50,side*(2.95+yoff),14.45],[30.0,side*(2.95+yoff),14.45],.035,steel)
 # Two live labels sit on navigation screens behind the front controls.
 for side in [-1,1]:
  bx('telemetry_bezel',[30.02,side*2.66,12.91],[.09,.93,.43],'black',cat='console')
  bx('telemetry_wall_mount',[30.07,side*3.25,12.80],[.12,.12,.46],steel,cat='console')
  rail('telemetry_mount_arm',[30.06,side*3.20,12.73],[30.06,side*2.66,12.73],.035,steel)
  screens.append(dict(part='telemetry',center_source_m=[29.967,side*2.66,12.91],normal_source=[-1,0,0],purpose='actual driving telemetry',width=.85,height=.37))
 # Hollow lounge room, connected by one internal straight stair and enclosed landing.
 rest=next(p for p in a['parts'] if p['name'].endswith('_fore_service_shell'));rm=mesh(rest)
 # Existing exterior windows/doors remain in shell; remove its solid internal core.
 rm=tm.boolean.difference([rm,boxmesh([9,0,10.28],[9.58,15.58,5.42]),boxmesh([14.1,0,12.52],[.9,2.0,2.40]),boxmesh([12.2,0,13.55],[4.5,2.25,1.8])],engine='manifold');replace(rest,rm)
 # Pale inner lining is a separate occupied-room finish, with the real window cuts.
 for side in [-1,1]:
  skin=boxmesh([9,side*7.775,10.28],[9.50,.02,5.32])
  for x in [5.5,8.4,11.3]:skin=tm.boolean.difference([skin,boxmesh([x,side*7.775,11.78],[1.18,.4,.72])],engine='manifold')
  put('lounge_inner_lining',skin,lining,cat='wall')
 for x in [4.225,13.775]:
  skin=boxmesh([x,0,10.28],[.02,15.50,5.32])
  if x>10:skin=tm.boolean.difference([skin,boxmesh([x,0,12.52],[.4,2,2.40])],engine='manifold')
  put('lounge_end_lining',skin,lining,cat='wall')
 bx('lounge_floor',[9,0,7.47],[9.60,15.60,.16],'cabin_floor',True,'floor')
 # Stairs are enclosed within the central equipment-house volume, with landing to aft cabin door.
 for i in range(20):
  x=5.8+(i+.5)*.38;z=7.55+(i+1)*.19
  bx('internal_stair_tread',[x,0,z-.04],[.38,1.70,.08],'deck_steel',True,'floor');route.append([x,0,z])
  bx('internal_stair_riser',[x+.19,0,z-.135],[.025,1.70,.19],steel,True,'wall')
 for side in [-1,1]:
  tube('internal_stair_stringer',[5.70,side*.90,7.45],[13.45,side*.90,11.30],.13,.22,.012)
  rail('internal_stair_handrail',[5.70,side*.93,8.48],[13.55,side*.93,12.40],.032)
  for i in [0,5,10,15,19]:
   x=5.8+(i+.5)*.38;z=7.55+(i+1)*.19;rail('internal_stair_post',[x,side*.93,z],[x,side*.93,z+1.0],.025)
 bx('enclosed_connector_floor',[14.675,0,11.275],[2.75,2.20,.15],'cabin_floor',True,'floor')
 for side in [-1,1]:
  # Painted pressure/weather skin follows the active exterior livery.  A
  # separate inset lining carries the occupied-space finish on the inside.
  bx('enclosed_connector_wall',[15.20,side*1.18,12.57],[3.70,.16,2.60],ivory,True,'wall')
  bx('enclosed_connector_inner_lining',[15.17,side*1.085,12.57],[3.60,.02,2.50],'cabin_lining',cat='wall')
 bx('stairhouse_roof',[13.49,0,13.91],[7.12,2.52,.16],ivory,True,'ceiling')
 bx('stairhouse_ceiling_lining',[13.46,0,13.815],[6.94,2.14,.02],'cabin_lining',cat='ceiling')
 for side in [-1,1]:
  bx('stairhouse_coaming',[11.68,side*1.18,13.38],[3.35,.16,1.06],ivory,True,'wall')
  bx('stairhouse_coaming_inner_lining',[11.68,side*1.085,13.38],[3.23,.02,.96],'cabin_lining',cat='wall')
 bx('stairhouse_coaming_end',[9.96,0,13.38],[.12,2.52,1.06],ivory,True,'wall')
 bx('stairhouse_coaming_end_inner_lining',[10.03,0,13.38],[.02,2.34,.96],'cabin_lining',cat='wall')
 # Aft doorway stays an open passage; frame radii echo watertight ship bulkheads.
 for x in [14.15,17.08]:
  for side in [-1,1]:bx('passage_jamb',[x,side*1.06,12.53],[.16,.12,2.36],steel,True,'wall')
  bx('passage_header',[x,0,13.72],[.16,2.24,.12],steel,True,'wall')
  for side in [-1,1]:rail('passage_grab',[x+.10,side*1.10,12.25],[x+.10,side*1.10,12.95],.023)
 # Lounge zones face across side aisles; robot circulation remains below the stairs.
 for side in [-1,1]:
  y=side*5.8
  bx('lounge_bench_base',[8.0,y,7.82],[4.8,1.10,.54],panel,True,'seat')
  put('lounge_bench_cushion',rounded_box([[5.6,y-.54,8.08],[10.4,y+.54,8.24]],.06),'cabin_lounge',True,'seat')
  bx('lounge_bench_back',[8,side*6.37,8.43],[4.8,.15,.92],'cabin_lounge',True,'seat')
  bx('lounge_table',[8,side*4.28,8.325],[2.55,1.05,.05],role('8E8774'),True,'workbench')
  for x in [7.2,8.8]:bx('lounge_table_leg',[x,side*4.28,7.92],[.12,.50,.74],steel,True,'workbench')
  bx('lounge_storage',[12.85,side*5.5,8.75],[.95,3.15,2.4],panel,True,'wall')
  for yy in np.linspace(side*4.3,side*6.7,4):
   bx('lounge_locker_door',[12.35,yy,8.80],[.04,.66,2.12],panel,cat='wall')
   rail('locker_handle',[12.31,yy+.22,8.63],[12.31,yy+.22,8.95],.023)
  for x in [5.2,8.8,12.3]:bx('lounge_bulkhead_rib',[x,side*7.70,10.30],[.10,.12,5.30],steel,cat='wall')
  rail('lounge_conduit',[4.5,side*7.65,12.8],[13.4,side*7.65,12.8],.045,steel)
  bx('lounge_ceiling_light',[8.1,side*4.8,12.98],[4.5,.12,.05],'cabin_light',cat='ceiling')
 # CC0 rubberduck/a52 maintenance terminal: authored UV + baked normal, 152 tris.
 asset=O/'assets/third_party/rubberduck_industrial/control_terminal.obj'
 vendor=tm.load(asset,force='mesh',process=False);v=vendor.vertices.copy();uv=np.array(vendor.visual.uv)[vendor.faces].reshape(-1,2)
 # OBJ is Y-up, front +Z. Orient the service face +X into the lounge.
 vv=np.column_stack([v[:,2],v[:,0],v[:,1]]);vv*=2.25/(vv[:,2].max()-vv[:,2].min());vv-=np.array([vv[:,0].min(),(vv[:,1].max()+vv[:,1].min())/2,vv[:,2].min()]);vv+=[4.45,3.05,7.55]
 flat=vv[vendor.faces].reshape(-1,3);m=tm.Trimesh(flat,np.arange(len(flat)).reshape(-1,3),process=False)
 a['colors']['vendor_control_terminal']='AAAAAA';p=put('maintenance_terminal',m,'vendor_control_terminal',True,'console');p['native_uv']=uv.tolist()
 bx('terminal_rear_cover',[4.43,3.05,8.675],[.03,1.08,2.25],steel,cat='wall')
 for z in [7.9,9.5]:bx('terminal_wall_bracket',[4.32,3.05,z],[.23,.85,.08],steel,cat='wall')
 rail('terminal_power_feed',[4.48,3.05,9.55],[4.48,3.05,12.75],.033,steel)
 # Lower mechanical architecture is exposed in the protected space between trucks.
 for g in ['front','rear','tail']:
  cx=a['groups'][g][0]
  for side in [-1,1]:
   y=side*6.5
   for z in [4.45,5.72]:tube('underframe_longeron',[cx-15,y,z],[cx+15,y,z],.30,.32,.020,g)
   for x in range(-15,15,5):
    tube('underframe_diagonal',[cx+x,y,4.45],[cx+x+5,y,5.72],.18,.20,.014,g)
    bx('underframe_node_plate',[cx+x,y,5.66],[.58,.06,.48],steel,g=g)
   for x in [-15,-10.5,-5,5,10.5,15]:tube('underframe_deck_tie',[cx+x,y,5.72],[cx+x,y,6.62],.26,.28,.018,g)
   # Hydraulic accumulator/manifold grouping is connected to lateral truck branches.
   for x in [-10.5,10.5]:
    for dx in [-.60,.60]:
     put('suspension_accumulator',cyl([cx+x+dx,side*5.7,4.70],[cx+x+dx,side*5.7,5.40],.22,16),role('39484D'),g=g)
    bx('hydraulic_manifold',[cx+x,side*4.6,5.00],[1.9,.54,.40],steel,g=g)
    for dx in [-.60,.60]:
     put('accumulator_feed',cyl([cx+x+dx,side*4.85,5.12],[cx+x+dx,side*5.70,5.12],.047,10),'black',g=g)
    put('truck_hydraulic_supply',cyl([cx+x,side*4.6,5.12],[cx+x,side*9.35,5.12],.065,12),'black',g=g)
   # Protected cable trunk with bracketed separate coolant supply/return.
   bx('power_cable_tray',[cx,side*2.35,5.04],[29.5,.75,.14],steel,g=g)
   for yoff in [-.16,.16]:put('insulated_power_cable',cyl([cx-14.8,side*2.35+yoff,5.15],[cx+14.8,side*2.35+yoff,5.15],.075,10),'black',g=g)
   for yy in [3.20,3.60]:
    put('coolant_longitudinal',cyl([cx-14.6,side*yy,4.87],[cx+14.6,side*yy,4.87],.095,12),role('677B7A'),g=g)
    for x in [-12,-6,0,6,12]:put('coolant_flange',cyl([cx+x-.04,side*yy,4.87],[cx+x+.04,side*yy,4.87],.16,12),steel,g=g)
   for x in [-12,-6,0,6,12]:bx('services_saddle',[cx+x,side*3.0,4.69],[.14,2.5,.10],steel,g=g)
  for x in [-10.5,10.5]:tube('truck_load_crosshead',[cx+x,-10.8,5.96],[cx+x,10.8,5.96],.38,.56,.026,g)
  for x in [-15,-5,5,15]:tube('underframe_crossmember',[cx+x,-6.5,5.55],[cx+x,6.5,5.55],.28,.34,.018,g)
  # Removable centre inspection covers; side machinery stays visually accessible.
  for x in [-10,0,10]:
   bx('power_junction_enclosure',[cx+x,0,5.04],[3.1,2.6,.72],steel,g=g)
   for yy in [-1.14,1.14]:bx('inspection_cover_seam',[cx+x,yy,4.665],[2.85,.04,.025],'black',g=g)
   for dx in [-1.27,1.27]:
    for yy in [-1.05,1.05]:put('inspection_cover_fastener',cyl([cx+x+dx,yy,4.66],[cx+x+dx,yy,4.61],.055,6),'silver',g=g)
 a['mechanical_mass_additions'].extend(mass)
 a['habitable_revision']=dict(removed=removed,obsolete_door_groups=sorted(obsolete),contacts=contacts,screens=screens,stair_route=route,room_floor_z=roomfloor,cabin_floor_z=floor,stair_riser_m=.19,stair_tread_m=.38,stair_width_m=1.70,worktop_height_m=.80,scope='Human-scale connected architecture; robot stair-climbing policy not trained. Added frame mass from hollow steel geometry; other service equipment remains within provisional hull allowance.')
 (O/'source/habitable.json').write_text(json.dumps(a['habitable_revision'],indent=2))
