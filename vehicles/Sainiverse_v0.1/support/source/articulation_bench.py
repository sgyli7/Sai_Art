"""Native zero-gravity articulation test fixture; not a driving evaluation.

The existing rear hull mass/inertia loads a real slider and three physical
rotary joints. Finite actuator forces change configuration; no pose replay.
"""
from pathlib import Path
import json, math, time
import xml.etree.ElementTree as E
import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'design/articulation_candidate.json').read_text())
P=json.loads((ROOT/'assets/physics.json').read_text())
OUT=ROOT/'reports/articulation_r015/bench'
SCHEDULE=[(15,[4,0,0,0]),(75,[4,45,0,0]),(135,[4,-45,0,0]),
          (175,[4,0,0,0]),(195,[4,0,8,0]),(215,[4,0,-8,0]),
          (235,[4,0,0,6]),(255,[4,0,0,-6]),(275,[4,0,0,0]),(300,[0,0,0,0])]

def target(t):
    q=next((q for end,q in SCHEDULE if t<end),SCHEDULE[-1][1])
    return np.array([q[0],*np.radians(q[1:])])

def build():
    root=E.Element('mujoco',model='Leviathan003_articulation_fixture')
    E.SubElement(root,'compiler',angle='radian')
    E.SubElement(root,'option',gravity='0 0 0',timestep='.005',integrator='implicitfast',iterations='50',tolerance='1e-10')
    w=E.SubElement(root,'worldbody')
    base=E.SubElement(w,'body',name='fixture_front',pos='-21 0 6.5')
    parent=base
    yaw=np.array(C['reference_anchor_m'])
    pitch=yaw+np.array(C['pitch_axis_offset_m'])
    roll=pitch+np.array(C['roll_axis_offset_from_pitch_m'])
    rear=np.array([P['hull_centers_x'][1],0,P['com_z']])
    names=['extension','yaw','pitch','roll']
    axes=['-1 0 0','0 0 1','0 1 0','1 0 0']
    limits=[C['extension_m'],*[[math.radians(x) for x in C[k+'_degrees']] for k in names[1:]]]
    for i,name in enumerate(names):
        offset=np.zeros(3) if i<2 else pitch-yaw if i==2 else rear-pitch
        b=E.SubElement(parent,'body',name=name+'_body',pos=' '.join(map(str,offset)))
        E.SubElement(b,'joint',name=name,type='slide' if i==0 else 'hinge',axis=axes[i],
                     pos='0 0 0' if i<3 else ' '.join(map(str,roll-rear)),limited='true',range=' '.join(map(str,limits[i])),
                     solreflimit='.01 1',solimplimit='.99 .999 .001')
        mass=C['moving_carrier_mass_kg'][i] if i<3 else P['mass_kg'][1]
        inertia=[C['carrier_inertia_kg_m2'][i]]*3 if i<3 else P['inertia_diagonal']
        E.SubElement(b,'inertial',pos='0 0 0',mass=str(mass),diaginertia=' '.join(map(str,inertia)))
        parent=b
    actuator=E.SubElement(root,'actuator')
    force=[C['extension_force_limit_N'],*C['rotation_torque_limits_Nm']]
    for name,f in zip(names,force):
        E.SubElement(actuator,'motor',name=name+'_drive',joint=name,ctrllimited='true',ctrlrange=f'{-f} {f}')
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'fixture.xml').write_text(E.tostring(root,encoding='unicode'))
    return mujoco.MjModel.from_xml_path(str(OUT/'fixture.xml'))

def main():
    m=build();d=mujoco.MjData(m)
    kp=np.array([C['extension_kp_N_per_m'],*C['rotation_kp_Nm_per_rad']])
    kd=np.array([C['extension_kd_Ns_per_m'],*C['rotation_kd_Nms_per_rad']])
    caps=np.array([C['extension_force_limit_N'],*C['rotation_torque_limits_Nm']])
    samples=[];started=time.monotonic()
    for step in range(60000):
        goal=target(d.time)
        d.ctrl[:]=np.clip(kp*(goal-d.qpos)-kd*d.qvel,-caps,caps)
        mujoco.mj_step(m,d)
        if step%100==99:
            samples.append(dict(time=d.time,position=d.qpos.tolist(),velocity=d.qvel.tolist(),force=d.ctrl.tolist(),target=goal.tolist()))
    result=dict(engine='MuJoCo '+mujoco.__version__,gravity=[0,0,0],simulation_s=d.time,
                wall_s=time.monotonic()-started,samples=samples,
                scope='Fixed-front zero-gravity joint fixture with actual previous rear mass/inertia, '
                      'three provisional carrier inertias and finite actuators. No ground contact, '
                      'vehicle driving, visual clearance, hardware strength or trained policy claim.')
    (OUT/'mujoco.json').write_text(json.dumps(result,indent=2)+'\n')
    for end,goal in SCHEDULE:
        s=min(samples,key=lambda s:abs(s['time']-(end-.5)))
        print(end, 'actual',np.round([s['position'][0],*np.degrees(s['position'][1:])],4),'target',goal)

if __name__=='__main__':main()
