"""Validate r022's rendered native regression against r021's same physical inputs."""
from pathlib import Path
import json,hashlib
import numpy as np
from suspension_physics import ROOT
OUT=ROOT/'candidates/r022_runtime/reports'
OLD=ROOT/'candidates/r021_track_tension/reports'
def read(p):return json.loads(p.read_text())
def delta(a,b):
    fields=['hull_positions','speed_m_s','wheel_travel_m','hitch_coordinates']
    return {f:float(np.max(np.abs(np.array([s[f] for s in a['samples']])-np.array([s[f] for s in b['samples']])))) for f in fields}
def main():
    assert read(OUT/'native_path_equivalence.json')['passed']
    fixtures={}
    for name,old in [('runtime_track_30','tension_track_v2'),('runtime_whole_180','tension_whole_180_v2'),('runtime_100kmh_same_command_180','tension_100kmh_180_v2')]:
        raw=read(OUT/(name+'.json'));v=read(OUT/(name+'_visual.json'));meta=read(OUT/(name+'_source.json'))
        assert not raw['failed'] and raw['dynamic_bodies']==153 and raw['joints']==152
        assert meta['runtime_restored'] and not meta['changed_sources']
        assert v['native_path_active'] and v['state_texture_bytes_match'] and v['state_texture_size']==[36,24]
        assert v['visual_meshes']==119 and v['physical_wheels']==72 and v['groups']==21
        assert max(v['maximum_wheel_binding_error_m'],v['maximum_idler_binding_error_m'])<.0001
        old_meta=read(OLD/(old+'_source.json'))
        for key in ['seconds','speed','terrain','curvature','capture','view']:assert meta['arguments'][key]==old_meta['arguments'][key],key
        dif=delta(raw,read(OLD/(old+'.json')));assert max(dif.values())==0.
        f=v['frames'];ms=np.array([x['frame_ms'] for x in f]);ratio=(f[-1]['simulation_s']-f[0]['simulation_s'])/((f[-1]['wall_usec']-f[0]['wall_usec'])/1e6)
        ov=read(OLD/(old+'_visual.json'));oldfps=1000/np.median([x['frame_ms'] for x in ov['frames']])
        row=dict(median_fps=float(1000/np.median(ms)),p95_ms=float(np.percentile(ms,95)),simulation_wall_ratio=ratio,visual_update_ms=v['mean_visual_update_ms'],previous_fps=float(oldfps),fps_gain=float(1000/np.median(ms)/oldfps),physical_max_deltas=dif,maximum_wheel_binding_error_m=v['maximum_wheel_binding_error_m'],maximum_idler_binding_error_m=v['maximum_idler_binding_error_m'],gpu=v['gpu'],physics_hz=v['physics_hz'],resolution=v['resolution'],msaa=v['msaa'],captures=v['captures'],peak_forward_kmh=raw['peak_speed_kmh'])
        if not v['captures']:assert row['median_fps']>=120 and row['p95_ms']<=40 and ratio>=.98
        if '100kmh' in name:assert 99.5<raw['peak_speed_kmh']<101
        fixtures[name]=row
    probes={}
    baseline=read(OUT/'baseline_12s.json')
    for name in ['freeze_12s','static_12s','no_upload_12s','cached_path_12s','native_path_12s','native_texture_12s']:
        d=delta(baseline,read(OUT/(name+'.json')));assert max(d.values())==0
        probes[name]={'measured':read(OUT/(name+'_probe.json')),'physical_max_deltas':d}
    report=dict(passed=True,fixtures=fixtures,diagnostic_ablations=probes,scope='Full current exterior at 1080p GB10, native 200 Hz physical fixture. Source, GLB, shape algorithm and independent native physical states checked; no full-game/interior/robot/crane performance acceptance.',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'runtime_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(fixtures,indent=2))
if __name__=='__main__':main()
