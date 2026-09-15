"""Independent full train motion with actual idler and belt forces."""
import argparse,json,concurrent.futures
import numpy as np
import check_running_gear_contact as cases
from suspension_physics import ROOT
OUT=ROOT/'candidates/r021_track_tension'
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['mujoco','godot','compare']);a=p.parse_args();cases.OUT=OUT
    if a.mode=='mujoco':
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
            for row in pool.map(cases.evaluate,cases.CASES):print(row,flush=True)
    elif a.mode=='godot':cases.native()
    else:
        cases.compare();rows={}
        for name in cases.CASES:
            raw={engine:json.loads((OUT/'reports'/(name+'_'+engine+'.json')).read_text()) for engine in ['mujoco','godot']};row={}
            for engine,data in raw.items():
                track=data['samples'][-1]['track_tension'];q=np.array([s['track_tension']['coordinates_m'] for s in data['samples']]);minimum_gap=float(np.min(np.sqrt((1.6+q[:,:,3])**2+(1.25-q[:,:,2])**2)-1.68))
                assert track['max_tension_N']<=1.5e6+1e-5 and track['max_recoil_force_N']<=1.2e6+1e-5
                assert track['idler_range_m'][0]>-.32 and track['idler_range_m'][1]<.24
                assert minimum_gap>0,(name,engine,minimum_gap)
                h=data['samples'][-1]['hydraulics'];assert h['valid'] and h['max_pressure_Pa']<=70e6*(1+1e-10)
                row[engine]=dict(final_track_summary={k:v for k,v in track.items() if k not in ['coordinates_m','lengths_m','tensions_N','idler_recoil_forces_N']},sampled_min_idler_neighbor_circumference_gap_m=minimum_gap)
            for field,scale in [('coordinates_m',.56),('lengths_m',.56),('tensions_N',1.5e6)]:
                x=np.array([s['track_tension'][field] for s in raw['mujoco']['samples']]);y=np.array([s['track_tension'][field] for s in raw['godot']['samples']]);error=float(np.sqrt(np.mean((x-y)**2)));row[field+'_rmse']=error;assert error/scale<.03,(name,field,error)
            rows[name]=row
        (OUT/'reports/track_vehicle_validation.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
