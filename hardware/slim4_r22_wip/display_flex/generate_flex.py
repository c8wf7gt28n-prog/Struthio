#!/usr/bin/env python3
"""STRUTHIO SLIM4 display flex: generate the KiCad flex board and its JLCPCB files from a panel pin map.

    python3 generate_flex.py <panel_pinmap.csv> <output folder> [--length MM] [--preview]

The flex joins the panel's 31-pin, 0.3 mm tail (Hirose FH26W-31S-0.3SHW(60) on the flex, LCSC C2973806) to
the R22 board's J1 (Hirose FH12-20S-0.5SH, bottom contact) through 20 gold fingers at 0.5 mm pitch.
Everything about the J1 end is fixed by the board. Everything about the panel end comes from the pin map:
one row per panel pin, with the panel's own signal name and its role, one of

    GND VCI IOVCC RESX CLKP CLKN D0P D0N D1P D1N LEDA LEDK NC

A pin map containing '?' roles is refused unless --preview is given (a preview is watermarked NOT FOR ORDER).

Layout (flex coordinates, mm, y towards J1): the FH26 sits at the top edge, opening up; its pins fan out to
0.5 mm columns; each net crosses on the bottom copper in its own row; the J1 columns run down the top copper
over a bottom-copper ground plane to vias above the fingers, which are on the bottom copper (the side that
faces the board at J1). The J1 columns sit beside the panel columns, so the flex has a dog-leg.
Needs KiCad 7.0.x (python3 with pcbnew, kicad-cli) and its footprint library in /usr/share/kicad/footprints.
"""
import csv, json, math, os, re, shutil, subprocess, sys, zipfile
sys.dont_write_bytecode = True
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = '/usr/share/kicad/footprints/'
ROLES = ['RESX', 'VCI', 'IOVCC', 'CLKP', 'CLKN', 'D1P', 'D1N', 'D0P', 'D0N', 'LEDK', 'LEDA', 'GND']   # row order (pairs adjacent)
# R22 J1 (FH12-20S-0.5SH, back side). x of each pin relative to J1's centre, in flex coordinates (seen from the
# flex's top copper, fingers on the bottom copper facing the board): x_flex = X_board - 17.0. From board/SLIM4_R22.kicad_pcb.
J1 = {1: ('RESX', 4.75), 2: ('VCI', 4.25), 3: ('IOVCC', 3.75), 4: ('NC', 3.25), 5: ('NC', 2.75), 6: ('GND', 2.25),
      7: ('NC', 1.75), 8: ('NC', 1.25), 9: ('GND', 0.75), 10: ('CLKP', 0.25), 11: ('CLKN', -0.25), 12: ('GND', -0.75),
      13: ('D1P', -1.25), 14: ('D1N', -1.75), 15: ('GND', -2.25), 16: ('D0P', -2.75), 17: ('D0N', -3.25), 18: ('GND', -3.75),
      19: ('LEDK', -4.25), 20: ('LEDA', -4.75)}
NETNAME = {'RESX': 'LCD_RESX', 'VCI': 'LCD_VCI_3V0', 'IOVCC': 'LCD_1V8', 'CLKP': 'MIPI_DSI_CLK_P', 'CLKN': 'MIPI_DSI_CLK_N',
           'D1P': 'MIPI_DSI_D1_P', 'D1N': 'MIPI_DSI_D1_N', 'D0P': 'MIPI_DSI_D0_P', 'D0N': 'MIPI_DSI_D0_N',
           'LEDK': 'LCD_LED_K', 'LEDA': 'LCD_LED_A', 'GND': 'GND'}
W = 0.10          # track width (mm)
VIA = (0.45, 0.20)
PITCH = 0.5       # column pitch after the fan-out
ROW = 0.55        # row pitch on the bottom copper
FINGER = (0.30, 3.75)
END_W = 10.5      # FH12-20 FPC width
STIFF = 6.0       # stiffener length at the J1 end (0.20 mm PI on the top side -> 0.30 mm total)


def die(msg):
    sys.exit('generate_flex: ' + msg)


def read_pinmap(path, preview):
    rows = list(csv.DictReader(open(path)))
    pins = {}
    for r in rows:
        n = int(r['pin']); role = r['role'].strip().upper()
        if role == '?' and not preview:
            die(f'pin {n} has no role yet: fill {os.path.basename(path)} from the panel datasheet (or pass --preview)')
        if role not in ROLES + ['NC', '?']:
            die(f'pin {n}: unknown role {role!r}')
        pins[n] = (r.get('panel_name', '').strip(), 'NC' if role == '?' else role)
    if sorted(pins) != list(range(1, 32)):
        die('the pin map must list pins 1..31 exactly once')
    need = {'RESX', 'VCI', 'IOVCC', 'CLKP', 'CLKN', 'D0P', 'D0N', 'D1P', 'D1N', 'LEDA', 'LEDK', 'GND'}
    have = {role for _, role in pins.values()}
    if not preview and need - have:
        die('the pin map has no pin for: ' + ', '.join(sorted(need - have)))
    return pins


