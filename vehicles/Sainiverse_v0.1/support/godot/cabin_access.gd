extends RefCounted
## Independent native counterpart of the finite door servo.
var c:Dictionary
var names:Array=[]
var requests:Array=[]
var targets:Array=[]
var torques:Array=[]
var latched:Array=[]
var latch_torques:Array=[]
var stalled:Array=[]
var obstructed:Array=[]
var angles:Array=[]
var rates:Array=[]
var power:=0.0
var drive_permitted:=false
var drive_closed_rate_limit_rad_s:=.02
func configure(config:Dictionary)->void:
	c=config
	for door in c.doors:names.append(door.name)
	for a in [targets,torques,stalled,angles,rates,latch_torques]:a.resize(names.size());a.fill(0.)
	for a in [requests,obstructed]:a.resize(names.size());a.fill(false)
	latched.resize(names.size());latched.fill(true)
func step(q:Array,dq:Array,speed:float,dt:float)->void:
	angles=q.duplicate();rates=dq.duplicate();power=0.;drive_permitted=true
	for i in names.size():
		if requests[i] and absf(speed)<=float(c.opening_vehicle_speed_limit_m_s):
			latched[i]=false
			targets[i]=deg_to_rad(float(c.maximum_open_deg));obstructed[i]=false
		elif not requests[i] and not obstructed[i]:targets[i]=0.
		var closing:bool=float(targets[i])<float(q[i])-.001
		var rate:=clampf(float(c.position_gain_s_inv)*(float(targets[i])-float(q[i])),-float(c.maximum_angular_speed_rad_s),float(c.maximum_angular_speed_rad_s))
		var limit:float=c.close_torque_limit_Nm if closing else c.open_torque_limit_Nm
		limit=minf(limit,float(c.motor_power_limit_W)/maxf(absf(float(dq[i])),.001))
		var torque:=clampf(float(c.velocity_gain_Nms_rad)*(rate-float(dq[i])),-limit,limit)
		var stopped:bool=closing and float(q[i])>.07 and absf(float(dq[i]))<.005 and absf(torque)>.95*float(c.close_torque_limit_Nm)
		stalled[i]=float(stalled[i])+dt if stopped else 0.
		if float(stalled[i])>=.4:obstructed[i]=true;targets[i]=q[i];torque=0.
		if not requests[i] and not obstructed[i] and absf(float(q[i]))<float(c.latch_capture_angle_rad) and absf(float(dq[i]))<float(c.latch_capture_speed_rad_s):latched[i]=true
		latch_torques[i]=clampf(-float(c.latch_stiffness_Nm_rad)*float(q[i])-float(c.latch_damping_Nms_rad)*float(dq[i]),-float(c.latch_torque_limit_Nm),float(c.latch_torque_limit_Nm)) if latched[i] else 0.
		if latched[i]:torque=0.
		torques[i]=torque;power+=maxf(torque*float(dq[i]),0.)
		drive_permitted=drive_permitted and latched[i] and not requests[i] and not obstructed[i] and absf(float(q[i]))<.015 and absf(float(dq[i]))<drive_closed_rate_limit_rad_s
func state()->Dictionary:
	return {"angles_rad":angles.duplicate(),"angular_rates_rad_s":rates.duplicate(),"targets_rad":targets.duplicate(),"torques_Nm":torques.duplicate(),"obstructed":obstructed.duplicate(),"power_W":power,"drive_permitted":drive_permitted,"latched":latched.duplicate(),"latch_torques_Nm":latch_torques.duplicate()}
