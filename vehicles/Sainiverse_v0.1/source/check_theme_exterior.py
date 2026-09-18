"""Regression guard for exterior additions that must follow the active livery."""
from pathlib import Path
import gzip
import json


ROOT = Path(__file__).resolve().parents[1]
THEMES = ("black", "desert", "white", "blue", "yellow")


assembly = json.loads(gzip.decompress((ROOT / "source/assembly.json.gz").read_bytes()))
elbows = [part for part in assembly["parts"] if part["name"].endswith("continuous_cooling_elbow")]
assert len(elbows) == 2, f"expected mirrored cooling elbows, found {len(elbows)}"

enclosure_skin_suffixes = (
    "enclosed_connector_wall",
    "stairhouse_roof",
    "stairhouse_coaming",
    "stairhouse_coaming_end",
)
enclosure_skins = [
    part for part in assembly["parts"]
    if part["name"].endswith(enclosure_skin_suffixes)
]
assert len(enclosure_skins) == 6, f"expected six connector enclosure skins, found {len(enclosure_skins)}"

for part in elbows + enclosure_skins:
    assert part["material"] == "ivory", (
        f"{part['name']} uses fixed exterior material {part['material']}; "
        "the exposed painted skin must use the theme-driven body role 'ivory'"
    )

for theme_id in THEMES:
    palette = json.loads((ROOT / "themes" / f"{theme_id}.json").read_text())["palette"]
    assert palette[elbows[0]["material"]] == palette["ivory"], theme_id

print("THEME_EXTERIOR_OK elbows=2 connector_skins=6 themes=5 role=ivory")
