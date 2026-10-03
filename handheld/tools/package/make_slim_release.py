#!/usr/bin/env python3
"""STRUTHIO ONE SLIM · the release: three quote-ready ordering packs, the software, the documents, the manual.

    /usr/bin/python3 tools/package/make_slim_release.py --prebuilt FIRMWARE_BUILD_DIR [--out DIST]

Writes, in DIST (default: <repo>/dist/STRUTHIO_ONE_SLIM):

  STRUTHIO_ONE_SLIM_1_3D_Print.zip       the 7 STL parts + a quote sheet  -> a 3D print service
  STRUTHIO_ONE_SLIM_2_PCB.zip            Gerbers, BOM, CPL + a quote sheet -> JLCPCB
  STRUTHIO_ONE_SLIM_3_Face_Panel.zip     cut and print files + a quote sheet -> an acrylic / UV print shop
  STRUTHIO_ONE_SLIM_4_Software.zip       the game, ready to flash (unzips to struthio/)
  STRUTHIO_ONE_SLIM_5_Documentation.zip  every document, PDF first
  STRUTHIO_ONE_SLIM_Build_Manual.pdf     the build manual on its own
  READ_ME_FIRST.txt                      what each file is, who it goes to, sizes and SHA-256

Every number in the quote sheets is read from the design files (STLs, board outline, panel DXF), so they cannot
drift from what is sent. Builds from the committed state only.
"""
import argparse, datetime, os, shutil, subprocess, sys, tempfile
import trimesh
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_one_packages as P
from make_one_packages import HH, put, text, pdf, zip_dir, sha, git

SLIM = os.path.join(HH, 'cad', 'slim')
REN = os.path.join(HH, 'docs', 'renders', 'slim')
PARTS = [  # file, qty, what it is, how it sits on the bed, colour
    ('slim_front', 1, 'front shell', 'face down', 'case colour'),
    ('slim_back', 1, 'back shell', 'back down', 'case colour'),
    ('slim_wing_left', 1, 'left wing button', 'top face down', 'black'),
    ('slim_wing_right', 1, 'right wing button', 'top face down', 'black'),
    ('slim_rocker', 1, 'dart rocker', 'top face down', 'black'),
    ('slim_power_button', 2, 'power button (tiny: one spare)', 'on its flat side', 'black'),
    ('slim_pin_jig', 1, 'pin jig (a tool, used once)', 'flat', 'any'),
]

def table(rows, heads):
    w = [max(len(str(r[i])) for r in rows + [heads]) for i in range(len(heads))]
    line = lambda r: '  ' + '  '.join(str(c).ljust(w[i]) for i, c in enumerate(r)).rstrip()
    return '\n'.join([line(heads), line(['-' * x for x in w])] + [line(r) for r in rows])

