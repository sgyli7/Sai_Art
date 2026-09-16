"""Scope-limited cross-engine ground dynamics comparison with visible gaps."""
from pathlib import Path
import hashlib,json,math
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'candidates/r015_articulation/reports/suspension'
CASES=['rough_sprung','rough_rigid','alternating_sprung','ditch_sprung','ramp_sprung','flat_sprung']

def data(label,engine):
    p=OUT/f'suite_v1_{label}_{engine}.json'
    return json.loads(p.read_text()),p
def values(d,k):return np.array([s[k] for s in d['samples']],dtype=float)
def main():
    comparisons=[];sources={}
    for label in CASES:
        m,mp=data(label,'mujoco');g,gp=data(label,'godot')
        sources[mp.name]=hashlib.sha256(mp.read_bytes()).hexdigest();sources[gp.name]=hashlib.sha256(gp.read_bytes()).hexdigest()
        assert len(m['samples'])==len(g['samples'])
        assert np.max(abs(values(m,'time')-values(g,'time')))<1e-6
        metrics={}
        for key in ['speed_m_s','hull_positions','heave_m','wheel_travel_m','normal_load_N']:
            delta=values(m,key)-values(g,key)
            metrics[key]=dict(rmse=float(np.sqrt(np.mean(delta**2))),maximum=float(np.max(abs(delta))))
        limits=dict(speed_rmse_m_s=.10,hull_position_rmse_m=.10,heave_rmse_m=.02,wheel_travel_rmse_m=.04,
                    support_load_rmse_fraction_of_weight=.05,all_step_anchor_residual_m=.01,
                    all_step_route_error_m=.50,sampled_wheel_abs_travel_m=.36,sampled_heave_abs_travel_m=.81,
                    minimum_sampled_upright=math.cos(math.radians(20)))
        state_checks=dict(native_runs_finished=not m['failed'] and not g['failed'],
            speed=metrics['speed_m_s']['rmse']<limits['speed_rmse_m_s'],
            hull_position=metrics['hull_positions']['rmse']<limits['hull_position_rmse_m'],
            heave=metrics['heave_m']['rmse']<limits['heave_rmse_m'],
            wheel_travel=metrics['wheel_travel_m']['rmse']<limits['wheel_travel_rmse_m'],
            support_load=metrics['normal_load_N']['rmse']/98100000<limits['support_load_rmse_fraction_of_weight'],
            joint_anchors=g['maximum_all_step_joint_anchor_residual_m']<limits['all_step_anchor_residual_m'],
            route=max(*m['max_all_step_lateral_path_error_m'],*g['max_all_step_lateral_path_error_m'])<limits['all_step_route_error_m'],
            travel_stops=max(np.max(abs(values(m,'wheel_travel_m'))),np.max(abs(values(g,'wheel_travel_m'))))<limits['sampled_wheel_abs_travel_m'] and max(np.max(abs(values(m,'heave_m'))),np.max(abs(values(g,'heave_m'))))<limits['sampled_heave_abs_travel_m'],
            upright=min(values(m,'upright').min(),values(g,'upright').min())>limits['minimum_sampled_upright'])
        if label=='flat_sprung':state_checks['top_speed']=min(m['peak_speed_kmh'],g['peak_speed_kmh'])>=99.5
        peak_m=np.array(m['peak_all_step_vertical_accel_m_s2']);peak_g=np.array(g['peak_all_step_vertical_accel_m_s2'])
        rms_m=np.array(m['rms_all_step_vertical_accel_after_settle_m_s2']);rms_g=np.array(g['rms_all_step_vertical_accel_after_settle_m_s2'])
        # Explicit diagnostic thresholds; never hide high-frequency disagreement
        # behind a position/velocity pass or downsampled acceleration samples.
        peak_agreement=bool(np.all(abs(peak_m-peak_g)<=np.maximum(.5,.25*np.maximum(peak_m,peak_g))))
        rms_agreement=bool(np.all(abs(rms_m-rms_g)<=np.maximum(.05,.25*np.maximum(rms_m,rms_g))))
        comparisons.append(dict(case=label,metrics=metrics,limits=limits,state_checks={k:bool(v) for k,v in state_checks.items()},
            state_comparison_passed=all(state_checks.values()),acceleration_peak_agreement=peak_agreement,acceleration_rms_agreement=rms_agreement,
            mujoco_peak_accel=peak_m.tolist(),godot_peak_accel=peak_g.tolist(),mujoco_rms_accel=rms_m.tolist(),godot_rms_accel=rms_g.tolist(),
            mujoco_peak_kmh=m['peak_speed_kmh'],godot_peak_kmh=g['peak_speed_kmh']))
    ride={}
    for engine in ['mujoco','godot']:
        sprung,_=data('rough_sprung',engine);rigid,_=data('rough_rigid',engine)
        x=np.linspace(20,200,1000)
        sp=values(sprung,'hull_positions')[:,0];rp=values(rigid,'hull_positions')[:,0]
        lateral_difference=np.interp(x,sp[:,0],sp[:,1])-np.interp(x,rp[:,0],rp[:,1])
        speed_difference=np.interp(x,sp[:,0],values(sprung,'speed_m_s'))-np.interp(x,rp[:,0],values(rigid,'speed_m_s'))
        comparable=bool(max(*sprung['max_all_step_lateral_path_error_m'],*rigid['max_all_step_lateral_path_error_m'])<.5 and np.max(abs(lateral_difference))<.25 and np.sqrt(np.mean(speed_difference**2))<.20)
        sa=np.array(sprung['rms_all_step_vertical_accel_after_settle_m_s2']);ra=np.array(rigid['rms_all_step_vertical_accel_after_settle_m_s2'])
        ride[engine]=dict(route_and_speed_comparable=comparable,maximum_distance_matched_path_difference_m=float(np.max(abs(lateral_difference))),
            distance_matched_speed_difference_rmse_m_s=float(np.sqrt(np.mean(speed_difference**2))),rms_reduction_fraction=(1-sa/np.maximum(ra,1e-12)).tolist(),
            scope='Same 18 km/h command and terrain; RMS uses every 200 Hz step after first 10 s over this 65 s test. Reduced contact model only, not a hardware or arbitrary-terrain performance rating.')
    report=dict(scope='Independent 85-body candidate ground dynamics, no learned controller, visuals, robot boarding or FPS acceptance.',
        comparisons=comparisons,ride=ride,state_comparisons_passed=all(x['state_comparison_passed'] for x in comparisons),
        acceleration_agreement_passed=all(x['acceleration_peak_agreement'] and x['acceleration_rms_agreement'] for x in comparisons),
        overall_user_goal_complete=False,evidence_sha256=sources)
    (OUT/'cross_engine_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    for c in comparisons:print(c['case'],'state',c['state_comparison_passed'],'peak',c['acceleration_peak_agreement'],'rms',c['acceleration_rms_agreement'],'speed_rmse',round(c['metrics']['speed_m_s']['rmse'],6))
    print(json.dumps(ride,indent=2))

if __name__=='__main__':main()
