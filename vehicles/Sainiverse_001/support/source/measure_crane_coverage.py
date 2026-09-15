"""Plan-view reach screen from actual authored crane and cargo geometry.

Circles are optimistic planar reach, never a crane load chart or 3D clearance.
"""
from pathlib import Path
import gzip,hashlib,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'candidates/r016_modular/reports'
def main():
    file=ROOT/'candidates/r015_articulation/source/assembly.json.gz';a=json.loads(gzip.decompress(file.read_bytes()))
    cargo=np.concatenate([p['vertices'] for p in a['parts'] if p['assembly']=='reservoir_bank']);lo,hi=cargo.min(0),cargo.max(0)
    lo[0]+=42;hi[0]+=42
    pivots=[]
    for i in (0,1):
        p=next(p for p in a['parts'] if p['assembly']==f'crane_{i}_fixed' and p['name'].endswith('_crane_slew'))
        v=np.array(p['vertices']);center=(v.min(0)+v.max(0))/2;center[0]+=42;pivots.append(center[:2])
    two=np.array(pivots);four=np.vstack([two,two*[1,-1]])
    x=np.arange(lo[0],hi[0]+.001,.05);y=np.arange(lo[1],hi[1]+.001,.05);xx,yy=np.meshgrid(x,y);points=np.column_stack([xx.ravel(),yy.ravel()])
    results=[];fig,axes=plt.subplots(1,3,figsize=(14,5),layout='constrained')
    for ax,(name,centers,radius) in zip(axes,[('Original two',two,11.2),('Four, same reach',four,11.2),('Four, reach target',four,19.5)]):
        distance=np.linalg.norm(points[:,None,:]-centers[None,:,:],axis=2).min(axis=1);covered=distance<=radius
        results.append(dict(case=name,pivots_local_xy_m=centers.tolist(),radius_m=radius,cargo_sample_coverage_fraction=float(covered.mean()),largest_nearest_pivot_distance_m=float(distance.max()),grid_spacing_m=.05))
        ax.pcolormesh(xx,yy,covered.reshape(xx.shape),cmap=matplotlib.colors.ListedColormap(['#f0c4a5','#93c7b4']),vmin=0,vmax=1,shading='nearest',rasterized=True)
        ax.add_patch(Rectangle((-16.5,-13.5),33,27,fill=False,edgecolor='#33434d',linewidth=1.4))
        for center in centers:
            ax.add_patch(Circle(center,radius,fill=False,edgecolor='#536b81',linewidth=.7,alpha=.5));ax.plot(*center,'o',color='#263e56',markersize=5)
        ax.set(xlim=(-20,20),ylim=(-17,17),aspect='equal',xlabel='Module X (m)',ylabel='Module Y (m)',title=f'{name}\n{len(centers)} cranes · {radius:g} m radius · {covered.mean():.0%} planar coverage')
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Cargo footprint: planar reach only — height, obstacles and rated load not validated',fontsize=12)
    OUT.mkdir(parents=True,exist_ok=True);fig.savefig(OUT/'crane_planar_coverage.png',dpi=150);plt.close(fig)
    report=dict(cargo_bounds_local_m=[lo.tolist(),hi.tolist()],cases=results,source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                scope='Optimistic 2D circle union over existing energy-bank footprint; ignores minimum radius, boom collision, hook/spreader height, rigging, luff limits and rated payload. 19.5 m is a design target, not current crane capability.')
    (OUT/'crane_planar_coverage.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
