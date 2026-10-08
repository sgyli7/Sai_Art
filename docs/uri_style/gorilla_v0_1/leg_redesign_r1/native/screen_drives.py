"""Search full finite cylinder envelopes before selecting a drive candidate.

Dimensions are explicit CUSTOM proposals, not made-up OEM part numbers.
Including stroke, barrel, gland and eye lengths may reject a plausible drawn
line. A passed envelope remains insufficient for pressure/fatigue qualification.
"""
from pathlib import Path
import json, math, hashlib,itertools,time
import numpy as np
import manifold3d as mf
import trimesh as tr
from shapely.geometry import LineString,Point

OUT=Path(__file__).resolve().parent;SP=OUT/'candidate_scene.json';s=json.loads(SP.read_text())
P={k:np.array(v) for k,v in s['stations_world_m'].items()}
F=(2200+2*800+3000)*9.81*1.5;eta=.85;pressure=30e6;bore=.09;rod=.045
pull=2*eta*pressure*math.pi*(bore*bore-rod*rod)/4

def rotation(c,q):return tr.transformations.rotation_matrix(math.radians(q),[0,1,0],c)
def point(T,p):return (T@np.r_[p,1])[:3]
def envelope(a,b,r):
    u=(b-a)/np.linalg.norm(b-a)
    T=tr.geometry.align_vectors([0,0,1],u);T[:3,3]=(a+b)/2
    return mf.Manifold.cylinder(np.linalg.norm(b-a),r,r,24,True).transform(T[:3,:4].copy())
def solid(p):
    return mf.Manifold(mf.Mesh64(np.array(p['vertices_world_m'],dtype=np.float64,order='C'),np.array(p['faces'],dtype=np.uint64,order='C')))
frames={p['body']:solid(p) for p in s['parts'] if p['role']=='structure'}
frames['shoe']=solid(next(p for p in s['parts'] if p['name']=='pressure_carrier'))

def basis(v):
    v=v/np.linalg.norm(v);n=np.array([-v[2],0,v[0]])
    if n[0]>0:n=-n
    return v,n

result=[];t0=time.time()
for i,j in enumerate(s['joints']):
    bore=(.120,.130,.090)[i];rod=bore/2;od=bore+.020
    pull=2*eta*pressure*math.pi*(bore*bore-rod*rod)/4
    c=P[j['id']];pa=P[['hip','knee','fold'][i]]
    pb=P[['fold','ankle','ankle'][i]] if i<2 else c+np.array([.35,0,-.14])
    u,n=basis(pa-c);v,m=basis(pb-c)
    crouch=json.loads((OUT/'grounded_crouch_report.json').read_text())
    assert crouch['source_sha256']==hashlib.sha256(SP.read_bytes()).hexdigest()
    axis_x=[point(np.array(p['body_transforms'][j['parent']]),c)[0] for p in crouch['poses']]
    target=F*max(abs(x-z) for x in (-.19,.31) for z in axis_x)
    options=[];rejections={'arm_or_capacity':0,'retracted_length':0,'frame_collision':0};tried=0
    for fa,fb,oa,ob in itertools.product((.40,.60,.80,.95),(.35,.55,.75,.95),(-.38,-.24,-.10,.10,.24,.38),(-.38,-.24,-.10,.10,.24,.38)):
        tried+=1;a=c+u*np.linalg.norm(pa-c)*fa+n*oa;b=c+v*np.linalg.norm(pb-c)*fb+m*ob
        rows=[]
        for q in np.linspace(0,s['crouch_joint_deltas_deg'][i],31):
            B=point(rotation(c,q),b);L=np.linalg.norm(B-a)
            arm=np.linalg.norm(np.cross(B-c,(a-B)/L));rows.append((q,L,arm,B))
        Lmin=min(r[1] for r in rows);Lmax=max(r[1] for r in rows);stroke=Lmax-Lmin+.016
        armmin=min(r[2] for r in rows);ratio=pull*armmin/target
        if ratio<1.20:rejections['arm_or_capacity']+=1;continue
        # Stroke + piston/gland/end/head clearance + two real eye regions.
        min_retracted=stroke+.205+.10
        if Lmin<min_retracted:rejections['retracted_length']+=1;continue
        barrel_length=stroke+.205
        collided=False
        for q,L,arm,B in rows:
            T=rotation(c,q);parent=frames[j['parent']];child=frames[j['child']].transform(T[:3,:4].copy())
            direction=(B-a)/L
            for yy in (-(.20,.36,.20)[i],(.20,.36,.20)[i]):
                A=a+[0,yy,0];BB=B+[0,yy,0]
                # Full outside barrel diameter110mm and gland; rod45mm.
                body=envelope(A+direction*.050,A+direction*(.050+barrel_length),od/2)
                pistonrod=envelope(A+direction*(.050+barrel_length),BB-direction*.050,rod/2)
                for frame in (parent,child):
                    if (body^frame).volume()>1e-10 or (pistonrod^frame).volume()>1e-10:
                        collided=True;break
                if collided:break
            if collided:break
        if collided:rejections['frame_collision']+=1;continue
        options.append({'a_world_m':a.tolist(),'b_world_m':b.tolist(),'lateral_offsets_m':[-(.20,.36,.20)[i],(.20,.36,.20)[i]],
                        'bore_m':bore,'rod_m':rod,'outside_diameter_m':od,
                        'barrel_length_m':barrel_length,'proposed_stroke_m':stroke,'eye_length_min_m':Lmin,'eye_length_max_m':Lmax,
                        'min_arm_m':armmin,'neutral_required_moment_Nm':target,'ideal_derated_pair_pull_N':pull,'nominal_min_ratio':ratio,
                        'sweep_samples':len(rows),'unqualified_custom_proposal':True,
                        'sizing_scope':'Worst specified CoP over grounded crouch FK; prescribed own-joint range in this crouch only. Force envelope provisional upperbody2200kg+2legs800kg allowances+external3000kg times1.5. Custom bore/rod,30MPa eta.85,NOT actual mass/continuous rating. No mount/valve/hose qualification.'})
    options.sort(key=lambda o:(o['outside_diameter_m']*o['barrel_length_m'],o['nominal_min_ratio']))
    r={'joint':j['id'],'candidates_tried':tried,'rejections':rejections,'passing_envelopes':len(options),'best':options[:3],'all_options':options}
    result.append(r);print(j['id'],r['passing_envelopes'],rejections,flush=True)
out={'scene_sha256':hashlib.sha256(SP.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
     'drives':result,'elapsed_seconds':time.time()-t0,'physical_accepted':False,'status':'envelope_screen_only_no_complete_drive_assembly'}
(OUT/'drive_envelope_screen.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
