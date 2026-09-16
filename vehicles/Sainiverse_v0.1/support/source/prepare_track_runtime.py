"""Keep exact live belt geometry, transport all 24 belt states in one float texture."""
from pathlib import Path
import json,hashlib
from suspension_physics import ROOT
OUT=ROOT/'candidates/r022_runtime'
def main():
    source=ROOT/'candidates/r021_track_tension/assets/tensioned_tracks.gdshader';shader=source.read_text()
    remove=['uniform vec2 belt_travel_m=vec2(0.);','uniform vec3 wheel_left_m=vec3(0.);','uniform vec3 wheel_right_m=vec3(0.);','uniform vec2 idler_m;','uniform vec2 curve_length_m;','uniform vec4 curve_left_a[16];','uniform vec4 curve_left_b[16];','uniform vec4 curve_right_a[16];','uniform vec4 curve_right_b[16];','uniform float wheel_angles_left[5];','uniform float wheel_angles_right[5];']
    for line in remove:
        assert line in shader;shader=shader.replace(line,'')
    shader=shader.replace('uniform float metal=.35;','uniform float metal=.35;\nuniform sampler2D track_state:filter_nearest,repeat_disable;\nuniform int state_row;')
    shader=shader.replace('vec4 live_belt(float phase,bool left){\n    float total=left?curve_length_m.x:curve_length_m.y;','vec4 live_belt(float phase,int row,float total){')
    shader=shader.replace('vec4 a=left?curve_left_a[i]:curve_right_a[i];vec4 b=left?curve_left_b[i]:curve_right_b[i];','vec4 a=texelFetch(track_state,ivec2(4+i,row),0);vec4 b=texelFetch(track_state,ivec2(20+i,row),0);')
    shader=shader.replace('float travel_m=VERTEX.y>0. ? belt_travel_m.x : belt_travel_m.y;\n    vec3 offsets=VERTEX.y>0. ? wheel_left_m : wheel_right_m;','int row=state_row+(VERTEX.y>0.?0:1);\n    vec4 suspension=texelFetch(track_state,ivec2(0,row),0);\n    vec2 phase_length=texelFetch(track_state,ivec2(1,row),0).xy;\n    vec4 angles=texelFetch(track_state,ivec2(2,row),0);\n    float end_angle=texelFetch(track_state,ivec2(3,row),0).x;\n    float travel_m=phase_length.x;vec3 offsets=suspension.xyz;')
    shader=shader.replace('VERTEX.y>0.?idler_m.x:idler_m.y','suspension.w')
    shader=shader.replace('VERTEX.y>0. ? wheel_angles_left[index] : wheel_angles_right[index]','index==4?end_angle:angles[index]')
    shader=shader.replace('live_belt(UV.x+travel_m,VERTEX.y>0.)','live_belt(UV.x+travel_m,row,phase_length.y)')
    assert 'curve_left' not in shader and 'belt_travel_m' not in shader
    target=OUT/'assets/tensioned_tracks_texture.gdshader';target.write_text(shader)
    binding=json.loads((OUT/'bindings.json').read_text());binding.update(shader=str(target),state_texture=True)
    binding['sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,Path(__file__),target,Path(binding['glb']),OUT/'physics/native_spec.json',OUT/'native/bin/libleviathan_track_path.so']}
    (OUT/'bindings.json').write_text(json.dumps(binding,indent=2)+'\n')
if __name__=='__main__':main()
