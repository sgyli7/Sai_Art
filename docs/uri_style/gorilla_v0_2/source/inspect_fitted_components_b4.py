"""Measure actual native component topology, articulation and interference.

Optional native views are rendered only from the inspected model. Collision
records include adjacent links and all modules owned by different links.
They are evidence, never assumed acceptance. This is geometric inspection.
"""
from pathlib import Path
import sys, math, json, hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

REV='b4'
for arg in sys.argv:
    if arg.startswith('--revision='):REV=arg.split('=',1)[1]
report_path=ROOT/f'lower_modular_components_{REV}.json'
report=json.loads(report_path.read_text())
source=ROOT/report['source'];bpy.ops.wm.open_mainfile(filepath=str(source))
LEFT=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('L_')]
OWNERS=[bpy.data.objects['L_'+n+'_pitch'] for n in ['thigh','return','shank','foot']]
RIGHT=[bpy.data.objects['R_'+n+'_pitch'] for n in ['thigh','return','shank','foot']]
P,K,H,A=[np.asarray(report['joints'][n]) for n in ['hip','knee','hock','ankle']]


def coords(o):
    v=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',v)
    m=np.asarray(o.matrix_world);return v.reshape(-1,3)@m[:3,:3].T+m[:3,3]


def topology(o):
    bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();bm.verts.index_update()
    edge=np.asarray([[e.verts[0].index,e.verts[1].index] for e in bm.edges]);n=len(bm.verts)
    graph=coo_matrix((np.ones(len(edge)*2),(np.r_[edge[:,0],edge[:,1]],np.r_[edge[:,1],edge[:,0]])),shape=(n,n))
    count,labels=connected_components(graph,directed=False)
    ret={'name':o.name,'owner':o.get('kinematic_owner'),'role':o.get('component_role'),
         'vertices':n,'faces':len(bm.faces),'connected_components':int(count),
         'loose_vertices':sum(not v.link_edges for v in bm.verts),
         'boundary_edges':sum(e.is_boundary for e in bm.edges),
         'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
         'signed_volume':bm.calc_volume(signed=True)}
    bm.free();return ret


def geometry(o):
    o.data.calc_loop_triangles();v=coords(o);f=np.asarray([t.vertices[:] for t in o.data.loop_triangles])
    return v,f,BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True)


def rx(q):
    c,s=math.cos(math.radians(q)),math.sin(math.radians(q))
    return np.array([[1,0,0],[0,c,-s],[0,s,c]])


def collision(a,b,ga,gb):
    # First eliminate disjoint bounds; then inspect actual triangle geometry.
    va,fa,treea=ga;vb,fb,treeb=gb
    if np.any(va.min(0)>vb.max(0)) or np.any(vb.min(0)>va.max(0)):return None
    pairs=treea.overlap(treeb)
    if not pairs:return None
    ia=np.unique([i for i,j in pairs]);ib=np.unique([j for i,j in pairs])
    hit=np.concatenate([va[fa[ia]].reshape(-1,3),vb[fb[ib]].reshape(-1,3)])
    return {'a':a.name,'b':b.name,'triangle_pairs':len(pairs),
            'involved_triangle_bounds':[hit.min(0).tolist(),hit.max(0).tolist()],
            'mean_involved_triangle_coordinate':hit.mean(0).tolist()}


def coplanar_overlap_area(a,b,normal):
    axis=int(np.argmax(abs(normal)));a=np.delete(a,axis,axis=1);b=np.delete(b,axis,axis=1)
    cross=lambda u,v:u[0]*v[1]-u[1]*v[0]
    if cross(b[1]-b[0],b[2]-b[0])<0:b=b[::-1]
    polygon=list(a)
    for i in range(3):
        p,q=b[i],b[(i+1)%3];edge=q-p;new=[]
        if not polygon:break
        for s,e in zip(polygon,[*polygon[1:],polygon[0]]):
            ds,de=cross(edge,s-p),cross(edge,e-p)
            inside_s,inside_e=ds>=0,de>=0
            if inside_s!=inside_e:new.append(s+(e-s)*ds/(ds-de))
            if inside_e:new.append(e)
        polygon=new
    if len(polygon)<3:return 0.
    polygon=np.asarray(polygon)
    return abs(sum(cross(polygon[i],polygon[(i+1)%len(polygon)]) for i in range(len(polygon))))/2


