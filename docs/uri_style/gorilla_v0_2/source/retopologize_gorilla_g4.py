"""Fit clean, closed armor to the accepted reconstructed volumes in Blender.

G3 contains generated rear fragments and scan-like dents. This stage replaces
those surfaces with source-fitted closed armor, retains the bent stance, and
restores editable Gorilla service features. It is an appearance assembly.
"""
from pathlib import Path
import sys, json, math, hashlib, time
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy
import numpy as np
from scipy.spatial import ConvexHull
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
START=time.time()
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source/gorilla_clean_g3.blend'))
source=bpy.data.objects['gorilla_reference_body_g3']
vv=np.empty(len(source.data.vertices)*3,dtype=np.float32)
source.data.vertices.foreach_get('co',vv);vv=vv.reshape(-1,3)
materials={k:bpy.data.materials['uri_'+k] for k in ['warm_white','blue','amber','graphite']}
materials['metal']=bpy.data.materials['uri_joint_metal'];materials['lamp']=bpy.data.materials['uri_lamp']
for o in list(bpy.data.objects):
    if o.type=='MESH':bpy.data.objects.remove(o,do_unlink=True)
fit_records=[]

def finish(o,mat,bevel=.005):
    o.data.materials.append(materials[mat])
    if bevel:
        m=o.modifiers.new('clean_edge_fillet','BEVEL');m.width=bevel;m.segments=4;m.limit_method='ANGLE';m.angle_limit=math.radians(18)
        m=o.modifiers.new('clean_surface_normals','WEIGHTED_NORMAL');m.keep_sharp=True
    o['part_type']='appearance_geometry_not_hardware_cad'
    return o

def fit(name,mask,mat,bevel=.006,offset=None):
    p=vv[mask]
    if len(p)<20:raise RuntimeError('No source volume for '+name)
    # Reduce samples while retaining the actual reconstruction's envelope.
    q=np.round(p/.004).astype(np.int32)
    _,idx=np.unique(q,axis=0,return_index=True);p=p[idx].astype(float)
    if offset is not None:p+=np.asarray(offset)
    h=ConvexHull(p)
    tri=h.simplices.copy();norm=np.cross(p[tri[:,1]]-p[tri[:,0]],p[tri[:,2]]-p[tri[:,0]])
    flip=np.sum(norm*h.equations[:,:3],axis=1)<0
    tri[flip]=tri[flip][:,[0,2,1]]
    used,inv=np.unique(tri.reshape(-1),return_inverse=True)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(p[used].tolist(),[],inv.reshape(-1,3).tolist());mesh.update()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
    finish(o,mat,bevel)
    o['source_volume']='g3 clean-side reconstructed geometry'
    fit_records.append({'part':name,'samples':len(p),'vertices':len(used),'bounds':[p.min(0).tolist(),p.max(0).tolist()]})
    return o

