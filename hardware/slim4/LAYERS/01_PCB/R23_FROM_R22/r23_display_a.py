# R23 edit 15, part A: the display port moves to the front, under the panel (no adapter flex).
#  Panel: Crystalfontz CFAF7201280A0-050TN (5 in, 720 x 1280 IPS, ILI9881C). Its 40-pin 0.5 mm tail (contacts on the
#  back, pin 1 on the left seen from the display face) is 40 mm long and 57 mm wide for its first 21.5 mm. The datasheet
#  (section 7.6) folds it once behind the module: bend radius 1.5 mm, starting at least 2 mm past the glass. Folded,
#  the contacts face away from the board, so J1 is a top-contact socket on the front: Hirose FH12A-40S-0.5SH(55).
#  The fold keeps x: J1 pad k takes panel pin k. The tail end lands about 34.3 mm above the panel's bottom edge
#  (40 - 2 x 2 mm - 1.14 x 1.5 mm), so J1 sits just below the battery window and the panel's bottom edge at Y 109.8.
#  Part A removes the old J1 (back, FH12-20) and the copper that met it, clears the copper that crossed the new J1's
#  pads, places the new J1 and locks every remaining track and via. The cleared connections are routed in part B.
exec(open(sys.argv[2]).read())
X0,Y0=1.9,76.0   # x: clear of the crystal vias; panel centre at X 1.2 (tail centre is 0.7 right of it)
DISPLAY=['MIPI_DSI_CLK_P','MIPI_DSI_CLK_N','MIPI_DSI_D0_P','MIPI_DSI_D0_N','MIPI_DSI_D1_P','MIPI_DSI_D1_N',
         'LCD_VCI_3V0','LCD_1V8','LCD_RESX','LCD_LED_A','LCD_LED_K']
OLD=b.FindFootprintByReference('J1')
def on_old_pad(pt): return any(p.HitTest(pt) for p in OLD.Pads())
for t in TR:
    if t.Type()!=pcbnew.PCB_VIA_T and (on_old_pad(t.GetStart()) or on_old_pad(t.GetEnd())) and t not in KILL: KILL.append(t)
KILL.append(OLD)
# the display nets' tails, back to their source clusters; ground stubs left by the old J1
prune_all(set(DISPLAY),(-30.0,85.0,30.0,128.0))
prune({'GND'},(10.0,99.0,26.0,119.0))
# the new J1: front, mouth toward +Y (the folded tail comes up from the panel's bottom edge)
j=place('Connector_FFC-FPC','Hirose_FH12-40S-0.5SH_1x40-1MP_P0.50mm_Horizontal','J1','FH12A-40S-0.5SH(55)','C506795',
        'R23 display port, top contact: Crystalfontz CFAF7201280A0-050TN tail folded once behind the panel; pad k = panel pin k; '
        'land pattern common to FH12 bottom and top contact (Hirose FH12 catalogue)',X0,Y0,0,back=False)
j.SetAttributes(OLD.GetAttributes())
PIN={10:'LCD_VCI_3V0',11:'LCD_VCI_3V0',14:'LCD_RESX',17:'GND',18:'GND',19:'LCD_1V8',20:'LCD_1V8',21:'GND',24:'GND',27:'GND',
     28:'MIPI_DSI_CLK_P',29:'MIPI_DSI_CLK_N',30:'GND',31:'MIPI_DSI_D1_P',32:'MIPI_DSI_D1_N',33:'GND',34:'MIPI_DSI_D0_P',
     35:'MIPI_DSI_D0_N',36:'GND',37:'GND',38:'LCD_LED_A',39:'LCD_LED_K',40:'LCD_LED_K'}
for p in j.Pads():
    if p.GetNumber()=='MP': p.SetNet(b.FindNet('')); continue
    k=int(p.GetNumber()); x,y=mm(p.GetPosition().x),mm(p.GetPosition().y)
    assert abs(x-(X0-9.75+0.5*(k-1)))<1e-3 and abs(y-(Y0-1.85))<1e-3, (k,x,y)
    p.SetNet(net(PIN[k]) if k in PIN else b.FindNet(''))
# copper of other nets that the new pads (and 0.1 mm clearance) would touch, on F.Cu or as vias
JP=[p for p in j.Pads()]
def hits_j1(t):
    if t.Type()==pcbnew.PCB_VIA_T:
        return any(p.GetEffectiveShape().Collide(pcbnew.SEG(t.GetPosition(),t.GetPosition()),t.GetWidth()//2+MM(0.1)) for p in JP)
    if t.GetLayer()!=L['F.Cu']: return False
    return any(p.GetEffectiveShape().Collide(pcbnew.SEG(t.GetStart(),t.GetEnd()),t.GetWidth()//2+MM(0.1)) for p in JP)
CLEARED=sorted({t.GetNetname() for t in TR if not _dead(t) and t.GetNetname() not in DISPLAY and hits_j1(t)})
for t in TR:
    if not _dead(t) and t.GetNetname() in CLEARED and hits_j1(t): KILL.append(t)
prune_all(set(CLEARED),(X0-14.0,Y0-4.0,X0+16.0,Y0+4.0))
print('cleared under J1:',CLEARED)
# ground pins: a via under each pin or pair (pin 24's sits under the unused lane-2/3 pads 25 and 26)
X=lambda pin: X0-9.75+0.5*(pin-1)
for pins,vx in [((17,18),X(17)+0.25),((21,),X(21)),((24,),X(24)+0.7),((27,),X(27)),((30,),X(30)),((33,),X(33)),((36,37),X(36)+0.25)]:
    vy=Y0-0.85
    add_via(vx,vy,G)
    for pin in pins:
        if abs(X(pin)-vx)<1e-6: add("F.Cu",[(X(pin),Y0-1.3),(vx,vy)],G)
        elif len(pins)==2: add("F.Cu",[(X(pin),Y0-1.3),(vx,vy)],G)
        else: add("F.Cu",[(X(pin),Y0-1.3),(X(pin),vy),(vx,vy)],G)
for t in b.GetTracks():
    if not _dead(t): t.SetLocked(True)
