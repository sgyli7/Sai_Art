extends Node2D
## Display-only real telemetry, separate from operable control joint values.
var host:SceneTree
var kind:=12
var timer:=0.
var channels:Array=[]
var screen_mesh:MeshInstance3D

func _ready()->void:
	screen_mesh=_find_screen(host.bodies.front)

func _find_screen(node:Node)->MeshInstance3D:
	if node is MeshInstance3D and str(node.name).contains("__decal_"+str(kind)+"_"):return node
	for child in node.get_children():
		var found:=_find_screen(child)
		if found!=null:return found
	return null

func _screen_in_camera()->bool:
	# Keep the dashboard live whenever any part of its screen enters the view.
	# A missing mesh falls back to normal updates.
	if screen_mesh==null or screen_mesh.mesh==null or host.camera==null:return true
	var bounds:AABB=screen_mesh.mesh.get_aabb()
	var center:Vector3=screen_mesh.global_transform*bounds.get_center()
	if host.camera.global_position.distance_to(center)<2.:return true
	if host.camera.is_position_in_frustum(center):return true
	for corner in 8:
		if host.camera.is_position_in_frustum(screen_mesh.global_transform*bounds.get_endpoint(corner)):return true
	return false

func _process(dt:float)->void:
	if not _screen_in_camera():
		get_viewport().render_target_update_mode=SubViewport.UPDATE_DISABLED
		return
	timer-=dt
	if timer>0.:return
	timer=.1 if host.camera.global_position.distance_to(host.bodies.front.global_position)<50. else .5
	if kind==16:
		queue_redraw();get_viewport().render_target_update_mode=SubViewport.UPDATE_ONCE;return
	var front:RigidBody3D=host.bodies.front;var up:Vector3=front.global_basis.y
	if kind==12:
		# The first display frame may precede the first suspension physics step.
		if host.track_tension.tensions.is_empty():return
		var hitch:Array=host.samples[-1].hitch_coordinates if not host.samples.is_empty() else [0.,0.,0.,0.]
		var tension:float=host.track_tension.tensions.max()/1000.
		channels=[["SPEED",front.linear_velocity.dot(front.global_basis.x)*3.6,-20.,100.,"km/h"],["PITCH",rad_to_deg(asin(clampf(front.global_basis.x.y,-1.,1.))),-30.,30.,"deg"],["ROLL",rad_to_deg(atan2(front.global_basis.z.y,up.y)),-30.,30.,"deg"],["ARTICULATION",rad_to_deg(float(hitch[1])),-30.,30.,"deg"],["TRACK TENSION",tension,0.,600.,"kN"],["SUSP. PEAK",host.visual.maximum_wheel_stroke_m,0.,.35,"m"],["YAW RATE",rad_to_deg(front.angular_velocity.y),-15.,15.,"deg/s"],["ALLOC. POWER",float(host.samples[-1].allocated_drive_power_W)/1e6 if not host.samples.is_empty() else 0.,0.,200.,"MW"]]
	else:
		if host.equipment==null or host.lift_data.is_empty():return
		var c:Dictionary=host.equipment.rig.cranes[host.equipment.selected];var p:Dictionary=host.equipment.rig.panel;var lift:Dictionary=host.lift_data[host.selected_lift]
		var depth:=0.
		for i in range(1,4):depth+=host.coordinate(lift.groups[i]).x
		channels=[["CRANE SLEW",rad_to_deg(host.equipment.coordinate(c.slew).x),-170.,170.,"deg"],["BOOM",rad_to_deg(host.equipment.coordinate(c.luff).x),0.,35.,"deg"],["EXTENSION",host.equipment.extension(c),float(c.extension_range_m[0]),float(c.extension_range_m[1]),"m"],["WINCH PAID",host.equipment.paid[c.name],1.3,24.,"m"],["LIFT OUT",host.coordinate(lift.groups[0]).x,0.,2.7,"m"],["LIFT DEPTH",depth,0.,7.35,"m"],["ANTENNA YAW",rad_to_deg(host.equipment.coordinate(p.slew).x),-60.,60.,"deg"],["ANTENNA FOLD",rad_to_deg(host.equipment.coordinate(p.fold).x),-70.,10.,"deg"]]
	queue_redraw();get_viewport().render_target_update_mode=SubViewport.UPDATE_ONCE
