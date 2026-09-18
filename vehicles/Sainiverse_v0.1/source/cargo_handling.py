"""First independently handled 20 ft top-tier container, reused source geometry.
Its 8 t gross scenario mass is deaggregated from the loaded trailer. This is a
handling test article, not a claimed container/crane rated capacity.
"""
import json
import numpy as np

def author(a,box,rod,O):
 tag='container_b0_r2_t2_';name='cargo_rear_b0_r2_t2'
 parts=[p for p in a['parts'] if tag in p['name']]
 assert parts
 vertices=np.concatenate([p['vertices'] for p in parts]);lo=vertices.min(0);hi=vertices.max(0);pivot=(lo+hi)/2
 a['groups'][name]=pivot.tolist()
 for p in parts:p['group']=name;p['physical_body']=name
 # Compact four-corner spreader and four sling legs; all are source-authored.
 z=hi[2]+.16;corners=[]
 for x in [lo[0]+.10,hi[0]-.10]:
  for y in [lo[1]+.10,hi[1]-.10]:
   corners.append(np.array([x,y,z]));box('cargo_twistlock',[x,y,z-.10],[.20,.20,.30],'steel',name)
 for y in [lo[1]+.10,hi[1]-.10]:box('cargo_spreader_longitudinal',[pivot[0],y,z],[hi[0]-lo[0]-.2,.15,.16],'crane',name)
 for x in [lo[0]+.10,hi[0]-.10]:box('cargo_spreader_crosshead',[x,pivot[1],z],[.20,hi[1]-lo[1]-.2,.20],'crane',name)
 eye=pivot.copy();eye[2]=hi[2]+1.15
 for corner in corners:rod('cargo_sling',corner,eye,.024,'steel',name)
 # Lift eye geometry is small; point attachment is explicit in the manifest.
 rod('cargo_eye_crosspin',eye+[-.10,0,0],eye+[.10,0,0],.045,'steel',name)
 # Removable rigging is a work-mode tool, not a permanent yellow cargo lid.
 a['colors']['rig_cargo_spreader']='535D62'
 for part in a['parts']:
  if part['group']==name and any(t in part['name'] for t in ['cargo_spreader','cargo_sling','cargo_eye_crosspin','cargo_twistlock']):part['material']='rig_cargo_spreader'
 size=hi-lo;mass=8000.;inertia=mass/12*(np.sum(size**2)-size**2)
 rig=a['equipment_actuation'];rig['bodies'].append(dict(name=name,hull='rear',pivot=pivot.tolist(),mass=mass,com=[0,0,0],inertia=inertia.tolist(),cargo=True,collision_bounds=[lo.tolist(),hi.tolist()]))
 rig['cargo']=[dict(name=name,hull='rear',mass_kg=mass,source_tag=tag,center=pivot.tolist(),size=size.tolist(),eye_local=(eye-pivot).tolist(),initially_secured=True,rigging_visibility='work_or_attached',rigging_installation='Instant installation/removal in work mode; tool handling animation is not simulated.')]
 # Keep every authored box in a stable selection manifest. Only the selected
 # dynamic article is promoted to a free body in this candidate; the manifest
 # makes tier eligibility and return-to-slot ownership explicit for the next
 # multi-load implementation instead of silently treating the stack as one box.
 catalog=[]
 for b in range(4):
  for r in range(6):
   for t in range(3):
    key=f'container_b{b}_r{r}_t{t}'
    members=[p for p in a['parts'] if key in p['name']]
    assert members,key
    vv=np.concatenate([p['vertices'] for p in members]);blo=vv.min(0);bhi=vv.max(0);bc=(blo+bhi)/2
    beye=bc.copy();beye[2]=bhi[2]+1.15
    catalog.append(dict(name=key,hull='rear',bay=b,row=r,tier=t,mass_kg=20000. if t==0 else 8000.,
                        center=bc.tolist(),size=(bhi-blo).tolist(),eye_local=(beye-bc).tolist(),
                        eligible_to_lift=t==2,blocking_tiers=list(range(t+1,3)),
                        return_slot_center=bc.tolist(),initially_secured=True))
 assert len(catalog)==72 and sum(x['eligible_to_lift'] for x in catalog)==24
 rig['cargo_catalog']=catalog
 a['colors'].setdefault('crane','C5A33D')
 (O/'source/equipment.json').write_text(json.dumps(rig,indent=2))
 (O/'source/cargo_handling.json').write_text(json.dumps(rig['cargo'],indent=2))
