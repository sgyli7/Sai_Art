"""Export named source-Z-up parts, batching only matching body/material pairs."""
import math
import numpy as np
import trimesh as tm

def export(a,path):
    colors=a['colors'];scene=tm.Scene()
    materials={k:tm.visual.material.PBRMaterial(name=k,baseColorFactor=[*bytes.fromhex(v),255],metallicFactor=.45 if k in ['steel','silver','track'] else .08,roughnessFactor=.5 if k!='glass' else .18) for k,v in colors.items()}
    grouped={}
    for p in a['parts']:grouped.setdefault((p['group'],p['material']),[]).append(p)
    for group,pivot in a['groups'].items():
        transform=np.eye(4);transform[:3,3]=pivot;scene.graph.update(frame_to=group,matrix=transform)
        for material in colors:
            parts=grouped.get((group,material),[])
            if not parts:continue
            meshes=[];uv=[]
            for p in parts:
                m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False);m=tm.graph.smooth_shade(m,angle=math.radians(40),facet_minarea=None)
                motion=p['motion'];value=[motion['index'],3] if motion['kind']=='wheel_slide' else [motion['index'],2] if motion['kind']=='wheel' else [motion['phase'],1] if motion['kind']=='belt' else [0,0]
                uv.append(np.tile(value,(len(m.vertices),1)));meshes.append(m)
            m=tm.util.concatenate(meshes);m.apply_translation(-np.array(pivot));m.visual=tm.visual.TextureVisuals(uv=np.concatenate(uv),material=materials[material])
            scene.add_geometry(m,node_name=group+'__'+material,geom_name=group+'__'+material,parent_node_name=group)
    def palette(tree):
        for m in tree['materials']:
            rgb=np.array(list(bytes.fromhex(colors[m['name']])))/255
            m['pbrMetallicRoughness']['baseColorFactor']=[*np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4).tolist(),1.]
            props=a.get('material_properties',{}).get(m['name'],{})
            if 'alpha' in props:
                m['pbrMetallicRoughness']['baseColorFactor'][3]=props['alpha'];m['alphaMode']='BLEND'
            for source,target in [('roughness','roughnessFactor'),('metallic','metallicFactor')]:
                if source in props:m['pbrMetallicRoughness'][target]=props[source]
            if props.get('double_sided'):m['doubleSided']=True
            if 'emissive' in props:m['emissiveFactor']=props['emissive']
    scene.export(path,tree_postprocessor=palette,include_normals=True)
    return dict(render_meshes=len(scene.geometry),triangles=sum(len(m.faces) for m in scene.geometry.values()),glb_bytes=path.stat().st_size)
