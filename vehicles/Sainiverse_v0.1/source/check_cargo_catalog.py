"""Check stable all-72 cargo selection metadata and top-down eligibility."""
from pathlib import Path
import json
O=Path(__file__).resolve().parents[1]
rig=json.loads((O/'source/equipment.json').read_text());rows=rig['cargo_catalog']
assert len(rows)==72 and {r['bay'] for r in rows}==set(range(4)) and {r['row'] for r in rows}==set(range(6)) and {r['tier'] for r in rows}==set(range(3))
for r in rows:
 assert r['return_slot_center']==r['center'] and r['initially_secured']
 assert r['eligible_to_lift']==(r['tier']==2)
 assert r['blocking_tiers']==list(range(r['tier']+1,3))
report=dict(total_boxes=len(rows),bays=4,rows=6,tiers=3,top_tier_eligible=sum(r['eligible_to_lift'] for r in rows),
            gross_mass_kg=sum(r['mass_kg'] for r in rows),selected_dynamic_article=rig['cargo'][0]['name'],
            scope='Selection/eligibility/return-slot manifest only; boxes other than the selected article are not yet promoted to dynamic bodies.')
(O/'reports/cargo_catalog.json').write_text(json.dumps(report,indent=2));print(report)
