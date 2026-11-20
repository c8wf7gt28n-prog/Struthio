import sys, math, random
from PIL import Image, ImageDraw, ImageFilter
S=sys.argv[1]
def hx(c):
    c=c.lstrip('#');return tuple(int(c[i:i+2],16) for i in (0,2,4))
PAL={'kasandra':dict(ground=hx('171b3c'),low=hx('5f4fa8'),mid=hx('ab8eda'),high=hx('83eaff'),hot=hx('e2a72e'),peak=hx('b9f4ff'),rest=hx('2a2d5c'),grid=hx('3a3f86')),
     'graphite':dict(ground=hx('0b0e0d'),low=hx('789654'),mid=hx('c3ed74'),high=hx('cbf08b'),hot=hx('ff9a36'),peak=hx('f4e8ce'),rest=hx('1c2420'),grid=hx('2c3a2a'))}
random.seed(7)
cpu=[0.18,0.62,0.35,0.81,0.27,0.44,0.12,0.69,0.22,0.55,0.38,0.91,0.15,0.47,0.3,0.58]
other=[0.22,0.35, 0.47,0.06, 0.32,0.12, 0.18,0.07, 0.08,0.41]
vals=cpu+other; groups=[16,2,2,2,2,2]
peaks=[min(1,v+random.uniform(0.04,0.2)) for v in vals]
hist=[0.25+0.18*math.sin(i/7.0)+0.12*math.sin(i/2.3)+random.uniform(-0.05,0.05) for i in range(120)]
def mix(a,b,t):return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
def ramp(P,t):
    return mix(P['low'],P['mid'],t/0.5) if t<0.5 else mix(P['mid'],P['high'],(t-0.5)/0.5)
def layout(W,gap=2,ggap=6,x0=10,x1=None):
    x1=x1 or W-10; n=len(vals); avail=x1-x0-(len(groups)-1)*ggap-(n-len(groups))*gap; bw=avail/n; xs=[];x=x0
    for g,k in enumerate(groups):
        for j in range(k):
            xs.append(x); x+=bw+(gap if j<k-1 else 0)
        x+=ggap
    return xs,bw
def glow(base,layer,radius=3,amount=1.0):
    g=layer.filter(ImageFilter.GaussianBlur(radius))
    return Image.alpha_composite(Image.alpha_composite(base,Image.eval(g,lambda v:int(min(255,v*amount)))),layer)
def hifi(W,H,P):
    im=Image.new('RGBA',(W,H),P['ground']+(255,)); lay=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(lay); rd=ImageDraw.Draw(im)
    rows=10; top=5; base=H-14; ch=(base-top-(rows-1))/rows; xs,bw=layout(W)
    for i,(x,v) in enumerate(zip(xs,vals)):
        lit=max(1,round(v*rows))
        for r in range(rows):
            y1=base-r*(ch+1); y0=y1-ch
            if r<lit:
                c=P['hot'] if r>=rows-2 else ramp(P,r/(rows-1))
                d.rectangle([x,y0,x+bw-1,y1-1],fill=c+(255,))
                # reflection
                ry0=base+2+r*2.2; 
                if ry0<H-1: rd.rectangle([x,ry0,x+bw-1,min(H-1,ry0+1.4)],fill=mix(P['ground'],c,max(0,0.35-r*0.07)))
            else:
                rd.rectangle([x,y0,x+bw-1,y1-1],fill=P['rest'])
        pk=round(peaks[i]*rows); y=base-(pk-1)*(ch+1)-ch-2
        d.rectangle([x,y,x+bw-1,y+1],fill=P['peak']+(235,))
    return glow(im,lay,2.2,0.9).convert('RGB')
def neon(W,H,P):
    im=Image.new('RGBA',(W,H),P['ground']+(255,)); rd=ImageDraw.Draw(im)
    base=H-12
    # perspective grid floor
    for k in range(1,5):
        y=base+k*k*0.7+1; rd.line([0,y,W,y],fill=mix(P['ground'],P['grid'],0.9-k*0.15))
    vp=W/2
    for k in range(-10,11):
        rd.line([vp+k*6,base,vp+k*40,H],fill=mix(P['ground'],P['grid'],0.6))
    lay=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(lay); xs,bw=layout(W,gap=3,ggap=8)
    for i,(x,v) in enumerate(zip(xs,vals)):
        h=max(2,v*(base-6)); c=P['hot'] if v>0.8 else ramp(P,v)
        d.rounded_rectangle([x+0.5,base-h,x+bw-0.5,base],radius=min(3,bw/2),fill=c+(255,))
        py=base-peaks[i]*(base-6)-3; d.ellipse([x+bw/2-1.6,py-1.6,x+bw/2+1.6,py+1.6],fill=P['peak']+(255,))
    return glow(im,lay,3.5,1.6).convert('RGB')
