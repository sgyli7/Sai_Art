extends "res://hub/sai.gd"
## Mission sequencing around the unchanged native locomotion / impedance controller.
var carrier:SceneTree
var robot_id:="Sai_Agent_001"
var manual_control:=false
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

func _ready()->void:
	settings={"task":"drive","skill":""};task="drive";visuals=DisplayServer.get_name()!="headless"
	var model_path:="res://sai_robots/Sai_Agent_002/robot.json" if robot_id=="Sai_Agent_002" else "res://sai_agent/robot.json"
	specification=JSON.parse_string(FileAccess.get_file_as_string(model_path))
	if specification==null or str(specification.get("robot_id",""))!=robot_id:failure="Sai model identity mismatch: "+robot_id;push_error(failure);return
	robot=load("res://sai/compliant_robot.gd").new();add_child(robot);robot.setup(specification,visuals,0.)
	var initial:=manual_spawn_basis if manual_spawn_valid else Basis.IDENTITY if cockpit_demo else Basis(Vector3.UP,PI/2.)
	var spawn:Vector3=manual_spawn_world if manual_spawn_valid else carrier.bodies.front.global_transform*carrier.local_source([30.90,-1.58,12.25]) if cockpit_demo else Vector3(0.,0.,20.2)
	if manual_control and not cockpit_demo and not manual_spawn_valid:
		spawn.z=100.2
		spawn.y=carrier.height(spawn.x+carrier.origin.offset_x,-spawn.z-carrier.origin.offset_z)
	for body in robot.bodies.values():
		body.position=initial*body.position+spawn;body.basis=initial*body.basis
		body.collision_layer=16;body.collision_mask=1|8|32
		if cockpit_demo and body.name in ["arm_gripper","arm_moving_jaw"]:
			body.collision_mask|=128;body.contact_monitor=true;body.max_contacts_reported=8
	native_controller=load("res://sai/native_controller.gd").new()
	if native_controller.last_error!="":failure=native_controller.last_error;push_error(failure);return
	if cockpit_demo:arm_solver=load("res://sai/native_grab_controller.gd").new(native_controller,specification)
	if visuals:
		var paint=load("res://hub/sai_materials.gd").new();paint.scene=self;paint._make_materials();paint._paint_robot();paint.free()
	print("SAINIVERSE_SAI_READY robot=",robot_id," physics_hz=",Engine.physics_ticks_per_second," policy_hz=50")

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
	state.hub_config=settings;state.stair_course=false;state.experimental_profile=false
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
	if cockpit_demo:return [0.,0.,0.]
	if manual_control:
		return [Input.get_axis("sainiverse_reverse","sainiverse_forward")*.14,Input.get_axis("sainiverse_right","sainiverse_left")*.45,0.]
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
	if phase not in ["approach","exit"]:return [0.,0.,0.]
	var target:Vector3=platform.global_position if phase=="approach" else front.global_transform*carrier.local_source([0.,-10.8,7.45])
	var delta:Vector3=target-base.global_position
	var desired:float=atan2(-delta.z,delta.x);var actual:float=atan2(-base.global_basis.x.z,base.global_basis.x.x)
	return [.14,clampf(2.*wrapf(desired-actual,-PI,PI),-.45,.45),0.]

func _physics_process(_delta:float)->void:
	if robot==null or native_controller==null or failure!="":return
	var state:Dictionary=robot.state()
	if robot.tick%maxi(1,Engine.physics_ticks_per_second/50)==0:
		if phase!=logged_phase:
			print("SAI_BOARDING_PHASE ",phase," t=",carrier.elapsed);logged_phase=phase;phase_times[phase]=carrier.elapsed
			if carrier.elapsed>11.:carrier._capture("sai_"+phase)
		state.robot_id=robot_id;state.command=movement_command();state.terrain_heights=height_scan();state.physics_owner="Godot/Jolt"
		command=exchange(state)
		var base:RigidBody3D=robot.bodies.chassis
		if base.global_basis.y.y<.60:failure="Robot tilt exceeded boarding limit";phase="failed"
		mission_samples.append({"time":carrier.elapsed,"phase":phase,"position":robot.source(base.global_position),"upright":base.global_basis.y.y,"wheels_supported":state.wheels_supported,"command":state.command,"controller_stage":command.get("stage","")})
	if not command.is_empty():robot.apply_command(state,command)
