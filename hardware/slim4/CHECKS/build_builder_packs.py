#!/usr/bin/env python3
"""Build the files to send to the three builders, from this package.

    python -B CHECKS/build_builder_packs.py <output folder>

Writes <output folder>/STRUTHIO_SLIM4_R31_BUILDER_FILES/ and a zip of it:
  1_PCB_FABRICATION/   JLCPCB order: Gerber + drill zip, BOM, placement (CPL), assembly drawings, KiCad source
  2_3D_PRINTING/       one STL and one STEP per printed part, renders
  3_ACRYLIC_STICKER/   face-film die line (PDF with a CutContour spot colour, SVG, DXF),
                       a 1:1 check drawing, the two tape die-cuts and the cover-glass lens outline

Needs KiCad 7.0.x (kicad-cli on PATH and a python3 that can import pcbnew) and the pinned
CadQuery environment (requirements.txt). No source in the package is changed: the PCB files are
plotted from a temporary copy of LAYERS/01_PCB (its SHA-256 is checked before and after), and
and the printed parts and film are rebuilt from LAYERS/02_CASE/build_r12.py. The one file written
into the package is CHECKS/R26_FAB_SUMMARY.json, a record
of the fab outputs (DRC, BOM coverage, via covering) that the studio and the convergence check read.
"""
from pathlib import Path
import csv, hashlib, io, json, math, re, runpy, shutil, subprocess, sys, tempfile, zipfile
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PCB_DIR = ROOT / 'LAYERS/01_PCB'
BOARD = 'SLIM4_R26.kicad_pcb'
NAME = 'SLIM4_R26'
TOP = 'STRUTHIO_SLIM4_R31_BUILDER_FILES'
SOURCING = json.loads((ROOT / 'CHECKS/BOM_SOURCING_R21.json').read_text())['by_mpn']
STAMP = (2026, 10, 8, 0, 0, 0)
STEP_STAMP = '2026-10-08T00:00:00'
GERBER_LAYERS = 'F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts'

# Printed parts: output name, CAD part name prefix, quantity per device, what to look after.
PRINTED = [
    ('01_FRONT_SHELL', 'FRONT SHELL R12', 1,
     'Plate 2.0 mm, only 0.70 mm over the LCD pocket ledge; 0.8 mm grille slots; lens rebate 59.4 x 104.6 (lens 59.2 x 104.4); '
     'flap holes 17.0; DART opening 50 x 7 with two 2.0 x 1.4 pivot bosses (1.0 mm trunnion, 0.10 mm radial clearance); front clamp posts 2.0; '
     'lap skirt 0.95 mm, 0.10 mm radial clearance to the rear lip.'),
    ('02_REAR_SHELL', 'REAR SHELL R12', 1,
     'Floor and walls 2.0 mm; 0.95 mm lap lip whose top stops 0.10 mm under the plate (tape seat); speaker chambers with ledges; '
     'board supports 2.4; power-plunger bore 2.8; RESET/BOOT pinholes 1.2; USB-C relief.'),
    ('03_FLAP_CAP_L', '16 MM FLAP CAP L', 1,
     'Cap 16.0 through a 17.0 plate hole; 17.8 x 0.8 retention flange; 1.4 actuator nub; four 1.2 stop legs (may be trimmed after a switch test).'),
    ('04_FLAP_CAP_R', '16 MM FLAP CAP R', 1, 'As the left cap.'),
    ('05_DART_ROCKER', 'DART ROCKER', 1,
     '49.0 x 6.5 cap; 1.0 mm trunnion pins snap into the front-shell bosses; two 1.4 nubs; 1.2 stop legs at X +/-23.'),
    ('06_POWER_PLUNGER', 'POWER PLUNGER', 1, '2.4 pin in the 2.8 rear-shell bore; 4.0 collar inside.'),
]
# Packages of the parts whose footprints were drawn from vendor land patterns (taken from their descriptions).
PACKAGE = {'ESP32-P4NRW32X': 'QFN-104 0.35 mm pitch + EP', 'W25Q512JVEIQ TR': 'WSON-8 8x6 mm', 'BQ24074RGTR': 'VQFN-16 (TI RGT0016C)',
           'TPS63070RNMR': 'VQFN-HR-15 (TI RNM0015A)', 'MAX98357AETE+T': 'TQFN-16 3x3 mm', 'TUSB320LAIRWBR': 'X2QFN-12 (TI RWB0012A)',
           'FH12A-40S-0.5SH(55)': 'FPC 40P 0.5 mm top-contact ZIF', 'USB4105-GF-A-120': 'USB-C receptacle', 'D2LS-11': 'Omron D2LS SMD',
           'D2LS-21(20M)': 'Omron D2LS SMD', 'D2LS-21': 'Omron D2LS SMD', 'ASWPA4035S2R2MT': 'Power inductor 4035', 'TPD2EUSB30DRTR': 'X2SON-3 1x1 mm (TI DRT)',
           'PESD5V0S1UL,315': 'SOD-882', 'L327S400H11L': 'SMD3225-4P crystal', 'B3U-1000P': 'Omron B3U SMD',
           'SM03B-SRSS-TB(LF)(SN)': 'JST SH 3P side entry', 'S2B-PH-SM4-TB(LF)(SN)': 'JST PH 2P side entry',
           '53261-0271': 'Molex PicoBlade 2P side entry', 'AO3401A': 'SOT-23'}