# ---------------------------------------------------------------------------------------------------------
def pack_3d(work):
    root = os.path.join(work, 'STRUTHIO_ONE_SLIM_3D_Print')
    rows, vol = [], 0.0
    for f, q, what, bed, col in PARTS:
        src = os.path.join(SLIM, 'stl', f + '.stl'); put(src, os.path.join(root, f + '.stl'))
        m = trimesh.load(src)
        assert m.is_watertight and m.body_count == 1, f'{f}.stl is not one watertight solid'
        x, y, z = m.extents; v = m.volume / 1000; vol += q * v
        rows.append([f + '.stl', q, f'{x:.1f} x {y:.1f} x {z:.1f}', f'{v:.2f}', what, col])
    for f in ('slim_hero.png', 'slim_exploded.png', 'slim_back.png'):
        put(os.path.join(REN, f), os.path.join(root, 'preview', f))
    text(os.path.join(root, 'README_QUOTE.txt'), f"""
STRUTHIO ONE SLIM - 3D PRINTED PARTS: QUOTE SHEET
=================================================

Upload the 7 .stl files to the print service. Every file is one closed (watertight) solid in millimetres,
already the right way round: no repair, scaling or mirroring needed.

PARTS (8 pieces, {vol:.1f} cm3 of plastic in all)
{table(rows, ['file', 'qty', 'size mm', 'cm3', 'what it is', 'colour'])}

MATERIAL: one of these
  - MJF nylon PA12 (HP Multi Jet Fusion), grey or dyed black      best: tough, crisp, no layer lines
  - SLS nylon PA12                                                 the same, slightly rougher
  - FDM PETG (or ASA), 0.2 mm layers (0.12 for the buttons), 4 walls, 6 top / 6 bottom layers, 40 % infill
  NOT resin (SLA/DLP): too brittle for the screw bosses. NOT PLA: it softens in a hot car.

TOLERANCES
  The shells meet in a tongue and groove with 0.15 mm play each side, and the buttons have 0.2 mm all round:
  standard tolerance (+/- 0.2 mm, or +/- 0.3 % for MJF) is right. No inserts, no threads, no supports needed
  for FDM (orientation: front shell face down, back shell back down, buttons top face down).

FINISH
  As printed is fine. Optional: dyed black (MJF), or a light bead blast. No paint on the button sides.

TEXT TO PASTE INTO THE QUOTE REQUEST
  "Please quote 1 set of the 7 attached STL parts (8 pieces: 2 of slim_power_button, 1 of each other),
   MJF PA12 (or PETG FDM), standard tolerance, dyed black or natural. Millimetres, watertight, print as is."

preview\\ shows the finished handheld (from the 3D model).
""")
    return root

def pack_pcb(work):
    root = os.path.join(work, 'STRUTHIO_ONE_SLIM_PCB'); out = os.path.join(HH, 'pcb', 'slim', 'out')
    for f in ('struthio_one_slim_gerbers.zip', 'BOM_JLCPCB.csv', 'CPL_JLCPCB.csv'):
        put(os.path.join(out, f), os.path.join(root, f))
    for f in ('board_top.png', 'board_bottom.png'):
        put(os.path.join(out, f), os.path.join(root, 'preview', f))
    drc = open(os.path.join(out, 'drc.rpt')).read()
    assert '** Found 0 unconnected pads **' in drc and 'Severity: error' not in drc, 'the board fails DRC'
    import pcbnew
    b = pcbnew.LoadBoard(os.path.join(out, 'struthio_one_slim.kicad_pcb')).GetBoardEdgesBoundingBox()
    w, h = pcbnew.ToMM(b.GetWidth()), pcbnew.ToMM(b.GetHeight())
    import csv
    bom = list(csv.reader(open(os.path.join(out, 'BOM_JLCPCB.csv'))))[1:]
    n_parts = sum(len(r[1].split(',')) for r in bom)
    rows = [[r[0], r[1], r[3]] for r in bom]
    text(os.path.join(root, 'README_QUOTE.txt'), f"""
STRUTHIO ONE SLIM - CONTROL BOARD: QUOTE SHEET (JLCPCB)
======================================================

The small board that carries the buttons and the battery socket. Board rev S2.
Design rule check: 0 errors, 0 unconnected pads.

1. jlcpcb.com > Instant Quote > Add gerber file > struthio_one_slim_gerbers.zip
   It reads the size itself: {w:.1f} x {h:.1f} mm, 2 layers.

2. Change only these (leave everything else as it is):
     PCB Thickness        0.8 mm        (NOT the default 1.6: the case is built around 0.8)
     PCB Qty              5             (the minimum; you use 1)
     PCB Color            any (green is cheapest and fastest)
     Surface Finish       HASL with lead free (or ENIG)

3. PCB Assembly: ON
     PCBA Type            Economic
     Assembly Side        Top Side
     PCBA Qty             2             (or 5; one spare is worth having)
   Next > upload BOM_JLCPCB.csv and CPL_JLCPCB.csv. {n_parts} parts, all surface-mount, all in JLC's library:
{table(rows, ['part', 'where', 'LCSC'])}

4. In the placement preview: J2 (the white battery socket) has its opening toward the board's RIGHT edge.
   If not, rotate it in 90 degree steps until it does. Then add to cart.

The header pins (J1) are NOT on the BOM on purpose: the builder fits 12 bare pins with the printed jig
(the board has to lie flat on the screen board's socket). Nothing else needs soldering or trimming.

preview\\ shows both sides of the board.
""")
    return root

