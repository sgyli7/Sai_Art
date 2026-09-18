# R033 cargo attachment references

Date: 2026-09-17. Scope: native Godot suspended-container attach/lift/release and a legible spreader. Research only; no runtime/source changes. Local `godot --version` reports `4.7.2.stable.official.ed1daf0bf`; `Leviathan_001/godot/project.godot` selects Jolt Physics. Engine source below is pinned to 4.7.2-stable.

## Joint choice and frames

- `PinJoint3D` joins one point on each body while permitting free relative rotation; the official example is a pendulum. It is suitable for the suspension pivot, but alone does not represent a spreader's rotation-resistant grip. [Godot PinJoint3D](https://docs.godotengine.org/en/stable/classes/class_pinjoint3d.html)
- Pin configuration takes the joint's **global origin** and converts that same point through each body's `to_local()`. Thus a joint created halfway between separated contact points does not pull those intended points together: it captures different offsets at its own current location. Position bodies/contact frames before attachment. A pin is not a variable-length rope. [PinJoint3D source, `_configure_joint`](https://raw.githubusercontent.com/godotengine/godot/4.7.2-stable/scene/3d/physics/joints/pin_joint_3d.cpp)
- `Generic6DOFJoint3D` captures full frames: `body.global_transform.affine_inverse() * joint.global_transform`, then orthonormalizes them. Its constructor enables linear and angular limits with zero lower/upper limits on all axes. An explicit six-axis lock can represent the aggregate spreader/container grip; keep pendulum freedom in an upstream suspension body/joint. Node-level methods are `set_param_x/y/z` and `set_flag_x/y/z`, whereas the server API takes an axis argument. [Generic6DOFJoint3D source](https://raw.githubusercontent.com/godotengine/godot/4.7.2-stable/scene/3d/physics/joints/generic_6dof_joint_3d.cpp)

## Live lifecycle cautions

`Joint3D` configures on entering the tree and changing body paths. Its notification handler does not rebuild anchors on transform change. Set the joint pose before assigning its bodies; moving the configured joint node is not a winch. Setting an unchanged body path returns immediately. Exiting the tree clears the constraint, removes its pair collision exceptions, and destruction frees the joint RID. [Joint3D source](https://raw.githubusercontent.com/godotengine/godot/4.7.2-stable/scene/3d/physics/joints/joint_3d.cpp)

Both paths must resolve to different `PhysicsBody3D` nodes. Leaving one path empty attaches the remaining body to the world; clearing only `node_b` is **not release**. `exclude_nodes_from_collision` defaults to true and only excludes the connected pair. [Joint3D API](https://docs.godotengine.org/en/stable/classes/class_joint3d.html)

Implementation sequence inferred from those sources: instantiate the joint, add it beneath a stable world parent with body paths still empty, set its global attachment frame, then assign both paths in the same callback. For release, remove the joint from its parent and `queue_free()` it, then clear the controller reference. Keep cargo as an independent dynamic body throughout. `queue_free()` alone deletes at frame end; removing the node from the tree first makes the constraint-clear lifecycle explicit. [Node lifecycle](https://docs.godotengine.org/en/stable/classes/class_node.html#class-node-method-queue-free), [joint lifecycle source](https://raw.githubusercontent.com/godotengine/godot/4.7.2-stable/scene/3d/physics/joints/joint_3d.cpp)

Jolt does not support PinJoint bias/damping/impulse-clamp settings or Generic6DOF limit softness/restitution/damping/ERP; changing these from defaults emits warnings. Joint solver priority is also ignored with Jolt. Do not tune these to conceal drift. Use supported constraints and measure the actual backend's motion. [Godot Jolt differences](https://docs.godotengine.org/en/stable/tutorials/physics/using_jolt_physics.html#joint-properties), [solver priority](https://docs.godotengine.org/en/stable/classes/class_joint3d.html#class-joint3d-property-solver-priority)

## Manufacturer cues

Bromma's SSX40/45 brochure states that floating twistlocks locate in container corner castings, permits 6 mm lateral float, and lists 90° twistlock rotation. The adjacent STR40/45 description specifies a rectangular telescoping frame, end beams, and cab indications for twistlock position and landing-pin status. These are separate functions: frame spreads load/alignment points; twistlocks engage the castings; landing detection confirms placement. [Bromma ship-to-shore brochure, PDF page 7 / printed 12–13](https://bromma.com/ship-to-shore-brochure-2025-web/)

Bromma explains that the standard landed pin determines landed status and mechanically prevents twistlock motion when not properly landed. Its extended pin option checks corner-casting engagement during lifting. This supports distinct **aligned/landed**, **locked**, and **lifting** feedback in the simulation. [Bromma Landed and Hold](https://bromma.com/prevent-accidents-with-bromma-landing-and-hold-indication-system/)

Original design adaptation: show two end beams joined by longitudinal members, four visible corner engagement heads, guide flippers, and a central suspension connection. Validate four corner positions and yaw before creating one aggregate locked joint. Treat that single constraint as an intentional rigid-grip simplification; it does not resolve four individual contact loads. Retain visible suspension between boom tip and spreader. Unlock only after a supported set-down for the normal workflow; a deliberate airborne release should visibly fall under gravity.

## Targeted evidence for implementation

Record attachment only near aligned corners; a loaded hoist raising cargo clear of support; swing following crane motion without per-frame cargo teleportation; set-down followed by joint removal; and cargo remaining supported after the crane departs. Include one airborne-release experiment if testing free-fall, with measured cargo height versus time. These are proposed verification cases, not tests performed by this research task.

Contact support check: despite its name, `get_contact_local_position` returns a global point. Convert it through the load transform before testing the lower face. The contact normal is used in world space. [Godot direct body state documentation](https://docs.godotengine.org/en/4.6/classes/class_physicsdirectbodystate3d.html#class-physicsdirectbodystate3d-method-get-contact-local-position).
