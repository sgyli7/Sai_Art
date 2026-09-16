"""Build an editable whole-vehicle candidate, retaining the r014 baseline."""
from pathlib import Path
import gzip,json,hashlib,math
import numpy as np
import trimesh as tm
from articulation_geometry import build,GROUPS,poses,sleeve_clearance_tool

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'candidates/r015_articulation'
for folder in ['assets','source','reports']:(OUT/folder).mkdir(parents=True,exist_ok=True)
baseline=ROOT/'revisions/r014/source/assembly.json.gz'
a=json.loads(gzip.decompress(baseline.read_bytes()))
removed=[];modified=[];kept=[]
tool=sleeve_clearance_tool()
for p in a['parts']:
    base=p['name'].split('_',1)[1]
    if base in ['hitch_ring','coupling_link','coupling_crosshead','rear_drawbar']:
        removed.append(p['name']);continue
    if p['group']=='front' and base in ['front_deck','front_crossbeam']:
        mesh=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
        overlap=tm.boolean.intersection([mesh,tool],engine='manifold')
        if len(overlap.faces) and overlap.volume>1e-7:
            cut=tm.boolean.difference([mesh,tool],engine='manifold')
            assert cut.is_volume and 0<cut.volume<mesh.volume
            modified.append(dict(name=p['name'],removed_volume_m3=float(mesh.volume-cut.volume)))
            p['vertices']=cut.vertices.tolist();p['faces']=cut.faces.tolist()
    kept.append(p)
new=build()
for i,p in enumerate(new):
    m=p['mesh'];kept.append(dict(name=f'{11000+i:05d}_'+p['name'],group=p['group'],material=p['material'],
                                vertices=m.vertices.tolist(),faces=m.faces.tolist(),assembly='articulation_r015',
                                surface_paint=None,motion={'kind':'static'}))
a['parts']=kept;a['groups'].update(GROUPS)
with gzip.open(OUT/'source/assembly.json.gz','wt') as f:json.dump(a,f,separators=(',',':'))
colors=a['colors'];materials={k:tm.visual.material.PBRMaterial(name=k,baseColorFactor=[*bytes.fromhex(v),255],metallicFactor=.45 if k in ['steel','silver','track'] else .08,roughnessFactor=.5 if k!='glass' else .18) for k,v in colors.items()}
scene=tm.Scene();triangles=0
for group,pivot in a['groups'].items():
    transform=np.eye(4);transform[:3,3]=pivot;scene.graph.update(frame_to=group,matrix=transform)
    for material in colors:
        batch=[];uv=[]
        for p in kept:
            if p['group']!=group or p['material']!=material:continue
            mesh=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False)
            mesh=tm.graph.smooth_shade(mesh,angle=math.radians(40),facet_minarea=None)
            motion=p['motion'];value=[motion['index'],2] if motion['kind']=='wheel' else [motion['phase'],1] if motion['kind']=='belt' else [0,0]
            uv.append(np.tile(value,(len(mesh.vertices),1)));batch.append(mesh)
        if not batch:continue
        mesh=tm.util.concatenate(batch);mesh.apply_translation(-np.array(pivot));triangles+=len(mesh.faces)
        mesh.visual=tm.visual.TextureVisuals(uv=np.concatenate(uv),material=materials[material])
        scene.add_geometry(mesh,node_name=group+'__'+material,geom_name=group+'__'+material,parent_node_name=group)
def palette(tree):
    for m in tree['materials']:
        rgb=np.array(list(bytes.fromhex(colors[m['name']])))/255
        linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
        m['pbrMetallicRoughness']['baseColorFactor']=[*linear.tolist(),1.]
scene.export(OUT/'assets/leviathan003.glb',tree_postprocessor=palette,include_normals=True)
states={'retracted':(0,0,0,0),'extended':(4,0,0,0),'left45':(4,np.pi/4,0,0),
        'right45':(4,-np.pi/4,0,0),'terrain_pose':(4,np.pi/4,np.radians(8),np.radians(6))}
(OUT/'source/preview_poses.json').write_text(json.dumps({k:{g:t.tolist() for g,t in poses(*q).items()} for k,q in states.items()},indent=2))
report=dict(status='candidate geometry, not installed or trained',parts=len(kept),triangles=triangles,render_meshes=len(scene.geometry),
            removed_old_parts=removed,cut_fixed_tunnel_parts=modified,new_parts=len(new),
            source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [baseline,ROOT/'source/articulation_geometry.py',ROOT/'source/build_articulation_candidate.py',ROOT/'design/articulation_candidate.json']},
            scope='Offset-axis telescopic coupling, fixed sleeve tunnel, original r014 upper works. '
                  'No hoses, actuator cylinders, full structural rating or road dynamics validation yet.')
(OUT/'reports/model.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
