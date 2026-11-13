# R24 edit 19: the 3.3 V buck-boost U4 (TPS63070), laid out as the datasheet's section 11 asks.
#  - L1 turned and moved next to the L1/L2 pins (1.6 mm, was 4.4 mm and 8 mm with both switch nodes on In3);
#    switch nodes are B.Cu copper areas; PGND (pin 10) runs between them to three vias under the inductor body.
#  - VIN: C402 becomes 10 uF 0603 (CL10A106KP8NNNC) at the VIN pins, C413 22 uF 0805 beside it; both in one
#    B.Cu SYS_RAW area with two vias to the In2 SYS_RAW plane.
#  - VOUT: new C416 10 uF 0603 at the VOUT pins, C414 and new C417-C419 22 uF 0805 in a row behind it (88 uF
#    nominal, about 40 uF at 3.3 V); one B.Cu 3V3_SYS area with three vias to the In2 3V3_SYS plane. C405 (100 nF,
#    3 mm away) removed.
#  - PS/SYNC (pin 1) joins EN on 3V3_ENABLE, pulled to SYS_RAW through R423 100 k (the datasheet's series
#    resistor for inputs tied to VIN); R423, the feedback divider R410/R411 and C401 (VAUX) moved next to their pins.
#  - U6 (LCD 3.0 V LDO) with C307/C308 moved east onto its In3 feed to make room.
#  Copper-area priorities, here and in edits 20-21: switch nodes 8, supply and output 7, ground 6 (distinct, so the
#  fill does not depend on the order KiCad visits neighbouring areas).
exec(open(sys.argv[2]).read())
import math
def orient(f, num, d):
    """Turn footprint f so that its pad num lies in direction d ('N','S','E','W') from its centre."""
    want={'N':(0,-1),'S':(0,1),'E':(1,0),'W':(-1,0)}[d]
    for r in (0,90,180,-90):
        f.SetOrientationDegrees(r); c=f.GetPosition()
        p=[q for q in f.Pads() if q.GetNumber()==num][0].GetPosition(); vx,vy=mm(p.x-c.x),mm(p.y-c.y)
        if vx*want[0]+vy*want[1] > 0.9*math.hypot(vx,vy): return r
    raise AssertionError((f.GetReference(),num,d))
def mv(ref,x,y,num='1',d=None):
    f=move(ref,x,y)
    if d: orient(f,num,d)
    return f
def new(lib,name,ref,value,lcsc,note,x,y,d,old=None):
    f=place(lib,name,ref,value,lcsc,note,x,y,0,old=old); orient(f,'1',d); return f
def pad_net(ref,num,netname):
    [p for p in fpr(ref).Pads() if p.GetNumber()==num][0].SetNet(net(netname))
V=lambda x,y,n: add_via(x,y,net(n))
T=lambda lay,pts,n,w=0.15: add(lay,pts,net(n),w)

# ---- rip-up
LOCAL={'U4_L1_SW','U4_L2_SW','U4_VAUX','U4_FB','3V3_ENABLE'}
BOX=(-27.6,97.2,-13.2,110.9)
kill_tracks(lambda t: t.GetNetname() in LOCAL)
kill_tracks(lambda t: t.GetNetname() in ('GND','3V3_SYS','SYS_RAW') and track_in_box(t,BOX))
kill_tracks(lambda t: t.GetNetname()=='LCD_VCI_3V0' and track_in_box(t,(-30,100,-5,115)))
KILL.append(fpr('C405'))

