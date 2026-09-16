"""Semantic base-surface assignment and an offline atlas; no added geometry.

Coverage includes all authored triangle area, including hidden faces, and is
reported separately for explicitly authored interior parts. Glass/lights/ink
are retained unchanged and remain in the denominator.
"""
from pathlib import Path
import json,zlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter

FAMILIES=['paint','steel','rubber','floor','wall','worktop','console','ceiling']
def family(p):
    n=p['name'];mat=p['material'];cat=p.get('interior_category','')
    if 'company_sticker' in p or 'native_uv' in p:return None
    if p.get('interior_finish'):
        if 'cockpit_tile' in p:return None
        if cat=='ceiling':return 'ceiling'
        if cat=='wall':return 'wall'
        if cat=='console':return 'console'
        if cat=='workbench':return 'worktop'
    if n.startswith('r027_') and '_r032_' in n and (cat=='seat' or mat.startswith('cabin_')):return None
    if mat in ['glass','cabin_glass','cabin_light','cabin_screen'] or any(s in n for s in ['wordmark','warning','paint_','insignia']):return None
    if cat:
        if cat=='floor':return 'floor'
        if cat=='ceiling':return 'ceiling'
        if 'workbench_top' in n or 'tray' in n or 'handoff_pad' in n:return 'worktop'
        if any(s in n for s in ['console','rack_module','panel','backboard','cabinet']):return 'console' if 'console' in n or 'rack_module' in n else 'wall'
        return 'steel'
    if 'container_' in n and '_roof' in n:return 'cargo'
    if mat in ['deck_steel','ramp_steel']:return 'floor'
    if mat in ['track','roller','black'] or 'hose' in n:return 'rubber'
    if mat in ['steel','silver','edge'] or any(s in n for s in ['hydraulic','piston','cylinder_rod','rail','truss','brace','pin']):return 'steel'
    return 'paint'

def assign(a):
    for p in a['parts']:
        kind=family(p)
        if kind is None:continue
        variant=zlib.crc32(p['name'].encode())%2
        if kind=='wall' and not any(s in p['name'] for s in ['storage','locker_door','backboard']):variant=0
        p['surface_texture']={'family':kind,'tile':5 if kind=='cargo' else FAMILIES.index(kind)*2+(0 if kind=='rubber' else variant),'all_faces':True}