def cube(name,center,size,mat,bevel=.004,rotation=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if rotation:o.rotation_euler=rotation
    return finish(o,mat,bevel)

def cylinder(name,center,radius,width,mat,axis=(1,0,0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=radius,depth=width,location=center)
    o=bpy.context.object;o.name=name;o.rotation_euler=Vector(axis).to_track_quat('Z','Y').to_euler()
    return finish(o,mat,.0025)

def beam(name,a,b,width,depth,mat):
    mid=(Vector(a)+Vector(b))/2
    o=cube(name,mid,(width,depth,(Vector(b)-Vector(a)).length),mat,.008)
    o.rotation_euler=(Vector(b)-Vector(a)).to_track_quat('Z','Y').to_euler()
    return o

x,y,z=vv.T;a=abs(x)
# The core is fitted to the observed wedge and crown, excluding inferred rear
# rails. Closing this envelope repairs the open U-shaped generated roof.
core=fit('continuous_wedge_core',(a<.195)&(z>.119)&(z<.43)&(y<.16),'warm_white',.008)
for side in (-1,1):
    sx=x*side
    fit(f'blue_upper_flank_{side}',(sx>.125)&(sx<.218)&(z>.290)&(z<.405)&(y<.075),'blue',.007,(side*.003,0,.002))
    fit(f'shoulder_guard_{side}',(sx>.197)&(sx<.297)&(z>.288)&(z<.385)&(y<.10),'blue',.008)
    fit(f'upper_arm_cover_{side}',(sx>.200)&(sx<.290)&(z>.155)&(z<.292)&(y<.12)&(y>-.17),'warm_white',.008)
    fit(f'forearm_guard_{side}',(sx>.190)&(sx<.291)&(z>-.135)&(z<.110)&(y<-.025)&(y>-.30),'blue',.008)
    fit(f'thigh_armor_{side}',(sx>.115)&(sx<.272)&(z>-.170)&(z<.080)&(y<.100)&(y>-.270),'blue',.012)
    fit(f'continuous_lower_leg_{side}',(sx>.125)&(sx<.254)&(z>-.398)&(z<-.216)&(y<.100)&(y>-.180),'blue',.007)
    # Restore clean orange distal caps as complete source-fitted armor pieces.
    fit(f'distal_thigh_amber_cap_{side}',(sx>.12)&(sx<.27)&(z>-.167)&(z<-.106)&(y<-.095)&(y>-.26),'amber',.007,(0,-.003,0))
    # Each real-looking joint is a separately editable appearance envelope.
    for tag,c,r,w in [('shoulder',(side*.215,-.018,.302),.043,.066),
                      ('elbow',(side*.257,-.085,.123),.036,.070),
                      ('hip',(side*.173,.009,.060),.047,.095),
                      ('knee',(side*.186,-.158,-.159),.048,.098),
                      ('return',(side*.190,.024,-.232),.043,.095),
                      ('ankle',(side*.190,-.029,-.386),.036,.094)]:
        cylinder(f'{tag}_joint_envelope_{side}',c,r,w,'graphite')
        # Thin amber rim expresses the old Gorilla material hierarchy.
        for sign in (-1,1):cylinder(f'{tag}_rim_{side}_{sign}',(c[0]+sign*w*.505,c[1],c[2]),r*.91,.003,'amber')
    beam(f'knee_return_bridge_{side}',(side*.188,-.153,-.164),(side*.19,.025,-.231),.086,.052,'graphite')
    beam(f'hip_to_thigh_inner_{side}',(side*.17,.015,.051),(side*.184,-.152,-.158),.085,.060,'graphite')
    beam(f'lower_leg_inner_{side}',(side*.19,.024,-.231),(side*.19,-.029,-.386),.073,.048,'graphite')
    beam(f'arm_upper_inner_{side}',(side*.215,-.018,.302),(side*.257,-.085,.123),.052,.05,'graphite')
    beam(f'arm_fore_inner_{side}',(side*.257,-.085,.123),(side*.223,-.198,-.145),.048,.043,'graphite')
    # Low integrated foot; its shank connection is broad, its sole is continuous.
    cx=side*.190
    plan=[(-.061,-.211),(.061,-.211),(.067,-.176),(.060,.063),(-.060,.063),(-.067,-.176)]
    verts=[(cx+xx,yy,-.433) for xx,yy in plan]
    verts += [(cx+xx*.92,yy,-.405 if yy<-.13 else -.377) for xx,yy in plan]
    faces=[tuple(range(5,-1,-1)),tuple(range(6,12))]+[(i,(i+1)%6,(i+1)%6+6,i+6) for i in range(6)]
    mesh=bpy.data.meshes.new(f'integrated_foot_{side}');mesh.from_pydata(verts,[],faces);mesh.update()
    foot=bpy.data.objects.new(f'integrated_foot_{side}',mesh);bpy.context.collection.objects.link(foot);finish(foot,'warm_white',.006)
    cube(f'continuous_sole_{side}',(cx,-.071,-.436),(.132,.282,.019),'graphite',.006)
    cube(f'ankle_bridge_cover_{side}',(cx,-.030,-.373),(.091,.088,.056),'warm_white',.008)
    cube(f'toe_top_cover_{side}',(cx,-.169,-.399),(.110,.063,.023),'warm_white',.004,(math.radians(-7),0,0))
    # Organized five-digit hand, positioned at the reference wrist height.
    hx=side*.221;hy=-.200;hz=-.145
    cylinder(f'wrist_{side}',(hx,hy,hz+.004),.024,.054,'graphite')
    cube(f'hand_palm_{side}',(hx,hy-.009,hz-.025),(.069,.039,.061),'warm_white',.010)
    for j in range(4):
        fx=hx+(j-1.5)*.015
        drop=(abs(j-1.5)-.5)*.006
        cube(f'finger_knuckle_{side}_{j}',(fx,hy-.020,hz-.065+drop),(.013,.025,.024),'graphite',.004)
        cube(f'finger_armor_{side}_{j}',(fx,hy-.029,hz-.081+drop),(.012,.024,.023),'warm_white',.004,(math.radians(17),0,0))
        cube(f'finger_tip_{side}_{j}',(fx,hy-.040,hz-.096+drop),(.012,.019,.015),'graphite',.004,(math.radians(35),0,0))
    cube(f'hand_thumb_{side}',(hx-side*.040,hy-.007,hz-.038),(.019,.026,.037),'warm_white',.005,(0,side*math.radians(25),0))

cube('integrated_waist_bridge',(0,-.025,.077),(.244,.141,.075),'graphite',.022)
cube('short_waist_service_cover',(0,-.102,.073),(.154,.043,.067),'warm_white',.014)
cube('waist_amber_strip',(0,-.126,.092),(.110,.009,.010),'amber',.002)

bvh=BVHTree.FromObject(core,bpy.context.evaluated_depsgraph_get())
def surface_y(xx,zz,front=True):
    h,n,i,d=bvh.ray_cast(Vector((xx,-2 if front else 2,zz)),Vector((0,1 if front else -1,0)),4)
    if h is None:raise RuntimeError(f'No core surface at {xx}, {zz}')
    return h.y
grilles=[]
for side in (-1,1):
    xx=side*.111;zz=.257;yy=surface_y(xx,zz)-.011
    cube(f'forward_radiator_housing_{side}',(xx,yy,zz),(.067,.034,.104),'warm_white',.008)
    cube(f'forward_radiator_rim_{side}',(xx,yy-.020,zz),(.056,.008,.091),'amber',.004)
    cube(f'forward_radiator_recess_{side}',(xx,yy-.024,zz),(.047,.006,.077),'graphite',.003)
    for j in range(9):cube(f'radiator_louver_{side}_{j}',(xx,yy-.028,zz+(j-4)*.008),(.045,.0025,.003),'metal',.0005)
    grilles.append({'center':[xx,yy,zz],'opening_normal':[0,-1,0]})
zz=.213;yy=surface_y(0,zz)-.005
cube('central_lamp_socket',(0,yy,zz),(.024,.015,.078),'graphite',.003)
cube('central_lamp_trim',(0,yy-.009,zz),(.019,.006,.072),'amber',.003)
cube('central_lamp_lens',(0,yy-.013,zz),(.011,.005,.059),'lamp',.002)
zz=.290;yy=surface_y(0,zz,False)+.011
cube('rear_hatch_seal',(0,yy,zz),(.115,.012,.143),'graphite',.008)
cube('rear_blue_service_hatch',(0,yy+.008,zz),(.106,.014,.134),'blue',.007)
cube('rear_hatch_handle',(0,yy+.019,zz+.043),(.030,.006,.009),'graphite',.002)
for side in (-1,1):cube(f'hatch_latch_marker_{side}',(side*.038,yy+.017,zz+.015),(.007,.004,.023),'amber',.001)

models=[o for o in bpy.context.scene.objects if o.type=='MESH']
scene=bpy.context.scene
scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.cycles.samples=48
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(1,1,1,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.80
scene.view_settings.exposure=-.65
corners=[o.matrix_world@Vector(c) for o in models for c in o.bound_box]
lo=Vector([min(c[i] for c in corners) for i in range(3)]);hi=Vector([max(c[i] for c in corners) for i in range(3)])
center=(lo+hi)/2;camera=scene.camera;camera.data.ortho_scale=max(hi-lo)*1.20
views=[]
for name,direction in [('front',(0,-1,0)),('left',(1,0,0)),('rear',(0,1,0)),('top',(0,0,1)),('reference',(.574,-.819,.18))]:
    camera.location=center+Vector(direction)*3
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(ROOT/'images'/f'{name}_native_g4.png')
    bpy.ops.render.render(write_still=True)
    views.append({'name':name,'file':f'images/{name}_native_g4.png','eye':list(camera.location),'target':list(center),'ortho_scale':camera.data.ortho_scale})
    print('RETOPO_NATIVE_VIEW',name,flush=True)
for o in models:o['assembly_revision']='gorilla_v0.2_g4'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/gorilla_surface_g4.blend'),compress=True)
bpy.ops.object.select_all(action='DESELECT')
for o in models:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'generated/gorilla_surface_g4.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
record={'revision':'g4','source_native':'source/gorilla_clean_g3.blend','source_raw_geometry_sha256':'60ba19b16ac5d6fdbe9d341502931ff52c49e2741b1087c366e05ba8f7fed971',
        'surface_fit_records':fit_records,'operations':['source-fitted closed crown and limb armor','removed generated rear and arm rails','five-digit hands','integrated low foot soles','Gorilla lamp, forward radiators and rear service hatch'],
        'radiators':grilles,'views':views,'bounds':[list(lo),list(hi)],'model_objects':len(models),'all_views_same_model_and_pose':True,
        'scale':'normalized appearance units','engineering_status':'Appearance assembly; joints are envelope annotations, not bearing/actuator CAD or a dynamics model.',
        'imagegen_used_before_native_geometry':False,'elapsed_seconds':time.time()-START}
(ROOT/'source/retopology_g4_record.json').write_text(json.dumps(record,indent=2)+'\n')
print('RETOPOLOGY_G4_COMPLETE',time.time()-START,flush=True)