# ---- parts
mv('L1',-22.35,103.0,'1','N')
new('Capacitor_SMD','C_0603_1608Metric','C402','CL10A106KP8NNNC','C19702','10 uF 10 V X5R, U4 VIN high-frequency bypass',-18.5,99.6,'S',old=fpr('C402'))
mv('C413',-20.4,98.55,'1','S')
mv('R423',-17.05,99.9,'1','N')
mv('C401',-15.25,103.25,'1','W')
mv('R411',-15.2,104.75,'1','W')
mv('R410',-15.2,106.25,'1','E')
new('Capacitor_SMD','C_0603_1608Metric','C416','CL10A106KP8NNNC','C19702','10 uF 10 V X5R, U4 VOUT high-frequency bypass',-18.3,105.7,'W')
mv('C414',-20.3,108.25,'1','N')
for ref,x in (('C417',-22.45),('C418',-24.45),('C419',-26.45)):
    new('Capacitor_SMD','C_0805_2012Metric',ref,'CL21A226MQQNNNE','C5674','22 uF 6.3 V X5R, U4 VOUT bulk',x,108.25,'N')
mv('U6',-6.0,106.5); fpr('U6').SetOrientationDegrees(180)
mv('C307',-6.0,109.15,'1','E')
mv('C308',-3.4,105.65,'1','N')
mv('C303',-28.55,107.5)
for ref,nets in (('C402',('SYS_RAW','GND')),('C416',('3V3_SYS','GND')),('C417',('3V3_SYS','GND')),('C418',('3V3_SYS','GND')),('C419',('3V3_SYS','GND'))):
    pad_net(ref,'1',nets[0]); pad_net(ref,'2',nets[1])
pad_net('U4','1','3V3_ENABLE')

# ---- U4 copper (B.Cu)
zone('B.Cu',[(-20.95,98.9),(-19.55,98.9),(-19.55,99.85),(-18.0,99.85),(-18.0,102.05),(-18.95,102.05),(-18.95,101.4),(-20.95,101.4)],'SYS_RAW',prio=7,name='U4 VIN')
zone('B.Cu',[(-21.0,96.2),(-18.0,96.2),(-18.0,99.6),(-19.35,99.6),(-19.35,98.7),(-21.0,98.7)],'GND',prio=6,name='U4 input capacitor ground')
zone('B.Cu',[(-19.35,101.95),(-21.05,101.95),(-21.05,101.55),(-21.75,101.55),(-21.75,102.66),(-19.35,102.66)],'U4_L1_SW',prio=8,name='U4 SW1')
zone('B.Cu',[(-19.35,103.34),(-21.75,103.34),(-21.75,104.45),(-21.05,104.45),(-21.05,104.05),(-19.35,104.05)],'U4_L2_SW',prio=8,name='U4 SW2')
zone('B.Cu',rect(-23.5,102.2,-21.9,103.8),'GND',prio=6,name='U4 PGND')
zone('B.Cu',[(-19.05,103.95),(-18.0,103.95),(-18.0,104.95),(-18.25,104.95),(-18.25,106.35),(-16.35,106.35),(-16.35,107.25),
             (-19.3,107.25),(-19.3,107.85),(-28.4,107.85),(-28.4,106.55),(-19.75,106.55),(-19.75,104.95),(-19.05,104.95)],'3V3_SYS',prio=7,name='U4 VOUT')
