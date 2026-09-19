extends CanvasLayer
## Foldable mouse control surface. Every command feeds the same physical
## cockpit joints used by keyboard input and future robot manipulation.

var host:SceneTree
var root_panel:PanelContainer
var body:VBoxContainer
var scroll:ScrollContainer
var status:Label
var sections:Dictionary={}
var section_headers:Dictionary={}
var controls:Dictionary={}
var events:Array=[]
var crane_status:Label
var lift_status:Label
var throttle:HSlider
var steering:HSlider
var brake:HSlider
var time_scale_slider:HSlider
var high_range:CheckButton
var panel_collapsed:=false
var ui_test_phase:=-1
var font:SystemFont

const BG=Color(0.045,0.052,0.060,.94)
const CARD=Color(0.075,0.085,0.095,.96)
const EDGE=Color(0.31,0.34,0.35,1.)
const TEXT=Color("E3E5DE")
const MUTED=Color("9BA39F")
const YELLOW=Color("D8A92E")
const RED=Color("C52232")

func configure(h:SceneTree)->void:
	host=h;layer=20;Engine.time_scale=1.;font=SystemFont.new();font.font_names=PackedStringArray(["Noto Sans CJK SC","Noto Sans CJK JP"])
	_build_ui();visible=str(host.options.get("clean_capture","false"))!="true"

func _style(color:Color,radius:=6,border:=0)->StyleBoxFlat:
	var s:=StyleBoxFlat.new();s.bg_color=color;s.corner_radius_top_left=radius;s.corner_radius_top_right=radius;s.corner_radius_bottom_left=radius;s.corner_radius_bottom_right=radius
	s.content_margin_left=10;s.content_margin_right=10;s.content_margin_top=7;s.content_margin_bottom=7
	if border>0:s.border_width_left=border;s.border_width_right=border;s.border_width_top=border;s.border_width_bottom=border;s.border_color=EDGE
	return s

func _label(text:String,size:=14,color:=TEXT)->Label:
	var l:=Label.new();l.text=text;l.add_theme_font_override("font",font);l.add_theme_font_size_override("font_size",size);l.add_theme_color_override("font_color",color);return l

func _button(text:String)->Button:
	var b:=Button.new();b.text=text;b.focus_mode=Control.FOCUS_NONE;b.custom_minimum_size=Vector2(0,34);b.add_theme_font_override("font",font);b.add_theme_font_size_override("font_size",13)
	b.add_theme_stylebox_override("normal",_style(Color(.11,.12,.13,.98),5,1));b.add_theme_stylebox_override("hover",_style(Color(.16,.17,.18,.98),5,1));b.add_theme_stylebox_override("pressed",_style(Color(.28,.20,.06,.98),5,1));return b

func _row()->HBoxContainer:
	var r:=HBoxContainer.new();r.add_theme_constant_override("separation",7);return r

func _build_ui()->void:
	root_panel=PanelContainer.new();root_panel.position=Vector2(20,20);root_panel.custom_minimum_size=Vector2(392,0);root_panel.add_theme_stylebox_override("panel",_style(BG,9,1));add_child(root_panel)
	var outer:=VBoxContainer.new();outer.add_theme_constant_override("separation",7);root_panel.add_child(outer)
	var header:=_row();outer.add_child(header)
	var collapse:=_button("SAINIVERSE_v0.1  ▾");collapse.size_flags_horizontal=Control.SIZE_EXPAND_FILL;collapse.alignment=HORIZONTAL_ALIGNMENT_LEFT;collapse.pressed.connect(func():panel_collapsed=not panel_collapsed;scroll.visible=not panel_collapsed;collapse.text="SAINIVERSE_v0.1  "+("▸" if panel_collapsed else "▾"));header.add_child(collapse)
	var quit:=_button("退出");quit.custom_minimum_size.x=58;quit.pressed.connect(_quit);header.add_child(quit)
	status=_label("SYSTEM ONLINE",14,MUTED);status.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;outer.add_child(status)
	scroll=ScrollContainer.new();scroll.custom_minimum_size=Vector2(370,0);scroll.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED;outer.add_child(scroll)
	body=VBoxContainer.new();body.size_flags_horizontal=Control.SIZE_EXPAND_FILL;body.add_theme_constant_override("separation",6);scroll.add_child(body)
	_build_drive();_build_robots();_build_crane();_build_lifts();_build_receiver();_build_view();_build_services();_build_help()

