#!/usr/bin/env python3
"""Check a rendered Sainiverse dual-control camera probe output directory.

Run manual mode with SAINIVERSE_REMOTE_PROBE=1, SAINIVERSE_CAMERA_PROBE=1,
SAINIVERSE_CAMERA_PROBE_HIDE_UI=1, SAINIVERSE_CAMERA_PROBE_IGNORE_MOUSE=1,
SAINIVERSE_DUAL_PROBE_STEER=1, and SAINIVERSE_DRIVE_PROBE=0 for 26 seconds.
"""

import argparse
import json
import math
from pathlib import Path


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1)]


def check(output: Path) -> dict:
    motion = json.loads((output / "camera_motion.json").read_text())
    switches = json.loads((output / "robot_switches.json").read_text())
    run = json.loads((output / "run.json").read_text())
    samples = switches["remote_probe"]
    window = [row for row in motion if 20 <= row["sim_time"] < 25.5]
    steps = []
    lag = []
    for before, after in zip(window, window[1:]):
        dt = (after["wall_usec"] - before["wall_usec"]) / 1_000_000
        if 0.001 < dt < 0.02:
            steps.append(math.dist(before["camera_carrier_local"], after["camera_carrier_local"]))
            lag.append(math.dist(before["target_carrier_local"], before["raw_robot_carrier_local"]))
    assert not run["failed"] and len(steps) >= 100, "Rendered camera probe did not complete"
    assert {row["quick_location"] for row in window} in ({2}, {3}), "MD camera left its locked view"
    assert max(row["car_speed_m_s"] for row in samples) >= 5, "Sainiverse did not drive"
    assert sum(row["car_left"] for row in samples) > 0 and sum(row["car_right"] for row in samples) > 0, "Carrier did not turn both ways"
    assert sum(row["robot_forward"] for row in samples) > 0 and not any(row["robot_fall"] for row in samples), "MicroDuck did not move upright"
    result = {
        "samples": len(steps),
        "camera_view": window[0]["quick_location"],
        "max_car_speed_m_s": max(row["car_speed_m_s"] for row in samples),
        "camera_carrier_step_p95_m": percentile(steps, 0.95),
        "camera_carrier_step_max_m": max(steps),
        "target_to_robot_lag_p95_m": percentile(lag, 0.95),
    }
    assert result["camera_carrier_step_p95_m"] <= 0.01, result
    assert result["target_to_robot_lag_p95_m"] <= 0.05, result
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(json.dumps(check(parser.parse_args().output), indent=2))
