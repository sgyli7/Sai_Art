extends "@SAI_ROOT@/support/godot/interior_review.gd"
## Appearance only; all dynamics and authored meshes remain the r023 carrier.
var style:Dictionary
var asset_dir:String
var painted_surfaces:=0
var animated_ink_passes:=0
var pigment_max_error:=0.0
var audited_pigments:=0

func _build()->void:
	super._build()
	style=JSON.parse_string(FileAccess.get_file_as_string(visual.config.style))
	asset_dir=str(visual.config.style).get_base_dir()+"/assets/"
	for body in bodies.values():_paint(body)
	for child in stage.get_children():
		if child is WorldEnvironment:
			var env:Environment=child.environment
			env.tonemap_mode=Environment.TONE_MAPPER_LINEAR
			env.ambient_light_color=Color(style.ambient_color);env.ambient_light_energy=float(style.ambient_energy)
			env.fog_enabled=false
		if child is DirectionalLight3D:
			child.light_energy=float(style.sun_energy);child.light_color=Color(style.sun_color)
			child.rotation_degrees=Vector3(-48,-36,0);child.shadow_bias=.02;child.shadow_normal_bias=1.
	for child in bodies.front.get_children():
		if child is OmniLight3D:child.light_energy=float(style.cabin_light_energy)
	for child in world_surface.get_children():
		if child is MeshInstance3D:child.material_override=_enamel(Color(style.ground_color),false)

func _enamel(color:Color,outlined:bool=true)->ShaderMaterial:
	var material:=ShaderMaterial.new();material.shader=load(asset_dir+"enamel.gdshader")
	material.set_shader_parameter("pigment",color);material.set_shader_parameter("hatch_strength",float(style.hatch_strength))
	if outlined:material.next_pass=_ink(false)
	return material

func _ink(animated:bool)->ShaderMaterial:
	var ink:=ShaderMaterial.new();ink.shader=load(asset_dir+("track_ink.gdshader" if animated else "ink.gdshader"))
	ink.set_shader_parameter("ink_color",Color(style.ink_color));ink.set_shader_parameter("line_pixels",float(style.line_pixels))
	ink.set_shader_parameter("fade_start",float(style.ink_fade_start_m));ink.set_shader_parameter("fade_end",float(style.ink_fade_end_m))
	return ink

func _paint(node:Node)->void:
	if node is MeshInstance3D:
		for index in node.mesh.get_surface_count():
			var old=node.get_active_material(index)
			var role:String=str(node.name).get_slice("__",1)
			if role=="cabin_glass" or role=="cabin_light":continue
			var color:Color=Color(style.palette[role]) if style.palette.has(role) else Color("969b95")
			if style.palette.has(role):
				var original:Color=old.albedo_color if old is StandardMaterial3D else old.get_shader_parameter("paint")
				pigment_max_error=maxf(pigment_max_error,maxf(absf(original.r-color.r),maxf(absf(original.g-color.g),absf(original.b-color.b))))
				audited_pigments+=1
			if old is ShaderMaterial and old.get_shader_parameter("track_state")!=null:
				# Keep the same material object in the dynamic adapter's update list.
				var texture=old.get_shader_parameter("track_state");var row=old.get_shader_parameter("state_row")
				old.shader=load(asset_dir+"track_enamel.gdshader");old.set_shader_parameter("paint",color)
				old.set_shader_parameter("hatch_strength",float(style.hatch_strength));old.set_shader_parameter("track_state",texture);old.set_shader_parameter("state_row",row)
				var ink:=_ink(true);ink.set_shader_parameter("track_state",texture);ink.set_shader_parameter("state_row",row);old.next_pass=ink
				animated_ink_passes+=1
			else:
				if not style.palette.has(role) and old is StandardMaterial3D:
					color=old.albedo_color
				node.set_surface_override_material(index,_enamel(color))
			painted_surfaces+=1
	for child in node.get_children():_paint(child)

func _write_visual_report()->void:
	super._write_visual_report()
	var matching_ink:=0
	for bogie in visual.bogies.values():
		for material in bogie.materials:
			if material.next_pass.get_shader_parameter("track_state")==material.get_shader_parameter("track_state") and material.next_pass.get_shader_parameter("state_row")==material.get_shader_parameter("state_row"):matching_ink+=1
	var file:=FileAccess.open(str(options.output_root)+"/"+str(options.output).get_basename()+"_style.json",FileAccess.WRITE)
	file.store_string(JSON.stringify({"painted_surfaces":painted_surfaces,"animated_ink_passes":animated_ink_passes,"matching_live_ink_states":matching_ink,"audited_original_pigments":audited_pigments,"maximum_original_pigment_error":pigment_max_error,"style":style,"scope":"Same actual dynamic geometry with enamel/ink shading. No physics or pose modification."},"  "));file.close()
