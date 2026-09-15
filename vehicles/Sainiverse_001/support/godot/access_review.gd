extends "@SAI_ROOT@/support/godot/atelier_review.gd"
## Actual finite motor/joint movement, never assigning door poses during a run.
var access_rays:Array=[]
var access_ray_results:Array=[]
func _build()->void:
	super._build()
	access_rays=JSON.parse_string(FileAccess.get_file_as_string(str(visual.config.access_manifest).get_base_dir()+"/access_probes.json"))
func _physics_process(dt:float)->bool:
	if access!=null:
		access.requests.fill(str(options.get("access_mode","parked"))=="cycle" and elapsed>=5. and elapsed<28.)
		if access_ray_results.size()<3 and elapsed>=[4.,24.,44.][access_ray_results.size()]:
			var results:Array=[]
			for ray in access_rays:
				var from:Vector3=bodies.front.global_transform*local_source(ray.start)
				var to:Vector3=bodies.front.global_transform*local_source(ray.end)
				var query:=PhysicsRayQueryParameters3D.create(from,to,8|32)
				var hit:Dictionary=root.world_3d.direct_space_state.intersect_ray(query)
				results.append({"name":ray.name,"kind":ray.kind,"expected_body":ray.body,"hit":not hit.is_empty(),"body":str(hit.collider.name) if not hit.is_empty() else "","distance_m":from.distance_to(hit.position) if not hit.is_empty() else -1.})
			access_ray_results.append({"time":elapsed,"angles_rad":access.angles.duplicate(),"rays":results})
	return super._physics_process(dt)

func _camera()->void:
	if not room_ready or str(options.get("view","whole"))!="doorway":super._camera();return
	camera.projection=Camera3D.PROJECTION_PERSPECTIVE;camera.fov=54.;camera.near=.025
	camera.global_position=bodies.front.global_transform*local_source([21.4,-7.6,13.15])
	camera.look_at(bodies.front.global_transform*local_source([19.15,-3.1,12.45]),bodies.front.global_basis.y)
	world_surface.position=Vector3(-origin.offset_x,0,-origin.offset_z)

func _write_visual_report()->void:
	super._write_visual_report()
	var record:Dictionary={"state":access.state(),"ray_results":access_ray_results,"door_names":access.names,"wall_and_fixture_shapes":spec.contact.interior.shapes.size(),"door_contact_shapes":[],"scope":"Native physical door bodies with finite drive torque and parked/closed drive interlocks. Wall/window/leaf/handle contacts enabled. Detailed hinge bearing contact is represented by joints. No actual robot boarding or pinch-safety qualification."}
	for door in spec.contact.access.doors:record.door_contact_shapes.append(door.collision.shapes.size())
	var file:=FileAccess.open(str(options.output_root)+"/"+str(options.output).get_basename()+"_access.json",FileAccess.WRITE);file.store_string(JSON.stringify(record,"  "));file.close()
	var interior_path:=str(options.output_root)+"/"+str(options.output).get_basename()+"_interior.json"
	var report:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(interior_path))
	report.scope="Actual mounted floor/fixture contacts queried in native physics. Hollow wall/window and physical moving-door contacts are included; see the access report for short-ray checks. Posed robot meshes are scale figures. Actual boarding and robot policies remain incomplete."
	file=FileAccess.open(interior_path,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close()
