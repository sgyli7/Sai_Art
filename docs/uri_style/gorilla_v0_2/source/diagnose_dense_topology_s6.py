from pathlib import Path
import bpy,bmesh,json
ROOT=Path(__file__).resolve().parents[1]
result={}
for revision,objname in [('s2','pixal_clear_side_leg'),('s6','pixal_clear_side_leg')]:
    path=ROOT/'source'/('lower_body_spatial_s2.blend' if revision=='s2' else 'lower_dense_surface_s6.blend')
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bm=bmesh.new();bm.from_mesh(bpy.data.objects[objname].data)
    stats={
       'vertices':len(bm.verts),'faces':len(bm.faces),
       'boundary_edges':sum(e.is_boundary for e in bm.edges),
       'wire_edges':sum(e.is_wire for e in bm.edges),
       'multi_face_edges':sum(len(e.link_faces)>2 for e in bm.edges),
       'noncontiguous_two_face_edges':sum(len(e.link_faces)==2 and not e.is_contiguous for e in bm.edges),
    }
    nonmanifold=[e for e in bm.edges if not e.is_manifold]
    stats['nonmanifold_sample']=[{'vertices':[list(v.co) for v in e.verts],'faces':len(e.link_faces)} for e in nonmanifold[:8]]
    result[revision]=stats;bm.free()
(ROOT/'dense_topology_diagnosis_s6.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
