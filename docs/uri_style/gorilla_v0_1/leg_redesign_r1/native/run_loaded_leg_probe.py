"""Free-base single-leg bench probe with source-installed slider force paths.

The 6000kg virtual load fixture is an explicit provisional bench load, NOT a
real upperbody, opposite leg or rated payload. Only the finite convex pads
contact the floor. Frame interference is separately checked with native CSG.
No world weld, prescribed root force, main-joint torque motor or gravity comp.
"""
from pathlib import Path
import json,hashlib,math,xml.etree.ElementTree as ET
import numpy as np
import trimesh as tr
import manifold3d as mf
import mujoco as mj
from check_candidate import solid

O=Path(__file__).resolve().parent;P=O/'assembled_scene.json';S=json.loads(P.read_text())
SHA=hashlib.sha256(P.read_bytes()).hexdigest()
C=json.loads((O/'assembly_grounded_path_report.json').read_text())
assert C['source_sha256']==SHA and not C['collisions'] and not C['floor_intrusions'] and not C['stroke_violations']
assert all(C['same_body_steel_connected'].values())
DIR=O/'loaded_probe_meshes';DIR.mkdir(exist_ok=True)
def fmt(v):return ' '.join(f'{float(x):.12g}' for x in np.ravel(v))
def element(parent,tag,**attrs):return ET.SubElement(parent,tag,{k:fmt(v) if isinstance(v,(list,tuple,np.ndarray)) else str(v) for k,v in attrs.items()})
def mesh(m):
    q=m.to_mesh64();return tr.Trimesh(np.array(q.vert_properties[:,:3]),np.array(q.tri_verts),process=False)
groups={}
for p in S['parts']:groups.setdefault(p['body'],[]).append(p)
mass={};com={};inertia={}
for owner,parts in groups.items():
    buckets={}
    for p in parts:
        density=p['density_kg_m3'];buckets[density]=buckets.get(density,mf.Manifold())+solid(p)
    props=[]
    for density,m in buckets.items():
        mm=mesh(m);mm.density=density;props.append(mm.mass_properties)
    mass[owner]=sum(p.mass for p in props);com[owner]=sum(p.mass*p.center_mass for p in props)/mass[owner]
    inertia[owner]=sum(p.inertia+p.mass*((np.dot(p.center_mass-com[owner],p.center_mass-com[owner])*np.eye(3))-np.outer(p.center_mass-com[owner],p.center_mass-com[owner])) for p in props)
H=np.array(S['stations_world_m']['hip']);origins={'thigh':H};rotations={k:np.eye(3) for k in ('thigh','middle','distal','shoe')}
for j in S['joints']:origins[j['child']]=np.array(j['center'])
for d in S['drivers']:
    A=np.array(d['A_neutral_world_m']);B=np.array(d['B_neutral_world_m']);R=tr.geometry.align_vectors([0,0,1],(B-A)/np.linalg.norm(B-A))[:3,:3]
    for body,p in ((d['barrel_body'],A),(d['rod_body'],B)):origins[body]=p;rotations[body]=R
root=ET.Element('mujoco',model='Gorilla finite leg provisional loaded probe')
element(root,'compiler',angle='radian',inertiafromgeom='false',alignfree='false')
element(root,'option',timestep='.0002',gravity=[0,0,-9.81*1.5],integrator='implicitfast',solver='Newton',iterations='100',tolerance='1e-10',cone='elliptic')
assets=element(root,'asset');world=element(root,'worldbody')
element(world,'geom',name='floor',type='plane',size=[5,5,.1],friction=[.8,.01,.001],solref=[.004,1],solimp=[.95,.99,.001],condim='3')
nodes={};nodes['thigh']=element(world,'body',name='thigh',pos=H)
element(nodes['thigh'],'freejoint',name='free_root')
for j in S['joints']:
    n=element(nodes[j['parent']],'body',name=j['child'],pos=origins[j['child']]-origins[j['parent']]);nodes[j['child']]=n
    element(n,'joint',name=j['id'],type='hinge',axis=[0,1,0],damping='10',limited='false')
