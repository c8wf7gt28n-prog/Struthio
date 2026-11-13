# R24 edit 22: bulk capacitors for the two MAX98357A amplifiers. The datasheet asks for 10 uF and 0.1 uF at VDD;
# each amplifier had 1 uF and 0.1 uF. C420 (U8) and C421 (U9), 10 uF 0805, sit 1.5 mm below the VDD pins, tied to
# the existing VDD via/route on B.Cu, each with its own ground via.
exec(open(sys.argv[2]).read())
import math
V=lambda x,y,n: add_via(x,y,net(n))
T=lambda lay,pts,n,w=0.15: add(lay,pts,net(n),w)
def orient(f, num, d):
    want={'N':(0,-1),'S':(0,1),'E':(1,0),'W':(-1,0)}[d]
    for r in (0,90,180,-90):
        f.SetOrientationDegrees(r); c=f.GetPosition()
        p=[q for q in f.Pads() if q.GetNumber()==num][0].GetPosition(); vx,vy=mm(p.x-c.x),mm(p.y-c.y)
        if vx*want[0]+vy*want[1] > 0.9*math.hypot(vx,vy): return r
    raise AssertionError((f.GetReference(),num,d))
for ref,x,y,d in (('C420',-30.2,115.35,'E'),('C421',29.0,115.6,'W')):
    f=place('Capacitor_SMD','C_0805_2012Metric',ref,'CL21A106KAYNNNE','C15850','10 uF 25 V X5R, amplifier VDD bulk',x,y,0)
    orient(f,'1',d)
    for p in f.Pads(): p.SetNet(net('SYS_RAW' if p.GetNumber()=='1' else 'GND'))
T('B.Cu',[(-29.25,114.19),(-29.25,115.35)],'SYS_RAW',0.4)
T('B.Cu',[(-31.15,115.35),(-31.15,116.4)],'GND',0.4); V(-31.15,116.4,'GND')
T('B.Cu',[(28.25,113.6),(28.25,115.2)],'SYS_RAW',0.3)                          # from VDD pin 8, clear of the SPK_R_P via
T('B.Cu',[(29.95,115.6),(30.9,115.6)],'GND',0.4); V(30.9,115.6,'GND')
print('amps: done')
