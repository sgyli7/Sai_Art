extends "res://robot_sai60.gd"
## Isolated 60 Hz leg plant; no legacy torque-PD correction.
func apply_command(state: Dictionary, next_command: Dictionary) -> void:
	super.apply_command(state, next_command)
