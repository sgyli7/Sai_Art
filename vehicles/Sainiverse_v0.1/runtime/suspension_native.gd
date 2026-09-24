extends SceneTree
## Independent Jolt suspension/traction test. No pose replay or visual claim.
const DESIGN_ROOT="@SAI_ROOT@/support"
const OriginFrame=preload("@SAI_ROOT@/support/godot/physics_origin_frame.gd")
const TrainSteering=preload("@SAI_ROOT@/support/godot/train_steering.gd")
const Hydraulic=preload("@SAI_ROOT@/support/godot/hydraulic_suspension.gd")
var hydraulics=null
var hydraulic_links:Array=[]
var hydraulic_indices:Dictionary={}
const TrackTension=preload("@SAI_ROOT@/support/godot/track_tension.gd")
var track_tension=null
var track_links:Array=[]
var track_indices:Dictionary={}
var access=null
var access_indices:Dictionary={}
var origin=OriginFrame.new()
var steering=null
var steering_names:Array=[]
var turning_cross_max:=0.0
var turning_lateral_max:=0.0
var turning_hitch_max:=0.0
var control_leader:="front"
var neutral_hull_xy:Dictionary={}
var spec:Dictionary
var cfg:Dictionary
var acfg:Dictionary
var stage:Node3D
var bodies:Dictionary={}
var links:Array=[]
var contacts:Array=[]
var elapsed:=0.0
var count:=0
var filtered_speed:=0.0
var samples:Array=[]
var last_imu:Array=[]
var peak_accel:Array=[0.0,0.0]
var peak_times:Array=[0.0,0.0]
var accel_squares:Array=[0.0,0.0]
var accel_count:=0
var route_max:Array=[0.0,0.0]
var maximum_anchor_residual:=0.0
var anchor_peaks:Dictionary={}
var maximum_local_anchor_residual:=0.0
var maximum_anchor_measurement_disagreement:=0.0
var peak_speed:=0.0
var contact_core=null
var native_contact_calls:=0
var native_link_calls:=0
var start_usec:int
var force_links:Array=[]
var hull_names:Array=[]
var hitch_names:Array=[]
var options:Dictionary={"terrain":"flat","speed":0.0,"curvature":0.0,"seconds":30.0,"brake_at":-1.0,"start_x":0.0,"rebase_distance":-1.0,"output":"godot_flat_settle.json","rigid":false,
	"spec":DESIGN_ROOT+"/candidates/r015_articulation/physics/native_spec.json","output_root":DESIGN_ROOT+"/candidates/r015_articulation/reports/suspension"}

func vec(a:Array)->Vector3:return Vector3(float(a[0]),float(a[2]),-float(a[1]))
func source(v:Vector3)->Array:return [v.x,-v.z,v.y]
func _initialize()->void:
	for arg in OS.get_cmdline_user_args():
		var pair=arg.split("=",true,1)
		if pair.size()==2:
			if pair[0] in ["speed","curvature","seconds","brake_at","start_x","rebase_distance"]:options[pair[0]]=float(pair[1])
			elif pair[0]=="rigid":options.rigid=pair[1]=="true"
			else:options[pair[0]]=pair[1]
	call_deferred("_build")

