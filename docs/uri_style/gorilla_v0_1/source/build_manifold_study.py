"""Drawing-only study of a local complex Fermat quintic patch projected R4 -> R3.
No Blender, mesh export, physical model or existing-image edits.
Source method: https://homes.luddy.indiana.edu/hansona/
"""
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,"/home/ethan/.cache/sai_art_surface_study")
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
BASE=Path(__file__).resolve().parent
r=np.linspace(.30,.96,121)
phi=np.linspace(-.52,.52,141)
R,Phi=np.meshgrid(r,phi,indexing="ij")
z1=R*np.exp(1j*Phi)
z2=(1-z1**5)**(.2)
Q=np.stack([z1.real,z1.imag,z2.real,z2.imag],axis=-1)
delta,beta=.50,.35
projection=np.array([[0,np.cos(delta),0,-np.sin(delta)],[-np.cos(beta),0,-np.sin(beta),0],[np.sin(beta),0,-np.cos(beta),0]])
V=Q@projection.T
# Anisotropic scaling/translation into a local art envelope. This is a shape study,
# not the complete protective shell or a metric-preserving CY representation.
low=V.min(axis=(0,1)); high=V.max(axis=(0,1))
scales=np.array([1.22,.78,.42])/(high-low)
V=(V-(high+low)/2)*scales + np.array([0,0,2.33])
X,Y,Z=V[...,0],V[...,1],V[...,2]
da,db=np.gradient(V,r,phi,axis=(0,1),edge_order=2)
cross=np.cross(da,db); area=np.linalg.norm(cross,axis=-1)
N=cross/area[...,None]
light=np.array([-.35,-.45,.82]); light=light/np.linalg.norm(light)
diffuse=np.abs(np.einsum("ijk,k->ij",N,light))
base=np.array([.88,.88,.84]); color=base[None,None,:]*(.53+.47*diffuse[...,None])
color=np.concatenate([color,np.ones(color.shape[:2]+(1,))],axis=-1)
fig=plt.figure(figsize=(14,7),facecolor="#ffffff")
for index,(az,el) in enumerate([(-63,30),(25,28)]):
 ax=fig.add_subplot(1,2,index+1,projection="3d",computed_zorder=False)
 ax.plot_surface(X,Y,Z,facecolors=color,rstride=2,cstride=2,linewidth=0,antialiased=True,shade=False)
 # Parametric trajectories belong to the computed patch, not decorative panel seams.
 for j in [20,45,70,95,120]:
  ax.plot(X[:,j],Y[:,j],Z[:,j]+.001,color="#357d9a",alpha=.52,linewidth=.7,zorder=10)
 for i in [15,45,75,105]:
  ax.plot(X[i,:],Y[i,:],Z[i,:]+.001,color="#668696",alpha=.36,linewidth=.65,zorder=10)
 ax.view_init(elev=el,azim=az);ax.set_proj_type("ortho")
 ax.set_box_aspect([1.22,.78,.65]);ax.set_xlim(-.68,.68);ax.set_ylim(-.44,.44);ax.set_zlim(2.06,2.60)
 ax.set_axis_off()
