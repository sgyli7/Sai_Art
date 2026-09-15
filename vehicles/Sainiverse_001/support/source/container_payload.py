"""Reusable sealed transport-container payload geometry and gross-mass registry.

Nominal external dimensions follow the existing project and Triton's published
20 ft standard fleet table. Corrugation, corner and lock geometry is simplified;
no manufacturer drawing or ISO load certification is claimed.
"""
import itertools
import numpy as np
import trimesh as tm

SIZE=np.array([6.058,2.438,2.591])
BAYS=[-10.887,-3.629,3.629,10.887]
ROWS=[-6.470,-3.882,-1.294,1.294,3.882,6.470]
DECK=7.45
SOCKET=.12
COLORS={'cargo_teal':'476970','cargo_sand':'A9A391','cargo_rust':'8B5547'}
SOURCE='https://tools.tritoncontainer.com/tritoncontainer/unitSpecs/fleet'

def box(center,size):
    m=tm.creation.box(size);m.apply_translation(center);return m
def cylinder(center,r,length,axis=(0,0,1),segments=16):
    m=tm.creation.cylinder(r,length,sections=segments);m.apply_transform(tm.geometry.align_vectors([0,0,1],axis));m.apply_translation(center);return m
def corrugated_side(side):
    # Thin, closed corrugated sheet entirely inside the nominal container gauge.
    length=SIZE[0]-.34;z0=-SIZE[2]/2+.17;z1=SIZE[2]/2-.17
    n=round(length/.28);xs=np.linspace(-length/2,length/2,n*4+1)
    depth=np.array([0,.018,.018,0]*(n)+[0]);center_y=side*(SIZE[1]/2-.033)
    vertices=[]
    for dz in [z0,z1]:
        for skin in [-.002,.002]:
            vertices.extend([[x,center_y+side*d+skin,dz] for x,d in zip(xs,depth)])
    N=len(xs);faces=[]
    def quad(a,b,c,d):faces.extend([[a,b,c],[a,c,d]])
    for i in range(N-1):
        quad(i,i+1,2*N+i+1,2*N+i)
        quad(N+i,3*N+i,3*N+i+1,N+i+1)
        quad(i,N+i,N+i+1,i+1);quad(2*N+i,2*N+i+1,3*N+i+1,3*N+i)
    quad(0,2*N,3*N,N);quad(N-1,2*N-1,4*N-1,3*N-1)
    m=tm.Trimesh(vertices=vertices,faces=faces,process=True);m.fix_normals();assert m.is_volume;return m

def template():
    parts=[]
    def add(name,mesh,material='cargo'):
        assert mesh.is_volume,name
        parts.append(dict(name=name,mesh=mesh,material=material))
    sx,sy,sz=SIZE
    add('floor',box([0,0,-sz/2+.11],[sx-.30,sy-.30,.08]),'edge')
    add('roof',box([0,0,sz/2-.04],[sx-.28,sy-.28,.012]))
    for side in [-1,1]:
        add(f'side_{side}',corrugated_side(side))
        for zsign in [-1,1]:
            add(f'longitudinal_rail_{side}_{zsign}',box([0,side*(sy/2-.055),zsign*(sz/2-.065)],[sx-.18,.075,.085]),'edge')
            add(f'end_rail_{side}_{zsign}',box([side*(sx/2-.055),0,zsign*(sz/2-.065)],[.075,sy-.18,.085]),'edge')
        for ysign in [-1,1]:
            add(f'corner_post_{side}_{ysign}',box([side*(sx/2-.06),ysign*(sy/2-.06),0],[.09,.09,sz-.20]),'edge')
    add('closed_front_panel',box([-sx/2+.045,0,0],[.015,sy-.26,sz-.28]))
    for side in [-1,1]:
        add(f'door_leaf_{side}',box([sx/2-.055,side*sy*.235,0],[.025,sy*.46,sz-.25]))
        for offset in [-.32,.32]:
            y=side*sy*.235+offset
            add(f'door_lockrod_{side}_{offset}',cylinder([sx/2-.017,y,0],.012,sz-.35),'steel')
            for zsign in [-1,1]:add(f'door_cam_{side}_{offset}_{zsign}',box([sx/2-.02,y,zsign*(sz/2-.18)],[.028,.08,.05]),'steel')
        for z in [-.82,0,.82]:add(f'door_hinge_{side}_{z}',cylinder([sx/2-.035,side*(sy/2-.09),z],.018,.11),'steel')
    for x in np.linspace(-sx/2+.22,sx/2-.22,14):add(f'roof_rib_{x:.3f}',box([x,0,sz/2-.024],[.05,sy-.27,.018]))
    cast=tm.creation.box([.18,.18,.16]);hole=tm.creation.cylinder(.045,.20,sections=20);hole.apply_scale([1.25,1.,1.])
    cast=tm.boolean.difference([cast,hole],engine='manifold');assert cast.is_volume
    for ex,ey,ez in itertools.product([-1,1],repeat=3):
        m=cast.copy();m.apply_translation([ex*(sx/2-.09),ey*(sy/2-.09),ez*(sz/2-.08)])
        add(f'corner_casting_{ex}_{ey}_{ez}',m,'steel')
    all_vertices=np.concatenate([p['mesh'].vertices for p in parts]);assert np.all(all_vertices.min(0)>=-SIZE/2-1e-8) and np.all(all_vertices.max(0)<=SIZE/2+1e-8)
    return parts

