# Sainiverse_v0.1 — 18 September inspection

This revision addresses the six supplied acceptance screenshots. Source coordinates are metres, +X forward, +Y left, +Z up. The editable assembly, GLB and native collision model are regenerated from the same source.

| Screenshot | Change | Evidence |
| --- | --- | --- |
| 1 — passage | Relocate both roof HVAC assemblies and front grilles outside the stair envelope; interrupt the old cross-rail at the stairhouse; remove its central post. | `accept_passage`, geometry checks, native floor/stair rays |
| 2 — service wall | Replace GEOTECH with the supplied transparent-background compact Sai mark at native atlas resolution. Six lift call stations receive fixed posts and deck feet. | `accept_workbay`, six source mounts |
| 3 — service station | Rotate the starboard switch-plate UVs 180 degrees in GLB and Blender; move engineer seats and their contact geometry inward 0.28 m. | `accept_services`, 0.285 m cushion-to-console gap |
| 4 — pilots | Two continuous rounded double-horn yokes, independent physical joints, console-facing columns, floor bearings and finite-torque linkage. | `accept_yokes`, MuJoCo external-torque bench, native UI trace |
| 5 — junction | Extend weather enclosure to meet the sloped cabin bulkhead; enlarge the real passage opening in visuals and collisions; remove overlapping floor area and obsolete trim; rebuild ladder stiles/brackets; shorten the roof conduit to remain inside the cabin. | `accept_joint`, source clearance and native floor rays |
| 6 — freight | Gray removable lifting rig appears in work mode or while attached. Six original fleet-label layouts use the supplied Sai identity; outer rows receive curated banner variants. | `accept_cargo` in transport/work states |

## References and interpretation

- Microsoft Flight Simulator's [official yoke animation guidance](https://docs.flightsimulator.com/html/mergedProjects/How_To_Make_An_Aircraft/Contents/Modelling/Cockpit/Animations/Yoke_Animation.htm) treats the yoke as a prominent animated cockpit component, including external views. The new source model therefore has two articulated operator controls, not a decorative second copy.
- The [official aircraft manual index](https://www.flightsimulator.com/aircraft-manuals/) links the [iniBuilds Antonov An-225 manual](https://msfs.dev-pset.com/assets/docs/Antonov%20AN-225%20POH.pdf). Aircraft-style twin horns are used here for ground-vehicle steering; this is not an An-225 systems replica or a claim of MSFS visual equivalence.
- Saber's [custom cargo guide](https://expeditions-guides.saber.games/custom_gameplay_entities/cargo/Creating_Custom_Cargo.pdf) distinguishes physical cargo units from packed cargo addons. Its [cargo spawning documentation](https://expeditions-guides.saber.games/map_modding/creating_a_map/objectives/objectives_in_snowrunner/stages/spawning_cargo/) describes manual crane loading. The separation of transport appearance and active handling equipment is our design interpretation; the sources do not specify this project's spreader design.

The six fleet graphics are generated locally with fixed typography, palette and wear seeds; they reuse the user's Sai mark. No new third-party art or cartoon logos are introduced.

## Scope

The currently handled container remains the single 8 t gross test article, with its existing deck restraint, hook pin and four-leg load path. Other containers retain static cargo ownership. Rigging installation/removal occurs instantly with work mode; tool installation animation is not simulated. Both yokes carry collision affordances and finite-force motion, but no trained Sai manipulation policy is claimed.

Screenshots validate the recorded views, not every possible intersection on the complete vehicle. Native rendered throughput is reported separately from fixed-frame GIF recording. Existing hills and robot demos remain explicitly labelled with their original simulation conditions.

## Follow-up: mast oscillation

The first rendered workbay review revealed a real regression from the earlier 100 Hz interactive-rate change. The original explicit PD gains applied separately to a serial three-stage mast caused alternating joint velocities up to 5.93 m/s. Uncommanded descent reached 0.447 m and then triggered the protective outward-slide logic, extending the lift 2.70 m. This was not a cosmetic rendering defect.

The unchanged geometry at 200 Hz settled below 0.4 mm, isolating time-discretization as the cause. `runtime/lift_servo.gd` and `source/lift_servo.py` now solve backward-Euler PD against the shared three-stage mass matrix, retaining the 60 kN force cap, gravity compensation, actual collisions and deployment interlocks. The 100 Hz full-vehicle headless reproduction then settled below 0.16 mm without the alternating velocity mode. `check_lift_stability.py` checks both uncommanded displacement and per-step velocity; the original trace fails it. The additional `lift_preview_cycle` scenario tests the interactive 100 Hz path with a 500 kg contact payload.

The follow-up also exposed that the outer two of four original grilles extended beyond the housing after the first relocation. All four now fit between the central stairhouse and the +/-8 m housing sides; regression checks cover both inner clearance and outer bounds.
