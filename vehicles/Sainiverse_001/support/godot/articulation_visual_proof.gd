extends "@SAI_ROOT@/support/godot/articulation_bench.gd"
## Render the actual candidate driven by the native joint fixture, not preview poses.
const CANDIDATE=DESIGN_ROOT+"/candidates/r015_articulation"
var capturing:=false
var mapped:Dictionary={}
var imported_rest:Dictionary={}
var source_basis:=Basis(Vector3.RIGHT,-PI/2)

func _build_fixture()->void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	super._build_fixture()
	var document:=GLTFDocument.new();var state:=GLTFState.new()
	assert(document.append_from_file(CANDIDATE+"/assets/leviathan003.glb",state)==OK)
	var asset:Node3D=document.generate_scene(state);stage.add_child(asset)
	_index_visual(asset)
	for name_ in mapped:
		var node:Node3D=mapped[name_]
		var source:Transform3D=node.global_transform
		var destination:Node3D
		if name_=="hitch_slide":destination=bodies[0]
		elif name_=="hitch_yaw":destination=bodies[1]
		elif name_=="hitch_pitch":destination=bodies[2]
		elif str(name_).begins_with("rear"):destination=bodies[3]
		else:destination=fixed
		node.reparent(destination);node.global_transform=Transform3D(source_basis,Vector3.ZERO)*source
		imported_rest[name_]=node.transform
	assert(mapped.size()==13)
	var environment:=WorldEnvironment.new();var env:=Environment.new()
	env.background_mode=Environment.BG_COLOR;env.background_color=Color(.18,.24,.28)
	env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color(.8,.86,.92);env.ambient_light_energy=.65
	environment.environment=env;stage.add_child(environment)
	var sun:=DirectionalLight3D.new();sun.rotation_degrees=Vector3(-45,-35,0);sun.light_energy=2.;stage.add_child(sun)
	var camera:=Camera3D.new();camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.size=116
	stage.add_child(camera);camera.position=Vector3(-110,105,100);camera.look_at(Vector3(-15,8,0));camera.current=true
	root.size=Vector2i(1600,1000)

func _index_visual(node:Node)->void:
	var n:String=str(node.name)
	if n in ["front","rear","hitch_slide","hitch_yaw","hitch_pitch"] or ("_bogie_" in n and not "__" in n):mapped[n]=node
	for child in node.get_children():_index_visual(child)

func _physics_process(dt:float)->bool:
	if capturing:return false
	if elapsed>=74.5:
		capturing=true
		for body in bodies:body.freeze=true
		call_deferred("_capture_native")
		return false
	return super._physics_process(dt)

func _capture_native()->void:
	await RenderingServer.frame_post_draw
	var pic:Image=root.get_texture().get_image()
	assert(pic.save_png(CANDIDATE+"/reports/godot_left45.png")==OK)
	var rear:RigidBody3D=bodies[3]
	var yaw_degrees:float=rad_to_deg(atan2(-rear.global_basis.x.z,rear.global_basis.x.x))
	var extension:float=-(bodies[0].global_position-anchor).x
	var max_binding_error:=0.
	for name_ in mapped:
		var node:Node3D=mapped[name_];var rest:Transform3D=imported_rest[name_]
		max_binding_error=maxf(max_binding_error,node.transform.origin.distance_to(rest.origin))
	var result:Dictionary={"simulation_s":elapsed,"yaw_deg":yaw_degrees,"extension_m":extension,
		"mapped_motion_groups":mapped.keys(),"max_local_binding_translation_error_m":max_binding_error,
		"physics_engine":ProjectSettings.get_setting("physics/3d/physics_engine"),"resolution":[pic.get_width(),pic.get_height()],
		"scope":"Rendered GLB attached to independently integrated native Jolt fixture; no terrain, training or real-time FPS claim."}
	var f:=FileAccess.open(CANDIDATE+"/reports/godot_visual_proof.json",FileAccess.WRITE);f.store_string(JSON.stringify(result,"  "));f.close()
	print("NATIVE_VISUAL_PROOF ",JSON.stringify(result));quit()
