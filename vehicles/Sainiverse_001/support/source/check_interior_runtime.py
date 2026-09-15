"""Check the authored interior and independently integrated full carrier fixture."""
from pathlib import Path
import hashlib
import json
import numpy as np
from suspension_physics import ROOT

OUT = ROOT / 'candidates/r023_interior/reports'
OLD = ROOT / 'candidates/r022_runtime/reports'


def read(path):
    return json.loads(path.read_text())


def main():
    for name in ['interior_geometry', 'interior_contacts_validation']:
        assert read(OUT / (name + '.json'))['passed']
    mj = read(OUT / 'rough_mujoco.json')
    assert not mj['failed'] and len(mj['samples']) == 650
    assert max(mj['previous_state_max_deltas'].values()) == 0
    fixtures = {}
    comparisons = {
        'interior_whole_180': 'runtime_whole_180',
        'interior_100kmh_180': 'runtime_100kmh_same_command_180',
    }
    for name in ['controls_v2', 'workshop_v2', *comparisons]:
        raw = read(OUT / (name + '.json'))
        visual = read(OUT / (name + '_visual.json'))
        room = read(OUT / (name + '_interior.json'))
        meta = read(OUT / (name + '_source.json'))
        assert not raw['failed'] and raw['dynamic_bodies'] == 153 and raw['joints'] == 152
        assert meta['returncode'] == 0 and meta['runtime_restored'] and not meta['changed_sources']
        for relative, digest in meta['source_sha256'].items():
            assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, relative
        assert visual['visual_meshes'] == 124 and visual['groups'] == 21 and visual['physical_wheels'] == 72
        assert visual['native_path_active'] and visual['state_texture_bytes_match']
        assert visual['state_texture_size'] == [36, 24]
        assert max(visual['maximum_wheel_binding_error_m'], visual['maximum_idler_binding_error_m']) < .0001
        assert room['contact_shapes'] == 35 and not room['contact_cache_enabled']
        assert room['static_figure_meshes'] == 183
        assert room['figures_visible'] == (name not in comparisons)
        assert len(room['floor_rays']) == 32
        assert all(p['hit'] and p['body'] == 'front' and p['error_m'] < .0001 for p in room['floor_rays'])
        assert room['screen_texts'][0].startswith('DRIVE\n') and 'HINGE' in room['screen_texts'][0]
        assert room['screen_texts'][1].startswith('RUNNING GEAR\n') and 'PEAK STROKE' in room['screen_texts'][1]
        frames = visual['frames']
        ms = np.array([f['frame_ms'] for f in frames])
        ratio = (frames[-1]['simulation_s'] - frames[0]['simulation_s']) / ((frames[-1]['wall_usec'] - frames[0]['wall_usec']) / 1e6)
        row = dict(median_fps=float(1000 / np.median(ms)), p95_ms=float(np.percentile(ms, 95)),
                   simulation_wall_ratio=ratio, captures=visual['captures'],
                   peak_forward_kmh=raw['peak_speed_kmh'], gpu=visual['gpu'], resolution=visual['resolution'],
                   physics_hz=visual['physics_hz'], msaa=visual['msaa'],
                   floor_ray_max_error_m=max(p['error_m'] for p in room['floor_rays']),
                   screen_texts=room['screen_texts'])
        if name in comparisons:
            old_name = comparisons[name]
            previous = read(OLD / (old_name + '.json'))
            previous_meta = read(OLD / (old_name + '_source.json'))
            for key in ['seconds', 'speed', 'terrain', 'curvature', 'capture', 'view']:
                assert meta['arguments'][key] == previous_meta['arguments'][key], key
            assert len(raw['samples']) == len(previous['samples']) == 1800
            differences = {}
            for field in ['hull_positions', 'speed_m_s', 'wheel_travel_m', 'hitch_coordinates']:
                differences[field] = float(np.max(np.abs(np.array([s[field] for s in raw['samples']]) - np.array([s[field] for s in previous['samples']]))))
            row['previous_state_max_deltas'] = differences
            # The explicit contact-cache setting changes native collision processing.
            # Preserve deltas rather than treating these unlike inputs as identity.
            row['exact_previous_state_identity'] = max(differences.values()) == 0
            assert row['median_fps'] >= 30 and row['p95_ms'] <= 40 and ratio >= .98
            row['optimization_120fps_diagnostic_passed'] = row['median_fps'] >= 120
            if '100kmh' in name:
                assert 99.5 < raw['peak_speed_kmh'] < 101
        fixtures[name] = row
    native = read(OUT / 'interior_whole_180.json')
    transfer = {}
    # Existing r019-r021 paired motion thresholds, applied to the matching 65 s prefix.
    for field, limit in [('speed_m_s', .1), ('hull_positions', .1), ('wheel_travel_m', .04), ('heave_m', .02), ('hitch_coordinates', .01)]:
        error = float(np.sqrt(np.mean((np.array([s[field] for s in mj['samples']]) - np.array([s[field] for s in native['samples'][:650]])) ** 2)))
        transfer[field + '_rmse'] = error
        assert error < limit, (field, error, limit)
    assert native['maximum_all_step_joint_anchor_residual_m'] < .01
    assert native['maximum_all_step_control_path_error_m'] < 1
    report = dict(passed=True, fixtures=fixtures, rough_65s_cross_engine=transfer, mujoco_previous_state_max_deltas=mj['previous_state_max_deltas'],
                  scope='Full carrier with authored interior and floor/fixture contacts, native fixture only. Posed robots visible only in inspection views. No robot policy, moving carrier contact transfer, door/lift/crane control or full-game performance acceptance.',
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT / 'interior_runtime_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(fixtures, indent=2))


if __name__ == '__main__':
    main()
