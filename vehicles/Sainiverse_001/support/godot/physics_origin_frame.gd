extends RefCounted
## Coordinate rebasing for a complete local physics island. Call between
## integration steps with every body in the island; world terrain/route queries
## must use the accumulated coordinates. Does not change velocity or rotation.
var offset_x:=0.0
var offset_z:=0.0
var events:Array=[]
var max_world_position_discontinuity:=0.0
var max_relative_position_change:=0.0
var max_velocity_change:=0.0

func source_position(local:Vector3)->Array:
	return [float(local.x)+offset_x,-float(local.z)-offset_z,float(local.y)]

func maybe_shift(bodies:Array,focus:RigidBody3D,distance:float,time_s:float)->void:
	if distance<=0 or maxf(absf(focus.global_position.x),absf(focus.global_position.z))<distance:return
	var shift:=Vector3(roundf(focus.global_position.x/distance)*distance,0.,roundf(focus.global_position.z/distance)*distance)
	var before:Array=[];var anchor:Vector3=focus.global_position
	for body:RigidBody3D in bodies:
		before.append({"world":source_position(body.global_position),"relative":body.global_position-anchor,
			"linear":body.linear_velocity,"angular":body.angular_velocity})
	# Two-body joints store local anchors and remain valid under a common
	# translation. Moving their Node3D here would rebuild their reference frames.
	for body:RigidBody3D in bodies:body.global_position-=shift
	offset_x+=float(shift.x);offset_z+=float(shift.z)
	for i in bodies.size():
		var body:RigidBody3D=bodies[i];var after:Array=source_position(body.global_position)
		for axis in 3:max_world_position_discontinuity=maxf(max_world_position_discontinuity,absf(float(after[axis])-float(before[i].world[axis])))
		max_relative_position_change=maxf(max_relative_position_change,((body.global_position-focus.global_position)-before[i].relative).length())
		max_velocity_change=maxf(max_velocity_change,maxf((body.linear_velocity-before[i].linear).length(),(body.angular_velocity-before[i].angular).length()))
	events.append({"time_s":time_s,"shift_local_xz_m":[shift.x,shift.z],"world_offset_xz_m":[offset_x,offset_z]})