RENDERS = ['VIEW_EXPLODED.png', 'VIEW_FRONT_ISO.png', 'VIEW_REAR_ISO.png', 'VIEW_INTERNALS.png', 'SECTION_F_LAP_DISPLAY.png']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def zip_dir(src, out, prefix=''):
    files = sorted(p for p in Path(src).rglob('*') if p.is_file())
    with zipfile.ZipFile(out, 'w') as z:
        for p in files:
            zi = zipfile.ZipInfo(prefix + p.relative_to(src).as_posix(), STAMP)
            zi.external_attr = 0o100644 << 16
            z.writestr(zi, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def pin_dates(path):
    """Replace KiCad's plot timestamps with the package date so rebuilds give the same bytes (dates only)."""
    p = Path(path)
    if p.suffix == '.pdf':                                   # same-length swap keeps the PDF offsets valid
        p.write_bytes(re.sub(rb'D:\d{14}', b'D:20261007000000', p.read_bytes()))
        return
    t = re.sub(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d', '2026-10-07T00:00:00+00:00', p.read_text())
    t = re.sub(r'date \d{4}-\d\d-\d\d \d\d:\d\d:\d\d', 'date 2026-10-07 00:00:00', t)
    t = re.sub(r'date \w{3} \w{3} [ \d]\d \d\d:\d\d:\d\d \d{4}', 'date Wed Oct  7 00:00:00 2026', t)
    p.write_text(t)


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'failed: {" ".join(map(str, cmd))}\n{r.stdout}\n{r.stderr}')
    return r.stdout


# ---------------------------------------------------------------------------
# 1  PCB fabrication
# ---------------------------------------------------------------------------
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
                inpad.append([fp.GetReference(), pad.GetNumber(), v.GetNetname(), round(mm(v.GetPosition().x), 3), round(mm(v.GetPosition().y), 3)])
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


def pcbnew_python():
    for exe in [shutil.which('python3'), '/usr/bin/python3']:
        if exe and subprocess.run([exe, '-c', 'import pcbnew'], capture_output=True).returncode == 0:
            return exe
    sys.exit('needs a python3 that can import pcbnew (KiCad 7.0.x)')


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
        bound = SOURCING.get(mpn, {}).get('lcsc', '') if not jlc else ''      # numbers in the board file win
        rows.append(dict(ref=g(r'\(fp_text reference "([^"]+)"'), value=value, mpn=mpn,
                         layer=g(r'\(layer "([^"]+)"\)'), lcsc=jlc[1] if jlc else bound, lcsc_source='board' if jlc else ('sourcing' if bound else ''),
                         descr=descr, pkg=pkg))
    return rows


def natural(ref):
    m = re.match(r'([A-Z]+)(\d+)', ref)
    return (m[1], int(m[2])) if m else (ref, 0)


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
    ax.text(-72, 150, f'STRUTHIO SLIM4 R26 - {side.upper()} SIDE ({n} parts), seen from the {side}. Scale 2:1 on A3. '
            'Outlines are courtyards; the CPL file is the placement authority.', fontsize=6.5, va='top')
    fig.savefig(path, metadata={'CreationDate': None}); plt.close(fig)


def build_pcb(dst):
    src_sha = sha(PCB_DIR / BOARD)
    ver = run(['kicad-cli', 'version']).strip()
    if not ver.startswith('7.'):
        sys.exit(f'kicad-cli {ver}: this board is KiCad 7 format; use KiCad 7.0.x so the plot matches the source')
    tmp = Path(tempfile.mkdtemp())
    try:
        work = tmp / 'pcb'
        shutil.copytree(PCB_DIR, work, ignore=shutil.ignore_patterns('R2?_FROM_R2?', '*.md', '*_PCB_LAYER.json'))
        g = tmp / 'gerber'
        g.mkdir()
        run(['kicad-cli', 'pcb', 'export', 'gerbers', '--layers', GERBER_LAYERS, '--subtract-soldermask', '--exclude-value',
             '-o', str(g) + '/', BOARD], cwd=work)
        run(['kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th', '--excellon-units', 'mm',
             '--generate-map', '--map-format', 'pdf', '-o', str(g) + '/', BOARD], cwd=work)
        run(['kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
             '-o', str(tmp / 'pos.csv'), BOARD], cwd=work)
        facts = json.loads(run([pcbnew_python(), '-c', PROBE.replace('BOARD', BOARD)], cwd=work).strip().splitlines()[-1])
        drc = (work / 'DRC.rpt').read_text()

        for f in g.iterdir():
            pin_dates(f)
        dst.mkdir(parents=True)
        ref = dst / 'REFERENCE'
        ref.mkdir()
        for m in sorted(g.glob('*.pdf')):
            shutil.move(str(m), ref / m.name)
        zip_dir(g, dst / f'{NAME}_GERBER_DRILL.zip')
        pth, npth = (g / f'{NAME}-PTH.drl').read_text(), (g / f'{NAME}-NPTH.drl').read_text()
        hits = lambda t: len(re.findall(r'(?m)^X-?[\d.]+Y-?[\d.]+$', t))
        drill_counts = {'pth_round_holes': hits(pth), 'plated_slots': pth.count('G85'), 'npth_holes': hits(npth) + npth.count('G85')}
        # Via covering as plotted: any solder-mask flash centred on a via (Gerber Y = -board Y) would be an opening.
        flashes = [(int(x) / 1e6, -int(y) / 1e6) for side in ('F_Mask.gts', 'B_Mask.gbs')
                   for x, y in re.findall(r'(?m)^X(-?\d+)Y(-?\d+)D03\*$', (g / f'{NAME}-{side}').read_text())]
        # a via inside an SMD pad sits in that pad's own opening (via-in-pad, filled and capped by POFV): not a via opening
        in_pad_xy = {(x, y) for _, _, _, x, y in facts['vias_in_smd_pads']}
        mask_at_vias = sorted({(round(vx, 3), round(vy, 3)) for vx, vy in facts['via_xy'] for fx, fy in flashes
                               if abs(fx - vx) < 0.05 and abs(fy - vy) < 0.05 and (round(vx, 3), round(vy, 3)) not in in_pad_xy})
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
                note = ('LCSC number from CHECKS/BOM_SOURCING_R21.json (checked on its LCSC/JLCPCB page)' if first['lcsc_source'] == 'sourcing'
                        else '' if lcsc else 'no LCSC number: source by manufacturer part number')
                w.writerow([val, ','.join(refs), pkg, lcsc, mpn, len(refs), 'Top' if layer == 'F.Cu' else 'Bottom', note])
        with open(tmp / 'pos.csv') as f, open(dst / f'{NAME}_CPL.csv', 'w', newline='') as o:
            w = csv.writer(o)
            w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
            rows = sorted(csv.DictReader(f), key=lambda r: natural(r['Ref']))
            for r in rows:
                w.writerow([r['Ref'], f"{float(r['PosX']):.4f}mm", f"{float(r['PosY']):.4f}mm",
                            'Top' if r['Side'] == 'top' else 'Bottom', f"{float(r['Rot']):g}"])
        cpl_count = len(rows)
        assembly_drawing(True, ref / 'ASSEMBLY_DRAWING_BACK_SIDE.pdf', facts)
        assembly_drawing(False, ref / 'ASSEMBLY_DRAWING_FRONT_SIDE.pdf', facts)
        for pdf in ref.glob('ASSEMBLY*.pdf'):
            pin_dates(pdf)
        for doc in ('ELECTRICAL_REVIEW_R22.md', 'DISPLAY_PORT.md', 'FIRMWARE_PINMAP.md', 'README_PCB_LAYER.md'):
            shutil.copy2(PCB_DIR / doc, ref / doc)
        shutil.copy2(ROOT / 'CHECKS/R26_DSI_REPORT.md', ref / 'R26_DSI_REPORT.md')
        srcdir = dst / 'KICAD_SOURCE'
        srcdir.mkdir()
        for f in [BOARD, f'{NAME}.kicad_pro', 'fp-lib-table']:
            shutil.copy2(PCB_DIR / f, srcdir / f)
        shutil.copytree(PCB_DIR / 'SLIM4.pretty', srcdir / 'SLIM4.pretty')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if sha(PCB_DIR / BOARD) != src_sha:
        sys.exit('the R26 board changed during the build: stop')

    no_lcsc = [(p['ref'], p['value']) for p in sorted(parts, key=lambda p: natural(p['ref'])) if not p['lcsc']]
    bound = [(p['ref'], p['value'], p['lcsc']) for p in sorted(parts, key=lambda p: natural(p['ref'])) if p['lcsc_source'] == 'sourcing']
    sides = {s: sum(1 for p in parts if (p['layer'] == 'F.Cu') == (s == 'Top')) for s in ('Top', 'Bottom')}
    drc_line = ' / '.join(l.strip('* ') for l in drc.splitlines() if l.startswith('** Found'))
    vias = ', '.join(f'{d:g} mm drill / {s:g} mm pad' for s, d in facts['vias'])
    slots = [h for h in facts['footprint_holes'] if h[1] != h[2]]
    npth = sorted({(h[0][:2] if h[0].startswith('SW') else h[0], h[1]) for h in facts['footprint_holes'] if not h[3]})
    tent = re.search(r'\(viasonmask (true|false)\)', text)
    readme = f"""STRUTHIO SLIM4 - PCB R26 - JLCPCB ORDER FILES
=============================================

Upload to JLCPCB (PCB + PCBA):
  {NAME}_GERBER_DRILL.zip   Gerber X2 (13 layers), Excellon drill (PTH and NPTH separate), job file
  {NAME}_BOM.csv            bill of materials, one line per part type, every line with an LCSC number
  {NAME}_CPL.csv            placement: designator, centre X/Y (mm), side, rotation

BOARD OPTIONS
  Layers                 {facts['copper_layers']}  (F.Cu, In1 GND plane, In2 power planes, In3 signal, In4 GND plane, B.Cu)
  Thickness              {facts['thickness']:g} mm  - REQUIRED: the enclosure is designed around 1.2 mm
  Size                   {facts['outline'][0]:g} x {facts['outline'][1]:g} mm, non-rectangular, with an internal battery window
  Stackup                JLCPCB JLC06121H-3313 (1.2 mm 6-layer, 1 oz outer / 0.5 oz inner): F.Cu | 3313
                         0.0994 | In1 | core 0.35 | In2 | 2116 0.1088 | In3 | core 0.35 | In4 | 3313 0.0994 | B.Cu
                         (written into the board file; the Gerber job file carries it)
  Copper weight          1 oz outer / 0.5 oz inner
  Min track / space      {min(facts['track_widths']):g} mm / {facts['min_clearance']:g} mm
  Vias                   {facts['via_count']} through vias, {vias}; no blind or buried vias
  Via covering           EPOXY FILLED AND CAPPED (via-in-pad, POFV; JLCPCB's default for 6 layers).
                         Needed: {len(facts['vias_in_smd_pads'])} vias sit in SMD pads ({', '.join(f'{r} pad {n}' for r, n, *_ in facts['vias_in_smd_pads'])}),
                         and every other via must stay covered (no mask openings are plotted; case
                         support posts and stop legs land on some of them)
  Plated slots           {', '.join(f'{r} {a:g} x {b:g} mm' for r, a, b, _ in slots) or 'none'} (USB-C shell legs)
  Non-plated holes       {', '.join(f'{r} dia {d:g} mm' for r, d in npth) or 'none'}
  Surface finish         ENIG (0.35 mm-pitch ESP32-P4 and QFN/WSON/X2SON parts need flat pads)
  Mask / silk            green / white
  Impedance control      YES - select impedance control with stackup JLC06121H-3313. Controlled: the three
                         MIPI-DSI pairs MIPI_DSI_CLK_P/N, MIPI_DSI_D0_P/N, MIPI_DSI_D1_P/N, coupled pairs,
                         100 ohm differential +/-10 %:
                           L1 F.Cu   0.127 mm lines, 0.18 mm gap, edge-coupled microstrip over In1 ground
                                     (about 100 ohm, Hammerstad-Jensen with the coupled-microstrip factor)
                           L4 In3.Cu 0.10 mm lines, 0.18 mm gap, edge-coupled stripline between In2 ground
                                     (0.1088 mm, a ground area over the DSI runs) and In4 ground (0.35 mm)
                                     (about 98 ohm, IPC-2141 asymmetric stripline)
                         The only other DSI copper is the B.Cu breakout under U1 (about 1 mm a line, 0.127 mm).
                         Check these widths and gaps in JLCPCB's impedance calculator when ordering; if it asks
                         for different ones, stop - the DSI routing would need adjusting, not the fab.
                         USB is full speed (12 Mbit/s) and needs no impedance control.
  Quantity               5 boards, 2 assembled (or as many as you want to assemble)

ASSEMBLY
  Sides                  BOTH: {sides['Bottom']} parts on the back (B.Cu) and {sides['Top']} on the front (the four Omron
                         D2LS switches SW1-SW4, which the case buttons press, and the display socket J1)
  Parts                  {len(parts)} placements, {len(groups)} BOM lines; LCSC numbers for all of them
{chr(10).join(f'                         {r:6} {v:22} {l}  (from CHECKS/BOM_SOURCING_R21.json)' for r, v, l in bound)}
{('  STILL WITHOUT AN LCSC NUMBER: ' + ', '.join(r for r, _ in no_lcsc)) if no_lcsc else ''}
  Rotations              KiCad's. In JLCPCB's placement preview check pin 1 / polarity of every
                         IC, diode, connector and crystal and correct the rotation there if their
                         library part is drawn at a different zero angle. Pay attention to:
                         U1 (ESP32-P4, QFN-104), U2, U4, U8-U14, D1, D2, Q1, Q2, Y1, J1-J5.
                         J1 is a TOP-contact FPC socket (FH12A) on the FRONT: contacts face away from
                         the board, mouth toward the bottom edge (+Y in KiCad).

U1 STOCK (check before ordering)
  On 2026-10-07 JLCPCB had 0 of the ESP32-P4NRW32X (C54540373); every other line was in stock.
  Pre-order it through JLCPCB Global Sourcing, or consign v3.x chips (ordering code ending in X)
  bought from an Espressif-authorised source. Do not substitute ESP32-P4NRW32 (no X, revision v1.x).

PLUG AND PLAY: FOUR PARTS PLUG INTO THE ASSEMBLED BOARD (buy separately, no soldering)
  J1 Display  Crystalfontz CFAF7201280A0-050TN: 5.0 in 720 x 1280 IPS, ILI9881C, MIPI DSI,
              66.1 x 120.4 x 1.85 mm. Its own 40-pin 0.5 mm tail goes straight into J1 (Hirose
              FH12A-40S top contact, on the front, under the panel): fold the tail once behind the
              panel (radius 1.5 mm, at least 2 mm past the glass), contacts facing up, push it into
              J1 and close the latch. No adapter cable. The panel then lies face up over the board,
              bottom edge at Y 109.8, with 2.3-3.3 mm between its back and the board.
              Pin map and fold: REFERENCE/DISPLAY_PORT.md.
  J3 Battery  a PROTECTED 1-cell Li-ion/LiPo of 1000 mAh or more, up to 34 x 50 x 7 mm (503450 about
              1000 mAh, 703450 about 1500 mAh), on a JST PH 2.0 mm 2-pin plug, red lead = pin 1 =
              BAT+ (the Adafruit / SparkFun convention).
              Check the polarity before plugging a pack in; do not try a reversed pack. Q2 (P-MOSFET)
              blocks a reversed pack while the board runs from it. With USB connected it does not: the
              design analysis predicts only the charger's 4-11 mA test current then (not tested), and
              the screen shows BATTERY REVERSED. Unplug it at once.
              Charge current 0.49 A nominal, 0.55 A worst case (BQ24074, R412 1.8 k): at most 0.55 C
              on a 1000 mAh cell. Charging stops on the charger's safety timer (4-6 h with TMR open);
              a 1500 mAh cell finishes inside it. There is NO cell-temperature sensing (TS is a fixed
              10 k): use a pack with its own protection board and do not charge it hot or below 0 C.
  J4, J5      2 speakers, 4-8 ohm, up to 3 W, on Molex PicoBlade 1.25 mm 2-pin plugs (the plug
  Speakers    Adafruit uses on its small speakers, e.g. product 3923): J4 left, J5 right; pin 1 = +.

CHECKS RUN ON THESE FILES
  KiCad {facts['version']} DRC: {drc_line}  (REFERENCE/DRC_REPORT_KICAD7.txt)
  Zone fills current: {'yes' if facts['fills_current'] else 'NO - refill before plotting'};  solder-mask openings at vias: {len(mask_at_vias)}
  Board: {facts['footprints']} footprints, {facts['nets']} nets, {facts['segments']} track segments, {facts['via_count']} vias
  Electrical and land-pattern review: REFERENCE/ELECTRICAL_REVIEW_R22.md (R22 board) and
  REFERENCE/README_PCB_LAYER.md (the R23 edits 12-15, the R24 power-layout edits 16-24, the R25 DSI and supply edits 25-30,
              the R26 DSI pair edits 31-35, and their checks; the DSI pair check: REFERENCE/R26_DSI_REPORT.md)

REFERENCE/    assembly drawings (courtyards, both sides, 2:1 on A3), drill maps, DRC report, electrical
              review, display port and firmware pin map
KICAD_SOURCE/ native KiCad 7 board, project and local footprint library (R26)
"""
    (dst / 'README_PCB_ORDER.txt').write_text(readme)

    # A record of the fab outputs in the package itself (the studio and the convergence check read it).
    drc_n = {k: int(re.search(rf'Found (\d+) {k}', drc)[1]) for k in ('DRC violations', 'unconnected pads', 'Footprint errors')}
    summary = {
        'board': f'LAYERS/01_PCB/{BOARD}', 'board_sha256': src_sha, 'generator': 'CHECKS/build_builder_packs.py',
        'status': 'order files ready (JLCPCB PCB + PCBA); U1 ESP32-P4NRW32X out of stock at JLCPCB on 2026-10-07: pre-order or consign',
        'kicad': facts['version'], 'drc': {'violations': drc_n['DRC violations'], 'unconnected_pads': drc_n['unconnected pads'],
                                           'footprint_errors': drc_n['Footprint errors']},
        'zone_fills_current': facts['fills_current'],
        'gerber_layers': GERBER_LAYERS.split(','), 'drill': drill_counts,
        'copper_layers': facts['copper_layers'], 'thickness_mm': facts['thickness'], 'outline_mm': facts['outline'],
        'min_track_mm': min(facts['track_widths']), 'min_clearance_mm': facts['min_clearance'],
        'vias': {'count': facts['via_count'], 'pad_mm': facts['vias'][0][0], 'drill_mm': facts['vias'][0][1],
                 'tented': bool(tent) and tent[1] == 'false', 'mask_openings_at_vias': [list(v) for v in mask_at_vias],
                 'in_smd_pads': [{'ref': r, 'pad': n, 'net': net, 'xy': [x, y]} for r, n, net, x, y in facts['vias_in_smd_pads']]},
        'bom': {'lines': len(groups), 'placements': len(parts), 'with_lcsc': sum(1 for p in parts if p['lcsc']),
                'by_mpn_only': [r for r, _ in no_lcsc], 'bound_in_sourcing_file': [r for r, _, _ in bound],
                'unbound': [p['ref'] for p in parts if 'BIND_BEFORE_FAB' in p['descr'] and not p['lcsc']],
                'out_of_stock': ['U1']},
        'cpl_placements': cpl_count, 'sides': sides,
        'order': {'build': 'prototype', 'quantity': '5 boards, 2 assembled', 'assembly': 'both sides', 'stackup': 'JLCPCB JLC06121H-3313 (1.2 mm 6-layer)',
                  'copper': '1 oz outer / 0.5 oz inner', 'finish': 'ENIG', 'via_covering': 'epoxy filled and capped (POFV)', 'impedance_control': {'ordered': True, 'nets': 'MIPI_DSI_* (3 pairs)', 'differential_ohm': 100, 'tolerance': '10%', 'width_mm': {'F.Cu': 0.127, 'In3.Cu': 0.10}, 'gap_mm': {'F.Cu': 0.18, 'In3.Cu': 0.18}, 'reference': {'F.Cu': 'In1 GND', 'In3.Cu': 'In2 GND area + In4 GND'}},
                  'mask_silk': 'green / white'},
    }
    (ROOT / 'CHECKS/R26_FAB_SUMMARY.json').write_text(json.dumps(summary, indent=1) + '\n')
    return facts, parts, no_lcsc


# ---------------------------------------------------------------------------
# 2  3D printing
# ---------------------------------------------------------------------------
def stl_check(path):
    import numpy as np
    data = Path(path).read_bytes()
    n = int.from_bytes(data[80:84], 'little')
    assert len(data) == 84 + 50 * n, 'not a binary STL'
    rec = np.frombuffer(data[84:], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]), count=n)
    v = rec['v'].reshape(-1, 3)
    _, idx = np.unique(np.round(v, 5), axis=0, return_inverse=True)
    tri = idx.reshape(-1, 3)
    e = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    return n, bool((counts == 2).all())