zone('B.Cu',rect(-27.25,108.5,-18.95,109.85),'GND',prio=6,name='U4 output capacitor ground')
T('B.Cu',[(-19.2,103.0),(-22.4,103.0)],'GND',0.3)                                   # PGND between the switch nodes, to the first via
T('B.Cu',[(-18.6,103.0),(-17.87,103.0),(-17.31,103.56),(-17.31,103.75),(-16.85,103.75)],'GND',0.114)   # PGND to GND pin 4
for x,y in ((-22.4,103.0),(-23.15,102.55),(-23.15,103.45)): V(x,y,'GND')
for x,y in ((-20.6,101.15),(-19.7,101.15)): V(x,y,'SYS_RAW')
for x,y in ((-20.3,96.55),(-19.3,97.5),(-18.5,97.6)): V(x,y,'GND')
for x in (-18.0,-17.3,-16.6): V(x,106.8,'3V3_SYS')
for x in (-19.25,-21.35,-23.45,-25.45): V(x,108.9,'GND')
T('B.Cu',[(-17.05,99.4),(-17.5,99.85),(-18.0,99.85),(-18.5,100.35)],'SYS_RAW',0.2)                             # R423 to VIN
T('B.Cu',[(-17.05,100.6),(-17.6,100.95),(-17.775,101.1),(-17.775,101.6)],'3V3_ENABLE',0.12)      # R423 to EN
T('B.Cu',[(-16.85,102.25),(-17.6,102.25),(-17.775,102.075),(-17.775,101.6)],'3V3_ENABLE',0.12)  # PS/SYNC to EN
T('B.Cu',[(-17.275,101.6),(-16.45,101.6)],'GND',0.15); V(-16.45,101.6,'GND')       # VSEL low
T('B.Cu',[(-16.85,103.25),(-15.75,103.25)],'U4_VAUX',0.2)
T('B.Cu',[(-16.85,103.75),(-16.65,103.95),(-14.75,103.95),(-14.75,103.25),(-14.1,103.25)],'GND',0.15); V(-14.1,103.25,'GND')
T('B.Cu',[(-17.275,104.4),(-17.275,104.75),(-15.7,104.75),(-15.7,106.25)],'U4_FB',0.12)
T('B.Cu',[(-14.7,104.75),(-14.0,104.75)],'GND',0.2); V(-14.0,104.75,'GND')
T('B.Cu',[(-14.7,106.25),(-14.0,106.25)],'3V3_SYS',0.2); V(-14.0,106.25,'3V3_SYS')
T('B.Cu',[(-17.525,105.7),(-16.6,105.7)],'GND',0.3); V(-16.6,105.7,'GND')

# ---- U6 at its new place (vias clear of the In3 LCD_1V8 route at y 107.36)
T('B.Cu',[(-5.05,105.4),(-4.3,105.4),(-4.05,105.15),(-3.4,105.15)],'LCD_VCI_3V0',0.2)
T('B.Cu',[(-4.3,105.4),(-4.3,107.6),(-3.9,108.0)],'LCD_VCI_3V0',0.2); V(-3.9,108.0,'LCD_VCI_3V0')
T('In3.Cu',[(-3.9,108.0),(-3.9,108.28),(-0.68,108.28)],'LCD_VCI_3V0',0.152)
T('B.Cu',[(-6.0,107.6),(-6.0,106.5)],'GND',0.2); V(-6.0,106.5,'GND')
T('B.Cu',[(-3.4,106.15),(-3.4,106.9)],'GND',0.2); V(-3.4,106.9,'GND')
T('B.Cu',[(-6.95,107.6),(-7.7,106.6)],'3V3_SYS',0.2); V(-7.7,106.6,'3V3_SYS')
T('B.Cu',[(-5.05,107.6),(-5.05,108.45),(-6.95,108.45),(-6.95,107.6)],'3V3_SYS',0.2)
T('B.Cu',[(-5.5,109.15),(-5.05,108.7),(-5.05,108.45)],'3V3_SYS',0.2)
T('B.Cu',[(-6.5,109.15),(-7.5,108.6)],'GND',0.2); V(-7.5,108.6,'GND')
# ---- links the rip-up cut: C303 (moved 0.55 mm west for C419), U5 pin 3, C302 ground
kill_tracks(lambda t: t.GetNetname()=='GND' and t.Type()!=pcbnew.PCB_VIA_T and (near(t.GetStart(),-28.5,107.5) or near(t.GetEnd(),-28.5,107.5) or near(t.GetStart(),-28.72,107.72)))
T('B.Cu',[(-28.05,107.5),(-28.05,106.51),(-28.491,106.509)],'3V3_SYS',0.152)
T('B.Cu',[(-29.05,107.5),(-28.72,108.0),(-28.72,109.03)],'GND',0.152)
T('B.Cu',[(-12.95,109.1),(-13.7,108.35)],'3V3_SYS',0.2); V(-13.7,108.35,'3V3_SYS')
T('B.Cu',[(-12.5,104.5),(-14.0,104.75)],'GND',0.2)

prune({'GND','3V3_SYS','SYS_RAW','LCD_VCI_3V0'},(-40,88,12,125))   # every new track ends on a pad or via
print('u4: done')
