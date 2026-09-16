# Third-party material

Sai_Agent_001's original code, shell, brackets and independent dimensional
envelopes are provided under Apache-2.0. Upstream material retains its provenance
and license; this file does not grant rights to omitted vendor CAD.

## SO101

Source: [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100/tree/eecbe3e0a9ebb23e25ad7b2759b03884c6660903),
commit `eecbe3e0a9ebb23e25ad7b2759b03884c6660903`.
The source `STEP/SO101/SO101 Assembly.step` has SHA256
`f754be35708382b05ce65768ae33c612f91dca11ad19d14807dc637eb944ba3d`.
License: [Apache-2.0](licenses/SO101-Apache-2.0.txt), as supplied by that upstream
repository. Changes: split into physical links, placed at the audited arm pose,
recolored, tessellated, contact-decomposed and combined with original mounts.
This basis does not assert separately obtained permissions from every supplier
whose parts may appear in the upstream assembly, or imply supplier endorsement.

## Raspberry Pi 5 mechanical model

Source: [Raspberry Pi official product resources](https://pip.raspberrypi.com/categories/892-raspberry-pi-5).
Copyright Raspberry Pi Ltd 2026. The downloaded model includes an explicit MIT
license and third-party redistribution statement, reproduced in full in
[RaspberryPi5-MIT.txt](licenses/RaspberryPi5-MIT.txt), including its disclaimer.
Changes: split, tessellated and positioned in the chassis.

## Vendor hardware represented by independent envelopes

Original detailed CAD for CubeMars actuators, goBILDA wheels/drive parts,
Waveshare boards, Pololu boards and Phidgets sensors is not redistributed here.
Public display models use independently generated cylinders or boxes at the
audited mounting frames and dimensional bounds. A vendor label is omitted.
These envelopes are installation/display approximations, not manufacturing
models or a claim of vendor authorization. The original collision model,
actuator frames and provisional inertia estimates are preserved separately.

The part-by-part record is [asset_provenance.json](models/asset_provenance.json).

## Runtime and training dependencies

MuJoCo, MuJoCo Warp, Warp, PyTorch, rsl_rl, NumPy, trimesh and ONNX Runtime are
external dependencies, not relicensed by this project. Python packages are
installed from their distributions with their own license material. Any future
binary bundle must carry the licenses of the components it actually contains.
