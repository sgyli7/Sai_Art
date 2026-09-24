extends "@SAI_ROOT@/support/godot/suspension_visual_review.gd"
## Current full vehicle, mounted room contacts and explicitly static robot figures.
var room_ready:=false
var room:Dictionary
var contact_checks:Array=[]
var figure_meshes:=0
var figures:Node3D
var displays:Array=[]
var last_text_time:=-1.0

func local_source(p:Array)->Vector3:return vec(p)-vec(spec.contact.interior.datum_source_m)
func _build()->void:
	super._build()
	room=JSON.parse_string(FileAccess.get_file_as_string(visual.config.interior_manifest))
	for item in room.screens:
		var display:=Label3D.new();display.font_size=28;display.pixel_size=.0018;display.outline_size=0;display.modulate=Color("c1dfbd")
		display.no_depth_test=false;display.shaded=false;display.text="INITIALIZING"
		bodies.front.add_child(display);display.position=local_source(item.center_source_m);display.rotation.y=-PI/2
		displays.append(display)
	for x in [19.8,24.5,29.2]:
		var lamp:=OmniLight3D.new();lamp.omni_range=5.5;lamp.light_energy=.7;lamp.light_color=Color("fff0ca");lamp.shadow_enabled=false
		bodies.front.add_child(lamp);lamp.position=local_source([x,0,14.3])
	figures=Node3D.new();bodies.front.add_child(figures);figures.name="INSPECTION_home_pose_figures"
	for name in ["sai","microduck"]:
		var doc:=GLTFDocument.new();var state:=GLTFState.new()
		var gltf_status:=doc.append_from_file(str(visual.config.glb).get_base_dir()+"/"+name+"_scale_figure.glb",state)
		assert(gltf_status==OK)
		var node:Node3D=doc.generate_scene(state);figures.add_child(node)
		var p:Array=[20.55,1.75,11.35+.220000000417] if name=="sai" else [21.30,1.85,11.35+.117182362199]
		node.transform=Transform3D(Basis(Vector3.UP,-PI/2)*Basis(Vector3.RIGHT,-PI/2),local_source(p))
		figure_meshes+=_count_meshes(node)
	# Figures belong only to inspection views; whole-vehicle performance excludes
	# these posed illustrations and never claims the real robot workload.
	figures.visible=str(options.view) in ["interior","workshop","controls"]
	room_ready=true;_camera()

func _count_meshes(node:Node)->int:
	var total:int=1 if node is MeshInstance3D else 0
	for child in node.get_children():total+=_count_meshes(child)
	return total
func _camera()->void:
	if not room_ready or not str(options.view) in ["interior","workshop","controls"]:super._camera();return
	var from:Array=[18.6,-.45,12.30];var target:Array=[32.7,0,12.05]
	if str(options.view)=="workshop":from=[23.15,-.1,12.12];target=[20.95,2.45,11.82]
	if str(options.view)=="controls":from=[31.45,-.75,12.18];target=[32.88,-1.8,12.005]
	camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.fov=69 if str(options.view)=="interior" else 56;camera.near=.025
	camera.global_position=bodies.front.global_transform*local_source(from)
	camera.look_at(bodies.front.global_transform*local_source(target),bodies.front.global_basis.y)
	world_surface.position=Vector3(-origin.offset_x,0,-origin.offset_z)
func _physics_process(dt:float)->bool:
	if room_ready and elapsed>4. and contact_checks.is_empty():
		var points:Array=[]
		for x in [18.,20.,22.,24.,26.,28.,30.,32.]:points.append([x,0,room.floor_z])
		for side in [-1,1]:
			for x in [19.15,23.15,25.05]:
				for y in [3.25,3.42,3.75,4.4]:points.append([x,side*y,room.floor_z])
		for p in points:
			var expected:Vector3=bodies.front.global_transform*local_source(p);var up:Vector3=bodies.front.global_basis.y
			var query:=PhysicsRayQueryParameters3D.create(expected+up*.10,expected-up*.10,8)
			var hit:Dictionary=root.world_3d.direct_space_state.intersect_ray(query)
			contact_checks.append({"source_point":p,"hit":not hit.is_empty(),"error_m":hit.position.distance_to(expected) if not hit.is_empty() else -1.,"body":str(hit.collider.name) if not hit.is_empty() else ""})
	return super._physics_process(dt)
func _process(dt:float)->bool:
	if room_ready and elapsed-last_text_time>=.10 and not samples.is_empty():
		last_text_time=elapsed
		var sample:Dictionary=samples[-1]
		displays[0].text="DRIVE\n%5.1f km/h\nHINGE %4.1f deg"%[float(sample.speed_m_s)*3.6,rad_to_deg(float(sample.hitch_coordinates[1]))]
		displays[1].text="RUNNING GEAR\nTENSION %3.0f kN\nPEAK STROKE %.2f m"%[float(track_tension.tensions.max())/1000.,visual.maximum_wheel_stroke_m]
	return super._process(dt)
func _write_visual_report()->void:
	super._write_visual_report()
	var report:Dictionary={"screen_texts":[displays[0].text,displays[1].text],"contact_cache_enabled":ProjectSettings.get_setting("physics/jolt_physics_3d/simulation/body_pair_contact_cache_enabled"),"floor_rays":contact_checks,"contact_shapes":spec.contact.interior.shapes.size(),"static_figure_meshes":figure_meshes,"figures_visible":figures.visible,"scope":"Actual mounted floor/fixture contacts queried in native physics. Posed source robot meshes are scale figures, not trained or moving robots. Wall/door contacts and actual boarding remain incomplete."}
	var file:=FileAccess.open(str(options.output_root)+"/"+str(options.output).get_basename()+"_interior.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
