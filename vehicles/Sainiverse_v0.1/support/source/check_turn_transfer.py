"""Measured transfer of the trained steering controller with retained failures."""
from pathlib import Path
import hashlib,json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'candidates/r017_turning/reports'
def val(d,k):return np.array([s[k] for s in d['samples']],dtype=float)
def main():
    cases=['tight','reverse','right_holdout','straight100'];results=[];sources={}
    for name in cases:
        suffix='' if name=='right_holdout' else '_trained'
        files=[OUT/f'{name}_{engine}{suffix}.json' for engine in ['mujoco','godot']]
        m,g=[json.loads(p.read_text()) for p in files]
        sources.update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        assert len(m['samples'])==len(g['samples']) and np.max(abs(val(m,'time')-val(g,'time')))<1e-6
        metrics={}
        for key in ['speed_m_s','hull_positions','hitch_coordinates','bogie_yaw_rad','heave_m','wheel_travel_m','normal_load_N']:
            delta=val(m,key)-val(g,key);metrics[key]=dict(rmse=float(np.sqrt(np.mean(delta**2))),maximum=float(abs(delta).max()))
        caps=np.array([5e6,5e7,5e7,3e7]*2+[2e7]*12)
        checks=dict(finished=not m['failed'] and not g['failed'],speed=metrics['speed_m_s']['rmse']<.1,
            position=metrics['hull_positions']['rmse']<.1,joints=metrics['hitch_coordinates']['rmse']<.01 and metrics['bogie_yaw_rad']['rmse']<.01,
            suspension=metrics['heave_m']['rmse']<.02 and metrics['wheel_travel_m']['rmse']<.04,
            support=metrics['normal_load_N']['rmse']/(14972000*9.81)<.05,
            native_anchors=g['maximum_all_step_joint_anchor_residual_m']<.01,
            path=max(m['maximum_all_step_control_path_error_m'],g['maximum_all_step_control_path_error_m'])<1.,
            actual_hitch_limit=max(m['maximum_all_step_hitch_yaw_deg'],g['maximum_all_step_hitch_yaw_deg'])<30.,
            actual_lateral_peak=max(m['maximum_all_step_body_lateral_accel_m_s2'],g['maximum_all_step_body_lateral_accel_m_s2'])<1.,
            finite_actuation=max(np.max(abs(val(m,'actuator_efforts'))/caps),np.max(abs(val(g,'actuator_efforts'))/caps))<=1.000001,
            upright=min(val(m,'upright').min(),val(g,'upright').min())>math.cos(math.radians(10)),
            origin_world_continuity=g['maximum_rebase_world_discontinuity_m']<.00005 and g['maximum_rebase_relative_change_m']<.00005 and g['maximum_rebase_velocity_change']==0.)
        if name=='straight100':checks.update(speed_100=min(m['peak_speed_kmh'],g['peak_speed_kmh'])>=99.5,stopped=max(abs(m['samples'][-1]['speed_m_s']),abs(g['samples'][-1]['speed_m_s']))<.05)
        results.append(dict(case=name,metrics=metrics,checks={k:bool(v) for k,v in checks.items()},passed=all(checks.values()),
            maximum_path_error_m=[m['maximum_all_step_control_path_error_m'],g['maximum_all_step_control_path_error_m']],
            maximum_hitch_yaw_deg=[m['maximum_all_step_hitch_yaw_deg'],g['maximum_all_step_hitch_yaw_deg']],
            native_maximum_anchor_residual_m=g['maximum_all_step_joint_anchor_residual_m']))
    report=dict(cases=results,passed=all(r['passed'] for r in results),source_sha256=sources,
        scope='Four independent native prepared-ground cases: trained tight turn/reverse, unseen right turn, 100 km/h straight acceleration/braking. Native constraints and finite actuator efforts, no pose replay. Low-speed turn results do not validate steering entry from 100 km/h, arbitrary terrain, full moving geometry, robot work or rendered FPS.')
    (OUT/'transfer_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    for r in results:print(r['case'],r['passed'],'position_rmse',r['metrics']['hull_positions']['rmse'],'path',r['maximum_path_error_m'],'native_anchor',r['native_maximum_anchor_residual_m'])
if __name__=='__main__':main()
