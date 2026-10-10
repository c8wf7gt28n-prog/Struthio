# R28 edit 45: the peer-to-peer radio, parts and nets. U15 is a RAKwireless RAK3172-SiP (RAK3172-SIP-9-SM-NI: an
# STM32WLE5 - SX126x-class LoRa/FSK radio with its own Cortex-M4 - in a 12 x 12 x 1.22 mm LGA-73, 902-928 MHz) on the
# back, west of U1, in copper that was empty in R27. It runs the radio itself and talks to U1 over a UART (RUI3 AT
# commands, 115200 baud; its firmware can be replaced over the same UART), so it needs four U1 lines: U1's free pads
# sit in a pad row whose escape lane holds about five tracks.
# Footprint from RAKwireless's RAK3172-SiP layout recommendation (top view): 64 pads 0.37 x 1.17 mm at 0.6 mm pitch,
# 16 a side, reaching 0.235 mm past the 12.0 mm body; nine 1.6 mm ground pads on a 2.8 mm grid in the middle.
# The support circuit is RAKwireless's minimum reference (RAK3272-SiP breakout schematic): VDD 4.7 uF + 100 nF and
# 100 nF, VBAT 1 uF, VREF+ 4.7 uF + 100 nF, VDDA 1 uF + 100 nF, the DC-DC (VDDSMPS through a 120 ohm bead with 100 nF;
# VLXSMPS - 15 uH - VFBSMPS with 470 nF + 100 nF), VDDRF and VDDPA each through a 120 ohm bead with 1 uF, NRST 10 k
# pull-up + 100 nF, BOOT0 10 k pull-down, RF_OUT through a pi network (0 ohm series, shunt places not fitted) to a
# U.FL socket for the antenna cable.
# The radio is an add-on that leaves every R27 function as it was: it only uses U1 pins that had no net and copper
# that was empty, and takes power from 3V3_SYS through R701, a 0 ohm link: with R701 off the radio is unpowered and
# the board is R27. Its 3.3 V (RADIO_3V3) is a pour on In3 under the radio, which every supply part reaches by a via;
# under the SiP there is only ground (B.Cu zone, a via in each centre pad).
# Pin assignment (SiP pin -> net -> U1 pad/GPIO):
#   30 PA3/UART2_RX <- RADIO_UART_TX <- 80 GPIO39 (U1 transmits)   29 PA2/UART2_TX -> RADIO_UART_RX -> 81 GPIO40
#   44 NRST         <- RADIO_NRST    <- 82 GPIO41                   43 BOOT0        <- RADIO_BOOT0   <- 93 GPIO50
# The signal routes to U1 are edit 46.
exec(open(sys.argv[2]).read())
import os
X, Y, ROT = -23.0, 85.5, 270          # body centre; rotation as KiCad shows the placed part (UART pins face U1, east)
SIP = 12.0
RF_W = 0.18                           # 50 ohm microstrip, B.Cu over In4 ground (0.0994 mm prepreg, er 4.1)
PINS = {'3': 'RADIO_3V3', '4': 'RADIO_3V3', '6': 'RADIO_3V3', '7': 'RADIO_3V3', '55': 'RADIO_3V3',
        '10': 'RADIO_VFB', '11': 'RADIO_VDDSMPS', '13': 'RADIO_VLX', '53': 'RADIO_VDDPA', '54': 'RADIO_VDDRF',
        '29': 'RADIO_UART_RX', '30': 'RADIO_UART_TX', '37': 'RADIO_RF', '43': 'RADIO_BOOT0', '44': 'RADIO_NRST'}
for k in ('12', '28', '35', '36', '38', '39', '46', '47', '52', '56') + tuple(str(k) for k in range(65, 74)): PINS[k] = 'GND'
U1PAD = {'80': 'RADIO_UART_TX', '81': 'RADIO_UART_RX', '82': 'RADIO_NRST', '93': 'RADIO_BOOT0'}
for nn in sorted(set(v for v in PINS.values() if v != 'GND') | {'RADIO_ANT'}): net(nn, create=True)   # sorted: same net codes every build

