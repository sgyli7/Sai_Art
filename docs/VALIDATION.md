# Sainiverse_v0.1 — r032 review evidence, 2026-09-17

## Polar game integration, 2026-09-20

The later polar game integration uses 60 Hz vehicle physics for manual driving,
60 Hz for the parked-carrier lead-in of MicroDuck demos, and 100 Hz for the
lead-in of Sai boarding demos. Once the carrier is parked and frozen, MicroDuck
uses its verified 200 Hz physics and Sai uses 1000 Hz; their policies remain at
50 Hz. This is a game integration profile, not a change to the r032 200 Hz
qualification drive below. A direct 60 Hz Sai lead-in made Sai 001 fail its
boarding route, so the successful 100 Hz setting is intentional.

At 1920×1080, Forward+, 4×MSAA, Godot 4.7.2 / NVIDIA GB10, the later rendered
checks measured the entire interval after simulation second 3, including the
carrier lead-in. "Minimum FPS" is the lowest complete one-second wall-time
window, not an average over the whole run:

| Route | Duration | P95 frame time | Minimum one-second FPS | Outcome |
| --- | ---: | ---: | ---: | --- |
| Manual carrier W/A replay | 23 s | 12.97 ms | 103 | 32.7 m forward; steering changed heading |
| Walking MicroDuck cabin patrol | 16 s | 10.47 ms | 170 | 0.94 m, no fall |
| Roller MicroDuck deck patrol | 16 s | 10.67 ms | 156 | 2.93 m, no fall |
| Sai 001 full boarding | 115 s | 9.36 ms | 90 | Completed; minimum upright 0.953 |
| Sai 002 full boarding | 115 s | 8.49 ms | 122 | Completed; minimum upright 0.945 |
| F5–F9 four-robot switch replay | 44 s | 11.25 ms | 126 | All four robots moved, no falls; returned to carrier |

The manual F5–F9 selection replay in the existing game checkout moved all four
robots on the snow and returned to the carrier with no falls or controller
errors. The [compact machine-readable results](../evidence/polar_game_validation_2026-09-20.json)
record all six checks. These are local machine measurements, not a cross-hardware guarantee. The game checkout's
`scripts/check_sainiverse_play.py` reproduces the input, route, and frame checks.

The interactive follow-up exercised F1/F2/F3 after selecting each of the four
robots in isolated checkouts. Half a second after each travel request, the
measured distance from the requested spawn was 0.116 m for walking MicroDuck,
0.121 m for roller MicroDuck, and 0.023–0.216 m for Sai 001/002. The MicroDuck
sessions reported no fall and the Sai sessions no failure. A further F3→F1
return worked for walking MicroDuck and Sai 001. Rendered 1920×1080 captures
of the F3 MicroDuck and Sai 001 views showed each robot visible in the cockpit
with the robot controls on the left. `python3 tests/check_interactions.py`
exercises the actual Godot scripts for panel input, per-robot hints, and travel
routing. These checks cover spawn placement and visible controls; they do not
measure long autonomous travel after relocation.

The unified launcher was checked at both levels. `run-native.sh --headless
--scene polar_range --seconds 3` exited successfully after actually launching
the Sainiverse Godot runtime; its report said `failed:false`. The headless
`godot/tests/polar_picker_probe.gd` activated the 03 world button and the
Sainiverse vehicle button and observed exit code 74, which is the launcher's
Sainiverse handoff.

The current polar media uses native rendering and the same robot physics.
The four-camera full-vehicle PV in the game repository was captured from the
manual W/A driving replay over simulation seconds 32–42. All 150 source frames
were 1280×720; the vehicle stayed entirely in view at each camera cut and the
44-second native run ended with `failed:false`, 34.9 m of forward travel, and
an 18.0 km/h peak. The GIF plays the captured frames at 15 FPS without
interpolation.
The revised Sai cockpit vignette runs the unchanged learned standing policy and
native arm impedance at 50/1000 Hz. The added yellow grip and its collision
shape were removed. A scripted arm target reaches the original lower steering
spoke; no Sainiverse model geometry or body count changed. In a 24-frame
capture, the hand had 3 sampled contacts, the wheel moved up to 0.115 rad,
minimum chassis upright was 0.973, and no failure or script error was reported.
The [new contact record](../evidence/polar_sai_cockpit_control_2026-09-20.json)
replaces the earlier grip-assisted claim. This is a controlled contact vignette,
not a learned autonomous manipulation task.
Walking MicroDuck traversed a 1.67 m span in the cockpit, walking out and back
with no fall. The GIF camera
views were checked at early, middle, and late frames for seat/console/platform
occlusion before encoding. Boarding frames were selected across the approach,
elevator ride, and exit; the elevator section compresses simulation time in
playback. No robot motion was synthesized between captured frames.

The original r032 measurements and media below are preserved as historical
qualification evidence; they used a different robot-demo staging profile.

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
