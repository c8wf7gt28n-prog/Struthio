#!/usr/bin/env python3
"""STRUTHIO ONE SLIM · the ONE board, 0.8 mm thick, lying on the Waveshare's J8 socket.

    /usr/bin/python3 make_slim_pcb.py         (KiCad 7 pcbnew, tracks planned by hand below)

The circuit, parts and tracks are the ONE's (pcb/one/make_one_pcb.py, rev C); what changes:
  - 0.8 mm board, outline from cad/slim/slim_cad.py (0.3 mm further in than the ONE's)
  - J1 is NOT assembled: the builder fits 8 bare header pins (pins 1, 3, 4, 5, 7, 16, 18, 24) with the
    printed pin jig, so the board can lie on the socket (docs/STRUTHIO_ONE_SLIM.md)
  - through-hole leads (SW5, J2) are trimmed flush by the builder; the back shell has 0.5 mm reliefs over them

Every position comes from cad/one/one_cad.py (as set up by slim_cad.py), so the board, the case and the fit
checks share one set of numbers. The design frame there is the view from the
front; KiCad's top view of this board is the same view (the top side faces the
front of the handheld), so KiCad x = design x and KiCad y = -design y (+ origin).

Parts (all on the top side, all assembled by JLCPCB):
  J1   2 x 16 male header, 2.54 mm, HCTL PZ254-2-16-Z-8.5 (C2894977), mounted the standard
       way (plastic on the top side). The case sets how far its 6 mm pins go into the
       Waveshare's ~4 mm socket (3.3 mm). Pad numbers = Waveshare's header numbers (pin 1 = BAT).
  SW1-4  XKB TS-1187A-B-A-B tact switches (C318884, JLC basic): LEFT, RIGHT, DART L, DART R
  SW5  G-Switch SS-12D06-G030 right-angle slide switch, 3 A (C17179519): battery hard cut
  J2   JST S2B-PH-K-S side-entry PH 2.0 socket (C173752): the battery plugs in here
  Q1   AO3401A P-FET (C15127): reverse-battery protection (a reversed battery lead switches it off)
  Q2, C1, R1, D1   AO3400A (C20917), 10 uF (C15850), 470 k (C25790), 1N4148WS (C2128): power-on pulse.
       On battery alone the Waveshare's AXP2101 keeps its battery switch off until the PWR key is held
       (AXP2101 datasheet 6.5.2). When the slide switch turns on, C1 lifts Q2's gate and Q2 holds PWR
       (header pin 24) low for ~3-8 s as C1 charges through R1; D1 empties C1 when the switch turns off.
       The firmware turns off "long press = power off" at boot, so the long press is harmless.
  All parts are JLC basic parts except J1, J2 and SW5.
"""
import csv, os, subprocess, sys, shutil
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'cad', 'one'))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'cad', 'slim'))
import slim_cad as S
G = S.o

OUT = os.path.join(HERE, 'out')
OX, OY = 100.0, 100.0                       # design (0, 0) sits here in KiCad
def P(x, y): return pcbnew.VECTOR2I(pcbnew.FromMM(float(OX + x)), pcbnew.FromMM(float(OY - y)))
def MM(v): return pcbnew.FromMM(float(v))

board = pcbnew.BOARD()
board.SetCopperLayerCount(2)
ds = board.GetDesignSettings()
ds.SetBoardThickness(MM(0.8))
ds.m_TrackMinWidth = MM(0.2); ds.m_MinClearance = MM(0.2); ds.m_CopperEdgeClearance = MM(0.3); ds.m_ViasMinSize = MM(0.6); ds.m_MinThroughDrill = MM(0.3)
nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetTrackWidth(MM(0.4)); nc.SetClearance(MM(0.25)); nc.SetViaDiameter(MM(0.7)); nc.SetViaDrill(MM(0.35))

