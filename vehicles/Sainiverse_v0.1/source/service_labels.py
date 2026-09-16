"""Nine original functional labels plus separately attributed user-supplied industrial stickers.
The composite atlas includes the selected third-party images under assets/user_stickers; see provenance docs.
"""
import json,zlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
LABELS=[('FIELD SERVICE','FS / 001','circle'),('THERMAL LOOP','RETURN / INSPECT SEALS','arrow'),('ISOLATE','BEFORE SERVICE','red'),('FILTER ACCESS','FA / 02','filter'),('ROBOT BOARDING','KEEP ACCESS CLEAR','robot'),('CRANE','PINCH ZONE','triangle'),('CARGO MODULE','CHECK LOCKS','module'),('CREW ENTRY','KEEP AISLE CLEAR','entry'),('RECOVERY','TOW POINT','ring')]
def draw_label(i,size=(512,192)):
    title,sub,kind=LABELS[i];im=Image.new('RGBA',(512,192));d=ImageDraw.Draw(im);ink=(212,209,188,255);dark=(31,35,37,255);red=(184,35,48,255);yellow=(210,168,54,255)
    if kind in ['red','triangle']:
        d.rounded_rectangle((5,18,507,174),radius=10,fill=(203,198,174,255));ink=dark
        if kind=='red':d.rectangle((5,18,507,54),fill=red);d.text((145,22),'ELECTRICAL',font=ImageFont.truetype(BOLD,20),fill=(240,231,203,255))
    elif kind=='module':d.polygon([(5,40),(30,18),(481,18),(507,40),(507,173),(5,173)],outline=ink,width=4)
    else:d.line((145,43,502,43),fill=red if kind=='arrow' else ink,width=4);d.line((145,160,502,160),fill=ink,width=2)
    if kind=='circle':
        d.ellipse((9,26,139,156),outline=ink,width=5);d.ellipse((19,36,129,146),outline=ink,width=2);d.line((50,118,100,68),fill=ink,width=15);d.arc((72,44,118,90),20,290,fill=ink,width=12);d.ellipse((40,108,61,129),fill=dark,outline=ink,width=4)
    elif kind=='arrow':
        d.arc((21,39,115,139),50,295,fill=ink,width=7);d.polygon([(92,36),(127,53),(96,69)],fill=ink);d.line((25,99,117,99),fill=red,width=5)
    elif kind=='red':
        d.line((30,117,61,117,111,70),fill=ink,width=8);d.ellipse((20,107,40,127),outline=ink,width=4);d.ellipse((108,106,129,127),outline=ink,width=4)
    elif kind=='filter':
        d.rectangle((26,44,112,142),outline=ink,width=4)
        for x in range(38,110,14):d.line((x,52,x,134),fill=ink,width=3)
    elif kind=='robot':
        d.rounded_rectangle((33,54,107,117),radius=11,outline=ink,width=5);d.ellipse((39,116,58,137),fill=ink);d.ellipse((82,116,101,137),fill=ink);d.line((72,54,72,34),fill=ink,width=4);d.ellipse((66,27,78,39),fill=red)
    elif kind=='triangle':
        d.polygon([(72,42),(127,141),(17,141)],fill=yellow,outline=dark,width=5);d.line((72,70,72,107),fill=dark,width=8);d.ellipse((67,119,77,129),fill=dark)
    elif kind=='module':d.text((33,53),'B',font=ImageFont.truetype(BOLD,84),fill=ink)
    elif kind=='entry':
        d.rounded_rectangle((36,36,106,146),radius=10,outline=ink,width=5);d.line((57,96,126,96),fill=ink,width=6);d.polygon([(126,96),(109,84),(109,108)],fill=ink)
    else:d.ellipse((24,47,113,136),outline=ink,width=13);d.line((109,92,134,92),fill=ink,width=12)
    d.text((148,63),title,font=ImageFont.truetype(BOLD,28),fill=ink);d.text((149,112),sub,font=ImageFont.truetype(FONT,18),fill=ink)
    # Sparse deterministic edge flaking leaves legible glyphs and changes per label.
    a=np.array(im);rng=np.random.default_rng(30600+i)
    mask=Image.new('L',im.size,255);md=ImageDraw.Draw(mask)
    for j in range(12):
        x=int(rng.integers(12,498));y=int(rng.choice([42,157]));md.line((x,y,x+int(rng.integers(3,17)),y+int(rng.integers(-2,3))),fill=int(rng.integers(20,160)),width=2)
    a[:,:,3]=(a[:,:,3].astype(float)*np.asarray(mask)/255).astype('uint8');return Image.fromarray(a).resize(size)
