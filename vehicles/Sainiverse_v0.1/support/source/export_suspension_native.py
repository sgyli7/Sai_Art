"""Export physical frames and coefficients for an independent native Jolt run."""
import hashlib,json
import mujoco
import numpy as np
from suspension_physics import Env,ROOT,C,A,OLD

def export_environment(env,out):
    m,d=env.m,env.d;nodes=[];joints=[]
    for i in range(1,m.nbody):
        assert np.allclose(m.body_iquat[i],[1,0,0,0])
        nodes.append(dict(name=m.body(i).name,parent=m.body(int(m.body_parentid[i])).name,
                          position=d.xpos[i].tolist(),mass=float(m.body_mass[i]),
                          inertia=m.body_inertia[i].tolist(),com=m.body_ipos[i].tolist()))
    for j in range(m.njnt):
        if m.jnt_type[j]==mujoco.mjtJoint.mjJNT_FREE:continue
        body=int(m.jnt_bodyid[j]);parent=int(m.body_parentid[body]);dof=int(m.jnt_dofadr[j]);qa=int(m.jnt_qposadr[j])
        joints.append(dict(name=m.joint(j).name,body=m.body(body).name,parent=m.body(parent).name,
                           kind='slide' if m.jnt_type[j]==mujoco.mjtJoint.mjJNT_SLIDE else 'hinge',
                           anchor=d.xanchor[j].tolist(),axis=d.xaxis[j].tolist(),
                           limits=m.jnt_range[j].tolist(),stiffness=float(m.jnt_stiffness[j]),
                           damping=float(m.dof_damping[dof]),springref=float(m.qpos_spring[qa])))
    out.write_text(json.dumps(dict(bodies=nodes,joints=joints,contact=env.manifest,config={**C,**env.manifest.get('config_overrides',{}),'total_mass_kg':env.total_mass},articulation=A,
                                  steering_inertia=env.steering_inertia,
                                  source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'source/suspension_physics.py',ROOT/'design/suspension_candidate.json',ROOT/'source/export_suspension_native.py']}),indent=2)+'\n')
    print(out, len(nodes),len(joints))

def main():
    export_environment(Env(),ROOT/'candidates/r015_articulation/physics/native_spec.json')

if __name__=='__main__':main()
