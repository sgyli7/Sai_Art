"""Appearance-envelope registration before the p13 illustration edit.

The dimensions below are manually read visible envelopes in the p11 drawing.
They are neither recovered CAD surfaces nor measured joint axes. Ellipsoid
volumes are used only as an equal-density visual-volume surrogate; no real
component masses, collision bodies or mechanical properties are modified.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMAGE = ROOT / "images/gorilla_four_view_pixal_lower_candidate_p11.png"

# LEFT faces toward decreasing image x. Dimensions: lateral, fore/aft, height.
# All entries use the original 1254 px sheet's scale, not physical units.
BASELINE = [
    dict(part="core_envelope", count=1, center_x=922.0, size=[240, 230, 228]),
    dict(part="thigh_envelopes", count=2, center_x=869.0, size=[120, 152, 212]),
    dict(part="shank_envelopes", count=2, center_x=952.0, size=[64, 88, 101]),
    dict(part="foot_envelopes", count=2, center_x=924.0, size=[128, 280, 65]),
    dict(part="arm_envelopes", count=2, center_x=976.0, size=[74, 85, 282]),
    dict(part="hip_envelope", count=1, center_x=946.0, size=[72, 84, 65]),
    dict(part="shoulder_envelopes", count=2, center_x=978.0, size=[86, 86, 85]),
]


def volume_center(parts):
    weights = [p["count"] * math.pi / 6 * math.prod(p["size"]) for p in parts]
    return sum(w * p["center_x"] for w, p in zip(weights, parts)) / sum(weights)


def main():
    target = json.loads(json.dumps(BASELINE))
    for part in target:
        if part["part"] in ("core_envelope", "thigh_envelopes"):
            # Retract only the forward envelope; keep its rear plane fixed.
            part["size"][1] -= 25
            part["center_x"] += 12.5
    for before, after in zip(BASELINE, target):
        assert before["size"][0] == after["size"][0]  # Frontal widths locked.
        assert before["size"][2] == after["size"][2]  # No height compensation.
        assert abs((before["center_x"] + before["size"][1] / 2)
                   - (after["center_x"] + after["size"][1] / 2)) < 1e-9
    support = [784.0, 1064.0]
    midpoint = sum(support) / 2
    before_center, after_center = volume_center(BASELINE), volume_center(target)
    report = {
        "basis_image": str(IMAGE.relative_to(ROOT)),
        "basis_sha256": hashlib.sha256(IMAGE.read_bytes()).hexdigest(),
        "scope": "manual illustration envelopes and orthographic registration intent",
        "coordinates": "Original sheet pixels; LEFT faces decreasing x; no physical scale assigned",
        "foot_contact_hull_extremes_x_px": support,
        "foot_contact_hull_midpoint_x_px": midpoint,
        "baseline_envelopes": BASELINE,
        "target_envelopes": target,
        "equal_density_visual_volume_surrogate": {
            "baseline_x_px": before_center,
            "target_x_px": after_center,
            "baseline_offset_from_contact_midpoint_px": before_center - midpoint,
            "target_offset_from_contact_midpoint_px": after_center - midpoint,
        },
        "registration_checks": {
            "frontal_component_widths_unchanged": True,
            "component_heights_unchanged": True,
            "rear_envelope_planes_unchanged": True,
            "feet_shanks_arms_shoulders_and_hip_envelopes_unchanged": True,
        },
        "limitations": [
            "Manual envelopes have uncertainty and omit concavities, overlap and hidden geometry.",
            "Equal-density visual volumes are not component masses or an actual center of mass.",
            "This does not validate joint kinematics, collision clearance or load-bearing capability.",
            "Generated artwork must be inspected independently; this plan does not certify its execution.",
        ],
    }
    out = ROOT / "side_layout_plan_p13.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report["equal_density_visual_volume_surrogate"], indent=2))


if __name__ == "__main__":
    main()
