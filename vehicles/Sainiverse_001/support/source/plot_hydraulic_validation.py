"""Standalone measured fixture plots; preserve complete raw records."""
from pathlib import Path
import json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from suspension_physics import ROOT
OUT=ROOT/'candidates/r020_hydraulics/reports'
def main():
    files=[OUT/(name+'_'+engine+'.json') for name in ['straight100','rough'] for engine in ['mujoco','godot']]
    records={p.stem:json.loads(p.read_text()) for p in files}
    fig,axes=plt.subplots(2,2,figsize=(12.5,7.3),layout='constrained')
    for engine,color,style in [('mujoco','#156d90','-'),('godot','#e78936','--')]:
        straight=records['straight100_'+engine]['samples'];rough=records['rough_'+engine]['samples'];t=np.array([s['time'] for s in rough])
        axes[0,0].plot([s['time'] for s in straight],[s['speed_m_s']*3.6 for s in straight],style,color=color,label=engine)
        axes[0,1].plot(t,[max(s['hydraulics']['upper_pressure_Pa'])/1e6 for s in rough],style,color=color,label=engine)
        axes[1,0].plot(t,[s['hydraulics']['pump_power_W']/1000 for s in rough],style,color=color,label=engine)
        axes[1,1].plot(t,[s['imu_vertical_accel_m_s2'][0] for s in rough],style,color=color,label=engine)
    axes[0,0].axhline(100,color='#888888',lw=.7);axes[0,0].set(title='Flat route: accelerate / brake',ylabel='Speed (km/h)')
    axes[0,1].axhline(70,color='#aa4444',lw=1,label='Pressure cap');axes[0,1].set(title='Rough route: maximum bank pressure',ylabel='Gauge pressure (MPa)',ylim=(0,75))
    axes[1,0].set(title='Rough route: leveling header draw',ylabel='Hydraulic supply power (kW)')
    axes[1,1].set(title='Front measuring point: unresolved shock agreement',ylabel='Vertical acceleration (m/s²)')
    for ax in axes.flat:ax.set_xlabel('Simulation time (s)');ax.grid(alpha=.18);ax.legend(fontsize=8)
    fig.suptitle('Leviathan 003 · r020 finite hydraulic candidate',fontsize=16)
    fig.text(.5,-.018,'Curves sampled at 10 Hz; peak gates use 200 Hz records. State transfer passes; ride comfort is not accepted.',ha='center',fontsize=10)
    fig.savefig(OUT/'hydraulic_validation.png',dpi=150,bbox_inches='tight');fig.savefig(OUT/'hydraulic_validation.pdf',bbox_inches='tight');plt.close(fig)
    data=dict(source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[Path(__file__)]},scope='Plots of measured native and MuJoCo data at 10 Hz, not invented mechanical imagery or all-step peak traces.')
    (OUT/'hydraulic_plot_sources.json').write_text(json.dumps(data,indent=2)+'\n')
if __name__=='__main__':main()
