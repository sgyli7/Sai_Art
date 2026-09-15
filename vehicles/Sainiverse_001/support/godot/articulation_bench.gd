extends SceneTree
## Zero-gravity mechanism fixture, not a vehicle scene or performance claim.
const DESIGN_ROOT="@SAI_ROOT@/support"
var cfg:Dictionary
var old:Dictionary
var stage:Node3D
var fixed:StaticBody3D
var bodies:Array[RigidBody3D]=[]
var axes:Array[Vector3]=[Vector3.LEFT,Vector3.UP,Vector3.FORWARD,Vector3.RIGHT]
var anchor:=Vector3(-21,6.5,0)
var elapsed:=0.0
var samples:Array=[]
var count:=0
var start_usec:int
var joints:Array[Joint3D]=[]
var parent_anchors:Array[Vector3]=[]
var body_anchors:Array[Vector3]=[]
var schedule:Array=[[15,[4,0,0,0]],[75,[4,45,0,0]],[135,[4,-45,0,0]],
	[175,[4,0,0,0]],[195,[4,0,8,0]],[215,[4,0,-8,0]],
	[235,[4,0,0,6]],[255,[4,0,0,-6]],[275,[4,0,0,0]],[300,[0,0,0,0]]]

func _initialize()->void:
	call_deferred("_build_fixture")

func _build_fixture()->void:
	Engine.physics_ticks_per_second=200
	cfg=JSON.parse_string(FileAccess.get_file_as_string(DESIGN_ROOT+"/design/articulation_candidate.json"))
	old=JSON.parse_string(FileAccess.get_file_as_string(DESIGN_ROOT+"/assets/physics.json"))
	var pitch_anchor:Vector3=anchor+Vector3(cfg.pitch_axis_offset_m[0],cfg.pitch_axis_offset_m[2],-cfg.pitch_axis_offset_m[1])
	var roll_anchor:Vector3=pitch_anchor+Vector3(cfg.roll_axis_offset_from_pitch_m[0],cfg.roll_axis_offset_from_pitch_m[2],-cfg.roll_axis_offset_from_pitch_m[1])
	stage=Node3D.new();root.add_child(stage)
	fixed=StaticBody3D.new();fixed.name="FixtureFront";fixed.position=anchor;stage.add_child(fixed)
	for i in 4:
		var body:=RigidBody3D.new();body.name="Carrier"+str(i)
		body.mass=float(cfg.moving_carrier_mass_kg[i]) if i<3 else float(old.mass_kg[1])
		if i<3:body.inertia=Vector3.ONE*float(cfg.carrier_inertia_kg_m2[i])
		else:body.inertia=Vector3(old.inertia_diagonal[0],old.inertia_diagonal[2],old.inertia_diagonal[1])
		body.center_of_mass_mode=RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
		body.center_of_mass=Vector3.ZERO;body.gravity_scale=0.;body.linear_damp=0.;body.angular_damp=0.;body.can_sleep=false
		body.collision_layer=0;body.collision_mask=0
		body.position=anchor if i<2 else pitch_anchor if i==2 else Vector3(-42,10,0)
		stage.add_child(body);bodies.append(body)
		var parent:PhysicsBody3D=fixed if i==0 else bodies[i-1]
		var joint:Joint3D
		if i==0:
			var slider:=SliderJoint3D.new()
			slider.basis=Basis(Vector3.UP,PI)
			slider.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_LOWER,0.)
			slider.set_param(SliderJoint3D.PARAM_LINEAR_LIMIT_UPPER,4.)
			joint=slider
		else:
			var hinge:=HingeJoint3D.new()
			hinge.basis=Basis(Quaternion(Vector3.BACK,axes[i]))
			hinge.set_flag(HingeJoint3D.FLAG_USE_LIMIT,true)
			var key:String=["yaw_degrees","pitch_degrees","roll_degrees"][i-1]
			hinge.set_param(HingeJoint3D.PARAM_LIMIT_LOWER,deg_to_rad(float(cfg[key][0])))
			hinge.set_param(HingeJoint3D.PARAM_LIMIT_UPPER,deg_to_rad(float(cfg[key][1])))
			joint=hinge
		var joint_anchor:Vector3=anchor if i<2 else pitch_anchor if i==2 else roll_anchor
		joint.position=joint_anchor;stage.add_child(joint)
		joint.node_a=parent.get_path();joint.node_b=body.get_path();joint.exclude_nodes_from_collision=true
		joints.append(joint)
		parent_anchors.append(joint_anchor-parent.position);body_anchors.append(joint_anchor-body.position)
	start_usec=Time.get_ticks_usec()

