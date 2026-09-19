extends "res://standalone/driver.gd"
## Existing native ONNX controller on the carrier's actual collidable cabin/deck.
## Only initialization places bodies. Every subsequent pose is Jolt-integrated.
var carrier: SceneTree
var mode_name := "walk"
var manual_input := false
var spawn_source := Vector3(22.,0.,11.354)
var spawn_world := Vector3(3.,0.,23.)
var evidence: Array = []

func _ready() -> void:
	var host:=Node3D.new();host.name="RobotHost";add_child(host)
	var world:=Node3D.new();world.name="World";add_child(world)
	var replay:Dictionary={} if manual_input else {"segments":[{"at":0.,"held":[]},{"at":1.,"held":["fwd"]},{"at":32. if str(carrier.options.get("mode",""))=="worksite" else 10.,"held":[]}]}
	get_tree().set_meta("microduck_session",{"mode":mode_name,"steps":0,"rows":[],"replay":replay,"trace_path":"","seconds":0.,"segment":-1,"resets":0,"switches":0,"first_fall":null,"started_usec":Time.get_ticks_usec(),"seed":915000,"error":"","events":[],"profiles":{}})
	super._ready()
	if mode_name=="roller":
		brain.limits.vmax_x=.35;motion.settings.heading_hold=true
	for body in _bodies.values():
		body.collision_layer=body.collision_layer<<4;body.collision_mask=(body.collision_mask<<4)|1|8
	DisplayServer.window_set_title("Sainiverse_v0.1")

func _setup_play_ui() -> void:pass
func _follow_camera(_delta:float) -> void:pass

func _handle(command:Variant) -> void:
	if command is Dictionary and command.get("cmd","")=="reset":
		command=command.duplicate(true)
		var offset:Vector3=spawn_world if manual_input else carrier.bodies.front.global_transform*carrier.local_source([spawn_source.x,spawn_source.y,spawn_source.z])
		var source_offset:Vector3=_g2m(offset)
		for pose in command.get("bodies",[]):
			for i in range(3):pose.pos[i]+=source_offset[i]
	super._handle(command)

func _ground_height_at(body_pos:Array) -> float:
	var body:RigidBody3D=carrier.bodies.front
	var point:Vector3=_m2g(Vector3(body_pos[0],body_pos[1],body_pos[2]))
	if manual_input:return carrier.height(point.x+carrier.origin.offset_x,-point.z-carrier.origin.offset_z)
	var local:Vector3=body.to_local(point)
	local.y=spawn_source.z-10.
	return (body.global_transform*local).y

func _decide(held:Array,taps:Array,order:Array,elapsed:float) -> bool:
	if mode_name=="roller" and _base!=null:
		var local:Vector3=carrier.bodies.front.to_local(_base.global_position)
		var cross_track:float=-local.z-spawn_source.y
		var forward:Vector3=carrier.bodies.front.global_basis.x
		motion.target_yaw=atan2(-forward.z,forward.x)-atan2(cross_track,1.5)
		motion.started=true
	var ok:=super._decide(held,taps,order,elapsed)
	if session.steps%5==0 and _base!=null:
		var p:Vector3=carrier.bodies.front.to_local(_base.global_position)
		var contacts:=0
		for body in _bodies.values():
			for other in body.get_colliding_bodies():
				if other==carrier.bodies.front:contacts+=1
		evidence.append({"time":elapsed,"local_source_m":[p.x,-p.z,p.y+10.],"mode":mode_name,"skill":"native_policy","carrier_contacts":contacts,"fell":session.first_fall!=null,"speed_m_s":measured_speed_mps})
	return ok
