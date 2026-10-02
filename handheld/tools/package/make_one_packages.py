#!/usr/bin/env python3
"""STRUTHIO ONE · builds the six release packages from the repository.

    /usr/bin/python3 tools/package/make_one_packages.py --prebuilt FIRMWARE_BUILD_DIR [--out DIST]

FIRMWARE_BUILD_DIR is an ESP-IDF build folder of handheld/firmware (bootloader/bootloader.bin,
partition_table/partition-table.bin, struthio.bin). Writes, in DIST (default: <repo>/dist):

  STRUTHIO_ONE_1_Firmware_Flashing.zip   prebuilt firmware + source + menu + flashing guide (top folder struthio/)
  STRUTHIO_ONE_2_Face_Panel_Print.zip    face panel cut + print files for the acrylic shop
  STRUTHIO_ONE_3_PCB_JLCPCB.zip          Gerbers, BOM, CPL, KiCad files, board pictures, order checklist (+ ONE_SLIM/)
  STRUTHIO_ONE_4_3D_Print.zip            the five STL parts and how to print them (+ ONE_SLIM/)
  STRUTHIO_ONE_5_Documents.zip           build guide, flashing guide, hardware facts (PDF + Markdown), renders
  STRUTHIO_Full_Backup_<commit>.zip      the whole repository at this commit + the art pack and soundtrack,
                                         and the same backup in parts of at most 24 MB (each opens on its own)
  PACKAGES.txt                           sizes and SHA-256 of everything above

Needs: git, node + Playwright (for the PDFs), KiCad's python (board pictures are made by pcb/one/plot_board.py).
"""
import argparse, datetime, hashlib, io, os, shutil, subprocess, sys, tempfile, zipfile

HH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
REPO = os.path.dirname(HH)
TOOLS = os.path.join(HH, 'tools', 'package')
PART_LIMIT = 24_000_000

def git(*a):
    return subprocess.check_output(['git', '-C', REPO, *a]).decode().strip()

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''): h.update(blk)
    return h.hexdigest()

def zip_dir(src, dst, top):
    """zip src/ into dst with every path under top/; deterministic order and timestamps"""
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for d, dirs, files in sorted(os.walk(src)):
            dirs.sort()
            for f in sorted(files):
                p = os.path.join(d, f); rel = os.path.relpath(p, src)
                zi = zipfile.ZipInfo(f'{top}/{rel}', (2026, 10, 2, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = (0o755 if os.access(p, os.X_OK) else 0o644) << 16
                with open(p, 'rb') as fh: z.writestr(zi, fh.read())

def put(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)

def text(dst, body):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'w', newline='\r\n').write(body.strip() + '\n')        # CRLF: readable in Windows Notepad too

def pdf(md, out_pdf, foot, images=()):
    with tempfile.TemporaryDirectory() as t:
        h = os.path.join(t, 'doc.html')
        args = [sys.executable, os.path.join(TOOLS, 'mdhtml.py'), md, h, '--foot', foot]
        for im in images: args += ['--image', im]
        subprocess.check_call(args)
        subprocess.check_call(['node', os.path.join(TOOLS, 'html2pdf.mjs'), h, out_pdf], stdout=subprocess.DEVNULL)

SKIP_DIRS = {'build', '__pycache__', 'idf_check', 'node_modules', 'managed_components', '.git'}
SKIP_FILES = {'sdkconfig', 'sdkconfig.old', 'dependencies.lock', 'test_buttons', '.DS_Store'}
def copy_tree(src, dst):
    for d, dirs, files in os.walk(src):
        rel = os.path.relpath(d, src)
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if f in SKIP_FILES or f.endswith(('.pyc', '.o', '.a')): continue
            os.makedirs(os.path.join(dst, rel), exist_ok=True)
            shutil.copy2(os.path.join(d, f), os.path.join(dst, rel, f))

# ---------------------------------------------------------------------------------------------------------
def pkg_flashing(work, prebuilt, docs):
    root = os.path.join(work, 'struthio')
    for t in ('core', 'render', 'audio', 'golden', 'host', 'firmware'):
        copy_tree(os.path.join(HH, t), os.path.join(root, 'handheld', t))
    put(os.path.join(HH, 'build', 'assets'), os.path.join(root, 'handheld', 'build', 'assets'))
    put(os.path.join(HH, 'tools', 'struthio_doctor.py'), os.path.join(root, 'handheld', 'tools', 'struthio_doctor.py'))
    for f in ('STRUTHIO.bat', 'struthio.sh', 'README_FIRST.txt'):
        put(os.path.join(HH, 'tools', 'launcher', f), os.path.join(root, f))
    os.chmod(os.path.join(root, 'struthio.sh'), 0o755)
    pb = os.path.join(root, 'prebuilt')
    put(os.path.join(prebuilt, 'bootloader', 'bootloader.bin'), os.path.join(pb, 'bootloader.bin'))
    put(os.path.join(prebuilt, 'partition_table', 'partition-table.bin'), os.path.join(pb, 'partition-table.bin'))
    put(os.path.join(prebuilt, 'struthio.bin'), os.path.join(pb, 'struthio.bin'))
    # the art pack and the soundtrack are flashed from handheld/build/assets (one copy in the package)
    open(os.path.join(pb, 'flash_args.txt'), 'w', newline='\n').write("""
--flash-mode dio --flash-freq 80m --flash-size 16MB
0x0 bootloader.bin
0x8000 partition-table.bin
0x10000 struthio.bin
0x410000 ../handheld/build/assets/struthio.pak
0xd10000 ../handheld/build/assets/struthio_music.ima
""".lstrip())
    put(docs['flash_pdf'], os.path.join(root, 'manual', 'STRUTHIO_ONE_Flashing_Guide.pdf'))
    put(docs['manual_pdf'], os.path.join(root, 'manual', 'STRUTHIO_ONE_Build_Manual_Windows11.pdf'))
    sums = []
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f); rel = os.path.relpath(p, root).replace(os.sep, '/')
            sums.append(f'{sha(p)}  {rel}')
    text(os.path.join(root, 'SHA256SUMS.txt'), '\n'.join(sorted(sums, key=lambda s: s[66:])))
    return root, 'struthio'

