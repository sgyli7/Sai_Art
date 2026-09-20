extends SceneTree

func _mesh(mesh_name:String)->MeshInstance3D:
	var mesh:=MeshInstance3D.new();mesh.name=mesh_name;mesh.mesh=BoxMesh.new()
	return mesh

func _pigment(mesh:MeshInstance3D)->Color:
	var mat:Material=mesh.get_surface_override_material(0)
	if mat==null or not (mat is ShaderMaterial):return Color(0,0,0,0)
	var shader_mat:=mat as ShaderMaterial
	if shader_mat.shader==null or not str(shader_mat.shader.resource_path).ends_with("enamel.gdshader"):
		return Color(0,0,0,0)
	var pigment:Variant=shader_mat.get_shader_parameter("pigment")
	if pigment is Color:return pigment
	if pigment is Vector4:return Color(pigment.x,pigment.y,pigment.z,pigment.w)
	return Color(0,0,0,0)

func _initialize()->void:call_deferred("_run")

func _run()->void:
	var remote=load("res://microduck_remote.gd").new()
	if remote==null or not remote.has_method("apply_visual_style"):
		printerr("FAIL: remote avatar helper is missing apply_visual_style")
		quit(1);return
	var avatar:=Node3D.new()
	var jaw:=_mesh("vis_unnamed_0_57")
	var shell:=_mesh("vis_unnamed_0_50")
	var accent:=_mesh("vis_unnamed_0_51")
	var hidden:=MeshInstance3D.new();hidden.name="collision_mesh";hidden.mesh=BoxMesh.new()
	var environment:=WorldEnvironment.new();environment.environment=Environment.new()
	var original_bg:Color=environment.environment.background_color
	avatar.add_child(jaw);avatar.add_child(shell);avatar.add_child(accent);avatar.add_child(hidden)
	root.add_child(avatar);root.add_child(environment)
	remote.apply_visual_style(avatar,"res://missing_robot.tscn")
	if not _pigment(jaw).is_equal_approx(Color("e0bd38")):
		printerr("FAIL: jaw vis mesh is not the enamel yellow pigment")
		quit(1);return
	if not _pigment(shell).is_equal_approx(Color("6c6a68")):
		printerr("FAIL: shell vis mesh is not the enamel graphite pigment")
		quit(1);return
	if not _pigment(accent).is_equal_approx(Color("89729e")):
		printerr("FAIL: accent vis mesh is not the enamel purple pigment")
		quit(1);return
	if hidden.get_surface_override_material(0)!=null:
		printerr("FAIL: non-vis mesh received a MicroDuck style override")
		quit(1);return
	if not bool(avatar.get_meta("microduck_visual_style",false)):
		printerr("FAIL: styled avatar did not record microduck_visual_style")
		quit(1);return
	if environment.environment.background_color!=original_bg:
		printerr("FAIL: avatar styling retuned the host scene environment")
		quit(1);return
	print("PASS: remote MD avatar reuses style.gd pigments without editing the scene")
	remote.free()
	quit(0)
