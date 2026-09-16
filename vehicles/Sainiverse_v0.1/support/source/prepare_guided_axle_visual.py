"""Use the same exterior frames with the newly authored sliding axle parts."""
from pathlib import Path
import hashlib,json
from suspension_physics import ROOT
OUT=ROOT/'candidates/r019_running_gear'
def main():
    bindings=json.loads((ROOT/'candidates/r018_visual_suspension/bindings.json').read_text())
    bindings['glb']=str(OUT/'assets/leviathan003_guided_axles.glb')
    bindings['native_blend']=str(OUT/'source/Leviathan_003_guided_axles.blend')
    bindings['shader']=str(OUT/'assets/guided_axles.gdshader')
    bindings['scope']='21 exterior physical groups, 72 independent wheel/axle carriers and their cylinder pistons. Wheels rotate by local odometry; axle, crosshead, rods and pistons only translate with their named physical wheel body. Belt remains the original fixed loop until tensioner mechanics is implemented. Custom hydraulic packaging is not a qualified component selection.'
    shader=(ROOT/'godot/sprung_wheel.gdshader').read_text()
    shader=shader.replace('if(UV.y<-.5){','if(UV.y<-1.5){\n        int index=clamp(int(round(UV.x)),1,3);\n        VERTEX.z+=offsets[index-1];\n    }else if(UV.y<-.5){')
    (OUT/'assets/guided_axles.gdshader').write_text(shader)
    files=[OUT/'source/assembly.json.gz',OUT/'assets/leviathan003_guided_axles.glb',OUT/'assets/guided_axles.gdshader',Path(__file__)]
    bindings['sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (OUT/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')
if __name__=='__main__':main()
