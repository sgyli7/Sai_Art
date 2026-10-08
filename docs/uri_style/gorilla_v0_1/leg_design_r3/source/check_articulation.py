"""Source-bound finite material check of appearance envelopes and their FK.

No material strength, bearing fit, actuator or whole-body control assertion.
Native torso is fit context only; its preexisting internal assembly is excluded.
"""
from pathlib import Path
import collections
import hashlib
import json
import numpy as np
import trimesh as tr
import manifold3d as mf

O = Path(__file__).resolve().parent
P = O/'leg_design_scene.json'
S = json.loads(P.read_text())


def solid(p):
    return mf.Manifold(mf.Mesh64(np.array(p['vertices_world_m'], dtype=np.float64, order='C'),
                                np.array(p['faces'], dtype=np.uint64, order='C')))


def main():
    groups = collections.defaultdict(list)
    components = []
    for p in S['parts']:
        m = solid(p)
        assert m.status() == mf.Error.NoError and m.volume() > 0, p['name']
        components.append({'name': p['name'], 'finite_positive_solid': True})
        owner = 'upper_context' if p['source_group'] == 'upper_context' else p['body']
        groups[owner].append((p, m))
    unions = {}
    for name, rows in groups.items():
        material = mf.Manifold()
        for p, m in rows:
            material += m
        unions[name] = material
    print('ART_CHECK_START', len(unions), 'material groups', flush=True)
    hits, floor, bounds = [], [], []
    names = list(unions)
    for pose in S['poses']:
        transforms = {b: np.array(t) for b, t in pose['body_transforms'].items()}
        transforms['upper_context'] = transforms['upper_torso']
        solids = {b: m.transform(transforms[b][:3, :4].copy()) for b, m in unions.items()}
        boxes = {b: np.array(m.bounding_box()).reshape(2, 3) for b, m in solids.items()}
        bounds.append({'sample': pose['sample'], 'height_m': max(bb[1, 2] for bb in boxes.values())})
        for name, bb in boxes.items():
            if bb[0, 2] < -1e-7:
                floor.append({'sample': pose['sample'], 'body': name, 'min_z_m': bb[0, 2]})
        for i, a in enumerate(names):
            for b in names[i+1:]:
                aa, bb = boxes[a], boxes[b]
                if np.any(aa[1] < bb[0]) or np.any(bb[1] < aa[0]):
                    continue
                inter = solids[a]^solids[b]
                volume = inter.volume()
                if volume > 1e-10:
                    event = {'sample': pose['sample'], 'a': a, 'b': b,
                             'volume_cm3': volume*1e6, 'intersection_bounds_m': inter.bounding_box()}
                    # Diagnose the first crossing of each group pair using
                    # the actual named meshes, not just bounding boxes.
                    if not any(h['a'] == a and h['b'] == b for h in hits):
                        event['parts'] = []
                        for pa, ma in groups[a]:
                            xa = ma.transform(transforms[a][:3, :4].copy())
                            for pb, mb in groups[b]:
                                xb = mb.transform(transforms[b][:3, :4].copy())
                                if (xa^xb).volume() > 1e-10:
                                    event['parts'].append([pa['name'], pb['name']])
                    hits.append(event)
        if pose['sample'] % 30 == 0:
            print('ART_CHECK', pose['sample'], 'hit_events', len(hits), flush=True)
    report = {'source_sha256': hashlib.sha256(P.read_bytes()).hexdigest(),
              'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'pose_samples': len(S['poses']), 'same_meshes_as_renders': True,
              'collision_events': hits, 'floor_events': floor, 'bounds_by_pose': bounds,
              'sampled_appearance_geometry_clear': len(hits) == len(floor) == 0,
              'physical_accepted': False,
              'scope': 'Finite appearance/guide volumes along prescribed unloaded FK, with both legs and upper context. '
                       'No installed drives, force capacity, fatigue, bearing or manufacturing acceptance; '
                       'preexisting upperbody internal fit excluded.',
              'mesh_checks': components}
    (O/'articulation_check.json').write_text(json.dumps(report, indent=2)+'\n')
    print('ART_CHECK_DONE', len(hits), 'intersections,', len(floor), 'floor events', flush=True)


if __name__ == '__main__':
    main()
