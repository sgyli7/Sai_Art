extends RefCounted
## Physical joint coordinates are the command source. Keyboard/mouse only drive the handles.
var host:SceneTree
var data:Dictionary
var links:Dictionary={}
var targets:Dictionary={}
var values:Dictionary={}
var pulses:Dictionary={}
var down:Dictionary={}
var physical_mode:=false
var parking:=false
var events:Array=[]
var rows:Array=[]
var dragged:=""
var range_latched:=0.
var test_actions:Dictionary={}
var ui_axes:Dictionary={}
var ui_selected_crane:=-1
var ui_selected_lift:=-1

func configure(h:SceneTree,d:Dictionary)->void:
	host=h;data=d
	for c in data.controls:
		for link in host.links:
			if link.spec.name==c.name:links[c.id]=link;break
		targets[c.id]=0.;values[c.id]=0.;down[c.id]=false
		var body:RigidBody3D=host.bodies[c.name];body.collision_layer=128;body.collision_mask=16
		for vertices in c.contacts_local:
			var shape:=ConvexPolygonShape3D.new();var points:=PackedVector3Array()
			for p in vertices:points.append(host.vec(p))
			shape.points=points;var col:=CollisionShape3D.new();col.shape=shape;body.add_child(col)
	for item in data.labels:
		if str(item.id).begins_with("steer"):continue
		var label:=Label3D.new();label.text=item.text;label.font_size=24;label.pixel_size=.0009;label.outline_size=0;label.shaded=true;label.modulate=Color("c9cbbb");label.visibility_range_end=30.
		host.bodies.front.add_child(label);label.position=host.local_source(item.position_source_m);label.rotation.x=-PI/2
		if item.station=="services":label.rotation.y=PI
		elif item.station=="pilot":label.rotation.y=-PI/2
		if item.id=="steer":label.rotation=Vector3(0,-PI/2,0);label.position+=Vector3(-.08,.32,0)
	for kind in [12,13,16]:
		var viewport:=SubViewport.new();viewport.size=Vector2i(768,768) if kind==16 else Vector2i(4096,2048);viewport.transparent_bg=false;viewport.disable_3d=true;viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;host.stage.add_child(viewport)
		var drawing=load(host.HERE+"/runtime/cockpit_instruments.gd").new();drawing.host=host;drawing.kind=kind;drawing.scale=Vector2.ONE if kind==16 else Vector2(2.,2.);viewport.add_child(drawing)
		host.normal_textures["live"+str(kind)]=viewport.get_texture()
	host._paint(host.bodies.front)

func coordinate(id:String)->Vector2:
	var link:Dictionary=links[id];var axis:Vector3=link.parent.global_basis*link.axis
	if link.spec.kind=="slide":
		var a:Vector3=link.parent.global_transform*link.a;var b:Vector3=link.body.global_transform*link.b
		return Vector2((b-a).dot(axis),(host.point_velocity(link.body,b)-host.point_velocity(link.parent,a)).dot(axis))
	var q:Quaternion=(link.parent.global_basis.inverse()*link.body.global_basis).get_rotation_quaternion()
	return Vector2(wrapf(2*atan2(Vector3(q.x,q.y,q.z).dot(link.axis),q.w),-PI,PI),(link.body.angular_velocity-link.parent.angular_velocity).dot(axis))

func pulse(id:String)->void:pulses[id]=host.elapsed+.30
func select_next(id:String,steps:int,maximum:float)->void:targets[id]=fmod(roundf(float(targets[id])/maximum*(steps-1))+1.,steps)*maximum/(steps-1)
func axis(id:String)->float:
	var v:float=float(values.get(id,0.));return 0. if absf(v)<.015 else v
func set_physical_mode(enabled:bool)->void:physical_mode=enabled;dragged=""

