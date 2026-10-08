"""Reference-fitted open armor panels and a connected articulated master.

The dense reconstruction supplies point/normal measurements only. No source
triangles are part of the editable candidate. Shells use regular quad patches
with explicit boundaries. Carrier forks leave real space for the next link.
This is normalized appearance geometry, not a load-rated mechanical assembly.
"""
from pathlib import Path
import sys, math, json, hashlib
ROOT = Path(__file__).resolve().parents[1]
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy, bmesh, numpy as np
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree, ConvexHull
from mathutils import Vector

DATA = np.load(ROOT/'source/dense_reference_fit_points_b1.npz')
LEG, NORMAL = DATA['leg_vertices'], DATA['leg_normals']
FOOT = DATA['foot_vertices']
P = np.array([.190, .029, .061]); K = np.array([.190, -.158, -.170])
H = np.array([.190, .006, -.169]); A = np.array([.190, -.042, -.412])
GROUND = -.45230
REV='b4'
for arg in sys.argv:
    if arg.startswith('--revision='):REV=arg.split('=',1)[1]
JOINTS = dict(thigh=P, return_link=K, shank=H, foot=A)
TAU = 2*math.pi
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/lower_modular_fit_b3.blend'))
scene = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)
master = bpy.data.collections['clean_master_leg_left']
mirrored = bpy.data.collections['clean_mirrored_leg_right']
OWNERS = {name: bpy.data.objects['L_'+('return' if name=='return_link' else name)+'_pitch'] for name in JOINTS}
RIGHT = {name: bpy.data.objects['R_'+('return' if name=='return_link' else name)+'_pitch'] for name in JOINTS}
objects, fits = [], []


