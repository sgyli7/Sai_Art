extends SceneTree
## Isolated static look development from the frozen authored GLB.
## No vehicle physics, policy, animation adapter or source binding is changed.
const OUT="@SAI_ROOT@"
var config:Dictionary
var style:Dictionary
var stage:Node3D
var model:Node3D
var camera:Camera3D
var paint:Array=[]
var meshes:Array=[]
var nodes:Array=[]
var report:Dictionary={"renders":[],"scope":"Actual frozen neutral GLB. Colors only in memory; identical shaders, lights, camera and geometry across variants. Not a new physical run or benchmark."}
func _initialize()->void:call_deferred("run")
func source(v:Array)->Vector3:return Vector3(v[0],v[2],-v[1])
func material(color:Color,outlined:bool=true)->ShaderMaterial:
	var m:=ShaderMaterial.new();var assets:=str(config.baseline_style).get_base_dir()+"/assets/"
	m.shader=load(assets+"enamel.gdshader");m.set_shader_parameter("pigment",color);m.set_shader_parameter("hatch_strength",float(style.hatch_strength))
	if outlined:
		var ink:=ShaderMaterial.new();ink.shader=load(assets+"ink.gdshader");ink.set_shader_parameter("ink_color",Color(style.ink_color));ink.set_shader_parameter("line_pixels",float(style.line_pixels));ink.set_shader_parameter("fade_start",float(style.ink_fade_start_m));ink.set_shader_parameter("fade_end",float(style.ink_fade_end_m));m.next_pass=ink
	return m
func collect(n:Node)->void:
	if n is MeshInstance3D:
		meshes.append(n);var role:=str(n.name).get_slice("__",1);assert(style.palette.has(role),str(n.name))
		var triangles:=0
		for i in n.mesh.get_surface_count():
			var arrays:Array=n.mesh.surface_get_arrays(i);triangles+=arrays[Mesh.ARRAY_INDEX].size()/3
			if role in ["cabin_glass","cabin_light"]:continue
			var m:=material(Color(style.palette[role]));n.set_surface_override_material(i,m);paint.append({"material":m,"role":role,"node":n.name})
		nodes.append({"name":str(n.name),"transform":str(n.global_transform),"mesh_rid":n.mesh.get_rid().get_id(),"triangles":triangles})
	for child in n.get_children():collect(child)
func geometry_signature()->String:
	var state:Array=[]
	for n in meshes:state.append([str(n.name),str(n.global_transform),n.mesh.get_rid().get_id()])
	return JSON.stringify(state).sha256_text()
func set_view(name:String)->void:
	camera.projection=Camera3D.PROJECTION_ORTHOGONAL;camera.near=.05;camera.far=2000.
	if name=="detail":
		var target:=source([1.,0.,13.]);camera.position=target+Vector3(75,47,90);camera.look_at(target,Vector3.UP);camera.size=57.;return
	var points:Array=[];var lo:=Vector3(INF,INF,INF);var hi:=-lo
	for n in meshes:
		for k in 8:
			var p:Vector3=n.global_transform*n.get_aabb().get_endpoint(k);points.append(p);lo=lo.min(p);hi=hi.max(p)
	var center:Vector3=(lo+hi)*.5;camera.position=center+Vector3(105,74,145);camera.look_at(center,Vector3.UP)
	var xmin:=INF;var xmax:=-INF;var ymin:=INF;var ymax:=-INF
	for p in points:
		var q:Vector3=camera.global_transform.affine_inverse()*p
		xmin=minf(xmin,q.x);xmax=maxf(xmax,q.x);ymin=minf(ymin,q.y);ymax=maxf(ymax,q.y)
	camera.position+=camera.global_basis.x*(xmin+xmax)*.5+camera.global_basis.y*(ymin+ymax)*.5
	camera.size=maxf(ymax-ymin,(xmax-xmin)/1.6)*1.13
func run()->void:
	config=JSON.parse_string(FileAccess.get_file_as_string(OUT+"/render_config.json"));style=JSON.parse_string(FileAccess.get_file_as_string(config.baseline_style))
	root.size=Vector2i(1600,1000);root.msaa_3d=Viewport.MSAA_4X;DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	stage=Node3D.new();root.add_child(stage)
	var doc:=GLTFDocument.new();var state:=GLTFState.new();assert(doc.append_from_file(config.model,state)==OK)
	model=doc.generate_scene(state);stage.add_child(model);model.rotation_degrees.x=-90.;collect(model);assert(meshes.size()>156)
	var signature:=geometry_signature();report.geometry_signature=signature;report.mesh_count=meshes.size();report.nodes=nodes;report.model=config.model
	var world:=WorldEnvironment.new();var env:=Environment.new();env.background_mode=Environment.BG_COLOR;env.background_color=Color(config.common_environment.background);env.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR;env.ambient_light_color=Color(config.common_environment.ambient_color);env.ambient_light_energy=float(config.common_environment.ambient_energy);env.tonemap_mode=Environment.TONE_MAPPER_LINEAR;env.fog_enabled=false;world.environment=env;stage.add_child(world)
	var sun:=DirectionalLight3D.new();sun.rotation_degrees=Vector3(-48,-36,0);sun.light_energy=float(config.common_environment.sun_energy);sun.light_color=Color(config.common_environment.sun_color);sun.shadow_enabled=true;sun.directional_shadow_max_distance=350;sun.shadow_bias=.02;sun.shadow_normal_bias=1.;stage.add_child(sun)
	var floor_node:=MeshInstance3D.new();var plane:=PlaneMesh.new();plane.size=Vector2(3000,3000);floor_node.mesh=plane;floor_node.material_override=material(Color(config.common_environment.ground),false);stage.add_child(floor_node)
	camera=Camera3D.new();stage.add_child(camera);camera.current=true
	report.environment=config.common_environment;report.sun_rotation=str(sun.rotation_degrees);report.shader_style=style;report.resolution=[1600,1000];report.painted_surfaces=paint.size()
	for variant in config.variants:
		for item in paint:item.material.set_shader_parameter("pigment",Color(variant.palette[item.role]))
		for view in ["whole","detail"]:
			set_view(view)
			for frame in 8:await process_frame
			await RenderingServer.frame_post_draw
			var path:String=OUT+"/renders/"+str(variant.code)+"_"+view+".png";var picture:=root.get_texture().get_image();assert(picture.get_size()==Vector2i(1600,1000));assert(picture.save_png(path)==OK);assert(geometry_signature()==signature)
			report.renders.append({"palette":variant.code,"view":view,"path":path,"camera_transform":str(camera.global_transform),"camera_size":camera.size,"geometry_signature":signature});print("PALETTE_RENDER ",variant.code," ",view)
	var file:=FileAccess.open(OUT+"/render_report.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();quit(0)
