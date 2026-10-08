"""Fit both source legs to the unchanged C15 upperbody reconstruction.

C15 is an unaccepted appearance approximation, not qualified hardware. Its
evaluated GLB triangles are rigidly relocated, never rescaled or redrawn.
The approved AA3 artwork remains the appearance authority. This fit is useful
for discovering assembly problems; it cannot qualify a whole robot.
"""
from pathlib import Path
import copy
import hashlib
import json
import numpy as np
import trimesh as tr

O = Path(__file__).resolve().parent
UPPER = Path('/home/ethan/Projects/Sai_Rotbots/experiments/gorilla_v0_1/appearance_c_round_fifteen')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    leg = json.loads((O / 'assembled_scene.json').read_text())
    frame_sha = sha(O / 'candidate_scene.json')
    assert leg['parent_geometry_sha256'] == frame_sha
    grounded = json.loads((O / 'grounded_crouch_report.json').read_text())
    assert grounded['source_sha256'] == frame_sha
    upper_fit=json.loads((O/'upper_fit_interface_scene.json').read_text())
    assert upper_fit['source_hashes']['leg_frame']==frame_sha
    half_spacing=leg.get('whole_fit_hip_half_spacing_m',upper_fit['hip_half_spacing_m'])
    assert half_spacing==upper_fit['hip_half_spacing_m']
    glb_to_engineering = np.array([[1., 0, 0], [0, 0, -1.], [0, 1., 0]])
    old_hip_midpoint = np.array([-.045, 0, 1.66])
    hip = np.array(leg['stations_world_m']['hip'])
    offset = np.array([hip[0], 0, hip[2]]) - old_hip_midpoint
    parts=copy.deepcopy(upper_fit['parts'])
    upper_records=[{'name':p['name'],'geometry_origin':p['geometry_origin'],
                    'vertices':len(p['vertices_world_m']),'triangles':len(p['faces'])}for p in parts]
    reflect = np.diag([1., -1., 1., 1.])
    placement=np.eye(4);placement[1,3]=half_spacing-hip[1]
    placement_inverse=np.linalg.inv(placement)
    for side, T in (('left', placement), ('right', reflect@placement)):
        for p in leg['parts']:
            q = copy.deepcopy(p)
            q['name'] = side + '_' + p['name']
            q['body'] = side + '_' + p['body']
            q['source_group'] = side + '_leg'
            v = tr.transform_points(np.array(p['vertices_world_m']), T)
            f = np.array(p['faces'])
            if side == 'right':
                f = f[:, ::-1]
            q['vertices_world_m'] = v.tolist()
            q['faces'] = f.tolist()
            parts.append(q)
    poses = []
    for probe in grounded['poses']:
        T = {b: np.array(t) for b, t in probe['body_transforms'].items()}
        for d in leg['drivers']:
            A, B = np.array(d['A_neutral_world_m']), np.array(d['B_neutral_world_m'])
            a = tr.transform_points(A[None], T[d['parent']])[0]
            b = tr.transform_points(B[None], T[d['child']])[0]
            R = tr.geometry.align_vectors(B-A, b-a)[:3, :3]
            for owner, now, old in ((d['barrel_body'], a, A), (d['rod_body'], b, B)):
                matrix = np.eye(4)
                matrix[:3, :3] = R
                matrix[:3, 3] = now - R @ old
                T[owner] = matrix
        translation = np.array(probe['hip_world_m']) - hip
        upper_transform = np.eye(4)
        upper_transform[:3, 3] = translation
        body_transforms = {p['body']: upper_transform.tolist() for p in parts
                           if p['source_group'] == 'upperbody_approximation'}
        for b, t in T.items():
            placed_t=placement@t@placement_inverse
            body_transforms['left_' + b] = placed_t.tolist()
            body_transforms['right_' + b] = (reflect @ placed_t @ reflect).tolist()
        poses.append({'sample': probe['sample'], 'hip_world_m': probe['hip_world_m'],
                      'body_transforms': body_transforms})
    v = np.vstack([p['vertices_world_m'] for p in parts])
    scene = {'revision': 'short_leg_whole_fit_02_with_native_hip_interface', 'coordinate_frame': leg['coordinate_frame'],
             'parts': parts, 'poses': poses,
             'source_hashes': {'leg_assembly': sha(O/'assembled_scene.json'),
                               'leg_frame': frame_sha,
                               'crouch_path': sha(O/'grounded_crouch_report.json'),
                               'C15_upper_scene': sha(UPPER/'appearance_c_scene.json'),
                               'C15_evaluated_glb': sha(UPPER/'appearance_c.glb'),
                               'C15_evaluated_manifest': sha(UPPER/'evaluated_mesh_manifest.json'),
                               'upper_fit_interface':sha(O/'upper_fit_interface_scene.json'),
                               'builder': sha(Path(__file__))},
             'upperbody_import': {'reference_directory': str(UPPER),
                                  'parts': upper_records, 'scale_changed': False,
                                  'glb_to_engineering_rotation': glb_to_engineering.tolist(),
                                  'translation_m': offset.tolist(),
                                  'old_display_hip_midpoint_m': old_hip_midpoint.tolist(),
                                  'replaced_internal_display_parts':upper_fit['replaced_internal_display_parts'],
                                  'source_is_not_accepted_AA3_geometry': True},
             'reference_bounds_m': [v.min(0).tolist(), v.max(0).tolist()],
             'reference_height_m': float(v[:, 2].max()),
             'hip_interface_mismatch': {'upper_display_half_spacing_m': .31,
                                        'new_leg_half_spacing_m': half_spacing,
                                        'native_pitch_carrier_geometry_installed':True,
                                        'pitch_drive_installed':False},
             'hip_interfaces':upper_fit['hip_interfaces'],
             'native_hip_carrier_density_mass_kg':upper_fit['carrier_density_integral_mass_kg'],
             'status': 'finite whole-fit geometry including pitch carrier, before wholebody physics',
             'physical_accepted': False, 'appearance_accepted': False,
             'limits': ['Upperbody is an unaccepted C15 reconstruction; AA3 artwork unchanged.',
                        'Rigid level torso follows solved hip translation; no dynamics implied.',
                        'Native pitch carrier with real bore/shaft/clevis replaces three legacy internal display boxes; hip drives not installed.',
                        'Upperbody density, components and inertia are unassigned.']}
    (O/'whole_fit_scene.json').write_text(json.dumps(scene, indent=2, allow_nan=False)+'\n')
    print('WHOLE_FIT', len(parts), 'parts', 'reference_height_m', scene['reference_height_m'],
          'deep_height_m', scene['reference_height_m'] + poses[-1]['hip_world_m'][2] - hip[2], flush=True)


if __name__ == '__main__':
    main()
