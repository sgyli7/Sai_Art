"""Native, same-camera theme and near-field review. Images are inspection evidence,
not an automatic assertion that an artistic quality target has been met.
"""
from pathlib import Path
import subprocess,sys,json
O=Path(__file__).resolve().parents[1]
def run(*args):subprocess.run([sys.executable,*map(str,args)],cwd=O,check=True)
for script in ['build.py','prepare_physics.py','check_cockpit_geometry.py','check_cockpit_mujoco.py','check_review_r032.py','check_boarding_envelope.py']:run('source/'+script)
for view,theme in [('controls','black'),('instrument_detail','black'),('engineer_detail','black'),('seat_detail','black'),*[("interior",t) for t in ['black','blue','white','yellow','desert']]]:
 out=O/'reports'/f'r032_final_{view}_{theme}'
 run('source/launch.py','--mode','parked','--view',view,'--theme',theme,'--seconds',10,'--capture','--clean-capture','--output',out)
 log=(out/'run.log').read_text();assert 'SCRIPT ERROR' not in log and 'ERROR:' not in log,(view,log[-3000:])
 assert (out/'run_9.0.png').exists()
 print('NATIVE_CAPTURE',view,theme,flush=True)
