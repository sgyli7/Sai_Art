"""Clean modular Blender reconstruction fitted to the dense shape reference.

The noisy source is a read-only fitting/reference layer. Delivered surfaces
are periodic section splines, fitted curved inserts and explicit joint/frame
modules. One master leg supplies both sides. Dimensions remain appearance
coordinates; this file does not establish mass or load qualification.
"""
from pathlib import Path
import sys, math, json, hashlib, time
ROOT=Path(__file__).resolve().parents[1]
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy, bmesh
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
from mathutils import Vector

START=time.time()
REV='b2' if '--b2' in sys.argv else 'b1'
DATA=np.load(ROOT/'source/dense_reference_fit_points_b1.npz')
LEG=DATA['leg_vertices']; FOOT=DATA['foot_vertices']
P=np.array([.190,.029,.061])
K=np.array([.190,-.158,-.170])
H=np.array([.190,.006,-.169])
A=np.array([.190,-.042,-.412])
GROUND=-.45230
TAU=2*math.pi
NTHETA=128
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
master=bpy.data.collections.new('clean_master_leg_left');scene.collection.children.link(master)
mirrored=bpy.data.collections.new('clean_mirrored_leg_right');scene.collection.children.link(mirrored)
fit_records=[]; roles={}; objects=[]


def material(name,colour,roughness=.42,metallic=.0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(*colour,1)
    p.inputs['Roughness'].default_value=roughness;p.inputs['Metallic'].default_value=metallic
    return m


CLAY=material('fitted_shell_clay',(.47,.50,.53),.48)
PANEL=material('fitted_insert_clay',(.43,.46,.49),.42)
CORE=material('continuous_support_frame',(.18,.21,.24),.35,.35)
METAL=material('joint_interface_metal',(.28,.31,.34),.31,.55)
PAD=material('connected_contact_pad',(.12,.14,.16),.65)


def mesh_object(name,vertices,faces,mat,role,owner):
    me=bpy.data.meshes.new(name+'_mesh');me.from_pydata(np.asarray(vertices).tolist(),[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new('L_'+name,me);master.objects.link(o);me.materials.append(mat)
    me.use_auto_smooth=True;me.auto_smooth_angle=math.radians(38)
    for f in me.polygons:f.use_smooth=True
    o['component_role']=role;o['kinematic_owner']=owner;o['source_method']='Clean source-fitted reconstruction'
    roles[o.name]={'role':role,'owner':owner};objects.append(o)
    return o


def radial_fit(name,points,start,end,t0,t1,thickness=.006,slot=None):
    """128 angular controls per section; robust envelopes, periodic fairing."""
    start,end=np.asarray(start),np.asarray(end)
    d=end-start;length=np.linalg.norm(d);d=d/length
    ux=np.array([1.,0.,0.]);uy=np.cross(d,ux);uy/=np.linalg.norm(uy)
    offsets=points-start
    along=offsets@d/length
    xx,yy=offsets@ux,offsets@uy
    radius=np.hypot(xx,yy);theta=np.mod(np.arctan2(yy,xx),TAU)
    ts=np.linspace(t0,t1,42);angles=np.arange(NTHETA)*TAU/NTHETA
    r=np.full((len(ts),NTHETA),np.nan)
    for i,t in enumerate(ts):
        mask=(abs(along-t)<(.026 if REV=='b2' else .043))&(radius>.008)&(radius<.15)
        for j,angle in enumerate(angles):
            angular=np.abs(np.angle(np.exp(1j*(theta-angle))))<(.055 if REV=='b2' else .074)
            sample=radius[mask&angular]
            if len(sample)>4:r[i,j]=np.quantile(sample,.94)
        known=np.flatnonzero(np.isfinite(r[i]))
        if len(known)>8:
            r[i]=np.interp(np.arange(NTHETA),np.r_[known-NTHETA,known,known+NTHETA],
                           np.r_[r[i,known],r[i,known],r[i,known]])
    for j in range(NTHETA):
        known=np.flatnonzero(np.isfinite(r[:,j]))
        assert len(known)>2, f'{name}: insufficient source coverage'
        r[:,j]=np.interp(np.arange(len(ts)),known,r[known,j])
    r=gaussian_filter(r,sigma=(1.05,1.6),mode=('nearest','wrap'))
    # Explicit small rolled ends, instead of jagged scan boundaries.
    r[0]=.94*r[1];r[-1]=.94*r[-2]
    centres=start+ts[:,None]*(end-start)
    radial=np.cos(angles)[:,None]*ux+np.sin(angles)[:,None]*uy
    outer=centres[:,None,:]+r[:,:,None]*radial[None,:,:]
    inner=centres[:,None,:]+np.maximum(.003,r-thickness)[:,:,None]*radial[None,:,:]
    vertices=np.concatenate((outer.reshape(-1,3),inner.reshape(-1,3)))
    size=len(ts)*NTHETA;faces=[];kept={}
    for i in range(len(ts)-1):
        for j in range(NTHETA):
            jj=(j+1)%NTHETA
            midpoint=(ts[i]+ts[i+1])/2
            angle=(j+.5)*TAU/NTHETA
            include=not(slot and slot(midpoint,angle))
            kept[i,j]=include
            if include:
                q=[i*NTHETA+j,i*NTHETA+jj,(i+1)*NTHETA+jj,(i+1)*NTHETA+j]
                faces.append(q);faces.append([x+size for x in q[::-1]])
    # Seal each exposed perimeter with a real thickness wall.
    boundary={}
    for face in faces[::2]:
        for a,b in zip(face,face[1:]+face[:1]):
            key=tuple(sorted((a,b)))
            if key in boundary:del boundary[key]
            else:boundary[key]=(a,b)
    for a,b in boundary.values():faces.append([b,a,a+size,b+size])
    distance=cKDTree(points).query(outer.reshape(-1,3),k=1)[0]
    fit_records.append({'component':name,'method':'42 x 128 periodic source-section envelope',
                        'source_points':len(points),'outer_surface_to_reference_distance_q50':float(np.quantile(distance,.5)),
                        'outer_surface_to_reference_distance_q95':float(np.quantile(distance,.95)),
                        'outer_surface_to_reference_distance_max':float(distance.max()),
                        'scope':'Local sampled surface distance, not whole-robot appearance accuracy'})
    return vertices,faces,{'centres':centres,'radial':radial,'radii':r,'t':ts,
                          'ux':ux,'uy':uy,'start':start,'end':end,'angles':angles}


def curved_insert(name,profile,i0,i1,j0,j1,owner,offset=.0018):
    """Curved removable panel following its parent's fitted surface."""
    centre=profile['centres'][i0:i1+1];r=profile['radii'][i0:i1+1,j0:j1+1]
    radial=profile['radial'][j0:j1+1]
    n,m=r.shape;outer=centre[:,None,:]+(r+offset)[:,:,None]*radial[None,:,:]
    inner=centre[:,None,:]+(r-.0015)[:,:,None]*radial[None,:,:]
    # Taper the rim into a continuous fitted bevel, leaving a recessed seam.
    edge=np.minimum(np.minimum(np.arange(n)[:,None],np.arange(n)[::-1,None]),
                    np.minimum(np.arange(m)[None,:],np.arange(m)[None,::-1]))
    relief=.0012*np.minimum(1.,edge/2)
    outer+=relief[:,:,None]*radial[None,:,:]
    vertices=np.concatenate((outer.reshape(-1,3),inner.reshape(-1,3)))
    count=n*m;faces=[]
    for i in range(n-1):
        for j in range(m-1):
            q=[i*m+j,i*m+j+1,(i+1)*m+j+1,(i+1)*m+j]
            faces.append(q);faces.append([a+count for a in q[::-1]])
    perimeter=list(range(m))+[i*m+m-1 for i in range(1,n)]+list(range((n-1)*m+m-2,(n-1)*m-1,-1))+[i*m for i in range(n-2,0,-1)]
    for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):faces.append([b,a,a+count,b+count])
    return mesh_object(name,vertices,faces,PANEL,'fitted removable armor insert',owner)


def annulus(name,centre,outer,inner,depth,mat,role,owner):
    vertices=[];centre=np.asarray(centre)
    for x in [-depth/2,depth/2]:
        for radius in [outer,inner]:
            for i in range(96):
                a=i*TAU/96;vertices.append(centre+[x,radius*math.cos(a),radius*math.sin(a)])
    faces=[]
    for i in range(96):
        j=(i+1)%96
        faces.extend([[i,j,192+j,192+i],[96+j,96+i,288+i,288+j],
                      [j,i,96+i,96+j],[192+i,192+j,288+j,288+i]])
    return mesh_object(name,vertices,faces,mat,role,owner)


def rounded_beam(name,start,end,width,depth,mat,role,owner):
    start,end=np.asarray(start),np.asarray(end);axis=end-start;axis/=np.linalg.norm(axis)
    ux=np.array([0.,1.,0.]) if abs(axis[0])>.9 else np.array([1.,0.,0.])
    ux=ux-axis*(ux@axis);ux/=np.linalg.norm(ux)
    uy=np.cross(axis,ux);uy/=np.linalg.norm(uy)
    corner=min(width,depth)*.18
    cross=[]
    for cx,cy,a0 in [(width/2-corner,depth/2-corner,0),(-width/2+corner,depth/2-corner,90),
                      (-width/2+corner,-depth/2+corner,180),(width/2-corner,-depth/2+corner,270)]:
        for a in np.linspace(a0,a0+90,7):
            a=math.radians(a);cross.append([cx+corner*math.cos(a),cy+corner*math.sin(a)])
    cross=np.asarray(cross);n=len(cross);vertices=[]
    for t in [0,.02,.98,1]:
        centre=start+(end-start)*t
        taper=.94 if t in (0,1) else 1
        vertices.extend(centre+(cross[:,0,None]*ux+cross[:,1,None]*uy)*taper)
    faces=[list(range(n))[::-1],list(range(3*n,4*n))]
    for k in range(3):
        for i in range(n):j=(i+1)%n;faces.append([k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i])
    return mesh_object(name,vertices,faces,mat,role,owner)


def union_into(target,other):
    """Weld a carrier volume; raw source never enters these Booleans."""
    bpy.context.view_layer.objects.active=target
    modifier=target.modifiers.new('weld_continuous_carrier','BOOLEAN');modifier.operation='UNION'
    modifier.solver='EXACT';modifier.object=other
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    objects.remove(other);roles.pop(other.name,None);bpy.data.objects.remove(other,do_unlink=True)
    for f in target.data.polygons:f.use_smooth=True


def cut_axis_space(target,centre,radius,depth):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=radius,depth=depth,
                                        location=centre,rotation=(0,math.pi/2,0))
    cutter=bpy.context.object
    bpy.context.view_layer.objects.active=target
    modifier=target.modifiers.new('concentric_articulation_clearance','BOOLEAN')
    modifier.operation='DIFFERENCE';modifier.solver='EXACT';modifier.object=cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter,do_unlink=True)


