extends "@SAI_ROOT@/runtime/suspension_native.gd"
const Visual=preload("@SAI_ROOT@/support/godot/suspension_visual.gd")
var visual=null
var camera:Camera3D
var frames:Array=[]
var last_frame_usec:=0
var visual_started_usec:=0
var captures:Dictionary={}
var capture_running:=false
var pv_frames:=0
var pv_capture_times:Array=[]
var world_surface:Node3D
var final_written:=false

func _build()->void:
	super._build()
	DisplayServer.window_set_size(Vector2i(1280,720) if str(options.get("pv","false"))=="true" else Vector2i(1920,1080));DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.msaa_3d=Viewport.MSAA_4X
	RenderingServer.viewport_set_measure_render_time(root.get_viewport_rid(),true)
	visual=Visual.new();stage.add_child(visual);visual.configure(bodies,str(options.get("bindings","")))
	var environment:=WorldEnvironment.new();var settings:=Environment.new()
	settings.background_mode=Environment.BG_COLOR;settings.background_color=Color("8eabbc")
	settings.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;settings.ambient_light_color=Color("bed0da");settings.ambient_light_energy=.65
	settings.tonemap_mode=Environment.TONE_MAPPER_FILMIC;environment.environment=settings;stage.add_child(environment)
	var sun:=DirectionalLight3D.new();sun.rotation_degrees=Vector3(-48,-35,0);sun.light_energy=1.4;sun.shadow_enabled=true
	sun.directional_shadow_max_distance=350;stage.add_child(sun)
	world_surface=Node3D.new();stage.add_child(world_surface)
	# A visible copy of the exact analytic hard-ground fixture, not a new collider.
	var surface:=SurfaceTool.new();surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for x in range(-140,201):
		for y in range(-120,121):
			for p in [Vector2(x,y),Vector2(x,y+1),Vector2(x+1,y),Vector2(x+1,y),Vector2(x,y+1),Vector2(x+1,y+1)]:
					surface.add_vertex(Vector3(p.x,height(p.x,p.y),-p.y))
	# The analytic route becomes flat beyond the rough patch; keep that ground
	# visible through the complete long-distance benchmark and origin rebases.
	for ends in [Vector2(-10000,-140),Vector2(201,10000)]:
		for p in [Vector2(ends.x,-10000),Vector2(ends.x,10000),Vector2(ends.y,-10000),Vector2(ends.y,-10000),Vector2(ends.x,10000),Vector2(ends.y,10000)]:surface.add_vertex(Vector3(p.x,height(p.x,p.y),-p.y))
	# Complete the lateral view surface. At these Y values tanh(Y/2) is
	# saturated, so each longitudinal sample extrudes the same analytic height.
	for x in range(-140,201):
		for edges in [Vector2(-10000,-120),Vector2(121,10000)]:
			for p in [Vector2(x,edges.x),Vector2(x,edges.y),Vector2(x+1,edges.x),Vector2(x+1,edges.x),Vector2(x,edges.y),Vector2(x+1,edges.y)]:surface.add_vertex(Vector3(p.x,height(p.x,p.y),-p.y))
	surface.generate_normals();var ground:=MeshInstance3D.new();ground.mesh=surface.commit()
	var mat:=StandardMaterial3D.new();mat.albedo_color=Color("4d5d60");mat.roughness=1.;ground.material_override=mat
	world_surface.add_child(ground)
	camera=Camera3D.new();camera.far=3500.;stage.add_child(camera);camera.current=true
	visual_started_usec=Time.get_ticks_usec();last_frame_usec=visual_started_usec
	visual.update_visual();_camera()

func _camera()->void:
	var front:RigidBody3D=bodies.front
	if str(options.get("view","whole"))=="exterior":
		camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.fov=46.;camera.near=.05
		camera.global_position=front.global_transform*Vector3(63,25,57)
		camera.look_at(front.global_transform*Vector3(8,3,0),front.global_basis.y)
		world_surface.position=Vector3(-origin.offset_x,0,-origin.offset_z)
		return
	var close:bool=str(options.get("view","whole"))=="track"
	var target:Vector3=bodies.front_bogie_fore_right.global_position if close else (front.global_position+bodies.tail.global_position)*.5+Vector3.UP*3
	camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=16 if close else 110
	camera.global_position=target+(Vector3(13,7,17) if close else Vector3(100,110,155));camera.look_at(target,Vector3.UP)
	world_surface.position=Vector3(-origin.offset_x,0,-origin.offset_z)

func _physics_process(dt:float)->bool:
	if visual==null:return super._physics_process(dt)
	visual.advance(dt)
	if elapsed+dt>=float(options.seconds) and not final_written:_write_visual_report()
	return super._physics_process(dt)

