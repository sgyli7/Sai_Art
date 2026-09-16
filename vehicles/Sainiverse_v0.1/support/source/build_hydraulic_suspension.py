"""Replace 72 unlimited linear joint springs with finite fluid/gas banks."""
from pathlib import Path
import hashlib,json,math
import xml.etree.ElementTree as E
import mujoco,numpy as np
from suspension_physics import ROOT,Env
from export_suspension_native import export_environment
OUT=ROOT/'candidates/r020_hydraulics'
def main():
    for folder in ['physics','reports','source','assets']:(OUT/folder).mkdir(parents=True,exist_ok=True)
    baseline=ROOT/'candidates/r019_running_gear/physics';root=E.parse(baseline/'suspended.xml').getroot();manifest=json.loads((baseline/'parameters.json').read_text());channels=[]
    for name in manifest['wheels']:
        j=root.find(f".//joint[@name='{name}']");k=float(j.get('stiffness'));d=float(j.get('damping'));rest=float(j.get('springref'))
        channels.append(dict(joint=name,linearized_stiffness_N_m=k,metering_damping_Ns_m=d,nominal_force_N=-k*rest))
        j.set('stiffness','0');j.set('damping','0')
    c=dict(channels=channels,cylinders_per_axle=3,bore_diameter_m=.20,rod_diameter_m=.15,pressure_limit_Pa=70e6,header_pressure_Pa=70e6,ambient_pressure_Pa=101325.,gas_exponent=1.4,
        accumulator_capacity_m3=.080,initial_reservoir_volume_m3=3.,reservoir_capacity_m3=8.,level_flow_gain_m2_s=.002,level_flow_limit_m3_s=.0002,level_deadband_m=.01,target_wheel_coordinate_m=0.,pump_power_limit_W=1.5e6,
        scope='Custom hydraulic design assumptions: adiabatic gas, incompressible oil, quasi-static lines, metering loss, finite relief pressure, shared finite oil inventory and powered leveling. No production cylinder, thermal/hose-transient or fatigue qualification.')
    manifest['hydraulics']=c;path=OUT/'physics/suspended.xml';path.write_text(E.tostring(root,encoding='unicode'));(OUT/'physics/parameters.json').write_text(json.dumps(manifest,indent=2)+'\n')
    env=Env('flat',False,True,path,manifest);export_environment(env,OUT/'physics/native_spec.json');old=mujoco.MjModel.from_xml_path(str(baseline/'suspended.xml'))
    assert env.m.nbody==old.nbody and env.m.nv==old.nv and env.m.nu==old.nu
    for field in ['body_mass','body_inertia','jnt_range','actuator_ctrlrange']:assert np.array_equal(getattr(env.m,field),getattr(old,field))
    h=env.hydraulics
    report=dict(channels=len(channels),initial_gas_volume_range_m3=[float(h.v0.min()),float(h.v0.max())],initial_gas_gauge_pressure_range_Pa=[float(h.p0.min()-h.atm),float(h.p0.max()-h.atm)],
        push_force_limit_N=h.area*c['pressure_limit_Pa'],pull_force_limit_N=h.annulus*c['pressure_limit_Pa'],total_initial_oil_inventory_m3=float(h.inventory),scope=c['scope'],
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'source/hydraulic_suspension.py',baseline/'suspended.xml',baseline/'parameters.json']})
    (OUT/'reports/build.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':main()
