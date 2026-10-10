# R24 edit 20: the 1.2 V buck U3 (TLV62569; net 1V1_HP), laid out as its datasheet section 10.1 asks.
#  - U3 turned 90 degrees so its SW, GND and EN pins face L2; L2 turned so its switch pad is 1 mm from the SW pin
#    (the switch node ran 7 mm, through In3). SW is one short B.Cu area.
#  - Input capacitor C126 (10 uF) at the VIN pin in a B.Cu 3V3_SYS area with two vias to the In2 3V3 plane (the
#    VIN feed was a 0.1 mm trace); output capacitor C135 (22 uF) next to L2's output pad in a B.Cu 1V1_HP area with
#    two vias to the In2 1V1 plane; both capacitor grounds share one B.Cu ground area with three vias.
#  - FB keeps its divider R104/R105/C134 on the side away from the switch node.
exec(open(sys.argv[2]).read())
import math
V=lambda x,y,n: add_via(x,y,net(n))
T=lambda lay,pts,n,w=0.15: add(lay,pts,net(n),w)
def orient_off(f, num, dx, dy):
    for r in (0,90,180,-90):
        f.SetOrientationDegrees(r); c=f.GetPosition()
        p=[q for q in f.Pads() if q.GetNumber()==num][0].GetPosition()
        if abs(mm(p.x-c.x)-dx)<0.05 and abs(mm(p.y-c.y)-dy)<0.05: return r
    raise AssertionError((f.GetReference(),num,dx,dy))
def orient(f, num, d):
    want={'N':(0,-1),'S':(0,1),'E':(1,0),'W':(-1,0)}[d]
    for r in (0,90,180,-90):
        f.SetOrientationDegrees(r); c=f.GetPosition()
        p=[q for q in f.Pads() if q.GetNumber()==num][0].GetPosition(); vx,vy=mm(p.x-c.x),mm(p.y-c.y)
        if vx*want[0]+vy*want[1] > 0.9*math.hypot(vx,vy): return r
    raise AssertionError((f.GetReference(),num,d))

# ---- rip-up
kill_tracks(lambda t: t.GetNetname()=='CORE_SW')
kill_tracks(lambda t: t.GetNetname()=='FB_DCDC' and track_in_box(t,(-2.2,98.5,2.0,103.0)))
EN_RUN=lambda t: seg_match(t,'F.Cu',-0.6936,99.6308,-0.6936,82.1489)     # EN's F.Cu run from U1, kept and shortened
kill_tracks(lambda t: t.GetNetname()=='EN_DCDC' and track_in_box(t,(-1.0,99.2,1.5,103.0)) and not EN_RUN(t))
for t in TR:
    if t.GetNetname()=='EN_DCDC' and EN_RUN(t):
        if near(t.GetStart(),-0.6936,99.6308): t.SetStart(pcbnew.VECTOR2I(MM(-0.6936),MM(99.0)))
        else: t.SetEnd(pcbnew.VECTOR2I(MM(-0.6936),MM(99.0)))
kill_tracks(lambda t: t.GetNetname()=='1V1_HP' and track_in_box(t,(-2.95,98.0,7.0,106.0)))
kill_tracks(lambda t: t.GetNetname() in ('3V3_SYS','GND') and track_in_box(t,(-1.75,98.3,4.6,106.2)))

# ---- parts
u3=move('U3',0.0,101.0); orient_off(u3,'3',1.1,0.95)
orient(move('L2',4.7,101.0),'1','W')
orient(move('C126',0.0,104.0),'1','W')
move('C135',4.7,104.65)

# ---- copper (B.Cu)
zone('B.Cu',rect(1.45,101.5,2.8,102.65),'CORE_SW',prio=8,name='U3 SW')
zone('B.Cu',rect(-1.75,101.55,-0.45,105.55),'3V3_SYS',prio=7,name='U3 VIN')
zone('B.Cu',rect(0.3,103.2,4.4,105.5),'GND',prio=6,name='U3 capacitor ground')
zone('B.Cu',rect(5.0,99.0,6.85,105.4),'1V1_HP',prio=7,name='U3 output')
T('B.Cu',[(1.1,101.95),(2.9,101.95)],'CORE_SW',0.4)
T('B.Cu',[(1.1,101.0),(0.0,101.0)],'GND',0.3); V(0.0,101.0,'GND')     # under the body: clear of F.Cu DART_LEFT
for x,y in ((1.95,104.1),(2.75,104.9),(3.7,103.55)): V(x,y,'GND')
for x in (-1.35,-0.65): V(x,105.2,'3V3_SYS')
for x in (5.5,6.4): V(x,103.4,'1V1_HP')
V(-0.6936,99.0,'EN_DCDC')
T('B.Cu',[(-0.6936,99.0),(0.6,99.0),(1.1,99.5),(1.1,100.05)],'EN_DCDC',0.15)
T('B.Cu',[(-1.1,100.05),(-2.0,100.05),(-3.15,101.2),(-4.0,101.2)],'FB_DCDC',0.15)
T('B.Cu',[(4.42,106.0),(7.5,106.0)],'3V3_SYS',0.152); V(4.42,106.0,'3V3_SYS')     # R308 pull-up feed kept
# R403 (3V3 to the USB PHY supply) was fed along the old switch-node route: B.Cu to a via, In3 to the U3 VIN vias
e=[t for t in b.GetTracks() if t.GetNetname()=='3V3_SYS' and t.Type()!=pcbnew.PCB_VIA_T and (near(t.GetStart(),0.35,93.65,0.01) or near(t.GetEnd(),0.35,93.65,0.01))]
pt=[q for q in (e[0].GetStart(),e[0].GetEnd()) if near(q,0.35,93.65,0.01)][0]
T('B.Cu',[(mm(pt.x),mm(pt.y)),(0.3,93.7),(0.3,94.25),(0.2,94.35),(0.2,96.5),(0.45,97.35)],'3V3_SYS',0.1); V(0.45,97.35,'3V3_SYS')   # clear of the In3 DSI pairs at y 96.1-96.7
T('In3.Cu',[(0.45,97.35),(0.6,97.5),(0.6,103.0),(-0.65,104.25),(-0.65,105.2)],'3V3_SYS',0.152)
prune({'GND','3V3_SYS','1V1_HP','FB_DCDC','EN_DCDC'},(-12,88,12,112))
print('u3: done')
