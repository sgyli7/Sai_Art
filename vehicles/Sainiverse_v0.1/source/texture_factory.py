"""Offline, deterministic semantic wear masks. No runtime noise or extra meshes.

R = paint loss, G = grime, B = thin exposed edge accent. Every stroke starts
from a named edge/handling region; random seeds only change its silhouette.
This is a panel-space approximation, explicitly NOT curvature/AO baking.
"""
from pathlib import Path
import argparse, hashlib, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1]

def stroke(draw, rng, center, length, width, angle=0., value=220):
    direction=np.array([np.cos(angle),np.sin(angle)])
    cross=np.array([-direction[1],direction[0]])
    positions=np.linspace(-.5,.5,11)
    # Coherent broad fluctuations, not independent pixel noise.
    widths=width*1.8*np.interp(np.linspace(0,1,11),np.linspace(0,1,5),rng.uniform(.2,1,5))
    pts=[]
    for sign,indices in [(1,range(11)),(-1,range(10,-1,-1))]:
        for i in indices:
            point=np.array(center)+direction*length*1.15*positions[i]+cross*sign*widths[i]
            pts.append(tuple(point))
    draw.polygon(pts,fill=int(value))

def tile(recipe,family,variant):
    size=recipe['tile_px'];rng=np.random.default_rng(recipe['seed']+family*1009+variant*97)
    r=Image.new('L',(size,size));g=Image.new('L',(size,size));d=ImageDraw.Draw(r);grime=ImageDraw.Draw(g)
    if family in [0,3]:
        # Two exposed edges, never the full perimeter. Most of the face stays clean.
        for edge in ([0,1] if variant%2==0 else [0,2]):
            for _ in range(11 if family==0 else 7):
                t=float(rng.uniform(.05,.95))*size
                depth=float(rng.uniform(.009,.022))*(recipe['edge_band_fraction']/.06)*size
                center=(t,size-depth) if edge==0 else (depth,t) if edge==1 else (size-depth,t)
                stroke(d,rng,center,float(rng.uniform(.018,.105))*size,float(rng.uniform(.002,.012))*size,0 if edge==0 else np.pi/2,rng.integers(125,240))
        if family==3:
            # Grip/latch area on the right, and a short drag mark at the foot.
            for _ in range(8):
                center=(rng.uniform(.81,.9)*size,rng.uniform(.43,.56)*size)
                stroke(d,rng,center,rng.uniform(.015,.05)*size,.0025*size,rng.uniform(-.25,.25),180)
    elif family==1:
        # Long-axis rubbing breaks a stencil into flakes without changing its font.
        for _ in range(18+variant*18):
            stroke(d,rng,(rng.uniform(.02,.98)*size,rng.uniform(.1,.9)*size),rng.uniform(.018,.09)*size,rng.uniform(.004,.018)*size,rng.uniform(-.10,.10),rng.integers(180,256))
    else:
        # Gravity-directed runs begin at the upper service edge, plus lower scuff.
        for x in rng.uniform(.08,.92,3):
            length=rng.uniform(.12,.32)*size
            stroke(grime,rng,(x*size,length/2),length,.01*size,np.pi/2,130)
        for _ in range(10):
            stroke(d,rng,(rng.uniform(.05,.95)*size,rng.uniform(.93,.985)*size),rng.uniform(.015,.07)*size,.003*size,0,190)
        g=g.filter(ImageFilter.GaussianBlur(1.5))
    arr=np.asarray(r)
    coverage=float(np.mean(arr>60))
    if coverage>recipe['maximum_paint_loss_coverage']:
        raise ValueError(f'Coverage budget exceeded: {family}/{variant}: {coverage}')
    inner=np.asarray(r.filter(ImageFilter.MinFilter(3))).astype(np.int16)
    accent=np.maximum(arr.astype(np.int16)-inner,0).astype(np.uint8)
    out=Image.merge('RGB',(r,g,Image.fromarray(accent)))
    return out,coverage