def mat(name, color, rough=.42, metal=0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
    return m


SHELL = mat('b4_clean_armor', (.48,.52,.56),.38)
INSERT = mat('b4_curved_service_inserts', (.41,.45,.49),.34)
FRAME = mat('b4_structural_frame', (.18,.22,.26),.34,.45)
JOINT = mat('b4_articulation_interfaces', (.30,.34,.39),.31,.65)
ROD = mat('b4_interface_rods', (.43,.47,.52),.26,.72)
SOLE = mat('b4_contact_surfaces', (.10,.13,.16),.63)


def object_mesh(name, vertices, faces, material, owner, role, smooth=True):
    # Compact indices, so bounded apertures never leave hundreds of loose verts.
    vertices=np.asarray(vertices); used=np.unique(np.concatenate([np.asarray(f) for f in faces]))
    remap=np.full(len(vertices),-1,dtype=int);remap[used]=np.arange(len(used))
    faces=[remap[np.asarray(f)].tolist() for f in faces]
    vertices=vertices[used]-JOINTS[owner]
    me=bpy.data.meshes.new('L_'+name+'_master_mesh')
    me.from_pydata(vertices.tolist(),[],faces); me.update()
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    bm.to_mesh(me);bm.free()
    me.materials.append(material);me.use_auto_smooth=True;me.auto_smooth_angle=math.radians(36)
    for p in me.polygons:p.use_smooth=smooth
    o=bpy.data.objects.new('L_'+name,me);master.objects.link(o)
    o.parent=OWNERS[owner];o.location=(0,0,0)
    o['component_role']=role;o['kinematic_owner']=owner
    o['construction']='Clean fitted patch or explicit continuous interface; source is reference only'
    objects.append(o);bpy.context.view_layer.update()
    return o


def patch_solid(name, outer, inner, material, owner, role, mask=None):
    nr,nc,_=outer.shape; count=nr*nc
    vertices=np.concatenate([outer.reshape(-1,3),inner.reshape(-1,3)])
    surface=[]
    for i in range(nr-1):
        for j in range(nc-1):
            if mask is None or not mask(i,j):
                surface.append([i*nc+j,i*nc+j+1,(i+1)*nc+j+1,(i+1)*nc+j])
    boundary={};faces=[]
    for q in surface:
        faces.extend([q,[k+count for k in q[::-1]]])
        for a,b in zip(q,q[1:]+q[:1]):
            key=tuple(sorted([a,b]))
            if key in boundary:del boundary[key]
            else:boundary[key]=(a,b)
    for a,b in boundary.values():faces.append([b,a,a+count,b+count])
    return object_mesh(name,vertices,faces,material,owner,role)


def source_profile(name, points, normals, start, end, ts, angles, fallback):
    start=np.asarray(start);end=np.asarray(end);delta=end-start;length=np.linalg.norm(delta)
    direction=delta/length;ux=np.array([1.,0,0]);uy=np.cross(direction,ux);uy/=np.linalg.norm(uy)
    dv=points-start;along=dv@direction/length;x=dv@ux;y=dv@uy
    radius=np.hypot(x,y);theta=np.arctan2(y,x)
    normal_radial=(normals@ux*x+normals@uy*y)/np.maximum(radius,1e-8)
    valid=(radius>.009)&(radius<.125)&(normal_radial>.28)&(abs(normals@direction)<.86)
    raw=np.full((len(ts),len(angles)),np.nan)
    for i,t in enumerate(ts):
        longitudinal=abs(along-t)<.016
        for j,angle in enumerate(angles):
            angular=abs(np.angle(np.exp(1j*(theta-angle))))<.040
            q=radius[valid&longitudinal&angular]
            if len(q)>3:raw[i,j]=np.quantile(q,.72)
    # Missing scan regions are interpolated between neighboring fitting controls,
    # not filled with source fragments or a maximum envelope around other modules.
    for i in range(len(ts)):
        known=np.flatnonzero(np.isfinite(raw[i]))
        if len(known)>2:raw[i]=np.interp(np.arange(len(angles)),known,raw[i,known])
    for j in range(len(angles)):
        known=np.flatnonzero(np.isfinite(raw[:,j]))
        raw[:,j]=np.interp(np.arange(len(ts)),known,raw[known,j]) if len(known)>1 else fallback
    radii=gaussian_filter(raw,sigma=(1.25,1.2),mode='nearest')
    directions=np.cos(angles)[:,None]*ux+np.sin(angles)[:,None]*uy
    centres=start+ts[:,None]*delta
    outer=centres[:,None,:]+radii[:,:,None]*directions[None,:,:]
    distance=cKDTree(points).query(outer.reshape(-1,3))[0]
    fits.append({'module':name,'controls':[len(ts),len(angles)],
                 'source_normal_filtered_points':int(valid.sum()),
                 'surface_to_local_reference_q50':float(np.quantile(distance,.5)),
                 'surface_to_local_reference_q95':float(np.quantile(distance,.95)),
                 'scope':'Local source-normal fitting only; not acceptance or a percent fidelity claim'})
    return dict(outer=outer,radii=radii,centres=centres,directions=directions,ts=ts,angles=angles,
                start=start,end=end,ux=ux,uy=uy)


def armor_patch(name, profile, owner, thickness=.005, slot=None):
    inner=profile['outer']-thickness*profile['directions'][None,:,:]
    return patch_solid(name,profile['outer'],inner,SHELL,owner,
                       'Fitted open armor shell with sealed module boundaries',slot)


def height_section_profile(name,points,z_top,z_bottom,angle0,angle1,centre_seed):
    """Regular horizontal contours bounded by real source height/planform.

    This avoids the extrapolated caps produced by diagonal-axis envelopes.
    The source point cloud is read-only measurement data. Every output face
    belongs to a newly constructed structured patch, not the noisy source.
    """
    ts=np.linspace(0,1,62);zs=z_top+ts*(z_bottom-z_top)
    angles=np.deg2rad(np.linspace(angle0,angle1,128));centres=[];raw=[]
    for z in zs:
        q=points[abs(points[:,2]-z)<.0045]
        if len(q)<15:
            nearest=np.argsort(abs(points[:,2]-z))[:500];q=points[nearest]
        bounds=np.quantile(q[:,:2],[.015,.985],axis=0)
        center=(bounds[0]+bounds[1])/2
        # A modest seed stabilizes incomplete scans without imposing a generic
        # symmetric cross section on an asymmetric armor component.
        center=.85*center+.15*np.asarray(centre_seed)
        centres.append([*center,z])
        xy=q[:,:2]-center;r=np.linalg.norm(xy,axis=1);a=np.arctan2(xy[:,1],xy[:,0])
        row=np.full(len(angles),np.nan)
        for j,theta in enumerate(angles):
            local=r[abs(np.angle(np.exp(1j*(a-theta))))<.054]
            if len(local)>3:row[j]=np.quantile(local,.90)
        known=np.flatnonzero(np.isfinite(row))
        if len(known)>3:row=np.interp(np.arange(len(angles)),known,row[known])
        raw.append(row)
    centres=gaussian_filter(np.asarray(centres),sigma=(1.15,0),mode='nearest')
    centres[:,2]=zs
    radii=np.asarray(raw)
    for j in range(len(angles)):
        known=np.flatnonzero(np.isfinite(radii[:,j]))
        assert len(known)>3,(name,j,'insufficient section coverage')
        radii[:,j]=np.interp(np.arange(len(zs)),known,radii[known,j])
    radii=gaussian_filter(radii,sigma=(1.45,1.25),mode='nearest')
    radial=np.column_stack((np.cos(angles),np.sin(angles),np.zeros(len(angles))))
    outer=centres[:,None,:]+radii[:,:,None]*radial[None,:,:]
    distance=cKDTree(points).query(outer.reshape(-1,3))[0]
    fits.append({'module':name,'controls':[len(zs),len(angles)],
                 'method':'Source-bounded horizontal section contours with fairing',
                 'local_surface_distance_q50':float(np.quantile(distance,.5)),
                 'local_surface_distance_q95':float(np.quantile(distance,.95)),
                 'scope':'Local geometric distance; no appearance acceptance inferred'})
    return dict(outer=outer,radii=radii,centres=centres,directions=radial,ts=ts,angles=angles,
                start=centres[0],end=centres[-1],ux=np.array([1.,0,0]),uy=np.array([0.,1.,0]),
                height_sections=True)


def insert(name,profile,t0,t1,a0,a1,owner,thick=.0024):
    """Fitted surface insert with rounded parametric corners and shallow relief."""
    ts=np.linspace(t0,t1,34); rows=[]; directions=[]
    center=(a0+a1)/2;half=(a1-a0)/2
    for i,t in enumerate(ts):
        u=i/(len(ts)-1)
        factor=1-.105*max(0,1-min(u,1-u)/.12)**2
        ang=np.linspace(center-half*factor,center+half*factor,44)
        r=np.array([np.interp(t,profile['ts'],np.array([
            np.interp(a,profile['angles'],row) for row in profile['radii']])) for a in ang])
        radial=np.cos(ang)[:,None]*profile['ux']+np.sin(ang)[:,None]*profile['uy']
        c=np.array([np.interp(t,profile['ts'],profile['centres'][:,axis]) for axis in range(3)])
        # A shallow controlled bevel rather than a second balloon over the shell.
        w=np.minimum(np.minimum(np.arange(44),np.arange(44)[::-1]),min(i,len(ts)-i-1))
        off=.0004+.00115*np.minimum(1.,w/3)
        rows.append(c+(r+off)[:,None]*radial);directions.append(radial)
    rows=np.asarray(rows);directions=np.asarray(directions)
    if REV not in ('b4','b5'):
        # Surface inserts are manufactured-looking panels, not every local
        # bump of the reconstruction. Fair only their interior controls while
        # preserving the measured perimeter and the overall armor mass.
        fair=gaussian_filter(rows,sigma=(2.2,1.6,0),mode='nearest')
        nr,nc,_=rows.shape
        edge=np.minimum(np.minimum(np.arange(nr)[:,None],np.arange(nr)[::-1,None]),
                        np.minimum(np.arange(nc)[None,:],np.arange(nc)[None,::-1]))
        blend=.70*np.minimum(1.,edge/4)
        rows=rows*(1-blend[:,:,None])+fair*blend[:,:,None]
    return patch_solid(name,rows,rows-thick*directions,INSERT,owner,
                       'Source-fitted removable surface insert; no independent paint-band geometry')


def ring(name,center,outer,inner,width,material,owner,role):
    vertices=[];center=np.asarray(center)
    for x in [-width/2,width/2]:
        for radius in [outer,inner]:
            for i in range(96):
                angle=i*TAU/96;vertices.append(center+[x,radius*math.cos(angle),radius*math.sin(angle)])
    faces=[]
    for i in range(96):
        j=(i+1)%96
        faces.extend([[i,j,192+j,192+i],[96+j,96+i,288+i,288+j],
                      [j,i,96+i,96+j],[192+i,192+j,288+j,288+i]])
    return object_mesh(name,vertices,faces,material,owner,role)


def swept(name,centres,widths,depths,material,owner,role):
    centres=np.asarray(centres);widths=np.broadcast_to(widths,len(centres));depths=np.broadcast_to(depths,len(centres))
    vertices=[];n=32
    for i,c in enumerate(centres):
        direction=centres[min(i+1,len(centres)-1)]-centres[max(i-1,0)]
        direction/=np.linalg.norm(direction)
        ux=np.array([1.,0,0]);ux-=direction*(ux@direction);ux/=np.linalg.norm(ux)
        uy=np.cross(direction,ux);uy/=np.linalg.norm(uy)
        w,d=widths[i],depths[i];r=min(w,d)*.16
        corners=[(w/2-r,d/2-r,0),(-w/2+r,d/2-r,90),(-w/2+r,-d/2+r,180),(w/2-r,-d/2+r,270)]
        for cx,cy,a0 in corners:
            for a in np.linspace(a0,a0+90,8,endpoint=False):
                a=math.radians(a);vertices.append(c+(cx+r*math.cos(a))*ux+(cy+r*math.sin(a))*uy)
    faces=[list(range(n))[::-1],list(range((len(centres)-1)*n,len(centres)*n))]
    for i in range(len(centres)-1):
        for j in range(n):k=(j+1)%n;faces.append([i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j])
    return object_mesh(name,vertices,faces,material,owner,role)


def beam(name,start,end,width,depth,material,owner,role):
    start,end=np.asarray(start),np.asarray(end)
    centres=start+np.array([0,.025,.975,1])[:,None]*(end-start)
    return swept(name,centres,[width*.95,width,width,width*.95],
                 [depth*.95,depth,depth,depth*.95],material,owner,role)


def tube(name,start,end,radius,material,owner,role):
    start,end=np.asarray(start),np.asarray(end);d=(end-start)/np.linalg.norm(end-start)
    u=np.array([1.,0,0]);u-=d*(u@d);u/=np.linalg.norm(u);v=np.cross(d,u)
    n=64;vertices=[]
    for t,rr in [(0,.94*radius),(.035,radius),(.965,radius),(1,.94*radius)]:
        c=start+t*(end-start)
        for j in range(n):vertices.append(c+rr*(u*math.cos(j*TAU/n)+v*math.sin(j*TAU/n)))
    faces=[list(range(n))[::-1],list(range(3*n,4*n))]
    for i in range(3):
        for j in range(n):k=(j+1)%n;faces.append([i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j])
    return object_mesh(name,vertices,faces,material,owner,role)


def boolean(target,cutter,operation):
    bpy.context.view_layer.objects.active=target
    mod=target.modifiers.new('integral_interface_volume','BOOLEAN');mod.operation=operation
    mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    assert len(target.data.polygons)>0,(target.name,operation,'Boolean produced an empty component')
    if cutter in objects:objects.remove(cutter)
    bpy.data.objects.remove(cutter,do_unlink=True)


def union(target,member):boolean(target,member,'UNION')


def bore(target,center,radius,width):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=radius,depth=width,
                                      location=center,rotation=(0,math.pi/2,0))
    boolean(target,bpy.context.object,'DIFFERENCE')


