"""Assess full current exterior fixtures without hiding their frame regression."""
from pathlib import Path
import json,hashlib
import numpy as np
from suspension_physics import ROOT
OUT=ROOT/'candidates/r021_track_tension/reports'
LABELS=['tension_track_v1','tension_track_v2','tension_whole_180_v1','tension_whole_180_v2','tension_100kmh_180_v2']
def main():
    rows={}
    for label in LABELS:
        raw=json.loads((OUT/(label+'.json')).read_text());a=json.loads((OUT/(label+'_visual.json')).read_text());meta=json.loads((OUT/(label+'_source.json')).read_text())
        assert meta['runtime_restored'] and not meta['changed_sources']
        assert not raw['failed'] and raw['dynamic_bodies']==153 and raw['joints']==152
        assert a['groups']==21 and a['physical_wheels']==72 and a['visual_meshes']==119
        assert max(a['maximum_wheel_binding_error_m'],a['maximum_idler_binding_error_m'])<.0001
        assert 'ERROR:' not in (OUT/(label+'.log')).read_text()
        t=raw['samples'][-1]['track_tension'];assert t['max_tension_N']<=1.5e6 and t['idler_range_m'][0]>-.32 and t['idler_range_m'][1]<.24
        f=a['frames'];ms=np.array([x['frame_ms'] for x in f]);ratio=(f[-1]['simulation_s']-f[0]['simulation_s'])/((f[-1]['wall_usec']-f[0]['wall_usec'])/1e6)
        row=dict(samples=len(ms),seconds=a['seconds'],resolution=a['resolution'],gpu=a['gpu'],msaa=a['msaa'],physics_hz=a['physics_hz'],terrain=raw['terrain'],median_fps=float(1000/np.median(ms)),p95_frame_ms=float(np.percentile(ms,95)),simulation_wall_ratio=ratio,peak_forward_speed_kmh=raw['peak_speed_kmh'],visual_update_ms=a['mean_visual_update_ms'],track_force_step_ms=t.get('mean_track_step_ms'),maximum_wheel_binding_error_m=a['maximum_wheel_binding_error_m'],maximum_idler_binding_error_m=a['maximum_idler_binding_error_m'],captures=a['captures'])
        row['performance_gate_pass']=None if a['captures'] else bool(row['median_fps']>=30 and row['p95_frame_ms']<=40 and ratio>=.98)
        if not a['captures']:assert row['performance_gate_pass']
        if '100kmh' in label:assert 99.5<raw['peak_speed_kmh']<101.
        rows[label]=row
    old=json.loads((OUT/'tension_track_v1.json').read_text());new=json.loads((OUT/'tension_track_v2.json').read_text());state_delta={}
    for field in ['hull_positions','speed_m_s','wheel_travel_m','hitch_coordinates']:
        x=np.array([s[field] for s in old['samples']]);y=np.array([s[field] for s in new['samples']]);state_delta[field]=float(np.max(abs(x-y)));assert state_delta[field]<1e-8
    report=dict(fixtures=rows,display_optimization_physical_state_max_delta=state_delta,scope='Complete three-module exterior and current 153-body/152-joint physics only. Frame regression from r020 remains material; no interiors, robots, crane handling or complete-game FPS acceptance.',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'visual_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