func _section(id:String,title:String,open:=false)->VBoxContainer:
	var card:=VBoxContainer.new();card.add_theme_constant_override("separation",6);body.add_child(card)
	var head:=_button(("▾ " if open else "▸ ")+title);head.alignment=HORIZONTAL_ALIGNMENT_LEFT;head.set_meta("title",title);card.add_child(head)
	var content:=VBoxContainer.new();content.visible=open;content.add_theme_constant_override("separation",6);content.add_theme_stylebox_override("panel",_style(CARD,6,1));card.add_child(content)
	head.pressed.connect(_toggle_section.bind(id,title))
	sections[id]=content;section_headers[id]=head;return content

func _toggle_section(id:String,title:String)->void:
	var opening:bool=not sections[id].visible
	for key in sections:
		sections[key].visible=false
		section_headers[key].text="▸ "+str(section_headers[key].get_meta("title",key))
	sections[id].visible=opening
	section_headers[id].text=("▾ " if opening else "▸ ")+title

func _slider_row(parent:VBoxContainer,label:String,minimum:float,maximum:float,step:float)->HSlider:
	var l:=_label(label,12,MUTED);parent.add_child(l);var s:=HSlider.new();s.min_value=minimum;s.max_value=maximum;s.step=step;s.custom_minimum_size=Vector2(0,24);s.focus_mode=Control.FOCUS_NONE;parent.add_child(s);return s

func _hold_pair(parent:VBoxContainer,label:String,left:String,right:String,axis:String)->void:
	parent.add_child(_label(label,12,MUTED));var r:=_row();parent.add_child(r)
	var a:=_button(left);var b:=_button(right);a.size_flags_horizontal=Control.SIZE_EXPAND_FILL;b.size_flags_horizontal=Control.SIZE_EXPAND_FILL;r.add_child(a);r.add_child(b)
	controls[axis+"_negative"]=a;controls[axis+"_positive"]=b
	a.button_down.connect(_axis.bind(axis,-1.));a.button_up.connect(_axis.bind(axis,0.));a.mouse_exited.connect(_release_axis.bind(axis))
	b.button_down.connect(_axis.bind(axis,1.));b.button_up.connect(_axis.bind(axis,0.));b.mouse_exited.connect(_release_axis.bind(axis))

func _build_drive()->void:
	var c:=_section("drive","驾驶 DRIVE",false)
	throttle=_slider_row(c,"油门 / 倒车",-1,1,.05);throttle.value_changed.connect(func(v):_axis("throttle",v))
	steering=_slider_row(c,"转向",-1,1,.05);steering.value_changed.connect(func(v):_axis("steer",v))
	brake=_slider_row(c,"制动",0,1,.05);brake.value_changed.connect(func(v):_axis("brake",v))
	var center:=_button("方向与油门回中");center.pressed.connect(func():throttle.value=0;steering.value=0);c.add_child(center)
	high_range=CheckButton.new();high_range.text="高速挡";high_range.add_theme_font_override("font",font);high_range.toggled.connect(func(on):_axis("high_range",1. if on else 0.));c.add_child(high_range)
	var r:=_row();c.add_child(r)
	for item in [["驻车制动","emergency"],["作业模式","work"]]:
		var b:=_button(item[0]);b.size_flags_horizontal=Control.SIZE_EXPAND_FILL;b.pressed.connect(_pulse.bind(str(item[1])));controls[str(item[1])]=b;r.add_child(b)

func _build_robots()->void:
	var c:=_section("robots","驾驶对象 ROBOTS",false)
	for item in [["F9 · Sainiverse","vehicle"],["F5 · MicroDuck","microduck"],["F6 · MD 轮滑","roller"],["F7 · Sai 001","sai001"],["F8 · Sai 002","sai002"]]:
		var button:=_button(item[0]);button.pressed.connect(host.select_robot_mode.bind(item[1]));c.add_child(button)
	c.add_child(_label("停车后切换；机器人控制器使用各自已验证的物理频率。",12,MUTED))

func _build_crane()->void:
	var c:=_section("crane","吊机 CRANE",false)
	var select:=OptionButton.new();select.add_theme_font_override("font",font);select.custom_minimum_size.y=36
	for i in host.equipment.rig.cranes.size():
		var crane:Dictionary=host.equipment.rig.cranes[i];select.add_item(("前拖车" if crane.hull=="rear" else "后拖车")+"  Crane "+str(i%4+1),i)
	select.item_selected.connect(_select_crane);controls["crane_select"]=select;c.add_child(select)
	crane_status=_label("",12,MUTED);c.add_child(crane_status)
	_hold_pair(c,"回转 SLEW","◀ 左转","右转 ▶","crane_slew")
	_hold_pair(c,"变幅 BOOM","▼ 降臂","升臂 ▲","crane_luff")
	_hold_pair(c,"伸缩 TELESCOPE","− 收缩","伸出 +","crane_extend")
	_hold_pair(c,"卷扬 WINCH","▼ 放绳","收绳 ▲","crane_winch")
	var hook:=_button("挂钩 / 落地释放");hook.add_theme_color_override("font_color",YELLOW);hook.pressed.connect(func():_pulse("cargo"));c.add_child(hook)

