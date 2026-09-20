extends RefCounted
## Explicit floor/furniture convex shapes, never a convex hull of a hollow room.
static func vec(a:Array)->Vector3:return Vector3(a[0],a[2],-a[1])
static func attach(body:CollisionObject3D,config:Dictionary)->int:
	var datum:Vector3=vec(config.datum_source_m)
	body.collision_layer=int(config.layer);body.collision_mask=int(config.mask)
	if not bool(config.get("preserve_body_material",false)):
		var material:=PhysicsMaterial.new();material.friction=float(config.get("friction_coefficient",.8));material.bounce=0.
		body.set("physics_material_override",material)
	for item in config.shapes:
		var node:=CollisionShape3D.new();node.name="contact_"+str(item.name)
		if item.type=="box":
			var shape:=BoxShape3D.new();shape.size=vec(item.size_m).abs();node.shape=shape;node.position=vec(item.center_source_m)-datum
		else:
			assert(item.type=="convex")
			var shape:=ConvexPolygonShape3D.new();var points:=PackedVector3Array()
			for p in item.vertices_source_m:points.append(vec(p)-datum)
			shape.points=points;node.shape=shape
		body.add_child(node)
	return config.shapes.size()
