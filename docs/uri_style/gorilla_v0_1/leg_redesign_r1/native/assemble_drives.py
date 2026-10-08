"""Custom finite cylinder/mount candidates; no OEM or hardware approval claim."""
from pathlib import Path
import json,hashlib,copy,sys
import numpy as np
import trimesh as tr
import manifold3d as mf
from shapely.geometry import Point
from shapely.ops import unary_union
import build_candidate as b

O=Path(__file__).resolve().parent;SP=O/'candidate_scene.json';s=json.loads(SP.read_text())
parts=copy.deepcopy(s['parts']);meta=[]
def arrays(m):
    q=m.to_mesh64();return np.array(q.vert_properties[:,:3]).tolist(),np.array(q.tri_verts).tolist()
def add(name,body,m,role,**kw):
    if m.status()!=mf.Error.NoError or m.volume()<=0:raise ValueError((name,m.status(),m.volume()))
    v,f=arrays(m);parts.append({'name':name,'body':body,'vertices_world_m':v,'faces':f,'role':role,
        'rgba':[.32,.36,.39,1] if role=='mount' else [.47,.51,.54,1],'density_kg_m3':7850,**kw})
def axis_solid(a,direction,start,end,ro,ri=0):
    T=tr.geometry.align_vectors([0,0,1],direction);T[:3,3]=a+direction*(start+end)/2
    m=mf.Manifold.cylinder(end-start,ro,ro,48,True)
    if ri:m=m-mf.Manifold.cylinder(end-start+.002,ri,ri,48,True)
    return m.transform(T[:3,:4].copy())
def nearest_anchor(body,p):
    if body=='shoe':return np.array([np.clip(p[0],.08,.26),.5,.070]),np.array([1.,0,0])
    i=('thigh','middle','distal').index(body);a=np.array(s['stations_world_m'][s['serial_links'][i][0]]);z=np.array(s['stations_world_m'][s['serial_links'][i][1]])
    u=(z-a)/np.linalg.norm(z-a);t=np.clip((p-a)@u,.245,np.linalg.norm(z-a)-.245)
    return a+u*t,u
