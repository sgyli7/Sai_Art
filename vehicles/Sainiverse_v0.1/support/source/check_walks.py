"""Regression for galleries intersecting the house and disconnected stair treads.
Geometry-only: this does not certify robot contact, navigation, or stair climbing.
"""
from pathlib import Path
import gzip,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
with gzip.open(ROOT/'source/assembly.json.gz','rt') as f:source=json.load(f)
parts=[];houses=[]
for p in source['parts']:
    v=np.asarray(p['vertices']);bounds=np.array([v.min(axis=0),v.max(axis=0)])
    if any(p['name'].endswith('_'+n) for n in ['bridge_walkdeck','bridge_upper_landing','bridge_lower_landing','bridge_stair_tread']):
        parts.append(dict(name=p['name'],bounds=bounds))
    if p['name'].endswith('_fore_service_shell'):houses.append(bounds)
count=json.loads((ROOT/'design/vehicle.json').read_text())['bridge']['stairs']['count']
assert len(houses)==1 and len(parts)==2*(count+3)
for p in parts:
    b=p['bounds']
    for house in houses:
        overlap=np.minimum(b[1],house[1])-np.maximum(b[0],house[0])
        assert not np.all(overlap>1e-5),'Gallery/stair intersects service cabin: '+p['name']
connections=[]
for i,p in enumerate(parts):
    a=p['bounds']
    for j,q in enumerate(parts[i+1:],i+1):
        b=q['bounds'];overlap=np.minimum(a[1,:2],b[1,:2])-np.maximum(a[0,:2],b[0,:2])
        rise=abs(a[1,2]-b[1,2])
        if np.all(overlap>.005) and rise<=.205:connections.append((i,j))
paths=[]
for sign in (-1,1):
    lower=next(i for i,p in enumerate(parts) if p['name'].endswith('_bridge_lower_landing') and np.sign(p['bounds'][:,1].mean())==sign)
    gallery=next(i for i,p in enumerate(parts) if p['name'].endswith('_bridge_walkdeck') and np.sign(p['bounds'][:,1].mean())==sign)
    previous={lower:None};queue=[lower]
    for node in queue:
        for a,b in connections:
            other=b if a==node else a if b==node else None
            if other is not None and other not in previous:previous[other]=node;queue.append(other)
    assert gallery in previous,'No continuous tread/landing chain to gallery'
    path=[];node=gallery
    while node is not None:path.append(parts[node]['name']);node=previous[node]
    paths.append(path[::-1])
report=dict(passed=True,walk_parts=len(parts),paths=paths,maximum_adjacent_step_m=.205,scope='Authored tread/landing surface connectivity and house clearance only. No collision, Sai contact, pathfinding or structural qualification.')
(ROOT/'reports/walk_geometry_validation.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='paths'})
