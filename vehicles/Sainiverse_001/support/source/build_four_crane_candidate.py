"""Four-corner transport packaging candidate from the authored r015 assembly.

Retracts the existing inner stage 1.7 m before mirroring the two cranes. This
does not claim a new working reach, lifting physics or a qualified load path.
"""
from pathlib import Path
import copy,gzip,hashlib,json,math
import numpy as np
import trimesh as tm

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'candidates/r016_modular'
BASE=ROOT/'candidates/r015_articulation/source/assembly.json.gz'

def main():
    a=json.loads(gzip.decompress(BASE.read_bytes()));parts=a['parts'];modified=[]
    retract_names={'crane_boom','crane_inner_top','crane_inner_bottom','crane_tip_cheek','hook_block','hook_block_pin','hook_warning_stripe','hook_block_sheave','hook_swivel','hook'}
    for p in parts:
        if p['assembly'] not in ['crane_0_upper','crane_1_upper']:continue
        name=p['name'].split('_',1)[1];v=np.array(p['vertices']);center=v.mean(0)
        shift=name in retract_names or name in ['crane_rope_sheave','crane_sheave_flange','crane_slide_pad'] and center[1]>-5
        if name=='winch_rope':
            if center[1]>-1:shift=True
            elif center[1]>-7:
                # Root fairlead remains fixed; tip endpoint follows telescoping
                # stage. Rebuild the actual round rope, not a sheared cylinder.
                start=np.array([center[0],-11+3.65,18.53]);end=np.array([center[0],-11+11.18-1.7,17.91])
                mesh=tm.creation.cylinder(.026,np.linalg.norm(end-start),sections=12)
                mesh.apply_transform(tm.geometry.align_vectors([0,0,1],end-start));mesh.apply_translation((start+end)/2)
                p['vertices']=mesh.vertices.tolist();p['faces']=mesh.faces.tolist();modified.append(p['name']);continue
        if shift:v[:,1]-=1.7;p['vertices']=v.tolist();modified.append(p['name'])
    copies=[];reflection=np.diag([1.,-1.,1.,1.])
    for p in parts:
        if not str(p['assembly']).startswith(('crane_0_','crane_1_')):continue
        q=copy.deepcopy(p);mesh=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False);mesh.apply_transform(reflection)
        q['vertices']=mesh.vertices.tolist();q['faces']=mesh.faces.tolist();q['name']=f'{12000+len(copies):05d}_'+p['name'].split('_',1)[1]
        q['assembly']=q['assembly'].replace('crane_0_','crane_2_').replace('crane_1_','crane_3_');copies.append(q)
    parts.extend(copies)
    # Put service ladders on the inward pedestal faces, away from perimeter
    # walkway rails. This remains symmetric and leaves the main girders intact.
    for p in parts:
        if str(p['assembly']).startswith('crane_') and p['name'].split('_',1)[1] in ['service_ladder_rail','service_ladder_rung']:
            v=np.array(p['vertices']);v[:,1]-=math.copysign(3.76,float(v[:,1].mean()));p['vertices']=v.tolist();modified.append(p['name'])
    walkway_cuts=[]
    for p in parts:
        if not p['name'].endswith('_rear_walkplate'):continue
        mesh=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False);before=mesh.volume
        for x in [-56.7,-27.3]:
            for y in [-11.,11.]:
                tool=tm.creation.box([3.24,3.44,1.]);tool.apply_translation([x,y,7.6])
                mesh=tm.boolean.difference([mesh,tool],engine='manifold')
        if abs(mesh.volume-before)>1e-6:
            walkway_cuts.append(dict(name=p['name'],removed_volume_m3=float(before-mesh.volume)))
            p['vertices']=mesh.vertices.tolist();p['faces']=mesh.faces.tolist();modified.append(p['name'])
    # Existing pedestal bottoms are 50 mm above the main deck. Add actual
    # bearing plates bridging that gap; no structural rating is inferred.
    for i,(x,y) in enumerate([(-56.7,-11.),(-27.3,-11.),(-56.7,11.),(-27.3,11.)]):
        mesh=tm.creation.box([3.2,3.4,.05]);mesh.apply_translation([x,y,7.475])
        parts.append(dict(name=f'{12400+i:05d}_crane_deck_bearing_plate',group='rear',material='steel',vertices=mesh.vertices.tolist(),faces=mesh.faces.tolist(),assembly=f'crane_{i}_fixed',surface_paint=None,motion={'kind':'static'}))
    for sub in ['source','assets','reports']:(OUT/sub).mkdir(parents=True,exist_ok=True)
    with gzip.open(OUT/'source/assembly.json.gz','wt') as f:json.dump(a,f,separators=(',',':'))
    # Exact mirrored vertex bounds and inter-crane triangle surface screen.
    managers={};crane_bounds={}
    for i in range(4):
        ps=[p for p in parts if str(p['assembly']).startswith(f'crane_{i}_')]
        manager=tm.collision.CollisionManager();v=[]
        for p in ps:
            manager.add_object(p['name'],tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False));v.extend(p['vertices'])
        managers[i]=manager;v=np.array(v);crane_bounds[i]=[v.min(0).tolist(),v.max(0).tolist()]
    collisions=[]
    for i in range(4):
        for j in range(i+1,4):
            hit,pairs=managers[i].in_collision_other(managers[j],return_names=True)
            if hit:collisions.extend(sorted(pairs))
    # Screen only newly added opposite-side cranes against unchanged structure;
    # existing load-bearing contacts inside each crane are intentional.
    remaining=tm.collision.CollisionManager()
    for p in parts:
        if str(p['assembly']).startswith('crane_') or p['surface_paint']:continue
        remaining.add_object(p['name'],tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False))
    other_hits=[]
    for i in range(4):
        hit,pairs=managers[i].in_collision_other(remaining,return_names=True)
        if hit:other_hits.extend(sorted(pairs))
    bearing_contacts=[];unexpected=[];lookup={p['name']:p for p in parts}
    for first,second in other_hits:
        plate=first if first.endswith('_crane_deck_bearing_plate') else second
        deck=second if plate==first else first
        if plate.endswith('_crane_deck_bearing_plate') and deck.endswith('_rear_deck'):
            pv=np.array(lookup[plate]['vertices']);dv=np.array(lookup[deck]['vertices'])
            gap=float(pv[:,2].min()-dv[:,2].max())
            if abs(gap)<1e-7:
                bearing_contacts.append(dict(plate=plate,deck=deck,vertical_gap_m=gap));continue
        unexpected.append([first,second])
    colors=a['colors'];scene=tm.Scene()
    materials={k:tm.visual.material.PBRMaterial(name=k,baseColorFactor=[*bytes.fromhex(v),255],metallicFactor=.45 if k in ['steel','silver','track'] else .08,roughnessFactor=.5 if k!='glass' else .18) for k,v in colors.items()}
    for group,pivot in a['groups'].items():
        tf=np.eye(4);tf[:3,3]=pivot;scene.graph.update(frame_to=group,matrix=tf)
        for material in colors:
            meshes=[];uv=[]
            for p in parts:
                if p['group']!=group or p['material']!=material:continue
                m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False);m=tm.graph.smooth_shade(m,angle=math.radians(40),facet_minarea=None)
                motion=p['motion'];value=[motion['index'],2] if motion['kind']=='wheel' else [motion['phase'],1] if motion['kind']=='belt' else [0,0]
                uv.append(np.tile(value,(len(m.vertices),1)));meshes.append(m)
            if not meshes:continue
            m=tm.util.concatenate(meshes);m.apply_translation(-np.array(pivot));m.visual=tm.visual.TextureVisuals(uv=np.concatenate(uv),material=materials[material])
            scene.add_geometry(m,node_name=group+'__'+material,geom_name=group+'__'+material,parent_node_name=group)
    def palette(tree):
        for m in tree['materials']:
            rgb=np.array(list(bytes.fromhex(colors[m['name']])))/255
            m['pbrMetallicRoughness']['baseColorFactor']=[*np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4).tolist(),1.]
    scene.export(OUT/'assets/leviathan003_four_cranes.glb',tree_postprocessor=palette,include_normals=True)
    report=dict(status='four-crane static transport packaging candidate; not installed',parts=len(parts),added_parts=len(copies)+4,modified_parts=modified,walkway_cuts=walkway_cuts,
                cranes=4,crane_bounds=crane_bounds,inter_crane_surface_intersections=collisions,unexpected_crane_to_structure_surface_intersections=unexpected,
                bearing_to_deck_contacts=bearing_contacts,neutral_packaging_passed=not collisions and not unexpected and len(bearing_contacts)==4,
                render_meshes=len(scene.geometry),triangles=sum(len(m.faces) for m in scene.geometry.values()),
                scope='Mirrored original corner pedestals, 1.7 m inner-stage retraction and corresponding rope endpoint adjustment. Discrete neutral surface intersections only, not containment, operating reach, deployment or load certification. Existing support/crane details remain provisional.',
                source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE,Path(__file__)]})
    (OUT/'reports/four_crane_packaging.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['modified_parts','source_sha256']},indent=2))

if __name__=='__main__':main()
