"""Export source-Z-up parts; batch plain pigments per body using a theme palette."""
import math,json
import numpy as np
import trimesh as tm
from full_surface import uv as surface_uv

def export(a,path):
    colors=dict(a['colors']);colors['vertex_palette']='FFFFFF';scene=tm.Scene()
    roles=[k for k in a['colors'] if not k.startswith(('rig_','art_','wear_','warn_','logo_','decal_','status_')) and k not in ['cabin_glass','cabin_light','deck_steel']]
    indices={name:i for i,name in enumerate(roles)}
    assert len(roles)<256
    (path.parent/'palette_roles.json').write_text(json.dumps(roles))
    materials={k:tm.visual.material.PBRMaterial(name=k,baseColorFactor=[*bytes.fromhex(v),255],metallicFactor=.45 if k in ['steel','silver','track'] else .08,roughnessFactor=.5 if k!='glass' else .18) for k,v in colors.items()}
    grouped={}
    for p in a['parts']:
        material='vertex_palette' if '_bogie_' not in p['group'] and p['material'] in indices else p['material']
        grouped.setdefault((p['group'],material),[]).append(p)
    for group,pivot in a['groups'].items():
        transform=np.eye(4);transform[:3,3]=pivot;scene.graph.update(frame_to=group,matrix=transform)
        for material in colors:
            parts=grouped.get((group,material),[])
            if not parts:continue
            meshes=[];uv=[];uv2=[];vertex_colors=[]
            for p in parts:
                m=tm.Trimesh(vertices=p['vertices'],faces=p['faces'],process=False);m=tm.graph.smooth_shade(m,angle=math.radians(40),facet_minarea=None)
                motion=p['motion'];value=[motion['index'],3] if motion['kind']=='wheel_slide' else [motion['index'],2] if motion['kind']=='wheel' else [motion['phase'],1] if motion['kind']=='belt' else [0,0]
                coords=np.tile(value,(len(m.vertices),1)).astype(float)
                if motion['kind']=='static' and '_bogie_' not in group:coords[:]=[-1.,-1.]
                if 'art_uv' in p:
                    meta=p['art_uv'];lo,hi=np.array(meta['bounds']);span=np.maximum(hi-lo,.001);coords[:]=[-10.,-10.] if meta.get('usage')=='decal' else [.124,.124]
                    axis=np.argmax(np.abs(m.vertex_normals),axis=1)
                    for k in meta['axes']:
                        active=axis==k;ij=[0,2] if k==1 else [1,2] if k==0 else [0,1]
                        if meta.get('usage')=='decal':
                            q=(m.vertices[active][:,ij]-np.array(meta['rect_center']))/np.array(meta['rect_size'])+.5;q[:,1]=1-q[:,1]
                            flip=(m.vertex_normals[active,k]>0) if k==1 else (m.vertex_normals[active,k]<0) if k==0 else np.zeros(len(q),dtype=bool)
                            q[flip,0]=1-q[flip,0];coords[active]=q;continue
                        q=(m.vertices[active][:,ij]-lo[ij])/span[ij];q=np.clip(q,.002,.998);q[:,1]=1-q[:,1]
                        if meta.get('flip_u'):q[:,0]=1-q[:,0]
                        tile=int(meta['tile']);grid=meta.get('grid',2);coords[active]=(q+np.array([tile%grid,tile//grid]))/grid
                uv.append(coords);uv2.append(surface_uv(m,p));meshes.append(m)
                if material=="vertex_palette":
                    rgb=np.array(list(bytes.fromhex(colors[p['material']])))/255.
                    linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
                    vertex_colors.append(np.tile([*np.rint(linear*65535),indices[p['material']]*257],(len(m.vertices),1)))
            m=tm.util.concatenate(meshes);m.apply_translation(-np.array(pivot));m.visual=tm.visual.TextureVisuals(uv=np.concatenate(uv),material=materials[material])
            m.vertex_attributes["_TEXCOORD_1"]=np.concatenate(uv2)
            if vertex_colors:m.vertex_attributes["_COLOR_0"]=np.concatenate(vertex_colors).astype(np.uint16)
            scene.add_geometry(m,node_name=group+'__'+material,geom_name=group+'__'+material,parent_node_name=group)
    def palette(tree):
        for mesh in tree['meshes']:
            for primitive in mesh['primitives']:
                attrs=primitive['attributes'];attrs['TEXCOORD_1']=attrs.pop('_TEXCOORD_1')
                if '_COLOR_0' in attrs:
                    attrs['COLOR_0']=attrs.pop('_COLOR_0');tree['accessors'][attrs['COLOR_0']]['normalized']=True
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
