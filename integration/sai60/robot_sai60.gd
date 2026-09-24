extends Node3D
# Ported from the existing r24 independent Godot physics implementation.
# All robot state is advanced by Godot/Jolt; Python only returns motor targets.
var specification: Dictionary
var bodies: Dictionary = {}
var drives: Array = []
var joint_rids: Array[RID] = []
var last_q: Array = []
var item: RigidBody3D
var tick := 0
var collision_margin := 0.0002
var show_visuals := true
var command: Dictionary = {}
var wheel_motor_targets := [0.0,0.0,0.0,0.0]
var previous_applied_actuators: Dictionary = {}
var initial_ground_height := 0.0
const CONTROLLER_HZ := 60

func control_decimation() -> int:
	var physics_hz := Engine.physics_ticks_per_second
	assert(physics_hz >= CONTROLLER_HZ and physics_hz % CONTROLLER_HZ == 0,
		"Sai physics rate must be an integer multiple of the 60 Hz controller")
	return physics_hz / CONTROLLER_HZ

func is_control_tick() -> bool:
	return tick % control_decimation() == 0

func sim_time_seconds() -> float:
	return float(tick) / float(Engine.physics_ticks_per_second)

func setup(spec: Dictionary, visuals: bool, ground_height: float = 0.0) -> void:
	specification = spec
	show_visuals = visuals
	initial_ground_height = ground_height
	build_robot()

func gv(a) -> Vector3:
	return Vector3(float(a[0]),float(a[2]),-float(a[1]))


func source(v: Vector3) -> Array:
	return [v.x,-v.z,v.y]


func basis_from_rows(rows: Array) -> Basis:
	var source_basis := Basis(Vector3(rows[0][0],rows[1][0],rows[2][0]),Vector3(rows[0][1],rows[1][1],rows[2][1]),Vector3(rows[0][2],rows[1][2],rows[2][2]))
	var f := Basis(Vector3(1,0,0),Vector3(0,0,-1),Vector3(0,1,0))
	return f*source_basis*f.transposed()