def build(out):
    sheet=Image.new('RGBA',(2048,2048))
    for i in range(9):sheet.paste(draw_label(i,(512,512)),(i%4*512,i//4*512))
    for i,n in enumerate(['aigle','rescue_units_01','offroad_warden_01'],start=9):
        im=Image.open(out.parent/'user_stickers'/f'{n}.png').convert('RGBA');sheet.paste(im.resize((512,512)),(i%4*512,i//4*512))
    from cockpit_art import plates
    for i,im in enumerate(plates(),12):sheet.paste(im,(i%4*512,i//4*512))
    sheet.save(out/'equipment_labels.png')
    covers=Image.new('RGBA',(1024,576))
    # Each wall retains a clear reading zone; silhouettes differ within the same strip.
    for row,i in enumerate([0,2,1,3]):
        lab=draw_label(i);lab.thumbnail((680,138));covers.paste(lab,(int((1024-lab.width)/2),row*144+3))
    covers.paste(Image.open(out.parent/'user_stickers/aigle.png').convert('RGBA').resize((1024,144)),(0,0))
    covers.save(out/'service_stickers.png')
    (out/'equipment_labels.json').write_text(json.dumps([dict(id=i,title=t,subtitle=s,symbol=k) for i,(t,s,k) in enumerate(LABELS)],indent=2))
def assign(a):
    for p in a['parts']:
        if p.get('company_replaces_service_logo'):continue
        n=p['name'];i=None;axis=1
        if n.endswith('fore_service_door_leaf'):i=2
        elif n.endswith('roof_machine_case'):i=3
        elif n.endswith('crane_pedestal_hatch'):i=10
        elif n.endswith('bridge_door_leaf'):i=7
        elif 'workbench_backboard' in n:i=11
        elif n.endswith('lift_controls'):i=4
        elif 'container_' in n and '_closed_front_panel' in n:i=6;axis=0
        if 'cockpit_tile' in p:
            i=p['cockpit_tile'];axis=p['cockpit_axis']
        if i is None:continue
        v=np.array(p['vertices']);lo=v.min(0);hi=v.max(0);ij=[0,2] if axis==1 else [1,2] if axis==0 else [0,1];span=hi[ij]-lo[ij]
        width=min(float(span[0])*.70,float(span[1])*1.6,2.2);height=width if i>=9 else width*192/512
        if i>=9:width=min(width,float(span[1])*.45,1.2);height=width
        center=(lo[ij]+hi[ij])*.5;center[1]+=span[1]*.16
        if 'cockpit_tile' in p:
            from cockpit_art import ASPECTS
            t=p['cockpit_transform'];width=min(t['width'],t['height']*ASPECTS[i]);height=width/ASPECTS[i];center=np.zeros(2)
        base=p['material'];mat=f'decal_{i}_{base}';a['colors'][mat]=a['colors'][base];p['material']=mat
        p['art_uv']={'cockpit_transform':p.get('cockpit_transform'),'usage':'decal','label_id':i,'axes':[axis],'rect_center':center.tolist(),'rect_size':[width,height],'bounds':[lo.tolist(),hi.tolist()]}
