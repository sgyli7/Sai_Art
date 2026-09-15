"""Inspection-only visibility changes, from the saved complete native assembly."""
import bpy
from pathlib import Path
from mathutils import Vector
OUT=Path(__file__).resolve().parents[1]/'candidates/r019_running_gear'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'source/Leviathan_003_guided_axles.blend'))
group='front_bogie_fore_right';by=-13.55
for obj in bpy.data.objects:
    if obj.type!='MESH':continue
    obj.hide_render=obj.get('source_group')!=group
    if obj.hide_render:continue
    center=obj.matrix_world@(sum((v.co for v in obj.data.vertices),Vector())/len(obj.data.vertices))
    if any(k in obj.name for k in ['fender','service_rail','center_platform']):obj.hide_render=True
    if obj.get('motion_kind')=='wheel' and center.y<by:obj.hide_render=True
    if obj.name.endswith('track_inner_frame') and by-.3<center.y<by:obj.hide_render=True
camera=bpy.context.scene.camera;camera.location=(12.2,-22,5.0);target=Vector((10.5,by,2.10));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=8.
for index,q in [(1,-.35),(2,.35),(3,0.)]:
    obj=bpy.data.objects[group+f'_wheel_right_{index}'];obj.location.z=float(obj['neutral_local_z'])+q
scene=bpy.context.scene;scene['inspection_view']='Near drum halves/frame/fenders intentionally hidden. Declared travel-limit poses, not dynamic simulation.'
scene.render.filepath=str(OUT/'reports/guided_axle_limit_cutaway.png');bpy.ops.render.render(write_still=True)
print('CORRECTED_CUTAWAY_COMPLETE')