func _draw()->void:
	if kind==16:
		_draw_status();return
	draw_rect(Rect2(0,0,2048,1024),Color(host.style.palette.cabin_console));var font:=ThemeDB.fallback_font
	var title:="TRACTION  /  VEHICLE ATTITUDE" if kind==12 else "HANDLING  /  CRANE %02d  /  LIFT %02d"%[host.equipment.selected+1,host.selected_lift+1]
	draw_string(font,Vector2(75,60),title,HORIZONTAL_ALIGNMENT_LEFT,-1,28,Color("D2D6CF"))
	draw_line(Vector2(75,82),Vector2(1973,82),Color("778087"),2.,true)
	for i in channels.size():
		var c:Array=channels[i];var center:=Vector2(256+(i%4)*512,307.2 if i<4 else 737.28);var r:=132.
		draw_circle(center,151.,Color("151B20"));draw_circle(center,r,Color("111A20"))
		# Small, legible divisions, heavier major marks and numeric calibration.
		for k in range(51):
			var t:float=deg_to_rad(135.+k*5.4);var dir:=Vector2(cos(t),sin(t));var major:bool=k%10==0
			draw_line(center+dir*(r-9),center+dir*(r-(26. if major else 17.)),Color("DEE0D4"),3. if major else 1.4,true)
			if major:
				var tick:float=lerpf(float(c[2]),float(c[3]),k/50.);var text:="%.1f"%tick if float(c[3])<=1. else "%.0f"%tick
				var pos:Vector2=center+dir*(r-42);var sz:Vector2=font.get_string_size(text,HORIZONTAL_ALIGNMENT_LEFT,-1,19)
				draw_string(font,pos-Vector2(sz.x*.5,-6.),text,HORIZONTAL_ALIGNMENT_LEFT,-1,19,Color("C1CEC6"))
		if i in [0,4,5] and kind==12:
			draw_arc(center,r-4,deg_to_rad(364.5),deg_to_rad(405),20,Color("C98F49"),4.,true)
		var angle:float=deg_to_rad(135.+clampf((float(c[1])-float(c[2]))/(float(c[3])-float(c[2])),0.,1.)*270.)
		var dir:=Vector2(cos(angle),sin(angle));var ortho:=Vector2(-dir.y,dir.x)
		draw_colored_polygon(PackedVector2Array([center-dir*22.-ortho*5.,center+dir*98.,center-dir*22.+ortho*5.]),Color("E5D5AE"))
		draw_circle(center,13.,Color("57636B"));draw_circle(center,7.,Color("BBC4BC"))
		var units:=str(c[4]);draw_string(font,center+Vector2(-27.,-34.),units,HORIZONTAL_ALIGNMENT_LEFT,90,21,Color("AAB7B6"))
		draw_rect(Rect2(center+Vector2(-58.,78.),Vector2(116.,28.)),Color("080E12"))
		var value:="%.2f"%float(c[1]);var vs:=font.get_string_size(value,HORIZONTAL_ALIGNMENT_LEFT,-1,21)
		draw_string(font,center+Vector2(-vs.x*.5,100.),value,HORIZONTAL_ALIGNMENT_LEFT,-1,21,Color("CDE0C8"))
		var label:=str(c[0]);var ls:=font.get_string_size(label,HORIZONTAL_ALIGNMENT_LEFT,-1,25)
		draw_string(font,center+Vector2(-ls.x*.5,193.),label,HORIZONTAL_ALIGNMENT_LEFT,-1,25,Color("D0D5CF"))
	draw_string(font,Vector2(75,990),"SAINIVERSE   /   NATIVE TELEMETRY    •    SI UNITS",HORIZONTAL_ALIGNMENT_LEFT,-1,22,Color("9EAFAE"))

func _draw_status()->void:
	var font:=ThemeDB.fallback_font
	draw_rect(Rect2(0,0,768,768),Color("101D23"))
	draw_string(font,Vector2(35,48),"SAINIVERSE  /  SYSTEM STATUS",HORIZONTAL_ALIGNMENT_LEFT,-1,26,Color("D0DDD0"))
	var moving:bool=host.bodies.front.linear_velocity.length()>.1
	var depth:=0.
	for item in host.lift_data:
		for i in range(1,4):depth=maxf(depth,absf(host.coordinate(item.groups[i]).x))
	var states:Array=[
		["PARK / STOP",host.cockpit.parking,"HOLD","RELEASED"],
		["SPEED RANGE",host.cockpit.axis("high_range")>.5,"HIGH","LOW"],
		["WORK MODE",host.equipment.working,"ACTIVE","STOW"],
		["LIFTS",depth>.04,"DEPLOYED","STOWED"],
		["CABIN ENTRY",host.doors_open,"OPEN","CLOSED"],
		["BOARDING",moving,"INHIBITED","AVAILABLE"]]
	for i in states.size():
		var state:Array=states[i];var y:=100.+i*96.;var active:bool=state[1]
		draw_rect(Rect2(32,y,704,79),Color("1D3036"));draw_circle(Vector2(57,y+39),8.,Color("D0A252") if active else Color("617F76"))
		draw_string(font,Vector2(82,y+44),str(state[0]),HORIZONTAL_ALIGNMENT_LEFT,-1,23,Color("ABBEB8"))
		draw_string(font,Vector2(450,y+44),str(state[2] if active else state[3]),HORIZONTAL_ALIGNMENT_LEFT,-1,24,Color("D0A252") if active else Color("B5D2BB"))
	draw_string(font,Vector2(36,738),"ACTUAL CONTROLS / NO TOUCH INPUT",HORIZONTAL_ALIGNMENT_LEFT,-1,20,Color("7D9996"))
