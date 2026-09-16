extends RefCounted
## Finite actuators and unilateral cable forces; no commanded rigid-body poses.
var total_skin_usec:=0
var skin_frames:=0
var total_step_usec:=0
var total_steps:=0
var host:SceneTree
var rig:Dictionary
var links:Dictionary={}
var coordinate_cache:Dictionary={}
var targets:Dictionary={}
var paid:Dictionary={}
var spans:Array=[]
var samples:Array=[]
var working:=false
var selected:=0
var auto_work:=false
var sample_clock:=0.
var maximum_cable_force:=0.

func configure(controller:SceneTree,data:Dictionary)->void:
	host=controller;rig=data
	for spec in rig.joints:
		for link in host.links:
			if link.spec.name==spec.name:links[spec.name]=link;break
		targets[spec.name]=0.
	for crane in rig.cranes:paid[crane.name]=float(crane.paid_length_m)
	for body in rig.bodies:
		var rb:RigidBody3D=host.bodies[body.name];rb.collision_layer=64;rb.collision_mask=1|8;rb.angular_damp=.15
		if body.has("collision_convex"):
			var col:=CollisionShape3D.new();var shape:=ConvexPolygonShape3D.new();var points:=PackedVector3Array()
			for v in body.collision_convex:points.append(host.vec(v))
			shape.points=points;col.shape=shape;rb.add_child(col)
		if body.has("collision_box"):
			var box:Dictionary=body.collision_box;var col:=CollisionShape3D.new();var shape:=BoxShape3D.new();shape.size=host.vec(box.size).abs();col.shape=shape;col.position=host.vec(box.center);rb.add_child(col)
	for box in rig.cargo_colliders:
		var col:=CollisionShape3D.new();var shape:=BoxShape3D.new();shape.size=host.vec(box.size).abs();col.shape=shape;col.position=host.vec(box.center);host.bodies[box.hull].add_child(col)
	for spec in rig.spans:
		var group:Node3D=host.visual.groups[spec.group]
		var node:MeshInstance3D=group.get_node(str(spec.group)+"__"+str(spec.material))
		spans.append({"spec":spec,"node":node,"group":group})

func coordinate(name:String)->Vector2:
	if coordinate_cache.has(name):return coordinate_cache[name]
	var link:Dictionary=links[name];var axis:Vector3=link.parent.global_basis*link.axis
	var pa:Vector3=link.parent.global_transform*link.a;var pb:Vector3=link.body.global_transform*link.b
	if link.spec.kind=="slide":
		var result:=Vector2((pb-pa).dot(axis),(host.point_velocity(link.body,pb)-host.point_velocity(link.parent,pa)).dot(axis));coordinate_cache[name]=result;return result
	var q:Quaternion=(link.parent.global_basis.inverse()*link.body.global_basis).get_rotation_quaternion()
	var result:=Vector2(wrapf(2*atan2(Vector3(q.x,q.y,q.z).dot(link.axis),q.w),-PI,PI),(link.body.angular_velocity-link.parent.angular_velocity).dot(axis));coordinate_cache[name]=result;return result

func endpoint(item:Dictionary)->Vector3:return host.bodies[item.body].global_transform*host.vec(item.local)

func servo(name:String,goal:float,rate:float,kp:float,kd:float,cap:float,dt:float,gravity_bodies:Array=[])->void:
	var link:Dictionary=links[name];var q:=coordinate(name);targets[name]=move_toward(float(targets[name]),goal,rate*dt)
	var axis:Vector3=link.parent.global_basis*link.axis;var anchor:Vector3=link.parent.global_transform*link.a
	var gravity:=0.
	for body_name in gravity_bodies:
		var body:RigidBody3D=host.bodies[body_name]
		gravity+=Vector3.DOWN.dot(axis)*body.mass*9.81 if link.spec.kind=="slide" else (host.com(body)-anchor).cross(Vector3.DOWN*body.mass*9.81).dot(axis)
	var effort:float=clampf(kp*(float(targets[name])-q.x)-kd*q.y-gravity,-cap,cap)
	if link.spec.kind=="slide":
		link.body.apply_force(axis*effort,anchor-link.body.global_position);link.parent.apply_force(-axis*effort,anchor-link.parent.global_position)
	else:link.body.apply_torque(axis*effort);link.parent.apply_torque(-axis*effort)