func _build()->void:
	Engine.physics_ticks_per_second=200
	spec=JSON.parse_string(FileAccess.get_file_as_string(str(options.spec)))
	cfg=spec.config;acfg=spec.articulation
	if float(options.rebase_distance)<0:options.rebase_distance=float(spec.contact.get("native_origin_rebase_distance_m",0.))
	hull_names=spec.contact.get("hulls",["front","rear"]);hitch_names=spec.contact.get("hitch_joints",["extension","hitch_yaw","hitch_pitch","hitch_roll"])
	if spec.contact.has("turning_control"):
		steering=TrainSteering.new();steering.configure(spec.contact.turning_control,spec.contact.steering_positions_local_xy_m)
		steering_names=spec.contact.steering_joints
	for array in [peak_accel,peak_times,accel_squares,route_max]:array.resize(hull_names.size());array.fill(0.)
	stage=Node3D.new();root.add_child(stage)
	for item in spec.bodies:
		if item.name in hull_names:neutral_hull_xy[item.name]=[item.position[0],item.position[1]]
		var body:=RigidBody3D.new();body.name=item.name;body.position=vec(item.position)+Vector3(float(options.start_x),0,0)
		body.mass=float(item.mass);body.inertia=Vector3(item.inertia[0],item.inertia[2],item.inertia[1])
		body.center_of_mass_mode=RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM;body.center_of_mass=vec(item.com)
		body.gravity_scale=1.;body.linear_damp=0.;body.angular_damp=0.;body.can_sleep=false
		body.collision_layer=0;body.collision_mask=0
		stage.add_child(body);bodies[item.name]=body
	for item in spec.joints:
		var body:RigidBody3D=bodies[item.body];var parent:RigidBody3D=bodies[item.parent]
		var anchor:Vector3=vec(item.anchor)+Vector3(float(options.start_x),0,0);var axis:Vector3=vec(item.axis)
		var joint:=Generic6DOFJoint3D.new();joint.name="joint_"+item.name
		joint.position=anchor;joint.basis=Basis(Quaternion(Vector3.RIGHT,axis))
		# Each six-axis constraint permits exactly one scalar joint motion.
		# Thus there is no multi-angle Euler/pyramid mismatch with MuJoCo.
		for suffix in ["x","y","z"]:
			joint.call("set_flag_"+suffix,Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_LIMIT,true)
			joint.call("set_flag_"+suffix,Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_LIMIT,true)
			for param in [Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT,Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT,Generic6DOFJoint3D.PARAM_ANGULAR_LOWER_LIMIT,Generic6DOFJoint3D.PARAM_ANGULAR_UPPER_LIMIT]:joint.call("set_param_"+suffix,param,0.)
		var locked:bool=bool(options.rigid) and float(item.stiffness)>0
		var lo:float=0. if locked else float(item.limits[0]);var hi:float=0. if locked else float(item.limits[1])
		if item.kind=="slide":
			joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT,lo)
			joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT,hi)
			if float(item.stiffness)>0 and not locked:
				joint.set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_SPRING,true)
				joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_STIFFNESS,item.stiffness)
				joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_DAMPING,item.damping)
				joint.set_param_x(Generic6DOFJoint3D.PARAM_LINEAR_SPRING_EQUILIBRIUM_POINT,item.springref)
		else:
			joint.set_param_x(Generic6DOFJoint3D.PARAM_ANGULAR_LOWER_LIMIT,-hi)
			joint.set_param_x(Generic6DOFJoint3D.PARAM_ANGULAR_UPPER_LIMIT,-lo)
			if float(item.stiffness)>0 and not locked:
				joint.set_flag_x(Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_SPRING,true)
				joint.set_param_x(Generic6DOFJoint3D.PARAM_ANGULAR_SPRING_STIFFNESS,item.stiffness)
				joint.set_param_x(Generic6DOFJoint3D.PARAM_ANGULAR_SPRING_DAMPING,item.damping)
				joint.set_param_x(Generic6DOFJoint3D.PARAM_ANGULAR_SPRING_EQUILIBRIUM_POINT,-float(item.springref))
		stage.add_child(joint);joint.node_a=parent.get_path();joint.node_b=body.get_path();joint.exclude_nodes_from_collision=not bool(item.get("access",false))
		links.append({"spec":item,"body":body,"parent":parent,"axis":axis,"a":anchor-parent.position,"b":anchor-body.position})
	for link in links:
		var item:Dictionary=link.spec
		if float(item.stiffness)<=0. and not bool(item.get("lift",false)) and not bool(item.get("equipment",false)) and not bool(item.get("cockpit",false)):force_links.append(link)
	for item in spec.contact.contacts:contacts.append({"body":bodies[item.body],"local":vec(item.local),"radius":float(item.radius),
		"stiffness":float(item.get("contact_stiffness",spec.contact.contact_stiffness)),"damping":float(item.get("contact_damping",spec.contact.contact_damping)),"nominal":float(item.get("nominal_load_N",spec.contact.nominal_contact_load))})
	if ClassDB.class_exists("LeviathanTrackPath"):
		contact_core=ClassDB.instantiate("LeviathanTrackPath")
	if spec.contact.has("hydraulics"):
		hydraulics=Hydraulic.new();hydraulics.configure(spec.contact.hydraulics)
		for name in hydraulics.names:
			hydraulic_indices[name]=hydraulic_links.size()
			for link in links:
				if link.spec.name==name:hydraulic_links.append(link);break
		assert(hydraulic_links.size()==hydraulics.names.size())
	start_usec=Time.get_ticks_usec()
	if spec.contact.has("track_tension"):
		track_tension=TrackTension.new();track_tension.configure(spec.contact.track_tension)
		for name in track_tension.names:
			track_indices[name]=track_links.size()
			for link in links:
				if link.spec.name==name:track_links.append(link);break
		assert(track_links.size()==track_tension.names.size())
	if spec.contact.has("interior"):
		var room=load("@SAI_ROOT@/support/godot/interior_contacts.gd")
		room.attach(bodies[spec.contact.interior.body],spec.contact.interior)
	if spec.contact.has("walkable"):
		var walkable=load("@SAI_ROOT@/support/godot/interior_contacts.gd")
		for group in spec.contact.walkable.groups:
			walkable.attach(bodies[group.body],group)
	if spec.contact.has("access"):
		access=load("@SAI_ROOT@/support/godot/cabin_access.gd").new();access.configure(spec.contact.access)
		var room=load("@SAI_ROOT@/support/godot/interior_contacts.gd")
		for i in access.names.size():
			access_indices[access.names[i]]=i
			room.attach(bodies[access.names[i]],spec.contact.access.doors[i].collision)

