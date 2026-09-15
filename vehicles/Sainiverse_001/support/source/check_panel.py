"""Inspect actual authored panel geometry and hinge attachment in the locked pose."""
from pathlib import Path
import json,gzip
import numpy as np
import trimesh as tm
ROOT=Path(__file__).resolve().parents[1]
with gzip.open(ROOT/'source/assembly.json.gz','rt') as f:r=json.load(f)
cfg=json.loads((ROOT/'design/vehicle.json').read_text())['panel']
def named(name):return [p for p in r['parts'] if p['name'].split('_',1)[1]==name]
def mesh(p):return tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
def one(name):
    p=named(name);assert len(p)==1,name
    return mesh(p[0])
rotation=tm.transformations.rotation_matrix(np.deg2rad(cfg['tilt_degrees']),[0,1,0])[:3,:3]
upper=np.array(cfg['upper_pivot']);center=upper+rotation@np.array([0,0,cfg['outer_height']/2])
def local(m):return (m.vertices-center)@rotation
outer=one('panel_outer');face=one('panel_face');pattern=one('panel_face_pattern')
assert outer.is_volume and face.is_volume and pattern.is_volume
for name,point in [('panel_lower_shaft',cfg['lower_pivot']),('panel_upper_shaft',cfg['upper_pivot'])]:
    m=one(name);assert np.allclose(m.bounds.mean(axis=0),point,atol=1e-6)
    extent=np.ptp(m.vertices,axis=0);assert extent[1]>5 and extent[0]<.51 and extent[2]<.51
outer_local=local(outer);face_local=local(face);pattern_local=local(pattern)
assert abs(outer_local[:,2].min()+cfg['outer_height']/2)<1e-5
assert np.allclose((upper-center)@rotation,[0,0,-cfg['outer_height']/2],atol=1e-6)
# Face pattern remains within the dark face and immediately in front of it.
for axis in (1,2):
    assert pattern_local[:,axis].min()>face_local[:,axis].min()+.05
    assert pattern_local[:,axis].max()<face_local[:,axis].max()-.05
pattern_gap=float(pattern_local[:,0].min()-face_local[:,0].max())
assert 0<pattern_gap<.005
arm_rows=[]
for p in named('panel_arm'):
    m=mesh(p);assert m.is_volume and m.euler_number==-2 # two pin holes
    arm_rows.append(dict(name=p['name'],euler_number=m.euler_number,volume=float(m.volume)))
assert len(arm_rows)==2
# Actual lugs must intersect the shell to transmit the represented support visually.
lug_contacts=[]
for p in named('panel_shell_lug'):
    intersection=tm.boolean.intersection([outer,mesh(p)],engine='manifold')
    assert len(intersection.faces) and intersection.volume>1e-5,p['name']
    lug_contacts.append(dict(name=p['name'],shell_intersection_m3=float(intersection.volume)))
assert len(lug_contacts)==2
base=one('panel_base');turntable=one('panel_turntable')
cut=tm.boolean.intersection([base,turntable],engine='manifold');assert len(cut.faces) and cut.volume>1e-5
# A cheek entering the base must not duplicate its exterior plane (black z-fighting).
for p in named('panel_fixed_fork'):
    bounds=mesh(p).bounds
    assert np.max(np.abs(bounds[:,1]))<np.max(np.abs(base.bounds[:,1]))-.02
# The base must sit on the already authored upper deck, within its footprint.
deck=one('raised_panel_deck');bounds=base.bounds;db=deck.bounds
margin=np.r_[bounds[0,:2]-db[0,:2],db[1,:2]-bounds[1,:2]];assert margin.min()>0
report=dict(passed=True,upper_hinge_on_shell_lower_edge=True,lower_pivot=cfg['lower_pivot'],upper_pivot=cfg['upper_pivot'],arms=arm_rows,lug_shell_contacts=lug_contacts,base_turntable_contact_m3=float(cut.volume),minimum_base_deck_margin_m=float(margin.min()),pattern_triangles=len(pattern.faces),pattern_front_gap_m=pattern_gap,scope='Actual locked visual assembly, closed shells, pin-hole topology and support attachment. No dynamic deployment, sensor function, bearing forces, cylinder travel or structural qualification.')
(ROOT/'reports/panel_geometry_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
