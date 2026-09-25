extends RigidBody3D
var last_contact_impulse_Ns := 0.0
var last_contact_count := 0
var last_contact_bodies: Array = []
var last_contact_points: Array = []
func _integrate_forces(state: PhysicsDirectBodyState3D) -> void:
	last_contact_count=state.get_contact_count()
	last_contact_impulse_Ns=0.0
	last_contact_bodies.clear()
	last_contact_points.clear()
	for i in range(last_contact_count):
		last_contact_impulse_Ns+=state.get_contact_impulse(i).length()
		var other=state.get_contact_collider_object(i)
		last_contact_bodies.append(str(other.name) if other is Node else str(other))
		var point=state.get_contact_local_position(i)
		last_contact_points.append([point.x,point.y,point.z])
