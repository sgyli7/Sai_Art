extends "@SAI_ROOT@/runtime/atelier_review.gd"
const HERE="@SAI_ROOT@"
var lift_data:Array=[]
var lift_links:Dictionary={}
var lift_targets:Dictionary={}
var lift_commands:Dictionary={}
var lift_samples:Array=[]
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
var equipment=null
var cockpit=null
var patrol=null
var sai_passenger=null
var parked_boarding_fixture:=false
var ramp_links:Dictionary={}
var ramp_targets:Dictionary={}
var ramp_samples:Array=[]

func _build()->void:
	manual=str(options.get("mode","manual"))=="manual"
	requested_drive_speed=float(options.get("speed",0.))
	super._build()
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
	var canvas:=CanvasLayer.new();stage.add_child(canvas);canvas.visible=str(options.get("clean_capture","false"))!="true"
	var panel:=PanelContainer.new();panel.position=Vector2(20,20);canvas.add_child(panel)
	var box:=StyleBoxFlat.new();box.bg_color=Color(.06,.07,.08,.9);box.content_margin_left=18;box.content_margin_right=18;box.content_margin_top=12;box.content_margin_bottom=12;box.corner_radius_top_left=8;box.corner_radius_bottom_right=8;panel.add_theme_stylebox_override("panel",box)
	hud=Label.new();hud.add_theme_font_size_override("font_size",17);var font:=SystemFont.new();font.font_names=PackedStringArray(["Noto Sans CJK SC","Noto Sans CJK JP"]);hud.add_theme_font_override("font",font);panel.add_child(hud)
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
	if str(options.get("mode",""))=="lift_cycle":
		witness=RigidBody3D.new();witness.name="TEST_500kg_payload";witness.mass=500.;witness.collision_layer=16;witness.collision_mask=1|8;witness.can_sleep=false
		stage.add_child(witness);witness.global_position=bodies[lift_data[0].groups[3]].global_position+Vector3.UP*.475
		var shape:=BoxShape3D.new();shape.size=Vector3(.9,.6,.9);var col:=CollisionShape3D.new();col.shape=shape;witness.add_child(col)
		var mesh:=MeshInstance3D.new();var cube:=BoxMesh.new();cube.size=shape.size;mesh.mesh=cube;var mat:=StandardMaterial3D.new();mat.albedo_color=Color("D5AD3D");mesh.material_override=mat;witness.add_child(mesh)
	cockpit=load(HERE+"/runtime/cockpit_control.gd").new();cockpit.configure(self,spec.contact.cockpit)
	_camera()