def pkg_panel(work):
    root = os.path.join(work, 'STRUTHIO_ONE_Face_Panel'); src = os.path.join(HH, 'cad', 'one', 'panel')
    for f in ('one_panel_cut.dxf', 'one_panel_cut.svg', 'one_panel_print.png', 'one_panel_print_MIRRORED.png',
              'one_panel_white.png', 'one_panel_proof.png'):
        put(os.path.join(src, f), os.path.join(root, f))
    put(os.path.join(HH, 'docs', 'renders', 'one', 'one_front.png'), os.path.join(root, 'preview_on_the_handheld.png'))
    sys.path.insert(0, os.path.join(HH, 'cad', 'one')); import one_cad as o
    b = o.panel2d().bounds(); w, h = b[2] - b[0], b[3] - b[1]
    text(os.path.join(root, 'README_ORDER.txt'), f"""
STRUTHIO ONE - FACE PANEL
=========================

One flat piece: the lens over the screen, the front art and the button wells.
Finished size {w:.2f} x {h:.2f} mm, 1.0 mm thick, three cut-outs (two wing buttons, the rocker).

What to ask the shop for
------------------------
  1.0 mm CLEAR CAST ACRYLIC, laser cut to one_panel_cut.dxf (units: mm, seen from the front).
  REVERSE-PRINTED (UV) on the back: first colour from one_panel_print_MIRRORED.png,
  then white from one_panel_white.png.
  The screen window must stay CLEAR: no ink there (it is transparent in the PNG).
  If the shop mirrors files itself, send one_panel_print.png instead and say so.

The files
---------
  one_panel_cut.dxf / .svg        cut lines (outline + 3 cut-outs), mm
  one_panel_print_MIRRORED.png    the art for the back of the panel, 600 dpi, 1 mm bleed
  one_panel_white.png             white underprint (black = white ink), mirrored like the art
  one_panel_print.png             the art as seen from the front, for checking
  one_panel_proof.png             art + cut lines (magenta) + clear window (blue)
  preview_on_the_handheld.png     how it looks on the finished handheld

Cheaper way
-----------
  Order only the clear cut panel, print one_panel_print.png on clear or white sticker vinyl
  at 100 % (600 dpi), cut out the screen window and stick it on the back of the panel.

Fitting: last step of the build guide. Tape on the black areas only, line it up inside the
rim, press from the middle outward.
""")
    return root, 'STRUTHIO_ONE_Face_Panel'

