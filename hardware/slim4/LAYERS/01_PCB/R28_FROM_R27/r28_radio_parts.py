# R28 edit 45: the peer-to-peer radio, parts and nets. U15 is a Seeed Wio-SX1262 module (Semtech SX1262, 862-930 MHz,
# +22 dBm, IPEX antenna socket; Seeed 114993390, FCC ID Z4T-WIO-SX1262) on the back, west of U1 in copper that was
# empty in R27. Its footprint is drawn here from the Seeed datasheet V1.1 Figure 9 (top view): 12 pads 0.6 x 2.2 mm
# centred on the edges of the 11.6 x 11.0 body; pins 1-8 (RF_SW MISO MOSI SCK NRST NSS GND VCC) on one 11.6 mm edge,
# 1.27 mm pitch, pin 1 centre 1.33 mm from the left; pins 12-9 (DIO1 BUSY GND ANT) on the other, from 2.60 mm.
# Pin 9 (ANT) has no net: on the IPEX variant it is not connected.
# The radio is an add-on that leaves every R27 function as it was: it only uses U1 pins that had no net (GPIO39-41,
# GPIO49-53; none is a strapping pin) and copper that was empty, and it takes power from 3V3_SYS through R701, a
# 0 ohm link: with R701 off the module is unpowered and the board is R27. C702 100 nF and C701 10 uF sit at the
# module's VCC pin. Under the module there is only ground (Seeed's layout rule): a B.Cu GND zone over the body and
# the strips north and south of it, stitched to the In1/In4 ground planes by vias outside the body.
# Pin assignment (module pin -> net -> U1 pad/GPIO), on U1's north row: the free pads there are the ones whose escapes
# reach open board (GPIO28-33 on the west side are enclosed by R27's escapes). Pad 98 (GPIO54), beside XTAL_N, stays
# empty; NRST, which only moves at a radio reset, takes pad 97 next to it.
#   1 RF_SW -> RADIO_RF_SW -> 80 GPIO39     2 MISO -> RADIO_MISO -> 81 GPIO40     3 MOSI -> RADIO_MOSI -> 82 GPIO41
#   4 SCK   -> RADIO_SCK   -> 92 GPIO49     6 NSS  -> RADIO_NSS  -> 93 GPIO50    12 DIO1 -> RADIO_DIO1 -> 94 GPIO51
#   11 BUSY -> RADIO_BUSY  -> 95 GPIO52     5 NRST -> RADIO_NRST -> 97 GPIO53
# The signal routes are edit 46.
exec(open(sys.argv[2]).read())
X, Y, ROT = -20.6, 85.5, 270          # body centre; rotation as KiCad shows the placed part (pins 1-8 face U1, east)
BW, BH = 11.6, 11.0                   # body, datasheet Figure 9
PAD = (0.6, 2.2)
PINS = {'1': 'RADIO_RF_SW', '2': 'RADIO_MISO', '3': 'RADIO_MOSI', '4': 'RADIO_SCK', '5': 'RADIO_NRST', '6': 'RADIO_NSS',
        '7': 'GND', '8': 'RADIO_3V3', '9': None, '10': 'GND', '11': 'RADIO_BUSY', '12': 'RADIO_DIO1'}
U1PAD = {'80': 'RADIO_RF_SW', '81': 'RADIO_MISO', '82': 'RADIO_MOSI', '92': 'RADIO_SCK', '93': 'RADIO_NSS',
         '94': 'RADIO_DIO1', '95': 'RADIO_BUSY', '97': 'RADIO_NRST'}
for nn in set(v for v in PINS.values() if v and v != 'GND'): net(nn, create=True)

# ---- the footprint (drawn top view, at the origin; then flipped to the back) ------------------------------------
f = pcbnew.FOOTPRINT(b)
lay = lambda n: b.GetLayerID(n)
for i in range(8):
    x, y = -BW/2 + 1.33 + 1.27*i, BH/2
    p = pcbnew.PAD(f); p.SetNumber(str(i + 1)); f.Add(p); p.SetPos0(pcbnew.VECTOR2I(MM(x), MM(y))); p.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
for i in range(4):
    x, y = -BW/2 + 2.60 + 1.27*i, -BH/2
    p = pcbnew.PAD(f); p.SetNumber(str(12 - i)); f.Add(p); p.SetPos0(pcbnew.VECTOR2I(MM(x), MM(y))); p.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
