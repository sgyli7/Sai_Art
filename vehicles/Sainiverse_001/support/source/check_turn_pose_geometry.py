"""Cross-module intersections in the actual depicted trained turn pose."""
from pathlib import Path
import gzip,hashlib,json
import numpy as np,trimesh as tm
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'candidates/r017_turning/reports'
def main():
    source=ROOT/'candidates/r016_modular/train_containers_first/source/assembly.json.gz';pose_path=OUT/'tight_pose_mujoco.json'
    a=json.loads(gzip.decompress(source.read_bytes()));pose=json.loads(pose_path.read_text())['final_motion_groups']
    groups={};transforms={}
    for name,s in pose.items():
        t=np.eye(4);t[:3,:3]=np.array(s['rotation_row_major']).reshape(3,3);t[:3,3]=s['position_source_m'];t=t@tm.transformations.translation_matrix(-np.array(s['neutral_body_position_source_m']));transforms[name]=t
    for p in a['parts']:
        if p['surface_paint']:continue
        owner=p['group'] if 'hitch' in p['group'] else p['group'].split('_')[0]
        m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False);m.apply_transform(transforms[p['group']]);groups.setdefault(owner,[]).append(m)
    managers={g:tm.collision.CollisionManager() for g in groups}
    for g,parts in groups.items():managers[g].add_object(g,tm.util.concatenate(parts))
    keys=list(groups);hits=[]
    for i,g in enumerate(keys):
        for h in keys[i+1:]:
            if managers[g].in_collision_other(managers[h]):hits.append([g,h])
    report=dict(cross_module_surface_intersections=hits,passed=not hits,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,pose_path,Path(__file__)]},
        scope='Single actual displayed pose, all original exterior triangles transformed by the 21 recorded body frames. Checks between hull-owned aggregates and coupler groups. Does not test within-hull bogie mount interference, wheel/belt deformation, containment or continuous motion.')
    (OUT/'posed_cross_module_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