def pack_panel(work):
    root = os.path.join(work, 'STRUTHIO_ONE_SLIM_Face_Panel'); src = os.path.join(SLIM, 'panel')
    for f in ('slim_panel_cut.dxf', 'slim_panel_cut.svg', 'slim_panel_print_MIRRORED.png', 'slim_panel_white.png',
              'slim_panel_print.png', 'slim_panel_proof.png'):
        put(os.path.join(src, f), os.path.join(root, f))
    put(os.path.join(REN, 'slim_front.png'), os.path.join(root, 'preview', 'on_the_handheld.png'))
    lines = open(os.path.join(src, 'slim_panel_cut.dxf')).read().split('\n')
    xs = [float(lines[i + 1]) for i, v in enumerate(lines) if v.strip() == '10']
    ys = [float(lines[i + 1]) for i, v in enumerate(lines) if v.strip() == '20']
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    from PIL import Image
    im = Image.open(os.path.join(src, 'slim_panel_print_MIRRORED.png')); dpi = im.info.get('dpi', (600, 600))[0]
    text(os.path.join(root, 'README_QUOTE.txt'), f"""
STRUTHIO ONE SLIM - FACE PANEL: QUOTE SHEET
==========================================

One flat piece of clear acrylic: the cover over the screen, the front art and the three button openings.
It drops into a pocket in the front of the case, so it is cut to size exactly as drawn.

  Size        {w:.2f} x {h:.2f} mm (outline in slim_panel_cut.dxf, millimetres, seen from the front)
  Thickness   1.0 mm
  Material    CLEAR CAST acrylic (PMMA), both protective films left on
  Cut         laser, outline + 3 cut-outs (two round wing buttons, the long rocker)
  Print       UV, REVERSE (on the back face): colour first, then white behind it
                colour  slim_panel_print_MIRRORED.png  ({im.size[0]} x {im.size[1]} px, {round(dpi)} dpi, already mirrored)
                white   slim_panel_white.png           (black = white ink), mirrored the same way
              The screen window stays CLEAR: no ink there (it is transparent in the colour file).
  Adhesive    clear adhesive transfer tape (3M 468MP or equal) laminated on the back, except over the window
  Quantity    1 (2 if a spare is cheap)

TEXT TO PASTE INTO THE QUOTE REQUEST
  "Please quote 1 (and 2) of the attached panel: 1.0 mm clear cast acrylic, laser cut to slim_panel_cut.dxf
   ({w:.1f} x {h:.1f} mm, 3 internal cut-outs). UV reverse-print on the back: colour from
   slim_panel_print_MIRRORED.png, then a white layer from slim_panel_white.png; the screen window left clear.
   Clear adhesive transfer tape (3M 468MP) on the back, except over the window."

If the shop mirrors files itself, send slim_panel_print.png (as seen from the front) instead and say so.
slim_panel_proof.png shows the art, the cut lines (magenta) and the clear window (blue) together.

Cheaper: order only the clear cut panel and print slim_panel_print.png on clear sticker vinyl at 100 %
(no scaling), cut out the window and stick it on the back.
""")
    return root

def pack_software(work, prebuilt, docs):
    root, top = P.pkg_flashing(work, prebuilt, docs)
    man = os.path.join(root, 'manual')
    os.remove(os.path.join(man, 'STRUTHIO_ONE_Build_Manual_Windows11.pdf'))          # the 23 mm ONE's: not this build
    sums = []
    os.remove(os.path.join(root, 'SHA256SUMS.txt'))
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f); rel = os.path.relpath(p, root).replace(os.sep, '/')
            sums.append(f'{sha(p)}  {rel}')
    text(os.path.join(root, 'SHA256SUMS.txt'), '\n'.join(sorted(sums, key=lambda s: s[66:])))
    return root, top

