"""Reproducible crops of the user's Sai artwork, retaining the supplied pixels.

The boards are presentation images, not alpha sheets. Clean marks use background
separation; weathered die cuts use manually traced outer silhouettes. No new logo
generation, OCR replacement, or rectangular presentation backgrounds.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageFont

ROOT=Path(__file__).resolve().parents[1]/'assets/company'

def build():
    ROOT.mkdir(exist_ok=True);items=[]
    source=Image.open(ROOT/'source/logo_variants.png').convert('RGB')
    for row,tone in enumerate(['dark','light']):
        for col,kind in enumerate(['primary','horizontal','compact']):
            box=(30+590*col,96+540*row,590+590*col,555+540*row)
            rgb=np.asarray(source.crop(box));f=rgb.astype(float)
            # Both checker colors are excluded. A small antialias transition is
            # retained, then edge RGB is taken from the nearest foreground.
            distance=(220-f.min(2)) if row==0 else (f.max(2)-63)
            alpha=np.clip((distance-12)/28,0,1)
            # Remove checker-colored fringes by unmatting antialiased edge pixels.
            fg=np.where((f[:,:,0]-f[:,:,2]>24)[:,:,None],np.array([213,166,85] if row==0 else [183,137,56]),np.array([69,72,68] if row==0 else [207,205,198]))
            rgb=np.where((alpha<.999)[:,:,None],fg,rgb).astype('uint8')
            mask=Image.fromarray(np.uint8(alpha*255));bounds=mask.getbbox()
            rgba=Image.fromarray(np.dstack([rgb,np.uint8(alpha*255)])).crop(bounds)
            name=f'{kind}_{tone}';rgba.save(ROOT/f'{name}.png');items.append(dict(name=name,source='logo_variants.png',crop=list(box),method='checker-background separation',size=list(rgba.size)))
    # Coordinates are traced against the original 1536 x 1024 user boards.
    polygons={
      'stickers_weathered.png':{
        'worn_primary':[(112,528),(112,342),(156,296),(156,239),(247,165),(277,138),(322,128),(350,141),(483,141),(496,158),(504,291),(493,318),(496,397),(505,459),(502,488),(459,536),(127,536)],
        'worn_medium':[(618,511),(618,367),(649,332),(650,279),(746,188),(774,169),(812,169),(831,147),(957,146),(977,166),(977,477),(932,532),(635,532)],
        'worn_vertical':[(1135,530),(1135,314),(1145,296),(1146,165),(1171,139),(1447,140),(1468,165),(1468,530),(1446,553),(1326,554),(1310,546),(1150,552)],
        'worn_banner':[(116,654),(182,589),(200,576),(574,576),(595,594),(597,652),(580,676),(124,676)],
        'worn_compact':[(751,604),(763,592),(978,592),(990,603),(990,658),(978,672),(760,672),(749,661)],
        'worn_stripe':[(1059,665),(1128,593),(1145,589),(1483,589),(1495,601),(1495,650),(1478,667),(1072,679)],
        'worn_hex':[(274,798),(338,755),(354,748),(372,752),(434,792),(436,882),(371,929),(352,934),(337,929),(272,887)],
        'worn_triangle':[(444,908),(524,767),(538,756),(549,759),(637,910),(636,921),(623,925),(454,925),(444,920)],
        'number_patch':[(1384,877),(1392,868),(1481,868),(1495,879),(1495,913),(1485,923),(1392,923),(1383,914)]},
      'stickers_field.png':{
        'field_primary':[(68,348),(86,322),(87,235),(103,210),(144,184),(166,177),(237,99),(258,94),(285,101),(303,151),(315,178),(397,185),(429,211),(434,270),(414,296),(446,332),(444,350),(420,365),(404,397),(409,424),(441,452),(448,532),(436,560),(411,579),(174,576),(149,565),(86,562),(68,547)],
        'field_small':[(523,167),(573,129),(589,130),(608,108),(627,102),(644,111),(648,130),(665,136),(705,164),(707,182),(696,197),(700,219),(700,296),(690,309),(544,312),(532,300),(532,242),(542,224),(543,204),(526,191)],
        'field_horizontal':[(743,191),(773,154),(794,141),(1047,140),(1062,152),(1062,237),(1049,254),(1017,283),(755,285),(744,274)],
        'field_strip':[(1096,186),(1111,174),(1480,174),(1493,186),(1492,240),(1481,253),(1110,255),(1096,244)],
        'field_hex':[(754,473),(803,429),(823,411),(896,411),(916,425),(963,474),(963,552),(917,593),(897,610),(820,610),(754,554)],
        'field_triangle':[(999,573),(1086,419),(1098,410),(1111,419),(1196,572),(1199,588),(1186,599),(1016,600),(1001,592)],
        'field_id':[(1247,398),(1256,386),(1338,386),(1352,399),(1353,595),(1341,608),(1256,608),(1245,596)],
        'field_vertical':[(1396,398),(1408,387),(1455,387),(1468,400),(1468,597),(1456,609),(1407,609),(1395,596)]}}
    for src,entries in polygons.items():
        im=Image.open(ROOT/'source'/src).convert('RGBA')
        for name,points in entries.items():
            # Supersampled edge mask, inset by 1 px to exclude studio halo.
            mask=Image.new('L',(im.width*3,im.height*3));ImageDraw.Draw(mask).polygon([(x*3,y*3) for x,y in points],fill=255)
            mask=mask.resize(im.size,Image.Resampling.LANCZOS).filter(ImageFilter.MinFilter(3))
            out=im.copy();out.putalpha(mask);bounds=mask.getbbox();out=out.crop(bounds);out.save(ROOT/f'{name}.png')
            items.append(dict(name=name,source=src,polygon=points,crop=list(bounds),method='traced die-cut silhouette, antialiased alpha',size=list(out.size)))
    # Original fleet labels use the supplied identity and consistent stencil rules.
    for i,title in enumerate(['FIELD POWER','SCIENCE / LAB','THERMAL STORE','HABITAT KIT','FIELD SPARES','DRIVE SERVICE']):
        im=Image.new('RGBA',(1024,384));d=ImageDraw.Draw(im);ink=(211,210,195,255)
        d.rounded_rectangle((5,5,1019,379),radius=18,outline=ink,width=5)
        logo=Image.open(ROOT/'compact_light.png');logo.thumbnail((160,205));im.paste(logo,(32,55),logo)
        d.text((220,48),title,font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',54),fill=ink)
        d.text((224,128),f'SAI / F{i+1:02d}     MODULAR SYSTEM',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',27),fill=ink)
        d.line((224,186,966,186),fill=ink,width=3)
        d.text((224,218),'LOCK 4 CORNERS / LIFT FROM ABOVE',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',24),fill=ink)
        for x in range(224,960,46):d.rectangle((x,298,x+21,307),fill=(204,165,70,255))
        rng=np.random.default_rng(831+i)
        for _ in range(24):
            x=int(rng.integers(15,1004));y=int(rng.choice([7,377]));d.line((x,y,x+int(rng.integers(3,17)),y),fill=(0,0,0,0),width=3)
        name=f'fleet_{i}';im.save(ROOT/f'{name}.png');items.append(dict(name=name,source='original procedural fleet label using supplied compact mark',method='deterministic vector/text layout',size=list(im.size)))
    height=512*((len(items)+3)//4)
    atlas=Image.new('RGBA',(2048,height));preview=Image.new('RGB',(2048,height),(61,69,73));draw=ImageDraw.Draw(preview)
    for i,item in enumerate(items):
        im=Image.open(ROOT/(item['name']+'.png'));im.thumbnail((480,444),Image.Resampling.LANCZOS)
        x=(i%4)*512+(512-im.width)//2;y=(i//4)*512+(476-im.height)//2
        atlas.paste(im,(x,y));preview.paste(im,(x,y),im)
        draw.text(((i%4)*512+16,(i//4)*512+479),item['name'],fill=(237,233,214),font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19))
        item['uv_rect']=[x/2048,y/height,(x+im.width)/2048,(y+im.height)/height]
        item['aspect']=item['size'][0]/item['size'][1]
    atlas.save(ROOT/'company_atlas.png');preview.crop((0,0,2048,512*((len(items)+3)//4))).resize((1024,256*((len(items)+3)//4))).save(ROOT/'contact_sheet.png')
    manifest=dict(provenance='User-supplied company identity artwork, 2026-09-17; source boards preserved unchanged. Cropping/alpha extraction only.',sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'source').glob('*.png')},items=items)
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    return {i['name']:i for i in items}

if __name__=='__main__':print('Extracted',len(build()),'company stickers')
