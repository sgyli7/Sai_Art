extends "@SAI_ROOT@/runtime/atelier_review.gd"
const HERE="@SAI_ROOT@"
var lift_data:Array=[]
var lift_links:Dictionary={}
var lift_targets:Dictionary={}
var lift_commands:Dictionary={}
var lift_samples:Array=[]
var lift_stability:Array=[]
var drive_interlock:=false
var selected_lift:=0
var doors_open:=false
var cam_mode:=0
var orbit_yaw:=.82
var orbit_pitch:=.40
var orbit_radius:=135.
var mouse_drag:=false
var hud:Label
var pv_caption:Label
var manual:=true
var camera_ready:=false
var free_position:=Vector3.ZERO
var camera_names=["整车环视","主控模块","驾驶舱","升降平台","自由观察","材质近景","驾驶舱支架","底部传动"]
var lift_peak_error:=0.
var lift_payload_mass:Dictionary={}
var requested_drive_speed:=0.
var witness:RigidBody3D
var witness_samples:Array=[]
var patrol_camera:Camera3D
var controller_usec:=0
var controller_steps:=0
var cargo=null
var equipment=null
var cockpit=null
var acceptance_frame_start_usec:int=0
var acceptance_rendered_frames:int=0
var operation_ui=null
var patrol=null
var sai_passenger=null
var parked_robots:Dictionary={}
var parked_boarding_fixture:=false
var parked_patrol_fixture:=false
var active_robot_kind:="vehicle"
var robot_switch_busy:=false
var robot_switch_message:=""
var robot_switch_message_until:=0.0
var robot_switch_history:Array=[]
var quick_travel_history:Array=[]
var active_quick_location:=0
var f1_panorama_dragged:=false
var f1_panorama_yaw:=0.
var f1_panorama_pitch:=0.
var f1_panorama_radius:=0.
var travel_probe_sequence:PackedStringArray=PackedStringArray()
var last_travel_probe_index:=-1
var switch_probe_sequence:PackedStringArray=PackedStringArray()
var last_switch_probe_index:=-1
var switch_probe_forward:=false
var remote_probe_stage:=0
var dual_probe_switch_done:=false
var remote_probe_keys:Dictionary={}
var remote_probe_samples:Array=[]
var camera_motion_samples:Array=[]
var manual_camera_target:=Vector3.ZERO
var manual_camera_target_valid:=false
var manual_camera_last_usec:=0
var saved_vehicle_orbit:Array=[]
var ramp_links:Dictionary={}
var ramp_targets:Dictionary={}
var ramp_samples:Array=[]
var sai60_physics_hz_samples:Array=[]
const QUICK_LOCATION_NAMES:Dictionary={1:"车旁雪地",2:"甲板",3:"驾驶舱"}

func _sai60_coworld()->bool:
	return OS.get_environment("SAINIVERSE_SAI60_POLICY")!=""

func _build()->void:
	manual=str(options.get("mode","manual")) in ["manual","ui_test","lift_preview_cycle"]
	if str(options.get("mode",""))=="sai_cockpit":options.seconds=minf(float(options.seconds),13.97)
	requested_drive_speed=float(options.get("speed",0.))
	if OS.has_environment("SAINIVERSE_SWITCH_PROBE") and OS.get_environment("SAINIVERSE_SWITCH_PROBE")!="":switch_probe_sequence=OS.get_environment("SAINIVERSE_SWITCH_PROBE").split(",")
	if OS.has_environment("SAINIVERSE_TRAVEL_PROBE") and OS.get_environment("SAINIVERSE_TRAVEL_PROBE")!="":travel_probe_sequence=OS.get_environment("SAINIVERSE_TRAVEL_PROBE").split(",")
	super._build()
	# The 60 Hz interactive solver produces sub-millimetre door motion with
	# short angular-rate spikes; a latched, closed door remains safe to drive.
	if manual and access!=null:access.drive_closed_rate_limit_rad_s=.12
	for binding in [["sainiverse_forward",KEY_W],["sainiverse_reverse",KEY_S],["sainiverse_left",KEY_A],["sainiverse_right",KEY_D]]:
		if InputMap.has_action(binding[0]):continue
		InputMap.add_action(binding[0]);var event:=InputEventKey.new();event.physical_keycode=binding[1]
		InputMap.action_add_event(binding[0],event)
	if str(options.get("terrain",""))=="polar" and DisplayServer.get_name()!="headless":
		for child in stage.get_children():
			if child is WorldEnvironment:
				var sky:=Sky.new();var sky_material:=ShaderMaterial.new();sky_material.shader=load(HERE+"/assets/polar_sky.gdshader")
				sky.sky_material=sky_material;child.environment.sky=sky;child.environment.background_mode=Environment.BG_SKY
				child.environment.ambient_light_energy=.34
			elif child is DirectionalLight3D:child.light_energy=.72
		for child in world_surface.get_children():
			if child is MeshInstance3D:
				var snow:=ShaderMaterial.new();snow.shader=load(HERE+"/assets/polar_snow.gdshader")
				child.material_override=snow;child.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	# The full 200 Hz qualification loop costs more than its 5 ms budget on the
	# complete rendered vehicle. Use 60 Hz while humans drive or MicroDuck
	# waits for its parked carrier; the Sai boarding fixture has its own staging
	# rate. Switch to the robot's verified rate after freezing the carrier.
	# Qualification modes keep 200 Hz.
	var robot_staging:bool=str(options.get("mode","")) in ["cabin_patrol","cockpit_patrol","deck_patrol","sai_board","sai_board_002","sai_cockpit"]
	var boarding_staging:bool=str(options.get("mode","")) in ["sai_board","sai_board_002","sai_cockpit"]
	if manual or robot_staging:
		# 60/60 ONNX coworld path must never stage at 100 Hz then jump to 1000/2000.
		var preferred_hz:int=60 if _sai60_coworld() else 100 if boarding_staging else int(OS.get_environment("SAINIVERSE_INTERACTIVE_HZ")) if manual and OS.has_environment("SAINIVERSE_INTERACTIVE_HZ") else 60
		Engine.physics_ticks_per_second=clampi(preferred_hz,60,200)
		Engine.max_physics_steps_per_frame=12
	equipment=load(HERE+"/runtime/equipment_control.gd").new();equipment.configure(self,spec.contact.equipment)
	equipment.auto_work=str(options.get("mode","")) in ["worksite","equipment_cycle"]
	lift_data=spec.contact.boarding_lifts
	for lift in lift_data:
		lift_commands[lift.name]=false;lift_payload_mass[lift.name]=0.
		for name in lift.groups:
			lift_targets[name]=0.
			for link in links:
				if link.spec.name==name:lift_links[name]=link;break
		var platform:RigidBody3D=bodies[lift.groups[3]]
		platform.collision_layer=8;platform.collision_mask=1|16
		platform.contact_monitor=true;platform.max_contacts_reported=8
		var collider:=CollisionShape3D.new();var shape:=BoxShape3D.new();shape.size=Vector3(3.2,.25,2.2);collider.shape=shape;platform.add_child(collider)
		for x in [-1.48,1.48]:
			var guard:=CollisionShape3D.new();var box:=BoxShape3D.new();box.size=Vector3(.08,1.05,2.2);guard.shape=box;guard.position=Vector3(x,.65,0);platform.add_child(guard)
	for lift in lift_data:
		var ramp:Dictionary=lift.ramp;var body:RigidBody3D=bodies[ramp.name]
		ramp_targets[ramp.name]=0.
		for link in links:
			if link.spec.name==ramp.name:ramp_links[ramp.name]=link;break
		body.collision_layer=8;body.collision_mask=1|16|32;body.contact_monitor=true;body.max_contacts_reported=16
		var col:=CollisionShape3D.new();var shape:=BoxShape3D.new();shape.size=vec(ramp.size_m).abs();col.shape=shape;col.position=Vector3.UP
		body.add_child(col)
	for hull in ["front","rear","tail"]:
		var body:RigidBody3D=bodies[hull];body.collision_layer=body.collision_layer|8;body.collision_mask=body.collision_mask|16
		for section in [[Vector3(0,-3.05,0),Vector3(34,1.,24.3)],[Vector3(-9.32,-3.05,0),Vector3(15.36,1.,27)],[Vector3(9.32,-3.05,0),Vector3(15.36,1.,27)]]:
			var shape:=BoxShape3D.new();shape.size=section[1];var col:=CollisionShape3D.new();col.shape=shape;col.position=section[0];body.add_child(col)
	for lift in lift_data:
		var hull:RigidBody3D=bodies[lift.hull];var bridge:=CollisionShape3D.new();var shape:=BoxShape3D.new();shape.size=Vector3(3.10,.06,.27);bridge.shape=shape
		bridge.position=vec([0.,float(lift.side)*12.05,7.42])-vec([0.,0.,10.]);hull.add_child(bridge)
	var inputs=load(HERE+"/runtime/input_receiver.gd").new();inputs.controller=self;stage.add_child(inputs)
	if str(options.get("pv","false"))=="true":
		var title_layer:=CanvasLayer.new();stage.add_child(title_layer);pv_caption=Label.new();title_layer.add_child(pv_caption)
		pv_caption.position=Vector2(22,20);pv_caption.add_theme_font_size_override("font_size",21);pv_caption.add_theme_color_override("font_shadow_color",Color.BLACK);pv_caption.add_theme_constant_override("shadow_offset_x",2);pv_caption.add_theme_constant_override("shadow_offset_y",2);pv_caption.add_theme_color_override("font_outline_color",Color.BLACK);pv_caption.add_theme_constant_override("outline_size",5)
	for child in stage.get_children():
		if child is WorldEnvironment:child.environment.background_color=Color("EEF1EA")
	figures.visible=false
	camera_ready=true
	# Platform and payload use the rendered ground fixture for actual contact.
	var ground_body:=StaticBody3D.new();ground_body.name="BoardingGround";ground_body.collision_layer=1;ground_body.collision_mask=8|16;world_surface.add_child(ground_body)
	var ground_shape:=CollisionShape3D.new()
	if str(options.get("terrain","flat"))=="flat":ground_shape.shape=WorldBoundaryShape3D.new()
	else:
		for child in world_surface.get_children():
			if child is MeshInstance3D:
				var tri:=ConcavePolygonShape3D.new();tri.set_faces(child.mesh.get_faces());ground_shape.shape=tri;break
	ground_body.add_child(ground_shape)

	DisplayServer.window_set_title("Sainiverse_v0.1")
	if str(options.get("view",""))=="detail":cam_mode=1;orbit_radius=65.
	if str(options.get("view",""))=="art":cam_mode=5;orbit_radius=24.;orbit_yaw=.98;orbit_pitch=.30
	if str(options.get("view",""))=="port":cam_mode=1;orbit_radius=65.;orbit_yaw=-.82
	if str(options.get("view",""))=="support":cam_mode=6;orbit_radius=27.;orbit_yaw=.85;orbit_pitch=.05
	if str(options.get("view",""))=="underbody":cam_mode=7;orbit_radius=30.;orbit_yaw=1.05;orbit_pitch=.015
	if str(options.get("view",""))=="lift":cam_mode=3;orbit_radius=15.
	if str(options.get("mode","")) in ["lift_cycle","lift_preview_cycle"]:
		witness=RigidBody3D.new();witness.name="TEST_500kg_payload";witness.mass=500.;witness.collision_layer=16;witness.collision_mask=1|8;witness.can_sleep=false
		stage.add_child(witness);witness.global_position=bodies[lift_data[0].groups[3]].global_position+Vector3.UP*.475
		var shape:=BoxShape3D.new();shape.size=Vector3(.9,.6,.9);var col:=CollisionShape3D.new();col.shape=shape;witness.add_child(col)
		var mesh:=MeshInstance3D.new();var cube:=BoxMesh.new();cube.size=shape.size;mesh.mesh=cube;var mat:=StandardMaterial3D.new();mat.albedo_color=Color("D5AD3D");mesh.material_override=mat;witness.add_child(mesh)
	cargo=load(HERE+"/runtime/cargo_handling.gd").new();cargo.configure(self)
	cockpit=load(HERE+"/runtime/cockpit_control.gd").new();cockpit.configure(self,spec.contact.cockpit)
	operation_ui=load(HERE+"/runtime/operation_ui.gd").new();stage.add_child(operation_ui);operation_ui.configure(self)
	camera.physics_interpolation_mode=Node.PHYSICS_INTERPOLATION_MODE_OFF
	world_surface.physics_interpolation_mode=Node.PHYSICS_INTERPOLATION_MODE_OFF
	if manual and DisplayServer.get_name()!="headless":_build_parked_robots()
	_camera()

