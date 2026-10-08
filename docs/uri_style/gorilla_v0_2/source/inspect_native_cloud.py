from pathlib import Path
import json, math
import numpy as np
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parents[1]
v=np.load(root/'source/raw_vertex_sample.npz')['vertices']
c=(v.min(0)+v.max(0))/2
s=900/1.266
out=Image.new('RGB',(2000,2000),'#e9edf0');d=ImageDraw.Draw(out)
for index,(name,axis) in enumerate([('FRONT INPUT',(0,2,1)),('RIGHT INPUT',(1,2,0)),('BACK INPUT',(0,2,1)),('TOP INPUT',(0,1,2))]):
    ox=(index%2)*1000;oy=(index//2)*1000
    u=v[:,axis[0]];w=v[:,axis[1]];depth=v[:,axis[2]]
    if index==2:u=-u
    if index==3:w=-w
    px=(500+u*s).astype(int);py=(500-w*s).astype(int)
    order=np.argsort(depth)
    if index<2: order=order[::-1]
    arr=np.full((1000,1000,3),235,dtype=np.uint8)
    valid=(px>=0)&(px<1000)&(py>=0)&(py<1000)
    ii=order[valid[order]]
    rgb=np.tile(np.array([105,112,118]),(len(v),1))
    rgb[(v[:,1]>.20)&(v[:,2]>.10)]=[219,64,64]
    rgb[(v[:,0]<-.10)&(v[:,1]<-.32)&(v[:,2]<.13)]=[215,110,27]
    arr[py[ii],px[ii]]=rgb[ii]
    out.paste(Image.fromarray(arr),(ox,oy))
    d=ImageDraw.Draw(out)
    for n in np.arange(-.5,.51,.1):
        x=ox+500+int(n*s);y=oy+500-int(n*s)
        d.line((x,oy+50,x,oy+950),fill='#c4c9cc',width=1)
        d.line((ox+50,y,ox+950,y),fill='#c4c9cc',width=1)
        d.text((x+2,oy+954),f'{n:.1f}',fill='black')
        d.text((ox+8,y),f'{n:.1f}',fill='black')
    d.text((ox+50,oy+25),name,fill='black')
out.save(root/'images/geometry_region_inspection.png')
print('CLOUD_INSPECTION',v.shape)
