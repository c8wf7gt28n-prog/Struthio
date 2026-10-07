#!/usr/bin/env python3
"""Build the JLCPCB order files for PCB R22.

    python3 -B scripts/build_r22_order_pack.py <output folder>

Writes <output folder>/STRUTHIO_SLIM4_R22_PCB_ORDER/ and a zip of it:
  SLIM4_R22_GERBER_DRILL.zip   Gerber X2 (13 layers) + Excellon drill (PTH / NPTH separate) + job file
  SLIM4_R22_BOM.csv            JLCPCB BOM: Comment, Designator, Footprint, LCSC Part #
  SLIM4_R22_CPL.csv            JLCPCB placement: Designator, Mid X, Mid Y, Layer, Rotation
  README_PCB_ORDER.txt         the order specification and what was checked
  REFERENCE/                   DRC report, drill maps, assembly drawings (courtyard outlines, both sides)
  KICAD_SOURCE/                the R22 board, project and footprint library

The plot and BOM logic is the one in hardware/slim4/CHECKS/build_builder_packs.py (R26), pointed at
the R22 board in ../board. Needs KiCad 7.0.x (kicad-cli on PATH and a python3 that imports pcbnew) and matplotlib for the
assembly drawings (run it with the package's pinned environment, hardware/slim4/requirements.txt).
Nothing in the board folder is written: the plots come from a temporary copy (SHA-256 checked).
"""
from pathlib import Path
import csv, hashlib, json, re, shutil, subprocess, sys, tempfile, zipfile
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parents[1]
PCB_DIR = HERE / 'board'
BOARD = 'SLIM4_R22.kicad_pcb'
NAME = 'SLIM4_R22'
TOP = 'STRUTHIO_SLIM4_R22_PCB_ORDER'
SOURCING = json.loads((HERE.parent / 'slim4/CHECKS/BOM_SOURCING_R21.json').read_text())['by_mpn']
STAMP = (2026, 10, 7, 0, 0, 0)
GERBER_LAYERS = 'F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts'
PACKAGE = {'ESP32-P4NRW32X': 'QFN-104 0.35 mm pitch + EP', 'W25Q512JVEIQ TR': 'WSON-8 8x6 mm', 'BQ24074RGTR': 'VQFN-16 (TI RGT0016C)',
           'TPS63070RNMR': 'VQFN-HR-15 (TI RNM0015A)', 'MAX98357AETE+T': 'TQFN-16 3x3 mm', 'TUSB320LAIRWBR': 'X2QFN-12 (TI RWB0012A)',
           'FH12-20S-0.5SH(55)': 'FPC 20P 0.5 mm bottom-contact ZIF', 'USB4105-GF-A-120': 'USB-C receptacle', 'D2LS-11': 'Omron D2LS SMD',
           'D2LS-21(20M)': 'Omron D2LS SMD', 'ASWPA4035S2R2MT': 'Power inductor 4035', 'TPD2EUSB30DRTR': 'X2SON-3 1x1 mm (TI DRT)',
           'PESD5V0S1UL,315': 'SOD-882', 'L327S400H11L': 'SMD3225-4P crystal', 'B3U-1000P': 'Omron B3U SMD',
           'SM03B-SRSS-TB(LF)(SN)': 'JST SH 3P side entry', 'SM02B-SRSS-TB(LF)(SN)': 'JST SH 2P side entry'}

