"""Deterministic, editable reference reconstruction; +X front, +Y port, +Z up.
No source meshes are available: dimensions are proportional estimates, not original CAD.
Display geometry never becomes per-part dynamic bodies.
"""
from pathlib import Path
import json, math, hashlib, shutil
import numpy as np
import trimesh as tm
from mesh_profiles import extrude_xz,circle_xz
from surface_marks import side_paint,lettering,ring_paths,snow_emblem
ROOT=Path(__file__).resolve().parents[1]
from layout import UNDER,LAYOUT,CENTERS,AUTHOR_CENTERS,DELTAS
RESERVOIRS=json.loads((ROOT/'design/vehicle.json').read_text())['reservoirs']
WHEELS=np.asarray(UNDER['wheels_x_z_radius'],dtype=float)
# A common sampled envelope around actual wheel circles owns both authored
# links and the GPU display path. Three lower wheel bottoms share one tangent.
from scipy.spatial import ConvexHull
samples=[]
for wx,wz,wr in WHEELS:
    for a in np.arange(24)*2*np.pi/24:
        samples.append((wx+(wr+UNDER['belt_centerline_clearance'])*np.cos(a),wz+(wr+UNDER['belt_centerline_clearance'])*np.sin(a)))
samples=np.asarray(samples)
TRACK_PATH=samples[ConvexHull(samples).vertices][::-1]
start=int(np.argmin(np.linalg.norm(TRACK_PATH-np.array([WHEELS[0,0],WHEELS[0,1]+WHEELS[0,2]+UNDER['belt_centerline_clearance']]),axis=1)))
TRACK_PATH=np.roll(TRACK_PATH,-start,axis=0)
TRACK_PATH=np.round(TRACK_PATH,7)
TRACK_CLOSED=np.vstack((TRACK_PATH,TRACK_PATH[:1]))
TRACK_LENGTHS=np.linalg.norm(np.diff(TRACK_CLOSED,axis=0),axis=1)
TRACK_CUMULATIVE=np.r_[0,np.cumsum(TRACK_LENGTHS)]

COLORS={'ivory':'c8ccbf','edge':'959f98','steel':'626e69','track':'353f40','roller':'74817c','glass':'253e42','yellow':'d5ad3d','orange':'b95132','black':'283032','silver':'adb7b4','panelmesh':'434c4b','insignia':'5b7888'}
MATS={k:tm.visual.material.PBRMaterial(name=k,baseColorFactor=[*bytes.fromhex(v),255],metallicFactor=.45 if k in ('steel','silver','track') else .08,roughnessFactor=.5 if k!='glass' else .18) for k,v in COLORS.items()}
parts=[]; meshes={}; groups={}; group='front'
def add(name,m,mat='ivory'):
    m.visual=tm.visual.TextureVisuals(material=MATS[mat]);parts.append((name,group,mat,m));return m

def box(name,p,s,mat='ivory',angle=0):
    if min(s)>.4:
        half=np.array(s)/2;b=min(.10,min(s)*.10)
        vertices=[]
        for signs in __import__('itertools').product((-1,1),repeat=3):
            for axis in range(3):
                q=half.copy();q[axis]-=b;vertices.append(q*np.array(signs))
        m=tm.convex.convex_hull(vertices)
    else:m=tm.creation.box(extents=s)
    if angle:m.apply_transform(tm.transformations.rotation_matrix(angle,[0,1,0]))
    m.apply_translation(p);return add(name,m,mat)

def cyl(name,p,r,h,mat='steel',axis=(0,0,1),sections=20):
    m=tm.creation.cylinder(r,h,sections=sections);m.apply_transform(tm.geometry.align_vectors([0,0,1],axis));m.apply_translation(p);return add(name,m,mat)

def beam(name,a,b,w=.12,mat='steel',depth=None):
    a=np.array(a);b=np.array(b);m=tm.creation.box(extents=[w,depth or w,np.linalg.norm(b-a)]);m.apply_transform(tm.geometry.align_vectors([0,0,1],b-a));m.apply_translation((a+b)/2);return add(name,m,mat)

def profile(name,xz,y,width,mat='ivory',holes=()):
    # Preserve the authored outline, including concave recesses and true openings.
    return add(name,extrude_xz(xz,y,width,holes),mat)

def profile_yz(name,yz,x,width,mat='ivory',holes=()):
    m=extrude_xz(yz,x,width,holes)
    swap=np.eye(4);swap[:3,:3]=[[0,1,0],[1,0,0],[0,0,1]];m.apply_transform(swap)
    return add(name,m,mat)

def rod(name,a,b,r,mat='steel'):
    a=np.array(a);b=np.array(b)
    return cyl(name,(a+b)/2,r,float(np.linalg.norm(b-a)),mat,b-a,20)

def rail(name,a,b,z):
    a=np.array([*a,z]);b=np.array([*b,z]);n=max(1,int(np.linalg.norm(b-a)/1.5))
    for h in (.6,1.15):beam(name+'_rail',a+[0,0,h],b+[0,0,h],.045,'edge')
    for t in np.linspace(0,1,n+1):
        p=a+(b-a)*t;beam(name+'_post',p,p+[0,0,1.15],.05,'edge')

def truss(name,x0,x1,y,z,height=.9,step=2):
    for zz in (z,z-height):beam(name+'_chord',(x0,y,zz),(x1,y,zz),.16,'steel',.22)
    xs=np.linspace(x0,x1,max(2,round((x1-x0)/step)+1))
    for i in range(len(xs)-1):beam(name+'_web',(xs[i],y,z-height*(i%2)),(xs[i+1],y,z-height*((i+1)%2)),.12,'steel')

def cabin(name,p,s,windows=False):
    x,y,z=p;dx,dy,dz=s;box(name,p,s)
    for yy in (y-dy/2-.035,y+dy/2+.035):
        for xx in np.arange(x-dx/2+.8,x+dx/2,.9):
            box(name+'_seam',(xx,yy,z),(.035,.025,dz-.2),'edge')
        for xx in np.arange(x-dx/2+1.4,x+dx/2,3.4):
            box(name+'_hatch',(xx,yy,z-.25),(1.1,.08,2),'ivory')
            box(name+'_handle',(xx+.33,yy+np.sign(yy-y)*.06,z-.1),(.05,.1,.3),'steel')
            if windows:box(name+'_window',(xx,yy+np.sign(yy-y)*.055,z+.65),(.8,.035,.65),'glass')
    for xx in np.arange(x-dx/2+1,x+dx/2,2.8):
        box(name+'_roof_hatch',(xx,y,z+dz/2+.055),(1.3,1.4,.08),'edge')
        beam(name+'_handle',(xx-.3,y,z+dz/2+.12),(xx+.3,y,z+dz/2+.12),.055,'steel')

def side_plate(name,x,y,z,w,h,depth=.06,r=.1,mat='ivory'):
    # Rounded plate corners are actual perimeter vertices, not a square decal.
    r=min(r,w/2-.001,h/2-.001);outline=[]
    for cx,cz,start in [(x+w/2-r,z+h/2-r,0),(x-w/2+r,z+h/2-r,90),
                        (x-w/2+r,z-h/2+r,180),(x+w/2-r,z-h/2+r,270)]:
        for a in np.linspace(start,start+90,5):
            outline.append((cx+r*np.cos(np.deg2rad(a)),cz+r*np.sin(np.deg2rad(a))))
    return profile(name,outline,y,depth,mat)

def side_door(name,x,y,z,w=1.0,h=2.2,window=False):
    side=np.sign(y)
    side_plate(name+'_gasket',x,y,z,w+.09,h+.09,.065,.12,'edge')
    side_plate(name+'_leaf',x,y+side*.048,z,w,h,.06,.10)
    for zz in (z-h*.34,z+h*.34):box(name+'_hinge',(x-w*.43,y+side*.10,zz),(.13,.16,.23),'edge')
    beam(name+'_handle',(x+w*.30,y+side*.17,z-.08),(x+w*.30,y+side*.17,z+.22),.055,'steel')
    if window:side_plate(name+'_window',x,y+side*.09,z+h*.22,w*.58,h*.25,.035,.07,'glass')

def turned(name,x,y,z,section,mat='silver',segments=48):
    """Closed radius/axial profile, rotated from lathe Z to vehicle X."""
    m=tm.creation.revolve(np.asarray(section),sections=segments)
    m.apply_transform(tm.geometry.align_vectors([0,0,1],[1,0,0]))
    m.apply_translation([x,y,z])
    if not m.is_volume:raise ValueError('Turned part must have closed outward volume: '+name)
    return add(name,m,mat)

def skin_ring(name,x,y,z,r,width,mat='edge'):
    # Visible thin cylindrical trim surface; no hidden full end disks inside shell.
    theta=np.arange(48)*2*np.pi/48
    v=np.array([[xx,y+r*np.cos(t),z+r*np.sin(t)] for xx in (x-width/2,x+width/2) for t in theta])
    f=[]
    for i in range(48):
        j=(i+1)%48;f.extend([(i,j,48+j),(i,48+j,48+i)])
    return add(name,tm.Trimesh(vertices=v,faces=f,process=False),mat)

