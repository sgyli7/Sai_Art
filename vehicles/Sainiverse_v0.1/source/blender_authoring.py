"""Editable full assembly plus clearly identified mechanical inspection views."""
import bpy,gzip,json,math,sys
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(OUT/'source'))
from blender_surface import apply as surface_nodes
a=json.loads(gzip.decompress((OUT/'source/assembly.json.gz').read_bytes()))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mats={}
def packed(path,colorspace='Non-Color'):
    image=bpy.data.images.load(str(OUT/path));image.colorspace_settings.name=colorspace;image.pack();return image
wear_image=packed('assets/generated/wear_atlas.png')
warning_image=packed('assets/generated/warning_atlas.png','sRGB')
stencil_image=packed('assets/generated/service_stickers.png','sRGB')
surface_image=packed('assets/generated/surface_atlas.png')
surface_normal=packed('assets/generated/surface_normal.png')
label_image=packed('assets/generated/equipment_labels.png','sRGB')
art_color=bpy.data.images.load(str(OUT/'assets/service_panel_handpainted.png'));art_color.colorspace_settings.name='Non-Color';art_color.pack()
art_normal=bpy.data.images.load(str(OUT/'assets/normals/brushed_metal_normal.png'));art_normal.colorspace_settings.name='Non-Color';art_normal.pack()
deck_normal=bpy.data.images.load(str(OUT/'assets/normals/deck_tread_normal.png'));deck_normal.colorspace_settings.name='Non-Color';deck_normal.pack()

