"""Discrete actual triangle collision screen for articulation design work.

FCL checks authored surfaces, not AABB overlap alone. This is not a continuous
sweep or dynamic validation. Shared pin/drawbar seating is recorded separately.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
import time
import itertools
import numpy as np
import trimesh as tm

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--assembly',type=Path,default=ROOT/'source/assembly.json.gz')
    parser.add_argument('--output',type=Path,default=ROOT/'reports/articulation_r015/scene_sweep.json')
    parser.add_argument('--step',type=int,default=15)
    parser.add_argument('--extension',type=float,default=0.)
    parser.add_argument('--combined',action='store_true')
    args=parser.parse_args()
    a=json.loads(gzip.decompress(args.assembly.read_bytes()))
    layout=json.loads((ROOT/'design/vehicle.json').read_text())['layout']
    anchor=[layout['hitch_x'],0,layout['hitch_z']]
    managers={h:tm.collision.CollisionManager() for h in ('front','rear')}
    parts={};names={'front':[],'rear':[]}
    started=time.monotonic()
    for p in a['parts']:
        if p['surface_paint']:continue
        h='front' if p['group'].startswith('front') else 'rear'
        mesh=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
        managers[h].add_object(p['name'],mesh)
        names[h].append(p['name']);parts[p['name']]=p
    out=[]
    cases=itertools.product(range(-45,46,args.step),(-8,0,8) if args.combined else (0,),(-6,0,6) if args.combined else (0,))
    for yaw,pitch,roll in cases:
        tr=tm.transformations.rotation_matrix(math.radians(yaw),[0,0,1],point=anchor)
        tr=tr@tm.transformations.rotation_matrix(math.radians(pitch),[0,1,0],point=anchor)
        tr=tr@tm.transformations.rotation_matrix(math.radians(roll),[1,0,0],point=anchor)
        tr[0,3]-=args.extension
        for name in names['rear']:managers['rear'].set_transform(name,tr)
        collision,pairs=managers['front'].in_collision_other(managers['rear'],return_names=True)
        seating=[];obstructions=[]
        for left,right in sorted(pairs):
            if left.endswith('_hitch_ring') and right.endswith('_rear_drawbar'):
                seating.append([left,right])
            else:obstructions.append([left,right])
        row=dict(yaw_deg=yaw,pitch_deg=pitch,roll_deg=roll,obstructions=obstructions,shared_seating=seating)
        out.append(row)
        print(json.dumps(dict(yaw=yaw,pitch=pitch,roll=roll,obstructions=len(obstructions),examples=obstructions[:8])),flush=True)
    report=dict(source_sha256=hashlib.sha256(args.assembly.read_bytes()).hexdigest(),
                samples=out,extension_m=args.extension,elapsed_s=time.monotonic()-started,
                scope='Discrete triangle surface intersections, yaw then pitch then roll, excludes coplanar paint. '
                      'FCL may miss full containment; not a continuous clearance certificate. '
                      'Existing ring/drawbar shared seating is separately reported, not discarded.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
