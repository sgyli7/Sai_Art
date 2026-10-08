"""Separate source sheets at touching multi-face edges without moving vertices.

Pairs oppositely directed half-edges by closest face normal, then constructs
per-vertex face fans. This only changes corner ownership. It does not remesh,
smooth, fit primitives, remove faces, or resolve geometric intersections.
"""
import itertools
import numpy as np

def separate_touching_sheets(mesh):
    mesh.update()
    nloop=len(mesh.loops)
    vertices=np.empty(len(mesh.vertices)*3,dtype=np.float32)
    mesh.vertices.foreach_get('co',vertices);vertices=vertices.reshape(-1,3)
    loop_vertex=np.empty(nloop,dtype=np.int32);mesh.loops.foreach_get('vertex_index',loop_vertex)
    loop_edge=np.empty(nloop,dtype=np.int32);mesh.loops.foreach_get('edge_index',loop_edge)
    starts=np.empty(len(mesh.polygons),dtype=np.int32);mesh.polygons.foreach_get('loop_start',starts)
    counts=np.empty(len(mesh.polygons),dtype=np.int32);mesh.polygons.foreach_get('loop_total',counts)
    normals=np.empty(len(mesh.polygons)*3,dtype=np.float32);mesh.polygons.foreach_get('normal',normals)
    normals=normals.reshape(-1,3)
    face_for_loop=np.repeat(np.arange(len(counts)),counts)
    next_loop=np.arange(nloop,dtype=np.int32)+1
    next_loop[starts+counts-1]=starts
    parent=np.arange(nloop,dtype=np.int32)
    rank=np.zeros(nloop,dtype=np.int8)
    def find(a):
        root=a
        while parent[root]!=root:root=int(parent[root])
        while parent[a]!=a:
            b=int(parent[a]);parent[a]=root;a=b
        return root
    def union(a,b):
        a,b=find(a),find(b)
        if a==b:return
        if rank[a]<rank[b]:a,b=b,a
        parent[b]=a
        if rank[a]==rank[b]:rank[a]+=1
    def pair(a,b):
        if loop_vertex[a]==loop_vertex[b]:
            union(a,b);union(int(next_loop[a]),int(next_loop[b]))
        else:
            union(a,int(next_loop[b]));union(int(next_loop[a]),b)
    order=np.argsort(loop_edge,kind='stable')
    edge_sorted=loop_edge[order]
    boundaries=np.r_[0,np.flatnonzero(np.diff(edge_sorted))+1,nloop]
    multiedges=0;unpaired=0
    for lo,hi in zip(boundaries[:-1],boundaries[1:]):
        corners=order[lo:hi]
        if len(corners)==2:pair(int(corners[0]),int(corners[1]));continue
        if len(corners)==1:unpaired+=1;continue
        multiedges+=1
        start_vertex=int(loop_vertex[corners[0]])
        forward=[int(a) for a in corners if loop_vertex[a]==start_vertex]
        backward=[int(a) for a in corners if loop_vertex[a]!=start_vertex]
        if len(forward)!=len(backward) or len(forward)>4:
            unpaired+=len(corners);continue
        def cost(permutation):
            return sum(-float(normals[face_for_loop[a]]@normals[face_for_loop[b]]) for a,b in zip(forward,permutation))
        optimal=min(itertools.permutations(backward),key=cost)
        for a,b in zip(forward,optimal):pair(a,b)
    roots=np.asarray([find(i) for i in range(nloop)],dtype=np.int32)
    _,first,inverse=np.unique(roots,return_index=True,return_inverse=True)
    new_vertices=vertices[loop_vertex[first]]
    faces=[inverse[s:s+n].tolist() for s,n in zip(starts,counts)]
    return new_vertices,faces,{
        'source_vertices':len(vertices),'output_vertices':len(new_vertices),
        'source_faces':len(counts),'output_faces':len(faces),
        'touching_edges_processed':multiedges,'unpaired_halfedge_cases':unpaired,
        'source_vertex_positions_changed':False,
        'scope':'Corner topology only; geometric intersections and engineering remain unverified',
    }
