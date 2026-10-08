"""Native symmetric projection registration for the user-marked TOP correction.

This is an editable appearance-envelope guide registered to the selected
FRONT/LEFT, not a replacement for the detailed lower-body master or a claim of
recovered CAD. Camera and white-shell depth are explicit; no source raster is
painted, warped or recolored here.
"""
from pathlib import Path
import math, json, hashlib, sys
import bpy, bmesh
from mathutils import Vector
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'source/top_registration_p21.blend'
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
WHITE=(.94,.90,.81,1); BLUE=(.014,.38,.75,1); DARK=(.075,.10,.12,1); GOLD=(.98,.55,.04,1)
left=[]; central=[]

def mesh(name, vertices, faces, color, paired=False):
    data=bpy.data.meshes.new(name+'_mesh'); data.from_pydata(vertices,[],faces); data.update(); data.use_auto_smooth=True
    bm=bmesh.new(); bm.from_mesh(data); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(data); bm.free()
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj); obj.color=color
    obj['scope']='Appearance envelope / projection only'
    bevel=obj.modifiers.new('Small continuous edge fillet','BEVEL'); bevel.width=.002; bevel.segments=3
    obj.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL')
    if paired:
        twin=obj.copy(); twin.name=name.replace('L_','R_',1); twin.data=obj.data; twin.scale.x=-1
        bpy.context.collection.objects.link(twin); left.append((obj,twin))
    else: central.append(obj)
    return obj

def loft(name, rings, color, paired=False):
    n=len(rings[0]); vertices=[tuple(v) for r in rings for v in r]
    faces=[tuple(reversed(range(n))),tuple(range((len(rings)-1)*n,len(rings)*n))]
    for k in range(len(rings)-1):
        for j in range(n): faces.append((k*n+j,k*n+(j+1)%n,(k+1)*n+(j+1)%n,(k+1)*n+j))
    return mesh(name,vertices,faces,color,paired)

def ellipsoid(name, center, radii, color):
    # Multiple round sections give a readable mass rather than rectangular boxes.
    cx,cy,cz=center; rx,ry,rz=radii; rings=[]
    for a in np.linspace(-math.pi/2+.018,math.pi/2-.018,17):
        rings.append([(cx+rx*math.cos(a)*math.cos(t),cy+ry*math.cos(a)*math.sin(t),cz+rz*math.sin(a)) for t in np.linspace(0,2*math.pi,48,endpoint=False)])
    return loft(name,rings,color,True)

# Manual FRONT/LEFT registration, normalized by their ~583 px elevation height.
# The same shell is used in TOP. Its frontal height never becomes TOP depth.
sections=[(.660,.026,-.175,.072),(.715,.043,-.187,.092),
          (.790,.075,-.190,.132),(.860,.112,-.168,.159),
          (.925,.145,-.117,.158),(.965,.142,-.072,.134),
          (.989,.119,-.022,.106),(.994,.102,.010,.093)]

def shell_ring(z,w,front,rear):
    depth=rear-front
    return [(-w*.73,rear,z),(w*.73,rear,z),(w,rear-depth*.13,z),
            (w*.91,front+depth*.18,z),(w*.25,front,z),
            (-w*.25,front,z),(-w*.91,front+depth*.18,z),(-w,rear-depth*.13,z)]

loft('Central_warm_white_shell',[shell_ring(*s) for s in sections],WHITE)
# Existing crown panel, fitted onto the same sloping crown; no new beak.
loft('Central_crown_panel',[shell_ring(.993,.094,.004,.092),
                          shell_ring(.997,.092,.006,.090)],(.88,.85,.77,1))
ellipsoid('L_blue_torso_side',(.126,-.015,.806),(.077,.135,.129),BLUE)
# Crown shell is a narrow rounded shoulder plate, not an oversized oval cap.
shoulder=[]
for z,w,front,rear,cx in [(.850,.040,-.023,.178,.210),(.900,.051,-.026,.180,.207),(.937,.037,.018,.170,.200),(.953,.022,.050,.143,.194)]:
    ring=shell_ring(z,w,front,rear)
    shoulder.append([(x+cx,y,zz) for x,y,zz in ring])
loft('L_shoulder_blue',shoulder,BLUE,True)
loft('Central_rear_blue_hatch_edge',[[(-.052,.163,.871),(.052,.163,.871),(.052,.177,.871),(-.052,.177,.871)],
                                      [(-.050,.163,.887),(.050,.163,.887),(.050,.177,.887),(-.050,.177,.887)]],BLUE)
