from pathlib import Path
import json, struct, math
import numpy as np
from scipy.spatial import cKDTree
root=Path(__file__).resolve().parents[1]
b=(root/'generated/reference_raw_geometry_00001_.glb').read_bytes()
jlen,jtype=struct.unpack_from('<II',b,12);g=json.loads(b[20:20+jlen]);binstart=28+jlen
p=g['meshes'][0]['primitives'][0];a=g['accessors'][p['attributes']['POSITION']];v=g['bufferViews'][a['bufferView']]
raw=np.frombuffer(b,dtype=np.float32,count=a['count']*3,offset=binstart+v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,3)
c=np.stack([raw[:,0],-raw[:,2],raw[:,1]],axis=1)
fov=24.84635563433873;t=math.tan(math.radians(fov)/2);dist=.5/t
uv=np.stack([512+512/t*c[:,0]/(dist+c[:,1]),512-512/t*c[:,2]/(dist+c[:,1])],axis=1)
idx=np.arange(0,len(c),8);tree=cKDTree(uv[idx]);out=[]
for name,pt in [('near_shoulder',(290,160)),('far_shoulder',(770,168)),('torso_top_near',(395,60)),('torso_top_far',(703,83)),('front_tip',(650,399)),('lamp',(665,323)),('near_radiator',(445,217)),('far_radiator',(720,252)),('pelvis',(597,506)),('near_knee',(395,670)),('far_knee',(790,655)),('near_ankle',(348,911)),('far_ankle',(751,918)),('near_wrist',(292,455)),('far_wrist',(849,660)),('near_rifle',(288,723)),('far_foot',(750,954))]:
    ix=tree.query_ball_point(pt,6);sel=idx[ix];pos=c[sel]
    if len(pos)==0: continue
    # Frontmost surface in a small projection ROI.
    pos=pos[np.argsort(pos[:,1])[:max(1,len(pos)//5)]]
    point=np.median(pos,axis=0)
    print(name,'%.4f %.4f %.4f'%tuple(point), 'projected',uv[sel].mean(axis=0).round(1).tolist())
    out.append({'name':name,'pixel':pt,'native_point':point.tolist()})
(root/'source/reference_feature_points.json').write_text(json.dumps({'camera_fov':fov,'perspective_distance':dist,'points':out},indent=2)+'\n')
np.savez_compressed(root/'source/raw_vertex_sample.npz',vertices=c[::8],uv=uv[::8])
