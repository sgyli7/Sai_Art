extends SceneTree
const PathBuilder=preload("@SAI_ROOT@/support/godot/track_path.gd")
const OUT="@SAI_ROOT@/support/candidates/r022_runtime"
func _initialize()->void:
	var status:=GDExtensionManager.load_extension(OUT+"/native/leviathan_track_path.gdextension")
	assert(status==GDExtensionManager.LOAD_STATUS_OK)
	var core=ClassDB.instantiate("LeviathanTrackPath")
	var binding:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(OUT+"/bindings.json"));var wheels:Array=binding.gear.wheels_x_z_radius
	var rng:=RandomNumberGenerator.new();rng.seed=219022
	var errors:=Vector3.ZERO;var native_usec:=0;var script_usec:=0
	for i in 3000:
		var q:=Vector3(rng.randf_range(-.35,.35),rng.randf_range(-.35,.35),rng.randf_range(-.35,.35));var idler:=rng.randf_range(-.32,.24)
		if i<16:
			q=Vector3(.35 if i&1 else -.35,.35 if i&2 else -.35,.35 if i&4 else -.35);idler=.24 if i&8 else -.32
		var start:=Time.get_ticks_usec();var a:Dictionary=PathBuilder.build(wheels,q,idler);script_usec+=Time.get_ticks_usec()-start
		start=Time.get_ticks_usec();var b:Dictionary=core.build(wheels,q,idler);native_usec+=Time.get_ticks_usec()-start
		assert(a.count==b.count)
		errors.x=maxf(errors.x,absf(a.length-b.length))
		for k in 16:
			for j in 4:
				errors.y=maxf(errors.y,absf(a.a[k][j]-b.a[k][j]));errors.z=maxf(errors.z,absf(a.b[k][j]-b.b[k][j]))
	var passed:bool=maxf(errors.x,maxf(errors.y,errors.z))<3e-6
	var report:Dictionary={"cases":3000,"seed":219022,"length_error_m":errors.x,"segment_a_max_error":errors.y,"segment_b_max_error":errors.z,"script_total_usec":script_usec,"native_total_usec":native_usec,"passed":passed,"scope":"Same current wheel radii; all 16 coordinate corners plus seeded independent wheel/idler positions. Same exact arc/tangent algorithm, float32 vectors and float64 scalar math. Pure geometry only."}
	var file:=FileAccess.open(OUT+"/reports/native_path_equivalence.json",FileAccess.WRITE);file.store_string(JSON.stringify(report,"  "));file.close();print(JSON.stringify(report));core=null;quit(0 if passed else 1)
