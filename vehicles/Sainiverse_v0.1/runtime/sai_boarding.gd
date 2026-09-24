extends "res://hub/sai.gd"
## Mission sequencing around the unchanged native locomotion / impedance controller.
var carrier:SceneTree
var robot_id:="Sai_Agent_001"
var manual_control:=false
var visual_only:=false
var parked_carrier_transform:=Transform3D.IDENTITY
var manual_spawn_valid:=false
var manual_spawn_world:=Vector3.ZERO
var manual_spawn_basis:=Basis.IDENTITY
var cockpit_demo:=false
var arm_solver=null
var cockpit_samples:Array=[]
var phase:="wait_ground"
var mission_samples:Array=[]
var stable_since:=-1.
var completed:=false
var failure:=""
var logged_phase:=""
var phase_times:Dictionary={}
var sai60_skill:=""
var policy_hz:int=50
var spawn_world_start:=Vector3.ZERO
var shared_world_ok:=false
var scene_body_names:PackedStringArray=PackedStringArray()
var last_command_source:=""
var last_input_axes:Array=[0.,0.]

func _sai60_enabled()->bool:
	return OS.get_environment("SAINIVERSE_SAI60_POLICY")!=""

func _ready()->void:
	sai60_skill=OS.get_environment("SAINIVERSE_SAI60_POLICY")
	var sai60:bool=_sai60_enabled()
	policy_hz=60 if sai60 else 50
	settings={"task":"drive","skill":sai60_skill if sai60 else ""};task="drive";visuals=DisplayServer.get_name()!="headless"
	var model_path:="res://sai_robots/Sai_Agent_002/robot.json" if robot_id=="Sai_Agent_002" else "res://sai_agent/robot.json"
	specification=JSON.parse_string(FileAccess.get_file_as_string(model_path))
	if specification==null or str(specification.get("robot_id",""))!=robot_id:failure="Sai model identity mismatch: "+robot_id;push_error(failure);return
	# five-up24 needs the isolated 60 Hz velocity-motor plant; stock game is still 50 Hz torque-PD.
	var robot_path:="res://sai/compliant_robot_sai60.gd" if sai60 and FileAccess.file_exists("res://sai/compliant_robot_sai60.gd") else "res://sai/compliant_robot.gd"
	if sai60 and robot_path!="res://sai/compliant_robot_sai60.gd":
		failure="Missing res://sai/compliant_robot_sai60.gd for 60/60 coworld path";push_error(failure);return
	robot=load(robot_path).new();add_child(robot);robot.setup(specification,visuals,0.)
	var initial:=manual_spawn_basis if manual_spawn_valid else Basis.IDENTITY if cockpit_demo else Basis(Vector3.UP,PI/2.)
	var spawn:Vector3=manual_spawn_world if manual_spawn_valid else carrier.bodies.front.global_transform*carrier.local_source([30.90,-1.58,12.25]) if cockpit_demo else Vector3(0.,0.,20.2)
	# 60/60 + existing manual Input axes: farther snow spawn facing away from the
	# carrier so hold-forward stays on open ground (z=20.2 into deploying lift tips ~2 m).
	if sai60 and not cockpit_demo and not manual_spawn_valid:
		initial=Basis(Vector3.UP,-PI/2.)
		spawn=Vector3(0.,0.,25.5)
		spawn.y=carrier.height(spawn.x+carrier.origin.offset_x,-spawn.z-carrier.origin.offset_z)
	elif manual_control and not cockpit_demo and not manual_spawn_valid:
		spawn.z=25.5
		spawn.y=carrier.height(spawn.x+carrier.origin.offset_x,-spawn.z-carrier.origin.offset_z)
	for body in robot.bodies.values():
		body.position=initial*body.position+spawn;body.basis=initial*body.basis
		body.collision_layer=16;body.collision_mask=1|8|32
		if manual_control and not visual_only:
			var front:RigidBody3D=carrier.bodies.front
			body.linear_velocity=front.linear_velocity+front.angular_velocity.cross(body.global_position-front.global_position)
			body.angular_velocity=front.angular_velocity
		if cockpit_demo and body.name in ["arm_gripper","arm_moving_jaw"]:
			body.collision_mask|=128;body.contact_monitor=true;body.max_contacts_reported=8
	spawn_world_start=robot.bodies.chassis.global_position
	if visual_only:
		parked_carrier_transform=carrier.bodies.front.global_transform
		physics_interpolation_mode=Node.PHYSICS_INTERPOLATION_MODE_OFF
		for body in robot.bodies.values():
			body.freeze=true
			body.collision_layer=0
			body.collision_mask=0
		robot.process_mode=Node.PROCESS_MODE_DISABLED
		set_physics_process(false)
		if visuals:
			var parked_paint=load("res://hub/sai_materials.gd").new()
			parked_paint.scene=self;parked_paint._make_materials();parked_paint._paint_robot();parked_paint.free()
		return
	var profile:=""
	if sai60:
		profile="res://sai_policy/experimental/"+sai60_skill+".json"
		if not FileAccess.file_exists(profile):
			failure="Missing experimental profile: "+profile;push_error(failure);return
	var controller_path:="res://sai/native_controller_sai60.gd" if sai60 and FileAccess.file_exists("res://sai/native_controller_sai60.gd") else "res://sai/native_controller.gd"
	if sai60 and controller_path!="res://sai/native_controller_sai60.gd":
		failure="Missing res://sai/native_controller_sai60.gd (stock CONTROL_DT=0.02 rejects 60 Hz ONNX)";push_error(failure);return
	native_controller=load(controller_path).new(profile)
	if native_controller.last_error!="":failure=native_controller.last_error;push_error(failure);return
	if cockpit_demo:arm_solver=load("res://sai/native_grab_controller.gd").new(native_controller,specification)
	if visuals:
		var paint=load("res://hub/sai_materials.gd").new();paint.scene=self;paint._make_materials();paint._paint_robot();paint.free()
	_record_shared_world()
	print("SAINIVERSE_SAI_READY robot=",robot_id," physics_hz=",Engine.physics_ticks_per_second," policy_hz=",policy_hz," skill=",sai60_skill," shared_world=",shared_world_ok)

