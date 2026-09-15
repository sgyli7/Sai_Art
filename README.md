# Sai_Design · Sainiverse 001 / 赛思黑 001

Private design review delivery. This repository contains the editable vehicle assembly, four colour themes, authored texture generators, Godot/Jolt driving review and a matching MuJoCo mechanism check. It is separate from Sai_Rotbots.

## Open the review

Use your existing **Robot_Godot_Sim2Sim** checkout and Godot 4.7 with Jolt. The supplied native track extension is built for **Linux ARM64**; other platforms need an extension build. No new game checkout is required.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py --game /absolute/path/to/Robot_Godot_Sim2Sim/main
```

Set `GODOT_BIN` when Godot is not on PATH. All generated absolute paths live in the ignored `.runtime/` cache. The existing game's project settings are restored on exit.

- W/S: drive/reverse. A/D: steer. Shift+W: high-speed target. Space: brake.
- Tab: camera. Hold right mouse: orbit. Wheel: zoom. Free view: WASD and Q/E.
- G: select lift. L: deploy/retract. Shift+L: all six. Driving waits for the lifts to stow.
- O: doors. T: black/desert/white/blue themes. F12: screenshot. Esc: exit.

```bash
# Hills and uneven hard ground; manually drive, or use the measured traversal controller.
.venv/bin/python run.py --game /path/to/main --terrain hills
.venv/bin/python run.py --game /path/to/main --terrain hills --mode traverse --seconds 60
# Indoor inspection
.venv/bin/python run.py --game /path/to/main --view interior
.venv/bin/python run.py --game /path/to/main --view workshop
# MuJoCo lift cycle and editable Blender source
.venv/bin/python run.py --action mujoco
.venv/bin/python run.py --action unpack-blend
```

## Design in this review

Theme black covers body and platform sides. Grey steel tread is confined to walking surfaces. Yellow cranes, restrained red identity bands and industrial service markings retain their own roles. Rounded cabin roof and capsule receiver contrast with squared service buildings. A continuous foundation closes the middle house/deck gap; internal rail barriers and protruding seam blocks are removed. Antenna roots and cooling connections have actual sockets/collars.

The surface atlas uses authored panel lines, steel pressings and broad sparse wear, with separate normal maps and aspect-preserving labels. It includes floors, walls, consoles, workshop furniture and ceilings. No cartoon animal stickers are used. Coverage is measured surface assignment, not a claim that every pixel should be dirty.

## Files

- `vehicles/Sainiverse_001/source/Sainiverse_001.blend.gz`: compressed editable Blender assembly; unpack using the command above.
- `vehicles/Sainiverse_001/assets/sainiverse001.glb`: neutral named-body mesh export. Runtime materials and the dynamic track shader are supplied separately.
- `vehicles/Sainiverse_001/source/`: assembly, texture generation and export sources.
- `vehicles/Sainiverse_001/physics/`: MJCF, native body/joint specification and controller settings.
- `vehicles/Sainiverse_001/themes/`: black, desert, white and blue palettes.
- `evidence/`: final screenshots, measured reports and the approximately 10-second driving GIF.
- `docs/VALIDATION.md`: evidence, measurement conditions and unverified requirements.

## Scope and provenance

This is a manually drivable conceptual design, not a hardware-certified vehicle or a trained end-to-end robot boarding policy. Cranes and receiver movement are not yet a validated SnowRunner-level handling system in this delivered runtime. The terrain is hard-ground contact; it does not simulate SnowRunner mud deformation. The 100 km/h command is for the prepared straight test, not the hill route.

User-supplied sticker assets are retained only as selected industrial examples for this private review. See `docs/THIRD_PARTY.md` and the detailed source records under the vehicle docs. No blanket open-source license is assigned to those assets.
