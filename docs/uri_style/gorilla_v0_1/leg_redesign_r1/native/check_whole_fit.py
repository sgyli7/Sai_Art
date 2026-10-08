"""Finite material cross-assembly interference along the source crouch path.

Leg-internal intersections are checked by the existing assembly checker.
Here every upperbody-leg and left-right pair is queried without pair masks.
This is sampled geometric fit, not a proof of strength or a motion limit box.
"""
from pathlib import Path
import hashlib
import json
import time
import numpy as np
import manifold3d as mf

O = Path(__file__).resolve().parent


def main():
    P = O/'whole_fit_scene.json'
    s = json.loads(P.read_text())
    assert s['source_hashes']['leg_assembly'] == hashlib.sha256((O/'assembled_scene.json').read_bytes()).hexdigest()
    parts = s['parts']
    meshes = []
    for p in parts:
        m = mf.Manifold(mf.Mesh64(np.array(p['vertices_world_m'], dtype=np.float64, order='C'),
                                 np.array(p['faces'], dtype=np.uint64, order='C')))
        if m.status() != mf.Error.NoError or m.volume() <= 0:
            raise ValueError((p['name'], m.status(), m.volume()))
        meshes.append(m)
    groups = np.array([p['source_group'] for p in parts])
    upper = np.flatnonzero(groups == 'upperbody_approximation')
    left = np.flatnonzero(groups == 'left_leg')
    right = np.flatnonzero(groups == 'right_leg')
    pairs = np.array([(a,b) for u,v in ((upper,left),(upper,right),(left,right))
                      for a in u for b in v], dtype=int)
    hits, floors, pose_bounds = [], [], []
    pair_totals = {}
    started = time.time()
    for pose in s['poses']:
        transformed = [m.transform(np.array(pose['body_transforms'][p['body']])[:3,:4].copy())
                       for p,m in zip(parts,meshes)]
        bounds = np.array([m.bounding_box() for m in transformed]).reshape(-1,2,3)
        broad = np.all(bounds[pairs[:,0],1] >= bounds[pairs[:,1],0], axis=1)
        broad &= np.all(bounds[pairs[:,1],1] >= bounds[pairs[:,0],0], axis=1)
        for a,b in pairs[broad]:
            volume = float((transformed[a] ^ transformed[b]).volume())
            if volume > 1e-10:
                key = parts[a]['name']+' / '+parts[b]['name']
                entry = {'sample':pose['sample'], 'a':parts[a]['name'], 'b':parts[b]['name'],
                         'a_body':parts[a]['body'], 'b_body':parts[b]['body'],
                         'intersection_cm3':volume*1e6}
                hits.append(entry)
                total = pair_totals.setdefault(key, {'first_sample':pose['sample'], 'last_sample':pose['sample'],
                                                     'samples':0, 'max_intersection_cm3':0.})
                total['last_sample'] = pose['sample']
                total['samples'] += 1
                total['max_intersection_cm3'] = max(total['max_intersection_cm3'], volume*1e6)
        for i in np.flatnonzero(bounds[:,0,2] < -1e-8):
            if parts[i]['role'] != 'contact_pad':
                floors.append({'sample':pose['sample'], 'part':parts[i]['name'],
                               'minimum_z_m':float(bounds[i,0,2])})
        pose_bounds.append({'sample':pose['sample'], 'bounds_m':[bounds[:,0].min(0).tolist(),
                                                              bounds[:,1].max(0).tolist()]})
        if pose['sample'] % 30 == 0:
            print('WHOLE_PROBE',pose['sample'],'/',len(s['poses']),'hits',len(hits),flush=True)
    report = {'source_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),
              'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'parts':len(parts), 'sampled_poses':len(s['poses']), 'cross_assembly_pairs':len(pairs),
              'collision_method':'Finite material Manifold64 CSG; all cross-assembly pairs, 1e-10m3 threshold.',
              'hits':hits, 'pair_totals':pair_totals, 'nonpad_floor_intrusions':floors,
              'pose_bounds':pose_bounds, 'elapsed_seconds':time.time()-started,
              'physical_accepted':False,
              'scope':'Uninstalled upperbody reconstruction and two native legs. Leg-internal checks separate; '
                      'source upperbody self-fit unqualified. No hip drive, continuous sweep or actual wholebody mass.'}
    (O/'whole_fit_report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print('WHOLE_DONE',len(hits),'hits',len(pair_totals),'unique pairs','nonpad_floor',len(floors),flush=True)


if __name__ == '__main__':
    main()