def pkg_pcb(work):
    root = os.path.join(work, 'STRUTHIO_ONE_PCB'); out = os.path.join(HH, 'pcb', 'one', 'out')
    for f in ('struthio_one_gerbers.zip', 'BOM_JLCPCB.csv', 'CPL_JLCPCB.csv', 'board_top.png', 'board_bottom.png', 'drc.rpt'):
        put(os.path.join(out, f), os.path.join(root, f))
    for f in ('struthio_one.kicad_pcb', 'struthio_one.kicad_pro'):
        put(os.path.join(out, f), os.path.join(root, 'kicad', f))
    put(os.path.join(HH, 'pcb', 'one', 'make_one_pcb.py'), os.path.join(root, 'kicad', 'make_one_pcb.py'))
    bom = open(os.path.join(out, 'BOM_JLCPCB.csv')).read().strip()
    text(os.path.join(root, 'README_ORDER.txt'), f"""
STRUTHIO ONE - CONTROL BOARD (rev C), JLCPCB
============================================

1. jlcpcb.com > Order now > upload struthio_one_gerbers.zip.
   2 layers, 1.6 mm, any colour. Everything else default.
2. Turn on PCB Assembly: TOP side, STANDARD PCBA (J1, J2 and SW5 are through-hole parts).
   Upload BOM_JLCPCB.csv and CPL_JLCPCB.csv.
3. In the placement preview check:
   - J1  an ordinary 2 x 16 header, plastic on the top side, all 32 pins in the strip's holes
   - J2  the socket opening faces the board's RIGHT edge
   - SW5 the knob points off the board's LEFT edge
   - Q1, Q2 (SOT-23): the single leg on the side the silkscreen shows; D1: band toward the left
   If a part is turned, rotate it in the preview in 90 degree steps until it matches.
4. Six parts are JLC basic parts; J1, J2 and SW5 are extended (one set-up fee each).

The parts
---------
{bom}

What the extra parts do
-----------------------
  Q1 (AO3401A)                 reverse-battery protection
  Q2, C1, R1, D1               power-on pulse: holds the Waveshare's PWR key (header pin 24)
                               for ~3-8 s when the slide switch turns on, because on battery
                               alone its power chip waits for that key (AXP2101 datasheet 6.5.2)

Files
-----
  struthio_one_gerbers.zip   the board (10 Gerber and drill files)
  BOM_JLCPCB.csv / CPL_JLCPCB.csv   parts and placement for JLC assembly
  board_top.png / board_bottom.png  what the board looks like
  drc.rpt                    KiCad design-rule check: no errors, no unconnected pads
                             (the only notes say the footprints come from libraries
                             this KiCad setup doesn't list)
  kicad/                     the KiCad board, and the script that builds it from the case model
""")
    slim = os.path.join(root, 'ONE_SLIM'); so = os.path.join(HH, 'pcb', 'slim', 'out')
    for f in ('struthio_one_slim_gerbers.zip', 'BOM_JLCPCB.csv', 'CPL_JLCPCB.csv', 'board_top.png', 'board_bottom.png', 'drc.rpt'):
        put(os.path.join(so, f), os.path.join(slim, f))
    for f in ('struthio_one_slim.kicad_pcb', 'struthio_one_slim.kicad_pro'):
        put(os.path.join(so, f), os.path.join(slim, 'kicad', f))
    put(os.path.join(HH, 'pcb', 'slim', 'make_slim_pcb.py'), os.path.join(slim, 'kicad', 'make_slim_pcb.py'))
    text(os.path.join(slim, 'README_ORDER.txt'), """
STRUTHIO ONE SLIM - CONTROL BOARD (rev S1), JLCPCB
==================================================

The same circuit as the ONE's board, on a 0.8 mm board shaped for the 16.5 mm case.

1. jlcpcb.com > Order now > upload struthio_one_slim_gerbers.zip.
   2 layers, PCB THICKNESS 0.8 mm (not the default 1.6), any colour.
2. PCB Assembly: TOP side, STANDARD PCBA. Upload BOM_JLCPCB.csv and CPL_JLCPCB.csv.
   J1 (the header) is NOT in them: you fit 8 bare pins yourself with the printed pin jig
   (docs: STRUTHIO_ONE_SLIM, section 5). The back silkscreen lists the 8 holes.
3. Check the placement preview as for the ONE (J2 opening to the right, SW5 knob off the left edge).
4. When the boards arrive: snip SW5's and J2's leads on the back flush (0.5 mm or less).
""")
    return root, 'STRUTHIO_ONE_PCB'

