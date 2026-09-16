# Industrial electrical cabinet resources — optional equipment-room use

Downloaded 2026-09-17. **Do not use these as cockpit pilot consoles.** Both were actually rendered and visually inspected: the “terminal” is a tall electrical enclosure with mesh doors, ventilation and two maintenance steps; the tank panel is a small cabinet with conduit. There are no usable detailed pilot controls or seat in this subset. They are plausible equipment-room props, not An-225 cockpit replicas. Retain only where their function makes sense.

## Sources and license

- Original author rubberduck: https://opengameart.org/content/high-quality-industrial-asset-pack — author states models and textures CC0 (some texture inputs by Yughues); the preview background has a separate license and is not included.
- Blender 4.0 repack author a52: https://opengameart.org/content/pbr-industrial-asset-pack — CC0. The author explicitly notes that baked variants lack newly converted metallic/roughness maps.
- Download: https://opengameart.org/sites/default/files/oga_industrial_a52_version_baked_models_0.zip
- License: https://creativecommons.org/publicdomain/zero/1.0/
- Suggested optional credit: “Industrial equipment: rubberduck, Blender repack by a52; some source textures by Yughues; CC0.”

## Supplied files and conversion

`control_terminal.obj` / `.glb`: 152 triangles. `tank_control_panel.obj` / `.glb`: 322 triangles. Each has one material, UVs, 1024 px diffuse and tangent-space normal image. AO and original spec maps are preserved separately. GLB embeds diffuse and normal, uses constant roughness 0.78 and metalness 0 as an explicit conservative conversion choice; specular was not mislabelled as metalness. Original baked images are unchanged.

OBJ was exported through Blender 4.0.2, GLB through trimesh because the local Blender glTF exporter lacks `_ctypes`. Bounds, exact counts and GLB hashes are in MODEL_REPORT.json. GLB/OBJ are +Y up. Imported source dimensions are arbitrary author units (terminal height 6.295; cabinet height 3.480), **not human-scale metres**. Choose uniform scale from desired installed height; set bottom to floor from recorded minimum Y. E.g. a 2.05 m tall terminal requires scale 2.05 / 6.29523, but its little steps and excessive depth mean it should remain an optional maintenance prop. Do not stretch axes independently or use it to close a passage.

`control_terminal_preview.png`, `control_terminal_front_preview.png`, and `tank_control_panel_preview.png` were rendered from the source for inspection. The dark rear preview exposes the original open back: place cabinet back against a wall or add a cap where needed. It is not a watertight collision mesh. No collision or physics verification has been performed. Geometry is cheap, but keep the normal and texture use compatible with the existing toon shader rather than adding a separate photoreal shader.

## Selection outcome

No freely downloadable, license-clear, low-poly industrial **pilot seat** meeting the current visual target was found during this bounded research pass. Kenney Space Station Kit CC0 models are available in the adjacent folder but were rejected for hero cockpit use after preview inspection: 118–176 triangles and overly simplistic forms. Do not install them merely to claim an external asset was used. Further work should refine the project's seat back shell, adjustment rails, armrests, harness and controls, or obtain a more suitable authored model.
