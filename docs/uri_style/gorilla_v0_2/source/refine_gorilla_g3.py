"""Native mesh cleanup and Gorilla identity restoration, without image synthesis.

The original dense reconstruction remains untouched. This stage removes weapon
volumes, seals cut surfaces, suppresses reconstruction noise and adds editable
Gorilla service/lamp/grille parts. Units remain a normalized appearance unit.
"""
from pathlib import Path
import sys, json, math, hashlib, time
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
START = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
npz = np.load(ROOT / 'source/working_geometry_g1.npz')
v, f = npz['vertices'].copy(), npz['faces']
labels = np.load(ROOT / 'source/working_component_labels.npy')
main_label = int(np.argmax(np.bincount(labels)))

def capsule_distance(points, a, b):
    a, b = np.asarray(a), np.asarray(b)
    ab = b-a
    t = np.clip((points-a) @ ab / (ab @ ab), 0, 1)
    return np.linalg.norm(points-(a+t[:, None]*ab), axis=1)

# The hand-held weapon is in front of the near forearm and shin. A 3D capsule
# follows its full axis; a separate lower-front envelope catches its muzzle.
gun = (capsule_distance(v, (-.236, -.236, .125), (-.158, -.458, -.337)) < .073)
gun |= (v[:, 0] < -.10) & (v[:, 0] > -.29) & (v[:, 1] < -.315) & (v[:, 2] < .05)
# Back-mounted inferred barrels and their plate, outside the rear torso shell.
back_gun = ((v[:, 0] > .12) & (v[:, 1] > .245) & (v[:, 2] > .085) & (v[:, 2] < .353))
back_gun |= (v[:, 1] > .305) & (v[:, 2] > .09)
# Small disconnected generated fragments are not appearance components.
islands = labels != main_label
removed = gun | back_gun | islands
keep_face = ~removed[f].any(axis=1)
f = f[keep_face]
# Put the reconstruction in the canonical frame before selecting the clear side.
R = (Matrix.Rotation(math.radians(10), 4, 'X') @
     Matrix.Rotation(math.radians(-4), 4, 'Y') @
     Matrix.Rotation(math.radians(-35), 4, 'Z'))
rr=np.asarray(R.to_3x3(),dtype=np.float64)
v=v@rr.T
v[:,0]+=.014
# The positive-X (unarmed) side is the geometry authority for both limbs. This
# replaces only the occluded-side reconstruction and enforces corresponding
# armor masses, hands, feet and bent stance in all turnaround views.
tri=v[f]
keep=(tri[:,:,0]>=0).all(1)
regular=f[keep]
crossing=f[(tri[:,:,0].min(1)<0)&(tri[:,:,0].max(1)>0)]
vv=v.tolist();ff=regular.tolist()
for t in crossing:
    poly=[v[int(i)] for i in t];clipped=[]
    for i,a in enumerate(poly):
        b=poly[(i+1)%3];inside=a[0]>=0;other=b[0]>=0
        if inside:clipped.append(a)
        if inside!=other:
            q=a+(b-a)*(-a[0]/(b[0]-a[0]));q[0]=0;clipped.append(q)
    if len(clipped)>=3:
        ids=[]
        for q in clipped:ids.append(len(vv));vv.append(q.tolist())
        for k in range(1,len(ids)-1):ff.append([ids[0],ids[k],ids[k+1]])
v=np.asarray(vv);f=np.asarray(ff)
used,inverse=np.unique(f.reshape(-1),return_inverse=True);v=v[used];f=inverse.reshape(-1,3)
# Remove the long center pelvis projection and the residual back weapon plate.
centroid=v[f].mean(1)
trim=((abs(centroid[:,0])<.065)&(centroid[:,2]<-.018)&(centroid[:,2]>-.145))
trim|=(centroid[:,1]>.205)&(centroid[:,2]>.07)&(abs(centroid[:,0])>.18)
f=f[~trim]
mir=v.copy();mir[:,0]*=-1
nf=len(v);v=np.concatenate([v,mir]);f=np.concatenate([f,f[:,[0,2,1]]+nf])
used,inverse=np.unique(f.reshape(-1),return_inverse=True);v=v[used];f=inverse.reshape(-1,3)
import fast_simplification
v,f=fast_simplification.simplify(v,f.astype(np.int32),target_count=350000,agg=5)
print('SYMMETRIC_CLEAR_SIDE_RESOLUTION',len(v),len(f),flush=True)
mesh = bpy.data.meshes.new('reference_cleaned_surface')
mesh.from_pydata(v.tolist(), [], f.tolist())
mesh.update()
body = bpy.data.objects.new('gorilla_reference_body_g3', mesh)
bpy.context.collection.objects.link(body)
bpy.context.view_layer.objects.active = body
body.select_set(True)
print('WEAPON_VOLUMES_REMOVED', len(v), len(f), flush=True)

