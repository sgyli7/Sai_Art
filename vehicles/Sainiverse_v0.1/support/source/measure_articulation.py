"""Screen the current authored decks at the newly requested +/-45 deg yaw.

This is a geometry diagnosis, not a dynamics or whole-vehicle clearance pass.
Positive solid intersection proves a blocker; a clear deck sample proves only
that these two solids do not intersect at that sampled angle.
"""
from pathlib import Path
import gzip
import hashlib
import json
import math

import numpy as np
import trimesh as tm

ROOT = Path(__file__).resolve().parents[1]


def main():
    data_path = ROOT / 'source/assembly.json.gz'
    assembly = json.loads(gzip.decompress(data_path.read_bytes()))
    cfg = json.loads((ROOT / 'assets/physics.json').read_text())
    anchor = np.array([cfg['hitch_x'], 0., cfg['hitch_z']])
    decks = {}
    for hull in ('front', 'rear'):
        part = next(p for p in assembly['parts']
                    if p['name'].endswith('_' + hull + '_deck'))
        decks[hull] = tm.Trimesh(vertices=part['vertices'], faces=part['faces'], process=False)
        assert decks[hull].is_volume, 'Need closed oriented actual deck solids'

    def pose(degrees):
        result = decks['rear'].copy()
        result.apply_transform(tm.transformations.rotation_matrix(
            math.radians(degrees), [0, 0, 1], point=anchor))
        return result

    def volume(degrees):
        cut = tm.boolean.intersection([decks['front'], pose(degrees)], engine='manifold')
        return max(0., float(cut.volume)) if len(cut.faces) else 0.

    samples = [dict(yaw_deg=a, intersection_m3=volume(a)) for a in range(-45, 46)]
    first = {}
    for sign in (-1, 1):
        blocked = next((a for a in range(1, 46) if volume(sign*a) > 1e-7), None)
        if blocked is None:
            first[str(sign)] = None
            continue
        lo, hi = float(blocked-1), float(blocked)
        for _ in range(16):
            mid = (lo+hi)/2
            if volume(sign*mid) > 1e-7:
                hi = mid
            else:
                lo = mid
        first[str(sign)] = dict(clear_deg=sign*lo, intersecting_deg=sign*hi,
                               volume_threshold_m3=1e-7)

    import xml.etree.ElementTree as ET
    joint = ET.parse(ROOT/'assets/vehicle.xml').find(".//joint[@name='hitch']")
    native_limit = [float(v) for v in joint.attrib['range'].split()]
    report = dict(source_sha256=hashlib.sha256(data_path.read_bytes()).hexdigest(),
                  requested_yaw_deg=[-45, 45], anchor_m=anchor.tolist(),
                  decks={k:v.bounds.tolist() for k,v in decks.items()},
                  first_deck_intersection=first, samples=samples,
                  current_mujoco_joint=dict(joint.attrib),
                  current_mujoco_ball_limit_deg=list(map(math.degrees,native_limit)),
                  deck_clearance_passed=all(s['intersection_m3'] <= 1e-7 for s in samples),
                  scope='Actual deck solids, pure yaw, zero pitch/roll. Does not screen other parts, '
                        'pipes, suspension travel or dynamic forces. Failing deck samples alone '
                        'prove current geometry cannot satisfy +/-45 degrees without modification.')
    out = ROOT/'reports/articulation_r014'
    out.mkdir(exist_ok=True)
    (out/'deck_sweep.json').write_text(json.dumps(report, indent=2)+'\n')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from scipy.spatial import ConvexHull
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    def footprint(mesh):
        points = mesh.vertices[:, :2]
        return points[ConvexHull(points).vertices]
    front_poly = footprint(decks['front'])
    for ax, degrees in zip(axes, (-45, 0, 45)):
        rear_poly = footprint(pose(degrees))
        for poly, color, label in ((front_poly, '#547b99', 'Front deck'),
                                   (rear_poly, '#c19c60', 'Rear deck')):
            ax.fill(poly[:,0],poly[:,1],color=color,alpha=.55,label=label)
        cut = tm.boolean.intersection([decks['front'], pose(degrees)], engine='manifold')
        if len(cut.faces) and cut.volume > 1e-7:
            poly = footprint(cut)
            ax.fill(poly[:,0],poly[:,1],color='#d92935',label='Solid overlap')
        ax.plot(anchor[0],anchor[1],'ko',markersize=4,label='Hitch')
        ax.set_title(f'Relative yaw {degrees:+d} deg\nDeck overlap {volume(degrees):.2f} m³')
        ax.set_aspect('equal'); ax.set_xlim(-70,22); ax.set_ylim(-48,48)
        ax.set_xlabel('Source X (m)'); ax.set_ylabel('Source Y (m)'); ax.grid(alpha=.2)
    axes[0].legend(fontsize=8,loc='upper left')
    fig.suptitle('r014 geometry diagnosis — deck solids only, not a motion validation')
    fig.savefig(out/'deck_sweep.png', dpi=140)
    print(json.dumps({k:v for k,v in report.items() if k!='samples'}, indent=2))


if __name__ == '__main__':
    main()
