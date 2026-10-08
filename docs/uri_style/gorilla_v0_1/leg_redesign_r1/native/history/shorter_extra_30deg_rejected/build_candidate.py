"""Finite, source-bound geometry probe. NOT a hardware or gait qualification.

Engineering coordinates: forward X, left Y, up Z, metres. Leg and shoe are
new candidates. An earlier interpretation that froze the old shoe was wrong.
"""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import trimesh as tr
import manifold3d as mf
from shapely.geometry import Point

OUT = Path(__file__).resolve().parent
BASE = Path('/home/ethan/Projects/Sai_Rotbots/experiments/gorilla_v0_1/appearance_c_round_fifteen/appearance_c_scene.json')
BASE_SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()
# LENGTHS are solved for a folded reference stance, never by first stacking
# short links vertically. Angles measured from downward vertical, + forward.
# These are candidate dimensions, NOT an alteration of the active SI contract.
LENGTHS = [.68,.68,.50]
PITCHES = [45.,-70.,40.]
# User explicitly releases the old 2.65m height lock. Solve HIP from a low
# ankle seat and folded link angles, rather than elongating links to hit 2.65m.
ANKLE=np.array([.058,.5,.178])
DELTAS=[np.array([L*math.sin(math.radians(a)),0,-L*math.cos(math.radians(a))]) for L,a in zip(LENGTHS,PITCHES)]
P={'hip':(ANKLE-sum(DELTAS)).tolist()}
cursor=np.array(P['hip'])
for name,L,angle in zip(('knee','fold','ankle'),LENGTHS,PITCHES):
    theta=math.radians(angle)
    cursor=cursor+np.array([L*math.sin(theta),0,-L*math.cos(theta)])
    P[name]=cursor.tolist()
PAIRS = [('hip','knee'),('knee','fold'),('fold','ankle')]
BODIES = ['thigh','middle','distal']
COLORS = [[.26,.30,.33,1],[.26,.30,.33,1],[.26,.30,.33,1]]

def cylinder(c,r,L,inner=0):
    s=mf.Manifold.cylinder(L,r,r,64,True)
    if inner:s=s-mf.Manifold.cylinder(L+.002,inner,inner,64,True)
    return s.rotate([90,0,0]).translate(c)

def box(c,d):
    return mf.Manifold.cube(d,True).translate(c)

def extrude(poly,y,t):
    from shapely.geometry.polygon import orient
    poly=orient(poly,sign=1.0)
    contours=[list(poly.exterior.coords)[:-1]]+[list(q.coords)[:-1] for q in poly.interiors]
    # polygon X,Z -> manifold X,Y; extrusion -> engineering Y, preserving
    # orientation by mapping (x,z,e) to (x,-e,z).
    return mf.CrossSection(contours).extrude(t).transform(np.array([
        [1.,0,0,0],[0,0,-1,y+t/2],[0,1,0,0]]))

def beam(a,b,w,d,wall):
    a,b=np.array(a),np.array(b);u=(b-a)/np.linalg.norm(b-a)
    v=np.array([1.,0.,0.]) if abs(u[1])>.95 else np.array([0.,1.,0.])
    v-=u*(v@u);v/=np.linalg.norm(v)
    n=np.cross(v,u);L=np.linalg.norm(b-a)
    s=mf.Manifold.cube([w,d,L],True)
    if wall:s=s-mf.Manifold.cube([w-2*wall,d-2*wall,L+.002],True)
    T=np.column_stack((v,n,u,(a+b)/2))
    return s.transform(T.copy())

def union(shapes):
    r=mf.Manifold()
    for s in shapes:r=r+s
    return r

parts=[]
def add(name,body,s,role='structure',color=None,density=7850,**kw):
    if s.status()!=mf.Error.NoError or s.volume()<=0:
        raise ValueError((name,s.status(),s.volume()))
    mesh=s.to_mesh64()
    p={'name':name,'body':body,'role':role,'vertices_world_m':np.asarray(mesh.vert_properties[:,:3]).tolist(),
       'faces':np.asarray(mesh.tri_verts).tolist(),'rgba':color or [.2,.26,.29,1],
       'density_kg_m3':density,'volume_m3':s.volume(),**kw}
    parts.append(p)
    return p

