"""User-requested order: command hull, containers, energy module.

Reuse the identical common bases and move only payload-specific source parts.
Keep the previous energy-first authored candidate and evidence intact.
"""
from pathlib import Path
import gzip,hashlib,json
import numpy as np
from container_payload import mass_properties
from export_assembly import export

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'candidates/r016_modular/train'
OUT=ROOT/'candidates/r016_modular/train_containers_first'

def main():
    for sub in ['source','assets','reports','physics']:(OUT/sub).mkdir(parents=True,exist_ok=True)
    source=BASE/'source/assembly.json.gz';a=json.loads(gzip.decompress(source.read_bytes()))
    moved=[];unchanged=0
    for p in a['parts']:
        energy=(p['assembly']=='reservoir_bank' or p['name'].split('_',1)[1].startswith(('tank_side_rack_','rack_column')))
        container=p['assembly'].startswith('container_') or p['assembly'] in ['cargo_locks','cargo_sockets']
        if energy or container:
            assert p['group']==('rear' if energy else 'tail')
            delta=[-42,0,0] if energy else [42,0,0]
            p['vertices']=(np.array(p['vertices'])+delta).tolist();p['group']='tail' if energy else 'rear'
            moved.append(dict(name=p['name'],delta_source_m=delta))
        else:unchanged+=1
    registry=json.loads((BASE/'source/payload_registry.json').read_text())
    for c in registry['containers']:c['center_source_m'][0]+=42
    old=json.loads((ROOT/'assets/physics.json').read_text())
    mass=mass_properties(registry['containers'],base_inertia=np.array(old['inertia_diagonal'])*3300000/5000000)
    registry['mass']=mass
    registry['hull_mass_properties']={'rear':mass}
    registry['common_module_instances']=[dict(name='rear',center_source_m=[-42,0,7.2],payload='container_cargo'),dict(name='tail',center_source_m=[-84,0,7.2],payload='energy_cylinder_bank')]
    registry['module_order_front_to_back']=['command','containers','energy']
    registry['scope']='Only payload order changed. Common chassis/cranes/bogies remain bit-identical in their existing world locations; simulation must use the corresponding per-hull cargo mass/COM.'
    (OUT/'source/payload_registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    (OUT/'source/common_transport_module.json.gz').write_bytes((BASE/'source/common_transport_module.json.gz').read_bytes())
    with gzip.open(OUT/'source/assembly.json.gz','wt') as f:json.dump(a,f,separators=(',',':'))
    result=export(a,OUT/'assets/leviathan003_three_modules.glb')
    template=json.loads(gzip.decompress((BASE/'source/common_transport_module.json.gz').read_bytes()))
    bounds=lambda ps:np.array([np.concatenate([p['vertices'] for p in ps]).min(0),np.concatenate([p['vertices'] for p in ps]).max(0)])
    common_bounds=bounds(template['parts']);payload_bounds={}
    for group in ['rear','tail']:
        payload_bounds[group]=bounds([p for p in a['parts'] if p['group']==group and (p['assembly'].startswith('container_') or p['assembly']=='reservoir_bank')]).tolist()
    result.update(module_order_front_to_back=registry['module_order_front_to_back'],parts=len(a['parts']),motion_groups=len(a['groups']),
        common_module_bounds_local_m=common_bounds.tolist(),common_module_size_m=np.ptp(common_bounds,axis=0).tolist(),payload_bounds_source_m=payload_bounds,
        stationary_common_parts=unchanged,moved_payload_parts=moved,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,Path(__file__),ROOT/'source/container_payload.py']},
        scope='Exact payload reorder of the energy-first three-module candidate. Shared base/cranes unchanged; the two payloads have different envelopes. No new physics or performance assertion.')
    (OUT/'reports/model.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['moved_payload_parts','source_sha256']},indent=2))

if __name__=='__main__':main()
