extends SceneTree
const Tension=preload("@SAI_ROOT@/support/godot/track_tension.gd")
func _initialize()->void:
	var args:=OS.get_cmdline_user_args();var input:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(args[0]));var bank=Tension.new();bank.configure(input.config);var result:Array=[]
	for fixture in input.fixtures:
		bank.step(fixture.q,fixture.dq,.005);result.append({"forces":bank.forces.duplicate(),"state":bank.state()})
	var file:=FileAccess.open(args[1],FileAccess.WRITE);file.store_string(JSON.stringify(result));file.close();print("TRACK_COMPONENT_COMPLETE");quit()
