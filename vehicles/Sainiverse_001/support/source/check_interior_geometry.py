"""Real mesh openings and conservative robot-envelope route geometry.

Door-route test explicitly removes door leaves/handles/seals; it proves a usable
aperture, not a door sweep, locomotion, reach or a ground-to-cabin route.
"""
from pathlib import Path
import gzip,json,hashlib
import numpy as np
import trimesh as tm
import manifold3d as manifold
from functools import reduce
def Polygon(points):return manifold.CrossSection([points])
def rect(x0,y0,x1,y1):return Polygon([[x0,y0],[x1,y0],[x1,y1],[x0,y1]])
from suspension_physics import ROOT
OUT=ROOT/'candidates/r023_interior'
def mesh(p):return tm.Trimesh(p['vertices'],p['faces'],process=False)
def main():
    a=json.loads(gzip.decompress((OUT/'source/assembly.json.gz').read_bytes()));meta=json.loads((OUT/'source/interior.json').read_text());robots=json.loads((OUT/'source/robot_envelopes.json').read_text());f=meta['floor_z']
    shell=mesh(next(p for p in a['parts'] if p['name'].endswith('bridge_shell')))
    origins=[];directions=[]
    for p in a['parts']:
        if p['material']!='cabin_glass' or 'door_window' in p['name']:continue
        vv=np.array(p['vertices']);mid=vv.mean(0);_,_,vh=np.linalg.svd(vv-mid);n=vh[-1]
        if np.dot(n,mid-[25,0,13.65])<0:n=-n
        origins.append(mid-n*.8);directions.append(n)
    loc,ids,_=shell.ray.intersects_location(np.array(origins),np.array(directions));blocked=[]
    for hit,i in zip(loc,ids):
        if np.linalg.norm(hit-origins[i])<1.6:blocked.append(int(i))
    assert not blocked,blocked
    candidates=[]
    for p in a['parts']:
        if p['group']!='front':continue
        v=np.array(p['vertices']);lo,hi=v.min(0),v.max(0)
        if hi[0]<16 or lo[0]>34.5 or hi[2]<f-.1 or lo[2]>f+1.2 or lo[1]>5.2 or hi[1]<-5.2:continue
        candidates.append(p)
    moving_tokens=['bridge_door_leaf','bridge_door_handle','bridge_door_lock','bridge_door_window','door_bottom_seal']
    door_removed=[p for p in candidates if not any(t in p['name'] for t in moving_tokens)]
    def manager(parts):
        manager=tm.collision.CollisionManager();manager.add_object('actual_mesh_obstacles',tm.util.concatenate([mesh(p) for p in parts]));return manager
    solid=manager(candidates);aperture=manager(door_removed)
    cfg=json.loads((OUT/'physics/interior_contacts.json').read_text());polygons=[]
    for shape in cfg['shapes']:
        if shape['type']=='convex':polygons.append(Polygon(meta['inner_plan_xy']))
        elif abs(shape['center_source_m'][2]+shape['size_m'][2]/2-f)<1e-6:
            center=np.array(shape['center_source_m']);half=np.array(shape['size_m'])/2;polygons.append(rect(*(center-half)[:2],*(center+half)[:2]))
    support=reduce(lambda a,b:a+b,polygons)
    rows={}
    for name,robot in robots.items():
        size=np.array(robot['sampled_dimensions_m']);hit_cases=[];unsupported=[];count=0
        def probe(mode,position,rotated=False):
            nonlocal count
            dims=size.copy()
            if rotated:dims[:2]=dims[:2][::-1]
            center=np.array([position[0],position[1],f+.01+dims[2]/2]);part=tm.creation.box(dims);tf=np.eye(4);tf[:3,3]=center
            active=aperture if mode=='door_leaf_removed' else solid
            if active.in_collision_single(part,transform=tf):hit_cases.append(dict(mode=mode,xy=position))
            footprint=rect(center[0]-dims[0]/2,center[1]-dims[1]/2,center[0]+dims[0]/2,center[1]+dims[1]/2)
            if (footprint-support).area()>1e-8:unsupported.append(dict(mode=mode,xy=position))
            count+=1
        for x in np.linspace(18,31.6,137):probe('central_aisle',[float(x),0.])
        for side in [-1,1]:
            for y in np.linspace(0,4.4,45):probe('door_leaf_removed',[19.15,float(side*y)],True)
            for y in np.linspace(0,1.6,17):probe('workbench_approach',[21.05,float(side*y)])
        rows[name]=dict(sampled_dimensions_m=size.tolist(),tested_positions=count,collision_cases=hit_cases,unsupported_footprints=unsupported)
        assert not hit_cases and not unsupported,(name,hit_cases[:5],unsupported[:5])
    current={p['name']:p for p in a['parts']};old=json.loads(gzip.decompress((ROOT/'candidates/r021_track_tension/source/assembly.json.gz').read_bytes()));allowed=set(meta['modified'])
    assert all(p==current[p['name']] for p in old['parts'] if p['name'] not in allowed)
    report=dict(passed=True,unobstructed_glazing_centers=len(origins),route_checks=rows,unchanged_original_parts=meta['unchanged_original_parts'],floor_continuity='Whole rectangular sampled robot envelope footprints covered by union of authored floor/threshold/gallery top surfaces',scope='Static actual-mesh screening; central aisle and two first-door approaches only. Door leaves/handles/seals removed for aperture check, no actual opened-door sweep or control. Joint envelope samples are conservative per pose, not certified continuous extrema. No arm reach, stairs/lift, learned task or whole-game proof.',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),OUT/'source/assembly.json.gz',OUT/'source/robot_envelopes.json',OUT/'physics/interior_contacts.json']})
    (OUT/'reports/interior_geometry.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
