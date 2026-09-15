"""Canonical SI layout, shared by visual export and both physics adapters."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
DESIGN=json.loads((ROOT/'design/vehicle.json').read_text())
UNDER=DESIGN['undercarriage']
LAYOUT=DESIGN['layout']
HULLS=('front','rear')
CENTERS=dict(zip(HULLS,UNDER['hull_centers_x']))
AUTHOR_CENTERS=dict(zip(HULLS,LAYOUT['authoring_hull_centers_x']))
DELTAS={h:CENTERS[h]-AUTHOR_CENTERS[h] for h in HULLS}
