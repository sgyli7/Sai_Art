"""Actual source checks for revision load-path contacts and bilateral layout.
These geometric checks are not strength, fatigue or manufacturer qualification.
"""
from pathlib import Path
import json,gzip
import numpy as np
import trimesh as tm
from scipy.spatial import cKDTree
O=Path(__file__).resolve().parents[1]
a=json.loads(gzip.decompress((O/'source/assembly.json.gz').read_bytes()))
parts=a['parts'];rows=[]
def match(text):return [p for p in parts if text in p['name']]
def mesh(p):return tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
for term in ['fore_service_shell','middlehouse_shell','continuous_cooling_elbow','equipment_window','cabin_root_','cabin_underfloor_girder','cabin_cross_bearer','underdeck_power_spine','underdeck_distribution_branch','rooftop_receiver']:
 ps=match(term)
 if not ps:continue
 points=np.concatenate([p['vertices'] for p in ps]);mirrored=points*np.array([1,-1,1]);dist=cKDTree(points).query(mirrored)[0]
 rows.append({'part_family':term,'parts':len(ps),'max_mirror_vertex_error_m':float(dist.max()),'passed':bool(dist.max()<.006)})
contacts=[]
for foot in match('cabin_root_foot'):
 side=np.sign(np.mean(foot['vertices'],axis=0)[1]);f=mesh(foot)
 for term in ['front_deck','cabin_root_column']:
  candidates=[p for p in match(term) if p['group']=='front' and (term=='front_deck' or np.sign(np.mean(p['vertices'],axis=0)[1])==side)]
  for p in candidates:
   q=mesh(p);overlap=np.minimum(f.bounds[1],q.bounds[1])-np.maximum(f.bounds[0],q.bounds[0])
   if np.min(overlap)>=-.00001:
    contacts.append({'from':foot['name'],'to':p['name'],'contact_bbox_depth_m':overlap.tolist()})
pipes=[{'name':p['name'],'watertight':mesh(p).is_watertight,'connected_components':len(mesh(p).split())} for p in match('continuous_cooling_elbow')]
report={'symmetry':rows,'root_contacts':contacts,'pipes':pipes,'scope':'Selected structural families, reflection vertex distance; root contact bbox adjacency and pipe manifold continuity. Not universal interference or strength verification.'}
(O/'reports/structure_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
assert all(r['passed'] for r in rows)
assert len(contacts)==4
assert len(pipes)==2 and all(p['watertight'] and p['connected_components']==1 for p in pipes)