def land():
    """RAK3172-SiP layout recommendation, top view: (x, y, w, h) per pad."""
    P_ = {}
    for k in range(1, 17):  P_[str(k)] = (-5.65, -4.5 + 0.6*(k - 1), 1.17, 0.37)
    for k in range(17, 33): P_[str(k)] = (-4.5 + 0.6*(k - 17), 5.65, 0.37, 1.17)
    for k in range(33, 49): P_[str(k)] = (5.65, 4.5 - 0.6*(k - 33), 1.17, 0.37)
    for k in range(49, 65): P_[str(k)] = (4.5 - 0.6*(k - 49), -5.65, 0.37, 1.17)
    for i, k in enumerate(range(65, 74)): P_[str(k)] = (-2.8 + 2.8*(i % 3), -2.8 + 2.8*(i // 3), 1.6, 1.6)
    return P_

# ---- the footprint (drawn top view, at the origin; then flipped to the back) ------------------------------------
f = pcbnew.FOOTPRINT(b)
lay = lambda n: b.GetLayerID(n)
for n, (x, y, w, h) in land().items():
    p = pcbnew.PAD(f); p.SetNumber(n); f.Add(p)
    p.SetPos0(pcbnew.VECTOR2I(MM(x), MM(y))); p.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    p.SetShape(pcbnew.PAD_SHAPE_RECT); p.SetAttribute(pcbnew.PAD_ATTRIB_SMD); p.SetLayerSet(p.SMDMask())
    p.SetSize(pcbnew.VECTOR2I(MM(w), MM(h)))
def shape(kind, layer, a, c, w):
    s_ = pcbnew.FP_SHAPE(f); s_.SetShape(kind); s_.SetLayer(lay(layer)); s_.SetWidth(MM(w))
    s_.SetStart0(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); s_.SetEnd0(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
    f.Add(s_); s_.SetDrawCoord(); return s_
H = SIP / 2
shape(pcbnew.SHAPE_T_RECT, 'F.Fab', (-H, -H), (H, H), 0.1)
shape(pcbnew.SHAPE_T_RECT, 'F.CrtYd', (-H - 0.485, -H - 0.485), (H + 0.485, H + 0.485), 0.05)       # pads + 0.25
for (a_, c_) in (((-H - 0.15, -H - 0.15), (-H + 0.9, -H - 0.15)), ((-H - 0.15, -H - 0.15), (-H - 0.15, -H + 0.9))):
    shape(pcbnew.SHAPE_T_SEGMENT, 'F.SilkS', a_, c_, 0.12)                                          # pin-1 corner
f.SetAttributes(pcbnew.FP_SMD)
b.Add(f)
f.SetPosition(pcbnew.VECTOR2I(MM(X), MM(Y))); f.Flip(f.GetPosition(), False); f.SetOrientationDegrees(ROT)
f.SetReference('U15'); f.SetValue('RAK3172-SIP-9-SM-NI'); f.Reference().SetVisible(False); f.Value().SetVisible(False)
u15 = f
f.SetFPID(pcbnew.LIB_ID('SLIM4', 'FP_U15'))
f.SetDescription('RAK3172-SIP-9-SM-NI | JLC global sourcing (RAKwireless SKU 306039) | R28: LoRa/FSK radio SiP '
                 '(STM32WLE5), 902-928 MHz, LGA-73 12 x 12 x 1.22 mm, land pattern from the RAKwireless RAK3172-SiP '
                 'layout recommendation; MSL 3: bake 125 C 12 h before reflow (RAKwireless)')
f.SetKeywords('SLIM4 R28 U RAK3172-SiP STM32WL radio')
for p in f.Pads():
    nn = PINS.get(p.GetNumber())
    if nn: p.SetNet(net(nn))
for num, nn in U1PAD.items():
    q = pad('U1', num); assert q.GetNetname() == '', (num, q.GetNetname()); q.SetNet(net(nn))
P = {p.GetNumber(): (round(mm(p.GetPosition().x), 3), round(mm(p.GetPosition().y), 3)) for p in f.Pads()}
assert P['30'][0] > X and P['37'][1] > Y and P['3'][1] < Y and P['55'][0] < X, P    # UART east, RF south, supply N/W

f.BuildCourtyardCaches(); mine = f.GetCourtyard(pcbnew.B_CrtYd)
for o in b.GetFootprints():
    if o.GetReference() == 'U15' or not o.IsFlipped() or _dead(o): continue
    o.BuildCourtyardCaches(); oc = o.GetCourtyard(pcbnew.B_CrtYd)
    if oc.OutlineCount() == 0: continue
    x_ = mine.CloneDropTriangulation(); x_.BooleanIntersection(oc, pcbnew.SHAPE_POLY_SET.PM_FAST)
    assert x_.Area() == 0, 'U15 courtyard overlaps ' + o.GetReference()
CY = (X - H - 0.485, Y - H - 0.485, X + H + 0.485, Y + H + 0.485)
REGION = (-33.6, 71.6, -17.6, 95.4)   # the radio's area (the In3 pour fills round R27's In3 tracks there)
for t in _copper_items():
    if t.GetLayer() in (L['B.Cu'], L['In3.Cu']) or t.Type() == pcbnew.PCB_VIA_T:
        assert not track_in_box(t, CY), 'copper under U15: ' + t.GetNetname()

def outward(num, d):
    """A point d mm beyond the outer end of SiP pad num (away from the body centre)."""
    x, y = P[num]
    if abs(x - X) > abs(y - Y): return (round(x + math.copysign(0.585 + d, x - X), 3), y)
    return (x, round(y + math.copysign(0.585 + d, y - Y), 3))

copper = _copper_items()
def refresh(): copper[:] = _copper_items()
def stub(num, pts, w=0.2):
    """A track from SiP pad num's outer end through pts (net of the pad)."""
    nn = PINS[num]; path = [outward(num, -0.3)] + list(pts)
    for a, c in zip(path, path[1:]):
        assert seg_free('B.Cu', a, c, w, net(nn).GetNetCode(), 0.12, copper), (num, a, c)
    add('B.Cu', path, net(nn), w); refresh(); return path[-1]
def via_at(x, y, nn):
    assert via_free(x, y, nn, 0.12, copper), (nn, x, y)
    add_via(x, y, net(nn)); NEW_VIAS.append(pcbnew.VECTOR2I(MM(x), MM(y))); refresh(); return (x, y)

# ---- ground: B.Cu zone over the SiP, a via in each centre pad (via-in-pad, filled and capped: JLCPCB 6-layer default)
zone('B.Cu', rect(*CY), 'GND', prio=6, conn='solid', name='U15 radio ground')
for k in range(65, 74): add_via(*P[str(k)], G); NEW_VIAS.append(pcbnew.VECTOR2I(MM(P[str(k)][0]), MM(P[str(k)][1])))
refresh()

# ---- RADIO_3V3 pour on In3 over the radio's area -----------------------------------------------------------------
in3_crossing = sorted({t.GetNetname() for t in _copper_items() if t.GetLayer() == L['In3.Cu'] and track_in_box(t, REGION)})
zone('In3.Cu', rect(*REGION), 'RADIO_3V3', prio=5, clearance=0.2, conn='solid', name='RADIO_3V3 pour (radio supply)')
def in_region(x, y, m=0.6): return REGION[0] + m <= x <= REGION[2] - m and REGION[1] + m <= y <= REGION[3] - m

# ---- general two-pad placement ---------------------------------------------------------------------------------
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
FILL = pcbnew.SHAPE_POLY_SET()
for z in b.Zones():
    if z.GetNetname() == '3V3_SYS' and z.IsOnLayer(L['In2.Cu']):
        FILL.BooleanAdd(z.GetFilledPolysList(L['In2.Cu']), pcbnew.SHAPE_POLY_SET.PM_FAST)
def in_3v3_plane(x, y):
    pts = [(x, y)] + [(x + 0.45*math.cos(a*math.pi/4), y + 0.45*math.sin(a*math.pi/4)) for a in range(8)]
    return all(FILL.Contains(pcbnew.VECTOR2I(MM(px), MM(py)), -1, 0) for px, py in pts)
PLANE = {'RADIO_3V3': lambda x, y: in_region(x, y), '3V3_SYS': in_3v3_plane, 'GND': lambda x, y: True}
placed = []
def two_pad(ref, lib, fpname, value, lcsc, note, near, rmax, joins, dnp=False, rots=(0, 90, 180, 270), w=0.25):
    """Place a two-pad part on the back as close to `near` as it fits (0.1 mm steps): courtyard clear of every back
    part, pads 0.12 mm from other nets. joins: [(net, kind, arg)] for its two pads, matched to pads in either order:
    ('pt', (points, reach)) a straight B.Cu track to the nearest free point; ('via', None) a new via of the net
    beside the pad (RADIO_3V3 only inside the In3 pour, 3V3_SYS only in the In2 3V3_SYS plane)."""
    g = place(lib, fpname, ref, value, lcsc, note, near[0], near[1], 0)
    g.SetDescription(f'{value} | JLC {lcsc} | {note}' if not dnp else f'DNP | {note}')
    if dnp:
        g.SetAttributes(g.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    back = [o for o in b.GetFootprints() if o.IsFlipped() and not _dead(o) and o.GetReference() != ref]
    silk = [d.GetBoundingBox() for d in b.GetDrawings() if d.GetLayer() == b.GetLayerID('B.SilkS')]   # board text: keep clear by 0.15
    for d_ in silk: d_.Inflate(MM(0.15))
    for o in back: o.BuildCourtyardCaches()
    pads = list(g.Pads())
    n = int(round(rmax / 0.1))
    cands = sorted((math.hypot(i*0.1, j*0.1), round(near[0] + i*0.1, 3), round(near[1] + j*0.1, 3))
                   for i in range(-n, n + 1) for j in range(-n, n + 1) if math.hypot(i*0.1, j*0.1) <= rmax)
    for d, x, y in cands:
        for rot in rots:
            g.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); g.SetOrientationDegrees(rot); g.BuildCourtyardCaches()
            cy = g.GetCourtyard(pcbnew.B_CrtYd); ok = not any(d_.Intersects(cy.BBox()) for d_ in silk)
            for o in back:
                if abs(mm(o.GetPosition().x) - x) > 12 or abs(mm(o.GetPosition().y) - y) > 12: continue
                oc = o.GetCourtyard(pcbnew.B_CrtYd)
                if oc.OutlineCount() == 0: continue
                x_ = cy.CloneDropTriangulation(); x_.BooleanIntersection(oc, pcbnew.SHAPE_POLY_SET.PM_FAST)
                if x_.Area() > 0: ok = False; break
            if not ok: continue
            for order in ((0, 1), (1, 0)):
                for pi_, (nn, _k, _a) in zip(order, joins): pads[pi_].SetNet(net(nn))   # this order's nets on both pads first
                plan = []
                for pi_, (nn, kind, arg) in zip(order, joins):
                    pd = pads[pi_]; pd.SetNet(net(nn)); sh = pd.GetEffectiveShape(); nc = net(nn).GetNetCode()
                    if any(t.GetNetCode() != nc and (t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() == L['B.Cu'])
                           and t.GetEffectiveShape().Collide(sh, MM(0.12)) for t in copper): plan = None; break
                    if any(q.GetNetCode() != nc and q.IsOnLayer(L['B.Cu']) and q.GetEffectiveShape().Collide(sh, MM(0.12))
                           for o in b.GetFootprints() if o.GetReference() != ref and not _dead(o)
                           and abs(mm(o.GetPosition().x) - x) < 10 and abs(mm(o.GetPosition().y) - y) < 10 for q in o.Pads()):
                        plan = None; break
                    pxy = (round(mm(pd.GetPosition().x), 3), round(mm(pd.GetPosition().y), 3))
                    if kind == 'pt':
                        best = None
                        for dd, tp in sorted((math.hypot(tp[0] - pxy[0], tp[1] - pxy[1]), tp) for tp in arg[0]):
                            if dd > arg[1]: break
                            if dd < 0.05 or seg_free('B.Cu', pxy, tp, w, nc, 0.12, copper): best = tp; break
                        if best is None: plan = None; break
                        plan.append((nn, pxy, best, None))
                    else:
                        v = None
                        for k in range(2, 10):
                            for ang in range(0, 360, 30):
                                vx = round(pxy[0] + 0.3*k*math.cos(math.radians(ang)), 2); vy = round(pxy[1] + 0.3*k*math.sin(math.radians(ang)), 2)
                                if PLANE[nn](vx, vy) and via_free(vx, vy, nn, 0.12, copper) and seg_free('B.Cu', pxy, (vx, vy), w, nc, 0.12, copper):
                                    v = (vx, vy); break
                            if v: break
                        if v is None: plan = None; break
                        plan.append((nn, pxy, None, v))
                if plan and len(plan) == 2:                       # the two joins against each other (different nets)
                    def geo(j_):
                        nn_, a_, tp_, v_ = j_; e_ = tp_ if tp_ is not None else v_
                        return pcbnew.SEG(pcbnew.VECTOR2I(MM(a_[0]), MM(a_[1])), pcbnew.VECTOR2I(MM(e_[0]), MM(e_[1]))), v_
                    (s0, v0), (s1, v1) = geo(plan[0]), geo(plan[1])
                    if s0.Distance(s1) < MM(w + 0.12) or (v0 and s1.Distance(pcbnew.VECTOR2I(MM(v0[0]), MM(v0[1]))) < MM(0.225 + w/2 + 0.12)) \
                       or (v1 and s0.Distance(pcbnew.VECTOR2I(MM(v1[0]), MM(v1[1]))) < MM(0.225 + w/2 + 0.12)):
                        plan = None
                if plan:
                    txt = []
                    for nn, pxy, tp, v in plan:
                        if tp is not None:
                            if math.hypot(tp[0] - pxy[0], tp[1] - pxy[1]) >= 0.05: add('B.Cu', [pxy, tp], net(nn), w)
                            txt.append(f'{nn} to ({tp[0]:.2f}, {tp[1]:.2f})')
                        else:
                            add_via(*v, net(nn)); NEW_VIAS.append(pcbnew.VECTOR2I(MM(v[0]), MM(v[1]))); add('B.Cu', [pxy, v], net(nn), w)
                            txt.append(f'{nn} via ({v[0]:.2f}, {v[1]:.2f})')
                    refresh()
                    pp = {pads[i_].GetNetname(): (round(mm(pads[i_].GetPosition().x), 3), round(mm(pads[i_].GetPosition().y), 3)) for i_ in (0, 1)}
                    placed.append(f'{ref} ({x:.2f}, {y:.2f}) r{rot}: ' + ', '.join(txt))
                    return pp
    if os.environ.get('R28_DEBUG'):
        print('NO PLACE for', ref); KILL.append(g); return {}
    raise AssertionError('no place for ' + ref)

def line_pts(a, c, step=0.1):
    n_ = max(1, int(math.hypot(c[0] - a[0], c[1] - a[1]) / step))
    return [(round(a[0] + (c[0] - a[0])*i/n_, 3), round(a[1] + (c[1] - a[1])*i/n_, 3)) for i in range(n_ + 1)]
C0402, C0603, R0402 = ('Capacitor_SMD', 'C_0402_1005Metric'), ('Capacitor_SMD', 'C_0603_1608Metric'), ('Resistor_SMD', 'R_0402_1005Metric')
FB = ('Inductor_SMD', 'L_0402_1005Metric')
N100, N1U, N470, U47, U10 = ('CL05B104KO5NNNC', 'C1525'), ('CL05A105KA5NQNC', 'C52923'), ('CL05A474KA5NNNC', 'C92361'), \
                            ('CL10A475KO8NNNC', 'C19666'), ('CL05A106MQ5NUNC', 'C15525')
BEAD = ('BLM15AG121SN1D', 'C85812')
GV = ('GND', 'via', None)

# ---- DC-DC: L701 15 uH between VLXSMPS (13) and VFBSMPS (10), over pins 10-13; VDDSMPS (11) up between its pads --
lx = round((P['10'][0] + P['13'][0]) / 2, 3); ly = round(P['10'][1] - 0.585 - 0.25 - 1.75 - 0.01, 3)
l701 = place('Inductor_SMD', 'L_Sunlord_SWPA3012S', 'L701', 'SWPA3012S150MT', 'C83417',
             'R28: radio DC-DC inductor, 15 uH (RAK3272-SiP reference)', lx, ly, 0)
l701.SetDescription('SWPA3012S150MT | JLC C83417 | R28: radio DC-DC inductor, 15 uH 450 mA (RAK3272-SiP reference L1)')
lp = sorted(l701.Pads(), key=lambda p: p.GetPosition().x)
lp[0].SetNet(net('RADIO_VFB')); lp[1].SetNet(net('RADIO_VLX'))
LPX = [(round(mm(p.GetPosition().x), 3), round(mm(p.GetPosition().y), 3)) for p in lp]
assert abs(LPX[0][0] - P['10'][0]) < 0.4 and abs(LPX[1][0] - P['13'][0]) < 0.4, (LPX, P['10'], P['13'])
stub('10', [(P['10'][0], LPX[0][1] + 0.6)], 0.3)
stub('13', [(P['13'][0], LPX[1][1] + 0.6)], 0.3)
top_l = round(ly - 1.75, 3)
vdds = stub('11', [(P['11'][0], round(top_l - 0.9, 3))], 0.2)
# ---- supply pins 3, 4, 6, 7 (RADIO_3V3) on the north side: stubs to a bus, decoupling on the bus ----------------
bus_y = round(P['3'][1] - 0.585 - 0.7, 3)
for k in ('3', '4', '6', '7'): stub(k, [(P[k][0], bus_y)], 0.2)
XC = [round(P['3'][0] + 0.94*k, 3) for k in range(4)]           # C711-C714 upright side by side, 3V3 pad on the bus
bus = [(round(P['3'][0] - 0.6, 3), bus_y), (XC[3], bus_y)]
add('B.Cu', bus, net('RADIO_3V3'), 0.3); refresh()
bv = via_at(round(bus[0][0] - 0.1, 3), round(bus_y - 0.75, 3), 'RADIO_3V3'); add('B.Cu', [bus[0], bv], net('RADIO_3V3'), 0.3); refresh()
BUS = line_pts(*bus, step=0.05)
for ref, val, note, x_ in (('C711', N100, 'R28: radio VDD (SiP pin 3) decoupling', XC[0]), ('C712', N1U, 'R28: radio VBAT (pin 4) decoupling', XC[1]),
                           ('C713', N100, 'R28: radio VREF+ (pin 6) decoupling', XC[2]), ('C714', N100, 'R28: radio VDDA (pin 7) decoupling', XC[3])):
    two_pad(ref, *C0402, *val, note, (x_, round(bus_y - 0.48, 3)), 0.0, [('RADIO_3V3', 'pt', (BUS, 0.05)), GV], rots=(90, 270))
for o in b.GetFootprints():                                     # 0.94 mm apart: their silk outlines would touch, so none
    if o.GetReference() in ('C711', 'C712', 'C713', 'C714'):
        for g_ in list(o.GraphicalItems()):
            if g_.GetLayer() == b.GetLayerID('B.SilkS'): o.Remove(g_)

VFB = line_pts((LPX[0][0], LPX[0][1] - 1.2), (LPX[0][0], LPX[0][1] + 1.2))
two_pad('C718', *C0402, *N470, 'R28: radio VFBSMPS 470 nF', (LPX[0][0] - 0.6, top_l - 0.9), 2.5, [('RADIO_VFB', 'pt', (VFB, 2.2)), GV])
two_pad('C719', *C0402, *N100, 'R28: radio VFBSMPS 100 nF', (LPX[0][0] - 1.6, top_l - 0.9), 5.0,
        [('RADIO_VFB', 'pt', (VFB + copper_points('RADIO_VFB'), 4.0)), GV])
VDDS = line_pts((P['11'][0], top_l + 1.0), vdds)
two_pad('E701', *FB, *BEAD, 'R28: radio VDDSMPS bead 120 ohm (RAK3272-SiP E3)', (vdds[0], vdds[1] - 1.0), 3.0,
        [('RADIO_VDDSMPS', 'pt', (VDDS, 1.6)), ('RADIO_3V3', 'via', None)])
two_pad('C720', *C0402, *N100, 'R28: radio VDDSMPS 100 nF', (vdds[0] + 1.0, vdds[1]), 3.0, [('RADIO_VDDSMPS', 'pt', (VDDS, 1.6)), GV])
# bulk decoupling of the RADIO_3V3 pins last: they can sit anywhere near, the VFB / VDDSMPS parts cannot
two_pad('C715', *C0402, *N1U, 'R28: radio VDDA (pin 7) 1 uF', (P['7'][0], bus_y - 2.2), 3.0, [('RADIO_3V3', 'pt', (BUS, 2.0)), GV])
two_pad('C716', *C0603, *U47, 'R28: radio VDD 4.7 uF', (P['3'][0] - 1.5, bus_y - 1.6), 4.0, [('RADIO_3V3', 'via', None), GV])
two_pad('C717', *C0603, *U47, 'R28: radio VREF+ 4.7 uF', (P['6'][0], bus_y - 3.0), 4.0, [('RADIO_3V3', 'via', None), GV])

# ---- west side: VDD (55), VDDRF (54) and VDDPA (53) ------------------------------------------------------------------
e55 = stub('55', [outward('55', 0.25)], 0.2)
e54 = stub('54', [outward('54', 0.25)], 0.2)
e53 = stub('53', [outward('53', 0.25)], 0.2)
two_pad('C721', *C0402, *N100, 'R28: radio VDD (SiP pin 55) decoupling', (e55[0] - 1.0, e55[1] - 0.9), 3.0, [('RADIO_3V3', 'pt', ([e55], 2.0)), GV])
two_pad('C722', *C0402, *N1U, 'R28: radio VDDRF 1 uF', (e54[0] - 1.6, e54[1]), 3.0, [('RADIO_VDDRF', 'pt', ([e54], 2.4)), GV])
two_pad('C723', *C0402, *N1U, 'R28: radio VDDPA 1 uF', (e53[0] - 1.0, e53[1] + 1.0), 3.0, [('RADIO_VDDPA', 'pt', ([e53], 2.0)), GV])
pv = None                                                       # pin 55 to the pour
for dx, dy in ((-0.9, -0.6), (-0.9, 0.0), (-1.2, -1.2), (-0.6, -1.0), (-1.5, -0.3)):
    cx, cy_ = round(e55[0] + dx, 2), round(e55[1] + dy, 2)
    if via_free(cx, cy_, 'RADIO_3V3', 0.12, copper) and seg_free('B.Cu', e55, (cx, cy_), 0.25, net('RADIO_3V3').GetNetCode(), 0.12, copper):
        pv = via_at(cx, cy_, 'RADIO_3V3'); add('B.Cu', [e55, pv], net('RADIO_3V3'), 0.25); refresh(); break
assert pv, 'no RADIO_3V3 via for pin 55'
VRF = line_pts(e54, (e54[0] - 0.6, e54[1])); add('B.Cu', [e54, VRF[-1]], net('RADIO_VDDRF'), 0.2)   # drawn: joins land on copper
VPA = line_pts(e53, (e53[0] - 0.6, e53[1])); add('B.Cu', [e53, VPA[-1]], net('RADIO_VDDPA'), 0.2); refresh()
two_pad('E702', *FB, *BEAD, 'R28: radio VDDRF bead 120 ohm (RAK3272-SiP E1)', (e54[0] - 3.0, e54[1]), 4.0,
        [('RADIO_VDDRF', 'pt', (copper_points('RADIO_VDDRF') + VRF, 2.4)), ('RADIO_3V3', 'via', None)])
two_pad('E703', *FB, *BEAD, 'R28: radio VDDPA bead 120 ohm (RAK3272-SiP E2)', (e53[0] - 2.4, e53[1] + 1.6), 4.0,
        [('RADIO_VDDPA', 'pt', (copper_points('RADIO_VDDPA') + VPA, 2.4)), ('RADIO_3V3', 'via', None)])

# ---- south side: RF_OUT (37) through the pi network to the U.FL socket; NRST (44); BOOT0 (43) -------------------
rf0 = outward('37', -0.3)
r704 = place('Resistor_SMD', 'R_0402_1005Metric', 'R704', '0402WGF0000TCE', 'C17168', 'R28: radio RF series link (pi network)',
             round(P['37'][0] + 0.51, 3), round(rf0[1] + 0.3 + 0.75, 3), 0)
r704.SetDescription('0402WGF0000TCE | JLC C17168 | R28: radio RF_OUT series 0 ohm of the pi network (RAK3272-SiP R4)')
rp = sorted(r704.Pads(), key=lambda p: p.GetPosition().x)
rp[0].SetNet(net('RADIO_RF')); rp[1].SetNet(net('RADIO_ANT'))
RA = (round(mm(rp[0].GetPosition().x), 3), round(mm(rp[0].GetPosition().y), 3)); RB = (round(mm(rp[1].GetPosition().x), 3), round(mm(rp[1].GetPosition().y), 3))
assert abs(RA[0] - rf0[0]) < 0.02, (RA, rf0)                  # RF_OUT drops straight onto R704's west pad
add('B.Cu', [rf0, RA], net('RADIO_RF'), RF_W); refresh()
c725 = place(*C0402, 'C725', 'DNP', '', 'R28: radio antenna shunt, not fitted (pi network, RAK3272-SiP C14)',
             round(RB[0] + 0.9, 3), round(RB[1] + 0.48, 3), 90)        # in the gap right after R704, top pad on the RF line
c725.SetDescription('DNP | R28: radio antenna shunt, not fitted (pi network, RAK3272-SiP C14)')
c725.SetAttributes(c725.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
cp_ = sorted(c725.Pads(), key=lambda p: p.GetPosition().y); cp_[0].SetNet(net('RADIO_ANT')); cp_[1].SetNet(G)
CT = (round(mm(cp_[0].GetPosition().x), 3), round(mm(cp_[0].GetPosition().y), 3)); CG = (round(mm(cp_[1].GetPosition().x), 3), round(mm(cp_[1].GetPosition().y), 3))
assert abs(CT[1] - RB[1]) < 0.01, (CT, RB)
gv725 = via_at(CG[0], round(CG[1] + 0.75, 3), 'GND'); add('B.Cu', [CG, gv725], G, 0.3)
c725.BuildCourtyardCaches(); c_right = mm(c725.GetCourtyard(pcbnew.B_CrtYd).BBox().GetRight())
j701 = place('Connector_Coaxial', 'U.FL_Hirose_U.FL-R-SMT-1_Vertical', 'J701', 'U.FL-R-SMT-1(10)', 'C88373',
             'R28: radio antenna socket', RB[0] + 4.0, RB[1] + 2.0, 0)
j701.SetDescription('U.FL-R-SMT-1(10) | JLC C88373 | R28: radio antenna socket (U.FL / IPEX MHF1), 50 ohm; KiCad 7 library '
                    'Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical')
sig = [p for p in j701.Pads() if p.GetNumber() == '1'][0]; sig.SetNet(net('RADIO_ANT'))
for p in j701.Pads():
    if p.GetNumber() != '1': p.SetNet(G)
for rot in (0, 90, 180, 270):                                   # signal pad up, towards the U15 corner
    j701.SetOrientationDegrees(rot)
    sx, sy = mm(sig.GetPosition().x) - mm(j701.GetPosition().x), mm(sig.GetPosition().y) - mm(j701.GetPosition().y)
    if sy < -0.9 and abs(sx) < 0.05: break
j701.BuildCourtyardCaches(); jb = j701.GetCourtyard(pcbnew.B_CrtYd).BBox()
jl, jt = mm(jb.GetX()) - mm(j701.GetPosition().x), mm(jb.GetY()) - mm(j701.GetPosition().y)
u15.BuildCourtyardCaches(); u_bot = mm(u15.GetCourtyard(pcbnew.B_CrtYd).BBox().GetBottom())
j701.SetPosition(pcbnew.VECTOR2I(MM(round(c_right + 0.02 - jl, 3)), MM(round(u_bot + 0.02 - jt, 3))))  # courtyard on C725 and U15
S1 = (round(mm(sig.GetPosition().x), 3), round(mm(sig.GetPosition().y), 3))
dy_ = round(S1[1] - RB[1], 3); assert 0 <= dy_ < 1.0 and S1[0] - dy_ > CT[0] + 0.3, (S1, RB, CT)
add('B.Cu', [RB, (round(S1[0] - dy_, 3), RB[1]), S1], net('RADIO_ANT'), RF_W); refresh()   # straight east over C725, 45 deg in
two_pad('C724', *C0402, 'DNP', '', 'R28: radio RF_OUT shunt, not fitted (pi network, RAK3272-SiP C13)', (RA[0] - 1.0, RA[1]), 1.5,
        [('RADIO_RF', 'pt', ([RA], 1.2)), GV], dnp=True, rots=(0, 180), w=RF_W)
for o in b.GetFootprints():                                     # J701 and R704: courtyards clear
    if not o.IsFlipped() or _dead(o): continue
    o.BuildCourtyardCaches(); oc = o.GetCourtyard(pcbnew.B_CrtYd)
    for g_ in (j701, r704, c725):
        if g_.GetReference() == o.GetReference(): continue
        g_.BuildCourtyardCaches(); x_ = g_.GetCourtyard(pcbnew.B_CrtYd).CloneDropTriangulation()
        x_.BooleanIntersection(oc, pcbnew.SHAPE_POLY_SET.PM_FAST)
        if x_.Area() > 0 and os.environ.get('R28_DEBUG'): print('OVERLAP', g_.GetReference(), o.GetReference()); continue
        assert x_.Area() == 0, g_.GetReference() + ' courtyard overlaps ' + o.GetReference()
for p in j701.Pads():                                           # its ground pads to the planes
    if p.GetNumber() == '1': continue
    px, py = round(mm(p.GetPosition().x), 3), round(mm(p.GetPosition().y), 3)
    for dx, dy in ((0, 0.9), (0, -0.9), (0.9, 0), (-0.9, 0), (0.7, 0.7), (-0.7, 0.7)):
        if via_free(px + dx, py + dy, 'GND', 0.12, copper) and seg_free('B.Cu', (px, py), (px + dx, py + dy), 0.3, G.GetNetCode(), 0.12, copper):
            via_at(round(px + dx, 3), round(py + dy, 3), 'GND'); add('B.Cu', [(px, py), (round(px + dx, 3), round(py + dy, 3))], G, 0.3); refresh(); break
e44 = stub('44', [outward('44', 0.35)], 0.2)
e43 = stub('43', [outward('43', 0.35)], 0.2)
two_pad('R703', *R0402, '0402WGF1002TCE', 'C25744', 'R28: radio NRST pull-up 10 k (RAK3272-SiP R1)', (e44[0] - 0.6, e44[1] + 1.1), 3.0,
        [('RADIO_NRST', 'pt', ([e44], 1.6)), ('RADIO_3V3', 'via', None)])
two_pad('C726', *C0402, *N100, 'R28: radio NRST 100 nF (RAK3272-SiP C11)', (e44[0] - 1.6, e44[1] + 1.1), 3.0,
        [('RADIO_NRST', 'pt', ([e44] + copper_points('RADIO_NRST'), 2.2)), GV])
two_pad('R702', *R0402, '0402WGF1002TCE', 'C25744', 'R28: radio BOOT0 pull-down 10 k (RAK3272-SiP R2)', (e43[0] + 0.6, e43[1] + 1.1), 3.0,
        [('RADIO_BOOT0', 'pt', ([e43], 1.6)), GV])

# ---- supply link from 3V3_SYS and bulk ----------------------------------------------------------------------------
two_pad('R701', *R0402, '0402WGF0000TCE', 'C17168', 'R28: radio supply link from 3V3_SYS (remove it and the radio is unpowered)',
        (-18.9, 76.5), 4.0, [('3V3_SYS', 'via', None), ('RADIO_3V3', 'via', None)])
two_pad('C701', *C0402, *U10, 'R28: radio supply bulk 10 uF', (-19.6, 78.2), 4.0, [('RADIO_3V3', 'via', None), GV])

print('radio: U15 RAK3172-SiP at (%.2f, %.2f) rot %d, back; U1 pads %s; In3 pour fills round %s; parts: %s'
      % (X, Y, ROT, U1PAD, ', '.join(in3_crossing) or 'nothing', '; '.join(placed)))
