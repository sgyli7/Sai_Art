"""Build robot walk surfaces and low guard contacts from the authored model.

The visible lift and passage openings stay open. Source meshes and masses are
unchanged; these are mounted contact proxies for the three existing hulls.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def bounds(part: dict) -> tuple[list[float], list[float]]:
    vertices = part["vertices"]
    return ([min(v[i] for v in vertices) for i in range(3)],
            [max(v[i] for v in vertices) for i in range(3)])


def body_for(x: float) -> str:
    return "front" if x > -21 else "rear" if x > -63 else "tail"


def box(name: str, lo: list[float], hi: list[float]) -> dict:
    return {"name": name, "type": "box",
            "center_source_m": [(a + b) / 2 for a, b in zip(lo, hi)],
            "size_m": [b - a for a, b in zip(lo, hi)]}


def slope_guard(name: str, low: list[float], high: list[float], axis: int,
                bottom_at_low: float, bottom_at_high: float, height: float) -> dict:
    # A convex prism follows the stair incline and leaves its tread path open.
    vertices = []
    cross = 1 - axis
    for along, bottom in ((low[axis], bottom_at_low), (high[axis], bottom_at_high)):
        for across in (low[cross], high[cross]):
            for z in (bottom, bottom + height):
                point = [0., 0., z]
                point[axis] = along
                point[cross] = across
                vertices.append(point)
    return {"name": name, "type": "convex", "vertices_source_m": vertices}


def compile_contacts() -> dict:
    with gzip.open(ROOT / "source/assembly.json.gz", "rt") as stream:
        parts = json.load(stream)["parts"]
    binding = json.loads((ROOT / "bindings.json").read_text())
    groups = {name: {"body": name,
                     "datum_source_m": binding["groups"][name]["neutral_body_position_source_m"],
                     "layer": 8, "mask": 48, "preserve_body_material": True,
                     "shapes": []} for name in ("front", "rear", "tail")}

    for part in parts:
        name = part["name"]
        lo, hi = bounds(part)
        carrier = body_for((lo[0] + hi[0]) / 2)
        shapes = groups[carrier]["shapes"]

        if name.endswith(("_bridge_lower_landing", "_bridge_stair_tread", "_instrument_gallery_floor")):
            shapes.append(box("floor_" + name, lo, hi))

        if name.endswith(("_front_walkplate", "_rear_walkplate")):
            # These meshes have two solid strips either side of a real lift
            # cutout. A single bounding box would seal the lift opening.
            xs = sorted(set(round(v[0], 5) for v in part["vertices"]))
            assert len(xs) in (4, 6), name
            middle = len(xs) // 2
            for index, (left, right) in enumerate(((xs[0], xs[middle - 1]), (xs[middle], xs[-1]))):
                shapes.append(box(f"floor_{name}_{index}", [left, lo[1], lo[2]], [right, hi[1], hi[2]]))

        # The visible rails have a large open space below the bottom bar.
        # Give each railed span a thin protective panel through robot height.
        # Split spans remain split at boarding and cross-module passages.
        if "_walk_rail_boarding_split" in name and lo[2] < 8.2 and hi[0] - lo[0] > 1:
            shapes.append(box("guard_" + name, [lo[0], lo[1], 7.54], [hi[0], hi[1], 8.65]))
        elif "_front_end_rail_rail" in name and lo[2] < 8.2:
            shapes.append(box("guard_" + name, [lo[0], lo[1], 7.45], [hi[0], hi[1], 8.65]))
        elif "_bridge_outer_rail_rail" in name and lo[2] < 12.0:
            shapes.append(box("guard_" + name, [lo[0], lo[1], 11.35], [hi[0], hi[1], 12.52]))
        elif "_bridge_end_rail_rail" in name and lo[2] < 12.0:
            shapes.append(box("guard_" + name, [lo[0], lo[1], 11.35], [hi[0], hi[1], 12.52]))

        if "_bridge_stair_handrail" in name and lo[2] < 8.5:
            near = lo[1] < 0
            bottom_low, bottom_high = (7.59, 11.35) if near else (11.35, 7.59)
            shapes.append(slope_guard("guard_" + name, lo, hi, 1, bottom_low, bottom_high, 1.17))
        elif "_r032_internal_stair_handrail" in name:
            shapes.append(slope_guard("guard_" + name, lo, hi, 0, 7.66, 11.35, 1.08))

    return {"revision": "robot_walkable_contacts_r001",
            "scope": "Existing deck strips, exterior stairs, upper instrument gallery, and guards along visible rails. Lift gaps and cross-module passages remain open.",
            "groups": list(groups.values())}


def save() -> None:
    config = compile_contacts()
    (ROOT / "physics/walkable_contacts.json").write_text(json.dumps(config, indent=2) + "\n")
    for filename in ("native_spec.json", "parameters.json"):
        path = ROOT / "physics" / filename
        document = json.loads(path.read_text())
        target = document["contact"] if filename == "native_spec.json" else document
        target["walkable"] = config
        path.write_text(json.dumps(document, indent=2) + "\n")

    path = ROOT / "physics/suspended.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    asset = root.find("asset")
    for mesh in list(asset):
        if mesh.get("name", "").startswith("walkable_mesh_"):
            asset.remove(mesh)
    bodies = {body.get("name"): body for body in root.findall(".//body")}
    for group in config["groups"]:
        parent = bodies[group["body"]]
        for geom in list(parent.findall("geom")):
            if geom.get("name", "").startswith("walkable_"):
                parent.remove(geom)
        datum = group["datum_source_m"]
        for index, shape in enumerate(group["shapes"]):
            label = f"walkable_{group['body']}_{index}"
            attributes = {"name": label, "mass": "0", "group": "4", "contype": "8",
                          "conaffinity": "48", "friction": ".8 .002 .0002"}
            if shape["type"] == "box":
                center = [a - b for a, b in zip(shape["center_source_m"], datum)]
                half = [v / 2 for v in shape["size_m"]]
                attributes.update(type="box", pos=" ".join(f"{v:.10g}" for v in center),
                                  size=" ".join(f"{v:.10g}" for v in half))
            else:
                mesh_name = "walkable_mesh_" + group["body"] + "_" + str(index)
                vertices = [v - datum[i] for point in shape["vertices_source_m"] for i, v in enumerate(point)]
                ET.SubElement(asset, "mesh", name=mesh_name, vertex=" ".join(f"{v:.10g}" for v in vertices))
                attributes.update(type="mesh", mesh=mesh_name)
            ET.SubElement(parent, "geom", **attributes)
    ET.indent(root)
    tree.write(path, encoding="unicode")
    print({group["body"]: len(group["shapes"]) for group in config["groups"]})


if __name__ == "__main__":
    save()
