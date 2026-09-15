extends SceneTree
const PathBuilder=preload("@SAI_ROOT@/support/godot/track_path.gd")
func _initialize()->void:
	var args:=OS.get_cmdline_user_args();var input:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(args[0]));var wheels:Array=[];var output:Array=[]
	for w in input.config.support_circles_x_z_radius_m:wheels.append([w[0],w[1],float(w[2])-.09])
	for fixture in input.fixtures:
		var q:Array=fixture.q;var shape:Dictionary=PathBuilder.build(wheels,Vector3(q[0],q[1],q[2]),q[3]);var a:Array=[];var b:Array=[]
		for i in shape.count:
			var x:Vector4=shape.a[i];var y:Vector4=shape.b[i];a.append([x.x,x.y,x.z,x.w]);b.append([y.x,y.y,y.z,y.w])
		output.append({"length":shape.length,"a":a,"b":b})
	var file:=FileAccess.open(args[1],FileAccess.WRITE);file.store_string(JSON.stringify(output));file.close();print("TRACK_PATH_COMPLETE");quit()
