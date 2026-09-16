"""Inspect installed tube axes, end direction and whole-bank rigid transform."""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
import trimesh as tm
ROOT=Path(__file__).resolve().parents[1]
def read(p):
 with gzip.open(p,'rt') as f:return json.load(f)
r=read(ROOT/'source/assembly.json.gz');old=read(ROOT/'revisions/r011/source/assembly.json.gz');cx=r['groups']['rear'][0]
crane=json.loads((ROOT/'reports/crane_pose_validation.json').read_text())
assert crane['passed'] and crane['source_sha256']==hashlib.sha256((ROOT/'source/assembly.json.gz').read_bytes()).hexdigest()
bogie=json.loads((ROOT/'reports/bogie_structure_validation.json').read_text())
assert bogie['passed'] and bogie['source_sha256']==hashlib.sha256((ROOT/'source/assembly.json.gz').read_bytes()).hexdigest()
changed_bogies=set(bogie['changed_existing_names'])
assert r['groups']==old['groups'] and len(r['parts'])==len(old['parts'])+len(bogie['added_names'])
rotation=np.array([[0,-1,0],[1,0,0],[0,0,1]])
counts={'rotated_bank':0,'translated_rack':0,'unchanged':0,'separately_verified_crane':0,'separately_verified_bogie':0}
for p,q in zip(old['parts'],r['parts']):
 if q['name'] in changed_bogies:
  counts['separately_verified_bogie']+=1;continue
 if q.get('assembly','').startswith('crane_'):
  counts['separately_verified_crane']+=1;continue
 for k in ['name','group','material','faces','motion','surface_paint']:assert p[k]==q[k],(p['name'],k)
 a=np.array(p['vertices']);b=np.array(q['vertices']);name=q['name'].split('_',1)[1]
 if q.get('assembly')=='reservoir_bank':
  expected=(a-[cx,0,0])@rotation.T+[cx,0,0];counts['rotated_bank']+=1;assert q['group']=='rear'
 elif name.startswith('tank_side_rack') or name=='rack_column':
  expected=a+[0,.4*np.sign(a[:,1].mean()),0];counts['translated_rack']+=1
 else:expected=a;counts['unchanged']+=1
 assert np.allclose(expected,b,atol=1e-10,rtol=0),q['name']
shells=[p for p in r['parts'] if p['name'].endswith('_sealed_reservoir_shell')];assert len(shells)==8
axis_rows=[];stations=[]
for p in shells:
 v=np.array(p['vertices']);span=np.ptp(v,axis=0);assert span[1]>24 and span[0]<5 and span[2]<5
 m=tm.Trimesh(vertices=v,faces=p['faces'],process=False);assert m.is_volume and m.euler_number==2
 stations.append([float(m.bounds.mean(axis=0)[i]) for i in [0,2]])
 axis_rows.append(dict(name=p['name'],span_m=span.tolist(),long_axis='Y',flat_cover_y_m=float(m.bounds[0,1]),ribbed_dome_y_m=float(m.bounds[1,1])))
assert np.allclose(sorted(set(round(s[0],6) for s in stations)),[-51.4,-45.6,-38.4,-32.6])
assert np.allclose(sorted(set(round(s[1],6) for s in stations)),[12,17.5])
# Near -Y flat-cover rings are full diameter, +Y nose rings are small diameter.
rims=[p for p in r['parts'] if p['name'].endswith('_sealed_reservoir_cap_rim')];assert len(rims)==16
for p in rims:
 v=np.array(p['vertices']);span=np.ptp(v,axis=0);assert span[1]<.06
 assert (span[0]>4.5 and v[:,1].mean()<-11.5) or (1.3<span[0]<1.5 and v[:,1].mean()>12.6)
# Keep longitudinal side racks outside the installed end covers and on the deck.
racks=[p for p in r['parts'] if 'tank_side_rack' in p['name'] or p['name'].endswith('_rack_column')]
for p in racks:
 v=np.array(p['vertices']);assert np.abs(v[:,1]).min()>12.85 and np.abs(v[:,1]).max()<13.5
# This static equipment correction must not silently invalidate the trained dynamics.
for name in ['assets/physics.json','training/policy.json']:
 assert (ROOT/name).read_bytes()==(ROOT/'revisions/r011'/name).read_bytes(),name
report=dict(passed=True,source_sha256=hashlib.sha256((ROOT/'source/assembly.json.gz').read_bytes()).hexdigest(),parts=counts,shells=axis_rows,column_x_and_level_z_m=stations,flat_cover_direction='-Y',ribbed_dome_direction='+Y',physics_and_policy_unchanged=True,reference_basis='Image2 plan/oblique view: tube axes transverse to hulls; images1 and4 show opposite dome/flat cover faces.',scope='Installed rigid geometry and sealed shell topology, not a pressure system, deployment mechanism or exact source-CAD dimensions.')
(ROOT/'reports/reservoir_orientation_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['shells','column_x_and_level_z_m']},indent=2))
