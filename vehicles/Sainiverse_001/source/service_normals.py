"""Manufacturing-shaped height fields matching the four artwork panels."""
from pathlib import Path
import numpy as np
from PIL import Image
O=Path(__file__).resolve().parents[1];N=768;L=4.;x,y=np.meshgrid(np.arange(N)*L/N,np.arange(N)*L/N)
def line(d,w):return np.exp(-(d/w)**2)
def rect(cx,cy,w,h,r=.06):
 qx=np.abs(x-cx)-(w/2-r);qy=np.abs(y-cy)-(h/2-r)
 return np.hypot(np.maximum(qx,0),np.maximum(qy,0))+np.minimum(np.maximum(qx,qy),0)-r
def rim():return -.0025*line(rect(2,2,3.70,3.70),.010)
def bolts(h,spots):
 for cx,cy in spots:
  rr=np.hypot(x-cx,y-cy);h+=.0014*line(rr-.065,.009)-.0015*line(rr-.035,.008)
 return h
fields=[]
h=rim();h=bolts(h,[(.37,.37),(3.63,.37),(.37,3.63),(3.63,3.63)]);fields.append(h)
h=rim()
for cx in [1.35,2.65]:h+=-.0025*np.clip(-rect(cx,2,.26,2.85,.12)/.025,0,1)
h=bolts(h,[(.24,.24),(2,.24),(3.76,.24),(.24,3.76),(2,3.76),(3.76,3.76)]);fields.append(h)
h=rim();h+=-.002*line(rect(3.10,.60,.82,.30,.03),.01);fields.append(h)
h=np.zeros_like(x)
for cy in [1.10,2.65]:h+=-.0025*np.clip(-rect(2,cy,3.35,.20,.09)/.02,0,1)
h+=.0018*line(y-3.55,.012);fields.append(h)
images=[]
for h in fields:
 gy,gx=np.gradient(h,L/N);n=np.stack([-gx,-gy,np.ones_like(h)],-1);n/=np.linalg.norm(n,axis=-1,keepdims=True);images.append(np.round((n*.5+.5)*255).astype('uint8'))
out=np.concatenate([np.concatenate(images[:2],axis=1),np.concatenate(images[2:],axis=1)],axis=0)
Image.fromarray(out).save(O/'assets/normals/service_panel_normal.png')
print('1536px service normal atlas; relief <= 2.5mm, no noise-based bumps.')
