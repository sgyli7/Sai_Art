"""Screen actual moving axle solids against their authored stationary frame."""
from pathlib import Path
import argparse,gzip,json,hashlib
import numpy as np
import trimesh as tm
from suspension_physics import ROOT
OUT=ROOT/'candidates/r019_running_gear'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    output=OUT/'reports'/(args.label+'.json');assert not output.exists()
    path=OUT/'source/assembly.json.gz';a=json.loads(gzip.decompress(path.read_bytes()));group='front_bogie_fore_right'
    parts=[p for p in a['parts'] if p['group']==group];pivot=np.array(a['groups'][group]);moving={1:[],2:[],3:[]};fixed=[]
    for p in parts:
        m=tm.Trimesh(vertices=np.array(p['vertices'])-pivot,faces=p['faces'],process=False)
        if p['motion']['kind'] in ['wheel','wheel_slide'] and p['motion']['index'] in moving:moving[p['motion']['index']].append((p['name'],m))
        elif p['motion']['kind']!='belt':fixed.append((p['name'],m))
    manager=tm.collision.CollisionManager()
    for name,m in fixed:manager.add_object(name,m)
    collisions=[];min_distance=1e9
    for index,items in moving.items():
        # Monotone prismatic path with 25 mm steps, including both limits.
        for q in np.linspace(-.35,.35,29):
            transform=np.eye(4);transform[2,3]=q
            bulk=tm.util.concatenate([m for _,m in items]);hit=manager.in_collision_single(bulk,transform=transform)
            if hit:
                for name,m in items:
                    overlap,names=manager.in_collision_single(m,transform=transform,return_names=True)
                    if overlap:collisions.append(dict(wheel=index,travel_m=float(q),moving=name,fixed=sorted(names)))
            else:min_distance=min(min_distance,manager.min_distance_single(bulk,transform=transform))
    report=dict(passed=not collisions,group=group,pose_count=87,collisions=collisions,minimum_noncolliding_surface_distance_m=float(min_distance),
        moving_parts=sum(len(v) for v in moving.values()),stationary_parts=len(fixed),
        scope='Actual triangle surface screening for lower wheel/carrier assemblies versus stationary bogie structure, both belts, ±0.35 m. Excludes moving belts, neighboring moving-wheel pairs and containment; not structural/cylinder qualification.',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),path]})
    output.write_text(json.dumps(report,indent=2)+'\n');print('passed',report['passed'],'hits',len(collisions),'clearance',min_distance)
    if collisions:print(json.dumps(collisions[:8],indent=2))
    raise SystemExit(1 if collisions else 0)
if __name__=='__main__':main()
