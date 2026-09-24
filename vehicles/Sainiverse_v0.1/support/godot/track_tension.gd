extends RefCounted
## Exact support-envelope integral; physical generalized forces, not posing.
var c:Dictionary
var names:Array=[]
var base:Array=[]
var forces:Array=[]
var lengths:Array=[]
var tensions:Array=[]
var pushes:Array=[]
var coordinates:Array=[]
var max_tension:=0.0
var max_extension:=0.0
var min_extension:=INF
var max_push:=0.0
var min_idler:=INF
var max_idler:=-INF
var slack_steps:=0
var dissipated:=0.0
var step_usec:=0
var steps:=0
var path_core=null
var native_calls:=0
var maximum_native_length_error_m:=0.0
var maximum_native_gradient_error:=0.0

func configure(config:Dictionary)->void:
	c=config
	for belt in c.belts:names.append_array(belt.joints)
	for w in c.support_circles_x_z_radius_m:base.append(Vector3(w[0],w[1],w[2]))

func envelope(w:Array)->Dictionary:
	if OS.get_environment("SAINIVERSE_NATIVE_TRACK_ENVELOPE")!="0":
		if path_core==null and ClassDB.class_exists("LeviathanTrackPath"):path_core=ClassDB.instantiate("LeviathanTrackPath")
		if path_core!=null and path_core.has_method("envelope"):
			var native:Dictionary=path_core.envelope(w)
			native_calls+=1
			if OS.get_environment("SAINIVERSE_NATIVE_TRACK_PARITY")=="1":
				var reference:Dictionary=_envelope_gd(w)
				maximum_native_length_error_m=maxf(maximum_native_length_error_m,absf(float(native.length)-float(reference.length)))
				for i in reference.gradient.size():
					maximum_native_gradient_error=maxf(maximum_native_gradient_error,(native.gradient[i] as Vector2).distance_to(reference.gradient[i]))
			return native
	return _envelope_gd(w)

func _envelope_gd(w:Array)->Dictionary:
	var angles:Array=[0.,TAU]
	for i in w.size():
		for j in i:
			var dx:float=w[i].x-w[j].x;var dz:float=w[i].y-w[j].y;var distance:float=sqrt(dx*dx+dz*dz)
			if distance<=absf(w[j].z-w[i].z):continue
			var a:float=atan2(dz,dx);var b:float=acos((w[j].z-w[i].z)/distance)
			angles.append(fposmod(a-b,TAU));angles.append(fposmod(a+b,TAU))
	angles.sort()
	var gradient:Array=[];gradient.resize(w.size());gradient.fill(Vector2.ZERO)
	var length:=0.0
	for k in angles.size()-1:
		var a:float=angles[k];var b:float=angles[k+1]
		if b-a<1e-12:continue
		var mid:float=(a+b)*.5;var nx:float=cos(mid);var nz:float=sin(mid);var owner:=0;var support:=-INF
		for i in w.size():
			var value:float=w[i].x*nx+w[i].y*nz+w[i].z
			if value>support:support=value;owner=i
		var integral:=Vector2(sin(b)-sin(a),cos(a)-cos(b));gradient[owner]+=integral
		length+=w[owner].x*integral.x+w[owner].y*integral.y+w[owner].z*(b-a)
	return {"length":length,"gradient":gradient}

func step(q:Array,dq:Array,dt:float)->void:
	var started:int=Time.get_ticks_usec()
	forces=[];lengths=[];tensions=[];pushes=[];coordinates=[]
	for belt in c.belts.size():
		var w:Array=base.duplicate();var offset:int=belt*4;var travel:Array=[];var rates:Array=[]
		for i in 4:travel.append(float(q[offset+i]));rates.append(float(dq[offset+i]))
		for i in 3:w[i+1].y+=travel[i]
		w[4].x+=travel[3]
		var shape:Dictionary=envelope(w);var g:Array=shape.gradient
		var jac:Array=[g[1].y,g[2].y,g[3].y,g[4].x];var rate:=0.0
		for i in 4:rate+=float(jac[i])*float(rates[i])
		var extension:float=shape.length-float(c.natural_length_m)
		var elastic:float=minf(float(c.belt_stiffness_N_m)*maxf(extension,0.),c.tension_limit_N)
		var tension:float=clampf(elastic+float(c.belt_damping_Ns_m)*rate,0.,c.tension_limit_N) if extension>0 else 0.
		var spring:float=clampf(float(c.recoil_preload_N)-float(c.recoil_stiffness_N_m)*float(travel[3]),0.,c.recoil_force_limit_N)
		var push:float=clampf(spring-float(c.recoil_damping_Ns_m)*float(rates[3]),0.,c.recoil_force_limit_N)
		for i in 4:forces.append(-tension*float(jac[i])+(push if i==3 else 0.))
		dissipated+=(maxf(0.,(tension-elastic)*rate)+maxf(0.,-(push-spring)*float(rates[3])))*dt
		lengths.append(shape.length);tensions.append(tension);pushes.append(push);coordinates.append(travel)
		max_tension=maxf(max_tension,tension);max_extension=maxf(max_extension,extension);min_extension=minf(min_extension,extension)
		max_push=maxf(max_push,push);min_idler=minf(min_idler,travel[3]);max_idler=maxf(max_idler,travel[3])
		if extension<=0:slack_steps+=1
	step_usec+=Time.get_ticks_usec()-started;steps+=1

func state()->Dictionary:
	return {"lengths_m":lengths.duplicate(),"tensions_N":tensions.duplicate(),"idler_recoil_forces_N":pushes.duplicate(),"coordinates_m":coordinates.duplicate(true),"max_tension_N":max_tension,"extension_range_m":[min_extension,max_extension],"idler_range_m":[min_idler,max_idler],"max_recoil_force_N":max_push,"slack_bank_steps":slack_steps,"dissipated_J":dissipated,"mean_track_step_ms":float(step_usec)/maxi(steps,1)/1000.,"native_calls":native_calls,"maximum_native_length_error_m":maximum_native_length_error_m,"maximum_native_gradient_error":maximum_native_gradient_error}
