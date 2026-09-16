"""Named, physically articulated operator controls and robot affordances (source metres)."""
import math,json
import numpy as np
import trimesh as tm
from mechanical_revision import mesh,boxmesh,cyl
from cockpit_geometry import ring,revolved
from refinement import rounded_box

def author(a,add,O):
 controls=[];labels=[]
 def put(n,m,mat='cabin_console',g='front'):
  add('r032_'+n,m,mat,g);a['parts'][-1]['interior_category']='console'
 def bx(n,c,s,mat='cabin_console',g='front'):put(n,boxmesh(c,s),mat,g)
 # Four decorative throttle sticks/yokes/pedals become identifiable working controls.
 a['parts']=[p for p in a['parts'] if not any(p['name'].endswith('_'+n) for n in ['power_lever','power_lever_grip','yoke_bar','yoke_grip','control_column','rudder_pedal'])]
 def control(id,kind,pivot,axis,limits,label,action,station='pilot',detents=0):
  name='cockpit_'+id;p=np.array(pivot,float);a['groups'][name]=pivot
  if kind=='button':
   put(id+'_bezel',rounded_box([p+[-.06,-.06,-.05],p+[.06,.06,-.005]],.009),'cabin_frame');put(id+'_cap',rounded_box([p+[-.0425,-.0425,.002],p+[.0425,.0425,.030]],.008),'cabin_trim' if id=='emergency' else 'cabin_metal',name)
   kind='slide';mass=.16;inertia=[.0002]*3;com=[0,0,.016];grasp=[0,0,.033];cap=6.;kp=500.;kd=12.;rate=.10
  elif kind=='selector':
   put(id+'_bezel',cyl(p-[0,0,.025],p+[0,0,.006],.07,24),'edge')
   put(id+'_knob',cyl(p,p+[0,0,.063],.046,32),'cabin_grip',name);bx(id+'_index',p+[.026,0,.066],[.041,.009,.009],'insignia',name)
   kind='hinge';mass=.35;inertia=[.004]*3;com=[0,0,.025];grasp=[.036,0,.033];cap=1.2;kp=5.;kd=.30;rate=2.
  elif kind=='wheel':
   put(id+'_column',cyl(p-[.30,0,0],p,.062,16),'steel')
   put(id+'_floor_post',cyl([p[0]-.30,p[1],11.36],p-[.30,0,0],.055,16),'steel')
   bx(id+'_floor_flange',[p[0]-.30,p[1],11.39],[.24,.26,.07],'steel')
   put(id+'_rim',ring(p,[1,0,0],.235,.024,96,16),'cabin_grip',name)
   for t in [0,math.pi*2/3,math.pi*4/3]:
    # Tapered, dished spokes join the hub and inner rim without capped overlaps.
    e=np.array([0,math.cos(t),math.sin(t)]);cross=np.cross([1,0,0],e)
    verts=[]
    for x,r,w in [(-.025,.060,.033),(0,.218,.018)]:
     for xx,sgn in [(-.006,-1),(-.006,1),(.006,-1),(.006,1)]:verts.append(p+[x+xx,0,0]+e*r+cross*w*sgn)
    put(id+'_spoke',tm.convex.convex_hull(verts),'cabin_metal',name)
   put(id+'_hub',revolved(p,[-1,0,0],[(0,-.025),(.065,-.025),(.076,-.010),(.076,.025),(.065,.040),(0,.043),(0,-.025)],64),'cabin_frame',name)
   put(id+'_hub_inlay',cyl(p-[.043,0,0],p-[.046,0,0],.046,48),'cabin_trim',name)
   kind='hinge';mass=1.2;inertia=[.07,.04,.04];com=[0,0,0];grasp=[0,-.235,0];cap=3.;kp=10.;kd=1.7;rate=1.7
  else:
   put(id+'_gate',rounded_box([p+[-.11,-.105,-.044],p+[.11,.105,.004]],.018),'cabin_frame')
   # Boot seals the moving shaft; bellows follows its body instead of floating over it.
   profile=[(0,0),(.052,0),(.055,.010),(.046,.021),(.050,.030),(.039,.041),(.043,.050),(.029,.067),(.020,.078),(0,.078),(0,0)]
   put(id+'_boot',revolved(p,[0,0,1],profile,40),'cabin_grip',name)
   put(id+'_shaft',cyl(p+[0,0,.055],p+[0,0,.21],.014,24),'cabin_metal',name)
   put(id+'_grip',rounded_box([p+[-.06,-.028,.182],p+[.06,.028,.24]],.020),'cabin_grip',name)
   for zz in [.199,.215,.23]:
    put(id+'_grip_seam',cyl(p+[-.038,-.0282,zz],p+[.038,-.0282,zz],.0015,6),'cabin_frame',name)
   kind='hinge';mass=.45;inertia=[.012]*3;com=[0,0,.105];grasp=[0,0,.21];cap=1.8;kp=6.;kd=.58;rate=2.
  owned=[p for p in a['parts'] if p['group']==name];points=np.concatenate([p['vertices'] for p in owned])-np.array(pivot)
  # Convex contact per actual component, so a wheel retains its hand opening.
  contacts=[(mesh(part).convex_hull.vertices-np.array(pivot)).tolist() for part in owned if not part['name'].endswith('_rim')]
  if id=='steer':
   # Smooth visual torus uses 16 convex contact arcs, preserving the hand opening.
   for t in np.linspace(0,2*math.pi,17)[:-1]:
    pts=[p+np.array([0,.235*math.cos(tt),.235*math.sin(tt)]) for tt in [t,t+math.pi/8]]
    contacts.append((cyl(pts[0],pts[1],.024,10).vertices-p).tolist())
  item=dict(id=id,name=name,parent='front',kind=kind,pivot_source_m=pivot,axis_source=axis,limits=limits,label=label,action=action,station=station,detents=detents,mass_kg=mass,com_local_m=com,inertia_diagonal_kg_m2=inertia,effort_cap=cap,kp=kp,kd=kd,rate=rate,contacts_local=contacts,grasp_local_m=grasp,approach_normal_source=[0,0,1] if id!='steer' else [-1,0,0],robot_contact_layer=128,return_mode='detent' if detents else 'spring_center',press_threshold_m=.007 if kind=='slide' else None)
  controls.append(item)
  labels.append(dict(id=id,text=label,position_source_m=(p+[-.11,0,.008]).tolist(),station=station))
 control('steer','wheel',[31.48,-1.58,12.34],[1,0,0],[-.65,.65],'STEER','signed curvature [-0.012,+0.012] 1/m')
 control('throttle','lever',[31.20,-.21,12.48],[0,1,0],[-.50,.50],'REVERSE / SPEED','signed speed request; forward 12 or 27.777778 m/s, reverse 5 m/s')
 control('brake','lever',[31.20,.21,12.48],[0,1,0],[0,.50],'BRAKE','proportional reduction of speed request to zero')
 control('high_range','selector',[31.84,-.20,12.49],[0,0,1],[0,.65],'LOW / HIGH','select 12 or 27.777778 m/s forward range',detents=2)
 control('emergency','button',[31.84,.20,12.49],[0,0,-1],[0,.012],'PARK / STOP','latched zero-speed request; press again to release')
 for i,(id,label) in enumerate([('crane_slew','SLEW'),('crane_luff','BOOM'),('crane_extend','TELESCOPE'),('crane_winch','WINCH')]):
  control(id,'lever',[26.77+i*.66,2.46,12.29],[0,1,0],[-.30,.30],label,'selected crane '+id.removeprefix('crane_')+' rate','crane')
 control('crane_select','selector',[26.68,2.04,12.28],[0,0,1],[0,2.45],'CRANE 1-8','select one of eight cranes','crane',8)
 control('work','button',[27.25,2.04,12.28],[0,0,-1],[0,.012],'WORK / STOW','toggle working state; stationary interlock','crane')
 for i,(id,label) in enumerate([('panel_slew','ANTENNA YAW'),('panel_fold','ANTENNA FOLD')]):control(id,'lever',[27.15+i*1.22,-2.56,12.29],[0,1,0],[-.30,.30],label,id+' rate','services')
 control('lift_select','selector',[26.7,-2.04,12.28],[0,0,1],[0,2.50],'LIFT 1-6','select one of six lifts','services',6)
 for i,(id,label,action) in enumerate([('lift','LIFT UP/DOWN','toggle selected lift'),('lifts_all','ALL LIFTS','toggle all lifts'),('doors','CABIN DOORS','toggle both cabin entry doors')]):control(id,'button',[27.3+i*.57,-2.04,12.28],[0,0,-1],[0,.012],label,action,'services')
 a['cockpit_controls']=dict(version=1,controls=controls,labels=labels,coordinate_system='+X forward, +Y left, +Z up; metres/radians',scope='Finite-effort physical controls mapped to current vehicle functions. Robot reach and contact affordances supplied; no trained Sai manipulation policy.')
 (O/'source/cockpit_controls.json').write_text(json.dumps(a['cockpit_controls'],indent=2))

