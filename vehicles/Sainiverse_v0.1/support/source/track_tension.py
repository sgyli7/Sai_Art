"""Conservative taut-disc envelope and finite passive recoil forces.

One independent +X idler and three lower-wheel slides per belt. This is an
elastic tendon reduction, not discrete chain-pin/soil contact simulation.
"""
import math
import numpy as np

def envelope(wheels):
    """Exact perimeter integral of max(c_i dot n + r_i), and its gradient."""
    w=np.asarray(wheels,dtype=float);angles=[0.,2*math.pi]
    for i in range(len(w)):
        for j in range(i):
            d=w[i,:2]-w[j,:2];length=math.hypot(*d)
            if length<=abs(w[j,2]-w[i,2]):continue
            a=math.atan2(d[1],d[0]);b=math.acos((w[j,2]-w[i,2])/length)
            angles.extend([(a-b)%(2*math.pi),(a+b)%(2*math.pi)])
    angles=sorted(angles);gradient=np.zeros((len(w),2));perimeter=0.;arcs=[]
    for a,b in zip(angles,angles[1:]):
        if b-a<1e-12:continue
        mid=(a+b)/2;n=np.array([math.cos(mid),math.sin(mid)])
        owner=int(np.argmax(w[:,:2]@n+w[:,2]));integral=np.array([math.sin(b)-math.sin(a),math.cos(a)-math.cos(b)])
        gradient[owner]+=integral;perimeter+=float(w[owner,:2]@integral+w[owner,2]*(b-a))
        if arcs and arcs[-1][0]==owner:arcs[-1][2]=b
        else:arcs.append([owner,a,b])
    return perimeter,gradient,arcs

def envelopes(w):
    """Batch equivalent of envelope; no fixed-angle discretization."""
    w=np.asarray(w,dtype=float);count,n,_=w.shape;i,j=np.tril_indices(n,-1)
    d=w[:,i,:2]-w[:,j,:2];length=np.linalg.norm(d,axis=2);ratio=(w[:,j,2]-w[:,i,2])/np.maximum(length,1e-30)
    a=np.arctan2(d[:,:,1],d[:,:,0]);b=np.arccos(np.clip(ratio,-1,1));valid=(length>np.abs(w[:,j,2]-w[:,i,2]))
    angles=np.sort(np.concatenate([np.zeros((count,1)),np.full((count,1),2*np.pi),np.where(valid,(a-b)%(2*np.pi),0),np.where(valid,(a+b)%(2*np.pi),0)],axis=1),axis=1)
    mid=(angles[:,1:]+angles[:,:-1])/2;normal=np.stack([np.cos(mid),np.sin(mid)],axis=2)
    owner=np.argmax(np.einsum('bni,bsi->bsn',w[:,:,:2],normal)+w[:,None,:,2],axis=2)
    integral=np.stack([np.sin(angles[:,1:])-np.sin(angles[:,:-1]),np.cos(angles[:,:-1])-np.cos(angles[:,1:])],axis=2)
    gradient=np.zeros((count,n,2));rows=np.arange(count)[:,None];np.add.at(gradient,(rows,owner),integral)
    selected=w[rows,owner];perimeter=np.sum(np.sum(selected[:,:,:2]*integral,axis=2)+selected[:,:,2]*np.diff(angles,axis=1),axis=1)
    return perimeter,gradient

class TrackTension:
    def __init__(self,config):
        self.c=config;self.names=[name for belt in config['belts'] for name in belt['joints']]
        self.base=np.array(config['support_circles_x_z_radius_m']);self.lengths=[];self.tensions=[];self.idler_forces=[];self.q=[]
        self.max_tension=0.;self.max_extension=0.;self.min_extension=math.inf;self.max_idler_force=0.;self.min_idler=math.inf;self.max_idler=-math.inf;self.slack_steps=0;self.dissipated_J=0.
    def step(self,q,dq,dt):
        c=self.c;travel=np.asarray(q).reshape(-1,4);rate=np.asarray(dq).reshape(-1,4);self.q=travel.tolist()
        w=np.broadcast_to(self.base,(len(travel),*self.base.shape)).copy();w[:,1:4,1]+=travel[:,:3];w[:,4,0]+=travel[:,3]
        length,gradient=envelopes(w);jac=np.c_[gradient[:,1:4,1],gradient[:,4,0]];ldot=np.sum(jac*rate,axis=1);extension=length-c['natural_length_m']
        elastic=np.minimum(c['belt_stiffness_N_m']*np.maximum(extension,0.),c['tension_limit_N'])
        tension=np.where(extension>0,np.clip(elastic+c['belt_damping_Ns_m']*ldot,0.,c['tension_limit_N']),0.)
        spring=np.clip(c['recoil_preload_N']-c['recoil_stiffness_N_m']*travel[:,3],0.,c['recoil_force_limit_N'])
        push=np.clip(spring-c['recoil_damping_Ns_m']*rate[:,3],0.,c['recoil_force_limit_N'])
        forces=-tension[:,None]*jac;forces[:,3]+=push
        self.dissipated_J+=float(np.sum(np.maximum(0.,(tension-elastic)*ldot)+np.maximum(0.,-(push-spring)*rate[:,3])))*dt
        self.lengths=length.tolist();self.tensions=tension.tolist();self.idler_forces=push.tolist()
        self.max_tension=max(self.max_tension,float(tension.max()));self.max_extension=max(self.max_extension,float(extension.max()));self.min_extension=min(self.min_extension,float(extension.min()))
        self.max_idler_force=max(self.max_idler_force,float(push.max()));self.min_idler=min(self.min_idler,float(travel[:,3].min()));self.max_idler=max(self.max_idler,float(travel[:,3].max()));self.slack_steps+=int(np.sum(extension<=0))
        return forces.ravel()
    def record(self):
        return dict(lengths_m=self.lengths,tensions_N=self.tensions,idler_recoil_forces_N=self.idler_forces,coordinates_m=self.q,max_tension_N=self.max_tension,extension_range_m=[self.min_extension,self.max_extension],idler_range_m=[self.min_idler,self.max_idler],max_recoil_force_N=self.max_idler_force,slack_bank_steps=self.slack_steps,dissipated_J=self.dissipated_J)
