"""Reproduce the r015 fixture in the existing game's generated runtime.

Run serially with other native tests. Restores runtime project settings even
if a subprocess fails. Does not install or modify the drivable vehicle bundle.
"""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=Path('/home/ethan/Projects/Robot_Godot_Sim2Sim/main/results/leviathan003/runtime')
OUT=ROOT/'reports/articulation_r015/bench'
project=RUNTIME/'project.godot'
saved=project.read_bytes()
text=saved.decode()
assert 'velocity_steps=12' in text and 'position_steps=4' in text, 'Unexpected generated runtime settings; inspect before replacing'
subprocess.run([sys.executable,str(ROOT/'source/articulation_bench.py')],check=True)
try:
    project.write_text(text.replace('velocity_steps=12','velocity_steps=64').replace('position_steps=4','position_steps=8'))
    tested_project=project.read_bytes()
    with (OUT/'godot.log').open('w') as log:
        subprocess.run(['/home/ethan/.local/bin/godot','--headless','--fixed-fps','200',
                        '--path',str(RUNTIME),'--script',str(ROOT/'godot/articulation_bench.gd')],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
finally:
    project.write_bytes(saved)
assert project.read_bytes()==saved
assert 'ERROR:' not in (OUT/'godot.log').read_text()
sha=lambda data:hashlib.sha256(data).hexdigest()
(OUT/'run_source.json').write_text(json.dumps(dict(
    runtime_project_before_sha256=sha(saved),runtime_project_tested_sha256=sha(tested_project),
    runtime_project_restored=True,velocity_steps=64,position_steps=8,
    script_sha256={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [
        ROOT/'source/run_articulation_bench.py',ROOT/'source/articulation_bench.py',
        ROOT/'godot/articulation_bench.gd',ROOT/'design/articulation_candidate.json']}),indent=2)+'\n')
subprocess.run([sys.executable,str(ROOT/'source/check_articulation_bench.py')],check=True)