def pack_docs(work, docs):
    root = os.path.join(work, 'STRUTHIO_ONE_SLIM_Documentation')
    for k, name in (('quick_pdf', '1_Quick_Start.pdf'), ('slim_manual_pdf', '2_Build_Manual.pdf'), ('order_pdf', '3_Order_List.pdf'),
                    ('flash_pdf', '4_Flashing_Guide.pdf'), ('slim_pdf', '5_Design_Guide.pdf'), ('facts_pdf', '6_Hardware_Facts.pdf')):
        put(docs[k], os.path.join(root, name))
    put(os.path.join(REN, 'slim_assembly.gif'), os.path.join(root, 'How_it_goes_together.gif'))
    for f in sorted(os.listdir(REN)):
        if f.endswith('.png'): put(os.path.join(REN, f), os.path.join(root, 'pictures', f))
    for f in sorted(os.listdir(os.path.join(REN, 'steps'))):
        if f.endswith('.png'): put(os.path.join(REN, 'steps', f), os.path.join(root, 'pictures', 'build_steps', f))
    put(os.path.join(SLIM, 'panel', 'slim_panel_proof.png'), os.path.join(root, 'pictures', 'face_panel_proof.png'))
    for f in ('board_top.png', 'board_bottom.png'):
        put(os.path.join(HH, 'pcb', 'slim', 'out', f), os.path.join(root, 'pictures', 'board_' + f.split('_')[1]))
    for s, d in (('STRUTHIO_ORDER.md', 'Order_List.md'), ('STRUTHIO_ONE_SLIM.md', 'Design_Guide.md'),
                 ('STRUTHIO_ONE_FLASHING.md', 'Flashing_Guide.md'), ('HARDWARE_FACTS.md', 'Hardware_Facts.md')):
        put(os.path.join(HH, 'docs', s), os.path.join(root, 'text_versions', d))
    text(os.path.join(root, 'START_HERE.txt'), """
STRUTHIO ONE SLIM - DOCUMENTATION
=================================

Read them in this order:

  1_Quick_Start.pdf          the whole build on one page: print it and keep it on the bench
  2_Build_Manual.pdf         every step with a picture and a check (Windows 11), 20 pages
  3_Order_List.pdf           everything to buy and order, as a checklist
  4_Flashing_Guide.pdf       putting the game on the screen board, in detail
  5_Design_Guide.pdf         why it is built the way it is: the 16.5 mm stack, run time, boot time, heat
  6_Hardware_Facts.pdf       the manufacturers' data the design is built on

  How_it_goes_together.gif   the assembly as a short animation
  pictures\\                  the handheld, each build step and the board (from the 3D model)
  text_versions\\             documents 3-6 as plain text (Markdown)
""")
    return root

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--prebuilt', required=True)
    ap.add_argument('--out', default=os.path.join(P.REPO, 'dist', 'STRUTHIO_ONE_SLIM')); args = ap.parse_args()
    if git('status', '--porcelain', '--untracked-files=no'):
        sys.exit('commit your changes first: the release is built from the committed state')
    commit = git('rev-parse', '--short', 'HEAD'); today = datetime.date.today().isoformat()
    dist = os.path.abspath(args.out)
    if os.path.isdir(dist): shutil.rmtree(dist)
    os.makedirs(dist)
    foot = f'STRUTHIO ONE SLIM · commit {commit} · {today}'
    with tempfile.TemporaryDirectory() as work:
        d = lambda n: os.path.join(work, n)
        docs = {'flash_pdf': d('flash.pdf'), 'facts_pdf': d('facts.pdf'), 'order_pdf': d('order.pdf'), 'slim_pdf': d('slim.pdf'),
                'slim_manual_pdf': d('slim_manual.pdf'), 'quick_pdf': d('quick.pdf'), 'manual_pdf': d('one_manual.pdf')}
        pdf(os.path.join(HH, 'docs', 'STRUTHIO_ONE_FLASHING.md'), docs['flash_pdf'], foot)
        pdf(os.path.join(HH, 'docs', 'HARDWARE_FACTS.md'), docs['facts_pdf'], foot)
        pdf(os.path.join(HH, 'docs', 'STRUTHIO_ORDER.md'), docs['order_pdf'], foot)
        pdf(os.path.join(HH, 'docs', 'STRUTHIO_ONE_SLIM.md'), docs['slim_pdf'], foot,
            [os.path.join(REN, 'slim_hero.png') + ':the ONE SLIM (from the 3D model)',
             os.path.join(REN, 'one_vs_slim_side.png') + ':the ONE and the ONE SLIM from the side, same scale'])
        for script, k in (('slim_manual.py', 'slim_manual_pdf'), ('quick_card.py', 'quick_pdf'), ('one_manual.py', 'manual_pdf')):
            subprocess.check_call([sys.executable, os.path.join(HH, 'tools', 'manual', script), docs[k]], stdout=subprocess.DEVNULL)
        made = []
        for i, (fn, top, name) in enumerate([
                (pack_3d, 'STRUTHIO_ONE_SLIM_3D_Print', '3D_Print'), (pack_pcb, 'STRUTHIO_ONE_SLIM_PCB', 'PCB'),
                (pack_panel, 'STRUTHIO_ONE_SLIM_Face_Panel', 'Face_Panel'),
                (lambda w: pack_software(w, args.prebuilt, docs)[0], 'struthio', 'Software'),
                (lambda w: pack_docs(w, docs), 'STRUTHIO_ONE_SLIM_Documentation', 'Documentation')], 1):
            w = d(f'p{i}'); os.makedirs(w)
            root = fn(w)
            z = os.path.join(dist, f'STRUTHIO_ONE_SLIM_{i}_{name}.zip'); zip_dir(root, z, top); made.append(z)
        m = os.path.join(dist, 'STRUTHIO_ONE_SLIM_Build_Manual.pdf'); shutil.copy2(docs['slim_manual_pdf'], m); made.append(m)
    what = {
        '1_3D_Print': 'send to a 3D print service (JLC3DP, Craftcloud, a local shop): its README_QUOTE.txt says what to ask for',
        '2_PCB': 'upload to jlcpcb.com: its README_QUOTE.txt lists the five settings to change',
        '3_Face_Panel': 'send to an acrylic laser-cut + UV print shop: its README_QUOTE.txt has the text to paste',
        '4_Software': 'for you: unzip to C:\\ (makes C:\\struthio), plug in the screen board, double-click FLASH_ME.bat',
        '5_Documentation': 'for you: START_HERE.txt, then the quick start and the build manual',
        'Build_Manual': 'the build manual on its own (also inside 5)',
    }
    lines = [f'STRUTHIO ONE SLIM - RELEASE · 16.5 mm case rev S3 · board rev S2 · commit {commit} · {today}', '',
             'Six files. The first three are what you send out for quotes; the rest are for you.', '']
    for p in made:
        key = next(k for k in what if k in os.path.basename(p))
        lines += [os.path.basename(p), f'    {what[key]}', f'    {os.path.getsize(p) / 1e6:.2f} MB  sha256 {sha(p)}', '']
    lines += ['Also to buy (see 3_Order_List.pdf): the Waveshare ESP32-S3-Touch-LCD-3.5B screen board, a 302535 LiPo cell',
              '(PH 2.0 plug), a plug-in 1 W 8 ohm cavity speaker (1.25 mm plug), 5 x M2 x 6 countersunk screws, a 2.54 mm',
              'header strip, 1.0 mm double-sided foam tape.']
    text(os.path.join(dist, 'READ_ME_FIRST.txt'), '\n'.join(lines))
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