func bump(x:float,center:float,width:float,height:float)->float:
	return height*.5*(1+cos(PI*clampf((x-center)/width,-1,1)))
func height(x:float,y:float)->float:
	match options.terrain:
		"flat":return 0.
		"hills":
			var hill:float=bump(x,85.,65.,5.)*bump(y,0.,110.,1.)
			var window:float=clampf((x-15.)/12.,0.,1.)*clampf((170.-x)/12.,0.,1.)
			return hill+window*bump(y,0.,110.,1.)*(.20*sin(TAU*x/12.)+.14*sin(TAU*x/7.+tanh(y/3.)*1.2)+.10*sin(y/6.))
		"polar":
			var hill:float=bump(x,85.,75.,1.8)*bump(y,0.,150.,1.)
			var window:float=clampf((x-10.)/14.,0.,1.)*clampf((180.-x)/14.,0.,1.)
			return hill+window*bump(y,0.,150.,1.)*(.09*sin(TAU*x/17.)+.06*sin(TAU*x/9.+tanh(y/8.))+.05*sin(y/13.))
		"alternating":
			var left:float=.5*(1+tanh(y/2))
			return left*(bump(x,30,2,.35)+bump(x,70,2,.3))+(1-left)*(bump(x,45,2,.35)+bump(x,85,2,.3))
		"ditch":return bump(x,60,3,-.4)
		"ramp":return clampf(x-20,0,30)*tan(deg_to_rad(8))
		"rough":return clampf((x-10)/5,0,1)*clampf((145-x)/5,0,1)*(.15*sin(TAU*x/9)+.10*sin(TAU*x/4+tanh(y/2)*PI/2))
	return 0.
func com(body:RigidBody3D)->Vector3:return body.global_transform*body.center_of_mass
func point_velocity(body:RigidBody3D,point:Vector3)->Vector3:return body.linear_velocity+body.angular_velocity.cross(point-com(body))

