"""Compile the actual vehicle and cross-check authored floor contacts in engines."""
from pathlib import Path
import json,hashlib,subprocess
import xml.etree.ElementTree as E
import numpy as np
import mujoco
from suspension_physics import ROOT
OUT=ROOT/'candidates/r023_interior'
def main():
    m=mujoco.MjModel.from_xml_path(str(OUT/'physics/suspended.xml'));d=mujoco.MjData(m);mujoco.mj_forward(m,d)
    old=mujoco.MjModel.from_xml_path(str(ROOT/'candidates/r022_runtime/physics/suspended.xml'))
    for field in ['body_mass','body_inertia','body_ipos','jnt_range','jnt_axis','actuator_gear','actuator_ctrlrange','actuator_forcerange']:assert np.array_equal(getattr(m,field),getattr(old,field)),field
    assert (m.nbody,m.nv,m.nu)==(old.nbody,old.nv,old.nu)
    c=json.loads((OUT/'physics/interior_contacts.json').read_text());f=11.35;points=[[x,0,f] for x in [18,20,22,24,26,28,30,32]]
    for side in [-1,1]:
        for x in [19.15,23.15,25.05]:
            for y in [3.25,3.42,3.75,4.4]:points.append([x,side*y,f])
    rays=[];group=np.zeros(6,np.uint8);group[4]=1;front=m.body('front').id
    for p in points:
        expected=d.xpos[front]+np.array(p)-np.array(c['datum_source_m']);gid=np.array([-1],dtype=np.int32)
        distance=mujoco.mj_ray(m,d,expected+[0,0,.1],np.array([0.,0.,-1.]),group,1,-1,gid)
        rays.append(dict(source_point=p,distance=float(distance),error_m=abs(float(distance)-.1),geom_id=int(gid[0])))
        assert distance>=0 and abs(distance-.1)<1e-5
    data={'contact':c,'points':points};(OUT/'reports/contact_component_input.json').write_text(json.dumps(data,indent=2)+'\n')
    # Reuse the compiled vehicle's actual authored geoms/assets in a fixed
    # component frame; no guessed floor proxy is substituted for the test.
    source=E.parse(OUT/'physics/suspended.xml').getroot();root=E.Element('mujoco',model='interior_contact_component');E.SubElement(root,'compiler',angle='radian');E.SubElement(root,'option',timestep='.005',gravity='0 0 -9.81',integrator='implicitfast')
    asset=source.find('asset')
    if asset is not None:root.append(asset)
    world=E.SubElement(root,'worldbody');body=E.SubElement(world,'body',name='cabin_frame',pos='0 0 10')
    for geom in source.find(".//body[@name='front']").findall('geom'):
        if geom.get('name','').startswith('interior_'):body.append(geom)
    for i,p in enumerate(points):
        b=E.SubElement(world,'body',name=f'probe_{i}',pos=' '.join(map(str,np.array(p)+[0,0,.09])));E.SubElement(b,'freejoint');E.SubElement(b,'geom',type='sphere',size='.02',mass='.05',contype='16',conaffinity='8',friction='.8 .002 .0002')
    E.indent(root);E.ElementTree(root).write(OUT/'reports/contact_component.xml',encoding='unicode')
    cm=mujoco.MjModel.from_xml_path(str(OUT/'reports/contact_component.xml'));cd=mujoco.MjData(cm)
    for _ in range(600):mujoco.mj_step(cm,cd)
    mj=[]
    for i,p in enumerate(points):
        bid=cm.body(f'probe_{i}').id;adr=cm.jnt_dofadr[cm.body_jntadr[bid]];mj.append(dict(source_position=cd.xpos[bid].tolist(),velocity_m_s=float(np.linalg.norm(cd.qvel[adr:adr+3])),height_error_m=float(cd.xpos[bid,2]-p[2]-.02)))
    project=Path('/home/ethan/Projects/Robot_Godot_Sim2Sim/main/results/leviathan003/runtime/project.godot');saved=project.read_bytes()
    assert c['native_project_settings']['physics/jolt_physics_3d/simulation/body_pair_contact_cache_enabled'] is False
    assert 'body_pair_contact_cache_enabled=' not in saved.decode()
    try:
        project.write_text(saved.decode().replace('[physics]','[physics]\n\njolt_physics_3d/simulation/body_pair_contact_cache_enabled=false'))
        with (OUT/'reports/contact_component_godot.log').open('w') as log:
            subprocess.run(['/home/ethan/.local/bin/godot','--headless','--path','/home/ethan/Projects/Robot_Godot_Sim2Sim/main/results/leviathan003/runtime','--script',str(ROOT/'godot/interior_contact_bench.gd'),'--',str(OUT/'reports/contact_component_input.json'),str(OUT/'reports/contact_component_godot.json')],check=True,timeout=30,stdout=log,stderr=subprocess.STDOUT)
    finally:project.write_bytes(saved)
    gd=json.loads((OUT/'reports/contact_component_godot.json').read_text());maximum={}
    for name,rows in [('mujoco',mj),('godot',gd['samples'])]:
        maximum[name]=dict(height_error_m=max(abs(s['height_error_m']) for s in rows),speed_m_s=max(s['velocity_m_s'] for s in rows));assert maximum[name]['height_error_m']<.002 and maximum[name]['speed_m_s']<.02
    report=dict(passed=True,native_project_settings=c['native_project_settings'],runtime_restored=project.read_bytes()==saved,compiled_vehicle=dict(bodies=m.nbody-1,dofs=m.nv,actuators=m.nu,added_contact_shapes=len(c['shapes']),mass_inertia_joints_actuators_unchanged=True),mujoco_floor_rays=rays,component_maxima=maximum,mujoco_component_samples=mj,godot_gravity=gd['gravity_m_s2'],scope='Actual vehicle compiles and includes 35 floor/furniture collision shapes. Static-floor contact component with 32 small sphere probes in both engines; this is not Sai/MicroDuck locomotion, wall/door interaction or moving-carrier load transfer.',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'godot/interior_contacts.gd',ROOT/'godot/interior_contact_bench.gd',OUT/'physics/suspended.xml',OUT/'physics/native_spec.json']})
    (OUT/'reports/interior_contacts_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(maximum,indent=2))
if __name__=='__main__':main()
