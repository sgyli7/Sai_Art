"""Near-field cockpit primitives, metres. Smooth visible geometry; separate contact proxies."""
import math
import numpy as np
import trimesh as tm

def ring(center,axis,radius,tube,major=96,minor=12):
 m=tm.creation.torus(major_radius=radius,minor_radius=tube,major_sections=major,minor_sections=minor)
 m.apply_transform(tm.geometry.align_vectors([0,0,1],axis));m.apply_translation(center);return m

def revolved(center,axis,profile,sections=48):
 # Closed radial/axial profile; cylindrical collars, bellows and dished hubs.
 m=tm.creation.revolve(np.array(profile,float),sections=sections)
 m.apply_transform(tm.geometry.align_vectors([0,0,1],axis));m.apply_translation(center);return m

def instrument_mounts(put,center,angle,width,height,axis=0):
 from mechanical_revision import cyl,boxmesh
 c=np.array(center);rot=tm.transformations.rotation_matrix(angle,[0,1,0])[:3,:3]
 # Front face outward -X; station panels outward toward aisle on +/-Y.
 if axis==0:u=rot@np.array([0,1,0]);v=rot@np.array([0,0,1]);n=rot@np.array([-1,0,0])
 else:u=np.array([1,0,0]);v=np.array([0,0,1]);n=np.array([0,-np.sign(c[1]),0])
 def local(x,y,d=0):return c+u*x+v*y+n*d
 # 2x4 actual instruments: matching live texture pixel locations exactly.
 for i in range(8):
  x=(-.375+(i%4)*.25)*width;y=(.20 if i<4 else -.22)*height
  radius=width*.070
  point=local(x,y,.025)
  put('instrument_bezel',revolved(point,n,[(radius-.010,0),(radius+.012,0),(radius+.015,.005),(radius+.015,.020),(radius+.008,.028),(radius-.010,.028),(radius-.010,0)],96),'cabin_frame',cat='console')
  put('instrument_retainer',ring(point+n*.025,n,radius+.010,.003,96,8),'cabin_metal',cat='console')
  for sx in [-1,1]:
   for sy in [-1,1]:
    b=local(x+sx*(radius+.027),y+sy*(radius+.024),.021)
    put('instrument_fastener',cyl(b,b+n*.006,.006,12),'cabin_metal',cat='console')
    # Dark slot is inset into the cap; tiny geometry reserved for first-person view.
    slot=boxmesh([0,0,0],[.008,.0015,.001]);T=np.eye(4);T[:3,:3]=np.column_stack([u,v,n]);T[:3,3]=b+n*.006;slot.apply_transform(T);put('fastener_slot',slot,'black',cat='console')
 # Panel perimeter fasteners; restrained structural rhythm, not random greebles.
 for x in [-width*.47,0,width*.47]:
  for y in [-height*.47,height*.47]:
   b=local(x,y,.02);put('panel_captive_screw',cyl(b,b+n*.007,.009,16),'cabin_metal',cat='console')