NETS = {}
def net(name):
    if name not in NETS:
        n = pcbnew.NETINFO_ITEM(board, name); board.Add(n); NETS[name] = n
    return NETS[name]

# ---- outline -----------------------------------------------------------------------------------------
def add_poly_edges(pts, layer=pcbnew.Edge_Cuts, width=0.1):
    for i in range(len(pts)):
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*pts[i])); s.SetEnd(P(*pts[(i + 1) % len(pts)]))
        s.SetLayer(layer); s.SetWidth(MM(width)); board.Add(s)
outline = S.one2d()
polys = outline.to_polygons()
for poly in polys: add_poly_edges([tuple(p) for p in poly])   # outer ring and the holes (post clearance, screws)

# ---- footprints --------------------------------------------------------------------------------------
def new_fp(ref, value, x, y, rot=0.0, fpname=None):
    fp = pcbnew.FOOTPRINT(board); fp.SetReference(ref); fp.SetValue(value)
    fp.SetFPID(pcbnew.LIB_ID('STRUTHIO', fpname or value.split()[0]))
    fp.SetPosition(P(x, y)); board.Add(fp)
    fp.Reference().SetVisible(True); fp.Value().SetVisible(False)
    fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.9), MM(0.9)))
    return fp

def add_pad(fp, num, dx, dy, shape, size, drill=None, layers='th', netname=None, rect_first=False):
    pad = pcbnew.PAD(fp)
    pad.SetNumber(str(num))
    if drill:
        pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH); pad.SetLayerSet(pad.PTHMask())
        pad.SetDrillSize(pcbnew.VECTOR2I(MM(drill), MM(drill)))
    else:
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD); pad.SetLayerSet(pad.SMDMask())
    pad.SetShape(shape)
    pad.SetSize(pcbnew.VECTOR2I(MM(size[0]), MM(size[1])))
    fp.Add(pad)
    pad.SetPos0(pcbnew.VECTOR2I(MM(dx), MM(-dy)))          # footprint-relative (what the file stores)
    pad.SetPosition(pcbnew.VECTOR2I(fp.GetPosition().x + MM(dx), fp.GetPosition().y - MM(dy)))
    if netname: pad.SetNet(net(netname))
    return pad

def silk_text(text, x, y, size=1.0, layer=pcbnew.F_SilkS):
    t = pcbnew.PCB_TEXT(board); t.SetText(text); t.SetPosition(P(x, y)); t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); t.SetTextThickness(MM(size * 0.15))
    if layer == pcbnew.B_SilkS: t.SetMirrored(True)
    board.Add(t)

