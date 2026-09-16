"""Publish authored floor/fixture contacts in both existing engine formats.

The hollow shell is deliberately not treated as one convex collider: that would
fill the room. Wall/door contact partition and actuation remain follow-up work.
"""
from pathlib import Path
import copy,gzip,json,hashlib
import xml.etree.ElementTree as E
import numpy as np
from suspension_physics import ROOT
OUT=ROOT/'candidates/r023_interior'
def main():
    c=json.loads((ROOT/'design/vehicle.json').read_text())['bridge_interior_candidate'];previous=ROOT/'candidates/r022_runtime';a=json.loads(gzip.decompress((OUT/'source/assembly.json.gz').read_bytes()));inside=json.loads((OUT/'source/interior.json').read_text());binding=json.loads((previous/'bindings.json').read_text())
    contacts=copy.deepcopy(inside['contacts'])
    for p in a['parts']:
        if p['name'].endswith(('bridge_walkdeck','bridge_upper_landing')):
            v=np.array(p['vertices']);lo,hi=v.min(0),v.max(0);contacts.append(dict(name=p['name'],body='front',type='box',center_source_m=((lo+hi)/2).tolist(),size_m=(hi-lo).tolist()))
    collision=dict(body='front',datum_source_m=binding['groups']['front']['neutral_body_position_source_m'],layer=8,mask=16,friction_coefficient=c['floor_friction_coefficient'],native_project_settings={'physics/jolt_physics_3d/simulation/body_pair_contact_cache_enabled':c['native_contact_cache_enabled']},shapes=contacts,scope='Authored continuous floor, flush thresholds, exterior upper galleries and fixed furniture. No wall/glass/door collision partition, lower stairs, lift, robot actuation or whole-game contact-transfer claim.')
    (OUT/'physics/interior_contacts.json').write_text(json.dumps(collision,indent=2)+'\n')
    root=E.parse(previous/'physics/suspended.xml').getroot();body=root.find(".//body[@name='front']");asset=root.find('asset')
    if asset is None:asset=E.SubElement(root,'asset')
    datum=np.array(collision['datum_source_m']);fmt=lambda x:' '.join(format(float(y),'.15g') for y in x)
    for i,contact in enumerate(contacts):
        attrs=dict(name='interior_'+contact['name'],contype='8',conaffinity='16',group='4',mass='0',rgba='.3 .45 .4 1',friction=str(c['floor_friction_coefficient'])+' .002 .0002')
        if contact['type']=='box':attrs.update(type='box',pos=fmt(np.array(contact['center_source_m'])-datum),size=fmt(np.array(contact['size_m'])/2))
        else:
            name=f'interior_convex_{i}';E.SubElement(asset,'mesh',name=name,vertex=fmt((np.array(contact['vertices_source_m'])-datum).ravel()));attrs.update(type='mesh',mesh=name)
        E.SubElement(body,'geom',**attrs)
    E.indent(root);E.ElementTree(root).write(OUT/'physics/suspended.xml',encoding='unicode')
    spec=json.loads((previous/'physics/native_spec.json').read_text());spec['contact']['interior']=collision;(OUT/'physics/native_spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    (OUT/'physics/parameters.json').write_bytes((previous/'physics/parameters.json').read_bytes())
    binding.update(glb=str(OUT/'assets/leviathan003_interior.glb'),native_blend=str(OUT/'source/Leviathan_003_interior.blend'),expected_meshes=inside['render_meshes'],native_project_settings=collision['native_project_settings'],interior_manifest=str(OUT/'source/interior.json'),interior_contacts=str(OUT/'physics/interior_contacts.json'),scope=inside['scope']+' Full r022 dynamic belt display preserved.')
    binding['sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'assets/leviathan003_interior.glb',OUT/'physics/native_spec.json',OUT/'physics/suspended.xml',OUT/'source/interior.json',Path(binding['shader']),Path(binding['path_extension']),Path(__file__)]}
    (OUT/'bindings.json').write_text(json.dumps(binding,indent=2)+'\n');print(len(contacts),'floor/fixture shapes; unchanged explicit mass/inertia and force model')
if __name__=='__main__':main()
