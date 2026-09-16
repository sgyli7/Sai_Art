"""Record five real native scenarios and encode 150 captured frames each."""
from pathlib import Path
import subprocess,sys,os,json,shutil,argparse
O=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--only',nargs='*');a=p.parse_args()
ffmpeg=os.environ.get('FFMPEG_BIN',shutil.which('ffmpeg') or 'ffmpeg');media=O/'media';media.mkdir(exist_ok=True)
for mode,seconds,terrain,name in [('parked',43,'flat','cockpit_tour'),('cabin_patrol',24,'flat','cabin_patrol'),('worksite',43,'flat','worksite'),('sai_board',115,'flat','sai_boarding'),('hill_turn',55,'hills','hills')]:
 if a.only and name not in a.only:continue
 out=O/'reports'/('release_r032_'+name)
 subprocess.run([sys.executable,str(O/'source/launch.py'),'--game',str(a.game),'--mode',mode,'--seconds',str(seconds),'--terrain',terrain,'--view','cabin_tour' if name=='cockpit_tour' else 'whole','--pv','--clean-capture','--capture','--output',str(out)],check=True)
 assert len(list(out.glob('run_pv_*.png')))==150,(mode,'missing frames')
 log=(out/'run.log').read_text();assert 'SCRIPT ERROR' not in log and 'ERROR:' not in log,mode
 if mode in ['worksite','cabin_patrol']:
  robot=json.loads((out/'robot_patrol.json').read_text());assert robot['first_fall'] is None and not robot['error'],robot
 if mode=='sai_board':
  robot=json.loads((out/'sai_boarding.json').read_text());assert robot['completed'] and not robot['failure'],robot
 else:assert not json.loads((out/'run.json').read_text())['failed']
 target=media/f'Sainiverse_v0.1_{name}.gif'
 subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-framerate','15','-i',str(out/'run_pv_%04d.png'),'-filter_complex','scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=3','-loop','0',str(target)],check=True)
 print(target,flush=True)
