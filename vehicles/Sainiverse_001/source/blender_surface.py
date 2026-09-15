"""Editable shader nodes equivalent to the runtime's semantic base atlas."""
import bpy

def apply(mat,shader,base_image,normal_image,label_image):
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    def calc(op,x,y=None):
        n=nodes.new('ShaderNodeMath');n.operation=op
        for i,v in enumerate([x,y]):
            if v is not None:
                if isinstance(v,(float,int)):n.inputs[i].default_value=v
                else:links.new(v,n.inputs[i])
        return n.outputs[0]
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map='SurfaceUV';uv.label='Preserved source metre / semantic family UV'
    sep=nodes.new('ShaderNodeSeparateXYZ');links.new(uv.outputs[0],sep.inputs[0]);x=sep.outputs[0];y=sep.outputs[1]
    index=calc('FLOOR',x);fx=calc('FRACT',x)
    isfloor=calc('MULTIPLY',calc('GREATER_THAN',index,5.5),calc('LESS_THAN',index,7.5))
    floorx=calc('ADD',.016,calc('MULTIPLY',.968,calc('FRACT',calc('DIVIDE',calc('MULTIPLY',calc('SUBTRACT',fx,.00001),4096),8))))
    floory=calc('ADD',.016,calc('MULTIPLY',.968,calc('FRACT',calc('DIVIDE',y,4))))
    def choose(a,b):return calc('ADD',a,calc('MULTIPLY',calc('SUBTRACT',b,a),isfloor))
    tx=calc('DIVIDE',calc('ADD',calc('MODULO',index,4),choose(fx,floorx)),4)
    ty=calc('SUBTRACT',1,calc('DIVIDE',calc('ADD',calc('FLOOR',calc('DIVIDE',index,4)),choose(y,floory)),4))
    vec=nodes.new('ShaderNodeCombineXYZ');links.new(tx,vec.inputs[0]);links.new(ty,vec.inputs[1])
    tex=nodes.new('ShaderNodeTexImage');tex.image=base_image;tex.label='Authored surface strokes / panel pressings';links.new(vec.outputs[0],tex.inputs[0])
    bw=nodes.new('ShaderNodeRGBToBW');links.new(tex.outputs['Color'],bw.inputs[0]);weight=calc('DIVIDE',bw.outputs[0],.56)
    mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';links.new(calc('GREATER_THAN',x,-.01),mix.inputs[0]);links.new(weight,mix.inputs[2])
    previous=shader.inputs['Base Color'].links
    if previous:links.new(previous[0].from_socket,mix.inputs[1])
    else:mix.inputs[1].default_value=shader.inputs['Base Color'].default_value
    links.new(mix.outputs[0],shader.inputs['Base Color'])
    texn=nodes.new('ShaderNodeTexImage');texn.image=normal_image;links.new(vec.outputs[0],texn.inputs[0])
    normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='SurfaceUV';links.new(calc('MULTIPLY',calc('GREATER_THAN',x,-.01),.65),normal.inputs['Strength']);links.new(texn.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    if mat.name.startswith('decal_'):
        index=int(mat.name.split('_')[1]);coord=nodes.new('ShaderNodeUVMap');coord.uv_map='MaterialUV';se=nodes.new('ShaderNodeSeparateXYZ');links.new(coord.outputs[0],se.inputs[0])
        uvv=nodes.new('ShaderNodeCombineXYZ');links.new(calc('DIVIDE',calc('ADD',se.outputs[0],index%4),4),uvv.inputs[0]);links.new(calc('DIVIDE',calc('ADD',se.outputs[1],3-index//4),4),uvv.inputs[1])
        label=nodes.new('ShaderNodeTexImage');label.image=label_image;links.new(uvv.outputs[0],label.inputs[0]);valid=1
        for v in [se.outputs[0],se.outputs[1]]:valid=calc('MULTIPLY',valid,calc('MULTIPLY',calc('GREATER_THAN',v,0),calc('LESS_THAN',v,1)))
        label_mix=nodes.new('ShaderNodeMixRGB');links.new(calc('MULTIPLY',valid,label.outputs['Alpha']),label_mix.inputs[0]);links.new(mix.outputs[0],label_mix.inputs[1]);links.new(label.outputs['Color'],label_mix.inputs[2]);links.new(label_mix.outputs[0],shader.inputs['Base Color'])