def articulated_carrier(name,start,end,owner,width,depth,spread,hub_radius=.028):
    axis=(end-start)/np.linalg.norm(end-start)
    # The full central beam ends before the distal joint chamber. Fork cheeks,
    # not a solid block through the child hub, continue to the shared pivot.
    stop=end-axis*.073
    if REV in ('b4','b5'):
        core=beam(name,start,stop,width,depth,FRAME,owner,'Continuous carrier with integral proximal hub and distal fork')
    else:
        t=np.array([0,.03,.16,.34,.56,.77,.97,1])
        centers=start+t[:,None]*(stop-start)
        if owner=='shank':centers[:,1]+=.006*np.sin(math.pi*t)
        widths=width*np.array([.76,.82,1.03,1.02,.87,.81,.94,.92])
        if owner=='shank':widths=width*np.array([.74,.76,.82,.87,.94,.90,.94,.92])
        depths=depth*np.array([.83,.94,1.02,.94,.86,.90,1.0,.95])
        core=swept(name,centers,widths,depths,FRAME,owner,
                   'Continuous contoured carrier with integral proximal hub and distal fork')
    hub=ring(name+'_proximal_hub',start,hub_radius,.0143,.050,JOINT,owner,'Integral proximal rotating hub')
    union(core,hub)
    for sign in [-1,1]:
        earcenter=end+np.array([sign*spread,0,0])
        shoulder_start=end-axis*.092+np.array([sign*(width/2-.007),0,0])
        shoulder_end=end-axis*.017+np.array([sign*spread,0,0])
        prong=beam(name+'_fork_cheek_'+str(sign),shoulder_start,shoulder_end,.012,.026,FRAME,owner,'Integral fork cheek')
        union(core,prong)
        ear=ring(name+'_ear_'+str(sign),earcenter,.034,.0146,.011,FRAME,owner,'Double-sided concentric fork interface')
        union(core,ear)
    # One common bore passes through the owning link's hub, with visible
    # bearing-interface clearance. No manufacturing tolerance is asserted.
    bore(core,start,.0143,.16)
    if owner=='shank' and REV not in ('b4','b5'):
        # One large longitudinal web window follows the source's framed shank;
        # it is an exterior/frame opening, not drilling or a bearing fit.
        p0=start+axis*.108;p1=start+axis*.174
        bpy.ops.mesh.primitive_cube_add(size=1,location=(p0+p1)/2)
        cutter=bpy.context.object;cutter.scale=(.12,.013,np.linalg.norm(p1-p0))
        cutter.rotation_euler=Vector(axis.tolist()).to_track_quat('Z','Y').to_euler()
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        bevel=cutter.modifiers.new('rounded_web_window','BEVEL');bevel.width=.0047;bevel.segments=6
        bpy.context.view_layer.objects.active=cutter;bpy.ops.object.modifier_apply(modifier=bevel.name)
        boolean(core,cutter,'DIFFERENCE')
    return core


