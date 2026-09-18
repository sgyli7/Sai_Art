"""Conservative cargo-box path screen against parked crane and cargo envelopes.

Source-space upright cargo, one top-tier article at a time, parked other cranes.
This does not qualify moving-boom clearance, load sway, carrier attitude, rigs,
structural strength or execution of every path by a finite-force controller.
"""
from pathlib import Path
import gzip,json,re,math
import numpy as np
O=Path(__file__).resolve().parents[1]
a=json.loads(gzip.decompress((O/'source/assembly.json.gz').read_bytes()))
rig=json.loads((O/'physics/parameters.json').read_text())['equipment']
containers={}
for p in a['parts']:
    m=re.search(r'container_b\d+_r\d+_t\d+',p['name'])
    if m:containers.setdefault(m[0],[]).extend(p['vertices'])
boxes={n:np.array([np.min(v,axis=0),np.max(v,axis=0)]) for n,v in containers.items()}
cranes=[c for c in rig['cranes'] if c['hull']=='rear']
stationary=[]
for b in rig['bodies']:
    if b.get('cargo') or not b['name'].startswith(('rear_crane','tail_crane')):continue
    cb=b['collision_box'];center=np.array(b['pivot'])+cb['center'];half=np.array(cb['size'])/2
    stationary.append((b['name'],np.array([center-half,center+half])))
obstacle_top=max(b[1][1,2] for b in stationary)
rows=[]
for tag,bb in sorted(boxes.items()):
    if not tag.endswith('_t2'):continue
    center=bb.mean(0);half=(bb[1]-bb[0])/2;eye_offset=half[2]+1.15;alternatives=[]
    for c in cranes:
        pin=np.array(a['groups'][c['luff']]);d=np.array(c['direction']);delta=center-pin;r=float(np.linalg.norm(delta[:2]));yaw=math.atan2(d[0]*delta[1]-d[1]*delta[0],np.dot(d[:2],delta[:2]))
        pitch=math.radians(35);tip_u=np.linalg.norm(np.array(c['tip']['local'])[:2]);tip_z=c['tip']['local'][2]
        def extension(radius):return (radius+tip_z*math.sin(pitch))/math.cos(pitch)-tip_u
        def cargo_z(radius):return pin[2]+radius*math.tan(pitch)+tip_z/math.cos(pitch)-1.3-.80-eye_offset
        # Enough height to carry the whole container above parked crane proxies.
        clear_z=obstacle_top+.6+half[2]
        clear_radius=max(r,(clear_z-pin[2]-tip_z/math.cos(pitch)+1.3+.80+eye_offset)/math.tan(pitch))
        if abs(yaw)>math.radians(170) or extension(r)<0 or extension(clear_radius)>c['extension_range_m'][1]:continue
        vec=delta[:2]/r;raised=center.copy();raised[2]=cargo_z(r)
        high=raised.copy();high[:2]=pin[:2]+vec*clear_radius;high[2]=cargo_z(clear_radius)
        # Slew outward, leaning toward the trailer's longitudinal center.
        end_yaw=math.copysign(math.radians(170),yaw if abs(yaw)>.001 else 1.)
        points=[]
        for t in np.linspace(0,1,61):points.append(('vertical',center+(raised-center)*t))
        for t in np.linspace(0,1,61):points.append(('clearance',raised+(high-raised)*t))
        base_angle=math.atan2(d[1],d[0])
        for angle in np.linspace(yaw,end_yaw,121):points.append(('swing',np.array([pin[0]+clear_radius*math.cos(base_angle+angle),pin[1]+clear_radius*math.sin(base_angle+angle),high[2]])))
        end=points[-1][1].copy();ground=end.copy();ground[2]=half[2]+.002
        for t in np.linspace(0,1,101):points.append(('lower',end+(ground-end)*t))
        obstacles=[(n,b) for n,b in boxes.items() if n!=tag]+[(n,b) for n,b in stationary if not n.startswith(c['name']+'_')]
        names=[x[0] for x in obstacles];bounds=np.array([x[1] for x in obstacles]);hits=[]
        for phase,p in points:
            overlap=np.minimum(p+half,bounds[:,1])-np.maximum(p-half,bounds[:,0])
            colliding=np.where(np.all(overlap>.003,axis=1))[0]
            for i in colliding:
                key=(phase,names[i])
                if key not in hits:hits.append(key)
        alternatives.append(dict(crane=c['name'],pickup_radius_m=r,pickup_yaw_rad=yaw,
                                 carry_pitch_rad=pitch,carry_extension_m=extension(clear_radius),
                                 carry_bottom_m=high[2]-half[2],drop_yaw_rad=end_yaw,
                                 samples=len(points),collisions=hits))
    clear=[p for p in alternatives if not p['collisions']]
    rows.append(dict(container=tag,clear_candidates=clear,blocked_candidates=[p for p in alternatives if p['collisions']]))
report=dict(top_tier_slots=len(rows),slots_with_clear_cargo_path=sum(bool(r['clear_candidates']) for r in rows),parked_obstacle_top_m=obstacle_top,slots=rows,scope=__doc__)
(O/'reports/crane_paths.json').write_text(json.dumps(report,indent=2))
print({k:v for k,v in report.items() if k not in ['slots','scope']})
for r in rows:
    if not r['clear_candidates']:print(r['container'],[(p['crane'],p['collisions']) for p in r['blocked_candidates']])