def mount(name,owner,p,anchor,away,opt):
    if opt.get('mount_style')=='side_integral_gussets':
        # Support the fork from the protected mid-span of the parent/child
        # load frame. The previous remote crossmember behind each eye swept
        # through the next joint's cylinder. Wider ears straddle the actual
        # barrel, and an 80mm pin carries the larger clevis span.
        radius=opt['mount_eye_outer_radius_m'];pin=opt['mount_pin_radius_m']
        off=opt['mount_ear_offset_m'];thick=opt['mount_ear_thickness_m']
        q=p+away*.13
        poly=unary_union([Point(*p[[0,2]]).buffer(radius),
                          Point(*anchor[[0,2]]).buffer(.045),
                          Point(*q[[0,2]]).buffer(.040)]).convex_hull
        poly=poly.difference(Point(*p[[0,2]]).buffer(pin-.0001,quad_segs=16))
        pieces=[b.extrude(poly,p[1]+sign*off,thick)for sign in (-1,1)]
        # The frame crossmember stops at the INNER cheek, before the barrel
        # band. A local bridge behind the eye closes only this fork, instead
        # of drawing a full-width transverse member through the cylinder.
        span=abs(p[1]-.5)-off+thick/2
        pieces.append(b.beam(anchor+[0,-span,0],anchor+[0,span,0],.060,.090,.012))
        pieces.append(b.beam(q+[0,-off-thick/2,0],q+[0,off+thick/2,0],.040,.050,.009))
        pieces.append(b.cylinder(p,pin,2*off+thick+.018,0))
        eye_half=opt['drive_eye_width_m']/2
        for sign in (-1,1):
            start=eye_half+.001;end=off-thick/2-.001
            centre=p+[0,sign*(start+end)/2,0]
            pieces.append(b.cylinder(centre,pin+.012,end-start,pin-.0001))
        add(name,owner,b.union(pieces),'mount',construction='Integral side gussets tied at actual frame mid-span, bored clevis, pressed 80mm pin and finite spacers. Grade/retention/strength unqualified.')
        return
    if opt.get('architecture')=='one central ankle cylinder; twin knee/fold cylinders':
        # The central ankle drive mounts directly to paired continuous side
        # gussets. Their Y planes lie outside the barrel, and their lower ends
        # overlap the actual calf cheeks / shared toe tray. No cantilevered
        # transverse box passes through the rotating cylinder eye.
        radius=opt['mount_eye_outer_radius_m'];pin=opt['mount_pin_radius_m']
        off=opt['mount_ear_offset_m'];thick=opt['mount_ear_thickness_m']
        root_radius=.030 if owner=='shoe' else .080
        profile=unary_union([Point(*p[[0,2]]).buffer(radius),
                             Point(*anchor[[0,2]]).buffer(root_radius)]).convex_hull
        profile=profile.difference(Point(*p[[0,2]]).buffer(pin-.0001,quad_segs=16))
        fork=b.union([b.extrude(profile,p[1]+sign*off,thick)for sign in (-1,1)])
        fork=fork+b.cylinder(p,pin,2*off+thick+.018,0)
        add(name,owner,fork,'mount',construction='Direct paired integral gussets to actual calf cheeks or toe tray, pressed pin. Grade/retention/strength unqualified.')
        return
    if name.endswith('_fixed_fork')and 'fixed_fork_away_vector'in opt:
        away=np.array(opt['fixed_fork_away_vector'],dtype=float)
        away/=np.linalg.norm(away)
    # Short ears turn AWAY from the rotating barrel/rod. A central box and
    # real transverse member carry the load back to the parent frame instead
    # of drawing a long fork plate through the cylinder wall.
    if name.startswith('ankle_') and name.endswith('_fixed_fork'):
        # The shorter continuous calf must not send its drive mount up into
        # the fold joint. Put the bracket behind/down, perpendicular to the
        # initial cylinder axis, with real finite ears and a transverse beam.
        away=np.array([-away[2],0,away[0]])
        if away[2]>0:away=-away
    reach=.13
    if opt.get('architecture')=='one central ankle cylinder; twin knee/fold cylinders' and name.endswith('_moving_fork'):
        # Foot-side fork lies over the toe tray, rather than following the
        # oblique cylinder axis down through the ground. This is real source
        # geometry, not a floor contact exclusion or a render adjustment.
        away=np.array([1.,0,0]);reach=.10
    q=p+away*reach
    ear_radius=opt.get('mount_eye_outer_radius_m',.05)
    pin_radius=opt.get('mount_pin_radius_m',.0201)
    ear_offset=opt.get('mount_ear_offset_m',.045)
    ear_thickness=opt.get('mount_ear_thickness_m',.016)
    # Pin is fixed in the fork's candidate interference seat. The separate
    # moving eye uses +0.4mm running clearance. No grade/tolerance approval.
    hole_radius=pin_radius-.0001
    poly=unary_union([Point(*q[[0,2]]).buffer(ear_radius),Point(*p[[0,2]]).buffer(ear_radius)]).convex_hull
    poly=poly.difference(Point(*p[[0,2]]).buffer(hole_radius,quad_segs=16))
    fork=b.union([b.extrude(poly,p[1]+v*ear_offset,ear_thickness) for v in (-1,1)])
    # Actual transverse box joins frame/pressure tray to the fork pair.
    span=abs(p[1]-.5)+max(.055,ear_offset+ear_thickness/2+.002)
    q[1]=.5
    cross=b.beam(q+[0,-span,0],q+[0,span,0],.065,.065,.010)
    back=b.beam(anchor,q,.160,.100,.015) if owner=='shoe' else b.beam(anchor,q,.120,.140,.012)
    # This crossmember is SHARED per owner and anchor, but harmless exact
    # unions remove duplicates before mass/inertia evaluation.
    pin_length=max(.120,2*ear_offset+ear_thickness+.018)
    fork=fork+cross+back+b.cylinder(p,pin_radius,pin_length,0)
    if opt.get('add_axial_spacers'):
        for sign in (-1,1):
            start=opt['drive_eye_width_m']/2+.001;end=ear_offset-ear_thickness/2-.001
            centre=p+[0,sign*(start+end)/2,0]
            fork=fork+b.cylinder(centre,pin_radius+.012,end-start,pin_radius-.0001)
    add(name,owner,fork,'mount',construction='Finite candidate fork with bored eyes and explicit pressed pin; weld/casting/retention NOT qualified')