def main():
    args = sys.argv[1:]
    preview = '--preview' in args
    length = 70.0
    if '--length' in args:
        length = float(args[args.index('--length') + 1])
    pos = [a for a in args if not a.startswith('--') and not re.match(r'^\d+(\.\d+)?$', a)]
    if len(pos) != 2:
        die(__doc__)
    pinmap, out = os.path.abspath(pos[0]), os.path.abspath(pos[1])
    pins = read_pinmap(pinmap, preview)
    name = 'SLIM4_DISPLAY_FLEX_R1' + ('_PREVIEW' if preview else '')
    os.makedirs(out, exist_ok=True)
    pro = os.path.join(out, name + '.kicad_pro')
    rules = json.load(open(os.path.join(HERE, 'flex_rules.kicad_pro')))
    pcb_path = os.path.join(out, name + '.kicad_pcb')

    b = pcbnew.BOARD()
    b.SetCopperLayerCount(2)
    ds = b.GetDesignSettings()
    ds.SetBoardThickness(pcbnew.FromMM(0.12))
    MM = pcbnew.FromMM
    nets = {}
    def net(role):
        if role not in nets:
            n = pcbnew.NETINFO_ITEM(b, NETNAME[role]); b.Add(n); nets[role] = n
        return nets[role]
    def seg(pts, layer, role, w=W):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1))); t.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
            t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(net(role)); b.Add(t)
    def via(x, y, role):
        v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(VIA[0])); v.SetDrill(MM(VIA[1]))
        v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(net(role)); b.Add(v)
    def line(pts, layer, w=0.1):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1)))
            s.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2))); s.SetLayer(layer); s.SetWidth(MM(w)); b.Add(s)
    def text(s, x, y, layer, size=0.8):
        t = pcbnew.PCB_TEXT(b); t.SetText(s); t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); t.SetTextThickness(MM(size * 0.15)); b.Add(t)

    # --- panel end: FH26W-31S on the top copper, opening at the top edge -----------------------------------------
    fp = pcbnew.FootprintLoad(LIB + 'Connector_FFC-FPC.pretty', 'Hirose_FH26-31S-0.3SHW_2Rows-31Pins-1MP_P0.60mm_Horizontal')
    b.Add(fp); fp.SetPosition(pcbnew.VECTOR2I(0, MM(2.3))); fp.SetOrientationDegrees(90)
    fp.SetReference('J1'); fp.SetValue('FH26W-31S-0.3SHW(60)'); fp.Reference().SetVisible(False)
    fp.SetDescription('FH26W-31S-0.3SHW(60) | JLC C2973806 | panel tail, contacts facing the flex')
    pads = {int(p.GetNumber()): p for p in fp.Pads() if p.GetNumber().isdigit()}
    used = sorted([n for n in pins if pins[n][1] != 'NC'], key=lambda n: pcbnew.ToMM(pads[n].GetPosition().x))
    for n, p in pads.items():
        if pins[n][1] != 'NC':
            p.SetNet(net(pins[n][1]))
    for p in fp.Pads():
        if not p.GetNumber().isdigit():
            p.SetNet(b.FindNet(''))                 # FH26 fitting nails: mechanical only
    # stubs out of the connector to y=4.3 (even pins pass between the odd row), then fan out to 0.5 mm columns
    nA = len(used)
    xA = {n: (i - (nA - 1) / 2) * PITCH for i, n in enumerate(used)}
    y_fan0, y_fan1 = 4.3, 4.3 + max(2.0, max(abs(xA[n] - pcbnew.ToMM(pads[n].GetPosition().x)) for n in used) * 2.2)
    rows_y0 = y_fan1 + 0.8
    role_rows = [r for r in ROLES if r in {pins[n][1] for n in used} | {v[0] for v in J1.values()}]
    yrow = {r: rows_y0 + i * ROW for i, r in enumerate(role_rows)}
    rows_y1 = rows_y0 + (len(role_rows) - 1) * ROW
    for n in used:
        role = pins[n][1]; px = pcbnew.ToMM(pads[n].GetPosition().x); py = pcbnew.ToMM(pads[n].GetPosition().y)
        seg([(px, py), (px, y_fan0), (xA[n], y_fan1), (xA[n], yrow[role])], pcbnew.F_Cu, role)
        via(xA[n], yrow[role], role)
    # --- J1 end ----------------------------------------------------------------------------------------------------
    x_off = max(xA.values()) + 1.2 + 4.75                    # J1 columns to the right of the panel columns
    y_body = rows_y1 + 1.2                                   # long section starts here
    y_fv = (length - FINGER[1] - 0.25 - 0.9, length - FINGER[1] - 0.25 - 1.6)   # staggered via rows above the fingers
    fing = pcbnew.FOOTPRINT(b); b.Add(fing); fing.SetReference('FINGERS'); fing.SetValue('FH12-20 gold fingers')
    fing.Reference().SetVisible(False); fing.Value().SetVisible(False)
    fing.SetPosition(pcbnew.VECTOR2I(MM(x_off), MM(length - 0.25 - FINGER[1] / 2)))
    fing.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    for k, (role, x) in J1.items():
        p = pcbnew.PAD(fing); p.SetNumber(str(k)); p.SetShape(pcbnew.PAD_SHAPE_RECT); p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p.SetSize(pcbnew.VECTOR2I(MM(FINGER[0]), MM(FINGER[1])))
        ls = pcbnew.LSET(); ls.AddLayer(pcbnew.B_Cu); ls.AddLayer(pcbnew.B_Mask); p.SetLayerSet(ls)
        fing.Add(p)
        p.SetPos0(pcbnew.VECTOR2I(MM(x), 0))                    # KiCad 7 saves the pad's footprint-relative Pos0
        p.SetPosition(pcbnew.VECTOR2I(MM(x_off + x), MM(length - 0.25 - FINGER[1] / 2)))
        if role != 'NC':
            p.SetNet(net(role))
            vy = y_fv[k % 2]
            seg([(x_off + x, yrow[role]), (x_off + x, vy)], pcbnew.F_Cu, role)
            via(x_off + x, yrow[role], role)
            via(x_off + x, vy, role)
            seg([(x_off + x, vy), (x_off + x, length - 0.25 - FINGER[1] + 0.05)], pcbnew.B_Cu, role)
    # --- rows on the bottom copper ---------------------------------------------------------------------------------
    for role in role_rows:
        xs = [xA[n] for n in used if pins[n][1] == role] + [x_off + x for k, (r, x) in J1.items() if r == role]
        if len(xs) > 1:
            seg([(min(xs), yrow[role]), (max(xs), yrow[role])], pcbnew.B_Cu, role, 0.12)
    # --- outline --------------------------------------------------------------------------------------------------
    x0 = min(min(xA.values()) - 0.8, -6.0); x1 = x_off + END_W / 2
    xe0, xe1 = x_off - END_W / 2, x_off + END_W / 2
    c = 0.8                                                   # 45 deg relief at the inside corner
    outline = [(x0, 0), (x1, 0), (xe1, length), (xe0, length), (xe0, y_body + c), (xe0 - c, y_body), (x0, y_body), (x0, 0)]
    line(outline, pcbnew.Edge_Cuts)
    # ground plane under the long section (bottom copper), stopping above the finger vias' clearance
    z = pcbnew.ZONE(b); z.SetLayer(pcbnew.B_Cu); z.SetNet(net('GND'))
    zp = [(xe0 + 0.3, y_body + 0.3), (xe1 - 0.3, y_body + 0.3), (xe1 - 0.3, length - FINGER[1] - 0.6), (xe0 + 0.3, length - FINGER[1] - 0.6)]
    ol = z.Outline(); ol.NewOutline()
    for x, y in zp:
        ol.Append(MM(x), MM(y))
    z.SetMinThickness(MM(0.1)); z.SetLocalClearance(MM(0.15)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    b.Add(z)
    # stiffener (User.1) and notes
    line([(xe0, length - STIFF), (xe1, length - STIFF), (xe1, length), (xe0, length), (xe0, length - STIFF)], pcbnew.User_1, 0.05)
    line([(x0, 0), (x1, 0), (x1, 4.6), (x0, 4.6), (x0, 0)], pcbnew.User_2, 0.05)
    text('PI STIFFENER 0.20 TOP SIDE -> 0.30 TOTAL', x_off, length - STIFF / 2, pcbnew.User_1, 0.6)
    text('FR4 OR PI STIFFENER 0.20 UNDER J1 (BOTTOM SIDE)', (x0 + x1) / 2, 2.3, pcbnew.User_2, 0.6)
    label = 'STRUTHIO SLIM4 DISPLAY FLEX R1' + (' PREVIEW - NOT FOR ORDER' if preview else '')
    text(label, x_off, (y_body + length - STIFF) / 2, pcbnew.F_SilkS, 0.9)
    for t in [x for x in b.GetDrawings() if x.GetClass() == 'PCB_TEXT' and x.GetText() == label]:
        t.SetTextAngleDegrees(90)
    text('1', x_off + 4.0, length - STIFF - 1.0, pcbnew.F_SilkS, 0.9)
    b.Save(pcb_path)
    json.dump(rules, open(pro, 'w'), indent=2)                 # after Save: a fresh BOARD() would write default rules
    for f in os.listdir(out):
        if f.endswith('.kicad_prl'):
            os.remove(os.path.join(out, f))
    print(json.dumps({'board': pcb_path, 'length_mm': length, 'width_top_mm': round(x1 - x0, 2), 'panel_pins_used': nA,
                      'rows': role_rows, 'preview': preview}))


if __name__ == '__main__':
    main()
