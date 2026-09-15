"""Deterministic data textures: shallow machined features, no photographic noise."""
from pathlib import Path
import numpy as np
from PIL import Image
import json
O=Path(__file__).resolve().parents[1];D=O/'assets/normals';D.mkdir(exist_ok=True)
N=1024;span=4.;x,y=np.meshgrid(np.arange(N)*span/N,np.arange(N)*span/N)
def normal(name,h):
 dy,dx=np.gradient(h,span/N);v=np.stack([-dx,-dy,np.ones_like(dx)],axis=-1);v/=np.linalg.norm(v,axis=-1,keepdims=True)
 Image.fromarray(np.round((v*.5+.5)*255).astype('uint8')).save(D/(name+'_normal.png'))
 Image.fromarray(np.round(np.clip((h+.008)/.016,0,1)*65535).astype('uint16')).save(D/(name+'_height.png'))
# Welded panel: one large inset perimeter, paired purposeful stiffening grooves.
def line(d,width):return np.exp(-(d/width)**2)
def border(x0,y0,w,h):
 dx=np.abs(x-x0)-w/2;dy=np.abs(y-y0)-h/2
 return np.abs(np.maximum(dx,dy))
edge=np.minimum.reduce([x,span-x,y,span-y]);h=-.0025*line(edge,.009)
# Shallow embossed inspection perimeter, restrained to one localized quadrant.
b=border(1.1,1.15,1.45,1.50);mask=(np.abs(x-1.1)<.76)&(np.abs(y-1.15)<.79)
h+=-.0018*line(b,.009)*mask
for cx in [2.65,3.10]:h+=.0012*line(x-cx,.013)*((y>.5)&(y<3.5))
normal('paint_panels',h)
# Gray tread steel: 20 cm spacing, 3 mm shallow raised lozenges; no random spots.
u=(x/.20)%1-.5;v=(y/.20)%1-.5;parity=(np.floor(x/.20)+np.floor(y/.20))%2
across=np.where(parity<.5,u-v,u+v);along=np.where(parity<.5,u+v,u-v)
h=.003*line(across*.20,.007)*np.clip((.065-np.abs(along*.20))/.018,0,1)
h-=.002*line(edge,.008);normal('deck_tread',h)
normal('brushed_metal',np.zeros_like(x))
(O/'source/material_controls.json').write_text(json.dumps(dict(normal_strength=.65,paint_tile_m=4.,deck_tile_m=4.,paint_relief_depth_m=.0025,deck_relief_depth_m=.003,tread_spacing_m=.20,grain=False,random_scratches=False,scope='Tangent-space OpenGL normal data generated from stated height fields. Optical detail only; does not alter contact or silhouette.'),indent=2))
print('Generated 3 normal/height pairs; no random grain or scratch mask.')
