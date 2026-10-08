"""Exact finite-material intersection probes and bounded statics.

No collision masks: every different-owner finite solid pair is queried after
the same FK. Sampled poses are not a certified independent joint-limit box.
"""
from pathlib import Path
import json, hashlib, itertools, math, time, sys
import numpy as np
import manifold3d as mf
from scipy.optimize import linprog
import trimesh as tr

OUT=Path(__file__).resolve().parent
SOURCE=OUT/(sys.argv[1] if len(sys.argv)>1 else 'candidate_scene.json')
S=json.loads(SOURCE.read_text())
SHA=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
GROUNDED='--grounded' in sys.argv

def solid(p):
    faces=[]
    for f in p['faces']:
        faces.extend([[f[0],f[i],f[i+1]] for i in range(1,len(f)-1)])
    return mf.Manifold(mf.Mesh64(np.array(p['vertices_world_m'],dtype=np.float64,order='C'),
                                np.array(faces,dtype=np.uint64,order='C')))

def rotate(c,q):
    c=np.array(c);r=tr.transformations.rotation_matrix(math.radians(q),[0,1,0],c)
    return r

def fk(q,root=None):
    T={'thigh':np.eye(4)}
    for j,a in zip(S['joints'],q):
        T[j['child']]=T[j['parent']]@rotate(j['center'],a)
    if root is not None:
        T={b:root@t for b,t in T.items()}
    for d in S.get('drivers',[]):
        A=np.array(d['A_neutral_world_m']);B=np.array(d['B_neutral_world_m'])
        a=(T[d['parent']]@np.r_[A,1])[:3];b=(T[d['child']]@np.r_[B,1])[:3]
        u=(B-A)/np.linalg.norm(B-A);v=(b-a)/np.linalg.norm(b-a)
        R=tr.geometry.align_vectors(u,v)[:3,:3]
        for body,now,old in ((d['barrel_body'],a,A),(d['rod_body'],b,B)):
            tt=np.eye(4);tt[:3,:3]=R;tt[:3,3]=now-R@old;T[body]=tt
    return T