def tank(name,x,y,z,r=2.45,length=23):
    half=length/2
    # Authoring coordinates: -X is a flat dished cover; +X is a ribbed dome.
    # The complete bank rotates at installation: covers -Y, domes +Y (refs 2/5 and 1).
    section=[(0,-half-.10),(.42,-half-.10),(.65,-half-.13),(.82,-half-.20),
             (r*.90,-half-.20),(r*.98,-half-.13),(r,-half+.04),
             (r,half-.15),(r*.98,half+.15),(r*.91,half+.52),
             (r*.77,half+.86),(r*.56,half+1.13),(.72,half+1.28),
             (.62,half+1.28),(.59,half+1.15),(0,half+1.15)]
    turned(name+'_shell',x,y,z,section)
    for side,xx in [(-1,x-half-.12),(1,x+half+1.27)]:
        # Ring-shaped rims leave the dished centers visible.
        radius=r*.965 if side<0 else .72
        turned(name+'_cap_rim',xx,y,z,[(radius-.065,-.025),(radius,-.025),(radius,.025),(radius-.065,.025),(radius-.065,-.025)],'edge')
    # Eight shallow radial stiffeners follow the forward dome, never a flat disk.
    for angle in np.arange(8)*2*np.pi/8:
        pts=[]
        for axial,radial in [(half+.05,r*.996),(half+.48,r*.93),(half+.83,r*.79),(half+1.15,r*.55)]:
            pts.append((x+axial,y+radial*np.cos(angle),z+radial*np.sin(angle)))
        for aa,bb in zip(pts,pts[1:]):beam(name+'_nose_rib',aa,bb,.085,'edge')
    stations=RESERVOIRS['band_stations_x']
    for i,xx in enumerate(stations):
        turned(name+'_band',xx,y,z,[(r-.025,-.095),(r+.08,-.095),(r+.08,.095),(r-.025,.095),(r-.025,-.095)],'edge')
        if i<5:
            for xxx in np.linspace(xx+.34,stations[i+1]-.34,7):skin_ring(name+'_skin_seam',xxx,y,z,r+.018,.022)
        angle=math.radians(RESERVOIRS['clamp_pin_angle_degrees'])
        pin_radius=RESERVOIRS['clamp_pin_radial_offset']
        for sign in (-1,1):
            py=y+sign*pin_radius*np.sin(angle);pz=z+pin_radius*np.cos(angle)
            # Curved band clamp with a true axial pin bore, seated on the band.
            outline=[]
            for rr,angles in [(r+.43,np.linspace(20,60,9)),(r+.05,np.linspace(60,20,9))]:
                outline.extend((y+sign*rr*np.sin(np.deg2rad(a)),z+rr*np.cos(np.deg2rad(a))) for a in angles)
            profile_yz(name+'_clamp_cheek',outline,xx,.42,'ivory',[circle_xz(py,pz,.105,24)])
            cyl(name+'_clamp_pin',(xx,py,pz),.10,.80,'steel',(1,0,0),20)
            for dx in (-.425,.425):
                cyl(name+'_pin_cap',(xx+dx,py,pz),.15,.07,'edge',(1,0,0),20)
                cyl(name+'_pin_nut',(xx+dx+np.sign(dx)*.05,py,pz),.083,.055,'steel',(1,0,0),6)
        # One shaped crown is an editable mesh, with air below its flattened top.
        crown=[(-1.80,2.09),(-1.20,2.52),(-.47,2.90),(.47,2.90),(1.20,2.52),(1.80,2.09),
               (1.68,1.98),(1.04,2.40),(.39,2.71),(-.39,2.71),(-1.04,2.40),(-1.68,1.98)]
        profile_yz(name+'_crown',[(y+yy,z+zz) for yy,zz in crown],xx,.19,'edge')
        box(name+'_crown_closure',(xx,y,z+2.91),(.40,.72,.16),'ivory')
        for yy in (y-.25,y+.25):cyl(name+'_closure_bolt',(xx,yy,z+3.015),.055,.05,'steel',sections=8)
        if i in (0,5):
            for yy in (y-.38,y+.38):box(name+'_marker',(xx,yy,z+3.00),(.16,.18,.10),'orange')

# Source topology is kept as named parts; runtime batches each material per moving group.
for hull,cx in AUTHOR_CENTERS.items():
    group=hull;groups[group]=[cx,0,7.2]
    box(hull+'_deck',(cx,0,7.15),(34 if hull=='front' else 33,27,.6))
    for yy in (-12.9,12.9):
        box(hull+'_side_fascia',(cx,yy,6.9),(33,.38,.95))
        for xx in (cx+offset for offset in UNDER['bogie_offsets_x']):
            cyl('side_service_flange',(xx,yy+np.sign(yy)*.25,6.95),.67,.2,'edge',(0,1,0),28)
            cyl('side_service_cap',(xx,yy+np.sign(yy)*.37,6.95),.52,.08,'ivory',(0,1,0),24)
        for xx in (cx-15,cx-6,cx+3,cx+15):
            box('side_access_hatch',(xx,yy+np.sign(yy)*.24,6.95),(1.0,.07,.6),'edge')
            box('amber_side_marker',(xx-.7,yy+np.sign(yy)*.26,6.95),(.17,.1,.18),'orange')
        truss(hull+'_lower',cx-16,cx+16,yy,6.8,1.15,3)
        rail(hull+'_walk',(cx-16,yy),(cx+16,yy),7.48)
        box(hull+'_walkplate',(cx,yy,7.5),(32,1.1,.08),'edge')
    for xx in np.arange(cx-15,cx+16,3.2):
        box(hull+'_crossbeam',(xx,0,6.55),(.35,25,.7),'steel')
    for y in (-9.5,9.5):
        box(hull+'_girder',(cx,y,6.65),(33,.55,1),'ivory')
        for x in (cx-4.5,cx+4.5):
            # Photo-visible orange drive machinery occupies the open belly bay.
            box('powerpack',(x,y,5.92),(7,3.2,1.5),'orange')
            outer=y+np.sign(y)*1.64
            for xx in np.linspace(x-2.8,x+2.8,5):
                cyl('power_hub',(xx,outer,5.98),.28,.08,'steel',(0,1,0),16)
                cyl('power_hub_center',(xx,outer+np.sign(y)*.05,5.98),.11,.06,'edge',(0,1,0),12)
            for xx in (x-2.85,x,x+2.85):box('powerpack_rib',(xx,y,5.94),(.12,3.3,1.56),'edge')
            rod('powerpack_service_line',(x-3,outer,5.45),(x+3,outer,5.45),.07,'steel')
            for xx in (x-2.4,x+2.4):beam('machinery_mount',(xx,y,6.8),(xx,y,6.45),.34,'steel')
    for localx in UNDER['bogie_offsets_x']:
        for side in (-1,1):
            x=cx+localx;y=side*11.8;stem=f'{hull}_bogie_{"fore" if localx>0 else "aft"}_{"left" if side>0 else "right"}'
            # Recessed cast support, inspection cover and rotary base. These
            # visual castings are not a newly qualified suspension mechanism.
            cyl('steering_collar',(x,y,6.12),1.5,.44,'edge')
            profile('cast_yoke',[(x-1.65,6.06),(x+1.60,6.06),(x+1.60,5.62),
                (x+.52,5.62),(x+.18,5.28),(x+.35,4.91),(x+1.25,4.56),
                (x+1.25,3.80),(x-.95,3.80),(x-1.65,4.53)],y,1.80)
            outer=y+side*.96
            side_plate('yoke_service_frame',x-.45,outer,4.62,1.70,1.25,.08,.18,'edge')
            side_plate('yoke_service_cover',x-.45,outer+side*.055,4.62,1.51,1.08,.07,.15)
            for off in (-.62,.62):
                for zz in (4.24,5.00):cyl('yoke_cover_bolt',(x-.45+off,outer+side*.11,zz),.065,.05,'steel',(0,1,0),8)
            for offset in (-2.4,2.4):
                beam('suspension_shoulder',(x+offset,y,6.35),(x+np.sign(offset)*1.25,y,5.55),.36,'edge',.50)
            group=stem;groups[group]=[x,y,UNDER['pivot_z']]
            box('bogie_backbone',(x,y,2.95),(8,1.3,.6),'steel')
            box('bogie_center_platform',(x,y,4.0),(8.5,1.35,.18),'edge')
            cyl('bogie_lower_bearing',(x,y,4.25),1.35,.42,'edge')
            cyl('bogie_bearing_flange',(x,y,4.10),1.60,.15,'steel')
            for a in np.arange(12)*math.pi/6:
                cyl('turntable_bolt',(x+1.46*np.cos(a),y+1.46*np.sin(a),4.2),.075,.08,'ivory',(0,0,1),8)
            for yy in (y-.72,y+.72):
                for x0,x1 in [(x-4.4,x-1.8),(x+1.8,x+4.4)]:rail('bogie_service_rail',(x0,yy),(x1,yy),4.10)
            for belt in (-1,1):
                by=y+belt*1.75
                # Separate folded fenders leave the central service platform legible.
                profile('belt_fender',[(x-5.5,3.84),(x-5.18,4.08),(x+4.78,4.08),
                    (x+5.6,3.75),(x+5.55,3.60),(x+4.75,3.92),
                    (x-5.14,3.92),(x-5.45,3.68)],by,2.3,'edge')
                for xx in np.linspace(x-4.45,x+4.1,6):
                    box('fender_removable_panel',(xx,by,4.10),(1.61,2.15,.04),'edge')
                    for yy in (by-.90,by+.90):cyl('fender_fastener',(xx,yy,4.14),.055,.04,'steel',(0,0,1),8)
                for xx in (x-3,x+3):beam('fender_bracket',(xx,y,3.15),(xx,by,3.94),.16,'steel')
                for facing in (-1,1):
                    outline=[(x-4.2,3.05),(x+4.2,3.05),(x+4.2,2.15),(x+3.55,1.45)]
                    for wx in (2.55,0,-2.55):
                        outline.extend((x+wx+.60*np.cos(a),1.45+.60*np.sin(a)) for a in np.linspace(0,np.pi,13))
                    outline.extend([(x-3.55,1.45),(x-4.2,2.15)])
                    frame=profile('track_inner_frame',outline,by+facing*.105,.07,'steel')
                    frame.metadata['assembly']='bogie_structure'
                for wheel_index,(wx,wz,r) in enumerate(WHEELS):
                    cyl('wheel_axle',(x+wx,by,wz),.17,1.6,'steel',(0,1,0),16)
                    first_wheel=len(parts)
                    # Paired drums leave a central gap for the moving guide horn.
                    for edge in (-1,1):
                        cyl('road_wheel',(x+wx,by+edge*.43,wz),r,.55,'track',(0,1,0),24)
                        cyl('wheel_rim',(x+wx,by+edge*.72,wz),r*.84,.07,'roller',(0,1,0),24)
                        cyl('wheel_hub',(x+wx,by+edge*.78,wz),r*.43,.10,'edge',(0,1,0),24)
                        cyl('hub_cap',(x+wx,by+edge*.845,wz),r*.25,.06,'steel',(0,1,0),20)
                        for a in np.arange(8)*math.pi/4:
                            cyl('wheel_rim_bolt',(x+wx+r*.60*np.cos(a),by+edge*.78,wz+r*.60*np.sin(a)),.05,.05,'ivory',(0,1,0),8)
                    for record in parts[first_wheel:]:record[3].metadata['wheel_index']=wheel_index
                # Uniform arclength spacing replaces short links crowded at corners.
                count=round(TRACK_CUMULATIVE[-1]/UNDER['target_link_pitch'])
                pitch=TRACK_CUMULATIVE[-1]/count
                for n in range(count):
                    phase=(n+.5)*pitch
                    k=min(len(TRACK_LENGTHS)-1,int(np.searchsorted(TRACK_CUMULATIVE,phase,side='right')-1))
                    t=(phase-TRACK_CUMULATIVE[k])/TRACK_LENGTHS[k]
                    d=(TRACK_CLOSED[k+1]-TRACK_CLOSED[k])/TRACK_LENGTHS[k]
                    q=TRACK_CLOSED[k]+t*(TRACK_CLOSED[k+1]-TRACK_CLOSED[k])
                    normal=np.array([-d[1],d[0]])
                    theta=-math.atan2(d[1],d[0]);first_part=len(parts)
                    box('track_link',(x+q[0],by,q[1]),(pitch*.90,1.8,.18),'track',theta)
                    cleat=q+normal*.13
                    box('track_cleat',(x+cleat[0],by,cleat[1]),(.13,1.92,.12),'edge',theta)
                    pin=q-d*pitch*.46
                    for sign in (-1,1):cyl('track_pin',(x+pin[0],by+sign*.93,pin[1]),.085,.10,'silver',(0,1,0),8)
                    horn=q-normal*.17
                    box('track_guide_horn',(x+horn[0],by,horn[1]),(.20,UNDER['guide_horn_width'],.22),'steel',theta)
                    for record in parts[first_part:]:record[3].metadata['belt_phase']=float(phase)
            group=hull