func step(dt:float,time:float)->void:
	var started:int=Time.get_ticks_usec()
	coordinate_cache.clear()
	if auto_work:working=time>=12. and (str(host.options.get("mode",""))!="equipment_cycle" or time<55.)
	var stopped:bool=host.bodies.front.linear_velocity.length()<.10
	working=working and stopped
	for i in rig.cranes.size():
		var c:Dictionary=rig.cranes[i];var pin:Array=host.visual.config.groups[c.luff].pivot_source_m;var hull:Array=host.visual.config.groups[c.hull].pivot_source_m
		var outward:float=-signf(float(pin[0])-float(hull[0]))*signf(float(c.direction[1]))
		var yaw_goal:=0.;var luff_goal:=0.;var extend_goal:=0.;var rope_goal:float=c.paid_length_m
		if working:
			if auto_work:
				luff_goal=.30;extend_goal=.65;rope_goal=maxf(1.3,float(c.paid_length_m)-1.4)
				if time>23.:yaw_goal=outward*.20*sin(minf((time-23.)*.085,PI*.65))
			else:
				yaw_goal=float(targets[c.slew]);luff_goal=float(targets[c.luff]);extend_goal=float(targets[c.extend]);rope_goal=float(paid[c.name])
				if i==selected:
					yaw_goal+=host.cockpit.axis("crane_slew")*.12*dt
					luff_goal+=host.cockpit.axis("crane_luff")*.07*dt
					extend_goal+=host.cockpit.axis("crane_extend")*.3*dt
					rope_goal+=host.cockpit.axis("crane_winch")*.45*dt
		servo(c.slew,clampf(yaw_goal,-PI/3,PI/3),.055,8000000.,2400000.,2500000.,dt)
		# Cylinder force acts at its two real eye locations. A finite force cap
		# limits attainable boom torque at the current lever arm.
		var q:=coordinate(c.luff);luff_goal=clampf(luff_goal,0.,deg_to_rad(35.));targets[c.luff]=move_toward(float(targets[c.luff]),luff_goal,.035*dt)
		var link:Dictionary=links[c.luff];var axis:Vector3=link.parent.global_basis*link.axis;var pivot:Vector3=link.parent.global_transform*link.a
		var gravity:=0.
		for name in [c.luff,c.extend,c.hook]:
			var body:RigidBody3D=host.bodies[name];gravity+=(host.com(body)-pivot).cross(Vector3.DOWN*body.mass*9.81).dot(axis)
		var requested:float=14000000.*(float(targets[c.luff])-q.x)-2800000.*q.y-gravity
		var a:=endpoint(c.cylinder_a);var b:=endpoint(c.cylinder_b);var direction:Vector3=(b-a).normalized();var lever:float=(b-pivot).cross(direction).dot(axis)
		var force:float=clampf(requested/maxf(lever,.1),-float(c.cylinder_force_cap_N),float(c.cylinder_force_cap_N))
		host.bodies[c.luff].apply_force(direction*force,b-host.bodies[c.luff].global_position);host.bodies[c.slew].apply_force(-direction*force,a-host.bodies[c.slew].global_position)
		servo(c.extend,clampf(extend_goal,-.9,1.8),.20,650000.,320000.,600000.,dt,[c.extend,c.hook])
		paid[c.name]=move_toward(float(paid[c.name]),clampf(rope_goal,1.3,11.),.4*dt)
		var top:=endpoint(c.tip);var bottom:=endpoint(c.hook_attach);var delta:Vector3=top-bottom;var length:float=delta.length();var rope_dir:Vector3=delta/maxf(length,.001)
		var velocity:float=(host.point_velocity(host.bodies[c.extend],top)-host.point_velocity(host.bodies[c.hook],bottom)).dot(rope_dir)
		var tension:float=clampf(float(c.rope_stiffness_N_m)*(length-float(paid[c.name]))+float(c.rope_damping_N_s_m)*velocity,0.,float(c.rope_force_cap_N)) if length>float(paid[c.name]) else 0.
		host.bodies[c.hook].apply_force(rope_dir*tension,bottom-host.bodies[c.hook].global_position);host.bodies[c.extend].apply_force(-rope_dir*tension,top-host.bodies[c.extend].global_position)
		maximum_cable_force=maxf(maximum_cable_force,tension)
		if sample_clock<=0.:samples.append({"time":time,"name":c.name,"slew_rad":coordinate(c.slew).x,"luff_rad":q.x,"extension_m":coordinate(c.extend).x,"paid_length_m":paid[c.name],"cable_length_m":length,"cable_force_N":tension,"cylinder_force_N":force,"hook_source_world":host.source(host.bodies[c.hook].global_position)})
	var panel:Dictionary=rig.panel
	var panel_yaw:float=.28*sin(maxf(time-15.,0.)*.06) if auto_work and working else float(targets[panel.slew]) if working else 0.
	var panel_fold:float=-.65*(.5-.5*cos(minf(maxf(time-15.,0.)*.09,PI))) if auto_work and working else float(targets[panel.fold]) if working else 0.
	if working and not auto_work:
		panel_yaw+=host.cockpit.axis("panel_slew")*.08*dt
		panel_fold+=host.cockpit.axis("panel_fold")*.08*dt
	servo(panel.slew,clampf(panel_yaw,-PI/3,PI/3),.05,16000000.,5000000.,5000000.,dt)
	servo(panel.fold,clampf(panel_fold,-1.2,.1),.055,16000000.,4000000.,12000000.,dt,[panel.fold])
	if sample_clock<=0.:samples.append({"time":time,"name":"receiver","slew_rad":coordinate(panel.slew).x,"fold_rad":coordinate(panel.fold).x})
	sample_clock-=dt
	if sample_clock<= -.000001:sample_clock=.1
	total_steps+=1;total_step_usec+=Time.get_ticks_usec()-started