def build_print(dst, B):
    import cadquery as cq
    (dst / 'STL').mkdir(parents=True)
    (dst / 'STEP').mkdir()
    rows = []
    for out, prefix, qty, note in PRINTED:
        hits = [p for p in B['PARTS'] if p['name'].startswith(prefix)]
        assert len(hits) == 1, prefix
        solid = hits[0]['solid']
        solid = solid.val() if hasattr(solid, 'val') else solid
        assert len(solid.Solids()) == 1, prefix
        stl = dst / 'STL' / f'{out}.stl'
        cq.exporters.export(solid, str(stl), exportType='STL', tolerance=0.01, angularTolerance=0.1)
        step = dst / 'STEP' / f'{out}.step'
        cq.exporters.export(solid, str(step), exportType='STEP')
        step.write_text(re.sub(r"(FILE_NAME\('[^']*',)'[0-9T:-]+'", lambda m: m.group(1) + "'" + STEP_STAMP + "'", step.read_text(), count=1))
        tris, closed = stl_check(stl)
        bb = solid.BoundingBox()
        rows.append(dict(name=out, qty=qty, note=note, size=(bb.xlen, bb.ylen, bb.zlen), vol=solid.Volume() / 1000, tris=tris, closed=closed))
    ref = dst / 'REFERENCE'
    ref.mkdir()
    for r in RENDERS:
        shutil.copy2(ROOT / 'CHECKS/renders' / r, ref / r)
    table = '\n'.join(f"  {r['name']:18} {r['qty']}   {r['size'][0]:6.1f} x {r['size'][1]:6.1f} x {r['size'][2]:5.2f}   {r['vol']:6.2f} cm3   "
                      f"{'closed' if r['closed'] else 'OPEN'}" for r in rows)
    notes = '\n'.join(f"  {r['name']}: {r['note']}" for r in rows)
    readme = f"""STRUTHIO SLIM4 - CASE R12 - FILES FOR THE 3D PRINT SERVICE
==========================================================

STATUS: ON HOLD - DO NOT PRINT. The owner set the case aside for PCB R23 (package R28; R24 in R29, R25 in R30, R26 in R31). CASE R12
was converged on PCB R21 (package R26); it does not fit the R23-R26 board's 5 in Crystalfontz panel or
its new connectors (CHECKS/R31_CONVERGENCE_REPORT.md lists the failing rows). The case pass
(CASE R13) redraws it; these files show the R12 design and its print specification.

ORDER (per device)
  Part               Qty  Size X x Y x Z (mm)        Volume       Mesh
{table}
  Order: 1 set (01-06) per device, plus 2 extra sets of the controls (03-06). The stop legs
  and trunnions are tuned on the first print (production gates D5, D11, D12).

FILES
  STL/    one binary STL per part, 0.01 mm chord tolerance; every mesh checked closed (watertight)
  STEP/   the same parts as exact solids (use these if the service accepts STEP)
  REFERENCE/  renders of the assembled case, for orientation only
  Units are millimetres. Parts are in their assembled position (front of the device = +Z),
  so the six files overlay each other in any viewer; orient them freely for printing.

PROCESS (specified, DECISIONS_R26.md)
  SLA, tough ABS-like engineering resin, 0.05 mm layers, black, all six parts; supports
  removed and sanded, no paint. The design has features close to the limits of most
  processes: a 0.70 mm ledge, 0.8 mm grille slots, 1.0 mm trunnion pins, 1.2 mm stop legs
  and pinholes, 1.4 mm actuator nubs, 0.10-0.2 mm running clearances. FDM is not suitable.
  Do not scale or add shrink compensation beyond the service's normal calibration.
  Keep support marks off: the outer side walls and the raised bezel rings and DART surround
  of 01, the outer back and walls of 02, and the top faces of 03-05. The flat front of 01
  is covered by the face film.

FEATURES TO PROTECT
{notes}

AFTER PRINTING
  Supplied separately, not printed: LCD module and its 0.7 mm cover-glass lens, the two
  0.10 mm tape die-cuts (lap ring and display frame; both in the sticker pack), battery and
  0.2 mm foam pad, two Same Sky CMS-18138A-SP speakers and 0.25 mm gaskets, FPC extension,
  harnesses. Assembly order: ASSEMBLY/ASSEMBLY_SEQUENCE.md in the
  project package.
"""
    (dst / 'README_PRINT_ORDER.txt').write_text(readme)
    return rows


