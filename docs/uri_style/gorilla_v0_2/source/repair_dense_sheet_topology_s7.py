from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.append(str(Path(__file__).resolve().parent))
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy,bmesh,numpy as np
from manifold_source_sheets import separate_touching_sheets
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/lower_dense_surface_s6.blend'))
records=[]
for o in [o for o in bpy.data.objects if o.type=='MESH']:
    vv,ff,record=separate_touching_sheets(o.data)
    new=bpy.data.meshes.new(o.name+'_separated_sheets');new.from_pydata(vv.tolist(),[],ff);new.update()
    for mat in o.data.materials:new.materials.append(mat)
    o.data=new
    for p in new.polygons:p.use_smooth=True
    bm=bmesh.new();bm.from_mesh(new)
    record.update(name=o.name,nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),
                  boundary_edges=sum(e.is_boundary for e in bm.edges),
                  multi_face_edges=sum(len(e.link_faces)>2 for e in bm.edges))
    bm.free();records.append(record)
    print('DENSE_SHEET_REPAIR',json.dumps(record),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/lower_dense_surface_s7.blend'),compress=True)
(ROOT/'lower_dense_sheet_topology_s7.json').write_text(json.dumps({
    'source':'source/lower_dense_surface_s6.blend','parts':records,
    'visible_surface_geometry_unchanged':True,
    'all_meshes_manifold':all(r['nonmanifold_edges']==0 for r in records),
    'appearance_accepted':False,'engineering_ready':False,
},indent=2)+'\n')