func _build_parked_robots()->void:
	for kind in ["microduck","roller","sai001","sai002"]:
		var destination:Dictionary=_quick_destination(3,kind)
		var node
		if kind in ["microduck","roller"]:
			node=load(HERE+"/runtime/microduck_remote.gd").new()
			node.carrier=self
			node.mode_name="roller" if kind=="roller" else "walk"
			node.spawn_world=destination.world
			node.dormant=true
			stage.add_child(node)
			node.set_destination(destination)
		else:
			node=load(HERE+"/runtime/sai_boarding.gd").new()
			node.carrier=self
			node.robot_id="Sai_Agent_002" if kind=="sai002" else "Sai_Agent_001"
			node.manual_spawn_valid=true
			node.manual_spawn_world=destination.world
			node.manual_spawn_basis=destination.basis
			node.visual_only=true
			stage.add_child(node)
		parked_robots[kind]=node

func _enable_f1_panorama_orbit()->void:
	if f1_panorama_dragged:return
	var initial:=Vector3(95.,54.,105.)
	f1_panorama_yaw=atan2(initial.z,initial.x)
	f1_panorama_pitch=asin(initial.y/initial.length())
	f1_panorama_radius=initial.length()
	f1_panorama_dragged=true

func _release_quick_robot_camera()->void:
	if active_quick_location not in [2,3]:return
	var remote_view:bool=patrol!=null and patrol.has_method("set_destination")
	var robot_target:Vector3=manual_camera_target if remote_view and manual_camera_target_valid else _selected_robot_position()+Vector3.UP*(.2 if active_robot_kind in ["sai001","sai002"] else .1)
	var view_offset:Vector3=camera.global_position-robot_target
	if view_offset.length()>.2:
		orbit_radius=clampf(view_offset.length(),.75,12.)
		orbit_yaw=atan2(view_offset.z,view_offset.x)
		orbit_pitch=asin(clampf(view_offset.y/view_offset.length(),-1.,1.))
	active_quick_location=0

func handle_input(event:InputEvent)->void:
	if not camera_ready or not manual:return
	if not switch_probe_sequence.is_empty() or OS.get_environment("SAINIVERSE_DRIVE_PROBE")=="1":
		stage.get_viewport().set_input_as_handled()
		return
	if event is InputEventMouse and operation_ui!=null and operation_ui.captures_point(event.position):return
	if event is InputEventKey and event.pressed and not event.echo and event.physical_keycode in [KEY_F5,KEY_F6,KEY_F7,KEY_F8,KEY_F9]:
		select_robot_mode({KEY_F5:"microduck",KEY_F6:"roller",KEY_F7:"sai001",KEY_F8:"sai002",KEY_F9:"vehicle"}[event.physical_keycode])
		stage.get_viewport().set_input_as_handled()
		return
	if event is InputEventKey and event.pressed and not event.echo and event.physical_keycode in [KEY_F1,KEY_F2,KEY_F3]:
		quick_travel({KEY_F1:1,KEY_F2:2,KEY_F3:3}[event.physical_keycode])
		stage.get_viewport().set_input_as_handled()
		return
	if active_robot_kind=="vehicle":cockpit.input(event)
	if event is InputEventMouseButton:
		if event.button_index==MOUSE_BUTTON_RIGHT:mouse_drag=event.pressed
		if event.pressed and event.button_index in [MOUSE_BUTTON_WHEEL_UP,MOUSE_BUTTON_WHEEL_DOWN]:
			if active_robot_kind!="vehicle":
				if active_quick_location==1:_enable_f1_panorama_orbit()
				else:_release_quick_robot_camera()
			var factor:float=.88 if event.button_index==MOUSE_BUTTON_WHEEL_UP else 1./.88
			if active_quick_location==1:f1_panorama_radius=clampf(f1_panorama_radius*factor,50.,350.)
			else:orbit_radius=clampf(orbit_radius*factor,4. if active_robot_kind=="vehicle" else .75,600.)
	if event is InputEventMouseMotion and mouse_drag:
		if active_robot_kind!="vehicle" and active_quick_location==1:
			_enable_f1_panorama_orbit()
			f1_panorama_yaw-=event.relative.x*.004
			f1_panorama_pitch=clampf(f1_panorama_pitch+event.relative.y*.003,-1.35,1.35)
		else:
			if active_robot_kind!="vehicle":_release_quick_robot_camera()
			orbit_yaw-=event.relative.x*.004;orbit_pitch=clampf(orbit_pitch+event.relative.y*.003,-1.35,1.35)
	if active_robot_kind!="vehicle" and event is InputEventMouse and (mouse_drag or event is InputEventMouseButton):stage.get_viewport().set_input_as_handled()
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_ESCAPE:
				options.seconds=elapsed+.02;manual=false;options.speed=0.
			KEY_TAB:
				if active_robot_kind=="vehicle":set_camera_mode((cam_mode+1)%camera_names.size())
			KEY_T:switch_theme()
			KEY_F12:_capture("manual_"+str(Time.get_ticks_msec()))