func _process(_delta:float)->void:
	if visual_only and carrier!=null and carrier.bodies.has("front"):
		global_transform=carrier.bodies.front.get_global_transform_interpolated()*parked_carrier_transform.affine_inverse()

func _record_shared_world()->void:
	var robot_space=robot.bodies.chassis.get_world_3d()
	var carrier_space=carrier.bodies.front.get_world_3d() if carrier!=null and carrier.bodies.has("front") else null
	shared_world_ok=robot_space!=null and carrier_space!=null and robot_space==carrier_space
	scene_body_names=PackedStringArray()
	if carrier==null:return
	for name in carrier.bodies:
		var body:RigidBody3D=carrier.bodies[name]
		if body!=null and not body.freeze:scene_body_names.append(str(name))
	# Lift/ramp remain dynamic on the boarding fixture even when the hull is frozen.
	if carrier.lift_data.size()>0:
		var lift:Dictionary=carrier.lift_data[0]
		for name in lift.groups:
			if not scene_body_names.has(str(name)):scene_body_names.append(str(name))
		if not scene_body_names.has(str(lift.ramp.name)):scene_body_names.append(str(lift.ramp.name))

func coworld_evidence()->Dictionary:
	var base:RigidBody3D=robot.bodies.chassis if robot!=null and robot.bodies.has("chassis") else null
	var end:Vector3=base.global_position if base!=null else spawn_world_start
	var distance:float=Vector2(end.x-spawn_world_start.x,end.z-spawn_world_start.z).length()
	var moving_scene:=0
	for name in scene_body_names:
		if carrier!=null and carrier.bodies.has(name) and not carrier.bodies[name].freeze:moving_scene+=1
	return {"shared_world_3d":shared_world_ok,"dynamic_scene_body_names":Array(scene_body_names),"dynamic_scene_body_count":moving_scene,"spawn_world_m":[spawn_world_start.x,spawn_world_start.y,spawn_world_start.z],"end_world_m":[end.x,end.y,end.z],"planar_distance_m":distance,"physics_hz":Engine.physics_ticks_per_second,"policy_hz":policy_hz,"stair_profile":native_controller.stair_profile_id if native_controller!=null else "","phase":phase,"sample_count":mission_samples.size()}

