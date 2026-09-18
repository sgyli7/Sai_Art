"""Short rendered regression for the foldable runtime UI performance."""
from pathlib import Path
import json
import statistics
import subprocess
import sys
import time
import argparse

O = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["manual", "ui_test"], default="ui_test")
parser.add_argument("--seconds", type=float, default=12.0)
args = parser.parse_args()
out = O / "reports" / ("ui_fps_" + time.strftime("%Y%m%d_%H%M%S"))
subprocess.run(
    [
        sys.executable,
        str(O / "source" / "launch.py"),
        "--mode",
        args.mode,
        "--seconds",
        str(args.seconds),
        "--output",
        str(out),
    ],
    cwd=O,
    check=True,
)
frames = json.loads((out / "run_visual.json").read_text())["frames"]
steady = [float(row["frame_ms"]) for row in frames if float(row["simulation_s"]) >= 3.0]
median_ms = statistics.median(steady)
fps = 1000.0 / median_ms
print(json.dumps({"mode": args.mode, "median_frame_ms": median_ms, "median_fps": fps, "samples": len(steady), "report": str(out)}, indent=2))
if fps < 30.0:
    raise SystemExit("UI_FPS_REGRESSION: median rendered FPS is below 30")