func _manual_md_remote_preview(kind:String)->bool:
	return manual and kind in ["microduck","roller"] and (DisplayServer.get_name()!="headless" or OS.get_environment("SAINIVERSE_REMOTE_MD_PREVIEW")=="1" or OS.get_environment("SAINIVERSE_REMOTE_PROBE")=="1")

func _manual_carrier_live(kind:String,remote_md:bool)->bool:
	return kind=="vehicle" or (manual and (remote_md or (kind in ["sai001","sai002"] and _sai60_coworld())))

func _manual_md_script(kind:String)->String:
	return HERE+("/runtime/microduck_remote.gd" if _manual_md_remote_preview(kind) else "/runtime/microduck_patrol.gd")

func _make_manual_md(kind:String)->Node:
	var node=load(_manual_md_script(kind)).new();node.carrier=self;node.manual_input=true
	node.mode_name="walk" if kind=="microduck" else "roller"
	return node

func select_robot_mode(kind:String)->void:
	if kind not in ["vehicle","microduck","roller","sai001","sai002"] or robot_switch_busy:return
	if kind==active_robot_kind:return
	robot_switch_busy=true;robot_switch_message="正在切换机器人…"
	call_deferred("_switch_robot_mode",kind)

func _quick_destination(index:int,kind:String)->Dictionary:
	if index==1:
		# Near the front boarding lift; the first camera view still frames the
		# complete 130 m carrier before returning to robot follow on movement.
		var ground:=Vector3(0.,0.,25.5)
		ground.y=height(ground.x+origin.offset_x,-ground.z-origin.offset_z)
		return {"world":ground,"source":Vector3.ZERO,"carrier_surface":false,"basis":Basis(Vector3.UP,PI/2.)}
	var source:Vector3=Vector3(-12.,-12.5,7.454) if index==2 else Vector3(27.5,.5,11.354) if kind=="sai002" else Vector3(27.5,-.4,11.354) if kind=="sai001" else Vector3(25.,1.2,11.354) if kind=="roller" else Vector3(25.,0.,11.354)
	return {"world":bodies.front.global_transform*local_source([source.x,source.y,source.z]),
		"source":source,"carrier_surface":true,"basis":Basis.IDENTITY if index==3 else Basis(Vector3.UP,PI/2.)}

func quick_travel(index:int)->void:
	if not QUICK_LOCATION_NAMES.has(index) or robot_switch_busy:return
	if active_robot_kind=="vehicle":
		robot_switch_message="请先切换到机器人，再使用 F1–F3 快速移动"
		robot_switch_message_until=elapsed+2.
		return
	var destination:=_quick_destination(index,active_robot_kind)
	active_quick_location=index
	f1_panorama_dragged=false
	if operation_ui!=null:operation_ui._release_robot_keys()
	robot_switch_message="快速移动："+QUICK_LOCATION_NAMES[index]
	robot_switch_message_until=elapsed+2.
	var point:Vector3=destination.world
	quick_travel_history.append({"time":elapsed,"robot":active_robot_kind,"station":index,
		"name":QUICK_LOCATION_NAMES[index],"target_world":[point.x,point.y,point.z]})
	if active_robot_kind in ["microduck","roller"] and patrol!=null:
		if patrol.has_method("set_destination"):patrol.set_destination(destination)
		else:
			patrol.spawn_world=destination.world
			patrol.spawn_source=destination.source
			patrol.manual_ground_on_carrier=destination.carrier_surface
			patrol._add_tap("reset")
	elif active_robot_kind in ["sai001","sai002"] and sai_passenger!=null:
		robot_switch_busy=true
		call_deferred("_respawn_sai_at",active_robot_kind,destination)

func _respawn_sai_at(kind:String,destination:Dictionary)->void:
	if sai_passenger!=null:sai_passenger.queue_free();sai_passenger=null
	await process_frame
	sai_passenger=load(HERE+"/runtime/sai_boarding.gd").new()
	sai_passenger.carrier=self;sai_passenger.manual_control=true
	sai_passenger.robot_id="Sai_Agent_002" if kind=="sai002" else "Sai_Agent_001"
	sai_passenger.manual_spawn_valid=true
	sai_passenger.manual_spawn_world=destination.world
	sai_passenger.manual_spawn_basis=destination.basis
	stage.add_child(sai_passenger)
	robot_switch_busy=false

func _selected_robot_position()->Vector3:
	if patrol!=null and patrol._base!=null:return patrol._base.global_position
	if sai_passenger!=null and sai_passenger.robot!=null:return sai_passenger.robot.bodies.chassis.global_position
	return Vector3.ZERO

func _probe_forward(pressed:bool)->void:
	if switch_probe_forward==pressed:return
	switch_probe_forward=pressed
	var event:=InputEventKey.new();event.physical_keycode=KEY_W;event.keycode=KEY_W;event.pressed=pressed
	Input.parse_input_event(event)

func _remote_probe_key(code:int,pressed:bool)->void:
	if bool(remote_probe_keys.get(code,false))==pressed:return
	remote_probe_keys[code]=pressed
	var event:=InputEventKey.new();event.physical_keycode=code;event.keycode=code;event.pressed=pressed
	Input.parse_input_event(event)

func _remote_probe_sample()->void:
	var robot_base:Node3D=patrol._base if patrol!=null and patrol._base!=null else sai_passenger.robot.bodies.chassis if sai_passenger!=null and sai_passenger.robot!=null else null
	if robot_base==null:return
	var front:RigidBody3D=bodies.front
	var facing:Vector3=front.global_basis.inverse()*robot_base.global_basis.x
	var local:Vector3=front.to_local(robot_base.global_position)
	remote_probe_samples.append({"time":elapsed,"car_x_m":front.global_position.x,"car_speed_m_s":front.linear_velocity.length(),"car_frozen":front.freeze,"up":Input.is_physical_key_pressed(KEY_UP),"car_left":Input.is_physical_key_pressed(KEY_LEFT),"car_right":Input.is_physical_key_pressed(KEY_RIGHT),"robot_forward":Input.is_physical_key_pressed(KEY_W),"left":Input.is_physical_key_pressed(KEY_A),"right":Input.is_physical_key_pressed(KEY_D),"robot_local":[local.x,local.y,local.z],"robot_yaw_rad":atan2(-facing.z,facing.x),"robot_fall":patrol.session.first_fall if patrol!=null else sai_passenger.failure,"worker_steps":patrol.received_steps if patrol!=null else 0})