PROBE = r'''
import json, pcbnew
b = pcbnew.LoadBoard("BOARD")
mm = pcbnew.ToMM
def fills(b):
    return [sum(z.GetFilledPolysList(l).Area() for l in z.GetLayerSet().Seq()) for z in b.Zones()]
stored = fills(b); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); fresh = fills(b)
b = pcbnew.LoadBoard("BOARD")
pcbnew.WriteDRCReport(b, "DRC.rpt", pcbnew.EDA_UNITS_MILLIMETRES, True)
tracks = list(b.GetTracks())
vias = [t for t in tracks if t.Type() == pcbnew.PCB_VIA_T]
segs = [t for t in tracks if t.Type() != pcbnew.PCB_VIA_T]
inpad = []
for v in vias:
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and pad.HitTest(v.GetPosition()):
                inpad.append([fp.GetReference(), pad.GetNumber(), v.GetNetname()])
holes = sorted({(fp.GetReference(), round(mm(p.GetDrillSize().x), 2), round(mm(p.GetDrillSize().y), 2), p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)
                for fp in b.GetFootprints() for p in fp.Pads() if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)})
parts = []
for fp in b.GetFootprints():
    back = fp.IsFlipped()
    cy = fp.GetCourtyard(pcbnew.B_CrtYd if back else pcbnew.F_CrtYd)
    loops = []
    for i in range(cy.OutlineCount()):
        o = cy.Outline(i)
        loops.append([[round(mm(o.CPoint(k).x), 3), round(mm(o.CPoint(k).y), 3)] for k in range(o.PointCount())])
    parts.append({"ref": fp.GetReference(), "side": "back" if back else "front", "x": mm(fp.GetPosition().x), "y": mm(fp.GetPosition().y), "courtyard": loops})
outline = []
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        pts = [d.GetStart(), d.GetArcMid(), d.GetEnd()] if d.GetShape() == pcbnew.SHAPE_T_ARC else [d.GetStart(), d.GetEnd()]
        outline.append([[round(mm(q.x), 3), round(mm(q.y), 3)] for q in pts])
bb = b.GetBoardEdgesBoundingBox(); ds = b.GetDesignSettings()
print(json.dumps({
    "version": pcbnew.Version(), "fills_current": max(abs(a - c) for a, c in zip(stored, fresh)) / 1e12 < 1e-6,
    "copper_layers": b.GetCopperLayerCount(), "thickness": mm(ds.GetBoardThickness()),
    "outline": [round(mm(bb.GetWidth()), 2), round(mm(bb.GetHeight()), 2)],
    "track_widths": sorted({round(mm(t.GetWidth()), 3) for t in segs}), "min_clearance": mm(ds.m_MinClearance),
    "vias": sorted({(round(mm(v.GetWidth()), 3), round(mm(v.GetDrillValue()), 3)) for v in vias}),
    "via_xy": [[mm(v.GetPosition().x), mm(v.GetPosition().y)] for v in vias],
    "via_count": len(vias), "blind_or_micro_vias": sum(v.GetViaType() != pcbnew.VIATYPE_THROUGH for v in vias),
    "vias_in_smd_pads": inpad, "footprint_holes": holes, "parts": parts, "edges": outline,
    "segments": len(segs), "footprints": len(b.GetFootprints()), "nets": b.GetNetCount(),
}))
'''


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'failed: {" ".join(map(str, cmd))}\n{r.stdout}\n{r.stderr}')
    return r.stdout


