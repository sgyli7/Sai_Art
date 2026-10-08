"""Custom finite cylinder/mount candidates; no OEM or hardware approval claim."""
from pathlib import Path
import json,hashlib,copy
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
def mount(name,owner,p,anchor,away):
    # Short ears turn AWAY from the rotating barrel/rod. A central box and
    # real transverse member carry the load back to the parent frame instead
    # of drawing a long fork plate through the cylinder wall.
    if name.startswith('ankle_') and name.endswith('_fixed_fork'):
        # The shorter continuous calf must not send its drive mount up into
        # the fold joint. Put the bracket behind/down, perpendicular to the
        # initial cylinder axis, with real finite ears and a transverse beam.
        away=np.array([-away[2],0,away[0]])
        if away[2]>0:away=-away
    q=p+away*.13
    poly=unary_union([Point(*q[[0,2]]).buffer(.05),Point(*p[[0,2]]).buffer(.05)]).convex_hull
    poly=poly.difference(Point(*p[[0,2]]).buffer(.020,quad_segs=16))
    fork=b.union([b.extrude(poly,p[1]+v*.045,.016) for v in (-1,1)])
    # Actual transverse box joins frame/pressure tray to the fork pair.
    span=abs(p[1]-.5)+.055
    q[1]=.5
    cross=b.beam(q+[0,-span,0],q+[0,span,0],.065,.065,.010)
    back=b.beam(anchor,q,.160,.100,.015) if owner=='shoe' else b.beam(anchor,q,.120,.140,.012)
    # This crossmember is SHARED per owner and anchor, but harmless exact
    # unions remove duplicates before mass/inertia evaluation.
    fork=fork+cross+back+b.cylinder(p,.0201,.120,0)
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
            mount(name+'_fixed_fork',j['parent'],a,aa,-direction);mount(name+'_moving_fork',j['child'],bb,cc,direction)
            eyeA=b.cylinder(a,.05,.032,.0205)
            wall=axis_solid(a,direction,.07,.07+bl,ro,ri)
            cap=axis_solid(a,direction,.07,.09,ro)
            gland=axis_solid(a,direction,.07+bl-.025,.07+bl,ro,rr+.0005)
            connector=axis_solid(a,direction,.02,.09,.020)
            barrel=b.union([eyeA,wall,cap,gland,connector])-b.cylinder(a,.0205,.15,0)
            add(name+'_cylinder',barrel_owner,barrel,'custom_cylinder_barrel',bore_m=2*ri,wall_m=ro-ri,
                scope='Finite self-designed geometry; seals/ports/fasteners/retention/pressure fatigue not qualified')
            rodlength=minimum-.125
            eyeB=b.cylinder(bb,.05,.032,.0205)
            shaft=axis_solid(bb,-direction,.027,rodlength,rr)
            piston=axis_solid(bb,-direction,rodlength-.015,rodlength+.015,ri-.0005)
            moving=b.union([eyeB,shaft,piston])-b.cylinder(bb,.0205,.15,0)
            add(name+'_piston_rod',rod_owner,moving,'custom_cylinder_piston_rod',rod_diameter_m=2*rr)
            meta.append({'id':name,'joint':j['id'],'parent':j['parent'],'child':j['child'],
              'barrel_body':barrel_owner,'rod_body':rod_owner,'A_neutral_world_m':a.tolist(),'B_neutral_world_m':bb.tolist(),
              'neutral_eye_length_m':L0,'eye_length_limits_m':[minimum-.008,opt['eye_length_max_m']+.008],
              'bore_m':2*ri,'rod_m':2*rr,'pressure_assumption_Pa':30e6,'efficiency_assumption':.85,
              'mount_pin_radius_m':.0201,'radial_probe_clearance_m':.0004,
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
    choice=json.loads((O/'drive_set_selection.json').read_text())
    assert choice['scene_sha256']==hashlib.sha256(SP.read_bytes()).hexdigest()
    assert choice['selection']
    out=build(choice['selection']['options'])
    out['drive_set_sha256']=hashlib.sha256((O/'drive_set_selection.json').read_bytes()).hexdigest()
    (O/'assembled_scene.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print('ASSEMBLED',len(out['parts']),'parts',len(out['drivers']),'custom cylinders',flush=True)
