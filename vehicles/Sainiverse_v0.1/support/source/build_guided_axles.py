"""Author guided vertical axle carriers consistent with the existing joint path.

Barrels are custom packaging geometry, not a selected off-the-shelf suspension.
"""
from pathlib import Path
import copy,gzip,hashlib,json,math
import numpy as np
import trimesh as tm
from suspension_physics import ROOT,U
from export_assembly import export
OUT=ROOT/'candidates/r019_running_gear'

def box(center,size):
    m=tm.creation.box(size);m.apply_translation(center);return m
def cylinder(center,radius,length,axis=(0,0,1)):
    m=tm.creation.cylinder(radius=radius,height=length,sections=32)
    m.apply_transform(tm.geometry.align_vectors([0,0,1],axis));m.apply_translation(center);return m
def tube(center,outer,inner,length):
    return tm.boolean.difference([cylinder(center,outer,length),cylinder(center,inner,length+.02)],engine='manifold')
def main():
    source=ROOT/'candidates/r016_modular/train_containers_first/source/assembly.json.gz'
    a=json.loads(gzip.decompress(source.read_bytes()));original=copy.deepcopy(a);removed=[];modified=[];added=[]
    for p in list(a['parts']):
        if p['name'].endswith('_bogie_road_arm'):
            removed.append(p['name']);a['parts'].remove(p)
    serial=0
    def add(name,group,mesh,material='steel',wheel=None):
        nonlocal serial
        assert mesh.is_volume,name
        p=dict(name=f'r019_{serial:05d}_{name}',group=group,material=material,vertices=mesh.vertices.tolist(),faces=mesh.faces.tolist(),assembly='guided_axle_carrier',surface_paint=None,motion={'kind':'static'} if wheel is None else {'kind':'wheel_slide','index':wheel})
        if wheel is not None:
            y=mesh.center_mass[1]-a['groups'][group][1];p['physical_body']=group+f'_wheel_{"left" if y>0 else "right"}_{wheel}'
        a['parts'].append(p);added.append(p['name']);serial+=1
    # Only one representative wheel carrier is authored, then rigidly repeated.
    # Each of its three cylinders has a 260 mm outside / 200 mm bore envelope.
    # These are packaging inputs, not a qualified 700 mm stroke component.
    template=[]
    def part(name,m,mat='steel',moving=False):template.append((name,m,mat,moving))
    part('axle_crosshead',box([0,0,.20],[.90,.26,.16]),moving=True)
    for dx in [-.31,0.,.31]:
        part('cylinder_barrel',tube([dx,0,2.49],.13,.10,1.06),'edge')
        part('cylinder_top_cap',cylinder([dx,0,3.0325],.13,.025),'steel')
        part('cylinder_lower_gland',tube([dx,0,1.96],.13,.076,.055),'steel')
        for z in [2.08,2.95]:part('cylinder_frame_clamp',tube([dx,0,z],.145,.129,.06),'steel')
        for z in [2.76,2.91]:
            part('cylinder_port',cylinder([dx,.151,z],.029,.062,(0,1,0)),'silver')
        part('piston_rod',cylinder([dx,0,.82],.075,1.20),'silver',True)
        part('piston',cylinder([dx,0,1.40],.099,.06),'steel',True)
    # Fixed items use absolute source Z. Moving items use Z relative to axle.
    for group,pivot in a['groups'].items():
        if '_bogie_' not in group:continue
        x,y,_=pivot
        for side in [-1,1]:
            by=y+side*1.75
            for index,(wx,wz,wr) in enumerate(U['wheels_x_z_radius']):
                if index not in [1,2,3]:continue
                for name,mesh,mat,moving in template:
                    m=mesh.copy();m.apply_translation([x+wx,by,wz if moving else 0.]);add(name,group,m,mat,index if moving else None)
        # Existing bores/arched frame plates become open service slots around
        # the stationary barrels. Their clamping collars bridge the 1 mm gap.
        cutters=[cylinder([x+wx+dx,y+side*1.75,2.50],.131,1.4) for side in [-1,1] for wx,_,_ in U['wheels_x_z_radius'][1:4] for dx in [-.31,0.,.31]]
        tool=tm.util.concatenate(cutters)
        for p in a['parts']:
            if p['group']!=group:continue
            if p['name'].endswith('_track_inner_frame'):
                old=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
                new=tm.boolean.difference([old,tool],engine='manifold');assert new.is_volume and 0<new.volume<old.volume
                p['vertices']=new.vertices.tolist();p['faces']=new.faces.tolist();modified.append(dict(name=p['name'],removed_volume_m3=float(old.volume-new.volume)))
            elif p['name'].endswith('_wheel_axle'):
                center=np.mean(p['vertices'],axis=0);index=int(np.argmin(abs(np.array(U['wheels_x_z_radius'])[:,0]-(center[0]-x))))
                if index in [1,2,3]:
                    p['motion']={'kind':'wheel_slide','index':index};p['physical_body']=group+f'_wheel_{"left" if center[1]>y else "right"}_{index}'
    assert len(removed)==72 and len(modified)==48
    with gzip.open(OUT/'source/assembly.json.gz','wt') as f:json.dump(a,f,separators=(',',':'))
    registry=ROOT/'candidates/r016_modular/train_containers_first/source/payload_registry.json';(OUT/'source/payload_registry.json').write_bytes(registry.read_bytes())
    stats=export(a,OUT/'assets/leviathan003_guided_axles.glb');assert stats['render_meshes']==119
    report=dict(parts=len(a['parts']),removed_static_arms=removed,modified_frames=modified,added_parts=added,sliding_visual_parts=sum(p['motion']['kind']=='wheel_slide' for p in a['parts']),**stats,
        packaging=dict(wheel_travel_m=[-.35,.35],cylinders_per_axle=3,cylinder_outer_diameter_m=.26,bore_diameter_m=.20,rod_diameter_m=.15,custom_stroke_m=.70),
        scope='Authored guided axle packaging with named wheel-body translations. Hydraulic circuit, force/flow limits, fatigue and capacity are not qualified. Belt tensioner remains absent.',
        reference='Enerpac HCRL instruction L4247_a pp.8-10 documents 260 mm OD / 200 mm bore / 700 bar high-tonnage class; its listed 150-300 mm stroke lifting cylinders are not selected for this 700 mm dynamic suspension.',
        reference_url='https://literature.enerpac.com/pdf/L4247_a.pdf',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),source,ROOT/'source/export_assembly.py']})
    (OUT/'reports/guided_axle_model.json').write_text(json.dumps(report,indent=2)+'\n');print({k:report[k] for k in ['parts','render_meshes','triangles','sliding_visual_parts']})
if __name__=='__main__':main()
