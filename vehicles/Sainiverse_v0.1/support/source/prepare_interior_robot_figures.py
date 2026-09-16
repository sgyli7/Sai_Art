"""Actual compiled robot visual meshes at home pose, for scale inspection only."""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
import mujoco,trimesh as tm
from suspension_physics import ROOT
OUT=ROOT/'candidates/r023_interior'
def main():
    definitions={'sai':('/home/ethan/Projects/RobotDesign/Sai_Agent_001/models/full/visual.xml','chassis',1),'microduck':('/home/ethan/Projects/microduck_rl/src/mjlab_microduck/robot/microduck/scene.xml','trunk_base',2)}
    result={}
    for name,(source,root_name,group) in definitions.items():
        m=mujoco.MjModel.from_xml_path(source);d=mujoco.MjData(m)
        if name=='microduck':
            home=json.loads(Path('/home/ethan/Projects/Robot_Godot_Sim2Sim/main/robots/microduck.json').read_text())['home'];d.qpos[7:7+len(home)]=home
        mujoco.mj_forward(m,d);root=m.body(root_name).id;desc={root}
        for b in range(root+1,m.nbody):
            if m.body_parentid[b] in desc:desc.add(b)
        parts=[];all_vertices=[]
        for g in range(m.ngeom):
            if m.geom_bodyid[g] not in desc or m.geom_group[g]!=group:continue
            assert m.geom_type[g]==mujoco.mjtGeom.mjGEOM_MESH
            mid=m.geom_dataid[g];va=m.mesh_vertadr[mid];fa=m.mesh_faceadr[mid]
            vv=m.mesh_vert[va:va+m.mesh_vertnum[mid]].astype(float)@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g]
            vv=(vv-d.xpos[root])@d.xmat[root].reshape(3,3);faces=m.mesh_face[fa:fa+m.mesh_facenum[mid]]
            rgba=m.geom_rgba[g].tolist();mat=int(m.geom_matid[g])
            if mat>=0:rgba=m.mat_rgba[mat].tolist()
            parts.append(dict(name=str(m.geom(g).name or f'part_{g}'),vertices=vv.tolist(),faces=faces.tolist(),rgba=rgba));all_vertices.append(vv)
        bounds=np.array([np.concatenate(all_vertices).min(0),np.concatenate(all_vertices).max(0)])
        result[name]=dict(source=source,source_sha256=hashlib.sha256(Path(source).read_bytes()).hexdigest(),parts=parts,bounds_root_m=bounds.tolist(),pose='compiled home pose; display scale figure, not a simulation or learned task')
        scene=tm.Scene()
        for i,p in enumerate(parts):
            mesh=tm.Trimesh(p['vertices'],p['faces'],process=False);mesh.visual=tm.visual.TextureVisuals(material=tm.visual.material.PBRMaterial(name=f'robot_{i}',baseColorFactor=np.round(np.array(p['rgba'])*255).astype(np.uint8),roughnessFactor=.6,metallicFactor=.1));scene.add_geometry(mesh,node_name=f'{name}_{i}')
        scene.export(OUT/'assets'/f'{name}_scale_figure.glb')
    (OUT/'source/robot_scale_figures.json.gz').write_bytes(gzip.compress(json.dumps(result,separators=(',',':')).encode(),mtime=0))
    print({k:dict(parts=len(v['parts']),bounds=v['bounds_root_m']) for k,v in result.items()})
if __name__=='__main__':main()
