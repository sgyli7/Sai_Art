"""Measure complete existing robot models for boarding clearance, not chassis only.

Uses compiled MuJoCo geometry frames, including all robot descendant visuals and
collision geometry. Sampled joint ranges are a design screen, not a continuous
motion certificate or a demonstrated locomotion envelope.
"""
from pathlib import Path
import hashlib, itertools, json
import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT.parents[3]
SIGNS = np.array(list(itertools.product([-1, 1], repeat=3)))

def measure(path, root_name, home=None):
    m = mujoco.MjModel.from_xml_path(str(path))
    d = mujoco.MjData(m)
    root = m.body(root_name).id
    descendants = {root}
    for b in range(root + 1, m.nbody):
        if m.body_parentid[b] in descendants:
            descendants.add(b)
    ids = np.array([g for g in range(m.ngeom) if m.geom_bodyid[g] in descendants])
    local = []
    for g in ids:
        kind = m.geom_type[g]; size = m.geom_size[g]
        if kind == mujoco.mjtGeom.mjGEOM_MESH:
            mesh = m.geom_dataid[g]; start = m.mesh_vertadr[mesh]
            verts = m.mesh_vert[start:start + m.mesh_vertnum[mesh]]
            lo, hi = verts.min(0), verts.max(0)
        else:
            if kind in [mujoco.mjtGeom.mjGEOM_BOX, mujoco.mjtGeom.mjGEOM_ELLIPSOID]:
                extent = size
            elif kind == mujoco.mjtGeom.mjGEOM_SPHERE:
                extent = np.repeat(size[0], 3)
            elif kind in [mujoco.mjtGeom.mjGEOM_CYLINDER, mujoco.mjtGeom.mjGEOM_CAPSULE]:
                extent = np.array([size[0], size[0], size[1] + (size[0] if kind == mujoco.mjtGeom.mjGEOM_CAPSULE else 0)])
            else:
                raise ValueError((g, kind))
            lo, hi = -extent, extent
        local.append((lo + hi) / 2 + SIGNS * (hi - lo) / 2)
    local = np.array(local)
    if home is not None:
        d.qpos[7:7 + len(home)] = home
    nominal_q = d.qpos.copy()
    def bounds():
        mujoco.mj_forward(m, d)
        pts = np.einsum('gij,gkj->gki', d.geom_xmat[ids].reshape(-1,3,3), local) + d.geom_xpos[ids,None,:]
        pts = (pts.reshape(-1,3) - d.xpos[root]) @ d.xmat[root].reshape(3,3)
        return np.array([pts.min(0), pts.max(0)])
    neutral = bounds()
    movable = [j for j in range(m.njnt) if m.jnt_bodyid[j] in descendants and m.jnt_limited[j] and m.jnt_type[j] in [mujoco.mjtJoint.mjJNT_HINGE, mujoco.mjtJoint.mjJNT_SLIDE]]
    rng = np.random.default_rng(3003); samples = [neutral]
    # One joint at each stop and 512 simultaneous samples; free root unchanged.
    for j in movable:
        for limit in m.jnt_range[j]:
            d.qpos[:] = nominal_q; d.qpos[m.jnt_qposadr[j]] = limit
            samples.append(bounds())
    for _ in range(512):
        d.qpos[:] = nominal_q
        for j in movable:
            d.qpos[m.jnt_qposadr[j]] = rng.uniform(*m.jnt_range[j])
        samples.append(bounds())
    samples = np.array(samples); sweep = np.array([samples[:,0].min(0), samples[:,1].max(0)])
    geometry_hash=hashlib.sha256()
    for array in [m.mesh_vert,m.mesh_face,m.geom_pos,m.geom_quat,m.geom_size,m.geom_type,m.geom_dataid,m.geom_bodyid,m.body_pos,m.body_quat,m.body_parentid,m.jnt_pos,m.jnt_axis,m.jnt_range]:
        geometry_hash.update(np.ascontiguousarray(array).tobytes())
    return dict(source=str(path), source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                compiled_geometry_sha256=geometry_hash.hexdigest(), measurement_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), root=root_name,
                bodies=len(descendants), geoms=len(ids), neutral_bounds_root_m=neutral.tolist(),
                neutral_dimensions_m=(neutral[1]-neutral[0]).tolist(), sampled_bounds_root_m=sweep.tolist(),
                sampled_dimensions_m=(sweep[1]-sweep[0]).tolist(), sampled_poses=len(samples),
                nominal_qpos=nominal_q.tolist(), method='Union of transformed local geom AABBs; conservative per pose. All robot visuals and contacts, no scene/item. Joint samples may include self-collision/non-operational poses; no proof of continuous extrema.')

def main():
    sai = PROJECTS/'RobotDesign/Sai_Agent_001/models/full/visual.xml'
    duck = PROJECTS/'microduck_rl/src/mjlab_microduck/robot/microduck/scene.xml'
    spec = json.loads((PROJECTS/'Robot_Godot_Sim2Sim/main/robots/microduck.json').read_text())
    report = dict(sai=measure(sai, 'chassis'), microduck=measure(duck,'trunk_base',spec['home']))
    out = ROOT/'candidates/r015_articulation/reports/boarding/robot_envelopes.json'
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({name:{k:v for k,v in item.items() if k in ['neutral_dimensions_m','sampled_dimensions_m','sampled_poses']} for name,item in report.items()},indent=2))

if __name__ == '__main__': main()
