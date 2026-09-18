"""Measure exported crane tube geometry, engagement and solid intersections.

Only nested tube shells/glands are covered. This is a packaging audit, not a
stress calculation, load rating or collision-free loaded-path qualification.
"""
from pathlib import Path
import gzip,json
import numpy as np
import trimesh as tm

O=Path(__file__).resolve().parents[1]
a=json.loads(gzip.decompress((O/'source/assembly.json.gz').read_bytes()))
rows=[]
def mesh(part):
    m=tm.Trimesh(vertices=part['vertices'],faces=part['faces'],process=True)
    assert m.is_volume, part['name']
    return m

for c in a['equipment_actuation']['cranes']:
    direction=np.array(c['direction']);pin=np.array(a['groups'][c['luff']])
    sections=[];glands=[]
    for s in c['sections']:
        ps=[p for p in a['parts'] if p['group']==s['name']]
        shell=mesh(next(p for p in ps if p['name'].endswith('_telescopic_box_section')))
        gland=mesh(next(p for p in ps if p['name'].endswith('_telescopic_gland')))
        extent=(shell.vertices-pin)@direction
        assert np.allclose([extent.min(),extent.max()],s['u'],atol=1e-6)
        sections.append(shell);glands.append(gland)
    for i in range(1,4):
        parent,child=c['sections'][i-1:i+1]
        overlap=parent['u'][1]-child['u'][0]-child['stroke']
        assert overlap>=2.-1e-6,(c['name'],i,overlap)
        # Actual solid meshes, including the parent's external retaining gland.
        max_volume=0.
        for fraction in np.linspace(0,1,9):
            moving=sections[i].copy();moving.apply_translation(direction*child['stroke']*fraction)
            for fixed in [sections[i-1],glands[i-1]]:
                intersect=tm.boolean.intersection([fixed,moving],engine='manifold')
                volume=abs(float(intersect.volume)) if len(intersect.faces) else 0.
                assert np.isfinite(volume),(c['name'],i,fraction)
                max_volume=max(max_volume,volume)
        assert max_volume<1e-7,(c['name'],i,max_volume)
        rows.append(dict(crane=c['name'],stage=child['name'],minimum_engagement_m=overlap,
                         sampled_positions=9,max_solid_intersection_m3=max_volume))
report=dict(cranes=8,watertight_shells=32,watertight_glands=32,
            boolean_pairs=len(rows)*9*2,minimum_engagement_m=min(r['minimum_engagement_m'] for r in rows),
            stages=rows,scope=__doc__)
(O/'reports/telescopic_sections.json').write_text(json.dumps(report,indent=2))
print({k:v for k,v in report.items() if k not in ['stages','scope']})
