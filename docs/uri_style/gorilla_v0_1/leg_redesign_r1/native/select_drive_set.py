"""Whole-chain conservative projected-cylinder rejection, BEFORE full solids."""
from pathlib import Path
import json,hashlib,itertools,math
import numpy as np
import trimesh as tr
from shapely.geometry import LineString,Point
from shapely.affinity import affine_transform

O=Path(__file__).resolve().parent;P=O/'candidate_scene.json';S=json.loads(P.read_text())
D=json.loads((O/'drive_envelope_screen.json').read_text())
assert D['scene_sha256']==hashlib.sha256(P.read_bytes()).hexdigest()
opts=[d['all_options'] for d in D['drives']]
def fk(q):
    T={'thigh':np.eye(4)}
    for j,a in zip(S['joints'],q):T[j['child']]=T[j['parent']]@tr.transformations.rotation_matrix(math.radians(a),[0,1,0],j['center'])
    return T
def move(p,T):return (T@np.r_[p,1])[:3]
def bands_overlap(a,b):
    ra=max(a['outside_diameter_m']/2,.05);rb=max(b['outside_diameter_m']/2,.05)
    return any(abs(x-y)<=ra+rb for x in a['lateral_offsets_m'] for y in b['lateral_offsets_m'])
def shape(o,j,T):
    a=move(o['a_world_m'],T[j['parent']]);b=move(o['b_world_m'],T[j['child']]);u=(b-a)/np.linalg.norm(b-a)
    aa=a+u*.070;bb=aa+u*o['barrel_length_m']
    body=LineString([aa[[0,2]],bb[[0,2]]]).buffer(o['outside_diameter_m']/2,quad_segs=8)
    rod=LineString([bb[[0,2]],(b-u*.05)[[0,2]]]).buffer(o['rod_m']/2,quad_segs=8)
    return body.union(rod).union(Point(*a[[0,2]]).buffer(.05)).union(Point(*b[[0,2]]).buffer(.05))
def mountshape(o,j,T):
    a=move(o['a_world_m'],T[j['parent']]);b=move(o['b_world_m'],T[j['child']]);u=(b-a)/np.linalg.norm(b-a)
    # Back crossmembers have real depth. Reject below-ground mounting before
    # finite assembly, including rotated neutral fork orientation.
    an=np.array(o['a_world_m']);bn=np.array(o['b_world_m']);un=(bn-an)/np.linalg.norm(bn-an)
    qa=move(an-un*.13,T[j['parent']]);qb=move(bn+un*.13,T[j['child']])
    return LineString([a[[0,2]],qa[[0,2]]]).buffer(.05).union(LineString([b[[0,2]],qb[[0,2]]]).buffer(.05))
T0=fk((0,0,0))
# Neutral standing ground is a real constraint, not just inter-part clearance.
# Reject proposed eyes under the sole and tall forefoot towers as well.
opts=[[o for o in options if shape(o,S['joints'][i],T0).bounds[1]>.008 and
       o['eye_length_min_m']>=o['barrel_length_m']+.135 and
       (i!=2 or .060<o['b_world_m'][2]<.260) and
       (i!=1 or o['b_world_m'][2]>.30) and
       o['a_world_m'][2]<S['stations_world_m'][['hip','knee','fold'][i]][2]-.060]
       for i,options in enumerate(opts)]
sh=[[shape(o,S['joints'][i],T0) for o in options] for i,options in enumerate(opts)]
allowed={}
for i,k in ((0,1),(0,2),(1,2)):
    allowed[i,k]=np.array([[not bands_overlap(opts[i][ai],opts[k][bi]) or not a.intersects(b) for bi,b in enumerate(sh[k])] for ai,a in enumerate(sh[i])])
tried=0;found=None
poses=[(np.array(S['crouch_joint_deltas_deg'])*t).tolist() for t in np.linspace(0,1,121)]
G=json.loads((O/'grounded_crouch_report.json').read_text())
roots=[]
ankle=np.array(S['stations_world_m']['ankle'])
for t,q in zip(np.linspace(0,1,121),poses):
    R=tr.transformations.rotation_matrix(math.radians(S['crouch_hip_pitch_deg']*t),[0,1,0],S['stations_world_m']['hip'])
    moved=move(ankle,R@fk(q)['shoe']);R[:3,3]+=ankle-moved;roots.append(R)
# Screen cylinder/fork floor clearance on the actual planted crouch path.
filtered=[]
for i,options in enumerate(opts):
    keep=[]
    for o in options:
        valid=True
        for q,R in zip(poses,roots):
            T={body:R@tt for body,tt in fk(q).items()}
            if shape(o,S['joints'][i],T).union(mountshape(o,S['joints'][i],T)).bounds[1]<.003:valid=False;break
        if valid:keep.append(o)
    filtered.append(keep)
opts=filtered
(O/'drive_floor_screen_options.json').write_text(json.dumps({'scene_sha256':D['scene_sha256'],'options':opts},indent=2)+'\n')
sh=[[shape(o,S['joints'][i],T0) for o in options] for i,options in enumerate(opts)]
for i,k in ((0,1),(0,2),(1,2)):
    allowed[i,k]=np.array([[not bands_overlap(opts[i][ai],opts[k][bi]) or not a.intersects(b) for bi,b in enumerate(sh[k])] for ai,a in enumerate(sh[i])])
for i,a in enumerate(opts[0]):
    for k,b in enumerate(opts[1]):
        if not allowed[0,1][i,k]:continue
        for h,c in enumerate(opts[2]):
            if not allowed[0,2][i,h] or not allowed[1,2][k,h]:continue
            tried+=1;passed=True
            for q in poses:
                T=fk(q);shapes=[shape(o,j,T) for o,j in zip((a,b,c),S['joints'])]
                if any(bands_overlap((a,b,c)[x],(a,b,c)[y]) and shapes[x].intersects(shapes[y]) for x,y in ((0,1),(0,2),(1,2))):passed=False;break
            if passed:found={'indices':[i,k,h],'options':[a,b,c],'tested_pose_count':len(poses)};break
        if found:break
    if found:break
r={'scene_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'envelope_screen_sha256':hashlib.sha256((O/'drive_envelope_screen.json').read_bytes()).hexdigest(),
   'neutral_clear_combinations_tried':tried,'selection':found,'method':'Conservative XZ filled envelopes only where actual cylinder Y bands overlap. Knee/ankle +/-200mm, fold +/-360mm. Prescribed grounded crouch coupling, NOT arbitrary independent joint limits. Floor/fork outline screen but not finite mounts/bolts. Not a full material/physical acceptance.',
   'physical_accepted':False}
(O/'drive_set_selection.json').write_text(json.dumps(r,indent=2)+'\n')
print('SET SEARCH',tried,'selected',bool(found),flush=True)
