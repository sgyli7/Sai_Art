"""Actual new guide/cartridge mesh clearance, preserving failed iterations."""
import argparse,gzip,json,hashlib
from pathlib import Path
import numpy as np,trimesh as tm
from suspension_physics import ROOT
OUT=ROOT/'candidates/r021_track_tension'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args();output=OUT/'reports'/(args.label+'.json');assert not output.exists()
    path=OUT/'source/assembly.json.gz';a=json.loads(gzip.decompress(path.read_bytes()));group='front_bogie_fore_right';pivot=np.array(a['groups'][group]);parts=[p for p in a['parts'] if p['group']==group];moving=[];fixed=[]
    for p in parts:
        mesh=tm.Trimesh(vertices=np.array(p['vertices'])-pivot,faces=p['faces'],process=False)
        if p.get('physical_body','').startswith(group+'_idler_'):moving.append((p['name'],mesh))
        elif p['motion']['kind']!='belt':fixed.append((p['name'],mesh))
    manager=tm.collision.CollisionManager()
    for name,mesh in fixed:manager.add_object(name,mesh)
    bulk=tm.util.concatenate([m for _,m in moving]);hits=[];minimum=1e9
    for q in np.linspace(-.32,.24,29):
        transform=np.eye(4);transform[0,3]=q
        if manager.in_collision_single(bulk,transform=transform):
            for name,mesh in moving:
                collided,names=manager.in_collision_single(mesh,transform=transform,return_names=True)
                if collided:hits.append(dict(q=float(q),moving=name,fixed=sorted(names)))
        else:minimum=min(minimum,manager.min_distance_single(bulk,transform=transform))
    report=dict(passed=not hits,poses=29,moving_parts=len(moving),stationary_parts=len(fixed),collisions=hits,minimum_noncolliding_surface_clearance_m=float(minimum),scope='Actual triangles, both idlers through -0.32..+0.24 m, other road wheels neutral. Excludes belt and containment. Independent simultaneous lower-wheel limits are not proved by this test.',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [path,Path(__file__)]})
    output.write_text(json.dumps(report,indent=2)+'\n');print('passed',not hits,'hits',len(hits),'clearance',minimum);print(json.dumps(hits[:8],indent=2));assert not hits
if __name__=='__main__':main()
