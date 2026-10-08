"""Create a manageable Blender cleanup mesh; preserve the untouched source."""
from pathlib import Path
import sys, json, time
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
t=time.time()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/reference_highpoly.blend'))
o=bpy.data.objects['reference_highpoly_0']
bpy.context.view_layer.objects.active=o
o.select_set(True)
print('START_DECIMATION',len(o.data.vertices),len(o.data.polygons),flush=True)
m=o.modifiers.new('cleanup_working_resolution','DECIMATE')
m.ratio=.035
bpy.ops.object.modifier_apply(modifier=m.name)
print('DECIMATION_COMPLETE',len(o.data.vertices),len(o.data.polygons),time.time()-t,flush=True)
coords=np.empty(len(o.data.vertices)*3,dtype=np.float32)
o.data.vertices.foreach_get('co',coords)
coords=coords.reshape(-1,3)
faces=np.empty(len(o.data.polygons)*3,dtype=np.int32)
o.data.polygons.foreach_get('vertices',faces)
np.savez_compressed(ROOT/'source/working_geometry_g1.npz',vertices=coords,faces=faces.reshape(-1,3))
o.name='cleanup_working_base'
o['source_status']='user-approved reconstruction direction; cleanup in progress'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/cleanup_working_g1.blend'),compress=True)
(ROOT/'source/working_resolution_record.json').write_text(json.dumps({'vertices':len(coords),'faces':len(faces)//3,'collapse_ratio':.035,'elapsed_seconds':time.time()-t,'source_preserved':True},indent=2)+'\n')
print('WORKING_MESH_SAVED',flush=True)
