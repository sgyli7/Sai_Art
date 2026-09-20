"""Exercise the real Sainiverse input and operation UI scripts in Godot."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
SOURCE = ROOT / "vehicles/Sainiverse_v0.1/runtime"


def main() -> int:
    subprocess.run([sys.executable, str(ROOT / "run.py"), "--action", "prepare"], check=True)
    drive = ROOT / ".runtime/Sainiverse_v0.1/runtime/drive.gd"
    with tempfile.TemporaryDirectory(prefix="sainiverse-interactions-") as scratch:
        project = Path(scratch)
        (project / "project.godot").write_text('config_version=5\n[application]\nconfig/name="Sainiverse interactions"\n')
        shutil.copy2(SOURCE / "operation_ui.gd", project / "operation_ui.gd")
        shutil.copy2(SOURCE / "microduck_remote.gd", project / "microduck_remote.gd")
        shutil.copy2(TESTS / "interaction_ui_probe.gd", project / "interaction_ui_probe.gd")
        shutil.copy2(TESTS / "microduck_style_probe.gd", project / "microduck_style_probe.gd")
        (project / "standalone").mkdir()
        (project / "standalone" / "driver.gd").write_text("""extends Node3D
var brain:Dictionary={"limits":{}}
var motion:Dictionary={"settings":{},"target_yaw":0.0,"started":false}
var _bodies:Dictionary={}
var session:Dictionary={"steps":0,"first_fall":null}
var measured_speed_mps:float=0.0
var _base:Node3D
func _ready()->void:pass
func _g2m(value:Vector3)->Vector3:return value
func _m2g(value:Vector3)->Vector3:return value
func _handle(_command:Variant)->void:pass
func _decide(_held:Array,_taps:Array,_order:Array,_elapsed:float)->bool:return true
""")
        visuals = ROOT / "integration/robots/visuals/microduck"
        visual_dir = project / "visuals" / "microduck"
        visual_dir.mkdir(parents=True)
        for name in ("style.gd", "enamel.gdshader", "ink.gdshader", "lens.gdshader", "robot_parts.json"):
            shutil.copy2(visuals / name, visual_dir / name)
        drive_probe = (TESTS / "interaction_drive_probe.gd.in").read_text().replace(
            "@DRIVE_SCRIPT@", str(drive)
        )
        (project / "interaction_drive_probe.gd").write_text(drive_probe)
        failed = False
        for name in ("interaction_ui_probe.gd", "interaction_drive_probe.gd", "microduck_style_probe.gd"):
            result = subprocess.run(
                ["godot", "--headless", "--path", str(project), "--script", f"res://{name}"],
                capture_output=True,
                text=True,
            )
            print(f"{name}: exit {result.returncode}")
            print((result.stdout + result.stderr).strip())
            failed |= result.returncode != 0 or "SCRIPT ERROR:" in result.stderr or "Parse Error:" in result.stderr
        return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
