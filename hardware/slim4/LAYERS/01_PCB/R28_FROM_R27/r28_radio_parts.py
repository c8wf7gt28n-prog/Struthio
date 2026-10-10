# R28 edit 45: the peer-to-peer radio, parts and nets. U15 is a RAKwireless RAK3172-9-SM-I (STM32WLE5CC: an SX126x-class
# LoRa/FSK radio with its own Cortex-M4; 902-928 MHz variant, IPEX antenna socket; FCC ID 2AF6B-RAK3172; LCSC C19723905)
# on the back, west of U1, in copper that was empty in R27. The module runs the radio itself and talks to U1 over a
# UART (AT commands, 115200 baud; its firmware can be replaced over the same UART), so it needs four U1 pins where a
# bare SX1262 needs six to eight: U1's free pads sit in a pad row whose escape lane holds about five tracks.
# Footprint from RAKwireless's RAK3172 datasheet (pad layout, top view): body 15.5 x 15.0 mm, 32 pads 0.7 x 1.8 mm at
# 1.0 mm pitch reaching 0.8 mm past the body edge; pins 1-12 along one 15.5 mm edge (pin 1 2.0 mm from the corner),
# 13-16 on the 15.0 mm edge opposite pins 25-32, 17-19 and 20-24 along the other 15.5 mm edge.
# The radio is an add-on that leaves every R27 function as it was: it only uses U1 pins that had no net and copper
# that was empty, and takes power from 3V3_SYS through R701, a 0 ohm link: with R701 off the module is unpowered and
# the board is R27. C702 100 nF and C701 10 uF sit at the module's VDD pin; R702 10 k holds BOOT0 low, so the module
# always starts its own firmware unless U1 raises BOOT0 on purpose. Under the module there is only ground: a B.Cu GND
# zone over the module, stitched to the In1/In4 ground planes by vias outside the body.
# Pin assignment (module pin -> net -> U1 pad/GPIO):
#   1 UART2_RX <- RADIO_UART_TX <- 80 GPIO39 (U1 transmits)    2 UART2_TX -> RADIO_UART_RX -> 81 GPIO40 (U1 receives)
#   22 RST     <- RADIO_NRST    <- 82 GPIO41                    21 BOOT0   <- RADIO_BOOT0   <- 93 GPIO50
#   24 VDD = RADIO_3V3; GND 11 17 18 23 28; every other pin unconnected (12 RF: only on the no-IPEX variant).
# The signal routes are edit 46.
exec(open(sys.argv[2]).read())
X, Y, ROT = -22.5, 86.0, 0            # body centre; rotation as KiCad shows the placed part (pins 20-24 face U1, north)
BW, BH = 15.5, 15.0                   # body, RAK3172 datasheet
PINS = {'1': 'RADIO_UART_TX', '2': 'RADIO_UART_RX', '21': 'RADIO_BOOT0', '22': 'RADIO_NRST', '24': 'RADIO_3V3',
        '11': 'GND', '17': 'GND', '18': 'GND', '23': 'GND', '28': 'GND'}
U1PAD = {'80': 'RADIO_UART_TX', '81': 'RADIO_UART_RX', '82': 'RADIO_NRST', '93': 'RADIO_BOOT0'}
for nn in set(v for v in PINS.values() if v != 'GND'): net(nn, create=True)

def land():
    """Pad centres of the datasheet's top view: (x, y, 'v' for a pad on a 15.5 mm edge, 'h' on a 15.0 mm edge)."""
    P = {}
    for k in range(1, 13): P[str(k)] = (BW/2 - 2.0 - (k - 1), -BH/2 + 0.1, 'v')
    for i, k in enumerate(range(13, 17)): P[str(k)] = (-BW/2 + 0.1, -BH/2 + 8.0 + i, 'h')
    for i, k in enumerate((17, 18, 19)): P[str(k)] = (-BW/2 + 2.5 + i, BH/2 - 0.1, 'v')
    for i, k in enumerate(range(20, 25)): P[str(k)] = (-BW/2 + 9.5 + i, BH/2 - 0.1, 'v')
    for i, k in enumerate(range(32, 24, -1)): P[str(k)] = (BW/2 - 0.1, -BH/2 + 4.0 + i, 'h')
    return P

