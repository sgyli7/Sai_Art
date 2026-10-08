"""Reconstruct the latest user reference before any image generation.

Observed control polygons are in original reference pixels. Each is lifted
onto an explicit 3D part plane, with an actual finite rear surface. A single
camera and one mesh source drive the overlay and all turnaround views.
Single-view depth, hidden articulations and cropped feet remain hypotheses.
"""
from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
import trimesh as tr

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path('/tmp/codex-remote-attachments/01a0f3ab-7a57-7172-b8c5-e517aa2973da/1DD0D354-F5EE-434C-A44E-D2B688E3F88B/1-照片-1.jpg')
AZIMUTH, ELEVATION = np.deg2rad([-28., 20.])
VIEW = np.array([np.cos(ELEVATION)*np.cos(AZIMUTH),
                 np.cos(ELEVATION)*np.sin(AZIMUTH), np.sin(ELEVATION)])
RIGHT = np.array([-np.sin(AZIMUTH), np.cos(AZIMUTH), 0.])
UP = np.cross(VIEW, RIGHT)
TARGET = np.array([0., 0., 1.3])
PIXEL_CENTER = np.array([400., 472.])
PIXELS_PER_LAYOUT_UNIT = 360.


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lift(pixel, normal, plane_offset):
    normal = np.asarray(normal, dtype=float)
    p = TARGET+(pixel[0]-PIXEL_CENTER[0])/PIXELS_PER_LAYOUT_UNIT*RIGHT \
        +(PIXEL_CENTER[1]-pixel[1])/PIXELS_PER_LAYOUT_UNIT*UP
    return p+VIEW*((plane_offset-normal@p)/(normal@VIEW))


def project(points):
    points = np.asarray(points)-TARGET
    return np.column_stack((PIXEL_CENTER[0]+PIXELS_PER_LAYOUT_UNIT*(points@RIGHT),
                            PIXEL_CENTER[1]-PIXELS_PER_LAYOUT_UNIT*(points@UP)))


PARTS, OBSERVATIONS = [], []


def append_mesh(name, body, mesh, shade, provenance, **extra):
    mesh.fix_normals()
    assert mesh.is_watertight and mesh.volume > 0, name
    PARTS.append({'name': name, 'body': body, 'vertices': mesh.vertices.tolist(),
                  'faces': mesh.faces.tolist(), 'shade': shade,
                  'geometry_role': provenance, **extra})


def panel(name, body, polygon, normal, offset, thickness, shade=.62, rear_scale=.87):
    uv = np.asarray(polygon, dtype=float)
    normal = np.asarray(normal, dtype=float); normal /= np.linalg.norm(normal)
    front = np.array([lift(p, normal, offset) for p in uv])
    # Finite thickness is along the component's local normal. The rear
    # silhouette is separately constrained inside the observed silhouette;
    # this is a stated single-view reconstruction, not hidden CAD evidence.
    centroid = uv.mean(0)
    rear_uv = centroid+(uv-centroid)*rear_scale
    rear = np.array([lift(p, normal, offset-thickness) for p in rear_uv])
    mesh = tr.convex.convex_hull(np.vstack([front, rear]))
    append_mesh(name, body, mesh, shade, 'observed_face_with_assumed_depth',
                plane_normal=normal.tolist(), plane_offset=float(offset),
                layout_thickness=float(thickness))
    error = np.linalg.norm(project(front)-uv, axis=1)
    OBSERVATIONS.append({'name': name, 'reference_polygon_px': uv.tolist(),
                         'observed_control_vertices_3d': front.tolist(),
                         'max_control_reprojection_error_px': float(error.max()),
                         'depth_confirmed': False})
    return front


def rod(name, body, a, b, radius, shade=.20):
    a, b = np.asarray(a), np.asarray(b)
    mesh=tr.creation.cylinder(radius=radius,height=np.linalg.norm(b-a),sections=24)
    transform=tr.geometry.align_vectors([0.,0.,1.],b-a)
    transform[:3,3]=(a+b)/2
    mesh.apply_transform(transform)
    append_mesh(name,body,mesh,shade,'inferred_internal_connection')


def joint(name, body, pixel, normal, offset, radius):
    n=np.asarray(normal,dtype=float);n/=np.linalg.norm(n)
    p=lift(pixel,n,offset)-VIEW*.15
    rod(name,body,p+[0.,-.12,0.],p+[0.,.12,0.],radius,.22)
    return p