# Center coupling and plumbing.
group='front'
hx,hz=LAYOUT['hitch_x'],LAYOUT['hitch_z']
cyl('hitch_ring',(hx,0,hz),1.35,2.8,'steel',(1,0,0))
for y in (-2,2):
    beam('coupling_link',(-16,y,hz),(hx,y,hz),.48,'edge')
    box('coupling_deck_mount',(-16,y,6.7),(1.3,1.0,.9),'steel')
beam('coupling_crosshead',(hx,-2,hz),(hx,2,hz),.48,'steel')
group='rear'
# Rear drawbar shares the physical articulation center after the frame transform.
for y in (-2,2):
    beam('rear_drawbar',(AUTHOR_CENTERS['rear']+16,y,hz),(hx-DELTAS['rear'],0,hz),.48,'edge')
    box('coupling_deck_mount',(AUTHOR_CENTERS['rear']+16,y,6.7),(1.3,1.0,.9),'steel')
group='front' 
# Bridge: chamfered in plan as well as elevation; reference 1/2 show a
# tapered lower bow and corner glazing rather than an extruded rectangular end.
BRIDGE=json.loads((ROOT/'design/vehicle.json').read_text())['bridge']
FLOOR=BRIDGE['floor_z'];STAIRS=BRIDGE['stairs'];rise=(FLOOR-STAIRS['bottom_z'])/STAIRS['count']
# The long cabin starts at gallery level; only the forward chin descends farther.
# Intersect a concave elevation with the chamfered plan, rather than taking its hull.
shell=extrude_xz(BRIDGE['shell_outline_xz'],0,7)
plan=[(15,-3.5),(32,-3.5),(34,-2.85),(34,2.85),(32,3.5),(15,3.5)]
clip=tm.convex.convex_hull([(x,y,z) for x,y in plan for z in (8,16)])
shell=tm.boolean.intersection([shell,clip],engine='manifold')
assert shell.is_volume
add('bridge_shell',shell)
roof_xy=[(16.85,-3.64),(32.05,-3.64),(34.15,-2.95),(34.15,2.95),(32.05,3.64),(16.85,3.64)]
add('bridge_roof',tm.convex.convex_hull([(x,y,z) for x,y in roof_xy for z in (14.91,15.08)]))
for side in (-1,1):
    yy=side*3.535
    for xx,window in zip(BRIDGE['door_x'],BRIDGE['door_window']):
        width=BRIDGE['door_width'];height=BRIDGE['door_height'];zz=FLOOR+.04+height/2
        side_plate('bridge_door_gasket',xx,yy,zz,width+.10,height+.10,.060,.08,'steel')
        side_plate('bridge_door_leaf',xx,yy+side*.046,zz,width,height,.052,.07,'edge')
        for dx in (-width*.40,width*.40):
            for zoff in (-height*.39,0,height*.39):
                box('bridge_door_hinge',(xx+dx,yy+side*.097,zz+zoff),(.15,.11,.28),'steel')
                box('bridge_door_hinge_knuckle',(xx+dx+np.sign(dx)*.04,yy+side*.161,zz+zoff),(.055,.04,.19),'ivory')
        for zoff in (-.45,.45):
            box('bridge_door_lock',(xx-width*.34,yy+side*.14,zz+zoff),(.18,.13,.15),'ivory')
        rod('bridge_door_handle',(xx+width*.31,yy+side*.20,zz-.23),(xx+width*.31,yy+side*.20,zz+.08),.030,'steel')
        if window:
            side_plate('bridge_door_window_gasket',xx,yy+side*.084,BRIDGE['window_center_z'],.92,1.02,.020,.07,'steel')
            side_plate('bridge_door_window',xx,yy+side*.10,BRIDGE['window_center_z'],.80,.90,.018,.065,'glass')
    for xx in BRIDGE['square_windows_x']:
        side_plate('bridge_square_window_frame',xx,yy-.020*side,BRIDGE['window_center_z'],1.05,1.12,.030,.075,'edge')
        side_plate('bridge_square_window',xx,yy+.002*side,BRIDGE['window_center_z'],.93,1.00,.020,.07,'glass')
    side_plate('bridge_side_glass',31.35,yy,13.65,1.16,1.47,.04,.10,'glass')
    corner=side_plate('bridge_corner_glass',0,0,0,1.55,1.47,.045,.11,'glass')
    angle=-side*math.atan2(.65,2.0)
    corner.apply_transform(tm.transformations.rotation_matrix(angle,[0,0,1]))
    corner.apply_translation([33.0,side*3.20,13.65])
    # Plate boundaries follow the varying lower edge, with no line floating below it.
    for xx in BRIDGE['side_panel_seams_x']:
        bottom=FLOOR if xx<=27.4 else max(9.5,FLOOR-(xx-27.4)*(FLOOR-9.5)/(29.1-27.4))
        box('bridge_vertical_seam',(xx,side*3.512,(14.73+bottom+.04)/2),(.036,.030,14.73-bottom-.04),'edge')
    hx,hz=BRIDGE['lower_hatch_center_x_z']
    side_plate('bridge_lower_hatch_gasket',hx,side*3.527,hz,1.24,1.40,.055,.055,'edge')
    side_plate('bridge_lower_hatch_leaf',hx,side*3.585,hz,1.12,1.28,.064,.05,'ivory')
    for zoff in (-.42,.42):box('bridge_lower_hatch_hinge',(hx+.55,side*3.64,hz+zoff),(.13,.08,.18),'edge')
    box('bridge_lower_hatch_latch',(hx-.45,side*3.65,hz),(.08,.09,.22),'steel')
    # Roof footholds rise between the solid service doors and return onto the roof.
    lx=BRIDGE['ladder_x']
    for zz in np.arange(FLOOR+.22,15.23,.28):
        for dx in (-.25,.25):rod('bridge_roof_rung_stand',(lx+dx,side*3.50,zz),(lx+dx,side*3.74,zz),.026,'edge')
        rod('bridge_roof_rung',(lx-.25,side*3.74,zz),(lx+.25,side*3.74,zz),.031,'edge')
    for dx in (-.25,.25):
        rod('bridge_ladder_top_return',(lx+dx,side*3.74,15.25),(lx+dx,side*3.24,15.25),.031,'edge')
        rod('bridge_ladder_top_anchor',(lx+dx,side*3.24,15.25),(lx+dx,side*3.24,15.07),.031,'edge')
    holes=[]
    for i in range(4):
        center=17.55+i*2.68
        holes.append([(center-1.125,11.09),(center+1.125,11.09),(center,9.94)])
    for i in range(3):
        center=18.89+i*2.68
        holes.append([(center-1.125,9.90),(center+1.125,9.90),(center,11.04)])
    holes.extend([[(16.22,9.90),(17.20,9.90),(16.22,10.97)],[(25.92,9.90),(27.16,9.90),(27.16,11.02)]])
    profile('bridge_gallery_truss',[(16,9.68),(27.38,9.68),(27.38,11.29),(16,11.29)],side*3.81,.27,'steel',holes)
    beam('bridge_lower_sill',(13.8,side*3.41,9.52),(31.5,side*3.41,9.52),.16,'edge',.18)
    box('bridge_walkdeck',(22.3,side*BRIDGE['gallery_center_y'],FLOOR-.05),(12.2,BRIDGE['gallery_width'],.10),'edge')
    rail('bridge_outer_rail',(16.2,side*5.05),(28.4,side*5.05),FLOOR)
    rail('bridge_end_rail',(28.4,side*3.74),(28.4,side*5.05),FLOOR)
    for xx in (16.5,19.5,22.5,25.5,28.0):
        beam('bridge_gallery_bracket',(xx,side*3.50,FLOOR-.02),(xx,side*4.85,FLOOR-.08),.12,'edge')
    box('bridge_upper_landing',(15.5,side*BRIDGE['gallery_center_y'],FLOOR-.05),(1.5,BRIDGE['gallery_width'],.10),'edge')
    box('bridge_lower_landing',(15.5,side*STAIRS['lower_landing_y'],7.54),(1.5,1.35,.10),'edge')
    for n in range(STAIRS['count']):
        ypos=side*(STAIRS['first_y']-n*STAIRS['pitch_y']);zpos=STAIRS['bottom_z']+(n+1)*rise
        box('bridge_stair_tread',(15.5,ypos,zpos-.05),(1.5,STAIRS['tread_depth'],.10),'edge')
    low_y=STAIRS['first_y']+.15;high_y=STAIRS['first_y']-(STAIRS['count']-1)*STAIRS['pitch_y']-.12
    for xx in (14.72,16.28):
        beam('bridge_stair_stringer',(xx,side*low_y,7.43),(xx,side*high_y,FLOOR-.15),.13,'steel',.22)
        for h in (.62,1.15):beam('bridge_stair_handrail',(xx,side*low_y,7.59+h),(xx,side*high_y,FLOOR+h),.045,'edge')
        for t in np.linspace(0,1,5):
            pp=np.array([xx,side*(low_y+(high_y-low_y)*t),7.59+(FLOOR-7.59)*t])
            beam('bridge_stair_post',pp,pp+[0,0,1.15],.045,'edge')