# Armor follows the actual exterior rather than wrapping an envelope around
# the return member and rear guard as if they were one solid thigh.
if REV=='b4':
    thigh_mask=(LEG[:,2]>-.225)&(LEG[:,1]<.056)
    tp=source_profile('thigh_main_shell',LEG[thigh_mask],NORMAL[thigh_mask],P,K,
                      np.linspace(-.025,1.02,54),np.deg2rad(np.linspace(-13,193,100)),.066)
    armor_patch('thigh_main_shell',tp,'thigh',.0055)
    insert('thigh_front_service_panel',tp,.13,.76,math.radians(57),math.radians(123),'thigh')
    insert('thigh_outer_lateral_panel',tp,.10,.75,math.radians(-5),math.radians(30),'thigh')
    insert('thigh_inner_lateral_panel',tp,.10,.75,math.radians(150),math.radians(185),'thigh')
    insert('knee_front_shield',tp,.79,.995,math.radians(34),math.radians(146),'thigh',.0045)
    shank_mask=(LEG[:,2]<-.202)&((LEG[:,2]<-.268)|(LEG[:,1]<.027))
    sp=source_profile('shank_front_side_shell',LEG[shank_mask],NORMAL[shank_mask],H,A,
                      np.linspace(.165,.920,54),np.deg2rad(np.linspace(-26,206,100)),.036)
    def opening(i,j):
        t=(sp['ts'][i]+sp['ts'][i+1])/2;ang=(sp['angles'][j]+sp['angles'][j+1])/2
        return ((t-.60)/.26)**2+(ang/math.radians(14))**2<1
    armor_patch('shank_front_side_shell',sp,'shank',.005,opening)
    insert('shank_front_service_panel',sp,.24,.84,math.radians(61),math.radians(119),'shank',.0022)
    g0=np.array([.190,.042,-.171]);g1=np.array([.190,.080,-.260])
    gmask=(LEG[:,2]<-.131)&(LEG[:,2]>-.286)&(LEG[:,1]>.018)
    gp=source_profile('hock_rear_guard',LEG[gmask],NORMAL[gmask],g0,g1,
                      np.linspace(.05,.92,42),np.deg2rad(np.linspace(141,399,96)),.049)
    armor_patch('hock_rear_guard',gp,'shank',.005)
    insert('hock_rear_service_panel',gp,.22,.75,math.radians(237),math.radians(303),'shank')
