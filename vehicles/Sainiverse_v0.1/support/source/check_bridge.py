"""Actual bridge topology, window containment and threshold/gallery connections."""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
import trimesh as tm
ROOT=Path(__file__).resolve().parents[1]
with gzip.open(ROOT/'source/assembly.json.gz','rt') as f:r=json.load(f)
def named(name):return [p for p in r['parts'] if p['name'].split('_',1)[1]==name]
def mesh(p):return tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
def bounds(p):
    v=np.array(p['vertices']);return np.array([v.min(axis=0),v.max(axis=0)])
shell=mesh(named('bridge_shell')[0]);assert shell.is_volume
assert shell.volume < shell.convex_hull.volume*.98,'Long cabin lower recess was filled by a convex hull'
leaves=named('bridge_door_leaf');glass=named('bridge_door_window')
assert len(leaves)==6 and len(glass)==2 and len(named('bridge_square_window'))==4
assert not named('bridge_access_leaf') and not named('bridge_upper_panel')
window_rows=[]
for p in glass+named('bridge_door_window_gasket'):
    b=bounds(p);c=b.mean(axis=0)
    door=min(leaves,key=lambda d:np.linalg.norm(bounds(d).mean(axis=0)-c))
    h=bounds(door);margin=np.r_[b[0,[0,2]]-h[0,[0,2]],h[1,[0,2]]-b[1,[0,2]]]
    assert margin.min()>.05,(p['name'],margin)
    window_rows.append({'name':p['name'],'minimum_leaf_margin_m':float(margin.min())})
galleries=named('bridge_walkdeck');thresholds=[]
for door in leaves:
    b=bounds(door);side=np.sign(b.mean(axis=0)[1])
    gal=next(g for g in galleries if np.sign(bounds(g).mean(axis=0)[1])==side);gb=bounds(gal)
    assert gb[0,0]<b[0,0] and gb[1,0]>b[1,0]
    assert .0<=b[0,2]-gb[1,2]<=.05
    assert min(abs(gb[:,1]))<3.5,'Gallery leaves a gap at the wall'
    thresholds.append({'name':door['name'],'rise_m':float(b[0,2]-gb[1,2])})
trusses=named('bridge_gallery_truss');assert len(trusses)==2
for p in trusses:
    m=mesh(p);assert m.is_volume and m.euler_number==-16
    assert m.volume/m.convex_hull.volume<.45,'Truss still reads as a largely solid plate'
    b=m.bounds;side=np.sign(b.mean(axis=0)[1]);g=next(g for g in galleries if np.sign(bounds(g).mean(axis=0)[1])==side)
    overlap=np.minimum(b[1],bounds(g)[1])-np.maximum(b[0],bounds(g)[0]);assert np.all(overlap>0)
# Short support beam terminates at the front of the gallery, not below the bow.
assert max(bounds(p)[1,0] for p in trusses)<28
assert len(named('bridge_lower_hatch_leaf'))==2 and len(named('bridge_roof_rung'))>=26
report={'passed':True,'shell_volume_m3':float(shell.volume),'convex_hull_volume_m3':float(shell.convex_hull.volume),
        'doors':6,'windowed_doors':2,'independent_square_windows':4,'short_gallery_trusses':2,
        'window_containment':window_rows,'thresholds':thresholds,'glb_sha256':hashlib.sha256((ROOT/'assets/leviathan003.glb').read_bytes()).hexdigest(),
        'scope':'Closed reconstructed envelope, concave lower silhouette, windows within door leaves and visually connected galleries. No interior, opening doors, Sai contact or structural qualification.'}
(ROOT/'reports/bridge_geometry_validation.json').write_text(json.dumps(report,indent=2))
print('PASS: concave bridge, 6 doors / 2 windowed, 4 independent square windows, connected thresholds and 2 short trusses')
