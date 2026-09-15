import bpy,json,gzip,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
with gzip.open(ROOT/'source/assembly.json.gz','rt') as f:r=json.load(f)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mats={}
for name,hexc in r['colors'].items():
    color=[int(hexc[i:i+2],16)/255 for i in (0,2,4)]
    color=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in color]+[1]
    m=bpy.data.materials.new(name);m.diffuse_color=color;m.use_nodes=True
    shader=m.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=color
    shader.inputs['Metallic'].default_value=.45 if name in ('steel','silver','track') else .08
    shader.inputs['Roughness'].default_value=.5 if name!='glass' else .18;mats[name]=m
collections={}
for name,pos in r['groups'].items():
    c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c);collections[name]=c
for p in r['parts']:
    mesh=bpy.data.meshes.new(p['name']);mesh.from_pydata(p['vertices'],[],p['faces']);mesh.materials.append(mats[p['material']]);mesh.update()
    obj=bpy.data.objects.new(p['name'],mesh);collections[p['group']].objects.link(obj);obj['motion_group']=p['group'];obj['source']='six user reference images / reconstructed'
    motion=p.get('motion',{'kind':'static'});obj['motion_kind']=motion['kind']
    if 'phase' in motion:obj['belt_phase_m']=motion['phase']
    if 'index' in motion:obj['wheel_index']=motion['index']
    # Flat facets on castings and plates, smooth cylinder walls without melting rims.
    if any(k in p['name'] for k in ('reservoir','wheel','rim','cylinder','collar')):
        mesh.use_auto_smooth=True;mesh.auto_smooth_angle=math.radians(40)
        for poly in mesh.polygons:poly.use_smooth=True
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=False
scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world.color=(.35,.35,.35)
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.64,.72,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
scene.view_settings.view_transform='Filmic';scene.view_settings.look='Medium High Contrast';scene.view_settings.exposure=0;scene.view_settings.gamma=1
bpy.ops.mesh.primitive_plane_add(size=2000,location=(0,0,-.08));floor=bpy.context.object;floor.name='STUDIO / excluded from asset'
mat=bpy.data.materials.new('studio');mat.diffuse_color=(.34,.39,.43,1);floor.data.materials.append(mat)
for loc,power,size in [((20,-40,90),75000,65),((-50,30,70),55000,50)]:
    data=bpy.data.lights.new('Softbox','AREA');data.energy=power;data.shape='DISK';data.size=size
    o=bpy.data.objects.new('Softbox',data);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((-12,0,8))-o.location).to_track_quat('-Z','Y').to_euler()
cameras={'front':((88,-114,62),(-11,0,11),108),'rear':((-125,95,58),(-13,0,12),105),'side':((0,-145,18),(-11,0,14),105),'top':((-11,0,160),(-11,0,0),105),'track':((31,-42,15),(11,-12,3),26)}
cameras.update({'house_port':((29,40,23),(-1,5,11),52),'house_starboard':((-32,-43,26),(-1,-4,12),49),'bridge_detail':((39,24,20),(24,0,12),28),'house_stairs':((30,24,16),(15.5,6,9.5),19),'joint':((23,-31,12),(11.5,-11.8,5.2),22),'crane':((-67,-28,22),(-53,-11,13),24),'panel_back':((-21,29,34),(-2,0,23),23),'reference2':((-90,-110,88),(-12,0,12),105)})
cameras['reservoir_clamps']=((-22,-25,31),(-35.5,-6.69,19),20)
cameras['reservoir_cradle']=((-38,-32,18),(-35.5,-11.15,13),24)
cameras['frame_marks']=((11,-31,10),(8,-13,7),13)
cameras['bridge_port']=((35,21,16),(28,3.5,12),18)
cameras['panel_front']=((33,-32,29),(1,0,23),28)
cameras['panel_back']=((-21,29,34),(1,0,23),28)
cameras['panel_root']=((18,-24,23),(2.8,0,18.8),17)
cameras['crane']=((-73,-24,26),(-56.7,-5.4,15.5),25)
cameras['crane_root']=((-65,-21,24),(-56.7,-10,16.5),13)
cameras['underbelly']=((0,-34,5.5),(0,-8,5.8),29)
cameras['bogie_front']=((30,-23,9),(11,-11.8,2.8),16)
for name,(eye,target,scale) in cameras.items():
    data=bpy.data.cameras.new(name);data.type='ORTHO';data.ortho_scale=scale;data.clip_end=3000
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=eye;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    if name=='reference2':data.type='PERSP';data.lens=48;o.location=Vector(target)+(Vector(eye)-Vector(target))*.98
scene.camera=bpy.data.objects['front'];bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/Leviathan_003.blend'))
if '--no-render' in sys.argv:sys.exit(0)
views=['front','track','bogie_front','reference2'] if '--r014' in sys.argv else ['front','reference2','crane','crane_root'] if '--r013' in sys.argv else ['front','reference2','reservoir_clamps','reservoir_cradle'] if '--r012' in sys.argv else ['front','bridge_detail','bridge_port','house_stairs'] if '--r010' in sys.argv else ['front','frame_marks'] if '--marks-finish' in sys.argv else ['front','bridge_detail','bridge_port','frame_marks'] if '--r009' in sys.argv else ['reservoir_clamps','reservoir_cradle'] if '--mounts-only' in sys.argv else ['front','reservoir_clamps','reservoir_cradle','reference2'] if '--r008' in sys.argv else ['front','panel_front','panel_root','panel_back','reference2'] if '--r007' in sys.argv else ['front','crane','crane_root','reference2'] if '--r006' in sys.argv else ['front','track','joint','underbelly'] if '--r005' in sys.argv else ['front','house_port','house_starboard','bridge_detail','house_stairs'] if '--r004' in sys.argv else ['front','panel_back','reference2'] if '--r003' in sys.argv else ['reference2'] if '--reference-only' in sys.argv else ['front','joint','crane','panel_back','reference2'] if '--r002' in sys.argv else ['front'] if '--hero-only' in sys.argv else ['front','rear','side','top','track']
for name in views:
    scene.render.resolution_y=900 if name=='reference2' else 1000
    scene.camera=bpy.data.objects[name];scene.render.filepath=str(ROOT/'reports'/('studio_r014' if '--r014' in sys.argv else 'studio_r013' if '--r013' in sys.argv else 'studio_r012' if '--r012' in sys.argv else '')/f'{name}.png');bpy.ops.render.render(write_still=True)