for p in f.Pads():
    p.SetShape(pcbnew.PAD_SHAPE_RECT); p.SetAttribute(pcbnew.PAD_ATTRIB_SMD); p.SetLayerSet(p.SMDMask())
    p.SetSize(pcbnew.VECTOR2I(MM(PAD[0]), MM(PAD[1])))
def shape(kind, layer, a, c, w):
    s = pcbnew.FP_SHAPE(f); s.SetShape(kind); s.SetLayer(lay(layer)); s.SetWidth(MM(w))
    s.SetStart0(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); s.SetEnd0(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
    if kind == pcbnew.SHAPE_T_CIRCLE: s.SetFilled(True)
    f.Add(s); s.SetDrawCoord(); return s
shape(pcbnew.SHAPE_T_RECT, 'F.Fab', (-BW/2, -BH/2), (BW/2, BH/2), 0.1)                                    # body
shape(pcbnew.SHAPE_T_RECT, 'F.CrtYd', (-BW/2 - 0.25, -BH/2 - PAD[1]/2 - 0.25), (BW/2 + 0.25, BH/2 + PAD[1]/2 + 0.25), 0.05)
for sx in (-1, 1):                                                                                         # silk: the pad-free edges
    shape(pcbnew.SHAPE_T_SEGMENT, 'F.SilkS', (sx*(BW/2 + 0.12), -BH/2 + 0.6), (sx*(BW/2 + 0.12), BH/2 - 0.6), 0.12)
shape(pcbnew.SHAPE_T_CIRCLE, 'F.SilkS', (-BW/2 + 1.33, BH/2 + PAD[1]/2 + 0.45), (-BW/2 + 1.33 + 0.2, BH/2 + PAD[1]/2 + 0.45), 0.05)  # pin 1
shape(pcbnew.SHAPE_T_CIRCLE, 'F.Fab', (BW/2 - 1.6, -BH/2 + 1.6), (BW/2 - 1.6 + 0.6, -BH/2 + 1.6), 0.05)  # IPEX socket (Figure 8)
f.SetAttributes(pcbnew.FP_SMD)
b.Add(f)
f.SetPosition(pcbnew.VECTOR2I(MM(X), MM(Y))); f.Flip(f.GetPosition(), False); f.SetOrientationDegrees(ROT)
f.SetReference('U15'); f.SetValue('Wio-SX1262'); f.Reference().SetVisible(False); f.Value().SetVisible(False)
f.SetFPID(pcbnew.LIB_ID('SLIM4', 'FP_U15'))
f.SetDescription('Wio-SX1262 | Seeed 114993390 (Wio-SX1262 with IPEX), JLC global sourcing | R28: LoRa/FSK radio module, '
                 '11.6 x 11.0 x 2.95 mm, land pattern from the Seeed datasheet V1.1 Figure 9; one reflow only (place it in the second, back-side pass)')
f.SetKeywords('SLIM4 R28 U Wio-SX1262 SX1262 radio')
for p in f.Pads():
    nn = PINS[p.GetNumber()]
    if nn: p.SetNet(net(nn))
for num, nn in U1PAD.items():
    q = pad('U1', num); assert q.GetNetname() == '', (num, q.GetNetname()); q.SetNet(net(nn))
P = {p.GetNumber(): (round(mm(p.GetPosition().x), 3), round(mm(p.GetPosition().y), 3)) for p in f.Pads()}
assert P['1'][0] > X and P['8'][0] > X and P['1'][1] < P['8'][1] and P['12'][0] < X, P   # pins 1-8 east, 1 north

# courtyard clear of every other back part
f.BuildCourtyardCaches(); mine = f.GetCourtyard(pcbnew.B_CrtYd)
for o in b.GetFootprints():
    if o.GetReference() == 'U15' or not o.IsFlipped() or _dead(o): continue
    o.BuildCourtyardCaches(); oc = o.GetCourtyard(pcbnew.B_CrtYd)
    if oc.OutlineCount() == 0: continue
    x_ = mine.CloneDropTriangulation(); x_.BooleanIntersection(oc, pcbnew.SHAPE_POLY_SET.PM_FAST)
    assert x_.Area() == 0, 'U15 courtyard overlaps ' + o.GetReference()
# nothing of another net under the body on any copper layer (the area was empty in R27)
BODY = (X - BH/2, Y - BW/2, X + BH/2, Y + BW/2)          # rotated 270: the 11.0 side runs along x
for t in _copper_items():
    assert not track_in_box(t, (BODY[0] - 1.2, BODY[1] - 1.5, BODY[2] + 1.2, BODY[3] + 1.5)), 'copper under U15: ' + t.GetNetname()

# ---- ground under the module ------------------------------------------------------------------------------------
GZ = (BODY[0], BODY[1] - 1.4, BODY[2], BODY[3] + 1.4)
zone('B.Cu', rect(*GZ), 'GND', prio=6, conn='solid', name='U15 radio ground')
gv = []
for yy in (GZ[1] + 0.7, GZ[3] - 0.7):
    for xx in (BODY[0] + 1.0, BODY[0] + 3.75, BODY[0] + 6.5, BODY[0] + 9.25):
        assert via_free(xx, yy, 'GND', 0.12), (xx, yy)
        add_via(xx, yy, G); NEW_VIAS.append(pcbnew.VECTOR2I(MM(xx), MM(yy))); gv.append((xx, yy))

# ---- power: C702 100 nF across pins 8/7, C701 10 uF and R701 0 ohm south of them ---------------------------------
# Placed by hand (positions from the module's own pads) and checked: courtyards clear of every other back part, pads
# and tracks 0.12 mm from other nets' copper, the 3V3_SYS via inside the filled In2 3V3_SYS plane.
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
p7, p8 = P['7'], P['8']
c702 = put('Capacitor_SMD', 'C_0402_1005Metric', 'C702', 'CL05B104KO5NNNC', 'C1525', 'R28: radio module VCC decoupling, across pins 8 and 7',
           p8[0] + 1.83, round((p7[1] + p8[1])/2 + 0.115, 3), 90, [('GND', (p8[0] + 1.83, p7[1])), ('RADIO_3V3', (p8[0] + 1.83, p8[1]))])
link('GND', [c702['GND'], (p7[0] + 0.8, p7[1])])
link('RADIO_3V3', [c702['RADIO_3V3'], (p8[0] + 0.8, p8[1])])
c701 = put('Capacitor_SMD', 'C_0603_1608Metric', 'C701', 'CL10A106KP8NNNC', 'C19702', 'R28: radio module VCC bulk, 10 uF 10 V X5R',
           p8[0] - 0.1, p8[1] + 4.08, 0, [('GND', (p8[0] - 0.9, p8[1] + 4.08)), ('RADIO_3V3', (p8[0] + 0.7, p8[1] + 4.08))])
sv = min(gv, key=lambda v: math.hypot(v[0] - c701['GND'][0], v[1] - c701['GND'][1]))      # nearest stitching via
link('GND', [c701['GND'], sv])
link('RADIO_3V3', [c701['RADIO_3V3'], (c702['RADIO_3V3'][0] - 0.08, c701['RADIO_3V3'][1] - 1.1), c702['RADIO_3V3']])
r701 = put('Resistor_SMD', 'R_0402_1005Metric', 'R701', '0402WGF0000TCE', 'C17168',
           'R28: radio supply link from 3V3_SYS (remove it and the radio is unpowered)',
           c701['RADIO_3V3'][0], c701['RADIO_3V3'][1] + 1.7, 90,
           [('RADIO_3V3', (c701['RADIO_3V3'][0], c701['RADIO_3V3'][1] + 1.2)), ('3V3_SYS', (c701['RADIO_3V3'][0], c701['RADIO_3V3'][1] + 2.2))])
link('RADIO_3V3', [r701['RADIO_3V3'], c701['RADIO_3V3']])
v3 = (r701['3V3_SYS'][0], round(r701['3V3_SYS'][1] + 0.85, 3))
assert in_3v3_plane(*v3) and via_free(*v3, '3V3_SYS', 0.12, copper), v3
add_via(*v3, net('3V3_SYS')); NEW_VIAS.append(pcbnew.VECTOR2I(MM(v3[0]), MM(v3[1])))
link('3V3_SYS', [r701['3V3_SYS'], v3])
print('radio: U15 Wio-SX1262 at (%.2f, %.2f) rot %d, back; pins %s; ground zone %s with %d vias; '
      'C702 %s, C701 %s, R701 %s, 3V3_SYS via %s'
      % (X, Y, ROT, ', '.join('%s %s' % (k, PINS[k] or 'NC') for k in sorted(PINS, key=int)), tuple(round(v, 2) for v in GZ), len(gv),
         c702, c701, r701, v3))
