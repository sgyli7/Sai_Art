"""Replace three C15 internal display hip boxes with a finite pitch carrier.

The remaining evaluated upperbody meshes and colours are rigidly relocated.
C15 remains an unaccepted approximation, not approved AA3 CAD geometry.
This carrier supplies a bearing interface; a hip drive is not installed.
"""
from pathlib import Path
import hashlib
import json,sys
import numpy as np
import trimesh as tr
import manifold3d as mf
from shapely.geometry import Point
from shapely.ops import unary_union
import build_candidate as b

O=Path(__file__).resolve().parent
U=Path('/home/ethan/Projects/Sai_Rotbots/experiments/gorilla_v0_1/appearance_c_round_fifteen')
HALF_SPACING=float(sys.argv[1]) if len(sys.argv)>1 else .39
REPLACED={'structure_waist_pedestal','left_structure_pelvis_crossmember','right_structure_pelvis_crossmember'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    leg=json.loads((O/'candidate_scene.json').read_text())
    upper=json.loads((U/'appearance_c_scene.json').read_text())
    evaluated=json.loads((U/'evaluated_mesh_manifest.json').read_text())
    assert evaluated['scene_sha256']==sha(U/'appearance_c_scene.json')
    glb=tr.load(U/'appearance_c.glb',force='scene')
    C=np.array([[1.,0,0],[0,0,-1.],[0,1.,0]])
    h=np.array(leg['stations_world_m']['hip'])
    shift=np.array([h[0],0,h[2]])-np.array([-.045,0,1.66])
    parts=[];excluded=[]
    for p in upper['parts']:
        if not (p['body']in ('torso','pelvis')or any(t in p['body']for t in ('arm','palm','finger','thumb'))):continue
        if p['name']in REPLACED:
            excluded.append({'name':p['name'],'role':p['role'],'body':p['body']})
            assert p['body']=='pelvis' and p['role']=='primary_structure_candidate'
            continue
        node,gn=glb.graph[p['name']];m=glb.geometry[gn].copy();m.apply_transform(node);m.merge_vertices(digits_vertex=9)
        if not m.is_watertight or not m.is_winding_consistent or m.volume<=0:raise ValueError(p['name'])
        parts.append({'name':'upper_'+p['name'],'body':'upper_'+p['body'],
                      'source_group':'upperbody_approximation','geometry_origin':'unchanged_C15_evaluated_triangles',
                      'role':p['role'],'rgba':p['rgba'],'vertices_world_m':(m.vertices@C.T+shift).tolist(),
                      'faces':m.faces.tolist(),'density_kg_m3':None,
                      'mass_status':'Unaccepted presentation geometry; physical wall/density unassigned.'})
    assert {p['name']for p in excluded}==REPLACED
    anchor=np.array([h[0]-.09,0,h[2]+.23])
    carrier=b.beam(anchor+[0,-HALF_SPACING-.084,0],anchor+[0,HALF_SPACING+.084,0],.140,.180,.016)
    carrier+=b.beam(anchor,np.array([h[0],0,h[2]+.43]),.180,.200,.020)
    joint_interfaces=[]
    for sign,side in ((1,'left'),(-1,'right')):
        hip=np.array([h[0],sign*HALF_SPACING,h[2]])
        root=np.array([anchor[0],hip[1],anchor[2]])
        profile=unary_union([Point(*hip[[0,2]]).buffer(.085),Point(*root[[0,2]]).buffer(.070)]).convex_hull
        profile=profile.difference(Point(*hip[[0,2]]).buffer(.0500,quad_segs=16))
        for off in (-.060,.060):carrier+=b.extrude(profile,hip[1]+off,.024)
        carrier+=b.cylinder(hip,.0501,.258,.030)
        joint_interfaces.append({'id':side+'_hip_pitch','parent':'upper_pelvis','child':side+'_thigh',
                                 'center_m':hip.tolist(),'axis':[0,1,0],
                                 'shaft_radius_m':.0501,'thigh_bearing_inner_radius_m':.0505,
                                 'radial_probe_gap_m':.0004,'drive_installed':False})
    if carrier.status()!=mf.Error.NoError or carrier.volume()<=0:raise ValueError('invalid hip carrier')
    positive=sum(p.volume()>1e-10 for p in carrier.decompose())
    if positive!=1:raise ValueError(('disconnected carrier steel',positive))
    mm=carrier.to_mesh64()
    parts.append({'name':'upper_proposed_hip_pitch_carrier','body':'upper_pelvis',
                  'source_group':'upperbody_approximation','geometry_origin':'new_native_hip_interface',
                  'role':'hip_interface_candidate','rgba':[.26,.30,.33,1],
                  'vertices_world_m':np.array(mm.vert_properties[:,:3]).tolist(),
                  'faces':np.array(mm.tri_verts).tolist(),'density_kg_m3':7850,
                  'mass_status':'Finite steel density integral only. Grade, welds, retention and fatigue unqualified.'})
    out={'revision':'C15_upper_fit_with_new_finite_hip_interface_01','parts':parts,
         'hip_half_spacing_m':HALF_SPACING,'hip_interfaces':joint_interfaces,
         'source_hashes':{'leg_frame':sha(O/'candidate_scene.json'),'C15_scene':sha(U/'appearance_c_scene.json'),
                          'C15_evaluated_glb':sha(U/'appearance_c.glb'),'C15_evaluated_manifest':sha(U/'evaluated_mesh_manifest.json'),
                          'builder':sha(Path(__file__)),'geometry_helper':sha(Path(b.__file__))},
         'preserved_upperbody_scale':True,'upperbody_translation_m':shift.tolist(),
         'replaced_internal_display_parts':excluded,'carrier_density_integral_mass_kg':carrier.volume()*7850,
         'physical_accepted':False,'appearance_accepted':False,
         'limits':['C15 upperbody is an unaccepted approximation; AA3 artwork unchanged.',
                   'Three legacy internal display boxes replaced by explicit bore/shaft/clevis geometry.',
                   'No installed hip drive, real upperbody mass distribution or stress/fatigue proof.',
                   'C15 presentation volumes are conservative fit obstacles, not actual hollow hardware.']}
    (O/'upper_fit_interface_scene.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print('UPPER_INTERFACE',len(parts),'parts','carrier_mass_kg',out['carrier_density_integral_mass_kg'],flush=True)

if __name__=='__main__':main()
