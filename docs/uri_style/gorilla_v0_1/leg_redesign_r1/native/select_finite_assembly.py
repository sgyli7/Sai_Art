"""Reject finite cylinders AND mounts before picking a whole crouching leg.

Coarse rejection only. The separate 121-pose material checker remains required.
All different owners are tested. No collision exclusions or pose-limit claims.
"""
from pathlib import Path
import json,hashlib,itertools,collections
import numpy as np
import trimesh as tr
import manifold3d as mf
import assemble_drives as a
from check_candidate import solid

O=Path(__file__).resolve().parent
S=json.loads((O/'candidate_scene.json').read_text())
D=json.loads((O/'drive_floor_screen_options.json').read_text())
G=json.loads((O/'grounded_crouch_report.json').read_text())
assert D['scene_sha256']==G['source_sha256']==hashlib.sha256((O/'candidate_scene.json').read_bytes()).hexdigest()
indices=list(range(0,121,10));poses=[G['poses'][i] for i in indices]
base=[(p,solid(p)) for p in S['parts']]
def transformed(scene):
    materials=[(p,solid(p)) for p in scene['parts'][len(base):]]
    result=[]
    for pose in poses:
        T={k:np.array(t) for k,t in pose['body_transforms'].items()}
        for d in scene['drivers']:
            A=np.array(d['A_neutral_world_m']);B=np.array(d['B_neutral_world_m'])
            aa=(T[d['parent']]@np.r_[A,1])[:3];bb=(T[d['child']]@np.r_[B,1])[:3]
            R=tr.geometry.align_vectors((B-A)/np.linalg.norm(B-A),(bb-aa)/np.linalg.norm(bb-aa))[:3,:3]
            for body,now,old in ((d['barrel_body'],aa,A),(d['rod_body'],bb,B)):
                tt=np.eye(4);tt[:3,:3]=R;tt[:3,3]=now-R@old;T[body]=tt
        result.append([(p,m.transform(T[p['body']][:3,:4].copy())) for p,m in materials])
    return result
baseposes=[[(p,m.transform(np.array(pose['body_transforms'][p['body']])[:3,:4].copy())) for p,m in base] for pose in poses]
def collision(rows,other=None):
    allrows=rows+(other or [])
    bounds=[np.array(m.bounding_box()).reshape(2,3) for p,m in allrows]
    for i,(pa,ma) in enumerate(rows):
        if bounds[i][0,2]<-1e-8:return ('floor',pa['name'])
        for k in range(i+1,len(allrows)):
            pb,mb=allrows[k]
            if pa['body']==pb['body']:continue
            if np.any(bounds[i][1]<bounds[k][0]) or np.any(bounds[k][1]<bounds[i][0]):continue
            if (ma^mb).volume()>1e-10:return (pa['name'],pb['name'])
    return None
sets=[];counts=[]
for joint,options in enumerate(D['options']):
    keep=[];bad=collections.Counter()
    for n,opt in enumerate(options):
        own=[None]*3;own[joint]=opt;scene=a.build(own);rows=transformed(scene)
        fail=next((c for r,b in zip(rows,baseposes) if (c:=collision(r,b))),None)
        if fail:bad[fail]+=1
        else:keep.append((opt,rows,n))
        if n%20==0:print('FINITE',joint,n,'kept',len(keep),flush=True)
        if len(keep)>=12:break
    sets.append(keep);counts.append({'joint':joint,'checked':n+1 if options else 0,'retained':len(keep),'rejections':[{'pair':list(k),'count':v} for k,v in bad.items()]})
    print('JOINT DONE',joint,'kept',len(keep),flush=True)
selected=None;tried=0
for combo in itertools.product(*sets):
    tried+=1
    passed=True
    for phase in range(len(poses)):
        rows=sum([c[1][phase] for c in combo],[])
        if collision(rows):passed=False;break
    if passed:selected=combo;break
report={'scene_sha256':D['scene_sha256'],'selector_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'assembly_builder_sha256':hashlib.sha256(Path(a.__file__).read_bytes()).hexdigest(),
        'options_sha256':hashlib.sha256((O/'drive_floor_screen_options.json').read_bytes()).hexdigest(),
        'probe_indices':indices,'per_joint':counts,'complete_combinations_tried':tried,
        'selection_found':selected is not None,'physical_accepted':False}
(O/'finite_drive_selection_report.json').write_text(json.dumps(report,indent=2)+'\n')
if selected:
    out={'scene_sha256':D['scene_sha256'],'envelope_screen_sha256':hashlib.sha256((O/'drive_envelope_screen.json').read_bytes()).hexdigest(),
         'selection':{'options':[c[0] for c in selected],'indices':[c[2] for c in selected],'tested_pose_count':len(poses)},
         'method':'Actual finite material mounting/cylinder rejection at 13 prescribed grounded crouch poses. All different-body pairs; MUST recheck full 121 poses. No dynamic/strength acceptance.',
         'physical_accepted':False}
    (O/'drive_set_selection.json').write_text(json.dumps(out,indent=2)+'\n')
else:
    (O/'drive_set_selection.json').write_text(json.dumps({'scene_sha256':D['scene_sha256'],'selection':None,'physical_accepted':False,'status':'No finite assembly found. Previous selection invalidated; do not assemble.'},indent=2)+'\n')
print('FINITE SET',tried,'selected',selected is not None,flush=True)