func _switch_robot_mode(kind:String)->void:
	if parked_robots.has(active_robot_kind):parked_robots[active_robot_kind].visible=true
	active_quick_location=0
	f1_panorama_dragged=false
	var ground_destination:Dictionary=_quick_destination(3,kind) if kind!="vehicle" else {}
	manual_camera_target_valid=false
	manual_camera_last_usec=0
	if active_robot_kind=="vehicle" and kind!="vehicle":
		saved_vehicle_orbit=[orbit_radius,orbit_yaw,orbit_pitch]
		orbit_radius=6.;orbit_yaw=.98;orbit_pitch=.28
	elif kind=="vehicle" and saved_vehicle_orbit.size()==3:
		orbit_radius=saved_vehicle_orbit[0];orbit_yaw=saved_vehicle_orbit[1];orbit_pitch=saved_vehicle_orbit[2]
	if robot_switch_history.size()>0 and active_robot_kind!="vehicle":
		var previous:Dictionary=robot_switch_history[robot_switch_history.size()-1]
		if previous.has("start_world"):
			var point:=_selected_robot_position()
			var start:Array=previous.start_world
			previous["distance_m"]=Vector2(point.x-float(start[0]),point.z-float(start[2])).length()
			previous["end_world"]=[point.x,point.y,point.z]
		if patrol!=null:previous["first_fall"]=patrol.session.first_fall
		if sai_passenger!=null:previous["failure"]=sai_passenger.failure
	if patrol!=null:patrol.queue_free();patrol=null
	if sai_passenger!=null:sai_passenger.queue_free();sai_passenger=null
	await process_frame
	var remote_md:bool=_manual_md_remote_preview(kind)
	var live_carrier:bool=_manual_carrier_live(kind,remote_md)
	physics_interpolation=remote_md
	for name in bodies:bodies[name].freeze=not live_carrier
	parked_patrol_fixture=not live_carrier
	parked_boarding_fixture=false
	Engine.physics_ticks_per_second=60 if live_carrier else 200 if kind in ["microduck","roller"] else 1000
	Engine.max_physics_steps_per_frame=12 if live_carrier else 16 if kind in ["microduck","roller"] else 256
	if not live_carrier:
		for axis in ["throttle","steer","brake"]:cockpit.ui_axes[axis]=0.
	if kind in ["microduck","roller"]:
		patrol=_make_manual_md(kind)
		patrol.spawn_world=ground_destination.world
		stage.add_child(patrol)
		if remote_md and patrol.has_method("set_destination"):patrol.set_destination(ground_destination)
	elif kind in ["sai001","sai002"]:
		sai_passenger=load(HERE+"/runtime/sai_boarding.gd").new();sai_passenger.carrier=self;sai_passenger.manual_control=true
		sai_passenger.robot_id="Sai_Agent_002" if kind=="sai002" else "Sai_Agent_001"
		sai_passenger.manual_spawn_valid=true
		sai_passenger.manual_spawn_world=ground_destination.world
		sai_passenger.manual_spawn_basis=ground_destination.basis
		stage.add_child(sai_passenger)
	if not ground_destination.is_empty():
		active_quick_location=3
		var point:Vector3=ground_destination.world
		quick_travel_history.append({"time":elapsed,"robot":kind,"station":3,"name":QUICK_LOCATION_NAMES[3],
			"initial_spawn":true,"target_world":[point.x,point.y,point.z]})
	if parked_robots.has(kind):parked_robots[kind].visible=false
	active_robot_kind=kind;robot_switch_history.append({"time":elapsed,"robot":kind,"physics_hz":Engine.physics_ticks_per_second,"robot_worker_hz":200 if remote_md else Engine.physics_ticks_per_second});robot_switch_busy=false;robot_switch_message=""

func set_camera_mode(index:int)->void:
	cam_mode=clampi(index,0,camera_names.size()-1)
	orbit_radius=135. if cam_mode==0 else 42. if cam_mode==1 else 13. if cam_mode in [2,3] else 24. if cam_mode in [5,6] else 30. if cam_mode==7 else orbit_radius
	if cam_mode==4:free_position=camera.global_position

func coordinate(name:String)->Vector2:
	var link:Dictionary=lift_links[name];var axis:Vector3=link.parent.global_basis*link.axis
	var pa:Vector3=link.parent.global_transform*link.a;var pb:Vector3=link.body.global_transform*link.b
	return Vector2((pb-pa).dot(axis),(point_velocity(link.body,pb)-point_velocity(link.parent,pa)).dot(axis))

func ramp_coordinate(name:String)->Vector2:
	var link:Dictionary=ramp_links[name];var rotation:Quaternion=(link.parent.global_basis.inverse()*link.body.global_basis).get_rotation_quaternion()
	var angle:float=wrapf(2*atan2(Vector3(rotation.x,rotation.y,rotation.z).dot(link.axis),rotation.w),-PI,PI)
	return Vector2(angle,(link.body.angular_velocity-link.parent.angular_velocity).dot(link.parent.global_basis*link.axis))

func _ramps(dt:float)->void:
	for lift in lift_data:
		if parked_boarding_fixture and lift.name!=lift_data[0].name:continue
		var ramp:Dictionary=lift.ramp;var link:Dictionary=ramp_links[ramp.name];var q:=ramp_coordinate(ramp.name)
		var tip:Vector3=link.body.global_position
		var terrain:float=height(tip.x+origin.offset_x,-tip.z-origin.offset_z)
		var low:bool=tip.y-terrain<.35 and coordinate(lift.groups[0]).x>2.65
		var goal:float=PI/2.+asin(clampf((tip.y-terrain-.02)/2.,0.,.18)) if low and bool(lift_commands[lift.name]) else 0.
		var occupied:bool=link.body.get_colliding_bodies().any(func(b):return b is RigidBody3D and (b.collision_layer&48)!=0)
		if occupied and goal<q.x:goal=q.x
		ramp_targets[ramp.name]=move_toward(float(ramp_targets[ramp.name]),goal,.65*dt)
		var axis:Vector3=link.parent.global_basis*link.axis
		var gravity:float=(link.body.global_basis*Vector3.UP).cross(Vector3.DOWN*float(ramp.mass_kg)*9.81).dot(axis)
		var effort:float=clampf(10000.*(float(ramp_targets[ramp.name])-q.x)-2000.*q.y-gravity,-3000.,3000.)
		link.body.apply_torque(axis*effort);link.parent.apply_torque(-axis*effort)
		if count%maxi(20,Engine.physics_ticks_per_second/10)==0:ramp_samples.append({"time":elapsed,"name":ramp.name,"angle_rad":q.x,"target_rad":goal,"hinge_height_m":tip.y-terrain,"occupied":occupied,"effort_Nm":effort})

