#!/usr/bin/env python3
"""STRUTHIO HANDHELD · Build Manual 1.5 -> 1.6: the A1.5 implementation loops closed.

Edits the owner's 1.5 FINAL docx in place and in its own styles: every "requires
v0.12 / CAD revision required / pending / v0.11 ZIP omits struthio.pak" line
becomes the real state (v0.12 reads the DART rocker and writes settings only on
change; cad/a15 is the print authority; CP1 Gerbers and the CM1 drawing exist;
the v0.12 package carries both prebuilt assets), and the A1.5 figures, CAD
numbers, ordering steps, checklists, FAQ and verification rows are added.
    python3 tools/manual/expand_v16.py S15.docx FIG_DIR OUT.docx
FIG_DIR holds service.png (service_shot.c); everything else is read from cad/a15.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docxkit as K
from PIL import Image, ImageChops

SRC, FIG, OUT = sys.argv[1:4]
HH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
A15 = lambda *p: os.path.join(HH, 'cad', 'a15', *p)
FG = lambda n: os.path.join(FIG, n)

def cropped(path, name, pad=24):
    """renders have wide empty margins; trim them so the part fills the figure"""
    im = Image.open(path).convert('RGB')
    bg = Image.new('RGB', im.size, im.getpixel((0, 0)))
    x0, y0, x1, y1 = ImageChops.difference(im, bg).getbbox()
    out = FG(name)
    im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad))).save(out)
    return out

K.open_doc(SRC)
At = K.At

# ---- title -------------------------------------------------------------------------------------
K.replace_in(K.para('STRUTHIO HANDHELD BUILD MANUAL 1.5'), 'MANUAL 1.5', 'MANUAL 1.6')
K.replace_in(K.para('Prepared for R.A. Peddycoart'), 'v0.11 software baseline + A1.5 locked silicone controls',
             'v0.12 software + A1.5 CAD, STRUTHIO-CP1 Gerbers and STRUTHIO-CM1 drawing for the locked silicone controls')

# ---- quick start -------------------------------------------------------------------------------
qs = K.table_hdr('GateWhat you do')
r3 = K.row_with(qs, 'A0: wire LEFT / RIGHT wings')
K.set_cell(K.cells(r3)[1], 'A0: wire LEFT / RIGHT wings to GPIO17 / GPIO18 + GND. A1.5: STRUTHIO-CP1 adds DART LEFT GPIO21 and DART RIGHT GPIO38 (read by v0.12).')
K.set_cell(K.cells(r3)[2], 'A0 wings register; on A1.5 the service screen counts ROCKER L and R presses.')
K.set_cell(K.cells(r3)[3], 'Permanent A1.5 control PCB before the A0 pass')
r8 = K.row_with(qs, 'Print revised A1.5 front')
K.set_cell(K.cells(r8)[1], 'Print the A1.5 front (cad/a15/stl) as a silicone-control fit coupon, then the rear shell.')
K.replace_in(K.para('Beginner ZIP checks:'),
             'The uploaded v0.11 ZIP includes PREBUILT struthio_music.ima but omits the unchanged visual struthio.pak; copy the known-good prebuilt struthio.pak from v0.9 into handheld/build/assets/ (or use a later package that explicitly includes it).',
             'The v0.12 ZIP includes both PREBUILT assets, struthio.pak and struthio_music.ima, in handheld/build/assets/.')

# ---- earlier "what x.y" notes: mark the 1.5 boundary as closed -----------------------------------
K.replace_in(K.para('• One authoritative greybox'), 'so source it from v0.9 or a later package that explicitly includes it.',
             'so source it from v0.9 or a later package that explicitly includes it. (1.6: the v0.12 ZIP includes it.)')
K.replace_in(K.para('• Audio language now matches reality'), 'STRUTHIO game audio is still pending.',
             'STRUTHIO game audio is still pending. (1.4 added it.)')
K.replace_in(K.para('• FINAL INPUT MAP'), 'GPIO21/38 direct-DART support requires the next firmware package; v0.11 does not read them.',
             'v0.12 reads GPIO21/38 directly (see What 1.6 completes).')
K.set_text(K.para('IMPLEMENTATION BOUNDARY'),
           'IMPLEMENTATION STATUS (1.6): the firmware and CAD work these locks required is done. v0.12 reads GPIO21/38 and saves '
           'settings only on change; cad/a15 models the silicone mat, DART rocker, PUI chamber, THOR battery and E-Switch. '
           'What remains is physical: CP1 boards, CM1 samples, a printed fit coupon and the real-board tests.')

# ---- What 1.6 completes (new section before SOURCE OF TRUTH) -------------------------------------------
a = At(K.before_break(K.para('SOURCE OF TRUTH')))
a.h1('What 1.6 completes — v0.12 firmware, A1.5 CAD, control PCB')
a.p('Edition 1.5 locked the A1.5 hardware and listed five loops to close before calling A1.5 build-ready. '
    'The first four are work a computer can finish, and 1.6 finishes them. The fifth needs your bench, your board and your ears.')
a.table(['Loop (from 1.5)', 'Status in 1.6', 'Where it is'], [
    ['1. Firmware v0.12: direct DART + hard-power NVS policy', 'DONE. GPIO21 / GPIO38 read at 1 kHz with the wings\' 8 ms debounce; one press = one dart that way. '
     'High score, DART mode and volume are written only when they change, and every flash write is read back.',
     'firmware/main/struthio_buttons.c, main.c, sdkconfig.defaults; host test "rocker"'],
    ['2. A1.5 CAD', 'DONE. Silicone mat pocket, 44 x 9 mm DART rocker, PUI chamber, THOR cavity, E-Switch, USB path, new sticker. 50 of 50 fit checks pass.',
     'cad/a15/STRUTHIO15.scad, stl/, svg/, dxf/, renders/, check_a15.py'],
    ['3. CP1 PCB + CM1 drawing', 'DONE for ordering. CP1 Gerbers pass their own design-rule check; the CM1 drawing is ready to send for quotes. '
     'Quotes and first samples are your step.', 'cad/a15/cp1/cp1_gerbers.zip; cad/a15/drawings/STRUTHIO-CM1_drawing.pdf, STRUTHIO-CP1_drawing.pdf'],
    ['4. v0.12 package with matched assets', 'DONE. One ZIP, both prebuilt assets included; no v0.9 pack hunting.',
     'STRUTHIO_HANDHELD_v0.12.zip: handheld/build/assets/struthio.pak + struthio_music.ima'],
    ['5. Real-board audio / runtime / control validation', 'OPEN: yours. Nothing in this edition has been flashed, printed, fabricated or molded yet.',
     'Steps 7–12, Shop Sheets B, C and E'],
], widths=[2.2, 4.2, 2.8], size=9)
a.h2('The one size change: 88 x 134 mm')
a.p('You chose to keep every locked control size and grow the body at the bottom only. The rocker below the wings needed about 3–4 mm. '
    'The CAD needs 6 mm, because the speaker sits behind CP1 between the wings and must also clear the board\'s USB-C plug. '
    'The result is 88 x 134 x 23 mm (A0.8.4: 88 x 128 x 23). The top edge, screen opening, lens land, board datums and top screws are unchanged. '
    'The bottom arch is dropped for a flat, stronger lower rail.')
a.callout('USB-C CAVEAT: the position of the board\'s own USB-C connector is NOT confirmed. The CAD assumes bottom centre (as A0) with a '
          'right-angle plug turning into a channel to a panel jack at x = +19.25 mm. If your board\'s connector is elsewhere, change USB_PLUG_* '
          'in STRUTHIO15.scad and re-run check_a15.py. The extra 2 mm may then not be needed.', fill='FCE4D6')
a.figure(A15('drawings', 'a15_face_layout.png'), 'FIGURE 1.6A — A1.5 face layout (cad/a15/drawings/a15_face_layout.png). '
         'All control dimensions are measured from the speaker-window centre (0, −47).', width=6.4)
a.figure(A15('renders', 'a15_struthio_front.png'), 'FIGURE 1.6B — A1.5 front: the new sticker art composed onto the CAD render. A preview, not a photograph.', width=3.2)
a.h2('Still to confirm on the parts in your hand')
a.bullets([
    ('Board USB-C position: ', 'see the caveat above.'),
    ('E-Switch pins: ', 'the body (12.7 x 6.6 x 6.71 mm), the 4.72 mm actuator and its 2.16 mm travel are modelled from distributor listings of '
     'the E-Switch drawing; the pin positions and actuator width (2.0 mm assumed) must be checked against the drawing or the part.'),
    ('Header positions for GPIO21 / GPIO38: ', 'as for GPIO17/18, confirm the header pin on your board revision.'),
    ('PUI frame: ', 'modelled as a 28 mm round; if your part has the square frame, re-check the 29.2 mm pocket.'),
    ('Feel: ', 'travel and snap are set by the CM1 web the molder builds; the CAD only proves the geometry (rest heights, stops, clearances).'),
])
a.source('E-Switch 500SSP1S1M7QEA dimensions: e-switch.com 500 Series product page, and the distributor listings on octopart.com, '
         'alldatasheet.com and futureelectronics.com (the e-switch.com drawing itself could not be downloaded for this edition).')

# ---- SOURCE OF TRUTH table --------------------------------------------------------------------------
st = K.table_hdr('PriorityAuthority')
r4 = K.row_with(st, 'A0.8.4 CAD envelope')
K.set_cell(K.cells(r4)[1], 'A1.5 CAD (cad/a15/STRUTHIO15.scad, check_a15.py); A0.8.4 is the historical baseline')
K.set_cell(K.cells(r4)[2], 'Mechanical geometry: silicone controls, DART rocker, PUI chamber, THOR cavity, E-Switch, USB path')
K.set_cell(K.cells(K.row_with(st, 'Build Manual 1.5'))[1], 'Build Manual 1.6')

# ---- Step 2 / 3: parts and the zip -------------------------------------------------------------------
cp = K.table_with('Revised A1.5 printed shell + silicone control carrier')
K.set_cell(K.cells(K.row_with(cp, 'Revised A1.5 printed shell'))[2], 'A1.5 CAD released (cad/a15/stl): print the front as a fit coupon first.')
K.replace_in(K.para('Unzip STRUTHIO_HANDHELD_v0.11'), 'STRUTHIO_HANDHELD_v0.11', 'STRUTHIO_HANDHELD_v0.12')
K.replace_in(K.para('Unzip STRUTHIO_HANDHELD_v0.12'),
             'The uploaded v0.11 package contains struthio_music.ima but omits the unchanged visual struthio.pak; for the full-art gate, copy the known-good struthio.pak from v0.9 into handheld/build/assets/ or use a later package that explicitly includes it.',
             'The v0.12 package contains both prebuilt assets, struthio.pak and struthio_music.ima, in handheld/build/assets/.')
z = K.table_hdr('Folder or file')
pak = K.row_with(z, 'build/assets/struthio.pak')
K.set_cell(K.cells(pak)[1], 'Prebuilt 8.3 MB visual asset pack. Included in the v0.12 ZIP.')
K.set_cell(K.cells(pak)[2], 'Yes: flashed by idf.py flash (move it aside only for the deliberate greybox test)')
cad_row = [tr for tr in K.rows(z) if K.el_text(K.cells(tr)[0]).startswith('cad/')]
like = cad_row[0] if cad_row else K.rows(z)[-1]
K.add_row(z, ['cad/a15/', 'A1.5 print authority: STRUTHIO15.scad, STLs, sticker cut file, outlines, renders, fit checks; cp1/ (Gerbers) and drawings/ (CM1, CP1).',
              'For printing and ordering'], after=like, like=like)
K.replace_in(K.para('For a normal build, do NOT run'),
             'The visual pack is prebuilt, but the uploaded v0.11 ZIP omits the unchanged struthio.pak. Copy the known-good v0.9 struthio.pak into handheld/build/assets/ (or use a later package that explicitly includes it).',
             'The visual pack is prebuilt and the v0.12 ZIP includes it at handheld/build/assets/struthio.pak.')

# ---- Step 6: controls ---------------------------------------------------------------------------------
K.replace_in(K.para('A0 still has LEFT, RIGHT and GND.'), 'The new DART pins are a hardware lock for v0.12; current v0.11 does not read them.',
             'v0.12 reads the DART pins: each press of a rocker end fires one dart toward that side.')
K.set_text(K.para('FIGURE 6.A'), 'FIGURE 6.A — A1.5 locked wiring. v0.12 reads GPIO21 / GPIO38 directly: one press of a rocker end = one dart that way.')
a = At(K.before_break(K.para('Step 7 — Bench-test the controls')))
a.h2('A1.5 control stack — what 1.6 adds to order and build')
a.p('The silicone mat (CM1) sits in a printed carrier behind the front shell. Its keys pass through the shell openings and are held by a flange '
    'all round. CP1 sits behind the mat: four gold comb contacts on the front, the wire pads on the back. The speaker sits behind CP1, '
    'gasketed front and back, and fires through a 13 mm window in CP1 and the mat into the grille between the wings.')
a.table(['z (mm from front face)', 'Layer'], [
    ['0 – 3.0', 'Front shell'], ['3.0 – 4.6', 'Printed carrier (holds CM1, locates CP1 on two heat-stake pins)'],
    ['4.6 – 5.6', 'CM1 web (wing travel 1.5, rocker-end travel 1.3)'], ['5.6 – 6.6', 'STRUTHIO-CP1, 1.0 mm FR-4'],
    ['6.6 – 7.2', 'Speaker front gasket'], ['7.2 – 12.4', 'PUI AS02808MR-R; closed rear tube up to the rear shell'],
], widths=[1.5, 5], size=9)
a.p('The rocker has a centre stop 1.1 mm deep: a flat press on the middle stops before either pill touches, so it never fires both ends. '
    'A one-end press moves the centre only 0.84 mm.')
a.figure(A15('drawings', 'STRUTHIO-CM1_drawing.png'), 'FIGURE 6.B — STRUTHIO-CM1 manufacturer drawing (PDF: cad/a15/drawings/STRUTHIO-CM1_drawing.pdf). '
         'Outline DXF: cad/a15/dxf/mat_outline.dxf.', width=6.4)
a.figure(A15('drawings', 'STRUTHIO-CP1_drawing.png'), 'FIGURE 6.C — STRUTHIO-CP1 drawing (PDF: cad/a15/drawings/STRUTHIO-CP1_drawing.pdf).', width=6.4)
a.figure(A15('cp1', 'cp1_layers.png'), 'FIGURE 6.D — CP1 copper as generated: front combs and GND bus (left), back traces and the wire-pad row (right).', width=6.4)
a.h2('Ordering CP1 (control PCB)')
a.steps([
    'Upload cad/a15/cp1/cp1_gerbers.zip to any PCB maker that accepts Gerber + Excellon files.',
    'Choose: 2 layers, FR-4, 1.0 mm thick, 1 oz copper, ENIG finish (not HASL: the contacts must be flat gold), any mask colour, white legend.',
    'Board size is 82.19 x 33.80 mm. The outline already includes the speaker window and the two post notches.',
    'Check the maker\'s preview against Figure 6.D before paying: four combs on the front, five wire pads labelled G, L, DL, DR, R on the back.',
])
a.h2('Quoting CM1 (silicone mat)')
a.steps([
    'Send cad/a15/drawings/STRUTHIO-CM1_drawing.pdf (and the STL, cad/a15/stl/struthio_a15_mat.stl, if asked) to a silicone keypad molder.',
    'Ask for the locked values on the drawing: gold VMQ, 50 Shore A ±5, 6.0 mm x 0.5 mm carbon pills ≤100 Ω; wings 1.5 mm / 125 g / 45–55 % snap; '
    'rocker ends 1.3 mm / 150 g / 40–50 % snap.',
    'Ask for first samples with measured force-travel curves. The molder designs the web that gives the feel; the drawing fixes the outline, '
    'key faces, pill positions and heights.',
    'Before samples arrive you can print the mat STL in TPU or resin as a shape check only. It will not feel right or make contact.',
])

# ---- Step 7: service screen, DART -----------------------------------------------------------------------
K.replace_in(K.para('A0 / v0.11 still uses Trial C'), 'A0 / v0.11 still uses Trial C', 'A0 / v0.12 still defaults to Trial C')
K.replace_in(K.para('A0 / v0.12 still defaults to Trial C'),
             'v0.12 should translate those contacts directly into directional dart commands without disturbing flap, steering or the 100 ms STRAIGHT wing chord.',
             'v0.12 does exactly that: each rocker-end press (the same 8 ms debounce as the wings) queues one dart toward that side, as the browser\'s '
             'own DART key does, without touching flap, steering or the 100 ms STRAIGHT chord. The rocker works in every DART mode. On A1.5, set the mode '
             'to ROCKER ONLY in service mode (LEFT tap) so holding the wings never darts. The default stays Trial C so a rocker-less A0 bench stays playable.')
K.replace_in(K.para('After greybox play works, copy/restore'),
             'The uploaded v0.11 ZIP omits this unchanged visual file, so use the established pack from v0.9 or a later package that includes it.',
             'The v0.12 ZIP includes it at that path.')
K.replace_figure('FIGURE 7.1', FG('service.png'))
sv = K.table_hdr('LineMeaning')
dr = K.row_with(sv, 'DART <trial>')
K.set_cell(K.cells(dr)[1], 'Active DART mode (A, B, C or ROCKER ONLY) and darts fired, wings and rocker together.')
K.add_row(sv, ['ROCKER L UP|DOWN <n>   R UP|DOWN <n>', 'Live state of each DART-rocker end (GPIO21 / GPIO38) and its press count.',
               'DOWN only while pressed; +1 per press; FIRED rises with it'], after=dr, like=dr)
tap = K.row_with(sv, 'LEFT TAP / LEFT HOLD')
K.replace_in(K.cells(tap)[1].find(K.qn('w:p')), 'LEFT tap: next DART trial (saved).', 'LEFT tap: next DART mode, A, B, C, ROCKER ONLY (saved).')
K.replace_in(K.para('A0 v0.11 has no DART button'), 'A0 v0.11 has no DART button and therefore tested',
             'A0 has no DART button and therefore tested')
K.replace_in(K.para('Trial A and B misfire frequently'), 'A1.5 removes that ambiguity with direct DART contacts.',
             'A1.5 removes that ambiguity with direct DART contacts. Played through the same four bot timelines, the rocker fires every dart the bot '
             'asked for and nothing else (27/27, 291/304, 63/63, 82/84; the few missing are re-presses faster than a thumb can make).')

# ---- Step 8: speaker and battery --------------------------------------------------------------------------
K.set_text(K.para('CAD starting target: reserve at least'),
           'A1.5 CAD: a 29.2 mm seating pocket and 6.3 mm between the front and rear gaskets (≥5.8 required), behind CP1, which with the carrier '
           'is the rigid front baffle. The front gasket seals 0.8 mm all round the 13 mm window; a closed tube carries the rear cavity up to the rear '
           'shell. The grille is 5 slots. Do not finalize grille open area until the real assembled shell has been listened to.')
K.replace_in(K.para('5. Battery selection is already locked'),
             'The A1.5 CAD target cavity is at least approximately 36 x 54 x 6.2 mm',
             'The A1.5 CAD cavity is 37.4 x 55.4 x 6.35 mm (≥36 x 54 x 6.2 required)')

# ---- Step 9: enclosure ---------------------------------------------------------------------------------
K.set_text(K.para('Now the CAD becomes physical.'),
           'Now the CAD becomes physical. A1.5 (cad/a15/STRUTHIO15.scad) is the print authority. It keeps A0.8.4\'s screen, board and crown datums and adds '
           'the silicone controls, DART rocker, PUI chamber, THOR cavity and E-Switch. To fit the rocker below the wings and the speaker clear of the '
           'board\'s USB-C plug, the body grows 6 mm at the bottom only: 88 x 134 mm. A0.8.4 stays in cad/a1 as the historical baseline.')
K.set_text(K.para('If you print anything before A1.5 CAD is complete'),
           'Print the A1.5 front first, in PLA, as a fit coupon. Confirm the LCD opening, board width and lens land, then the carrier, CP1 and speaker seat.')
K.replace_in(K.para('Do NOT print the old A0.8.4 wing caps'),
             'After A1.5 CAD is available, print a front/control fit coupon first, then test the actual silicone sample and control PCB together.',
             'Print the A1.5 front/control fit coupon first, then test the actual silicone sample and control PCB together.')
K.replace_figure('A0.8.4 CAD export view', cropped(A15('renders', 'internals_angle.png'), 'a15_internals_angle.png'),
                 'FIGURE 9.A — A1.5 inside the shell (cad/a15/renders): board, CP1, speaker with its rear tube, E-Switch on the left wall. '
                 'Right: the front with the CM1 keys through it.')
K.set_text(K.para('• Before A1.5 CAD exists'),
           '• Print the A1.5 front (cad/a15/stl/struthio_a15_front.stl) as the front/control fit coupon first. Print from A0.8.4 only for a historical comparison.')
K.set_text(K.para('A0.8.4 baseline CAD numbers'), 'A0.8.4 baseline CAD numbers — historical reference')
a = At(K.para('A0.8.4 baseline CAD numbers — historical reference'))
a.h2('A1.5 CAD numbers (cad/a15/STRUTHIO15.scad)')
a.p('All dimensions in millimetres. x right, y up, from the board centre line; z from the front face back. Change a number at the top of the file, '
    'export again, and run the checks. Do not edit the STL files themselves.')
a.table(['Parameter', 'Value', 'What it controls'], [
    ['BODY_W x (BODY_H + BOTTOM_EXT)', '88 x 134 (128 + 6)', 'Outer footprint; grows at the bottom only; depth 23 as A0.8.4'],
    ['BOTTOM_ARCH', 'false', 'Flat lower rail (A0.8.4 had a 1.8 mm arch)'],
    ['BTN_X, BTN_Y', '±24, −46', 'Wing key centres; faces 28 x 18.5'],
    ['Rocker', '44 x 9 face at y −61.2; contacts x ±12', 'DART rocker; contacts 24.0 apart'],
    ['Travel (pill face above CP1)', 'wings 1.5, rocker ends 1.3', 'Locked travel; rocker centre stop 1.1'],
    ['SPKR_X, SPKR_Y', '0, −52.6', 'PUI centre behind CP1; window Ø13 at (0, −47); pocket Ø29.2'],
    ['BAT_W x BAT_H x BAT_T, BAT_Y', '36 x 54 x 6.2, 13.5', 'THOR-503450 (cavity 37.4 x 55.4 x 6.35)'],
    ['SCREW_X, SCREW_Y / SCREW_Y_BOT', '±37, 55.5 / −63', 'Four rear M2-class screws; the lower pair moved below the wing skirts'],
    ['USB_PLUG_*', 'x −6..16, y −37.5..−32.8, z 7.5..14', 'Right-angle plug keep-out (board connector position: CONFIRM)'],
    ['USB channel / jack', 'x 16.5..22; jack at x +19.25', 'Path to the bottom-wall panel jack'],
    ['E-Switch', 'left wall (x −38.25), y 12', 'BAT+ hard cut; actuator 2.1 proud; the right side keeps the BOOT / RESET service slot'],
    ['STICKER_TOP / BOTTOM, widths', '−27.2 / −68.0, 82 / 86', 'Art panel: 2 wing holes, rocker hole, 5 grille slots'],
], widths=[2.4, 2.4, 4.2], size=9)
a.h2('A1.5 export / check commands')
a.code(['cd handheld/cad/a15', './export_a15.sh            # needs OpenSCAD 2021.01 or newer, Python trimesh + shapely',
        '#  -> stl/struthio_a15_front.stl, _back.stl, _mat.stl',
        '#  -> svg/struthio_a15_front_sticker.svg, dxf/ (CP1, CM1, key outlines), renders/, art/',
        '#  -> A1.5 CHECK: all pass   (50 checks)',
        'python3 check_a15.py       # the checks alone',
        'python3 cp1/make_cp1.py    # CP1 Gerbers + CP1 DRC: all pass',
        'python3 drawings/make_drawings.py   # CM1 / CP1 drawings'])
a.p('What the checks prove: every part is one watertight solid; each key passes its opening with ≥0.25 mm clearance and is captured by ≥0.5 mm of flange; '
    'each pill rests exactly its locked travel above CP1; CP1 and the mat clear the board and the screw posts; the speaker window is sealed; '
    'the speaker clears the USB plug keep-out (1.1 mm); the battery and E-Switch volumes are free of plastic; every sticker hole sits inside the sticker.')
K.set_text(K.para('A0.8.4 historical export / check commands'), 'A0.8.4 historical export / check commands')
K.set_text(K.para('The included A0.8.4 STL/SCAD files remain useful'),
           'The A0.8.4 STL/SCAD files in cad/a1 remain for historical geometry checks. The A1.5 files in cad/a15 carry the silicone, DART, PUI, THOR '
           'and hard-power geometry and are checked by check_a15.py.')
K.set_text(K.para('Print settings: starting points'), 'Print settings: starting points for fit coupons and A1.5 parts')

# ---- Step 10: sticker -----------------------------------------------------------------------------------
stk = K.table_hdr('File (cad/a1/)')
K.set_cell(K.cells(K.rows(stk)[0])[0], 'File (cad/a15/)')
K.set_cell(K.cells(K.row_with(stk, 'art/sticker_front_print.png'))[1], 'The print file: 600 dpi, 2056 x 1038 px = 87.0 x 43.9 mm including bleed.')
svr = K.row_with(stk, 'svg/struthio_a084_front_sticker.svg')
K.set_cell(K.cells(svr)[0], 'svg/struthio_a15_front_sticker.svg')
K.set_cell(K.cells(svr)[1], 'A1.5 cut outline: the outer edge, two wing openings, the DART rocker opening and five grille slots.')
K.replace_in(K.para('2. Measure the printed art with a ruler'), '81.2 mm', '87.0 mm')
K.set_text(K.para('4. A0.8.4 reference only'),
           '4. Cut along the A1.5 outline (svg/struthio_a15_front_sticker.svg): outer edge, both wing openings, the rocker opening and the five grille slots. '
           'The proof (art/sticker_front_proof.png) shows the cut lines on the art.')
K.replace_in(K.para('5. Dry-fit on the printed front'), 'the wing caps and grille slots', 'the silicone wings, DART rocker and grille slots')
K.replace_figure('FIGURE 10.1', A15('art', 'sticker_front_proof.png'),
                 'FIGURE 10.1 — The A1.5 sticker proof with its cut lines (cad/a15/art/sticker_front_proof.png). Figure 1.6B shows it on the shell.')

# ---- Step 11: assembly ---------------------------------------------------------------------------------
K.replace_in(K.para('Hard power-off is acceptable for this design'),
             'v0.12 should enable NVS erase verification and avoid periodic background writes. Save high score/settings only on discrete changes.',
             'v0.12 does this: it writes high score, DART mode and volume only when they change, never periodically, and reads back every '
             'flash write (CONFIG_SPI_FLASH_VERIFY_WRITE).')
K.replace_in(K.para('Battery is now locked to THOR-503450, 1000 mAh.'),
             'Revise the CAD cavity to at least approximately 36 x 54 x 6.2 mm so',
             'The A1.5 CAD cavity is 37.4 x 55.4 x 6.35 mm (≥36 x 54 x 6.2) so')
K.replace_in(K.para('The portrait board orientation places'), 'to the bottom opening.',
             'to the bottom opening. A1.5 assumes a right-angle plug at the board (connector position: confirm) and a panel jack at x = +19.25 mm.')
K.replace_figure('Historical A0 rear-layout reference only', cropped(A15('renders', 'internals.png'), 'a15_internals.png'),
                 'FIGURE 11.A — A1.5 internals from the front (cad/a15/renders/internals.png): board, CP1 below it with the speaker, USB channel '
                 '(purple), E-Switch on the left. For electrical wiring use Figure 6A and Shop Sheet F.', max_h_in=4.6)
K.replace_in(K.para('• 5. Route controls'), 'Do not expect GPIO21/38 direct DART to work until v0.12 firmware is installed.',
             'v0.12 reads GPIO21/38: check both ROCKER counts in service mode, then set DART mode to ROCKER ONLY.')

# ---- software chapter: what is not finished -----------------------------------------------------------------
p = K.para('• A1.5 DART hardware is locked')
K.set_text(p, '• A1.5 DART: v0.12 reads the two-contact rocker on GPIO21/38 (host-tested on the four bot timelines); not yet pressed on a real board. '
              'A0 keeps Trial C as the default.')
a = At(p.getnext())
a.bullets(['A1.5 CAD, CP1 Gerbers and the CM1 drawing are generated and checked on the desktop; nothing has been printed, fabricated or molded yet.'])

# ---- Shop Sheet A ---------------------------------------------------------------------------------------
bom = K.table_hdr('QtyPart')
K.set_cell(K.cells(K.row_with(bom, 'STRUTHIO-CM1;'))[4], 'LOCKED; drawing cad/a15/drawings/STRUTHIO-CM1_drawing.pdf; quote + first samples')
K.set_cell(K.cells(K.row_with(bom, 'STRUTHIO-CP1;'))[4], 'LOCKED; Gerbers cad/a15/cp1/cp1_gerbers.zip (ENIG, 1.0 mm)')
K.set_cell(K.cells(K.row_with(bom, 'A1.5 control harness'))[4], 'LOCKED wiring; read by v0.12')
K.set_cell(K.cells(K.row_with(bom, 'Printed A1.5 shell'))[4], 'A1.5 CAD released: cad/a15/stl (front coupon first)')
st_row = K.row_with(bom, 'Front art sticker')
K.set_cell(K.cells(st_row)[2], 'Printed + laminated; A1.5 art around the DART rocker')
K.set_cell(K.cells(st_row)[4], 'cad/a15/art + svg/struthio_a15_front_sticker.svg')

# ---- Shop Sheet B / C checklists ---------------------------------------------------------------------------
for side in ('LEFT', 'RIGHT'):
    K.replace_in(K.para(f'☐ GPIO{21 if side == "LEFT" else 38} = DART {side}'), '(A1.5; direct firmware support required)', '(A1.5; read by v0.12)')
K.set_text(K.para('☐ A0 Trial C tested'), '☐ A0 Trial C tested; A1.5: ROCKER L and R each count +1 per press in service mode, DART mode set to ROCKER ONLY, rocker feel validated')
K.set_text(K.para('☐ Known-good prebuilt struthio.pak sourced'), '☐ struthio.pak (in the v0.12 ZIP at handheld/build/assets/) flashed for the full-art gate')
K.set_text(K.para('☐ CAD checks: export script reports all checks pass.'),
           '☐ CAD checks: cad/a15/export_a15.sh reports "A1.5 CHECK: all pass" and cp1/make_cp1.py "CP1 DRC: all pass".')
a = At(K.para('☐ CAD checks: cad/a15/export_a15.sh').getnext())
a.checks(['Board USB-C connector position measured; USB_PLUG_* matches it (or changed and check_a15.py re-run).',
          'E-Switch pins checked against the E-Switch drawing / the part before the cradle is printed in the final material.',
          'CP1 delivered: ENIG, 1.0 mm; continuity from each comb to its wire pad; no comb shorted to GND at rest.'])

# ---- Shop Sheet F ----------------------------------------------------------------------------------------
pins = K.table_hdr('FunctionGPIO pins')
for name in ('DART LEFT', 'DART RIGHT'):
    K.set_cell(K.cells(K.row_with(pins, name))[2], 'A1.5 input, pull-up, active low; read by v0.12 (one press = one dart). Header pin: confirm.')
wires = K.table_hdr('#From')
for w, pad in (('W1', 'L'), ('W2', 'R'), ('W3', 'DL'), ('W4', 'DR'), ('W5', 'G')):
    tr = K.row_with(wires, w + 'GPIO') if w != 'W5' else K.row_with(wires, 'W5')
    c = K.cells(tr)
    note = {'W3': 'A1.5; read by v0.12', 'W4': 'A1.5; read by v0.12'}.get(w, K.el_text(c[4]))
    K.set_cell(c[4], f'{note}; CP1 pad {pad}')
a = At(K.para('From firmware/main/board_pins.h and Waveshare').getnext())
a.note('CP1 wire pads are on the back of the board, labelled G, L, DL, DR, R on the silkscreen (2.54 mm pitch). Wire by the labels.')

# ---- FAQ ---------------------------------------------------------------------------------------------------
K.replace_in(K.para('Can I really switch it off like a Game Boy?'),
             'v0.12 should avoid periodic writes and enable erase verification for extra robustness.',
             'v0.12 writes settings only when they change and reads back every flash write.')
K.replace_in(K.para('Which DART trial is best?'), 'Trial C remains the A0/v0.11 fallback.', 'Trial C remains the A0 default.')
K.replace_in(K.para('Which DART trial is best?'), 'on GPIO21 / GPIO38 once v0.12 support is installed.',
             'on GPIO21 / GPIO38, read by v0.12. On A1.5 set DART mode to ROCKER ONLY in service mode.')
a = At(K.para('The log scrolls too fast to read.'))
a.p('The A1.5 body is 88 x 134 mm, the 1.5 decision said about 3–4 mm. The rocker alone needed that; the speaker between the wings must also clear the '
    'board\'s USB-C plug, which takes the total to 6 mm. If your board\'s connector is not where the CAD assumes, the extra may not be needed.',
    bold_lead='Why is A1.5 6 mm taller than A0.8.4, not 3–4?  ')
a.p('Yes. cad/a15/cp1/cp1_gerbers.zip is ready for a PCB maker: 2 layers, 1.0 mm, ENIG. It is cheap, so order it before the silicone samples.',
    bold_lead='Can I order CP1 now?  ')

# ---- implementation loops: status -------------------------------------------------------------------------------
K.set_text(K.para('IMPLEMENTATION WORK GENERATED BY THE 1.5 HARDWARE LOCK'), 'IMPLEMENTATION WORK GENERATED BY THE 1.5 HARDWARE LOCK — STATUS IN 1.6')
K.set_text(K.para('Before calling A1.5 build-ready, close these five loops'),
           '1.5 listed five loops to close, in order, before calling A1.5 build-ready. 1.6 closes the four a computer can close. '
           'The fifth, real-board audio / runtime / control validation, is yours.')
for prefix, tag, where in [
        ('• Firmware v0.12: add active-low', 'DONE', ' → firmware/main/struthio_buttons.c, service.c; host test "rocker".'),
        ('• Firmware v0.12 hard-power hardening', 'DONE', ' → implemented as write-on-change (main.c app_save_i32) plus read-back of every flash write (sdkconfig.defaults).'),
        ('• CAD A1.5: replace tact-switch wells', 'DONE', ' → cad/a15/STRUTHIO15.scad; checks in check_a15.py.'),
        ('• CAD A1.5 audio', 'DONE (grille tuning after listening)', ' → 29.2 pocket, 6.3 between gaskets, closed rear tube.'),
        ('• CAD A1.5 power', 'DONE (E-Switch pins: confirm)', ' → cavity 37.4 x 55.4 x 6.35; E-Switch on the left wall; USB channel + jack.'),
        ('• Artwork', 'DONE', ' → cad/a15/art, svg/struthio_a15_front_sticker.svg.'),
        ('• Packaging/docs', 'DONE', ' → STRUTHIO_HANDHELD_v0.12.zip includes struthio.pak and struthio_music.ima; this manual.')]:
    p = K.para(prefix)
    K.set_text(p, '• ' + tag + ' — ' + K.el_text(p)[2:] + where)
a = At(K.para('• Still fit-selected rather than architecture-locked'))
a.bullets([('DONE — CP1 PCB + CM1 drawing: ', 'cad/a15/cp1/cp1_gerbers.zip (CP1 DRC: all pass); cad/a15/drawings/STRUTHIO-CM1_drawing.pdf and STRUTHIO-CP1_drawing.pdf. '
            'Ordering CP1 and quoting CM1 are in Step 6.'),
           ('OPEN — Real-board validation: ', 'Steps 7–12 and Shop Sheets B, C, E: rocker counts, speaker and chamber listening test, measured runtime, 20 hard-power cycles.')])

# ---- appendix ---------------------------------------------------------------------------------------------
K.replace_in(K.para('• The v0.11 software core is well defined'), 'The v0.11 software core is well defined',
             'The v0.12 software core is well defined (it adds the DART rocker and the hard-power save policy)')
K.set_text(K.para('• The A0.8.4 shell envelope remains a strong baseline'),
           '• The A1.5 CAD (cad/a15) replaces A0.8.4 as print authority: 88 x 134 x 23 mm, 50 of 50 fit checks pass. A0.8.4 stays as the historical baseline.')
K.set_text(K.para('• Next actions are concrete'),
           '• Next actions are physical: order CP1, get CM1 quotes and samples, print the A1.5 front coupon, confirm the board\'s USB-C position, '
           'then run the audio, runtime and control tests on a real board.')
links = K.para('• E-Switch 500SSP1S1M7QEA / 500 Series')
a = At(links.getnext())
a.bullets(['E-Switch 500SSP1S1M7QEA distributor listings used for the CAD dimensions — https://octopart.com/part/e-switch/500SSP1S1M7QEA • '
           'https://www.alldatasheet.com/datasheet-pdf/pdf/587987/E-SWITCH/500SSP1S1M7QEA.html • '
           'https://www.futureelectronics.com/p/electromechanical--switches--slide/500ssp1s1m7qea-e-switch-8141762'])

ver = K.table_hdr('CheckResult')
last = K.row_with(ver, 'A1 CAD (A0.8.4)')
for vals in reversed([
        ['A1.5 CAD', '50 of 50 fit checks pass (check_a15.py): keys, travel, rocker stop, speaker seal, USB keep-out, battery, E-Switch, sticker'],
        ['STRUTHIO-CP1', 'CP1 DRC: all pass (clearance ≥0.25 mm, copper ≥0.4 mm from edges, each 6 mm pill bridges signal and GND); Gerbers re-read by gerbonara'],
        ['DART rocker (host test)', '4 bot timelines: 27/27, 291/304, 63/63, 82/84 darts; the missing ones are re-presses faster than a thumb; no other darts']]):
    K.add_row(ver, vals, after=last, like=last)

hist = K.table_hdr('EditionWhat changed')
K.add_row(hist, ['v0.12 / Build Manual 1.6', 'A1.5 loops closed: GPIO21/38 DART rocker + write-on-change saves (v0.12); A1.5 CAD 88 x 134 mm with 50 checks; '
                 'CP1 Gerbers + CM1/CP1 drawings; v0.12 ZIP with both prebuilt assets.'])

K.doc.save(OUT)
print('wrote', OUT)