else:
    # The descending front mass, tapered lower edge and real upper cut are all
    # measured at source heights. The open back leaves the return link visible.
    rear_limit=np.interp(LEG[:,2],[-.228,-.18,-.10,-.045,0,.067],[-.069,-.061,-.044,-.012,.082,.058])
    thigh_mask=(LEG[:,2]>-.218)&(LEG[:,2]<.067)&(LEG[:,1]<rear_limit)
    tp=height_section_profile('thigh_main_shell',LEG[thigh_mask],.064,-.214,137,403,[.19,-.107])
    armor_patch('thigh_main_shell',tp,'thigh',.0055)
    insert('thigh_front_service_panel',tp,.13,.72,math.radians(232),math.radians(308),'thigh')
    insert('thigh_outer_lateral_panel',tp,.09,.77,math.radians(337),math.radians(379),'thigh')
    insert('thigh_inner_lateral_panel',tp,.09,.77,math.radians(161),math.radians(203),'thigh')
    insert('knee_front_shield',tp,.76,.98,math.radians(214),math.radians(326),'thigh',.0042)
    if REV not in ('b4','b5'):
        upper_mask=(LEG[:,2]>-.054)&(LEG[:,2]<.067)&(LEG[:,1]>-.036)
        hp=height_section_profile('thigh_rear_hip_cover',LEG[upper_mask],.064,-.045,-43,223,[.178,.023])
        armor_patch('thigh_rear_hip_cover',hp,'thigh',.005)
        insert('thigh_rear_hip_panel',hp,.15,.80,math.radians(53),math.radians(127),'thigh')
    shank_mask=(LEG[:,2]<-.214)&(LEG[:,2]>-.387)&(LEG[:,1]<np.interp(LEG[:,2],[-.387,-.285,-.214],[.017,.047,.026]))
    sp=height_section_profile('shank_front_side_shell',LEG[shank_mask],-.216,-.382,133,407,[.19,-.025])
    def opening(i,j):
        t=(sp['ts'][i]+sp['ts'][i+1])/2;ang=(sp['angles'][j]+sp['angles'][j+1])/2
        return ((t-.63)/.27)**2+((ang-TAU)/math.radians(12))**2<1
    armor_patch('shank_front_side_shell',sp,'shank',.005,opening)
    insert('shank_front_service_panel',sp,.12,.89,math.radians(240),math.radians(300),'shank',.0022)
    if REV=='b5':g_top,g_bottom=-.159,-.278
    else:g_top,g_bottom=-.194,-.267
    gmask=(LEG[:,2]<g_top+.006)&(LEG[:,2]>g_bottom-.006)&(LEG[:,1]>.031)
    gp=height_section_profile('hock_rear_guard',LEG[gmask],g_top,g_bottom,-34,214,[.19,.070])
    guard=armor_patch('hock_rear_guard',gp,'shank',.005)
    insert('hock_rear_service_panel',gp,.14,.87,math.radians(57),math.radians(123),'shank')
    # Actual hock opening is concentric with the next-link interface, not an
    # arbitrary crack copied from the source. Radius allows pose perturbations.
    bore(guard,H,.038 if REV!='b5' else .040,.24)
