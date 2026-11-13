#!/usr/bin/env python3
"""Refill, DRC and plot a flex board written by generate_flex.py into a JLCPCB FPC order folder and zip.

    python3 export_flex.py <folder holding SLIM4_DISPLAY_FLEX_R1[_PREVIEW].kicad_pcb>

Writes <folder>/ORDER/ (Gerbers + drill zip, BOM, CPL, 1:1 fit template PDF, DRC report, README) and
<folder>/<name>_ORDER.zip. Needs KiCad 7.0.x (kicad-cli, python3 with pcbnew).
"""
import csv, glob, json, os, re, shutil, subprocess, sys, zipfile
sys.dont_write_bytecode = True

STAMP = (2026, 10, 7, 0, 0, 0)
LAYERS = 'F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,F.SilkS,Edge.Cuts,User.1,User.2'
PROBE = r'''
import json, pcbnew, sys
p = sys.argv[1]
b = pcbnew.LoadBoard(p); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); b.Save(p)
b = pcbnew.LoadBoard(p); pcbnew.WriteDRCReport(b, "DRC.rpt", pcbnew.EDA_UNITS_MILLIMETRES, True)
bb = b.GetBoardEdgesBoundingBox()
print(json.dumps({"w": round(pcbnew.ToMM(bb.GetWidth()), 2), "h": round(pcbnew.ToMM(bb.GetHeight()), 2),
                  "vias": sum(1 for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T)}))
'''


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'failed: {" ".join(cmd)}\n{r.stdout}\n{r.stderr}')
    return r.stdout


