"""S5: explicit front knee shield, with S4's pose and support geometry retained."""
from pathlib import Path
import runpy
ROOT=Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT/'source/render_lower_module_guide_s4.py'),init_globals={
    'SOURCE':ROOT/'source/lower_body_spatial_s4.blend',
    'REV':'s5',
    'DISTINCT_KNEE_GUARD':True,
})