def triangle_crossing_category(a,b,tolerance=1e-7):
    na=np.cross(a[1]-a[0],a[2]-a[0]);nb=np.cross(b[1]-b[0],b[2]-b[0])
    la,lb=np.linalg.norm(na),np.linalg.norm(nb)
    if min(la,lb)<1e-14:return 'degenerate'
    na/=la;nb/=lb
    da=(b-a[0])@na;db=(a-b[0])@nb
    if max(abs(da).max(),abs(db).max())<tolerance:
        area=coplanar_overlap_area(a,b,na)
        return 'coplanar_overlap' if area>2e-13 else 'boundary_contact'
    if da.min()<-tolerance and da.max()>tolerance and db.min()<-tolerance and db.max()>tolerance:
        return 'penetrating'
    return 'boundary_contact'


def self_intersections(o):
    vertices,triangles,tree=geometry(o);found=[];broad_count=0;contacts=0;degenerate=0
    for i,j in tree.overlap(tree):
        if i>=j or np.intersect1d(triangles[i],triangles[j]).size:continue
        broad_count+=1
        category=triangle_crossing_category(vertices[triangles[i]],vertices[triangles[j]])
        if category=='boundary_contact':contacts+=1
        elif category=='degenerate':degenerate+=1
        else:found.append([int(i),int(j),category])
    return {'name':o.name,'nonadjacent_triangle_pairs':len(found),
            'raw_bvh_nonadjacent_pairs':broad_count,'boundary_contact_pairs':contacts,
            'degenerate_triangle_pairs':degenerate,'plane_distance_tolerance':1e-7,
            'sample_pairs':found[:10],
            'scope':'Actual self crossing or positive-area coplanar overlap; shared vertices and tolerance-level boundary contacts reported separately'}


records=[]
for name,angles in [('reference_bent',(0,0,0,0)),('further_fold',(0,-6,6,0)),
                    ('partial_extension',(0,6,-6,0)),('ankle_pitch',(0,0,0,5))]:
    for l,r,q in zip(OWNERS,RIGHT,angles):l.rotation_euler.x=math.radians(q);r.rotation_euler.x=math.radians(q)
    bpy.context.view_layer.update()
    expected=[P,P+rx(angles[0])@(K-P)]
    expected.append(expected[1]+rx(sum(angles[:2]))@(H-K))
    expected.append(expected[2]+rx(sum(angles[:3]))@(A-H))
    gs={o.name:geometry(o) for o in LEFT}
    hits=[]
    for i,a in enumerate(LEFT):
        for b in LEFT[i+1:]:
            if a.get('kinematic_owner')!=b.get('kinematic_owner'):
                hit=collision(a,b,gs[a.name],gs[b.name])
                if hit:hits.append(hit)
    records.append({'pose':name,'angles_degrees':angles,
                    'fk_position_error_max':float(max(np.linalg.norm(np.asarray(o.matrix_world.translation)-p) for o,p in zip(OWNERS,expected))),
                    'mirror_joint_position_error_max':float(max(np.linalg.norm(np.asarray(o.matrix_world.translation)-p*np.array([-1,1,1])) for o,p in zip(RIGHT,expected))),
                    'different_owner_triangle_intersections':hits,
                    'core_carrier_triangle_intersections':[h for h in hits if h['a'] in report['core_names'] and h['b'] in report['core_names']],
                    'scope':'Actual modeled articulation perturbations; no walking, balance, material or load claim'})
    print('NATIVE_COMPONENT_POSE',name,len(hits),flush=True)
for l,r in zip(OWNERS,RIGHT):l.rotation_euler.x=0;r.rotation_euler.x=0
bpy.context.view_layer.update()
top=[topology(o) for o in LEFT]
self_checks=[self_intersections(o) for o in LEFT] if '--self-check' in sys.argv else report.get('self_intersection_checks',[])
mirrors=[]
for o in LEFT:
    right=bpy.data.objects[o.name.replace('L_','R_',1)];expected=coords(o);expected[:,0]*=-1
    mirrors.append({'left':o.name,'right':right.name,'shared_mesh_data':o.data==right.data,
                    'max_vertex_mirror_error':float(np.max(abs(expected-coords(right))))})
report.update(master_topology=top,mirroring=mirrors,pose_checks=records,
              connected_closed_master_components=all(t['connected_components']==1 and not t['nonmanifold_edges'] and t['signed_volume']>0 for t in top),
              strict_shared_mesh_mirroring=all(m['shared_mesh_data'] and m['max_vertex_mirror_error']<1e-7 for m in mirrors),
              core_intersections_observed=any(r['core_carrier_triangle_intersections'] for r in records),
              different_owner_intersections_observed=any(r['different_owner_triangle_intersections'] for r in records))
if self_checks:
    report['self_intersection_checks']=self_checks
    report['master_self_intersections_observed']=any(c['nonadjacent_triangle_pairs'] for c in self_checks)
report_path.write_text(json.dumps(report,indent=2)+'\n')
print('NATIVE_COMPONENT_INSPECTION',report['connected_closed_master_components'],report['core_intersections_observed'],flush=True)

