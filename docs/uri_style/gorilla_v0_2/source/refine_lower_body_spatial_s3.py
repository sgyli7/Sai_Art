"""Closed modular lower-body appearance fitted to the selected bent leg.

Retains S2's whole feet and reference frame; replaces damaged generated skin
with editable contour lofts. Current upper-body art remains v0.1, untouched.
This is appearance geometry with explicit candidate joint envelopes, not
manufacturing detail or a qualified structural/physical model.
"""
from pathlib import Path
import sys, math, json, hashlib, time
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy, bmesh
import numpy as np
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
START=time.time()
SOURCE=ROOT/'source/lower_body_spatial_s2.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
for o in list(bpy.data.objects):
    if o.type=='MESH' and o.name.startswith('pixal_'):
        bpy.data.objects.remove(o,do_unlink=True)
materials={
 'shell':bpy.data.materials['neutral_source_shell'],
 'foot':bpy.data.materials['neutral_integrated_foot'],
 'frame':bpy.data.materials['neutral_support_frame'],
 'metal':bpy.data.materials['neutral_joint_face'],
}
# Keep inspection surfaces below clipping white: lighting is part of the
# review, not the module color allocation awaiting user spatial review.
for key in ('shell','foot'):
    p=materials[key].node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value=(.35,.40,.44,1) if key=='shell' else (.56,.59,.60,1)
for o in bpy.data.objects:
    if o.type=='LIGHT':o.data.energy*=.30

def finish(o,key,bevel=.003):
    o.data.materials.append(materials[key])
    o['scope']='appearance_volume_not_machining_or_load_qualification'
    o.data.use_auto_smooth=True;o.data.auto_smooth_angle=math.radians(40)
    if bevel:
        mod=o.modifiers.new('controlled_shell_edge','BEVEL');mod.width=bevel
        mod.segments=4;mod.limit_method='ANGLE';mod.angle_limit=math.radians(18)
        mod=o.modifiers.new('surface_normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    return o

def obj_mesh(name,v,f,key,bevel=.003):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(v,[],f);mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh);bm.free()
    return finish(o,key,bevel)

def loft(name,rings,key,bevel=.003):
    n=len(rings[0]);v=sum(rings,[])
    f=[tuple(range(n-1,-1,-1)),tuple(range((len(rings)-1)*n,len(rings)*n))]
    for k in range(len(rings)-1):
        f.extend((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j) for j in range(n))
    return obj_mesh(name,v,f,key,bevel)

def section(cx,y,z,w,front,rear):
    # Chamfered rectangular section, with an intentional front center facet.
    return [(cx-w*.65,y-front,z),(cx+w*.65,y-front,z),
            (cx+w,y-front*.60,z),(cx+w,y+rear*.65,z),
            (cx+w*.65,y+rear,z),(cx-w*.65,y+rear,z),
            (cx-w,y+rear*.65,z),(cx-w,y-front*.60,z)]

def cylinder(name,c,r,width,key):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=r,depth=width,location=c)
    o=bpy.context.object;o.name=name;o.rotation_euler=(0,math.pi/2,0)
    finish(o,key,.0015)
    for p in o.data.polygons:p.use_smooth=True
    return o

def cheek(name,x,width,yz,key):
    n=len(yz);v=[(xx,y,z) for xx in (x-width/2,x+width/2) for y,z in yz]
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    f += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return obj_mesh(name,v,f,key,.004)

def strut(name,a,b,r):
    a,b=Vector(a),Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=r,depth=(b-a).length,location=(a+b)/2)
    o=bpy.context.object;o.name=name;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return finish(o,'metal',.001)