func _lifts(dt:float)->void:
	if lift_data.is_empty():return
	drive_interlock=false
	var cycle:=str(options.get("mode","manual")) in ["lift_cycle","lift_preview_cycle"]
	for lift in lift_data:
		if parked_boarding_fixture and lift.name!=lift_data[0].name:continue
		if cycle:lift_commands[lift.name]=elapsed>=12. and elapsed<47.
		if count%maxi(20,Engine.physics_ticks_per_second/10)==0:
			var supported_mass:=0.
			for passenger in bodies[lift.groups[3]].get_colliding_bodies():
				if passenger is RigidBody3D and (passenger.collision_layer&16)!=0:supported_mass+=passenger.mass
			lift_payload_mass[lift.name]=clampf(supported_mass,0.,500.)
		var states:Array=[]
		for name in lift.groups:states.append(coordinate(name))
		if lift.name==lift_data[0].name and elapsed<12.:
			lift_stability.append({"time":elapsed,"q":states.map(func(v):return v.x),"velocity":states.map(func(v):return v.y),"command":lift_commands[lift.name]})
		var out_name:String=lift.groups[0];var out_state:Vector2=states[0]
		var depth:=0.
		for i in range(1,4):depth+=states[i].x
		var want:bool=bool(lift_commands[lift.name]);var speed:float=bodies[lift.hull].linear_velocity.length()
		var allow:bool=speed<.10 and bodies[lift.hull].global_basis.y.y>.995
		var out_goal:float=lift.stroke_out if want or depth>.03 else 0.
		if not allow and depth<.03:out_goal=0.
		var top_world:Vector3=bodies[lift.hull].global_transform*(vec(lift.pivot)-vec(visual.config.groups[lift.hull].neutral_body_position_source_m))+bodies[lift.hull].global_basis.y*.125
		var projected:Vector3=top_world+bodies[lift.hull].global_basis*vec([0,float(lift.side)*float(lift.stroke_out),0])
		var terrain_h:float=-INF;var terrain_low:float=INF
		for xx in [-1.6,1.6]:
			for zz in [-1.1,1.1]:
				var point:Vector3=projected+bodies[lift.hull].global_basis*Vector3(xx,0,zz)
				var h:float=height(point.x+origin.offset_x,-point.z-origin.offset_z);terrain_h=maxf(terrain_h,h);terrain_low=minf(terrain_low,h)
		allow=allow and terrain_h-terrain_low<.12
		# 250 mm physical deck: the underside lands on terrain, with at most
		# 5 mm controller preload. Finite force and actual collision stop descent.
		var depth_goal:float=clampf((top_world.y-terrain_h-.245)/maxf(bodies[lift.hull].global_basis.y.y,.95),0.,3*float(lift.stroke_stage)) if want and out_state.x>float(lift.stroke_out)-.04 and allow else 0.

		if not want and ramp_coordinate(lift.ramp.name).x>.04:depth_goal=depth
		var goals:Array=[]
		for i in range(4):
			var name:String=lift.groups[i];var goal:float=out_goal if i==0 else depth_goal/3.
			var velocity:float=.55 if i==0 else .7/3.
			lift_targets[name]=move_toward(float(lift_targets[name]),goal,velocity*dt)
			goals.append(lift_targets[name])
		var forces:Array=preload("lift_servo.gd").efforts(states,goals,lift.masses,float(lift_payload_mass[lift.name])+float(lift.ramp.mass_kg),dt)
		for i in range(4):
			var name:String=lift.groups[i]
			var q:Vector2=states[i];var link:Dictionary=lift_links[name];var axis:Vector3=link.parent.global_basis*link.axis
			var carried:float=float(lift_payload_mass[lift.name])+float(lift.ramp.mass_kg)
			for j in range(i,4):carried+=float(lift.masses[j])
			var gravity_effort:float=-Vector3.DOWN.dot(axis)*9.81*carried
			var effort:float=clampf(float(forces[i])+gravity_effort,-60000.,60000.)
			var pa:Vector3=link.parent.global_transform*link.a;var pb:Vector3=link.body.global_transform*link.b
			link.body.apply_force(axis*effort,pb-link.body.global_position);link.parent.apply_force(-axis*effort,pa-link.parent.global_position)
			if elapsed>10.:lift_peak_error=maxf(lift_peak_error,absf(float(lift_targets[name])-q.x))
		if want or out_state.x>.04 or depth>.04:drive_interlock=true
		if count%maxi(20,Engine.physics_ticks_per_second/10)==0:
			var floor_height:float=bodies[lift.groups[3]].global_position.y+.125
			lift_samples.append({"time":elapsed,"name":lift.name,"out_m":out_state.x,"depth_m":depth,"requested_down":want,"platform_height_m":floor_height,"top_world_m":top_world.y,"depth_goal_m":depth_goal,"stage_targets":[lift_targets[lift.groups[1]],lift_targets[lift.groups[2]],lift_targets[lift.groups[3]]],"underside_gap_m":floor_height-.25-terrain_h,"ground_contacts":int(bodies[lift.groups[3]].get_colliding_bodies().any(func(b):return b.name=="BoardingGround")),"payload_mass_kg":lift_payload_mass[lift.name],"terrain_delta_m":terrain_h-terrain_low,"deployment_allowed":allow,"drive_interlock":drive_interlock})
	if witness!=null and count%maxi(20,Engine.physics_ticks_per_second/10)==0:
		var floor:RigidBody3D=bodies[lift_data[0].groups[3]];var relative:Vector3=floor.to_local(witness.global_position)
		witness_samples.append({"time":elapsed,"payload_local":source(relative),"payload_kg":500.,"floor_gap_m":relative.y-.425})
	if access!=null:access.requests.fill(doors_open)