func input(event:InputEvent)->void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_G:ui_selected_lift=-1;select_next("lift_select",6,2.50)
			KEY_N:ui_selected_crane=-1;select_next("crane_select",8,2.45)
			KEY_L:pulse("lifts_all" if event.shift_pressed else "lift")
			KEY_O:pulse("doors")
			KEY_C:pulse("work")
			KEY_H:pulse("cargo")
			KEY_B:pulse("emergency")
	if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT:
		if not event.pressed:dragged="";return
		var from:Vector3=host.camera.project_ray_origin(event.position);var to:Vector3=from+host.camera.project_ray_normal(event.position)*30.
		var query:=PhysicsRayQueryParameters3D.create(from,to,128|8);var hit:Dictionary=host.root.world_3d.direct_space_state.intersect_ray(query)
		if hit.is_empty():return
		for c in data.controls:
			if hit.collider!=host.bodies[c.name]:continue
			if c.kind=="slide":pulse(c.id)
			elif int(c.detents)>1:
				select_next(c.id,int(c.detents),float(c.limits[1]))
				if c.id=="high_range":range_latched=targets.high_range
			else:dragged=c.id
	if event is InputEventMouseMotion and dragged!="":
		for c in data.controls:
			if c.id==dragged:targets[c.id]=clampf(float(targets[c.id])-event.relative.y*.004+event.relative.x*.002,float(c.limits[0]),float(c.limits[1]))

func _press(id:String)->void:
	var accepted:=true
	match id:
		"emergency":parking=not parking
		"doors":host.doors_open=not host.doors_open
		"cargo":accepted=host.cargo.request()
		"work":
			accepted=host.bodies.front.linear_velocity.length()<.1
			if accepted:host.equipment.working=not host.equipment.working
		"lift","lifts_all":
			accepted=host.bodies.front.linear_velocity.length()<.08
			if accepted:
				var goal:bool=not host.lift_commands[host.lift_data[host.selected_lift].name]
				if id=="lifts_all":
					for lift in host.lift_data:host.lift_commands[lift.name]=goal
				else:host.lift_commands[host.lift_data[host.selected_lift].name]=goal
	events.append({"time":host.elapsed,"control":id,"accepted":accepted,"source":"physical_joint_threshold"})

func _test(time:float)->void:
	for item in [[5.,"doors"],[6.,"cargo"],[7.,"doors"],[9.,"work"],[20.,"work"],[26.,"emergency"],[29.,"emergency"],[35.,"lift"],[74.,"lift"],[112.,"lifts_all"],[151.,"lifts_all"]]:
		var key:=str(item[0])+str(item[1])
		if time>=float(item[0]) and not test_actions.has(key):test_actions[key]=true;pulse(str(item[1]))
	for id in ["crane_slew","crane_luff","crane_extend","panel_slew","panel_fold"]:targets[id]=.22 if time>11. and time<16. else 0.
	# Exercise a visibly useful paid-length range in the physical winch handle.
	targets.crane_winch=.30 if time>11. and time<23. else 0.
	targets.crane_select=.7 if time>2. else 0.;targets.lift_select=1.0 if time>2. else 0.;targets.high_range=.65 if time>22. and time<30. else 0.
	targets.throttle=.12 if time>24. and time<27. else 0.;targets.steer=.25 if time>24. and time<27. else 0.;targets.brake=.5 if time>27. and time<29. else 0.

