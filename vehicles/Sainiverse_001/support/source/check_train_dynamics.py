"""Compare native three-module acceleration/braking without hiding failures."""
from pathlib import Path
import argparse,hashlib,json,math
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
def values(data,key):return np.array([s[key] for s in data['samples']],dtype=float)
def main():
    p=argparse.ArgumentParser();p.add_argument('--containers-first',action='store_true');p.add_argument('--mujoco-label',default='straight_brake_mujoco_initial');p.add_argument('--godot-label',default='straight_brake_godot_initial');p.add_argument('--output-label',default='straight_brake_comparison');p.add_argument('--brake-at',type=float,default=75.);args=p.parse_args()
    assert all(s.replace('_','').isalnum() for s in [args.mujoco_label,args.godot_label,args.output_label])
    out=ROOT/'candidates/r016_modular'/('train_containers_first' if args.containers_first else 'train')/'reports'
    files=[out/(args.mujoco_label+'.json'),out/(args.godot_label+'.json')]
    m,g=[json.loads(f.read_text()) for f in files];weight=m['total_mass_kg']*9.81
    assert m['total_mass_kg']==g['total_mass_kg'] and len(m['samples'])==len(g['samples'])
    assert np.max(abs(values(m,'time')-values(g,'time')))<1e-6
    metrics={}
    for key in ['speed_m_s','hull_positions','heave_m','wheel_travel_m','hitch_coordinates','normal_load_N']:
        delta=values(m,key)-values(g,key);metrics[key]=dict(rmse=float(np.sqrt(np.mean(delta**2))),maximum=float(np.max(abs(delta))))
    limits=dict(speed_rmse_m_s=.1,hull_position_rmse_m=.1,heave_rmse_m=.02,wheel_travel_rmse_m=.04,
        support_load_rmse_fraction_of_weight=.05,all_step_joint_anchor_residual_m=.01,all_step_lateral_path_error_m=.5,
        sampled_wheel_abs_travel_m=.36,sampled_heave_abs_travel_m=.81,minimum_sampled_upright=math.cos(math.radians(20)),
        peak_speed_kmh=99.5,stopped_speed_m_s=.05,steady_support_error_fraction=.001)
    checks=dict(native_runs_finished=not m['failed'] and not g['failed'],
        speed=metrics['speed_m_s']['rmse']<limits['speed_rmse_m_s'],hull_position=metrics['hull_positions']['rmse']<limits['hull_position_rmse_m'],
        heave=metrics['heave_m']['rmse']<limits['heave_rmse_m'],wheel_travel=metrics['wheel_travel_m']['rmse']<limits['wheel_travel_rmse_m'],
        support_load=metrics['normal_load_N']['rmse']/weight<limits['support_load_rmse_fraction_of_weight'],
        joint_anchors=g['maximum_all_step_joint_anchor_residual_m']<limits['all_step_joint_anchor_residual_m'],
        route=max(*m['max_all_step_lateral_path_error_m'],*g['max_all_step_lateral_path_error_m'])<limits['all_step_lateral_path_error_m'],
        travel_stops=max(np.max(abs(values(m,'wheel_travel_m'))),np.max(abs(values(g,'wheel_travel_m'))))<limits['sampled_wheel_abs_travel_m'] and max(np.max(abs(values(m,'heave_m'))),np.max(abs(values(g,'heave_m'))))<limits['sampled_heave_abs_travel_m'],
        upright=min(values(m,'upright').min(),values(g,'upright').min())>limits['minimum_sampled_upright'],
        top_speed=min(m['peak_speed_kmh'],g['peak_speed_kmh'])>=limits['peak_speed_kmh'],
        stopped=max(abs(m['samples'][-1]['speed_m_s']),abs(g['samples'][-1]['speed_m_s']))<limits['stopped_speed_m_s'],
        steady_weight=max(abs(m['samples'][-1]['normal_load_N']-weight),abs(g['samples'][-1]['normal_load_N']-weight))/weight<limits['steady_support_error_fraction'])
    braking={}
    for engine,data in [('mujoco',m),('godot',g)]:
        t=values(data,'time');v=values(data,'speed_m_s');x=values(data,'hull_positions')[:,0,0]
        eligible=np.flatnonzero((t>=args.brake_at)&(abs(v)<limits['stopped_speed_m_s']))
        stop=next((int(i) for i in eligible if np.all(abs(v[i:])<limits['stopped_speed_m_s'])),None)
        braking[engine]=dict(peak_kmh=data['peak_speed_kmh'],brake_command_s=args.brake_at,
            sustained_stop_time_s=float(t[stop]) if stop is not None else None,
            distance_to_sustained_stop_m=float(x[stop]-np.interp(args.brake_at,t,x)) if stop is not None else None,
            final_speed_m_s=float(v[-1]),maximum_anchor_residual_m=data.get('maximum_all_step_joint_anchor_residual_m'),
            final_total_normal_load_N=data['samples'][-1]['normal_load_N'])
    report=dict(module_order=['command','containers','energy'] if args.containers_first else ['command','energy','containers'],
        total_mass_kg=m['total_mass_kg'],weight_N=weight,limits=limits,metrics=metrics,checks={k:bool(v) for k,v in checks.items()},
        all_checks_passed=all(checks.values()),braking=braking,
        evidence_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
        scope=f'{m["seconds"]:.3f} s native flat-ground test with 10 s settling, 100 km/h command and braking at {args.brake_at} s. 200 Hz maxima where explicitly named; comparison/braking from 10 Hz samples. No learned policy, turn, terrain, crane, robot or rendered FPS acceptance. Joint residual threshold stays 10 mm; any failure remains reported.')
    if g.get('rebase_distance_m',0)>0:
        report['origin_checks']=dict(at_least_one_rebase=len(g['origin_rebases'])>0,
            world_continuity=g['maximum_rebase_world_discontinuity_m']<.00005,
            relative_geometry=g['maximum_rebase_relative_change_m']<.00005,
            velocity_unchanged=g['maximum_rebase_velocity_change']==0.)
        report['all_checks_passed']=report['all_checks_passed'] and all(report['origin_checks'].values())
    (out/(args.output_label+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
