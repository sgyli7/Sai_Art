"""Verify retained pigments/geometry, dynamic ink bindings and native display cost."""
from pathlib import Path
import gzip
import hashlib
import json
import numpy as np
from suspension_physics import ROOT

OUT = ROOT / 'candidates/r024_atelier'
OLD = ROOT / 'candidates/r023_interior'


def read(p):
    return json.loads(p.read_text())


def main():
    style = read(OUT / 'style.json')
    assert style['palette'] == json.loads(gzip.decompress((OLD / 'source/assembly.json.gz').read_bytes()))['colors']
    assert read(OUT / 'bindings.json')['glb'] == read(OLD / 'bindings.json')['glb']
    for name in ['suspended.xml', 'native_spec.json', 'parameters.json', 'interior_contacts.json']:
        assert (OUT / 'physics' / name).read_bytes() == (OLD / 'physics' / name).read_bytes()
    report = {}
    previous_runs = dict(exterior_style_v3='exterior_before_style_v3', workshop_style_v3='workshop_v2', track_style_v3='interior_whole_180', style_whole_180='interior_whole_180')
    for name, previous in previous_runs.items():
        raw = read(OUT / 'reports' / (name + '.json'))
        old = read(OLD / 'reports' / (previous + '.json'))
        meta = read(OUT / 'reports' / (name + '_source.json'))
        visual = read(OUT / 'reports' / (name + '_visual.json'))
        paint = read(OUT / 'reports' / (name + '_style.json'))
        assert not raw['failed'] and raw['dynamic_bodies'] == 153 and raw['joints'] == 152
        assert meta['runtime_restored'] and not meta['changed_sources'] and meta['returncode'] == 0
        for path, expected in meta['source_sha256'].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
        assert visual['visual_meshes'] == 124 and visual['physical_wheels'] == 72 and visual['groups'] == 21
        assert visual['native_path_active'] and visual['state_texture_bytes_match']
        assert max(visual['maximum_idler_binding_error_m'], visual['maximum_wheel_binding_error_m']) < .0001
        assert paint['animated_ink_passes'] == paint['matching_live_ink_states'] == 72
        assert paint['audited_original_pigments'] == 122 and paint['maximum_original_pigment_error'] < .000001
        deltas = {}
        for key in ['hull_positions', 'speed_m_s', 'wheel_travel_m', 'hitch_coordinates']:
            deltas[key] = float(np.max(np.abs(np.array([s[key] for s in raw['samples']]) - np.array([s[key] for s in old['samples'][:len(raw['samples'])]]))))
        assert max(deltas.values()) == 0, (name, deltas)
        frames = visual['frames']
        ms = np.array([f['frame_ms'] for f in frames])
        ratio = (frames[-1]['simulation_s'] - frames[0]['simulation_s']) / ((frames[-1]['wall_usec'] - frames[0]['wall_usec']) / 1e6)
        row = dict(median_fps=float(1000 / np.median(ms)), p95_frame_ms=float(np.percentile(ms, 95)), simulation_wall_ratio=ratio,
                   physical_max_deltas=deltas, palette_max_error=paint['maximum_original_pigment_error'], captures=visual['captures'],
                   gpu=visual['gpu'], resolution=visual['resolution'], physics_hz=visual['physics_hz'], msaa=visual['msaa'])
        if name == 'style_whole_180':
            assert len(raw['samples']) == 1800 and not visual['captures']
            assert row['median_fps'] >= 30 and row['p95_frame_ms'] <= 40 and ratio >= .98
        report[name] = row
    result = dict(passed=True, original_palette_retained=True, original_glb_reused=True, physics_inputs_byte_identical=True,
                  fixtures=report, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  scope='Native appearance revision with unchanged pigments, full authored geometry and exact sampled dynamics. No new physics/robot training or full-game acceptance.')
    (OUT / 'reports/style_validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
