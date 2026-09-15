"""Check authoring/export parity and the actual sealed reservoir geometry."""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
import trimesh as tm
ROOT=Path(__file__).resolve().parents[1]
with gzip.open(ROOT/'source/assembly.json.gz','rt') as f:recipe=json.load(f)
scene=tm.load_scene(ROOT/'assets/leviathan003.glb')
source_faces=sum(len(p['faces']) for p in recipe['parts'])
glb_faces=sum(len(m.faces) for m in scene.geometry.values())
visual=json.loads((ROOT/'assets/visual_meshes.json').read_text())
assert source_faces==glb_faces==sum(p['triangles'] for p in visual)
source_vertices=np.vstack([p['vertices'] for p in recipe['parts']])
assert np.isfinite(source_vertices).all()
assert np.allclose(scene.bounds,[source_vertices.min(axis=0),source_vertices.max(axis=0)],atol=1e-5)
shells=[]
for p in recipe['parts']:
    if p['name'].endswith('sealed_reservoir_shell'):
        m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
        assert m.is_volume and m.euler_number==2
        shells.append(dict(name=p['name'],bounds=m.bounds.tolist(),closed=True))
assert len(shells)==8
# Regression for the reviewed roof mistake: a raised deck must not cover the
# vertical projection of either roof fan intake.
by_name={p['name'].split('_',1)[1]:p for p in recipe['parts']}
deck_vertices=np.asarray(by_name['raised_panel_deck']['vertices'])
deck_bounds=np.array([deck_vertices.min(axis=0),deck_vertices.max(axis=0)])
fan_checks=[]
for p in recipe['parts']:
    if p['name'].endswith('_vent_fan'):
        v=np.asarray(p['vertices']);bounds=np.array([v.min(axis=0),v.max(axis=0)])
        xy_overlap=np.minimum(bounds[1,:2],deck_bounds[1,:2])-np.maximum(bounds[0,:2],deck_bounds[0,:2])
        assert not np.all(xy_overlap>0), 'Raised deck obstructs roof fan: '+p['name']
        fan_checks.append(p['name'])
assert len(fan_checks)==2

policy=json.loads((ROOT/'training/policy.json').read_text())
assert hashlib.sha256((ROOT/'assets/physics.json').read_bytes()).hexdigest()==policy['physics_sha256']
report=dict(passed=True,triangles=glb_faces,render_meshes=len(scene.geometry),source_parts=len(recipe['parts']),sealed_shells=shells,physics_matches_training=True,uncovered_roof_fans=fan_checks,limits='Mesh closure and export parity only; not structure/pressure/engineering qualification. Thin skin seams are intentionally open visual strips.')
(ROOT/'reports/assets_validation.json').write_text(json.dumps(report,indent=2))
print({k:v for k,v in report.items() if k!='sealed_shells'})
