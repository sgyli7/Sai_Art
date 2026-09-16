"""Physical-aspect instrument artwork: 4:1 gauge strips, 1:1 switch/chart plates.
The atlas stores resampled tiles; UV projection restores their intended metric aspect.
"""
from PIL import Image,ImageDraw,ImageFont
import math
F='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
ASPECTS={12:2.,13:2.,14:1.,15:1.,16:1.}
def plates():
 out=[]
 for kind in range(4):
  w,h=(1536,768) if kind<2 else (768,768)
  im=Image.new('RGBA',(w,h),(44,49,52,255));d=ImageDraw.Draw(im);ink=(205,211,196);muted=(127,144,145);font=ImageFont.truetype(F,18 if kind<2 else 20);small=ImageFont.truetype(F,14)
  d.rectangle((5,5,w-6,h-6),outline=(13,18,21),width=6);d.line((10,10,w-11,10),fill=(112,123,124),width=3)
  for x in [19,w-20]:
   for y in [19,h-20]:d.ellipse((x-5,y-5,x+5,y+5),fill=muted);d.line((x-3,y,x+3,y),fill=(33,39,42),width=2)
  title=['TRACTION / ATTITUDE / NAVIGATION','HANDLING / CRANE / LIFTS','DISTRIBUTION / CONTROL','ROUTE / SYSTEM MONITOR'][kind]
  d.text((37,25),title,font=font,fill=ink)
  if kind<2:
   for i in range(8):
    x=192+(i%4)*384;y=230.4 if i<4 else 552.96;r=99
    d.ellipse((x-r-11,y-r-11,x+r+11,y+r+11),fill=(15,23,28),outline=muted,width=3)
    for k in range(51):
     t=math.radians(135+k*5.4);major=k%10==0
     d.line((x+math.cos(t)*(r-7),y+math.sin(t)*(r-7),x+math.cos(t)*(r-(20 if major else 13)),y+math.sin(t)*(r-(20 if major else 13))),fill=ink,width=2 if major else 1)
    d.text((x-29,y-5),'NO LINK',font=small,fill=muted)
    names=['SPEED','PITCH','ROLL','ARTICULATION','TRACK TENSION','SUSP. PEAK','YAW RATE','ALLOC. POWER'] if kind==0 else ['CRANE SLEW','BOOM','EXTENSION','WINCH PAID','LIFT OUT','LIFT DEPTH','ANTENNA YAW','ANTENNA FOLD']
    d.text((x,y+144),names[i],font=font,fill=ink,anchor='mm')
  elif kind==2:
   d.text((38,65),'SERVICE SCHEMATIC / REFERENCE',font=font,fill=ink)
   for j,label in enumerate(['TRACTION','HYDRAULICS','BRAKES','CONTROL BUS','SUSPENSION','INTERLOCKS']):
    y=120+j*99;d.text((38,y),label,font=font,fill=ink)
    d.line((240,y+14,680,y+14),fill=muted,width=3)
    for i in range(4):
     x=280+i*120;d.rectangle((x-17,y-3,x+17,y+30),fill=(26,33,37),outline=muted,width=2)
     d.text((x-12,y+38),str(i+1),font=small,fill=ink)
   d.text((38,735),'LIVE VALUES ON TELEMETRY PANELS',font=small,fill=ink)
  else:
   for j in range(2):
    y=83+j*328;d.rounded_rectangle((36,y,730,y+298),radius=10,fill=(11,20,24),outline=muted,width=5)
    for x in range(60,715,42):d.line((x,y+42,x,y+270),fill=(25,47,48))
    for z in range(46,271,39):d.line((55,y+z,710,y+z),fill=(25,47,48))
    if j==0:d.line((69,y+229,160,y+188,252,y+210,370,y+117,462,y+160,597,y+59,710,y+98),fill=(134,190,160),width=4)
    else:
     for k in range(6):d.rectangle((74+k*108,y+246-(k*35+55)%179,130+k*108,y+250),fill=(102,164,147))
    d.text((60,y+16),'REFERENCE ROUTE / NOT LIVE' if j==0 else 'CHANNEL LAYOUT / NOT LIVE',font=font,fill=ink)
  out.append(im.resize((512,512),Image.Resampling.LANCZOS))
 return out
