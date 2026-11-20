import sys, math, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont
S=sys.argv[1]; R='/home/user/Struthio/branding/fonts'
def hx(c):
    c=c.lstrip('#');return tuple(int(c[i:i+2],16) for i in (0,2,4))
PAL={'kasandra':dict(ground=hx('171b3c'),low=hx('5f4fa8'),mid=hx('ab8eda'),high=hx('83eaff'),hot=hx('e2a72e'),peak=hx('b9f4ff'),rest=hx('2a2d5c'),grid=hx('3a3f86'),text=hx('e3e3ff'),label=hx('b9f4ff'),font=R+'/typewriter/KasandraEliteMono-Regular.ttf'),
     'graphite':dict(ground=hx('0b0e0d'),low=hx('789654'),mid=hx('c3ed74'),high=hx('cbf08b'),hot=hx('ff9a36'),peak=hx('f4e8ce'),rest=hx('1c2420'),grid=hx('2c3a2a'),text=hx('f4e8ce'),label=hx('cbf08b'),font=R+'/plex/IBMPlexMono-Medium.ttf')}
def mix(a,b,t):t=max(0,min(1,t));return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))
def ramp(P,t):return P['hot'] if t>=0.85 else (mix(P['low'],P['mid'],t/0.5) if t<0.5 else mix(P['mid'],P['high'],(t-0.5)/0.5))
def glow(base,layer,radius=3,amount=1.0):
    g=layer.filter(ImageFilter.GaussianBlur(radius)); g=Image.eval(g,lambda v:int(min(255,v*amount)))
    return Image.alpha_composite(Image.alpha_composite(base,g),layer)
KEYS=['CPU','GPU','RAM','TXT']
STATES={'busy':[0.62,0.41,0.47,0.28],'idle':[0.20,None,0.08,None]}
random.seed(3)
def spark(v,n=40):
    base=v if v is not None else 0
    return [max(0,min(1,base+0.18*math.sin(i/4.0+base*9)+random.uniform(-0.06,0.06))) for i in range(n)]
def fnt(P,size):return ImageFont.truetype(P['font'],size)
def cells(W,n=4):return [(W*i/n, W*(i+1)/n) for i in range(n)]
def txt(d,xy,s,P,size,fill,anchor='mm'):d.text(xy,s,fill=fill,font=fnt(P,size),anchor=anchor)
def rings(W,H,P,vals):
    im=Image.new('RGBA',(W,H),P['ground']+(255,)); lay=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(lay); bd=ImageDraw.Draw(im)
    for (x0,x1),k,v in zip(cells(W),KEYS,vals):
        cx=(x0+x1)/2; cy=H/2-4; r=19
        box=[cx-r,cy-r,cx+r,cy+r]
        bd.arc(box,135,405,fill=P['rest'],width=4)
        if v is not None: d.arc(box,135,135+270*v,fill=ramp(P,v)+(255,),width=4)
        txt(bd,(cx,cy+1),'—' if v is None else '%d'%round(v*100),P,13,P['text'] if v is not None else mix(P['ground'],P['text'],0.45))
        txt(bd,(cx,H-6),k,P,10,P['label'])
    return glow(im,lay,2.6,1.5).convert('RGB')
def tubes(W,H,P,vals):
    im=Image.new('RGBA',(W,H),P['ground']+(255,)); lay=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(lay); bd=ImageDraw.Draw(im)
    for (x0,x1),k,v in zip(cells(W),KEYS,vals):
        cx=(x0+x1)/2; w=x1-x0-16; tx0=cx-w/2; ty=H/2+3
        txt(bd,(tx0,13),k,P,10,P['label'],'lm'); txt(bd,(tx0+w,13),'—' if v is None else '%d%%'%round(v*100),P,12,P['text'] if v is not None else mix(P['ground'],P['text'],0.45),'rm')
        bd.rounded_rectangle([tx0,ty,tx0+w,ty+7],radius=3.5,fill=P['rest'])
        if v is not None and v>0.01: d.rounded_rectangle([tx0,ty,tx0+max(7,w*v),ty+7],radius=3.5,fill=ramp(P,v)+(255,))
        for s in range(1,4): bd.line([tx0+w*s/4,ty+10,tx0+w*s/4,ty+12],fill=P['grid'])
    return glow(im,lay,3.0,1.6).convert('RGB')
