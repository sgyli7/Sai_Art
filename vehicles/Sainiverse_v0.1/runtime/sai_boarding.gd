extends "res://hub/sai.gd"
## Mission sequencing around the unchanged native locomotion / impedance controller.
var carrier:SceneTree
var phase:="wait_ground"
var mission_samples:Array=[]
var stable_since:=-1.
var completed:=false
var failure:=""
var logged_phase:=""
var phase_times:Dictionary={}

func _ready()->void:
	settings={"task":"drive","skill":""};task="drive";visuals=DisplayServer.get_name()!="headless"
	specification=JSON.parse_string(FileAccess.get_file_as_string("res://sai_agent/robot.json"))
	robot=load("res://sai/compliant_robot.gd").new();add_child(robot);robot.setup(specification,visuals,0.)
	var initial:=Basis(Vector3.UP,PI/2.)
	for body in robot.bodies.values():
		body.position=initial*body.position+Vector3(0.,0.,20.2);body.basis=initial*body.basis
		body.collision_layer=16;body.collision_mask=1|8|32
	native_controller=load("res://sai/native_controller.gd").new()
	if native_controller.last_error!="":failure=native_controller.last_error;push_error(failure);return
	if visuals:
		var paint=load("res://hub/sai_materials.gd").new();paint.scene=self;paint._make_materials();paint._paint_robot();paint.free()
	print("SAINIVERSE_SAI_READY physics_hz=",Engine.physics_ticks_per_second," policy_hz=50")

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
	return native_controller.command(state)

func movement_command()->Array:
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
	if robot.tick%40==0:
		if phase!=logged_phase:
			print("SAI_BOARDING_PHASE ",phase," t=",carrier.elapsed);logged_phase=phase;phase_times[phase]=carrier.elapsed
			if carrier.elapsed>11.:carrier._capture("sai_"+phase)
		state.robot_id="Sai_Agent_001";state.command=movement_command();state.terrain_heights=height_scan();state.physics_owner="Godot/Jolt"
		command=exchange(state)
		var base:RigidBody3D=robot.bodies.chassis
		if base.global_basis.y.y<.60:failure="Robot tilt exceeded boarding limit";phase="failed"
		mission_samples.append({"time":carrier.elapsed,"phase":phase,"position":robot.source(base.global_position),"upright":base.global_basis.y.y,"wheels_supported":state.wheels_supported,"command":state.command,"controller_stage":command.get("stage","")})
	if not command.is_empty():robot.apply_command(state,command)