# Three front windows fit within the chamfered bow width.
for yy in (-1.84,0,1.84):
    m=side_plate('bridge_windscreen',0,0,0,1.63,1.57,.04,.12,'glass')
    m.apply_transform(tm.transformations.rotation_matrix(math.pi/2,[0,0,1]));m.apply_translation([34.025,yy,13.65])
    cyl('bridge_wiper_pivot',(34.06,yy-.50,12.96),.070,.055,'steel',(1,0,0),16)
    rod('bridge_wiper_arm',(34.08,yy-.50,12.96),(34.08,yy+.04,13.50),.025,'steel')
    rod('bridge_wiper_blade',(34.08,yy-.18,13.17),(34.08,yy+.34,13.81),.030,'black')
for xx in (19,22.2,25.4,28.6):
    for yy in (-1.65,1.65):
        box('bridge_roof_hatch',(xx,yy,15.14),(1.40,1.15,.09),'ivory')
        for yoff in (-.40,.40):beam('roof_handle_stand',(xx-.3,yy+yoff,15.19),(xx-.3,yy+yoff,15.42),.045,'edge')
        beam('bridge_roof_handle',(xx-.3,yy-.4,15.42),(xx-.3,yy+.4,15.42),.045,'edge')
# Front service house: two tiers of forward louvres and side inspection doors.
box('fore_service_shell',(9,0,10.4),(10,16,5.8))
for side in (-1,1):
    for xx in (5.5,8.4,11.3):
        side_door('fore_service_door',xx,side*8.035,9.55,1.20,2.4)
        side_plate('fore_service_small_port',xx,side*8.06,12.05,.65,.60,.045,.08,'edge')
    for xx in (4.7,7.3,10.2,13.2):box('fore_house_seam',(xx,side*8.055,10.5),(.05,.05,5.2),'edge')
    rail('fore_roof_side',(4.25,side*7.75),(13.75,side*7.75),13.36)
    rail('fore_house_deck',(4.25,side*9.1),(13.8,side*9.1),7.55)
for xx in (4.25,13.75):rail('fore_roof_end',(xx,-7.75),(xx,7.75),13.36)
for yy in (-5.85,-1.95,1.95,5.85):
    for zz in (9.65,11.65):
        box('fore_vent_frame',(14.035,yy,zz),(.12,3.64,1.72),'edge')
        box('fore_vent_recess',(14.11,yy,zz),(.04,3.38,1.48),'black')
        for zoff in np.linspace(-.64,.64,9):box('fore_vent_louvre',(14.16,yy,zz+zoff),(.12,3.38,.055),'steel')
# Paired rooftop machines with bases, front fan rims, and connecting ducts.
for yy in (-1.4,1.4):
    box('roof_machine_base',(10.1,yy,13.42),(3.1,2.2,.20),'edge')
    box('roof_machine_case',(10.1,yy,14.20),(2.7,2.0,1.50),'ivory')
    cyl('roof_machine_front',(11.52,yy,14.22),.76,.16,'steel',(1,0,0),32)
    turned('roof_machine_rim',11.64,yy,14.22,[(.55,-.08),(.74,-.08),(.74,.08),(.55,.08),(.55,-.08)],'edge',32)
    cyl('roof_machine_hub',(11.73,yy,14.22),.22,.10,'edge',(1,0,0),20)
    for theta_ in np.arange(8)*math.pi/4:
        beam('roof_machine_spoke',(11.70,yy+.25*np.cos(theta_),14.22+.25*np.sin(theta_)),
             (11.70,yy+.58*np.cos(theta_+.22),14.22+.58*np.sin(theta_+.22)),.07,'silver')
    rod('roof_machine_pipe',(8.65,yy,14.20),(7.8,yy,14.20),.18,'edge')
    rod('roof_machine_pipe_down',(7.8,yy,14.20),(7.8,yy,13.40),.18,'edge')
beam('antenna',(12,-5,13.4),(12,-5,23),.045,'steel')
beam('antenna',(12,5,13.4),(12,5,21),.035,'steel')
# Tall central service bank and lower aft paired bays meet at x=-7.4.
box('middle_service_shell',(-1.7,0,11.1),(11.4,21,6))
for side in (-1,1):
    xs=(-6.2,-3.95,-1.7,.55,2.8) if side<0 else (-5.4,-1.7,2.0)
    width=2.03 if side<0 else 3.38
    for xx in xs:
        side_plate('main_access_gasket',xx,side*10.535,11.1,width+.08,5.2,.07,.08,'edge')
        side_plate('main_access_leaf',xx,side*10.60,11.1,width,5.12,.09,.08)
        for off in (-width*.41,width*.41):
            for zz in (9.0,10.4,11.8,13.2):box('main_panel_fastener',(xx+off,side*10.68,zz),(.14,.10,.18),'edge')
        for zz in (9.1,13.1):box('main_panel_stiffener',(xx,side*10.68,zz),(width-.1,.12,.085),'edge')
for yy in (-7.5,7.5):
    truss('panel_rooftop',-8,4,yy*.8,15.4,1.15,1.7)
    cyl('rooftop_receiver',(-1,yy,14.6),.67,4,'edge',(1,0,0))
    for xx in (-2.25,.25):
        box('receiver_seat',(xx,yy,14.18),(.40,1.50,.4),'steel')
        turned('receiver_strap',xx,yy,14.6,[(.65,-.06),(.72,-.06),(.72,.06),(.65,.06),(.65,-.06)],'steel',32)
    box('vent_roof',(-5,yy,14.2),(2.6,2.6,.45))
    cyl('vent_fan',(-5,yy,14.46),1.0,.04,'steel',(0,0,1),32)
    cyl('vent_fan_hub',(-5,yy,14.52),.23,.07,'edge',(0,0,1),20)
    for a in np.arange(12)*math.pi/6:
        beam('fan_grille',(-5+.25*np.cos(a),yy+.25*np.sin(a),14.53),(-5+.93*np.cos(a),yy+.93*np.sin(a),14.53),.045,'edge')
