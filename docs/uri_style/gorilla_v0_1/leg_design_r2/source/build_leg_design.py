"""Art-owned leg proportions, articulation and armor; not manufacturing CAD.

Use the previously checked three-link FK as a proportion guide. No actuator,
drill, bearing-fit, pressure rating or material strength is frozen by this file.
Every view and the articulation preview come from the same mesh source.
"""
from pathlib import Path
import copy
import hashlib
import json
import sys
import numpy as np
import trimesh as tr
import manifold3d as mf

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 'leg_redesign_r1' / 'native'
sys.path.insert(0, str(OLD))
import build_candidate as g

BLUE = [.015, .57, .88, 1.]
WHITE = [.91, .88, .80, 1.]
GOLD = [1., .64, .13, 1.]
DARK = [.075, .08, .084, 1.]
METAL = [.27, .30, .32, 1.]
HALF_SPACING = .39


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def solid(p):
    return mf.Manifold(mf.Mesh64(np.array(p['vertices_world_m'], dtype=np.float64, order='C'),
                                np.array(p['faces'], dtype=np.uint64, order='C')))


def loft(a, b, sections, wall=None):
    """Closed chamfered loft; wall creates a real open-ended armor cavity."""
    a, b = np.array(a), np.array(b)
    u = (b-a) / np.linalg.norm(b-a)
    v = np.array([0., 1., 0.])
    n = np.cross(v, u)
    points, faces = [], []
    rings = []
    for t, width, depth in sections:
        w, d = width/2, depth/2
        c = .22
        local = [(-w, -d*(1-c)), (-w*(1-c), -d), (w*(1-c), -d), (w, -d*(1-c)),
                 (w, d*(1-c)), (w*(1-c), d), (-w*(1-c), d), (-w, d*(1-c))]
        rings.append([a+(b-a)*t+v*x+n*y for x, y in local])
    points = np.array(rings).reshape(-1, 3).tolist()
    count = len(rings)
    for k in range(count-1):
        for j in range(8):
            q, r = k*8+j, k*8+(j+1)%8
            faces += [[q, r, r+8], [q, r+8, q+8]]
    faces += [[0, j+1, j] for j in range(1, 7)]
    faces += [[8*(count-1), 8*(count-1)+j, 8*(count-1)+j+1] for j in range(1, 7)]
    mesh = tr.Trimesh(points, faces, process=True)
    mesh.fix_normals()
    outer = mf.Manifold(mf.Mesh64(np.array(mesh.vertices, dtype=np.float64, order='C'),
                                 np.array(mesh.faces, dtype=np.uint64, order='C')))
    if wall:
        # Leave end caps, with motion windows cut afterward. An uncapped
        # tube shows a large empty rectangle in front view and is not armor.
        aa = a+(b-a)*sections[0][0]
        bb = a+(b-a)*sections[-1][0]
        cavity = loft(aa+u*wall, bb-u*wall,
                      [((t-sections[0][0])/(sections[-1][0]-sections[0][0]), w-2*wall, d-2*wall)
                       for t, w, d in sections])
        outer = outer-cavity
    assert outer.status() == mf.Error.NoError and outer.volume() > 0
    return outer


def add(parts, name, body, material, rgba, role, **extra):
    assert material.status() == mf.Error.NoError and material.volume() > 0, name
    m = material.to_mesh64()
    parts.append({'name': name, 'body': body, 'rgba': rgba, 'role': role,
                  'vertices_world_m': np.asarray(m.vert_properties[:, :3]).tolist(),
                  'faces': np.asarray(m.tri_verts).tolist(),
                  'geometry_origin': 'new_art_native_geometry',
                  'source_group': 'leg_design', **extra})


def trim_articulation_windows(parts, path):
    """Reserve the neighboring moving envelopes in each armor's local frame.

    These are appearance relief windows, not drills/bores/fit dimensions. Use
    actual finite neighbors plus 3 mm visual assembly clearance. Earlier
    outer surfaces take visual precedence over later nested surfaces.
    """
    order = ['thigh', 'middle', 'distal', 'shoe']
    finished = set()
    for owner in order:
        neighbors = []
        for p in parts:
            if p['body'] == owner:
                continue
            if p['role'] in ('kinematic_guide', 'contact_pad') or p['body'] in finished:
                neighbors.append((p['body'], solid(p)))
        # Hollow structure guides need no shape change. For the armor use a
        # conservative outer clearance hull per neighboring mesh; do not
        # rely on the reference probe's drilled bore to route a new surface.
        sweep = []
        for body, m in neighbors:
            grown = m.hull().minkowski_sum(mf.Manifold.cube([.006]*3, True))
            for pose in path['poses'][::4]:
                T = {b: np.array(t) for b, t in pose['body_transforms'].items()}
                rel = np.linalg.inv(T[owner])@T[body]
                sweep.append(grown.transform(rel[:3, :4].copy()))
        cutter = mf.Manifold.batch_boolean(sweep, mf.OpType.Add)
        trimmed = 0
        for p in parts:
            if p['body'] != owner or p['role'] in ('kinematic_guide', 'contact_pad'):
                continue
            original = solid(p)
            revised = original-cutter
            assert revised.status() == mf.Error.NoError and revised.volume() > 0, p['name']
            if original.volume()-revised.volume() > 1e-10:
                m = revised.to_mesh64()
                p['vertices_world_m'] = np.asarray(m.vert_properties[:, :3]).tolist()
                p['faces'] = np.asarray(m.tri_verts).tolist()
                p['motion_relief_window'] = True
                trimmed += 1
        print('ART_RELIEF', owner, trimmed, 'surfaces', flush=True)
        finished.add(owner)


