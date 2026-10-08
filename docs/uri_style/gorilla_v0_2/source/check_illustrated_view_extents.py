"""Read-only raster alignment audit; this does not certify 3D geometry.

Run with the ComfyUI Python runtime (Pillow, NumPy and SciPy available).
The source pixels are never modified. Text and frame components are excluded
before measuring the visible extents of each illustrated robot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def audit(image_path: Path) -> dict:
    rgb = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.int16)
    height, width = rgb.shape[:2]
    panel_w, panel_h = width // 2, height // 2
    extents = {}
    for name, ox, oy in (
        ("FRONT", 0, 0),
        ("LEFT", panel_w, 0),
        ("REAR", 0, panel_h),
        ("TOP", panel_w, panel_h),
    ):
        margin = 10
        roi = rgb[oy + margin:oy + panel_h - margin,
                  ox + margin:ox + panel_w - margin]
        lo, hi = roi.min(axis=2), roi.max(axis=2)
        mask = ((hi < 215) | ((hi - lo > 16) & (lo < 245))).astype(np.uint8)
        labels, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=np.uint8))
        areas = np.bincount(labels.ravel())
        keep = np.zeros_like(mask, dtype=bool)
        component_areas = []
        for label in range(1, count + 1):
            area = int(areas[label])
            if area >= 250:
                keep |= labels == label
                component_areas.append(area)
        yy, xx = np.nonzero(keep)
        if not len(xx):
            raise ValueError(f"No usable subject components in {name}")
        bbox = [int(xx.min()) + margin, int(yy.min()) + margin,
                int(xx.max()) + margin, int(yy.max()) + margin]
        extents[name] = {
            "bbox_panel_px": bbox,
            "visible_width_px": bbox[2] - bbox[0] + 1,
            "visible_height_px": bbox[3] - bbox[1] + 1,
            "retained_component_areas_px": sorted(component_areas, reverse=True),
        }
    heights = [extents[n]["visible_height_px"] for n in ("FRONT", "LEFT", "REAR")]
    top_width = extents["TOP"]["visible_width_px"]
    front_width = extents["FRONT"]["visible_width_px"]
    top_depth = extents["TOP"]["visible_height_px"]
    left_depth = extents["LEFT"]["visible_width_px"]
    height_spread = (max(heights) - min(heights)) / (sum(heights) / 3)
    width_error = top_width / front_width - 1
    return {
        "image": str(image_path.resolve()),
        "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
        "dimensions_px": [width, height],
        "measurement_scope": "visible raster extents after frame/text exclusion",
        "limitations": [
            "Antialiasing, highlights, shadows and disconnected small features affect extents.",
            "This is not proof of common 3D geometry, source fidelity, collision clearance or load capacity.",
        ],
        "panels": extents,
        "elevation_height_spread_fraction": height_spread,
        "top_to_front_visible_width_ratio": top_width / front_width,
        "top_uniform_scale_to_match_front": front_width / top_width,
        "top_to_left_visible_depth_ratio": top_depth / left_depth,
        "top_depth_scale_to_match_left": left_depth / top_depth,
        "raster_alignment_findings": {
            "elevation_height_difference_exceeds_2_percent": height_spread > 0.02,
            "top_width_difference_exceeds_2_percent": abs(width_error) > 0.02,
            "top_depth_difference_exceeds_2_percent": abs(top_depth / left_depth - 1) > 0.02,
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.image)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in (
        "elevation_height_spread_fraction", "top_to_front_visible_width_ratio",
        "top_uniform_scale_to_match_front", "raster_alignment_findings")}, indent=2))