func _physics_process(dt:float)->bool:
	if spec.is_empty() or bodies.size()!=spec.bodies.size():return false
	var speed_request:float=0. if elapsed<10 else float(options.speed)
	if float(options.brake_at)>=0 and elapsed>=float(options.brake_at):speed_request=0.
	control_leader=str(hull_names[-1]) if steering!=null and speed_request<0 else "front"
	var leader:RigidBody3D=bodies[control_leader]
	origin.maybe_shift(bodies.values(),leader,float(options.rebase_distance),elapsed)
	var speed:float=leader.linear_velocity.dot(leader.global_basis.x)
	if access!=null:
		var angles:Array=[];var rates:Array=[]
		for door in spec.contact.access.doors:
			var body:RigidBody3D=bodies[door.name];var parent:RigidBody3D=bodies.front;var axis:Vector3=vec(door.axis_source)
			var rotation:Quaternion=(parent.global_basis.inverse()*body.global_basis).get_rotation_quaternion()
			angles.append(wrapf(2*atan2(Vector3(rotation.x,rotation.y,rotation.z).dot(axis),rotation.w),-PI,PI))
			rates.append((body.angular_velocity-parent.angular_velocity).dot(parent.global_basis*axis))
		access.step(angles,rates,speed,dt)
		if not access.drive_permitted:speed_request=0.
	if steering!=null:
		var world:Array=origin.source_position(leader.global_position);var neutral:Array=neutral_hull_xy[control_leader]
		var state:Dictionary=steering.update(speed_request,speed,0. if elapsed<10 else float(options.curvature),0. if str(options.get("mode","")) in ["manual","hill_turn"] else float(world[0])-float(neutral[0]),0. if str(options.get("mode","")) in ["manual","hill_turn"] else float(world[1])-float(neutral[1]),0. if str(options.get("mode","")) in ["manual","hill_turn"] else atan2(-leader.global_basis.x.z,leader.global_basis.x.x),dt)
		speed_request=state.speed_request_m_s
		if elapsed>=10:turning_cross_max=maxf(turning_cross_max,absf(state.cross_track_error_m))
	var rate:float=cfg.drive_accel_limit_m_s2 if speed_request>filtered_speed else cfg.brake_accel_limit_m_s2
	if steering!=null:rate=cfg.drive_accel_limit_m_s2 if absf(speed_request)>absf(filtered_speed) and speed_request*filtered_speed>=0 else cfg.brake_accel_limit_m_s2
	filtered_speed+=clampf(speed_request-filtered_speed,-rate*dt,rate*dt)
	var accel:float=clampf(2*(filtered_speed-speed),-float(cfg.brake_accel_limit_m_s2),float(cfg.drive_accel_limit_m_s2))
	if steering!=null:
		var error:float=2*(filtered_speed-speed);var direction:float=-1. if speed<-.1 or filtered_speed<0 else 1.
		var cap:float=cfg.drive_accel_limit_m_s2 if error*direction>0 else cfg.brake_accel_limit_m_s2
		accel=clampf(error,-cap,cap)
	var available_power:float=cfg.power_limit_W
	if access!=null:available_power=maxf(0.,available_power-access.power)
	if hydraulics!=null:
		var coordinates:Array=[];var rates:Array=[]
		if contact_core!=null and contact_core.has_method("sample_linear_links") and OS.get_environment("SAINIVERSE_LEGACY_LINK_SAMPLING")!="1":
			var sampled:Dictionary=contact_core.sample_linear_links(hydraulic_links)
			coordinates=sampled.coordinates;rates=sampled.rates;native_link_calls+=1
		else:
			for link in hydraulic_links:
				var axis:Vector3=link.parent.global_basis*link.axis
				var pa:Vector3=link.parent.global_transform*link.a;var pb:Vector3=link.body.global_transform*link.b
				var q:float=(pb-pa).dot(axis);var dq:float=(point_velocity(link.body,pb)-point_velocity(link.parent,pa)).dot(axis)
				coordinates.append(q);rates.append(dq);link.control_state=[axis,pa,pb,q,dq]
		hydraulics.step(coordinates,rates,dt);available_power=maxf(0.,available_power-hydraulics.pump_power_W)
	var qvalues:Dictionary={};var efforts:Dictionary={};var residual:=0.0
	if track_tension!=null:
		var coordinates:Array=[];var rates:Array=[]
		if contact_core!=null and contact_core.has_method("sample_linear_links") and OS.get_environment("SAINIVERSE_LEGACY_LINK_SAMPLING")!="1":
			var sampled:Dictionary=contact_core.sample_linear_links(track_links)
			coordinates=sampled.coordinates;rates=sampled.rates;native_link_calls+=1
		else:
			for link in track_links:
				var axis:Vector3=link.parent.global_basis*link.axis
				var pa:Vector3=link.parent.global_transform*link.a;var pb:Vector3=link.body.global_transform*link.b
				var q:float=(pb-pa).dot(axis);var dq:float=(point_velocity(link.body,pb)-point_velocity(link.parent,pa)).dot(axis)
				coordinates.append(q);rates.append(dq);link.control_state=[axis,pa,pb,q,dq]
		track_tension.step(coordinates,rates,dt)
	var audit_tick:bool=count%20==19
	for link in (links if audit_tick else force_links):
		var body:RigidBody3D=link.body;var parent:RigidBody3D=link.parent;var item:Dictionary=link.spec
		var diagnostic_only:bool=float(item.stiffness)>0. or bool(item.get("lift",false)) or bool(item.get("equipment",false)) or bool(item.get("cockpit",false))
		if diagnostic_only and not audit_tick:continue
		var cached:bool=link.has("control_state")
		var axis:Vector3=link.control_state[0] if cached else parent.global_basis*link.axis
		var pa:Vector3=link.control_state[1] if cached else parent.global_transform*link.a
		var pb:Vector3=link.control_state[2] if cached else body.global_transform*link.b
		var q:float;var dq:float;var link_residual:float
		if cached:
			q=link.control_state[3];dq=link.control_state[4];link_residual=((pb-pa)-axis*q).length()
		elif item.kind=="slide":
			q=(pb-pa).dot(axis);dq=(point_velocity(body,pb)-point_velocity(parent,pa)).dot(axis)
			link_residual=((pb-pa)-axis*q).length()
		else:
			var rotation:Quaternion=(parent.global_basis.inverse()*body.global_basis).get_rotation_quaternion()
			q=wrapf(2*atan2(Vector3(rotation.x,rotation.y,rotation.z).dot(link.axis),rotation.w),-PI,PI)
			dq=(body.angular_velocity-parent.angular_velocity).dot(axis);link_residual=pa.distance_to(pb)
		if audit_tick:
			residual=maxf(residual,link_residual)
			var relative_delta:Vector3=(body.global_position-parent.global_position)+(body.global_basis*link.b-parent.global_basis*link.a)
			var local_residual:float=(relative_delta-axis*relative_delta.dot(axis)).length() if item.kind=="slide" else relative_delta.length()
			maximum_local_anchor_residual=maxf(maximum_local_anchor_residual,local_residual)
			maximum_anchor_measurement_disagreement=maxf(maximum_anchor_measurement_disagreement,absf(local_residual-link_residual))
			if link_residual>float(anchor_peaks.get(item.name,{}).get("residual_m",-1.)):
				anchor_peaks[item.name]={"residual_m":link_residual,"time_s":elapsed,"front_position":origin.source_position(bodies.front.global_position),"coordinate":q}
			qvalues[item.name]=q
		if bool(item.get("lift",false)) or bool(item.get("equipment",false)) or bool(item.get("cockpit",false)):continue
		if access_indices.has(item.name):
			var effort:float=float(access.torques[access_indices[item.name]])+float(access.latch_torques[access_indices[item.name]]);efforts[item.name]=effort
			body.apply_torque(axis*effort);parent.apply_torque(-axis*effort)
			continue
		if float(item.stiffness)==0:
			if hydraulic_indices.has(item.name) or track_indices.has(item.name):
				var force:float=hydraulics.forces[int(hydraulic_indices[item.name])] if hydraulic_indices.has(item.name) else 0.
				if track_indices.has(item.name):force+=float(track_tension.forces[int(track_indices[item.name])])
				efforts[item.name]=force
				body.apply_force(axis*force,pb-body.global_position);parent.apply_force(-axis*force,pa-parent.global_position)
				continue
			var kp:float;var kd:float;var cap:float;var target:=0.0
			var steer_index:int=steering_names.find(item.name)
			if steer_index>=0:
				kp=steering.config.bogie_yaw_kp_Nm_rad;kd=steering.config.bogie_yaw_kd_Nms_rad;cap=steering.config.bogie_yaw_torque_limit_Nm
				target=steering.bogie_yaw[steer_index]
			else:
				var index:int=hitch_names.find(item.name);assert(index>=0);index=index%4
				kp=acfg.extension_kp_N_per_m if index==0 else acfg.rotation_kp_Nm_per_rad[index-1]
				kd=acfg.extension_kd_Ns_per_m if index==0 else acfg.rotation_kd_Nms_per_rad[index-1]
				cap=acfg.extension_force_limit_N if index==0 else acfg.rotation_torque_limits_Nm[index-1]
				if steering!=null and index==1:
					target=steering.hitch_yaw;kp=steering.config.hitch_yaw_kp_Nm_rad;kd=steering.config.hitch_yaw_kd_Nms_rad
				if index==1:turning_hitch_max=maxf(turning_hitch_max,absf(q))
			var effort:float=clampf(kp*(target-q)-kd*dq,-cap,cap);efforts[item.name]=effort
			if item.kind=="slide":
				body.apply_force(axis*effort,pb-body.global_position);parent.apply_force(-axis*effort,pa-parent.global_position)
			else:body.apply_torque(axis*effort);parent.apply_torque(-axis*effort)
	var points:Array=contacts;var total_load:=0.0;var supported:=0
	var used_native:bool=false
	if contact_core==null and ClassDB.class_exists("LeviathanTrackPath"):
		contact_core=ClassDB.instantiate("LeviathanTrackPath")
	if contact_core!=null and contact_core.has_method("contact_geometry") and OS.get_environment("SAINIVERSE_LEGACY_CONTACT")!="1":
		var result:Dictionary=contact_core.contact_geometry(contacts,str(options.terrain),origin.offset_x,origin.offset_z,float(cfg.contact_max_nominal_load_factor))
		if result.has("total_load"):
			total_load=float(result.total_load);supported=int(result.supported);used_native=true;native_contact_calls+=1
	if not used_native:
		for item in contacts:
			var body:RigidBody3D=item.body;var center:Vector3=body.global_transform*item.local
			var world_x:float=float(center.x)+origin.offset_x;var world_y:float=-float(center.z)-origin.offset_z
			var h:float=height(world_x,world_y)
			var dx:float=(height(world_x+.01,world_y)-height(world_x-.01,world_y))/.02
			var dy:float=(height(world_x,world_y+.01)-height(world_x,world_y-.01))/.02
			var normal:=Vector3(-dx,1,dy).normalized()
			var penetration:float=item.radius-(center.y-h)*normal.y
			var point:Vector3=center-normal*float(item.radius);var velocity:Vector3=point_velocity(body,point)
			var load:float=clampf(float(item.stiffness)*penetration-float(item.damping)*velocity.dot(normal),0,float(item.nominal)*float(cfg.contact_max_nominal_load_factor)) if penetration>=0 else 0.
			var forward:Vector3=(body.global_basis.x-normal*body.global_basis.x.dot(normal)).normalized()
			var lateral:Vector3=normal.cross(forward);var longitudinal_speed:float=velocity.dot(forward)
			item.point=point;item.normal=normal;item.forward=forward;item.lateral=lateral;item.velocity=velocity;item.load=load;item.speed=longitudinal_speed
			total_load+=load
			if load>1:supported+=1
	var grade:=0.0;var leverage_mean:=0.0
	var leader_com:Vector3=com(leader)
	for p in points:
		p.share=float(p.load)/maxf(total_load,1.);grade+=float(p.share)*p.forward.y*9.81
		p.leverage=(p.point-leader_com).cross(p.forward).y;leverage_mean+=float(p.leverage)*float(p.share)
	var propulsion:float=clampf(float(cfg.total_mass_kg)*(accel+grade+float(cfg.rolling_resistance)*9.81*tanh(speed*2)),-float(cfg.friction)*total_load,available_power/maxf(absf(speed),2))
	var yaw_request:=0.0;var moment:=0.0
	if maxf(absf(speed),absf(speed_request))>.1:
		var heading:float=atan2(-leader.global_basis.x.z,leader.global_basis.x.x)
		var desired:float=atan2(-float(cfg.path_cross_track_gain_per_s)*(-float(leader.global_position.z)-origin.offset_z),maxf(absf(speed),1))
		var error:float=wrapf(desired-heading,-PI,PI);var limit:float=float(cfg.path_lateral_accel_limit_m_s2)/maxf(absf(speed),1)
		yaw_request=clampf(float(cfg.path_heading_gain_per_s)*error,-limit,limit)
		if steering!=null:yaw_request=steering.state.yaw_rate_request_rad_s
		moment=clampf(float(spec.steering_inertia)*float(cfg.path_yaw_rate_gain_per_s)*(yaw_request-leader.angular_velocity.y),-float(cfg.path_yaw_moment_limit_Nm),float(cfg.path_yaw_moment_limit_Nm))
	var denominator:=0.0
	for p in points:p.leverage-=leverage_mean;denominator+=float(p.share)*float(p.leverage)*float(p.leverage)
	var power:=0.0
	for p in points:
		p.drive=propulsion*float(p.share)+moment*float(p.share)*float(p.leverage)/maxf(denominator,1.)
		power+=absf(float(p.drive)*float(p.speed))
	var power_scale:float=minf(1.,available_power/maxf(power,1.))
	for p in points:
		var fx:float=float(p.drive)*power_scale-float(cfg.rolling_resistance)*float(p.load)*tanh(float(p.speed)*2)
		var fy:float=-float(cfg.total_mass_kg)*float(p.share)*float(cfg.lateral_relaxation_per_s)*p.velocity.dot(p.lateral)
		var tangent:Vector3=p.forward*fx+p.lateral*fy
		tangent*=minf(1.,float(cfg.friction)*float(p.load)/maxf(tangent.length(),1.))
		var force:Vector3=p.normal*float(p.load)+tangent
		p.body.apply_force(force,p.point-p.body.global_position)
	var imu:Array=[];var accelerations:Array=[];var hulls:Array=[];var positions:Array=[];var upright:Array=[]
	accelerations.resize(hull_names.size());accelerations.fill(0.)
	for name in hull_names:
		var body:RigidBody3D=bodies[name];hulls.append(body);positions.append(origin.source_position(body.global_position));upright.append(body.global_basis.y.y)
	for i in hulls.size():
		var body:RigidBody3D=hulls[i];var offset:Vector3=Vector3(25,2.5,0) if i==0 else Vector3(0,5,0)
		imu.append(body.linear_velocity+body.angular_velocity.cross(body.global_basis*offset))
		if last_imu.size()==hulls.size():accelerations[i]=(imu[i].y-last_imu[i].y)/dt
		if elapsed>=10 and last_imu.size()==hulls.size():turning_lateral_max=maxf(turning_lateral_max,absf(((imu[i]-last_imu[i])/dt).dot(body.global_basis.z)))
		if absf(float(accelerations[i]))>float(peak_accel[i]):peak_accel[i]=absf(float(accelerations[i]));peak_times[i]=elapsed
		if elapsed>=10:
			accel_squares[i]+=float(accelerations[i])*float(accelerations[i])
			route_max[i]=maxf(float(route_max[i]),absf(float(body.global_position.z)+origin.offset_z))
	if elapsed>=10:accel_count+=1
	maximum_anchor_residual=maxf(maximum_anchor_residual,residual)
	last_imu=imu;peak_speed=maxf(peak_speed,speed)
	if count%20==19:
		var heave:Array=[];var wheels:Array=[]
		for name in spec.contact.bogies:heave.append(qvalues[name+"_heave"])
		for name in spec.contact.wheels:wheels.append(qvalues[name])
		var hitch_coordinates:Array=[]
		for name in hitch_names:hitch_coordinates.append(qvalues[name])
		samples.append({"time":elapsed,"speed_m_s":speed,"hull_positions":positions,
			"upright":upright,"normal_load_N":total_load,"supported_contacts":supported,
			"heave_m":heave,"wheel_travel_m":wheels,"imu_vertical_accel_m_s2":accelerations,
			"hitch_coordinates":hitch_coordinates,
			"path_yaw_rate_request_rad_s":yaw_request,"path_yaw_moment_request_Nm":moment,"allocated_drive_power_W":power*power_scale,"joint_anchor_residual_m":residual})
		if hydraulics!=null:samples[-1]["hydraulics"]=hydraulics.state()
		if track_tension!=null:samples[-1]["track_tension"]=track_tension.state()
		if access!=null:samples[-1]["access"]=access.state()
		if steering!=null:
			var angles:Array=[];var actuator_efforts:Array=[];var headings:Array=[]
			for name in steering_names:angles.append(qvalues[name])
			for name in hitch_names+steering_names:actuator_efforts.append(efforts[name])
			for body:RigidBody3D in hulls:headings.append(atan2(-body.global_basis.x.z,body.global_basis.x.x))
			samples[-1].merge({"steering":steering.state.duplicate(true),"bogie_yaw_rad":angles,"actuator_efforts":actuator_efforts,"hull_heading_rad":headings,"control_leader":control_leader})
	elapsed+=dt;count+=1
	var failed:bool=hydraulics!=null and not hydraulics.valid
	for body:RigidBody3D in hulls:failed=failed or not body.global_position.is_finite() or body.global_basis.y.y<.5
	if elapsed>=float(options.seconds) or failed:
		var rms:Array=[]
		for value in accel_squares:rms.append(sqrt(float(value)/maxi(accel_count,1)))
		var out:Dictionary={"engine":"Godot "+str(Engine.get_version_info().string),"physics_engine":ProjectSettings.get_setting("physics/3d/physics_engine"),
			"failed":failed,"terrain":options.terrain,"rigid":options.rigid,"seconds":elapsed,"wall_seconds":(Time.get_ticks_usec()-start_usec)/1e6,
			"dynamic_bodies":bodies.size(),"joints":links.size(),"native_contact_calls":native_contact_calls,"native_link_calls":native_link_calls,"peak_speed_kmh":peak_speed*3.6,"peak_all_step_vertical_accel_m_s2":peak_accel,"samples":samples,
			"rms_all_step_vertical_accel_after_settle_m_s2":rms,"total_mass_kg":cfg.total_mass_kg,
			"peak_acceleration_times_s":peak_times,"max_all_step_lateral_path_error_m":route_max,"joint_anchor_sample_hz":10,"maximum_sampled_joint_anchor_residual_m":maximum_anchor_residual,
			"joint_anchor_peaks":anchor_peaks,"initial_world_x_m":options.start_x,
			"maximum_local_relative_anchor_residual_m":maximum_local_anchor_residual,"maximum_anchor_measurement_disagreement_m":maximum_anchor_measurement_disagreement,
			"origin_rebases":origin.events,"rebase_distance_m":options.rebase_distance,"maximum_rebase_world_discontinuity_m":origin.max_world_position_discontinuity,
			"maximum_rebase_relative_change_m":origin.max_relative_position_change,"maximum_rebase_velocity_change":origin.max_velocity_change,
			"scope":"Native Jolt scalar serial joints with springs and finite-power track forces. Engine gravity 9.81 m/s² and reduced compliant belt contacts. Joint diagnostics sampled at 10 Hz; force control remains 200 Hz. Provisional parameters, no learned policy or visual/FPS claim."}
		if hydraulics!=null:out["hydraulics"]=hydraulics.state()
		if steering!=null:out.merge({"control_leader":control_leader,"maximum_all_step_control_path_error_m":turning_cross_max,"maximum_all_step_body_lateral_accel_m_s2":turning_lateral_max,
			"maximum_all_step_hitch_yaw_deg":rad_to_deg(turning_hitch_max),"command_curvature_m_inv":options.curvature,"command_speed_m_s":options.speed})
		var file:=FileAccess.open(str(options.output_root)+"/"+str(options.output),FileAccess.WRITE)
		file.store_string(JSON.stringify(out,"  "));file.close()
		print("SUSPENSION_NATIVE_COMPLETE ",JSON.stringify({"failed":failed,"seconds":elapsed,"peak_kmh":peak_speed*3.6,"samples":samples.size()}))
		quit(1 if failed else 0)
	return false