def silk_rect(x0, y0, x1, y1, layer=pcbnew.F_SilkS):
    add_poly_edges([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, 0.15)

# J1: Waveshare header numbering, odd pins on the edge row (x 24.47), pin 1 at the top
HDR_NETS = {1: 'BAT', 3: 'GND', 4: 'GND', 5: 'GPIO21', 7: 'GPIO38', 16: 'GPIO17', 18: 'GPIO18', 24: 'PWRON', 29: 'GND', 30: 'GND'}
xe, xc = G.HDR_ROW_X[1], G.HDR_ROW_X[0]
j1 = new_fp('J1', 'Header_2x16_Waveshare',  (xe + xc) / 2, G.HDR_PIN1_Y - 7.5 * 2.54)
for n in range(1, 33):
    k = (n - 1) // 2
    x = (xe if n % 2 else xc) - (xe + xc) / 2
    y = G.HDR_PIN1_Y - k * 2.54 - (G.HDR_PIN1_Y - 7.5 * 2.54)
    add_pad(j1, n, x, y, pcbnew.PAD_SHAPE_RECT if n == 1 else pcbnew.PAD_SHAPE_CIRCLE, (1.7, 1.7), drill=1.02, netname=HDR_NETS.get(n))
silk_rect(xc - 1.4 - 0.1, G.HDR_PIN1_Y + 1.4, xe + 1.4, G.HDR_PIN1_Y - 15 * 2.54 - 1.4)
silk_text('1', xe + 2.4, G.HDR_PIN1_Y, 1.0)

# SW1-4: TS-1187A. Only the diagonal pads carry nets: A to the GPIO, D to GND. A diagonal pair is never
# joined inside the switch, so the key works whichever way the assembler turns the part.
SW = {'SW1': ('LEFT', 'GPIO17'), 'SW2': ('RIGHT', 'GPIO18'), 'SW3': ('DART_L', 'GPIO21'), 'SW4': ('DART_R', 'GPIO38')}
for ref, (key, sig) in SW.items():
    x, y = G.switch_xy()[key]
    fp = new_fp(ref, 'TS-1187A-B-A-B', x, y)
    for i, (dx, dy) in enumerate(((-3.0, 1.875), (3.0, 1.875), (-3.0, -1.875), (3.0, -1.875))):
        add_pad(fp, 'ABCD'[i], dx, dy, pcbnew.PAD_SHAPE_RECT, (1.0, 0.75), netname={0: sig, 3: 'GND'}.get(i))
    silk_rect(x - 2.0, y - 2.6, x + 2.0, y + 2.6)            # between the pads

# SW5: SS-12D06-G030 (G-Switch drawing SK-12D06-G030 rev A0): three 0.7 x 1.3 mm pins at 4.7 mm pitch, bent down
# 4.1 mm behind the body to their outside face, so the pin centre is 3.75 mm behind it. Pin 2 is the common;
# the slider's contact moves with the knob, so knob toward pin 1 (toward the screen) joins 2-1: ON.
body, knob, x_front = G.psw_box()
xp = x_front + G.PSW_DEPTH + 3.75
sw5 = new_fp('SW5', 'SS-12D06-G030', xp, G.PSW_Y)
for i, dy in enumerate((4.7, 0.0, -4.7)):
    add_pad(sw5, i + 1, 0, dy, pcbnew.PAD_SHAPE_CIRCLE, (2.4, 2.4), drill=1.6, netname=('BAT', 'BAT_RAW', None)[i])
silk_rect(x_front + 1.8, G.PSW_Y - G.PSW_LEN / 2, x_front + G.PSW_DEPTH, G.PSW_Y + G.PSW_LEN / 2)   # (the body overhangs the edge)
silk_text('ON', x_front + 4.0, G.PSW_Y + 4.0, 1.2)
sw5.Reference().SetPosition(P(xp - 1.0, G.PSW_Y - 8.4))
j1.Reference().SetPosition(P(18.6, G.HDR_PIN1_Y + 2.4))

# J2: JST S2B-PH-K-S, entry facing up (toward the battery), pin 1 = +
lib = '/usr/share/kicad/footprints/Connector_JST.pretty'
j2 = pcbnew.FootprintLoad(lib, 'JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal')
j2.SetReference('J2'); j2.SetValue('S2B-PH-K-S'); board.Add(j2)
j2.SetOrientationDegrees(90); j2.SetPosition(P(G.PH_SOCK[0], G.PH_SOCK[1]))   # entry faces +x
for pad in j2.Pads(): pad.SetNet(net('BAT_IN' if pad.GetNumber() == '1' else 'GND'))
p1 = [p for p in j2.Pads() if p.GetNumber() == '1'][0].GetPosition()
silk_text('+', pcbnew.ToMM(p1.x) - OX - 2.6, OY - pcbnew.ToMM(p1.y) - 0.6, 1.4)
silk_text('BATTERY', G.PH_SOCK[0] + 3.0, G.PH_SOCK[1] - 3.4, 1.0)

# small parts from the KiCad library: power-on pulse and reverse-battery FET (positions from the case model)
KLIB = '/usr/share/kicad/footprints/'
def lib_fp(ref, value, lib, name, x, y, rot=0.0):
    fp = pcbnew.FootprintLoad(KLIB + lib + '.pretty', name)
    fp.SetReference(ref); fp.SetValue(value); board.Add(fp)
    fp.SetOrientationDegrees(rot); fp.SetPosition(P(x, y))
    fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.7), MM(0.7))); fp.Reference().SetVisible(False)
    return fp