loft_specs={}
axes={}
for side in (-1,1):
    cx=side*.178
    axes[str(side)]={
        'hip':[cx,-.004,.069],
        'knee':[cx,-.115,-.151],
        'return':[cx,.025,-.227],
        'ankle':[side*.185,-.029,-.375],
    }
    # Longitudinal shape follows the selected broad proximal shell, with the
    # forward-most surface now staying behind the forefoot contact edge.
    specs=[(.068,-.008,.065,.052,.049),(.045,-.022,.087,.064,.067),
           (-.010,-.055,.094,.081,.078),(-.065,-.088,.091,.084,.073),
           (-.107,-.109,.084,.071,.063),(-.140,-.114,.073,.052,.054)]
    rings=[section(cx,y,z,w,front,rear) for z,y,w,front,rear in specs]
    o=loft(f'proximal_thigh_shell_{side}',rings,'shell',.005)
    o['module']='proximal_thigh_shell';loft_specs[o.name]=specs
    # A separate service panel follows the thigh's actual sloping surface.
    face_specs=[(.043,-.088,.057),(-.012,-.140,.066),(-.069,-.178,.061),(-.092,-.178,.053)]
    outer=[(cx-w,y-.004,z) for z,y,w in face_specs]
    outer += [(cx+w,y-.004,z) for z,y,w in reversed(face_specs)]
    inner=[(x,y+.006,z) for x,y,z in outer]
    n=len(outer)
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    obj_mesh(f'thigh_access_panel_{side}',outer+inner,f,'shell',.0025)
    # The knee guard is a whole independent shaped module, not a painted band.
    knee_specs=[(-.117,-.116,.073,.061,.046),
                (-.143,-.119,.075,.063,.049),
                (-.172,-.111,.066,.051,.043),
                (-.187,-.095,.052,.034,.032)]
    guard=loft(f'knee_guard_module_{side}',[section(cx,y,z,w,fr,re) for z,y,w,fr,re in knee_specs],'foot',.004)
    guard['module']='complete_knee_guard';loft_specs[guard.name]=knee_specs
    # Two broad, closed side cheeks make the return link read as a connected
    # support bridge rather than several tiny serial ankles.
    yz=[(-.125,-.135),(-.150,-.159),(-.132,-.185),
        (.009,-.253),(.050,-.235),(.047,-.205)]
    for cheek_side in (-1,1):
        cheek(f'broad_return_cheek_{side}_{cheek_side}',cx+cheek_side*.053,.023,yz,'frame')
    for tag,c,r,w in [('hip',axes[str(side)]['hip'],.038,.142),
                     ('knee',axes[str(side)]['knee'],.039,.151),
                     ('return',axes[str(side)]['return'],.036,.141)]:
        cylinder(f'{tag}_candidate_envelope_{side}',c,r,w,'frame')
        for face in (-1,1):
            cylinder(f'{tag}_side_face_{side}_{face}',(c[0]+face*w*.52,c[1],c[2]),r*.75,.006,'metal')
    # A continuous curved lower leg reaches the wide foot axle directly.
    shank_specs=[(-.222,.025,.049,.036,.035),(-.249,.018,.063,.045,.043),
                 (-.280,-.001,.059,.042,.039),(-.314,-.015,.054,.038,.035),
                 (-.348,-.025,.052,.034,.031),(-.374,-.029,.053,.029,.027)]
    shank=loft(f'continuous_shank_shell_{side}',[section(side*.185,y,z,w,fr,re) for z,y,w,fr,re in shank_specs],'shell',.0035)
    shank['module']='continuous_shank_to_ankle';loft_specs[shank.name]=shank_specs
    # The small cylinder is a service/actuator envelope. The broad shell and
    # return bridge remain visible as the overall support; no rating asserted.
    strut(f'rear_service_cylinder_{side}',(side*.185,.064,-.257),(side*.185,.020,-.351),.012)
    strut(f'rear_service_rod_{side}',(side*.185,.020,-.351),(side*.185,-.014,-.375),.007)
    rear_guard=[(.010,-.206),(.041,-.209),(.080,-.243),(.070,-.264),(.010,-.250)]
    cheek(f'return_guard_module_{side}',cx,.098,rear_guard,'shell')

scene=bpy.context.scene
scene.cycles.samples=40;scene.cycles.use_denoising=False
scene.view_settings.exposure=-.25
meshes=[o for o in scene.objects if o.type=='MESH']
depg=bpy.context.evaluated_depsgraph_get()
all_v=[];parts=[];geometry_hash=hashlib.sha256()
for o in meshes:
    e=o.evaluated_get(depg);me=e.to_mesh()
    v=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',v);v=v.reshape(-1,3)
    m=np.asarray(o.matrix_world,dtype=np.float64);w=v@m[:3,:3].T+m[:3,3]
    geometry_hash.update(o.name.encode());geometry_hash.update(w.tobytes())
    # Native closed-surface check is limited to topology, not collisions.
    bm=bmesh.new();bm.from_mesh(me)
    nonmanifold=sum(not edge.is_manifold for edge in bm.edges)
    signed_volume=bm.calc_volume(signed=True);bm.free()
    parts.append({'name':o.name,'vertices':len(w),'bounds_xyz':[w.min(0).tolist(),w.max(0).tolist()],
                  'nonmanifold_edges':nonmanifold,'signed_volume':signed_volume})
    all_v.append(w);e.to_mesh_clear()