for name,h in a['colors'].items():
    rgb=[int(h[i:i+2],16)/255 for i in [0,2,4]];rgba=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]+[1.]
    mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=rgba
    shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=rgba;shader.inputs['Metallic'].default_value=.5 if name in ['silver','steel'] else .08;shader.inputs['Roughness'].default_value=.4 if name=='silver' else .88
    props=a.get('material_properties',{}).get(name,{})
    if 'alpha' in props:shader.inputs['Transmission Weight'].default_value=.8;shader.inputs['IOR'].default_value=1.45;shader.inputs['Roughness'].default_value=props['roughness']
    if 'emissive' in props:shader.inputs['Emission Color'].default_value=[*props['emissive'],1];shader.inputs['Emission Strength'].default_value=2.0
    if name.startswith('art_'):
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=art_color
        if name=='art_workbay_wall':
            nodes=mat.node_tree.nodes;links=mat.node_tree.links
            coord=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(coord.outputs['Generated'],sep.inputs[0])
            def calc(op,x=None,y=None):
                n=nodes.new('ShaderNodeMath');n.operation=op
                for i,value in enumerate([x,y]):
                    if value is not None:
                        if isinstance(value,(int,float)):n.inputs[i].default_value=value
                        else:links.new(value,n.inputs[i])
                return n.outputs[0]
            u=calc('MULTIPLY',sep.outputs['X'],2.99999);cell=calc('FLOOR',u)
            xx=calc('MULTIPLY',calc('ADD',calc('FRACT',u),calc('MODULO',cell,2)),.5)
            yy=calc('MULTIPLY',calc('ADD',sep.outputs['Z'],calc('SUBTRACT',1,calc('FLOOR',calc('DIVIDE',cell,2)))),.5)
            combine=nodes.new('ShaderNodeCombineXYZ');links.new(xx,combine.inputs['X']);links.new(yy,combine.inputs['Y']);links.new(combine.outputs[0],tex.inputs['Vector'])
            geom=nodes.new('ShaderNodeNewGeometry');trans=nodes.new('ShaderNodeVectorTransform');trans.vector_type='NORMAL';trans.convert_from='WORLD';trans.convert_to='OBJECT';links.new(geom.outputs['Normal'],trans.inputs[0])
            normal_sep=nodes.new('ShaderNodeSeparateXYZ');links.new(trans.outputs[0],normal_sep.inputs[0]);mask=calc('GREATER_THAN',calc('ABSOLUTE',normal_sep.outputs['Y']),.5)
        flat=mat.node_tree.nodes.new('ShaderNodeMixRGB');flat.inputs[1].default_value=(.55,.55,.55,1);mat.node_tree.links.new(tex.outputs['Alpha'],flat.inputs[0]);mat.node_tree.links.new(tex.outputs['Color'],flat.inputs[2])
        bw=mat.node_tree.nodes.new('ShaderNodeRGBToBW');mat.node_tree.links.new(flat.outputs[0],bw.inputs[0])
        weight=mat.node_tree.nodes.new('ShaderNodeMath');weight.operation='MULTIPLY_ADD';weight.inputs[1].default_value=1/.55;weight.inputs[2].default_value=0;mat.node_tree.links.new(bw.outputs[0],weight.inputs[0])
        mix=mat.node_tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[1].default_value=rgba
        if name=='art_workbay_wall':mat.node_tree.links.new(mask,mix.inputs[0])
        mat.node_tree.links.new(weight.outputs[0],mix.inputs[2]);mat.node_tree.links.new(mix.outputs[0],shader.inputs['Base Color'])
    if name.startswith('art_') or name=='deck_steel':
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=art_normal if name.startswith('art_') else deck_normal
        normal=mat.node_tree.nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.8;mat.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color']);mat.node_tree.links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    if name.startswith(('wear_','logo_','warn_')):
        nodes=mat.node_tree.nodes;links=mat.node_tree.links
        tex=nodes.new('ShaderNodeTexImage');tex.image=warning_image if name.startswith('warn_') else wear_image
        if name.startswith('warn_'):links.new(tex.outputs['Color'],shader.inputs['Base Color'])
        else:
            sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],sep.inputs[0])
            amount=nodes.new('ShaderNodeMath');amount.operation='MULTIPLY';amount.inputs[1].default_value=1.35 if name.startswith('logo_') else .7;amount.use_clamp=True;links.new(sep.outputs[0],amount.inputs[0])
            weather=nodes.new('ShaderNodeMixRGB');links.new(amount.outputs[0],weather.inputs[0]);weather.inputs[1].default_value=rgba;weather.inputs[2].default_value=(.014,.015,.018,1) if name.startswith('logo_') else (.065,.070,.071,1);links.new(weather.outputs[0],shader.inputs['Base Color'])
    if name=='art_workbay_wall':
        # Same three panel-local cells as Godot; map stencil to the clear lower band.
        xfrac=calc('FRACT',u);z=sep.outputs['Z']
        wuv=nodes.new('ShaderNodeCombineXYZ');links.new(calc('DIVIDE',calc('ADD',xfrac,cell),4),wuv.inputs['X']);links.new(calc('ADD',calc('MULTIPLY',z,.25),.75),wuv.inputs['Y'])
        wm=nodes.new('ShaderNodeTexImage');wm.image=wear_image;links.new(wuv.outputs[0],wm.inputs['Vector']);wr=nodes.new('ShaderNodeSeparateColor');links.new(wm.outputs[0],wr.inputs[0])
        aged=nodes.new('ShaderNodeMixRGB');links.new(calc('MULTIPLY',wr.outputs[0],calc('MULTIPLY',mask,.7)),aged.inputs[0]);links.new(mix.outputs[0],aged.inputs[1]);aged.inputs[2].default_value=(.065,.070,.071,1)
        first=calc('LESS_THAN',cell,.5)
        lx=calc('DIVIDE',calc('SUBTRACT',xfrac,calc('ADD',.13,calc('MULTIPLY',first,.09))),calc('ADD',.74,calc('MULTIPLY',first,-.39)))
        ly=calc('DIVIDE',calc('SUBTRACT',calc('SUBTRACT',1,z),calc('ADD',.59,calc('MULTIPLY',first,-.06))),calc('ADD',.065,calc('MULTIPLY',first,.165)))
        suv=nodes.new('ShaderNodeCombineXYZ');links.new(lx,suv.inputs['X']);links.new(calc('SUBTRACT',1,calc('DIVIDE',calc('ADD',ly,cell),4)),suv.inputs['Y'])
        st=nodes.new('ShaderNodeTexImage');st.image=stencil_image;st.extension='CLIP';links.new(suv.outputs[0],st.inputs['Vector'])
        valid=mask
        for val in [lx,ly]:valid=calc('MULTIPLY',valid,calc('MULTIPLY',calc('GREATER_THAN',val,0),calc('LESS_THAN',val,1)))
        decal=nodes.new('ShaderNodeMixRGB');links.new(calc('MULTIPLY',calc('MULTIPLY',valid,st.outputs['Alpha']),.8),decal.inputs[0]);links.new(aged.outputs[0],decal.inputs[1]);links.new(st.outputs['Color'],decal.inputs[2]);links.new(decal.outputs[0],shader.inputs['Base Color'])
    if name=='deck_steel':
        nodes=mat.node_tree.nodes;links=mat.node_tree.links
        geom=nodes.new('ShaderNodeNewGeometry');trans=nodes.new('ShaderNodeVectorTransform');trans.vector_type='NORMAL';trans.convert_from='WORLD';trans.convert_to='OBJECT';links.new(geom.outputs['Normal'],trans.inputs[0])
        sep=nodes.new('ShaderNodeSeparateXYZ');links.new(trans.outputs[0],sep.inputs[0]);ab=nodes.new('ShaderNodeMath');ab.operation='ABSOLUTE';links.new(sep.outputs['Z'],ab.inputs[0]);side=nodes.new('ShaderNodeMath');side.operation='LESS_THAN';side.inputs[1].default_value=.65;links.new(sep.outputs['Z'],side.inputs[0])
        mix=nodes.new('ShaderNodeMixRGB');links.new(side.outputs[0],mix.inputs[0]);mix.inputs[1].default_value=rgba
        rgb=[int(a['colors']['ivory'][i:i+2],16)/255 for i in [0,2,4]];mix.inputs[2].default_value=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]+[1.]
        # Same single-skin red waist paint as Godot; no duplicate geometry.
        coord=nodes.new('ShaderNodeTexCoord');pos=nodes.new('ShaderNodeSeparateXYZ');links.new(coord.outputs['Object'],pos.inputs[0])
        def band_math(op,x,y=None):
            n=nodes.new('ShaderNodeMath');n.operation=op
            for i,v in enumerate([x,y]):
                if v is None:continue
                if isinstance(v,(int,float)):n.inputs[i].default_value=v
                else:links.new(v,n.inputs[i])
            return n.outputs[0]
        band=band_math('GREATER_THAN',band_math('ABSOLUTE',sep.outputs['Y']),.8)
        for test in [band_math('GREATER_THAN',band_math('ABSOLUTE',pos.outputs['Y']),12.65),band_math('GREATER_THAN',pos.outputs['Z'],-1.20),band_math('LESS_THAN',pos.outputs['Z'],-1.00)]:band=band_math('MULTIPLY',band,test)
        paint=nodes.new('ShaderNodeMixRGB');links.new(band,paint.inputs[0]);links.new(mix.outputs[0],paint.inputs[1]);paint.inputs[2].default_value=(.48,.008,.02,1.)
        links.new(paint.outputs[0],shader.inputs['Base Color'])
    if name not in ['cabin_glass','glass','cabin_light','cabin_screen']:surface_nodes(mat,shader,surface_image,surface_normal,label_image)
    mats[name]=mat