func handle_input(event:InputEvent)->void:
	if not camera_ready or not manual:return
	cockpit.input(event)
	if event is InputEventMouseButton:
		if event.button_index==MOUSE_BUTTON_RIGHT:mouse_drag=event.pressed
		if event.pressed and event.button_index==MOUSE_BUTTON_WHEEL_UP:orbit_radius=maxf(4.,orbit_radius*.88)
		if event.pressed and event.button_index==MOUSE_BUTTON_WHEEL_DOWN:orbit_radius=minf(600.,orbit_radius/ .88)
	if event is InputEventMouseMotion and mouse_drag:
		orbit_yaw-=event.relative.x*.004;orbit_pitch=clampf(orbit_pitch+event.relative.y*.003,-1.35,1.35)
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_ESCAPE:
				options.seconds=elapsed+.02;manual=false;options.speed=0.
			KEY_TAB:
				cam_mode=(cam_mode+1)%6;orbit_radius=135. if cam_mode==0 else 42. if cam_mode==1 else 13.
				if cam_mode==4:free_position=camera.global_position
			KEY_T:switch_theme()
			KEY_F12:_capture("manual_"+str(Time.get_ticks_msec()))

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
	var cycle:=str(options.get("mode","manual"))=="lift_cycle"
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
		for i in range(4):
			var name:String=lift.groups[i];var goal:float=out_goal if i==0 else depth_goal/3.
			var velocity:float=.55 if i==0 else .7/3.
			lift_targets[name]=move_toward(float(lift_targets[name]),goal,velocity*dt)
			var q:Vector2=states[i];var link:Dictionary=lift_links[name];var axis:Vector3=link.parent.global_basis*link.axis
			var carried:float=float(lift_payload_mass[lift.name])+float(lift.ramp.mass_kg)
			for j in range(i,4):carried+=float(lift.masses[j])
			var gravity_effort:float=-Vector3.DOWN.dot(axis)*9.81*carried
			var effort:float=clampf(80000.*(float(lift_targets[name])-q.x)-14000.*q.y+gravity_effort,-60000.,60000.)
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
	if patrol==null and elapsed>=10. and str(options.get("mode","")) in ["cabin_patrol","deck_patrol","worksite"]:
		patrol=load(HERE+"/runtime/microduck_patrol.gd").new();patrol.carrier=self
		patrol.mode_name="walk" if str(options.mode)=="cabin_patrol" else "roller"
		patrol.spawn_source=Vector3(25.,0.,11.354) if str(options.mode)=="cabin_patrol" else Vector3(-12.,-11.5,7.454)
		stage.add_child(patrol)
		if str(options.mode)=="worksite":
			var layer:=CanvasLayer.new();stage.add_child(layer)
			var container:=SubViewportContainer.new();container.position=Vector2(872,100);container.size=Vector2(384,216);container.stretch=true;layer.add_child(container)
			var viewport:=SubViewport.new();viewport.size=Vector2i(384,216);viewport.world_3d=stage.get_world_3d();viewport.render_target_update_mode=SubViewport.UPDATE_ALWAYS;container.add_child(viewport)
			patrol_camera=Camera3D.new();patrol_camera.near=.015;patrol_camera.fov=48.;viewport.add_child(patrol_camera);patrol_camera.current=true
			var label:=Label.new();label.text="LIVE / MicroDuck deck patrol";label.position=Vector2(872,76);layer.add_child(label)
	if sai_passenger==null and elapsed>=10. and str(options.get("mode",""))=="sai_board":
		Engine.physics_ticks_per_second=2000;Engine.max_physics_steps_per_frame=256
		parked_boarding_fixture=true
		# Stationary carrier fixture: freeze after the full suspension has settled.
		# The selected lift/ramp and every robot body continue physical integration.
		var moving:Array=lift_data[0].groups.duplicate();moving.append(lift_data[0].ramp.name)
		for name in bodies:
			if not moving.has(name):bodies[name].freeze=true
		sai_passenger=load(HERE+"/runtime/sai_boarding.gd").new();sai_passenger.carrier=self;stage.add_child(sai_passenger)
	if not parked_boarding_fixture:cockpit.step(dt)
	_lifts(dt)
	_ramps(dt)
	if not parked_boarding_fixture:equipment.step(dt,elapsed)
	drive_interlock=drive_interlock or not equipment.stowed()
	if count%maxi(20,Engine.physics_ticks_per_second/10)==0:
		for role in indicator_materials:
			indicator_materials[role].set_shader_parameter("indicator_on",1. if role=="status_power" or (role=="status_motion" and bodies.front.linear_velocity.length()>.1) or (role=="status_lift" and drive_interlock) else 0.)
	if manual or str(options.get("mode",""))=="cockpit_test":
		options.speed=0. if drive_interlock else cockpit.drive_speed();options.curvature=cockpit.axis("steer")*.012

	elif str(options.get("mode",""))=="lift_cycle":options.speed=3. if elapsed>14 and elapsed<46 else 0.
	else:options.speed=requested_drive_speed
	if str(options.get("mode",""))=="hill_turn":options.curvature=.006*clampf((elapsed-34.)/4.,0.,1.)
	if drive_interlock:options.speed=0.
	if parked_boarding_fixture:
		elapsed+=dt;count+=1
		if elapsed>=float(options.seconds):
			_write_visual_report()
			var file:=FileAccess.open(str(options.output_root)+"/run.json",FileAccess.WRITE)
			file.store_string(JSON.stringify({"seconds":elapsed,"wall_seconds":(Time.get_ticks_usec()-start_usec)/1e6,"parked_carrier_fixture":true,"dynamic_selected_lift_ramp_bodies":5,"robot_controller_hz":50,"physics_hz":2000,"scope":"Carrier settled dynamically for 10 seconds, then held fixed for stationary boarding. Lift, ramp and Sai remain dynamic with actual collisions and finite actuator forces. Does not measure hull response to boarding load."},"  "));file.close();quit()
		return false
	var result:bool=super._physics_process(dt)
	controller_steps+=1;controller_usec+=Time.get_ticks_usec()-controller_start
	return result