func height_scan()->Array:
	var base:RigidBody3D=robot.bodies.chassis;var direction:Vector3=base.global_basis*Vector3.RIGHT
	var yaw:=atan2(-direction.z,direction.x);var heights:Array=[]
	for x in [-.36,-.18,0.,.18,.36,.54,.72,.9]:
		for y in [-.24,0.,.24]:
			var sx:float=base.global_position.x+cos(yaw)*x-sin(yaw)*y
			var sz:float=base.global_position.z-sin(yaw)*x-cos(yaw)*y
			var ray:=PhysicsRayQueryParameters3D.create(Vector3(sx,base.global_position.y+1.,sz),Vector3(sx,base.global_position.y-1.,sz),9)
			var hit:=get_world_3d().direct_space_state.intersect_ray(ray);heights.append(float(hit.position.y) if not hit.is_empty() else 0.)
	return heights

func exchange(state:Dictionary)->Dictionary:
	state.hub_config=settings;state.stair_course=false;state.experimental_profile=not str(settings.get("skill","")).is_empty()
	state.terrain_path_heights=preload("res://sai/terrain_scan.gd").wheel_path(self,9)
	state.terrain_edge_heights=preload("res://sai/terrain_scan.gd").edge_profile(self,9)
	state.wheel_ground_heights=preload("res://sai/terrain_scan.gd").wheel_ground(self,9)
	state.world_origin=[0.,0.,0.];state.contact_following_descent=true
	var positions:Array=[];var supported:=0
	for leg in specification.leg_order:
		var wheel:RigidBody3D=robot.bodies[str(leg)+"_wheel"];positions.append(robot.source(wheel.position))
		if not wheel.get_colliding_bodies().is_empty():supported+=1
	state.wheel_positions=positions;state.wheels_supported=supported;state.arm_gravity_bias=_arm_gravity_bias();state.merge(_leg_support_state(),true)
	var result:Dictionary=native_controller.command(state)
	if cockpit_demo and arm_solver!=null:
		var control:Dictionary=carrier.spec.contact.cockpit.controls[0]
		var angle:float=.06*sin((carrier.elapsed-12.)*1.3) if carrier.elapsed>12. else 0.
		var parent:RigidBody3D=carrier.bodies.front
		var pivot:Vector3=parent.global_transform*carrier.local_source(control.pivot_source_m)
		# Aim at the lower spoke's existing collision proxy, without adding a grip.
		var offset:Vector3=carrier.vec([-.028,-.215,-.075])
		var target:Vector3=pivot+parent.global_basis*Basis(Vector3.RIGHT,angle)*offset
		var home:Array=specification.arm_home_source_deg.duplicate()
		result.target_arm=arm_solver._ik(Vector3(target.x,-target.z,target.y),state,home)
		result.arm_bias=state.arm_gravity_bias
		result.grip_cap=1.4
		var hand:RigidBody3D=robot.bodies.arm_gripper
		var tool:Vector3=hand.global_transform*robot.gv(specification.tool_local_m)
		var touch:bool=hand.get_colliding_bodies().has(carrier.bodies[control.name]) or robot.bodies.arm_moving_jaw.get_colliding_bodies().has(carrier.bodies[control.name])
		if robot.tick%maxi(1,Engine.physics_ticks_per_second/10)==0:
			cockpit_samples.append({"time":carrier.elapsed,"steer_rad":carrier.cockpit.coordinate("steer").x,"target_rad":angle,"tool_error_m":tool.distance_to(target),"tool_world_m":[tool.x,tool.y,tool.z],"target_world_m":[target.x,target.y,target.z],"base_world_m":[robot.bodies.chassis.global_position.x,robot.bodies.chassis.global_position.y,robot.bodies.chassis.global_position.z],"hand_contact":touch,"upright":robot.bodies.chassis.global_basis.y.y})
	return result

