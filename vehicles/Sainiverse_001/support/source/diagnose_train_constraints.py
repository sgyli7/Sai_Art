"""Native reproduction at the actual three-section joint/contact boundary."""
from pathlib import Path
import argparse,json,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'candidates/r016_modular/train_containers_first/reports'
def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--seconds',type=float,default=115);p.add_argument('--start-x',type=float,default=0.);p.add_argument('--position-steps',type=int,default=8);p.add_argument('--rebase-distance',type=float,default=0.);args=p.parse_args()
    subprocess.run([sys.executable,str(ROOT/'source/run_suspension_native.py'),'--train','--containers-first','--label',args.label,'--speed','27.7777777778','--seconds',str(args.seconds),'--brake-at','75','--start-x',str(args.start_x),'--position-steps',str(args.position_steps),'--rebase-distance',str(args.rebase_distance)],check=True)
    result=json.loads((OUT/(args.label+'.json')).read_text())
    residual=result['maximum_all_step_joint_anchor_residual_m']
    print('NATIVE_ANCHOR_CHECK',json.dumps(dict(measured_m=residual,limit_m=.01,passed=residual<=.01)))
    for name,peak in sorted(result.get('joint_anchor_peaks',{}).items(),key=lambda x:x[1]['residual_m'],reverse=True)[:8]:print(name,peak)
    raise SystemExit(0 if residual<=.01 else 1)

if __name__=='__main__':main()