fixture=element(nodes['thigh'],'body',name='virtual_load_fixture',pos=[0,0,0])
element(fixture,'inertial',pos=[0,0,0],mass='6000',diaginertia=[400,400,400])
element(fixture,'site',name='fixture_point',size='.02',rgba=[1,.4,.05,1])
eq=element(root,'equality');acts=element(root,'actuator')
for d in S['drivers']:
    A=np.array(d['A_neutral_world_m']);B=np.array(d['B_neutral_world_m']);R=rotations[d['barrel_body']]
    quat=tr.transformations.quaternion_from_matrix(np.block([[R,np.zeros((3,1))],[np.zeros((1,3)),np.ones((1,1))]]))
    n=element(nodes[d['parent']],'body',name=d['barrel_body'],pos=A-origins[d['parent']],quat=quat);nodes[d['barrel_body']]=n
    element(n,'joint',name=d['id']+'_swing',type='hinge',axis=R.T@np.array([0,1,0]),damping='.05',limited='false')
    rn=element(n,'body',name=d['rod_body'],pos=R.T@(B-A));nodes[d['rod_body']]=rn
    lo,hi=np.array(d['eye_length_limits_m'])-d['neutral_eye_length_m']
    element(rn,'joint',name=d['id']+'_slide',type='slide',axis=[0,0,1],range=[lo,hi],damping='100',solreflimit=[.002,1])
    element(rn,'site',name=d['id']+'_rod_eye',pos=[0,0,0],size='.003')
    element(nodes[d['child']],'site',name=d['id']+'_mount_eye',pos=B-origins[d['child']],size='.003')
    element(eq,'connect',name=d['id']+'_closure',site1=d['id']+'_rod_eye',site2=d['id']+'_mount_eye',solref=[.002,1],solimp=[.99,.999,.0001])
    pull=d['efficiency_assumption']*d['pressure_assumption_Pa']*math.pi*(d['bore_m']**2-d['rod_m']**2)/4
    push=d['efficiency_assumption']*d['pressure_assumption_Pa']*math.pi*d['bore_m']**2/4
    element(acts,'motor',name=d['id']+'_force',joint=d['id']+'_slide',gear='1',ctrllimited='true',ctrlrange=[-pull,push])
for owner,parts in groups.items():
    n=nodes[owner];R=rotations[owner];I=R.T@inertia[owner]@R
    element(n,'inertial',pos=R.T@(com[owner]-origins[owner]),mass=f'{mass[owner]:.12g}',fullinertia=[I[0,0],I[1,1],I[2,2],I[0,1],I[0,2],I[1,2]])
    for p in parts:
        v=(np.array(p['vertices_world_m'])-origins[owner])@R
        name=p['name'];tr.Trimesh(v,np.array(p['faces']),process=False).export(DIR/(name+'.stl'))
        element(assets,'mesh',name=name,file=str(DIR/(name+'.stl')))
        contact=p['role']=='contact_pad'
        element(n,'geom',name=name,type='mesh',mesh=name,rgba=p['rgba'],contype='1' if contact else '0',conaffinity='1' if contact else '0',friction=[.8,.01,.001],solref=[.004,1],solimp=[.95,.99,.001],condim='3')
XML=O/'loaded_leg_probe.xml';ET.indent(root);XML.write_text(ET.tostring(root,encoding='unicode')+'\n')
M=mj.MjModel.from_xml_path(str(XML));data=mj.MjData(M)
qids={j['id']:mj.mj_name2id(M,mj.mjtObj.mjOBJ_JOINT,j['id']) for j in S['joints']}
slides=[mj.mj_name2id(M,mj.mjtObj.mjOBJ_JOINT,d['id']+'_slide') for d in S['drivers']]
swings=[mj.mj_name2id(M,mj.mjtObj.mjOBJ_JOINT,d['id']+'_swing') for d in S['drivers']]
def fk(q):
    T={'thigh':np.eye(4)}
    for j,r in zip(S['joints'],q):T[j['child']]=T[j['parent']]@tr.transformations.rotation_matrix(r,[0,1,0],j['center'])
    R=tr.transformations.rotation_matrix(-sum(q),[0,1,0],H);ank=np.array(S['stations_world_m']['ankle']);moved=(R@T['shoe']@np.r_[ank,1])[:3];R[:3,3]+=ank-moved
    T={body:R@t for body,t in T.items()};length=[];swing=[]
    for d in S['drivers']:
        A=np.array(d['A_neutral_world_m']);B=np.array(d['B_neutral_world_m'])
        aa=(T[d['parent']]@np.r_[A,1])[:3];bb=(T[d['child']]@np.r_[B,1])[:3]
        v=(bb-aa)/np.linalg.norm(bb-aa);Rot=tr.geometry.align_vectors((B-A)/np.linalg.norm(B-A),v)[:3,:3]
        for body,now,old in ((d['barrel_body'],aa,A),(d['rod_body'],bb,B)):
            t=np.eye(4);t[:3,:3]=Rot;t[:3,3]=now-Rot@old;T[body]=t
        length.append(np.linalg.norm(bb-aa))
        # Relative parent-cylinder Y angle from the actual two eye positions.
        vv=T[d['parent']][:3,:3].T@v;un=(B-A)/np.linalg.norm(B-A)
        swing.append(math.atan2(vv[0],vv[2])-math.atan2(un[0],un[2]))
    return T,np.array(length),np.array(swing)