func _build_lifts()->void:
	var c:=_section("lifts","升降平台 LIFTS",false);var select:=OptionButton.new();select.add_theme_font_override("font",font);select.custom_minimum_size.y=36
	for i in host.lift_data.size():select.add_item(["主控左","主控右","前拖左","前拖右","后拖左","后拖右"][i],i)
	select.item_selected.connect(_select_lift);c.add_child(select);lift_status=_label("",12,MUTED);c.add_child(lift_status)
	var r:=_row();c.add_child(r)
	for item in [["当前平台 升/降","lift"],["全部平台 升/降","lifts_all"]]:
		var b:=_button(item[0]);b.size_flags_horizontal=Control.SIZE_EXPAND_FILL;b.pressed.connect(_pulse.bind(str(item[1])));controls[str(item[1])]=b;r.add_child(b)
	controls["lift_select"]=select

func _build_receiver()->void:
	var c:=_section("receiver","接收板 RECEIVER",false)
	_hold_pair(c,"天线回转","◀ 左转","右转 ▶","panel_slew")
	_hold_pair(c,"折叠机构","▼ 折叠","展开 ▲","panel_fold")

func _build_view()->void:
	var c:=_section("view","视角与外观 VIEW",false);var views:=OptionButton.new();views.add_theme_font_override("font",font)
	time_scale_slider=_slider_row(c,"时间流速 0.1×～3.0×（默认 1.0×）",.1,3.,.1)
	time_scale_slider.value=1.;time_scale_slider.value_changed.connect(func(v):Engine.time_scale=clampf(v,.1,3.))
	for i in host.camera_names.size():views.add_item(host.camera_names[i],i)
	views.item_selected.connect(_select_view);views.select(host.cam_mode);controls["view_select"]=views;c.add_child(views)
	var themes:=OptionButton.new();themes.add_theme_font_override("font",font)
	for i in ["black","desert","white","blue","yellow"]:themes.add_item(i.capitalize())
	themes.select(["black","desert","white","blue","yellow"].find(host.theme_id));themes.item_selected.connect(_select_theme);controls["theme_select"]=themes;c.add_child(themes)
	var snap:=_button("保存截图");snap.pressed.connect(func():host._capture("ui_"+str(Time.get_ticks_msec())));c.add_child(snap)

func _build_services()->void:
	var c:=_section("services","舱体与服务 SERVICES",false);var r:=_row();c.add_child(r)
	for item in [["舱门 开/关","doors"],["全部收起 / 作业","work"]]:
		var b:=_button(item[0]);b.size_flags_horizontal=Control.SIZE_EXPAND_FILL;b.pressed.connect(_pulse.bind(str(item[1])));controls[str(item[1])]=b;r.add_child(b)

func _build_help()->void:
	var c:=_section("help","帮助 HELP",false)
	var help:=_label("鼠标：展开分组、选择设备、拖动驾驶滑杆；吊机按钮需按住。\nF5/F6/F7/F8 切换机器人，F9 返回母车；停车后切换。\nW/S 前后行驶，A/D 转向；右键环视 · 滚轮缩放 · Tab 切换视角。",12,MUTED);help.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;c.add_child(help)

func captures_point(point:Vector2)->bool:return visible and root_panel.get_global_rect().has_point(point)

func _record(action:String,value)->void:events.append({"time":host.elapsed,"action":action,"value":value})
func _axis(id:String,value:float)->void:host.cockpit.ui_axes[id]=value;_record(id,value)
func _release_axis(id:String)->void:
	_axis(id,0.)
func _pulse(id:String)->void:host.cockpit.pulse(id);_record(id,"pulse")
func _select_crane(index:int)->void:
	host.equipment.selected=index;host.cockpit.targets.crane_select=2.45*index/7.;host.cockpit.ui_selected_crane=index;_record("select_crane",index)
func _select_lift(index:int)->void:
	host.selected_lift=index;host.cockpit.targets.lift_select=2.50*index/5.;host.cockpit.ui_selected_lift=index;_record("select_lift",index)
func _select_view(index:int)->void:host.set_camera_mode(index);_record("camera",index)
func _select_theme(index:int)->void:
	var ids=["black","desert","white","blue","yellow"];host.set_theme_id(ids[index]);_record("theme",ids[index])
func _quit()->void:host.options.seconds=host.elapsed+.02;host.manual=false;host.options.speed=0.;Engine.time_scale=1.;_record("quit",true)

