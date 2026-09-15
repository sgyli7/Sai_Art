"""Describe authored-to-physical frames without rebuilding the accepted mesh."""
from pathlib import Path
import gzip,hashlib,json
import mujoco
from suspension_physics import ROOT

OUT=ROOT/'candidates/r018_visual_suspension'
def main():
    source=ROOT/'candidates/r016_modular/train_containers_first'
    assembly=source/'source/assembly.json.gz'
    a=json.loads(gzip.decompress(assembly.read_bytes()))
    physics=ROOT/'candidates/r017_turning/physics/suspended.xml'
    m=mujoco.MjModel.from_xml_path(str(physics));d=mujoco.MjData(m)
    d.qpos[2]=10.;mujoco.mj_forward(m,d)
    bindings={n:dict(pivot_source_m=p,neutral_body_position_source_m=d.xpos[m.body(n).id].tolist()) for n,p in a['groups'].items()}
    wheel_parts=[p for p in a['parts'] if p['motion']['kind']=='wheel']
    gear=json.loads((ROOT/'assets/running_gear.json').read_text())
    report=dict(groups=bindings,gear=gear,glb=str(source/'assets/leviathan003_three_modules.glb'),
                native_blend=str(source/'source/Leviathan_003_three_modules.blend'),
                physical_wheels=72,wheel_visual_parts=len(wheel_parts),render_meshes=119,
                scope='Authored 21 exterior groups bind to physical bodies; 72 road-wheel translations use native body frames. Wheel spin is no-slip odometry animation, not independent spin dynamics. Belt loop remains the rigid authored loop pending tensioner mechanics.',
                sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [assembly,physics,source/'assets/leviathan003_three_modules.glb',Path(__file__)]})
    (OUT/'bindings.json').write_text(json.dumps(report,indent=2)+'\n')
    # Preserve the accepted shader and asset. Only add independent wheel travel.
    shader=(ROOT/'godot/belt.gdshader').read_text().replace('uniform float travel_m=0.;','uniform vec2 belt_travel_m=vec2(0.);\nuniform vec3 wheel_left_m=vec3(0.);\nuniform vec3 wheel_right_m=vec3(0.);')
    shader=shader.replace('void vertex(){','uniform float wheel_angles_left[5];\nuniform float wheel_angles_right[5];\nvoid vertex(){\n    float travel_m=VERTEX.y>0. ? belt_travel_m.x : belt_travel_m.y;\n    vec3 offsets=VERTEX.y>0. ? wheel_left_m : wheel_right_m;')
    shader=shader.replace('float a=-travel_m/wheel.z;', 'float a=VERTEX.y>0. ? wheel_angles_left[index] : wheel_angles_right[index];')
    shader=shader.replace('vec2 n=NORMAL.xz;', 'if(index>0 && index<4){VERTEX.z+=offsets[index-1];}\n        vec2 n=NORMAL.xz;')
    (ROOT/'godot/sprung_wheel.gdshader').write_text(shader)
    print('bindings',len(bindings),'wheel parts',len(wheel_parts))
if __name__=='__main__':main()