def potential(q):
    T,_,_=fk(q)
    return 14.715*(sum(mass[b]*(T[b]@np.r_[com[b],1])[2] for b in mass)+6000*(T['thigh']@np.r_[H,1])[2])
def commands(q):
    T,L,_=fk(q);f=np.zeros(len(S['drivers']));h=1e-5
    for i,j in enumerate(S['joints']):
        qq=q.copy();qq[i]+=h;up=potential(qq);lp=fk(qq)[1];qq[i]-=2*h;dn=potential(qq);ln=fk(qq)[1]
        tau=(up-dn)/(2*h)
        ids=np.array([k for k,d in enumerate(S['drivers'])if d['joint']==j['id']],dtype=int)
        if len(ids)==0:raise ValueError(('unactuated main joint',j['id']))
        arms=(lp[ids]-ln[ids])/(2*h)
        if arms@arms<1e-12:raise ValueError(('singular cylinder geometry',j['id']))
        # Actual installed pressure areas and number of cylinders are used.
        # Minimum-norm equal-pair load sharing reduces to tau/(2*arm) for
        # twins, and tau/arm for the single central ankle drive.
        f[ids]=tau*arms/(arms@arms)
    return L,f
table=[]
for t in np.linspace(0,1,121):
    q=np.deg2rad(np.array(S['crouch_joint_deltas_deg'])*t);L,f=commands(q);table.append([t,*L,*f])