func material(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color=c
	m.roughness=0.65
	return m


func build_robot() -> void:
	for name in specification.bodies:
		var d: Dictionary=specification.bodies[name]
		var body := RigidBody3D.new()
		if name.ends_with("_wheel"):
			body.set_script(load("res://wheel_contact_probe.gd"))
		body.name=name
		body.position=gv(d.origin_m)+Vector3(0,0.224-float(specification.bodies.chassis.origin_m[2])+initial_ground_height,0)
		body.mass=d.mass_kg
		body.center_of_mass_mode=RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
		body.center_of_mass=gv(d.com_local_m)
		var ii: Array=d.diagonal_inertia_kgm2
		body.inertia=Vector3(ii[0],ii[2],ii[1])
		# Godot's diagonal inertia and child-axis rotor surrogate are an
		# explicit approximation, not MuJoCo's full tensor/relative armature.
		if d.has("joint"):
			var rotor: float=0.028 if d.joint.kind=="arm" else 0.0003 if d.joint.kind=="wheel" else 0.002
			if d.joint.kind=="cargo_slide":rotor=0.0
			elif d.joint.kind=="cargo_drive":rotor=0.00001
			var axis := gv(d.joint.axis)
			body.inertia+=Vector3(axis.x*axis.x,axis.y*axis.y,axis.z*axis.z)*rotor
		body.linear_damp_mode=RigidBody3D.DAMP_MODE_REPLACE
		body.angular_damp_mode=RigidBody3D.DAMP_MODE_REPLACE
		body.linear_damp=0
		body.angular_damp=0
		body.can_sleep=false
		body.collision_layer=1
		body.collision_mask=6
		if name.ends_with("_wheel"):
			body.contact_monitor=true
			body.max_contacts_reported=16
		var pm := PhysicsMaterial.new()
		pm.friction=0.8
		body.physics_material_override=pm
		add_child(body)
		bodies[name]=body
		for c in d.collision:
			var cs := CollisionShape3D.new()
			if c.type=="box":
				var shape := BoxShape3D.new()
				shape.size=Vector3(c.size[0]*2,c.size[2]*2,c.size[1]*2)
				cs.shape=shape
				cs.position=gv(c.pos)
			elif c.type=="cylinder":
				var shape := CylinderShape3D.new()
				shape.radius=c.size[0]
				shape.height=c.size[1]*2
				cs.shape=shape
				cs.position=gv(c.pos)
				cs.rotation.x=PI/2
			elif c.type=="mesh":
				var shape := ConvexPolygonShape3D.new()
				var points := PackedVector3Array()
				for v in c.convex_points_m:points.append(gv(v))
				shape.points=points
				cs.shape=shape
			else:
				var a := gv(c.fromto.slice(0,3))
				var b := gv(c.fromto.slice(3,6))
				var shape := CapsuleShape3D.new()
				shape.radius=c.size[0]
				shape.height=a.distance_to(b)+2*c.size[0]
				cs.shape=shape
				cs.position=(a+b)/2
				cs.quaternion=Quaternion(Vector3.UP,(b-a).normalized())
			cs.shape.margin=collision_margin
			body.add_child(cs)
		if show_visuals:
			var scene=load(d.godot_glb)
			if scene is PackedScene:
				var root=scene.instantiate()
				body.add_child(root)
				for mi in root.find_children("*","MeshInstance3D",true,false):
					var index := int(str(mi.name).get_slice("_",str(mi.name).get_slice_count("_")-1))
					var c: Array=d.visuals[index].rgba
					mi.material_override=material(Color(c[0],c[1],c[2],c[3]))
	for name in specification.bodies:
		var d: Dictionary=specification.bodies[name]
		if d.parent==null:continue
		var parent: RigidBody3D=bodies[d.parent]
		var child: RigidBody3D=bodies[name]
		var axis := gv(d.joint.axis).normalized()
		if d.joint.kind=="cargo_slide":
			var slider_align := Basis(Quaternion(Vector3.RIGHT,axis))
			var slider := PhysicsServer3D.joint_create()
			PhysicsServer3D.joint_make_generic_6dof(slider,parent.get_rid(),Transform3D(slider_align,child.position-parent.position),child.get_rid(),Transform3D(slider_align,Vector3.ZERO))
			for j in range(3):
				PhysicsServer3D.generic_6dof_joint_set_flag(slider,j,PhysicsServer3D.G6DOF_JOINT_FLAG_ENABLE_LINEAR_LIMIT,true)
				PhysicsServer3D.generic_6dof_joint_set_param(slider,j,PhysicsServer3D.G6DOF_JOINT_LINEAR_LOWER_LIMIT,0.0)
				PhysicsServer3D.generic_6dof_joint_set_param(slider,j,PhysicsServer3D.G6DOF_JOINT_LINEAR_UPPER_LIMIT,0.067 if j==0 else 0.0)
				PhysicsServer3D.generic_6dof_joint_set_flag(slider,j,PhysicsServer3D.G6DOF_JOINT_FLAG_ENABLE_ANGULAR_LIMIT,true)
				PhysicsServer3D.generic_6dof_joint_set_param(slider,j,PhysicsServer3D.G6DOF_JOINT_ANGULAR_LOWER_LIMIT,0.0)
				PhysicsServer3D.generic_6dof_joint_set_param(slider,j,PhysicsServer3D.G6DOF_JOINT_ANGULAR_UPPER_LIMIT,0.0)
			PhysicsServer3D.generic_6dof_joint_set_flag(slider,0,PhysicsServer3D.G6DOF_JOINT_FLAG_ENABLE_LINEAR_MOTOR,true)
			PhysicsServer3D.generic_6dof_joint_set_param(slider,0,PhysicsServer3D.G6DOF_JOINT_LINEAR_MOTOR_FORCE_LIMIT,3.15)
			joint_rids.append(slider)
			drives.append({"parent":parent,"child":child,"axis":axis,"kind":d.joint.kind,"rest":child.position-parent.position})
			last_q.append(0.0)
			continue
		var align := Basis(Quaternion(Vector3(0,0,1),axis))
		var center: float=0 if d.joint.kind=="wheel" else (d.joint.range_rad[0]+d.joint.range_rad[1])/2
		# Center the hinge's reference interval. Godot measures the opposite
		# sign, angle=center-q; this preserves SO101 travel across q=-PI.
		var frame_a := Transform3D(align,child.position-parent.position)
		var frame_b := Transform3D(Basis(axis,-center)*align,Vector3.ZERO)
		var rid := PhysicsServer3D.joint_create()
		PhysicsServer3D.joint_make_hinge(rid,parent.get_rid(),frame_a,child.get_rid(),frame_b)
		PhysicsServer3D.hinge_joint_set_flag(rid,PhysicsServer3D.HINGE_JOINT_FLAG_USE_LIMIT,d.joint.kind!="wheel")
		if d.joint.kind!="wheel":
			PhysicsServer3D.hinge_joint_set_param(rid,PhysicsServer3D.HINGE_JOINT_LIMIT_LOWER,center-d.joint.range_rad[1])
			PhysicsServer3D.hinge_joint_set_param(rid,PhysicsServer3D.HINGE_JOINT_LIMIT_UPPER,center-d.joint.range_rad[0])
		joint_rids.append(rid)
		drives.append({"parent":parent,"child":child,"axis":axis,"kind":d.joint.kind})
		last_q.append(0.0)


func build_item() -> void:
	item=RigidBody3D.new()
	item.set_script(load("res://item_observation.gd"))
	item.name="item"
	item.mass=0.1
	item.can_sleep=false
	item.linear_damp_mode=RigidBody3D.DAMP_MODE_REPLACE
	item.angular_damp_mode=RigidBody3D.DAMP_MODE_REPLACE
	item.linear_damp=0
	item.angular_damp=0
	item.collision_layer=4
	item.collision_mask=3
	item.contact_monitor=true
	item.max_contacts_reported=64
	var h: Array=specification.object.initial_pose_m
	item.position=gv([h[0][3],h[1][3],h[2][3]])
	item.basis=basis_from_rows(h)
	var p := PhysicsMaterial.new()
	p.friction=0.8
	item.physics_material_override=p
	add_child(item)
	var c := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	var size: Array=specification.object.size_m
	shape.size=Vector3(size[0],size[2],size[1])
	shape.margin=collision_margin
	c.shape=shape
	item.add_child(c)
	var mi := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size=shape.size
	mi.mesh=mesh
	mi.material_override=material(Color(0.95,0.60,0.12))
	item.add_child(mi)


func state() -> Dictionary:
	var base: RigidBody3D=bodies.chassis
	var q: Array=[]
	var v: Array=[]
	var joint_off_axis_rad: Array=[]
	for i in range(drives.size()):
		var d: Dictionary=drives[i]
		if d.kind=="cargo_slide":
			var relative_position: Vector3=d.parent.global_basis.inverse()*(d.child.position-d.parent.position)-d.rest
			q.append(relative_position.dot(d.axis))
			var velocity: Vector3=d.child.linear_velocity-d.parent.linear_velocity-d.parent.angular_velocity.cross(d.child.position-d.parent.position)
			v.append(velocity.dot(d.parent.global_basis*d.axis))
			joint_off_axis_rad.append(0.0)
			continue
		var relative: Basis=d.parent.global_basis.inverse()*d.child.global_basis
		var quat := relative.orthonormalized().get_rotation_quaternion()
		var quat_vector: Vector3=Vector3(quat.x,quat.y,quat.z)
		var perpendicular: Vector3=quat_vector-Vector3(d.axis)*quat_vector.dot(Vector3(d.axis))
		joint_off_axis_rad.append(2.0*asin(clampf(perpendicular.length(),0.0,1.0)))
		var raw := wrapf(2*atan2(Vector3(quat.x,quat.y,quat.z).dot(d.axis),quat.w),-PI,PI)
		var angle: float=last_q[i]+wrapf(raw-last_q[i],-PI,PI)
		q.append(angle)
		last_q[i]=angle
		var axis: Vector3=d.parent.global_basis*d.axis
		v.append((d.child.angular_velocity-d.parent.angular_velocity).dot(axis))
	var gripper: RigidBody3D=bodies.arm_gripper
	var cargo := cargo_state()
	var wheel_impulse_Ns: Array=[]
	var wheel_direct_contact_count: Array=[]
	var wheel_contact_bodies: Array=[]
	var wheel_contact_points: Array=[]
	for corner in ["front_left","front_right","rear_left","rear_right"]:
		var wheel: RigidBody3D=bodies[corner+"_wheel"]
		wheel_impulse_Ns.append(wheel.get("last_contact_impulse_Ns"))
		wheel_direct_contact_count.append(wheel.get("last_contact_count"))
		wheel_contact_bodies.append(wheel.get("last_contact_bodies").duplicate(true))
		wheel_contact_points.append(wheel.get("last_contact_points").duplicate(true))
	return {"time":sim_time_seconds(),"wheel_contact_impulse_Ns":wheel_impulse_Ns,"wheel_direct_contact_count":wheel_direct_contact_count,"wheel_contact_bodies":wheel_contact_bodies,"wheel_contact_points":wheel_contact_points,"q":q,"v":v,"joint_off_axis_rad":joint_off_axis_rad,"base_position":source(base.position),
		"cargo_supported":cargo.supported,"cargo_bounds_m":cargo.bounds,
		"payload_position_m":source(item.position) if item != null else [],
		"payload_linear_world_m_s":source(item.linear_velocity) if item != null else [],
		"cargo_bilateral":cargo.bilateral,"cargo_inside":cargo.inside,
		"tool_m":source(gripper.global_transform*gv(specification.tool_local_m)),
		"base_rotation_columns":[source(base.global_basis*gv([1,0,0])),source(base.global_basis*gv([0,1,0])),source(base.global_basis*gv([0,0,1]))],
		"base_linear_world":source(base.linear_velocity),"base_angular_world":source(base.angular_velocity),
		"previous_applied_actuators":previous_applied_actuators.duplicate(true)}


func cargo_state() -> Dictionary:
	if item == null:return {"supported":false,"inside":false,"bilateral":false,"bounds":[]}
	var base: RigidBody3D=bodies.chassis
	var h := base.global_transform.affine_inverse()*item.global_transform
	var dims: Array=specification.object.size_m
	var low := Vector3(INF,INF,INF)
	var high := Vector3(-INF,-INF,-INF)
	for x in [-1,1]:
		for y in [-1,1]:
			for z in [-1,1]:
				var p := h*gv([x*dims[0]/2,y*dims[1]/2,z*dims[2]/2])+gv(specification.bodies.chassis.origin_m)
				var a: Array=source(p)
				low=low.min(Vector3(a[0],a[1],a[2]))
				high=high.max(Vector3(a[0],a[1],a[2]))
	var supported := false
	var left := false
	var right := false
	for b in item.get_colliding_bodies():
		if str(b.name)=="chassis":supported=true
		if str(b.name)=="cargo_slide_-1":left=true
		if str(b.name)=="cargo_slide_1":right=true
		if str(b.name).begins_with("arm_"):supported=false;break
	var inside := low.x>=-0.146 and high.x<=-0.037 and low.y>=-0.112 and high.y<=0.112 and low.z>.254 and high.z<.315
	supported=supported and inside
	return {"supported":supported,"inside":inside,"bilateral":left and right,"bounds":[[low.x,low.y,low.z],[high.x,high.y,high.z]]}


func apply_cargo(s: Dictionary) -> Dictionary:
	var slide_target_velocity_m_s: Array=[]
	var ratio: float=specification.cargo.drive_metres_per_radian
	var target: float=clampf(ratio*float(command.get("cargo_target_rad",0.0)),0.0,0.067)
	for i in [22,23]:
		var speed: float=clampf(12.0*(target-float(s.q[i]))-0.8*float(s.v[i]),-0.25,0.25)
		PhysicsServer3D.generic_6dof_joint_set_param(joint_rids[i],0,PhysicsServer3D.G6DOF_JOINT_LINEAR_MOTOR_TARGET_VELOCITY,speed)
		slide_target_velocity_m_s.append(speed)
	var rotor: Dictionary=drives[24]
	var motor: float=clampf(0.01*(command.get("cargo_target_rad",0.0)-s.q[24])-0.0003*s.v[24],-0.003,0.003)
	var torque: Vector3=(rotor.parent.global_basis*rotor.axis)*motor
	rotor.child.apply_torque(torque)
	rotor.parent.apply_torque(-torque)
	return {"slide_target_velocity_m_s":slide_target_velocity_m_s,
		"slide_force_limit_N":3.15,"rotor_requested_torque_Nm":motor}


func _exit_tree() -> void:
	for rid in joint_rids:PhysicsServer3D.free_rid(rid)

func apply_command(s: Dictionary, next_command: Dictionary) -> void:
	command = next_command
	var motor_target_velocity_rad_s: Array=[]
	var motor_max_impulse_Nms: Array=[]
	var arm_requested_torque_Nm: Array=[]
	for i in range(22):
		var d: Dictionary=drives[i]
		if i < 16:
			var speed: float
			var cap: float
			if d.kind == "wheel":
				var leg: int=i/4
				var requested_speed: float=-float(command.wheel_speed[leg]) if command.mode == "transport" else -4.0 * (float(command.target_leg[i]) - float(s.q[i]))
				var max_delta: float=20.0/float(Engine.physics_ticks_per_second)
				wheel_motor_targets[leg]+=clampf(requested_speed-float(wheel_motor_targets[leg]),-max_delta,max_delta)
				speed=float(wheel_motor_targets[leg])
				cap = 1.3
			else:
				speed = -0.5 * (float(command.target_leg[i]) - float(s.q[i]))
				cap = 8.0
			PhysicsServer3D.hinge_joint_set_flag(joint_rids[i], PhysicsServer3D.HINGE_JOINT_FLAG_ENABLE_MOTOR, true)
			PhysicsServer3D.hinge_joint_set_param(joint_rids[i], PhysicsServer3D.HINGE_JOINT_MOTOR_TARGET_VELOCITY, clampf(speed, -30.0, 30.0) if d.kind == "wheel" else clampf(speed, -6.0, 6.0))
			PhysicsServer3D.hinge_joint_set_param(joint_rids[i], PhysicsServer3D.HINGE_JOINT_MOTOR_MAX_IMPULSE, cap / float(Engine.physics_ticks_per_second))
			motor_target_velocity_rad_s.append(clampf(speed,-30.0,30.0) if d.kind == "wheel" else clampf(speed,-6.0,6.0))
			motor_max_impulse_Nms.append(cap / float(Engine.physics_ticks_per_second))
			continue
		var u: float
		if i<16:
			if d.kind=="wheel":
				if command.mode=="transport":u=clampf(0.4*(command.wheel_speed[i/4]-s.v[i]),-1.3,1.3)
				else:u=clampf(2*(command.target_leg[i]-s.q[i])-0.4*s.v[i],-1.3,1.3)
			else:u=clampf(80*(command.target_leg[i]-s.q[i])-2*s.v[i],-8,8)
			u-=0.03*s.v[i]
		else:
			var cap: float=command.grip_cap if i==21 else 2.94
			u=clampf(10.0*(command.target_arm[i-16]-s.q[i])-0.30*s.v[i]+command.arm_bias[i-16]-0.052*tanh(s.v[i]/0.01),-cap,cap)
			arm_requested_torque_Nm.append(u)
		var torque: Vector3=(d.parent.global_basis*d.axis)*u
		d.child.apply_torque(torque)
		d.parent.apply_torque(-torque)
	var cargo_actuators: Dictionary=apply_cargo(s) if drives.size()>=25 else {}
	previous_applied_actuators={"applied_at_state_time_s":float(s.time),
		"hinge_target_velocity_rad_s":motor_target_velocity_rad_s,
		"hinge_max_impulse_Nms":motor_max_impulse_Nms,
		"arm_requested_torque_Nm":arm_requested_torque_Nm,
		"cargo":cargo_actuators}
	tick+=1