# This bundled Blender has OpenVDB disabled. Seal boundary loops and use its
# available native octree dual-contour remesher. The resolution is an appearance
# resolution, not a collision or physical parameter.
remesh=body.modifiers.new('native_surface_reconstruction','REMESH')
remesh.mode='SMOOTH';remesh.octree_depth=9;remesh.scale=.95
remesh.use_remove_disconnected=True;remesh.threshold=.002
remesh.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=remesh.name)
print('CUT_SURFACES_SEALED', len(body.data.vertices), len(body.data.polygons), flush=True)
smooth = body.modifiers.new('surface_noise_cleanup', 'SMOOTH')
smooth.factor = .52
smooth.iterations = 55
bpy.ops.object.modifier_apply(modifier=smooth.name)
for face in body.data.polygons:
    face.use_smooth = True

# All geometry was calibrated before the clear-side reflection.
body['source_glb_sha256'] = '60ba19b16ac5d6fdbe9d341502931ff52c49e2741b1087c366e05ba8f7fed971'
body['physical_scale'] = 'normalized appearance coordinate; no engineering scale assigned'
body['editing_scope'] = 'weapon removal, surface cleanup, service-feature restoration'

def material(name, hex_color, metallic=.15, roughness=.40):
    c=tuple(int(hex_color[i:i+2],16)/255 for i in (1,3,5))
    def srgb_linear(x): return x/12.92 if x <= .04045 else ((x+.055)/1.055)**2.4
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*c,1)
    m.use_nodes=True
    p=m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value=(*map(srgb_linear,c),1)
    p.inputs['Metallic'].default_value=metallic
    p.inputs['Roughness'].default_value=roughness
    m['palette_srgb']=hex_color
    return m

M = {
    'warm_white': material('uri_warm_white', '#F1EBD9', .08, .44),
    'blue': material('uri_blue', '#069EEB', .23, .32),
    'amber': material('uri_amber', '#F5B523', .20, .37),
    'graphite': material('uri_graphite', '#29343C', .40, .48),
    'metal': material('uri_joint_metal', '#78858C', .65, .35),
    'lamp': material('uri_lamp', '#FFE3A0', .03, .25),
}
keys=list(M)
for key in keys: body.data.materials.append(M[key])
def mi(k): return keys.index(k)

# Native material regions follow the armor and joint silhouette. They are
# working appearance assignments, independent of engineering material specs.
for face in body.data.polygons:
    x,y,z=face.center
    a=abs(x)
    key='warm_white'
    if a>.215 and z>.29: key='blue'
    if a>.235 and .065<z<.16: key='graphite'
    if a>.26 and -.13<z<.075: key='blue'
    if a>.30 and z<-.13: key='warm_white'
    if .10<a<.265 and -.21<z<.085: key='blue'
    if .12<a<.27 and -.165<z<-.095: key='amber'
    if .10<a<.285 and -.36<z<-.205: key='blue'
    if z<-.39: key='warm_white'
    if z<-.422: key='graphite'
    # Structural return link and principal pivots keep a dark metal read.
    if .1<a<.28 and -.21<z<-.166: key='graphite'
    if .10<a<.285 and -.39<z<-.358: key='graphite'
    if a<.09 and z<.09: key='graphite'
    if .08<a<.175 and .12<z<.295 and y<-.10: key='blue'
    face.material_index=mi(key)

