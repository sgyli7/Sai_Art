"""Short rays on actual cabin contact geometry in each physical door state."""
import json
import numpy as np
import mujoco
from suspension_physics import ROOT

OUT=ROOT/'candidates/r025_access'

def definitions():
    access=json.loads((OUT/'source/access.json').read_text());rays=[]
    for d in access['doors']:
        for dx in [-.40,0.,.40]:
            for z in [11.60,12.10,13.65]:
                rays.append(dict(name=f"{d['name']}_{dx}_{z}",kind='door',body=d['name'],start=[d['center_x']+dx,d['side']*4.15,z],end=[d['center_x']+dx,d['side']*3.10,z]))
    for side in [-1,1]:
        for x in [20.5,22.,26.1]:
            rays.append(dict(name=f'wall_{side}_{x}',kind='wall',body='front',start=[x,side*3.90,11.85],end=[x,side*3.1,11.85]))
    for p in access['wall_contacts']:
        if p['name'].startswith('wall_piece'):continue
        v=np.array(p['vertices_source_m']);c=v.mean(0);_,_,vh=np.linalg.svd(v-c);n=vh[-1]
        rays.append(dict(name=p['name'],kind='window',body='front',start=(c+n*.12).tolist(),end=(c-n*.12).tolist()))
    return rays

def probe(env, rays):
    front=env.m.body('front').id;rot=env.d.xmat[front].reshape(3,3);datum=np.array(env.parameters['interior']['datum_source_m']) if hasattr(env,'parameters') else np.array([0.,0.,10.])
    group=np.zeros(6,np.uint8);group[4]=1;result=[]
    for ray in rays:
        start=env.d.xpos[front]+rot@(np.array(ray['start'])-datum);direction=rot@(np.array(ray['end'])-np.array(ray['start']));length=np.linalg.norm(direction);gid=np.array([-1],np.int32)
        distance=mujoco.mj_ray(env.m,env.d,start,direction/length,group,1,-1,gid);hit=0<=distance<=length
        body=env.m.body(int(env.m.geom_bodyid[gid[0]])).name if hit else ''
        result.append(dict(name=ray['name'],kind=ray['kind'],expected_body=ray['body'],hit=bool(hit),body=body,distance_m=float(distance) if hit else -1.))
    return dict(time=float(env.d.time),angles_rad=env.access.q.tolist(),rays=result)

if __name__=='__main__':
    (OUT/'source/access_probes.json').write_text(json.dumps(definitions(),indent=2)+'\n')
