extends RefCounted
## Source-owned container with actual rigid contact, deck lock and hook pin.
var host:SceneTree
var data:Dictionary
var body:RigidBody3D
var deck_lock:Generic6DOFJoint3D
var hook_joint:PinJoint3D
var attached_crane:=-1
var phase:="secured"
var phase_start:=0.
var samples:Array=[]
var events:Array=[]
var next_sample:=0.
var test_mode:=false
var released:=false
var initial_position:=Vector3.ZERO
var max_lift:=0.
var rejection:=""
var supported_time:=0.
var next_button_pulse:=0.
var rigging_meshes:Array[MeshInstance3D]=[]

func update_rigging()->void:
	if rigging_meshes.is_empty():
		for node in body.find_children("*rig_cargo_spreader*","MeshInstance3D",true,false):rigging_meshes.append(node)
	for node in rigging_meshes:node.visible=host.equipment.working or attached_crane>=0

func pulse_hook()->void:
	# The scenario operates the same physical button as keyboard/mouse or an arm.
	if host.elapsed>=next_button_pulse:
		host.cockpit.pulse("cargo");next_button_pulse=host.elapsed+1.

func configure(h:SceneTree)->void:
	host=h;data=h.equipment.rig.cargo[0];body=h.bodies[data.name]
	body.collision_layer=256;body.collision_mask=1|8|64;body.contact_monitor=true;body.max_contacts_reported=32;body.angular_damp=.3
	initial_position=body.global_position
	deck_lock=Generic6DOFJoint3D.new();deck_lock.name="ContainerDeckTwistlocks";h.stage.add_child(deck_lock);deck_lock.global_position=body.global_position
	for suffix in ["x","y","z"]:
		deck_lock.call("set_flag_"+suffix,Generic6DOFJoint3D.FLAG_ENABLE_LINEAR_LIMIT,true)
		deck_lock.call("set_flag_"+suffix,Generic6DOFJoint3D.FLAG_ENABLE_ANGULAR_LIMIT,true)
		for param in [Generic6DOFJoint3D.PARAM_LINEAR_LOWER_LIMIT,Generic6DOFJoint3D.PARAM_LINEAR_UPPER_LIMIT,Generic6DOFJoint3D.PARAM_ANGULAR_LOWER_LIMIT,Generic6DOFJoint3D.PARAM_ANGULAR_UPPER_LIMIT]:deck_lock.call("set_param_"+suffix,param,0.)
	deck_lock.node_a=deck_lock.get_path_to(h.bodies[data.hull]);deck_lock.node_b=deck_lock.get_path_to(body)
	test_mode=str(h.options.get("mode",""))=="cargo_cycle"

func eye()->Vector3:return body.global_transform*host.vec(data.eye_local)
func hook_eye(index:int)->Vector3:
	return host.bodies[host.equipment.rig.cranes[index].hook].global_transform*Vector3(0,-.48,0)
func remove_joint(joint:Joint3D)->void:
	joint.get_parent().remove_child(joint);joint.queue_free()
func request()->bool:
	rejection=""
	if host.bodies.front.linear_velocity.length()>.10 or not host.equipment.working:rejection="PARK AND ENABLE WORK";return false
	if hook_joint!=null:
		if supported_time<.35 or body.linear_velocity.length()>.15:rejection="LAND LOAD BEFORE RELEASE";return false
		remove_joint(hook_joint);hook_joint=null;attached_crane=-1;released=true
		events.append({"time":host.elapsed,"action":"release","position":host.source(body.global_position)});return true
	var index:int=host.equipment.selected
	if hook_eye(index).distance_to(eye())>.32:rejection="ALIGN HOOK WITH LIFTING EYE";return false
	if body.linear_velocity.distance_to(host.bodies[host.equipment.rig.cranes[index].hook].linear_velocity)>.3:rejection="WAIT FOR HOOK TO SETTLE";return false
	# Configure anchors only after putting the joint in its actual world frame.
	hook_joint=PinJoint3D.new();hook_joint.name="ContainerHookPin";host.stage.add_child(hook_joint);hook_joint.global_position=hook_eye(index)
	hook_joint.node_a=hook_joint.get_path_to(host.bodies[host.equipment.rig.cranes[index].hook]);hook_joint.node_b=hook_joint.get_path_to(body)
	if deck_lock!=null:remove_joint(deck_lock);deck_lock=null
	attached_crane=index;events.append({"time":host.elapsed,"action":"attach","hook_eye_error_m":hook_eye(index).distance_to(eye()),"mass_kg":body.mass});return true
