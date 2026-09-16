"""Native exterior review from actual body frames; no regenerated geometry."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'candidates/r017_turning'
source=ROOT/'candidates/r016_modular/train_containers_first/source/Leviathan_003_three_modules.blend'
pose_path=OUT/'reports/tight_pose_mujoco.json';pose=json.loads(pose_path.read_text());poses=pose['final_motion_groups']
bpy.ops.wm.open_mainfile(filepath=str(source))
front=poses['front'];heading=math.atan2(front['rotation_row_major'][3],front['rotation_row_major'][0]);p=front['position_source_m']
frame=Matrix.Rotation(-heading,4,'Z')@Matrix.Translation(Vector((-p[0],-p[1],0)))
for name,state in poses.items():
    obj=bpy.data.objects[name];pivot=obj.matrix_world.translation.copy();r=state['rotation_row_major']
    body=Matrix([r[:3],r[3:6],r[6:9]]).to_4x4();body.translation=Vector(state['position_source_m'])
    obj.matrix_world=frame@body@Matrix.Translation(pivot-Vector(state['neutral_body_position_source_m']))
scene=bpy.context.scene;scene.cycles.samples=32;scene.cycles.use_denoising=False
scene['physics_pose_sha256']=hashlib.sha256(pose_path.read_bytes()).hexdigest()
scene['scope']=pose['scope']+' Presentation frame recenters/rotates the complete assembly without changing relative poses.'
center=sum([frame@Vector(poses[n]['position_source_m']) for n in ['front','rear','tail']],Vector())/3
camera=scene.camera;camera.data.type='ORTHO';camera.data.ortho_scale=160
def view(offset):
    camera.location=center+Vector(offset);camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=1440;scene.render.resolution_y=900
view((-125,-175,150))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'source/Leviathan_003_turn_review.blend'))
scene.render.filepath=str(OUT/'reports/trained_turn_whole.png');bpy.ops.render.render(write_still=True)
view((0,0,180));scene.render.resolution_y=1100
scene.render.filepath=str(OUT/'reports/trained_turn_top.png');bpy.ops.render.render(write_still=True)
print('NATIVE_TURN_REVIEW_COMPLETE')
