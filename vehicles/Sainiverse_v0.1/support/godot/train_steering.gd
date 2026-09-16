extends RefCounted
## Requests only. Native finite actuators and contacts determine actual motion.
var config:Dictionary
var positions:Array=[]
var hitch_yaw:=0.0
var bogie_yaw:Array=[]
var state:Dictionary={}
func configure(c:Dictionary,p:Array)->void:
	config=c;positions=p;bogie_yaw.resize(p.size());bogie_yaw.fill(0.)
func update(speed_request:float,speed:float,curvature_request:float,x:float,y:float,heading:float,dt:float)->Dictionary:
	var half:float=float(config.module_center_spacing_m)/2
	var geometry_limit:float=tan(deg_to_rad(minf(config.operating_hitch_yaw_deg,config.mechanical_hitch_yaw_deg)/2))/half
	var path_limit:float=tan(deg_to_rad(config.path_hitch_equivalent_limit_deg/2))/half
	var request:float=clampf(curvature_request,-path_limit,path_limit)
	var speed_cap:float=sqrt(float(config.lateral_accel_command_limit_m_s2)/maxf(absf(request),1e-12))
	var bounded_speed:float=clampf(speed_request,-speed_cap,speed_cap)
	var curvature_cap:float=minf(geometry_limit,float(config.lateral_accel_command_limit_m_s2)/maxf(speed*speed,1.))
	var tangent:=0.0;var cross_track:=y
	if absf(request)>=1e-10:
		tangent=atan2(request*x,1-request*y)
		var radius:float=1/request
		cross_track=(absf(radius)-sqrt(x*x+(y-radius)*(y-radius)))*signf(request)
	var direction:float=-1. if speed_request<0 or speed<-.1 else 1.
	var desired:float=tangent-direction*atan2(float(config.path_cross_track_gain_per_s)*cross_track,maxf(absf(speed),1.))
	var yaw_rate:float=request*speed+float(config.path_heading_gain_per_s)*wrapf(desired-heading,-PI,PI)
	var cap:float=minf(float(config.lateral_accel_command_limit_m_s2)/maxf(absf(speed),1.),geometry_limit*maxf(absf(speed),.1))
	yaw_rate=clampf(yaw_rate,-cap,cap)
	var correction_curvature:float=yaw_rate/speed if absf(speed)>.5 else request
	var bounded_curvature:float=clampf(correction_curvature,-curvature_cap,curvature_cap)
	var target:float=-2*atan(half*bounded_curvature)
	var rate:float=deg_to_rad(config.hitch_target_rate_deg_s)*dt
	hitch_yaw+=clampf(target-hitch_yaw,-rate,rate)
	var effective:float=-tan(hitch_yaw/2)/half
	rate=deg_to_rad(config.bogie_target_rate_deg_s)*dt
	for i in bogie_yaw.size():
		target=atan2(effective*float(positions[i][0]),1-effective*float(positions[i][1]))
		target=clampf(target,-deg_to_rad(config.bogie_yaw_limit_deg),deg_to_rad(config.bogie_yaw_limit_deg))
		bogie_yaw[i]=float(bogie_yaw[i])+clampf(target-float(bogie_yaw[i]),-rate,rate)
	state={"requested_curvature_m_inv":curvature_request,"limited_curvature_m_inv":bounded_curvature,"effective_curvature_m_inv":effective,
		"speed_request_m_s":bounded_speed,"yaw_rate_request_rad_s":yaw_rate,"cross_track_error_m":cross_track,
		"hitch_yaw_target_rad":hitch_yaw,"bogie_yaw_targets_rad":bogie_yaw.duplicate()}
	return state
