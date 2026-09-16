"""Finite pressure accumulator banks, metering losses and shared oil inventory.

Gas is adiabatic (design assumption), oil incompressible, lines quasi-static.
Relief, replenishment and leveling flows update volume; no unlimited force.
"""
import numpy as np

class HydraulicSuspension:
    def __init__(self,config):
        self.c=config;self.names=[c['joint'] for c in config['channels']]
        self.area=config['cylinders_per_axle']*np.pi*config['bore_diameter_m']**2/4
        self.annulus=self.area-config['cylinders_per_axle']*np.pi*config['rod_diameter_m']**2/4
        self.rod_area=self.area-self.annulus;self.gamma=config['gas_exponent'];self.atm=config['ambient_pressure_Pa']
        load=np.array([c['nominal_force_N'] for c in config['channels']]);k=np.array([c['linearized_stiffness_N_m'] for c in config['channels']])
        self.damping=np.array([c['metering_damping_Ns_m'] for c in config['channels']])
        self.p0=load/self.area+self.atm;self.v0=self.gamma*self.p0*self.area**2/k
        self.constant=self.p0*self.v0**self.gamma;self.vmin=(self.constant/(config['pressure_limit_Pa']+self.atm))**(1/self.gamma)
        self.volume=self.v0.copy();self.previous_q=np.zeros(len(load));self.reservoir=config['initial_reservoir_volume_m3']
        self.inventory=self.reservoir+np.sum(config['accumulator_capacity_m3']-self.volume)
        self.force=np.zeros(len(load));self.upper_pressure=np.zeros(len(load));self.lower_pressure=np.zeros(len(load));self.pump_power_W=0.
        self.heat_J=0.;self.pump_energy_J=0.;self.relief_volume_m3=0.;self.makeup_volume_m3=0.
        self.max_pressure_Pa=0.;self.max_pump_power_W=0.;self.max_inventory_error_m3=0.;self.min_reservoir=self.reservoir;self.max_reservoir=self.reservoir
        self.force_min=np.full(len(load),np.inf);self.force_max=np.full(len(load),-np.inf);self.pressure_limited_steps=0;self.valid=True

    def step(self,q,dq,dt):
        c=self.c;q=np.asarray(q);dq=np.asarray(dq)
        delta=q-self.previous_q
        # First displace fluid with actual piston travel. Relief oil returns to
        # the tank; an empty accumulator takes atmospheric makeup oil.
        raw=self.volume-self.area*delta
        relief=np.maximum(self.vmin-raw,0.);makeup=np.maximum(raw-c['accumulator_capacity_m3'],0.)
        mechanical_volume=np.clip(raw,self.vmin,c['accumulator_capacity_m3'])
        self.reservoir+=float(np.sum(relief-makeup)-self.annulus*np.sum(delta))
        self.heat_J+=float(relief.sum())*c['pressure_limit_Pa']
        self.relief_volume_m3+=float(relief.sum());self.makeup_volume_m3+=float(makeup.sum())
        error=q-c['target_wheel_coordinate_m'];error=np.where(abs(error)>c['level_deadband_m'],error-np.sign(error)*c['level_deadband_m'],0.)
        flow=np.clip(c['level_flow_gain_m2_s']*error,-c['level_flow_limit_m3_s'],c['level_flow_limit_m3_s'])
        # Bleeding an empty bank cannot release oil or generate heat.
        flow=np.maximum(flow,-(c['accumulator_capacity_m3']-mechanical_volume)/dt)
        header=c['header_pressure_Pa'];requested=header*float(np.maximum(flow,0.).sum())
        scale=min(1.,c['pump_power_limit_W']/max(requested,1.));flow=np.where(flow>0,flow*scale,flow)
        positive=float(np.maximum(flow,0.).sum())*dt;negative=float(np.maximum(-flow,0.).sum())*dt
        if positive>max(self.reservoir,0.):flow=np.where(flow>0,flow*max(self.reservoir,0.)/positive,flow)
        if negative>max(c['reservoir_capacity_m3']-self.reservoir,0.):flow=np.where(flow<0,flow*max(c['reservoir_capacity_m3']-self.reservoir,0.)/negative,flow)
        self.pump_power_W=header*float(np.maximum(flow,0.).sum());pump_work=self.pump_power_W*dt;self.pump_energy_J+=pump_work
        raw=mechanical_volume-flow*dt;pump_relief=np.maximum(self.vmin-raw,0.)
        self.volume=np.clip(raw,self.vmin,c['accumulator_capacity_m3'])
        self.reservoir+=float(np.sum(pump_relief-flow*dt));self.relief_volume_m3+=float(pump_relief.sum())
        def energy(v):return self.constant*v**(1-self.gamma)/(self.gamma-1)+self.atm*v
        # Fixed-pressure header supply: stored gas energy is integrated exactly
        # over the pumped volume; the remaining work is throttling/relief heat.
        stored=float(np.sum(energy(self.volume)-energy(mechanical_volume)))
        valve_heat=pump_work-stored
        assert valve_heat>=-1e-5,'Hydraulic supply cannot create stored energy'
        self.heat_J+=max(0.,valve_heat)
        relief+=pump_relief
        gas=np.clip(self.constant/self.volume**self.gamma-self.atm,0.,c['pressure_limit_Pa'])
        # Empty accumulators cannot drive a cylinder at precharge pressure.
        # Makeup oil comes from the atmospheric tank; compression/pumping must
        # refill the accumulator before stored gas can do mechanical work.
        gas=np.where(self.volume>=c['accumulator_capacity_m3']-1e-12,0.,gas)
        spring=-self.area*gas;requested_force=spring-self.damping*dq
        self.force=np.clip(requested_force,-self.area*c['pressure_limit_Pa'],self.annulus*c['pressure_limit_Pa'])
        damping=self.force-spring;self.heat_J+=float(np.sum(np.maximum(-damping*dq,0.)))*dt
        self.upper_pressure=np.maximum(-self.force,0.)/self.area;self.lower_pressure=np.maximum(self.force,0.)/self.annulus
        self.pressure_limited_steps+=int(np.any(abs(self.force-requested_force)>1e-5) or np.any(relief>1e-12))
        inventory=self.reservoir+np.sum(c['accumulator_capacity_m3']-self.volume-self.rod_area*q)
        self.max_inventory_error_m3=max(self.max_inventory_error_m3,abs(float(inventory-self.inventory)))
        self.max_pressure_Pa=max(self.max_pressure_Pa,float(max(self.upper_pressure.max(),self.lower_pressure.max())))
        self.max_pump_power_W=max(self.max_pump_power_W,self.pump_power_W);self.min_reservoir=min(self.min_reservoir,self.reservoir);self.max_reservoir=max(self.max_reservoir,self.reservoir)
        self.force_min=np.minimum(self.force_min,self.force);self.force_max=np.maximum(self.force_max,self.force);self.previous_q=q.copy()
        self.valid=bool(0<=self.reservoir<=c['reservoir_capacity_m3'] and self.max_inventory_error_m3<1e-7 and np.all(np.isfinite(self.force)))
        if not self.valid:raise RuntimeError('Hydraulic circuit outside its finite inventory domain')
        return self.force

    def record(self):
        gas_absolute=self.constant/self.volume**self.gamma
        return dict(forces_N=self.force.tolist(),upper_pressure_Pa=self.upper_pressure.tolist(),lower_pressure_Pa=self.lower_pressure.tolist(),gas_volumes_m3=self.volume.tolist(),
            reservoir_m3=self.reservoir,pump_power_W=self.pump_power_W,pump_energy_J=self.pump_energy_J,heat_J=self.heat_J,
            gas_energy_J=float(np.sum(gas_absolute*self.volume/(self.gamma-1)+self.atm*self.volume)),
            relief_volume_m3=self.relief_volume_m3,makeup_volume_m3=self.makeup_volume_m3,max_inventory_error_m3=self.max_inventory_error_m3,
            max_pressure_Pa=self.max_pressure_Pa,max_pump_power_W=self.max_pump_power_W,reservoir_range_m3=[self.min_reservoir,self.max_reservoir],
            all_step_force_min_N=self.force_min.tolist(),all_step_force_max_N=self.force_max.tolist(),pressure_limited_steps=self.pressure_limited_steps,valid=self.valid)
