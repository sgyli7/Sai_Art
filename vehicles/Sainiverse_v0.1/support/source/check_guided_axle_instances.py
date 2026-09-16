"""Verify repeated source geometry, ownership and continuous inter-wheel bounds."""
from pathlib import Path
import gzip,json,hashlib,itertools
import numpy as np
from scipy.spatial import cKDTree
import mujoco,trimesh as tm
from suspension_physics import ROOT
OUT=ROOT/'candidates/r019_running_gear'
def main():
    path=OUT/'source/assembly.json.gz';oldpath=ROOT/'candidates/r016_modular/train_containers_first/source/assembly.json.gz'
    a=json.loads(gzip.decompress(path.read_bytes()));old=json.loads(gzip.decompress(oldpath.read_bytes()));byname={p['name']:p for p in a['parts']}
    unchanged=0
    for p in old['parts']:
        if p['name'].endswith(('_bogie_road_arm','_wheel_axle','_track_inner_frame')):continue
        assert byname[p['name']]==p,p['name'];unchanged+=1
    groups=[g for g in a['groups'] if '_bogie_' in g];assert len(groups)==12 and a['groups']==old['groups']
    reference=None;maximum_copy_delta=0.;maximum_bound_expansion=0.
    model=mujoco.MjModel.from_xml_path(str(OUT/'physics/suspended.xml'))
    for group in groups:
        pivot=np.array(a['groups'][group]);parts=[p for p in a['parts'] if p['group']==group]
        added=[p for p in parts if p['name'].startswith('r019_')]
        local=[np.array(p['vertices'])-pivot for p in added]
        assert len(added)==168
        if reference is None:reference=local
        else:
            for vertices,target in zip(local,reference):
                assert vertices.shape==target.shape
                delta=float(cKDTree(target).query(vertices)[0].max());assert delta<1e-5;maximum_copy_delta=max(maximum_copy_delta,delta)
        before=np.concatenate([np.array(p['vertices']) for p in old['parts'] if p['group']==group]);after=np.concatenate([np.array(p['vertices']) for p in parts]);growth=max(float((before.min(0)-after.min(0)).max()),float((after.max(0)-before.max(0)).max()));assert growth<1e-5;maximum_bound_expansion=max(maximum_bound_expansion,growth)
        for p in added:
            if p['motion']['kind']=='wheel_slide':assert model.body(p['physical_body']).id>0
    group=groups[0];pivot=np.array(a['groups'][group]);swept={}
    for side in [-1,1]:
        for index in [1,2,3]:
            pts=np.concatenate([np.array(p['vertices']) for p in a['parts'] if p['group']==group and p['motion']['kind'] in ['wheel','wheel_slide'] and p['motion']['index']==index and np.sign(np.mean(np.array(p['vertices'])[:,1])-pivot[1])==side])
            lo=pts.min(0);hi=pts.max(0);lo[2]-=.35;hi[2]+=.35;swept[f'{side}_{index}']=(lo,hi)
    pair_gaps={}
    for (n,(lo,hi)),(m,(otherlo,otherhi)) in itertools.combinations(swept.items(),2):
        gap=float(np.max(np.maximum(otherlo-hi,lo-otherhi)));assert gap>0.;pair_gaps[n+'/'+m]=gap
    scene=tm.load_scene(OUT/'assets/leviathan003_guided_axles.glb');tags=set();sliding_vertices=0
    for geometry in scene.geometry.values():
        uv=np.array(geometry.visual.uv);values=np.unique(np.round(uv[:,1],5));tags.update(values.tolist());sliding_vertices+=int(np.sum(abs(uv[:,1]-3)<1e-5))
    assert tags=={0.,1.,2.,3.} and sliding_vertices>0 and len(scene.geometry)==119
    report=dict(passed=True,unchanged_old_parts=unchanged,repeated_bogies=12,added_parts_per_bogie=168,maximum_added_copy_delta_m=maximum_copy_delta,maximum_bogie_bounds_expansion_m=maximum_bound_expansion,
        swept_inter_wheel_aabb_gaps_m=pair_gaps,glb_render_meshes=len(scene.geometry),glb_motion_tags=sorted(tags),glb_sliding_vertices=sliding_vertices,
        scope='All new bogie templates repeat at equal scale; old geometry outside the specified frame/axle/arm edits is identical. Swept AABB separation proves no inter-wheel/carrier collision for any independent ±0.35 m lower-wheel travel, within one rigid bogie. Does not cover belt deformation or whole-vehicle suspension sweeps.',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),path,oldpath,OUT/'assets/leviathan003_guided_axles.glb']})
    (OUT/'reports/guided_axle_instances.json').write_text(json.dumps(report,indent=2)+'\n');print('passed copies',maximum_copy_delta,'sliding GPU vertices',sliding_vertices)
if __name__=='__main__':main()
