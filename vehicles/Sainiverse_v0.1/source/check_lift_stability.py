"""Catch uncommanded mast deployment / jitter in the actual native run trace."""
import json,sys
from pathlib import Path
root=Path(sys.argv[1]);a=json.loads((root/'run_boarding.json').read_text())
rows=[r for r in a['samples'] if 3<r['time']<12 and not r['requested_down']]
assert rows,'No settled, stowed samples'
out=max(abs(r['out_m']) for r in rows);depth=max(abs(r['depth_m']) for r in rows)
result={'max_uncommanded_extension_m':out,'max_uncommanded_depth_m':depth,'limit_m':.02}
trace=root/'lift_stability.json'
if trace.exists():
 samples=[r for r in json.loads(trace.read_text()) if 3<r['time']<12 and not r['command']]
 result['max_stowed_stage_speed_m_s']=max(abs(v) for r in samples for v in r['velocity'])
print(json.dumps(result));assert max(out,depth)<.02,'Stowed lift moved without a command'
assert result.get('max_stowed_stage_speed_m_s',0)<.03,'High-frequency mast jitter'
