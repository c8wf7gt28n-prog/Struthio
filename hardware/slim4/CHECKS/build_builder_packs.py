#!/usr/bin/env python3
"""Build the files to send to the three builders, from this package.

    python -B CHECKS/build_builder_packs.py <output folder>

Writes <output folder>/STRUTHIO_SLIM4_R25_BUILDER_FILES/ and a zip of it:
  1_PCB_FABRICATION/   Gerber + drill zip, BOM, placement (CPL), assembly drawings, KiCad source
  2_3D_PRINTING/       one STL and one STEP per printed part, renders
  3_ACRYLIC_STICKER/   face-film die line (PDF with a CutContour spot colour, SVG, DXF),
                       a 1:1 check drawing, and the optional 0.7 mm lens outline

Needs KiCad 7.0.x (kicad-cli on PATH and a python3 that can import pcbnew) and the pinned
CadQuery environment (requirements.txt). Nothing in the package is changed: the PCB files are
plotted from a temporary copy of LAYERS/01_PCB (its SHA-256 is checked before and after), and
the printed parts and film are rebuilt from LAYERS/02_CASE/build_r11.py.
"""
from pathlib import Path
import csv, hashlib, io, json, math, re, runpy, shutil, subprocess, sys, tempfile, zipfile
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
PCB_DIR = ROOT / 'LAYERS/01_PCB'
BOARD = 'SLIM4_R21.kicad_pcb'
TOP = 'STRUTHIO_SLIM4_R25_BUILDER_FILES'
STAMP = (2026, 10, 7, 0, 0, 0)
STEP_STAMP = '2026-10-07T00:00:00'
GERBER_LAYERS = 'F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts'

# Printed parts: output name, CAD part name prefix, quantity per device, what to look after.
PRINTED = [
    ('01_FRONT_SHELL', 'FRONT SHELL R11', 1,
     'Plate 2.0 mm, only 0.70 mm over the LCD pocket ledge; 0.8 mm grille slots; lens rebate 59.4 x 104.6 (lens 59.2 x 104.4); '
     'flap holes 17.0; DART opening 50 x 7 with two 2.0 x 1.4 pivot bosses (1.0 mm trunnion, 0.05 mm radial clearance); front clamp posts 2.0.'),
    ('02_REAR_SHELL', 'REAR SHELL R11', 1,
     'Floor and walls 2.0 mm; 1.0 mm lap lip; speaker chambers with ledges; board supports 2.4; power-plunger bore 2.8; '
     'RESET/BOOT pinholes 1.2; USB-C relief.'),
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
           'FH12-20S-0.5SH(55)': 'FPC 20P 0.5 mm bottom-contact ZIF', 'USB4105-GF-A-120': 'USB-C receptacle', 'D2LS-11': 'Omron D2LS SMD',
           'D2LS-21(20M)': 'Omron D2LS SMD', 'ASWPA4035S2R2MT': 'Power inductor 4035'}