func _physics_process(dt:float)->bool:
	if bodies.size()!=4:return false
	var requested:Array=schedule[-1][1]
	for entry in schedule:
		if elapsed<float(entry[0]):requested=entry[1];break
	var target:Array=[float(requested[0]),deg_to_rad(float(requested[1])),deg_to_rad(float(requested[2])),deg_to_rad(float(requested[3]))]
	var position:Array=[];var velocity:Array=[];var forces:Array=[];var anchor_errors:Array=[]
	for i in 4:
		var body:RigidBody3D=bodies[i]
		var parent:Node3D=fixed if i==0 else bodies[i-1]
		var parent_omega:Vector3=Vector3.ZERO if i==0 else bodies[i-1].angular_velocity
		var axis:Vector3=parent.global_basis*axes[i]
		var q:float;var dq:float;var kp:float;var kd:float;var cap:float
		if i==0:
			q=(body.global_position-anchor).dot(axes[0]);dq=body.linear_velocity.dot(axes[0])
			kp=cfg.extension_kp_N_per_m;kd=cfg.extension_kd_Ns_per_m;cap=cfg.extension_force_limit_N
		else:
			var rotation:Quaternion=(parent.global_basis.inverse()*body.global_basis).get_rotation_quaternion()
			q=2*atan2(Vector3(rotation.x,rotation.y,rotation.z).dot(axes[i]),rotation.w)
			dq=(body.angular_velocity-parent_omega).dot(axis)
			kp=cfg.rotation_kp_Nm_per_rad[i-1];kd=cfg.rotation_kd_Nms_per_rad[i-1];cap=cfg.rotation_torque_limits_Nm[i-1]
		var effort:float=clampf(kp*(float(target[i])-q)-kd*dq,-cap,cap)
		if i==0:body.apply_central_force(axis*effort)
		else:
			body.apply_torque(axis*effort)
			bodies[i-1].apply_torque(-axis*effort)
		position.append(q);velocity.append(dq);forces.append(effort)
		if i>0:
			var body_anchor:Vector3=body.global_transform*body_anchors[i]
			var parent_anchor:Vector3=parent.global_transform*parent_anchors[i]
			anchor_errors.append(body_anchor.distance_to(parent_anchor))
	if count%100==99:
		samples.append({"time":elapsed,"position":position,"velocity":velocity,"force":forces,"target":target,"anchor_errors_m":anchor_errors})
	elapsed+=dt;count+=1
	if elapsed>=300:
		var output:Dictionary={"engine":"Godot "+str(Engine.get_version_info().string),"physics_engine":ProjectSettings.get_setting("physics/3d/physics_engine"),
			"gravity":[0,0,0],"simulation_s":elapsed,"wall_s":(Time.get_ticks_usec()-start_usec)/1e6,"samples":samples,
			"scope":"Fixed-front zero-gravity joint fixture; finite actuator forces, actual previous rear mass/inertia. No ground, vehicle driving, visual clearance or training claim."}
		var f:=FileAccess.open(DESIGN_ROOT+"/reports/articulation_r015/bench/godot.json",FileAccess.WRITE)
		f.store_string(JSON.stringify(output,"  "));f.close()
		print("ARTICULATION_BENCH_COMPLETE ",JSON.stringify({"seconds":elapsed,"samples":samples.size(),"physics":output.physics_engine}))
		quit()
	return false
