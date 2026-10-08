"""Native material collision replay of sampled free-base dynamic states."""
from pathlib import Path
import json,hashlib,time
import numpy as np
from check_candidate import solid

O=Path(__file__).resolve().parent;P=O/'assembled_scene.json';S=json.loads(P.read_text())
R=json.loads((O/'loaded_leg_probe_report.json').read_text());sha=hashlib.sha256(P.read_bytes()).hexdigest()
assert R['source_sha256']==sha
base={p['name']:solid(p) for p in S['parts']};pairs=[(a,b) for i,a in enumerate(S['parts']) for b in S['parts'][i+1:] if a['body']!=b['body']]
hits=[];floor=[];minpad=0.;start=time.time()
for i,state in enumerate(R['snapshots']):
    T={b:np.array(t) for b,t in state['transforms'].items()}
    mats={p['name']:base[p['name']].transform(T[p['body']][:3,:4].copy()) for p in S['parts']}
    bounds={n:np.array(m.bounding_box()).reshape(2,3) for n,m in mats.items()}
    for p in S['parts']:
        z=float(bounds[p['name']][0,2])
        if p['role']=='contact_pad':minpad=min(minpad,z)
        elif z<-1e-8:floor.append({'sample':i,'case':state['case'],'time_s':state['time_s'],'part':p['name'],'minimum_z_m':z})
    for a,b in pairs:
        aa,bb=bounds[a['name']],bounds[b['name']]
        if np.any(aa[1]<bb[0]) or np.any(bb[1]<aa[0]):continue
        v=float((mats[a['name']]^mats[b['name']]).volume())
        if v>1e-10:hits.append({'sample':i,'case':state['case'],'time_s':state['time_s'],'a':a['name'],'b':b['name'],'intersection_cm3':v*1e6})
    if i%40==0:print('DYNAMIC MATERIAL',i,'/',len(R['snapshots']),'hits',len(hits),flush=True)
out={'source_sha256':sha,'dynamic_report_sha256':hashlib.sha256((O/'loaded_leg_probe_report.json').read_bytes()).hexdigest(),
     'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'sampled_states':len(R['snapshots']),
     'collisions':hits,'non_pad_floor_intrusions':floor,'minimum_pad_z_m':minpad,
     'scope':'Finite material replay of every sampled body state, all different-owner pairs. Pads have numerical contact penetration; uncalibrated rigid contact is NOT an elastic pad validation. Samples NOT continuous time proof.',
     'physical_accepted':False,'elapsed_seconds':time.time()-start}
(O/'loaded_material_replay_report.json').write_text(json.dumps(out,indent=2)+'\n')
print('MATERIAL DONE',len(hits),'collisions',len(floor),'nonpad floor hits','pad z',minpad,flush=True)