def vu(W,H,P,vals):
    im=Image.new('RGBA',(W,H),P['ground']+(255,)); lay=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(lay); bd=ImageDraw.Draw(im)
    for (x0,x1),k,v in zip(cells(W),KEYS,vals):
        cx=(x0+x1)/2; w=x1-x0-10
        bd.rounded_rectangle([cx-w/2,3,cx+w/2,H-3],radius=5,fill=mix(P['ground'],P['rest'],0.7),outline=P['grid'])
        px,py,r=cx,H-10,30
        for t in range(0,11):
            a=math.radians(210+120*t/10); x=px+r*math.cos(a); y=py+r*math.sin(a); x2=px+(r-4 if t%5 else r-7)*math.cos(a); y2=py+(r-4 if t%5 else r-7)*math.sin(a)
            bd.line([x,y,x2,y2],fill=P['hot'] if t>=9 else P['label'],width=1)
        if v is not None:
            a=math.radians(210+120*v); d.line([px,py,px+(r-2)*math.cos(a),py+(r-2)*math.sin(a)],fill=ramp(P,v)+(255,),width=2)
        else:
            a=math.radians(210); bd.line([px,py,px+(r-2)*math.cos(a),py+(r-2)*math.sin(a)],fill=mix(P['ground'],P['text'],0.3),width=1)
        bd.ellipse([px-2,py-2,px+2,py+2],fill=P['text'])
        txt(bd,(cx-w/2+6,H-9),k,P,9,P['label'],'lm'); txt(bd,(cx+w/2-6,H-9),'—' if v is None else '%d'%round(v*100),P,10,P['text'],'rm')
    return glow(im,lay,2.2,1.4).convert('RGB')
def ringspark(W,H,P,vals):
    im=Image.new('RGBA',(W,H),P['ground']+(255,)); lay=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(lay); bd=ImageDraw.Draw(im)
    for (x0,x1),k,v in zip(cells(W),KEYS,vals):
        r=14; cx=x0+r+6; cy=H/2-3
        bd.arc([cx-r,cy-r,cx+r,cy+r],0,360,fill=P['rest'],width=3)
        if v is not None: d.arc([cx-r,cy-r,cx+r,cy+r],-90,-90+360*v,fill=ramp(P,v)+(255,),width=3)
        txt(bd,(cx,cy+1),'—' if v is None else '%d'%round(v*100),P,11,P['text'] if v is not None else mix(P['ground'],P['text'],0.45))
        txt(bd,(cx,H-5),k,P,9,P['label'])
        sx0=cx+r+5; sx1=x1-5; sy0=10; sy1=H-14
        bd.line([sx0,sy1,sx1,sy1],fill=P['grid'])
        if v is not None:
            sp=spark(v); pts=[(sx0+(sx1-sx0)*i/(len(sp)-1), sy1-(sy1-sy0)*s) for i,s in enumerate(sp)]
            d.line(pts,fill=ramp(P,v)+(220,),width=1)
            d.ellipse([pts[-1][0]-1.8,pts[-1][1]-1.8,pts[-1][0]+1.8,pts[-1][1]+1.8],fill=P['peak']+(255,))
        else:
            txt(bd,((sx0+sx1)/2,(sy0+sy1)/2),'no reading',P,8,mix(P['ground'],P['text'],0.4))
    return glow(im,lay,2.4,1.5).convert('RGB')
VAR={'E_rings':rings,'F_tubes':tubes,'G_vu':vu,'H_ringspark':ringspark}
for look,mid in (('kasandra',1566),('graphite',1594)):
    P=PAL[look]
    for name,fn in VAR.items():
        for st,vals in STATES.items():
            m=fn(1920-mid-12,56,P,vals); m.save(f'{name}_{look}_{st}.png'); m.resize((m.size[0]*3,m.size[1]*3),Image.LANCZOS).save(f'{name}_{look}_{st}_x3.png')
labels={'E_rings':'E · Neon rings','F_tubes':'F · Neon tubes','G_vu':'G · VU needles','H_ringspark':'H · Ring and a minute of history'}
tiles=[]
for name,lab in labels.items():
    for look,st in (('kasandra','busy'),('kasandra','idle'),('graphite','busy')):
        tiles.append(('%s (%s look, %s)'%(lab,'Kasandra' if look=='kasandra' else 'Graphite','a model at work' if st=='busy' else 'as today, no model'),Image.open(f'{name}_{look}_{st}_x3.png')))
w=max(t[1].size[0] for t in tiles); h=sum(t[1].size[1]+34 for t in tiles)+10
sheet=Image.new('RGB',(w+20,h),(245,242,236)); dd=ImageDraw.Draw(sheet); y=10
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
for lab,img in tiles:
    dd.text((10,y),lab,fill=(30,30,30),font=font); y+=26; sheet.paste(img,(10,y)); y+=img.size[1]+8
sheet.save('meter_styles_sheet.png'); print(sheet.size)
