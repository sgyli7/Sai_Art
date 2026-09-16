"""Add actual door bodies and convex room contacts to both engine inputs."""
from pathlib import Path
import copy
import gzip
import json
import shutil
import xml.etree.ElementTree as E
import numpy as np
from suspension_physics import ROOT, Env
from export_suspension_native import export_environment
from build_bridge_interior import mesh

OUT = ROOT / 'candidates/r025_access'
OLD = ROOT / 'candidates/r024_atelier'
fmt = lambda values: ' '.join(format(float(v), '.15g') for v in values)


def main():
    access = json.loads((OUT / 'source/access.json').read_text())
    cfg = json.loads((ROOT / 'design/vehicle.json').read_text())['cabin_access_candidate']
    cfg = {**cfg, 'doors': copy.deepcopy(access['doors'])}
    a = json.loads(gzip.decompress((OUT / 'source/assembly.json.gz').read_bytes()))
    collision = json.loads((OLD / 'physics/interior_contacts.json').read_text())
    collision['mask'] = 16 | 32
    collision['shapes'] += access['wall_contacts']
    collision['scope'] = 'Actual floor/fixtures and partitioned hollow wall/window contacts. Door bodies use separate moving leaf/handle proxies. Hinge mating is represented by the scalar joint, not detailed bearing surface contacts.'
    root = E.parse(OLD / 'physics/suspended.xml').getroot()
    flag = root.find('option/flag')
    if flag is None:
        flag = E.SubElement(root.find('option'), 'flag')
    flag.set('filterparent', 'disable')
    front = root.find(".//body[@name='front']")
    # All old floor shapes remain geometrically identical; enable door pairs.
    for geom in front.findall('geom'):
        if geom.get('name', '').startswith('interior_'):
            geom.set('conaffinity', str(16 | 32))
    asset = root.find('asset')
    count = 0

    def geom(body, item, datum, layer, mask):
        nonlocal count
        attrs = dict(name='access_' + item['name'], mass='0', group='4', contype=str(layer), conaffinity=str(mask), friction='.8 .002 .0002', rgba='.45 .5 .45 1')
        if item['type'] == 'box':
            attrs.update(type='box', pos=fmt(np.array(item['center_source_m']) - datum), size=fmt(np.array(item['size_m']) / 2))
        else:
            name = f'access_mesh_{count}'
            E.SubElement(asset, 'mesh', name=name, vertex=fmt((np.array(item['vertices_source_m']) - datum).ravel()))
            attrs.update(type='mesh', mesh=name)
        E.SubElement(body, 'geom', **attrs)
        count += 1

    for item in access['wall_contacts']:
        geom(front, item, np.array(collision['datum_source_m']), 8, 16 | 32)
    actuators = root.find('actuator')
    for door in cfg['doors']:
        pivot = np.array(door['pivot_source_m'])
        body = E.SubElement(front, 'body', name=door['name'], pos=fmt(pivot - np.array(collision['datum_source_m'])))
        E.SubElement(body, 'inertial', mass=str(door['mass_kg']), pos=fmt(door['com_local_m']), diaginertia=fmt(door['inertia_diagonal_kg_m2']))
        E.SubElement(body, 'joint', name=door['name'], type='hinge', axis=fmt(door['axis_source']), limited='true', range=fmt(door['limits_rad']), damping='0', solreflimit='.01 1')
        E.SubElement(actuators, 'motor', name='drive_' + door['name'], joint=door['name'], ctrllimited='true', ctrlrange=fmt([-cfg['open_torque_limit_Nm'], cfg['open_torque_limit_Nm']]))
        for p in a['parts']:
            if p['group'] == door['name'] and p['name'].endswith(('bridge_door_handle', 'bridge_door_lock')):
                door['contacts'].append(dict(name=p['name'], body=door['name'], type='convex', vertices_source_m=mesh(p).convex_hull.vertices.tolist()))
        door['collision'] = dict(body=door['name'], datum_source_m=pivot.tolist(), layer=32, mask=8 | 16 | 32, friction_coefficient=.8, shapes=door['contacts'])
        for contact in door['contacts']:
            geom(body, contact, pivot, 32, 8 | 16 | 32)
    E.indent(root)
    E.ElementTree(root).write(OUT / 'physics/suspended.xml', encoding='unicode')
    parameters = json.loads((OLD / 'physics/parameters.json').read_text())
    parameters['total_mass_kg'] += sum(d['mass_kg'] for d in cfg['doors'])
    parameters['access'] = cfg
    parameters['interior'] = collision
    (OUT / 'physics/parameters.json').write_text(json.dumps(parameters, indent=2) + '\n')
    (OUT / 'physics/interior_contacts.json').write_text(json.dumps(collision, indent=2) + '\n')
    env = Env('flat', False, True, OUT / 'physics/suspended.xml', parameters)
    export_environment(env, OUT / 'physics/native_spec.json')
    spec = json.loads((OUT / 'physics/native_spec.json').read_text())
    for joint in spec['joints']:
        if joint['name'].startswith('cabin_door_'):
            joint['access'] = True
    (OUT / 'physics/native_spec.json').write_text(json.dumps(spec, indent=2) + '\n')
    bindings = json.loads((OLD / 'bindings.json').read_text())
    interior=json.loads(Path(bindings['interior_manifest']).read_text())
    interior['doors']=cfg['doors'];interior['scope']='Actual hollow cabin with six separately driven doors; robot task and end-to-end boarding remain unverified.'
    (OUT/'source/interior.json').write_text(json.dumps(interior,indent=2)+'\n')
    for door in cfg['doors']:
        bindings['groups'][door['name']] = dict(pivot_source_m=door['pivot_source_m'], neutral_body_position_source_m=door['pivot_source_m'])
    bindings.update(glb=str(OUT / 'assets/leviathan003_access.glb'), native_blend=str(OUT / 'source/Leviathan_003_access.blend'),
                    expected_meshes=access['render_meshes'], expected_groups=len(a['groups']), interior_manifest=str(OUT/'source/interior.json'), interior_contacts=str(OUT / 'physics/interior_contacts.json'), access_manifest=str(OUT / 'source/access.json'),
                    scope='Full r025 carrier with six finite driven doors and partitioned cabin contacts. r024 original-palette enamel/ink style. Robot policies and full boarding remain incomplete.')
    bindings.pop('sha256',None)
    (OUT / 'bindings.json').write_text(json.dumps(bindings, indent=2) + '\n')
    for name in ['sai_scale_figure.glb', 'microduck_scale_figure.glb']:
        shutil.copyfile(ROOT / 'candidates/r023_interior/assets' / name, OUT / 'assets' / name)
    print(dict(bodies=env.m.nbody - 1, dofs=env.m.nv, actuators=env.m.nu, total_mass_kg=env.total_mass, added_shapes=count))


if __name__ == '__main__':
    main()
