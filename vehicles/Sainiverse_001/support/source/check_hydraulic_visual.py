"""Measured rendered hydraulics fixtures, with explicit remaining exclusions."""
from pathlib import Path
import hashlib,json
import numpy as np
from suspension_physics import ROOT
OUT=ROOT/'candidates/r020_hydraulics'
LABELS=['hydraulic_track_review','hydraulic_whole_review','hydraulic_whole_180','hydraulic_100kmh_180']
def main():
    rows={}
    for label in LABELS:
        raw=json.loads((OUT/'reports'/(label+'.json')).read_text())
        visual=json.loads((OUT/'reports'/(label+'_visual.json')).read_text())
        meta=json.loads((OUT/'reports'/(label+'_source.json')).read_text())
        assert not raw['failed'] and raw['dynamic_bodies']==129 and raw['joints']==128
        assert meta['runtime_restored'] and not meta['changed_sources']
        assert 'ERROR:' not in (OUT/'reports'/(label+'.log')).read_text()
        assert visual['groups']==21 and visual['physical_wheels']==72 and visual['visual_meshes']==119
        assert visual['maximum_wheel_binding_error_m']<.0001
        state=raw['samples'][-1]['hydraulics']
        assert state['valid'] and state['max_pressure_Pa']<=70e6*(1+1e-10)
        assert state['max_pump_power_W']<=1.5e6+1e-6 and state['max_inventory_error_m3']<1e-7
        frames=visual['frames'];ms=np.array([f['frame_ms'] for f in frames])
        ratio=(frames[-1]['simulation_s']-frames[0]['simulation_s'])/((frames[-1]['wall_usec']-frames[0]['wall_usec'])/1e6)
        row=dict(samples=len(ms),simulation_seconds=visual['seconds'],peak_forward_speed_kmh=raw['peak_speed_kmh'],terrain=raw['terrain'],resolution=visual['resolution'],gpu=visual['gpu'],rendering_method=visual['rendering_method'],msaa=visual['msaa'],physics_hz=visual['physics_hz'],
            median_fps=float(1000/np.median(ms)),p95_frame_ms=float(np.percentile(ms,95)),simulation_wall_ratio=ratio,mean_visual_update_ms=visual['mean_visual_update_ms'],maximum_wheel_binding_error_m=visual['maximum_wheel_binding_error_m'],draw_calls_min_max=[min(f['draw_calls'] for f in frames),max(f['draw_calls'] for f in frames)],captures=visual['captures'],
            hydraulic_max_pressure_MPa=state['max_pressure_Pa']/1e6,hydraulic_max_pump_W=state['max_pump_power_W'],max_inventory_error_m3=state['max_inventory_error_m3'])
        row['isolated_performance_fixture']=not bool(visual['captures'])
        row['performance_gate_pass']=bool(row['median_fps']>=30 and row['p95_frame_ms']<=40 and ratio>=.98) if row['isolated_performance_fixture'] else None
        if '180' in label:assert row['performance_gate_pass'] and len(ms)>1000
        if '100kmh' in label:assert 99.5<raw['peak_speed_kmh']<101
        rows[label]=row
    report=dict(fixtures=rows,scope='Three exterior modules, actual native 129-body/128-joint physics, 72 hydraulic banks, guided axle/piston display, shadows and 4x MSAA. Fixed belt loop remains unresolved. No interiors, robots, crane operation, accumulator/tank hardware or full science-station workload. Exterior-fixture FPS is not complete-game acceptance.',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'reports/visual_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