def main():
    frame = json.loads((OLD/'candidate_scene.json').read_text())
    path = json.loads((OLD/'grounded_crouch_report.json').read_text())
    upper = json.loads((OLD/'upper_fit_interface_scene.json').read_text())
    assert path['source_sha256'] == sha(OLD/'candidate_scene.json')
    station = {k: np.array(v) for k, v in frame['stations_world_m'].items()}
    parts = []
    for p in frame['parts']:
        q = copy.deepcopy(p)
        q.pop('density_kg_m3', None)
        q.pop('construction', None)
        q['geometry_origin'] = 'prior_kinematic_clearance_guide'
        q['source_group'] = 'leg_design'
        q['role'] = 'kinematic_guide' if q['role'] != 'contact_pad' else q['role']
        q['rgba'] = DARK if q['role'] != 'contact_pad' else [.035, .04, .045, 1]
        parts.append(q)
    # The previous finite frame is only a guide underneath these surfaces;
    # its engineering holes and wall numbers are NOT a new Art requirement.
    for body, a, b, sections in (
        ('thigh', 'hip', 'knee', [( .29, .265, .245), (.50, .32, .27), (.62, .295, .255)]),
        ('middle', 'knee', 'fold', [(.20, .23, .175), (.45, .255, .195), (.78, .22, .165)]),
        ('distal', 'fold', 'ankle', [(.26, .275, .20), (.50, .29, .205), (.74, .255, .175)])):
        add(parts, body+'_blue_armor', body, loft(station[a], station[b], sections, .015),
            BLUE, 'armor', design_intent='Chamfered segment follows its own complete load link; guide thickness only.')
    add(parts, 'thigh_lower_orange_panel', 'thigh',
        loft(station['hip'], station['knee'], [(.62, .295, .255), (.81, .251, .207)], .015),
        GOLD, 'armor', design_intent='Orange lower-thigh cap, matching approved palette assignment.')
    # Low ankle cover merges with the long distal fork silhouette. There is
    # no fourth short serial link stacked between the calf and the sole.
    for joint, owner, radius in (('knee', 'middle', .106), ('fold', 'distal', .106), ('ankle', 'shoe', .093)):
        for side in (-1, 1):
            c = station[joint] + np.array([0., side*.146, 0.])
            add(parts, f'{joint}_joint_cover_{side}', owner, g.cylinder(c, radius, .028),
                METAL, 'joint_cover', design_intent='Appearance joint envelope; engineering determines bearings and fastening.')
            c += [0., side*.014, 0.]
            add(parts, f'{joint}_orange_rim_{side}', owner,
                g.cylinder(c, radius+.001, .006, radius-.009), GOLD, 'joint_cover')
    # Entire sole is newly designed: one continuous keel from toe to heel.
    add(parts, 'foot_continuous_keel', 'shoe', g.box([.025, .5, .058], [.59, .30, .040]),
        DARK, 'foot_support', design_intent='Continuous toe-heel bridge, not isolated old shoe pads.')
    toe = [( .018, .026), (.350, .026), (.340, .076), (.260, .120), (.085, .132), (.018, .091)]
    from shapely.geometry import Polygon
    # Two hollow outer cheek covers leave the center low ankle support clear.
    for side in (-1, 1):
        add(parts, f'foot_toe_ivory_side_{side}', 'shoe',
            g.extrude(Polygon(toe), .5+side*.125, .025), WHITE, 'armor')
    heel = [(-.288, .026), (-.115, .026), (-.118, .110), (-.185, .119), (-.270, .085)]
    for side in (-1, 1):
        add(parts, f'foot_heel_ivory_side_{side}', 'shoe',
            g.extrude(Polygon(heel), .5+side*.112, .024), WHITE, 'armor')
    add(parts, 'foot_heel_dark_guard', 'shoe',
        g.box([-.246, .5, .073], [.056, .235, .074]), DARK, 'armor')
    add(parts, 'foot_front_top_plate', 'shoe',
        g.box([.214, .5, .086], [.21, .226, .038]), WHITE, 'armor')
    add(parts, 'foot_ivory_low_hull', 'shoe',
        loft([-.270, .5, .067], [.335, .5, .067],
             [(0., .25, .072), (.22, .27, .126), (.73, .30, .130), (1., .235, .044)], .014),
        WHITE, 'armor', design_intent='Low continuous faceted toe-heel casing; calf enters a relieved ankle saddle.')

    trim_articulation_windows(parts, path)

    placement = np.eye(4); placement[1, 3] = HALF_SPACING-.5
    reflection = np.diag([1., -1., 1., 1.])
    upper_parts = copy.deepcopy(upper['parts'])
    # Internal prior carrier is retained for fit context only. We do not
    # develop any manufacturing detail in this appearance deliverable.
    for p in upper_parts:
        p.pop('density_kg_m3', None)
        p['source_group'] = 'upper_context'
    whole = upper_parts[:]
    for side, transform in (('left', placement), ('right', reflection@placement)):
        for p in parts:
            q = copy.deepcopy(p)
            q['name'] = side+'_'+p['name']; q['body'] = side+'_'+p['body']
            q['source_group'] = side+'_leg'
            q['vertices_world_m'] = tr.transform_points(np.array(p['vertices_world_m']), transform).tolist()
            if side == 'right':
                q['faces'] = np.array(p['faces'])[:, ::-1].tolist()
            whole.append(q)
    poses = []
    hip = station['hip']
    for k in path['poses']:
        root = np.eye(4); root[:3, 3] = np.array(k['hip_world_m'])-hip
        T = {p['body']: root.tolist() for p in upper_parts}
        for body, matrix in k['body_transforms'].items():
            transform = placement@np.array(matrix)@np.linalg.inv(placement)
            T['left_'+body] = transform.tolist()
            T['right_'+body] = (reflection@transform@reflection).tolist()
        poses.append({'sample': k['sample'], 'body_transforms': T,
                      'hip_world_m': [k['hip_world_m'][0], HALF_SPACING, k['hip_world_m'][2]]})
    v = np.vstack([p['vertices_world_m'] for p in whole])
    s = {'revision': 'leg_design_r2', 'coordinate_frame': frame['coordinate_frame'],
         'parts': whole, 'poses': poses, 'left_stations_m':
         {n: (p+[0., HALF_SPACING-.5, 0.]).tolist() for n, p in station.items()},
         'link_lengths_m': frame['reference_link_lengths_m'],
         'reference_pitches_from_down_vertical_deg': frame['reference_pitches_from_down_vertical_deg'],
         'deep_crouch_pitches_from_down_vertical_deg': frame['deep_crouch_absolute_link_pitches_deg'],
         'hip_half_spacing_m': HALF_SPACING,
         'reference_bounds_m': [v.min(0).tolist(), v.max(0).tolist()],
         'reference_height_m': float(v[:, 2].max()),
         'deep_crouch_height_m': float(v[:, 2].max()+poses[-1]['hip_world_m'][2]-hip[2]),
         'source_hashes': {'builder': sha(Path(__file__)), 'frame_guide': sha(OLD/'candidate_scene.json'),
                          'grounded_fk': sha(OLD/'grounded_crouch_report.json'),
                          'upper_context': sha(OLD/'upper_fit_interface_scene.json')},
         'scope': 'Leg appearance, articulation/proportions and finite armor fit; no manufacturing design or rated load.',
         'upper_context': 'Unaccepted C15 reconstruction, rigidly translated without rescaling. AA3 artwork remains upper appearance authority.',
         'engineering_owner': '启动 Gorilla V0.1 工程方案',
         'not_frozen': ['drilling', 'bearings', 'wall thickness/material', 'actuator architecture/SKU',
                        'hip attachment', 'mass/inertia', 'strength/fatigue', 'rated payload', 'foot articulation'],
         'old_height_lock_released': True, 'physical_accepted': False, 'appearance_accepted': False}
    (ROOT/'source'/'leg_design_scene.json').write_text(json.dumps(s, indent=2)+'\n')
    exchange = tr.Scene()
    to_y_up = np.array([[1.,0,0,0], [0,0,1.,0], [0,-1.,0,0], [0,0,0,1.]])
    for p in whole:
        if p['source_group'] == 'upper_context':
            continue
        mesh = tr.Trimesh(np.array(p['vertices_world_m']), np.array(p['faces']), process=False)
        mesh.apply_transform(to_y_up)
        mesh.visual = tr.visual.TextureVisuals(material=tr.visual.material.PBRMaterial(
            baseColorFactor=np.round(np.array(p['rgba'])*255).astype(np.uint8),
            metallicFactor=.18, roughnessFactor=.40))
        mesh.metadata = {'body_owner': p['body'], 'appearance_part': True, 'manufacturing_part': False}
        exchange.add_geometry(mesh, node_name=p['name'], geom_name=p['name'])
    (ROOT/'source'/'leg_design_legs.glb').write_bytes(exchange.export(file_type='glb'))
    print('ART_DESIGN', len(parts), 'leg parts,', len(whole), 'whole context parts, height', s['reference_height_m'])


if __name__ == '__main__':
    main()
