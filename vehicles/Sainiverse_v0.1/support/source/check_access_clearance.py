"""Actual triangle sweeps with distance-bounded angular subdivision."""
from pathlib import Path
import gzip
import json
import math
import hashlib
import numpy as np
import trimesh as tm
from suspension_physics import ROOT
from build_bridge_interior import mesh

OUT = ROOT / 'candidates/r025_access'


def rotation(door, angle):
    return tm.transformations.rotation_matrix(door['side'] * angle, [0, 0, 1], door['pivot_source_m'])


def main():
    a = json.loads(gzip.decompress((OUT / 'source/assembly.json.gz').read_bytes()))
    access = json.loads((OUT / 'source/access.json').read_text())
    names = {d['name'] for d in access['doors']}
    bounds = {p['name']: np.array([np.min(p['vertices'], axis=0), np.max(p['vertices'], axis=0)]) for p in a['parts']}
    report = {'doors': {}, 'scope': 'Full visible rigid-part meshes against nearby authored fixed geometry. Compliant door gaskets and bottom seals excluded explicitly. Angular intervals certified by nearest-distance versus rigid rotational displacement bound; no robot locomotion or hardware stress proof.'}
    for door in access['doors']:
        fixed = tm.collision.CollisionManager()
        pivot = np.array(door['pivot_source_m'])
        for p in a['parts']:
            if p['group'] in names or p['group'] != 'front' or 'bridge_door_gasket' in p['name']:
                continue
            b = bounds[p['name']]
            if np.any(b[1] < pivot - [2, 2, 2]) or np.any(b[0] > pivot + [2, 2, 2]):
                continue
            fixed.add_object(p['name'], mesh(p))
        rows = []
        for p in a['parts']:
            if p['group'] != door['name'] or 'door_bottom_seal' in p['name']:
                continue
            m = mesh(p)
            radius = float(np.linalg.norm(m.vertices[:, :2] - pivot[:2], axis=1).max())
            evaluations = 0
            minimum = math.inf
            minimum_angle = 0.
            failure = None

            def interval(lo, hi):
                nonlocal evaluations, minimum, minimum_angle, failure
                mid = (lo + hi) / 2
                transform = rotation(door, mid)
                evaluations += 1
                collision, touching = fixed.in_collision_single(m, transform, return_names=True)
                if collision:
                    failure = dict(angle_deg=math.degrees(mid), parts=sorted(touching))
                    return False
                distance = fixed.min_distance_single(m, transform)
                if distance < minimum:
                    minimum, minimum_angle = float(distance), math.degrees(mid)
                # Every mesh point moves at most this chord between midpoint
                # and either interval endpoint. The distance is 1-Lipschitz.
                bound = 2 * radius * math.sin((hi - lo) / 4)
                if distance > bound + 1e-7:
                    return True
                if hi - lo < 1e-7 or evaluations > 20000:
                    failure = dict(unresolved_interval_rad=[lo, hi], distance_m=float(distance), displacement_bound_m=bound)
                    return False
                return interval(lo, mid) and interval(mid, hi)

            passed = interval(0., door['limits_rad'][1])
            row = dict(part=p['name'], passed=passed, evaluations=evaluations, sampled_min_clearance_m=minimum, minimum_angle_deg=minimum_angle, failure=failure)
            rows.append(row)
            if not passed:
                report['doors'][door['name']] = rows
                report['passed'] = False
                (OUT / 'reports/access_clearance.json').write_text(json.dumps(report, indent=2) + '\n')
                raise AssertionError((door['name'], row))
        report['doors'][door['name']] = rows
        print(door['name'], len(rows), 'parts', sum(r['evaluations'] for r in rows), 'distance evaluations', flush=True)
    # Exact X extrema of all door vertices over the complete permitted arcs
    # prove that adjacent doors on each side cannot overlap at arbitrary angles.
    envelopes = {}
    for door in access['doors']:
        vertices = np.concatenate([np.array(p['vertices']) for p in a['parts'] if p['group'] == door['name']])
        pivot = np.array(door['pivot_source_m'])
        delta = vertices[:, :2] - pivot[:2]
        values = []
        for x, y in delta:
            theta = math.atan2(-door['side'] * y, x)
            candidates = [0., door['limits_rad'][1]] + [theta + n * math.pi for n in range(-2, 3) if 0 < theta + n * math.pi < door['limits_rad'][1]]
            values.extend(pivot[0] + x * math.cos(t) - door['side'] * y * math.sin(t) for t in candidates)
        envelopes[door['name']] = [min(values), max(values)]
    gaps = []
    for side in [-1, 1]:
        doors = sorted((d for d in access['doors'] if d['side'] == side), key=lambda d: d['center_x'])
        for left, right in zip(doors, doors[1:]):
            gap = envelopes[right['name']][0] - envelopes[left['name']][1]
            assert gap > 0, gap
            gaps.append(dict(doors=[left['name'], right['name']], minimum_x_gap_m=gap))
    report.update(passed=True, independent_door_sweep_x_bounds=envelopes, independent_door_gaps=gaps,
                  source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), OUT / 'source/assembly.json.gz', OUT / 'source/access.json']})
    (OUT / 'reports/access_clearance.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