print('OPEN_FITTED_ARMOR_COMPONENTS_COMPLETE',flush=True)

CORE_NAMES=['L_thigh_carrier','L_return_carrier','L_shank_ankle_carrier','L_foot_central_carrier']
articulated_carrier('thigh_carrier',P,K,'thigh',.067,.038,.039,.029)
articulated_carrier('return_carrier',K,H,'return_link',.054,.029,.037,.027)
articulated_carrier('shank_ankle_carrier',H,A,'shank',.062,.034,.038,.028)

# The foot reference is used only for the complete forefoot, heel and cradle.
# Thin continuous rails replace the thick fill plate of the previous attempt.
deck_z=GROUND+.0078
foot=beam('foot_central_carrier',np.array([.190,-.146,deck_z]),np.array([.190,.056,deck_z]),
          .039,.0105,FRAME,'foot','Continuous ankle pedestal, centre web and foot rails')
hub=ring('foot_integral_ankle_hub',A,.0295,.0143,.050,JOINT,'foot','Integral ankle-to-foot hub')
union(foot,hub)
pedestal=beam('foot_integral_pedestal',A,np.array([.190,-.042,deck_z]),.039,.033,FRAME,'foot','Integral hub-to-sole pedestal')
union(foot,pedestal);bore(foot,A,.0143,.17)

# Three curved forefoot rails; paired heel rails and crossmembers have shared
# volumes and endpoints. The dark sole patches are distinct contact modules.
for j,x in enumerate([.151,.190,.229]):
    centres=np.array([[x,-.069,deck_z+.0005],[x,-.099,deck_z+.006],
                      [x,-.143,deck_z+.001],[x,-.181,deck_z+.001],
                      [x,-.203,deck_z+.015]])
    rail=swept('forefoot_rail_'+str(j),centres,[.017,.018,.017,.018,.019],
               [.008,.009,.008,.008,.009],FRAME,'foot','Connected curved forefoot frame rail')
    union(foot,rail)
