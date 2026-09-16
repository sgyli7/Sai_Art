"""Actual geometry regression for the paired reservoir mounting assembly."""
from pathlib import Path
import json,gzip,copy
import numpy as np
import trimesh as tm
ROOT=Path(__file__).resolve().parents[1]
def read(path):
    with gzip.open(path,'rt') as f:return json.load(f)
r=read(ROOT/'source/assembly.json.gz');old=read(ROOT/'revisions/r007/source/assembly.json.gz')
# Undo the separately verified transverse installation only for legacy shape/pin fixtures.
local=copy.deepcopy(r);cx=r['groups']['rear'][0]
for p in local['parts']:
    if p.get('assembly')=='reservoir_bank':
        v=np.array(p['vertices']);x=v[:,0]-cx;y=v[:,1].copy()
        v[:,0]=cx+y;v[:,1]=-x;p['vertices']=v.tolist()

def named(recipe,name):return [p for p in recipe['parts'] if p['name'].split('_',1)[1]==name]
def mesh(p):return tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
def center(p):return mesh(p).bounds.mean(axis=0)
shells=named(r,'sealed_reservoir_shell');local_shells=named(local,'sealed_reservoir_shell');old_shells=named(old,'sealed_reservoir_shell')
assert len(shells)==len(old_shells)==8
for p,q in zip(local_shells,old_shells):
    assert np.allclose(np.array(p['vertices'])-r['groups']['rear'],np.array(q['vertices'])-old['groups']['rear'],atol=1e-10,rtol=0) and np.array_equal(p['faces'],q['faces'])
clamps=named(r,'sealed_reservoir_clamp_cheek');pins=named(r,'sealed_reservoir_clamp_pin');assert len(clamps)==len(pins)==96
bore_clearance=[]
for p,pin in zip(clamps,pins):
    m=mesh(p);assert m.is_volume and m.euler_number==0
    _,distance,_=tm.proximity.closest_point_naive(m,[center(pin)])
    assert .1005<distance[0]<.106,(p['name'],distance)
    bore_clearance.append(float(distance[0]-.1))
def endpoints(p):
    v=np.array(p['vertices']);c=v.mean(axis=0);_,_,axes=np.linalg.svd(v-c,full_matrices=False);axis=axes[0]
    projection=(v-c)@axis
    return np.array([v[abs(projection-bound)<1e-6].mean(axis=0) for bound in (projection.min(),projection.max())])
def link_errors(recipe):
    pin_meshes=[mesh(p) for name in ('sealed_reservoir_clamp_pin','paired_bridge_pin') for p in named(recipe,name)]
    result=[]
    for p in named(recipe,'paired_crown_link'):
        for point in endpoints(p):
            distances=[]
            for pm in pin_meshes:
                c=pm.bounds.mean(axis=0)
                if pm.bounds[0,0]-.001<=point[0]<=pm.bounds[1,0]+.001:distances.append(float(np.linalg.norm(point[1:]-c[1:])))
            result.append(min(distances,default=999))
    return result
old_errors=link_errors(old);errors=link_errors(local)
assert len(errors)==192 and max(errors)<1e-5 and max(old_errors)>.1
# Existing solid-shell envelopes are exclusions for major support metalwork.
major=[p for name in ('paired_cradle_crosshead','paired_cradle_upright','lower_reservoir_saddle') for p in named(r,name)]
checked=0
for p in major:
    m=mesh(p);assert m.is_volume
    for shell in shells:
        sm=mesh(shell)
        if np.any(np.minimum(m.bounds[1],sm.bounds[1])-np.maximum(m.bounds[0],sm.bounds[0])<=0):continue
        checked+=1;cut=tm.boolean.intersection([m,sm],engine='manifold')
        assert not len(cut.faces) or cut.volume<1e-5,(p['name'],shell['name'],cut.volume)
# Feet must contact the authored deck; preserve the previous visible-gap fixture.
deck=mesh(named(r,'rear_deck')[0]);deck_top=deck.bounds[1,2]
old_gaps=[float(mesh(p).bounds[0,2]-deck_top) for p in named(old,'paired_cradle_foot')]
assert min(old_gaps)>.12
feet=[]
for p in named(r,'paired_cradle_foot'):
    m=mesh(p);cut=tm.boolean.intersection([m,deck],engine='manifold')
    assert len(cut.faces) and cut.volume>1e-4
    feet.append(dict(name=p['name'],deck_gap_m=float(m.bounds[0,2]-deck_top),contact_volume_m3=float(cut.volume)))
assert len(feet)==4
report=dict(passed=True,sealed_shell_shape_unchanged_under_installation_rotation=8,clamp_pin_pairs=96,bore_min_radial_clearance_m=min(bore_clearance),bore_max_radial_clearance_m=max(bore_clearance),link_endpoints_checked=len(errors),maximum_endpoint_to_pin_axis_m=max(errors),previous_maximum_endpoint_error_m=max(old_errors),major_support_shell_narrow_tests=checked,major_support_shell_intersections=0,previous_foot_deck_gap_m=old_gaps,feet=feet,scope='Locked visual attachment geometry, pin alignment and sealed-shell exclusion only. Ring/pad/seat contact is idealized; no deployment, stress, restraint loads or hardware qualification.')
(ROOT/'reports/reservoir_mount_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