# The port aft facade carries the three visible X braces in reference 1.
for side in (-1,1):
    yy=side*7
    box('aft_service_shell',(-11.9,yy,9.5),(9,8.8,4))
    for xx in (-14.85,-11.9,-8.95):
        side_plate('aft_module_frame',xx,side*11.435,9.55,2.82,3.72,.09,.08,'edge')
        side_plate('aft_module_infill',xx,side*11.50,9.55,2.67,3.56,.08,.05)
        if side>0:
            for slope in (-1,1):
                beam('aft_port_x_brace',(xx-1.20,side*11.58,9.55-slope*1.58),(xx+1.20,side*11.58,9.55+slope*1.58),.13,'edge')
            for off in (-1.18,1.18):
                for zz in (8.0,11.10):box('aft_brace_node',(xx+off,11.61,zz),(.30,.10,.30),'ivory')
        else:
            beam('aft_starboard_sill',(xx-1.15,-11.57,9.55),(xx+1.15,-11.57,9.55),.09,'edge')
    for xx in (-14.5,-11.9,-9.3):
        box('aft_roof_panel',(xx,yy,11.57),(2.35,6.8,.10),'ivory')
        for yy2 in (yy-2.2,yy+2.2):beam('aft_roof_handle',(xx-.3,yy2,11.69),(xx+.3,yy2,11.69),.055,'edge')
    # Aft face split into two framed panels rather than unrelated hatches.
    for y2 in (yy-2.2,yy+2.2):
        box('aft_end_panel',(-16.435,y2,9.5),(.07,4.0,3.65),'edge')
        box('aft_end_infill',(-16.485,y2,9.5),(.06,3.85,3.5),'ivory')
# Main-deck transverse walks now connect the two longitudinal side galleries.
for xx in (-16.65,16.65):
    box('front_transverse_walk',(xx,0,7.54),(.6,26,.08),'edge')
    for y0,y1 in [(-12.9,-2),(2,12.9)]:rail('front_end_rail',(xx,y0),(xx,y1),7.58)
# Elevated service deck bridges both rooftop trusses; the center turntable
# has a visible load path to the main cabin instead of hanging between side frames.
box('raised_panel_deck',(-1.5,0,15.48),(14,12.8,.16),'ivory')
for yy in (-6.0,6.0):
    for xx in (-7,-3,1,4):
        box('raised_deck_seat',(xx,yy,14.20),(.50,.55,.30),'edge')
        beam('raised_deck_post',(xx,yy,14.25),(xx,yy,15.4),.16,'edge')
for xx in (-8,4):
    for zz in (14.25,15.4):beam('raised_cross_frame',(xx,-6,zz),(xx,6,zz),.16,'steel')
    for j,yy in enumerate(np.arange(-6,6,1.5)):
        beam('raised_cross_web',(xx,yy,14.25 if j%2 else 15.4),(xx,yy+1.5,15.4 if j%2 else 14.25),.12,'steel')
# Double-axis folded panel support, locked in the authored transport pose.
PANEL=json.loads((ROOT/'design/vehicle.json').read_text())['panel']
lower=np.array(PANEL['lower_pivot'],dtype=float);upper=np.array(PANEL['upper_pivot'],dtype=float)
cyl('panel_turntable',(-1,0,15.75),3.25,.45,'edge',sections=48)
for a in np.arange(20)*math.pi/10:
    cyl('panel_turntable_bolt',(-1+3.08*np.cos(a),3.08*np.sin(a),16.01),.055,.07,'steel',sections=8)
profile('panel_base',[(-6.2,16.30),(-5.65,15.94),(4.85,15.94),(5.4,16.45),
    (5.4,17.14),(4.85,17.74),(-5.65,17.74),(-6.2,17.16)],0,6.0)
for yy in (-3.025,3.025):
    side_plate('panel_base_inspection_frame',-4.25,yy,16.85,2.35,.70,.05,.12,'edge')
    side_plate('panel_base_inspection_cover',-4.25,yy+np.sign(yy)*.035,16.85,2.12,.51,.035,.10,'ivory')
    cyl('panel_base_service_ring',(-.8,yy,16.85),.34,.06,'yellow',(0,1,0),28)
    cyl('panel_base_service_cap',(-.8,yy+np.sign(yy)*.04,16.85),.28,.045,'ivory',(0,1,0),28)
for xx in (-4.4,-1.3):
    box('panel_base_top_hatch',(xx,0,17.78),(2.25,2.70,.07),'edge')
    for yy in (-.65,.65):beam('panel_base_top_handle',(xx-.33,yy,17.91),(xx+.33,yy,17.91),.055,'steel')
# Fixed fork cheeks terminate at the lower shaft, with a gap to the moving cheeks.
for yy in (-2.75,2.75):
    profile('panel_fixed_fork',[(3.25,17.35),(5.55,17.35),(5.55,18.58),
        (5.05,18.96),(4.36,18.90),(3.85,18.15),(3.25,17.88)],yy,.40,
        holes=[circle_xz(lower[0],lower[2],.26,32)])
for yy in PANEL['arm_y']:
    profile('panel_arm',[(4.3,17.85),(5.20,17.85),(5.38,18.55),(4.68,19.28),
        (4.22,20.79),(3.70,21.18),(3.03,20.92),(2.90,20.32),
        (3.37,19.75),(3.85,18.26)],yy,.50,
        holes=[circle_xz(lower[0],lower[2],.26,32),circle_xz(upper[0],upper[2],.26,32)])
    for pivot in (lower,upper):
        cyl('panel_bearing_housing',(pivot[0],yy,pivot[2]),.47,.61,'ivory',(0,1,0),32)
        cyl('panel_bearing_ring',(pivot[0],yy+np.sign(yy)*.345,pivot[2]),.37,.07,'edge',(0,1,0),32)
        cyl('panel_pivot_cap',(pivot[0],yy+np.sign(yy)*.39,pivot[2]),.27,.04,'steel',(0,1,0),32)
    # Lifting-cylinder eyes meet a roof bracket and a bracket on the folded link.
    base=np.array([.40,yy,17.87]);end=np.array([3.69,yy,19.22]);split=base+(end-base)*.65
    rod('panel_cylinder_barrel',base,split,.17,'edge')
    rod('panel_cylinder_rod',split,end,.085,'silver')
    for at in (base,end):cyl('panel_cylinder_pin',at,.18,.78,'steel',(0,1,0),24)
    for vv in (yy-.29,yy+.29):
        profile('panel_cylinder_roof_ear',[(.06,17.69),(.76,17.69),(.76,18.02),(.45,18.12),(.10,18.03)],vv,.11,'edge')
        profile('panel_cylinder_link_ear',[(3.42,19.0),(3.97,19.0),(4.13,19.49),(3.61,19.56)],vv,.11,'ivory')
    # Shell attachment lugs share the upper shaft rather than ending below the face.
    profile('panel_shell_lug',[(3.04,20.27),(3.12,21.00),(3.75,21.25),
        (4.02,20.71),(3.87,20.26)],yy,.62,'ivory')
for name,pivot,length in [('panel_lower_shaft',lower,6.55),('panel_upper_shaft',upper,5.45)]:
    cyl(name,pivot,.25,length,'steel',(0,1,0),32)
# Crosswise housing between side links, with broad rounded edges from the source view.
profile('panel_fold_case',[(4.15,18.68),(4.98,18.68),(5.03,19.27),
    (4.11,20.52),(3.18,20.48),(3.58,19.25)],0,3.82)
box('panel_fold_case_cover',(4.69,0,19.08),(.14,3.40,.65),'ivory',math.radians(-15))
# One local frame owns shell, face, rear panels and the upper hinge position.
theta=math.radians(PANEL['tilt_degrees'])
panel_rotation=tm.transformations.rotation_matrix(theta,[0,1,0])[:3,:3]
panel_center=upper+panel_rotation@np.array([0,0,PANEL['outer_height']/2])
def panel_slab(name,cy,cz,width,height,depth,thickness,radius,mat):
    outline=[]
    for uy,uz,start in [(width/2-radius,height/2-radius,0),(-width/2+radius,height/2-radius,90),
                        (-width/2+radius,-height/2+radius,180),(width/2-radius,-height/2+radius,270)]:
        for a in np.linspace(start,start+90,7):
            outline.append((cy+uy+radius*np.cos(np.deg2rad(a)),cz+uz+radius*np.sin(np.deg2rad(a))))
    m=extrude_xz(outline,depth,thickness)
    swap=np.eye(4);swap[:3,:3]=[[0,1,0],[1,0,0],[0,0,1]];m.apply_transform(swap)
    transform=np.eye(4);transform[:3,:3]=panel_rotation;transform[:3,3]=panel_center;m.apply_transform(transform)
    return add(name,m,mat)