def atlas(out):
    size=512;sheet=Image.new('RGB',(2048,2048));preview=Image.new('RGB',(2048,2048));font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
    for k,kind in enumerate(FAMILIES):
        for v in range(2):
            kind='cargo' if k==2 and v==1 else FAMILIES[k]
            rng=np.random.default_rng(30300+k*71+v);im=Image.new('RGB',(size,size),(143,143,143));d=ImageDraw.Draw(im)
            # Broad paint strokes are sparse and coherent, never per-pixel noise.
            broad=Image.new('L',(512,512),143);bd=ImageDraw.Draw(broad)
            for j in range(7):
                x,y=rng.integers(40,460,2);w,h=rng.integers(45,130,2);bd.ellipse((int(x-w),int(y-h),int(x+w),int(y+h)),fill=int(rng.choice([127,134,154,162])))
            broad=broad.filter(ImageFilter.GaussianBlur(22));im=Image.merge('RGB',(broad,broad,broad));d=ImageDraw.Draw(im)
            # Controlled long strokes and broad, quiet paint variation.
            for i in range(18):
                x=int(rng.integers(10,490));y=int(rng.integers(10,490));length=int(rng.integers(12,85));c=int(rng.integers(137,151))
                d.line((x,y,min(x+length,502),y+int(rng.integers(-2,3))),fill=(c,c,c),width=1)
            if kind in ['paint','steel']:
                # A few drawn joint/weld traces at the component boundaries.
                for y in [8,503]:
                    d.line((5,y,506,y),fill=(101,101,101),width=2);d.line((5,y+3,506,y+3),fill=(173,173,173),width=1)
                for _ in range(15):
                    x=int(rng.integers(12,498));y=int(rng.choice([12,497]));length=int(rng.integers(3,18));d.line((x,y,x+length,y-1),fill=(185,185,185),width=2)
                if kind=='steel':
                    for y in range(20,490,23):d.line((30,y,470,y+1),fill=(150,150,150),width=1)
            elif kind=='rubber':
                for y in range(32,500,64):
                    d.line((8,y,503,y),fill=(113,113,113),width=4);d.line((8,y+5,503,y+5),fill=(160,160,160),width=2)
            elif kind=='cargo':
                for x in range(16,508,35):
                    d.line((x,14,x,495),fill=(105,105,105),width=3);d.line((x+4,14,x+4,495),fill=(177,177,177),width=2)
                d.rectangle((8,8,503,503),outline=(112,112,112),width=3)
            elif kind=='floor':
                for x in range(0,512,64):d.line((x,0,x,511),fill=(73,73,73),width=2)
                for y in range(0,512,128):d.line((0,y,511,y),fill=(73,73,73),width=2)
                # Sparse shoe/robot wear follows the two traffic strips.
                for yy in [85+v*17,334-v*13]:
                    for j in range(7):
                        xx=int(rng.integers(8,475));d.line((xx,yy+int(rng.integers(-7,8)),min(xx+int(rng.integers(16,50)),504),yy),fill=(176,176,176),width=3)
                for y in range(16,512,24):
                    for x in range(12+(y//24%2)*9,512,24):
                        d.line((x,y,x+6,y-5),fill=(169,169,169),width=2)
            elif kind in ['wall','ceiling']:
                # 1.2 x 2.4 m removable bulkhead panels; quiet broad brush work,
                # actual perimeter seals, captive screws, lower scuff band.
                d.rectangle((4,4,507,507),outline=(78,78,78),width=3)
                d.line((9,500,9,9,500,9),fill=(183,183,183),width=2)
                d.line((13,496,499,496,499,13),fill=(112,112,112),width=2)
                for x in [21,490]:
                    for y in [24,254,486]:
                        d.ellipse((x-4,y-2,x+4,y+2),fill=(95,95,95));d.line((x-2,y,x+2,y),fill=(183,183,183),width=1)
                if kind=='wall':
                    d.line((16,433,495,433),fill=(116,116,116),width=2)
                    for j in range(8):
                        x=int(rng.integers(27,475));y=int(rng.integers(442,484));d.line((x,y,x+int(rng.integers(4,18)),y-1),fill=(166,166,166),width=1)
                    if v==1:
                        d.rounded_rectangle((75,72,437,207),radius=9,outline=(106,106,106),width=2)
                        d.line((81,77,431,77),fill=(177,177,177),width=1)
                        for x in [89,423]:
                            for y in [84,196]:d.ellipse((x-3,y-2,x+3,y+2),fill=(90,90,90))
                        d.line((110,130,325,130),fill=(118,118,118),width=1)
                else:
                    d.rounded_rectangle((126,165,386,324),radius=6,outline=(113,113,113),width=2)
                    for y in range(180,307,12):
                        d.line((145,y,367,y),fill=(96,96,96),width=3);d.line((145,y+3,367,y+3),fill=(174,174,174),width=1)
            elif kind=='worktop':
                d.rectangle((7,7,504,504),outline=(87,87,87),width=3)
                for x in range(24,488,16):d.line((x,485,x,475 if x%64 else 465),fill=(74,74,74),width=2)
                for _ in range(14):
                    x,y=rng.integers(90,420,2);d.line((int(x),int(y),int(x+22),int(y-7)),fill=(179,179,179),width=1)
            else:
                # Enclosure finish only: no fake repeated switches or gauges.
                d.rectangle((8,8,503,503),outline=(105,105,105),width=2)
                d.line((12,14,12,495,495,495),fill=(166,166,166),width=1)
                for x in [24,487]:
                    for y in [24,487]:
                        d.ellipse((x-4,y-4,x+4,y+4),fill=(99,99,99));d.line((x-2,y,x+2,y),fill=(176,176,176),width=1)
                for y in range(416,456,8):d.line((43,y,136,y),fill=(115,115,115),width=2)
            # Padding prevents adjacent-family bleed at ordinary mip levels.
            im=im.resize((496,496));tile=Image.new('RGB',(512,512),(143,143,143));tile.paste(im,(8,8))
            index=k*2+v;sheet.paste(tile,((index%4)*512,(index//4)*512))
            preview.paste(tile,((index%4)*512,(index//4)*512));ImageDraw.Draw(preview).text(((index%4)*512+20,(index//4)*512+470),kind+' / '+str(v),font=font,fill=(240,240,240))
    sheet.save(out/'surface_atlas.png');preview.save(out/'surface_atlas_preview.png')
    # Height gradients come from intentional panel/pressing marks, never noise.
    h=np.asarray(sheet.convert('L').filter(ImageFilter.GaussianBlur(.65)),dtype=float)/255
    gy,gx=np.gradient(h);normal=np.stack([-gx*2.2,gy*2.2,np.ones_like(h)],axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255),'RGB').save(out/'surface_normal.png')

def uv(mesh,part):
    meta=part.get('surface_texture')
    if not meta:return np.full((len(mesh.vertices),2),-1,dtype=np.float32)
    v=mesh.vertices;lo=v.min(0);span=np.maximum(v.max(0)-lo,.0001);axis=np.argmax(np.abs(mesh.vertex_normals),axis=1);out=np.zeros((len(v),2))
    for k,ij in enumerate([[1,2],[0,2],[0,1]]):
        active=axis==k;q=(v[active][:,ij]-lo[ij])/span[ij]
        out[active,0]=(meta['tile']%2 if meta['family']=='floor' else meta['tile'])+.02+q[:,0]*.96;out[active,1]=.02+(1-q[:,1])*.96
        if meta['family'] in ['wall','ceiling']:
            # Only store a stable tile ID. Imported half-precision UVs cannot
            # safely encode metres / 4096 beside a large integer tile index.
            # The runtime projects physical local positions for these families.
            out[active]=[meta['tile']+.5,.5]
        if meta['family']=='floor' and k==(1 if part['material']=='ramp_steel' else 2):
            top=active if part['material']=='ramp_steel' else active & (mesh.vertex_normals[:,2]>.65)
            j=2 if part['material']=='ramp_steel' else 1
            out[top]=[meta['tile']+.5,.5]
    return out.astype(np.float32)

def report(a,path):
    totals={k:{'area_m2':0.,'textured_area_m2':0.,'parts':0,'textured_parts':0} for k in ['all','interior','exterior']};families={}
    for p in a['parts']:
        v=np.array(p['vertices']);tri=v[np.array(p['faces'])];area=float(np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1).sum()*.5)
        # Conservative count: only the new all-face layer, not older partial decals.
        yes=bool(p.get('surface_texture'));section='interior' if p.get('interior_category') else 'exterior'
        for key in ['all',section]:
            q=totals[key];q['area_m2']+=area;q['parts']+=1
            if yes:q['textured_area_m2']+=area;q['textured_parts']+=1
        if yes:
            f=p['surface_texture']['family'];families[f]=families.get(f,0)+area
    for q in totals.values():q['coverage']=q['textured_area_m2']/q['area_m2']
    data={'scope':'Authored triangle surface area, including hidden faces; transparent surfaces remain in denominator. Actual GLB UV2/runtime binding audited separately. Not percentage covered in dirt.','sections':totals,'family_area_m2':families}
    path.write_text(json.dumps(data,indent=2));return data