def nets(fp, m):
    for pad in fp.Pads(): pad.SetNet(net(m[pad.GetNumber()]))
SP = G.SMD_PARTS
q1 = lib_fp('Q1', 'AO3401A', 'Package_TO_SOT_SMD', 'SOT-23', *SP['Q1']); nets(q1, {'1': 'GND', '2': 'BAT_RAW', '3': 'BAT_IN'})
q2 = lib_fp('Q2', 'AO3400A', 'Package_TO_SOT_SMD', 'SOT-23', *SP['Q2']); nets(q2, {'1': 'PG', '2': 'GND', '3': 'PWRON'})
c1 = lib_fp('C1', '10uF', 'Capacitor_SMD', 'C_0805_2012Metric', *SP['C1']); nets(c1, {'1': 'PG', '2': 'BAT'})
r1 = lib_fp('R1', '470k', 'Resistor_SMD', 'R_0402_1005Metric', *SP['R1']); nets(r1, {'1': 'PG', '2': 'GND'})
d1 = lib_fp('D1', '1N4148WS', 'Diode_SMD', 'D_SOD-323', *SP['D1']); nets(d1, {'1': 'PG', '2': 'GND'})   # 1 = cathode

# labels
silk_text('STRUTHIO ONE SLIM', 0, -44.0, 1.6)
silk_text('rev S1  0.8 mm', 0, -47.0, 1.0)
silk_text('J1: PINS 1 3 4 5 7 16 18 24 ONLY', 0, -56.0, 1.0, pcbnew.B_SilkS)
silk_text('PINS 3.0 MM OUT OF THE FRONT', 0, -58.0, 1.0, pcbnew.B_SilkS)

