# Review validation · 2026-09-16

## What changed

- Exterior and indoor surfaces now share authored semantic albedo/normal atlases: steel deck pressings, paint, metal, rubber, cargo roofs, walls, console panels, workshop and ceiling finishes. Detail placement is tied to part-local surfaces and intended functions.
- Platform sides use the main theme pigment (black in the default theme), and are excluded from steel tread UV mapping. Walking surfaces retain the uniform grey steel finish.
- Squared service building hierarchy restored. Continuous middle-house foundation, capsule receiver ends, cooling pipe collars and antenna flanges added. Protruding vertical seam strips and the inner service-door rail barrier removed; exterior edge guards retained.
- Container roof ribs were replaced by mapped pressings. The final mesh has 1,340,240 triangles, with 273 batched render meshes and 51 moving visual groups. Fine detail is primarily mapped; the entire vehicle is not a low-poly asset.
- Labels use face-local aspect ratios and face orientation; readable interior/back-face label UVs were corrected after the first portable interior check. Industrial user-supplied marks supplement original service labels. Animal graphics are excluded.

## Texture audit

`evidence/surface_coverage.json` measures assigned triangle surface area, including hidden faces. Overall assigned coverage is **99.82%** and indoor coverage **99.36%** (551 of 559 indoor parts). Actual exported GLB UV2 buffers were audited separately. These figures measure mapped surfaces, not artistic quality, visible dirt coverage or an independent visual acceptance score. Transparent/display surfaces are intentionally handled separately.

Exterior, cabin and workshop screenshots are native Godot renders. UV0 still carries live wheel/belt motion metadata; UV2 carries the surface atlas. No per-frame texture generation was introduced.

## Native hills / GIF

`evidence/final_hills_pv` and `hills_summary.json` record a 55-second native Godot/Jolt run over a finite 5 m rounded hill plus uneven and left/right-offset hard-ground relief. Peak speed was **20.40 km/h**. The front body travelled from x≈47.72 m/z≈11.92 m at 24 s, through x≈83.37 m/z≈14.24 m at 32 s, to x≈126.18 m/z≈11.65 m at 42 s and x≈168.57 m/z≈9.84 m at 55 s. This demonstrates ascent, crest passage and descent on this fixture.

The 10-second GIF is 150 frames at 15 fps, captured from simulation time 32–42 s. It contains whole-vehicle and bogie views; it is live contact simulation, not a pose animation. A final label UV orientation correction followed recording; vehicle geometry, suspension, terrain and camera route are identical. The companion MP4 is supplied for a smaller playback file.

Bogie heave ranged approximately −0.377 to +0.377 m; roadwheel travel −0.350 to +0.342 m. Maximum measured joint-anchor residual was 0.0162 m. Front/rear/tail RMS vertical accelerations after settling were 4.03/1.76/0.96 m/s². The front cabin still experiences appreciable disturbance: this is not proof of a comfort target or of universally smooth transport. No claim of SnowRunner-equivalent mud/snow simulation is made.

## Boarding mechanisms

The native lift test (`native_lift_datum_fixed`) ran 75 seconds with six finite-force mechanisms and a 500 kg contact witness on one platform. A corrected 0.11 m nominal/loaded hull datum mismatch aligned visual and physical platforms. All six platforms contacted the ground in all 480 samples during the 38–46 s contact window; measured underside gaps were approximately −0.20 to +0.074 mm. They returned to stowed positions and released the driving interlock. The witness remained supported.

A separate actual MuJoCo 75-second cycle completed with finite 60 kN actuator limits, finite states and all six lifts retracted. In the settled lowering window, underside gaps were approximately −0.015 to +0.629 mm, with intermittent solver contacts. The same check passed from the portable bundle without the original candidate paths.

These are mechanism checks, not a trained Sai/MicroDuck boarding policy. A grounded 250 mm thick platform still requires a step/ramp solution for a fully step-free robot route. Dynamic loaded crane operations, the receiver slew/fold system and hardware qualification remain unfinished.

## Portability and source

Portable materialization and native Godot loading were checked inside the existing Robot_Godot_Sim2Sim checkout. Editable Blender 4.0.2 authoring completed with 21,894 named parts and nine packed images. The supplied native extension is verified on Linux ARM64 only. Windows/macOS/x86 binaries are not included as tested deliverables.

Performance measurement and the final source hashes are recorded alongside this file in the evidence summary. Capture runs are not used to assert realtime frame rate.

## Final straight-line performance

The final portable bundle ran for 180 s at 1920×1080, Forward+, 4× MSAA, 200 Hz physics on NVIDIA GB10 / Godot 4.7.2. Peak speed was **100.0001 km/h** on flat prepared ground. Median frame rate was **94.13 FPS**, mean **86.68 FPS**; p95 frame time **16.50 ms**, p99 **20.22 ms**, across 15,342 timed frames. No screenshot capture was enabled. Simulation/wall ratio was approximately **0.992**. Native track extension and uploaded state texture verification passed; maximum wheel/idler binding errors were below 0.046 mm. These measurements apply to this fixture, machine and camera; they do not guarantee 94 FPS on other systems or terrains. See `evidence/final_straight180/performance_summary.json`.