func update_skins()->void:
	var started:int=Time.get_ticks_usec()
	for item in spans:
		var spec:Dictionary=item.spec;var group:Node3D=item.group;var node:MeshInstance3D=item.node
		var a:Vector3=group.to_local(endpoint(spec.a));var b:Vector3=group.to_local(endpoint(spec.b));var direction:Vector3=(b-a).normalized()
		if spec.mode=="from_a":b=a+direction*float(spec.length)
		if spec.mode=="to_b":a=b-direction*float(spec.length)
		var old_a:=Vector3(spec.rest_start[0],spec.rest_start[1],spec.rest_start[2]);var old_b:=Vector3(spec.rest_end[0],spec.rest_end[1],spec.rest_end[2]);var old_dir:Vector3=(old_b-old_a).normalized()
		var factor:float=a.distance_to(b)/old_a.distance_to(old_b)-1.
		var stretch:=Basis(Vector3.RIGHT+old_dir*old_dir.x*factor,Vector3.UP+old_dir*old_dir.y*factor,Vector3.BACK+old_dir*old_dir.z*factor)
		var rotation:=Basis(Quaternion(old_dir,(b-a).normalized()));var basis:Basis=rotation*stretch
		node.transform=Transform3D(basis,a-basis*old_a)

	skin_frames+=1;total_skin_usec+=Time.get_ticks_usec()-started

func stowed()->bool:
	for c in rig.cranes:
		if absf(float(paid[c.name])-float(c.paid_length_m))>.025:return false
	for name in targets:
		if absf(coordinate(name).x)>.025:return false
	return not working