func _process(_dt:float)->bool:
	if visual==null:return false
	visual.update_visual();_camera()
	var now:int=Time.get_ticks_usec()
	if elapsed>3. and not capture_running:
		frames.append({"wall_usec":now-visual_started_usec,"simulation_s":elapsed,"frame_ms":(now-last_frame_usec)/1000.,
			"process_ms":Performance.get_monitor(Performance.TIME_PROCESS)*1000.,"physics_ms":Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)*1000.,
			"gpu_ms":RenderingServer.viewport_get_measured_render_time_gpu(root.get_viewport_rid()),"render_cpu_ms":RenderingServer.viewport_get_measured_render_time_cpu(root.get_viewport_rid()),"render_setup_ms":RenderingServer.get_frame_setup_time_cpu(),
			"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),"primitives":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)})
	last_frame_usec=now
	var mode:String=str(options.get("mode",""))
	var capture_time:float=12.8+float(pv_frames)/15. if mode=="sai_cockpit" else 11.+float(pv_frames)/15. if mode in ["cabin_patrol","cockpit_patrol","deck_patrol"] else 32.+float(pv_frames)/15.
	if str(options.get("mode",""))=="sai_board":
		var phases:Dictionary=get("sai_passenger").phase_times if get("sai_passenger")!=null else {}
		capture_time=float(phases.get("approach",INF))+9.+float(pv_frames)/15. if pv_frames<40 else float(phases.get("approach",INF))+31.+float(pv_frames-40)/15. if pv_frames<70 else float(phases.get("ride",INF))+2.+float(pv_frames-70)*.32 if pv_frames<120 else float(phases.get("exit",INF))+1.+float(pv_frames-120)*.55
	var frame_limit:int=24 if mode=="sai_cockpit" else 150
	if str(options.get("pv","false"))=="true" and elapsed>=capture_time and pv_frames<frame_limit and not capture_running:
		_capture("pv_%04d"%pv_frames);pv_frames+=1
	if str(options.get("capture","false"))=="true":
		for when in ([9.,24.,40.,72.] if str(options.get("mode",""))=="lift_cycle" else [9.,14.,20.,24.]):
			if elapsed>=when and not captures.has(str(when)):
				captures[str(when)]=true;_capture(str(when))
	return false

func _capture(label:String)->void:
	capture_running=true
	await RenderingServer.frame_post_draw
	if label.begins_with("pv_"):pv_capture_times.append({"frame":label,"simulation_s":elapsed})
	var filename:String=str(options.output_root)+"/"+str(options.output).get_basename()+"_"+label+".png"
	root.get_texture().get_image().save_png(filename)
	last_frame_usec=Time.get_ticks_usec();capture_running=false

func _write_visual_report()->void:
	final_written=true
	var wheel_states:Dictionary={}
	for name in spec.contact.wheels:
		wheel_states[name]=source(bodies[name].global_position)
	var report:Dictionary={"frames":frames,"rendering_method":RenderingServer.get_current_rendering_method(),"resolution":[root.size.x,root.size.y],
		"gpu":RenderingServer.get_video_adapter_name(),"godot":Engine.get_version_info(),"physics_hz":Engine.physics_ticks_per_second,"msaa":4,
		"visual_meshes":visual.meshes,"groups":visual.groups.size(),"physical_wheels":wheel_states.size(),
		"maximum_wheel_binding_error_m":visual.maximum_wheel_binding_error_m,"maximum_wheel_stroke_m":visual.maximum_wheel_stroke_m,
		"maximum_idler_binding_error_m":visual.maximum_idler_binding_error_m,
		"mean_visual_update_ms":visual.update_usec/maxi(visual.updates,1)/1000.,"visual_updates":visual.updates,
		"seconds":elapsed,"wall_seconds":(Time.get_ticks_usec()-visual_started_usec)/1e6,"scope":visual.config.scope,
		"captures":captures,"pv_capture_times":pv_capture_times,"view":options.get("view","whole"),"native_wheel_positions":wheel_states}
	report["native_path_active"]=visual.path_core!=null
	if visual.state_texture!=null:
		# Read back only after timed frames, to verify the GPU received the current
		# complete float state. This diagnostic readback is not in the frame loop.
		var uploaded:PackedByteArray=visual.state_texture.get_image().get_data()
		report["state_texture_size"]=[36,24]
		report["state_texture_bytes_match"]=uploaded==visual.state_rows.to_byte_array()
	var file:=FileAccess.open(str(options.output_root)+"/"+str(options.output).get_basename()+"_visual.json",FileAccess.WRITE)
	file.store_string(JSON.stringify(report,"  "));file.close()
