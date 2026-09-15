"""Export the exact GLB geometry as visual-only MuJoCo meshes (zero added mass)."""
from pathlib import Path
import json
import numpy as np
import trimesh as tm
ROOT=Path(__file__).resolve().parents[1]
from layout import CENTERS
from physics import CFG
scene=tm.load_scene(ROOT/'assets/leviathan003.glb');groups={};colors={}
for node in scene.graph.nodes_geometry:
    transform,geom=scene.graph[node];mesh=scene.geometry[geom].copy();mesh.apply_transform(transform)
    hull='front' if node.startswith('front') else 'rear';mat=node.split('__')[-1];key=(hull,mat)
    mesh.apply_translation(-np.array([CENTERS[hull],0,CFG['com_z']]));groups.setdefault(key,[]).append(mesh)
    colors[mat]=(np.array(mesh.visual.material.baseColorFactor,dtype=float)/255).tolist()
folder=ROOT/'assets/mj_meshes';folder.mkdir(exist_ok=True);rows=[]
for (hull,mat),meshes in groups.items():
    name=hull+'_'+mat;m=tm.util.concatenate(meshes);m.export(folder/(name+'.stl'))
    rows.append(dict(name=name,hull=hull,color=colors[mat],file='mj_meshes/'+name+'.stl',triangles=len(m.faces)))
(ROOT/'assets/visual_meshes.json').write_text(json.dumps(rows,indent=2));print(len(rows),'visual meshes',sum(r['triangles'] for r in rows),'triangles')