parents={};world_origins={};wheel_parents={}
for name,pivot in a['groups'].items():
    obj=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(obj);obj.location=pivot;obj['physical_body']=name;parents[name]=obj;world_origins[name]=Vector(pivot)
    if '_bogie_' in name:
        for side in [-1,1]:
            for index,(x,z) in enumerate([(-2.55,1.15),(0,1.18),(2.55,1.15),(4.15,2.4)],start=1):
                key=name+(f'_idler_{"left" if side>0 else "right"}' if index==4 else f'_wheel_{"left" if side>0 else "right"}_{index}')
                w=bpy.data.objects.new(key,None);bpy.context.collection.objects.link(w);w.parent=obj;w.location=(x,side*1.75,z-pivot[2]);w['physical_body']=key;w['joint']='X slide, -0.32 to +0.24 m' if index==4 else 'vertical slide, -0.35 to +0.35 m';w['neutral_local_z']=w.location.z;wheel_parents[key]=w;parents[key]=w;world_origins[key]=Vector((pivot[0]+x,pivot[1]+side*1.75,z))
for p in a['parts']:
    owner=p['group'];motion=p['motion'];index=motion.get('index',0)
    if motion['kind'] in ['wheel','wheel_slide'] and index in [1,2,3]:
        side='left' if sum(v[1] for v in p['vertices'])/len(p['vertices'])>a['groups'][owner][1] else 'right'
        owner+=f'_wheel_{side}_{index}'
    if p.get('physical_body','').find('_idler_')>=0:owner=p['physical_body']
    mesh=bpy.data.meshes.new(p['name']);mesh.from_pydata([Vector(v)-world_origins[owner] for v in p['vertices']],[],p['faces']);mesh.materials.append(mats[('wear_'+p['material']) if p.get('art_uv',{}).get('usage')=='wear' else p['material']]);mesh.update()
    if 'art_uv' in p or p['material']=='deck_steel':
        uv=mesh.uv_layers.new(name='MaterialUV');meta=p.get('art_uv');lo=Vector(meta['bounds'][0]) if meta else None;hi=Vector(meta['bounds'][1]) if meta else None
        for face in mesh.polygons:
            axis=max(range(3),key=lambda i:abs(face.normal[i]));ij=[0,2] if axis==1 else [1,2] if axis==0 else [0,1]
            for loop_index in face.loop_indices:
                v=Vector(p['vertices'][mesh.loops[loop_index].vertex_index])
                if meta and meta.get('usage')=='decal':
                    if axis in meta['axes']:
                        coord=[(v[ij[j]]-meta['rect_center'][j])/meta['rect_size'][j]+.5 for j in range(2)]
                        if (axis==1 and face.normal.y>0) or (axis==0 and face.normal.x<0):coord[0]=1-coord[0]
                    else:coord=[-10.,-10.]
                elif meta and axis in meta['axes']:
                    q=[max(.002,min(.998,(v[i]-lo[i])/max(hi[i]-lo[i],.001))) for i in ij];q[1]=1-q[1]
                    if meta.get('flip_u'):q[0]=1-q[0]
                    tile=meta['tile'];grid=meta.get('grid',2);coord=[(q[0]+tile%grid)/grid,1-(q[1]+tile//grid)/grid]
                    if meta.get('usage')=='warn':coord=[q[1]*(.125 if axis==0 else 1),1-(q[0]+tile%4)/4]
                elif meta:coord=[.24,.76]
                else:coord=[v[ij[0]]/4,1-v[ij[1]]/4]
                uv.data[loop_index].uv=coord
    # Source UV2 stored without lossy material-specific rebaking.
    layer=mesh.uv_layers.new(name='SurfaceUV');meta=p.get('surface_texture');vsource=[Vector(v) for v in p['vertices']];lo=Vector([min(v[i] for v in vsource) for i in range(3)]);span=Vector([max(max(v[i] for v in vsource)-lo[i],.0001) for i in range(3)])
    for face in mesh.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]));ij=[[1,2],[0,2],[0,1]][axis]
        for li in face.loop_indices:
            if meta:
                v=vsource[mesh.loops[li].vertex_index];q=[(v[i]-lo[i])/span[i] for i in ij]
                coord=[meta['tile']+.00001+(v[ij[0]]-lo[ij[0]])/4096,span[ij[1]]-(v[ij[1]]-lo[ij[1]])] if meta['family']=='floor' and ((axis==1 and p['material']=='ramp_steel') or (axis==2 and face.normal.z>.65 and p['material']!='ramp_steel')) else [(meta['tile']%2 if meta['family']=='floor' else meta['tile'])+.02+q[0]*.96,.02+(1-q[1])*.96]
            else:coord=[-1.,-1.]
            layer.data[li].uv=coord
    obj=bpy.data.objects.new(p['name'],mesh);bpy.context.collection.objects.link(obj);obj.parent=parents[owner];obj['physical_body']=owner;obj['motion_kind']=motion['kind'];obj['source_group']=p['group'];obj['interior_category']=p.get('interior_category','');obj['source_name']=p['name']
    if any(t in p['name'] for t in ['barrel','piston','gland','clamp']):
        mesh.use_auto_smooth=True;mesh.auto_smooth_angle=math.radians(40)
        for face in mesh.polygons:face.use_smooth=True

