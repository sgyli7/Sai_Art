# r032 — cockpit, access and mechanical revision

This is a review candidate. The user's Microsoft Flight Simulator close-up quality
requirement remains a visual acceptance requirement, not an automatic test result.
Research and source evidence: `R032_REFERENCE_RESEARCH.md`,
`R032_COCKPIT_CLOSEUP_REFERENCE.md`.

## Geometry and materials

The previous wheel was twenty capped cylinder segments. It is now a continuous
96×16 torus with dished spokes, hub, supported column and independent conservative
contact arcs. Both front instrument slabs previously intersected the console;
measured intersection volume is now zero. Instruments have raised mounting rings,
recessed dial faces and captive screws. Runtime dial/legend artwork uses two shared
4096×2048 targets; fine markings are rendered into these textures, not thousands of
mesh letters. Dials update at 10 Hz nearby and 2 Hz beyond 50 m.

Pilot and engineer seats now separate soft upholstery, hard backing, bolsters,
arm supports, suspension/adjustment structure and floor attachment. Interior
soft parts use finer rounded profiles. Fabric weave is very low contrast and fades
before it aliases; there is no random speckle displacement. Upholstery differs
from the paint in every theme; lounge fabric has its own related colour.

| Theme | Console | Pilot upholstery | Lounge | Hard seat frame |
|---|---|---|---|---|
| Black | #343D43 | #907354 | #776C60 | #242C32 |
| White | #56656B | #657D84 | #60747D | #303A40 |
| Blue | #394952 | #A38565 | #A28D70 | #26343E |
| Yellow | #444C4D | #687777 | #74766A | #2B3438 |
| Desert | #4E5651 | #718079 | #796A58 | #303C37 |

The hatch's spurious blue glass was removed. Wipers and four redundant cabin doors
were removed; symmetric windows and two usable entry doors remain. The forward
floor extends to the shell, and a hollow lounge/stair connector reaches the cabin.
The lounge includes one UV-authored CC0 maintenance terminal; provenance is in
`assets/third_party/rubberduck_industrial/PROVENANCE.md`. This is not imported MSFS
commercial geometry.

## Lift and underframe

Fixed lift rail cassettes attach to the hull; moving rails retain 2.05 m overlap at
full horizontal extension. Guide rollers sit at two separated bearing stations.
Nested vertical guides retain 1.45 m overlap at their full stage stroke; paired
visible cylinder rods retain 0.50 m overlap in the drawn arrangement. These are
geometric checks, not strength qualification. The deck/boarding bridge is a single
solid to remove coplanar junctions. Mast/actuator cutouts and the travel envelope
are checked separately from intentional sliding engagement.

Underframe additions include hollow longitudinal trusses, deck ties, truck
crossheads, motor/reducer packaging, manifolds, accumulator feeds and protected
service routes. Metal volume contributes provisional mass and inertia. This does
not establish a manufactured 100 km/h rating or certify load paths by FEA.

## Function and evidence

See `COCKPIT_CONTROLS.md` for all 17 controls, current readings, limits, contact
frames and explicit robot-training limitations. `cockpit_native_acceptance.json`
records the 195 s native control scenario; `cockpit_mujoco.json` records the
finite-force joint/contact bench. `mujoco_cycle.json` records the 75 s complete
six-lift model cycle. Geometry checks do not replace native close-up inspection.

Historical r031 FPS/GIF evidence must not be relabelled as r032. New full-vehicle
performance, robot-route checks and presentation captures are generated separately
before replacing the private review delivery.

## Company identity and interior finish

The user-supplied boards are retained with source hashes. Reproducible extraction
produces 23 transparent Sai marks and weathered stickers; 38 selected placements
span occupied rooms, console faces, seat backs, vehicle fascias and crane hatches.
A single atlas preserves each sticker’s aspect ratio; board captions and baked
checkerboard backgrounds are excluded. Eight obsolete raised wordmarks were removed.

Actual inward shell faces, including the lounge's previously occluding floor and
ceiling, now carry separate lining/floor materials. Wall seams, ceiling access
panels, enclosure joints and scuffs use metric local projection, avoiding the
precision loss observed when metric coordinates were packed into tiny UV fractions.
Walking surfaces and vertical painted fascias retain distinct finishes.

## Contact performance

140 exact rectangular convex contacts became equivalent box primitives; two pairs
of touching boxes with identical other-axis extents were merged. Door/window openings
and furniture contact bounds remain. The native controller precomputes its active
force-link list; diagnostics retain all joints at 10 Hz. Final measured performance
is recorded separately, not inherited from r031.
