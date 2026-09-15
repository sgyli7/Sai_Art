"""Exact planar-profile extrusion for visual authoring; supports recesses/holes."""
import numpy as np
import trimesh
import manifold3d


def extrude_xz(outline, center_y, width, holes=()):
    if not np.isfinite(width) or width<=0:raise ValueError('Positive extrusion width required')
    paths=[np.asarray(ring,dtype=np.float64) for ring in [outline,*holes]]
    if any(p.ndim!=2 or p.shape[1]!=2 or len(p)<3 or not np.isfinite(p).all() for p in paths):
        raise ValueError('Finite planar contours with at least three vertices required')
    cross=manifold3d.CrossSection(paths,manifold3d.FillRule.EvenOdd)
    raw=cross.extrude(width).to_mesh()
    q=np.asarray(raw.vert_properties)[:,:3].astype(float)
    # (planar x, planar z, extrusion y) -> source XYZ; swap reverses winding.
    vertices=np.column_stack((q[:,0],q[:,2]+center_y-width/2,q[:,1]))
    mesh=trimesh.Trimesh(vertices=vertices,faces=np.asarray(raw.tri_verts)[:,::-1],process=False)
    expected=float(cross.area()*width)
    if not mesh.is_volume or abs(mesh.volume-expected)>max(1e-7,expected*2e-5):
        raise ValueError('Profile export lost its volume or winding')
    mesh.metadata['profile_area_m2']=float(cross.area())
    mesh.metadata['profile_width_m']=float(width)
    mesh.metadata['profile_holes']=len(holes)
    return mesh


def circle_xz(x,z,radius,segments=32):
    a=np.arange(segments)*2*np.pi/segments
    return np.column_stack((x+radius*np.cos(a),z+radius*np.sin(a))).tolist()
