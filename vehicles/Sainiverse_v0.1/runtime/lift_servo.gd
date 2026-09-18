extends RefCounted
## Backward-Euler PD for a telescopic serial mast. Units: kg, m, s, N.
## Each vertical joint accelerates its descendants; treating stages independently
## makes the alternating mode unstable when an interactive tick becomes 10 ms.
static func efforts(states:Array,targets:Array,masses:Array,payload:float,dt:float)->Array:
	const K:=80000.
	const D:=14000.
	var m3:float=float(masses[3])+payload
	var m2:float=float(masses[2])+m3
	var m1:float=float(masses[1])+m2
	var mass:=Basis(Vector3(m1,m2,m3),Vector3(m2,m2,m3),Vector3(m3,m3,m3))
	var diagonal:float=dt*D+dt*dt*K
	var implicit:=Basis(mass.x+Vector3(diagonal,0,0),mass.y+Vector3(0,diagonal,0),mass.z+Vector3(0,0,diagonal))
	var error:=Vector3(float(targets[1])-states[1].x,float(targets[2])-states[2].x,float(targets[3])-states[3].x)
	var velocity:=Vector3(states[1].y,states[2].y,states[3].y)
	var force:Vector3=mass*(implicit.inverse()*(K*error-(D+dt*K)*velocity))
	var horizontal_mass:float=float(masses[0])+m1
	var horizontal:float=(K*(float(targets[0])-states[0].x)-(D+dt*K)*states[0].y)/(1.+(D*dt+K*dt*dt)/horizontal_mass)
	return [horizontal,force.x,force.y,force.z]