def bevel_cube(name, center, dimensions, mat, bevel=.004, rotation=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o=bpy.context.object
    o.name=name
    o.dimensions=dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rotation is not None: o.rotation_euler=rotation
    o.data.materials.append(mat)
    m=o.modifiers.new('machined_edge','BEVEL');m.width=bevel;m.segments=3
    m=o.modifiers.new('surface_normals','WEIGHTED_NORMAL')
    o['role']='appearance_component_not_engineering_hardware'
    return o

bvh=BVHTree.FromObject(body,bpy.context.evaluated_depsgraph_get())
def surface_y(x,z,front=True):
    origin=Vector((x,-2 if front else 2,z));direction=Vector((0,1 if front else -1,0))
    hit,normal,index,distance=bvh.ray_cast(origin,direction,4)
    return float(hit.y) if hit else (-.2 if front else .17)

# The mirrored unarmed thigh contains no launcher bores or launcher cover.
# Restore a short integrated waist bridge and blunt service armor, with no
# suspended center appendage.
bevel_cube('pelvis_inner_bridge',(0,-.056,.026),(.180,.095,.070),M['graphite'],.020)
bevel_cube('pelvis_service_armor',(0,-.128,.032),(.135,.038,.060),M['warm_white'],.018)
bevel_cube('pelvis_amber_band',(0,-.152,.050),(.099,.009,.009),M['amber'],.003)

# Forward facing radiators: the face normal is precisely -Y. TOP therefore
# sees only the upper lip, rather than an upward-facing opening.
grille_record=[]
for side in (-1,1):
    x=side*.119;z=.260;y=surface_y(x,z)-.013
    bevel_cube(f'radiator_housing_{side}',(x,y,z),(.069,.032,.106),M['warm_white'],.009)
    bevel_cube(f'radiator_amber_frame_{side}',(x,y-.018,z),(.058,.009,.091),M['amber'],.005)
    bevel_cube(f'radiator_dark_recess_{side}',(x,y-.024,z),(.048,.006,.077),M['graphite'],.003)
    for j in range(9):
        bevel_cube(f'radiator_louver_{side}_{j}',(x,y-.028,z+(j-4)*.008),(.046,.0025,.0030),M['metal'],.0006)
    grille_record.append({'side':side,'center':[x,y,z],'opening_normal':[0,-1,0]})

x=0;z=.203;y=surface_y(x,z)-.008
bevel_cube('central_amber_lamp_frame',(x,y,z),(.022,.015,.080),M['graphite'],.004)
bevel_cube('central_amber_lamp_trim',(x,y-.008,z),(.018,.005,.074),M['amber'],.003)
lamp=bevel_cube('central_amber_lamp_lens',(x,y-.012,z),(.010,.005,.059),M['lamp'],.002)
shader=M['lamp'].node_tree.nodes['Principled BSDF']
shader.inputs['Emission Color'].default_value=(1,.57,.13,1)
shader.inputs['Emission Strength'].default_value=.6

# A low-profile rear service shell and blue hatch replace generated clutter.
z=.284;y=surface_y(0,z,False)+.006
bevel_cube('rear_service_shell',(0,y,z),(.250,.026,.225),M['warm_white'],.025)
bevel_cube('rear_service_hatch_seal',(0,y+.018,z),(.115,.009,.152),M['graphite'],.010)
bevel_cube('rear_blue_service_hatch',(0,y+.024,z),(.107,.012,.143),M['blue'],.008)
bevel_cube('rear_hatch_handle',(0,y+.033,z+.043),(.029,.005,.009),M['graphite'],.002)
for side in (-1,1):
    bevel_cube(f'rear_hatch_marker_{side}',(side*.039,y+.032,z+.015),(.007,.005,.024),M['amber'],.001)

# Both hands now come from the unarmed reference side; no weapon-hand stub.

# The entire model uses one transform and one shared pose in all views.
models=[o for o in bpy.context.scene.objects if o.type=='MESH']
corners=[o.matrix_world@Vector(c) for o in models for c in o.bound_box]
lo=Vector(tuple(min(c[i] for c in corners) for i in range(3)))
hi=Vector(tuple(max(c[i] for c in corners) for i in range(3)))
center=(lo+hi)/2
scene=bpy.context.scene
scene.unit_settings.system='NONE'
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=False
scene.render.use_persistent_data=True
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.render.resolution_x=1100;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard';scene.view_settings.exposure=-1.05
scene.world=bpy.data.worlds.new('clean_studio')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.91,.94,.98,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
for name,loc,power,size in [('key',(2,-3,4),170,3),('fill',(-2,-1,2),85,3),('rim',(1,3,3),130,2)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    light=bpy.context.object;light.name=name;light.data.energy=power;light.data.size=size
    light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;camera.name='canonical_four_view_camera'
camera.data.type='ORTHO';camera.data.ortho_scale=max(hi-lo)*1.19
scene.camera=camera
views=[]
for name,direction,up in [('front',(0,-1,0),'Y'),('left',(1,0,0),'Y'),('rear',(0,1,0),'Y'),('top',(0,0,1),'Y'),('reference',(.574,-.819,.18),'Y')]:
    camera.location=center+Vector(direction)*3
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z',up).to_euler()
    scene.render.filepath=str(ROOT/'images'/f'{name}_native_g3.png')
    bpy.ops.render.render(write_still=True)
    views.append({'name':name,'path':f'images/{name}_native_g3.png','eye':list(camera.location),'target':list(center),'orthographic_scale':camera.data.ortho_scale})
    print('CLEAN_NATIVE_VIEW',name,flush=True)

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/gorilla_clean_g3.blend'),compress=True)
bpy.ops.object.select_all(action='DESELECT')
for o in models:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'generated/gorilla_clean_g3.glb'),export_format='GLB',use_selection=True,export_apply=True)
record={'revision':'g3','source_preserved':True,'input_glb_sha256':body['source_glb_sha256'],
        'removed_vertex_regions':{'handheld_weapon':int(gun.sum()),'back_weapon':int(back_gun.sum()),'disconnected_fragments':int(islands.sum())},
        'native_operations':['3D weapon face removal','native smooth octree dual-contour remesh depth 9','55 smoothing iterations and unobscured-side geometric reflection','camera-coordinate calibration','editable lamp, forward radiator, rear service hatch and thigh armor restoration'],
        'calibration_degrees':{'yaw':-35,'roll_y':-4,'photo_elevation_x':10},
        'coordinate_frame':{'up':'+Z','front':'-Y','left':'+X','scale':'normalized appearance units'},
        'bounds':[list(lo),list(hi)],'vertices':sum(len(o.data.vertices) for o in models),'faces':sum(len(o.data.polygons) for o in models),
        'radiator_faces':grille_record,'views':views,'same_geometry_and_pose_all_views':True,'imagegen_used':False,
        'qualification':'native appearance cleanup candidate; not mechanically dimensioned or load qualified','elapsed_seconds':time.time()-START}
(ROOT/'source/cleanup_g3_record.json').write_text(json.dumps(record,indent=2)+'\n')
print('CLEANUP_G3_COMPLETE',record['elapsed_seconds'],flush=True)
