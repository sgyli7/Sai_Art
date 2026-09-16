# R032 reference research — Sainiverse_v0.1

Date: 2026-09-17. Scope: visual/functional reference for the cockpit, internal circulation and underside. This is research and a proposed design basis, not a structural, ergonomic or vehicle certification.

## What was actually inspected

The following pages were read with the web tool and their key images were **visually opened in the in-app browser**, rather than relying on search titles:

| Reference | Image inspected | Useful observation |
|---|---|---|
| [Microsoft Flight Simulator / iniBuilds AN-225 manual V2](https://flightsimulator.azureedge.net/wp-content/uploads/2023/04/AN225_MSFS_Manual_V2.pdf), linked by the [official aircraft-manuals page](https://www.flightsimulator.com/aircraft-manuals/) | PDF viewer page 14, cockpit layout, and page 20, right-hand engineer station | A continuous main instrument fascia joins two pilot positions; a substantial centre pedestal runs between them. Instruments are grouped by task. The engineer position is a dense sidewall/desk arrangement behind the pilot, rather than a row of identical floor cabinets in the forward field of view. |
| [NASA crawler-transporter fact sheet](https://www.nasa.gov/wp-content/uploads/2015/12/638823main_crawler-transporter.pdf) | PDF pages 2 and 4; technical table and overall photographs | Four truck assemblies carry the platform; each has paired tracks. A deep, open structural frame connects the platform to the trucks. The photographs establish the scale and load-path hierarchy; they do not reveal every underside pipe. |
| [NASA crawler-transporter 2 maintenance photograph, 2015](https://www.nasa.gov/image-article/crawler-transporter-2-2/) | Main photograph, technician between the tracks | Large circular bearing/gear interfaces, heavy webs and substantial mechanical access space. Human scale makes the thickness and clearance legible. |
| [Intrepid Museum: submarine Growler](https://intrepidmuseum.org/exhibitions/permanent-exhibitions/submarine-growler) | Gallery images 1–3: periscope, helm, aft torpedo room | Instruments sit in coherent mounted groups, cables/pipes follow the ceiling and hull, chairs have physical mountings, and the hull encloses the equipment instead of leaving flat planes disconnected. No weapon forms are needed in Sainiverse. |
| [USS Midway Museum: Below Deck](https://www.midway.org/visit/our-exhibits/below-deck-exhibits) | Engine Room & Main Engine Control photograph | Controls, gauges and valves form one task-focused wall. Adjacent exhibit image shows overhead services. The page distinguishes living/social spaces from engine/control spaces. |

The MSFS manual is an official **simulation product** reference. Its own preface says simulation use and adapted procedures. No real An-225 cockpit was measured. The Growler and Midway sites were not exhaustively toured; no full dimensional ship deck plan was obtained. Browser screenshots were reviewed live; the copyrighted photographs are not copied into the deliverable assets.

## Facts supporting the underside architecture

NASA documents electric traction, hydraulic steering, and hydraulic jacking/equalizing/levelling as separate systems. The older fact sheet lists 16 traction motors, four per truck, and eight track belts. It also describes electrical, lubrication and monitoring subsystems. Those facts support **distributed drive and organised services**, not a central mechanical driveshaft invented solely to fill empty space. [NASA fact sheet, pp. 2–3](https://www.nasa.gov/wp-content/uploads/2015/12/638823main_crawler-transporter.pdf)

NASA's upgrade account explicitly names stronger roller bearings and lubrication, JEL cylinders, generators, braking, shear-web stiffeners and rebuilt gearboxes. Therefore believable detail belongs at load transfer, drive, suspension and maintenance interfaces. [NASA upgrade account](https://www.nasa.gov/general/crawler-transporter/)

NASA's historical Saturn V manual describes an unloaded speed of 2 mph and a loaded speed of 1 mph on level ground. **This is not evidence that a NASA-like platform can achieve 100 km/h.** Sainiverse's simulated target and provisional power/mass model remain separate from the reference. [NASA Saturn V Flight Manual, Ground Support, crawler-transporter section](https://www.nasa.gov/wp-content/uploads/static/history/afj/ap12fj/pdf/a12_sa507-flightmanual.pdf)

## Proposed design decisions for Sainiverse (original design, not measured reference facts)

### Cockpit: one coherent workplace

1. Build a full-width, shallow wraparound front instrument fascia under the windows. Left/right instrument groups are symmetrical in enclosure shape, with a central vehicle-status group. A dark padded glare shield finishes the upper edge. Keep the driver's eye line above this edge.
2. Add two human-sized suspended/bolted seats, with backs, seat pans, rails/pedestals and armrests. Do not duplicate giant electrical cabinets alongside the windscreen. The seats and controls establish the human scale that is absent from the current two low boxes.
3. Connect a centre pedestal from the fascia rearwards between the seats. Its controls should represent track propulsion, brake, operating mode and emergency stop. Do not copy six aircraft throttles onto a ground vehicle merely because AN-225 has six engines.
4. Add a bounded overhead panel between/behind the forward roof beams, with lighting, electrical isolation and auxiliary-system groups. Keep the main aisle and standing headroom clear.
5. Put an engineer desk and map/communications station behind the front seats, against the side walls. Dense graphics belong on these panels. A few large gauges plus small switch/label atlases provide hierarchy; endless identical rectangular machine-front textures do not.
6. Remove all windscreen wipers as explicitly requested. Close the floor-to-front-wall and wall-to-window joints with actual continuous solids/reveals. A black cover plane should not hide a missing floor or wall.
7. Use muted warm-grey/blue-grey instrument panels within the existing black theme, charcoal glare shield, dark upholstery, and restrained amber/green/red states. This is a local functional palette; it does not change the vehicle's exterior theme.

Provisional ergonomic targets to test against the actual camera and robot bounds: worktop approximately 0.74–0.78 m above finished floor; seat pan approximately 0.45–0.50 m; main aisle 1.2 m clear; standing headroom at least 2.1 m. These are authoring targets, **not dimensions copied from An-225 nor a compliance claim**.

### Rest space → enclosed stair vestibule → cockpit

Use one legible circulation sequence: rest room, a framed internal opening, enclosed connecting vestibule/stair, then the rear of the cockpit. Keep the existing exterior service stair only if it has a distinct maintenance/emergency destination. Do not place three consecutive external doors into the same undivided cabin.

A ship-inspired connection needs floor continuity, real sidewalls, a ceiling, bulkhead thickness at openings, handrails anchored into the stair stringers/wall, and one lighting/service route. Closed spaces cannot be joined only by a floating outdoor walkway. Use a stair landing at both ends rather than placing the last riser against a door. Show the change of level through the stair geometry, not through a sloped wall decoration.

Borrow the readable compartments and constrained service routing, not literal submarine high coamings or vertical ladders that would block Sai/MicroDuck. The US submarine force specifically warns that access involves vertical ladders and that ladders/hatches must stay clear; those historical constraints should **not** be copied blindly into a robot-accessible primary route. [US Navy submarine tour guidance](https://www.sublant.usff.navy.mil/Contact-Us/Tour-Request/)

Replace redundant doors with matching windows on both exterior sides. Retain one meaningful exterior entrance per side and the rear interior connection. A low table can remain a lounge coffee table only if paired with lounge seating; an office/map workstation must receive normal desk height and leg clearance. Add a compact locker, wall handset, ventilation grille and restrained compartment labels at actual destinations. Their mountings must attach to the walls, not sit on unrelated trim planes.

The layout of stair and door clearances must be checked against collision geometry. A visually connected stair is not evidence that an existing learned locomotion policy can climb it; that requires a separate rollout. If roller access across a level change is required, retain the working lift or reserve a dedicated internal lift, rather than pretending wheeled robots can use steep naval stairs.

### Underside: a visible chain of useful structures

Use five organised systems, each with a visible start/end:

| System | Geometry to show | Connection rule |
|---|---|---|
| Load path | Two deep longitudinal main girders, transverse truck crossheads, diagonal/shear-web braces, bolted gusset regions | Truck suspension mounts connect to crossheads; crossheads join main girders; girders support the deck. Do not scatter disconnected ribs over a flat underside. |
| Drive | Distributed electric motor/reduction housings near the relevant track drive sprockets; protected cable trunks | Short local torque path. Cable trunks connect power distribution to each truck; no ornamental shaft across a steering or slide joint. |
| Levelling/suspension | Cylinder barrels, rods, clevis pins, local valve block and accumulator cluster | Every cylinder connects two actual suspension members. If the relevant joint moves, visual ends follow those physical bodies. |
| Services | Paired supply/return lines along inner girder faces, clipped cable trays, branching at truck stations | Corners use continuous elbows; flexible loops only where relative movement requires them. Avoid pipes crossing the suspension's swept volume. |
| Maintenance | A bounded centre inspection route, removable guards, gearbox access covers and sparse identification plates | Access openings sit beside the serviced assembly. Keep vulnerable parts above the lowest protective structure. |

The goal is structured density, not maximum part count. Model the deep beam profile, large drives, cylinder eyes, pipe turns and joints. Use an atlas/normal map for weld seams, fasteners, shallow vent ribs, labels, flange bolt patterns and paint wear. Reuse materials and merge static detail per physical body to preserve the existing batching optimisation. Do not introduce per-fastener nodes or extra real-time lights.

## Acceptance checks for the implementation

- Photograph-equivalent views: wide underbody; one truck crosshead; full forward cockpit; aft engineer station; route from lounge through the enclosed connector; exterior door/window close-up.
- Door/window surfaces are mapped to their owning body and wall opening; no free blue square covers a door decal. Avoid decal edges crossing handles, reveals or ladder uprights.
- Window apertures have thickness, lower sills, upper reveals and no light leak at the floor/front wall.
- Every new visible pipe has connected endpoints. Every support touches both its load and its support node.
- Check bilateral window shape/placement and removal of duplicated entry doors.
- Test a human camera sweep and the existing robot collision bounds along the internal route; report any untested stair locomotion separately.
- Recheck lift, track-steer and suspension swept clearances after underside detail is added.
- Record face count, render mesh/draw-call change and an uncontended FPS sample against the existing accepted build; do not claim the old benchmark still applies to a heavier new interior without measuring it.

## Addendum: lift root, telescoping carriage and downward mast

Added 2026-09-17 for the user-reported floating root and bare rectangular crossbeam.

### Additional first-party material actually inspected

- [DHOLLANDIA DH-S slide-away liftgate operation manual](https://shop.dhollandia.com/loaddocument?UID=kqwnTWUIAUt3hw), document dated 2021-10-19. **PDF viewer page 8 (printed page 7) was visually inspected.** Its numbered line drawing shows twin slide tubes, chassis mounting brackets with triangular webs, a sliding lift frame, platform/arms/cylinders and a separate pump unit. Printed pp. 6 and 12 explain that the frame slides in chassis-mounted tubes and that translation uses a hydraulic-motor pinion/rack or a double-acting retraction cylinder. This is a very close organisational reference for Sainiverse's horizontal deployment. The manufacturer's cargo-lift use restrictions and ratings do not certify a Sainiverse passenger device.
- [Genie GR / QS service manual 1275811GT, February 2022](https://manuals.genielift.com/Parts%20And%20Service%20Manuals/data/Service/Material%20and%20Small%20Personnel%20Lifts/1275811GT.pdf). **PDF viewer pages 87–88 (printed 73–74) were visually inspected:** nested columns, lift-cylinder mounting plate/clevis, chained stages and idler mounting details. Printed 75–76 describe column assembly, guide pads and chain adjustment. The lesson is multiple guided sections and real end fittings, not a stack of disconnected boxes.
- [Rollon telescopic rail product family](https://lp.rollon.com/en/telescopic-telescopic-rail) and [full-extension family](https://www.rollon.com/ind/en/family/telescopic-slides/full-extension/) were read for terminology only. Three-element rails can achieve full extension by an intermediate section. **No Rollon product was sized or selected, and its catalogue capacity cannot be transferred to a bespoke 2.7 m cantilever.**

### Recommended architecture

`hull crossmembers → bolted fixed twin guide rails → moving twin beams → outboard crosshead/flanges → stationary outer mast → 3 descending guided stages → platform yoke → platform/ramp`.

Each arrow is a real connected load path. The fixed rails must extend inboard under the deck and be attached to at least two load-bearing crossmembers with webbed brackets; a box touching the deck edge is insufficient. The outer mast belongs to the horizontal carriage, so it moves outward but never detaches from the carriage while the lower stages descend. Add a broad end plate, side gussets and fastener atlas at that joint. Small crosshead notches/fillets and removable covers should describe assembly and maintenance, rather than arbitrary surface boxes.

Use two separated rails to resist torsion from an off-centre robot. Render their C/box profiles, rail mouths, inner moving sections, replaceable wear pads and two spaced bearing stations. The bearing stations carry vertical reactions and bending moment; the horizontal actuator is not a substitute for them. Use one synchronised rack/pinion drive with a cross-shaft between rails, or two explicitly synchronised cylinders. The rack route is compact and matches the source; its motor/gearbox attaches to the carriage or fixed rail according to which carries the rack. Never model an unsupported motor floating midway along a moving beam.

### Provisional geometry that preserves engagement at 2.7 m deployment

The following are **authoring inputs to validate**, not manufacturer specifications or a rated design. Define an outward local coordinate `u`, with the fixed rail mouth at `u = 0`:

- Fixed rail interval: `[-4.20, 0.00] m`.
- Moving beam when stowed: `[-4.00, 0.00] m`.
- Horizontal travel `q`: `[0, 2.70] m`; moving beam interval becomes `[-4.00 + q, q]`.
- Engagement is the intersection of those intervals: `overlap(q) = 4.00 - q`; minimum is **1.30 m**.
- Two load-bearing guide stations, centred approximately at `u = -1.05 m` and `u = -0.15 m`, provide **0.90 m separation** and remain within the engaged length at full extension. Their roller/pad footprints must also fit, with end margin; point centres alone are insufficient.
- The outboard crosshead is rigidly attached at the moving beams' ends. A visual flange must not stay at the old stowed position while the mast leaves it behind.
- Add mechanical end stops and retracted retention/locking features. The simulation travel limit must agree with these visible limits.

If 4.2 m of inboard packaging is unavailable, use a true three-section telescoping assembly and distribute the 2.7 m travel across its two sliding interfaces. For example, each interface travelling 1.35 m with a 2.0 m section leaves 0.65 m engagement, before end allowances. This is a packaging alternative requiring new guide spacing/strength calculations; do not silently extend a 2 m single beam by 2.7 m.

The existing `source/lifts.json` declares one horizontal slide at 2.7 m and **three vertical slides of 2.45 m each**, not four vertical slides. Retaining that travel requires each descending mast member to be longer than 2.45 m. A provisional 3.10 m member leaves 0.65 m overlap per fully extended interface; check that the fixed mast/storage envelope can contain this and that the lower crosshead can reach ground without end-of-travel impacts. Keep only meaningful overlap geometry, not four full-height bars superimposed at the same coordinate.

Genie's reference lifts extend upward from a chassis; Sainiverse's downward-hanging cargo mast is an original adaptation. Do not invert an upward lift's chain sketch and claim it supports a hanging load. A clear implementation for the current independently actuated stages is a double-acting, load-holding actuator between every parent/child pair, its barrel and rod eyes on the respective members. A chain-reeved alternative needs an actual force/tension path and slack/failure behaviour; leave it out rather than adding decorative chains.

### Force and moment checks required before accepting the geometry

- Define the supported outboard mass from the actual stage/platform/ramp parts plus payload; do not use payload alone. Current declared stage/out/platform masses sum to 1,380 kg, the ramp adds 120 kg and the provisional payload is 500 kg. This gives an illustrative **2,000 kg total** if conservatively treated together; some of that mass remains closer to the root in the actual configuration.
- Compute root moment from each part: `M_root = Σ(m_i * g * u_i)` plus inertial terms. If the illustrative 2,000 kg were all at 2.7 m, static moment would be about **53 kN·m**, before platform load offset and dynamic factors.
- Guide reactions include a couple of magnitude approximately `M_root / guide_spacing`; 53 kN·m over 0.90 m is roughly **59 kN** across the guide pair, in addition to net vertical force. A pair of symmetric rails shares it only for symmetric loading. This explains why one tiny root sleeve is not credible.
- For each vertical actuator, use the downstream supported mass and acceleration: `F >= m_downstream*(g + a)/efficiency`, then check the relevant tension/compression direction, buckling, pin shear, bearing pressure, rail bending, bracket load and deflection. A force-limited prismatic joint alone does not establish hardware adequacy.
- Horizontal rack force must account for acceleration, guide friction and slope; actuator power follows `P = F*v/efficiency`. Choose speed/force limits from these inputs instead of assigning an arbitrary motor housing and assuming it works.

### Visual and simulation acceptance

Inspect stowed, half-out, fully-out/high, fully-out/half-down and fully-out/ground poses. At every pose: fixed rails stay bolted to the hull; moving rails remain visibly captured; mast/end flange stay connected; actuator ends follow their bodies; no leg intersects a track or ramp. Retain the parked/level/ground-clearance interlock, deploy horizontally before descending, raise completely before retracting, and interlock driving until retracted. Re-run the existing 500 kg witness and full lift sweep, including guide-root clearance, and explicitly keep the result as a simulation test rather than a certified lifting capacity.

## 免费资源补充筛选（2026-09-17）

已实际下载/渲染检查 CC0 的 rubberduck / a52 工业资源，并导出两个可导入 OBJ / GLB。记录在 `../assets/third_party/rubberduck_industrial/PROVENANCE.md`，精确拓扑与 SHA256 在同目录 `MODEL_REPORT.json`。`control_terminal.glb` 为 152 三角、`tank_control_panel.glb` 为 322 三角，各有 1024px diffuse/normal。源作者：[rubberduck](https://opengameart.org/content/high-quality-industrial-asset-pack)；Blender 4.0 重打包：[a52](https://opengameart.org/content/pbr-industrial-asset-pack)。

**实际外观不应被名称误导**：这些是网门配电柜/带导管控制柜，可考虑后部设备舱，不是飞行员操作台，不包含可拆的精细驾驶旋钮。模型背后开放，应贴墙或补背盖。源单位也不是已验证的真实米制尺寸。Kenney Space Station Kit 的座椅/电脑虽可下载且 CC0，但查看预览后积木感太强，已注明不推荐作为驾驶舱最终资产。本轮限时筛选未找到同时满足低面数、明确许可和足够工业真实感的免费驾驶座椅，不能宣称已找到合格替代；现有座椅应继续按背壳、轨道、调节支架和安全带细化。