def make_frame(i,a,b):
    A,B=np.array(P[a]),np.array(P[b]);L=np.linalg.norm((B-A)[[0,2]])
    # Continuous pierced cheeks integrate BOTH joint eyes; no detached discs.
    caps=[Point(*A[[0,2]]).buffer(.10,quad_segs=16),
          Point(*B[[0,2]]).buffer(.095,quad_segs=16)]
    poly=caps[0].union(caps[1]).convex_hull
    parent_bore=.0615;child_bore=.0500
    proximal=parent_bore if i==0 else child_bore
    poly=poly.difference(Point(*A[[0,2]]).buffer(proximal,quad_segs=16))
    poly=poly.difference(Point(*B[[0,2]]).buffer(parent_bore,quad_segs=16))
    # Load cheeks remain broad in X/Z but are nested in Y. Paired cylinders
    # occupy explicit external side bands instead of cutting through the box.
    offset=.105 if i%2==0 else .060
    cheeks=[extrude(poly,.5+sgn*offset,.024) for sgn in (-1,1)]
    # The box joins the two cheeks over the centre span and stops before the
    # interleaved journals. Actual hollow wall, not a filled collision hull.
    u=(B-A)/np.linalg.norm(B-A)
    web=beam(A+u*.24,B-u*.24,2*offset+.024,.155,.009)
    frame=union(cheeks+[web])
    # Journal is an explicit interference-seat construction assumption. Bore
    # radial running gap is 0.5mm for this probe, NOT a manufacturing tolerance.
    for c,receive in ((A,i==0),(B,True)):
        if receive:
            for sgn in (-1,1):
                center=c+[0,sgn*offset,0]
                frame=frame+cylinder(center,.0616,.024,.0505)
    add('frame_'+BODIES[i],BODIES[i],frame,color=COLORS[i],
        construction='Connected finite hollow box with integral pierced cheeks; press-fit journal seat assumption, fastening/grade unqualified',
        plate_thickness_m=.024,box_wall_m=.009,cheek_offset_m=offset)
    if i:
        # Shaft is fixed to this child; parent journals rotate around it.
        pin=cylinder(A,.0501,.258,.03)
        add('shaft_'+a,BODIES[i],pin,'shaft',color=[.5,.55,.59,1])

def new_shoe():
    from shapely.geometry import Polygon
    # Separate low toe/heel contact regions. This is an explicit new candidate,
    # not an invented claim that the old foot was frozen or physically passed.
    for name,profile in (
        ('toe',[(.025,.345),(.29,.345),(.35,.405),(.35,.595),(.29,.655),(.025,.655)]),
        ('heel',[(-.29,.36),(-.14,.36),(-.10,.40),(-.10,.60),(-.14,.64),(-.29,.64)])):
        poly=Polygon(profile)
        s=mf.CrossSection([list(poly.exterior.coords)[:-1]]).extrude(.026)
        add(name+'_contact_pad','shoe',s,'contact_pad',color=[.06,.07,.08,1],density=1100)

def foot_carrier():
    A=np.array(P['ankle'])
    # New low shoe carrier nested inside the distal clevis. Toe and heel pads
    # are new finite candidates, not locked legacy foot geometry.
    outer=Point(*A[[0,2]]).buffer(.082,quad_segs=16).union(
        Point(A[0],.11).buffer(.060,quad_segs=16)).convex_hull
    outer=outer.difference(Point(*A[[0,2]]).buffer(.05,quad_segs=16))
    cheek=[extrude(outer,.5+s*.060,.024) for s in (-1,1)]
    pieces=cheek+[box([A[0],.5,.105],[.13,.144,.04])]
    for s in (-1,1):
        # Curved support path, all within the same locked standing carrier.
        a=[A[0],.5+s*.028,.105];b=[.10,.5+s*.028,.052]
        pieces.append(beam(a,b,.04,.055,.008))
        pieces.append(beam([A[0],.5+s*.028,.105],[-.20,.5+s*.028,.052],.04,.055,.008))
    pieces += [box([.18,.5,.042],[.31,.30,.032]),box([-.195,.5,.042],[.19,.28,.032])]
    add('pressure_carrier','shoe',union(pieces),color=[.27,.3,.32,1],
        scope='Locked standing carrier only. Fore/heel articulation, latches and full native pressure coverage NOT verified.')
    add('shaft_ankle','shoe',cylinder(A,.0501,.258,.03),'shaft',color=[.5,.55,.59,1])

def main():
    for i,(a,b) in enumerate(PAIRS):make_frame(i,a,b)
    new_shoe();foot_carrier()
    scene={'revision':'native_leg_probe_03_lowered_crouch','coordinate_frame':{'forward':'+X','left':'+Y','up':'+Z','units':'m'},
       'parts':parts,'stations_world_m':P,'serial_links':PAIRS,
       'reference_link_lengths_m':LENGTHS,'reference_pitches_from_down_vertical_deg':PITCHES,
       'height_decision':'Old 2.65m target explicitly released by user. New leg dimensions reduce reference hip height; whole height pending unchanged-upperbody assembly.',
       'joints':[{'id':n,'parent':BODIES[i],'child':BODIES[i+1] if i<2 else 'shoe','center':P[n],
                  'axis':[0,1,0],'running_radial_gap_m':.0005} for i,n in enumerate(('knee','fold','ankle'))],
       'original_reference_only':{'source':str(BASE),'sha256':BASE_SHA,
                      'scope':'Reference only. No original foot or SI parameters have been overwritten.'},
       'decision':'User clarified that preserving the old foot was NOT the instruction. This probe rebuilds the complete lower support architecture.',
       'reference_pose':'Crouched load-bearing stance, NOT vertically stacked/straightened. Thigh forward-down, middle rear-down, distal forward-down. All motion samples are deltas from this geometry.',
       'build_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       'status':'geometry_probe_before_drive_and_physical_acceptance','physical_accepted':False,
       'not_included':['hip/pelvis attachment','actual complete drives and valves','ankle roll','unloaded foot fold/locks','wholebody equilibrium and motions','elastic stress/fatigue/thermal qualification']}
    (OUT/'candidate_scene.json').write_text(json.dumps(scene,indent=2,allow_nan=False)+'\n')
    print('BUILT',len(parts),'finite candidate parts',flush=True)

if __name__=='__main__':main()
