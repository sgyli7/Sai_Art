"""Front service/working/receiver hierarchy derived from the user's C-700 view."""
import numpy as np
import trimesh as tm

def refine(a,box,rod,add,role,extrude_xz):
 keep=[]
 remove={'main_access_leaf','main_access_gasket','main_panel_fastener','main_panel_stiffener','panel_rooftop_chord','panel_rooftop_web','aft_port_x_brace'}
 for p in a['parts']:
  n=p['name'].split('_',1)[-1]
  if p['group']=='front' and n in remove:continue
  if p['group']=='front':
   v=np.array(p['vertices'])
   if n=='middle_service_shell':
    # Port roof is lower; starboard retains the reference's equipment wall.
    mesh=tm.Trimesh(vertices=v,faces=p['faces'],process=False)
    cut=tm.creation.box([13.,8.,4.]);cut.apply_translation([-1.7,7.4,14.1])
    mesh=tm.boolean.difference([mesh,cut],engine='manifold')
    v=mesh.vertices.copy();p['faces']=mesh.faces.tolist()
   if n in ['rooftop_receiver','receiver_seat','receiver_strap','vent_roof','vent_fan_hub','vent_fan','fan_grille'] and v[:,1].mean()>0:continue
   if n in ['aft_port_x_brace','aft_module_frame','aft_roof_handle','aft_end_panel','fore_vent_frame','fore_vent_louvre']:p['material']=role('596466')
   p['vertices']=v.tolist()
  keep.append(p)
 a['parts']=keep
 steel=role('596466');black=role('202124');trim=role('485658');glass=role('455B61');red=role('A51B2B')
 # Middle is a low work/service bay with two personnel access leaves, not a
 # wall of garage shutters. End room / fore mechanical house remains taller.
 for side in [-1,1]:
  y=side*10.57
  for x in ([-5.5,.6] if side>0 else []):
   box('workbay_access_leaf',(x,y,9.65),(1.30,.09,2.50),black,'front')
   for z in [8.39,10.91]:box('workbay_door_trim',(x,y+side*.055,z),(1.42,.045,.04),steel,'front')
   for dx in [-.69,.69]:box('workbay_door_jamb',(x+dx,y+side*.055,9.65),(.04,.045,2.54),steel,'front')
   box('workbay_door_handle',(x+.43,y+side*.10,9.65),(.045,.05,.30),red,'front')
  for x in ([-7.25,-3.0,3.8] if side>0 else []):box('workbay_panel_joint',(x,y,10.0 if side>0 else 11.0),(.045,.025,3.8 if side>0 else 5.8),trim,'front')
  # Low roof walkway is separate from equipment and raised gallery.
  roof=12.14 if side>0 else 14.14
  for x in [-7.2,-4.5,-1.8,.9,3.6]:rod('workbay_roof_guard',[x,side*10.3,roof],[x,side*10.3,roof+1.04],.032,'edge','front')
  for z in [roof+.51,roof+1.04]:rod('workbay_roof_guard',[-7.2,side*10.3,z],[3.6,side*10.3,z],.032,'edge','front')
  # Close the end of each roof service walkway; posts land on its own deck.
  for x in [-7.2,3.6]:
   for z in [roof+.51,roof+1.04]:rod('roof_guard_return',[x,side*10.3,z],[x,side*6.65,z],.032,'edge','front')
   rod('roof_guard_return_post',[x,side*6.65,roof],[x,side*6.65,roof+1.04],.032,'edge','front')
  # Raised instrument gallery: tapered dark panes, structural mullions,
  # bottom sill and open piers visibly spanning the low workbay.
  for x in np.linspace(-7.7,4.7,9):
   verts=[]
   for depth in [0.,.07]:
    verts.extend([[x-.48,side*(6.13-depth),14.37],[x+.48,side*(6.13-depth),14.37],[x+.67,side*(6.39-depth),15.26],[x-.67,side*(6.39-depth),15.26]])
   pane=tm.Trimesh(vertices=verts,faces=[[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],[1,5,6],[1,6,2],[2,6,7],[2,7,3],[3,7,4],[3,4,0]],process=False)
   add('instrument_ribbon_panel',pane,glass,'front')
   rod('instrument_mullion',[x-.49,side*6.14,14.31],[x-.69,side*6.43,15.34],.038,steel,'front')
  for z in [14.28,15.32]:box('instrument_ribbon_sill',(-1.5,side*6.43,z),(14.0,.14,.13),steel,'front')
  for x in [-7.5,3.9]:box('instrument_pier',(x,side*5.9,13.22),(.24,.24,2.20),steel,'front')
  # Paired bent ventilation ducts connect raised instrument plenum to lower
  # service roof. Continuous outline and transverse branch, not isolated pods.
  if side>0:
   shape=[(-7.6,12.15),(-7.6,13.85),(-6.9,14.40),(-5.9,14.40),(-5.9,13.80),(-6.6,13.30),(-6.6,12.72),(1.8,12.72),(2.6,12.15)]
   add('bent_service_duct',extrude_xz(shape,side*8.5,1.1),steel,'front')
   box('instrument_duct_branch',(-6.65,side*7.2,14.09),(1.5,2.0,.57),steel,'front')
   for x in [-5.8,-2.6,.6]:box('duct_service_seam',(x,side*8.5,12.76),(.055,1.16,.06),trim,'front')
  # Original aft connecting bays have large diagonal braces on both sides.
  for x in [-14.85,-11.90,-8.95]:
   rod('aft_connection_diagonal',[x-1.30,side*11.50,7.86],[x+1.30,side*11.50,11.18],.055,steel,'front')
   rod('aft_connection_diagonal',[x+1.30,side*11.52,7.86],[x-1.30,side*11.52,11.18],.055,steel,'front')
 box('instrument_gallery_floor',(-1.5,0,14.20),(14.0,12.8,.15),black,'front')
