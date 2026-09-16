# Sainiverse_v0.1 — verified mechanism snapshot, 2026-09-16

Display/export name: Sainiverse_v0.1. Black, desert, white and blue are themes. Historical report names and stable internal body IDs remain for traceability.

The model has 21,991 authored parts, 91 moving visual groups, 280 batched meshes and 1,356,382 triangles. Native Jolt uses 223 bodies and 214 joints; MuJoCo includes 224 bodies counting world, 268 DOFs and 82 actuators. Visual geometry, collision proxies and provisional mass/inertia are separate.

## Structure

The deck/fascia/lower chord is a joined skin with shader-painted red waistline, eliminating 24 overlapping coplanar face pairs (now zero). Grey steel remains on walking surfaces; sides use the main theme pigment. Cabin footings, columns, haunches and longitudinal/cross girders establish a connected support path. Underdeck distribution, motors, reducers and shafts have distinct roles. Both cooling elbows are connected watertight meshes. Equipment-room windows and selected support families are mirrored.

The sampled boarding clearance audit covers six lifts × 36 poses, including guards and dynamic ramps: zero fixed-hull intersections. Intended guides/hinges are excluded. This is a sampled geometry test, not an exhaustive interference or strength certificate.

## Boarding

Each lift uses four serial prismatic stages (60 kN finite actuator cap) and a dynamic 2 m folding ramp (3 kNm cap). A fixed 270 mm bridge closes the deck transfer gap. Parked/level/terrain checks and stow-before-drive interlocks operate in native runtime. Native 78 s cycle returns all six mechanisms; a 500 kg witness stays supported. MuJoCo 75 s cycle also returns all six mechanisms with finite states.

Sai runs its existing native ONNX locomotion/impedance controller at 2 kHz physics / 50 Hz policy. The carrier settles dynamically for 10 s, then is a stationary fixture; selected lift/ramp and Sai stay dynamic. Ground → ramp → lift → deck completes at 99.1145 s, with four supported wheels and upright ≈1 at end. This does not validate hull response to the boarding robot and is not a newly trained end-to-end mission policy.

Walking MicroDuck uses its existing ONNX controller at 200 Hz physics / 50 Hz policy on the cabin floor. The final 14 s robot run ends without a fall. Roller MicroDuck patrols the real deck for 33 s without a recorded fall; lane-heading feedback and a route endpoint clear of the stairs constrain the route. Pose placement is initialization only.

## Cranes and receiver

Eight cranes have independent slew, luff, extension and dynamic free hooks. Cylinder forces act at physical eyes (2 MN cap); skins follow measured endpoints. A massless unilateral elastic cable uses 300 kN/m stiffness, 20 kNs/m damping and 500 kN tension cap. Receiver yaw and upper-bearing fold use finite joint torque and a convex collision proxy. Native and MuJoCo 85 s unloaded cycles deploy and return near zero. External payload pickup, load ratings and SnowRunner-equivalent cargo handling are not qualified.

Equipment masses are provisional thin-wall estimates, min(solid volume, surface area × wall thickness): 30 mm steel / 20 mm receiver aluminium, with small pins solid. Removed equipment mass/inertia is deaggregated from its parent hull; total mass is 15,481,233.60 kg. No stress, fatigue or hardware validation is claimed.

## Driving, performance and media

Final native hills run is 55 s, peak 16.47 km/h, measured hitch yaw peak 8.09°. Rounded uphill/downhill terrain plus uneven cross-slope relief uses real compliant contact. It does not model deformable snow/mud or certify ride comfort.

Final 100 s flat test: peak 100.0009 km/h, simulation/wall ratio 0.984. At 1920×1080, Forward+, 4×MSAA on NVIDIA GB10 / Godot 4.7.2, measured median 81.71 FPS, p95 frame time 18.71 ms, p99 20.62 ms. No screenshot capture. Force control stays at 200 Hz; joint diagnostic sampling is 10 Hz. An earlier 23 FPS regression was rejected and fixed by per-body pigment batching, cached controller calculations and native gravity. These results are specific to the tested machine, scene and view.

Four GIFs use 150 real rendered frames each, about 10 s at 15 fps: hills/turning, Sai boarding, cabin walking and parked crane/receiver/deck patrol. Sai's last clip is selected from actual exit completion, not a fixed timing assumption. Worksite inset shares the same live physical world. Captured simulation times are recorded separately; clips may select/compress longer missions.

Engine references: https://mujoco.readthedocs.io/en/stable/XMLreference.html ; https://docs.godotengine.org/en/stable/classes/class_generic6dofjoint3d.html . These explain engine mechanisms, not hardware ratings.