# ---------------------------------------------------------------------------
# 3  Acrylic face sticker
# ---------------------------------------------------------------------------
PT = 72 / 25.4


def cutline_pdf(loops, path, title, margin=10.0):
    """1:1 vector PDF: cut paths only, stroked in a 'CutContour' spot colour (100 % magenta alternate)."""
    xs = [x for l in loops for x, _ in l]; ys = [y for l in loops for _, y in l]
    x0, y0 = min(xs) - margin, min(ys) - margin
    w, h = max(xs) - min(xs) + 2 * margin, max(ys) - min(ys) + 2 * margin
    ops = ['/CS0 CS 1 SCN 0.25 w 1 j']
    for l in loops:
        pts = [((x - x0) * PT, (h - (y - y0)) * PT) for x, y in l]      # PDF is Y-up; the datum is Y-down
        ops.append(f'{pts[0][0]:.3f} {pts[0][1]:.3f} m ' + ' '.join(f'{px:.3f} {py:.3f} l' for px, py in pts[1:]) + ' h S')
    content = '\n'.join(ops).encode()
    objs = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        (f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w * PT:.3f} {h * PT:.3f}] /TrimBox [0 0 {w * PT:.3f} {h * PT:.3f}] '
         f'/Resources << /ColorSpace << /CS0 5 0 R >> >> /Contents 4 0 R >>').encode(),
        b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream',
        b'[/Separation /CutContour /DeviceCMYK << /FunctionType 2 /Domain [0 1] /C0 [0 0 0 0] /C1 [0 1 0 0] /N 1 >>]',
        f'<< /Title ({title}) /Producer (STRUTHIO build_builder_packs.py) >>'.encode(),
    ]
    out = io.BytesIO()
    out.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(out.tell())
        out.write(f'{i} 0 obj\n'.encode() + o + b'\nendobj\n')
    xref = out.tell()
    out.write(f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode())
    for o in offs:
        out.write(f'{o:010d} 00000 n \n'.encode())
    out.write(f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R /Info 6 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    Path(path).write_bytes(out.getvalue())
    return w, h


def dxf(loops, path):
    q = '0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1015\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n'
    for pts in loops:
        q += '0\nLWPOLYLINE\n100\nAcDbEntity\n8\nCUTLINE\n100\nAcDbPolyline\n90\n' + str(len(pts)) + '\n70\n1\n'
        q += ''.join(f'10\n{x:.5f}\n20\n{-y:.5f}\n' for x, y in pts)
    Path(path).write_text(q + '0\nENDSEC\n0\nEOF\n')


def svg(loops, path, title, desc):
    xs = [x for l in loops for x, _ in l]; ys = [y for l in loops for _, y in l]
    x0, y0, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    d = ' '.join('M ' + ' L '.join(f'{x:.4f},{y:.4f}' for x, y in l) + ' Z' for l in loops)
    Path(path).write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{h:.3f}mm" '
        f'viewBox="{x0:.4f} {y0:.4f} {w:.4f} {h:.4f}">\n<title>{title}</title>\n<desc>{desc}</desc>\n'
        f'<g id="CutContour" fill="none" stroke="#ec008c" stroke-width="0.1"><path d="{d}"/></g>\n</svg>\n')


