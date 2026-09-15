extends RefCounted
## Same finite fluid inventory and pressure equations as the source simulator.
var c:Dictionary
var names:Array=[]
var area:float
var annulus:float
var rod_area:float
var gamma:float
var atm:float
var volume:Array=[]
var previous_q:Array=[]
var gas_constant:Array=[]
var vmin:Array=[]
var damping:Array=[]
var forces:Array=[]
var upper:Array=[]
var lower:Array=[]
var force_min:Array=[]
var force_max:Array=[]
var reservoir:float
var inventory:float
var pump_power_W:=0.0
var pump_energy_J:=0.0
var heat_J:=0.0
var relief_volume_m3:=0.0
var makeup_volume_m3:=0.0
var max_pressure_Pa:=0.0
var max_pump_power_W:=0.0
var max_inventory_error_m3:=0.0
var min_reservoir:float
var max_reservoir:float
var pressure_limited_steps:=0
var valid:=true

func configure(config:Dictionary)->void:
	c=config;area=c.cylinders_per_axle*PI*pow(c.bore_diameter_m,2)/4.;annulus=area-c.cylinders_per_axle*PI*pow(c.rod_diameter_m,2)/4.;rod_area=area-annulus;gamma=c.gas_exponent;atm=c.ambient_pressure_Pa
	reservoir=c.initial_reservoir_volume_m3;inventory=reservoir;min_reservoir=reservoir;max_reservoir=reservoir
	for channel in c.channels:
		names.append(channel.joint);damping.append(channel.metering_damping_Ns_m)
		var pressure:float=channel.nominal_force_N/area+atm;var nominal:float=gamma*pressure*area*area/float(channel.linearized_stiffness_N_m)
		var constant:float=pressure*pow(nominal,gamma);gas_constant.append(constant);vmin.append(pow(constant/(float(c.pressure_limit_Pa)+atm),1./gamma))
		volume.append(nominal);previous_q.append(0.);forces.append(0.);upper.append(0.);lower.append(0.);force_min.append(INF);force_max.append(-INF);inventory+=float(c.accumulator_capacity_m3)-nominal