def support_with_ears(name,start,end,width,depth,owner,ear_radius,ear_inner,spread):
    body=rounded_beam(name,start,end,width,depth,CORE,'continuous link carrier and clevis',owner)
    # Only the upstream link owns the distal fork. The child has a central
    # rotor at its proximal pivot; two overlapping forks would be incorrect.
    for endname,point in [('distal',end)]:
        for sign in [-1,1]:
            c=np.asarray(point).copy();c[0]+=sign*spread
            ear=annulus(name+'_'+endname+('_inner' if sign<0 else '_outer'),c,
                        ear_radius,ear_inner,.015,CORE,'welded clevis ear',owner)
            # Each ear overlaps the continuous carrier at its broad shoulder.
            shoulder=rounded_beam(name+'_shoulder',point,c,.022,ear_radius*1.20,CORE,
                                  'integral ear shoulder',owner)
            union_into(body,shoulder);union_into(body,ear)
    cut_axis_space(body,end,.0292,.0625 if REV=='b2' else .065)
    cut_axis_space(body,start,.0136,.150)
    for sign in [-1,1]:
        c=np.asarray(start).copy();c[0]+=sign*.050
        cut_axis_space(body,c,.035,.035)
    return body


# Main shape is fitted, not a primitive volume used as the design silhouette.
def segment_distance(points,start,end):
    delta=end-start;t=np.clip((points-start)@delta/(delta@delta),0,1)
    return np.linalg.norm(points-start-t[:,None]*delta,axis=1)
