extends SceneTree
## Run the unchanged 200 Hz MicroDuck controller beside the 60 Hz carrier.

class Pacer extends Node:
	var next_usec:int=0
	func _process(_delta:float)->void:
		if next_usec==0:next_usec=Time.get_ticks_usec()
		next_usec+=5000
		var wait_usec:int=next_usec-Time.get_ticks_usec()
		if wait_usec>0:OS.delay_usec(wait_usec)
		else:next_usec=Time.get_ticks_usec()

class Bridge extends Node:
	var driver:Node3D
	var inbound:=PacketPeerUDP.new()
	var outbound:=PacketPeerUDP.new()
	var tick:=0
	func configure(host:Node3D,receive_port:int,send_port:int)->void:
		driver=host
		if inbound.bind(receive_port,"127.0.0.1")!=OK:
			push_error("MicroDuck worker could not bind its local port")
			get_tree().quit(2)
		outbound.set_dest_address("127.0.0.1",send_port)
	func _physics_process(_delta:float)->void:
		while inbound.get_available_packet_count()>0:
			var packet:Variant=JSON.parse_string(inbound.get_packet().get_string_from_utf8())
			if packet is Dictionary:
				if packet.get("quit",false):get_tree().quit();return
				if packet.has("held"):
					driver._held_now=packet.held
					driver._held_press_order=packet.held.duplicate()
					for action in packet.get("taps",[]):driver._add_tap(str(action))
		if not driver.ready_to_run:return
		tick+=1
		if tick%4!=0:return
		var poses:Dictionary={}
		for name in driver._bodies:
			var body:RigidBody3D=driver._bodies[name]
			var position:Vector3=body.global_position
			var rotation:Quaternion=body.global_basis.get_rotation_quaternion()
			poses[name]=[position.x,position.y,position.z,rotation.x,rotation.y,rotation.z,rotation.w]
		outbound.put_packet(JSON.stringify({"step":driver.session.steps,"fall":driver.session.first_fall,"poses":poses}).to_utf8_buffer())

func _initialize()->void:call_deferred("_start")

func _start()->void:
	Engine.physics_ticks_per_second=200
	var receive_port:=0
	var send_port:=0
	var roller:=false
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--receive-port="):receive_port=int(arg.trim_prefix("--receive-port="))
		elif arg.begins_with("--send-port="):send_port=int(arg.trim_prefix("--send-port="))
		elif arg=="--roller":roller=true
	if receive_port<1024 or send_port<1024:
		push_error("MicroDuck worker requires local IPC ports")
		quit(2);return
	var driver:Node3D=load("res://standalone/driver.gd").new()
	var host:=Node3D.new();host.name="RobotHost";driver.add_child(host)
	var world:=Node3D.new();world.name="World"
	var floor_body:=StaticBody3D.new();floor_body.collision_layer=1;floor_body.collision_mask=16
	var floor_shape:=CollisionShape3D.new();var floor_box:=BoxShape3D.new();floor_box.size=Vector3(40.,.1,40.)
	floor_shape.shape=floor_box;floor_body.position.y=-.05;floor_body.add_child(floor_shape);world.add_child(floor_body)
	driver.add_child(world);root.add_child(driver)
	if roller:
		driver.brain.limits.vmax_x=.35
		driver.motion.settings.heading_hold=true
	var bridge:=Bridge.new();bridge.configure(driver,receive_port,send_port);root.add_child(bridge)
	root.add_child(Pacer.new())