def build(options):
    global parts,meta
    parts=copy.deepcopy(s['parts']);meta=[]
    for j,opt in zip(s['joints'],options):
        if opt is None:continue
        A=np.array(opt['a_world_m']);B=np.array(opt['b_world_m']);direction=(B-A)/np.linalg.norm(B-A)
        L0=np.linalg.norm(B-A);minimum=opt['eye_length_min_m'];bl=opt['barrel_length_m'];ro=opt['outside_diameter_m']/2;ri=opt['bore_m']/2;rr=opt['rod_m']/2
        for index,off in enumerate(opt['lateral_offsets_m']):
            a=A+[0,off,0];bb=B+[0,off,0];name=f"{j['id']}_{index}";barrel_owner=name+'_barrel';rod_owner=name+'_rod'
            aa,u=nearest_anchor(j['parent'],a);cc,v=nearest_anchor(j['child'],bb)
            mount(name+'_fixed_fork',j['parent'],a,aa,-direction,opt);mount(name+'_moving_fork',j['child'],bb,cc,direction,opt)
            pin_radius=opt.get('mount_pin_radius_m',.0201)
            eye_radius=opt.get('drive_eye_outer_radius_m',.05)
            eye_width=opt.get('drive_eye_width_m',.032)
            hole_radius=pin_radius+.0004
            eyeA=b.cylinder(a,eye_radius,eye_width,hole_radius)
            neck=opt.get('barrel_neck_start_m',.070)
            wall=axis_solid(a,direction,neck,neck+bl,ro,ri)
            cap=axis_solid(a,direction,neck,neck+.020,ro)
            gland=axis_solid(a,direction,neck+bl-.025,neck+bl,ro,rr+.0005)
            connector=axis_solid(a,direction,.02,neck+.020,opt.get('barrel_eye_connector_radius_m',.020))
            barrel=b.union([eyeA,wall,cap,gland,connector])-b.cylinder(a,hole_radius,max(.15,eye_width+.012),0)
            add(name+'_cylinder',barrel_owner,barrel,'custom_cylinder_barrel',bore_m=2*ri,wall_m=ro-ri,
                scope='Finite self-designed geometry; seals/ports/fasteners/retention/pressure fatigue not qualified')
            rodlength=minimum-(.125+neck-.070)
            eyeB=b.cylinder(bb,eye_radius,eye_width,hole_radius)
            shaft=axis_solid(bb,-direction,.027,rodlength,rr)
            piston=axis_solid(bb,-direction,rodlength-.015,rodlength+.015,ri-.0005)
            moving=b.union([eyeB,shaft,piston])-b.cylinder(bb,hole_radius,max(.15,eye_width+.012),0)
            add(name+'_piston_rod',rod_owner,moving,'custom_cylinder_piston_rod',rod_diameter_m=2*rr)
            meta.append({'id':name,'joint':j['id'],'parent':j['parent'],'child':j['child'],
              'barrel_body':barrel_owner,'rod_body':rod_owner,'A_neutral_world_m':a.tolist(),'B_neutral_world_m':bb.tolist(),
              'neutral_eye_length_m':L0,'eye_length_limits_m':[minimum-.008,opt['eye_length_max_m']+.008],
              'bore_m':2*ri,'rod_m':2*rr,'pressure_assumption_Pa':30e6,'efficiency_assumption':.85,
              'mount_pin_radius_m':pin_radius,'radial_probe_clearance_m':.0004,
              'eye_width_m':eye_width,'eye_outer_radius_m':eye_radius,
              'mount_ear_offset_m':opt.get('mount_ear_offset_m',.045),
              'mount_ear_thickness_m':opt.get('mount_ear_thickness_m',.016),
              'barrel_neck_start_m':neck,
              'construction_status':'custom proposal NOT selected OEM or verified pressure part'})
    out=copy.deepcopy(s)
    out['parts']=parts;out['drivers']=meta
    out['parent_geometry_sha256']=hashlib.sha256(SP.read_bytes()).hexdigest()
    out['revision']='native_leg_probe_02_with_custom_drives_and_mounts'
    out['assembly_builder_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out['geometry_helper_sha256']=hashlib.sha256(Path(b.__file__).read_bytes()).hexdigest()
    out['status']='assembled_finite_candidate_before_material_collision_and_dynamic_rejection'
    out['physical_accepted']=False
    return out

if __name__=='__main__':
    choice_path=O/(sys.argv[1] if len(sys.argv)>1 else 'drive_set_selection.json')
    choice=json.loads(choice_path.read_text())
    assert choice['scene_sha256']==hashlib.sha256(SP.read_bytes()).hexdigest()
    assert choice['selection']
    out=build(choice['selection']['options'])
    out['drive_set_sha256']=hashlib.sha256(choice_path.read_bytes()).hexdigest()
    out['drive_selection_file']=choice_path.name
    if 'whole_fit_hip_half_spacing_m'in choice:
        out['whole_fit_hip_half_spacing_m']=choice['whole_fit_hip_half_spacing_m']
        out['revision']='native_leg_probe_04_compact_drives_short_crouch'
        out['architecture']='Twin side knee/fold drives and one central ankle drive with integral foot/calf gussets.'
    (O/'assembled_scene.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print('ASSEMBLED',len(out['parts']),'parts',len(out['drivers']),'custom cylinders',flush=True)