def compile(a,s,b,params,root,O):
 import xml.etree.ElementTree as E
 fmt=lambda x:' '.join(str(float(v)) for v in x)
 data=a['cockpit_controls'];front=next(x for x in s['bodies'] if x['name']=='front');datum=np.array(b['groups']['front']['neutral_body_position_source_m']);node=root.find('.//body[@name="front"]');asset=root.find('asset')
 for c in data['controls']:
  p=np.array(c['pivot_source_m']);name=c['name'];mass=c['mass_kg'];pos=p+np.array(front['position'])-datum
  s['bodies'].append(dict(name=name,mass=mass,com=c['com_local_m'],inertia=c['inertia_diagonal_kg_m2'],position=pos.tolist()))
  s['joints'].append(dict(name=name,body=name,parent='front',anchor=pos.tolist(),axis=c['axis_source'],kind=c['kind'],limits=c['limits'],stiffness=0,damping=0,springref=0,cockpit=True))
  b['groups'][name]=dict(pivot_source_m=p.tolist(),neutral_body_position_source_m=p.tolist())
  rb=E.SubElement(node,'body',name=name,pos=fmt(p-datum));E.SubElement(rb,'inertial',mass=str(mass),pos=fmt(c['com_local_m']),diaginertia=fmt(c['inertia_diagonal_kg_m2']))
  E.SubElement(rb,'joint',name=name,type=c['kind'],axis=fmt(c['axis_source']),range=fmt(c['limits']),limited='true',damping='0',armature='0')
  E.SubElement(root.find('actuator'),'motor',name=name,joint=name,ctrllimited='true',ctrlrange=fmt([-c['effort_cap'],c['effort_cap']]))
  for i,v in enumerate(c['contacts_local']):
   n=name+f'_contact_{i}';E.SubElement(asset,'mesh',name=n,vertex=fmt(np.array(v).ravel()));E.SubElement(rb,'geom',name=n,type='mesh',mesh=n,mass='0',contype='128',conaffinity='16',friction='.8 .005 .0001')
 s['contact']['cockpit']=data;params['cockpit']=data
