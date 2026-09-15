"""Install a named 003 launch entry in the existing game without replacing 001."""
from pathlib import Path
import shutil,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
GAME=Path('/home/ethan/Projects/Robot_Godot_Sim2Sim/main')
script=GAME/'run-leviathan003.sh'
text='''#!/usr/bin/env bash
set -euo pipefail
LEVIATHAN003_GAME="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LEVIATHAN003_DESIGN="${LEVIATHAN_DESIGN_ROOT:-/home/ethan/Projects/RobotDesign/Leviathan_001}"
export DISPLAY="${DISPLAY:-:1}" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
exec "$LEVIATHAN003_DESIGN/.venv/bin/python" "$LEVIATHAN003_DESIGN/vehicles/Leviathan_003/source/launch.py" --game "$LEVIATHAN003_GAME" "$@"
'''
if script.exists() and script.read_text()!=text:raise RuntimeError('Existing 003 launcher differs; inspect before replacing')
script.write_text(text);script.chmod(0o755)
# A portable model folder can be imported without the development source path.
destination=GAME/'integrations/leviathan003';destination.mkdir(parents=True,exist_ok=True)
for name in ['leviathan003.glb','physics.json','vehicle.xml','running_gear.json']:shutil.copy2(ROOT/'assets'/name,destination/name)
shutil.copy2(ROOT/'training/policy.json',destination/'policy.json')
shutil.copytree(ROOT/'assets/mj_meshes',destination/'mj_meshes',dirs_exist_ok=True)
for f in (ROOT/'godot').iterdir():
    if f.is_file():shutil.copy2(f,destination/f.name)
(destination/'README.md').write_text('''# Leviathan 003

模型与训练源位于 RobotDesign/Leviathan_001/vehicles/Leviathan_003。

从此游戏根目录运行 `./run-leviathan003.sh`。此目录是可导入资产和运行脚本，不是另一份游戏工程。
003 启动入口复用现有 03 极地地形与天空。原来的 001/F7 Sai 切换入口保留；本版 003 尚未接入 Sai 登车作业。

100 km/h 是平整硬地仿真速度。双刚体/32接触点运输近似；上装固定。
GLB 包含命名的 front/rear 和八个 bogie 组。源坐标 +X 前、+Y 左、+Z 上；runtime.gd 在 Godot 边界转换。
独立加载 assets/vehicle.xml 不会自动运行 Python 的接触控制；请使用设计包的 source/physics.py。

完整来源、简化边界和实测以设计包 README.md 和 reports/ 为准。
''')
(ROOT/'reports/game_install.json').write_text(json.dumps({'game':str(GAME),'launcher':str(script),'integration':str(destination),'files':{str(f.relative_to(destination)):hashlib.sha256(f.read_bytes()).hexdigest() for f in destination.rglob('*') if f.is_file()}},indent=2))
print(script)