RENDERS = ['VIEW_EXPLODED.png', 'VIEW_FRONT_ISO.png', 'VIEW_REAR_ISO.png', 'VIEW_INTERNALS.png']


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
PCBNEW_PROBE = r'''
import json, collections, pcbnew
b = pcbnew.LoadBoard("SLIM4_R21.kicad_pcb")
mm = pcbnew.ToMM
def fills(b):
    return [sum(z.GetFilledPolysList(l).Area() for l in z.GetLayerSet().Seq()) for z in b.Zones()]
stored = fills(b)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
fresh = fills(b)
b = pcbnew.LoadBoard("SLIM4_R21.kicad_pcb")
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
slots = sorted({(fp.GetReference(), round(mm(p.GetDrillSize().x), 2), round(mm(p.GetDrillSize().y), 2), p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)
                for fp in b.GetFootprints() for p in fp.Pads() if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)})
bb = b.GetBoardEdgesBoundingBox()
ds = b.GetDesignSettings()
print(json.dumps({
    "version": pcbnew.Version(),
    "fills_current": max(abs(a - c) for a, c in zip(stored, fresh)) / 1e12 < 1e-6,
    "copper_layers": b.GetCopperLayerCount(),
    "thickness": mm(ds.GetBoardThickness()),
    "outline": [round(mm(bb.GetWidth()), 2), round(mm(bb.GetHeight()), 2)],
    "track_widths": sorted({round(mm(t.GetWidth()), 3) for t in segs}),
    "min_clearance": mm(ds.m_MinClearance),
    "vias": sorted({(round(mm(v.GetWidth()), 3), round(mm(v.GetDrillValue()), 3)) for v in vias}),
    "via_count": len(vias),
    "blind_or_micro_vias": sum(v.GetViaType() != pcbnew.VIATYPE_THROUGH for v in vias),
    "vias_in_smd_pads": inpad,
    "footprint_holes": slots,
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
        rows.append(dict(ref=g(r'\(fp_text reference "([^"]+)"'), value=value, mpn='' if re.match(r'\d{4} ', value) else value,
                         layer=g(r'\(layer "([^"]+)"\)'), lcsc=jlc[1] if jlc else '', descr=descr, pkg=pkg))
    return rows


def natural(ref):
    m = re.match(r'([A-Z]+)(\d+)', ref)
    return (m[1], int(m[2])) if m else (ref, 0)


def assembly_drawing(B_side, path, parts, outline):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Polygon as MPoly
    from matplotlib.transforms import Affine2D
    fig = plt.figure(figsize=(297 / 25.4, 420 / 25.4))           # A3 portrait, board at 2:1
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(-74.25, 74.25); ax.set_ylim(169, -41)
    ax.set_aspect('equal'); ax.axis('off')
    sx = -1 if B_side else 1                                       # back side drawn as seen from the back
    ax.add_patch(MPoly([(sx * x, y) for x, y in outline['outer']], closed=True, fill=False, lw=0.6, ec='k'))
    for h in outline.get('holes', []):
        ax.add_patch(MPoly([(sx * x, y) for x, y in h], closed=True, fill=False, lw=0.6, ec='k'))
    side = 'back' if B_side else 'front'
    n = 0
    for p in parts:
        if p['side'] != side:
            continue
        n += 1
        r = Rectangle((-p['w'] / 2, -p['h'] / 2), p['w'], p['h'], fill=False, lw=0.3, ec='#1f5fa8')
        r.set_transform(Affine2D().rotate_deg(-sx * p['rot']).translate(sx * p['x'], p['y']) + ax.transData)
        ax.add_patch(r)
        fs = max(2.2, min(6.0, 1.6 * min(p['w'], p['h'])))
        ax.text(sx * p['x'], p['y'], p['ref'], ha='center', va='center', fontsize=fs, color='#b0201a')
    ax.text(-72, 150, f'STRUTHIO SLIM4 R21 - {side.upper()} SIDE ({n} parts), seen from the {side}. Scale 2:1 on A3. '
            'Outlines are part envelopes; the CPL file is the placement authority.', fontsize=6.5, va='top')
    fig.savefig(path, metadata={'CreationDate': None}); plt.close(fig)


def build_pcb(dst):
    src_sha = sha(PCB_DIR / BOARD)
    ver = run(['kicad-cli', 'version']).strip()
    if not ver.startswith('7.'):
        sys.exit(f'kicad-cli {ver}: this board is KiCad 7 format; use KiCad 7.0.x so the plot matches the source')
    tmp = Path(tempfile.mkdtemp())
    try:
        work = tmp / 'pcb'
        shutil.copytree(PCB_DIR, work)
        g = tmp / 'gerber'
        g.mkdir()
        run(['kicad-cli', 'pcb', 'export', 'gerbers', '--layers', GERBER_LAYERS, '--subtract-soldermask', '--exclude-value',
             '-o', str(g) + '/', BOARD], cwd=work)
        run(['kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th', '--excellon-units', 'mm',
             '--generate-map', '--map-format', 'pdf', '-o', str(g) + '/', BOARD], cwd=work)
        run(['kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
             '-o', str(tmp / 'pos.csv'), BOARD], cwd=work)
        facts = json.loads(run([pcbnew_python(), '-c', PCBNEW_PROBE], cwd=work).strip().splitlines()[-1])
        drc = (work / 'DRC.rpt').read_text()

        for f in g.iterdir():
            pin_dates(f)
        dst.mkdir(parents=True)
        ref = dst / 'REFERENCE'
        ref.mkdir()
        for m in sorted(g.glob('*.pdf')):
            shutil.move(str(m), ref / m.name)
        zip_dir(g, dst / 'SLIM4_R21_GERBER_DRILL.zip')
        (ref / 'DRC_REPORT_KICAD7.txt').write_text(re.sub(r'\*\* Created on .*\*\*\n', '', drc))

        text = (work / BOARD).read_text()
        parts = board_parts(text)
        groups = {}
        for p in parts:
            groups.setdefault((p['value'], p['mpn'], p['lcsc'], p['pkg'], p['layer']), []).append(p['ref'])
        with open(dst / 'SLIM4_R21_BOM.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #', 'Manufacturer Part #', 'Quantity', 'Side', 'Note'])
            for (val, mpn, lcsc, pkg, layer), refs in sorted(groups.items(), key=lambda kv: natural(sorted(kv[1], key=natural)[0])):
                refs = sorted(refs, key=natural)
                descr = next(p['descr'] for p in parts if p['ref'] == refs[0])
                note = ('' if lcsc else 'part not bound yet: confirm before ordering' if 'BIND_BEFORE_FAB' in descr
                        else 'no LCSC number recorded: source by manufacturer part number')
                w.writerow([val, ','.join(refs), pkg, lcsc, mpn, len(refs), 'Top' if layer == 'F.Cu' else 'Bottom', note])
        with open(tmp / 'pos.csv') as f, open(dst / 'SLIM4_R21_CPL.csv', 'w', newline='') as o:
            w = csv.writer(o)
            w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
            rows = sorted(csv.DictReader(f), key=lambda r: natural(r['Ref']))
            for r in rows:
                w.writerow([r['Ref'], f"{float(r['PosX']):.4f}mm", f"{float(r['PosY']):.4f}mm",
                            'Top' if r['Side'] == 'top' else 'Bottom', f"{float(r['Rot']):g}"])
        cpl_count = len(rows)

        layer_json = json.loads((work / 'SLIM4_R21_PCB_LAYER.json').read_text())
        assembly_drawing(True, ref / 'ASSEMBLY_DRAWING_BACK_SIDE.pdf', layer_json['parts'], layer_json['board'])
        assembly_drawing(False, ref / 'ASSEMBLY_DRAWING_FRONT_SIDE.pdf', layer_json['parts'], layer_json['board'])

        srcdir = dst / 'KICAD_SOURCE'
        srcdir.mkdir()
        for f in [BOARD, 'SLIM4_R21.kicad_pro', 'fp-lib-table']:
            shutil.copy2(PCB_DIR / f, srcdir / f)
        shutil.copytree(PCB_DIR / 'SLIM4.pretty', srcdir / 'SLIM4.pretty')
        shutil.copy2(PCB_DIR / 'RELEASE_GATES.md', ref / 'RELEASE_GATES_R21.md')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if sha(PCB_DIR / BOARD) != src_sha:
        sys.exit('the R21 board changed during the build: stop')

    win = layer_json['board']['holes'][0]
    window = (max(x for x, _ in win) - min(x for x, _ in win), max(y for _, y in win) - min(y for _, y in win))
    proxies = sum('package proxy' in p['descr'] for p in parts)
    vendor_land = [p['ref'] for p in sorted(parts, key=lambda p: natural(p['ref'])) if 'package proxy' not in p['descr']]
    no_lcsc = [(p['ref'], p['value']) for p in sorted(parts, key=lambda p: natural(p['ref'])) if not p['lcsc']]
    sides = {s: sum(1 for p in parts if (p['layer'] == 'F.Cu') == (s == 'Top')) for s in ('Top', 'Bottom')}
    drc_line = ' / '.join(l.strip('* ') for l in drc.splitlines() if l.startswith('** Found'))
    vias = ', '.join(f'{d:g} mm drill / {s:g} mm pad' for s, d in facts['vias'])
    slots = [h for h in facts['footprint_holes'] if h[1] != h[2]]
    npth = sorted({(h[0][:2] if h[0].startswith('SW') else h[0], h[1]) for h in facts['footprint_holes'] if not h[3]})
    readme = f"""STRUTHIO SLIM4 - PCB R21 - FILES FOR THE BOARD HOUSE / ASSEMBLER
=================================================================

STATUS: PROTOTYPE / ENGINEERING BUILD ONLY. The R21 board is a routing checkpoint that its
own release note marks "not for fabrication or assembly" until the gates in
REFERENCE/RELEASE_GATES_R21.md are closed (schematic/ERC review, power and high-speed
review, final part selection). These files are complete for quoting and for a prototype
order; ordering before those gates close is the owner's decision.

UPLOAD
  SLIM4_R21_GERBER_DRILL.zip   Gerber X2 (13 layers), Excellon drill (PTH and NPTH separate), job file
  SLIM4_R21_BOM.csv            bill of materials, one line per part type (LCSC numbers where recorded)
  SLIM4_R21_CPL.csv            placement: designator, centre X/Y (mm), side, rotation

BOARD SPECIFICATION (read from the board file)
  Layers                 {facts['copper_layers']} copper: F.Cu, In1 (GND plane), In2 (power planes), In3 (signal), In4 (GND plane), B.Cu
  Thickness              {facts['thickness']:g} mm  - REQUIRED: the enclosure is designed around 1.2 mm
  Size                   {facts['outline'][0]:g} x {facts['outline'][1]:g} mm, non-rectangular outline with an internal
                         {window[0]:g} x {window[1]:g} mm battery window (routed cut-out, see Edge_Cuts)
  Stackup                not defined in the design: use the board house's standard 6-layer 1.2 mm stackup
  Copper weight          not specified: 1 oz outer / 0.5 oz inner assumed
  Min track / space      {min(facts['track_widths']):g} mm / {facts['min_clearance']:g} mm (track widths used: {', '.join(f'{w:g}' for w in facts['track_widths'])} mm)
  Vias                   {facts['via_count']} through vias, {vias}; no blind or buried vias
  Via covering           all vias TENTED (solder mask over vias). Required: two vias sit under
                         case contact points (SW2 cap stop leg at 35.69, 107.06 and a rear support
                         post at 21.5, 76.0).
  Vias in pads           {len(facts['vias_in_smd_pads'])}: {', '.join(f'{r} pad {n}' for r, n, _ in facts['vias_in_smd_pads'])} - ask for via-in-pad filled and capped
                         (resin plugged, plated over), or accept solder wicking on those two pads
  Plated slots           {', '.join(f'{r} {a:g} x {b:g} mm' for r, a, b, _ in slots)} (USB-C shell legs)
  Non-plated holes       {', '.join(f'{r} dia {d:g} mm' for r, d in npth)} (switch bosses / USB-C pegs)
  Surface finish         ENIG recommended (0.35 mm-pitch ESP32-P4, QFN/WSON parts need flat pads)
  Solder mask / silk     colour free choice; back-side silkscreen carries outlines
  Impedance control      required for MIPI-DSI (100 ohm differential) and USB 2.0 (90 ohm
                         differential) in principle, but the traces were not sized to a fab
                         stackup yet (release gate 3). For a prototype, order without impedance
                         control or ask the board house to calculate it for their stackup.

ASSEMBLY
  Parts                  {len(parts)} placements: {sides['Bottom']} on the BACK (B.Cu) and {sides['Top']} on the FRONT (F.Cu: the four
                         Omron D2LS switches SW1-SW4, which the case controls press)
                         Two-sided assembly. The four D2LS switches can also be hand-soldered.
  CPL                    {cpl_count} lines. Rotations are KiCad's; check every IC, diode,
                         connector and polarised part in the assembler's placement preview and
                         correct rotations there (assembler footprint libraries use different
                         zero orientations).
  Parts without an LCSC number ({len(no_lcsc)}) - source by manufacturer part number or supply them:
{chr(10).join(f'    {r:6} {v}' for r, v in no_lcsc)}
  C310 (CL05B224KO5NNNC) is marked "bind before fab": confirm the 220 nF part before ordering.
  Land patterns: {proxies} of the {len(parts)} footprints - every part except {', '.join(vendor_land)}, which
  follow vendor land patterns - are marked in the board as "package proxy; exact land-pattern
  audit remains a fab gate". Ask the assembler's DFM review to check those pads against the
  parts in the BOM.
  Not on the board, supplied separately: LCD module + FPC, battery, speakers (see the case pack).

CHECKS RUN ON THESE FILES
  KiCad {facts['version']} DRC: {drc_line}  (REFERENCE/DRC_REPORT_KICAD7.txt)
  Zone fills in the board file are current: {'yes' if facts['fills_current'] else 'NO - refill before plotting'}
  Board: {facts['footprints']} footprints, {facts['nets']} nets, {facts['segments']} track segments, {facts['via_count']} vias
  DRC uses the design's own rules (0.1 mm); run the board house's DFM check as well.

REFERENCE/   assembly drawings (both sides, 2:1 on A3), drill maps, DRC report, R21 release gates
KICAD_SOURCE/ native KiCad 7 board, project and local footprint library (unchanged R21 source)
"""
    (dst / 'README_PCB_ORDER.txt').write_text(readme)
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
    readme = f"""STRUTHIO SLIM4 - CASE R11 - FILES FOR THE 3D PRINT SERVICE
==========================================================

STATUS: first fit prototype of a converged CAD candidate, not a tooling release. Print one
set, assemble it on a real R21 board, then check fit, button feel and the plain 1.0 mm lap
joint between the shells (no snap or screw is modelled yet).

ORDER (per device)
  Part               Qty  Size X x Y x Z (mm)        Volume       Mesh
{table}
  Recommended extras: 2 more of each control (03-06). They are small, and the stop legs and
  trunnions are tuned on the first print (production gates D5, D11, D12).

FILES
  STL/    one binary STL per part, 0.01 mm chord tolerance; every mesh checked closed (watertight)
  STEP/   the same parts as exact solids (use these if the service accepts STEP)
  REFERENCE/  renders of the assembled case, for orientation only
  Units are millimetres. Parts are in their assembled position (front of the device = +Z),
  so the six files overlay each other in any viewer; orient them freely for printing.

PROCESS (recommendation - confirm with the service)
  SLA / resin, a tough or ABS-like engineering resin, 0.05 mm layers or finer, for all parts.
  The design has features close to the limits of most processes: a 0.70 mm ledge, 0.8 mm
  grille slots, 1.0 mm trunnion pins, 1.2 mm stop legs and pinholes, 1.4 mm actuator nubs,
  0.05-0.2 mm running clearances. MJF/SLS nylon is a possible alternative for the two shells
  if the service confirms the 0.70 mm ledge and 0.8 mm slots. FDM is not suitable.
  Do not scale or add shrink compensation beyond the service's normal calibration.
  Keep support marks off: the outer side walls and the raised bezel rings and DART surround
  of 01, the outer back and walls of 02, and the top faces of 03-05. The flat front of 01
  is covered by the face film.

FEATURES TO PROTECT
{notes}

AFTER PRINTING
  Supplied separately, not printed: LCD module and its 0.7 mm lens (lens outline is in the
  acrylic pack), battery and 0.2 mm foam pad, two Same Sky CMS-18138A-SP speakers and 0.25 mm
  gaskets, FPC extension, harnesses. Assembly order: ASSEMBLY/ASSEMBLY_SEQUENCE.md in the
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
        ax.text(sx, max(B['GRILLE_YS']) + 2.2, '6 slots 12.2 x 1.0', ha='center', va='top', fontsize=5.5)
    ax.annotate('', xy=(-52, -4), xytext=(52, -4), arrowprops=dict(arrowstyle='<->', lw=0.5))
    ax.text(0, -5, '104.0', ha='center', va='bottom', fontsize=7)
    ax.annotate('', xy=(56, 0), xytext=(56, 135.3), arrowprops=dict(arrowstyle='<->', lw=0.5))
    ax.text(57, 67.6, '135.3', rotation=-90, va='center', fontsize=7)
    ax.plot([-50, 0], [150, 150], color='k', lw=1.2)
    ax.text(-25, 152, '50 mm - print at 100 % and measure this bar', ha='center', va='top', fontsize=7)
    ax.text(-100, -55, 'STRUTHIO SLIM4 - ACRYLIC FACE FILM R1 - 1:1 CHECK DRAWING (not the cut file)\n'
            'Seen from the FRONT (outer face). Magenta = cut line. Blue dashed = screen active area. Dotted = 0.7 mm lens under the film.\n'
            'Outline equals the case outline: the film edge meets the case edge with no margin.', fontsize=7, va='top')
    fig.savefig(path, metadata={'CreationDate': None}); plt.close(fig)


def build_sticker(dst, B):
    P = B['P']
    film = B['FILM_POLY']
    loops = [list(film.exterior.coords)[:-1]] + [list(h.coords)[:-1] for h in film.interiors]
    dst.mkdir(parents=True)
    w, h = cutline_pdf(loops, dst / 'FACE_FILM_CUTLINE_1to1.pdf', 'STRUTHIO SLIM4 face film R1 - cut line 1:1')
    svg(loops, dst / 'FACE_FILM_CUTLINE.svg', 'STRUTHIO SLIM4 face film R1 - cut line',
        'Front view, mm, 1:1. One CutContour path: outline, two flap cut-outs, DART cut-out, six vent slots.')
    dxf(loops, dst / 'FACE_FILM_CUTLINE.dxf')
    lens = B['rrect'](0, B['ACTIVE_CY'], P['lens'][0], P['lens'][1], P['lens_r'], 16)
    lens_loop = list(lens.exterior.coords)[:-1]
    check_drawing(dst / 'FACE_FILM_CHECK_DRAWING_A4.pdf', B, loops, lens_loop)
    ld = dst / 'OPTIONAL_LENS_0.7MM'
    ld.mkdir()
    cutline_pdf([lens_loop], ld / 'LENS_CUTLINE_1to1.pdf', 'STRUTHIO SLIM4 protective lens - cut line 1:1')
    svg([lens_loop], ld / 'LENS_CUTLINE.svg', 'STRUTHIO SLIM4 protective lens', '59.2 x 104.4 mm, corner radius 2.5, 0.70 mm clear sheet.')
    dxf([lens_loop], ld / 'LENS_CUTLINE.dxf')
    (ld / 'README_LENS.txt').write_text(f"""PROTECTIVE LENS - optional item for a shop that laser-cuts clear sheet
=====================================================================
Rigid clear window bonded into the front-shell rebate over the LCD, under the face film.
  Size        {P['lens'][0]:g} x {P['lens'][1]:g} mm, corner radius {P['lens_r']:g} mm (rebate {P['lens_rebate'][0]:g} x {P['lens_rebate'][1]:g}: 0.1 mm per side)
  Thickness   {P['lens'][2]:g} mm (the rebate depth; thicker sheet will stand proud of the face)
  Material    not chosen: clear cast acrylic (PMMA) or polycarbonate, optical grade, both
              faces masked; or 0.7 mm cover glass from a display supplier
  Quantity    1 per device
  Cut outline tolerance +0/-0.1 mm if the shop can hold it.
If the sticker printer cannot cut rigid sheet, send this folder to a laser-cutting shop.
""")
    sp = P
    readme = f"""STRUTHIO SLIM4 - ACRYLIC FACE FILM R1 - FILES FOR THE STICKER PRINTER
=====================================================================

STATUS: cut line ready for a test cut; PRINT ARTWORK NOT DESIGNED YET. Order a few blank
clear die-cut films now to check fit on the printed case. Printed artwork (ink, white
backing, texture) is added only after the visible design is approved; it must keep the screen
area clear.

WHAT IT IS
  A clear face film that covers the whole front of the device, including the screen.
  Shape: {B['OUTLINE_POLY'].bounds[2] - B['OUTLINE_POLY'].bounds[0]:.1f} x {B['OUTLINE_POLY'].bounds[3] - B['OUTLINE_POLY'].bounds[1]:.1f} mm, the exact outline of the case front.
  Cut-outs: two dia {sp['bezel_od'] + 2 * sp['film_clear']:g} mm holes (flap buttons), one {sp['dart_surround'][0] + 2 * sp['film_clear']:g} x {sp['dart_surround'][1] + 2 * sp['film_clear']:g} mm slot r{sp['dart_surround_r'] + sp['film_clear']:g}
  (DART button), six {sp['grille_slot'][0] + 0.2:.1f} x {sp['grille_slot'][1] + 0.2:.1f} mm vent slots over the speaker grilles. No screen
  window: the film runs continuously over the screen.

FILES
  FACE_FILM_CUTLINE_1to1.pdf   cut file: one vector path in the spot colour "CutContour",
                               page {w:.1f} x {h:.1f} mm, 1:1 (10 mm margin round the part)
  FACE_FILM_CUTLINE.svg / .dxf the same path (mm, front view; SVG stroke magenta, DXF layer CUTLINE)
  FACE_FILM_CHECK_DRAWING_A4.pdf  dimensions, screen keep-clear zone and a 50 mm scale bar;
                               print at 100 % and lay it on the printed case to check the outline
  OPTIONAL_LENS_0.7MM/         the rigid lens under the film (a separate item - see its README)

SPECIFICATION (recommendation - confirm with the printer)
  Material      clear film, {sp['film_t']:g} mm total including adhesive is the design assumption
                (the case allows for it; production gate E7). Optically clear, low haze, gloss;
                PET or polycarbonate face film with permanent optically clear adhesive.
                ("Acrylic" is the project's name for this layer; any clear film that meets
                the thickness and optics works.)
  Over the screen  no texture, no ink, no adhesive pattern or bubbles inside the active area.
  Cut           die-cut or kiss-cut on liner, along the CutContour path, as seen from the FRONT.
                If the artwork is later reverse-printed on the adhesive side, the printer
                mirrors the artwork, not the cut line's physical shape.
  Tolerance     the outline equals the case edge with no margin, so the cut must hold about
                +/-0.1 mm. If the printer cannot, ask for their tolerance: the outline will be
                inset by that amount in the next revision (an owner decision; it is not
                changed here).
  Small features  the six vent slots are only 1.0 mm wide (12.2 mm long). Many sticker cutters
                cannot cut slots that narrow cleanly; ask before ordering. Film left over the
                grille would muffle the speakers, so if the slots cannot be cut the vent
                cut-outs need redesigning (an owner decision) - do not just leave them out.
  Quantity      test cut: 3-5 blank films per device built.

APPLYING
  Last step of assembly, after the buttons are checked (ASSEMBLY_SEQUENCE.md step 8). Register
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
    B = runpy.run_path(str(ROOT / 'LAYERS/02_CASE/build_r11.py'))
    prints = build_print(top / '2_3D_PRINTING', B)
    build_sticker(top / '3_ACRYLIC_STICKER', B)
    report = json.loads((ROOT / 'CHECKS/R25_CONVERGENCE_REPORT.json').read_text())
    c = report['counts']
    conv = f"{c.get('FAIL', 0)} FAIL, {c.get('PASS', 0)} PASS, {c.get('GATE', 0)} GATE"
    (top / 'README.txt').write_text(f"""STRUTHIO SLIM4 R25 - FILES FOR THE BUILDERS
===========================================

Three folders, one per supplier. Each has a README_..._ORDER.txt to send with the files.

1_PCB_FABRICATION   board house / assembler: PCB R21, {pcb_facts['copper_layers']} layers, {pcb_facts['thickness']:g} mm, {len(parts)} parts
                    PROTOTYPE ONLY: R21 is not released for fabrication (see its README).
2_3D_PRINTING       print service: front shell, rear shell, two flap caps, DART rocker,
                    power plunger (CASE R11)
3_ACRYLIC_STICKER   sticker printer: clear face film R1 cut line (no print artwork yet), plus
                    the optional 0.7 mm lens outline for a laser-cutting shop

Order of work: board and parts first; print one case set and fit it on the assembled board;
order the face film last, after the fit check.

Generated from the R25 project package (PCB R21 unchanged, CASE R11, ACRYLIC R1;
convergence check {conv}) by CHECKS/build_builder_packs.py. Open items
that need parts in hand or supplier answers are listed in the package's PRODUCTION_GATES.md
and repeated in each README where they concern that supplier.
""")
    zip_dir(top, out / f'{TOP}.zip', prefix=f'{TOP}/')
    files = sorted(p for p in top.rglob('*') if p.is_file())
    print(f'{len(files)} files, {sum(p.stat().st_size for p in files):,} bytes -> {out / (TOP + ".zip")} '
          f'({(out / (TOP + ".zip")).stat().st_size:,} bytes)')
    for r in prints:
        print(f"  {r['name']:18} {r['tris']:7} triangles  {'closed' if r['closed'] else 'OPEN'}")


if __name__ == '__main__':
    main()