def main():
    for directory in ('source','images','references'):
        (ROOT/directory).mkdir(parents=True,exist_ok=True)
    shutil.copy2(REFERENCE,ROOT/'references'/'primary_user_reference.jpg')
    # Entire structure is rebuilt from the actual latest photo. No rejected
    # R2/R3 geometry or generated drawing contributes an exterior shape.
    panel('crown_roof_wedge','torso',
          [[234,0],[506,0],[551,35],[590,83],[615,128],[593,165],
           [554,185],[477,174],[391,133],[301,84],[254,52]],
          [1.,0.,1.05],2.34,.58,.69)
    panel('main_front_tapered_face','torso',
          [[312,117],[405,148],[474,182],[566,183],[551,263],[520,345],
           [497,369],[459,373],[426,336],[398,266],[376,213],[335,180]],
          [1.,0.,.12],.69,.48,.64)
    panel('near_shoulder_continuous_plate','near_upper_arm',
          [[137,7],[204,27],[235,76],[220,110],[190,145],[164,163],
           [120,163],[91,145],[76,118],[82,80],[103,44]],
          [1.,-.35,0.],.69,.31,.65)
    panel('far_shoulder_plate','far_upper_arm',
          [[638,75],[673,92],[693,119],[692,144],[670,170],[640,163],
           [616,133],[610,106]],
          [1.,.25,0.],.45,.28,.61)
    panel('near_upper_arm_shield','near_upper_arm',
          [[111,170],[193,157],[204,180],[191,226],[176,266],[153,295],
           [118,285],[91,247],[90,205]],
          [1.,-.20,0.],.78,.31,.56)
    panel('far_upper_arm_shield','far_upper_arm',
          [[659,173],[691,175],[713,216],[720,269],[701,321],[668,292],
           [646,247],[639,211]],
          [1.,.15,0.],.47,.29,.53)
    panel('near_forearm_shield','near_forearm',
          [[96,335],[137,344],[145,398],[157,452],[171,501],[164,527],
           [144,550],[112,544],[99,487],[80,414],[75,360]],
          [1.,-.15,0.],.85,.30,.64)
    panel('far_forearm_shield','far_forearm',
          [[699,320],[722,314],[742,344],[746,431],[735,502],[722,567],
           [704,615],[676,608],[675,565],[682,488],[680,409]],
          [1.,.10,0.],.58,.28,.58)
    panel('near_front_radiator_housing','torso',
          [[274,107],[315,115],[337,143],[340,189],[329,221],[312,236],
           [284,232],[267,211],[259,167],[264,129]],
          [1.,0.,0.],.735,.07,.54)
    panel('near_forward_radiator_recess','torso',
          [[281,123],[314,130],[326,148],[328,191],[318,213],[300,218],
           [280,205],[274,165]],
          [1.,0.,0.],.742,.016,.12)
    panel('far_forward_radiator_recess','torso',
          [[606,183],[623,177],[626,195],[622,235],[607,248],[596,244]],
          [1.,0.,0.],.725,.025,.13)
    panel('reference_front_nose_lamp','torso',
          [[533,143],[562,143],[579,151],[574,172],[558,180],[542,172]],
          [1.,0.,1.05],2.349,.010,.52)
    panel('reference_vertical_front_lamp','torso',
          [[511,269],[523,265],[521,310],[511,330],[507,318]],
          [1.,0.,.12],.697,.011,.48)
    panel('reference_compact_hip_front_cover','pelvis',
          [[422,375],[469,369],[528,384],[540,415],[534,486],[514,531],
           [474,533],[447,496],[434,451],[422,410]],
          [1.,0.,0.],.45,.22,.59)
    panel('near_full_thigh_armor','near_thigh',
          [[277,289],[320,274],[353,289],[374,331],[358,411],[330,505],
           [301,591],[274,654],[250,684],[219,681],[191,651],[174,600],
           [170,542],[185,436],[217,350],[247,311]],
          [1.,-.12,-.30],.29,.46,.60)
    panel('near_thigh_dark_inset','near_thigh',
          [[284,331],[319,334],[336,350],[326,430],[299,502],[272,526],
           [244,503],[248,440],[263,374]],
          [1.,-.12,-.30],.297,.012,.14)
    panel('near_thigh_lower_fitted_cover','near_thigh',
          [[242,502],[272,521],[303,498],[300,555],[281,615],[257,656],
           [220,655],[204,620],[207,568]],
          [1.,-.12,-.30],.305,.025,.64)
    panel('far_full_thigh_armor','far_thigh',
          [[566,325],[621,324],[670,348],[702,384],[723,425],[742,478],
           [746,563],[729,616],[704,658],[676,677],[641,675],[615,638],
           [589,585],[558,503],[534,428],[528,377],[543,347]],
          [1.,.13,.24],.61,.44,.59)
    panel('far_thigh_upper_service_cover','far_thigh',
          [[570,337],[620,342],[659,364],[686,398],[703,444],[718,484],
           [701,510],[672,504],[637,474],[605,424],[578,375]],
          [1.,.13,.24],.628,.022,.65)
    panel('far_thigh_lower_knee_cover','far_thigh',
          [[641,501],[671,513],[706,535],[727,563],[719,612],[699,648],
           [669,662],[642,644],[620,607],[610,562]],
          [1.,.13,.24],.637,.024,.57)
    panel('far_return_link_integrated_shield','far_middle',
          [[570,564],[593,557],[615,577],[628,615],[613,662],[589,715],
           [565,751],[538,754],[516,728],[513,682],[531,615]],
          [1.,.06,-.05],.29,.30,.49)
    panel('far_continuous_lower_leg','far_distal',
          [[607,644],[642,642],[669,659],[682,700],[693,744],[688,790],
           [675,850],[653,889],[631,904],[611,881],[604,838],[593,783],
           [589,730],[594,677]],
          [1.,.06,.05],.42,.36,.57)
    panel('near_continuous_lower_leg','near_distal',
          [[213,665],[244,672],[270,662],[269,697],[252,750],[235,823],
           [217,912],[204,934],[184,932],[188,865],[192,798],[196,731]],
          [1.,-.05,-.04],.35,.30,.55)
    # Exposed joints and skeleton are separate from the masks. Their hidden
    # exact locations cannot be recovered from a single partly occluded view.
    near = {'hip':joint('near_hip_joint','pelvis',[300,322],[1.,-.12,-.30],.29,.095),
            'knee':joint('near_knee_joint','near_middle',[246,653],[1.,-.12,-.30],.29,.090),
            'fold':joint('near_fold_joint','near_distal',[216,723],[1.,-.05,-.04],.35,.083),
            'ankle':joint('near_low_ankle','near_foot',[205,926],[1.,-.05,-.04],.35,.081)}
    far = {'hip':joint('far_hip_joint','pelvis',[584,354],[1.,.13,.24],.61,.095),
           'knee':joint('far_knee_joint','far_middle',[666,615],[1.,.13,.24],.61,.096),
           'fold':joint('far_fold_joint','far_distal',[566,669],[1.,.06,-.05],.29,.085),
           'ankle':joint('far_low_ankle','far_foot',[642,889],[1.,.06,.05],.42,.082)}
    for side, axes in (('near',near),('far',far)):
        for owner,a,b in (('thigh','hip','knee'),('middle','knee','fold'),('distal','fold','ankle')):
            for offset in (-.08,.08):
                rod(side+'_'+owner+'_internal_cheek_'+str(offset),side+'_'+owner,
                    axes[a]+[0.,offset,0.],axes[b]+[0.,offset,0.],.066,.24)
    rod('pelvis_transverse_internal_bridge','pelvis',near['hip'],far['hip'],.11,.21)
    # The feet are cropped by the photograph/UI. Complete low support is
    # explicitly provisional instead of falsely described as copied detail.
    for side,axes in (('near',near),('far',far)):
        ankle=axes['ankle']
        mesh=tr.creation.box([.43,.28,.10]);mesh.apply_translation(ankle+[.04,0.,-.11])
        append_mesh(side+'_cropped_foot_envelope',side+'_foot',mesh,.46,
                    'unobserved_cropped_region_provisional')
    # Sleeve cores fill the armor connections; no long suspended hip tabs.
    for side,uv,n,d in (('near',[146,291],[1.,-.20,0.],.78),
                        ('far',[697,309],[1.,.15,0.],.47)):
        elbow=joint(side+'_elbow',side+'_forearm',uv,n,d,.095)
        shoulder_pixel=[153,147] if side=='near' else [665,174]
        wrist_pixel=[149,529] if side=='near' else [696,609]
        shoulder=lift(shoulder_pixel,np.array(n)/np.linalg.norm(n),d)-VIEW*.15
        wrist=lift(wrist_pixel,np.array(n)/np.linalg.norm(n),d)-VIEW*.15
        rod(side+'_upper_arm_core',side+'_upper_arm',shoulder,elbow,.102,.31)
        rod(side+'_forearm_core',side+'_forearm',elbow,wrist,.093,.31)
    # Connected closed body masses establish depth across the observed faces.
    # Roof and front are parts of one wedge, not floating camera-facing slabs.
    torso_vertices=np.vstack([p['vertices'] for p in PARTS
                              if p['name'] in ('crown_roof_wedge','main_front_tapered_face')])
    append_mesh('continuous_torso_wedge_core','torso',tr.convex.convex_hull(torso_vertices),.59,
                'inferred_depth_connecting_observed_wedge_faces')
    for side in ('near','far'):
        vertices=np.vstack([p['vertices'] for p in PARTS if p['body']==side+'_upper_arm'])
        append_mesh(side+'_continuous_upper_arm_body',side+'_upper_arm',
                    tr.convex.convex_hull(vertices),.58,'inferred_continuous_body_under_observed_armor')

    vertices=np.vstack([p['vertices'] for p in PARTS])
    minimum=vertices.min(0); maximum=vertices.max(0)
    scene={'revision':'reference_rebuild_r4','mode':'code_model_before_imagegen',
           'reference_file':'references/primary_user_reference.jpg',
           'reference_sha256':sha(REFERENCE),'source_sha256':sha(Path(__file__)),
           'reference_dimensions_px':[748,945],
           'coordinate_frame':{'forward':'+X','left':'+Y','up':'+Z',
                               'units':'relative layout units; absolute physical scale unconfirmed'},
           'camera':{'view_vector':VIEW.tolist(),'right_vector':RIGHT.tolist(),
                     'up_vector':UP.tolist(),'target':TARGET.tolist(),
                     'pixel_center':PIXEL_CENTER.tolist(),
                     'pixels_per_layout_unit':PIXELS_PER_LAYOUT_UNIT,
                     'projection':'orthographic single-view hypothesis'},
           'parts':PARTS,'observations':OBSERVATIONS,
           'joint_layout_hypothesis':{'near':{k:v.tolist() for k,v in near.items()},
                                      'far':{k:v.tolist() for k,v in far.items()}},
           'bounds':[minimum.tolist(),maximum.tolist()],
           'constraints':{'old_height_lock_released':True,'image_generation_performed':False,
                          'previous_R2_R3_shapes_used':False,'drilling_design_frozen':False},
           'unconfirmed':['camera intrinsics/depth','hidden posterior surfaces',
                          'occluded joint positions','cropped feet and sole',
                          'physical load path, actuator package and strength'],
           'reference_geometry_accepted':False,'physical_accepted':False}
    output=ROOT/'source'/'reference_scene.json'
    output.write_text(json.dumps(scene,indent=2)+'\n')
    exchange=tr.Scene()
    to_y_up=np.array([[1.,0.,0.,0.],[0.,0.,1.,0.],[0.,-1.,0.,0.],[0.,0.,0.,1.]])
    for p in PARTS:
        mesh=tr.Trimesh(p['vertices'],p['faces'],process=False)
        mesh.apply_transform(to_y_up)
        mesh.visual.vertex_colors=np.array([p['shade']*255]*3+[255],dtype=np.uint8)
        exchange.add_geometry(mesh,node_name=p['name'],geom_name=p['name'])
    (ROOT/'source'/'reference_geometry.glb').write_bytes(exchange.export(file_type='glb'))
    report={'scene_sha256':sha(output),'positive_watertight_part_count':len(PARTS),
            'observed_face_count':len(OBSERVATIONS),
            'max_observed_control_reprojection_error_px':max(o['max_control_reprojection_error_px'] for o in OBSERVATIONS),
            'metric_scope':'Control-polygon reprojection only, not reference-wide accuracy or recovered 3D truth.',
            'imagegen_used':False,'hidden_geometry_verified':False,'physics_verified':False}
    (ROOT/'source'/'geometry_check.json').write_text(json.dumps(report,indent=2)+'\n')
    print('REFERENCE_GEOMETRY',len(PARTS),'finite parts;',len(OBSERVATIONS),'observed contours',flush=True)


if __name__=='__main__':main()
