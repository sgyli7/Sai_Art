"""Check the displayed tangent/arc path against the physical belt geometry."""
import json,subprocess,hashlib
from pathlib import Path
import numpy as np
from suspension_physics import ROOT
from track_tension import envelope
OUT=ROOT/'candidates/r021_track_tension/reports'
def point(a,b,f):
    return a[:2]+a[2]*np.array([np.cos(a[3]+b[1]*f),np.sin(a[3]+b[1]*f)]) if b[2]>.5 else a[:2]+(a[2:]-a[:2])*f
def main():
    source=OUT/'component_input.json';target=OUT/'path_component_godot.json'
    with (OUT/'path_component_godot.log').open('w') as log:subprocess.run(['/home/ethan/.local/bin/godot','--headless','--path','/home/ethan/Projects/Robot_Godot_Sim2Sim/main/results/leviathan003/runtime','--script',str(ROOT/'godot/track_path_bench.gd'),'--',str(source),str(target)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    inputs=json.loads(source.read_text());paths=json.loads(target.read_text());base=np.array(inputs['config']['support_circles_x_z_radius_m']);length_error=[];closure=[];clearance=[]
    for fixture,path in zip(inputs['fixtures'],paths):
        q=fixture['q'][:4];w=base.copy();w[1:4,1]+=q[:3];w[4,0]+=q[3];length_error.append(abs(path['length']-envelope(w)[0]));aa=np.array(path['a']);bb=np.array(path['b'])
        for i,(a,b) in enumerate(zip(aa,bb)):
            closure.append(float(np.linalg.norm(point(a,b,1)-point(aa[(i+1)%len(aa)],bb[(i+1)%len(bb)],0))))
            points=np.array([point(a,b,f) for f in np.linspace(0,1,25)]);clearance.append(float(np.min(np.linalg.norm(points[:,None,:]-w[None,:,:2],axis=2)-w[None,:,2])))
    raw=json.loads((OUT/'rough_godot.json').read_text());visual=json.loads((OUT/'tension_track_v1.json').read_text());delta={}
    for field in ['hull_positions','speed_m_s','wheel_travel_m','hitch_coordinates']:
        x=np.array([s[field] for s in raw['samples'][:len(visual['samples'])]]);y=np.array([s[field] for s in visual['samples']]);delta[field]=float(np.max(abs(x-y)));assert delta[field]<1e-8
    report=dict(paths=len(paths),maximum_length_error_m=max(length_error),maximum_segment_endpoint_gap_m=max(closure),minimum_expanded_circle_clearance_m=min(clearance),rendered_vs_headless_state_max_delta=delta,passed=bool(max(length_error)<3e-6 and max(closure)<3e-6 and min(clearance)>-3e-6),scope='Sampled exact path and rigid cleat reference-frame geometry. No individual hinge clearance, elastic bushing qualification, slack sag or free-span ground-contact claim.',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'godot/track_path.gd',target]})
    (OUT/'path_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
if __name__=='__main__':main()