# Connect lift authoring parents in the exact native serial chain.
for lift in json.loads((OUT/'source/lifts.json').read_text()):
    previous=parents[lift['hull']]
    for name in lift['groups']:
        child=parents[name];world=child.location.copy();child.parent=previous
        child.location=world-Vector(a['groups'][previous.name]);previous=child
for lift in json.loads((OUT/'source/lifts.json').read_text()):
    child=parents[lift['ramp']['name']];world=child.location.copy();child.parent=parents[lift['groups'][-1]];child.location=world-Vector(lift['pivot'])
for joint in a.get('equipment_actuation',{}).get('joints',[]):
    child=parents[joint['body']];world=Vector(a['groups'][joint['body']]);child.parent=parents[joint['parent']];child.location=world-Vector(a['groups'][joint['parent']])
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
scene['skin']='黑色';scene['vehicle_name']='Sainiverse_v0.1';scene['art_revision']='r031';scene['scope']='Editable authored model. Godot enamel/ink shader lives in assets. Physical validation is in reports; no learned robot policy.'
text=bpy.data.texts.new('READ ME — Sainiverse_v0.1');text.write('Source SI +X forward +Y left +Z up. Separate body groups and per-part materials. See README.md for driving and validation. Reference-derived conceptual geometry, not a CAD manufacturing qualification.')
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.clip_end=3000;area.spaces.active.shading.color_type='MATERIAL'
   area.spaces.active.region_3d.view_distance=160;area.spaces.active.region_3d.view_location=Vector((-35,0,10))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'source/Sainiverse_v0.1.blend'))
print('SAINIVERSE_ART_AUTHORING_COMPLETE',len(a['parts']))