def zip_dir(src, out, prefix=''):
    with zipfile.ZipFile(out, 'w') as z:
        for p in sorted(p for p in Path(src).rglob('*') if p.is_file()):
            zi = zipfile.ZipInfo(prefix + p.relative_to(src).as_posix(), STAMP)
            zi.external_attr = 0o100644 << 16
            z.writestr(zi, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def pin_dates(p):
    p = Path(p)
    if p.suffix == '.pdf':
        p.write_bytes(re.sub(rb'D:\d{14}', b'D:20261007000000', p.read_bytes()))
        return
    t = re.sub(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d', '2026-10-07T00:00:00+00:00', p.read_text())
    t = re.sub(r'date \d{4}-\d\d-\d\d \d\d:\d\d:\d\d', 'date 2026-10-07 00:00:00', t)
    t = re.sub(r'date \w{3} \w{3} [ \d]\d \d\d:\d\d:\d\d \d{4}', 'date Wed Oct  7 00:00:00 2026', t)
    p.write_text(t)


def pcbnew_python():
    for exe in [shutil.which('python3'), '/usr/bin/python3']:
        if exe and subprocess.run([exe, '-c', 'import pcbnew'], capture_output=True).returncode == 0:
            return exe
    sys.exit('needs a python3 that can import pcbnew (KiCad 7.0.x)')


def natural(ref):
    m = re.match(r'([A-Z]+)(\d+)', ref)
    return (m[1], int(m[2])) if m else (ref, 0)


def board_parts(text):
    rows = []
    for blk in re.split(r'\n  \(footprint ', text)[1:]:
        g = lambda pat: (re.search(pat, blk) or [None, ''])[1]
        descr = g(r'\(descr "([^"]*)"\)')
        jlc = re.search(r'JLC (C\d+)', descr)
        tags = g(r'\(tags "([^"]*)"\)')
        value = g(r'\(fp_text value "([^"]+)"')
        pkg = PACKAGE.get(value) or re.sub(r'^SLIM4 R\d+ (?:[CR] )?|\s*\d{4}Metric', '', tags)
        mpn = '' if re.match(r'\d{4} ', value) else value
        bound = SOURCING.get(mpn, {}).get('lcsc', '') if not jlc else ''
        rows.append(dict(ref=g(r'\(fp_text reference "([^"]+)"'), value=value, mpn=mpn, layer=g(r'\(layer "([^"]+)"\)'),
                         lcsc=jlc[1] if jlc else bound, lcsc_source='board' if jlc else ('sourcing' if bound else ''), descr=descr, pkg=pkg))
    return rows


def assembly_drawing(back, path, facts):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly, Arc
    fig = plt.figure(figsize=(297 / 25.4, 420 / 25.4))           # A3 portrait, board at 2:1
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(-74.25, 74.25); ax.set_ylim(169, -41)
    ax.set_aspect('equal'); ax.axis('off')
    sx = -1 if back else 1                                         # back side drawn as seen from the back
    for pts in facts['edges']:
        ax.plot([sx * x for x, _ in pts], [y for _, y in pts], lw=0.6, color='k')
    side = 'back' if back else 'front'
    n = 0
    for p in facts['parts']:
        if p['side'] != side:
            continue
        n += 1
        for loop in p['courtyard']:
            ax.add_patch(MPoly([(sx * x, y) for x, y in loop], closed=True, fill=False, lw=0.3, ec='#1f5fa8'))
        xs = [x for loop in p['courtyard'] for x, _ in loop] or [p['x']]
        ys = [y for loop in p['courtyard'] for _, y in loop] or [p['y']]
        fs = max(2.2, min(6.0, 1.6 * min(max(xs) - min(xs), max(ys) - min(ys))))
        ax.text(sx * p['x'], p['y'], p['ref'], ha='center', va='center', fontsize=fs, color='#b0201a')
    ax.text(-72, 150, f'STRUTHIO SLIM4 R22 - {side.upper()} SIDE ({n} parts), seen from the {side}. Scale 2:1 on A3. '
            'Outlines are courtyards; the CPL file is the placement authority.', fontsize=6.5, va='top')
    fig.savefig(path, metadata={'CreationDate': None}); plt.close(fig)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1]).resolve()
    dst = out / TOP
    if dst.exists():
        shutil.rmtree(dst)
    src_sha = sha(PCB_DIR / BOARD)
    ver = run(['kicad-cli', 'version']).strip()
    if not ver.startswith('7.'):
        sys.exit(f'kicad-cli {ver}: this board is KiCad 7 format; use KiCad 7.0.x')
    tmp = Path(tempfile.mkdtemp())
    try:
        work = tmp / 'pcb'
        shutil.copytree(PCB_DIR, work)
        g = tmp / 'gerber'; g.mkdir()
        run(['kicad-cli', 'pcb', 'export', 'gerbers', '--layers', GERBER_LAYERS, '--subtract-soldermask', '--exclude-value',
             '-o', str(g) + '/', BOARD], cwd=work)
        run(['kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th', '--excellon-units', 'mm',
             '--generate-map', '--map-format', 'pdf', '-o', str(g) + '/', BOARD], cwd=work)
        run(['kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both', '-o', str(tmp / 'pos.csv'), BOARD], cwd=work)
        facts = json.loads(run([pcbnew_python(), '-c', PROBE.replace('BOARD', BOARD)], cwd=work).strip().splitlines()[-1])
        drc = (work / 'DRC.rpt').read_text()
        for f in g.iterdir():
            pin_dates(f)
        dst.mkdir(parents=True)
        ref = dst / 'REFERENCE'; ref.mkdir()
        for m in sorted(g.glob('*.pdf')):
            shutil.move(str(m), ref / m.name)
        zip_dir(g, dst / f'{NAME}_GERBER_DRILL.zip')
        pth, npth = (g / f'{NAME}-PTH.drl').read_text(), (g / f'{NAME}-NPTH.drl').read_text()
        flashes = [(int(x) / 1e6, -int(y) / 1e6) for side in ('F_Mask.gts', 'B_Mask.gbs')
                   for x, y in re.findall(r'(?m)^X(-?\d+)Y(-?\d+)D03\*$', (g / f'{NAME}-{side}').read_text())]
        mask_at_vias = sorted({(round(vx, 3), round(vy, 3)) for vx, vy in facts['via_xy'] for fx, fy in flashes if abs(fx - vx) < 0.05 and abs(fy - vy) < 0.05})
        (ref / 'DRC_REPORT_KICAD7.txt').write_text(re.sub(r'\*\* Created on .*\*\*\n', '', drc).replace(str(work) + '/', ''))

        text = (work / BOARD).read_text()
        parts = board_parts(text)
        groups = {}
        for p in parts:
            groups.setdefault((p['value'], p['mpn'], p['lcsc'], p['pkg'], p['layer']), []).append(p['ref'])
        with open(dst / f'{NAME}_BOM.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #', 'Manufacturer Part #', 'Quantity', 'Side', 'Note'])
            for (val, mpn, lcsc, pkg, layer), refs in sorted(groups.items(), key=lambda kv: natural(sorted(kv[1], key=natural)[0])):
                refs = sorted(refs, key=natural)
                first = next(p for p in parts if p['ref'] == refs[0])
                note = ('LCSC number from hardware/slim4/CHECKS/BOM_SOURCING_R21.json (checked on its LCSC/JLCPCB page)' if first['lcsc_source'] == 'sourcing'
                        else '' if lcsc else 'no LCSC number: source by manufacturer part number')
                w.writerow([val, ','.join(refs), pkg, lcsc, mpn, len(refs), 'Top' if layer == 'F.Cu' else 'Bottom', note])
        with open(tmp / 'pos.csv') as f, open(dst / f'{NAME}_CPL.csv', 'w', newline='') as o:
            w = csv.writer(o)
            w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
            rows = sorted(csv.DictReader(f), key=lambda r: natural(r['Ref']))
            for r in rows:
                w.writerow([r['Ref'], f"{float(r['PosX']):.4f}mm", f"{float(r['PosY']):.4f}mm", 'Top' if r['Side'] == 'top' else 'Bottom', f"{float(r['Rot']):g}"])
        cpl_count = len(rows)
        assembly_drawing(True, ref / 'ASSEMBLY_DRAWING_BACK_SIDE.pdf', facts)
        assembly_drawing(False, ref / 'ASSEMBLY_DRAWING_FRONT_SIDE.pdf', facts)
        for pdf in ref.glob('ASSEMBLY*.pdf'):
            pin_dates(pdf)
        srcdir = dst / 'KICAD_SOURCE'; srcdir.mkdir()
        for f in [BOARD, f'{NAME}.kicad_pro', 'fp-lib-table']:
            shutil.copy2(PCB_DIR / f, srcdir / f)
        shutil.copytree(PCB_DIR / 'SLIM4.pretty', srcdir / 'SLIM4.pretty')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if sha(PCB_DIR / BOARD) != src_sha:
        sys.exit('the R22 board changed during the build: stop')

    no_lcsc = [(p['ref'], p['value']) for p in sorted(parts, key=lambda p: natural(p['ref'])) if not p['lcsc']]
    bound = [(p['ref'], p['value'], p['lcsc']) for p in sorted(parts, key=lambda p: natural(p['ref'])) if p['lcsc_source'] == 'sourcing']
    sides = {s: sum(1 for p in parts if (p['layer'] == 'F.Cu') == (s == 'Top')) for s in ('Top', 'Bottom')}
    drc_line = ' / '.join(l.strip('* ') for l in drc.splitlines() if l.startswith('** Found'))
    vias = ', '.join(f'{d:g} mm drill / {s:g} mm pad' for s, d in facts['vias'])
    slots = [h for h in facts['footprint_holes'] if h[1] != h[2]]
    npth = sorted({(h[0][:2] if h[0].startswith('SW') else h[0], h[1]) for h in facts['footprint_holes'] if not h[3]})
    tent = re.search(r'\(viasonmask (true|false)\)', text)
    readme = f"""STRUTHIO SLIM4 - PCB R22 - JLCPCB ORDER FILES
=============================================

Upload to JLCPCB (PCB + PCBA):
  {NAME}_GERBER_DRILL.zip   Gerber X2 (13 layers), Excellon drill (PTH and NPTH separate), job file
  {NAME}_BOM.csv            bill of materials, one line per part type, every line with an LCSC number
  {NAME}_CPL.csv            placement: designator, centre X/Y (mm), side, rotation

BOARD OPTIONS
  Layers                 {facts['copper_layers']}  (F.Cu, In1 GND plane, In2 power planes, In3 signal, In4 GND plane, B.Cu)
  Thickness              {facts['thickness']:g} mm  - REQUIRED: the enclosure is designed around 1.2 mm
  Size                   {facts['outline'][0]:g} x {facts['outline'][1]:g} mm, non-rectangular, with an internal battery window
  Stackup                JLCPCB standard 6-layer 1.2 mm stackup
  Copper weight          1 oz outer / 0.5 oz inner
  Min track / space      {min(facts['track_widths']):g} mm / {facts['min_clearance']:g} mm
  Vias                   {facts['via_count']} through vias, {vias}; no blind or buried vias
  Via covering           EPOXY FILLED AND CAPPED (via-in-pad, POFV; JLCPCB's default for 6 layers).
                         Needed: {len(facts['vias_in_smd_pads'])} vias sit in SMD pads ({', '.join(f'{r} pad {n}' for r, n, _ in facts['vias_in_smd_pads'])}),
                         and every other via must stay covered (no mask openings are plotted)
  Plated slots           {', '.join(f'{r} {a:g} x {b:g} mm' for r, a, b, _ in slots) or 'none'} (USB-C shell legs)
  Non-plated holes       {', '.join(f'{r} dia {d:g} mm' for r, d in npth) or 'none'}
  Surface finish         ENIG (0.35 mm-pitch ESP32-P4 and QFN/WSON/X2SON parts need flat pads)
  Mask / silk            green / white
  Impedance control      not needed: MIPI-DSI runs are 29-40 mm, USB is full speed (12 Mbit/s)
  Quantity               5 boards, 2 assembled (or as many as you want to assemble)

ASSEMBLY
  Sides                  BOTH: {sides['Bottom']} parts on the back (B.Cu) and {sides['Top']} on the front (the four Omron
                         D2LS switches SW1-SW4, which the case buttons press)
  Parts                  {len(parts)} placements, {len(groups)} BOM lines; LCSC numbers for all of them
{chr(10).join(f'                         {r:6} {v:22} {l}  (from BOM_SOURCING_R21.json)' for r, v, l in bound)}
{('  STILL WITHOUT AN LCSC NUMBER: ' + ', '.join(r for r, _ in no_lcsc)) if no_lcsc else ''}
  Rotations              KiCad's. In JLCPCB's placement preview check pin 1 / polarity of every
                         IC, diode, connector and crystal and correct the rotation there if their
                         library part is drawn at a different zero angle. Pay attention to:
                         U1 (ESP32-P4, QFN-104), U2, U4, U8-U14, D1, D2, Q1, Y1, J1-J5.

NOT ON THE BOARD (buy separately)
  Display     Startek KD047HDFID001: 4.7 in 720 x 1280 IPS, ST7703, 450 nits, 61.0 x 110.6 x 1.8 mm.
              It plugs into J1 through the display adapter (see DISPLAY_PORT.md); ask Startek for the
              full datasheet (FPC pin definition and initialisation code) when ordering.
  Battery     703450-class Li-ion with protection board and 10k NTC, JST SH 3-pin lead (J3: 1 BAT+, 2 NTC, 3 GND)
  Speakers    2 x Same Sky CMS-18138A-SP with a JST SH 2-pin lead (J4 left, J5 right)

CHECKS RUN ON THESE FILES
  KiCad {facts['version']} DRC: {drc_line}  (REFERENCE/DRC_REPORT_KICAD7.txt)
  Zone fills current: {'yes' if facts['fills_current'] else 'NO - refill before plotting'};  solder-mask openings at vias: {len(mask_at_vias)}
  Board: {facts['footprints']} footprints, {facts['nets']} nets, {facts['segments']} track segments, {facts['via_count']} vias
  Electrical and land-pattern review: ELECTRICAL_REVIEW_R22.md
"""
    (dst / 'README_PCB_ORDER.txt').write_text(readme)
    zip_dir(dst, out / f'{TOP}.zip', TOP + '/')
    print(json.dumps({'drc': drc_line, 'fills_current': facts['fills_current'], 'parts': len(parts), 'bom_lines': len(groups),
                      'no_lcsc': no_lcsc, 'cpl': cpl_count, 'mask_at_vias': len(mask_at_vias), 'tented': bool(tent) and tent[1] == 'false',
                      'vias_in_pads': facts['vias_in_smd_pads'], 'zip': str(out / f'{TOP}.zip')}, indent=1))


if __name__ == '__main__':
    main()
