"""Standard top-view orientation: forward is down the page; no mesh edit."""
from pathlib import Path
import hashlib
import json
import math
import bpy

ROOT = Path(__file__).resolve().parents[1]
P = ROOT/'source'/'leg_design_scene.json'
S = json.loads(P.read_text()); source_sha = hashlib.sha256(P.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source'/'leg_design_context.blend'))
for obj in bpy.data.objects:
    if obj.get('appearance_source_sha256'):
        assert obj['appearance_source_sha256'] == source_sha
cam = bpy.context.scene.camera
lo, hi = S['reference_bounds_m']; cx = (lo[0]+hi[0])/2
cam.location = (cx, 0, 7); cam.rotation_euler = (0, 0, math.pi/2)
cam.data.ortho_scale = max((hi[1]-lo[1])*1100/900, hi[0]-lo[0])*1.12
bpy.context.scene.render.filepath = str(ROOT/'images'/'top.png')
bpy.ops.render.render(write_still=True)
manifest = ROOT/'source'/'render_manifest.json'
r = json.loads(manifest.read_text())
for image in r['renders']:
    if image['file'] == 'top.png':
        image.update({'camera_m': list(cam.location), 'camera_euler_rad': list(cam.rotation_euler),
                      'orthographic_scale_m': cam.data.ortho_scale, 'forward_on_page': 'down',
                      'camera_refinement_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      'mesh_changes': False})
manifest.write_text(json.dumps(r, indent=2)+'\n')
print('TOP_CAMERA_REFINED', flush=True)
