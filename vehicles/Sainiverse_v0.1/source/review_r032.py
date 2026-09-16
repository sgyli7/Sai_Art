"""Reproduce focused r032 source checks and native close-view inspection captures."""
import subprocess,sys,json
from pathlib import Path
O=Path(__file__).resolve().parents[1]
def run(*args):subprocess.run([sys.executable,*map(str,args)],cwd=O,check=True)
run('source/build.py');run('source/prepare_physics.py');run('source/check_review_r032.py');run('source/check_boarding_envelope.py')
for view,theme in [('interior','black'),('controls','black'),('cockpit_rear','black'),('stairs','black'),('lounge','black'),('pedestal','black'),('underbody_detail','black'),('lift_detail','black'),('interior','blue'),('interior','white'),('interior','yellow')]:
 out=O/'reports'/f'r032_review_{view}_{theme}'
 run('source/launch.py','--mode','parked','--view',view,'--theme',theme,'--seconds','10','--capture','--clean-capture','--output',out)
 log=(out/'run.log').read_text();assert 'SCRIPT ERROR' not in log and 'ERROR:' not in log,view
 r=json.loads((out/'run_interior.json').read_text());assert all(q['hit'] and q['error_m']<.025 for q in r['floor_rays']),(view,[q for q in r['floor_rays'] if not q['hit'] or q['error_m']>=.025])
 print('REVIEW_OK',view,theme,flush=True)