func movement_command()->Array:
	if cockpit_demo:
		last_command_source="cockpit_demo_zero";last_input_axes=[0.,0.];return [0.,0.,0.]
	if manual_control:
		# Existing player/manual velocity entry: keyboard axes (also fed by
		# SAINIVERSE_DRIVE_PROBE via Input.action_press("sainiverse_forward")).
		var axis_fwd:float=Input.get_axis("sainiverse_reverse","sainiverse_forward")
		var axis_yaw:float=Input.get_axis("sainiverse_right","sainiverse_left")
		last_command_source="Input.get_axis(sainiverse_reverse,sainiverse_forward)*.14"
		last_input_axes=[axis_fwd,axis_yaw]
		return [axis_fwd*.14,axis_yaw*.25,0.]
	var lift:Dictionary=carrier.lift_data[0];var platform:RigidBody3D=carrier.bodies[lift.groups[3]]
	var base:RigidBody3D=robot.bodies.chassis;var local:Vector3=platform.to_local(base.global_position)
	var t:float=carrier.elapsed;var down:bool=carrier.coordinate(lift.groups[0]).x>2.65 and platform.global_position.y<.15
	var ramp:Vector2=carrier.ramp_coordinate(lift.ramp.name)
	if phase=="wait_ground":
		carrier.lift_commands[lift.name]=true
		if down and ramp.x>1.60:phase="approach"
	if phase=="approach" and absf(local.z)<.22 and absf(local.x)<.35:
		phase="settle";stable_since=t
	if phase=="settle" and t-stable_since>1.:
		phase="ride";carrier.lift_commands[lift.name]=false
	if phase=="ride" and carrier.coordinate(lift.groups[0]).x<.02 and carrier.coordinate(lift.groups[1]).x<.01 and carrier.coordinate(lift.groups[2]).x<.01 and carrier.coordinate(lift.groups[3]).x<.01:
		phase="exit"
	var front:RigidBody3D=carrier.bodies.front;var in_hull:Vector3=front.to_local(base.global_position)
	if phase=="exit" and -in_hull.z> -11.3:phase="complete";completed=true
	if phase not in ["approach","exit"]:
		last_command_source="boarding_phase_hold_zero";last_input_axes=[0.,0.];return [0.,0.,0.]
	var target:Vector3=platform.global_position if phase=="approach" else front.global_transform*carrier.local_source([0.,-10.8,7.45])
	var delta:Vector3=target-base.global_position
	var desired:float=atan2(-delta.z,delta.x);var actual:float=atan2(-base.global_basis.x.z,base.global_basis.x.x)
	last_command_source="boarding_plan_approach_or_exit";last_input_axes=[1.,0.]
	return [.14,clampf(2.*wrapf(desired-actual,-PI,PI),-.45,.45),0.]

func _physics_process(_delta:float)->void:
	if robot==null or native_controller==null or failure!="":return
	var state:Dictionary=robot.state()
	# 60/60: one inference per physics step. Legacy boarding keeps physics/50.
	var control_period:int=1 if policy_hz>=Engine.physics_ticks_per_second else maxi(1,Engine.physics_ticks_per_second/policy_hz)
	if robot.tick%control_period==0:
		if phase!=logged_phase:
			print("SAI_BOARDING_PHASE ",phase," t=",carrier.elapsed);logged_phase=phase;phase_times[phase]=carrier.elapsed
			if carrier.elapsed>11. and str(carrier.options.get("capture","false"))=="true":carrier._capture("sai_"+phase)
		state.robot_id=robot_id;state.command=movement_command();state.terrain_heights=height_scan();state.physics_owner="Godot/Jolt"
		command=exchange(state)
		var base:RigidBody3D=robot.bodies.chassis
		if base.global_basis.y.y<.60:failure="Robot tilt exceeded boarding limit";phase="failed"
		# Log-only actuator snapshot from the same controller command already applied
		# this tick; does not change the control law.
		var sample:Dictionary={"time":carrier.elapsed,"phase":phase,"position":robot.source(base.global_position),"upright":base.global_basis.y.y,"wheels_supported":state.wheels_supported,"command":state.command,"command_source":last_command_source,"input_axes":last_input_axes.duplicate(),"sainiverse_forward_pressed":Input.is_action_pressed("sainiverse_forward"),"manual_control":manual_control,"controller_stage":command.get("stage",""),"physics_hz":Engine.physics_ticks_per_second,"policy_hz":policy_hz}
		sample["policy_action"]=command.get("policy_action",[])
		sample["target_leg"]=command.get("target_leg",[])
		sample["wheel_speed"]=command.get("wheel_speed",[])
		var q_raw=state.get("q",[])
		sample["q"]=q_raw.duplicate() if typeof(q_raw)==TYPE_ARRAY else q_raw
		mission_samples.append(sample)
	if not command.is_empty():robot.apply_command(state,command)