panel_slab('panel_outer',0,0,PANEL['outer_width'],PANEL['outer_height'],0,PANEL['outer_thickness'],.26,'ivory')
panel_slab('panel_face',0,0,6.80,9.52,.415,.025,.16,'black')
# Tiny raised diamonds reproduce the reference's visible grey weave using portable
# geometry. This is a passive patterned face, not functional sensor elements.
pattern=[]
for row,zz in enumerate(np.arange(-4.59,4.60,PANEL['pattern_pitch'])):
    for yy in np.arange(-3.23,3.24,PANEL['pattern_pitch']):
        yy+=PANEL['pattern_pitch']*.5*(row%2)
        if yy>3.24:continue
        q=tm.creation.box(extents=[.005,.055,.055])
        q.apply_transform(tm.transformations.rotation_matrix(math.pi/4,[1,0,0]))
        q.apply_translation([.431,yy,zz]);pattern.append(q)
m=tm.util.concatenate(pattern);transform=np.eye(4);transform[:3,:3]=panel_rotation;transform[:3,3]=panel_center;m.apply_transform(transform)
add('panel_face_pattern',m,'panelmesh')
for local_y in (-1.78,1.78):
    for local_z in (-3.12,0,3.12):
        panel_slab('panel_rear_cell',local_y,local_z,3.28,2.86,-.45,.10,.10,'edge')
        panel_slab('panel_rear_cover',local_y,local_z,3.01,2.59,-.51,.035,.08,'ivory')
for yy in (-3.48,0,3.48):
    q=panel_center+panel_rotation@np.array([-.55,yy,0]);box('panel_back_spine',q,(.16,.15,9.8),'edge',theta)
for yy in (-3.725,3.725):
    for depth,size,mat in [(0,(.61,.04,1.45),'edge'),(0,(.46,.045,1.27),'ivory')]:
        q=panel_center+panel_rotation@np.array([depth,yy+(.026 if mat=='ivory' else 0)*np.sign(yy),1.15])
        box('panel_side_service_cover',q,size,mat,theta)
# Rear twin-tier 4-column reservoirs. No weapon or sensor functionality.
group='rear'
bank_start=len(parts)
for y in RESERVOIRS['centers_y']:
    for z in RESERVOIRS['levels_z']:tank('sealed_reservoir',-38,y,z)
# Shared supports are registered to the same two end bands as the clamp hardware.
# A shaped waist beam fits the actual gap between all four cylinders of each pair.
for yc in (-6.5,6.5):
    for xx,direction in [(RESERVOIRS['band_stations_x'][0],-1),(RESERVOIRS['band_stations_x'][-1],1)]:
        ys=np.linspace(-3.25,3.25,81);bottom=[];top=[]
        for dy in ys:
            radial=abs(abs(dy)-2.9)
            reach=math.sqrt(max(0,2.53**2-radial**2))
            bottom.append((yc+dy,max(14.20,12+reach+.03)))
            top.append((yc+dy,min(15.30,17.5-reach-.03)))
        profile_yz('paired_cradle_crosshead',bottom+top[::-1],xx,1.15)
        profile('paired_cradle_upright',[(xx-.32,9.1),(xx+.32,9.1),
            (xx+.48,14.1),(xx+.48,16.8),(xx+.34,17.8),
            (xx-.34,17.8),(xx-.48,16.8),(xx-.32,14.1)],yc,.7)
        box('paired_cradle_foot',(xx-direction*.75,yc,7.67),(4.5,4.8,.45),'edge')
        for off in (-1.35,1.35):
            profile('paired_pivot_leg',[(xx-1.8,7.86),(xx+1.2,7.86),
                (xx+.85,8.65),(xx+.28,9.55),(xx-.28,9.55),(xx-.9,8.9)],yc+off,.5)
            cyl('cradle_pivot',(xx,yc+off,9.25),.42,.65,'edge',(0,1,0),24)
            cyl('cradle_pivot_cap',(xx,yc+off+np.sign(off)*.34,9.25),.26,.055,'steel',(0,1,0),24)
        beam('lower_cradle_crossbeam',(xx,yc-4.12,8.82),(xx,yc+4.12,8.82),1.40,'edge',.35)
        for yy in (yc-2.9,yc+2.9):
            # Lower saddle follows the installation band; a thin dark liner fits it.
            arc_y=np.linspace(-1.1,1.1,33)
            arc=[(yy+u,12-math.sqrt(2.56**2-u*u)) for u in arc_y]
            profile_yz('lower_reservoir_saddle',[(yy-1.1,8.95),(yy+1.1,8.95)]+arc[::-1],xx,1.10,'ivory')
            inner=[(yy+u,12-math.sqrt(2.53**2-u*u)) for u in arc_y]
            profile_yz('reservoir_saddle_liner',arc+inner[::-1],xx,.32,'black')
            # Upper and lower contact pads bear on the band, not inside the shell.
            for zz in (14.5425,14.9575):box('cradle_band_pad',(xx,yy,zz),(.32,.45,.055),'black')
    pin_radius=RESERVOIRS['clamp_pin_radial_offset'];angle=math.radians(RESERVOIRS['clamp_pin_angle_degrees'])
    inner_y=2.9-pin_radius*math.sin(angle);pin_z=pin_radius*math.cos(angle)
    for xx in RESERVOIRS['band_stations_x']:
        for zz in RESERVOIRS['levels_z']:
            for dx in (-.34,.34):
                for sign in (-1,1):
                    rod('paired_crown_link',(xx+dx,yc+sign*inner_y,zz+pin_z),(xx+dx,yc+sign*.25,zz+2.47),.085,'edge')
            box('paired_crown_bridge',(xx,yc,zz+2.47),(.92,.62,.22),'ivory')
            for off in (-.25,.25):cyl('paired_bridge_pin',(xx,yc+off,zz+2.47),.10,1.06,'steel',(1,0,0),20)
# The reference bank is transverse: four stations along vehicle X, tube axes Y.
# Rotate the complete sealed shells AND their shared mounting hardware together.
bank_rotation=tm.transformations.rotation_matrix(math.radians(RESERVOIRS['installation_yaw_degrees']),[0,0,1],point=[AUTHOR_CENTERS['rear'],0,0])
for _,_,_,mesh in parts[bank_start:]:
    mesh.apply_transform(bank_rotation);mesh.metadata['assembly']='reservoir_bank'
for y in (-RESERVOIRS['rack_y'],RESERVOIRS['rack_y']):
    truss('tank_side_rack',-52,-23,y,12,1.15,2)
    for x in (-52,-23):beam('rack_column',(x,y,7.4),(x,y,12),.24,'edge')
