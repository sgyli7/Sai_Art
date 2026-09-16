"""Convex pieces for authored convex CSG cuts; no hull across a room opening."""
import numpy as np
import trimesh as tm
import manifold3d as mf


def manifold(mesh):
    return mf.Manifold(mf.Mesh64(np.asarray(mesh.vertices, np.float64), np.asarray(mesh.faces, np.uint64)))


def mesh(solid):
    data = solid.to_mesh64()
    return tm.Trimesh(np.asarray(data.vert_properties)[:, :3], np.asarray(data.tri_verts), process=False)


def subtract_convex(parts, cutter, tolerance=1e-9):
    """Disjoint outside halfspaces partition P minus a convex cutter C."""
    c = manifold(cutter)
    normals = cutter.face_normals
    offsets = np.einsum('ij,ij->i', normals, cutter.triangles_center)
    raw_planes = np.column_stack([normals, offsets])
    _, indices = np.unique(np.round(raw_planes, 9), axis=0, return_index=True)
    planes = raw_planes[indices]
    output = []
    for part in parts:
        if (part ^ c).volume() <= tolerance:
            output.append(part)
            continue
        remainder = part
        for plane in planes:
            outside, remainder = remainder.split_by_plane(plane[:3].tolist(), float(plane[3]))
            if outside.volume() > tolerance:
                output.append(outside)
            if remainder.volume() <= tolerance:
                break
    return output


def subtract_many(solids, cutters):
    pieces = [manifold(p) for p in solids]
    for cutter in cutters:
        pieces = subtract_convex(pieces, cutter)
    result = []
    for piece in pieces:
        m = mesh(piece)
        if m.volume < 1e-8:
            continue
        hull = m.convex_hull
        assert abs(hull.volume - m.volume) < max(2e-6, m.volume * 2e-5), (hull.volume, m.volume)
        result.append(hull)
    return result
