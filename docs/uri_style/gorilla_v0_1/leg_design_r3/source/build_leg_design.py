"""R3 Art rebuild: continuous armored volumes over the prescribed three-link Z.

The R2 appearance is rejected. Its underlying finite FK is reused solely for
joint coordinates and articulation relief, never as an exterior template.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import numpy as np
import trimesh as tr
import manifold3d as mf

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT.parent / 'leg_design_r2' / 'source'
spec = importlib.util.spec_from_file_location('art_geometry_utilities', PREVIOUS/'build_leg_design.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)
OLD = u.OLD
BLUE, WHITE, GOLD, DARK, METAL = u.BLUE, u.WHITE, u.GOLD, u.DARK, u.METAL


def loft(a, b, sections, wall=None):
    """Rounded rectangular cross sections and a long, tapered armor envelope."""
    a, b = np.asarray(a), np.asarray(b)
    axis = (b-a)/np.linalg.norm(b-a)
    lateral = np.array([0., 1., 0.])
    depth = np.cross(lateral, axis)
    ring_count = 24
    verts, faces = [], []
    for t, width, thick in sections:
        for j in range(ring_count):
            angle = 2*np.pi*j/ring_count
            c, s = np.cos(angle), np.sin(angle)
            x = np.sign(c)*abs(c)**(2/3.4)*width/2
            y = np.sign(s)*abs(s)**(2/3.4)*thick/2
            verts.append(a+(b-a)*t+lateral*x+depth*y)
    for k in range(len(sections)-1):
        for j in range(ring_count):
            q = k*ring_count+j
            r = k*ring_count+(j+1)%ring_count
            faces.extend([[q, r, r+ring_count], [q, r+ring_count, q+ring_count]])
    for j in range(1, ring_count-1):
        faces.append([0, j+1, j])
        end = (len(sections)-1)*ring_count
        faces.append([end, end+j, end+j+1])
    mesh = tr.Trimesh(verts, faces, process=True)
    mesh.fix_normals()
    material = mf.Manifold(mf.Mesh64(np.array(mesh.vertices, dtype=np.float64, order='C'),
                                   np.array(mesh.faces, dtype=np.uint64, order='C')))
    if wall:
        start, end = sections[0][0], sections[-1][0]
        inner_a = a+(b-a)*start+axis*wall
        inner_b = a+(b-a)*end-axis*wall
        cavity = loft(inner_a, inner_b,
                      [((t-start)/(end-start), w-2*wall, d-2*wall) for t, w, d in sections])
        material -= cavity
    assert material.status() == mf.Error.NoError and material.volume() > 0
    return material


def main():
    frame = json.loads((OLD/'candidate_scene.json').read_text())
    path = json.loads((OLD/'grounded_crouch_report.json').read_text())
    upper = json.loads((OLD/'upper_fit_interface_scene.json').read_text())
    assert path['source_sha256'] == u.sha(OLD/'candidate_scene.json')
    stations = {k: np.array(v) for k, v in frame['stations_world_m'].items()}
    parts = []
    for p in frame['parts']:
        q = copy.deepcopy(p)
        q.pop('density_kg_m3', None)
        q.pop('construction', None)
        q['role'] = 'contact_pad' if p['role'] == 'contact_pad' else 'kinematic_guide'
        q['rgba'] = DARK
        q['geometry_origin'] = 'prior_finite_FK_guide_not_exterior_design'
        q['source_group'] = 'leg_design'
        parts.append(q)
    # The thigh is an integrated rounded armor mass, not a sleeve suspended
    # between two long exposed loops. Middle and distal shells meet their
    # articulation envelopes while retaining two spatially separated folds.
    for body, a, b, sections in (
        ('thigh', 'hip', 'knee', [(.04,.29,.25),(.12,.375,.32),(.28,.46,.40),
                                (.48,.44,.39),(.64,.405,.36),(.72,.36,.32)]),
        ('middle', 'knee', 'fold', [(.10,.255,.22),(.22,.31,.255),(.38,.34,.28),
                                  (.62,.325,.265),(.80,.28,.23),(.89,.24,.20)]),
        ('distal', 'fold', 'ankle', [(.10,.285,.245),(.22,.355,.29),(.42,.36,.30),
                                   (.64,.33,.27),(.79,.29,.24),(.89,.255,.205)])):
        u.add(parts, body+'_continuous_blue_armor', body,
              loft(stations[a], stations[b], sections, .016), BLUE, 'armor',
              design_intent='Reference-led complete rounded armor volume; not a flat link strip.')
    u.add(parts, 'thigh_integrated_orange_knee_cap', 'thigh',
          loft(stations['hip'], stations['knee'],
               [(.72,.36,.32),(.80,.325,.295),(.89,.285,.26)], .016), GOLD, 'armor')
    for joint, owner, radius in (('knee','middle',.097),('fold','distal',.096),('ankle','shoe',.087)):
        for side in (-1, 1):
            c = stations[joint]+[0., side*.158, 0.]
            u.add(parts, f'{joint}_recessed_cover_{side}', owner,
                  u.g.cylinder(c, radius, .025), METAL, 'joint_cover')
            c += [0., side*.013, 0.]
            u.add(parts, f'{joint}_fine_orange_rim_{side}', owner,
                  u.g.cylinder(c, radius+.001, .004, radius-.004), GOLD, 'joint_cover')
    u.add(parts, 'new_foot_continuous_keel', 'shoe',
          u.g.box([.025,.5,.056], [.59,.30,.036]), DARK, 'foot_support')
    u.add(parts, 'new_foot_low_ivory_shell', 'shoe',
          loft([-.279,.5,.067],[.34,.5,.067],
               [(0.,.245,.065),(.14,.285,.10),(.36,.31,.124),
                (.62,.315,.127),(.86,.285,.096),(1.,.235,.040)], .014), WHITE, 'armor',
          design_intent='One new low toe-heel support casing with an ankle saddle; no old shoe reuse.')
    u.add(parts, 'new_foot_dark_heel_bumper', 'shoe',
          u.g.box([-.253,.5,.067],[.05,.255,.056]), DARK, 'armor')
    u.trim_articulation_windows(parts, path)

    # Only space context is inherited above the waist. The rejected dangling
    # central pelvis and rear tail are completely replaced by a short saddle.
    removed = ('saffron_front_pelvis_cartridge', 'pelvis_front_black_latch',
               'ivory_rear_pelvis_cartridge', 'rear_yellow_pelvis_band',
               'dark_pelvis_inner_layer', 'proposed_hip_pitch_carrier')
    upper_parts = [copy.deepcopy(p) for p in upper['parts']
                   if not any(n in p['name'] for n in removed)]
    for p in upper_parts:
        p.pop('density_kg_m3',None)
        p['source_group'] = 'upper_context'
    hip = stations['hip']
    u.add(upper_parts,'new_short_wide_pelvis_saddle','upper_pelvis',
          loft([hip[0]+.055,0.,1.38],[hip[0]+.055,0.,1.225],
               [(0.,.53,.25),(.32,.54,.26),(.75,.48,.23),(1.,.38,.19)],.016),
          GOLD,'armor',design_intent='Short broad waist saddle; no dangling central blade.')
    upper_parts[-1]['source_group'] = 'upper_context'
    # Keep actual upper context clear of the thicker thigh through the
    # prescribed path. AA3 remains the exterior authority for torso/arms.
    upper_clearance = mf.Manifold.batch_boolean([u.solid(p).hull() for p in upper_parts],mf.OpType.Add)
    local_upper = upper_clearance.translate([0.,.11,0.])
    sweeps=[]
    for pose in path['poses'][::4]:
        root = np.eye(4); root[:3,3] = np.array(pose['hip_world_m'])-hip
        relative = np.linalg.inv(np.array(pose['body_transforms']['thigh']))@root
        sweeps.append(local_upper.transform(relative[:3,:4].copy()))
    cutter=mf.Manifold.batch_boolean(sweeps,mf.OpType.Add)
    for p in parts:
        if p['body'] != 'thigh' or p['role'] == 'kinematic_guide': continue
        m=u.solid(p)-cutter
        assert m.status() == mf.Error.NoError and m.volume()>0,p['name']
        out=m.to_mesh64();p['vertices_world_m']=np.asarray(out.vert_properties[:,:3]).tolist()
        p['faces']=np.asarray(out.tri_verts).tolist()
    placement=np.eye(4);placement[1,3]=u.HALF_SPACING-.5
    reflection=np.diag([1.,-1.,1.,1.])
    whole=upper_parts[:]
    for side,transform in (('left',placement),('right',reflection@placement)):
        for p in parts:
            q=copy.deepcopy(p);q['name']=side+'_'+p['name'];q['body']=side+'_'+p['body']
            q['source_group']=side+'_leg'
            q['vertices_world_m']=tr.transform_points(np.array(p['vertices_world_m']),transform).tolist()
            if side=='right':q['faces']=np.array(p['faces'])[:,::-1].tolist()
            whole.append(q)
    poses=[]
    for k in path['poses']:
        root=np.eye(4);root[:3,3]=np.array(k['hip_world_m'])-hip
        transforms={p['body']:root.tolist() for p in upper_parts}
        for body,matrix in k['body_transforms'].items():
            t=placement@np.array(matrix)@np.linalg.inv(placement)
            transforms['left_'+body]=t.tolist();transforms['right_'+body]=(reflection@t@reflection).tolist()
        poses.append({'sample':k['sample'],'body_transforms':transforms,
                      'hip_world_m':[k['hip_world_m'][0],u.HALF_SPACING,k['hip_world_m'][2]]})
    v=np.vstack([p['vertices_world_m'] for p in whole])
    s={'revision':'leg_design_r3','coordinate_frame':frame['coordinate_frame'],
       'parts':whole,'poses':poses,'left_stations_m':
       {n:(p+[0.,u.HALF_SPACING-.5,0.]).tolist() for n,p in stations.items()},
       'link_lengths_m':frame['reference_link_lengths_m'],
       'reference_pitches_from_down_vertical_deg':frame['reference_pitches_from_down_vertical_deg'],
       'deep_crouch_pitches_from_down_vertical_deg':frame['deep_crouch_absolute_link_pitches_deg'],
       'reference_bounds_m':[v.min(0).tolist(),v.max(0).tolist()],
       'reference_height_m':float(v[:,2].max()),
       'deep_crouch_height_m':float(v[:,2].max()+poses[-1]['hip_world_m'][2]-hip[2]),
       'source_hashes':{'builder':u.sha(Path(__file__)),'frame_guide':u.sha(OLD/'candidate_scene.json'),
                        'grounded_fk':u.sha(OLD/'grounded_crouch_report.json'),
                        'upper_context':u.sha(OLD/'upper_fit_interface_scene.json'),
                        'geometry_utilities':u.sha(PREVIOUS/'build_leg_design.py')},
       'upper_context':'C15 spatial context with new short waist; AA3 torso/arms are appearance authority.',
       'scope':'Art silhouette, armor volumes, joint placement and finite articulation only.',
       'engineering_owner':'启动 Gorilla V0.1 工程方案',
       'r2_appearance_rejected':True,'old_height_lock_released':True,
       'appearance_accepted':False,'physical_accepted':False}
    (ROOT/'source'/'leg_design_scene.json').write_text(json.dumps(s,separators=(',',':'))+'\n')
    exchange=tr.Scene()
    to_y_up=np.array([[1.,0,0,0],[0,0,1.,0],[0,-1.,0,0],[0,0,0,1.]])
    for p in whole:
        if p['source_group']=='upper_context':continue
        mesh=tr.Trimesh(np.array(p['vertices_world_m']),np.array(p['faces']),process=False)
        mesh.apply_transform(to_y_up)
        mesh.visual=tr.visual.TextureVisuals(material=tr.visual.material.PBRMaterial(
            baseColorFactor=np.round(np.array(p['rgba'])*255).astype(np.uint8),
            metallicFactor=.18,roughnessFactor=.40))
        exchange.add_geometry(mesh,node_name=p['name'],geom_name=p['name'])
    (ROOT/'source'/'leg_design_legs.glb').write_bytes(exchange.export(file_type='glb'))
    print('ART_REBUILD_R3',len(parts),'parts per leg; reference height',s['reference_height_m'],flush=True)


if __name__ == '__main__':
    main()