def build(recipe,dest):
    if recipe['variants_per_family']!=4 or len(recipe['families'])!=4:raise ValueError('Runtime atlas contract requires four families with four variants each.')
    dest.mkdir(parents=True,exist_ok=True);size=recipe['tile_px'];atlas=Image.new('RGB',(size*4,size*4));rows=[]
    preview=Image.new('RGB',(4*384,4*256),(226,226,216));pd=ImageDraw.Draw(preview)
    for family,name in enumerate(recipe['families']):
        for variant in range(4):
            im,coverage=tile(recipe,family,variant);index=family*4+variant
            filename=f'{name}_{variant:02d}.png';im.save(dest/filename)
            atlas.paste(im,(variant*size,family*size))
            rows.append(dict(index=index,family=name,variant=variant,coverage=coverage,file=filename,sha256=hashlib.sha256((dest/filename).read_bytes()).hexdigest()))
            data=np.array(im.resize((368,218)),dtype=float)/255
            base=np.array([42,45,49] if family!=1 else [172,169,153],dtype=float)
            rgb=np.broadcast_to(base,data.shape).copy();rgb=rgb*(1-data[:,:,0,None]*.7)+np.array([96,99,98])*data[:,:,0,None]*.7
            rgb*=1-data[:,:,1,None]*.35;rgb+=data[:,:,2,None]*14
            preview.paste(Image.fromarray(np.uint8(np.clip(rgb,0,255))),(variant*384+8,family*256+26));pd.text((variant*384+8,family*256+6),f'{name} / {variant}',fill=(30,30,30))
    atlas.save(dest/'wear_atlas.png');preview.save(dest/'contact_sheet.png')
    # Same font and layout in every stencil; only paint loss changes.
    logo=Image.new('RGBA',(1024,144));ld=ImageDraw.Draw(logo);font=ImageFont.truetype(recipe['font'],130)
    bounds=ld.textbbox((0,0),recipe['logo'],font=font);ld.text(((1024-bounds[2])/2,(144-(bounds[3]-bounds[1]))/2-bounds[1]),recipe['logo'],font=font,fill=(205,204,189,255))
    logo_atlas=Image.new('RGBA',(1024,144*4));warnings=Image.new('RGBA',(1024,128*4))
    logo_alpha=np.array(logo)[:,:,3].astype(float)
    for v in range(4):
        mask=np.array(Image.open(dest/f'stencil_loss_{v:02d}.png').resize(logo.size))[:,:,0]/255.
        rgba=np.array(logo).copy();rgba[:,:,3]=np.uint8(logo_alpha*(1-np.clip(mask*(.75+v*.18),0,1)))
        image=Image.fromarray(rgba);image.save(dest/f'sainiverse_stencil_{v:02d}.png');logo_atlas.paste(image,(0,v*144))
        yy,xx=np.indices((128,1024));stripe=((xx+yy)//64)%2
        color=np.where(stripe[:,:,None]>0,np.array([205,165,51]),np.array([24,26,28])).astype(float)
        edge=np.array(Image.open(dest/f'edge_chips_{v:02d}.png').resize((1024,128)))[:,:,0]/255.
        color=color*(1-edge[:,:,None]*.55)+np.array([85,88,86])*edge[:,:,None]*.55
        warn=Image.fromarray(np.uint8(color)).convert('RGBA');warn.save(dest/f'warning_strip_{v:02d}.png');warnings.paste(warn,(0,v*128))
    logo_atlas.save(dest/'stencil_atlas.png');warnings.save(dest/'warning_atlas.png')
    labels=Image.new('RGBA',(1024,576));labels.paste(Image.open(dest/'sainiverse_stencil_00.png'),(0,0))
    for i,(title,sub) in enumerate([('PWR - 01','ISOLATE BEFORE SERVICE'),('COOLANT - 02','CHECK PRESSURE BEFORE OPENING'),('SERVICE - 03','MAINTENANCE ACCESS')],start=1):
        lab=Image.new('RGBA',(1024,144));ld=ImageDraw.Draw(lab);ld.rounded_rectangle((70,12,950,134),radius=6,fill=(172,174,165,255),outline=(35,40,42,255),width=4)
        ld.text((100,20),title,font=ImageFont.truetype(recipe['font'],45),fill=(45,47,49,255));ld.text((100,85),sub,font=ImageFont.truetype(recipe['font'],23),fill=(60,61,58,255));labels.paste(lab,(0,i*144))
    labels.save(dest/'service_stickers.png')
    board=Image.new('RGB',(1024,4*240),(43,46,50));bd=ImageDraw.Draw(board)
    for v in range(4):
        mark=Image.open(dest/f'sainiverse_stencil_{v:02d}.png');board.paste(mark,(0,v*240),mark)
        warn=Image.open(dest/f'warning_strip_{v:02d}.png').resize((960,48));board.paste(warn,(32,v*240+158))
        bd.text((32,v*240+218),f'Variant {v+1} / shared font / paint loss {v+1}',fill=(180,184,185))
    board.save(dest/'markings_preview.png')
    manifest=dict(recipe=recipe,tiles=rows,atlas_grid=[4,4],channels={'R':'paint loss','G':'grime','B':'edge accent'},scope='Offline semantic panel masks; no mesh-map bake. 16 wear variants, 4 stencils, 4 warning strips.',runtime_atlases=['wear_atlas.png','stencil_atlas.png','warning_atlas.png'])
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'tiles':len(rows),'max_coverage':max(x['coverage'] for x in rows),'output':str(dest)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--recipe',type=Path,default=ROOT/'source/texture_recipe.json');parser.add_argument('--output',type=Path,default=ROOT/'assets/generated');args=parser.parse_args()
    build(json.loads(args.recipe.read_text()),args.output)
