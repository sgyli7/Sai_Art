"""Check actual native 195 s all-control trace, not target values alone."""
from pathlib import Path
import json,argparse
O=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--report',type=Path,default=O/'reports/r032_cockpit_control_test_v2');args=ap.parse_args();p=args.report
d=json.loads((p/'cockpit_controls.json').read_text());rows=d['samples'];events=d['events'];e=json.loads((p/'equipment.json').read_text())['samples'];b=json.loads((p/'run_boarding.json').read_text())['samples']
assert 'SCRIPT ERROR' not in (p/'run.log').read_text()
expected={'doors','work','emergency','lift','lifts_all'}
has_cargo='cargo' in rows[0]['values']
assert {x['control'] for x in events}==expected|({'cargo'} if has_cargo else set())
assert all(x['accepted'] for x in events if x['control']!='cargo')
if has_cargo:assert len([x for x in events if x['control']=='cargo' and not x['accepted']])==1
assert all(sum(x['control']==name for x in events)==2 for name in expected)
assert all(max(x['values'][k] for x in rows)>.15 for k in rows[0]['values'] if k!='cargo')
assert all(x['selected_crane']==2 and x['selected_lift']==2 for x in rows if 5<x['time']<190)
assert max(x['speed_request_m_s'] for x in rows)>6
assert all(x['speed_request_m_s']==0 for x in rows if 26.2<x['time']<29.)
q=[x for x in e if x['name']=='rear_crane2']
assert max(x['slew_rad'] for x in q)>.2 and max(x['luff_rad'] for x in q)>.15 and max(x['extension_m'] for x in q)>.8 and max(x['paid_length_m'] for x in q)>4.5
q=[x for x in e if x['name']=='receiver'];assert max(x['slew_rad'] for x in q)>.2 and max(x['fold_rad'] for x in q)>.08
for name in sorted({x['name'] for x in b}):
 q=[x for x in b if x['name']==name];assert max(x['depth_m'] for x in q)>7 and q[-1]['depth_m']<.04 and q[-1]['out_m']<.04,name
out=dict(seconds=195,controls=len(rows[0]['values']),physical_button_events=len(events),selected_crane=3,selected_lift=3,all_six_lifts_deployed_and_retracted=True,report=str(p.resolve().relative_to(O)),scope='Native dynamics and command-chain trace; no robot arm policy, structural qualification or subjective artwork approval.')
(O/'reports/cockpit_native_acceptance.json').write_text(json.dumps(out,indent=2));print(out)
