"""Resolve static inter-group material overlap in the unaccepted Art draft.

This is finite geometric relief only. It is not recovered hidden geometry,
machined bearing/drill design, articulation-range or load validation.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import manifold3d as mf
import trimesh as tr

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'source'/'reference_scene.json'
S=json.loads(P.read_text())
raw=ROOT/'source'/'reference_scene_untrimmed.json'
raw.write_bytes(P.read_bytes())
def solid(p):return mf.Manifold(mf.Mesh64(np.array(p['vertices'],dtype=np.float64,order='C'),
                                        np.array(p['faces'],dtype=np.uint64,order='C')))
order=['torso','pelvis','near_upper_arm','far_upper_arm','near_forearm','far_forearm',
       'near_thigh','far_thigh','near_middle','far_middle','near_distal','far_distal',
       'near_foot','far_foot']
resolved=[];prior=mf.Manifold();edits=[];omitted=[]
for body in order:
    members=[p for p in S['parts'] if p['body']==body]
    group=[]
    cutter=prior.minkowski_sum(mf.Manifold.cube([.002]*3,True)) if not prior.is_empty() else prior
    for p in members:
        before=solid(p);after=before-cutter
        assert after.status()==mf.Error.NoError,p['name']
        if after.is_empty() or after.volume()<1e-10:
            omitted.append({'name':p['name'],'role':p['geometry_role'],'reason':'Fully inside a preceding group in the single-view draft.'})
            continue
        if before.volume()-after.volume()>1e-10:
            edits.append({'name':p['name'],'removed_volume_layout_units_cubed':before.volume()-after.volume()})
            m=after.to_mesh64();p['vertices']=np.asarray(m.vert_properties[:,:3]).tolist()
            p['faces']=np.asarray(m.tri_verts).tolist();p['static_relief']=True
        resolved.append(p);group.append(after)
    if group:prior+=mf.Manifold.batch_boolean(group,mf.OpType.Add)
S['parts']=resolved
S['static_clearance_record']={'untrimmed_source_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
                            'clearance_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                            'assembly_clearance_layout_units':.002,'edited_parts':edits,
                            'omitted_parts':omitted,'manufacturing_fit':False,'motion_range_checked':False}
P.write_text(json.dumps(S,indent=2)+'\n')
exchange=tr.Scene()
to_y_up=np.array([[1.,0.,0.,0.],[0.,0.,1.,0.],[0.,-1.,0.,0.],[0.,0.,0.,1.]])
for p in resolved:
    mesh=tr.Trimesh(p['vertices'],p['faces'],process=False);mesh.apply_transform(to_y_up)
    mesh.visual.vertex_colors=np.array([p['shade']*255]*3+[255],dtype=np.uint8)
    exchange.add_geometry(mesh,node_name=p['name'],geom_name=p['name'])
(ROOT/'source'/'reference_geometry.glb').write_bytes(exchange.export(file_type='glb'))
print('STATIC_ART_RELIEF',len(edits),'edited;',len(omitted),'omitted; no manufacturing fit assertion',flush=True)
