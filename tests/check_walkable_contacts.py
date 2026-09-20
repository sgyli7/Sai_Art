"""Probe authored walkable surfaces and guards against the real Godot contacts."""

from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "vehicles/Sainiverse_v0.1"


def bounds(part: dict) -> tuple[list[float], list[float]]:
    vertices = part["vertices"]
    return ([min(v[i] for v in vertices) for i in range(3)],
            [max(v[i] for v in vertices) for i in range(3)])


def carrier_body(x: float) -> str:
    return "front" if x > -21 else "rear" if x > -63 else "tail"


def build_cases() -> dict:
    with gzip.open(SOURCE / "source/assembly.json.gz", "rt") as stream:
        parts = json.load(stream)["parts"]
    binding = json.loads((SOURCE / "bindings.json").read_text())
    datums = {name: binding["groups"][name]["neutral_body_position_source_m"]
              for name in ("front", "rear", "tail")}
    # The rendered groups below are the walking route, not decorative plates
    # on the bogies or cargo containers. Include both sides and all three hulls.
    floor_names = ("_continuous_floor", "_front_walkplate", "_rear_walkplate", "_bridge_walkdeck",
                   "_bridge_upper_landing", "_bridge_lower_landing", "_bridge_stair_tread",
                   "_r032_lounge_floor", "_r032_enclosed_connector_floor",
                   "_r032_internal_stair_tread", "_r032_engineer_seat_floor_plate",
                   "_instrument_gallery_floor", "_boarding_floor")
    upper_landings = [bounds(part) for part in parts if part["name"].endswith("_bridge_upper_landing")]
    cases = []
    for part in parts:
        name = part["name"]
        lo, hi = bounds(part)
        x, y = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        body = carrier_body(x)
        if name.endswith(floor_names):
            top = hi[2]
            if name.endswith("_bridge_stair_tread") and any(
                land_lo[0] <= x <= land_hi[0] and land_lo[1] <= y <= land_hi[1] and top < land_hi[2] - .04
                for land_lo, land_hi in upper_landings
            ):
                continue  # This authored tread is below the upper landing.
            samples = [(name, x)]
            if name.endswith(("_front_walkplate", "_rear_walkplate")):
                # The authored mesh has two strips and an opening for the lift.
                xs = sorted(set(round(v[0], 3) for v in part["vertices"]))
                middle = len(xs) // 2
                samples = [(name + ":aft", (xs[0] + xs[middle - 1]) / 2),
                           (name + ":fore", (xs[middle] + xs[-1]) / 2)]
            for label, sample_x in samples:
                cases.append(dict(name=label, body=carrier_body(sample_x),
                                  start=[sample_x, y, top + .25], finish=[sample_x, y, top - .40],
                                  expected=[sample_x, y, top], tolerance=.04))
        # A robot must not slip through the open air beneath these visible
        # rails. Query across the edge at its chassis height, above the deck.
        if "_bridge_outer_rail_rail" in name and lo[2] < 12.0:
            z = 11.56
            cases.append(dict(name=name + ":guard", body=body,
                              start=[x, y - .42 if y < 0 else y + .42, z],
                              finish=[x, y + .42 if y < 0 else y - .42, z],
                              expected=[x, y, z], tolerance=.16))
        if "_bridge_end_rail_rail" in name and lo[2] < 12.0:
            z = 11.56
            cases.append(dict(name=name + ":guard", body=body,
                              start=[x - .42, y, z], finish=[x + .42, y, z],
                              expected=[x, y, z], tolerance=.16))
        if "_walk_rail_boarding_split" in name and lo[2] < 8.2 and hi[0] - lo[0] > 1:
            z = 7.76
            cases.append(dict(name=name + ":guard", body=body,
                              start=[x, y - .42 if y < 0 else y + .42, z],
                              finish=[x, y + .42 if y < 0 else y - .42, z],
                              expected=[x, y, z], tolerance=.16))
        if "_front_end_rail_rail" in name and lo[2] < 8.2:
            z = 7.76
            cases.append(dict(name=name + ":guard", body=body,
                              start=[x - .42, y, z], finish=[x + .42, y, z],
                              expected=[x, y, z], tolerance=.16))
        if "_bridge_stair_handrail" in name and lo[2] < 8.5:
            z = (7.59 + 11.35) / 2 + .25
            cases.append(dict(name=name + ":guard", body=body,
                              start=[x - .42, y, z], finish=[x + .42, y, z],
                              expected=[x, y, z], tolerance=.16))
        if "_r032_internal_stair_handrail" in name:
            z = (7.66 + 11.35) / 2 + .25
            cases.append(dict(name=name + ":guard", body=body,
                              start=[x, y - .42, z], finish=[x, y + .42, z],
                              expected=[x, y, z], tolerance=.16))
    return {"datums": datums, "cases": cases}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", type=Path, default=Path(os.environ["SAI_GODOT_PROJECT"]) if os.environ.get("SAI_GODOT_PROJECT") else None)
    parser.add_argument("--only", default="", help="Run only cases whose authored name contains this text")
    args = parser.parse_args()
    if args.game is None:
        parser.error("Provide --game PATH or SAI_GODOT_PROJECT")
    contacts = json.loads((SOURCE / "physics/walkable_contacts.json").read_text())
    godot_shapes = sum(len(group["shapes"]) for group in contacts["groups"])
    mujoco_shapes = sum(geom.get("name", "").startswith("walkable_") for geom in
                        ET.parse(SOURCE / "physics/suspended.xml").findall(".//geom"))
    if godot_shapes != mujoco_shapes:
        parser.error(f"Godot/MuJoCo walkable contact count differs: {godot_shapes}/{mujoco_shapes}")
    subprocess.run([sys.executable, str(ROOT / "run.py"), "--action", "prepare"], check=True, capture_output=True)
    runtime = args.game / "results/leviathan003/runtime"
    if not (runtime / "project.godot").is_file():
        parser.error(f"Prepared Godot runtime missing: {runtime}")
    with tempfile.TemporaryDirectory(prefix="sainiverse-contacts-") as scratch:
        temp = Path(scratch)
        checks = temp / "checks.json"
        cases = build_cases()
        if args.only:
            cases["cases"] = [case for case in cases["cases"] if args.only in case["name"]]
            if not cases["cases"]:
                parser.error(f"No collision probe case matches {args.only!r}")
        cases["dynamic"] = not args.only
        checks.write_text(json.dumps(cases))
        source = (ROOT / ".runtime/Sainiverse_v0.1/runtime/drive.gd").resolve()
        probe = temp / "probe.gd"
        probe.write_text((ROOT / "tests/walkable_contact_probe.gd.in").read_text().replace("@DRIVE_SCRIPT@", str(source)))
        command = ["godot", "--headless", "--path", str(runtime), "--script", str(probe), "--",
                   f"spec={(ROOT / '.runtime/Sainiverse_v0.1/physics/native_spec.json').resolve()}",
                   f"bindings={(ROOT / '.runtime/Sainiverse_v0.1/bindings.json').resolve()}",
                   f"output_root={temp}", "output=run.json", "seconds=4", "mode=parked", "terrain=polar", "view=whole", f"checks={checks}"]
        result = subprocess.run(command, text=True, capture_output=True, timeout=90)
        print((result.stdout + result.stderr).strip())
        return result.returncode or int("SCRIPT ERROR:" in result.stderr or "Parse Error:" in result.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
