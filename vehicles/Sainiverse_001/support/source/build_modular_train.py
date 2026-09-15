"""Common transport module plus energy/container three-section assembly.

Payload identity is separate from the shared chassis, cranes and fore/aft
interfaces. This authoring entry does not create or simulate game physics.
"""
from pathlib import Path
import copy,gzip,hashlib,json
import numpy as np
import trimesh as tm
from articulation_geometry import sleeve_clearance_tool
from container_payload import build as cargo_build,mass_properties,COLORS,SOURCE
from export_assembly import export

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'candidates/r016_modular/train'
BASE=ROOT/'candidates/r016_modular/source/assembly.json.gz'

def shifted(part,delta,name,group,assembly=None):
    p=copy.deepcopy(part);p['name']=name;p['group']=group
    p['vertices']=(np.array(p['vertices'])+delta).tolist()
    if assembly is not None:p['assembly']=assembly
    return p

def main():
    a=json.loads(gzip.decompress(BASE.read_bytes()));parts=a['parts'];next_id=20000
    for sub in ['source','assets','reports','physics']:(OUT/sub).mkdir(parents=True,exist_ok=True)
    aft=[]
    for p in parts:
        if p['group']=='front' and (p['assembly']=='articulation_r015' or p['name'].endswith('_coupling_deck_mount')):
            aft.append(shifted(p,[-42,0,0],f'{next_id}_'+p['name'].split('_',1)[1],'rear','module_aft_receiver'));next_id+=1
    parts.extend(aft)
    tool=sleeve_clearance_tool();tool.apply_translation([-42,0,0]);cuts=[]
    for p in parts:
        if p['group']!='rear' or p['name'].split('_',1)[1] not in ['rear_deck','rear_crossbeam']:continue
        m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
        hit=tm.boolean.intersection([m,tool],engine='manifold')
        if len(hit.faces) and hit.volume>1e-7:
            cut=tm.boolean.difference([m,tool],engine='manifold');assert cut.is_volume
            cuts.append(dict(name=p['name'],removed_volume_m3=float(m.volume-cut.volume)));p['vertices']=cut.vertices.tolist();p['faces']=cut.faces.tolist()
    def payload_specific(p):
        return p['assembly']=='reservoir_bank' or p['name'].split('_',1)[1].startswith(('tank_side_rack_','rack_column'))
    common=[p for p in parts if p['group'].startswith('rear') and not payload_specific(p)]
    template=dict(colors=a['colors'],groups={},parts=[])
    for group,pivot in a['groups'].items():
        if group.startswith('rear'):template['groups'][group.replace('rear','module',1)]=(np.array(pivot)+[42,0,0]).tolist()
    for p in common:
        template['parts'].append(shifted(p,[42,0,0],p['name'],p['group'].replace('rear','module',1)))
    with gzip.open(OUT/'source/common_transport_module.json.gz','wt') as f:json.dump(template,f,separators=(',',':'))
    # Clone only the common base; energy-specific tanks and side racks stay on
    # the energy module and do not silently survive on the container module.
    copies=[];mapping={}
    for p in common:
        name=f'{next_id}_'+p['name'].split('_',1)[1];next_id+=1
        copies.append(shifted(p,[-42,0,0],name,p['group'].replace('rear','tail',1)))
        mapping[name]=p['name']
    for group,pivot in list(a['groups'].items()):
        if group.startswith('rear'):a['groups'][group.replace('rear','tail',1)]=(np.array(pivot)+[-42,0,0]).tolist()
    for p in list(parts):
        if p['group'].startswith('hitch_'):
            name=f'{next_id}_'+p['name'].split('_',1)[1];next_id+=1
            copies.append(shifted(p,[-42,0,0],name,'tail_'+p['group'],'tail_coupling'))
    for group,pivot in list(a['groups'].items()):
        if group.startswith('hitch_'):a['groups']['tail_'+group]=(np.array(pivot)+[-42,0,0]).tolist()
    parts.extend(copies)
    payload,registry=cargo_build(-84.)
    for p in payload:
        m=p['mesh'];parts.append(dict(name=f'{next_id}_'+p['name'],group='tail',material=p['material'],vertices=m.vertices.tolist(),faces=m.faces.tolist(),assembly=p['assembly'],surface_paint=None,motion={'kind':'static'}));next_id+=1
    a['colors'].update(COLORS)
    old=json.loads((ROOT/'assets/physics.json').read_text())
    mass=mass_properties(registry,base_inertia=np.array(old['inertia_diagonal'])*3300000/5000000)
    payload_report=dict(profile='container_cargo',containers=registry,mass=mass,dimensions_source=SOURCE,
                        common_module_instances=[dict(name='rear',center_source_m=[-42,0,7.2],payload='energy_cylinder_bank'),dict(name='tail',center_source_m=[-84,0,7.2],payload='container_cargo')])
    (OUT/'source/payload_registry.json').write_text(json.dumps(payload_report,indent=2)+'\n')
    with gzip.open(OUT/'source/assembly.json.gz','wt') as f:json.dump(a,f,separators=(',',':'))
    result=export(a,OUT/'assets/leviathan003_three_modules.glb')
    result.update(parts=len(parts),motion_groups=len(a['groups']),container_count=len(registry),common_template_parts=len(common),cloned_common_parts=len(mapping),added_aft_receiver_parts=len(aft),receiver_tunnel_cuts=cuts,
                  common_clone_map=mapping,payload_mass=mass,scope='Three-section authored geometry with shared transport base and locked container registry. No new dynamic validation or handling claim; spare rear receiver and modified deck tunnels require structural review.',
                  source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE,Path(__file__),ROOT/'source/container_payload.py',ROOT/'source/export_assembly.py']})
    (OUT/'reports/model.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['common_clone_map','source_sha256']},indent=2))

if __name__=='__main__':main()
