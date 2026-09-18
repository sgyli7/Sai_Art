# r033 cargo handling — work in progress

r032 remains the published private review release (9beb4bb). This candidate adds
one independently movable top-tier 20 ft container using its existing authored
geometry, plus a source-authored four-corner spreader and four sling legs. The
8,000 kg gross scenario mass is transferred out of the rear hull, not duplicated.
A new physical HOOK / RELEASE button (H) uses the same finite joint threshold as
other cockpit controls. Native handling uses a deck lock, proximity hook pin and
supported release. Container pose is never assigned after initialization.

The initial code audit found the previous 11 m winch and inward ±60° slew range
could not perform ground-side loading. Candidate crane slew is ±170° and paid cable
limit 24 m. Rear hooks start above the top tier instead of within the aggregated
cargo envelope. Static container contacts are split by column to preserve the
removed top-tier opening. These changes require loaded native/MuJoCo testing,
clearance review and performance/route regression before replacing the release.

Current test is one 8 t article, not all 72 boxes or a manufacturer load chart.
Manual full cargo selection, re-securing and limit UI are still pending. The
single-load MuJoCo handling chain is now measured below. Do not relabel r032 GIFs
as proof of this capability.


## 2026-09-17 measured progress

Native v3 and MuJoCo complete align → attach → lift → slew → ground set-down →
release with the same 8 t source load. Native peak rise 4.82675 m, release 114.91 s;
MuJoCo 4.82812 m, release 121.47 s. The final native load retains four contacts and
40+ s supported time. `check_loaded_cargo.py` checks final 15 s rest drift, actual
height and travel, connection removal, phase order and continuous supported rest.
Native v2 was intentionally cancelled before completion after official API docs
confirmed contact points were global; v3 fixes the support-frame conversion.

The optimistic reach screen found only 8 of 24 top-tier positions reachable.
This contradicts full coverage, so the cargo feature is **not complete**. Existing
outer/inner boom lengths and overlap require a real multistage authoring revision;
merely increasing a slide limit would detach the tubes visually. Next work must
replace that geometry/physical chain, recheck 24-slot reach and collision-free
paths, generalize handling beyond the one article, support re-securing, and then
rerun the controls/robot/performance checks before private main is updated.

## Multistage and physical-button continuation

The original single telescoping member is replaced on all eight cranes by four
chamfered, hollow box sections with three serial strokes of 4.30, 4.00 and 3.80 m.
`check_telescopic_sections.py` measures the exported geometry, verifies 32 closed
shells and 32 glands, and runs 432 solid-intersection tests at nine extension
positions. No shell/gland intersection was found; minimum full-stroke overlap is
2.00 m (other interfaces 2.28 and 2.46 m). These are packaging dimensions, not a
manufacturer rating or verified strength calculation.

`check_crane_coverage.py` now finds 24/24 reachable top-tier lifting eyes, replacing
the former 8/24 result. `check_crane_paths.py` additionally samples 344 upright
cargo positions per candidate through vertical lift, clearance lift, outward
slew and lowering. All 24 slots have at least one candidate without overlap with
other cargo boxes or parked crane envelopes. This screen excludes moving-boom
clearance, rigging, payload swing and hull attitude; it is not full path acceptance.

The HOOK / RELEASE cockpit control now dispatches to the actual MuJoCo cargo
handler. Without a handler, the isolated control bench explicitly rejects the
request. The bench passes with 18 physical joints; the existing passive 0.5 kg
contact probe still presses WORK. Native and MuJoCo cargo scenarios now press the
physical button instead of directly creating/removing the attachment. In the
first button-driven run, both engines recorded exactly two accepted physical
presses, matching attach/release times: native 43.215 / 133.130 s and MuJoCo
103.180 / 197.520 s. Both loads rested without measurable drift in the last 15 s.
Evidence: `r033_cargo_button_native`, `r033_cargo_button_mujoco.json`,
`r033_cargo_button_acceptance.json`.

The next trajectory keeps horizontal pickup radius while luffing, then adds a
separate clearance phase before outward slew. This avoids the former shortcut
of luffing at a fixed extension, which changes the horizontal load position
before it is clear of adjacent stacks. Corresponding native/MuJoCo scenario
evidence is kept separately under `r033_clearance_*`.

Still open: general cargo selection and top-down eligibility for all 72 boxes;
return-to-slot twistlock securing; complete moving boom/rigging collision audit;
loaded qualification beyond this one 8 t scenario; matching regenerated Blender
source and regression/PV packaging. Published private main remains r032.

The later clearance-route rerun supersedes the earlier timing paragraph for
current candidate evidence: native `r033_clearance_native` completed 260 s with
release at 166.045 s and 6.834 m peak rise; MuJoCo `r033_clearance_mujoco.log`
completed 320 s with release at 225.720 s and 6.567 m peak rise. Both accepted
two physical HOOK button presses. The acceptance helper records 0.108 m native
and 0.063 m MuJoCo horizontal drift during vertical lift; native clearance/slew
samples have zero contacts. Earlier v3 numbers remain archived and are not
mixed into the current result.
