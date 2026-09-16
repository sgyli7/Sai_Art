"""Seeded derivative-free policy training through actual MuJoCo episodes.
A 3-parameter feedback policy, not an untrained NN or a prerecorded trajectory.
"""
from physics import *
import argparse
p=argparse.ArgumentParser();p.add_argument('--generations',type=int,default=4);a=p.parse_args()
build();rng=np.random.default_rng(3003);mean=np.log(DEFAULT);sigma=np.array([.5,.5,.4]);history=[];best=(float('inf'),DEFAULT)
for generation in range(a.generations):
    candidates=[np.exp(mean)]+[np.clip(np.exp(mean+rng.normal(size=3)*sigma),[.3,.3,.4],[5,5,6]) for _ in range(7)]
    scores=[]
    for index,policy in enumerate(candidates):
        results=[episode(policy,seed=100+generation,seconds=75,mode=mode)[0] for mode in ['turn','straight']]
        loss=sum(r['loss'] for r in results)/len(results);scores.append(loss)
        history.append(dict(generation=generation,index=index,policy=policy.tolist(),loss=float(loss),episodes=results))
        if loss<best[0]:best=(loss,policy)
        print(generation,index,round(loss,5),policy,flush=True)
    elite=np.log(np.array(candidates)[np.argsort(scores)[:3]]);mean=elite.mean(0);sigma=np.maximum(.1,elite.std(0))
policy=best[1];result=dict(policy_type='bounded parametric feedback; cross-entropy policy search in MuJoCo',weights=policy.tolist(),parameters=['speed_error_gain','yaw_alignment_gain','lateral_velocity_gain'],training_seed=3003,training_episodes=len(history)*2,training_sim_seconds=len(history)*150,loss=float(best[0]),observations=['front_speed_m_s','hull_angular_velocity','hull_heading','contact_velocity','command_speed','command_yaw'],actions='bounded traction and lateral patch forces; poses always integrated by MuJoCo',physics_sha256=__import__('hashlib').sha256((ROOT/'assets/physics.json').read_bytes()).hexdigest())
(ROOT/'training/policy.json').write_text(json.dumps(result,indent=2));(ROOT/'training/history.json').write_text(json.dumps(history,indent=2))
validation=[]
for seed in [200,201,202,203,204]:
    for mode in ['straight','turn']:
        r,rows=episode(policy,seed=seed,seconds=100,mode=mode,record=True);validation.append(r)
        (ROOT/'reports'/f'mujoco_{mode}_{seed}.json').write_text(json.dumps({'result':r,'samples':rows},indent=2))
summary=dict(policy=result,holdout=validation,passed=all(r['min_upright']>.98 and (r['max_speed_kmh']>=99.9 if r['mode']=='straight' else abs(r['final_speed_kmh'])<.1) for r in validation))
(ROOT/'reports/training_validation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