for y,span in [(-.079,.102),(-.154,.104),(-.191,.111),(.015,.103),(.068,.107)]:
    # Crossmembers are extruded along Y, broad across X; no frame volume is
    # faked by placing disconnected cylinders near each other.
    c=np.array([.190,y,deck_z+.001]);cross=beam('sole_crossmember',c+[0,-.0055,0],c+[0,.0055,0],span,.009,FRAME,'foot','Integral transverse foot crossmember')
    union(foot,cross)
for x in [.151,.229]:
    centres=np.array([[x,-.006,deck_z+.001],[x,.018,deck_z+.004],
                      [x,.054,deck_z+.001],[x,.074,deck_z+.010]])
    rail=swept('heel_rail',centres,.018,[.009,.010,.009,.010],FRAME,'foot','Connected curved heel frame rail')
    union(foot,rail)
for y,length,span in [(-.176,.030,.106),(.052,.024,.101),(-.037,.038,.042)]:
    center=np.array([.190,y,GROUND+.0028])
    beam('sole_contact_'+str(y),center+[0,-length/2,0],center+[0,length/2,0],span,.0056,SOLE,'foot','Connected frame contact pad')

# Reference-like paired foot braces: ordered major members and concentric
# endpoints. These are fixed appearance frame supports, not actuator specs.
for sign in [-1,1]:
    top_spread=.030 if REV=='b4' else .018
    for label,top,base in [
        ('fore',A+[sign*top_spread,-.018,.010],np.array([.190+sign*.038,-.144,deck_z+.002])),
        ('heel',A+[sign*top_spread,.020,.004],np.array([.190+sign*.038,.052,deck_z+.003]))]:
        rod=tube(label+'_support_rod_'+str(sign),top,base,.0054,JOINT,'foot','Paired foot frame support with shared endpoints')
        union(foot,rod)
        d=(base-top)/np.linalg.norm(base-top)
        sleeve=tube(label+'_support_sleeve_'+str(sign),top+d*.015,base-d*.013,.0073,JOINT,'foot','Ordered brace sleeve on the same support axis')
        union(foot,sleeve)
        if REV not in ('b4','b5'):
            eye=ring(label+'_frame_endpoint_'+str(sign),base,.0095,.003,.009,JOINT,'foot','Concentric end form on foot brace axis')
            union(foot,eye)

if REV not in ('b4','b5'):
    for x in [.151,.190,.229]:
        # Integrated turned-up toe ends retain the claw-like reference form.
        points=np.array([[x,-.187,deck_z+.001],[x,-.200,deck_z+.012],[x,-.207,deck_z+.019]])
        end=swept('toe_end_form',points,[.020,.022,.023],[.009,.011,.012],FRAME,'foot','Integral rounded toe end form')
        union(foot,end)

def expanded_pose_cutter(reference,q,owner,padding=.0023):
    """Actual reference mesh, enlarged slightly, at its real owner transform."""
    original=OWNERS[owner].rotation_euler.x
    OWNERS[owner].rotation_euler.x=math.radians(q);bpy.context.view_layer.update()
    mesh=reference.data.copy();mesh.update()
    local=np.asarray([v.co[:] for v in mesh.vertices]);norm=np.asarray([v.normal[:] for v in mesh.vertices])
    local+=padding*norm
    mesh.vertices.foreach_set('co',local.astype(np.float32).ravel());mesh.update()
    cutter=bpy.data.objects.new('temporary_pose_clearance',mesh);master.objects.link(cutter)
    cutter.matrix_world=reference.matrix_world.copy()
    OWNERS[owner].rotation_euler.x=original;bpy.context.view_layer.update()
    return cutter

