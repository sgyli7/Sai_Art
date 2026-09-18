"""Verify observed native and MuJoCo handling, not just commanded animation."""
import json,argparse
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--native',type=Path,default=O/'reports/r033_clearance_native');args=p.parse_args()
n=json.loads((args.native/'cargo_handling.json').read_text());m=json.loads((O/'reports/mujoco_cargo.json').read_text());out={}
for engine,d in [('native',n),('mujoco',m)]:
 phases=[e['phase'] for e in d['events'] if 'phase' in e]
 assert phases==['align','lift','clearance','swing','lower','released'],(engine,phases)
 assert d['released'] and d['mass_kg']==8000 and d['max_lift_m']>3.3
 rows=d['samples'];tail=[r for r in rows if r['time']>rows[-1]['time']-15]
 assert all(r['phase']=='released' and r['speed_m_s']<.05 for r in tail)
 positions=np.array([r['position'] for r in tail]);assert np.max(np.ptp(positions,axis=0))<.005
 assert np.linalg.norm(positions[-1,:2]-np.array(rows[0]['position'])[:2])>10
 assert abs(positions[-1,2]-2.591/2)<.01
 if engine=='native':assert all(r['attached_crane']==-1 and r['supported_time_s']>.35 and r['contacts']>0 for r in tail)
 else:assert all(not r['hook_connected'] and r['supported_time_s']>.35 for r in tail)
 buttons=json.loads((args.native/'cockpit_controls.json').read_text())['events'] if engine=='native' else d['cockpit_events']
 hook_buttons=[e for e in buttons if e['control']=='cargo' and e['accepted']]
 assert len(hook_buttons)==2,(engine,buttons)
 for button,action in zip(hook_buttons,['attach','release']):
  assert abs(button['time']-next(e['time'] for e in d['events'] if e.get('action')==action))<.01
 lift=np.array([r['position'] for r in rows if r['phase']=='lift'])
 lift_drift=float(np.max(np.linalg.norm(lift[:,:2]-lift[0,:2],axis=1)))
 assert lift_drift<.20,(engine,'horizontal drift during vertical lift',lift_drift)
 if engine=='native':assert all(r['contacts']==0 for r in rows if r['phase'] in ['clearance','swing'])
 out[engine]=dict(mass_kg=d['mass_kg'],max_lift_m=d['max_lift_m'],release_s=next(e['time'] for e in d['events'] if e.get('phase')=='released'),final_rest_height_m=float(positions[-1,2]),final_15s_drift_m=float(np.max(np.ptp(positions,axis=0))))
 out[engine]['accepted_physical_hook_button_events']=len(hook_buttons)
 out[engine]['vertical_lift_horizontal_drift_m']=lift_drift
(O/'reports/r033_loaded_acceptance.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