func _physics_process(dt:float)->bool:
	var controller_start:int=Time.get_ticks_usec()
	if not camera_ready:return super._physics_process(dt)
	var dual_probe_kind:String=OS.get_environment("SAINIVERSE_DUAL_PROBE_KIND")
	if manual and (OS.get_environment("SAINIVERSE_REMOTE_PROBE")=="1" or dual_probe_kind in ["sai001","sai002"]):
		var probe_kind:String=dual_probe_kind if dual_probe_kind in ["sai001","sai002"] else "roller" if OS.get_environment("SAINIVERSE_REMOTE_KIND")=="roller" else "microduck"
		if elapsed>=11. and remote_probe_stage==0 and not robot_switch_busy:
			select_robot_mode(probe_kind);remote_probe_stage=1
		if elapsed>=13. and remote_probe_stage==1 and not robot_switch_busy and active_robot_kind==probe_kind:
			if probe_kind in ["microduck","roller"] or OS.get_environment("SAINIVERSE_DUAL_PROBE_TRAVEL")=="2":quick_travel(2)
			remote_probe_stage=2
		if elapsed>=16. and remote_probe_stage==2:
			var car_probe:bool=OS.get_environment("SAINIVERSE_DUAL_PROBE_CAR")!="0"
			var robot_probe:bool=OS.get_environment("SAINIVERSE_DUAL_PROBE_ROBOT")!="0"
			var yaw_probe:bool=robot_probe and OS.get_environment("SAINIVERSE_DUAL_PROBE_YAW")!="0"
			_remote_probe_key(KEY_UP,car_probe and elapsed<26.)
			_remote_probe_key(KEY_LEFT,car_probe and OS.get_environment("SAINIVERSE_DUAL_PROBE_STEER")=="1" and elapsed>=19. and elapsed<22.)
			_remote_probe_key(KEY_RIGHT,car_probe and OS.get_environment("SAINIVERSE_DUAL_PROBE_STEER")=="1" and elapsed>=23. and elapsed<25.)
			_remote_probe_key(KEY_W,robot_probe and elapsed<26.)
			_remote_probe_key(KEY_A,yaw_probe and elapsed>=17. and elapsed<20.)
			_remote_probe_key(KEY_D,yaw_probe and elapsed>=21. and elapsed<24.)
			if count%maxi(1,Engine.physics_ticks_per_second/5)==0:_remote_probe_sample()
		if elapsed>=20. and not dual_probe_switch_done and not robot_switch_busy and OS.get_environment("SAINIVERSE_DUAL_PROBE_SWITCH") in ["microduck","roller","sai001","sai002","vehicle"]:
			dual_probe_switch_done=true
			select_robot_mode(OS.get_environment("SAINIVERSE_DUAL_PROBE_SWITCH"))
	if manual and OS.get_environment("SAINIVERSE_DRIVE_PROBE")=="1":
		if elapsed>=11. and elapsed<19.:Input.action_press("sainiverse_forward")
		else:Input.action_release("sainiverse_forward")
		if elapsed>=16. and elapsed<19.:Input.action_press("sainiverse_left")
		else:Input.action_release("sainiverse_left")
	# 60/60 coworld: reuse existing sainiverse_* Input axes (same path as hold-forward).
	# ~45 s ops-like probe (each active segment ≤8 s): fwd → fwd+left → fwd → stop.
	# t=11..19 forward; t=19..25 forward+left; t=25..33 forward; t>=33 stop.
	elif _sai60_coworld() and sai_passenger!=null and sai_passenger.manual_control and OS.get_environment("SAINIVERSE_DRIVE_PROBE")=="1":
		if elapsed>=11. and elapsed<33.:Input.action_press("sainiverse_forward")
		else:Input.action_release("sainiverse_forward")
		if elapsed>=19. and elapsed<25.:Input.action_press("sainiverse_left")
		else:Input.action_release("sainiverse_left")
		Input.action_release("sainiverse_right")
		Input.action_release("sainiverse_reverse")
	if manual and not switch_probe_sequence.is_empty() and elapsed>=11.:
		var probe_index:=int((elapsed-11.)/6.)
		var probe_kind:String=switch_probe_sequence[probe_index] if probe_index<switch_probe_sequence.size() else ""
		_probe_forward(travel_probe_sequence.is_empty() and probe_index<4 and active_robot_kind==probe_kind and elapsed-11.-6.*probe_index>=1. and elapsed-11.-6.*probe_index<4.)
		if probe_index<switch_probe_sequence.size() and probe_index!=last_switch_probe_index and not robot_switch_busy:
			select_robot_mode(switch_probe_sequence[probe_index])
			if robot_switch_busy:last_switch_probe_index=probe_index
	if manual and not travel_probe_sequence.is_empty() and active_robot_kind!="vehicle" and elapsed>=13.:
		var travel_index:=int((elapsed-13.)/4.)
		if travel_index<travel_probe_sequence.size() and travel_index!=last_travel_probe_index and not robot_switch_busy:
			quick_travel(int(travel_probe_sequence[travel_index]))
			last_travel_probe_index=travel_index
	if not quick_travel_history.is_empty():
		var travel:Dictionary=quick_travel_history[-1]
		if not travel.has("arrived_world") and elapsed-float(travel.time)>=.5 and not robot_switch_busy:
			var point:=_selected_robot_position()
			travel["arrived_world"]=[point.x,point.y,point.z]
			var target:Array=travel.target_world
			travel["error_m"]=point.distance_to(Vector3(float(target[0]),float(target[1]),float(target[2])))
			if patrol!=null:travel["first_fall"]=patrol.session.first_fall
			if sai_passenger!=null:travel["failure"]=sai_passenger.failure
	if not switch_probe_sequence.is_empty() and robot_switch_history.size()>0 and active_robot_kind!="vehicle":
		var current:Dictionary=robot_switch_history[robot_switch_history.size()-1]
		if not current.has("start_world"):
			var point:=_selected_robot_position()
			if point!=Vector3.ZERO:current["start_world"]=[point.x,point.y,point.z]
	if patrol==null and elapsed>=10. and str(options.get("mode","")) in ["cabin_patrol","cockpit_patrol","deck_patrol","worksite"]:
		if str(options.get("mode","")) in ["cabin_patrol","cockpit_patrol","deck_patrol"]:
			for name in bodies:bodies[name].freeze=true
			parked_patrol_fixture=true
			Engine.physics_ticks_per_second=200
			Engine.max_physics_steps_per_frame=16
		patrol=load(HERE+"/runtime/microduck_patrol.gd").new();patrol.carrier=self
		patrol.mode_name="walk" if str(options.mode) in ["cabin_patrol","cockpit_patrol"] else "roller"
		patrol.spawn_source=Vector3(25.,0.,11.354) if str(options.mode)=="cabin_patrol" else Vector3(29.4,0.,11.354) if str(options.mode)=="cockpit_patrol" else Vector3(-12.,-12.5,7.454)
		stage.add_child(patrol)
		if str(options.mode)=="worksite":
			var layer:=CanvasLayer.new();stage.add_child(layer)
			var container:=SubViewportContainer.new();container.position=Vector2(872,100);container.size=Vector2(384,216);container.stretch=true;layer.add_child(container)
			var viewport:=SubViewport.new();viewport.size=Vector2i(384,216);viewport.world_3d=stage.get_world_3d();viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;container.add_child(viewport)
			patrol_camera=Camera3D.new();patrol_camera.near=.015;patrol_camera.fov=48.;viewport.add_child(patrol_camera);patrol_camera.current=true
			var label:=Label.new();label.text="LIVE / MicroDuck deck patrol";label.position=Vector2(872,76);layer.add_child(label)
	if parked_patrol_fixture:
		elapsed+=dt;count+=1
		if elapsed>=float(options.seconds):
			_write_visual_report()
			var report:=FileAccess.open(str(options.output_root)+"/run.json",FileAccess.WRITE)
			report.store_string(JSON.stringify({"seconds":elapsed,"wall_seconds":(Time.get_ticks_usec()-start_usec)/1e6,"parked_carrier_fixture":true,"robot_controller_hz":50,"physics_hz":Engine.physics_ticks_per_second,"mode":str(options.mode),"selected_robot":active_robot_kind},"  "));report.close();quit()
		return false
	if sai_passenger==null and elapsed>=10. and str(options.get("mode","")) in ["sai_board","sai_board_002","sai_cockpit"]:
		if _sai60_coworld():
			Engine.physics_ticks_per_second=60
			Engine.max_physics_steps_per_frame=12
		else:
			Engine.physics_ticks_per_second=1000 if OS.get_environment("SAINIVERSE_USE_GAME_ROBOTS")=="1" else 2000
			Engine.max_physics_steps_per_frame=256
		parked_boarding_fixture=true
		# Stationary carrier fixture: freeze after the full suspension has settled.
		# The selected lift/ramp and every robot body continue physical integration.
		var moving:Array=["cockpit_steer","cockpit_steer_copilot"] if str(options.get("mode",""))=="sai_cockpit" else lift_data[0].groups.duplicate()
		if str(options.get("mode",""))!="sai_cockpit":moving.append(lift_data[0].ramp.name)
		for name in bodies:
			if not moving.has(name):bodies[name].freeze=true
		sai_passenger=load(HERE+"/runtime/sai_boarding.gd").new();sai_passenger.carrier=self
		sai_passenger.robot_id="Sai_Agent_002" if str(options.mode)=="sai_board_002" else "Sai_Agent_001"
		sai_passenger.cockpit_demo=str(options.get("mode",""))=="sai_cockpit"
		# 60/60: route velocity through existing manual Input axes (DRIVE_PROBE presses
		# sainiverse_forward); not a separate hardcoded [.14,0,0] propulsion branch.
		if _sai60_coworld() and not sai_passenger.cockpit_demo:
			sai_passenger.manual_control=true
		if sai_passenger.cockpit_demo:cockpit.set_physical_mode(true)
		stage.add_child(sai_passenger)
	if not parked_boarding_fixture or str(options.get("mode",""))=="sai_cockpit":cockpit.step(dt)
	_lifts(dt)
	_ramps(dt)
	if not parked_boarding_fixture:
		cargo.step(dt)
		equipment.step(dt,elapsed)
	drive_interlock=drive_interlock or not equipment.stowed() or cargo.attached_crane>=0
	if count%maxi(20,Engine.physics_ticks_per_second/10)==0:
		for role in indicator_materials:
			indicator_materials[role].set_shader_parameter("indicator_on",1. if role=="status_power" or (role=="status_motion" and bodies.front.linear_velocity.length()>.1) or (role=="status_lift" and drive_interlock) else 0.)
	if manual or str(options.get("mode",""))=="cockpit_test":
		options.speed=0. if drive_interlock else cockpit.drive_speed();options.curvature=cockpit.axis("steer")*.012

	elif str(options.get("mode","")) in ["lift_cycle","lift_preview_cycle"]:options.speed=3. if elapsed>14 and elapsed<46 else 0.
	else:options.speed=requested_drive_speed
	if str(options.get("mode",""))=="hill_turn":options.curvature=.006*clampf((elapsed-34.)/4.,0.,1.)
	if drive_interlock:options.speed=0.
	if parked_boarding_fixture:
		elapsed+=dt;count+=1
		if _sai60_coworld() and (sai60_physics_hz_samples.is_empty() or int(sai60_physics_hz_samples[-1].physics_hz)!=Engine.physics_ticks_per_second or count%maxi(1,Engine.physics_ticks_per_second/10)==0):
			sai60_physics_hz_samples.append({"time":elapsed,"physics_hz":Engine.physics_ticks_per_second,"count":count})
		if elapsed>=float(options.seconds):
			_write_visual_report()
			var file:=FileAccess.open(str(options.output_root)+"/run.json",FileAccess.WRITE)
			var policy_hz:int=60 if _sai60_coworld() else 50
			file.store_string(JSON.stringify({"seconds":elapsed,"wall_seconds":(Time.get_ticks_usec()-start_usec)/1e6,"parked_carrier_fixture":true,"dynamic_selected_lift_ramp_bodies":0 if str(options.get("mode",""))=="sai_cockpit" else 5,"robot_controller_hz":policy_hz,"physics_hz":Engine.physics_ticks_per_second,"sai60_coworld":_sai60_coworld(),"physics_hz_samples":sai60_physics_hz_samples,"scope":"Stationary cockpit manipulation with dynamic steering joints and Sai articulation." if str(options.get("mode",""))=="sai_cockpit" else "Carrier settled dynamically for 10 seconds, then held fixed for stationary boarding. Lift, ramp and Sai remain dynamic with actual collisions and finite actuator forces. Does not measure hull response to boarding load."},"  "));file.close();quit()
		return false
	var result:bool=super._physics_process(dt)
	controller_steps+=1;controller_usec+=Time.get_ticks_usec()-controller_start
	return result

