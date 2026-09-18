"""Authored crane and receiver bodies, plus actuator/cable display skins.
Geometry remains source-owned. Span skins follow actual endpoint bodies at runtime;
main mechanism masses and inertia are deaggregated from the existing hull ledger.
"""
import math,json
import numpy as np
import trimesh as tm

def center(p):
 v=np.array(p['vertices']);return (v.min(0)+v.max(0))/2

def author(a,add,rod,O):
 rig={'bodies':[],'joints':[],'cranes':[],'panel':{},'spans':[]}
 def body(name,pivot,hull,parent,axis=None,limits=None,kind='hinge'):
  a['groups'][name]=list(pivot);rig['bodies'].append({'name':name,'pivot':list(pivot),'hull':hull})
  if parent:rig['joints'].append({'name':name,'parent':parent,'body':name,'pivot':list(pivot),'axis':list(axis),'limits':limits,'kind':kind})
 def bind(p,g):p['group']=g;p['physical_body']=g
 def span(name,start,end,radius,color,group,end_a,end_b,mode='stretch',length=None):
  material='rig_'+name;a['colors'][material]=color
  rod('rig_'+name,start,end,radius,material,group)
  rig['spans'].append({'group':group,'material':material,'rest_start':list(np.array(start)-a['groups'][group]),'rest_end':list(np.array(end)-a['groups'][group]),'a':end_a,'b':end_b,'mode':mode,'length':length})
 def endpoint(g,world):return {'body':g,'local':list(np.array(world)-a['groups'][g])}
 for hull in ['rear','tail']:
  for index in range(4):
   upper=[p for p in a['parts'] if p['group']==hull and p.get('assembly')==f'crane_{index}_upper']
   pin=center(next(p for p in upper if p['name'].endswith('_crane_main_pin')))
   hook=center(next(p for p in upper if p['name'].endswith('_hook_swivel')))+[0,0,.47]
   d=hook-pin;d[2]=0;d/=np.linalg.norm(d);v=np.array([d[1],-d[0],0.]);prefix=f'{hull}_crane{index}'
   yaw=prefix+'_slew';luff=prefix+'_luff';ext=prefix+'_extend';hang=prefix+'_hook'
   base=pin+[0,0,-1.68]
   body(yaw,base,hull,hull,[0,0,1],[-math.radians(170),math.radians(170)]);body(luff,pin,hull,yaw,v,[0.,math.radians(35)])
   stage1=prefix+'_stage1';stage2=prefix+'_stage2'
   body(stage1,pin,hull,luff,d,[0.,4.30],'slide');body(stage2,pin,hull,stage1,d,[0.,4.00],'slide');body(ext,pin,hull,stage2,d,[0.,3.80],'slide')
   old_hook=hook.copy();old_tip=float(np.dot(hook-pin,d));tip_u=7.08
   hook=pin+d*tip_u+[0,0,.34-1.3-.32]
   shift_hook=hook-old_hook;shift_tip=d*(tip_u-old_tip)
   body(hang,hook,hull,None)
   def cp(u,w,z):return pin+d*u+v*w+np.array([0,0,z-pin[2]])
   cylinder_a=cp(1.,0,14.85);cylinder_b=cp(3.4,0,17.08)
   to_remove=[]
   for p in upper:
    n=p['name'].split('_',1)[-1];c=center(p);u=np.dot(c-pin,d)
    if n in ['winch_rope','crane_cylinder_barrel','crane_cylinder_rod','crane_hydraulic_pin','crane_root_cheek','crane_root_top','crane_root_bottom','crane_boom','crane_inner_top','crane_inner_bottom','crane_slide_pad']:
     to_remove.append(p);continue
    if n=='crane_cylinder_upper_ear':
     p['vertices']=(np.array(p['vertices'])-.65*d).tolist();g=luff
    elif n.startswith('hook') or n=='hook':
     p['vertices']=(np.array(p['vertices'])+shift_hook).tolist();g=hang
    elif n=='crane_tip_cheek':
     p['vertices']=(np.array(p['vertices'])+shift_tip).tolist();g=ext
    elif n in ['crane_rope_sheave','crane_sheave_flange'] and u>6.:
     p['vertices']=(np.array(p['vertices'])+shift_tip).tolist();g=ext
    elif n=='crane_slide_pad':g=ext if u>6 else luff
    elif n in ['crane_turning_head','crane_pivot_fork','crane_main_pin','crane_main_pin_cap','crane_cylinder_base_ear']:g=yaw
    else:g=luff
    bind(p,g)
   a['parts']=[p for p in a['parts'] if p not in to_remove]
   from telescopic_boom import author as author_boom
   yellow=next(p['material'] for p in upper if p['name'].endswith('_crane_turning_head'))
   sections=author_boom(pin,d,v,[luff,stage1,stage2,ext],add,rod,yellow)
   # Hydraulic skins are defined once, then only oriented/translated to real
   # eye positions. Their allocated mass remains on the luff body.
   vector=cylinder_b-cylinder_a;L=np.linalg.norm(vector);direction=vector/L
   for part,start,end,radius,col,mode,length in [
     ('barrel',cylinder_a,cylinder_a+direction*(L*.67),.23,'454E50','from_a',L*.67),
     ('rod',cylinder_b-direction*2.65,cylinder_b,.115,'899292','to_b',2.65)]:
    span(prefix+'_'+part,start,end,radius,col,luff,endpoint(yaw,cylinder_a),endpoint(luff,cylinder_b),mode,length)
   for point,g in [(cylinder_a,yaw),(cylinder_b,luff)]:rod('actuator_eye_pin',point-v*.64,point+v*.64,.24,'steel',g)
   # Ropes track their actual anchors; ideal massless cable dynamics are explicit
   # in the native/MJCF controller, not a prescribed hook animation.
   tip_u=float(np.dot(hook-pin,d));anchor=cp(tip_u,0,17.72)
   for side in [-1,1]:
    w=side*.21;root=cp(3.65,w,18.53);winch=cp(-.55,w,19.205);tip=cp(tip_u,w,17.91);top=cp(tip_u,w,17.72);bottom=hook+v*w+[0,0,.32]
    rod('crane_root_rope',winch,root,.026,'steel',luff)
    span(prefix+f'_feed{side}',root,tip,.026,'899292',ext,endpoint(luff,root),endpoint(ext,tip))
    span(prefix+f'_fall{side}',top,bottom,.026,'899292',ext,endpoint(ext,top),endpoint(hang,bottom))
   rig['cranes'].append({'name':prefix,'hull':hull,'slew':yaw,'luff':luff,'extend':ext,'stages':[stage1,stage2,ext],'stage_strokes_m':[4.30,4.00,3.80],'sections':sections,'extension_range_m':[0.,12.10],'hook':hang,'direction':d.tolist(),'luff_axis':v.tolist(),'cylinder_a':endpoint(yaw,cylinder_a),'cylinder_b':endpoint(luff,cylinder_b),'tip':endpoint(ext,anchor),'hook_attach':endpoint(hang,hook+[0,0,.32]),'paid_length_m':float(np.linalg.norm(anchor-hook-[0,0,.32])),'rope_stiffness_N_m':300000.,'rope_damping_N_s_m':20000.,'rope_force_cap_N':500000.,'cylinder_force_cap_N':2000000.})
 # Receiver yaw and upper bearing fold. Lower support/cylinder geometry stays
 # on the yaw cradle; only the actual shell and shaft rotate at the upper hinge.
 pivot=np.array([-1.,0.,15.75]);hinge=np.array([3.6,0.,20.55]);yaw='receiver_slew';fold='receiver_fold'
 body(yaw,pivot,'front','front',[0,0,1],[-math.pi/3,math.pi/3]);body(fold,hinge,'front',yaw,[0,1,0],[-1.20,.10])
 shell_names={'panel_outer','panel_face','panel_face_pattern','panel_rear_cell','panel_rear_cover','panel_back_spine','panel_side_service_cover','panel_shell_lug','panel_upper_shaft'}
 for p in a['parts']:
  if p['group']!='front':continue
  n=p['name'].split('_',1)[-1]
  if not n.startswith('panel_') or n in ['panel_turntable_bolt']:continue
  if n in shell_names:bind(p,fold)
  elif n in ['panel_bearing_housing','panel_bearing_ring','panel_pivot_cap'] and center(p)[2]>20.:bind(p,fold)
  elif n.startswith(('panel_base','panel_fixed_fork','panel_arm','panel_bearing','panel_pivot','panel_cylinder','panel_lower_shaft','panel_fold_case','panel_turntable')):bind(p,yaw)
 rig['panel']={'slew':yaw,'fold':fold}
 # Explicit source-volume provisional masses. They replace the corresponding
 # frozen hull allocation; total carrier mass is conserved during deaggregation.
 for item in rig['bodies']:
  ms=[];centers=[];tensors=[]
  for p in a['parts']:
   if p['group']!=item['name']:continue
   m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
   if not m.is_volume:continue
   density=2700. if item['name']=='receiver_fold' else 7850.
   volume=abs(m.volume)
   # Thin-wall envelope estimate: large visual housings are not solid metal.
   # Small pins/rods remain solid when their volume is below area * wall.
   wall=.020 if item["name"]=="receiver_fold" else .030
   fraction=min(1.,float(m.area)*wall/max(volume,1e-12))
   mass=volume*density*fraction
   if mass<=1e-7:continue
   ms.append(mass);centers.append(m.center_mass);tensors.append(m.moment_inertia*density*fraction)
  assert ms,item['name']
  M=sum(ms);com=np.average(centers,axis=0,weights=ms);I=np.zeros((3,3))
  for mass,c,tensor in zip(ms,centers,tensors):
   d=c-com;I+=tensor+mass*(np.eye(3)*np.dot(d,d)-np.outer(d,d))
  item.update(mass=M,com=(com-item['pivot']).tolist(),inertia=np.maximum(np.diag(I),1.).tolist())
 rig['scope']='Finite-force named rigid-body mechanisms. Hydraulic/rope skins follow actual physical endpoints; cylinder skin mass lumped on luff. Provisional 30 mm steel / 20 mm aluminium thin-wall envelope masses deaggregated from provisional hull allocation. No manufacturer ratings.'
 a['equipment_actuation']=rig;(O/'source/equipment.json').write_text(json.dumps(rig,indent=2))
