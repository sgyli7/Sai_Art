extends Node3D
## Display adapter only. Never applies a force or changes a physical body.
const ROOT="@SAI_ROOT@/support"
var config:Dictionary
var bodies:Dictionary
var groups:Dictionary={}
var bogies:Dictionary={}
var meshes:=0
var maximum_wheel_binding_error_m:=0.0
var maximum_wheel_stroke_m:=0.0
var update_usec:=0.0
var updates:=0
var source_basis:=Basis(Vector3.RIGHT,-PI/2)
const TrackPath=preload("@SAI_ROOT@/support/godot/track_path.gd")
var maximum_idler_binding_error_m:=0.0
var path_core=null
var state_texture:ImageTexture
var state_rows:=PackedVector4Array()

func vec(a:Array)->Vector3:return Vector3(a[0],a[2],-a[1])
func configure(native_bodies:Dictionary,bindings_path:String="")->void:
	bodies=native_bodies
	if bindings_path.is_empty():bindings_path=ROOT+"/candidates/r018_visual_suspension/bindings.json"
	config=JSON.parse_string(FileAccess.get_file_as_string(bindings_path))
	if config.has("path_extension"):
		var status:=GDExtensionManager.load_extension(str(config.path_extension))
		assert(status==GDExtensionManager.LOAD_STATUS_OK or status==GDExtensionManager.LOAD_STATUS_ALREADY_LOADED)
		assert(ClassDB.class_exists("LeviathanTrackPath"))
		path_core=ClassDB.instantiate("LeviathanTrackPath")
	if bool(config.get("state_texture",false)):
		state_texture=ImageTexture.create_from_image(Image.create(36,24,false,Image.FORMAT_RGBAF))
	var document:=GLTFDocument.new();var state:=GLTFState.new()
	var gltf_status:=document.append_from_file(config.glb,state)
	assert(gltf_status==OK)
	var asset:Node3D=document.generate_scene(state);add_child(asset)
	_index(asset)
	assert(groups.size()==int(config.get("expected_groups",21)) and meshes==int(config.get("expected_meshes",119)))
	for name in groups:
		var node:Node3D=groups[name];var binding:Dictionary=config.groups[name]
		node.reparent(bodies[name],false)
		node.transform=Transform3D(source_basis,vec(binding.pivot_source_m)-vec(binding.neutral_body_position_source_m))
		if "_bogie_" in str(name):
			bogies[name]={"node":node,"materials":[],"travel":Vector2.ZERO,"wheel_rest":{},"angles":[PackedFloat64Array([0.,0.,0.,0.,0.]),PackedFloat64Array([0.,0.,0.,0.,0.])]}
			for side in ["left","right"]:
				for index in [1,2,3]:
					var wheel_name:String=str(name)+"_wheel_"+side+"_"+str(index)
					var wheel:RigidBody3D=bodies[wheel_name]
					bogies[name].wheel_rest[wheel_name]=bodies[name].global_transform.affine_inverse()*wheel.global_position
			_attach(node,bogies[name].materials)
			if bool(config.get("tensioned_tracks",false)):
				bogies[name]["idler_rest"]={};bogies[name]["curve_q"]=[null,null];bogies[name]["curves"]=[null,null]
				for side in ["left","right"]:
					var idler_name:String=str(name)+"_idler_"+side
					bogies[name].idler_rest[idler_name]=bodies[name].global_transform.affine_inverse()*bodies[idler_name].global_position
	assert(bogies.size()==12)
	if state_texture!=null:
		var row:=0
		for name in bogies:
			for material:ShaderMaterial in bogies[name].materials:
				material.set_shader_parameter("track_state",state_texture)
				material.set_shader_parameter("state_row",row)
			row+=2

func _index(node:Node)->void:
	if node is MeshInstance3D:meshes+=1
	if config.groups.has(str(node.name)):groups[str(node.name)]=node
	for child in node.get_children():_index(child)

func _attach(node:Node,materials:Array)->void:
	if node is MeshInstance3D:
		node.extra_cull_margin=1.0
		for i in node.mesh.get_surface_count():
			var base:StandardMaterial3D=node.get_active_material(i)
			var material:=ShaderMaterial.new();material.shader=load(str(config.get("shader",ROOT+"/godot/sprung_wheel.gdshader")))
			material.set_shader_parameter("paint",base.albedo_color);material.set_shader_parameter("metal",base.metallic)
			node.set_surface_override_material(i,material);materials.append(material)
	for child in node.get_children():_attach(child,materials)