thigh_mask=(LEG[:,2]>-.226)&(LEG[:,1]<.061)
if REV=='b2':
    dt=segment_distance(LEG,P,K)/.105
    dr=segment_distance(LEG,K,H)/.052
    ds=segment_distance(LEG,H,A)/.062
    thigh_mask&=(dt<dr)&(dt<ds)
thigh_points=LEG[thigh_mask]
vv,ff,thigh_profile=radial_fit('thigh_shell',thigh_points,P,K,-.025,1.06,.006)
thigh=mesh_object('thigh_shell',vv,ff,CLAY,'source-fitted thigh armor', 'thigh')
curved_insert('thigh_front_panel',thigh_profile,7,34,20,46,'thigh')
curved_insert('thigh_outer_service_panel',thigh_profile,11,29,0,14,'thigh',.0012)

shank_mask=(LEG[:,2]<-.207)&(LEG[:,1]<.071)
if REV=='b2':shank_mask&=((LEG[:,2]<-.277)|(LEG[:,1]<.040))
shank_points=LEG[shank_mask]
def actuator_slot(t,angle):
    # A bounded side opening with sealed walls; not scan cracks or arbitrary holes.
    return .34<t<.86 and abs(np.angle(np.exp(1j*angle)))<.22
vv,ff,shank_profile=radial_fit('shank_shell',shank_points,H,A,.20,.885,.0055,actuator_slot)
shank=mesh_object('shank_shell',vv,ff,CLAY,'source-fitted shank cover with actuator aperture','shank')
curved_insert('shank_front_panel',shank_profile,5,34,22,44,'shank',.001)