if REV not in ('b4','b5'):
    # Clear the actual return-link sweep inside the thigh, preserving the front
    # silhouette. This is a measured interface relief, not arbitrary trimming.
    return_core=bpy.data.objects['L_return_carrier']
    return_sweep=[]
    local=np.asarray([v.co[:] for v in return_core.data.vertices])
    for q in [-6,0,6]:
        OWNERS['return_link'].rotation_euler.x=math.radians(q);bpy.context.view_layer.update()
        matrix=np.asarray(return_core.matrix_world)
        return_sweep.append(local@matrix[:3,:3].T+matrix[:3,3])
    OWNERS['return_link'].rotation_euler.x=0;bpy.context.view_layer.update()
    return_points=np.concatenate(return_sweep)
    padding=np.array([[x,y,z] for x in [-.0018,.0018] for y in [-.0018,.0018] for z in [-.0018,.0018]])
    return_points=(return_points[:,None,:]+padding[None,:,:]).reshape(-1,3)
    return_hull=ConvexHull(return_points)
    for name in ['L_thigh_main_shell','L_knee_front_shield','L_thigh_inner_lateral_panel']:
        cutter=object_mesh('temporary_return_sweep',return_points,return_hull.simplices.tolist(),FRAME,'thigh',
                          'Temporary convex clearance bound of actual return-link poses; excluded from final model')
        boolean(bpy.data.objects[name],cutter,'DIFFERENCE')
    # The source's low rear corner also enters the upper shank when unfolded.
    # Give that corner the same measured sweep clearance while retaining the
    # dense reference's broad front mass and section contours.
    shank_shell=bpy.data.objects['L_shank_front_side_shell'];upper_sweep=[]
    local=np.asarray([v.co[:] for v in shank_shell.data.vertices])
    top_points=local[local[:,2]>-.072]
    for q in [-6,0,6]:
        OWNERS['return_link'].rotation_euler.x=math.radians(q)
        OWNERS['shank'].rotation_euler.x=math.radians(-q);bpy.context.view_layer.update()
        matrix=np.asarray(shank_shell.matrix_world)
        upper_sweep.append(top_points@matrix[:3,:3].T+matrix[:3,3])
    OWNERS['return_link'].rotation_euler.x=0;OWNERS['shank'].rotation_euler.x=0;bpy.context.view_layer.update()
    points=np.concatenate(upper_sweep)
    padding=np.array([[x,y,z] for x in [-.0018,.0018] for y in [-.0018,.0018] for z in [-.0018,.0018]])
    points=(points[:,None,:]+padding[None,:,:]).reshape(-1,3)
    hull=ConvexHull(points)
    cutter=object_mesh('temporary_upper_shank_sweep',points,hull.simplices.tolist(),FRAME,'thigh',
                       'Temporary convex bound of actual upper-shank poses; excluded from final model')
    boolean(bpy.data.objects['L_thigh_main_shell'],cutter,'DIFFERENCE')

# End covers and axle interfaces are separate modules but have the same axis.
# Shallow concentric covers replace the oversized flat white circles.
for joint,point,upowner in [('hip',P,'thigh'),('knee',K,'thigh'),('hock',H,'return_link'),('ankle',A,'shank')]:
    ring(joint+'_common_axle',point,.0139,.006,.092,ROD,upowner,'Common transverse joint axis')
    for sign in [-1,1]:
        c=point+[sign*.048,0,0]
        ring(joint+'_side_cover_'+str(sign),c,.0262,.0005,.0038,INSERT,upowner,'Shallow joint side cover')
        ring(joint+'_side_cover_rim_'+str(sign),c+[sign*.0017,0,0],.0265,.0218,.0018,JOINT,upowner,'Concentric interface rim')

# Finalize master and bind each right module to its exact mesh data.
for o in objects:
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=3e-7)
    # Boolean outputs occasionally contain tiny coplanar triangular slits.
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    o.data.update();o.data.use_auto_smooth=True;o.data.auto_smooth_angle=math.radians(36)
    r=o.copy();r.data=o.data;r.name=o.name.replace('L_','R_',1)
    mirrored.objects.link(r);r.parent=RIGHT[o['kinematic_owner']]
    r['mirror_source']=o.name
bpy.context.view_layer.update()

report={'revision':REV,'source':f'source/lower_modular_components_{REV}.blend',
        'joints':dict(hip=P.tolist(),knee=K.tolist(),hock=H.tolist(),ankle=A.tolist()),
        'source_fit':fits,'units':'Normalized appearance units; no load or manufacturing qualification',
        'construction':'Regular clean component patches fitted to source point/normal measurements; no dense source triangles used',
        'reference_scope':'Latest dense appearance direction, foot reference used for feet only',
        'core_names':CORE_NAMES,'appearance_accepted':False,'engineering_ready':False}
(ROOT/f'lower_modular_components_{REV}.json').write_text(json.dumps(report,indent=2)+'\n')
source=ROOT/f'source/lower_modular_components_{REV}.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(source),compress=True)
print('REBUILT_CLEAN_COMPONENTS_SAVED',len(objects),flush=True)