# Two end cranes on the flat-cover deck edge; reference2/5 transport pose.
CRANES=json.loads((ROOT/'design/vehicle.json').read_text())['cranes']
for crane_index,(x,y,direction) in enumerate(CRANES['placement_x_y_direction']):
    crane_start=len(parts)
    def cp(u,v,z):return (x+direction*u,y+v,z)
    def plate(name,outline,v,width,mat='yellow',holes=()):
        return profile(name,[(x+direction*u,z) for u,z in outline],y+v,width,mat,
                       [[(x+direction*u,z) for u,z in ring] for ring in holes])
    cabin('crane_pedestal',(x,y,9.35),CRANES['pedestal_size'],True)
    box('crane_foundation',(x,y,11.29),CRANES['foundation_size'],'edge')
    cyl('crane_slew_flange',cp(0,0,11.48),1.35,.20,'edge',sections=40)
    cyl('crane_slew',cp(0,0,12.91),1.10,2.68,'ivory',sections=40)
    for a in np.arange(16)*math.pi/8:
        cyl('crane_foundation_bolt',cp(1.21*np.cos(a),1.21*np.sin(a),11.62),.065,.08,'steel',sections=8)
    cyl('crane_neck',cp(0,0,15.0),.77,1.60,'edge',sections=32)
    for zz in (14.33,15.48):cyl('crane_neck_ring',cp(0,0,zz),.84,.13,'ivory',sections=32)
    # Exposed service slots and access cover belong to the column, not the boom.
    for zz in np.arange(13.43,14.05,.12):
        box('crane_column_slot',cp(0,1.105,zz),(.68,.025,.045),'steel')
        box('crane_column_slot',cp(0,-1.105,zz),(.68,.025,.045),'steel')
    side_plate('crane_column_cover',x,y+math.copysign(1.11,y),12.50,.68,.9,.035,.10,'ivory')
    upper_start=len(parts)
    box('crane_turning_head',cp(0,0,15.92),(2.40,2.0,.44),'yellow')
    for v in (-.85,.85):
        plate('crane_pivot_fork',[(-.85,15.85),(.95,15.85),(1.15,17.65),(.3,18.0),(-.85,17.72)],v,.20)
    cyl('crane_main_pin',cp(0,0,17.38),.32,2.22,'steel',(0,1,0),28)
    for v in (-1.14,1.14):cyl('crane_main_pin_cap',cp(0,v,17.38),.40,.09,'edge',(0,1,0),28)
    # The root jacket surrounds a narrower three-window telescoping box section.
    root_outline=[(-1.15,16.92),(3.65,17.03),(3.65,18.04),(.60,18.60),(-1.15,18.30)]
    for v in (-.61,.61):
        plate('crane_root_cheek',root_outline,v,.12,holes=[circle_xz(1.65,17.70,.36,28)])
    beam('crane_root_top',cp(-1.05,0,18.34),cp(.60,0,18.62),.12,'yellow',1.34)
    beam('crane_root_top',cp(.60,0,18.62),cp(3.66,0,18.06),.12,'yellow',1.34)
    beam('crane_root_bottom',cp(-1.05,0,16.94),cp(3.66,0,17.04),.12,'yellow',1.34)
    tip=x+direction*CRANES['boom_tip_offset_x']
    inner_outline=[(2.65,17.13),(11.20,17.13),(11.20,17.69),(2.65,18.06)]
    holes=[]
    for u in (4.7,7.3,9.7):
        top=18.06+(17.69-18.06)*(u-2.65)/(11.20-2.65)
        holes.append(circle_xz(u,(17.13+top)/2,min(.30,(top-17.13)/2-.12),28))
    for v in (-.38,.38):plate('crane_boom',inner_outline,v,.11,holes=holes)
    beam('crane_inner_top',cp(2.65,0,18.07),cp(11.20,0,17.70),.10,'yellow',.86)
    beam('crane_inner_bottom',cp(2.65,0,17.12),cp(11.20,0,17.12),.10,'yellow',.86)
    for u,z in ((3.65,17.55),(8.35,17.44)):
        for v in (-.49,.49):box('crane_slide_pad',cp(u,v,z),(.24,.10,.52),'edge')
    # Cylinder and pin axes meet the fork and boom ear explicitly.
    base=np.array(cp(1.0,0,14.85));end=np.array(cp(4.05,0,17.08));split=base+(end-base)*.67
    rod('crane_cylinder_barrel',base,split,.23,'edge')
    rod('crane_cylinder_rod',split,end,.115,'silver')
    for pin in (base,end):cyl('crane_hydraulic_pin',pin,.24,1.22,'steel',(0,1,0),24)
    for v in (-.50,.50):
        plate('crane_cylinder_upper_ear',[(3.73,17.30),(4.38,17.30),(4.29,16.91),(3.84,16.91)],v,.16)
        plate('crane_cylinder_base_ear',[(.63,15.2),(1.31,15.2),(1.32,14.68),(.63,14.68)],v,.16,'edge')
    # Rear winch, fairleads, tip sheaves and two rope falls.
    cyl('crane_winch_drum',cp(-.58,0,18.84),.35,1.0,'steel',(0,1,0),32)
    for v in (-.57,.57):
        cyl('crane_winch_flange',cp(-.58,v,18.84),.44,.09,'edge',(0,1,0),32)
        plate('crane_winch_stand',[(-1.15,18.29),(.03,18.50),(-.10,18.94),(-1.05,18.94)],v,.13,'edge')
    for v in np.linspace(-.42,.42,11):cyl('crane_drum_rope',cp(-.58,v,18.84),.365,.027,'black',(0,1,0),24)
    cyl('crane_winch_motor',cp(-.58,-.92,18.84),.29,.49,'edge',(0,1,0),24)
    hook_z=CRANES['hook_center_z']
    for v in (-.21,.21):
        for u,z in ((3.65,18.34),(11.18,17.72)):
            cyl('crane_rope_sheave',cp(u,v,z),.19,.095,'steel',(0,1,0),24)
            for dv in (-.07,.07):cyl('crane_sheave_flange',cp(u,v+dv,z),.23,.035,'edge',(0,1,0),24)
        for aa,bb in [(cp(-.55,v,19.205),cp(3.65,v,18.53)),(cp(3.65,v,18.53),cp(11.18,v,17.91)),(cp(11.37,v,17.72),cp(11.37,v,hook_z+.32))]:
            rod('winch_rope',aa,bb,.026,'steel')
    for v in (-.57,.57):plate('crane_tip_cheek',[(10.89,17.20),(11.58,17.20),(11.58,17.86),(11.20,18.04),(10.89,17.91)],v,.12)
    # Closed hook-block cheeks with visible sheave axle; open forged J outline below.
    hook_u=11.37
    for v in (-.36,.36):
        plate('hook_block',[(hook_u-.41,hook_z-.32),(hook_u+.41,hook_z-.32),(hook_u+.48,hook_z+.28),(hook_u+.28,hook_z+.50),(hook_u-.28,hook_z+.50),(hook_u-.48,hook_z+.28)],v,.12)
        cyl('hook_block_pin',cp(hook_u,v,hook_z+.04),.15,.16,'steel',(0,1,0),20)
        for off in (-.24,.17):
            plate('hook_warning_stripe',[(hook_u+off-.09,hook_z-.28),(hook_u+off+.04,hook_z-.28),(hook_u+off+.25,hook_z+.24),(hook_u+off+.12,hook_z+.24)],v+math.copysign(.068,v),.018,'black')
    cyl('hook_block_sheave',cp(hook_u,0,hook_z+.04),.30,.60,'steel',(0,1,0),28)
    cyl('hook_swivel',cp(hook_u,0,hook_z-.47),.17,.32,'steel',sections=20)
    plate('hook',[(hook_u-.12,hook_z-.52),(hook_u+.13,hook_z-.52),(hook_u+.13,hook_z-.83),(hook_u+.31,hook_z-.92),(hook_u+.51,hook_z-.85),(hook_u+.58,hook_z-.63),(hook_u+.70,hook_z-.70),(hook_u+.66,hook_z-1.00),(hook_u+.39,hook_z-1.14),(hook_u+.06,hook_z-1.07),(hook_u-.12,hook_z-.86)],0,.22,'steel')
    upper_end=len(parts)
    # Service ladder reaches the pedestal roof; column-side pipe stops at rotation gap.
    outer=y+math.copysign(1.88,y)
    for xx in (x-.34,x+.34):beam('service_ladder_rail',(xx,outer,7.8),(xx,outer,11.9),.06,'edge')
    for zz in np.arange(7.95,11.4,.35):beam('service_ladder_rung',(x-.34,outer,zz),(x+.34,outer,zz),.05,'edge')
    for v in (-.35,.35):
        rod('crane_column_service_pipe',cp(-1.115,v,11.58),cp(-1.115,v,14.15),.045,'steel')
    for part_index in range(crane_start,len(parts)):
        parts[part_index][3].metadata['assembly']=f'crane_{crane_index}_'+('upper' if upper_start<=part_index<upper_end else 'fixed')
# Reference-visible painted identifiers, access markers and service panel trim.
# Thin geometry survives Blender / glTF / MuJoCo without engine-only decals.
MARKS=json.loads((ROOT/'design/vehicle.json').read_text())['surface_marks']
def paint(name,contours,center,side,mat='steel'):
    return add('paint_'+name,side_paint(contours,center,side),mat)
def rectangle(u,v,w,h):
    return [(u-w/2,v-h/2),(u+w/2,v-h/2),(u+w/2,v+h/2),(u-w/2,v+h/2)]
def hazard_ring(name,x,y,z,side,radius=.22):
    paint(name+'_outline',ring_paths(radius,radius*.58),[x,y,z],side,'yellow')
    # Small four dark breaks belong to the ring; no simulated light emission.
    for angle in np.arange(4)*math.pi/2:
        a=np.linspace(angle-.15,angle+.15,4)
        ring=np.vstack((np.column_stack((radius*np.cos(a),radius*np.sin(a))),
                        np.column_stack((radius*.58*np.cos(a[::-1]),radius*.58*np.sin(a[::-1])))))
        paint(name+'_sector',[ring],[x,y+side*.0045,z],side,'steel')
    paint(name+'_center',[[(-.025,-radius*.43),(.025,-radius*.43),(.025,radius*.43),(-.025,radius*.43)]],[x,y,z],side,'steel')
for hull,cx in AUTHOR_CENTERS.items():
    label=MARKS[hull+'_identifier']
    group=hull
    for side in (-1,1):
        y=side*13.507
        add('paint_frame_identifier',lettering(label,[cx+8.9,y,7.10],side,.31),'steel')
        for x in (cx-8.0,cx+5.2):hazard_ring('frame_service',x,y,7.13,side,.16)
        for x in (cx-15.8,cx-4.8,cx+1.8,cx+15.8):
            paint('frame_round_marker',ring_paths(.105,.035),[x,side*13.097,6.68],side,'orange')
        for x in (cx-7.0,cx-.2,cx+12.9):
            # Orange rectangular inspection sticker with white ruled center.
            paint('access_tab',[rectangle(0,0,.51,.18)],[x,y,7.20],side,'orange')
            for zoff in (-.04,.015):paint('access_tab_rule',[rectangle(0,zoff,.33,.015)],[x,y+side*.0045,7.20],side,'ivory')
        for x in (cx-14,cx+14):
            side_plate('twin_lamp_surround',x,y+side*.025,7.10,.73,.31,.04,.05,'steel')
            for off in (-.17,.17):
                cyl('frame_amber_lens',(x+off,y+side*.06,7.10),.112,.025,'yellow',(0,1,0),20)
                for zoff in (-.055,.055):box('lens_division',(x+off,y+side*.076,7.10+zoff),(.21,.007,.012),'edge')
        for localx in UNDER['bogie_offsets_x']:
            number=MARKS['support_numbers'][hull][str(int(localx>0))]
            # Static support top under the shoulder; label follows its parent hull.
            add('paint_support_number',lettering(number,[cx+localx+.90,side*12.704,5.84],side,.30),'steel')
        for x in (cx-9.7,cx-3.8,cx+2.3,cx+9.7):
            # Existing fascia relief, aligned below the deck edge.
            paint('frame_panel_trim',[[(-.62,-.20),(.42,-.20),(.62,-.05),(.62,.09),(.595,.09),(.595,-.04),(.41,-.18),(-.62,-.18)]],[x,y,7.12],side,'edge')
