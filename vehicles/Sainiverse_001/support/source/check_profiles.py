"""Regression: concave recesses and through-holes must survive tessellation."""
from mesh_profiles import *
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
# 4x4 section with a 2x3 open notch. Convex-hull export incorrectly produces 16.
outline=[(0,0),(4,0),(4,4),(3,4),(3,1),(1,1),(1,4),(0,4)]
u=extrude_xz(outline,0,2)
assert abs(u.volume-20)<1e-6 and u.is_volume
assert abs(u.convex_hull.volume-32)<1e-6
# Clockwise and counter-clockwise input describe the same volume.
reverse=extrude_xz(outline[::-1],0,2)
assert abs(reverse.volume-u.volume)<1e-6
# One real through-hole gives a genus-one solid and removes exact polygonal area.
h=extrude_xz([(0,0),(4,0),(4,4),(0,4)],0,2,[circle_xz(2,2,.5,32)])
expected=(16-32/2*.5**2*np.sin(2*np.pi/32))*2
assert abs(h.volume-expected)<1e-5 and h.euler_number==0 and h.is_volume
# Screen the actual authored source parts, including every hole-bearing boom.
import gzip
with gzip.open(ROOT/'source/assembly.json.gz','rt') as f:recipe=json.load(f)
selected=[]
for item in recipe['parts']:
    if any(s in item['name'] for s in ('cast_yoke','panel_arm','crane_boom')):
        m=trimesh.Trimesh(vertices=item['vertices'],faces=item['faces'],process=False)
        assert m.is_volume
        if 'crane_boom' in item['name']:assert m.euler_number==-4 # three tunnels
        selected.append({'name':item['name'],'volume':float(m.volume),'convex_volume':float(m.convex_hull.volume),'euler_number':int(m.euler_number)})
report={'passed':True,'notched_test_volume':float(u.volume),'old_convex_hull_volume':float(u.convex_hull.volume),'hole_test_volume':float(h.volume),'actual_parts':selected}
(ROOT/'reports/profiles.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
