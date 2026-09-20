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
        shutil.copy2(TESTS / "interaction_ui_probe.gd", project / "interaction_ui_probe.gd")
        drive_probe = (TESTS / "interaction_drive_probe.gd.in").read_text().replace(
            "@DRIVE_SCRIPT@", str(drive)
        )
        (project / "interaction_drive_probe.gd").write_text(drive_probe)
        failed = False
        for name in ("interaction_ui_probe.gd", "interaction_drive_probe.gd"):
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