def run():
    meshes={p['name']:solid(p) for p in S['parts']}
    geometry=[];body_solids={};mass={};inertia={}
    for p in S['parts']:
        m=meshes[p['name']]
        geometry.append({'name':p['name'],'status':str(m.status()),'volume_m3':float(m.volume()),
                         'closed_connected_components':len(m.decompose())})
        if m.status()!=mf.Error.NoError or m.volume()<=0:raise ValueError(geometry[-1])
        body_solids[p['body']]=body_solids.get(p['body'],mf.Manifold())+m
    # Net steel per rigid body; coincident press-fit geometry is unioned before
    # volume accounting. Pads have separate density and do not overlap steel.
    for body in body_solids:
        steel=mf.Manifold();pads=mf.Manifold()
        for p in S['parts']:
            if p['body']==body:
                if p['role']=='contact_pad':pads=pads+meshes[p['name']]
                else:steel=steel+meshes[p['name']]
        mass[body]=steel.volume()*7850+pads.volume()*1100
        pieces=steel.decompose()
        inertia[body]={'steel_net_volume_m3':steel.volume(),'pad_net_volume_m3':pads.volume(),
                       'steel_positive_material_components':sum(x.volume()>1e-10 for x in pieces),
                       'enclosed_negative_cavity_shells':sum(x.volume()<-1e-10 for x in pieces)}
    probes=[(0.,0.,0.)]
    probes += [tuple(float(x) for x in q) for q in itertools.product([-20,-10,0,10,20],repeat=3) if q!=(0,0,0)]
    # Extra deterministic coupled path (forward/return), not endpoint-only.
    probes += [(15*math.sin(t),-12*math.sin(t),10*math.sin(t)) for t in np.linspace(0,2*math.pi,121)]
    roots=[None]*len(probes)
    if GROUNDED:
        G=json.loads((OUT/'grounded_crouch_report.json').read_text())
        assert G['source_sha256']==S.get('parent_geometry_sha256',SHA)
        probes=[];roots=[]
        for t in np.linspace(0,1,121):
            q=(np.array(S['crouch_joint_deltas_deg'])*t).tolist()
            root=rotate(S['stations_world_m']['hip'],S['crouch_hip_pitch_deg']*t)
            ankle=np.array(S['stations_world_m']['ankle'])
            pose=fk(q)
            moved=(root@pose['shoe']@np.r_[ankle,1])[:3]
            root[:3,3]+=ankle-moved
            probes.append(q);roots.append(root)
    pairs=[(a,b) for i,a in enumerate(S['parts']) for b in S['parts'][i+1:] if a['body']!=b['body']]
    collisions=[];min_gaps={};t0=time.time();floor_intrusions=[];stroke_violations=[]
    for index,q in enumerate(probes):
        T=fk(q,roots[index]);mov={p['name']:meshes[p['name']].transform(T[p['body']][:3,:4].copy()) for p in S['parts']}
        bounds={p['name']:np.array(mov[p['name']].bounding_box()).reshape(2,3) for p in S['parts']}
        for p in S['parts']:
            if bounds[p['name']][0,2]<-1e-8:
                floor_intrusions.append({'probe':index,'part':p['name'],'min_z_m':float(bounds[p['name']][0,2])})
        for d in S.get('drivers',[]):
            a=(T[d['parent']]@np.r_[d['A_neutral_world_m'],1])[:3]
            b=(T[d['child']]@np.r_[d['B_neutral_world_m'],1])[:3]
            length=float(np.linalg.norm(b-a));lo,hi=d['eye_length_limits_m']
            if not lo<=length<=hi:stroke_violations.append({'probe':index,'driver':d['id'],'eye_length_m':length,'limits_m':[lo,hi]})
        for a,b in pairs:
            ba,bb=bounds[a['name']],bounds[b['name']]
            if np.any(ba[1]<bb[0]) or np.any(bb[1]<ba[0]):continue
            v=float((mov[a['name']]^mov[b['name']]).volume())
            if v>1e-10:
                collisions.append({'probe':index,'q_deg':list(q),'a':a['name'],'b':b['name'],
                                   'intersection_cm3':v*1e6})
        if index%40==0:print('PROBE',index,'/',len(probes),'collisions',len(collisions),flush=True)
    neutral=fk((0,0,0))
    for a,b in pairs:
        gap=meshes[a['name']].min_gap(meshes[b['name']],.02)
        if gap<.02:min_gaps[a['name']+' / '+b['name']]=gap
    # Physical lower-bound question: do nonnegative ground reactions exist
    # for the prescribed downward resultants, on the ACTUAL native pad vertices?
    contacts=[]
    for p in S['parts']:
        if p['role']=='contact_pad':
            v=np.array(p['vertices_world_m']);contacts.extend(v[np.isclose(v[:,2],0,atol=1e-9),:2].tolist())
    contacts=np.unique(np.round(contacts,9),axis=0)
    F=(2200+2*800+3000)*9.81*1.5
    A=np.vstack([np.ones(len(contacts)),contacts[:,0],contacts[:,1]])
    cases=[]
    for copx in (-.19,-.045,.20,.31):
        ans=linprog(np.zeros(len(contacts)),A_eq=A,b_eq=[F,F*copx,F*.5],bounds=(0,None),method='highs')
        cases.append({'cop_forward_m':copx,'cop_left_m':.5,'force_N':F,'unilateral_reactions_feasible':bool(ans.success),
                      'equilibrium_max_residual_N_Nm':float(np.max(np.abs(A@ans.x-[F,F*copx,F*.5]))) if ans.success else None,
                      'vertex_reactions_N':ans.x.tolist() if ans.success else None})
    # Desired joint efforts obtained from the vertical force line. This is a
    # force envelope, not the mass/inertia of a qualified complete robot.
    demands=[]
    for j in S['joints']:
        demands.append({'joint':j['id'],'largest_neutral_vertical_force_moment_Nm':F*max(abs(c-j['center'][0]) for c in (-.19,.31)),
                        'actual_drive_selected':False,'capacity_pass':None})
    report={'source_sha256':SHA,'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'geometry':geometry,'net_material_mass_kg_by_body':mass,'net_material_details':inertia,
        'scope':'New single-leg finite frame probe only; density assumptions steel7850/pad1100. No actual complete actuators, hips, ankle roll, folding foot or upperbody. Not a passed physical structure.',
        'fk_probe_count':len(probes),'q_values_are_not_safe_joint_limits':True,
        'collision_method':'Manifold64 finite material CSG; no masks, all different-owner pairs. Intersection volume threshold1e-10m3. Finite pose samples, NOT continuous certification.',
        'collisions':collisions,'neutral_short_gaps_m':min_gaps,
        'floor_intrusions':floor_intrusions,'stroke_violations':stroke_violations,
        'pose_scope':'prescribed grounded crouch path; root relocation is geometric FK, not dynamic support' if GROUNDED else 'independent stress probes, NOT accepted motion limits',
        'same_body_steel_connected':{b:inertia[b]['steel_positive_material_components']==1 for b in inertia},
        'contact_cases':cases,'contact_vertices_xy_m':contacts.tolist(),'neutral_required_moments':demands,
        'pressure_case_assumption':{'provisional_upperbody_self_mass_allowance_kg':2200,'provisional_per_leg_mass_allowance_kg':800,'external_downforce_mass_equivalent_kg':3000,'force_factor':1.5,
                                   'not_actual_mass_or_payload_qualification':True},
        'dynamic_steps':0,'physical_accepted':False,'elapsed_seconds':time.time()-t0}
    report['neutral_ground_min_z_m']=min(np.array(p['vertices_world_m'])[:,2].min() for p in S['parts'])
    report['source_file']=SOURCE.name
    report['scope']='Finite frame and custom drive/mount candidate. Source identifies missing/unqualified parts. NO pressure-part qualification, finite-element strength, wholebody contact dynamics or hardware acceptance.'
    destination='assembly_rejection_report.json' if S.get('drivers') else 'geometry_and_statics_report.json'
    if GROUNDED:destination='assembly_grounded_path_report.json' if S.get('drivers') else 'frame_grounded_path_report.json'
    (OUT/destination).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('DONE probes',len(probes),'collisions',len(collisions),'mass',sum(mass.values()),flush=True)

if __name__=='__main__':run()