func advance(dt:float)->void:
	# Each belt's odometry is measured at its own side of the physical bogie.
	for name in bogies:
		var data:Dictionary=bogies[name];var body:RigidBody3D=bodies[name]
		for side in 2:
			var wheel_name:String=str(name)+"_wheel_"+("left" if side==0 else "right")+"_2"
			var offset:Vector3=body.global_basis*(Vector3(0,0,data.wheel_rest[wheel_name].z)-body.center_of_mass)
			var velocity:Vector3=body.linear_velocity+body.angular_velocity.cross(offset)
			var distance:float=velocity.dot(body.global_basis.x)*dt
			var phase_distance:float=distance
			if bool(config.get("tensioned_tracks",false)) and data.curves[side]!=null:phase_distance*=float(config.gear.perimeter)/float(data.curves[side].length)
			data.travel[side]=fposmod(data.travel[side]+phase_distance,float(config.gear.perimeter))
			for i in 5:data.angles[side][i]=fposmod(data.angles[side][i]-distance/float(config.gear.wheels_x_z_radius[i][2]),TAU)

func update_visual()->void:
	var started:int=Time.get_ticks_usec()
	state_rows.clear()
	for name in bogies:
		var data:Dictionary=bogies[name];var body:RigidBody3D=bodies[name]
		var body_inverse:Transform3D=body.global_transform.affine_inverse()
		var offsets:Array=[Vector3.ZERO,Vector3.ZERO]
		var idler_offsets:=Vector2.ZERO
		for side_index in 2:
			var side:String="left" if side_index==0 else "right"
			for index in [1,2,3]:
				var wheel_name:String=str(name)+"_wheel_"+side+"_"+str(index)
				var wheel:RigidBody3D=bodies[wheel_name]
				var local:Vector3=body_inverse*wheel.global_position
				var delta:Vector3=local-data.wheel_rest[wheel_name]
				offsets[side_index][index-1]=delta.y
				maximum_wheel_stroke_m=maxf(maximum_wheel_stroke_m,absf(delta.y))
				var w:Array=config.gear.wheels_x_z_radius[index]
				var y:float=data.wheel_rest[wheel_name].z*-1.
				var vertex:=Vector3(w[0],y,w[1]-config.gear.pivot_z+delta.y)
				var predicted:Vector3=data.node.global_transform*vertex
				maximum_wheel_binding_error_m=maxf(maximum_wheel_binding_error_m,predicted.distance_to(wheel.global_position))
			if bool(config.get("tensioned_tracks",false)):
				var idler_name:String=str(name)+"_idler_"+side;var idler:RigidBody3D=bodies[idler_name]
				var local:Vector3=body_inverse*idler.global_position
				idler_offsets[side_index]=local.x-data.idler_rest[idler_name].x
				var predicted:Vector3=data.node.global_transform*Vector3(4.15+idler_offsets[side_index],-data.idler_rest[idler_name].z,2.4-config.gear.pivot_z)
				maximum_idler_binding_error_m=maxf(maximum_idler_binding_error_m,predicted.distance_to(idler.global_position))
				var shape_q:=Vector4(offsets[side_index].x,offsets[side_index].y,offsets[side_index].z,idler_offsets[side_index])
				if data.curve_q[side_index]!=shape_q:
					data.curve_q[side_index]=shape_q
					data.curves[side_index]=path_core.build(config.gear.wheels_x_z_radius,offsets[side_index],idler_offsets[side_index]) if path_core!=null else TrackPath.build(config.gear.wheels_x_z_radius,offsets[side_index],idler_offsets[side_index])
					for material:ShaderMaterial in data.materials:
						if state_texture!=null:break
						material.set_shader_parameter("curve_"+side+"_a",data.curves[side_index].a);material.set_shader_parameter("curve_"+side+"_b",data.curves[side_index].b)
		if state_texture!=null:
			for side in 2:
				var q:Vector3=offsets[side];var a:PackedFloat64Array=data.angles[side]
				state_rows.append(Vector4(q.x,q.y,q.z,idler_offsets[side]))
				state_rows.append(Vector4(data.travel[side],data.curves[side].length,0,0))
				state_rows.append(Vector4(a[0],a[1],a[2],a[3]));state_rows.append(Vector4(a[4],0,0,0))
				state_rows.append_array(data.curves[side].a);state_rows.append_array(data.curves[side].b)
			continue
		var left_angles:=PackedFloat32Array(Array(data.angles[0]));var right_angles:=PackedFloat32Array(Array(data.angles[1]))
		for material:ShaderMaterial in data.materials:
			if bool(config.get("tensioned_tracks",false)):
				material.set_shader_parameter("idler_m",idler_offsets)
				material.set_shader_parameter("curve_length_m",Vector2(data.curves[0].length,data.curves[1].length))
			material.set_shader_parameter("wheel_left_m",offsets[0]);material.set_shader_parameter("wheel_right_m",offsets[1])
			material.set_shader_parameter("belt_travel_m",data.travel)
			material.set_shader_parameter("wheel_angles_left",left_angles);material.set_shader_parameter("wheel_angles_right",right_angles)
	if state_texture!=null:
		assert(state_rows.size()==36*24)
		state_texture.update(Image.create_from_data(36,24,false,Image.FORMAT_RGBAF,state_rows.to_byte_array()))
	update_usec+=Time.get_ticks_usec()-started;updates+=1