func _manual_robot_camera(target:Vector3)->void:
	var remote_view:bool=patrol!=null and patrol.has_method("set_destination")
	var carrier_basis:Basis=patrol.rendered_carrier.basis if remote_view else bodies.front.global_basis
	if remote_view:
		# This SceneTree owns the camera, so Camera3D.get_process_delta_time() is
		# not the render interval here. Measure successive camera updates instead.
		var now_usec:int=Time.get_ticks_usec()
		var render_dt:float=clampf(float(now_usec-manual_camera_last_usec)/1000000.,0.,.1) if manual_camera_last_usec>0 else 0.
		manual_camera_last_usec=now_usec
		if not manual_camera_target_valid or patrol.camera_snap_pending:
			manual_camera_target=target
			manual_camera_target_valid=true
			patrol.camera_snap_pending=false
		else:
			manual_camera_target=manual_camera_target.lerp(target,1.-exp(-12.*render_dt))
		target=manual_camera_target
	camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.near=.015;camera.far=3500.;camera.fov=48.
	if active_quick_location==1:
		var moved:bool=false
		if not quick_travel_history.is_empty():
			var travel:Dictionary=quick_travel_history[-1]
			var start:Array=travel.target_world
			var distance:float=target.distance_to(Vector3(float(start[0]),float(start[1]),float(start[2])))
			# A reset can take several frames. The old location is not player movement.
			if distance<.6:travel["f1_arrived"]=true
			moved=bool(travel.get("f1_arrived",false)) and distance>1.5
		if moved or Input.is_action_pressed("sainiverse_forward") or Input.is_action_pressed("sainiverse_reverse") or Input.is_action_pressed("sainiverse_left") or Input.is_action_pressed("sainiverse_right"):
			active_quick_location=0
		else:
			var front_position:Vector3=patrol.rendered_carrier.origin if remote_view else bodies.front.global_position
			var tail_position:Vector3=bodies.tail.get_global_transform_interpolated().origin if remote_view else bodies.tail.global_position
			var whole:Vector3=(front_position+tail_position)*.5+Vector3.UP*4.
			camera.fov=50.;camera.near=.08
			var panorama_offset:=Vector3(95.,54.,105.)
			if f1_panorama_dragged:
				panorama_offset=Vector3(cos(f1_panorama_pitch)*cos(f1_panorama_yaw),sin(f1_panorama_pitch),cos(f1_panorama_pitch)*sin(f1_panorama_yaw))*f1_panorama_radius
			camera.global_position=whole+carrier_basis*panorama_offset
			camera.look_at(whole,Vector3.UP)
			_record_camera_motion(whole)
			return
	if active_quick_location==2:
		# Stay over the walking lane, below the roof and inside the outer guardrail.
		camera.global_position=target+carrier_basis*Vector3(2.,.85,-.25)
		camera.look_at(target,Vector3.UP)
		_record_camera_motion(target)
		return
	if active_quick_location==3:
		camera.global_position=target+carrier_basis*Vector3(-.9,.85,.95)
		camera.look_at(target,Vector3.UP)
		_record_camera_motion(target)
		return
	var offset:=Vector3(cos(orbit_pitch)*cos(orbit_yaw),sin(orbit_pitch),cos(orbit_pitch)*sin(orbit_yaw))*orbit_radius
	var position:=target+offset
	# Keep the follow camera on the robot's side of a cabin wall or deck rail.
	var ray:=PhysicsRayQueryParameters3D.create(target,position,8)
	var hit:=stage.get_world_3d().direct_space_state.intersect_ray(ray)
	if not hit.is_empty():
		position=target+offset.normalized()*maxf(.45,target.distance_to(hit.position)-.18)
	camera.global_position=position;camera.look_at(target,Vector3.UP)
	_record_camera_motion(target)

func _record_camera_motion(target:Vector3)->void:
	if OS.get_environment("SAINIVERSE_CAMERA_PROBE")!="1" or active_robot_kind not in ["microduck","roller"] or patrol==null:return
	if camera_motion_samples.size()>25000:return
	var car_position:Vector3=bodies.front.global_position
	camera_motion_samples.append({"wall_usec":Time.get_ticks_usec(),"sim_time":elapsed,"camera":[camera.global_position.x,camera.global_position.y,camera.global_position.z],"target":[target.x,target.y,target.z],"car":[car_position.x,car_position.y,car_position.z]})

func _camera()->void:
	if camera_ready and cargo!=null and str(options.get("mode",""))=="cargo_cycle":
		var target:Vector3=cargo.body.global_position+Vector3.UP*2.;camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.near=.05;camera.fov=55.;camera.global_position=target+Vector3(17,11,22);camera.look_at(target,Vector3.UP);return
	if not camera_ready:super._camera();return
	if sai_passenger!=null and sai_passenger.robot!=null:
		var target:Vector3=sai_passenger.robot.bodies.chassis.global_position+Vector3.UP*.2
		if sai_passenger.cockpit_demo:
			var grip:Vector3=bodies.cockpit_steer.global_transform*vec([-.028,-.215,-.075])
			camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.near=.015;camera.fov=60.
			camera.global_position=bodies.front.global_transform*local_source([30.55,-2.35,13.2])
			camera.look_at(target.lerp(grip,.55),Vector3.UP)
			return
		if sai_passenger.manual_control:
			_manual_robot_camera(target);return
		camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.near=.015;camera.fov=48.
		if sai_passenger.phase in ["ride","exit","complete"]:
			camera.global_position=target+Vector3(.70,1.30,.55)
		else:camera.global_position=target+Vector3(2.,1.2,2.0)
		camera.look_at(target,Vector3.UP);return
	if patrol!=null and patrol._base!=null and str(options.get("mode",""))!="worksite":
		var target:Vector3=patrol._base.global_position+Vector3.UP*.10
		if patrol.manual_input:_manual_robot_camera(target);return
		camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.fov=48.;camera.near=.015
		camera.global_position=target+Vector3(-1.15,.55,1.10);camera.look_at(target,Vector3.UP);return
	if str(options.view) in ["accept_passage","accept_joint","accept_services","accept_yokes","accept_workbay","accept_cargo","cabin_tour","interior","workshop","controls","seat_detail","instrument_detail","engineer_detail","lounge","stairs","cockpit_rear","lift_detail","lift_root","pedestal","underbody_detail"]:super._camera();return
	if str(options.get("pv","false"))=="true":
		var t:float=elapsed-32.;var front:RigidBody3D=bodies.front
		var target:Vector3=(front.global_position+bodies.tail.global_position)*.5+Vector3.UP*4.
		if str(options.view)=="polar_panorama":
			# Four unobstructed, full-vehicle views; keep the camera outside the
			# carrier even while the driving replay changes its heading.
			var shots:=[Vector3(0.,48.,145.),Vector3(95.,54.,105.),Vector3(0.,52.,-145.),Vector3(-95.,58.,-105.)]
			var shot:int=clampi(int(floor(maxf(t,0.)/2.5)),0,shots.size()-1)
			camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.fov=50.;camera.near=.08;camera.far=3500.
			camera.global_position=target+front.global_basis*shots[shot]
			camera.look_at(target,Vector3.UP)
			world_surface.position=Vector3(-origin.offset_x,0,-origin.offset_z)
			return
		var offset:=Vector3(96,47,114)
		if str(options.get("mode",""))=="worksite":
			target+=Vector3(7,3,0);offset=Vector3(35,55,145)
		if t>=4. and t<7. and str(options.get("mode",""))!="worksite":
			target=bodies.front_bogie_fore_right.global_position+Vector3.UP*3.;offset=Vector3(20,7,28)
		elif t>=7. and str(options.get("mode",""))!="worksite":target=front.global_position+Vector3(-14,3,0);offset=Vector3(58,23,70)
		camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.fov=48.;camera.near=.08;camera.far=3500.
		camera.global_position=target+offset;camera.look_at(target,Vector3.UP);world_surface.position=Vector3(-origin.offset_x,0,-origin.offset_z);return
	camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.near=.08;camera.far=3500.;camera.fov=48.
	var front:RigidBody3D=bodies.front
	if cam_mode==2:
		camera.global_position=front.global_transform*local_source([30.8,-1.58,12.9]);camera.look_at(front.global_transform*local_source([45.,0,12.65]),front.global_basis.y)
	elif cam_mode==4:
		camera.global_position=free_position;camera.rotation=Vector3(-orbit_pitch,orbit_yaw,0)
	else:
		var target:Vector3=(front.global_position+bodies.tail.global_position)*.5+Vector3.UP*4
		var radius:=orbit_radius
		if cam_mode==1:target=front.global_transform*local_source([5.,0,12.]);radius=orbit_radius
		if cam_mode==5:target=front.global_transform*local_source([3.,-5.,12.8]);radius=orbit_radius
		if cam_mode==6:target=front.global_transform*local_source([17.,0.,7.6]);radius=orbit_radius
		if cam_mode==7:target=front.global_transform*local_source([3.,0.,4.0]);radius=orbit_radius
		if cam_mode==3:target=bodies[lift_data[selected_lift].groups[3]].global_position+Vector3.UP*.6;radius=orbit_radius
		var offset:=Vector3(cos(orbit_pitch)*cos(orbit_yaw),sin(orbit_pitch),cos(orbit_pitch)*sin(orbit_yaw))*radius
		camera.global_position=target+offset;camera.look_at(target,Vector3.UP)
	world_surface.position=Vector3(-origin.offset_x,0,-origin.offset_z)

