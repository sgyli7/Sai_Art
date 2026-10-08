"""Extract visible surface points and normals for source-fitted retopology."""
from pathlib import Path
import sys
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy, numpy as np
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/lower_dense_assembled_s9.blend'))
data={}
for label,name in [('leg','pixal_clear_side_leg'),('foot','complete_reference_foot_left')]:
    o=bpy.data.objects[name];n=len(o.data.vertices)
    v=np.empty(n*3,dtype=np.float32);o.data.vertices.foreach_get('co',v)
    normals=np.empty(n*3,dtype=np.float32);o.data.vertices.foreach_get('normal',normals)
    matrix=np.asarray(o.matrix_world)
    data[label+'_vertices']=v.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]
    data[label+'_normals']=normals.reshape(-1,3)@np.linalg.inv(matrix[:3,:3])
np.savez_compressed(ROOT/'source/dense_reference_fit_points_b1.npz',**data)
print('SOURCE_FIT_POINTS_READY',[(k,len(v)) for k,v in data.items()],flush=True)