table=np.array(table)
results=[];snapshots=[]
for name,phase,duration in [('reference_hold',0.,2.),('deep_crouch_hold',1.,2.),('loaded_crouch_motion',None,4.)]:
    mj.mj_resetData(M,data);initial=0 if phase is None else phase;q=np.deg2rad(np.array(S['crouch_joint_deltas_deg'])*initial);T,L,sw=fk(q)
    data.qpos[:3]=(T['thigh']@np.r_[H,1])[:3]
    data.qpos[3:7]=tr.transformations.quaternion_from_matrix(T['thigh'])
    for j,r in zip(S['joints'],q):data.qpos[M.jnt_qposadr[qids[j['id']]]]=r
    for k,d in enumerate(S['drivers']):
        data.qpos[M.jnt_qposadr[slides[k]]]=L[k]-d['neutral_eye_length_m'];data.qpos[M.jnt_qposadr[swings[k]]]=sw[k]
    mj.mj_forward(M,data)
    maxqerror=0.;maxclosure=0.;maxforce_ratio=0.;maxrootdrift=0.;minpadz=0.;bad=False;trace=[]
    for step in range(round(duration/M.opt.timestep)):
        tt=data.time;t=phase if phase is not None else .5-.5*math.cos(math.pi*min(tt/3,1))
        count=len(S['drivers'])
        lengths=np.array([np.interp(t,table[:,0],table[:,1+k]) for k in range(count)])
        ff=np.array([np.interp(t,table[:,0],table[:,1+count+k]) for k in range(count)])
        for k,d in enumerate(S['drivers']):
            actual=data.qpos[M.jnt_qposadr[slides[k]]]+d['neutral_eye_length_m'];speed=data.qvel[M.jnt_dofadr[slides[k]]]
            raw=ff[k]+80e6*(lengths[k]-actual)-2e5*speed
            data.ctrl[k]=np.clip(raw,*M.actuator_ctrlrange[k]);maxforce_ratio=max(maxforce_ratio,abs(raw)/abs(M.actuator_ctrlrange[k,0 if raw<0 else 1]))
        mj.mj_step(M,data)
        if not np.isfinite(data.qpos).all() or any(w.number for w in data.warning):bad=True;break
        if step%50==0:
            target=np.deg2rad(np.array(S['crouch_joint_deltas_deg'])*t);actual=np.array([data.qpos[M.jnt_qposadr[qids[j['id']]]] for j in S['joints']]);err=np.max(np.abs(actual-target))*180/math.pi
            maxqerror=max(maxqerror,float(err));expected=fk(target)[0];hip=(expected['thigh']@np.r_[H,1])[:3];maxrootdrift=max(maxrootdrift,float(np.linalg.norm(data.qpos[:3]-hip)))
            closure=max(np.linalg.norm(data.site_xpos[mj.mj_name2id(M,mj.mjtObj.mjOBJ_SITE,d['id']+'_rod_eye')]-data.site_xpos[mj.mj_name2id(M,mj.mjtObj.mjOBJ_SITE,d['id']+'_mount_eye')]) for d in S['drivers']);maxclosure=max(maxclosure,float(closure))
            reaction=np.zeros(3)
            for ci in range(data.ncon):
                cf=np.zeros(6);mj.mj_contactForce(M,data,ci,cf);reaction+=np.array(data.contact[ci].frame).reshape(3,3).T@cf[:3]
            trace.append({'time_s':float(data.time),'phase':float(t),'joint_error_deg':float(err),'hip_world_m':data.qpos[:3].tolist(),'closure_error_m':float(closure),'contact_count':int(data.ncon),'reaction_world_N':reaction.tolist(),'actuator_force_N':data.actuator_force.tolist()})
        if step%500==0:
            transforms={}
            for b in mass:
                bid=mj.mj_name2id(M,mj.mjtObj.mjOBJ_BODY,b);Rworld=data.xmat[bid].reshape(3,3)@rotations[b].T;tworld=data.xpos[bid]-Rworld@origins[b]
                mat=np.eye(4);mat[:3,:3]=Rworld;mat[:3,3]=tworld;transforms[b]=mat.tolist()
            snapshots.append({'case':name,'time_s':float(data.time),'transforms':transforms})
    results.append({'case':name,'simulated_time_s':float(data.time),'steps':step+1,'max_joint_tracking_error_deg':maxqerror,'max_closure_error_m':maxclosure,
                    'max_root_reference_deviation_m':maxrootdrift,'max_requested_directional_force_ratio':maxforce_ratio,'solver_warning_or_nonfinite':bad,'trace':trace,
                    'physical_accepted':False})
    print(name,'steps',step+1,'qerror',maxqerror,'closure',maxclosure,'rootdeviation',maxrootdrift,'warnings',bad,flush=True)
report={'source_sha256':SHA,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'mjcf_sha256':hashlib.sha256(XML.read_bytes()).hexdigest(),
        'mujoco_version':mj.__version__,'native_leg_mass_kg':sum(mass.values()),'virtual_fixture_mass_kg':6000,'gravity_for_load_factor_m_s2':14.715,
        'root_free':True,'installed_cylinder_count':len(S['drivers']),
        'only_actuation':f"{len(S['drivers'])} bounded slider forces through source-installed point-closure cylinder mechanisms. No main-joint torque motors or world support.",
        'contact_scope':'Actual convex native pad meshes against floor ONLY. Structural holes are not convex collision proxies. All-frame material replay REQUIRED for dynamic snapshots.',
        'unqualified_assumptions':['6000kg virtual fixture, not actual upperbody/other leg/payload','custom pressure cylinders and seals/valves not qualified','steel7850/pad1100 assumed','rigid-body simulation has no stress/fatigue/thermal proof','numerical contact parameters not physical pad calibration'],
        'results':results,'dynamic_steps':sum(r['steps'] for r in results),'snapshots':snapshots,'physical_accepted':False}
(O/'loaded_leg_probe_report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