func step(q:Array,dq:Array,dt:float)->void:
	var flows:Array=[];var mechanical_volume:Array=[];var requested:=0.0;var limited:=false
	for i in names.size():
		var delta:float=float(q[i])-float(previous_q[i]);var raw:float=float(volume[i])-area*delta
		var relief:float=maxf(float(vmin[i])-raw,0.);var makeup:float=maxf(raw-float(c.accumulator_capacity_m3),0.)
		mechanical_volume.append(clampf(raw,float(vmin[i]),float(c.accumulator_capacity_m3)))
		reservoir+=relief-makeup-annulus*delta;heat_J+=relief*float(c.pressure_limit_Pa);relief_volume_m3+=relief;makeup_volume_m3+=makeup
		limited=limited or relief>1e-12
		var error:float=float(q[i])-float(c.target_wheel_coordinate_m)
		error=error-signf(error)*float(c.level_deadband_m) if absf(error)>float(c.level_deadband_m) else 0.
		var flow:float=clampf(float(c.level_flow_gain_m2_s)*error,-float(c.level_flow_limit_m3_s),float(c.level_flow_limit_m3_s))
		flow=maxf(flow,-(float(c.accumulator_capacity_m3)-float(mechanical_volume[i]))/dt);flows.append(flow);requested+=float(c.header_pressure_Pa)*maxf(flow,0.)
	var scale:float=minf(1.,float(c.pump_power_limit_W)/maxf(requested,1.));var positive:=0.0;var negative:=0.0
	for i in names.size():
		if float(flows[i])>0:flows[i]*=scale
		positive+=maxf(flows[i],0.)*dt;negative+=maxf(-float(flows[i]),0.)*dt
	var add_scale:float=minf(1.,maxf(reservoir,0.)/maxf(positive,1e-30));var bleed_scale:float=minf(1.,maxf(float(c.reservoir_capacity_m3)-reservoir,0.)/maxf(negative,1e-30))
	pump_power_W=0.
	for i in names.size():
		var flow:float=float(flows[i])*(add_scale if float(flows[i])>0 else bleed_scale)
		var pump_work:float=float(c.header_pressure_Pa)*maxf(flow,0.)*dt;pump_power_W+=pump_work/dt
		var raw:float=float(mechanical_volume[i])-flow*dt;var relief:float=maxf(float(vmin[i])-raw,0.)
		volume[i]=clampf(raw,float(vmin[i]),float(c.accumulator_capacity_m3));reservoir+=relief-flow*dt;relief_volume_m3+=relief
		var before:float=float(gas_constant[i])*pow(mechanical_volume[i],1.-gamma)/(gamma-1.)+atm*float(mechanical_volume[i])
		var after:float=float(gas_constant[i])*pow(volume[i],1.-gamma)/(gamma-1.)+atm*float(volume[i])
		var valve_heat:float=pump_work-(after-before)
		assert(valve_heat>=-1e-5,"Hydraulic supply cannot create stored energy")
		heat_J+=maxf(0.,valve_heat)
		var gas:float=clampf(float(gas_constant[i])/pow(volume[i],gamma)-atm,0.,float(c.pressure_limit_Pa))
		if float(volume[i])>=float(c.accumulator_capacity_m3)-1e-12:gas=0.
		var spring:float=-area*gas;var wanted:float=spring-float(damping[i])*float(dq[i])
		forces[i]=clampf(wanted,-area*float(c.pressure_limit_Pa),annulus*float(c.pressure_limit_Pa))
		heat_J+=maxf(-(float(forces[i])-spring)*float(dq[i]),0.)*dt
		upper[i]=maxf(-float(forces[i]),0.)/area;lower[i]=maxf(forces[i],0.)/annulus
		limited=limited or absf(float(forces[i])-wanted)>1e-5 or relief>1e-12
		force_min[i]=minf(force_min[i],forces[i]);force_max[i]=maxf(force_max[i],forces[i]);max_pressure_Pa=maxf(max_pressure_Pa,maxf(upper[i],lower[i]))
		previous_q[i]=q[i]
	var current_inventory:float=reservoir
	for i in names.size():current_inventory+=float(c.accumulator_capacity_m3)-float(volume[i])-rod_area*float(q[i])
	max_inventory_error_m3=maxf(max_inventory_error_m3,absf(current_inventory-inventory));max_pump_power_W=maxf(max_pump_power_W,pump_power_W);pump_energy_J+=pump_power_W*dt
	min_reservoir=minf(min_reservoir,reservoir);max_reservoir=maxf(max_reservoir,reservoir)
	if limited:pressure_limited_steps+=1
	valid=reservoir>=0. and reservoir<=float(c.reservoir_capacity_m3) and max_inventory_error_m3<1e-7
	assert(valid,"Hydraulic circuit outside finite inventory domain")

func state()->Dictionary:
	var energy:=0.0
	for i in names.size():energy+=float(gas_constant[i])/pow(volume[i],gamma)*float(volume[i])/(gamma-1.)+atm*float(volume[i])
	return {"forces_N":forces.duplicate(),"upper_pressure_Pa":upper.duplicate(),"lower_pressure_Pa":lower.duplicate(),"gas_volumes_m3":volume.duplicate(),"reservoir_m3":reservoir,"pump_power_W":pump_power_W,"pump_energy_J":pump_energy_J,"heat_J":heat_J,"gas_energy_J":energy,"relief_volume_m3":relief_volume_m3,"makeup_volume_m3":makeup_volume_m3,"max_inventory_error_m3":max_inventory_error_m3,"max_pressure_Pa":max_pressure_Pa,"max_pump_power_W":max_pump_power_W,"reservoir_range_m3":[min_reservoir,max_reservoir],"all_step_force_min_N":force_min.duplicate(),"all_step_force_max_N":force_max.duplicate(),"pressure_limited_steps":pressure_limited_steps,"valid":valid}
