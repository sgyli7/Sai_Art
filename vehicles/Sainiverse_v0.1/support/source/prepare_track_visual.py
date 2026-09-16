"""Rigid cleat placements on the physically driven elastic track envelope."""
from pathlib import Path
import json,hashlib
from suspension_physics import ROOT
OUT=ROOT/'candidates/r021_track_tension'
def main():
    source=ROOT/'candidates/r019_running_gear/assets/guided_axles.gdshader';shader=source.read_text()
    shader=shader.replace('uniform float wheel_angles_left[5];','''uniform vec2 idler_m;
uniform vec2 curve_length_m;
uniform vec4 curve_left_a[16];
uniform vec4 curve_left_b[16];
uniform vec4 curve_right_a[16];
uniform vec4 curve_right_b[16];
vec4 live_belt(float phase,bool left){
    float total=left?curve_length_m.x:curve_length_m.y;
    float s=mod(phase/23.43539363436418*total,total);
    for(int i=0;i<16;i++){
        vec4 a=left?curve_left_a[i]:curve_right_a[i];vec4 b=left?curve_left_b[i]:curve_right_b[i];
        if(b.x<=0.){continue;}
        if(s<=b.x){
            if(b.z>.5){float angle=a.w+b.y*s/b.x;return vec4(a.xy+a.z*vec2(cos(angle),sin(angle))-vec2(0.,3.),vec2(sin(angle),-cos(angle)));}
            vec2 direction=normalize(a.zw-a.xy);return vec4(a.xy+direction*s-vec2(0.,3.),direction);
        }s-=b.x;
    }
    return vec4(0.,0.,1.,0.);
}
uniform float wheel_angles_left[5];''')
    shader=shader.replace('int index=clamp(int(round(UV.x)),1,3);\n        VERTEX.z+=offsets[index-1];','int index=clamp(int(round(UV.x)),1,4);\n        if(index==4){VERTEX.x+=VERTEX.y>0.?idler_m.x:idler_m.y;}else{VERTEX.z+=offsets[index-1];}')
    shader=shader.replace('if(index>0 && index<4){VERTEX.z+=offsets[index-1];}','if(index>0 && index<4){VERTEX.z+=offsets[index-1];}\n        if(index==4){VERTEX.x+=VERTEX.y>0.?idler_m.x:idler_m.y;}')
    shader=shader.replace('vec4 next=belt(UV.x+travel_m);','vec4 next=live_belt(UV.x+travel_m,VERTEX.y>0.);')
    target=OUT/'assets/tensioned_tracks.gdshader';target.write_text(shader)
    binding=json.loads((ROOT/'candidates/r020_hydraulics/bindings.json').read_text());binding.update(glb=str(OUT/'assets/leviathan003_tensioned_tracks.glb'),native_blend=str(OUT/'source/Leviathan_003_tensioned_tracks.blend'),shader=str(target),tensioned_tracks=True,
        scope='24 actual moving idlers, 72 sprung lower wheels and rigid cleat placements on their changing elastic envelope. Strain follows finite tension; no individual pin joints, derailment or free-span ground contact. Recoil hardware is provisional packaging; no complete-game acceptance.')
    binding['sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,Path(__file__),target,OUT/'assets/leviathan003_tensioned_tracks.glb',OUT/'physics/native_spec.json']}
    (OUT/'bindings.json').write_text(json.dumps(binding,indent=2)+'\n')
if __name__=='__main__':main()
