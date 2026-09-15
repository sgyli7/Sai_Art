extends SceneTree
const ROOT="@SAI_ROOT@/support"
const Hydraulic=preload("@SAI_ROOT@/support/godot/hydraulic_suspension.gd")
func _initialize()->void:
	var manifest:Dictionary=JSON.parse_string(FileAccess.get_file_as_string(ROOT+"/candidates/r020_hydraulics/physics/parameters.json"));var output:Dictionary={}
	for fixture in [["slow_closed",.05,.5,0.],["pressure_limits",.35,5.,1.5e6],["pump_limit",.35,5.,1e5]]:
		var c:Dictionary=manifest.hydraulics.duplicate(true);c.pump_power_limit_W=fixture[3]
		if fixture[0]=="slow_closed":c.level_flow_gain_m2_s=0.
		var h=Hydraulic.new();h.configure(c);var samples:Array=[]
		for i in 4001:
			var time:float=i*.005;var q:Array=[];var dq:Array=[]
			for j in 72:
				q.append(float(fixture[1])*sin(TAU*float(fixture[2])*time));dq.append(float(fixture[1])*TAU*float(fixture[2])*cos(TAU*float(fixture[2])*time))
			h.step(q,dq,.005)
			if i%20==0:samples.append(h.state())
		output[fixture[0]]=samples
	var f:=FileAccess.open(ROOT+"/candidates/r020_hydraulics/reports/component_godot.json",FileAccess.WRITE);f.store_string(JSON.stringify(output,"  "));f.close();print("HYDRAULIC_COMPONENT_COMPLETE");quit()