guard_start=np.array([.190,.021,-.184]);guard_end=np.array([.190,.064,-.251])
guard_points=LEG[(LEG[:,2]>-.280)&(LEG[:,2]<-.128)&(LEG[:,1]>-.018)]
vv,ff,guard_profile=radial_fit('hock_guard',guard_points,guard_start,guard_end,-.08,1.02,.006)
mesh_object('hock_guard',vv,ff,CLAY,'source-fitted posterior hock guard','shank')
curved_insert('hock_guard_panel',guard_profile,8,31,14,41,'shank',.001)

# A fitted knee shield is its own component; it never defines a paint band.
if REV=='b2':
    curved_insert('knee_front_guard',thigh_profile,29,40,17,49,'thigh',.0021)
else:
    shield_points=LEG[(LEG[:,2]<-.102)&(LEG[:,2]>-.235)&(LEG[:,1]<-.108)]
    shield_start=np.array([.190,-.180,-.123]);shield_end=np.array([.190,-.163,-.213])
    vv,ff,shield_profile=radial_fit('knee_front_guard',shield_points,shield_start,shield_end,.03,.97,.005)
    mesh_object('knee_front_guard',vv,ff,PANEL,'independent fitted knee guard','thigh')

print('CLEAN_SOURCE_FITTED_ARMOR_READY',flush=True)