func _camera()->void:
	if not camera_ready:super._camera();return
	if sai_passenger!=null and sai_passenger.robot!=null:
		var target:Vector3=sai_passenger.robot.bodies.chassis.global_position+Vector3.UP*.2
		camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.near=.015;camera.fov=48.
		if sai_passenger.phase=="ride":
			target=bodies[lift_data[0].groups[3]].global_position+Vector3.UP*.5
			camera.global_position=target+Vector3(11.,6.,12.)
		else:camera.global_position=target+Vector3(2.,1.2,2.0)
		camera.look_at(target,Vector3.UP);return
	if patrol!=null and patrol._base!=null and str(options.get("mode",""))!="worksite":
		var target:Vector3=patrol._base.global_position+Vector3.UP*.10
		camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.fov=48.;camera.near=.015
		camera.global_position=target+Vector3(-1.15,.55,1.10);camera.look_at(target,Vector3.UP);return
	if str(options.view) in ["cabin_tour","interior","workshop","controls","seat_detail","instrument_detail","engineer_detail","lounge","stairs","cockpit_rear","lift_detail","lift_root","pedestal","underbody_detail"]:super._camera();return
	if str(options.get("pv","false"))=="true":
		var t:float=elapsed-32.;var front:RigidBody3D=bodies.front
		var target:Vector3=(front.global_position+bodies.tail.global_position)*.5+Vector3.UP*4.
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
	if patrol_camera!=null and patrol!=null and patrol._base!=null:
		var p:Vector3=patrol._base.global_position+Vector3.UP*.1
		patrol_camera.global_position=p+Vector3(-1.15,.65,1.1);patrol_camera.look_at(p,Vector3.UP)
	if pv_caption!=null:
		var phase:String=str(options.get("mode","review"))
		if sai_passenger!=null:phase="SAI BOARDING / "+sai_passenger.phase.to_upper()
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
		if hud!=null:
			var speed:float=bodies.front.linear_velocity.dot(bodies.front.global_basis.x)*3.6
			hud.text="Sainiverse_v0.1\n%5.1f km/h    %s    %.0f FPS\n%s\nW/S 驾驶  A/D 转向  Shift 高速  空格制动\nTab 视角  右键环视  滚轮缩放  O 舱门  T 主题色\nG 选择升降台  L 升降  Shift+L 全部  F12 截图\nC 作业/收起  N 切换吊机  小键盘 4/6 回转 8/2 俯仰 +/- 伸缩\nPageUp/Down 卷扬  Z/X 天线回转 R/F 折叠\n自由观察：WASD 移动 / Q、E 升降   Esc 退出"%[speed,camera_names[cam_mode],Engine.get_frames_per_second(),"升降台联锁：请等待收起" if drive_interlock else "升降台 "+str(selected_lift+1)+" / 6 · 已收起，可驾驶"]
	var result:bool=super._process(dt)
	if equipment!=null:equipment.update_skins()
	return result

func _write_visual_report()->void:
	super._write_visual_report()
	if equipment!=null:
		var proof:=FileAccess.open(str(options.output_root)+"/equipment.json",FileAccess.WRITE)
		proof.store_string(JSON.stringify({"mean_controller_ms":float(controller_usec)/maxi(1,controller_steps)/1000.,"mean_skin_ms":float(equipment.total_skin_usec)/maxi(1,equipment.skin_frames)/1000.,"mean_step_ms":float(equipment.total_step_usec)/maxi(1,equipment.total_steps)/1000.,"samples":equipment.samples,"maximum_cable_force_N":equipment.maximum_cable_force,"scope":"Finite cylinder forces, joint torques and unilateral elastic cable; hooks are dynamic free bodies. No external lifted cargo validation or hardware qualification."},"  "));proof.close()
	if cockpit!=null:
		var proof:=FileAccess.open(str(options.output_root)+"/cockpit_controls.json",FileAccess.WRITE);proof.store_string(JSON.stringify({"events":cockpit.events,"samples":cockpit.rows,"scope":"Actual finite-effort control joints; commands read joint position. Manipulator contact surfaces included; no trained robot manipulation."},"  "));proof.close()
	if sai_passenger!=null:
		var proof:=FileAccess.open(str(options.output_root)+"/sai_boarding.json",FileAccess.WRITE)
		proof.store_string(JSON.stringify({"samples":sai_passenger.mission_samples,"completed":sai_passenger.completed,"failure":sai_passenger.failure,"physics_hz":2000,"policy_hz":50,"parked_carrier_fixture":parked_boarding_fixture,"scope":"Scripted boarding mission using existing learned locomotion and native impedance; real contacts and finite-force lift/ramp."},"  "));proof.close()
	if patrol!=null:
		var proof:=FileAccess.open(str(options.output_root)+"/robot_patrol.json",FileAccess.WRITE)
		proof.store_string(JSON.stringify({"mode":patrol.mode_name,"samples":patrol.evidence,"first_fall":patrol.session.first_fall,"error":patrol.session.error,"controller":"Existing native ONNX 50 Hz / Jolt 200 Hz","scope":"Actual policy torque actuation and carrier rigid-body contact; initialization is the only pose placement."},"  "));proof.close()
	var file:=FileAccess.open(str(options.output_root)+"/"+str(options.output).get_basename()+"_boarding.json",FileAccess.WRITE)
	file.store_string(JSON.stringify({"lifts":lift_data,"samples":lift_samples,"witness_samples":witness_samples,"ramp_samples":ramp_samples,"peak_servo_error_m":lift_peak_error,"native_rigid_bodies":bodies.size(),"finite_force_cap_N":60000,"mode":options.get("mode","manual"),"scope":"Native scalar-joint lift bodies with finite PD/gravity feedforward, collidable platform, parked deployment/drive interlocks. No learned robot policy or hardware safety certification."},"  "));file.close()
