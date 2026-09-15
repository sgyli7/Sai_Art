"""Screen four lift reservation volumes against actual candidate geometry.

Reservation volumes are not authored lift parts. A conservative sphere proves
same-hull bogie rotational clearance; sampled AABBs screen cross-hull poses.
Neither test certifies future lift hardware, the entry threshold, or terrain.
"""
from pathlib import Path
import gzip, hashlib, itertools, json
import numpy as np
from articulation_geometry import poses

ROOT=Path(__file__).resolve().parents[1]
def main():
    source=ROOT/'candidates/r015_articulation/source/assembly.json.gz'
    config=ROOT/'design/module_interfaces_candidate.json'
    a=json.loads(gzip.decompress(source.read_bytes()));c=json.loads(config.read_text())
    signs=np.array(list(itertools.product([-1,1],repeat=3)))
    bounds=[];radii={}
    for part in a['parts']:
        v=np.array(part['vertices']);lo,hi=v.min(0),v.max(0)
        bounds.append((part['name'],part['group'],(lo+hi)/2+signs*(hi-lo)/2))
        g=part['group']
        if 'bogie' in g:
            pivot=np.array(a['groups'][g]);pivot[2]=4.25
            # Any rotation about the suspension pivot, plus wheel slide range.
            radii[g]=max(radii.get(g,0),float(np.linalg.norm(v-pivot,axis=1).max())+.35)
    reservations=[]
    for hull,info in c['hulls'].items():
        cx=info['datum_source_m'][0]
        for side in c['lift_sides']:
            for mode in ['stowed','deployment']:
                xy=np.array(c['lift_stowed_reserved_bounds_source_relative_hull_xy_m'] if mode=='stowed' else c['lift_station_reserved_source_relative_hull_xy_bounds_m'])
                zz=c['lift_stowed_reserved_z_source_m'] if mode=='stowed' else c['lift_deployment_reserved_z_source_m']
                ys=sorted((xy[:,1]*side).tolist());lo=np.array([cx+xy[0,0],ys[0],zz[0]]);hi=np.array([cx+xy[1,0],ys[1],zz[1]])
                reservations.append((hull,side,mode,(lo+hi)/2+signs*(hi-lo)/2))
    states=[(0,0,0,0)]+[(4,np.radians(y),0,0) for y in range(-45,46,3)]
    states += [(4,np.radians(y),np.radians(p),np.radians(r)) for y,p,r in itertools.product([-45,0,45],[-8,0,8],[-6,0,6])]
    hits=[]
    for q in states:
        tf=poses(*q)
        def transform(corners,hull):
            m=tf[hull];return corners@m[:3,:3].T+m[:3,3]
        # Compare in each lift's hull frame: world AABBs of co-rotated long
        # decks spuriously overlap outside reservations at large yaw angles.
        framed={}
        for hull in ['front','rear']:
            inv=np.linalg.inv(tf[hull]);pb=[]
            for name,g,corners in bounds:
                owner=g if g in tf else ('front' if g.startswith('front') else 'rear')
                m=inv@tf[owner];p=corners@m[:3,:3].T+m[:3,3]
                pb.append((name,g,p.min(0),p.max(0)))
            framed[hull]=(pb,np.array([b[2] for b in pb]),np.array([b[3] for b in pb]))
        for hull,side,mode,corners in reservations:
            # Deployed lift only permitted parked/aligned; articulation checks stowed.
            if mode=='deployment' and q!=(0,0,0,0):continue
            pb,lows,highs=framed[hull];lo,hi=corners.min(0),corners.max(0)
            overlap=np.flatnonzero(np.all(highs>lo,axis=1)&np.all(lows<hi,axis=1))
            if len(overlap):hits.append(dict(pose=q,hull=hull,side=side,mode=mode,parts=[pb[i][0] for i in overlap]))
    gaps={g:abs(a['groups'][g][0]-(0 if g.startswith('front') else -42))-r-1 for g,r in radii.items()}
    report=dict(status='reservation packaging screen',sampled_articulation_poses=len(states),reservation_volumes=len(reservations),
                broadphase_overlaps=hits,same_hull_bogie_sphere_radius_with_wheel_travel_m=radii,
                same_hull_bogie_longitudinal_clearance_lower_bound_m=gaps,
                passed=not hits and min(gaps.values())>0,
                scope='AABB rejection is conservative for checked poses, with opposite-hull bogies at nominal positions; same-hull sphere clearance covers arbitrary bogie rotation and +/-0.35 m wheel slide. Heave is along hull Z and does not change longitudinal separation. Future mechanisms, landing/gate cuts, terrain, combined opposite-hull suspension, continuous cross-hull motion and robot traversal remain unverified.',
                source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,config,Path(__file__)]})
    out=ROOT/'candidates/r015_articulation/reports/boarding/lift_packaging.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=report['passed'],poses=len(states),overlap_cases=len(hits),
                         first_overlaps=hits[:2],minimum_same_hull_bogie_longitudinal_gap_m=min(gaps.values())),indent=2))

if __name__=='__main__':main()