def pkg_3d(work):
    root = os.path.join(work, 'STRUTHIO_ONE_3D_Print'); stl = os.path.join(HH, 'cad', 'one', 'stl')
    for f in sorted(os.listdir(stl)):
        if f.endswith('.stl'): put(os.path.join(stl, f), os.path.join(root, f))
    for f in ('one_exploded.png', 'one_hero.png'):
        put(os.path.join(HH, 'docs', 'renders', 'one', f), os.path.join(root, 'preview_' + f[4:]))
    text(os.path.join(root, 'README_PRINT.txt'), """
STRUTHIO ONE - 3D PRINTED PARTS
===============================

Five parts, one of each. PETG (or ASA), 0.2 mm layers, 4 walls, 6 top / 6 bottom layers, 40 % gyroid infill.
Not PLA: it softens at 55-60 C (a car in summer) and creeps under the screws.
The files are in millimetres and already the right way round (no mirroring needed).

  Part                    Put on the bed            Supports
  one_front.stl           its FACE down (flat)      none
  one_back.stl            its BACK down             none
  one_wing_left.stl       its TOP face down         none
  one_wing_right.stl      its TOP face down         none
  one_rocker.stl          its TOP face down         none

The wing buttons and the rocker have their engraving on the top face, so it prints into the
first layers: keep the bed clean and the first layer neat. Fill the engraving afterwards with a
blue paint pen if you like.

Also needed for the case
------------------------
  an 11 mm piece of 1.75 mm filament   the rocker's axle
  2 x M2 x 8 pan-head screws           self-tapping or machine; they tap the 1.7 mm pilot holes
  3 mm soft foam pad, ~30 x 45 mm      on top of the battery
  thin double-sided tape               the speaker, and the face panel

Check after printing
--------------------
  - The wing buttons slide in their collars with the key in the slot, and spring back freely.
  - The rocker tips both ways on its axle.
  - The back shell's top hooks go into the slots in the front shell's top edge.
If a cap is tight, take 0.1-0.2 mm off its sides with fine sandpaper; never force it.
""")
    slim = os.path.join(root, 'ONE_SLIM'); sstl = os.path.join(HH, 'cad', 'slim', 'stl')
    for f in sorted(os.listdir(sstl)):
        if f.endswith('.stl'): put(os.path.join(sstl, f), os.path.join(slim, f))
    for f in ('slim_hero.png', 'slim_exploded.png', 'one_vs_slim_side.png'):
        put(os.path.join(HH, 'docs', 'renders', 'slim', f), os.path.join(slim, 'preview_' + f))
    text(os.path.join(slim, 'README_PRINT.txt'), """
STRUTHIO ONE SLIM - 3D PRINTED PARTS (16.5 mm case)
===================================================

PETG (or ASA), 0.4 mm nozzle, 0.2 mm layers (0.12 mm for the caps), 4 walls, 6 top / 6 bottom
layers, 40 % gyroid. Every wall in this case is then solid plastic. Not PLA.

  Part                    Put on the bed            Supports
  slim_front.stl          its FACE down             none (the groove opens upward)
  slim_back.stl           its BACK down             none (the tongue points up; countersinks are 45 deg)
  slim_wing_left/right    TOP face down             none
  slim_rocker.stl         TOP face down             none
  slim_pin_jig.stl        flat                      none   (a tool: sets the 8 header pins)
  slim_pin_spacer.stl     flat                      none   ONLY if your Waveshare's J8 socket top is
                                                           11.5 mm behind the glass, not 12.6 (measure)

The shells meet in a tongue and groove: 0.7 mm tongue, 1.0 mm groove, 0.15 mm play each side.
If it is tight, file the tongue lightly; never open the groove.

Also needed: 3 x M2 x 6 and 2 x M2 x 8 countersunk screws, 1.0 mm double-sided foam tape,
an 11 mm piece of 1.75 mm filament (the rocker's axle).
""")
    return root, 'STRUTHIO_ONE_3D_Print'

