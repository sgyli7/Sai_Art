"""Actual 3D unloaded crouch path, sole fixed by FK/root displacement.

This checks reach and finite material, not loads or a dynamic controller.
Hip pitch is an uninstalled interface DOF. No hidden root support is claimed:
root displacement is a geometric consequence of keeping the sole planted.
"""
from pathlib import Path
import json,hashlib,math
import numpy as np
import trimesh as tr
import manifold3d as mf

O=Path(__file__).resolve().parent;P=O/'candidate_scene.json';S=json.loads(P.read_text())
def M(p):return mf.Manifold(mf.Mesh64(np.array(p['vertices_world_m'],dtype=np.float64,order='C'),np.array(p['faces'],dtype=np.uint64,order='C')))
base={p['name']:M(p) for p in S['parts']}
anchor=np.array(S['stations_world_m']['ankle']);hip=np.array(S['stations_world_m']['hip'])
poses=[];hits=[];lowest=[]
for k,t in enumerate(np.linspace(0,1,121)):
    # Reference -> additional deep crouch. Foot angle remains exactly zero.
    h=S['crouch_hip_pitch_deg']*t;q=(np.array(S['crouch_joint_deltas_deg'])*t).tolist()
    T={'thigh':tr.transformations.rotation_matrix(math.radians(h),[0,1,0],hip)}
    for j,a in zip(S['joints'],q):T[j['child']]=T[j['parent']]@tr.transformations.rotation_matrix(math.radians(a),[0,1,0],j['center'])
    moved=(T['shoe']@np.r_[anchor,1])[:3];shift=anchor-moved
    for b in T:T[b][:3,3]+=shift
    root=(T['thigh']@np.r_[hip,1])[:3]
    foot_err=float(np.max(np.abs(T['shoe']-np.eye(4))))
    solids={p['name']:base[p['name']].transform(T[p['body']][:3,:4].copy()) for p in S['parts']}
    bounds={n:np.array(m.bounding_box()).reshape(2,3) for n,m in solids.items()}
    minimum=min(bb[0,2] for bb in bounds.values());lowest.append(minimum)
    for i,a in enumerate(S['parts']):
        for b in S['parts'][i+1:]:
            if a['body']==b['body']:continue
            aa,bb=bounds[a['name']],bounds[b['name']]
            if np.any(aa[1]<bb[0]) or np.any(bb[1]<aa[0]):continue
            volume=(solids[a['name']]^solids[b['name']]).volume()
            if volume>1e-10:hits.append({'sample':k,'a':a['name'],'b':b['name'],'intersection_cm3':volume*1e6})
    poses.append({'sample':k,'hip_pitch_deg':h,'joint_deltas_deg':q,'hip_world_m':root.tolist(),
                  'foot_transform_identity_max_error':foot_err,'body_transforms':{b:T[b].tolist() for b in T}})
r={'source_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
   'pose_samples':121,'collisions':hits,'minimum_native_z_m':min(lowest),'maximum_foot_transform_error':max(p['foot_transform_identity_max_error']for p in poses),
   'reference_hip_height_m':poses[0]['hip_world_m'][2],'deep_crouch_hip_height_m':poses[-1]['hip_world_m'][2],
   'actual_native_geometry_used':True,'poses':poses,'physical_accepted':False,'dynamic_steps':0,
   'scope':'Finite frame/contact-surface geometry only. Stance reach and rooted FK are not a loaded physical acceptance. Drivers, installed hip, armor, opposite leg and upperbody excluded; assembly_rejection_report.json remains rejected.'}
(O/'grounded_crouch_report.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
print('CROUCH',r['reference_hip_height_m'],'->',r['deep_crouch_hip_height_m'],'collision_count',len(hits),'foot_error',r['maximum_foot_transform_error'],flush=True)
