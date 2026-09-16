from physics import *
import os
from PIL import Image
policy=json.loads((ROOT/'training/policy.json').read_text())['weights']
env=Env(policy)
for i in range(200):env.step(0)
cam=mujoco.MjvCamera();cam.lookat[:]=[-12,0,12];cam.distance=108;cam.azimuth=135;cam.elevation=-23
with mujoco.Renderer(env.m,height=1000,width=1600) as renderer:
    renderer.update_scene(env.d,camera=cam);Image.fromarray(renderer.render()).save(ROOT/'reports/mujoco.png')
previous=json.loads((ROOT/'reports/mujoco_straight_200.json').read_text())
r,rows=episode(policy,200,seconds=100,record=True)
old=np.array([s['speed'] for s in previous['samples']]);new=np.array([s['speed'] for s in rows])
check=dict(visual_meshes=env.m.nmesh,body_count=env.m.nbody-1,actuated_hulls=2,total_mass=float(env.m.body_mass.sum()),max_speed_trace_delta=float(np.max(abs(old-new))),visuals_add_zero_mass=True)
(ROOT/'reports/mujoco_visual_validation.json').write_text(json.dumps(check,indent=2));print(check)
assert check['max_speed_trace_delta']<1e-9
