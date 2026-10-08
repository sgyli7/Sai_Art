"""Reject a compact drive architecture against the finite whole-body fit.

Keep the source leg lengths, reference crouch and steel frames unchanged.
Compare two lateral drives at knee/fold with one central ankle drive. A 130mm
central ankle bore approximately replaces the pull area of two 90mm bores;
the geometric lever arm and directional pressure limit still require checks.
All parts are custom proposals, not pressure- or strength-qualified hardware.
"""
from pathlib import Path
import copy
import hashlib
import itertools
import json
import collections
import math
import numpy as np
import manifold3d as mf
import trimesh as tr
import assemble_drives as a

O = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def solid(p):
    return mf.Manifold(mf.Mesh64(np.array(p['vertices_world_m'],dtype=np.float64,order='C'),
                                np.array(p['faces'],dtype=np.uint64,order='C')))


def main():
    S = json.loads((O/'candidate_scene.json').read_text())
    D = json.loads((O/'drive_envelope_screen.json').read_text())
    G = json.loads((O/'grounded_crouch_report.json').read_text())
    W = json.loads((O/'upper_fit_interface_scene.json').read_text())
    assert D['scene_sha256'] == G['source_sha256'] == sha(O/'candidate_scene.json')
    upper = mf.Manifold()
    for p in W['parts']:
        if p['source_group'] == 'upperbody_approximation':
            upper += solid(p)
    indices = list(range(0,121,10))
    poses = [G['poses'][i] for i in indices]
    hip = np.array(S['stations_world_m']['hip'])
    upperposes = [upper.translate(np.array(p['hip_world_m'])-hip) for p in poses]
    hip_half_spacing=W['hip_half_spacing_m']
    lateral_translation = np.array([0., hip_half_spacing-.5, 0.])
    base = [(p,solid(p)) for p in S['parts']]
    baseposes = [[(p,m.transform(np.array(pose['body_transforms'][p['body']])[:3,:4].copy()))
                  for p,m in base] for pose in poses]
    options = [copy.deepcopy(d['all_options'])for d in D['drives']]
    # Use finite material for the modified mounts instead of reusing the old
    # filled-outline fork/floor screen, which discarded valid new layouts.
    options[1]=[o for o in options[1]if o['b_world_m'][2]>.30]
    options[2]=[o for o in options[2]if .080<o['b_world_m'][2]<.230 and -.25<o['b_world_m'][0]<.40]
    for i in (0,1):
        for opt in options[i]:
            opt.update({'lateral_offsets_m':[-(.19,.20)[i],(.19,.20)[i]],
                        'mount_style':'compact_short_clevis','add_axial_spacers':True,
                        'mount_pin_radius_m':.0401,'mount_eye_outer_radius_m':.065,
                        'mount_ear_offset_m':.060,'mount_ear_thickness_m':.020,
                        'drive_eye_outer_radius_m':.065,'drive_eye_width_m':.068,
                        'barrel_eye_connector_radius_m':.030})
    for opt in options[1]:
        opt['lateral_offsets_m'] = [-.20,.20]
    # A knee drive that reaches down beside the ankle consumes the lower
    # folding space. Compare explicit front A / high-middle B attachments,
    # supported within the existing thigh and middle frame dimensions.
    knee_custom=[]
    target=options[0][0]['neutral_required_moment_Nm']
    c=np.array(S['stations_world_m']['knee'])
    for A,B,bore in itertools.product(([.09,.5,1.10],[.115,.5,1.11],[.14,.5,1.11]),
                                      ([.30,.5,.68],[.31,.5,.70],[.33,.5,.70]),(.150,.160)):
        A,B=np.array(A),np.array(B)
        lengths=[];arms=[]
        for angle in np.linspace(0,S['crouch_joint_deltas_deg'][0],31):
            R=tr.transformations.rotation_matrix(math.radians(angle),[0,1,0],c)
            moved=tr.transform_points(B[None],R)[0];length=float(np.linalg.norm(moved-A))
            lengths.append(length);arms.append(float(np.linalg.norm(np.cross(moved-c,(A-moved)/length))))
        stroke=max(lengths)-min(lengths)+.016;rod=bore/2
        pull=2*.85*30e6*math.pi*(bore*bore-rod*rod)/4
        ratio=pull*min(arms)/target
        if ratio<1.20 or min(lengths)<stroke+.368:continue
        opt=copy.deepcopy(options[0][0])
        opt.update({'a_world_m':A.tolist(),'b_world_m':B.tolist(),
                    'lateral_offsets_m':[-.215,.215],'bore_m':bore,'rod_m':rod,
                    'outside_diameter_m':bore+.024,'barrel_length_m':stroke+.205,
                    'proposed_stroke_m':stroke,'eye_length_min_m':min(lengths),'eye_length_max_m':max(lengths),
                    'min_arm_m':min(arms),'ideal_derated_pair_pull_N':pull,'nominal_min_ratio':ratio,
                    'mount_pin_radius_m':.0451,'mount_eye_outer_radius_m':.070,
                    'mount_ear_offset_m':.060,'mount_ear_thickness_m':.024,
                    'drive_eye_outer_radius_m':.065,'drive_eye_width_m':.080,
                    'barrel_eye_connector_radius_m':rod,'barrel_neck_start_m':.090,
                    'fixed_fork_away_vector':[0,0,1],
                    'architecture_note':'High middle-link attachment frees the distal folding space; thigh fork bridge points up behind the eye.'})
        knee_custom.append(opt)
    options[0]=knee_custom+options[0]
    for opt in options[2]:
        old_pair_pull = opt['ideal_derated_pair_pull_N']
        bore, rod = .130, .065
        single_pull = .85*30e6*math.pi*(bore*bore-rod*rod)/4
        opt.update({'lateral_offsets_m':[0.], 'bore_m':bore, 'rod_m':rod,
                    'outside_diameter_m':bore+.020,
                    'mount_pin_radius_m':.0451, 'mount_eye_outer_radius_m':.090,
                    'mount_ear_offset_m':.100, 'mount_ear_thickness_m':.024,
                    'drive_eye_outer_radius_m':.065, 'drive_eye_width_m':.080,
                    'barrel_eye_connector_radius_m':.0325,
                    'ideal_derated_total_pull_N':single_pull,
                    'ideal_derated_pair_pull_N':single_pull,
                    'nominal_min_ratio':opt['nominal_min_ratio']*single_pull/old_pair_pull,
                    'architecture':'one central ankle cylinder; twin knee/fold cylinders',
                    'sizing_scope':opt['sizing_scope']+' Central ankle uses one actual pressure area, not a fictitious pair.'})
    # A compact foot-side eye need not reuse the rejected lateral mount's
    # forward overhang. Explicit candidate eye positions remain above the
    # shared tray and are recomputed for real stroke and pressure area.
    custom=[]
    seed=next(o for o in options[2]if np.linalg.norm(np.array(o['a_world_m'])-
                  [.11329314441124688,.5,.48547791494856507])<1e-8 and
                  np.linalg.norm(np.array(o['b_world_m'])-[.3576390676354103,.5,.1658476690885259])<1e-8)
    placements=[(seed['a_world_m'],B)for B in
                ([.28763906763541036,.5,.1938476690885259],[.26,.5,.18])]
    # Lower the proximal ankle eye clear of the intermediate web. A modest
    # forward offset clears the short distal web without stretching the leg
    # or sending the eye up into the folded middle segment.
    placements += [(A,[.3576390676354103,.5,.1658476690885259])for A in
                   ([.04,.5,.39548764959244953],[.06,.5,.39548764959244953],
                    [.08,.5,.39548764959244953])]
    for A,B in placements:
        opt=copy.deepcopy(seed)
        A=np.array(A);B=np.array(B);c=np.array(S['stations_world_m']['ankle'])
        lengths=[];arms=[]
        for angle in np.linspace(0,S['crouch_joint_deltas_deg'][2],31):
            R=tr.transformations.rotation_matrix(math.radians(angle),[0,1,0],c)
            moved=tr.transform_points(B[None],R)[0]
            lengths.append(float(np.linalg.norm(moved-A)))
            arms.append(float(np.linalg.norm(np.cross(moved-c,(A-moved)/lengths[-1]))))
        stroke=max(lengths)-min(lengths)+.016
        if min(lengths)<stroke+.305:
            continue
        opt.update({'a_world_m':A.tolist(),'b_world_m':B.tolist(),'eye_length_min_m':min(lengths),
                    'eye_length_max_m':max(lengths),'proposed_stroke_m':stroke,
                    'barrel_length_m':stroke+.205,'min_arm_m':min(arms),
                    'nominal_min_ratio':opt['ideal_derated_total_pull_N']*min(arms)/opt['neutral_required_moment_Nm'],
                    'refined_foot_eye':True})
        if opt['nominal_min_ratio']>=1.20:
            custom.append(opt)
    options[2]=custom+options[2]

    def transformed(scene):
        materials = [(p,solid(p)) for p in scene['parts'][len(base):]]
        result = []
        for pose in poses:
            T = {k:np.array(t) for k,t in pose['body_transforms'].items()}
            for d in scene['drivers']:
                A,B = np.array(d['A_neutral_world_m']),np.array(d['B_neutral_world_m'])
                aa = tr.transform_points(A[None],T[d['parent']])[0]
                bb = tr.transform_points(B[None],T[d['child']])[0]
                R = tr.geometry.align_vectors(B-A,bb-aa)[:3,:3]
                for owner,now,old in ((d['barrel_body'],aa,A),(d['rod_body'],bb,B)):
                    tt=np.eye(4);tt[:3,:3]=R;tt[:3,3]=now-R@old;T[owner]=tt
            result.append([(p,m.transform(T[p['body']][:3,:4].copy())) for p,m in materials])
        return result

    def collision(rows, others=()):
        allrows = rows + list(others)
        bounds = [np.array(m.bounding_box()).reshape(2,3) for p,m in allrows]
        for i,(pa,ma) in enumerate(rows):
            if bounds[i][0,2] < -1e-8:
                return ('floor',pa['name'])
            for k in range(i+1,len(allrows)):
                pb,mb=allrows[k]
                if pa['body']==pb['body']:
                    continue
                if np.any(bounds[i][1]<bounds[k][0]) or np.any(bounds[k][1]<bounds[i][0]):
                    continue
                if (ma^mb).volume()>1e-10:
                    return (pa['name'],pb['name'])
        return None

    def upper_collision(rows, u):
        ub=np.array(u.bounding_box()).reshape(2,3)
        for p,m in rows:
            placed=m.translate(lateral_translation)
            bb=np.array(placed.bounding_box()).reshape(2,3)
            if bb[0,1] <= 0:
                # Reject centreline encroachment, then verify all opposite-leg
                # pairs explicitly in the full 121-pose checker after selection.
                return ('centreline',p['name'])
            if np.any(bb[1]<ub[0]) or np.any(ub[1]<bb[0]):
                continue
            if (placed^u).volume()>1e-10:
                return ('upperbody',p['name'])
        return None

    for phase,(rows,u) in enumerate(zip(baseposes,upperposes)):
        failure=upper_collision(rows,u)
        if failure:
            raise ValueError(('Base frame already conflicts with upperbody',indices[phase],failure))

    kept,counts=[],[]
    for joint,opts in enumerate(options):
        rows_keep=[];bad=collections.Counter()
        for n,opt in enumerate(opts):
            own=[None]*3;own[joint]=opt
            scene=a.build(own);rows=transformed(scene)
            fail=None
            for r,b,u in zip(rows,baseposes,upperposes):
                fail=collision(r,b) or upper_collision(r,u)
                if fail:
                    break
            if fail:
                bad[fail]+=1
            else:
                rows_keep.append((opt,rows,n))
            if n%10==0:
                print('COMPACT',joint,n,'kept',len(rows_keep),flush=True)
        kept.append(rows_keep)
        counts.append({'joint':joint,'tested':len(opts),'kept':len(rows_keep),
                       'rejections':[{'pair':list(k),'count':v}for k,v in bad.items()]})
        print('COMPACT_JOINT',joint,'kept',len(rows_keep),flush=True)
    selected=None;tried=0;pair_bad=collections.Counter()
    for combo in itertools.product(*kept):
        tried+=1
        fail=None
        for phase in range(len(poses)):
            rows=sum([c[1][phase]for c in combo],[])
            fail=collision(rows)
            if fail:
                break
        if fail:
            pair_bad[fail]+=1
        else:
            selected=combo
            break
    report={'scene_sha256':D['scene_sha256'],'whole_fit_sha256':sha(O/'upper_fit_interface_scene.json'),
            'selector_sha256':sha(Path(__file__)),'assembly_builder_sha256':sha(Path(a.__file__)),
            'options_sha256':sha(O/'drive_envelope_screen.json'),
            'pose_indices':indices,'per_joint':counts,'combinations_tried':tried,
            'combination_rejections':[{'pair':list(k),'count':v}for k,v in pair_bad.items()],
            'selection_found':selected is not None,'physical_accepted':False,
            'architecture':{'hip_half_spacing_m':hip_half_spacing,'knee_lateral_offsets_m':[-.19,.19],
                            'fold_lateral_offsets_m':[-.20,.20],
                            'ankle_lateral_offsets_m':[0.],'ankle_bore_m':.13},
            'scope':'13-pose finite material rejection, including C15 upperbody and centreline. '
                    'Must run full 121-pose checks, drive loading and install a real hip attachment.'}
    (O/'compact_selection_report.json').write_text(json.dumps(report,indent=2)+'\n')
    choice={'scene_sha256':D['scene_sha256'],'selection':None,'physical_accepted':False,
            'whole_fit_hip_half_spacing_m':hip_half_spacing}
    if selected:
        choice['selection']={'options':[c[0]for c in selected],'indices':[c[2]for c in selected],
                             'tested_pose_count':len(poses)}
    (O/'compact_drive_selection.json').write_text(json.dumps(choice,indent=2)+'\n')
    print('COMPACT_SET',tried,'selected',selected is not None,flush=True)


if __name__=='__main__':
    main()
