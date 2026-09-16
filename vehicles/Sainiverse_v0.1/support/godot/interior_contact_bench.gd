extends SceneTree
const Contacts=preload("@SAI_ROOT@/support/godot/interior_contacts.gd")
var probes:Array=[]
var count:=0
var output:String
var config:Dictionary
func _initialize()->void:
	var args:=OS.get_cmdline_user_args();config=JSON.parse_string(FileAccess.get_file_as_string(args[0]));output=args[1]
	Engine.physics_ticks_per_second=200
	call_deferred("_build")
func _build()->void:
	var stage:=Node3D.new();root.add_child(stage)
	var floor_body:=StaticBody3D.new();stage.add_child(floor_body);floor_body.position=Contacts.vec(config.contact.datum_source_m)
	Contacts.attach(floor_body,config.contact)
	for point in config.points:
		var body:=RigidBody3D.new();body.mass=.05;body.collision_layer=16;body.collision_mask=8;body.can_sleep=false;body.linear_damp=0.;body.angular_damp=0.
		body.position=Contacts.vec(point)+Vector3.UP*.09
		var shape:=CollisionShape3D.new();var sphere:=SphereShape3D.new();sphere.radius=.02;shape.shape=sphere;body.add_child(shape);stage.add_child(body);probes.append(body)
func _physics_process(_dt:float)->bool:
	if probes.is_empty():return false
	count+=1
	if count<600:return false
	var states:Array=[]
	for i in probes.size():
		var body:RigidBody3D=probes[i];states.append({"source_position":[body.position.x,-body.position.z,body.position.y],"velocity_m_s":body.linear_velocity.length(),"height_error_m":body.position.y-float(config.points[i][2])-.02})
	var f:=FileAccess.open(output,FileAccess.WRITE);f.store_string(JSON.stringify({"samples":states,"physics_hz":200,"gravity_m_s2":ProjectSettings.get_setting("physics/3d/default_gravity",9.8),"scope":"Static authored cabin floor/fixture contact component, 50 g sphere probes. No robot locomotion or moving-carrier load transfer."},"  "));f.close();print("INTERIOR_CONTACT_PROBES_COMPLETE");quit();return false