def main():
    d = os.path.abspath(sys.argv[1])
    pcb = glob.glob(os.path.join(d, 'SLIM4_DISPLAY_FLEX_R1*.kicad_pcb'))[0]
    name = os.path.basename(pcb)[:-10]
    preview = name.endswith('_PREVIEW')
    facts = json.loads([l for l in run(['python3', '-c', PROBE, pcb], d).splitlines() if l.startswith('{')][-1])
    drc = open(os.path.join(d, 'DRC.rpt')).read()
    found = dict((k, int(v)) for v, k in re.findall(r'Found (\d+) (DRC violations|unconnected pads|Footprint errors)', drc))
    o = os.path.join(d, 'ORDER'); shutil.rmtree(o, ignore_errors=True); os.makedirs(o)
    g = os.path.join(d, 'gerber'); shutil.rmtree(g, ignore_errors=True); os.makedirs(g)
    run(['kicad-cli', 'pcb', 'export', 'gerbers', '--layers', LAYERS, '--subtract-soldermask', '-o', g + '/', pcb], d)
    run(['kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-units', 'mm', '-o', g + '/', pcb], d)
    run(['kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both', '-o', os.path.join(d, 'pos.csv'), pcb], d)
    run(['kicad-cli', 'pcb', 'export', 'pdf', '--layers', 'Edge.Cuts,F.SilkS,User.1,User.2,F.Cu', '--black-and-white',
         '-o', os.path.join(o, name + '_FIT_TEMPLATE_1to1.pdf'), pcb], d)
    for f in os.listdir(g):                                    # pin plot dates so rebuilds give the same bytes
        p = os.path.join(g, f); t = open(p).read()
        t = re.sub(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d', '2026-10-07T00:00:00+00:00', t)
        t = re.sub(r'date \d{4}-\d\d-\d\d \d\d:\d\d:\d\d', 'date 2026-10-07 00:00:00', t)
        t = re.sub(r'date \w{3} \w{3} [ \d]\d \d\d:\d\d:\d\d \d{4}', 'date Wed Oct  7 00:00:00 2026', t)
        open(p, 'w').write(t)
    with zipfile.ZipFile(os.path.join(o, name + '_GERBER_DRILL.zip'), 'w') as z:
        for f in sorted(os.listdir(g)):
            zi = zipfile.ZipInfo(f, STAMP); zi.external_attr = 0o100644 << 16
            z.writestr(zi, open(os.path.join(g, f), 'rb').read(), compress_type=zipfile.ZIP_DEFLATED)
    shutil.rmtree(g)
    with open(os.path.join(o, name + '_BOM.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        w.writerow(['FH26W-31S-0.3SHW(60)', 'J1', 'FPC 31P 0.3 mm', 'C2973806'])
    with open(os.path.join(d, 'pos.csv')) as f, open(os.path.join(o, name + '_CPL.csv'), 'w', newline='') as out:
        w = csv.writer(out); w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for r in csv.DictReader(f):
            if r['Ref'] == 'J1':
                w.writerow([r['Ref'], f"{float(r['PosX']):.4f}mm", f"{float(r['PosY']):.4f}mm", 'Top', f"{float(r['Rot']):g}"])
    os.remove(os.path.join(d, 'pos.csv'))
    shutil.copy(os.path.join(d, 'DRC.rpt'), os.path.join(o, 'DRC_REPORT_KICAD7.txt'))
    warn = ('\n*** PREVIEW: the panel pin map is a placeholder. DO NOT ORDER THESE FILES. ***\n'
            '*** Fill panel_pinmap.csv from Startek\'s KD047HDFID001 datasheet and run without --preview. ***\n') if preview else ''
    readme = f"""STRUTHIO SLIM4 - DISPLAY FLEX R1 - JLCPCB FLEX PCB ORDER{warn}
Joins the Startek KD047HDFID001 panel tail (31 pins, 0.3 mm) to the R22 board's J1 (FH12-20, 0.5 mm).

Upload to JLCPCB as a FLEX PCB:
  {name}_GERBER_DRILL.zip   copper F/B, coverlay openings (mask), paste, silk, outline,
                             User.1 = stiffener at the J1 end, User.2 = stiffener under the FH26
  {name}_BOM.csv / _CPL.csv one part on the top side: J1 FH26W-31S-0.3SHW(60), LCSC C2973806

FLEX OPTIONS
  Layers                 2, polyimide, 1/2 oz copper, yellow coverlay
  Size                   {facts['w']} x {facts['h']} mm
  Gold fingers (J1 end)  20 x 0.30 mm at 0.50 mm pitch on the BOTTOM side, ENIG
  Stiffener, J1 end      polyimide on the TOP side over the last 6.0 mm (User.1), thickness chosen so the
                         finger end is 0.30 mm total (FH12 accepts 0.30 +/- 0.05 mm; usually 0.2 mm PI)
  Stiffener, panel end   0.2 mm FR4 or PI on the BOTTOM side under the FH26 connector (User.2)
  Min track / space      0.10 / 0.08 mm; vias 0.45 / 0.20 mm
  Surface finish         ENIG
  Quantity               5, with the FH26 connector assembled (one-side SMT)

ASSEMBLY
  Panel tail into the FH26 with its contacts ("conduct side") facing the flex.
  Gold fingers into the board's J1 with the fingers facing the board (FH12 is bottom contact),
  pin 1 (silk "1") towards the board's pin 1.

BEFORE ORDERING: print {name}_FIT_TEMPLATE_1to1.pdf at 100 %, cut it out and route it through
the printed case from the panel tail to J1. Change --length in generate_flex.py if it is short or long.

CHECKS: KiCad DRC {found.get('DRC violations')} violations, {found.get('unconnected pads')} unconnected pads, {facts['vias']} vias.
"""
    open(os.path.join(o, 'README_FLEX_ORDER.txt'), 'w').write(readme)
    zp = os.path.join(d, name + '_ORDER.zip')
    with zipfile.ZipFile(zp, 'w') as z:
        for f in sorted(os.listdir(o)):
            zi = zipfile.ZipInfo(name + '_ORDER/' + f, STAMP); zi.external_attr = 0o100644 << 16
            z.writestr(zi, open(os.path.join(o, f), 'rb').read(), compress_type=zipfile.ZIP_DEFLATED)
    print(json.dumps({'drc': found, 'size_mm': [facts['w'], facts['h']], 'zip': zp, 'preview': preview}))


if __name__ == '__main__':
    main()
