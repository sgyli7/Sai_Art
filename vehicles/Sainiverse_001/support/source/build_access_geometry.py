"""Six single-axis cabin doors and exact CSG-based wall contact partition."""
from pathlib import Path
import copy
import gzip
import hashlib
import json
import numpy as np
import trimesh as tm
from suspension_physics import ROOT
from build_bridge_interior import box, prism_xy, mesh
from mesh_profiles import extrude_xz
from convex_csg import subtract_many, manifold, mesh as manifold_mesh
import manifold3d as mf
from export_assembly import export

OUT = ROOT / 'candidates/r025_access'


def cylinder(center, radius, length):
    result = tm.creation.cylinder(radius=radius, height=length, sections=24)
    result.apply_translation(center)
    return result


def ring(center, outer, inner, length):
    return tm.boolean.difference([cylinder(center, outer, length), cylinder(center, inner, length + .01)], engine='manifold')


def main():
    for folder in ['source', 'assets', 'physics', 'reports']:
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    prior = ROOT / 'candidates/r023_interior'
    src = prior / 'source/assembly.json.gz'
    a = json.loads(gzip.decompress(src.read_bytes()))
    original = copy.deepcopy(a)
    cfg = json.loads((ROOT / 'design/vehicle.json').read_text())
    door_cfg = cfg['cabin_access_candidate']
    interior = json.loads((prior / 'source/interior.json').read_text())
    serial = 0
    added, moved, removed = [], [], []

    def add(label, geometry, material, group='front'):
        nonlocal serial
        assert geometry.is_volume, label
        name = f'r025_{serial:04d}_{label}'
        serial += 1
        p = dict(name=name, group=group, material=material, vertices=geometry.vertices.tolist(), faces=geometry.faces.tolist(),
                 motion={'kind': 'static'}, physical_body=group, assembly='cabin_access')
        a['parts'].append(p)
        added.append(name)
        return p

    # The previous bilateral hinge decorations have no single physical axis.
    keep = []
    for p in a['parts']:
        if p['name'].endswith(('bridge_door_hinge', 'bridge_door_hinge_knuckle')):
            removed.append(p['name'])
        else:
            keep.append(p)
    a['parts'] = keep
    doors = []
    moving_tokens = ['bridge_door_leaf', 'bridge_door_handle', 'bridge_door_lock', 'bridge_door_window', 'door_bottom_seal']
    for side in [-1, 1]:
        for index, x in enumerate(cfg['bridge']['door_x']):
            name = f'cabin_door_{"right" if side < 0 else "left"}_{index + 1}'
            pivot = [x - door_cfg['hinge_offset_x_m'], side * door_cfg['hinge_abs_y_m'], 12.84]
            a['groups'][name] = pivot
            names = []
            for p in a['parts']:
                if p['group'] != 'front' or not any(t in p['name'] for t in moving_tokens):
                    continue
                center = mesh(p).bounds.mean(0)
                if center[1] * side < 0 or abs(center[0] - x) > .6:
                    continue
                if p['name'].endswith('bridge_door_lock'):
                    m = mesh(p)
                    m.apply_translation([2 * (x - center[0]), 0, 0])
                    p['vertices'] = m.vertices.tolist()
                p['group'] = name
                p['physical_body'] = name
                names.append(p['name'])
                moved.append(p['name'])
            assert any(n.endswith('bridge_door_leaf') for n in names)
            for j, z in enumerate([11.709, 12.84, 13.971]):
                hx, hy = pivot[:2]
                add('hinge_frame_seat', box([hx - .055, side * 3.578, z], [.12, .15, .34]), 'steel')
                for dz in [-.10, .10]:
                    arm=tm.boolean.difference([box([hx - .027, side * 3.653, z + dz], [.075, .19, .055]),cylinder([hx,hy,z+dz],.026,.07)],engine='manifold')
                    add('hinge_fixed_arm', arm, 'steel')
                    add('hinge_fixed_bearing', ring([hx, hy, z + dz], .048, .026, .065), 'ivory')
                add('hinge_rotating_pin', cylinder([hx, hy, z], .025, .30), 'silver', name)
                add('hinge_leaf_hub', cylinder([hx, hy, z], .044, .10), 'edge', name)
                add('hinge_leaf_arm', box([hx + .092, side * 3.645, z], [.16, .15, .055]), 'edge', name)
                # An annular rotary drive above the middle hinge remains clear
                # of the rotating arm plane, with a separate rotating core.
                if j == 1:
                    add('door_rotary_stator', ring([hx, hy, z + .21], .085, .035, .13), 'steel')
                    add('door_rotary_mount', box([hx - .095, side * 3.615, z + .21], [.05, .20, .09]), 'steel')
                    add('door_rotary_core', cylinder([hx, hy, z + .205], .033, .13), 'silver', name)
            parts = [p for p in a['parts'] if p['group'] == name]
            all_vertices = np.concatenate([np.array(p['vertices']) for p in parts])
            bounds = np.array([all_vertices.min(0), all_vertices.max(0)])
            center = bounds.mean(0)
            size = bounds[1] - bounds[0]
            mass = door_cfg['effective_door_mass_kg']
            inertia = mass / 12 * np.array([size[1]**2 + size[2]**2, size[0]**2 + size[2]**2, size[0]**2 + size[1]**2])
            doors.append(dict(name=name, center_x=x, side=side, pivot_source_m=pivot, axis_source=[0, 0, side],
                              limits_rad=[0, float(np.radians(door_cfg['maximum_open_deg']))],
                              mass_kg=mass, com_local_m=(center - pivot).tolist(), inertia_diagonal_kg_m2=inertia.tolist(),
                              parts=[p['name'] for p in parts]))

    # Reproduce the original shell CSG with convex positive cells, then retain
    # each outside halfspace instead of replacing the hollow shell by its hull.
    raw = json.loads(gzip.decompress((ROOT / 'candidates/r021_track_tension/source/assembly.json.gz').read_bytes()))
    outer = mesh(next(p for p in raw['parts'] if p['name'].endswith('bridge_shell')))
    positives = []
    splits = [16, 17, 27.4, 29.1, 31.8, 34]
    for lo, hi in zip(splits, splits[1:]):
        piece = tm.boolean.intersection([outer, box([(lo + hi) / 2, 0, 12], [hi - lo, 20, 20])], engine='manifold')
        assert abs(piece.convex_hull.volume - piece.volume) < 2e-5
        positives.append(piece.convex_hull)
    floor = interior['floor_z']
    ceiling = cfg['bridge_interior_candidate']['ceiling_z']
    inner = tm.boolean.intersection([prism_xy(interior['inner_plan_xy'], floor - .025, ceiling),
              extrude_xz([(16.22, floor - .025), (33.8, floor - .025), (33.8, ceiling), (17.16, ceiling)], 0, 6.6)], engine='manifold')
    cutters = [inner.convex_hull, box([31.45, 0, 10.38], [4., 5.1, 1.40])]
    for d in interior['doors']:
        cutters.append(box([d['center_x'], d['side'] * 3.5, floor + d['clear_height_m'] / 2], [d['clear_width_m'], 1.15, d['clear_height_m']]))
    for p in raw['parts']:
        if p['group'] != 'front' or 'bridge_' not in p['name'] or p['material'] != 'glass':
            continue
        m = mesh(p)
        center = m.vertices.mean(0)
        _, _, vh = np.linalg.svd(m.vertices - center, full_matrices=False)
        normal = vh[-1]
        flat = (m.vertices - center) - np.outer((m.vertices - center) @ normal, normal)
        cutters.append(tm.convex.convex_hull(np.vstack([center + flat * .97 + normal * .60, center + flat * .97 - normal * .60])))
    wall_pieces = subtract_many(positives, cutters)
    wall = mesh(next(p for p in a['parts'] if p['name'].endswith('bridge_shell')))
    solid_union = mf.Manifold.batch_boolean([manifold(m) for m in wall_pieces],mf.OpType.Add)
    union=manifold_mesh(solid_union)
    missed = manifold_mesh(manifold(wall)-solid_union)
    missing = (manifold(wall)-solid_union).volume()
    extra = (solid_union-manifold(wall)).volume()
    print('Partition diagnostic',len(wall_pieces),outer.volume,sum(p.volume for p in positives),wall.volume,union.volume,missing,extra,missed.bounds,flush=True)
    if missing>5e-4:missed.export(OUT/'reports/missing_wall.ply')
    assert max(missing, extra) < 5e-4, (missing, extra)
    contacts = [dict(name=f'wall_piece_{i:03d}', body='front', type='convex', vertices_source_m=m.vertices.tolist()) for i, m in enumerate(wall_pieces)]
    for p in a['parts']:
        if p['group'] == 'front' and p['material'] == 'cabin_glass':
            contacts.append(dict(name=p['name'], body='front', type='convex', vertices_source_m=mesh(p).convex_hull.vertices.tolist()))
    for d in doors:
        # Solid leaf proxy includes the window glazing. Its outline follows the
        # authored door, while the two windowed doors remain visually transparent.
        leaf = next(p for p in a['parts'] if p['group'] == d['name'] and p['name'].endswith('bridge_door_leaf'))
        d['contacts'] = [dict(name=leaf['name'], body=d['name'], type='convex', vertices_source_m=mesh(leaf).convex_hull.vertices.tolist())]
    (OUT / 'source/assembly.json.gz').write_bytes(gzip.compress(json.dumps(a, separators=(',', ':')).encode(), mtime=0))
    exported = export(a, OUT / 'assets/leviathan003_access.glb')
    result = dict(doors=doors, wall_contacts=contacts, wall_convex_pieces=len(wall_pieces), wall_missing_volume_m3=float(missing), wall_extra_volume_m3=float(extra),
                  removed=removed, reassigned=moved, added=added, total_parts=len(a['parts']), **exported,
                  previous_original_parts_unchanged=sum(p == q for p, q in zip(original['parts'], a['parts'])) if not removed else None,
                  scope='Authored single-axis doors and partitioned cabin shell. Finite drive/contact testing, moving-door clearance and robot traversal are separate validations. Effective door mass/inertia are provisional simulation inputs, not hardware ratings.',
                  source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [src, Path(__file__), ROOT / 'source/convex_csg.py', ROOT / 'design/vehicle.json']})
    (OUT / 'source/access.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['total_parts', 'render_meshes', 'triangles', 'wall_convex_pieces', 'wall_missing_volume_m3', 'wall_extra_volume_m3']}, indent=2))


if __name__ == '__main__':
    main()
