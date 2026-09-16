"""Short full-scene FPS regression loop; diagnostic target, not final acceptance."""
import argparse,json,subprocess,sys
import numpy as np
from suspension_physics import ROOT
OUT=ROOT/'candidates/r022_runtime'
def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--probe-mode',default='normal');a=p.parse_args()
    subprocess.run([sys.executable,str(ROOT/'source/run_suspension_visual.py'),'--candidate','r022_runtime','--label',a.label,'--seconds','12','--terrain','flat','--speed','5','--view','whole','--probe-mode',a.probe_mode],check=True)
    raw=json.loads((OUT/'reports'/(a.label+'_visual.json')).read_text());frames=raw['frames'];ms=np.array([f['frame_ms'] for f in frames]);fps=1000/np.median(ms)
    ratio=(frames[-1]['simulation_s']-frames[0]['simulation_s'])/((frames[-1]['wall_usec']-frames[0]['wall_usec'])/1e6)
    report=dict(probe_mode=a.probe_mode,median_fps=float(fps),p95_ms=float(np.percentile(ms,95)),simulation_wall_ratio=ratio,visual_update_ms=raw['mean_visual_update_ms'],diagnostic_target_fps=120,passed=bool(fps>=120 and ratio>=.98),scope='12 s current full exterior/native physics cost probe, first 3 s excluded. 120 FPS is an optimization diagnostic against the prior 225 FPS exterior, not a redefinition of full-game acceptance.')
    (OUT/'reports'/(a.label+'_probe.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(0 if report['passed'] else 1)
if __name__=='__main__':main()
