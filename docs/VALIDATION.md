# Sainiverse_v0.1 — r032 review evidence, 2026-09-17

Current visuals and measurements supersede r031. Five themes are black, white,
blue, yellow and desert. The supplied Sai company emblem is separate from the
vehicle's English display name.

## Model, identity and interiors

23,228 authored parts, 104 visual body groups, 323 batched meshes and 1,511,302
triangles. The native model uses 236 bodies and 227 joints; MuJoCo includes world
as body 237, with 281 DOFs and 95 actuators. Total provisional mass is
15,639,253.536 kg. Visual meshes and contact proxies remain separate.

Three original user-supplied company sheets are retained with hashes. Their
reproducible crop pipeline produces 23 RGBA variants and one padded atlas;
38 body-bound placements use original aspect ratios. Eight obsolete raised
wordmarks were removed. Source masks, individual PNGs and placement coordinates
are included in assets/company/.

Cockpit and lounge shell inward faces now use independent lining; the actual
visible lounge floor and ceiling were reassigned rather than covered by a
coincident mesh. Walls, ceiling inspection panels, metal enclosures and walking
surfaces have different finishes. Metric body-local projection fixed the native
panel-seam distortion observed with fractional packed UVs. Upholstery and hard
frames use separate colours in every theme. New native close-ups and GIFs show
these surfaces in the actual runtime.

The wheel is a single connected 96-section circular rim (maximum chord sagitta
0.126 mm); both front gauge/console intersection volumes are zero. 17 finite-effort
physical controls map to driving, brake/range/park, crane axes/selection/work,
receiver axes, lift selection/motion/all-lifts and doors. Native 195 s control
scenario records all controls, 10 physical button events, and all-six-lift
extension/retraction. The MuJoCo bench tests all 17 coordinates and a passive
0.5 kg contact probe pressing the WORK button. No trained robot-arm policy is claimed.

The user's MSFS close-up quality bar remains a visual review criterion. These
measurements do not establish commercial flight-simulator artwork parity.

## Structure and lifts

Cabin floor closure, enclosed lounge/stair connection, fewer exterior doors and
symmetric windows address the earlier room defects. Wipers and the false blue
pedestal glass were removed. Underframe trusses, crossheads, motor/reducer,
distribution and protected services have distinct roles and provisional mass.

The lift/deck boarding bridge has zero detected coplanar overlap. Sampled boarding
clearance checks cover six lifts × 36 poses (126 Boolean pairs). Fixed rail
cassettes and moving arms retain 2.05 m overlap at full outward extension;
vertical guide overlap is 1.45 m and the drawn cylinder rod engagement is 0.50 m.
These are geometric checks, not strength certificates.

The final native 78 s cycle deploys and returns all six lifts with the complete
carrier dynamic. Minimum platform tops are 0.2498–0.2501 m, matching the 0.25 m
platform thickness at ground contact. Final horizontal/vertical errors are below
0.4 mm. A 500 kg witness remains supported; its post-settle floor gap ranges from
−0.203 mm to +10.04 mm during the cycle. Peak transient servo error is 0.127 m.
The MuJoCo 75 s six-lift cycle also completes with finite state.

## Performance

Exact primitive conversion replaces 140 rectangular convexes with equivalent
boxes; two adjacent box pairs are merged. There are 471 interior contact shapes.
No door/window openings or furniture contacts were removed for performance.

The final 100 s flat-drive run reaches 100.0008 km/h, with simulation/wall ratio
0.9802. At 1920×1080, Forward+, 4×MSAA, Godot 4.7.2 / NVIDIA GB10, no capture,
frames after 10 s give median **65.75 FPS**, p95 **37.70 ms**, p99 **46.14 ms**.
This is lower than the old r031 performance; that older value is not reused.
Force control runs at 200 Hz, with joint diagnostics at 10 Hz. These are
scene/machine-specific simulation measurements, not a manufactured speed rating.

## Media and robot routes

Five new GIFs replace the old presentation: cockpit detail tour, walking MicroDuck
cabin patrol, crane/receiver plus roller MicroDuck worksite, Sai boarding, and
uneven hills/turning. Each contains 150 native-rendered frames at 15 fps (10 s).
Captions show simulation time; longer operations are sampled/compressed.

MicroDuck uses existing native ONNX controllers: 200 Hz physics / 50 Hz policy.
Sai uses its existing 2 kHz physics / 50 Hz policy controller. Its carrier first
settles dynamically for 10 s and then becomes a stationary fixture; the robot,
selected lift and ramp remain dynamic. This does not test hull response to the
boarding robot. The separate witness-payload test above retains a dynamic hull.
Stair geometry/contact continuity is checked; learned robot stair traversal is
not demonstrated.

Cranes use independent slew/luff/extension and dynamic hooks, finite cylinder
forces and a unilateral elastic cable. The presentation is unloaded mechanism
operation. External cargo pickup/load ratings and SnowRunner-equivalent handling
remain unqualified. Hills have real hard-ground relief/contact; deformable
snow/mud, fatigue and manufacturing certification are outside this evidence.

## Reproduction and source

Current raw JSON (gzip), logs, representative frames and hashes are under
[evidence/r032](../evidence/r032/); current GIFs are under evidence/media/.
Historical evidence remains labelled r031. The final media_checks.json records
frame durations, robot outcomes and hills measurements; portable_checks.json
records the packaged replay. Editable packed Blender, named-body GLB, MJCF,
source generation scripts and five palette JSON files are included.

The maintenance terminal's CC0 provenance is retained in
vehicles/Sainiverse_v0.1/assets/third_party/rubberduck_industrial/PROVENANCE.md.
User-provided company art is not relabelled CC0. Robot dependencies keep their
original source/licence records in integration/robots/. Linux ARM64 is verified;
other platforms require rebuilding the supplied native extensions.
