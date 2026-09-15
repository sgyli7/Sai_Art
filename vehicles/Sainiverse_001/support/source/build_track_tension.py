"""Add actual idler bodies and passive belt coupling, preserving r020 inputs."""
import json,hashlib,math
from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np,mujoco
from suspension_physics import ROOT,U,C,V,Env,fmt
from export_suspension_native import export_environment
from track_tension import envelope
OUT=ROOT/'candidates/r021_track_tension'
def main():
    for name in ['physics','source','assets','reports']:(OUT/name).mkdir(parents=True,exist_ok=True)
    old=ROOT/'candidates/r020_hydraulics/physics';tree=E.parse(old/'suspended.xml');root=tree.getroot();m=json.loads((old/'parameters.json').read_text())
    gear=json.loads((ROOT/'assets/running_gear.json').read_text());w=np.array(U['wheels_x_z_radius']);w[:,2]+=U['belt_centerline_clearance'];length,grad,_=envelope(w)
    c=V['track_tension_candidate'];stiffness=c['belt_stiffness_N_m'];preload=stiffness*(length-gear['perimeter'])*grad[4,0];belts=[];added_mass=0.
    for bogie in m['bogies']:
        parent=root.find(f".//body[@name='{bogie}']")
        for side,y in [('right',-1.75),('left',1.75)]:
            name=bogie+'_idler_'+side;radius=U['wheels_x_z_radius'][4][2];mass=c['idler_effective_mass_kg'];pos=[4.15,y,2.4-C['bogie_pivot_z_m']]
            b=E.SubElement(parent,'body',name=name,pos=fmt(pos));E.SubElement(b,'inertial',pos='0 0 0',mass=str(mass),diaginertia=fmt([mass*(3*radius**2+1.6**2)/12,mass*radius**2/2,mass*(3*radius**2+1.6**2)/12]))
            E.SubElement(b,'joint',name=name,type='slide',axis='1 0 0',range=fmt(c['idler_travel_m']),stiffness='0',damping='0',solreflimit='.01 1',solimplimit='.99 .999 .001')
            E.SubElement(b,'geom',type='sphere',size=str(radius),mass='0',contype='0',conaffinity='0')
            matches=[x for x in m['contacts'] if x['body']==bogie and np.allclose(x['local'],pos)]
            assert len(matches)==1;matches[0]['body']=name;matches[0]['local']=[0,0,0]
            belts.append(dict(bogie=bogie,side=side,joints=[bogie+f'_wheel_{side}_{i}' for i in [1,2,3]]+[name]));added_mass+=mass
    m['total_mass_kg']+=added_mass
    m['track_tension']=dict(belts=belts,support_circles_x_z_radius_m=w.tolist(),natural_length_m=gear['perimeter'],belt_stiffness_N_m=stiffness,belt_damping_Ns_m=c['belt_damping_Ns_m'],tension_limit_N=c['tension_limit_N'],recoil_preload_N=preload,recoil_stiffness_N_m=c['recoil_stiffness_N_m'],recoil_damping_Ns_m=c['recoil_damping_Ns_m'],recoil_force_limit_N=c['recoil_force_limit_N'],idler_travel_m=c['idler_travel_m'],
        scope='Elastic taut-disc convex envelope, finite passive recoil, actual +X sliding idler per belt. Wheel-supported terrain contacts remain reduced. No chain pin, free-span terrain contact, derailment or rated recoil hardware. 12000 kg per new moving idler is provisional, using the existing road-wheel effective-mass class; prior frame masses retained, so total mass rises 288000 kg and is not a CAD-derived allocation.')
    path=OUT/'physics/suspended.xml';path.write_text(E.tostring(root,encoding='unicode'));(OUT/'physics/parameters.json').write_text(json.dumps(m,indent=2)+'\n')
    env=Env('flat',False,True,path,m);export_environment(env,OUT/'physics/native_spec.json')
    report=dict(dynamic_bodies=env.m.nbody-1,dofs=env.m.nv,actuators=env.m.nu,belts=len(belts),added_idler_effective_mass_kg=added_mass,total_mass_kg=env.total_mass,nominal_envelope_length_m=length,natural_length_m=gear['perimeter'],nominal_tension_N=stiffness*(length-gear['perimeter']),recoil_preload_N=preload,scope=m['track_tension']['scope'],source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'source/track_tension.py',ROOT/'design/vehicle.json',old/'parameters.json',old/'suspended.xml']})
    (OUT/'reports/build.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
