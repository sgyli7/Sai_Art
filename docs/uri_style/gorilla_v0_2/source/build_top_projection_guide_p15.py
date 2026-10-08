"""Generate an analytic orthographic position guide, not a final robot model.

Lofted envelopes are manually registered to P13/P14 FRONT and LEFT. They
only constrain camera, plan extent and occlusion. They do not recover the
accepted shell surfaces, articulation axes, collisions, mass or engineering.
No source raster pixels are loaded or edited by this program.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
faces = []
parts = []


def add_loft(name, rings, shade):
    rings = [np.asarray(r, dtype=float) for r in rings]
    parts.append({"name": name, "rings_xyz": [r.tolist() for r in rings]})
    faces.append((rings[0], shade))
    faces.append((rings[-1], shade))
    for bottom, top in zip(rings, rings[1:]):
        for i in range(len(bottom)):
            j = (i + 1) % len(bottom)
            faces.append((np.asarray([bottom[i], bottom[j], top[j], top[i]]), shade))


def oval(name, cx, cy, rx, ry, z, shade, height=.06):
    theta = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    contour = np.column_stack((cx + rx * np.cos(theta), cy + ry * np.sin(theta)))
    add_loft(name, [np.column_stack((contour, np.full(24, z-height/2))),
                    np.column_stack((contour, np.full(24, z+height/2)))], shade)


def foot(side):
    # Y positive = rear. Feet splay outward 15 degrees, as in FRONT.
    length, width = 254/583, 95/583
    xy = np.asarray([[-.42, .48], [.42, .48], [.50, .30],
                     [.45, -.25], [.34, -.52], [-.38, -.52],
                     [-.50, -.25], [-.45, .30]]) * [width, length]
    yaw = side * math.radians(15)
    rotation = np.asarray([[math.cos(yaw), -math.sin(yaw)],
                           [math.sin(yaw), math.cos(yaw)]])
    xy = xy @ rotation.T + [side*.227, 0]
    add_loft(f"foot_{side}", [np.column_stack((xy, np.full(8, .025))),
                              np.column_stack((xy*.97+[side*.227*.03, 0], np.full(8, .105)))], .86)


def main():
    for side in (-1, 1):
        foot(side)
        oval(f"shank_{side}", side*.188, .028, .066, .075, .235, .76, .17)
        oval(f"fold_carrier_{side}", side*.155, .017, .072, .065, .332, .63, .05)
        oval(f"thigh_{side}", side*.145, -.085, .105, 127/583/2, .465, .78, .17)
        oval(f"knee_guard_{side}", side*.159, -.130, .084, .065, .332, .60, .065)
        oval(f"hip_{side}", side*.140, .044, .063, .062, .592, .66, .06)
        oval(f"shoulder_{side}", side*.230, .092, .076, .108, .875, .66, .065)
        oval(f"upper_arm_{side}", side*.290, .050, .061, .070, .755, .82, .06)
        oval(f"elbow_{side}", side*.318, .008, .047, .052, .640, .58, .05)
        oval(f"forearm_{side}", side*.333, -.021, .050, .085, .492, .70, .07)
        oval(f"hand_{side}", side*.337, -.101, .047, .055, .348, .81, .05)
    # Angular continuous wedge. These are envelope rings, not redesigned panels.
    def ring(w, front, rear, z):
        return [[-w*.70, rear, z], [w*.70, rear, z],
                [w, rear-.028, z], [w*.95, front+.085, z],
                [w*.28, front, z], [-w*.28, front, z],
                [-w*.95, front+.085, z], [-w, rear-.028, z]]
    add_loft("core", [ring(.058, -.177, .089, .660),
                      ring(.142, -.110, .188, .880),
                      ring(.111, -.018, .103, .994)], .94)
    oval("rear_hatch_rim", 0, .190, .060, .010, .925, .62, .015)
    all_vertices = np.concatenate([v for v, _ in faces])
    minimum, maximum = all_vertices.min(axis=0), all_vertices.max(axis=0)
    # Render new analytic polygons; no existing artwork raster is edited.
    canvas = Image.new("RGB", (1280, 960), "white")
    draw = ImageDraw.Draw(canvas)
    def project(vertex):
        return [(640 + x*1250, 470 - y*1250) for x, y, _ in vertex]
    for vertex, shade in sorted(faces, key=lambda f: f[0][:, 2].mean()):
        gray = int(shade*255)
        polygon = project(vertex)
        draw.polygon(polygon, fill=(gray, gray, gray))
        draw.line(polygon+[polygon[0]], fill="#56616c", width=2)
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 27)
        note_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 21)
    except OSError:
        title_font = note_font = ImageFont.load_default()
    draw.text((640, 70), "ORTHOGRAPHIC TOP - POSITION / OCCLUSION GUIDE", fill="#334455", font=title_font, anchor="mm")
    draw.text((640, 880), "FRONT DOWN | Envelopes only; retain artwork's shell design", fill="#334455", font=note_font, anchor="mm")
    out = ROOT / "images/top_projection_position_guide_p15.png"
    canvas.save(out)
    report = {
        "coordinate_frame": "+X lateral, +Y rear, +Z up; normalized drawing-height units",
        "camera": "Orthographic +Z looking straight down; X horizontal, +Y upwards on page",
        "scope": "Analytic envelope projection and overlap guide only; not final shell design or engineering",
        "basis_artwork": "images/gorilla_four_view_registration_p14.png",
        "parts": parts,
        "bounds_xyz": [minimum.tolist(), maximum.tolist()],
        "projected_top_span_px_at_583_px_per_unit": {
            "lateral": float((maximum[0]-minimum[0])*583),
            "fore_aft": float((maximum[1]-minimum[1])*583),
        },
        "actual_mass_collision_or_joint_validation": False,
        "output": str(out.relative_to(ROOT)),
    }
    (ROOT/"top_projection_position_guide_p15.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report["projected_top_span_px_at_583_px_per_unit"]))


if __name__ == "__main__":
    main()
