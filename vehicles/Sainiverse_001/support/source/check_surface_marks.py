"""Check paint against host surfaces and separately validated layout translations."""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def recipe(path):
    with gzip.open(path,'rt') as f:return json.load(f)
new=recipe(ROOT/'source/assembly.json.gz')
# Layout translations are independently checked against r010 triangle surfaces.
layout=json.loads((ROOT/'reports/layout_validation.json').read_text())
assert layout['passed'] and layout['source_sha256']==hashlib.sha256((ROOT/'source/assembly.json.gz').read_bytes()).hexdigest()

def distances(points,host,side,normal=None):
    n=np.array(normal if normal is not None else [0,side,0],dtype=float);n/=np.linalg.norm(n)
    reference=np.eye(3)[np.argmin(np.abs(n))]
    u_axis=reference-n*np.dot(reference,n);u_axis/=np.linalg.norm(u_axis)
    basis=np.column_stack([u_axis,np.cross(n,u_axis)])
    tri=np.array(host['vertices'])[np.array(host['faces'])]
    a,b,c=tri[:,0],tri[:,1],tri[:,2]
    v0=(b-a)@basis;v1=(c-a)@basis
    det=v0[:,0]*v1[:,1]-v0[:,1]*v1[:,0]
    keep=abs(det)>1e-10;a,b,c,v0,v1,det=[q[keep] for q in (a,b,c,v0,v1,det)]
    diff=points@basis;diff=diff[:,None,:]-(a@basis)[None,:,:]
    u=(diff[:,:,0]*v1[:,1]-diff[:,:,1]*v1[:,0])/det
    v=(v0[:,0]*diff[:,:,1]-v0[:,1]*diff[:,:,0])/det
    inside=(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)
    projected=a[None,:,:]+u[:,:,None]*(b-a)[None,:,:]+v[:,:,None]*(c-a)[None,:,:]
    d=(points[:,None,:]-projected)@n
    return np.where(inside&(d>=-1e-6),d,np.inf).min(axis=1)

rows=[]
for p in new['parts']:
    meta=p.get('surface_paint')
    if not meta:continue
    assert p['motion']['kind']=='static' and p['group'] in ('front','rear')
    name=p['name'];side=meta['paint_side'];points=np.array(p['vertices'])
    if 'support_number' in name:host_kind='cast_yoke'
    elif 'frame_round_marker' in name:host_kind=p['group']+'_side_fascia'
    elif 'bridge_hatch_corner' in name:host_kind='bridge_lower_hatch_leaf'
    elif 'bridge_' in name:host_kind='bridge_shell'
    elif 'crane_' in name:host_kind='crane_root_cheek'
    else:host_kind=p['group']+'_deck'
    hosts=[h for h in new['parts'] if h['name'].endswith('_'+host_kind) and h['group']==p['group']]
    assert hosts,host_kind
    d=np.min(np.array([distances(points,h,side,meta.get('paint_normal')) for h in hosts]),axis=0)
    assert np.isfinite(d).all() and d.max()<.020 and d.min()>=.001,(name,d.min(),d.max())
    # The snow emblem and lower corner brackets must clear the last bridge door.
    if 'bridge_emblem' in name or 'bridge_hatch_corner' in name:
        assert points[:,0].min()>28.75,name
    if 'paint_access_tab' in name:
        bounds=np.array([points.min(axis=0),points.max(axis=0)])
        for lamp in new['parts']:
            if lamp['group']!=p['group'] or not lamp['name'].endswith('_twin_lamp_surround'):continue
            vv=np.array(lamp['vertices'])
            if np.sign(vv[:,1].mean())!=side:continue
            overlap=np.minimum(bounds[1,[0,2]],vv[:,[0,2]].max(axis=0))-np.maximum(bounds[0,[0,2]],vv[:,[0,2]].min(axis=0))
            assert not np.all(overlap>0),'Paint concealed by lamp surround: '+name
    rows.append({'name':name,'host':host_kind,'min_gap_m':float(d.min()),'max_gap_m':float(d.max())})
assert len(rows)==168
report={'passed':True,'layout_geometry_validation':'layout_validation.json',
        'paint_parts':len(rows),'surface_checks':rows,'glb_sha256':hashlib.sha256((ROOT/'assets/leviathan003.glb').read_bytes()).hexdigest(),
        'scope':'Actual authored mark vertices project onto the exterior host within 20 mm; r010 surface preservation under declared layout translations checked separately. Does not prove reference-identical lettering, colour or weathering.'}
(ROOT/'reports/surface_marks_validation.json').write_text(json.dumps(report,indent=2))
print('PASS:',len(rows),'paint parts on exterior hosts; layout surface preservation verified')