# The continuous support chain has explicit common pivots and double-shear ears.
support_with_ears('thigh_carrier',P,K,.085,.046,'thigh',.034,.0218,.043)
support_with_ears('return_carrier',K,H,.086,.044,'return',.033,.0208,.041)
shank_carrier=support_with_ears('shank_ankle_carrier',H,A,.080,.041,'shank',.033,.0208,.039)
for name,point,owner,radius in [('hip',P,'thigh',.029),('knee',K,'return',.027),
                              ('hock',H,'shank',.028),('ankle',A,'foot',.027)]:
    annulus(name+'_rotor',point,radius,.0136,.062,METAL,'concentric rotating interface',owner)
    annulus(name+'_axle',point,.0133,.004,.129,METAL,'common transverse axle',
            'thigh' if name in ('hip','knee') else 'return' if name=='hock' else 'shank')
    for sign in [-1,1]:
        p=point.copy();p[0]+=sign*.070
        annulus(name+'_end_cap_'+str(sign),p,.023,.0008 if REV=='b2' else .0045,.006,PANEL,'joint end cap',
                'thigh' if name in ('hip','knee') else 'return' if name=='hock' else 'shank')

# Source-fitted toe/heel planforms; continuous central carrier joins the ankle.
def foot_plate(name,y0,y1,owner,mat,top_offset=.012):
    ys=np.linspace(y0,y1,38);xs=[];ztop=[]
    source=FOOT[FOOT[:,2]<GROUND+.033]
    for y in ys:
        q=source[abs(source[:,1]-y)<.008]
        if len(q)>8:
            xs.append(np.quantile(q[:,0],[.02,.98]));ztop.append(np.quantile(q[:,2],.92))
        else:xs.append([.153,.227]);ztop.append(GROUND+top_offset)
    xs=gaussian_filter(np.asarray(xs),sigma=(1.1,0),mode='nearest')
    ztop=gaussian_filter(np.asarray(ztop),sigma=1.2,mode='nearest')
    ztop=np.clip(ztop,GROUND+.009,GROUND+.031)
    vertices=[]
    for i,y in enumerate(ys):
        xlo,xhi=xs[i];z=ztop[i]
        # Two shoulders and a crowned centre form a curved plate cross section.
        xx=np.linspace(xlo,xhi,9)
        crown=.0018*np.sin(np.linspace(0,math.pi,9))
        vertices.extend(np.column_stack((xx,np.full(9,y),z+crown)))
        vertices.extend(np.column_stack((xx,np.full(9,y),np.full(9,GROUND+.001))))
    faces=[]
    for i in range(len(ys)-1):
        for j in range(8):
            a=i*18+j;b=(i+1)*18+j
            faces.extend([[a,a+1,b+1,b],[a+9,b+9,b+10,a+10]])
        faces.extend([[i*18,(i+1)*18,(i+1)*18+9,i*18+9],
                      [i*18+8,i*18+17,(i+1)*18+17,(i+1)*18+8]])
    for i,reverse in [(0,True),(len(ys)-1,False)]:
        for j in range(8):
            q=[i*18+j,i*18+9+j,i*18+10+j,i*18+1+j]
            faces.append(q[::-1] if reverse else q)
    return mesh_object(name,vertices,faces,mat,'source-fitted connected foot sole module',owner)

toe=foot_plate('forefoot_plate',-.205,-.066,'foot',CLAY)
heel=foot_plate('heel_plate',-.017,.084,'foot',CLAY)
foot_frame=rounded_beam('foot_central_carrier',np.array([.190,-.116,GROUND+.019]),
                        np.array([.190,.049,GROUND+.019]),.077,.026,CORE,
                        'continuous forefoot-to-heel carrier','foot')
# Explicit ankle bridge reaches the rotor at A; it is not a decorative overlap.
bridge=rounded_beam('ankle_to_foot_bridge',A,np.array([.190,-.042,GROUND+.019]),
                    .062,.037,CORE,'continuous ankle-to-sole bridge','foot')
union_into(foot_frame,bridge)
union_into(foot_frame,toe);union_into(foot_frame,heel)

