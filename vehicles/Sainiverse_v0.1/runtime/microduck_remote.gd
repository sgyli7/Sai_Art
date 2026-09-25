extends Node3D
## Visual and input bridge to the independent 200 Hz MicroDuck world.
var carrier:SceneTree
var mode_name:="walk"
var manual_input:=true
var dormant:=false
var spawn_world:=Vector3.ZERO
var spawn_source:=Vector3.ZERO
var manual_ground_on_carrier:=false
var evidence:Array=[]
var session:Dictionary={"first_fall":null,"error":""}
var _base:Node3D
var avatar:Node3D
var body_nodes:Dictionary={}
var receive:=PacketPeerUDP.new()
var send:=PacketPeerUDP.new()
var receive_port:=0
var worker_pid:=0
var attached_to_carrier:=false
var local_anchor:=Vector3.ZERO
var world_anchor:=Vector3.ZERO
var pending_taps:Array=[]
var last_packet_usec:=0
var received_steps:=0
var started_usec:=0
var rendered_carrier:=Transform3D.IDENTITY
var rendered_frame:=-1
var pose_current:Dictionary={}
var pose_snap_pending:=true
var camera_snap_pending:=true
var last_evidence_step:=-1

func apply_visual_style(robot_root:Node,robot_scene:String)->void:
	var style_script:=load("res://visuals/microduck/style.gd")
	if style_script==null or robot_root==null:return
	style_script.new().apply_robot(robot_root,robot_scene)

func _strip_physics(node:Node)->void:
	for child in node.get_children():
		if child is Joint3D or child is CollisionShape3D:child.free()
		else:_strip_physics(child)

func _ready()->void:
	started_usec=Time.get_ticks_usec()
	physics_interpolation_mode=Node.PHYSICS_INTERPOLATION_MODE_OFF
	var deployment:Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://runtime_assets/deployment.json"))
	var robot:Dictionary=deployment.robots["roller" if mode_name=="roller" else "walk"]
	avatar=load(str(robot.scene)).instantiate()
	_strip_physics(avatar)
	for child in avatar.get_children():
		if child is RigidBody3D:
			child.freeze=true
			child.collision_layer=0
			child.collision_mask=0
			body_nodes[str(child.name)]=child
	add_child(avatar)
	apply_visual_style(avatar,str(robot.scene))
	_base=body_nodes.get(str(robot.base_body))
	if _base==null:_base=body_nodes.get("trunk_base")
	world_anchor=spawn_world
	if dormant:
		set_physics_process(false)
		return
	var candidate:int=21000+int(OS.get_process_id()%1000)*2
	for offset in range(0,200,2):
		if receive.bind(candidate+offset,"127.0.0.1")==OK:
			receive_port=candidate+offset
			break
	if receive_port==0:
		session.error="MicroDuck 本地通信端口不可用"
		return
	send.set_dest_address("127.0.0.1",receive_port+1)
	var arguments:=PackedStringArray(["--headless","--fixed-fps","200","--path",ProjectSettings.globalize_path("res://"),"--script","res://standalone/carrier_worker.gd","--","--receive-port="+str(receive_port+1),"--send-port="+str(receive_port),"--parent-pid="+str(OS.get_process_id())])
	if mode_name=="roller":arguments.append("--roller")
	worker_pid=OS.create_process(OS.get_executable_path(),arguments)
	if worker_pid<=0:session.error="MicroDuck 200 Hz 进程启动失败"

func _exit_tree()->void:
	if worker_pid>0:
		send.put_packet('{"quit":true}'.to_utf8_buffer())
		OS.kill(worker_pid)
		worker_pid=0

func set_destination(destination:Dictionary)->void:
	attached_to_carrier=bool(destination.carrier_surface)
	if attached_to_carrier:
		local_anchor=carrier.bodies.front.to_local(destination.world)
	else:world_anchor=destination.world
	pose_snap_pending=true
	camera_snap_pending=true
	_add_tap("reset")

func _add_tap(action:String)->void:
	if not pending_taps.has(action):pending_taps.append(action)

func _physics_process(_dt:float)->void:
	if worker_pid<=0:return
	var held:Array=[]
	for binding in [[KEY_W,"fwd"],[KEY_S,"back"],[KEY_A,"left"],[KEY_D,"right"],[KEY_Q,"strafe_l"],[KEY_E,"strafe_r"]]:
		if Input.is_physical_key_pressed(binding[0]):held.append(binding[1])
	var packet:Dictionary={"held":held,"taps":pending_taps}
	send.put_packet(JSON.stringify(packet).to_utf8_buffer())
	pending_taps=[]

func _process(dt:float)->void:
	update_rendered_pose(dt)

func update_rendered_pose(dt:float)->void:
	# The SceneTree camera runs independently of Node processing. Ensure the
	# robot and camera use the same interpolated carrier pose in each frame.
	var frame:int=Engine.get_process_frames()
	if rendered_frame==frame:return
	rendered_frame=frame
	# Both the 60 Hz carrier and 50 Hz pose stream are interpolated for rendering.
	# Physics bodies, joints and control timing remain unchanged.
	rendered_carrier=carrier.bodies.front.get_global_transform_interpolated()
	if attached_to_carrier:global_transform=rendered_carrier*Transform3D(Basis.IDENTITY,local_anchor)
	else:global_transform=Transform3D(Basis.IDENTITY,world_anchor)
	while receive.get_available_packet_count()>0:
		var packet:Variant=JSON.parse_string(receive.get_packet().get_string_from_utf8())
		if not packet is Dictionary or not packet.has("poses"):continue
		last_packet_usec=Time.get_ticks_usec()
		received_steps=int(packet.step)
		session.first_fall=packet.get("fall",null)
		var next_poses:Dictionary={}
		for name in packet.poses:
			if not body_nodes.has(name):continue
			var pose:Array=packet.poses[name]
			if pose.size()!=7:continue
			var rotation:=Quaternion(float(pose[3]),float(pose[4]),float(pose[5]),float(pose[6])).normalized()
			next_poses[name]=Transform3D(Basis(rotation),Vector3(float(pose[0]),float(pose[1]),float(pose[2])))
		if pose_snap_pending or pose_current.is_empty():
			for name in next_poses:body_nodes[name].transform=next_poses[name]
			pose_snap_pending=false
			camera_snap_pending=true
		pose_current=next_poses
	if not pose_current.is_empty():
		var alpha:=1.-exp(-45.*clampf(dt,0.,.1))
		for name in pose_current:
			body_nodes[name].transform=body_nodes[name].transform.interpolate_with(pose_current[name],alpha)
	if received_steps%10==0 and received_steps!=last_evidence_step and _base!=null and not pose_current.is_empty():
		last_evidence_step=received_steps
		var local:Vector3=carrier.bodies.front.to_local(_base.global_position)
		evidence.append({"time":carrier.elapsed,"local_source_m":[local.x,-local.z,local.y+10.],"fell":session.first_fall!=null,"worker_steps":received_steps})
	if worker_pid>0 and last_packet_usec==0 and Time.get_ticks_usec()-started_usec>8_000_000:
		session.error="MicroDuck 200 Hz 进程没有返回姿态"