def check_drawing(path, B, loops, lens_loop):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly, Rectangle
    P = B['P']
    fig = plt.figure(figsize=(210 / 25.4, 297 / 25.4))              # A4 portrait at 1:1
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(-105, 105); ax.set_ylim(297 - 60, -60)
    ax.set_aspect('equal'); ax.axis('off')
    for l in loops:
        ax.add_patch(MPoly(l, closed=True, fill=False, lw=0.8, ec='#ec008c'))
    aw, ah = P['active']
    ax.add_patch(Rectangle((-aw / 2, B['ACTIVE_CY'] - ah / 2), aw, ah, fill=False, lw=0.6, ls='--', ec='#1f5fa8'))
    ax.add_patch(MPoly(lens_loop, closed=True, fill=False, lw=0.4, ls=':', ec='#555'))
    ax.text(0, B['ACTIVE_CY'], 'SCREEN ACTIVE AREA\n58.10 x 103.30\nkeep optically clear:\nno ink, texture or adhesive voids',
            ha='center', va='center', fontsize=7, color='#1f5fa8')
    for x, y in P['flap_centers']:
        ax.text(x, y, 'dia 18.4', ha='center', va='center', fontsize=6)
    ax.text(0, P['dart_cy'], '52.4 x 9.4  r4.6', ha='center', va='center', fontsize=6)
    for sx, _ in B['SPK_CENTERS']:
        ax.text(sx, max(B['GRILLE_YS']) + 2.2, 'vent %.1f x %.1f' % tuple(B['FILM_VENT_SIZE']), ha='center', va='top', fontsize=5.5)
    ax.annotate('', xy=(-52, -4), xytext=(52, -4), arrowprops=dict(arrowstyle='<->', lw=0.5))
    ax.text(0, -5, '104.0', ha='center', va='bottom', fontsize=7)
    ax.annotate('', xy=(56, 0), xytext=(56, 135.3), arrowprops=dict(arrowstyle='<->', lw=0.5))
    ax.text(57, 67.6, '135.3', rotation=-90, va='center', fontsize=7)
    ax.plot([-50, 0], [150, 150], color='k', lw=1.2)
    ax.text(-25, 152, '50 mm - print at 100 % and measure this bar', ha='center', va='top', fontsize=7)
    ax.add_patch(MPoly(list(B['OUTLINE_POLY'].exterior.coords), closed=True, fill=False, lw=0.4, ls='--', ec='#888'))
    ax.text(-100, -55, 'STRUTHIO SLIM4 - FACE FILM R2 - 1:1 CHECK DRAWING (not the cut file)\n'
            'Seen from the FRONT (outer face). Magenta = cut line. Grey dashed = case edge. Blue dashed = screen active area. Dotted = lens.\n'
            'Film edge 0.20 mm inside the case edge. Clear, unprinted: 0.175 mm optical PET + 0.025 mm OCA.', fontsize=7, va='top')
    fig.savefig(path, metadata={'CreationDate': None}); plt.close(fig)