def pkg_docs(work, docs):
    root = os.path.join(work, 'STRUTHIO_ONE_Documents')
    put(docs['manual_pdf'], os.path.join(root, 'STRUTHIO_ONE_Build_Manual_Windows11.pdf'))
    put(docs['build_pdf'], os.path.join(root, 'STRUTHIO_ONE_Build_Guide.pdf'))
    put(docs['flash_pdf'], os.path.join(root, 'STRUTHIO_ONE_Flashing_Guide.pdf'))
    put(docs['facts_pdf'], os.path.join(root, 'Hardware_Facts.pdf'))
    put(docs['slim_pdf'], os.path.join(root, 'STRUTHIO_ONE_SLIM_Guide.pdf'))
    put(os.path.join(HH, 'docs', 'STRUTHIO_ONE_SLIM.md'), os.path.join(root, 'markdown', 'STRUTHIO_ONE_SLIM_Guide.md'))
    rs = os.path.join(HH, 'docs', 'renders', 'slim')
    for f in sorted(os.listdir(rs)):
        if f.endswith('.png'): put(os.path.join(rs, f), os.path.join(root, 'pictures', 'slim', f))
    for s, d in (('STRUTHIO_ONE.md', 'STRUTHIO_ONE_Build_Guide.md'), ('STRUTHIO_ONE_FLASHING.md', 'STRUTHIO_ONE_Flashing_Guide.md'),
                 ('HARDWARE_FACTS.md', 'Hardware_Facts.md')):
        put(os.path.join(HH, 'docs', s), os.path.join(root, 'markdown', d))
    put(os.path.join(HH, 'firmware', 'README.md'), os.path.join(root, 'markdown', 'Firmware_Notes.md'))
    r = os.path.join(HH, 'docs', 'renders', 'one')
    for f in sorted(os.listdir(r)):
        if f.endswith('.png'): put(os.path.join(r, f), os.path.join(root, 'pictures', f))
    put(os.path.join(HH, 'cad', 'one', 'panel', 'one_panel_proof.png'), os.path.join(root, 'pictures', 'face_panel_proof.png'))
    for f in ('board_top.png', 'board_bottom.png'):
        put(os.path.join(HH, 'pcb', 'one', 'out', f), os.path.join(root, 'pictures', 'pcb_' + f))
    text(os.path.join(root, 'README.txt'), """
STRUTHIO ONE - DOCUMENTS
========================

  STRUTHIO_ONE_Build_Manual_Windows11.pdf
                                   START HERE: the whole build in one manual, in build order,
                                   with pictures of every step, screenshots and diagrams
  STRUTHIO_ONE_SLIM_Guide.pdf      the 16.5 mm ONE SLIM: what changes, parts, build, battery
                                   run time, boot time, heat
  STRUTHIO_ONE_Build_Guide.pdf     the hardware reference: parts, printing, ordering,
                                   the 14 assembly steps, tests, faults, what to confirm
  STRUTHIO_ONE_Flashing_Guide.pdf  putting the game on the Waveshare board
  Hardware_Facts.pdf               the manufacturers' data the design is built on
  markdown\\                        the same documents as text, plus the firmware notes
  pictures\\                        renders, the face panel proof and the board
""")
    return root, 'STRUTHIO_ONE_Documents'

