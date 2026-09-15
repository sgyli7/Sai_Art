"""Candidate solids, named physical frames and discrete motion checks."""
from pathlib import Path
import gzip,json,hashlib,itertools,math
import numpy as np
import trimesh as tm
import mujoco
from articulation_geometry import poses,GROUPS,YAW,PITCH,ROLL

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'candidates/r015_articulation'
path=OUT/'source/assembly.json.gz';a=json.loads(gzip.decompress(path.read_bytes()))
keys=['front','hitch_slide','hitch_yaw','hitch_pitch','rear']
man={g:tm.collision.CollisionManager() for g in keys};names={g:[] for g in keys};meshes={};new={g:[] for g in keys}
for p in a['parts']:
    if p['surface_paint']:continue
    g=p['group'] if p['group'] in keys else 'front' if p['group'].startswith('front') else 'rear'
    m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
    man[g].add_object(p['name'],m);names[g].append(p['name']);meshes[p['name']]=m
    if p['assembly']=='articulation_r015':
        assert m.is_volume,p['name'];new[g].append(m)

# All three moving carrier assemblies must be mechanically connected solids.
connected={}
for g in ['hitch_slide','hitch_yaw','hitch_pitch']:
    union=tm.boolean.union(new[g],engine='manifold')
    pieces=union.split(only_watertight=False)
    connected[g]=dict(components=len(pieces),volume_m3=float(union.volume))
    assert len(pieces)==1,(g,'disconnected carrier assembly',len(pieces))

m=mujoco.MjModel.from_xml_path(str(ROOT/'reports/articulation_r015/bench/fixture.xml'));d=mujoco.MjData(m)
native={'hitch_slide':'extension_body','hitch_yaw':'yaw_body','hitch_pitch':'pitch_body','rear':'roll_body'}
mujoco.mj_forward(m,d)
neutral={}
for g,name in native.items():
    body=m.body(name).id;tr=np.eye(4);tr[:3,:3]=d.xmat[body].reshape(3,3);tr[:3,3]=d.xpos[body];neutral[g]=tr

cases=[(float(e),0,0,0) for e in np.arange(0,4.01,.25)]
cases += [(4,float(y),0,0) for y in range(-45,46,3)]
cases += [(4,float(y),float(p),float(r)) for y,p,r in itertools.product((-45,0,45),(-8,0,8),(-6,0,6))]
cases=list(dict.fromkeys(cases));results=[];max_frame_error=0.
for extension,yaw,pitch,roll in cases:
    angles=np.radians([yaw,pitch,roll]);transforms=poses(extension,*angles)
    d.qpos[:]=[extension,*angles];mujoco.mj_forward(m,d)
    for g,name in native.items():
        body=m.body(name).id;tr=np.eye(4);tr[:3,:3]=d.xmat[body].reshape(3,3);tr[:3,3]=d.xpos[body]
        expected=transforms[g]@neutral[g]
        max_frame_error=max(max_frame_error,float(np.abs(tr-expected).max()))
    for g in keys:
        for name in names[g]:man[g].set_transform(name,transforms[g])
    pairs=[]
    for i,g in enumerate(keys):
        for h in keys[i+1:]:
            collision,found=man[g].in_collision_other(man[h],return_names=True)
            pairs+=sorted(found)
    results.append(dict(extension_m=extension,yaw_deg=yaw,pitch_deg=pitch,roll_deg=roll,intersections=pairs))
    if pairs:print('INTERSECTION',results[-1],flush=True)
assert max_frame_error<1e-8,('visual/native frame mismatch',max_frame_error)
report=dict(passed=not any(row['intersections'] for row in results),
            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),carrier_connectivity=connected,
            physical_axes_m={'yaw':YAW.tolist(),'pitch':PITCH.tolist(),'roll':ROLL.tolist()},
            native_mujoco_transform_max_abs_error=max_frame_error,samples=results,
            minimum_full_extension_sleeve_overlap_m=1.7,
            scope='Actual closed carrier solids and whole-model discrete surface intersection screen; '
                  'includes extension sequence, yaw and combined angles. FCL surface queries do not prove '
                  'containment absence or continuous swept clearance. Native forward kinematics match '
                  'authored body transforms; this is not full-vehicle road dynamics or structural qualification.')
(OUT/'reports/geometry_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
raise SystemExit(0 if report['passed'] else 1)