group='front'
for side in (-1,1):
    y=side*3.505
    paint('bridge_emblem',snow_emblem(),[29.30,y,12.13],side,'insignia')
    # Narrow trim divides the long bridge side into the same horizontal levels.
    for x,z,width in [(24.1,14.67,14.0),(23.8,11.39,14.6),(30.20,9.76,2.00)]:
        paint('bridge_trim',[rectangle(0,0,width,.025)],[x,y,z],side,'edge')
    # Corner warning brackets on the lower forward service hatch.
    for u in (-.48,.48):
        for v in (-.40,.40):
            su=1 if u>0 else -1;sv=1 if v>0 else -1
            path=[(u,v),(u-su*.22,v),(u-su*.22,v-sv*.045),(u-su*.045,v-sv*.045),(u-su*.045,v-sv*.20),(u,v-sv*.20)]
            paint('bridge_hatch_corner',[path],[29.55,side*3.623,10.52],side,'yellow')
    hazard_ring('bridge_service',30.5,y,12.10,side,.12)
    # The crane safety mark is a visible weight icon, with no invented load rating.
for crane_index,(x,y,direction) in enumerate(CRANES['placement_x_y_direction']):
    mark_start=len(parts)
    group='rear'
    for side in (-1,1):
        yy=y+side*.674
        center=[x+direction*2.45,yy,17.65]
        paint('crane_weight',[[( -.20,-.23),(.20,-.23),(.14,.06),(-.14,.06)]],center,side,'steel')
        paint('crane_weight_eye',ring_paths(.075,.035),[center[0],yy,17.78],side,'steel')
        paint('crane_weight_knockout',[rectangle(0,0,.10,.10)],[center[0],yy+side*.0045,17.55],side,'yellow')

    for _,_,_,mesh in parts[mark_start:]:mesh.metadata['assembly']=f'crane_{crane_index}_upper'

# Apply the complete slew pose, including hydraulic attachment ears and rigging.
for crane_index,(x,y,direction) in enumerate(CRANES['placement_x_y_direction']):
    angle=math.radians(CRANES['transport_heading_degrees'][crane_index]-(180 if direction<0 else 0))
    transform=tm.transformations.rotation_matrix(angle,[0,0,1],point=[x,y,0])
    for _,_,_,mesh in parts:
        if mesh.metadata.get('assembly')!=f'crane_{crane_index}_upper':continue
        mesh.apply_transform(transform)
        if mesh.metadata.get('surface_paint'):
            mesh.metadata['paint_center']=tm.transform_points([mesh.metadata['paint_center']],transform)[0].tolist()
            mesh.metadata['paint_normal']=(transform[:3,:3]@np.array([0,mesh.metadata['paint_side'],0])).tolist()

# Central end service covers, carried by each bogie rather than by the hull.
# Append new pieces to retain the IDs of existing parts in the editable source.
for group,pivot in groups.items():
    if '_bogie_' not in group:continue
    x,y,_=pivot;housing=UNDER['end_housing'];first_housing=len(parts)
    for belt in (-1,1):
        by=y+belt*1.75
        for wx,wz,_ in WHEELS[1:4]:
            beam('bogie_road_arm',(x+wx+.45,by,2.30),(x+wx,by,wz),.22,'steel',.28)
    for end in (-1,1):
        outline=[(x+end*dx,z) for dx,z in housing['outline_positive_xz']]
        profile('bogie_end_housing',outline,y,housing['half_width_y']*2,'edge')
        box('bogie_end_hatch_seal',(x+end*5.46,y,2.77),(.06,1.15,1.42),'steel')
        box('bogie_end_hatch_leaf',(x+end*5.50,y,2.77),(.035,1.02,1.29),'edge')
        box('bogie_end_hatch_handle',(x+end*5.535,y+.35,2.78),(.05,.055,.30),'steel')
    for _,_,_,mesh in parts[first_housing:]:mesh.metadata['assembly']='bogie_structure'

# Apply the explicit authoring-frame translation once, before all exports.
for _,pg,_,mesh in parts:
    hull='front' if pg.startswith('front') else 'rear'
    delta=DELTAS[hull]
    if delta:
        mesh.apply_translation([delta,0,0])
        if 'paint_center' in mesh.metadata:mesh.metadata['paint_center'][0]+=delta
for pg,pivot in groups.items():pivot[0]+=DELTAS['front' if pg.startswith('front') else 'rear']

# Material-coalesced GLB: one node per motion group and material, not 4000 draw calls.
scene=tm.Scene();stats={}
for g,pivot in groups.items():
    t=np.eye(4);t[:3,3]=pivot;scene.graph.update(frame_to=g,matrix=t)
    for mat in MATS:
        batch=[]
        for _,pg,pm,original in parts:
            if pg!=g or pm!=mat:continue
            # Explicit hard-edge/smooth-surface normals survive GLB import. The
            # sealed authoring source remains unchanged by render-only splitting.
            m=tm.graph.smooth_shade(original,angle=math.radians(40),facet_minarea=None)
            m.metadata=dict(original.metadata)
            _=m.vertex_normals
            batch.append(m)
        if not batch:continue
        uv=np.concatenate([np.tile([m.metadata.get('wheel_index',m.metadata.get('belt_phase',0)),2 if 'wheel_index' in m.metadata else 1 if 'belt_phase' in m.metadata else 0],(len(m.vertices),1)) for m in batch])
        mesh=tm.util.concatenate(batch);mesh.apply_translation(-np.array(pivot));mesh.visual=tm.visual.TextureVisuals(uv=uv,material=MATS[mat])
        scene.add_geometry(mesh,node_name=g+'__'+mat,geom_name=g+'__'+mat,parent_node_name=g)
        stats[g+'__'+mat]=len(mesh.faces)
ROOT.joinpath('assets').mkdir(exist_ok=True)
def gltf_linear_palette(tree):
    # glTF baseColorFactor is linear; COLORS is an sRGB authoring palette.
    # Override the export tree to retain float precision (PBRMaterial stores RGBA8).
    for material in tree.get('materials',[]):
        rgb=np.array(list(bytes.fromhex(COLORS[material['name']])))/255.
        linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        material['pbrMetallicRoughness']['baseColorFactor']=[*linear.tolist(),1.]
scene.export(ROOT/'assets/leviathan003.glb',tree_postprocessor=gltf_linear_palette,include_normals=True)
# Lossless editable source recipe for Blender; each authored part retains its own object.
recipe={'groups':groups,'colors':COLORS,'parts':[{'name':f'{i:04d}_{name}','group':g,'material':mat,'vertices':m.vertices.tolist(),'faces':m.faces.tolist(),'assembly':m.metadata.get('assembly',''),'surface_paint':({k:v for k,v in m.metadata.items() if k.startswith('paint_')} if m.metadata.get('surface_paint') else None),'motion':({'kind':'wheel','index':int(m.metadata['wheel_index'])} if 'wheel_index' in m.metadata else {'kind':'belt','phase':float(m.metadata['belt_phase'])} if 'belt_phase' in m.metadata else {'kind':'static'})} for i,(name,g,mat,m) in enumerate(parts)]}
import gzip
with gzip.open(ROOT/'source/assembly.json.gz','wt') as f:json.dump(recipe,f,separators=(',',':'))
report={'part_count':len(parts),'render_meshes':len(stats),'triangles':sum(stats.values()),'groups':groups,'bounds_m':scene.bounds.tolist(),'glb_bytes':(ROOT/'assets/leviathan003.glb').stat().st_size,'revision':'r014_bogie_structure','profile_count':sum('profile_area_m2' in m.metadata for _,_,_,m in parts),'real_hole_count':sum(m.metadata.get('profile_holes',0) for _,_,_,m in parts),'source':'six user images; reconstructed geometry, no original CAD','scale':'inherited approximate 90 m class; not an exact measured source dimension'}
(ROOT/'reports/model.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))

shader=(ROOT/'source/belt_template.gdshader').read_text()
path_values=','.join('vec2('+','.join(f'{v:.8f}' for v in p)+')' for p in TRACK_CLOSED)
wheel_values=','.join('vec3('+','.join(f'{v:.8f}' for v in (wx,wz-UNDER['pivot_z'],radius))+')' for wx,wz,radius in WHEELS)
shader=shader.replace('__PATH_DECLARATION__',f'const vec2 path[{len(TRACK_CLOSED)}]=vec2[]({path_values});')
shader=shader.replace('__WHEEL_DECLARATION__',f'const vec3 wheels[{len(WHEELS)}]=vec3[]({wheel_values});')
shader=shader.replace('__SEGMENTS__',str(len(TRACK_LENGTHS))).replace('__PIVOT_Z__',f"{UNDER['pivot_z']:.8f}").replace('__LAST_WHEEL__',str(len(WHEELS)-1))
(ROOT/'godot/belt.gdshader').write_text(shader)
(ROOT/'assets/running_gear.json').write_text(json.dumps({'schema':1,'pivot_z':UNDER['pivot_z'],'wheels_x_z_radius':WHEELS.tolist(),'path_x_z':TRACK_PATH.tolist(),'perimeter':float(TRACK_CUMULATIVE[-1]),'source':'design/vehicle.json; common authored links and generated GPU shader'},indent=2))
