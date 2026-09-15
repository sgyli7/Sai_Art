"""Size a candidate idler stroke against the actual declared wheel travel.

This geometric screen is not a physical tensioner, chain solver or force model.
"""
from pathlib import Path
import itertools,json,hashlib
import numpy as np
from scipy.optimize import brentq
from suspension_physics import ROOT,U
OUT=ROOT/'candidates/r019_running_gear'
def main():
    gear=json.loads((ROOT/'assets/running_gear.json').read_text());w=np.array(U['wheels_x_z_radius']);target=gear['perimeter']
    theta=np.arange(2048)*2*np.pi/2048;normal=np.c_[np.cos(theta),np.sin(theta)]
    base=w[:,:2]@normal.T+(w[:,2]+.09)[:,None]
    rows=[]
    for offsets in itertools.product(np.linspace(-.35,.35,9),repeat=3):
        support=base.copy();support[1:4]+=np.array(offsets)[:,None]*normal[:,1]
        other=np.max(support[:4],axis=0)
        def error(x):return 2*np.pi*np.maximum(other,support[4]+x*normal[:,0]).mean()-target
        assert error(-.6)<0<error(.6),offsets
        dx=brentq(error,-.6,.6,xtol=1e-10)
        centers=w[:,:2].copy();centers[1:4,1]+=offsets;centers[4,0]+=dx
        gap=min(float(np.linalg.norm(centers[4]-centers[i])-w[4,2]-w[i,2]) for i in range(4))
        rows.append(dict(wheel_travel_m=list(offsets),idler_shift_x_m=dx,residual_m=error(dx),idler_to_other_wheel_circumference_gap_m=gap))
    report=dict(states=len(rows),target_authored_polygon_loop_length_m=target,idler_shift_x_range_m=[min(r['idler_shift_x_m'] for r in rows),max(r['idler_shift_x_m'] for r in rows)],
        maximum_numeric_length_residual_m=max(abs(r['residual_m']) for r in rows),minimum_wheel_circumference_gap_m=min(r['idler_to_other_wheel_circumference_gap_m'] for r in rows),rows=rows,
        scope='Taut expanded-circle convex envelope, one movable +X idler, 9^3 sampled lower-wheel positions across ±0.35 m. Stroke sizing only: no chain pin geometry, continuous envelope proof, finite-force idler or dynamic belt coupling.',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'assets/running_gear.json',ROOT/'design/vehicle.json']})
    (OUT/'reports/tensioner_stroke_screen.json').write_text(json.dumps(report,indent=2)+'\n');print('states',len(rows),'required idler range',report['idler_shift_x_range_m'])
if __name__=='__main__':main()
