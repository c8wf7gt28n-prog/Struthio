#!/usr/bin/env python3
"""STRUTHIO ONE SLIM · the ONE board, 0.8 mm thick, behind the Waveshare's J8 socket.

    /usr/bin/python3 make_slim_pcb.py         (KiCad 7 pcbnew, tracks planned by hand below)

Rev S4 (no soldering): JLCPCB fits every part, the header included. The ONE's circuit without the slide switch
and the power-on pulse: the Waveshare's own PWR key is the power button, so the cell connects straight through
Q1 (reverse-battery guard) to header pin 1. Header pin 9 has no net: the firmware reads that as "ONE SLIM"
(the ONE board ties it to GND).
  - 0.8 mm board, outline from cad/slim/slim_cad.py
  - the case's front bosses hold the board 2.4 mm + the header plastic behind the socket, so the pins go 3.6 mm in

Every position comes from cad/one/one_cad.py (as set up by slim_cad.py), so the board, the case and the fit
checks share one set of numbers. The design frame there is the view from the front; KiCad's top view of this
board is the same view (the top side faces the front of the handheld), so KiCad x = design x and
KiCad y = -design y (+ origin).

Parts (all on the top side, all surface-mount, all assembled by JLCPCB):
  J1A, J1B  Ckmtw B-2100N10P-B110 (C124391): 2 x 5 male header, 2.54 mm, surface-mount, 6.0 mm pins.
            J1A on Waveshare pins 1-10, J1B on 15-24 (a free row between them, so the plastics never touch).
            Footprint from the datasheet (210SMT-2*XP): pads 3.45 x 1.0, 8.4 mm across, 1.5 mm apart.
  SW1-4     XKB TS-1187A-B-A-B tact switches (C318884, JLC basic): LEFT, RIGHT, DART L, DART R
  J2        JST S2B-PH-SM4-TB (C295747): surface-mount side-entry PH 2.0 socket, the battery plugs in here
  Q1        AO3401A P-FET (C15127, JLC basic): reverse-battery protection
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

# J1A, J1B: Waveshare header numbering, odd pins on the edge row (x 24.47), pin 1 at the top. Each pin's
# foot runs outward: odd-row pads to the edge side, even-row pads to the inside.
HDR_NETS = {1: 'BAT', 3: 'GND', 4: 'GND', 5: 'GPIO21', 7: 'GPIO38', 16: 'GPIO17', 18: 'GPIO18'}   # 9: no net (SLIM)
xe, xc = G.HDR_ROW_X[1], G.HDR_ROW_X[0]
XM = (xe + xc) / 2
PAD_C, PAD_L, PAD_W = 0.75 + 3.45 / 2, 3.45, 1.0
HDR = {}
for ref, (r0, r1) in S.HDR_ROWS.items():
    yc = G.HDR_PIN1_Y - (r0 + r1) / 2 * 2.54
    fp = new_fp(ref, 'B-2100N10P-B110', XM, yc, fpname='PinHeader_2x05_P2.54mm_SMD_Ckmtw210SMT')
    for k in range(r0, r1 + 1):
        for n in (2 * k + 1, 2 * k + 2):
            dx = PAD_C if n % 2 else -PAD_C
            add_pad(fp, n - 2 * r0, dx, G.HDR_PIN1_Y - k * 2.54 - yc, pcbnew.PAD_SHAPE_RECT, (PAD_L, PAD_W), netname=HDR_NETS.get(n))
    HDR[ref] = (fp, r0)
    yt, yb = G.HDR_PIN1_Y - r0 * 2.54 + 1.27, G.HDR_PIN1_Y - r1 * 2.54 - 1.27
    for yy in (yt + 0.2, yb - 0.2): add_poly_edges([(XM - 2.54, yy), (XM + 2.54, yy)], pcbnew.F_SilkS, 0.15)
    fp.Reference().SetPosition(P(17.6, yt - 0.6)); fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
silk_text('1', xe + 4.2, G.HDR_PIN1_Y + 1.6, 0.9)

def hdr_pad(n):
    """(x, y) of the pad for Waveshare pin n"""
    for fp, r0 in HDR.values():
        q = [p for p in fp.Pads() if p.GetNumber() == str(n - 2 * r0)]
        if q and r0 * 2 < n <= r0 * 2 + 10:
            c = q[0].GetPosition(); return (pcbnew.ToMM(c.x) - OX, OY - pcbnew.ToMM(c.y))
    raise KeyError(n)

# SW1-4: TS-1187A. Only the diagonal pads carry nets: A to the GPIO, D to GND. A diagonal pair is never
# joined inside the switch, so the key works whichever way the assembler turns the part.
SW = {'SW1': ('LEFT', 'GPIO17'), 'SW2': ('RIGHT', 'GPIO18'), 'SW3': ('DART_L', 'GPIO21'), 'SW4': ('DART_R', 'GPIO38')}
for ref, (key, sig) in SW.items():
    x, y = G.switch_xy()[key]
    fp = new_fp(ref, 'TS-1187A-B-A-B', x, y)
    for i, (dx, dy) in enumerate(((-3.0, 1.875), (3.0, 1.875), (-3.0, -1.875), (3.0, -1.875))):
        add_pad(fp, 'ABCD'[i], dx, dy, pcbnew.PAD_SHAPE_RECT, (1.0, 0.75), netname={0: sig, 3: 'GND'}.get(i))
    silk_rect(x - 2.0, y - 2.6, x + 2.0, y + 2.6)            # between the pads


# J2: JST S2B-PH-SM4-TB (surface-mount, side entry), entry facing +x, pin 1 = +
lib = '/usr/share/kicad/footprints/Connector_JST.pretty'
j2 = pcbnew.FootprintLoad(lib, 'JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal')
j2.SetReference('J2'); j2.SetValue('S2B-PH-SM4-TB'); board.Add(j2)
j2.SetOrientationDegrees(90); j2.SetPosition(P(G.PH_SOCK[0], G.PH_SOCK[1]))   # entry faces +x
for pad in j2.Pads():
    if pad.GetNumber() in ('1', '2'): pad.SetNet(net('BAT_IN' if pad.GetNumber() == '1' else 'GND'))
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
q1 = lib_fp('Q1', 'AO3401A', 'Package_TO_SOT_SMD', 'SOT-23', *SP['Q1']); nets(q1, {'1': 'GND', '2': 'BAT', '3': 'BAT_IN'})

# labels
silk_text('STRUTHIO ONE SLIM', 0, -44.0, 1.6)
silk_text('rev S4  0.8 mm', 0, -47.0, 1.0)
silk_text('EVERY PART FITTED BY JLCPCB', 0, -56.0, 1.0, pcbnew.B_SilkS)
silk_text('NO SOLDERING', 0, -58.0, 1.0, pcbnew.B_SilkS)

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
    sw = {r: board.FindFootprintByReference(r) for r in ('SW1', 'SW2', 'SW3', 'SW4')}
    pi, po = XM - PAD_C + PAD_L / 2, XM + PAD_C - PAD_L / 2                    # inner ends of the even / odd pads
    # ---- left: the wings (even row of J1B), out under the pads' outer ends and down two lanes by the strip edge
    xg17, xg18 = 17.3, 18.1
    x, y = hdr_pad(16); x0 = x - PAD_L / 2 + 0.3
    track([(x0, y), (xg17 + 0.6, y), (xg17, y - 0.6), (xg17, -35.0)], 'GPIO17')
    via(xg17, -35.6, 'GPIO17'); track([(xg17, -35.0), (xg17, -35.6)], 'GPIO17')
    cx, cy = G.switch_xy()['LEFT']
    track([(xg17, -35.6), (xg17, cy), (cx, cy)], 'GPIO17', pcbnew.B_Cu)      # under the right switch, below the BAT run
    via(cx, cy, 'GPIO17')
    bx, by = pad_xy(sw['SW1'], 'A'); track([(cx, cy), (bx + (by - cy), by), (bx, by)], 'GPIO17')
    x, y = hdr_pad(18)
    track([(x0, y), (xg18 + 0.4, y), (xg18, y - 0.4), (xg18, -36.6)], 'GPIO18')
    ax, ay = pad_xy(sw['SW2'], 'A'); track([(xg18, -36.6), (ax, -36.6 - (xg18 - ax)), (ax, ay)], 'GPIO18')
    # ---- right: BAT, DART L, DART R (odd row of J1A). BAT goes out to a via by the edge; the darts drop to vias
    # between the rows under the plastic. All three cross the header zone on the bottom layer.
    xbat, x21, x38 = 28.3, 26.45, 25.8
    x, y = hdr_pad(1); track([(x, y), (xbat, y)], 'BAT', width=W_PWR); via(xbat, y, 'BAT')
    for n, sig, xl, xv in ((5, 'GPIO21', x21, 27.0), (7, 'GPIO38', 25.3, 25.3)):
        x, y = hdr_pad(n); yv = y - 1.27
        track([(po + 0.3, y), (XM + 0.0, y - (po + 0.3 - XM)), (XM, yv)], sig); via(XM, yv, sig)
        yu = 1.4 if sig == 'GPIO21' else 2.6                                      # back up below J1B
        track([(XM, yv), (xl, yv), (xl, yu + 0.6), (xv, yu)], sig, pcbnew.B_Cu); via(xv, yu, sig)
    track([(27.0, 1.4), (x21, 0.85), (x21, -49.5), (x21 + 1.0, -50.5)], 'GPIO21')
    via(x21 + 1.0, -50.5, 'GPIO21')
    bx, by = pad_xy(sw['SW3'], 'A')
    track([(x21 + 1.0, -50.5), (bx, -50.5), (bx, by + 1.6)], 'GPIO21', pcbnew.B_Cu)
    via(bx, by + 1.6, 'GPIO21'); track([(bx, by + 1.6), (bx, by)], 'GPIO21')
    bx, by = pad_xy(sw['SW4'], 'A'); yr = by + 1.8                            # run above the rocker switch row
    track([(25.3, 2.6), (x38, 2.1), (x38, yr), (bx, yr), (bx, by)], 'GPIO38')
    # battery in: J2 pin 1 -> Q1 drain; Q1 source -> BAT, up the bottom layer to header pin 1; Q1 gate to ground
    j2p1 = pad_xy(j2, 1)
    qd, qs, qg = pad_xy(q1, 3), pad_xy(q1, 2), pad_xy(q1, 1)
    track([j2p1, (qd[0], j2p1[1]), qd], 'BAT_IN', width=W_PWR)
    yv = qs[1] - 1.35                                                     # come up under Q1's source, clear of its gate
    track([(xbat, hdr_pad(1)[1]), (xbat, -34.3), (qs[0] + 2.4, -34.3), (qs[0] + 2.4, yv), (qs[0], yv)], 'BAT', pcbnew.B_Cu, W_PWR)
    via(qs[0], yv, 'BAT'); track([(qs[0], yv), qs], 'BAT', width=W_PWR)
    track([qg, (qg[0], qg[1] + 1.1)], 'GND'); via(qg[0], qg[1] + 1.1, 'GND')
    # ground: the two GND header pads straight down to the bottom pour, and stitching beside the switches
    x, y = hdr_pad(3); track([(po + 0.3, y), (XM, y - (po + 0.3 - XM)), (XM, y - 1.27)], 'GND'); via(XM, y - 1.27, 'GND')
    x, y = hdr_pad(4); track([(x, y), (x - 1.9, y)], 'GND'); via(x - 1.9, y, 'GND')
    for x, y in [(-21.5, -53.5), (24, -53.5), (-16, -65.0), (16, -65.0), (XM, 19.0), (21.0, 0.0), (21.0, -12.0),
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
    with open(os.path.join(OUT, 'tht_leads.txt'), 'w') as f:                # through-hole leads (none since S2)
        for fp in b.GetFootprints():
            ref = fp.GetReference()
            for p in fp.Pads():
                if p.GetAttribute() != pcbnew.PAD_ATTRIB_PTH: continue
                q = p.GetPosition(); f.write(f'{ref} {p.GetNumber()} {pcbnew.ToMM(q.x) - OX:.3f} {OY - pcbnew.ToMM(q.y):.3f}\n')

def write_assembly():
    """JLCPCB BOM and placement (CPL) files"""
    lcsc = {'J1A': 'C124391', 'J1B': 'C124391', 'SW1': 'C318884', 'SW2': 'C318884', 'SW3': 'C318884', 'SW4': 'C318884', 'J2': 'C295747', 'Q1': 'C15127'}
    comment = {'J2': 'S2B-PH-SM4-TB(LF)(SN)'}
    rows = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference(); v = comment.get(ref, fp.GetValue())
        rows.setdefault((v, fp.GetFPIDAsString(), lcsc[ref]), []).append(ref)
    with open(os.path.join(OUT, 'BOM_JLCPCB.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for (v, fpid, part), refs in rows.items(): w.writerow([v, ','.join(sorted(refs)), fpid or 'custom', part])
    with open(os.path.join(OUT, 'CPL_JLCPCB.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for fp in board.GetFootprints():
            c = fp.GetPosition()
            w.writerow([fp.GetReference(), f'{pcbnew.ToMM(c.x) - OX:.3f}mm', f'{OY - pcbnew.ToMM(c.y):.3f}mm', 'Top', f'{fp.GetOrientationDegrees():.0f}'])

if __name__ == '__main__':
    main()