func step(dt:float)->void:
	var is_test:bool=str(host.options.get("mode",""))=="cockpit_test"
	if is_test:_test(host.elapsed)
	elif host.manual and not physical_mode:
		# The selected robot owns WASD; the carrier uses the arrow keys.
		var active:bool=host.cam_mode!=4 and host.switch_probe_sequence.is_empty()
		var robot_selected:bool=host.active_robot_kind!="vehicle"
		if robot_selected and host.stage!=null and (Input.is_physical_key_pressed(KEY_UP) or Input.is_physical_key_pressed(KEY_DOWN) or Input.is_physical_key_pressed(KEY_LEFT) or Input.is_physical_key_pressed(KEY_RIGHT) or Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_Q) or Input.is_physical_key_pressed(KEY_E)):
			host.stage.get_viewport().gui_release_focus()
		var keys={"steer":[KEY_A,KEY_D],"throttle":[KEY_W,KEY_S],"crane_slew":[KEY_KP_4,KEY_KP_6],"crane_luff":[KEY_KP_8,KEY_KP_2],"crane_extend":[KEY_KP_ADD,KEY_KP_SUBTRACT],"crane_winch":[KEY_PAGEDOWN,KEY_PAGEUP],"panel_slew":[KEY_Z,KEY_X],"panel_fold":[KEY_R,KEY_F]}
		for id in keys:
			if dragged==id:continue
			var keyboard:=0.
			if id=="steer":
				keyboard=float(int(active and Input.is_physical_key_pressed(KEY_LEFT))-int(active and Input.is_physical_key_pressed(KEY_RIGHT))) if robot_selected else float(int(active and Input.is_action_pressed("sainiverse_left"))-int(active and Input.is_action_pressed("sainiverse_right")))
			elif id=="throttle":
				keyboard=float(int(active and Input.is_physical_key_pressed(KEY_UP))-int(active and Input.is_physical_key_pressed(KEY_DOWN))) if robot_selected else float(int(active and Input.is_action_pressed("sainiverse_forward"))-int(active and Input.is_action_pressed("sainiverse_reverse")))
			else:keyboard=float(int(active and Input.is_physical_key_pressed(keys[id][0]))-int(active and Input.is_physical_key_pressed(keys[id][1])))
			var ui:float=float(ui_axes.get(id,0.));var level:float=keyboard if absf(keyboard)>.001 else ui
			targets[id]=level*(.65 if id=="steer" else .5 if id=="throttle" else .30)
		if dragged!="brake":targets.brake=maxf(.5 if active and Input.is_physical_key_pressed(KEY_CTRL if robot_selected else KEY_SPACE) else 0.,float(ui_axes.get("brake",0.))*.5)
		targets.high_range=.65 if Input.is_physical_key_pressed(KEY_SHIFT) or float(ui_axes.get("high_range",0.))>.5 else range_latched
	elif not physical_mode:
		# Automated review modes retain their own commands and show them on handles.
		targets.throttle=clampf(float(host.options.speed)/27.777778,-1.,1.)*.5;targets.steer=clampf(float(host.options.curvature)/.012,-1.,1.)*.65
	if not physical_mode:
		if dragged=="steer_copilot":targets.steer=targets.steer_copilot
		else:targets.steer_copilot=targets.steer
	var steering_a:=coordinate("steer");var steering_b:=coordinate("steer_copilot")
	for c in data.controls:
		var id:String=c.id;var q:=coordinate(id);var goal:float=float(targets[id]);var lo:float=c.limits[0];var hi:float=c.limits[1]
		if c.kind=="slide":goal=hi if float(pulses.get(id,-1.))>host.elapsed else 0.
		if physical_mode:goal=roundf(q.x/hi*(int(c.detents)-1))*hi/(int(c.detents)-1) if int(c.detents)>1 else 0.
		var link:Dictionary=links[id];var axis_world:Vector3=link.parent.global_basis*link.axis
		var gravity:float=Vector3.DOWN.dot(axis_world)*float(c.mass_kg)*9.81 if c.kind=="slide" else (link.body.global_basis*host.vec(c.com_local_m)).cross(Vector3.DOWN*float(c.mass_kg)*9.81).dot(axis_world)
		var coupling:=0.
		if id=="steer" or id=="steer_copilot":
			var other:Vector2=steering_b if id=="steer" else steering_a
			coupling=28.*(other.x-q.x)+1.2*(other.y-q.y)
		var effort:float=clampf(float(c.kp)*(goal-q.x)-float(c.kd)*q.y-gravity+coupling,-float(c.effort_cap),float(c.effort_cap))
		if c.kind=="slide":link.body.apply_central_force(axis_world*effort);link.parent.apply_force(-axis_world*effort,link.body.global_position-link.parent.global_position)
		else:link.body.apply_torque(axis_world*effort);link.parent.apply_torque(-axis_world*effort)
		values[id]=clampf(q.x/hi,-1. if lo<0. else 0.,1.)
		if c.kind=="slide":
			if q.x>.007 and not down[id]:down[id]=true;_press(id)
			if q.x<.003:down[id]=false
		host.selected_lift=ui_selected_lift if ui_selected_lift>=0 else clampi(roundi(axis("lift_select")*5),0,5)
		host.equipment.selected=ui_selected_crane if ui_selected_crane>=0 else clampi(roundi(axis("crane_select")*7),0,7)
	if host.count%maxi(20,Engine.physics_ticks_per_second/10)==0:rows.append({"time":host.elapsed,"values":values.duplicate(),"speed_request_m_s":drive_speed(),"parking":parking,"selected_lift":host.selected_lift,"selected_crane":host.equipment.selected,"physical_mode":physical_mode})

func drive_speed()->float:
	var throttle:float=axis("throttle");var limit:float=27.777778 if axis("high_range")>.5 else 12.
	if parking:return 0.
	return (throttle*limit if throttle>=0. else throttle*5.)*(1.-axis("brake"))