# Paired members follow the provided foot's architecture, with shared endpoints.
for sign in [-1,1]:
    top=A+np.array([sign*.030,-.009,.011])
    front=np.array([.190+sign*.030,-.140,GROUND+.017])
    rear=np.array([.190+sign*.028,.046,GROUND+.017])
    rounded_beam('forefoot_support_'+str(sign),top,front,.013,.014,METAL,
                  'front paired foot support member','foot')
    rounded_beam('heel_support_'+str(sign),A+np.array([sign*.028,.010,-.001]),rear,.013,.015,METAL,
                  'rear paired foot support member','foot')
    tip=np.array([.190+sign*.032,-.183,GROUND+.018])
    rounded_beam('toe_edge_rail_'+str(sign),tip,np.array([.190+sign*.032,-.070,GROUND+.015]),
                 .009,.010,PANEL,'ordered toe edge rail','foot')

# A single parent hierarchy owns the clean modules. No independent right leg.
owners={};previous=None
for name,point in [('thigh',P),('return',K),('shank',H),('foot',A)]:
    empty=bpy.data.objects.new('L_'+name+'_pitch',None);master.objects.link(empty)
    empty.empty_display_type='ARROWS';empty.empty_display_size=.035
    if previous:
        empty.parent=previous;empty.location=Vector((point-previous_point).tolist())
    else:empty.location=Vector(point.tolist())
    empty['axis_local']='+X';empty['role']='Appearance articulation locator; no hardware contract'
    owners[name]=empty;previous=empty;previous_point=point
for o in objects:
    owner=owners[o['kinematic_owner']]
    centre={'thigh':P,'return':K,'shank':H,'foot':A}[o['kinematic_owner']]
    values=np.asarray([v.co[:] for v in o.data.vertices])
    o.data.vertices.foreach_set('co',(values-centre).astype(np.float32).ravel())
    o.parent=owner;o.location=(0,0,0);o.data.update()
mirror_root=bpy.data.objects.new('R_master_mirror',None);mirrored.objects.link(mirror_root)
mirror_root.scale=(-1,1,1);mirror_root['source']='Linked geometry from the single left master'
right_owners={}
for name in owners:
    source=owners[name];copy=source.copy();copy.name=source.name.replace('L_','R_',1);mirrored.objects.link(copy)
    copy.parent=mirror_root if name=='thigh' else right_owners[source.parent.name.split('_')[1]]
    right_owners[name]=copy
for o in objects:
    copy=o.copy();copy.data=o.data;copy.name=o.name.replace('L_','R_',1)
    mirrored.objects.link(copy);copy.parent=right_owners[o['kinematic_owner']]
    copy['mirror_source']=o.name
bpy.context.view_layer.update()

topology=[]
for o in objects:
    bm=bmesh.new();bm.from_mesh(o.data)
    topology.append({'name':o.name,'vertices':len(bm.verts),'faces':len(bm.faces),
                     'boundary_edges':sum(e.is_boundary for e in bm.edges),
                     'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
                     'signed_volume':bm.calc_volume(signed=True)})
    bm.free()
all_meshes=[o for o in scene.objects if o.type=='MESH']
def world_coordinates(o):
    v=np.asarray([p.co[:] for p in o.data.vertices]);m=np.asarray(o.matrix_world)
    return v@m[:3,:3].T+m[:3,3]
points=np.concatenate([world_coordinates(o) for o in all_meshes])
lo,hi=points.min(0),points.max(0);center=Vector(((lo+hi)/2).tolist())
mirror_checks=[]
for o in objects:
    right=bpy.data.objects[o.name.replace('L_','R_',1)]
    expected=world_coordinates(o);expected[:,0]*=-1
    observed=world_coordinates(right)
    mirror_checks.append({'left':o.name,'right':right.name,'shared_mesh_data':o.data==right.data,
                          'max_paired_vertex_mirror_error':float(np.max(np.abs(expected-observed)))})

scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False
scene.render.use_persistent_data=True;scene.render.resolution_x=1200;scene.render.resolution_y=1200
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='Standard';scene.view_settings.exposure=0
scene.world=bpy.data.worlds.new('clean_review_world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.88,.90,.92,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.5
for name,location,energy,size in [('key',(2,-3,4),150,3),('fill',(-2,-1,2),65,3),('rim',(1,3,3),100,3)]:
    bpy.ops.object.light_add(type='AREA',location=location)
    lamp=bpy.context.object;lamp.name=name;lamp.data.energy=energy;lamp.data.size=size
    lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera;camera.data.type='ORTHO'
views={}
scale=float(max(hi-lo)*1.26)
for name,direction in [('front',(0,-1,0)),('left',(1,0,0)),('rear',(0,1,0)),('top',(0,0,1)),
                       ('front_oblique',(1,-1,.52)),('rear_oblique',(1,1,.52))]:
    camera.location=center+Vector(direction).normalized()*3
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    inv=np.asarray(camera.matrix_world.inverted());projected=points@inv[:3,:3].T+inv[:3,3]
    span=np.ptp(projected[:,:2],axis=0)
    if 'oblique' in name:
        offset=(projected[:,:2].min(0)+projected[:,:2].max(0))/2
        basis=np.asarray(camera.matrix_world)[:3,:3]
        camera.location+=Vector((basis[:,0]*offset[0]+basis[:,1]*offset[1]).tolist())
        camera.data.ortho_scale=float(max(span)*1.17)
    else:camera.data.ortho_scale=scale
    out=ROOT/'images'/f'lower_modular_fit_{name}_{REV}.png'
    scene.render.filepath=str(out);bpy.ops.render.render(write_still=True)
    views[name]={'image':str(out.relative_to(ROOT)),'span_world':span.tolist(),
                 'camera_matrix_world':np.asarray(camera.matrix_world).tolist(),
                 'ortho_scale':camera.data.ortho_scale}
    print('MODULAR_FITTED_VIEW',name,flush=True)
source=ROOT/'source'/f'lower_modular_fit_{REV}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source),compress=True)
report={
    'source':str(source.relative_to(ROOT)),
    'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'reference_scope':'Dense model is read-only fitting/reference data; it is absent from the reconstructed scene.',
    'primary_shape_references':['references/user_dense_assembly_front_shape_b1.jpg',
                                'references/user_dense_assembly_rear_shape_b1.jpg'],
    'foot_reference_role':'Foot only; no silver reference leg is adopted',
    'joints':{'hip':P.tolist(),'knee':K.tolist(),'hock':H.tolist(),'ankle':A.tolist()},
    'stance':'Reference-like bent pose is the zero pose; no old overall-height constraint',
    'units':'Normalized appearance coordinates; engineering dimensions, mass, load and fits not assigned',
    'module_roles':roles,'source_surface_fit':fit_records,'master_topology':topology,
    'mirroring':mirror_checks,
    'all_right_modules_share_left_master_mesh':all(r['shared_mesh_data'] for r in mirror_checks),
    'max_mirror_error':max(r['max_paired_vertex_mirror_error'] for r in mirror_checks),
    'views':views,'bounds_xyz':[lo.tolist(),hi.tolist()],
    'projection_checks':{
        'front_left_height':abs(views['front']['span_world'][1]-views['left']['span_world'][1])<1e-6,
        'front_top_width':abs(views['front']['span_world'][0]-views['top']['span_world'][0])<1e-6,
        'left_top_depth':abs(views['left']['span_world'][0]-views['top']['span_world'][1])<1e-6},
    'appearance_accepted':False,'engineering_ready':False,
    'connection_kinematic_motion_checks':'Pending actual source review and affected interface tests',
    'elapsed_seconds':time.time()-START,
}
(ROOT/f'lower_modular_fit_{REV}.json').write_text(json.dumps(report,indent=2)+'\n')
print('MODULAR_FITTED_MASTER_COMPLETE',len(objects),len(all_meshes),flush=True)