func _process(dt:float)->bool:
	if robot_switch_message_until>0. and elapsed>=robot_switch_message_until:
		robot_switch_message="";robot_switch_message_until=0.
	if elapsed>=3.:
		if acceptance_frame_start_usec==0:acceptance_frame_start_usec=Time.get_ticks_usec()
		acceptance_rendered_frames+=1
	if patrol_camera!=null and patrol!=null and patrol._base!=null:
		var p:Vector3=patrol._base.global_position+Vector3.UP*.1
		patrol_camera.global_position=p+Vector3(-1.15,.65,1.1);patrol_camera.look_at(p,Vector3.UP)
	if pv_caption!=null:
		var phase:String=str(options.get("mode","review"))
		if phase=="cockpit_patrol":phase="MICRODUCK / COCKPIT PATROL"
		if sai_passenger!=null:phase="SAI ARM / ORIGINAL COCKPIT CONTROL" if sai_passenger.cockpit_demo else "SAI BOARDING / "+sai_passenger.phase.to_upper()
		pv_caption.text="Sainiverse_v0.1  |  "+phase+"\nSimulation  %.1f s"%elapsed
	if camera_ready:
		if cam_mode==4:
			var move:=Vector3.ZERO
			if Input.is_physical_key_pressed(KEY_W):move.z-=1
			if Input.is_physical_key_pressed(KEY_S):move.z+=1
			if Input.is_physical_key_pressed(KEY_A):move.x-=1
			if Input.is_physical_key_pressed(KEY_D):move.x+=1
			if Input.is_physical_key_pressed(KEY_E):move.y+=1
			if Input.is_physical_key_pressed(KEY_Q):move.y-=1
			free_position+=camera.global_basis*move*dt*(25. if Input.is_physical_key_pressed(KEY_SHIFT) else 5.)
		if operation_ui!=null:operation_ui.refresh()
	var result:bool=super._process(dt)
	if equipment!=null:equipment.update_skins()
	if cargo!=null:cargo.update_rigging()
	return result

func _write_visual_report()->void:
	super._write_visual_report()
	var frame_seconds:float=(Time.get_ticks_usec()-acceptance_frame_start_usec)/1000000.
	var frame_report:=FileAccess.open(str(options.output_root)+"/render_throughput.json",FileAccess.WRITE)
	frame_report.store_string(JSON.stringify({"frames":acceptance_rendered_frames,"wall_seconds":frame_seconds,"average_fps":acceptance_rendered_frames/maxf(frame_seconds,.001),"view":str(options.view),"scope":"Rendered frames per wall second after simulation second 3; screenshot capture overhead included."},"  "));frame_report.close()
	if cargo!=null:
		var f:=FileAccess.open(str(options.output_root)+"/cargo_handling.json",FileAccess.WRITE);f.store_string(JSON.stringify(cargo.report(),"  "));f.close()
	if equipment!=null:
		var proof:=FileAccess.open(str(options.output_root)+"/equipment.json",FileAccess.WRITE)
		proof.store_string(JSON.stringify({"mean_controller_ms":float(controller_usec)/maxi(1,controller_steps)/1000.,"mean_skin_ms":float(equipment.total_skin_usec)/maxi(1,equipment.skin_frames)/1000.,"mean_step_ms":float(equipment.total_step_usec)/maxi(1,equipment.total_steps)/1000.,"samples":equipment.samples,"maximum_cable_force_N":equipment.maximum_cable_force,"scope":"Finite cylinder forces, joint torques and unilateral elastic cable; hooks are dynamic free bodies. No external lifted cargo validation or hardware qualification."},"  "));proof.close()
	if cockpit!=null:
		var proof:=FileAccess.open(str(options.output_root)+"/cockpit_controls.json",FileAccess.WRITE);proof.store_string(JSON.stringify({"events":cockpit.events,"samples":cockpit.rows,"scope":"Actual finite-effort control joints; commands read joint position. Manipulator contact surfaces included; no trained robot manipulation."},"  "));proof.close()
	if operation_ui!=null:
		var proof:=FileAccess.open(str(options.output_root)+"/operation_ui.json",FileAccess.WRITE);proof.store_string(JSON.stringify(operation_ui.report(),"  "));proof.close()
	if sai_passenger!=null:
		var report_name:String="sai_cockpit.json" if sai_passenger.cockpit_demo else "sai_boarding.json"
		var proof:=FileAccess.open(str(options.output_root)+"/"+report_name,FileAccess.WRITE)
		var policy_hz:int=60 if _sai60_coworld() else 50
		var coworld:Dictionary={}
		if _sai60_coworld() and sai_passenger.has_method("coworld_evidence"):
			coworld=sai_passenger.coworld_evidence()
		proof.store_string(JSON.stringify({"robot_id":sai_passenger.robot_id,"samples":sai_passenger.cockpit_samples if sai_passenger.cockpit_demo else sai_passenger.mission_samples,"completed":sai_passenger.completed,"failure":sai_passenger.failure,"physics_hz":Engine.physics_ticks_per_second,"policy_hz":policy_hz,"parked_carrier_fixture":parked_boarding_fixture,"sai60_coworld":_sai60_coworld(),"sai60_skill":OS.get_environment("SAINIVERSE_SAI60_POLICY"),"physics_hz_samples":sai60_physics_hz_samples,"coworld":coworld,"scope":"Stationary carrier; existing Sai arm impedance and physical steering contact." if sai_passenger.cockpit_demo else ("60/60 ONNX coworld boarding with dynamic lift/ramp and Sai sharing one physics world." if _sai60_coworld() else "Scripted boarding mission using existing learned locomotion and native impedance; real contacts and finite-force lift/ramp.")},"  "));proof.close()
		if _sai60_coworld():
			var summary:=FileAccess.open(str(options.output_root)+"/sai60_coworld_report.json",FileAccess.WRITE)
			summary.store_string(JSON.stringify({"physics_hz":Engine.physics_ticks_per_second,"policy_hz":policy_hz,"physics_hz_samples":sai60_physics_hz_samples,"wall_seconds":(Time.get_ticks_usec()-start_usec)/1e6,"sim_seconds":elapsed,"coworld":coworld,"failure":sai_passenger.failure,"completed":sai_passenger.completed},"  "));summary.close()
	var switches:=FileAccess.open(str(options.output_root)+"/robot_switches.json",FileAccess.WRITE)
	switches.store_string(JSON.stringify({"history":robot_switch_history,"active_robot":active_robot_kind,"quick_travel":quick_travel_history,"remote_probe":remote_probe_samples},"  "));switches.close()
	if not camera_motion_samples.is_empty():
		var motion:=FileAccess.open(str(options.output_root)+"/camera_motion.json",FileAccess.WRITE)
		motion.store_string(JSON.stringify(camera_motion_samples));motion.close()
	if patrol!=null:
		var proof:=FileAccess.open(str(options.output_root)+"/robot_patrol.json",FileAccess.WRITE)
		var remote_worker:bool=patrol.has_method("set_destination")
		proof.store_string(JSON.stringify({"mode":patrol.mode_name,"samples":patrol.evidence,"first_fall":patrol.session.first_fall,"error":patrol.session.error,"controller":"Existing native ONNX 50 Hz / Jolt 200 Hz","scope":"Independent 200 Hz robot physics on a local static floor, rendered on the 60 Hz vehicle. No vehicle acceleration, contact feedback, or load transfer in this interactive mode." if remote_worker else "Actual policy torque actuation and carrier rigid-body contact; initialization is the only pose placement."},"  "));proof.close()
	var file:=FileAccess.open(str(options.output_root)+"/"+str(options.output).get_basename()+"_boarding.json",FileAccess.WRITE)
	file.store_string(JSON.stringify({"lifts":lift_data,"samples":lift_samples,"witness_samples":witness_samples,"ramp_samples":ramp_samples,"peak_servo_error_m":lift_peak_error,"native_rigid_bodies":bodies.size(),"finite_force_cap_N":60000,"mode":options.get("mode","manual"),"scope":"Native scalar-joint lift bodies with finite PD/gravity feedforward, collidable platform, parked deployment/drive interlocks. No learned robot policy or hardware safety certification."},"  "));file.close()
	var stability_file:=FileAccess.open(str(options.output_root)+"/lift_stability.json",FileAccess.WRITE);stability_file.store_string(JSON.stringify(lift_stability));stability_file.close()
