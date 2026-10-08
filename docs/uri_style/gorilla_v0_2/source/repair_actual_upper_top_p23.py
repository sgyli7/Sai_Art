"""Inspect and locally correct the C15 hood rims for an upper-only TOP guide.

The rejected P22 whole-body assembly is not an input. C15 is a geometric
reference, not an appearance approval. Only the paired projecting hood rims
change; every other mesh is retained verbatim. No upstream file is written.
"""
from pathlib import Path
import hashlib, json, math, sys
sys.path.append('/home/ethan/Softwares/ComfyUI/.venv/lib/python3.12/site-packages')
import bpy, bmesh, numpy as np
from mathutils import Matrix, Vector
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'source/upstream_v0_1_appearance_c15.blend'
SCENE_JSON = ROOT / 'references/upstream_v0_1_appearance_c15_scene.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parts = {p['name']: p for p in json.loads(SCENE_JSON.read_text())['parts']}
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
assert bpy.context.scene.get('source_scene_sha256') == sha(SCENE_JSON)

def mesh_identity(o):
    v = np.empty(len(o.data.vertices) * 3, dtype=np.float32)
    o.data.vertices.foreach_get('co', v)
    f = np.asarray([x for p in o.data.polygons for x in p.vertices], dtype=np.int64)
    n = np.asarray([len(p.vertices) for p in o.data.polygons], dtype=np.int64)
    return hashlib.sha256(v.tobytes() + n.tobytes() + f.tobytes()).hexdigest()

def coords(o):
    v = np.empty(len(o.data.vertices) * 3, dtype=np.float32)
    o.data.vertices.foreach_get('co', v)
    m = np.asarray(o.matrix_world)
    return v.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3]

def is_upper(body):
    return body == 'torso' or any(k in body for k in ('upper_arm','forearm','palm','finger','thumb'))

upper = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name in parts and is_upper(parts[o.name]['body'])]
original = {o.name: mesh_identity(o) for o in upper}
for o in list(bpy.context.scene.objects):
    if o not in upper: bpy.data.objects.remove(o, do_unlink=True)

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16
scene.cycles.use_denoising = False
scene.world.use_nodes = True
scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(1,1,1,1)
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=1.0
sh = scene.display.shading
sh.light = 'STUDIO'; sh.studio_light = 'paint.sl'; sh.color_type = 'OBJECT'
sh.show_shadows = True; sh.show_cavity = True; sh.cavity_type = 'BOTH'
sh.show_object_outline = True; sh.object_outline_color = (.07,.09,.1)
sh.background_type = 'WORLD'; scene.world.color = (1,1,1)
scene.render.film_transparent = False
scene.view_settings.view_transform = 'Standard'
scene.render.resolution_x = scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
for o in upper:
    o.color = tuple(parts[o.name]['rgba'])
    o['source_original_name'] = o.name
    o['source_scene_sha256'] = sha(SCENE_JSON)

allv = np.concatenate([coords(o) for o in upper])
center = Vector(((allv.min(0)+allv.max(0))/2).tolist())
bpy.ops.object.camera_add()
camera = bpy.context.object; camera.name = 'Actual_upper_orthographic_top_camera'
camera.data.type = 'ORTHO'; scene.camera = camera

