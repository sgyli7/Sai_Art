extends SceneTree
class FakePatrol extends Node:
	var taps:Array=[]
	func _add_tap(action:String)->void:taps.append(action)
	func set_destination(_destination:Dictionary)->void:pass

var options := {"clean_capture":false,"mode":"manual"}
var equipment := {"rig":{"cranes":[{"hull":"rear"}]}}
var lift_data := []
var camera_names := ["整车环视"]
var cam_mode := 0
var theme_id := "black"
var active_robot_kind := "microduck"
var camera_ready := true
var bodies := {"front":RigidBody3D.new()}
var robot_switch_message := ""
var access = null
var drive_interlock := false
var elapsed := 0.0
var patrol:=FakePatrol.new()
var travel_requests:Array=[]
var switch_requests:Array=[]

func select_robot_mode(kind:String)->void:switch_requests.append(kind)
func quick_travel(index:int)->void:travel_requests.append(index)
func set_camera_mode(_index:int)->void:pass
func set_theme_id(_id:String)->void:pass
func _initialize()->void:call_deferred("_run")

func _find_button(node:Node,title:String)->Button:
	if node is Button and node.text==title:return node
	for child in node.get_children():
		var found:=_find_button(child,title)
		if found!=null:return found
	return null

func _run()->void:
	root.add_child(bodies.front)
	root.add_child(patrol)
	var ui=load("res://operation_ui.gd").new()
	root.add_child(ui)
	ui.configure(self)
	ui.crane_status=null
	ui.lift_status=null
	ui.refresh()
	var vehicle_card:Control=ui.sections["drive"].get_parent()
	var help:Label=ui.sections["help"].get_child(0)
	if not vehicle_card.visible or not ui.sections["drive"].visible:
		printerr("FAIL: vehicle drive controls are hidden while MicroDuck is active")
		quit(1);return
	if not help.text.contains("捡地") or not help.text.contains("方向键"):
		printerr("FAIL: simultaneous MicroDuck and carrier control hints are absent")
		quit(1);return
	ui._toggle_section("robots","驾驶对象 ROBOTS")
	if not ui.sections["drive"].visible or not ui.sections["robot_controls"].visible:
		printerr("FAIL: opening another section hides simultaneous controls")
		quit(1);return
	var forward:=_find_button(ui.sections["robot_controls"],"前进 W")
	if forward==null:
		printerr("FAIL: MicroDuck has no clickable forward control")
		quit(1);return
	forward.button_down.emit();Input.flush_buffered_events()
	if not Input.is_physical_key_pressed(KEY_W):
		printerr("FAIL: robot forward button does not press W")
		quit(1);return
	forward.button_up.emit();Input.flush_buffered_events()
	if Input.is_physical_key_pressed(KEY_W):
		printerr("FAIL: robot forward button remains held after release")
		quit(1);return
	var deck:=_find_button(ui.sections["robot_controls"],"F2 甲板")
	deck.pressed.emit()
	if travel_requests!=[2]:
		printerr("FAIL: deck quick-travel button did not dispatch")
		quit(1);return
	var pick:=_find_button(ui.sections["robot_controls"],"捡地 1")
	pick.pressed.emit()
	if patrol.taps!=["pick"]:
		printerr("FAIL: MicroDuck skill button did not reach its controller")
		quit(1);return
	active_robot_kind="roller";ui.refresh()
	if not help.text.contains("下蹲滑行") or not vehicle_card.visible:
		printerr("FAIL: roller-specific controls are absent")
		quit(1);return
	active_robot_kind="sai001";ui.refresh()
	if not help.text.contains("Sai Robot") or not help.text.contains("方向键") or not vehicle_card.visible or not ui.sections["drive"].visible or pick.visible:
		printerr("FAIL: Sai Robot and vehicle controls are not visible together")
		quit(1);return
	active_robot_kind="sai002";ui.refresh()
	if not ui.mode_hint.text.contains("Sai 002") or not vehicle_card.visible or not ui.sections["drive"].visible:
		printerr("FAIL: Sai 002 and vehicle controls are not visible together")
		quit(1);return
	active_robot_kind="vehicle";ui.refresh()
	if not vehicle_card.visible or not ui.sections["drive"].visible or ui.sections["robot_controls"].get_parent().visible:
		printerr("FAIL: vehicle controls do not return with Sainiverse")
		quit(1);return
	print("PASS: UI routes robot input, travel, and per-robot hints")
	quit(0)
