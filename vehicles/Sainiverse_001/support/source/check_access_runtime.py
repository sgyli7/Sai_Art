"""Behavioral checks on full-carrier native evidence and opened contact apertures."""
from pathlib import Path
import hashlib,json
import numpy as np
from suspension_physics import ROOT
OUT=ROOT/'candidates/r025_access'
def read(name):return json.loads((OUT/'reports'/name).read_text())
def main():
    m=read('cycle_mujoco_latch_v2.json');g=read('door_cycle_latch_v2.json');cfg=json.loads((OUT/'physics/parameters.json').read_text())['access'];cycles={}
    for name,run in [('MuJoCo',m),('Godot',g)]:
        assert not run['failed'] and len(run['samples'])==450
        s=run['samples'];q=np.array([x['access']['angles_rad'] for x in s]);rate=np.array([x['access']['angular_rates_rad_s'] for x in s]);torque=np.array([x['access']['torques_Nm'] for x in s])
        assert np.isfinite(q).all() and np.isfinite(rate).all() and np.isfinite(torque).all()
        assert q.min()>-.01 and q.max()<np.radians(111.)
        opened=min(s,key=lambda x:abs(x['time']-24))['access'];assert max(abs(np.array(opened['angles_rad'])-np.radians(110)))<.01
        assert max(abs(q[-1]))<.015 and s[-1]['access']['drive_permitted']
        assert not any(any(x['access']['obstructed']) for x in s)
        held=max(abs(x['speed_m_s']) for x in s if 10<=x['time']<28);assert held<.002
        assert all(not x['access']['drive_permitted'] for x in s if 5.1<x['time']<28)
        assert s[-1]['speed_m_s']>4.9
        assert abs(torque).max()<=cfg['open_torque_limit_Nm']+1e-8
        closing=np.array([np.array(x['access']['targets_rad'])<np.array(x['access']['angles_rad'])-.001 for x in s])
        assert np.max(abs(torque[closing]))<=cfg['close_torque_limit_Nm']+1e-8
        assert (abs(torque*rate)<=cfg['motor_power_limit_W']+1e-8).all()
        latch=np.array([x['access']['latch_torques_Nm'] for x in s]);assert abs(latch).max()<=cfg['latch_torque_limit_Nm']+1e-8
        assert all(not x['access']['drive_permitted'] or all(x['access']['latched']) for x in s)
        assert all(not x['access']['drive_permitted'] or (max(abs(np.array(x['access']['angles_rad'])))<.015 and max(abs(np.array(x['access']['angular_rates_rad_s'])))<.02) for x in s)
        cycles[name]=dict(maximum_sampled_open_deg=float(np.degrees(q.max())),maximum_sampled_rate_rad_s=float(abs(rate).max()),maximum_sampled_torque_Nm=float(abs(torque).max()),open_interval_max_vehicle_speed_m_s=held,drive_resume_s=min(x['time'] for x in s if x['time']>28 and x['access']['drive_permitted']))
    pair={}
    for key,limit in [('hull_positions',.03),('speed_m_s',.01),('wheel_travel_m',.01)]:
        delta=np.array([s[key] for s in m['samples']])-np.array([s[key] for s in g['samples']]);value=float(np.sqrt(np.mean(delta**2)));assert value<limit;pair[key+'_rmse']=value
    delta=np.array([s['access']['angles_rad'] for s in m['samples']])-np.array([s['access']['angles_rad'] for s in g['samples']]);pair['maximum_door_angle_difference_rad']=float(abs(delta).max());assert abs(delta).max()<.01
    rays={}
    for name,phases in [('MuJoCo',m['ray_results']),('Godot',read('door_cycle_latch_v2_access.json')['ray_results'])]:
        assert len(phases)==3
        for i,phase in enumerate(phases):
            assert len(phase['rays'])==71
            for ray in phase['rays']:
                expect=ray['kind']!='door' or i!=1
                assert ray['hit']==expect,(name,i,ray)
                if expect:assert ray['body']==ray['expected_body'],(name,i,ray)
        rays[name]=dict(phases=3,rays_per_phase=71,doorway_rays=54,wall_rays=6,window_rays=11,closed_blocked_open_clear=True)
    performance={}
    for label in ['door_cycle_latch_v2','access_whole_latch_v2_180','access_high100_latch_v2_180']:
        raw=read(label+'.json');meta=read(label+'_source.json');v=read(label+'_visual.json');paint=read(label+'_style.json');room=read(label+'_interior.json')
        assert not raw['failed'] and raw['dynamic_bodies']==159 and raw['joints']==158
        assert meta['runtime_restored'] and not meta['changed_sources'] and meta['returncode']==0
        assert 'ERROR:' not in (OUT/'reports'/(label+'.log')).read_text()
        for path,digest in meta['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
        assert v['visual_meshes']==156 and v['groups']==27 and v['physical_wheels']==72
        assert v['native_path_active'] and v['state_texture_bytes_match']
        assert max(v['maximum_idler_binding_error_m'],v['maximum_wheel_binding_error_m'])<.0001
        assert paint['animated_ink_passes']==paint['matching_live_ink_states']==72
        assert paint['audited_original_pigments']==152 and paint['maximum_original_pigment_error']<1e-6
        assert all(p['hit'] and p['body']=='front' and p['error_m']<.0001 for p in room['floor_rays']) and len(room['floor_rays'])==32
        frames=v['frames'];ms=np.array([f['frame_ms'] for f in frames]);ratio=(frames[-1]['simulation_s']-frames[0]['simulation_s'])/((frames[-1]['wall_usec']-frames[0]['wall_usec'])/1e6)
        metrics=dict(median_fps=float(1000/np.median(ms)),p95_frame_ms=float(np.percentile(ms,95)),simulation_wall_ratio=ratio,peak_speed_kmh=raw['peak_speed_kmh'],captures=v['captures'],gpu=v['gpu'],resolution=v['resolution'],physics_hz=v['physics_hz'],msaa=v['msaa'])
        if label!='door_cycle_latch_v2':
            assert len(raw['samples'])==1800 and not v['captures']
            assert metrics['median_fps']>=30 and metrics['p95_frame_ms']<=40 and ratio>=.98
            assert all(x['access']['drive_permitted'] for x in raw['samples'] if x['time']>=10),label
            if label=='access_high100_latch_v2_180':assert 99.9<raw['peak_speed_kmh']<100.1
        performance[label]=metrics
    held_runs={}
    for terrain,mj_label,gd_label in [('rough','rough_mujoco_latch_v2','access_whole_latch_v2_180'),('flat100','high100_mujoco_latch_v2','access_high100_latch_v2_180')]:
        mj=read(mj_label+'.json');gd=read(gd_label+'.json');row={}
        for engine,run in [('MuJoCo',mj),('Godot',gd)]:
            assert not run['failed'] and len(run['samples'])==1800
            samples=[x for x in run['samples'] if x['time']>=10]
            assert all(x['access']['drive_permitted'] and all(x['access']['latched']) for x in samples)
            lock=np.array([x['access']['latch_torques_Nm'] for x in samples]);assert abs(lock).max()<=cfg['latch_torque_limit_Nm']
            row[engine]=dict(maximum_sampled_door_angle_rad=max(max(abs(np.array(x['access']['angles_rad']))) for x in samples),maximum_sampled_latch_torque_Nm=float(abs(lock).max()),peak_speed_kmh=run['peak_speed_kmh'])
            if terrain=='flat100':assert 99.9<run['peak_speed_kmh']<100.1
        held_runs[terrain]=row
    assert read('access_clearance.json')['passed'] and read('access_robot_route.json')['passed']
    result=dict(passed=True,cycles=cycles,paired_engines=pair,contact_rays=rays,performance=performance,closed_latch_runs=held_runs,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='Full 159-body carrier: finite door cycle and compliant transport latch, closed drive interlock, actual wall/window/aperture queries, geometric route screen, native style and performance. No actual robot policy, lift route, obstruction-force qualification, complete-game integration, or hardware rating.')
    (OUT/'reports/access_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
