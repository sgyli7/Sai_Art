"""Finite differences, balance identities, and native scalar force parity."""
from pathlib import Path
import json,subprocess,hashlib
import numpy as np
from suspension_physics import ROOT
from track_tension import envelope,envelopes,TrackTension
OUT=ROOT/'candidates/r021_track_tension'
def main():
    c=json.loads((OUT/'physics/parameters.json').read_text())['track_tension'];rng=np.random.default_rng(21003);base=np.array(c['support_circles_x_z_radius_m']);n=128
    q=rng.uniform([-.35,-.35,-.35,-.32],[.35,.35,.35,.24],(n,4));dq=rng.uniform(-2,2,(n,4));shapes=np.broadcast_to(base,(n,5,3)).copy();shapes[:,1:4,1]+=q[:,:3];shapes[:,4,0]+=q[:,3]
    lengths,grads=envelopes(shapes);errors=[];balance=[];torque=[];batch=[]
    for w,length,g in zip(shapes,lengths,grads):
        reference,gradient,_=envelope(w);batch.append(max(abs(reference-length),float(np.max(abs(gradient-g)))))
        for wi,axis in [(1,1),(2,1),(3,1),(4,0)]:
            a=w.copy();b=w.copy();a[wi,axis]+=1e-6;b[wi,axis]-=1e-6;fd=(envelope(a)[0]-envelope(b)[0])/2e-6;errors.append(abs(fd-g[wi,axis]))
        balance.append(float(np.linalg.norm(g.sum(axis=0))));torque.append(abs(float(np.sum(w[:,0]*g[:,1]-w[:,1]*g[:,0]))))
    # Each row drives 24 independent banks at deliberately varied coordinates.
    fixtures=[];expected=[];bank=TrackTension(c)
    for start in range(100):
        ids=(np.arange(24)+start)%n;row=dict(q=q[ids].ravel().tolist(),dq=dq[ids].ravel().tolist());fixtures.append(row)
        f=bank.step(row['q'],row['dq'],.005);expected.append(dict(forces=f.tolist(),state=bank.record()))
    input=OUT/'reports/component_input.json';output=OUT/'reports/component_godot.json';input.write_text(json.dumps(dict(config=c,fixtures=fixtures)))
    with (OUT/'reports/component_godot.log').open('w') as log:subprocess.run(['/home/ethan/.local/bin/godot','--headless','--path','/home/ethan/Projects/Robot_Godot_Sim2Sim/main/results/leviathan003/runtime','--script',str(ROOT/'godot/track_component_bench.gd'),'--',str(input),str(output)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    native=json.loads(output.read_text());delta=float(np.max(abs(np.array([r['forces'] for r in expected])-np.array([r['forces'] for r in native]))))
    report=dict(states=n,finite_difference_max_error=max(errors),force_gradient_balance_error=max(balance),torque_gradient_error=max(torque),batch_scalar_max_error=max(batch),native_force_max_delta_N=delta,max_tension_N=bank.max_tension,max_recoil_force_N=bank.max_idler_force,slack_bank_steps=bank.slack_steps,
        passed=bool(max(errors)<1e-7 and max(balance)<1e-12 and max(torque)<1e-11 and max(batch)<1e-12 and delta<100. and bank.max_tension<=c['tension_limit_N'] and bank.max_idler_force<=c['recoil_force_limit_N']),
        scope='Prescribed-coordinate force and geometric identities, including slack/force caps. Float32 native geometry accounts for a bounded force parity tolerance. Not physical vehicle motion or hardware clearance.',source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'source/track_tension.py',ROOT/'godot/track_tension.gd',input]})
    (OUT/'reports/component_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['passed']
if __name__=='__main__':main()
