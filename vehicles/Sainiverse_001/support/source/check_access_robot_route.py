"""Actual open-door meshes: conservative sampled robot-envelope route screen."""
from pathlib import Path
import gzip,json,hashlib
from functools import reduce
import numpy as np
import trimesh as tm
import manifold3d as mf
from suspension_physics import ROOT
OUT=ROOT/'candidates/r025_access'
OLD=ROOT/'candidates/r023_interior'
def rect(x0,y0,x1,y1):return mf.CrossSection([[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]])
def main():
    assembly=json.loads(gzip.decompress((OUT/'source/assembly.json.gz').read_bytes()));meta=json.loads((OUT/'source/interior.json').read_text());robots=json.loads((OLD/'source/robot_envelopes.json').read_text());f=meta['floor_z']
    doors={d['name']:d for d in meta['doors']};obstacles=[]
    for p in assembly['parts']:
        if p['group']!='front' and p['group'] not in doors:continue
        m=tm.Trimesh(p['vertices'],p['faces'],process=False)
        if p['group'] in doors:
            d=doors[p['group']];tf=tm.transformations.rotation_matrix(d['limits_rad'][1],d['axis_source'],d['pivot_source_m']);m.apply_transform(tf)
        lo,hi=m.bounds
        if hi[0]<16 or lo[0]>34.5 or hi[2]<f-.1 or lo[2]>f+1.2 or lo[1]>5.2 or hi[1]<-5.2:continue
        obstacles.append(m)
    manager=tm.collision.CollisionManager();manager.add_object('actual_authored_meshes',tm.util.concatenate(obstacles))
    # Only the original authored floor/fixture set supplies support. Newly added
    # wall convex pieces must never be mistaken for floor coverage.
    cfg=json.loads((OLD/'physics/interior_contacts.json').read_text());polygons=[]
    for shape in cfg['shapes']:
        if shape['type']=='convex':polygons.append(mf.CrossSection([meta['inner_plan_xy']]))
        elif abs(shape['center_source_m'][2]+shape['size_m'][2]/2-f)<1e-6:
            c=np.array(shape['center_source_m']);h=np.array(shape['size_m'])/2;polygons.append(rect(*(c-h)[:2],*(c+h)[:2]))
    support=reduce(lambda a,b:a+b,polygons);rows={}
    for name,robot in robots.items():
        size=np.array(robot['sampled_dimensions_m']);fail=[];unsupported=[];count=0
        def probe(mode,xy,rotated=False):
            nonlocal count
            dims=size.copy()
            if rotated:dims[:2]=dims[:2][::-1]
            c=np.array([*xy,f+.01+dims[2]/2]);tf=np.eye(4);tf[:3,3]=c
            if manager.in_collision_single(tm.creation.box(dims),transform=tf):fail.append(dict(mode=mode,xy=xy))
            if (rect(c[0]-dims[0]/2,c[1]-dims[1]/2,c[0]+dims[0]/2,c[1]+dims[1]/2)-support).area()>1e-8:unsupported.append(dict(mode=mode,xy=xy))
            count+=1
        for x in np.linspace(18,31.6,137):probe('central_aisle',[float(x),0.])
        for side in [-1,1]:
            for y in np.linspace(0,4.4,45):probe('actual_open_first_door',[19.15,float(side*y)],True)
            for y in np.linspace(0,1.6,17):probe('workbench_approach',[21.05,float(side*y)])
        rows[name]=dict(envelope_m=size.tolist(),tested_positions=count,collisions=fail,unsupported=unsupported)
    result=dict(passed=all(not r['collisions'] and not r['unsupported'] for r in rows.values()),doors_open_deg=110,route_checks=rows,scope='Actual complete opening-door geometry retained and rotated to the measured full-open target. Sampled box-envelope clearance and floor footprint support only; not locomotion, full continuous joint extrema, lift access or end-to-end robot task.',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),OUT/'source/assembly.json.gz',OUT/'source/interior.json',OLD/'source/robot_envelopes.json',OLD/'physics/interior_contacts.json']})
    (OUT/'reports/access_robot_route.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert result['passed']
if __name__=='__main__':main()