fig.subplots_adjust(left=0,right=1,bottom=0,top=1,wspace=-.08)
fig.savefig(BASE/"raw_fermat_projection_rev_l.png",dpi=160,facecolor="white")
metrics={"revision":"L","purpose":"local shape/normal-flow reference for art only, no new model deliverable","source_method":"https://homes.luddy.indiana.edu/hansona/","implicit_equation":"z1^5+z2^5=1, complex variables; local real 2-manifold in R4; a slice of a quintic CY, not the full real 6-dimensional manifold or Ricci-flat metric","parameterization":"z1=r*exp(i*phi), z2=(1-z1^5)^(1/5) on one smooth principal branch","r_domain":[.30,.96],"phi_domain":[-.52,.52],"projection_R4_to_R3":projection.tolist(),"projection_row_orthogonality_error":float(np.max(np.abs(projection@projection.T-np.eye(3)))),"art_scaling_after_projection":scales.tolist(),"complex_equation_max_residual":float(np.max(np.abs(z1**5+z2**5-1))),"distance_to_branch_locus_min":float(np.min(np.abs(1-z1**5))),"projected_parameter_area_min":float(area.min()),"sampled_bounds_m":{"x":[float(X.min()),float(X.max())],"y":[float(Y.min()),float(Y.max())],"z":[float(Z.min()),float(Z.max())]},"limit":"Partial open drawing patch, not a closed shell, not a CAD or collision/strength/printability proof. Imagegen may interpret rather than exactly reproduce it. Guide iso-curves must not become decorative seams in final artwork.","sha256_source":hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(BASE/"manifold_projection_study_rev_l.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({k:metrics[k] for k in ["complex_equation_max_residual","distance_to_branch_locus_min","projected_parameter_area_min","projection_row_orthogonality_error"]}))

# Adapt the single projected chart to the crown's art envelope. Row-wise scaling
# retains the coupled projected transverse profile, while locator curves control
# the required protective volume; this is openly a design adaptation, not CY geometry.
T=(R-.30)/(.96-.30)
U=Phi/.52
center=70
rowx=np.max(np.abs(X),axis=1)[:,None]
raw_y=Y-Y[:,center,None]
raw_z=Z-Z[:,center,None]
rowy=np.max(np.abs(raw_y),axis=1)[:,None]
rowz=np.max(np.abs(raw_z),axis=1)[:,None]
FX=(.28+.33*T)*X/rowx
FY=.28-.73*T+.065*raw_y/rowy
FZ=2.30+.28*T-.035*T*(1-T)+(.065+.105*T)*raw_z/rowz
F=np.stack([FX,FY,FZ],axis=-1)
fda,fdb=np.gradient(F,r,phi,axis=(0,1),edge_order=2)
farea=np.linalg.norm(np.cross(fda,fdb),axis=-1)
fnormal=np.cross(fda,fdb)/farea[...,None]
fd=np.abs(np.einsum("ijk,k->ij",fnormal,light))
fc=np.array([.89,.89,.86])[None,None,:]*(.62+.38*fd[...,None])
fc=np.concatenate([fc,np.ones(fc.shape[:2]+(1,))],axis=-1)
fig=plt.figure(figsize=(14,7),facecolor="white")
for index,(az,el) in enumerate([(-63,25),(25,28)]):
 ax=fig.add_subplot(1,2,index+1,projection="3d",computed_zorder=False)
 ax.plot_surface(FX,FY,FZ,facecolors=fc,rstride=2,cstride=2,linewidth=0,antialiased=False,shade=False)
 for j in [20,45,70,95,120]:
  ax.plot(FX[:,j],FY[:,j],FZ[:,j]+.001,color="#357d9a",alpha=.45,linewidth=.65,zorder=10)
 for i in [15,45,75,105]:
  ax.plot(FX[i,:],FY[i,:],FZ[i,:]+.001,color="#668696",alpha=.32,linewidth=.6,zorder=10)
 ax.view_init(elev=el,azim=az);ax.set_proj_type("ortho");ax.set_box_aspect([1.22,.78,.65])
 ax.set_xlim(-.65,.65);ax.set_ylim(-.50,.38);ax.set_zlim(2.12,2.66);ax.set_axis_off()
fig.subplots_adjust(left=0,right=1,bottom=0,top=1,wspace=-.08)
fig.savefig(BASE/"manifold_projection_guide_rev_l.png",dpi=160,facecolor="white")
metrics["art_adaptation"]={"method":"cross-section width and sagittal locators fitted to crown envelope; transverse profile remains coupled to all projected complex coordinates","formulas":{"x":"(0.28+0.33t)*Px/maxabs(Px)","y":"0.28-0.73t+0.065*(Py-Py0)/maxabs(Py-Py0)","z":"2.30+0.28t-0.035t(1-t)+(0.065+0.105t)*(Pz-Pz0)/maxabs(Pz-Pz0)"},"sampled_parameter_area_min":float(farea.min()),"purpose":"normal and shape flow guide only; no seams, material or model detail authority","status":"non-isometric physical-form adaptation, not a raw CY projection or complete CY manifold"}
metrics["sha256_source"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(BASE/"manifold_projection_study_rev_l.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n")
print("Art envelope adaptation complete",float(farea.min()))