# ---- ground pour on both layers ------------------------------------------------------------------------
def add_zone(layer):
    z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(net('GND'))
    z.SetLocalClearance(MM(0.3)); z.SetMinThickness(MM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    ol = z.Outline(); ol.NewOutline()
    ring = max(polys, key=lambda p: abs(G._area(p)))
    for x, y in ring: ol.Append(MM(OX + x), MM(OY - y))
    board.Add(z)
    return z

def save(path):
    pcbnew.SaveBoard(path, board)

# ---- tracks: planned by hand (seven nets), see the routing notes in docs/STRUTHIO_ONE.md --------------------
W_SIG, W_PWR = 0.4, 0.8
def track(points, netname, layer=pcbnew.F_Cu, width=W_SIG):
    for a, b in zip(points, points[1:]):
        t = pcbnew.PCB_TRACK(board); t.SetStart(P(*a)); t.SetEnd(P(*b))
        t.SetLayer(layer); t.SetWidth(MM(width)); t.SetNet(net(netname)); board.Add(t)

def via(x, y, netname):
    v = pcbnew.PCB_VIA(board); v.SetPosition(P(x, y)); v.SetWidth(MM(0.7)); v.SetDrill(MM(0.35))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(net(netname)); board.Add(v)

def pad_xy(fp, num):
    p = [q for q in fp.Pads() if q.GetNumber() == str(num)][0].GetPosition()
    return (pcbnew.ToMM(p.x) - OX, OY - pcbnew.ToMM(p.y))

def route():
    hx = {n: pad_xy(j1, n) for n in (1, 5, 7, 16, 18)}
    sw = {r: board.FindFootprintByReference(r) for r in ('SW1', 'SW2', 'SW3', 'SW4')}
    # left channel (x < even row): GPIO17, GPIO18
    xa, xb = 19.6, 20.25
    # GPIO17 drops to the bottom layer under the strip, runs under the right button at the switch row
    # and comes back up under the left switch; GPIO18 turns straight into the right switch
    x, y = hx[16]; track([(x, y), (xb - 0.0, y - 0.65), (xa, y - 1.3), (xa, -34.9), (19.0, -35.5)], 'GPIO17')
    via(19.0, -35.5, 'GPIO17')
    cx, cy = G.switch_xy()['LEFT']
    track([(19.0, -35.5), (19.0, cy), (cx, cy)], 'GPIO17', pcbnew.B_Cu)
    via(cx, cy, 'GPIO17')
    bx, by = pad_xy(sw['SW1'], 'A'); track([(cx, cy), (bx + (by - cy), by), (bx, by)], 'GPIO17')
    x, y = hx[18]; track([(x, y), (xb, y - 0.65), (xb, -36.6)], 'GPIO18')
    ax, ay = pad_xy(sw['SW2'], 'A'); track([(xb, -36.6), (ax, -36.6 - (xb - ax)), (ax, ay)], 'GPIO18')
    # right channel (x > odd row): GPIO38, GPIO21, BAT
    x38, x21, xbat = 25.8, 26.45, 27.3                                # close to the odd row: the strip edge clears the back shell
    bx, by = pad_xy(sw['SW4'], 'A'); yr = by + 1.8                       # run above the rocker switch row
    x, y = hx[7]; track([(x, y), (x38, y - (x38 - x)), (x38, yr)], 'GPIO38')
    track([(x38, yr), (bx, yr), (bx, by)], 'GPIO38')
    x, y = hx[5]; track([(x, y), (x21, y - (x21 - x)), (x21, -49.5), (x21 + 1.0, -50.5)], 'GPIO21')
    via(x21 + 1.0, -50.5, 'GPIO21')
    bx, by = pad_xy(sw['SW3'], 'A')
    track([(x21 + 1.0, -50.5), (bx, -50.5), (bx, by + 1.6)], 'GPIO21', pcbnew.B_Cu)
    via(bx, by + 1.6, 'GPIO21'); track([(bx, by + 1.6), (bx, by)], 'GPIO21')
    x, y = hx[1]; track([(x, y), (xbat, y - (xbat - x)), (xbat, -34.3)], 'BAT', width=W_PWR)
    via(xbat, -34.3, 'BAT')
    p1 = pad_xy(sw5, 1)
    track([(xbat, -34.3), (p1[0] + 3.7, -34.3), (p1[0], -38.0), p1], 'BAT', pcbnew.B_Cu, W_PWR)
    # battery in: J2 pin 1 -> Q1 drain; Q1 source -> slide switch common; Q1 gate to ground
    j2p1, p2 = pad_xy(j2, 1), pad_xy(sw5, 2)
    qd, qs, qg = pad_xy(q1, 3), pad_xy(q1, 2), pad_xy(q1, 1)
    track([j2p1, (qd[0], j2p1[1]), qd], 'BAT_IN', width=W_PWR)
    yb = -38.4
    track([qs, (qs[0] - 0.6, yb), (-29.0, yb), (-29.0, p2[1]), p2], 'BAT_RAW', width=W_PWR)
    track([qg, (qg[0], qg[1] + 1.1)], 'GND'); via(qg[0], qg[1] + 1.1, 'GND')
    # power-on pulse on the strip, below the header: PWRON runs down between the two pin rows
    pw = pad_xy(j1, 24); qd2, qg2, qs2 = pad_xy(q2, 3), pad_xy(q2, 1), pad_xy(q2, 2)
    track([pw, (23.2, pw[1] - (23.2 - pw[0])), (23.2, -6.8), (24.9, -8.5), (24.9, qd2[1]), qd2], 'PWRON', width=0.2)
    cp, cb = pad_xy(c1, 1), pad_xy(c1, 2); rp, rg = pad_xy(r1, 1), pad_xy(r1, 2); dk, da = pad_xy(d1, 1), pad_xy(d1, 2)
    xg = 21.0                                                            # the gate node: a short bus down the left
    track([cp, (xg, cp[1]), (xg, rp[1]), rp], 'PG', width=0.3)
    track([(xg, rp[1]), (xg, dk[1]), dk], 'PG', width=0.3)
    track([(xg, dk[1]), (xg, qg2[1]), qg2], 'PG', width=0.3)
    track([qs2, (qs2[0], qs2[1] - 1.3)], 'GND'); via(qs2[0], qs2[1] - 1.3, 'GND')
    track([rg, (23.9, -13.0)], 'GND', width=0.3); track([da, (23.9, -13.0)], 'GND', width=0.3); via(23.9, -13.0, 'GND')
    via(xbat, -9.0, 'BAT'); track([(xbat, -9.0), (23.9, -9.0)], 'BAT', pcbnew.B_Cu, width=0.4)
    via(23.9, -9.0, 'BAT'); track([(23.9, -9.0), (cb[0], -9.0), cb], 'BAT', width=0.4)
    # ground stitching beside the switches and on the strip
    for x, y in [(-21.5, -53.5), (24, -53.5), (-16, -65.0), (16, -65.0), (17.6, 22.0), (17.6, 5.0), (17.6, -12.0),
                 (-9, -47.5), (9, -47.5), (0, -60), (-31.5, -58), (31.5, -58)]:
        via(x, y, 'GND')

def main():
    os.makedirs(OUT, exist_ok=True)
    route()
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu): add_zone(layer)
    path = os.path.join(OUT, 'struthio_one_slim.kicad_pcb'); save(path)
    write_assembly()
    # zones are filled and checked on the board as KiCad loads it from disk
    b = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(path, b)
    rpt = os.path.join(OUT, 'drc.rpt')
    pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print('wrote', path, 'and', rpt)
    with open(os.path.join(OUT, 'tht_leads.txt'), 'w') as f:                # for the back shell's reliefs (slim_cad.py)
        for ref in ('SW5', 'J2'):
            for p in b.FindFootprintByReference(ref).Pads():
                q = p.GetPosition(); f.write(f'{ref} {p.GetNumber()} {pcbnew.ToMM(q.x) - OX:.3f} {OY - pcbnew.ToMM(q.y):.3f}\n')

