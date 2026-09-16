"""Measure source-model crane/shell interference and confirm real boom openings."""
from pathlib import Path
import json,gzip
import numpy as np
import trimesh as tm
ROOT=Path(__file__).resolve().parents[1]
def read(path):
    with gzip.open(path,'rt') as f:return json.load(f)
def mesh(p):return tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
def interference(recipe):
    shells=[p for p in recipe['parts'] if p['name'].endswith('_sealed_reservoir_shell')]
    candidates=[p for p in recipe['parts'] if p['name'].split('_',1)[1] in ('crane_pedestal','crane_slew','crane_neck','crane_turning_head','crane_pivot_fork','crane_boom','crane_root_cheek')]
    issues=[];tested=0
    for p in candidates:
        m=mesh(p)
        for shell in shells:
            sm=mesh(shell);overlap=np.minimum(m.bounds[1],sm.bounds[1])-np.maximum(m.bounds[0],sm.bounds[0])
            if np.any(overlap<=1e-6):continue
            tested+=1
            cut=tm.boolean.intersection([m,sm],engine='manifold')
            if len(cut.faces) and cut.volume>1e-5:issues.append(dict(crane_part=p['name'],shell=shell['name'],overlap_m3=float(cut.volume)))
    return dict(candidate_parts=len(candidates),narrow_phase_tests=tested,intersections=issues)
current=read(ROOT/'source/assembly.json.gz');previous=read(ROOT/'revisions/r005/source/assembly.json.gz')
before=interference(previous);after=interference(current)
assert before['intersections'], 'Regression fixture no longer reproduces the reviewed collision'
assert not after['intersections'],after
# Both columns sit over their housing, and housings/foundation remain over the deck.
deck=mesh(next(p for p in current['parts'] if p['name'].endswith('_rear_deck'))).bounds
foundation_rows=[]
for p in current['parts']:
    if p['name'].split('_',1)[1] in ('crane_pedestal','crane_foundation'):
        bounds=mesh(p).bounds
        margins=np.r_[bounds[0,:2]-deck[0,:2],deck[1,:2]-bounds[1,:2]]
        assert margins.min()>=.14, (p['name'],margins)
        foundation_rows.append(dict(name=p['name'],minimum_deck_margin_m=float(margins.min())))
assert len(foundation_rows)==4
booms=[]
for p in current['parts']:
    if p['name'].endswith('_crane_boom'):
        m=mesh(p);assert m.is_volume and m.euler_number==-4
        booms.append(dict(name=p['name'],volume=float(m.volume),euler_number=m.euler_number))
assert len(booms)==4 # two sides of each boxed telescoping arm
# Each rope fall reaches the tip sheave and hook height; block/sheave cannot float.
ropes=[p for p in current['parts'] if p['name'].endswith('_winch_rope')]
vertical=[]
for p in ropes:
    b=mesh(p).bounds;span=b[1]-b[0]
    if span[0]<.1 and span[2]>3:vertical.append(dict(name=p['name'],bottom=float(b[0,2]),top=float(b[1,2])))
assert len(vertical)==4 and all(abs(p['bottom']-13.72)<.03 and abs(p['top']-17.72)<.03 for p in vertical)
report=dict(passed=True,previous=before,current=after,foundation_deck_margins=foundation_rows,boom_cheeks=booms,vertical_rope_falls=vertical,scope='Actual crane body vs sealed-shell geometry; authoring assembly and locked transport pose only. No crane load, dynamic articulation, cable mechanics or hardware rating verified.')
(ROOT/'reports/crane_geometry_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
