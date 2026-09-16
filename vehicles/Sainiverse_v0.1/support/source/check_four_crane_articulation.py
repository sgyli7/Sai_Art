"""Offset-axis whole-model sweep for the latest four-crane, +/-30 deg target."""
from pathlib import Path
import gzip,hashlib,itertools,json,math,time
import numpy as np
import trimesh as tm
from articulation_geometry import poses

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'candidates/r016_modular/reports'
def main():
    source=ROOT/'candidates/r016_modular/source/assembly.json.gz';a=json.loads(gzip.decompress(source.read_bytes()))
    keys=['front','hitch_slide','hitch_yaw','hitch_pitch','rear'];man={g:tm.collision.CollisionManager() for g in keys};names={g:[] for g in keys}
    for p in a['parts']:
        if p['surface_paint']:continue
        g=p['group'] if p['group'] in keys else 'front' if p['group'].startswith('front') else 'rear'
        man[g].add_object(p['name'],tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False));names[g].append(p['name'])
    angles=list(dict.fromkeys([(y,0,0) for y in range(-30,31,5)]+list(itertools.product([-30,0,30],[-8,0,8],[-6,0,6]))))
    results=[];started=time.monotonic();passing=[]
    for extension in np.arange(0,4.01,.5):
        failed=0
        for yaw,pitch,roll in angles:
            ts=poses(float(extension),*np.radians([yaw,pitch,roll]))
            for g in keys:
                for name in names[g]:man[g].set_transform(name,ts[g])
            pairs=[]
            for i,g in enumerate(keys):
                for h in keys[i+1:]:
                    hit,found=man[g].in_collision_other(man[h],return_names=True)
                    if hit:pairs.extend(sorted(found))
            failed+=bool(pairs)
            results.append(dict(extension_m=float(extension),yaw_deg=yaw,pitch_deg=pitch,roll_deg=roll,intersections=pairs))
        if not failed:passing.append(float(extension))
        print('extension',extension,'failed poses',failed,'/',len(angles),flush=True)
    report=dict(assembly_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),mechanical_yaw_target_degrees=[-30,30],tested_extensions_passing_all_sampled_angles_m=passing,
                smallest_tested_passing_extension_m=min(passing) if passing else None,sampled_poses=len(results),samples=results,wall_seconds=time.monotonic()-started,
                scope='Actual four-crane two-hull geometry, offset yaw/pitch/roll axes, 0.5 m extension steps and sampled angles. Nominal suspension poses only; not continuous clearance, containment, three-module dynamics, lifting or safety certification.')
    (OUT/'articulation_30deg_screen.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
