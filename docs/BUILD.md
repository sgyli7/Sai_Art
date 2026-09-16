# Editable sources and rebuilding

`run.py --action prepare` expands relative bundle paths into `.runtime/Sainiverse_v0.1`. Work on a copy of that directory when experimenting; a later `run.py` refresh will restore packaged source files.

Using the requirements environment:

```bash
python run.py --action prepare
python .runtime/Sainiverse_v0.1/source/build.py
python .runtime/Sainiverse_v0.1/source/prepare_physics.py
python .runtime/Sainiverse_v0.1/source/audit_glb.py
blender -b --python .runtime/Sainiverse_v0.1/source/blender_authoring.py
```

Blender authoring was tested with Blender 4.0.2. It creates individually named mesh objects, physical-body parents, the lift hierarchy, packed images and editable material nodes. The game export batches matching body/material geometry to 280 meshes. The artwork source is not generated inside Godot.

The carrier physics remains a reduced contact model: 223 bodies, 214 joints, finite-force hydraulic suspension/traction and simplified compliant belt contact. The visual belt is reconstructed from the corresponding live wheel/track state. It is not a chain of individually simulated steel links.

## Native track extension

The Linux ARM64 prebuilt library lives under `support/native/bin`. The supplied C++ source uses godot-cpp commit `6cceaf6a5f8b0d78ac5d71c139fd7fabba43b918`; obtain that dependency separately. The exact exported Godot API JSON used for the build is included under `support/native/api`.

```bash
cmake -S .runtime/Sainiverse_v0.1/support/native -B /tmp/sai-track-build \
  -DGODOT_CPP_PATH=/absolute/path/to/godot-cpp -DCMAKE_BUILD_TYPE=Release
cmake --build /tmp/sai-track-build -j2
```

The packaged extension descriptor currently selects the verified Linux ARM64 binary. Builds for other architectures require matching descriptor entries and native runtime verification; those platforms are not claimed as tested.

The `support/source` directory also preserves earlier diagnostic helpers. Some reference historical local experiments; the supported portable entrypoints are `run.py`, `source/build.py`, `source/prepare_physics.py`, `source/audit_glb.py` and `source/blender_authoring.py`.