if '--render' not in sys.argv:raise SystemExit(0)
asset=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(('L_','R_'))]
world=np.concatenate([coords(o) for o in asset]);lo,hi=world.min(0),world.max(0)
center=Vector(((lo+hi)/2).tolist());scene=bpy.context.scene;camera=scene.camera
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,float(lo[2])-.00002))
floor=bpy.context.object;floor.name='display_ground_only';floor['excluded_from_asset']=True
m=bpy.data.materials.new('b4_display_floor');m.use_nodes=True
m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.81,.84,.87,1)
m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.82;floor.data.materials.append(m)
scene.cycles.samples=64;scene.cycles.use_denoising=False
views={};scale=float(max(hi-lo)*1.22)
for name,axis in [('front_oblique',(1,-1,.52)),('rear_oblique',(1,1,.52)),
                  ('front',(0,-1,0)),('left',(1,0,0)),('rear',(0,1,0)),('top',(0,0,1))]:
    camera.location=center+Vector(axis).normalized()*3
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
    inv=np.asarray(camera.matrix_world.inverted());projected=world@inv[:3,:3].T+inv[:3,3]
    span=np.ptp(projected[:,:2],axis=0)
    if 'oblique' in name:
        offset=(projected[:,:2].min(0)+projected[:,:2].max(0))/2;basis=np.asarray(camera.matrix_world)[:3,:3]
        camera.location+=Vector((basis[:,0]*offset[0]+basis[:,1]*offset[1]).tolist())
        camera.data.ortho_scale=float(max(span)*1.17)
    else:camera.data.ortho_scale=scale
    out=ROOT/'images'/f'lower_modular_components_{name}_{REV}.png'
    scene.render.filepath=str(out);bpy.ops.render.render(write_still=True)
    views[name]={'image':str(out.relative_to(ROOT)),'span_world':span.tolist(),
                'camera_matrix_world':np.asarray(camera.matrix_world).tolist(),'ortho_scale':camera.data.ortho_scale}
    print('NATIVE_COMPONENT_VIEW',name,flush=True)
if '--foot-detail' in sys.argv:
    original_camera=camera.matrix_world.copy();original_scale=camera.data.ortho_scale
    for o in asset:
        if o.name.startswith('R_'):o.hide_render=True
    foot_world=np.concatenate([coords(o) for o in LEFT if o.get('kinematic_owner')=='foot'])
    # Include the owning fork and axle in the framing as actual source geometry.
    ankle_points=np.concatenate([coords(o) for o in LEFT if 'ankle' in o.name])
    ankle_points=ankle_points[ankle_points[:,2]<-.358]
    focus=np.concatenate([foot_world,ankle_points]);fc=Vector(((focus.min(0)+focus.max(0))/2).tolist())
    for name,axis in [('ankle_front_detail',(1,-1,.65)),('ankle_rear_detail',(1,1,.65))]:
        camera.location=fc+Vector(axis).normalized()*3
        camera.rotation_euler=(fc-camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
        inv=np.asarray(camera.matrix_world.inverted());proj=focus@inv[:3,:3].T+inv[:3,3]
        span=np.ptp(proj[:,:2],axis=0);offset=(proj[:,:2].min(0)+proj[:,:2].max(0))/2
        basis=np.asarray(camera.matrix_world)[:3,:3]
        camera.location+=Vector((basis[:,0]*offset[0]+basis[:,1]*offset[1]).tolist())
        camera.data.ortho_scale=float(max(span)*1.22)
        out=ROOT/'images'/f'lower_modular_components_{name}_{REV}.png'
        scene.render.filepath=str(out);bpy.ops.render.render(write_still=True)
        views[name]={'image':str(out.relative_to(ROOT)),'scope':'One actual master ankle/foot; opposite leg hidden for inspection only',
                    'camera_matrix_world':np.asarray(camera.matrix_world).tolist(),'ortho_scale':camera.data.ortho_scale}
        print('NATIVE_COMPONENT_VIEW',name,flush=True)
    for o in asset:o.hide_render=False
    camera.matrix_world=original_camera;camera.data.ortho_scale=original_scale
bpy.ops.wm.save_as_mainfile(filepath=str(source),compress=True)
report['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();report['views']=views
report['projection_checks']={
    'front_left_height':abs(views['front']['span_world'][1]-views['left']['span_world'][1])<1e-6,
    'front_top_width':abs(views['front']['span_world'][0]-views['top']['span_world'][0])<1e-6,
    'left_top_depth':abs(views['left']['span_world'][0]-views['top']['span_world'][1])<1e-6}
report_path.write_text(json.dumps(report,indent=2)+'\n')
print('NATIVE_COMPONENT_REVIEW_RENDERED',flush=True)
