extends "@SAI_ROOT@/runtime/interior_review.gd"
## Appearance only; all dynamics and authored meshes remain the r023 carrier.
var palette_texture:ImageTexture
var style:Dictionary
var asset_dir:String
var painted_surfaces:=0
var animated_ink_passes:=0
var pigment_max_error:=0.0
var audited_pigments:=0
var theme_id:="black"
var material_cache:Dictionary={}
var normal_textures:Dictionary={}
var material_controls:Dictionary={}
var indicator_materials:Dictionary={}

func _build()->void:
	super._build()
	style=JSON.parse_string(FileAccess.get_file_as_string(visual.config.style))
	asset_dir=str(visual.config.style).get_base_dir()+"/assets/"
	theme_id=str(options.get("theme","black"))
	material_controls=JSON.parse_string(FileAccess.get_file_as_string(str(visual.config.style).get_base_dir()+"/source/material_controls.json"))
	var theme:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(str(visual.config.style).get_base_dir()+"/themes/"+theme_id+".json"))
	style.palette=theme.palette
	var roles:Array=JSON.parse_string(FileAccess.get_file_as_string(asset_dir+"palette_roles.json"))
	var palette_image:=Image.create(256,1,false,Image.FORMAT_RGBA8);palette_image.fill(Color.WHITE)
	for i in roles.size():palette_image.set_pixel(i,0,Color(style.palette.get(roles[i],"969b95")))
	palette_texture=ImageTexture.create_from_image(palette_image)
	_enamel(Color("808080"),false)
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
		if child is MeshInstance3D:child.material_override=_enamel(Color(style.ground_color),false,3)

func _enamel(color:Color,outlined:bool=true,kind:int=0)->ShaderMaterial:
	var material:=ShaderMaterial.new();material.shader=load(asset_dir+"surface.gdshader");material.set_shader_parameter("surface_kind",kind)
	material.set_shader_parameter("normal_strength",float(material_controls.get("normal_strength",.8)))
	material.set_shader_parameter("artwork_strength",float(material_controls.get("artwork_strength",.7)))
	var texture_key:String="deck_tread" if kind==1 else "brushed_metal"
	if not normal_textures.has(texture_key):
		var image:=Image.load_from_file(asset_dir+"normals/"+texture_key+"_normal.png");image.generate_mipmaps()
		normal_textures[texture_key]=ImageTexture.create_from_image(image)
	material.set_shader_parameter("detail_normal",normal_textures[texture_key])
	if not normal_textures.has("artwork"):
		var image:=Image.load_from_file(asset_dir+"service_panel_handpainted.png");image.generate_mipmaps()
		normal_textures["artwork"]=ImageTexture.create_from_image(image)
	material.set_shader_parameter("artwork",normal_textures.artwork)
	for entry in [["equipment_labels","generated/equipment_labels.png"],["surface_normal","generated/surface_normal.png"],["surface_atlas","generated/surface_atlas.png"],["wear_map","generated/wear_atlas.png"],["wordmark","generated/service_stickers.png"],["warning_map","generated/warning_atlas.png"]]:
		if not normal_textures.has(entry[0]):
			var bitmap:=Image.load_from_file(asset_dir+entry[1]);bitmap.generate_mipmaps();normal_textures[entry[0]]=ImageTexture.create_from_image(bitmap)
		material.set_shader_parameter(entry[0],normal_textures[entry[0]])
	material.set_shader_parameter("body_pigment",Color(style.palette.ivory));material.set_shader_parameter("pigment",color);material.set_shader_parameter("hatch_strength",float(style.hatch_strength))
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
			if style.palette.has(role) and old is StandardMaterial3D:
				var original:Color=old.albedo_color if old is StandardMaterial3D else old.get_shader_parameter("paint")
				pigment_max_error=maxf(pigment_max_error,maxf(absf(original.r-color.r),maxf(absf(original.g-color.g),absf(original.b-color.b))))
				audited_pigments+=1
			if old is ShaderMaterial and old.get_shader_parameter("track_state")!=null:
				# Keep the same material object in the dynamic adapter's update list.
				var texture=old.get_shader_parameter("track_state");var row=old.get_shader_parameter("state_row")
				old.shader=load(asset_dir+"track_enamel.gdshader");old.set_shader_parameter("surface_atlas",normal_textures.surface_atlas);old.set_shader_parameter("paint",color)
				old.set_shader_parameter("hatch_strength",float(style.hatch_strength));old.set_shader_parameter("track_state",texture);old.set_shader_parameter("state_row",row)
				var ink:=_ink(true);ink.set_shader_parameter("track_state",texture);ink.set_shader_parameter("state_row",row);old.next_pass=ink
				animated_ink_passes+=1
			else:
				if not style.palette.has(role) and old is StandardMaterial3D:
					color=old.albedo_color
				node.set_surface_override_material(index,_enamel(color,true,10 if role.begins_with("decal_") else 6 if role.begins_with("warn_") else 7 if role.begins_with("logo_") else 8 if role.begins_with("wear_") else 5 if role=="art_workbay_wall" else 4 if role.begins_with("art_") else 1 if role=="deck_steel" else 0))
			if role=="vertex_palette":
				node.get_active_material(index).set_shader_parameter("palette_indexed",true);node.get_active_material(index).set_shader_parameter("palette_map",palette_texture)
			if role.begins_with("decal_"):node.get_active_material(index).set_shader_parameter("label_id",int(role.get_slice("_",1)))
			if role.begins_with("status_"):
				var status=node.get_active_material(index);status.set_shader_parameter("indicator_on",1. if role=="status_power" else 0.);indicator_materials[role]=status
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

func switch_theme()->void:
	var ids=["black","desert","white","blue"]
	theme_id=ids[(ids.find(theme_id)+1)%4]
	var theme:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(str(visual.config.style).get_base_dir()+"/themes/"+theme_id+".json"))
	style.palette=theme.palette
	var roles:Array=JSON.parse_string(FileAccess.get_file_as_string(asset_dir+"palette_roles.json"))
	var palette_image:=Image.create(256,1,false,Image.FORMAT_RGBA8);palette_image.fill(Color.WHITE)
	for i in roles.size():palette_image.set_pixel(i,0,Color(style.palette.get(roles[i],"969b95")))
	palette_texture=ImageTexture.create_from_image(palette_image)
	_enamel(Color("808080"),false)
	for body in bodies.values():_paint(body)
