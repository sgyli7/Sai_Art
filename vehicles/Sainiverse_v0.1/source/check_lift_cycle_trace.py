"""Check actual 100/200 Hz native lift-cycle traces, including the 500 kg witness."""
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);a=json.loads((root/'run_boarding.json').read_text())
assert 'SCRIPT ERROR' not in (root/'run.log').read_text()
results=[]
for lift in a['lifts']:
 rows=[r for r in a['samples'] if r['name']==lift['name']];last=rows[-1]
 depth=max(r['depth_m'] for r in rows);ground=max(r['ground_contacts'] for r in rows)
 assert depth>6.8 and ground==1,(lift['name'],'no landing')
 assert abs(last['depth_m'])<.02 and abs(last['out_m'])<.02,(lift['name'],'not stowed')
 assert min(r['underside_gap_m'] for r in rows)>-.005,(lift['name'],'ground penetration')
 results.append(dict(name=lift['name'],max_depth_m=depth,final_out_m=last['out_m'],final_depth_m=last['depth_m']))
w=[r for r in a['witness_samples'] if r['time']>3];assert w
gap=max(abs(r['floor_gap_m']) for r in w);assert gap<.01,gap
out=dict(mode=a['mode'],lifts=results,payload_kg=500,max_payload_floor_gap_m=gap)
(root/'cycle_checks.json').write_text(json.dumps(out,indent=2));print(out)