def write_assembly():
    """JLCPCB BOM and placement (CPL) files"""
    lcsc = {'J1': '', 'SW1': 'C318884', 'SW2': 'C318884', 'SW3': 'C318884', 'SW4': 'C318884', 'SW5': 'C17179519', 'J2': 'C173752'}
    lcsc.update({'Q1': 'C15127', 'Q2': 'C20917', 'C1': 'C15850', 'R1': 'C25790', 'D1': 'C2128'})
    comment = {'J1': 'PZ254-2-16-Z-8.5 2x16 male header (standard mounting)', 'SW5': 'SS-12D06-G030', 'J2': 'S2B-PH-K-S'}
    rows = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference(); v = comment.get(ref, fp.GetValue())
        if ref == 'J1': continue                                          # fitted by the builder: 8 bare pins
        rows.setdefault((v, fp.GetFPIDAsString(), lcsc[ref]), []).append(ref)
    with open(os.path.join(OUT, 'BOM_JLCPCB.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for (v, fpid, part), refs in rows.items(): w.writerow([v, ','.join(sorted(refs)), fpid or 'custom', part])
    with open(os.path.join(OUT, 'CPL_JLCPCB.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for fp in board.GetFootprints():
            if fp.GetReference() == 'J1': continue
            c = fp.GetPosition()
            w.writerow([fp.GetReference(), f'{pcbnew.ToMM(c.x) - OX:.3f}mm', f'{OY - pcbnew.ToMM(c.y):.3f}mm', 'Top', f'{fp.GetOrientationDegrees():.0f}'])

if __name__ == '__main__':
    main()
