extends RefCounted
## Clockwise tangent/arc path, starting at the original upper-left point.
static func build(wheels:Array,travel:Vector3,idler:float)->Dictionary:
	var w:Array=[]
	for v in wheels:w.append(Vector3(v[0],v[1],float(v[2])+.09))
	for i in 3:w[i+1].y+=travel[i]
	w[4].x+=idler
	var upper:float=PI*.5;var lower:float=upper-TAU;var angles:Array=[upper,lower]
	for i in 5:
		for j in i:
			var dx:float=w[i].x-w[j].x;var dz:float=w[i].y-w[j].y;var distance:float=sqrt(dx*dx+dz*dz)
			if distance<=absf(w[j].z-w[i].z):continue
			var a:float=atan2(dz,dx);var b:float=acos((w[j].z-w[i].z)/distance)
			angles.append(lower+fposmod(a-b-lower,TAU));angles.append(lower+fposmod(a+b-lower,TAU))
	angles.sort();angles.reverse()
	var arcs:Array=[]
	for k in angles.size()-1:
		var a:float=angles[k];var b:float=angles[k+1]
		if a-b<1e-10:continue
		var mid:float=(a+b)*.5;var owner:=0;var support:=-INF;var nx:float=cos(mid);var nz:float=sin(mid)
		for i in 5:
			var value:float=w[i].x*nx+w[i].y*nz+w[i].z
			if value>support:owner=i;support=value
		if not arcs.is_empty() and arcs[-1][0]==owner:arcs[-1][2]=b
		else:arcs.append([owner,a,b])
	var first:Array=[];var second:Array=[];var total:=0.0
	for index in arcs.size():
		var arc:Array=arcs[index];var previous:Array=arcs[(index+arcs.size()-1)%arcs.size()]
		var c:Vector3=w[arc[0]];var p:Vector3=w[previous[0]];var angle:float=arc[1];var n:=Vector2(cos(angle),sin(angle))
		var start:=Vector2(p.x,p.y)+p.z*n;var end:=Vector2(c.x,c.y)+c.z*n;var length:float=start.distance_to(end)
		if length>1e-8:
			first.append(Vector4(start.x,start.y,end.x,end.y));second.append(Vector4(length,0,0,0));total+=length
		length=c.z*(float(arc[1])-float(arc[2]))
		first.append(Vector4(c.x,c.y,c.z,arc[1]));second.append(Vector4(length,float(arc[2])-float(arc[1]),1,0));total+=length
	assert(first.size()<=16)
	var count:int=first.size()
	while first.size()<16:first.append(Vector4.ZERO);second.append(Vector4.ZERO)
	return {"a":PackedVector4Array(first),"b":PackedVector4Array(second),"length":total,"count":count}