func set_phase(p:String)->void:
	phase=p;phase_start=host.elapsed;events.append({"time":host.elapsed,"phase":p})
	print("CARGO_PHASE ",p," t=",host.elapsed)
	if str(host.options.get("capture","false"))=="true":host.call_deferred("_capture","cargo_"+p)
func step(dt:float)->void:
	var state:=PhysicsServer3D.body_get_direct_state(body.get_rid())
	var supported:=false
	if state!=null:
		for i in state.get_contact_count():
			var n:Vector3=state.get_contact_local_normal(i)
			var p:Vector3=body.to_local(state.get_contact_local_position(i))
			if n.dot(Vector3.UP)>.5 and p.y<-.7:supported=true
	supported_time=supported_time+dt if supported else 0.
	max_lift=maxf(max_lift,body.global_position.y-initial_position.y)
	if test_mode:
		host.equipment.working=host.elapsed>=12.;host.equipment.selected=0
		var c:Dictionary=host.equipment.rig.cranes[0]
		var goal:Dictionary={"yaw":-.374,"luff":.30,"extend":3.94,"rope":3.5}
		if host.elapsed>=12. and phase=="secured":set_phase("align")
		if phase=="align":
			# Winch closes measured vertical error; all motions remain finite servos.
			goal.rope=clampf(float(host.equipment.paid[c.name])+hook_eye(0).y-eye().y,1.3,24.)
			if attached_crane==0:set_phase("lift")
			elif hook_eye(0).distance_to(eye())<.28 and body.linear_velocity.distance_to(host.bodies[c.hook].linear_velocity)<.25:pulse_hook()
		elif phase=="lift":
			# Raise vertically over the stack before moving sideways. Coordinate
			# extension with measured luff; a fixed extension sweeps into neighbours.
			var pitch:float=host.equipment.coordinate(c.luff).x
			goal.luff=minf(.60,.30+(host.elapsed-phase_start)*.015);goal.rope=1.3
			goal.extend=(10.42810649+.34*sin(pitch))/cos(pitch)-7.08
			if pitch>.59 and body.linear_velocity.length()<.15:set_phase("clearance")
		elif phase=="clearance":
			goal.luff=.60;goal.extend=7.20;goal.rope=1.3
			if host.equipment.extension(c)>7.12 and body.linear_velocity.length()<.15:set_phase("swing")
		elif phase=="swing":
			goal.luff=.60;goal.extend=7.20;goal.rope=1.3;goal.yaw=-2.95
			if absf(host.equipment.coordinate(c.slew).x+2.95)<.025 and body.linear_velocity.length()<.20:set_phase("lower")
		elif phase=="lower":
			goal.luff=.60;goal.extend=7.20;goal.yaw=-2.95;goal.rope=24.
			if body.get_contact_count()>0 and body.global_position.y<2.0 and body.linear_velocity.length()<.12:
				if released:set_phase("released")
				elif supported_time>.35:pulse_hook()
		elif phase=="released":goal.luff=.60;goal.extend=7.20;goal.yaw=-2.95;goal.rope=1.3
		if host.equipment.working:host.equipment.override_goals[c.name]=goal
		else:host.equipment.override_goals.erase(c.name)
	if host.elapsed>=next_sample:
		next_sample=host.elapsed+.10
		samples.append({"time":host.elapsed,"phase":phase,"position":host.source(body.global_position),"speed_m_s":body.linear_velocity.length(),"contacts":body.get_contact_count(),"contact_bodies":body.get_colliding_bodies().map(func(b):return str(b.name)),"supported_time_s":supported_time,"attached_crane":attached_crane,"deck_locked":deck_lock!=null,"hook_eye_error_m":hook_eye(0).distance_to(eye()),"max_lift_m":max_lift,"rejection":rejection})
func report()->Dictionary:
	return {"rigging_meshes":rigging_meshes.size(),"rigging_visible":not rigging_meshes.is_empty() and rigging_meshes[0].visible,"mass_kg":body.mass,"released":released,"max_lift_m":max_lift,"events":events,"samples":samples,"scope":"One authored 8 t gross 20 ft container; real free body, deck restraint, proximity hook pin and supported release. Work-mode rigging installation is instantaneous. Not all cargo or manufacturer rating qualification."}