func refresh()->void:
	if host==null or not host.camera_ready:return
	if str(host.options.get("mode",""))=="ui_test":_exercise_routes()
	# Stay compact while sections are folded, then cap the open menu to the
	# viewport so every control remains reachable by scrolling at 720p.
	var desired:=body.get_combined_minimum_size().y
	scroll.custom_minimum_size.y=minf(desired,clampf(get_viewport().get_visible_rect().size.y-150.,360.,760.))
	var speed:float=host.bodies.front.linear_velocity.dot(host.bodies.front.global_basis.x)*3.6
	var robot_label:String={"vehicle":"Sainiverse","microduck":"MicroDuck","roller":"MD 轮滑","sai001":"Sai 001","sai002":"Sai 002"}.get(host.active_robot_kind,"Sainiverse")
	var state_text:String=host.robot_switch_message if host.robot_switch_message!="" else "联锁：车门未锁妥" if host.active_robot_kind=="vehicle" and host.access!=null and not host.access.drive_permitted else "联锁：设备未收起" if host.active_robot_kind=="vehicle" and host.drive_interlock else "当前控制："+robot_label
	status.text="%5.1f km/h   %s   %.0f FPS · %.1f×\n%s"%[speed,host.camera_names[host.cam_mode],Engine.get_frames_per_second(),Engine.time_scale,state_text]
	if crane_status!=null:
		var c:Dictionary=host.equipment.rig.cranes[host.equipment.selected]
		crane_status.text="Crane %d/8 · %s\n回转 %+.1f°  俯仰 %.1f°\n伸长 %.2f m  吊绳 %.2f m%s"%[host.equipment.selected+1,"作业已启用" if host.equipment.working else "请先启用作业模式",rad_to_deg(host.equipment.coordinate(c.slew).x),rad_to_deg(host.equipment.coordinate(c.luff).x),host.equipment.extension(c),host.equipment.paid[c.name]," · 已挂载" if host.cargo.attached_crane==host.equipment.selected else ""]
	if lift_status!=null:
		var lift:Dictionary=host.lift_data[host.selected_lift];var depth:=0.
		for i in range(1,4):depth+=host.coordinate(lift.groups[i]).x
		lift_status.text="平台 %d/6 · %s · 深度 %.2f m"%[host.selected_lift+1,"下降请求" if host.lift_commands[lift.name] else "收起请求",depth]

func _exercise_routes()->void:
	var phase:=int(host.elapsed)
	if phase==ui_test_phase:return
	ui_test_phase=phase
	match phase:
		1:_toggle_section("drive","驾驶 DRIVE")
		2:(controls["work"] as Button).pressed.emit()
		3:_toggle_section("crane","吊机 CRANE")
		4:
			var selector:=controls["crane_select"] as OptionButton;selector.select(5);selector.item_selected.emit(5)
		5:(controls["crane_slew_positive"] as Button).button_down.emit()
		6:(controls["crane_slew_positive"] as Button).button_up.emit()
		7:(controls["crane_luff_positive"] as Button).button_down.emit()
		8:(controls["crane_luff_positive"] as Button).button_up.emit()
		9:(controls["crane_extend_positive"] as Button).button_down.emit()
		10:(controls["crane_extend_positive"] as Button).button_up.emit()
		11:(controls["crane_winch_negative"] as Button).button_down.emit()
		12:(controls["crane_winch_negative"] as Button).button_up.emit()
		13:throttle.value=.4;steering.value=-.3;brake.value=.2
		14:throttle.value=0.;steering.value=0.;brake.value=0.
		15:
			var selector:=controls["lift_select"] as OptionButton;selector.select(3);selector.item_selected.emit(3)
		16:(controls["lift"] as Button).pressed.emit()
		17:(controls["panel_slew_positive"] as Button).button_down.emit()
		18:(controls["panel_slew_positive"] as Button).button_up.emit();(controls["panel_fold_negative"] as Button).button_down.emit()
		19:(controls["panel_fold_negative"] as Button).button_up.emit()
		20:
			var selector:=controls["view_select"] as OptionButton;selector.select(1);selector.item_selected.emit(1)
		21:
			var selector:=controls["theme_select"] as OptionButton;selector.select(3);selector.item_selected.emit(3)
		22:(controls["doors"] as Button).pressed.emit()
		23:(controls["emergency"] as Button).pressed.emit()

func report()->Dictionary:
	return {"foldable_sections":sections.keys(),"cranes":host.equipment.rig.cranes.size(),"lifts":host.lift_data.size(),"events":events,"scope":"Mouse UI dispatches through the same finite physical cockpit controls; automated signal coverage does not replace human usability review."}
