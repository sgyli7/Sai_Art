"""Read-only reference volume for clean 3D armor fitting; not final geometry."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy,numpy as np,trimesh
from scipy.ndimage import binary_closing,binary_fill_holes,gaussian_filter
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/lower_dense_assembled_s9.blend'))
o=bpy.data.objects['pixal_clear_side_leg'];o.data.calc_loop_triangles()
v=np.asarray([p.co[:] for p in o.data.vertices]);m=np.asarray(o.matrix_world)
v=v@m[:3,:3].T+m[:3,3]
f=np.asarray([t.vertices[:] for t in o.data.loop_triangles])
mesh=trimesh.Trimesh(vertices=v,faces=f,process=False)
pitch=.0015
guide=mesh.voxelized(pitch=pitch,method='subdivide')
raw=guide.matrix.astype(bool)
raw=np.pad(raw,3)
closed=binary_closing(raw,iterations=1)
solid=binary_fill_holes(closed)
origin=guide.transform[:3,3]-pitch*3
path=ROOT/'source/primary_reference_volume_guide_b8.npz'
np.savez_compressed(path,solid=solid,origin=origin,pitch=pitch)
record={'reference':'source/lower_dense_assembled_s9.blend','reference_object':o.name,
        'role':'Read-only outer-volume fitting measurements; never imported as the finished model',
        'guide':str(path.relative_to(ROOT)),'guide_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'pitch':pitch,'shape':list(solid.shape),'raw_surface_voxels':int(raw.sum()),
        'solid_voxels':int(solid.sum()),'origin':origin.tolist(),
        'processing':'Triangle sampling, one-cell closing and enclosed-volume filling for outer armor fitting',
        'foot_included':False,'geometry_or_physics_accepted':False}
(ROOT/'primary_reference_volume_guide_b8.json').write_text(json.dumps(record,indent=2)+'\n')
print('PRIMARY_OUTER_VOLUME_GUIDE',record['shape'],record['solid_voxels'],flush=True)