ellipsoid('L_upper_arm_white',(.269,.055,.817),(.055,.070,.070),WHITE)
ellipsoid('L_arm_blue_cap',(.301,.010,.765),(.052,.065,.077),BLUE)
ellipsoid('L_upper_arm_lower_white',(.293,.010,.709),(.047,.058,.060),WHITE)
ellipsoid('L_elbow_hub',(.317,.004,.641),(.045,.044,.043),DARK)
ellipsoid('L_forearm_blue',(.333,-.024,.532),(.052,.080,.093),BLUE)
ellipsoid('L_hand_white',(.333,-.103,.398),(.046,.046,.048),WHITE)
ellipsoid('L_fingers_dark',(.341,-.113,.356),(.044,.045,.032),DARK)
ellipsoid('L_hip_cover',(.143,.036,.617),(.063,.065,.045),WHITE)
ellipsoid('L_thigh_blue',(.145,-.072,.490),(.105,.106,.148),BLUE)
ellipsoid('L_knee_gold',(.159,-.133,.359),(.083,.062,.053),GOLD)
ellipsoid('L_return_joint',(.166,.005,.337),(.072,.055,.043),DARK)
ellipsoid('L_shank_blue',(.188,.024,.240),(.055,.061,.092),BLUE)
ellipsoid('L_ankle_hub',(.190,.003,.117),(.058,.061,.043),DARK)

foot_outline=np.array([[-.063,.178],[.063,.178],[.078,.119],[.076,-.160],
                       [.055,-.232],[-.055,-.232],[-.078,-.160],[-.078,.119]])
angle=math.radians(15); rot=np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]])
xy=foot_outline@rot.T+[.213,0]
loft('L_complete_foot',[[(x,y,.020) for x,y in xy],[(x,y,.072) for x,y in xy]],WHITE,True)

scene=bpy.context.scene; scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'; scene.display.shading.studio_light='paint.sl'
scene.display.shading.color_type='OBJECT'; scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True; scene.display.shading.cavity_type='BOTH'
scene.display.shading.show_object_outline=True; scene.display.shading.object_outline_color=(.05,.08,.11)
scene.display.shading.background_type='WORLD'; scene.world.color=(1,1,1)
scene.view_settings.view_transform='Standard'
scene.render.resolution_x=1024; scene.render.resolution_y=1024; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
bpy.ops.object.camera_add(); cam=bpy.context.object; cam.name='Orthographic_same_source_camera'; cam.data.type='ORTHO'; scene.camera=cam
views={}
objects=[o for o in scene.objects if o.type=='MESH']
vertices=np.array([o.matrix_world@v.co for o in objects for v in o.data.vertices])
minimum=vertices.min(0); maximum=vertices.max(0); center=Vector(((minimum+maximum)/2).tolist())
for name,axis in [('top',(0,0,1)),('left',(1,0,0)),('front',(0,-1,0))]:
    cam.location=center+Vector(axis)*4
    if name=='top': cam.rotation_euler=(0,0,0)  # -Z optical axis, +Y page up, front at page bottom.
    else: cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    inv=np.array(cam.matrix_world.inverted()); projected=vertices@inv[:3,:3].T+inv[:3,3]
    low=projected[:,:2].min(0); high=projected[:,:2].max(0); offset=(low+high)/2
    basis=np.array(cam.matrix_world)[:3,:3]; cam.location+=Vector((basis[:,0]*offset[0]+basis[:,1]*offset[1]).tolist())
    cam.data.ortho_scale=.94 if name=='top' else 1.15
    scene.render.filepath=str(ROOT/f'images/native_registration_{name}_p21.png')
    bpy.ops.render.render(write_still=True)
    views[name]={'path':f'images/native_registration_{name}_p21.png','projected_span':(high-low).tolist(),
                 'camera_matrix':np.array(cam.matrix_world).tolist(),'ortho_scale':cam.data.ortho_scale}
mirror=[]
for l,r in left:
    vl=np.array([l.matrix_world@v.co for v in l.data.vertices]); vr=np.array([r.matrix_world@v.co for v in r.data.vertices]); vl[:,0]*=-1
    mirror.append({'left':l.name,'right':r.name,'shared_mesh_data':l.data==r.data,
                   'maximum_vertex_mirror_error':float(abs(vl-vr).max())})
topology=[]
for obj in [p[0] for p in left]+central:
    bm=bmesh.new(); bm.from_mesh(obj.data)
    topology.append({'name':obj.name,'boundary_edges':sum(e.is_boundary for e in bm.edges),
                     'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges)})
    bm.free()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report={'revision':'p21','source':'source/top_registration_p21.blend',
        'basis':'references/user_four_view_top_fix_p19.jpg',
        'scope':'Manually registered appearance envelopes and exact orthographic camera; not final complete robot CAD',
        'white_shell_sections_z_half_width_front_rear':sections,
        'white_shell_plan_extent_xy':[.290,.349],
        'top_camera_axis':[0,0,-1],'front_direction_in_top':'page bottom',
        'strict_shared_mesh_mirror':all(m['shared_mesh_data'] and m['maximum_vertex_mirror_error']<1e-8 for m in mirror),
        'mirrors':mirror,'topology':topology,'views':views,
        'detailed_lower_master_not_modified':'source/lower_modular_components_b6.blend',
        'physical_or_mass_validation':False,'full_model_appearance_acceptance':False,
        'source_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()}
(ROOT/'native_top_registration_p21.json').write_text(json.dumps(report,indent=2)+'\n')
print('NATIVE_TOP_REGISTRATION',report['strict_shared_mesh_mirror'],report['white_shell_plan_extent_xy'],flush=True)