def pkg_backup(dist, commit):
    """git archive of HEAD + the untracked art pack / soundtrack; plus parts of at most 24 MB"""
    prefix = 'Struthio/'
    raw = subprocess.check_output(['git', '-C', REPO, 'archive', '--format=zip', f'--prefix={prefix}', 'HEAD'])
    src = zipfile.ZipFile(io.BytesIO(raw))
    entries = [(i.filename, src.read(i)) for i in src.infolist() if not i.is_dir()]
    a = os.path.join(HH, 'build', 'assets')
    for f in sorted(os.listdir(a)):
        entries.append((f'{prefix}handheld/build/assets/{f}', open(os.path.join(a, f), 'rb').read()))
    restore = f"""STRUTHIO - FULL BACKUP
======================

The whole STRUTHIO repository at commit {commit} (branch claude/handheld-core-port), plus the
handheld's art pack and soundtrack (handheld/build/assets, which git does not track).

Unzip everything into one folder: you get Struthio/ exactly as it was. If you have the backup in
parts, unzip all the parts into the same folder (each part holds different files).

Start with Struthio/handheld/docs/STRUTHIO_ONE.md (the build guide).
"""
    entries.append((f'{prefix}RESTORE.txt', restore.encode()))
    def write(path, items):
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for n, data in items:
                zi = zipfile.ZipInfo(n, (2026, 10, 2, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o644 << 16
                z.writestr(zi, data)
    full = os.path.join(dist, f'STRUTHIO_Full_Backup_{commit}.zip'); write(full, entries)
    out = [full]
    if os.path.getsize(full) > PART_LIMIT:
        groups = [('docs', lambda n: n.startswith(prefix + 'handheld/docs/')),
                  ('cad', lambda n: n.startswith(prefix + 'handheld/cad/')),
                  ('rest', lambda n: True)]
        left = list(entries); k = 0
        for name, test in groups:
            sel = [e for e in left if test(e[0])]; left = [e for e in left if not test(e[0])]
            if not any(n.endswith('RESTORE.txt') for n, _ in sel): sel.append((f'{prefix}RESTORE.txt', restore.encode()))
            k += 1
            p = os.path.join(dist, f'STRUTHIO_Full_Backup_{commit}_part{k}of{len(groups)}_{name}.zip'); write(p, sel); out.append(p)
    return out

# ---------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--prebuilt', required=True); ap.add_argument('--out', default=os.path.join(REPO, 'dist'))
    args = ap.parse_args()
    if git('status', '--porcelain', '--untracked-files=no'):
        sys.exit('commit your changes first: the packages are built from the committed state')
    commit = git('rev-parse', '--short', 'HEAD'); today = datetime.date.today().isoformat()
    dist = os.path.abspath(args.out); os.makedirs(dist, exist_ok=True)
    for f in os.listdir(dist):
        if f.endswith('.zip') or f == 'PACKAGES.txt': os.remove(os.path.join(dist, f))
    foot = f'STRUTHIO ONE · commit {commit} · {today}'
    with tempfile.TemporaryDirectory() as work:
        docs = {'build_pdf': os.path.join(work, 'build.pdf'), 'flash_pdf': os.path.join(work, 'flash.pdf'), 'facts_pdf': os.path.join(work, 'facts.pdf')}
        r = os.path.join(HH, 'docs', 'renders', 'one')
        pdf(os.path.join(HH, 'docs', 'STRUTHIO_ONE.md'), docs['build_pdf'], foot,
            [os.path.join(r, 'one_front.png') + ':the finished handheld', os.path.join(r, 'one_exploded.png') + ':how it goes together'])
        pdf(os.path.join(HH, 'docs', 'STRUTHIO_ONE_FLASHING.md'), docs['flash_pdf'], foot)
        pdf(os.path.join(HH, 'docs', 'HARDWARE_FACTS.md'), docs['facts_pdf'], foot)
        docs['slim_pdf'] = os.path.join(work, 'slim.pdf'); rs = os.path.join(HH, 'docs', 'renders', 'slim')
        pdf(os.path.join(HH, 'docs', 'STRUTHIO_ONE_SLIM.md'), docs['slim_pdf'], foot,
            [os.path.join(rs, 'slim_hero.png') + ':the ONE SLIM (from the 3D model)', os.path.join(rs, 'one_vs_slim_side.png') + ':23.0 mm and 16.5 mm, same scale'])
        docs['manual_pdf'] = os.path.join(work, 'manual.pdf')
        subprocess.check_call([sys.executable, os.path.join(HH, 'tools', 'manual', 'one_manual.py'), docs['manual_pdf']], stdout=subprocess.DEVNULL)
        made = []
        for i, (fn, name) in enumerate([(lambda w: pkg_flashing(w, args.prebuilt, docs), 'Firmware_Flashing'),
                                        (pkg_panel, 'Face_Panel_Print'), (pkg_pcb, 'PCB_JLCPCB'), (pkg_3d, '3D_Print'),
                                        (lambda w: pkg_docs(w, docs), 'Documents')], 1):
            w = os.path.join(work, f'p{i}'); os.makedirs(w)
            root, top = fn(w)
            z = os.path.join(dist, f'STRUTHIO_ONE_{i}_{name}.zip'); zip_dir(root, z, top); made.append(z)
        made += pkg_backup(dist, commit)
    lines = [f'STRUTHIO ONE packages · commit {commit} · {today}', '']
    for z in made:
        lines.append(f'{os.path.getsize(z) / 1e6:7.2f} MB  {sha(z)}  {os.path.basename(z)}')
    text(os.path.join(dist, 'PACKAGES.txt'), '\n'.join(lines))
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
