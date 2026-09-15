"""Evidence for bindings, unresolved belt length, and the rendered fixture cost."""
from pathlib import Path
import gzip,hashlib,json
import numpy as np
from suspension_physics import ROOT
OUT=ROOT/'candidates/r018_visual_suspension/reports'
def main():
    source=OUT/'rough_track_v3.json';raw=json.loads(source.read_text())
    gear=json.loads((ROOT/'assets/running_gear.json').read_text());w=np.array(gear['wheels_x_z_radius'])
    q=np.array([s['wheel_travel_m'] for s in raw['samples']]).reshape(-1,12,2,3)
    lengths_by_resolution=[]
    # Cauchy's perimeter formula for the convex envelope of the five expanded
    # support circles. This is a lower bound on any closed, taut exterior path;
    # it does not assume that an unstretched belt can intersect a wheel.
    for count in [1440,2880]:
        theta=np.arange(count)*2*np.pi/count;normals=np.c_[np.cos(theta),np.sin(theta)]
        support=w[:,:2]@normals.T+(w[:,2]+.09)[:,None];lengths=[]
        for offsets in q.reshape(-1,3):
            h=support.copy();h[1:4]+=offsets[:,None]*normals[:,1]
            lengths.append(2*np.pi*np.max(h,axis=0).mean())
        lengths_by_resolution.append(np.array(lengths))
    lengths=lengths_by_resolution[-1]
    diagnostic=dict(samples=len(lengths),authored_polygon_loop_length_m=gear['perimeter'],
        minimum_support_envelope_m=float(lengths.min()),maximum_support_envelope_m=float(lengths.max()),
        maximum_required_extension_over_authored_loop_m=float(lengths.max()-gear['perimeter']),
        perimeter_resolution_change_max_m=float(np.max(np.abs(lengths_by_resolution[0]-lengths))),
        sampled_wheel_travel_min_max_m=[float(q.min()),float(q.max())],
        stationary_axle_to_moving_wheel_max_offset_m=float(np.max(abs(q))),
        passed=False,scope='Mechanism screening FAIL: belt length/tensioner and axle/support mechanics must be authored before complete suspended running-gear acceptance.')
    assembly=ROOT/'candidates/r016_modular/train_containers_first/source/assembly.json.gz'
    parts=json.loads(gzip.decompress(assembly.read_bytes()))['parts']
    belt_min=min(min(v[2] for v in p['vertices']) for p in parts if p['group']=='front_bogie_fore_right' and p['motion']['kind']=='belt')
    spec=json.loads((ROOT/'candidates/r017_turning/physics/native_spec.json').read_text())
    initial_z=next(b['position'][2] for b in spec['bodies'] if b['name']=='front')
    diagnostic['nominal_authored_belt_lowest_z_m']=belt_min
    diagnostic['initial_native_root_z_m']=initial_z
    diagnostic['nominal_displayed_belt_lowest_z_m']=belt_min+initial_z-10.
    diagnostic['contact_geometry_issue']='Authored cleat extends about 0.28 m beyond the lower wheel radius; native contact skin is 0.18 m. The nominal display penetrates flat ground by 0.14 m including the 0.04 m nominal contact deflection. Reconcile contact envelope before visual suspension acceptance.'
    results={}
    for label in ['rough_track_v3','whole_180_v4','whole_100kmh_180_v4']:
        path=OUT/(label+'_visual.json')
        if not path.exists():continue
        a=json.loads(path.read_text());meta=json.loads((OUT/(label+'_source.json')).read_text())
        physical=json.loads((OUT/(label+'.json')).read_text())
        assert not physical['failed'] and physical['dynamic_bodies']==129 and physical['joints']==128
        assert meta['runtime_restored'] and not meta['changed_sources']
        assert 'ERROR:' not in (OUT/(label+'.log')).read_text()
        assert a['groups']==21 and a['physical_wheels']==72 and a['visual_meshes']==119
        assert a['maximum_wheel_binding_error_m']<.0001
        if '100kmh' in label:assert 99.5<physical['peak_speed_kmh']<101.
        frames=a['frames'];ms=np.array([f['frame_ms'] for f in frames])
        ratio=(frames[-1]['simulation_s']-frames[0]['simulation_s'])/((frames[-1]['wall_usec']-frames[0]['wall_usec'])/1e6)
        results[label]=dict(samples=len(ms),simulation_seconds=a['seconds'],peak_speed_kmh=physical['peak_speed_kmh'],terrain=physical['terrain'],resolution=a['resolution'],gpu=a['gpu'],rendering_method=a['rendering_method'],msaa=a['msaa'],
            median_fps=float(1000/np.median(ms)),p95_frame_ms=float(np.percentile(ms,95)),simulation_wall_ratio=ratio,
            mean_visual_update_ms=a['mean_visual_update_ms'],maximum_wheel_binding_error_m=a['maximum_wheel_binding_error_m'],
            mean_physics_monitor_ms=float(np.mean([f['physics_ms'] for f in frames])),
            draw_calls_min_max=[min(f['draw_calls'] for f in frames),max(f['draw_calls'] for f in frames)],
            captures=a['captures'],fixture_performance_pass=bool(1000/np.median(ms)>=30 and np.percentile(ms,95)<=40 and ratio>=.98))
    # Rendering/odometry must not feed back into the native physical result.
    before=json.loads((OUT/'rough_whole_v1.json').read_text())
    errors={}
    for field in ['hull_positions','wheel_travel_m','heave_m','hitch_coordinates','speed_m_s']:
        error=float(np.max(np.abs(np.array([s[field] for s in before['samples']])-np.array([s[field] for s in raw['samples']]))))
        assert error<1e-8,(field,error);errors[field]=error
    report=dict(rendered_fixtures=results,belt_mechanism=diagnostic,view_and_shader_change_physical_state_max_delta=errors,
        scope='Bound-wheel diagnostic candidate only. Render metrics include three exterior modules, native 129-body/128-joint dynamics, shadows, 4x MSAA and analytic hard ground. No interiors, robots, crane operation, compliant belt display or whole-game FPS acceptance.',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),source,assembly,ROOT/'candidates/r017_turning/physics/native_spec.json',ROOT/'assets/running_gear.json']})
    (OUT/'visual_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
