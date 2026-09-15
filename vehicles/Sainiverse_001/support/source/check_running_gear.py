"""Check shipped motion attributes, link grouping, orientation and native render regression."""
from pathlib import Path
import json,gzip,struct,hashlib,argparse
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--motion-report',default='motion_r005');args=parser.parse_args()
MOTION=ROOT/'reports'/args.motion_report
b=(ROOT/'assets/leviathan003.glb').read_bytes();size,_=struct.unpack_from('<II',b,12)
g=json.loads(b[20:20+size]);binary_start=28+size

def accessor(index):
    a=g['accessors'][index];v=g['bufferViews'][a['bufferView']]
    dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']]
    width={'VEC2':2,'VEC3':3,'SCALAR':1}[a['type']];unit=np.dtype(dtype).itemsize
    return np.ndarray((a['count'],width),dtype=dtype,buffer=b,offset=binary_start+v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',width*unit),unit))
counts={'static':0,'belt':0,'wheel':0}
for mesh in g['meshes']:
    for primitive in mesh['primitives']:
        uv=accessor(primitive['attributes']['TEXCOORD_0']);faces=accessor(primitive['indices']).ravel().reshape(-1,3)
        assert np.isfinite(uv).all() and set(np.unique(uv[:,1]))<={-1.,0.,1.}
        assert np.all(np.ptp(uv[faces],axis=1)<1e-6),f'Mixed motion within a triangle: {mesh["name"]}'
        for name,value in [('static',1),('belt',0),('wheel',-1)]:counts[name]+=int(np.count_nonzero(uv[:,1]==value))
        wi=uv[uv[:,1]==-1,0]
        assert np.all((wi>=0)&(wi<=4)&(wi==np.round(wi)))
        if '_bogie_' not in mesh['name']:assert np.all(uv[:,1]==1)
with gzip.open(ROOT/'source/assembly.json.gz','rt') as f:r=json.load(f)
gear=json.loads((ROOT/'assets/running_gear.json').read_text());path=np.array(gear['path_x_z']);closed=np.vstack([path,path[:1]])
lengths=np.linalg.norm(np.diff(closed,axis=0),axis=1);cum=np.r_[0,lengths.cumsum()];total=cum[-1]
assert abs(total-gear['perimeter'])<1e-6
rows=[]
for group,origin in r['groups'].items():
    if '_bogie_' not in group:continue
    parts=[p for p in r['parts'] if p['group']==group]
    wheels=[p for p in parts if p['name'].endswith('_road_wheel')]
    assert len(wheels)==20
    for i in range(5):assert len([p for p in wheels if p['motion']['index']==i])==4
    links=[p for p in parts if p['name'].endswith('_track_link')]
    cleats=[p for p in parts if p['name'].endswith('_track_cleat')]
    horns=[p for p in parts if p['name'].endswith('_track_guide_horn')]
    assert len(links)==len(cleats)==len(horns)==102
    for offset in (-1.75,1.75):
        belt=[p for p in links if abs(np.mean(p['vertices'],axis=0)[1]-origin[1]-offset)<1e-5]
        phases=np.sort([p['motion']['phase'] for p in belt]);spacing=np.diff(np.r_[phases,phases[0]+total])
        assert len(belt)==51 and np.ptp(spacing)<1e-6
    for collection,sign in [(cleats,1),(horns,-1)]:
        for p in collection:
            phase=p['motion']['phase'];k=min(len(lengths)-1,np.searchsorted(cum,phase,side='right')-1)
            tangent=(closed[k+1]-closed[k])/lengths[k];normal=np.array([-tangent[1],tangent[0]])
            q=closed[k]+tangent*(phase-cum[k]);center=np.mean(p['vertices'],axis=0)[[0,2]]-[origin[0],0]
            assert sign*np.dot(center-q,normal)>.1,'Cleat/horn faces wrong way: '+p['name']
    rows.append(dict(group=group,belts=2,links=102,paired_wheels=10,link_pitch_m=float(total/51)))
assert len(rows)==8
native=json.loads((MOTION/'native.json').read_text())
assert native['glb_sha256']==hashlib.sha256(b).hexdigest()
assert native['shader_sha256']==hashlib.sha256((ROOT/'godot/belt.gdshader').read_bytes()).hexdigest()
assert all(native['native_uv_vertices'].get(k,0)>0 for k in counts)
images={name:np.array(Image.open(MOTION/f'{name}.png').convert('RGB')).astype(int) for name in ('zero','forward','reverse','zero_repeat')}
# Actual wheel annuli and lower-belt crop must move; the fixed rail above must not.
crops={'wheel':(750,530,850,603),'belt':(700,619,900,647),'static_rail':(460,267,670,320)}
diffs={}
for name,(x0,y0,x1,y1) in crops.items():
    diffs[name]={key:float(np.abs(images[key][y0:y1,x0:x1]-images['zero'][y0:y1,x0:x1]).mean()) for key in ('forward','reverse','zero_repeat')}
    assert diffs[name]['zero_repeat']<.05
    if name=='static_rail':assert diffs[name]['forward']<.05 and diffs[name]['reverse']<.05
    else:assert diffs[name]['forward']>.5 and diffs[name]['reverse']>.5
report=dict(passed=True,glb_sha256=native['glb_sha256'],shader_sha256=native['shader_sha256'],vertices_by_motion=counts,bogies=rows,native_render_mean_pixel_change=diffs,scope='Visual topology and shipped native shader motion only. Wheels and belt links are not individual physical bodies; no drivetrain or hardware qualification.')
(ROOT/'reports/running_gear_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='bogies'},indent=2))