def render(name, axis):
    camera.location = center + Vector(axis) * 8
    camera.rotation_euler = (0,0,math.pi/2) if axis == (0,0,1) else (center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    inv = np.asarray(camera.matrix_world.inverted())
    v = allv @ inv[:3,:3].T + inv[:3,3]
    span = np.ptp(v[:,:2], axis=0)
    off = (v[:,:2].min(0)+v[:,:2].max(0))/2
    basis = np.asarray(camera.matrix_world)[:3,:3]
    camera.location += Vector((basis[:,0]*off[0]+basis[:,1]*off[1]).tolist())
    camera.data.ortho_scale = float(max(span)*1.15)
    scene.render.filepath = str(ROOT / ('images/'+name+'.png'))
    bpy.ops.render.render(write_still=True)
    return {'image':'images/'+name+'.png','camera_type':'ORTHO','camera_matrix_world':np.asarray(camera.matrix_world).tolist(), 'ortho_scale':camera.data.ortho_scale}

lipnames = ['left_ivory_hood_window_side_lip','right_ivory_hood_window_side_lip']
for n in lipnames: bpy.data.objects[n].hide_render = True
render('native_c15_upper_without_side_lips_p23', (0,0,1))
for n in lipnames: bpy.data.objects[n].hide_render = False

# Native central shield section depths supply the front limit; no new body
# silhouette is invented. A monotone depth contraction preserves Y/Z contours.
shield = np.asarray(parts['continuous_ivory_torso_armor_cover']['vertices_world_m'], dtype=float)
shield = shield[:len(shield)//2]
zs = np.unique(shield[:,2])
xf = np.array([shield[shield[:,2] == z,0].max() for z in zs])
left = bpy.data.objects[lipnames[0]]
outer = np.asarray(parts[lipnames[0]]['vertices_world_m'], dtype=float)[:160]
rows = outer.reshape(20,8,3)
front = rows[:10,0,:]
# The two bottom rows share a clipped Z; retain their forward envelope.
oz = np.unique(front[:,2])
ox = np.array([front[front[:,2] == z,0].max() for z in oz])
anchor = .08
newouter = outer.copy()
target = np.interp(outer[:,2],zs,xf) - .035
oldlimit = np.interp(outer[:,2],oz,ox)
ratio = np.minimum(1., np.maximum(.05,(target-anchor)/np.maximum(oldlimit-anchor,.02)))
forward = outer[:,0] > anchor
newouter[forward,0] = anchor + (outer[forward,0]-anchor)*ratio[forward]
# Reconstruct the inner skin with the existing seven-millimetre visual shell
# thickness after the local surface correction; it is not a manufacturing fit.
outerfaces = [list(f) for f in parts[lipnames[0]]['faces'] if max(f) < 160]
normals = np.zeros_like(newouter)
for f in outerfaces:
    a,b,c = newouter[f[:3]]
    n = np.cross(b-a,c-a)
    for i in f: normals[i] += n
normals /= np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
newv = np.concatenate([newouter,newouter-.007*normals]).astype(np.float32)
beforev = coords(left)
left.parent = None
left.location = (0,0,0)
left.rotation_mode = "XYZ"
left.rotation_euler = (0,0,0)
left.scale = (1,1,1)
left.data.vertices.foreach_set('co',newv.reshape(-1))
left.data.update()
left['art_local_correction'] = 'Front depth contracted to follow the native central chest skin; original frontal Y/Z outline retained; inner skin recomputed.'
right = bpy.data.objects[lipnames[1]]
# One left master and a exact right reflection, including corrected shell skin.
right.parent = None
right.data = left.data
right.location = (0,0,0)
right.rotation_mode = "XYZ"
right.rotation_euler = (0,0,0)
right.scale = (1,-1,1)
right['art_local_correction'] = left['art_local_correction']
bpy.context.view_layer.update()

checks = []
for o in upper:
    if o.name in lipnames: continue
    checks.append({'name':o.name,'mesh_bytes_unchanged':mesh_identity(o)==original[o.name]})
lv,rv = coords(left),coords(right)
reflected = lv.copy(); reflected[:,1] *= -1
assert np.array_equal(reflected,rv)
topology = {}
for n in lipnames:
    bm = bmesh.new(); bm.from_mesh(bpy.data.objects[n].data)
    topology[n] = {'boundary_edges':sum(e.is_boundary for e in bm.edges),
                   'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),
                   'vertices':len(bm.verts),'faces':len(bm.faces),
                   'minimum_face_area_m2':min(f.calc_area() for f in bm.faces)}
    bm.free()
assert all(c['mesh_bytes_unchanged'] for c in checks)
assert all(t['boundary_edges']==0 and t['nonmanifold_edges']==0 and t['minimum_face_area_m2']>1e-12 for t in topology.values())
allv = np.concatenate([coords(o) for o in upper])
views={}
for n,axis in [('top',(0,0,1)),('front',(1,0,0)),('left',(0,1,0))]:
    views[n] = render('native_c15_upper_corrected_'+n+'_p23',axis)
out = ROOT/'source/v0_1_upper_top_corrected_p23.blend'
scene['geometry_scope']='Upper-only geometric guide. P22 whole-body assembly rejected and excluded.'
scene['appearance_accepted']=False; scene['physics_accepted']=False
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
report={'revision':'p23','source':str(out.relative_to(ROOT)),'source_sha256':sha(out),
        'upstream_snapshot':str(SOURCE.relative_to(ROOT)),'upstream_snapshot_sha256':sha(SOURCE),
        'upstream_scene_sha256':sha(SCENE_JSON),
        'diagnosis':'The two forward tips belong to the paired hood-window rim meshes. Their independently traced LEFT depth projected beyond the central chest cover.',
        'old_rim_forward_extreme_m':float(beforev[:,0].max()),
        'new_rim_forward_extreme_m':float(lv[:,0].max()),
        'central_cover_forward_extreme_m':float(shield[:,0].max()),
        'front_outer_yz_contour_change_max_m':float(abs(newouter[:,1:]-outer[:,1:]).max()),
        'other_upper_meshes_unchanged':all(c['mesh_bytes_unchanged'] for c in checks),
        'preservation_checks':checks,'paired_rims_shared_master':left.data==right.data,
        'paired_rims_exact_mirror':bool(np.array_equal(reflected,rv)), 'corrected_rim_topology':topology,
        'views':views,'rejected_p22_assembly_used':False,'upstream_files_modified':False,
        'appearance_accepted':False,'physics_accepted':False,'whole_v0_2_qualified':False}
(ROOT/'actual_upper_top_correction_p23.json').write_text(json.dumps(report,indent=2)+'\n')
print('LOCAL_RIM_CORRECTION',report['old_rim_forward_extreme_m'],report['new_rim_forward_extreme_m'],report['paired_rims_exact_mirror'],flush=True)