def scope(W,H,P):
    im=Image.new('RGBA',(W,H),P['ground']+(255,)); rd=ImageDraw.Draw(im)
    base=H-6
    for y in range(8,base,8): rd.line([0,y,W,y],fill=mix(P['ground'],P['grid'],0.45))
    for x in range(0,W,20): rd.line([x,4,x,base],fill=mix(P['ground'],P['grid'],0.3))
    tr=Image.new('RGBA',(W,H),(0,0,0,0)); td=ImageDraw.Draw(tr)
    pts=[(W*i/(len(hist)-1), base-2-h*(base-10)) for i,h in enumerate(hist)]
    td.line(pts,fill=P['high']+(255,),width=2)
    im=glow(im,tr,2.5,1.4)
    lay=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(lay); xs,bw=layout(W,gap=2,ggap=6)
    for i,(x,v) in enumerate(zip(xs,vals)):
        h=max(2,v*(base-8)); c=P['hot'] if v>0.8 else ramp(P,v)
        d.rectangle([x,base-h,x+bw-1,base],fill=c+(150,))
        d.rectangle([x,base-h,x+bw-1,base-h+1],fill=P['peak']+(255,))
    return Image.alpha_composite(im,lay).convert('RGB')
VAR={'A_hifi':hifi,'B_neon':neon,'C_scope':scope}
for look in ('kasandra','graphite'):
    P=PAL[look]
    shot=Image.open(f'{S}/work/head_mock/mock3_{look}.png').convert('RGB'); orig=Image.open(f'{S}/work/shots084/out/2_field_{look}.png').convert('RGB')
    mid=353 if look=='kasandra' else 325
    for name,fn in VAR.items():
        out=shot.copy()
        ref=[orig.getpixel((900,y)) for y in range(58)]
        for x in range(0,mid-2):
            for y in range(58): out.putpixel((x,y),ref[y])
        eq=fn(mid-24,52,P); out.paste(eq,(12,3))
        out.save(f'{name}_{look}.png')
        out.crop((0,0,mid+330,70)).resize(((mid+330)*2,140),Image.LANCZOS).save(f'{name}_{look}_zoom.png')
        eq.resize((eq.size[0]*3,eq.size[1]*3),Image.NEAREST).save(f'{name}_{look}_x3.png')

def neonscope(W,H,P):
    im=Image.new('RGBA',(W,H),P['ground']+(255,)); rd=ImageDraw.Draw(im)
    base=H-12
    for k in range(1,5):
        y=base+k*k*0.7+1; rd.line([0,y,W,y],fill=mix(P['ground'],P['grid'],0.9-k*0.15))
    vp=W/2
    for k in range(-10,11): rd.line([vp+k*6,base,vp+k*40,H],fill=mix(P['ground'],P['grid'],0.6))
    tr=Image.new('RGBA',(W,H),(0,0,0,0)); td=ImageDraw.Draw(tr)
    pts=[(W*i/(len(hist)-1), base-3-h*(base-12)) for i,h in enumerate(hist)]
    td.line(pts,fill=P['high']+(170,),width=1)
    im=glow(im,tr,2.0,1.2)
    lay=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(lay); xs,bw=layout(W,gap=3,ggap=8)
    for i,(x,v) in enumerate(zip(xs,vals)):
        h=max(2,v*(base-6)); c=P['hot'] if v>0.8 else ramp(P,v)
        d.rounded_rectangle([x+0.5,base-h,x+bw-0.5,base],radius=min(3,bw/2),fill=c+(235,))
        py=base-peaks[i]*(base-6)-3; d.ellipse([x+bw/2-1.4,py-1.4,x+bw/2+1.4,py+1.4],fill=P['peak']+(255,))
    return glow(im,lay,3.2,1.5).convert('RGB')
VAR['D_neonscope']=neonscope
for look in ('kasandra','graphite'):
    P=PAL[look]; mid=353 if look=='kasandra' else 325
    shot=Image.open(f'{S}/work/head_mock/mock3_{look}.png').convert('RGB'); orig=Image.open(f'{S}/work/shots084/out/2_field_{look}.png').convert('RGB')
    out=shot.copy(); ref=[orig.getpixel((900,y)) for y in range(58)]
    for x in range(0,mid-2):
        for y in range(58): out.putpixel((x,y),ref[y])
    eq=neonscope(mid-24,52,P); out.paste(eq,(12,3)); out.save(f'D_neonscope_{look}.png')
    eq.resize((eq.size[0]*3,eq.size[1]*3),Image.NEAREST).save(f'D_neonscope_{look}_x3.png')
# one sheet: the four styles in both looks, at three times their size, labelled
from PIL import ImageFont
names=[('A_hifi','A · Hi-fi deck'),('B_neon','B · Neon tubes'),('C_scope','C · Scope and bars'),('D_neonscope','D · Neon tubes over a scope')]
tiles=[]
for key,label in names:
    for look in ('kasandra','graphite'):
        tiles.append((f'{label} ({"Kasandra" if look=="kasandra" else "Graphite"} look)',Image.open(f'{key}_{look}_x3.png')))
w=max(t[1].size[0] for t in tiles); h=sum(t[1].size[1]+34 for t in tiles)+10
sheet=Image.new('RGB',(w+20,h),(245,242,236)); dd=ImageDraw.Draw(sheet); y=10
try: font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
except Exception: font=None
for label,img in tiles:
    dd.text((10,y),label,fill=(30,30,30),font=font); y+=26; sheet.paste(img,(10,y)); y+=img.size[1]+8
sheet.save('equalizer_styles_sheet.png'); print(sheet.size)