def build(center_x=-84.):
    proto=template();parts=[];registry=[]
    for bay,x in enumerate(BAYS):
        for row,y in enumerate(ROWS):
            for tier in range(3):
                ident=f'container_b{bay}_r{row}_t{tier}'
                center=np.array([center_x+x,y,DECK+SOCKET+SIZE[2]*(tier+.5)])
                material=list(COLORS)[(bay+row//2)%3]
                registry.append(dict(id=ident,profile='20ft_standard_sealed',center_source_m=center.tolist(),size_m=SIZE.tolist(),gross_mass_kg=20000. if tier==0 else 8000.,tier=tier,bay=bay,row=row,restraint_state='locked_transport'))
                for p in proto:
                    m=p['mesh'].copy();m.apply_translation(center)
                    parts.append(dict(name=ident+'_'+p['name'],mesh=m,material=material if p['material']=='cargo' else p['material'],assembly=ident))
            for ex,ey in itertools.product([-1,1],repeat=2):
                px=center_x+x+ex*(SIZE[0]/2-.09);py=y+ey*(SIZE[1]/2-.09)
                parts.append(dict(name=f'socket_b{bay}_r{row}_{ex}_{ey}',mesh=box([px,py,DECK+SOCKET/2],[.22,.22,SOCKET]),material='steel',assembly='cargo_sockets'))
                for tier in range(3):
                    z=DECK+SOCKET+SIZE[2]*tier
                    parts.append(dict(name=f'lock_b{bay}_r{row}_t{tier}_{ex}_{ey}',mesh=cylinder([px,py,z],.03,.12,segments=12),material='yellow',assembly='cargo_locks'))
    return parts,registry

def mass_properties(registry,base_mass=3300000.,base_center=(0,0,10),base_inertia=None):
    """Aggregate locked cargo exactly; base mass/inertia remain provisional."""
    center_x=float(np.mean([p['center_source_m'][0] for p in registry]));base_center=np.array(base_center,dtype=float);base_center[0]=center_x
    masses=np.array([base_mass]+[p['gross_mass_kg'] for p in registry]);centers=np.array([base_center]+[p['center_source_m'] for p in registry]);com=(masses[:,None]*centers).sum(0)/masses.sum()
    inertia=np.array(base_inertia,dtype=float) if base_inertia is not None else np.ones(3)
    delta=base_center-com;inertia+=base_mass*(delta@delta-delta**2)
    for p in registry:
        m=p['gross_mass_kg'];sx,sy,sz=p['size_m'];delta=np.array(p['center_source_m'])-com
        inertia+=m*np.array([sy*sy+sz*sz,sx*sx+sz*sz,sx*sx+sy*sy])/12+m*(delta@delta-delta**2)
    return dict(base_hull_mass_kg=base_mass,locked_container_gross_mass_kg=float(masses[1:].sum()),combined_hull_mass_kg=float(masses.sum()),center_of_mass_source_m=com.tolist(),inertia_diagonal_kg_m2=inertia.tolist(),
                scope='72 sealed container gross masses and box-distribution inertia aggregated for locked transport. Bare hull mass/inertia are declared simulation assumptions, not CAD-derived or rated. Unlock/lifting requires separate bodies and recomputation.')