def build_sticker(dst, B):
    P = B['P']
    film = B['FILM_POLY']
    loops = [list(film.exterior.coords)[:-1]] + [list(h.coords)[:-1] for h in film.interiors]
    dst.mkdir(parents=True)
    w, h = cutline_pdf(loops, dst / 'FACE_FILM_CUTLINE_1to1.pdf', 'STRUTHIO SLIM4 face film R2 - cut line 1:1')
    svg(loops, dst / 'FACE_FILM_CUTLINE.svg', 'STRUTHIO SLIM4 face film R2 - cut line',
        'Front view, mm, 1:1. One CutContour path: outline, two flap cut-outs, DART cut-out, two vent windows.')
    dxf(loops, dst / 'FACE_FILM_CUTLINE.dxf')
    lens = B['rrect'](0, B['ACTIVE_CY'], P['lens'][0], P['lens'][1], P['lens_r'], 16)
    lens_loop = list(lens.exterior.coords)[:-1]
    check_drawing(dst / 'FACE_FILM_CHECK_DRAWING_A4.pdf', B, loops, lens_loop)

    # Cover-glass lens (a separate supplier: display cover-glass maker).
    ld = dst / 'LENS_COVER_GLASS_0.7MM'
    ld.mkdir()
    cutline_pdf([lens_loop], ld / 'LENS_CUTLINE_1to1.pdf', 'STRUTHIO SLIM4 cover glass - outline 1:1')
    svg([lens_loop], ld / 'LENS_CUTLINE.svg', 'STRUTHIO SLIM4 cover glass', '59.2 x 104.4 mm, corner radius 2.5, 0.70 mm glass.')
    dxf([lens_loop], ld / 'LENS_CUTLINE.dxf')
    (ld / 'README_LENS.txt').write_text(f"""COVER-GLASS LENS - send to a display cover-glass supplier (not the sticker printer)
=================================================================================
Rigid window over the LCD, held by the display tape frame and the face film (DECISIONS_R26.md).
  Size        {P['lens'][0]:g} x {P['lens'][1]:g} mm, corner radius {P['lens_r']:g} mm (rebate {P['lens_rebate'][0]:g} x {P['lens_rebate'][1]:g}: 0.1 mm per side)
  Thickness   {P['lens'][2]:.2f} mm (equal to the rebate depth: the top sits flush with the case face)
  Material    chemically strengthened soda-lime cover glass, clear, both faces polished
  Edges       CNC cut, edges ground and chamfered 0.1 mm; no AR or AF coating; no print
  Tolerance   outline +0 / -0.10 mm; thickness 0.70 ±0.05 mm
  Quantity    1 per device, plus 2 spares
""")

    # Die-cut double-sided tapes (the sticker printer kiss-cuts these on liner).
    td = dst / 'TAPE_DIE_CUTS'
    td.mkdir()
    lcd_w, lcd_h, _ = P['lcd']
    lcd_cy = P['lcd_top_y'] + lcd_h / 2
    ww, wh = B['TAPE_WINDOW']
    rect = lambda cx, cy, a, b: [(cx - a / 2, cy - b / 2), (cx + a / 2, cy - b / 2), (cx + a / 2, cy + b / 2), (cx - a / 2, cy + b / 2)]
    frame = [rect(0, lcd_cy, lcd_w, lcd_h), rect(0, B['ACTIVE_CY'], ww, wh)]
    ring = B['LAP_TAPE']
    ring_loops = [list(ring.exterior.coords)[:-1]] + [list(i.coords)[:-1] for i in ring.interiors]
    for name, lp, title in (('DISPLAY_TAPE_FRAME', frame, 'display tape frame'), ('LAP_TAPE_RING', ring_loops, 'lap tape ring')):
        cutline_pdf(lp, td / f'{name}_1to1.pdf', f'STRUTHIO SLIM4 {title} - cut line 1:1')
        svg(lp, td / f'{name}.svg', f'STRUTHIO SLIM4 {title}', 'Front view, mm, 1:1, 0.10 mm double-sided tape.')
        dxf(lp, td / f'{name}.dxf')
    rw = P['wall'] / 2 - P['lap_clear'] / 2 - 0.1
    (td / 'README_TAPES.txt').write_text(f"""TAPE DIE-CUTS - kiss-cut on liner, same supplier as the face film
================================================================
Material for both: 0.10 mm total double-sided tape, clear PET carrier with permanent acrylic
adhesive on both faces (no foam), supplied on a liner with a pull tab.

DISPLAY_TAPE_FRAME   outer {lcd_w:g} x {lcd_h:g} mm (the LCD module outline), window {ww:.3f} x {wh:.3f} mm
                     (the active area + 0.05 mm per side), window offset to the active area.
                     Laid on the module front: bonds the module to the case ledge and carries the
                     0.5 mm lens border. 1 per device.
LAP_TAPE_RING        {rw:.2f} mm wide ring following the shell joint. Laid on the rear-shell lip top:
                     bonds the two shells (the joint has no screws). 1 per device; it can be peeled
                     to open the case. Order 3 per device for rework.
Views are from the FRONT. Tolerance ±0.1 mm.
""")

    sp = P
    readme = f"""STRUTHIO SLIM4 - FACE FILM R2 - FILES FOR THE STICKER PRINTER
=============================================================

STATUS: ON HOLD with the case (package R31). Clear, UNPRINTED film (decided in DECISIONS_R26.md):
no ink, no white, no texture. The R2 line and the lens follow CASE R12, which does not fit the
R23-R26 board's 5 in panel; the case pass (CASE R13) redraws them. Do not order yet.

WHAT IT IS
  A clear face film that covers the whole front of the device, including the screen.
  Shape: {B['FILM_OUTLINE'].bounds[2] - B['FILM_OUTLINE'].bounds[0]:.1f} x {B['FILM_OUTLINE'].bounds[3] - B['FILM_OUTLINE'].bounds[1]:.1f} mm: the case outline set in {sp['film_edge_inset']:.2f} mm all round.
  Cut-outs: two dia {sp['bezel_od'] + 2 * sp['film_clear']:g} mm holes (flap buttons), one {sp['dart_surround'][0] + 2 * sp['film_clear']:g} x {sp['dart_surround'][1] + 2 * sp['film_clear']:g} mm slot r{sp['dart_surround_r'] + sp['film_clear']:g}
  (DART button), two {B['FILM_VENT_SIZE'][0]:.1f} x {B['FILM_VENT_SIZE'][1]:.1f} mm vent windows r{sp['film_vent_r']:g} over the speaker grilles.
  Narrowest cut feature {B['FILM_VENT_SIZE'][1]:.1f} mm. No screen window: the film runs over the screen.

FILES
  FACE_FILM_CUTLINE_1to1.pdf   cut file: one vector path in the spot colour "CutContour",
                               page {w:.1f} x {h:.1f} mm, 1:1 (10 mm margin round the part)
  FACE_FILM_CUTLINE.svg / .dxf the same path (mm, front view; SVG stroke magenta, DXF layer CUTLINE)
  FACE_FILM_CHECK_DRAWING_A4.pdf  dimensions, case edge, screen zone and a 50 mm scale bar;
                               print at 100 % and lay it on the printed case to check the outline
  TAPE_DIE_CUTS/               two 0.10 mm double-sided tape parts (see README_TAPES.txt)
  LENS_COVER_GLASS_0.7MM/      the glass lens - a separate supplier (see README_LENS.txt)

SPECIFICATION (specified)
  Stack         {' + '.join(f'{t:.3f} mm {n}' for n, t in sp['film_stack'])} = {sp['film_t']:.2f} mm
                (the thickness the case is designed for). Optically clear, low haze, gloss.
  Over the screen  no texture and no bubbles inside the active area (laminate bubble-free).
  Cut           kiss-cut on liner along the CutContour path, as seen from the FRONT.
  Tolerance     outline ±0.2 mm is acceptable: the edge is set in 0.20 mm from the case edge.
  Quantity      5 films per device (fit tests and rework).

APPLYING
  Last step of assembly, after the buttons are checked (ASSEMBLY_SEQUENCE.md step 9). Register
  the two round cut-outs and the DART slot on the raised rings of the front shell, then
  lay the film down from the centre outwards.
"""
    (dst / 'README_STICKER_ORDER.txt').write_text(readme)
    return loops, (w, h)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = Path(sys.argv[1]).resolve()
    if out == ROOT or ROOT in out.parents:
        sys.exit('write the builder files outside the package folder')
    top = out / TOP
    if top.exists():
        shutil.rmtree(top)
    pcb_facts, parts, no_lcsc = build_pcb(top / '1_PCB_FABRICATION')
    B = runpy.run_path(str(ROOT / 'LAYERS/02_CASE/build_r12.py'))
    prints = build_print(top / '2_3D_PRINTING', B)
    build_sticker(top / '3_ACRYLIC_STICKER', B)
    report = json.loads((ROOT / 'CHECKS/R31_CONVERGENCE_REPORT.json').read_text())
    c = report['counts']
    conv = f"{c.get('FAIL', 0)} FAIL, {c.get('PASS', 0)} PASS, {c.get('GATE', 0)} GATE"
    (top / 'README.txt').write_text(f"""STRUTHIO SLIM4 R31 - FILES FOR THE BUILDERS
===========================================

1_PCB_FABRICATION   JLCPCB PCB + assembly: PCB R26, {pcb_facts['copper_layers']} layers, {pcb_facts['thickness']:g} mm, {len(parts)} parts,
                    5 boards, 2 assembled. READY, except U1 (ESP32-P4NRW32X): no JLCPCB stock on
                    2026-10-07 - pre-order or consign it (see its README).
                    The assembled board takes four plug-in parts, no soldering: the Crystalfontz
                    CFAF7201280A0-050TN display (its own tail into J1), a protected 1-cell pack of
                    1000 mAh or more on JST PH (J3)
                    and two speakers on Molex PicoBlade (J4, J5). Details in its README.
2_3D_PRINTING       ON HOLD: CASE R12, set aside by the owner for R23-R26 (it does not fit the 5 in panel).
3_ACRYLIC_STICKER   ON HOLD with the case: face film R2, tape die-cuts and the cover-glass lens.

Order of work: the board and the four plug-in parts; flash the firmware (firmware/slim4 in the
repository) and bring the board up on the bench; then the case pass for the R26 board and panel.

PROJECT_DOCS        the package documents the READMEs refer to: PRODUCTION_GATES.md (what to order,
                    then, and in the case pass), RELEASE_GATES.md (the board's closed and open gates),
                    ASSEMBLY_SEQUENCE.md, R31_CONVERGENCE_REPORT.md and BOM_SOURCING_R21.json.

Generated from the R31 project package (PCB R26, CASE R12, ACRYLIC R2; convergence check {conv})
by CHECKS/build_builder_packs.py. The generator, the checks and the firmware are in the repository
(hardware/slim4/CHECKS, firmware/slim4); they are not needed to place the orders.
""")
    docs = top / 'PROJECT_DOCS'
    docs.mkdir()
    for rel in ('PRODUCTION_GATES.md', 'LAYERS/01_PCB/RELEASE_GATES.md', 'ASSEMBLY/ASSEMBLY_SEQUENCE.md',
                'CHECKS/R31_CONVERGENCE_REPORT.md', 'CHECKS/BOM_SOURCING_R21.json'):
        shutil.copy2(ROOT / rel, docs / Path(rel).name)
    zip_dir(top, out / f'{TOP}.zip', prefix=f'{TOP}/')
    files = sorted(p for p in top.rglob('*') if p.is_file())
    print(f'{len(files)} files, {sum(p.stat().st_size for p in files):,} bytes -> {out / (TOP + ".zip")} '
          f'({(out / (TOP + ".zip")).stat().st_size:,} bytes)')
    for r in prints:
        print(f"  {r['name']:18} {r['tris']:7} triangles  {'closed' if r['closed'] else 'OPEN'}")


if __name__ == '__main__':
    main()
