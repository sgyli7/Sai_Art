"""Finish connected clean carriers, validate mirror/FK and inspect collisions.

No dense reference geometry is imported. Source-fitted armor is unchanged.
All mechanics below are appearance geometry in normalized units; no material,
mass, actuator, manufacturing fit or load rating is established here.
"""
from pathlib import Path
import sys,math,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

report=json.loads((ROOT/'lower_modular_fit_b2.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/lower_modular_fit_b2.blend'))
CORE_NAMES=['L_thigh_carrier','L_return_carrier','L_shank_ankle_carrier','L_foot_central_carrier']
P,K,H,A=[np.array(report['joints'][name]) for name in ['hip','knee','hock','ankle']]


def pair(name):return name.replace('L_','R_',1)


def weld(target,member):
    target.data=target.data.copy()
    bpy.context.view_layer.objects.active=target
    mod=target.modifiers.new('continuous_module_weld','BOOLEAN');mod.operation='UNION'
    mod.solver='EXACT';mod.object=member
    bpy.ops.object.modifier_apply(modifier=mod.name)
    right_member=bpy.data.objects.get(pair(member.name))
    if right_member:bpy.data.objects.remove(right_member,do_unlink=True)
    bpy.data.objects.remove(member,do_unlink=True)
    bpy.data.objects[pair(target.name)].data=target.data


def difference(target,cutter):
    target.data=target.data.copy();bpy.context.view_layer.objects.active=target
    mod=target.modifiers.new('ordered_interface_space','BOOLEAN');mod.operation='DIFFERENCE'
    mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    bpy.data.objects[pair(target.name)].data=target.data


for carrier,rotor in zip(CORE_NAMES,['L_hip_rotor','L_knee_rotor','L_hock_rotor','L_ankle_rotor']):
    weld(bpy.data.objects[carrier],bpy.data.objects[rotor])
foot=bpy.data.objects[CORE_NAMES[-1]]
for name in [o.name for o in bpy.data.objects if o.name.startswith(('L_forefoot_support_',
            'L_heel_support_','L_toe_edge_rail_'))]:
    weld(foot,bpy.data.objects[name])

# Keep the through-axis bore continuous across the actual foot bridge/hub.
bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=.0136,depth=.18,
                                    location=A,rotation=(0,math.pi/2,0))
difference(foot,bpy.context.object)

# Large ordered frame windows retain the centre web and both side rails.
# Their purpose is visible structural separation, not machining/drill design.
for y,length in [(-.126,.065),(.038,.034)]:
    for x in [.175,.205]:
        bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,-.438))
        cutter=bpy.context.object;cutter.scale=(.013,length,.060)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        bevel=cutter.modifiers.new('rounded_frame_window','BEVEL');bevel.width=.0022;bevel.segments=4
        bpy.context.view_layer.objects.active=cutter;bpy.ops.object.modifier_apply(modifier=bevel.name)
        difference(foot,cutter)

for name in CORE_NAMES:
    o=bpy.data.objects[name]
    o['component_role']='Connected link carrier with integral proximal hub and distal interface'
    o.data.use_auto_smooth=True;o.data.auto_smooth_angle=math.radians(38)
    for p in o.data.polygons:p.use_smooth=True


def world_coordinates(o):
    v=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',v)
    v=v.reshape(-1,3);m=np.asarray(o.matrix_world)
    return v@m[:3,:3].T+m[:3,3]


def topology(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    vertices=len(bm.verts);edge=np.array([[e.verts[0].index,e.verts[1].index] for e in bm.edges])
    graph=coo_matrix((np.ones(len(edge)*2),
                     (np.r_[edge[:,0],edge[:,1]],np.r_[edge[:,1],edge[:,0]])),shape=(vertices,vertices))
    components,labels=connected_components(graph,directed=False)
    result={'name':o.name,'vertices':vertices,'faces':len(bm.faces),
            'boundary_edges':sum(e.is_boundary for e in bm.edges),
            'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
            'connected_components':int(components),'signed_volume':bm.calc_volume(signed=True)}
    bm.free();return result


def rx(q):
    q=math.radians(q);c,s=math.cos(q),math.sin(q)
    return np.array([[1,0,0],[0,c,-s],[0,s,c]])


def bvh(o):
    o.data.calc_loop_triangles()
    vertices=world_coordinates(o)
    triangles=np.asarray([p.vertices[:] for p in o.data.loop_triangles])
    return BVHTree.FromPolygons(vertices.tolist(),triangles.tolist(),all_triangles=True)


left_owners=[bpy.data.objects['L_'+n+'_pitch'] for n in ['thigh','return','shank','foot']]
right_owners=[bpy.data.objects['R_'+n+'_pitch'] for n in ['thigh','return','shank','foot']]
pose_checks=[]
for name,angles in [('reference_bent',(0,0,0,0)),('further_fold',(0,-6,6,0)),
                     ('partial_extension',(0,6,-6,0)),('ankle_pitch',(0,0,0,5))]:
    for left,right,q in zip(left_owners,right_owners,angles):
        left.rotation_euler.x=math.radians(q);right.rotation_euler.x=math.radians(q)
    bpy.context.view_layer.update()
    expected=[P,P+rx(angles[0])@(K-P)]
    expected.append(expected[1]+rx(sum(angles[:2]))@(H-K))
    expected.append(expected[2]+rx(sum(angles[:3]))@(A-H))
    error=max(np.linalg.norm(np.asarray(o.matrix_world.translation)-p) for o,p in zip(left_owners,expected))
    mirror_error=max(np.linalg.norm(np.asarray(right.matrix_world.translation)-p*np.array([-1,1,1]))
                     for right,p in zip(right_owners,expected))
    trees={n:bvh(bpy.data.objects[n]) for n in CORE_NAMES}
    collisions=[]
    for i in range(4):
        for j in range(i+1,4):
            overlap=trees[CORE_NAMES[i]].overlap(trees[CORE_NAMES[j]])
            if overlap:collisions.append({'a':CORE_NAMES[i],'b':CORE_NAMES[j],'triangle_pairs':len(overlap),
                                           'adjacent_links':j==i+1})
    pose_checks.append({'name':name,'angles_degrees':angles,'fk_position_max_error':float(error),
                        'mirror_joint_position_max_error':float(mirror_error),
                        'actual_carrier_triangle_intersections':collisions,
                        'scope':'Core carrier geometry in four small pose perturbations, not walking/contact/load validation'})
for left,right in zip(left_owners,right_owners):left.rotation_euler.x=0;right.rotation_euler.x=0
bpy.context.view_layer.update()

left_meshes=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('L_')]
topology_checks=[topology(o) for o in left_meshes]
mirror_checks=[]
for o in left_meshes:
    r=bpy.data.objects[pair(o.name)];expected=world_coordinates(o);expected[:,0]*=-1
    mirror_checks.append({'left':o.name,'right':r.name,'shared_mesh_data':o.data==r.data,
                          'max_paired_vertex_mirror_error':float(np.max(abs(expected-world_coordinates(r))))})