world=np.concatenate(all_v);lo,hi=world.min(0),world.max(0)
center=Vector(((lo+hi)/2).tolist());scale=float(max(hi-lo)*1.19)
camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=scale
views={}
for name,axis in [('front',(0,-1,0)),('left',(1,0,0)),('rear',(0,1,0)),('top',(0,0,1)),
                 ('front_oblique',(1,-1,.52)),('rear_oblique',(1,1,.52))]:
    camera.location=center+Vector(axis).normalized()*3
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    inv=np.asarray(camera.matrix_world.inverted());local=world@inv[:3,:3].T+inv[:3,3]
    span=np.ptp(local[:,:2],axis=0)/scale*1000
    out=ROOT/'images'/f'lower_body_native_{name}_s3.png'
    scene.render.filepath=str(out);bpy.ops.render.render(write_still=True)
    views[name]={'image':str(out.relative_to(ROOT)),'type':'ORTHO',
                 'shared_geometry_sha256':geometry_hash.hexdigest(),'orthographic_scale':scale,
                 'projected_span_px':span.tolist(),'camera_matrix_world':np.asarray(camera.matrix_world).tolist()}
    print('LOWER_BODY_NATIVE_VIEW',name,json.dumps(span.tolist()),flush=True)

source_out=ROOT/'source/lower_body_spatial_s3.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source_out),compress=True)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'generated/lower_body_spatial_s3.glb'),
                         export_format='GLB',use_selection=True,export_apply=True)
checks={
 'front_left_height':abs(views['front']['projected_span_px'][1]-views['left']['projected_span_px'][1])<1e-3,
 'front_rear_width':abs(views['front']['projected_span_px'][0]-views['rear']['projected_span_px'][0])<1e-3,
 'front_top_width':abs(views['front']['projected_span_px'][0]-views['top']['projected_span_px'][0])<1e-3,
 'left_top_depth':abs(views['left']['projected_span_px'][0]-views['top']['projected_span_px'][1])<1e-3,
 'closed_individual_meshes':all(p['nonmanifold_edges']==0 for p in parts),
 'positive_individual_volume':all(p['signed_volume']>0 for p in parts),
}
report={
 'scope':'Same-source lower-body appearance candidate with component lofts; no upper redesign',
 'reference_lower_source':'references/user_pixal_lower_body.jpg',
 'source_s2_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'upper_body_authority':'gorilla_v0_1/images/locked_four_view_review_rev_aa3.png unchanged',
 'source_method':'Manual closed contour lofts following selected native lower shape; replaces incomplete S2 scan skin, retains complete S2 feet',
 'pose':'Bent hip/knee/return/shank chain; not straight humanoid stance',
 'axes_scope':'Appearance candidate centers only; not hardware hinge or actuator contract',
 'axes_xyz':axes,'loft_specs':loft_specs,'coordinate_frame':'+X lateral, -Y front, +Z up; normalized appearance units',
 'palette':'Neutral inspection only; URI module color allocation pending',
 'bounds_xyz':[lo.tolist(),hi.tolist()],'geometry_sha256':geometry_hash.hexdigest(),
 'parts':parts,'views':views,'geometry_checks':checks,
 'whole_robot_corresponding_model':False,'appearance_accepted':False,
 'engineering_ready':False,'mass_collision_and_strength_validation':False,
 'output_blend':str(source_out.relative_to(ROOT)),'elapsed_seconds':time.time()-START,
}
(ROOT/'lower_body_native_spatial_s3.json').write_text(json.dumps(report,indent=2)+'\n')
print('LOWER_BODY_SPATIAL_COMPLETE',json.dumps(checks),flush=True)
