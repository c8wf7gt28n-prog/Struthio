# R24 edit 21: the backlight boost U7 (TPS61165) rebuilt in the free B.Cu area east of it, laid out as its datasheet
# section 11.1 asks.
#  - U7 turned so its SW and GND pins face east. L3's switch pad is 1.1 mm from SW (was 5.5 mm), D2's anode sits on
#    the same B.Cu switch area, and the output capacitor C309 closes the SW-D2-C309-GND loop on B.Cu next to the GND
#    pin (it closed through the planes, 8 mm round). Switch node, output and ground are copper areas, not 0.15 mm traces.
#  - Input capacitor C311 at the VIN pin with a via to the In2 SYS_RAW plane; C301 (100 nF on SYS_RAW, fed by an In3
#    trace) removed: C311 is 4.7 uF against the datasheet's 1 uF.
#  - Sense resistor R309 next to FB and the compensation capacitor C310 next to COMP.
#  - The panel's LED_A and LED_K keep their F.Cu runs and vias; from there B.Cu to the new block. CTRL keeps its route
#    from R422. The LCD_VCI_3V0 B.Cu run at x 24.52 moves to In3 (between two new vias) to let them cross.
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
def orient_off(f, num, dx, dy):
    for r in (0,90,180,-90):
        f.SetOrientationDegrees(r); c=f.GetPosition()
        p=[q for q in f.Pads() if q.GetNumber()==num][0].GetPosition()
        if abs(mm(p.x-c.x)-dx)<0.05 and abs(mm(p.y-c.y)-dy)<0.05: return r
    raise AssertionError((f.GetReference(),num,dx,dy))

# ---- rip-up
kill_tracks(lambda t: t.GetNetname() in ('BL_SW','BL_COMP'))
kill_tracks(lambda t: t.GetNetname()=='BACKLIGHT_PWM' and t.GetLayer()==L['B.Cu'] and track_in_box(t,(14.5,94,19,99)))
kill_tracks(lambda t: t.GetNetname()=='LCD_LED_A' and t.Type()!=pcbnew.PCB_VIA_T and t.GetLayer()==L['B.Cu'])
kill_tracks(lambda t: t.GetNetname()=='LCD_LED_K' and t.GetLayer() in (L['B.Cu'],L['In3.Cu']))
kill_tracks(lambda t: t.GetNetname()=='LCD_LED_K' and t.Type()==pcbnew.PCB_VIA_T and near(t.GetPosition(),17.8,100.82))
kill_tracks(lambda t: t.GetNetname()=='SYS_RAW' and track_in_box(t,(13,93,24,100)))
for seg in ((16.05,94.15,16.05,95.9),(14.5,100.0,16.2,100.0),(16.2,100.0,16.2,102.0)): remove('B.Cu',*seg,'GND')   # stubs to the old U7/C309/R309 ground pads
VCI=[t for t in TR if t.GetNetname()=='LCD_VCI_3V0' and t.Type()!=pcbnew.PCB_VIA_T and t.GetLayer()==L['B.Cu'] and abs(mm(t.GetStart().x)-24.52)<0.01 and abs(mm(t.GetEnd().x)-24.52)<0.01]
assert len(VCI)==1; KILL.append(VCI[0]); VA,VB=[(mm(q.x),mm(q.y)) for q in sorted((VCI[0].GetStart(),VCI[0].GetEnd()),key=lambda q:q.y)]
KILL.append(fpr('C301'))

# ---- parts
orient_off(move('U7',28.0,99.0),'3',0.95,-1.1)          # SW at the north-east corner, GND south-east
orient(move('L3',32.4,97.6),'2','W')
orient(move('D2',31.25,102.55),'A','N')
orient(move('C309',29.05,102.6),'2','N')
orient(move('R309',25.7,102.4),'1','N')
orient(move('C310',27.4,102.0),'1','N')
orient(move('C311',25.25,98.3),'1','N')

# ---- copper (B.Cu)
zone('B.Cu',[(29.2,97.45),(31.45,97.45),(31.45,100.25),(32.05,100.25),(32.05,101.75),(30.45,101.75),(30.45,98.35),(29.2,98.35)],'BL_SW',prio=8,name='U7 SW')
zone('B.Cu',rect(28.55,99.55,29.75,102.35),'GND',prio=6,name='U7 power ground')
zone('B.Cu',rect(28.55,102.85,32.05,104.9),'LCD_LED_A',prio=7,name='U7 output')
T('B.Cu',[(28.95,97.9),(30.6,97.9)],'BL_SW',0.4)
V(29.2,100.95,'GND')
for x,y,yp in ((33.9,95.2,95.9),(33.9,100.0,99.3)): V(x,y,'SYS_RAW'); T('B.Cu',[(x,y),(x,yp)],'SYS_RAW',0.4)   # L3 input to the In2 plane
T('B.Cu',[(27.05,97.6),(25.25,97.6)],'SYS_RAW',0.3); V(25.25,96.6,'SYS_RAW'); T('B.Cu',[(25.25,97.525),(25.25,96.6)],'SYS_RAW',0.3)
T('B.Cu',[(25.25,99.075),(25.25,99.95)],'GND',0.3); V(25.25,99.95,'GND')
T('B.Cu',[(28.0,100.6),(27.4,101.2),(27.4,101.5)],'BL_COMP',0.15)
T('B.Cu',[(27.4,102.5),(27.4,103.3)],'GND',0.2); V(27.4,103.3,'GND')
T('B.Cu',[(27.05,100.1),(27.05,100.6),(26.4,101.25),(25.7,101.6)],'LCD_LED_K',0.15)           # FB to the top of the sense resistor
T('B.Cu',[(25.7,103.2),(25.7,104.0)],'GND',0.3); V(25.7,104.0,'GND')
T('B.Cu',[(17.95,96.75),(18.6,97.4),(18.6,101.6),(25.7,101.6)],'LCD_LED_K',0.25)
T('B.Cu',[(17.25,99.45),(17.6,99.8),(17.6,105.3),(28.9,105.3),(29.05,103.6)],'LCD_LED_A',0.25)
T('B.Cu',[(13.89,94.88),(14.91,95.9),(27.6,95.9),(28.0,96.3),(28.0,97.9)],'BACKLIGHT_PWM',0.15)
V(*VA,'LCD_VCI_3V0'); V(*VB,'LCD_VCI_3V0')
T('In3.Cu',[VA,VB],'LCD_VCI_3V0',0.152)
prune({'GND','SYS_RAW','BACKLIGHT_PWM','LCD_LED_A','LCD_LED_K','LCD_VCI_3V0'},(5,85,36,112))
print('u7: done')
