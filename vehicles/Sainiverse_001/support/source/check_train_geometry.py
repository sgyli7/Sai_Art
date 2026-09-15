"""Actual three-module mesh packaging and offset-axis kinematic screening.

This is a discrete surface-intersection test, not a continuous or structural
certificate. Bogies stay in their nominal suspension/steering pose.
"""
from pathlib import Path
import argparse,gzip,hashlib,itertools,json,time
import numpy as np
import trimesh as tm
import mujoco
from articulation_geometry import poses
from train_physics import build

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'candidates/r016_modular/train'
KEYS=['front','hitch_slide','hitch_yaw','hitch_pitch','rear',
      'tail_hitch_slide','tail_hitch_yaw','tail_hitch_pitch','tail']

def transforms(first,second):
    a=poses(first[0],*np.radians(first[1:]));b=poses(second[0],*np.radians(second[1:]))
    shift=tm.transformations.translation_matrix([-42,0,0])
    out=dict(a)
    for g in ['hitch_slide','hitch_yaw','hitch_pitch','rear']:
        out['tail' if g=='rear' else 'tail_'+g]=a['rear']@shift@b[g]@np.linalg.inv(shift)
    return out

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--containers-first',action='store_true');args=parser.parse_args()
    if args.containers_first:OUT=ROOT/'candidates/r016_modular/train_containers_first'
    started=time.monotonic();source=OUT/'source/assembly.json.gz'
    assembly=json.loads(gzip.decompress(source.read_bytes()));by_name={p['name']:p for p in assembly['parts']}
    model_report=json.loads((OUT/'reports/model.json').read_text())
    registry_data=json.loads((OUT/'source/payload_registry.json').read_text())
    container_group=next(m['name'] for m in registry_data['common_module_instances'] if m['payload']=='container_cargo')
    if 'common_clone_map' not in model_report:
        model_report['common_clone_map']=json.loads((ROOT/'candidates/r016_modular/train/reports/model.json').read_text())['common_clone_map']
    clone_errors=[]
    for dst,src in model_report['common_clone_map'].items():
        a,b=by_name[dst],by_name[src]
        if (a['faces']!=b['faces'] or a['material']!=b['material'] or
            np.max(abs(np.array(a['vertices'])-np.array(b['vertices'])-[-42,0,0]))>1e-10):clone_errors.append(dst)
    managers={g:tm.collision.CollisionManager() for g in KEYS};names={g:[] for g in KEYS};group_meshes={g:[] for g in KEYS}
    payload=tm.collision.CollisionManager();common=tm.collision.CollisionManager()
    for p in assembly['parts']:
        if p['surface_paint']:continue
        group=p['group'] if p['group'] in KEYS else p['group'].split('_')[0]
        mesh=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
        managers[group].add_object(p['name'],mesh);names[group].append(p['name'])
        group_meshes[group].append(mesh)
        if p['group']==container_group:
            if p['assembly'].startswith('container_'):payload.add_object(p['name'],mesh)
            elif p['assembly'] not in ['cargo_locks','cargo_sockets']:common.add_object(p['name'],mesh)
    cargo_hit,cargo_pairs=payload.in_collision_other(common,return_names=True)
    # All groups move rigidly in this nominal-bogie screen. Concatenating their
    # original triangles preserves the surface test while avoiding 20k per-part
    # transform updates at every pose. Resolve original names only upon a hit.
    bulk={g:tm.collision.CollisionManager() for g in KEYS}
    for g in KEYS:bulk[g].add_object(g,tm.util.concatenate(group_meshes[g]))
    # Verify the composed mesh transform against the actual MuJoCo joint tree.
    xml,manifest=build(out=OUT);m=mujoco.MjModel.from_xml_path(str(xml));d=mujoco.MjData(m)
    joint_ids=[mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,n) for n in manifest['hitch_joints']]
    body_ids={g:mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,g) for g in KEYS}
    # The ground-dynamics initialization lowers the entire train by 0.21 m.
    # Compare kinematics in the authored neutral world, with root Z = 10 m;
    # otherwise rotations incorrectly use an unshifted mesh bearing axis.
    d.qpos[2]=10.
    mujoco.mj_forward(m,d);neutral={g:d.xpos[bid].copy() for g,bid in body_ids.items()}
    zero=(0.,0.,0.,0.);cases={(zero,zero)}
    angles=list(dict.fromkeys([(y,0,0) for y in range(-30,31,5)]+list(itertools.product([-30,0,30],[-8,0,8],[-6,0,6]))))
    for angleset in angles:
        pose=(0.,*angleset);cases.add((pose,zero));cases.add((zero,pose))
    # C-turn, S-turn, opposed/same pitch and roll on both actual couplers.
    for y1,y2,p1,p2,r1,r2 in itertools.product([-30,30],[-30,30],[-8,8],[-8,8],[-6,6],[-6,6]):
        cases.add(((0.,y1,p1,r1),(0.,y2,p2,r2)))
    for e1,e2,y1,y2 in itertools.product([0.,4.],[0.,4.],[-30,30],[-30,30]):
        cases.add(((e1,y1,0.,0.),(e2,y2,0.,0.)))
    results=[];position_error=0.;basis_error=0.
    for i,(a,b) in enumerate(sorted(cases)):
        ts=transforms(a,b);d.qpos[:]=m.qpos0;d.qpos[2]=10.
        for jid,q in zip(joint_ids,[a[0],*np.radians(a[1:]),b[0],*np.radians(b[1:])]):d.qpos[m.jnt_qposadr[jid]]=q
        mujoco.mj_forward(m,d)
        for g in KEYS:
            position_error=max(position_error,float(np.max(abs((ts[g]@np.r_[neutral[g],1])[:3]-d.xpos[body_ids[g]]))))
            basis_error=max(basis_error,float(np.max(abs(ts[g][:3,:3]-d.xmat[body_ids[g]].reshape(3,3)))))
            bulk[g].set_transform(g,ts[g])
        pairs=[]
        for j,g in enumerate(KEYS):
            for h in KEYS[j+1:]:
                if bulk[g].in_collision_other(bulk[h]):
                    for key in [g,h]:
                        for name in names[key]:managers[key].set_transform(name,ts[key])
                    hit,found=managers[g].in_collision_other(managers[h],return_names=True)
                    assert hit,'Grouped triangles and per-part surface result disagree.'
                    pairs.extend(sorted(found))
        results.append(dict(first=list(a),second=list(b),intersections=pairs))
        if i%20==0:print('pose',i+1,'/',len(cases),'intersections',len(pairs),flush=True)
    registry=json.loads((OUT/'source/payload_registry.json').read_text())['containers']
    gauge_errors=[]
    for c in registry:
        verts=np.concatenate([p['vertices'] for p in assembly['parts'] if p['assembly']==c['id']]);center=np.array(c['center_source_m']);half=np.array(c['size_m'])/2
        if np.any(verts.min(0)<center-half-1e-8) or np.any(verts.max(0)>center+half+1e-8):gauge_errors.append(c['id'])
    result=dict(assembly_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        exact_common_clone_count=len(model_report['common_clone_map']),clone_errors=clone_errors,
        containers_with_geometry_inside_declared_gauge=len(registry)-len(gauge_errors),container_gauge_errors=gauge_errors,
        container_vs_common_surface_intersections=sorted(cargo_pairs),
        maximum_mesh_vs_mujoco_frame_position_error_m=position_error,maximum_mesh_vs_mujoco_frame_basis_error=basis_error,
        sampled_poses=len(results),failed_poses=sum(bool(x['intersections']) for x in results),samples=results,
        passed=not clone_errors and not gauge_errors and not cargo_hit and position_error<1e-8 and basis_error<1e-8 and not any(x['intersections'] for x in results),
        wall_seconds=time.monotonic()-started,
        scope='Actual three-section geometry, two offset-axis couplers, adjacent and non-adjacent groups. Discrete surface screening only, nominal bogies and stowed cranes; not containment, continuous clearance, suspension extremes, load handling or structural qualification. Cargo locks/sockets excluded from cargo/common check because they intentionally connect payload to deck.')
    (OUT/'reports/geometry_screen.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))
    raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':main()
