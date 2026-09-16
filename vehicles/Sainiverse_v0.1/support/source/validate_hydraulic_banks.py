"""Pressure/inventory bounds and an independent work-energy check, not a drive test."""
import copy,json,math,subprocess,hashlib
from pathlib import Path
import numpy as np
from hydraulic_suspension import HydraulicSuspension
from suspension_physics import ROOT
OUT=ROOT/'candidates/r020_hydraulics/reports'
def main():
    cfg=json.loads((OUT.parent/'physics/parameters.json').read_text())['hydraulics'];results={};dt=.005
    for name,amplitude,frequency,pump in [('slow_closed',.05,.5,0.),('pressure_limits',.35,5.,1.5e6),('pump_limit',.35,5.,1e5)]:
        c=copy.deepcopy(cfg);c['pump_power_limit_W']=pump
        if name=='slow_closed':c['level_flow_gain_m2_s']=0.
        h=HydraulicSuspension(c);initial=h.record()['gas_energy_J'];work=0.;prior_q=np.zeros(72);prior_f=None;samples=[]
        for i in range(4001):
            t=i*dt;q=np.full(72,amplitude*math.sin(2*math.pi*frequency*t));dq=np.full(72,amplitude*2*math.pi*frequency*math.cos(2*math.pi*frequency*t))
            f=h.step(q,dq,dt)
            if prior_f is not None:work+=float(np.sum(.5*(f+prior_f)*(q-prior_q)))
            prior_f=f.copy();prior_q=q.copy()
            if i%20==0:samples.append(h.record())
        state=h.record();assert state['valid'] and state['max_pressure_Pa']<=c['pressure_limit_Pa']*(1+1e-12) and state['max_pump_power_W']<=pump+1e-6 and state['max_inventory_error_m3']<1e-8
        residual=work+(state['gas_energy_J']-initial)+state['heat_J']-state['pump_energy_J']
        if name=='slow_closed':assert abs(residual)/max(state['heat_J'],1)<.01 and state['relief_volume_m3']==0.
        if name=='pressure_limits':assert min(state['all_step_force_min_N'])<-.999*h.area*c['pressure_limit_Pa'] and max(state['all_step_force_max_N'])>.999*h.annulus*c['pressure_limit_Pa'] and state['relief_volume_m3']>0
        if name=='pump_limit':assert abs(state['max_pump_power_W']-pump)<1e-6
        results[name]=dict(samples=samples,final=state,mechanical_work_J=work,work_energy_residual_J=residual,scope='Prescribed-coordinate component fixture; no vehicle motion claim. Energy gate applies only to the slow closed circuit, not high-rate relief fixtures.')
    (OUT/'component_python.json').write_text(json.dumps(results,indent=2)+'\n')
    with (OUT/'component_godot.log').open('w') as log:
        subprocess.run(['/home/ethan/.local/bin/godot','--headless','--path','/home/ethan/Projects/Robot_Godot_Sim2Sim/main/results/leviathan003/runtime','--script',str(ROOT/'godot/hydraulic_component_bench.gd')],check=True,stdout=log,stderr=subprocess.STDOUT)
    assert 'ERROR:' not in (OUT/'component_godot.log').read_text()
    native=json.loads((OUT/'component_godot.json').read_text());comparisons={}
    for name,result in results.items():
        row={}
        for field in ['forces_N','upper_pressure_Pa','lower_pressure_Pa','gas_volumes_m3','reservoir_m3','pump_power_W','heat_J']:
            left=np.array([s[field] for s in result['samples']]);right=np.array([s[field] for s in native[name]])
            delta=float(np.max(abs(left-right)));row[field+'_max_delta']=delta;assert delta<1e-6*max(1.,float(np.max(abs(left)))),(name,field,delta)
        row['passed']=True;row['slow_energy_relative_residual']=abs(result['work_energy_residual_J'])/max(result['final']['heat_J'],1.) if name=='slow_closed' else None
        row['pressure_max_Pa']=result['final']['max_pressure_Pa'];row['pump_max_W']=result['final']['max_pump_power_W'];row['oil_inventory_error_m3']=result['final']['max_inventory_error_m3'];comparisons[name]=row
    (OUT/'component_validation.json').write_text(json.dumps(comparisons,indent=2)+'\n');print(json.dumps(comparisons,indent=2))
if __name__=='__main__':main()
