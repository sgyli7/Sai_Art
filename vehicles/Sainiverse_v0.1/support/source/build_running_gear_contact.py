"""Reconcile reduced contacts with measured authored cleats; preserve r017."""
from pathlib import Path
import copy,gzip,hashlib,json
import xml.etree.ElementTree as E
import mujoco,numpy as np
from suspension_physics import ROOT,Env,C,fmt,U
from export_suspension_native import export_environment

OUT=ROOT/'candidates/r019_running_gear'
def build():
    for folder in ['physics','source','assets','reports']:(OUT/folder).mkdir(parents=True,exist_ok=True)
    authored=ROOT/'candidates/r016_modular/train_containers_first/source/assembly.json.gz'
    a=json.loads(gzip.decompress(authored.read_bytes()));rows=[]
    lower_wheel_bottoms=[z-r for x,z,r in U['wheels_x_z_radius'][1:4]]
    assert np.ptp(lower_wheel_bottoms)<1e-9
    for group,pivot in a['groups'].items():
        if '_bogie_' not in group:continue
        parts=[p for p in a['parts'] if p['group']==group and p['motion']['kind']=='belt']
        for side in [-1,1]:
            vertices=np.concatenate([np.array(p['vertices']) for p in parts if np.sign(np.mean(np.array(p['vertices'])[:,1])-pivot[1])==side])
            bottom=float(vertices[:,2].min());skin=lower_wheel_bottoms[0]-bottom
            rows.append(dict(bogie=group,side=side,authored_lowest_z_m=bottom,outer_skin_m=skin))
    assert len(rows)==24 and np.ptp([r['outer_skin_m'] for r in rows])<1e-9
    skin=rows[0]['outer_skin_m'];delta=skin-C['track_contact_skin_m']
    old_path=ROOT/'candidates/r017_turning/physics/suspended.xml';old_manifest=ROOT/'candidates/r017_turning/physics/parameters.json'
    manifest=json.loads(old_manifest.read_text());root=E.parse(old_path).getroot()
    front=root.find("./worldbody/body[@name='front']");position=np.fromstring(front.get('pos'),sep=' ');old_height=float(position[2]);position[2]+=delta;front.set('pos',fmt(position))
    for contact in manifest['contacts']:contact['radius']+=delta
    manifest['config_overrides']={'track_contact_skin_m':skin}
    manifest['contact_geometry_revision']='r019 measured cleat envelope; original nominal 0.04 m compliant contact retained'
    path=OUT/'physics/suspended.xml';path.write_text(E.tostring(root,encoding='unicode'))
    (OUT/'physics/parameters.json').write_text(json.dumps(manifest,indent=2)+'\n')
    env=Env('flat',False,True,path,manifest);export_environment(env,OUT/'physics/native_spec.json')
    old=mujoco.MjModel.from_xml_path(str(old_path));assert env.m.nbody==old.nbody and env.m.nu==old.nu and env.m.nv==old.nv
    for key in ['body_mass','body_inertia','jnt_range','jnt_stiffness','dof_damping','actuator_ctrlrange']:assert np.array_equal(getattr(old,key),getattr(env.m,key)),key
    report=dict(measured_belts=rows,old_contact_skin_m=C['track_contact_skin_m'],new_contact_skin_m=skin,root_height_before_m=old_height,root_height_after_m=float(position[2]),
        geometry_contact_offset_removed_m=delta,remaining_nominal_contact_deflection_m=C['contact_deflection_at_nominal_load_m'],
        invariant_fields=['body_mass','body_inertia','jnt_range','jnt_stiffness','dof_damping','actuator_ctrlrange'],
        scope='Contact-envelope correction only. Source geometry and trained gains unchanged; no belt tensioner or axle-carrier acceptance.',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),authored,old_path,old_manifest,ROOT/'source/export_suspension_native.py']})
    (OUT/'reports/contact_geometry.json').write_text(json.dumps(report,indent=2)+'\n');print('contact skin',skin,'root z',position[2]);return path,manifest
if __name__=='__main__':build()
