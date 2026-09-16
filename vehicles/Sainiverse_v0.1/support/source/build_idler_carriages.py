"""Author idler guides and compact twin recoil-cartridge packaging."""
import gzip,json,hashlib
from pathlib import Path
import numpy as np,trimesh as tm
from suspension_physics import ROOT
from export_assembly import export
from build_guided_axles import box,cylinder
OUT=ROOT/'candidates/r021_track_tension'
def tube_x(center,outer,inner,length):
    return tm.boolean.difference([cylinder(center,outer,length,(1,0,0)),cylinder(center,inner,length+.02,(1,0,0))],engine='manifold')
def main():
    source=ROOT/'candidates/r019_running_gear/source/assembly.json.gz';a=json.loads(gzip.decompress(source.read_bytes()));added=[];modified=[];serial=0
    def add(name,group,mesh,material='steel',side=None):
        nonlocal serial
        assert mesh.is_volume,name
        p=dict(name=f'r021_{serial:05d}_{name}',group=group,material=material,vertices=mesh.vertices.tolist(),faces=mesh.faces.tolist(),assembly='idler_carriage',surface_paint=None,motion={'kind':'static'} if side is None else {'kind':'wheel_slide','index':4})
        if side is not None:p['physical_body']=group+'_idler_'+side
        a['parts'].append(p);added.append(p['name']);serial+=1
    for group,pivot in a['groups'].items():
        if '_bogie_' not in group:continue
        px,py,_=pivot
        for p in a['parts']:
            if p['group']!=group:continue
            center=np.mean(p['vertices'],axis=0);side='left' if center[1]>py else 'right'
            if p['motion'].get('kind')=='wheel' and p['motion'].get('index')==4:p['physical_body']=group+'_idler_'+side
            if p['name'].endswith('_wheel_axle') and center[0]-px>4:
                p['motion']={'kind':'wheel_slide','index':4};p['physical_body']=group+'_idler_'+side
            if p['name'].endswith('_track_inner_frame'):
                old=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
                cutter=box([px+4.11,center[1],2.4],[1.18,.4,.48]);mesh=tm.boolean.difference([old,cutter],engine='manifold')
                assert mesh.is_volume and mesh.volume<old.volume;p['vertices']=mesh.vertices.tolist();p['faces']=mesh.faces.tolist();modified.append(p['name'])
        for sign,side in [(-1,'right'),(1,'left')]:
            by=py+sign*1.75;cy=py+sign*.7975
            add('idler_axle_carriage',group,box([px+4.15,by,2.4],[.48,.26,.44]),side=side)
            for z in [2.12,2.68]:add('idler_guide_rail',group,box([px+4.11,by,z],[1.32,.28,.08]))
            add('idler_axle_extension',group,cylinder([px+4.15,(by+cy)/2,2.4],.10,abs(by-cy),(0,1,0)),side=side)
            add('recoil_yoke',group,box([px+4.15,cy,2.4],[.16,.10,.72]),side=side)
            add('recoil_fixed_bracket',group,box([px+2.16,py+sign*.71,2.4],[.16,.18,.72]))
            for z in [2.16,2.64]:
                add('recoil_cartridge',group,tube_x([px+2.835,cy,z],.07,.055,1.29),'edge')
                add('recoil_end_cap',group,cylinder([px+2.1775,cy,z],.07,.025,(1,0,0)))
                add('recoil_gland',group,tube_x([px+3.46,cy,z],.07,.038,.035))
                add('recoil_rod',group,cylinder([px+3.55,cy,z],.035,1.20,(1,0,0)),'silver',side)
                add('recoil_piston',group,cylinder([px+2.96,cy,z],.054,.04,(1,0,0)),'steel',side)
    with gzip.open(OUT/'source/assembly.json.gz','wt') as f:json.dump(a,f,separators=(',',':'))
    stats=export(a,OUT/'assets/leviathan003_tensioned_tracks.glb')
    report=dict(parts=len(a['parts']),modified_frames=modified,added_parts=len(added),**stats,scope='24 guided idler axles and twin-cartridge recoil packaging. Existing frame plates have actual slide openings. Rods/pistons/yokes carry their named idler-body motion; wheel drums remain rotary. Cartridge hardware is packaging for an equivalent finite recoil model, not a selected pressure vessel, seal or rating. Belt path display still requires its physical-state binding.',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),source]})
    (OUT/'reports/idler_model.json').write_text(json.dumps(report,indent=2)+'\n');print({k:report[k] for k in ['parts','added_parts','render_meshes','triangles']})
if __name__=='__main__':main()
