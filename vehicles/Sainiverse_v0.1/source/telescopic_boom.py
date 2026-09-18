"""Four nested chamfered box sections with explicit bearing engagement.
Eight-wall solid annular extrusions, not overlapping solid cubes. Dimensions are
an authored packaging proposal; finite actuation is separate from structural rating.
"""
import numpy as np
import trimesh as tm

def section_ring(width,height,bevel):
 w,h=width/2,height/2;b=bevel
 return np.array([[-w+b,-h],[w-b,-h],[w,-h+b],[w,h-b],[w-b,h],[-w+b,h],[-w,h-b],[-w,-h+b]])
def tube(pin,d,v,start,end,width,height,wall):
 outer=section_ring(width,height,.10);inner=section_ring(width-2*wall,height-2*wall,max(.03,.10-wall/2));vertices=[]
 for u in [start,end]:
  for ring in [outer,inner]:
   for w,z in ring:vertices.append(pin+d*u+v*w+[0,0,.34+z])
 faces=[]
 for k in range(8):
  n=(k+1)%8
  for q in [(k,n,16+n,16+k),(8+n,8+k,24+k,24+n),(n,k,8+k,8+n),(16+k,16+n,24+n,24+k)]:
   faces.extend([(q[0],q[1],q[2]),(q[0],q[2],q[3])])
 mesh=tm.Trimesh(vertices=vertices,faces=faces,process=True);mesh.fix_normals();assert mesh.is_volume
 return mesh

def author(pin,d,v,names,add,rod,color):
 # Each stage is expressed relative to its parent. Full-stroke bearing overlap
 # is calculated on that relative frame; serial translations add at the tip.
 sections=[dict(name=names[0],u=[-.95,6.30],width=1.34,height=1.52,wall=.065,stroke=0.),dict(name=names[1],u=[0.,6.50],width=1.12,height=1.26,wall=.052,stroke=4.30),dict(name=names[2],u=[.22,6.70],width=.91,height=1.02,wall=.046,stroke=4.00),dict(name=names[3],u=[.44,6.90],width=.71,height=.79,wall=.041,stroke=3.80)]
 for i,s in enumerate(sections):
  add('telescopic_box_section',tube(pin,d,v,*s['u'],s['width'],s['height'],s['wall']),color,s['name'],'crane')
  # Front gland ring, dark wear pads and small fasteners belong to this section.
  end=s['u'][1]
  add('telescopic_gland',tube(pin,d,v,end-.13,end+.03,s['width']+.075,s['height']+.075,.035),'steel',s['name'],'crane')
  for sign in [-1,1]:
   p=pin+d*(end-.21)+v*sign*(s['width']/2+.023)+[0,0,.34]
   rod('telescopic_gland_pin',p-v*.035,p+v*.035,.045,'steel',s['name'])
  if i:
   s['minimum_overlap_m']=sections[i-1]['u'][1]-(s['u'][0]+s['stroke'])
   assert s['minimum_overlap_m']>=2.
 return sections