asset_meshes=left_meshes+[bpy.data.objects[pair(o.name)] for o in left_meshes]
world=np.concatenate([world_coordinates(o) for o in asset_meshes]);lo,hi=world.min(0),world.max(0)
center=Vector(((lo+hi)/2).tolist());scene=bpy.context.scene
ground=float(world[:,2].min())
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,ground-.00002))
floor=bpy.context.object;floor.name='display_ground_only';floor['excluded_from_asset']=True
mat=bpy.data.materials.new('neutral_display_floor');mat.use_nodes=True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.81,.83,.85,1)
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.82
floor.data.materials.append(mat)
camera=scene.camera;scene.cycles.samples=32;scene.cycles.use_denoising=False
views={};scale=float(max(hi-lo)*1.26)
for name,axis in [('front',(0,-1,0)),('left',(1,0,0)),('rear',(0,1,0)),('top',(0,0,1)),
                  ('front_oblique',(1,-1,.52)),('rear_oblique',(1,1,.52))]:
    camera.location=center+Vector(axis).normalized()*3
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    inv=np.asarray(camera.matrix_world.inverted());projected=world@inv[:3,:3].T+inv[:3,3]
    span=np.ptp(projected[:,:2],axis=0)
    if 'oblique' in name:
        offset=(projected[:,:2].min(0)+projected[:,:2].max(0))/2
        basis=np.asarray(camera.matrix_world)[:3,:3]
        camera.location+=Vector((basis[:,0]*offset[0]+basis[:,1]*offset[1]).tolist())
        camera.data.ortho_scale=float(max(span)*1.17)
    else:camera.data.ortho_scale=scale
    image_path=ROOT/'images'/f'lower_modular_fit_{name}_b3.png'
    scene.render.filepath=str(image_path);bpy.ops.render.render(write_still=True)
    views[name]={'image':str(image_path.relative_to(ROOT)),'span_world':span.tolist(),
                 'camera_matrix_world':np.asarray(camera.matrix_world).tolist(),'ortho_scale':camera.data.ortho_scale}
    print('MODULAR_CONNECTED_VIEW',name,flush=True)
source=ROOT/'source/lower_modular_fit_b3.blend';bpy.ops.wm.save_as_mainfile(filepath=str(source),compress=True)
report.update(source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              master_topology=topology_checks,mirroring=mirror_checks,views=views,
              bounds_xyz=[lo.tolist(),hi.tolist()],
              all_right_modules_share_left_master_mesh=all(c['shared_mesh_data'] for c in mirror_checks),
              max_mirror_error=max(c['max_paired_vertex_mirror_error'] for c in mirror_checks),
              core_connection_checks=[t for t in topology_checks if t['name'] in CORE_NAMES],
              pose_checks=pose_checks,
              actual_carrier_intersections_observed=any(p['actual_carrier_triangle_intersections'] for p in pose_checks),
              connection_kinematic_motion_checks='Actual model FK, strict mirror and carrier triangle intersections measured; inspect results and appearance separately',
              appearance_accepted=False,engineering_ready=False)
report['module_roles']={o.name:{'role':o.get('component_role'),'owner':o.get('kinematic_owner')} for o in left_meshes}
report['projection_checks']={
    'front_left_height':abs(views['front']['span_world'][1]-views['left']['span_world'][1])<1e-6,
    'front_top_width':abs(views['front']['span_world'][0]-views['top']['span_world'][0])<1e-6,
    'left_top_depth':abs(views['left']['span_world'][0]-views['top']['span_world'][1])<1e-6}
(ROOT/'lower_modular_fit_b3.json').write_text(json.dumps(report,indent=2)+'\n')
print('CONNECTED_MODULAR_SOURCE_COMPLETE',report['actual_carrier_intersections_observed'],flush=True)
