"""Actual native vehicle cases plus pressure, inventory and shared-power gates."""
import argparse,json,concurrent.futures
import numpy as np
import check_running_gear_contact as cases
from suspension_physics import ROOT
OUT=ROOT/'candidates/r020_hydraulics'
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['mujoco','godot','compare']);a=p.parse_args();cases.OUT=OUT
    if a.mode=='mujoco':
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
            for row in pool.map(cases.evaluate,cases.CASES):print(row,flush=True)
    elif a.mode=='godot':cases.native()
    else:
        cases.compare();rows={}
        for name in cases.CASES:
            mj=json.loads((OUT/'reports'/(name+'_mujoco.json')).read_text());gd=json.loads((OUT/'reports'/(name+'_godot.json')).read_text());row={}
            for engine,data in [('mujoco',mj),('godot',gd)]:
                state=data['samples'][-1]['hydraulics']
                assert state['valid'] and state['max_pressure_Pa']<=70e6*(1+1e-10) and state['max_pump_power_W']<=1.5e6+1e-6 and state['max_inventory_error_m3']<1e-7
                power=max(s['allocated_drive_power_W']+s['hydraulics']['pump_power_W'] for s in data['samples']);assert power<=180e6*(1+1e-8)
                row[engine]=dict(max_pressure_MPa=state['max_pressure_Pa']/1e6,max_pump_power_W=state['max_pump_power_W'],max_total_sampled_power_W=power,reservoir_range_m3=state['reservoir_range_m3'],oil_inventory_error_m3=state['max_inventory_error_m3'],heat_J=state['heat_J'],relief_volume_m3=state['relief_volume_m3'])
            for field,scale in [('forces_N',6.6e6),('upper_pressure_Pa',70e6),('lower_pressure_Pa',70e6),('gas_volumes_m3',.08),('reservoir_m3',8.)]:
                x=np.array([s['hydraulics'][field] for s in mj['samples']]);y=np.array([s['hydraulics'][field] for s in gd['samples']]);error=float(np.sqrt(np.mean((x-y)**2)));row[field+'_rmse']=error;assert error/scale<.03,(name,field,error)
            rows[name]=row
        (OUT/'reports/hydraulic_vehicle_validation.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