# ---- the footprint (drawn top view, at the origin; then flipped to the back) ------------------------------------
f = pcbnew.FOOTPRINT(b)
lay = lambda n: b.GetLayerID(n)
for n, (x, y, o) in land().items():
    p = pcbnew.PAD(f); p.SetNumber(n); f.Add(p)
    p.SetPos0(pcbnew.VECTOR2I(MM(x), MM(y))); p.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    p.SetShape(pcbnew.PAD_SHAPE_RECT); p.SetAttribute(pcbnew.PAD_ATTRIB_SMD); p.SetLayerSet(p.SMDMask())
    p.SetSize(pcbnew.VECTOR2I(MM(0.7 if o == 'v' else 1.8), MM(1.8 if o == 'v' else 0.7)))
def shape(kind, layer, a, c, w):
    s_ = pcbnew.FP_SHAPE(f); s_.SetShape(kind); s_.SetLayer(lay(layer)); s_.SetWidth(MM(w))
    s_.SetStart0(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); s_.SetEnd0(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
    if kind == pcbnew.SHAPE_T_CIRCLE: s_.SetFilled(True)
    f.Add(s_); s_.SetDrawCoord(); return s_
shape(pcbnew.SHAPE_T_RECT, 'F.Fab', (-BW/2, -BH/2), (BW/2, BH/2), 0.1)                                    # body
shape(pcbnew.SHAPE_T_RECT, 'F.CrtYd', (-BW/2 - 1.05, -BH/2 - 1.05), (BW/2 + 1.05, BH/2 + 1.05), 0.05)     # pads + 0.25
shape(pcbnew.SHAPE_T_SEGMENT, 'F.SilkS', (-BW/2 - 0.12, -BH/2 + 1.0), (-BW/2 - 0.12, BH/2 - 8.6), 0.12)   # pad-free edge
shape(pcbnew.SHAPE_T_CIRCLE, 'F.SilkS', (BW/2 - 2.0, -BH/2 - 1.25), (BW/2 - 2.0 + 0.2, -BH/2 - 1.25), 0.05)  # pin 1
shape(pcbnew.SHAPE_T_CIRCLE, 'F.Fab', (-BW/2 + 1.6, -BH/2 + 1.6), (-BW/2 + 2.2, -BH/2 + 1.6), 0.05)        # IPEX socket
f.SetAttributes(pcbnew.FP_SMD)
b.Add(f)
f.SetPosition(pcbnew.VECTOR2I(MM(X), MM(Y))); f.Flip(f.GetPosition(), False); f.SetOrientationDegrees(ROT)
f.SetReference('U15'); f.SetValue('RAK3172-9-SM-I'); f.Reference().SetVisible(False); f.Value().SetVisible(False)
f.SetFPID(pcbnew.LIB_ID('SLIM4', 'FP_U15'))
f.SetDescription('RAK3172-9-SM-I | JLC C19723905 | R28: LoRa/FSK radio module (STM32WLE5CC), 902-928 MHz, IPEX, '
                 '15.5 x 15.0 x 2.6 mm, land pattern from the RAKwireless RAK3172 datasheet; one reflow only')
f.SetKeywords('SLIM4 R28 U RAK3172 STM32WL radio')
for p in f.Pads():
    nn = PINS.get(p.GetNumber())
    if nn: p.SetNet(net(nn))
for num, nn in U1PAD.items():
    q = pad('U1', num); assert q.GetNetname() == '', (num, q.GetNetname()); q.SetNet(net(nn))
P = {p.GetNumber(): (round(mm(p.GetPosition().x), 3), round(mm(p.GetPosition().y), 3)) for p in f.Pads()}
assert P['24'][1] < Y and P['21'][1] < Y and P['1'][1] > Y and P['24'][0] > P['21'][0], P      # 20-24 north, 1-12 south

f.BuildCourtyardCaches(); mine = f.GetCourtyard(pcbnew.B_CrtYd)
for o in b.GetFootprints():
    if o.GetReference() == 'U15' or not o.IsFlipped() or _dead(o): continue
    o.BuildCourtyardCaches(); oc = o.GetCourtyard(pcbnew.B_CrtYd)
    if oc.OutlineCount() == 0: continue
    x_ = mine.CloneDropTriangulation(); x_.BooleanIntersection(oc, pcbnew.SHAPE_POLY_SET.PM_FAST)
    assert x_.Area() == 0, 'U15 courtyard overlaps ' + o.GetReference()
CY = (X - BW/2 - 1.05, Y - BH/2 - 1.05, X + BW/2 + 1.05, Y + BH/2 + 1.05)
for t in _copper_items():                      # no B.Cu copper (tracks, vias) of R27 inside the module's courtyard
    if t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == L['B.Cu']:
        assert not track_in_box(t, CY), 'copper under U15: ' + t.GetNetname()

# ---- ground under the module ------------------------------------------------------------------------------------
zone('B.Cu', rect(*CY), 'GND', prio=6, conn='solid', name='U15 radio ground')
gv = []
for vx, vy in ((CY[0] + 0.55, Y - 6.0), (CY[0] + 0.55, Y - 3.0), (CY[0] + 0.55, Y + 4.5), (CY[0] + 0.55, Y + 6.5),
               (X - 1.5, CY[1] + 0.5), (X + 4.75, CY[3] - 0.5)):
    if via_free(vx, vy, 'GND', 0.12):
        add_via(vx, vy, G); NEW_VIAS.append(pcbnew.VECTOR2I(MM(vx), MM(vy))); gv.append((vx, vy))
assert len(gv) >= 4, gv

# ---- power: C702 100 nF and C701 10 uF north of pins 24 (VDD) / 23 (GND), R701 0 ohm from 3V3_SYS; R702 BOOT0 ----
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
FILL = pcbnew.SHAPE_POLY_SET()
for z in b.Zones():
    if z.GetNetname() == '3V3_SYS' and z.IsOnLayer(L['In2.Cu']):
        FILL.BooleanAdd(z.GetFilledPolysList(L['In2.Cu']), pcbnew.SHAPE_POLY_SET.PM_FAST)
def in_3v3_plane(x, y):
    pts = [(x, y)] + [(x + 0.45*math.cos(a*math.pi/4), y + 0.45*math.sin(a*math.pi/4)) for a in range(8)]
    return all(FILL.Contains(pcbnew.VECTOR2I(MM(px), MM(py)), -1, 0) for px, py in pts)
copper = _copper_items()
def put(lib, name, ref, value, lcsc, note, x, y, rot, nets):
    """Place a two-pad part on the back at (x, y, rot); nets: [(net, point)] - each pad takes the net of the point
    nearest to it. Asserts courtyard and pad clearance. Returns {net: pad centre}."""
    g = place(lib, name, ref, value, lcsc, note, x, y, rot); g.SetDescription(f'{value} | JLC {lcsc} | {note}')
    ps = list(g.Pads()); at = {}
    for nn, pt in nets:
        q = min(ps, key=lambda p: math.hypot(mm(p.GetPosition().x) - pt[0], mm(p.GetPosition().y) - pt[1]))
        q.SetNet(net(nn)); ps.remove(q); at[nn] = (round(mm(q.GetPosition().x), 3), round(mm(q.GetPosition().y), 3))
    assert not ps
    g.BuildCourtyardCaches(); cy = g.GetCourtyard(pcbnew.B_CrtYd)
    for o in b.GetFootprints():
        if o.GetReference() == ref or not o.IsFlipped() or _dead(o): continue
        o.BuildCourtyardCaches(); oc = o.GetCourtyard(pcbnew.B_CrtYd)
        if oc.OutlineCount() == 0: continue
        x_ = cy.CloneDropTriangulation(); x_.BooleanIntersection(oc, pcbnew.SHAPE_POLY_SET.PM_FAST)
        assert x_.Area() == 0, ref + ' courtyard overlaps ' + o.GetReference()
    for p in g.Pads():
        sh = p.GetEffectiveShape()
        for t in copper:
            if t.GetNetCode() != p.GetNetCode() and (t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == L['B.Cu']):
                assert not t.GetEffectiveShape().Collide(sh, MM(0.12)), (ref, t.GetNetname())
        for o in b.GetFootprints():
            if o.GetReference() == ref: continue
            for q in o.Pads():
                if q.GetNetCode() != p.GetNetCode() and q.IsOnLayer(L['B.Cu']):
                    assert not q.GetEffectiveShape().Collide(sh, MM(0.12)), (ref, o.GetReference(), q.GetNumber())
    return at
def link(nn, pts, w=0.3):
    for a, c in zip(pts, pts[1:]):
        assert seg_free('B.Cu', a, c, w, net(nn).GetNetCode(), 0.12, copper), (nn, a, c)
    add('B.Cu', pts, net(nn), w)
p24, p23, p21 = P['24'], P['23'], P['21']
top = p24[1] - 0.9                                           # outer end of the north pads
c702 = put('Capacitor_SMD', 'C_0402_1005Metric', 'C702', 'CL05B104KO5NNNC', 'C1525', 'R28: radio module VDD decoupling, across pins 24 and 23',
           (p24[0] + p23[0]) / 2, round(top - 0.95, 3), 0, [('RADIO_3V3', (p24[0], top - 0.95)), ('GND', (p23[0], top - 0.95))])
link('RADIO_3V3', [c702['RADIO_3V3'], (p24[0], top + 0.3)])
link('GND', [c702['GND'], (p23[0], top + 0.3)])
c701 = put('Capacitor_SMD', 'C_0603_1608Metric', 'C701', 'CL10A106KP8NNNC', 'C19702', 'R28: radio module VDD bulk, 10 uF 10 V X5R',
           (p24[0] + p23[0]) / 2, round(top - 2.45, 3), 0, [('RADIO_3V3', (p24[0] + 0.3, top - 2.45)), ('GND', (p23[0] - 0.3, top - 2.45))])
link('RADIO_3V3', [c701['RADIO_3V3'], (c702['RADIO_3V3'][0], c701['RADIO_3V3'][1]), c702['RADIO_3V3']])
vg = (round(c701['GND'][0] - 0.95, 3), c701['GND'][1])
assert via_free(*vg, 'GND', 0.12, copper), vg
add_via(*vg, G); NEW_VIAS.append(pcbnew.VECTOR2I(MM(vg[0]), MM(vg[1]))); link('GND', [c701['GND'], vg])
r701 = put('Resistor_SMD', 'R_0402_1005Metric', 'R701', '0402WGF0000TCE', 'C17168',
           'R28: radio supply link from 3V3_SYS (remove it and the radio is unpowered)',
           round(c701['RADIO_3V3'][0] + 1.75, 3), c701['RADIO_3V3'][1], 0,
           [('RADIO_3V3', (c701['RADIO_3V3'][0] + 1.2, c701['RADIO_3V3'][1])), ('3V3_SYS', (c701['RADIO_3V3'][0] + 2.3, c701['RADIO_3V3'][1]))])
link('RADIO_3V3', [r701['RADIO_3V3'], c701['RADIO_3V3']])
v3 = (round(r701['3V3_SYS'][0] + 0.85, 3), r701['3V3_SYS'][1])
assert in_3v3_plane(*v3) and via_free(*v3, '3V3_SYS', 0.12, copper), v3
add_via(*v3, net('3V3_SYS')); NEW_VIAS.append(pcbnew.VECTOR2I(MM(v3[0]), MM(v3[1])))
link('3V3_SYS', [r701['3V3_SYS'], v3])
r702 = put('Resistor_SMD', 'R_0402_1005Metric', 'R702', '0402WGF1002TCE', 'C25744',
           'R28: radio BOOT0 pull-down (the module starts its own firmware unless U1 raises BOOT0)',
           p21[0], round(top - 1.3, 3), 90, [('RADIO_BOOT0', (p21[0], top - 0.8)), ('GND', (p21[0], top - 1.8))])
link('RADIO_BOOT0', [r702['RADIO_BOOT0'], (p21[0], top + 0.3)])
vb = (r702['GND'][0], round(r702['GND'][1] - 0.85, 3))
assert via_free(*vb, 'GND', 0.12, copper), vb
add_via(*vb, G); NEW_VIAS.append(pcbnew.VECTOR2I(MM(vb[0]), MM(vb[1]))); link('GND', [r702['GND'], vb])
print('radio: U15 RAK3172 at (%.2f, %.2f) rot %d, back; pins %s; U1 pads %s; ground zone %s with %d vias; '
      'C702 %s, C701 %s, R701 %s, 3V3_SYS via %s, R702 %s'
      % (X, Y, ROT, ', '.join('%s %s' % (k, PINS[k]) for k in sorted(PINS, key=int)), U1PAD,
         tuple(round(v, 2) for v in CY), len(gv), c702, c701, r701, v3, r702))
