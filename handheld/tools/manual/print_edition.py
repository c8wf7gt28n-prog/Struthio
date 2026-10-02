#!/usr/bin/env python3
"""STRUTHIO HANDHELD · the print edition of the build manual.

Builds the whole manual from scratch in the owner's document styles (the
1.5 manual is used only as the style template: fonts, headings, Audio Guide
and Source Note styles, page size). Every command, log line, file name and
number matches the release package built by tools/package/make_package.py.

    python3 tools/manual/print_edition.py TEMPLATE.docx FIG_DIR USER_IMG_DIR OUT.docx [PAGES.json]

FIG_DIR: figs12.py + figs_print.py output and service.png.
USER_IMG_DIR: the owner's own pictures (heritage photos 06.png, illustrated
board sheet 12.png, browser screenshot 13.png); not stored in the repository.
PAGES.json: heading -> page, from a first PDF render, fills the contents page.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docxkit as K
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

TEMPLATE, FIG, USR, OUT = sys.argv[1:5]
PAGES = json.load(open(sys.argv[5])) if len(sys.argv) > 5 else {}
HERE = os.path.dirname(os.path.abspath(__file__))
HH = os.path.normpath(os.path.join(HERE, '..', '..'))
CAD = lambda *p: os.path.join(HH, 'cad', 'handheld', *p)
SCH = lambda n: os.path.join(HH, 'docs', 'schematics', 'png', n)
FG = lambda n: os.path.join(FIG, n)
UI = lambda n: os.path.join(USR, n)
DR = lambda n: os.path.join(HH, 'docs', 'renders', n)

doc = K.open_doc(TEMPLATE)
body = doc.element.body
sect = body.find(qn('w:sectPr'))
for el in list(body):
    if el is not sect: body.remove(el)
a = K.At(sect)

# ---- numbering helpers ----------------------------------------------------------------------------------
CH = {'n': 0, 'fig': 0, 'name': ''}
TOC = []
def chapter(title, number=None, newpage=True):
    CH['fig'] = 0
    CH['n'] = number
    TOC.append((1, title))
    a.h1(title, newpage=newpage)
import tempfile
from PIL import Image
TMP = tempfile.mkdtemp(prefix='struthio_figs_')
def prep(path, width_in, dpi=220):
    """print-resolution copy: at most `dpi` at the printed width; photo-like images as JPEG"""
    im = Image.open(path)
    if im.mode in ('RGBA', 'LA', 'P'):
        bg = Image.new('RGB', im.size, 'white'); im = im.convert('RGBA'); bg.paste(im, mask=im.split()[3]); im = bg
    else:
        im = im.convert('RGB')
    w = int(width_in * dpi)
    if im.width > w: im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    photo = len(im.resize((160, max(1, 160 * im.height // im.width))).getcolors(1 << 16) or range(9999)) > 3000
    out = os.path.join(TMP, f'{len(os.listdir(TMP)):03d}' + ('.jpg' if photo else '.png'))
    im.save(out, quality=88, optimize=True) if photo else im.save(out, optimize=True)
    return out
_fig = a.figure
a.figure = lambda path, caption, width=6.4: _fig(prep(path, width), caption, width)
def fig(path, caption, width=6.4):
    CH['fig'] += 1
    tag = f'FIGURE {CH["n"]}.{CH["fig"]}' if CH['n'] is not None else 'FIGURE'
    a.figure(path, f'{tag} — {caption}', width)
def rule(t): a.callout(t, fill='FFF2CC')
def stop(t): a.callout(t, fill='F8D7D3')
def ok(t): a.callout(t, fill='E2EFDA')
def code(*lines): a.code(list(lines))

# ---- page setup: footer with page numbers, header line ---------------------------------------------------
sec = doc.sections[0]
sec.different_first_page_header_footer = True
def field(par, instr):
    r = par.add_run(); f1 = OxmlElement('w:fldChar'); f1.set(qn('w:fldCharType'), 'begin'); r._r.append(f1)
    r2 = par.add_run(); it = OxmlElement('w:instrText'); it.set(qn('xml:space'), 'preserve'); it.text = instr; r2._r.append(it)
    r3 = par.add_run(); f2 = OxmlElement('w:fldChar'); f2.set(qn('w:fldCharType'), 'separate'); r3._r.append(f2)
    r4 = par.add_run('1')
    r5 = par.add_run(); f3 = OxmlElement('w:fldChar'); f3.set(qn('w:fldCharType'), 'end'); r5._r.append(f3)
    for r in (r4,): r.font.size = Pt(9)
fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = fp.add_run('STRUTHIO HANDHELD BUILD MANUAL  ·  '); r.font.size = Pt(8.5); r.font.color.rgb = RGBColor(0x70, 0x70, 0x70)
field(fp, 'PAGE')
doc.core_properties.title = 'STRUTHIO Handheld Build Manual'
doc.core_properties.subject = 'Print edition: from bare board to finished handheld'
doc.core_properties.author = 'R.A. Peddycoart'
doc.core_properties.comments = ''

# ======================================================================================================
# COVER
# ======================================================================================================
def centered(t, size, bold=False, color=None, space_after=6, italic=False):
    p = a._para(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(space_after)
    rr = p.add_run(t); rr.font.size = Pt(size); rr.bold = bold; rr.italic = italic
    if color: rr.font.color.rgb = RGBColor(*color)
    return p
centered('STRUTHIO HANDHELD', 34, True, (0x10, 0x28, 0x38), 2)
centered('BUILD MANUAL', 20, True, (0xB0, 0x7A, 0x14), 4)
centered('From bare board to a finished 1990s-style handheld: firmware, controls, sound, shell and final assembly', 11.5, False, (0x50, 0x50, 0x50), 10)
p = a._para(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run().add_picture(prep(FG('p10_hero.png'), 4.6, 300), width=Inches(4.6))
centered('Prepared for R.A. Peddycoart', 10.5, False, (0x50, 0x50, 0x50), 2)
centered('Use with the STRUTHIO_HANDHELD package (the struthio folder). Every command in this manual matches that package.', 9.5, False, (0x70, 0x70, 0x70), 0, True)

# ======================================================================================================
# CONTENTS (static, page numbers from a first render)
# ======================================================================================================
TOC_ANCHOR = None
def contents_page():
    global TOC_ANCHOR
    a.pagebreak()
    p = a._para('Heading 1'); p.add_run('CONTENTS')
    TOC_ANCHOR = a._para()      # the table goes in front of this paragraph at the end
contents_page()

# ======================================================================================================
# ABOUT THIS MANUAL
# ======================================================================================================
chapter('Before you start', None)
a.p('This manual takes you from a bare Waveshare ESP32-S3 board to a finished STRUTHIO handheld: power on, the game starts, two gold wing keys '
    'and a DART rocker play it, and the whole machine lives in a sculpted shell with its own speaker and battery. You do not need to be an '
    'engineer. You need patience, a soldering iron, a multimeter, a computer, and the discipline to prove one thing before adding the next.')
a.h2('How the manual works')
a.bullets([
    ('Gates. ', 'The build is a chain of gates (Quick Start). Each gate says what to do and what PASS looks like. Do not start a gate until '
     'the one before it passes.'),
    ('Two machines. ', 'First the bench build: the bare board on your desk, on USB power, with two loose switches. It proves the electronics '
     'and the game. Then the handheld: custom silicone controls, speaker, battery and the printed shell. The bench build is not a lesser '
     'version; it is the machine that proves everything the handheld depends on.'),
    ('The menu. ', 'The package has a build menu (STRUTHIO.bat on Windows, struthio.sh on macOS and Linux). Every option prints the exact '
     'command it runs, and this manual shows the same commands, so you can use either.'),
    ('"confirm". ', 'Anything that cannot be known from the project files (a header pin on your board revision, a connector position) is '
     'marked "confirm": check it on the part in your hand.'),
])
a.table(['You will see', 'It means'], [
    ['Blue AUDIO GUIDE block', 'The narrated "why": read it before doing the step.'],
    ['Yellow box', 'A rule or a gate you must pass.'],
    ['Red box', 'Stop: a safety rule, or something that can damage parts.'],
    ['Green box', 'What success looks like.'],
    ['Grey box, fixed-width font', 'Text you type, or text the board prints.'],
    ['"example" next to a number', 'An illustration, not a measurement. Record your own in Shop Sheet E.'],
], widths=[2, 5])
a.table(['If you are…', 'Read first', 'Then'], [
    ['new to electronics', 'Foundations (after Step 1)', 'Steps 2–8 in order, one gate at a time'],
    ['comfortable with Arduino / ESP32', 'Quick Start, Step 3', 'Steps 4–8; Shop Sheet F is your pin card'],
    ['only printing the shell', 'Steps 9–11', 'Never close a shell around an unproven board'],
    ['curious how the game works', '"How the software works"', 'Shop Sheet G, the glossary'],
    ['stuck', 'Step 13 and Shop Sheet D', 'Go back one gate'],
], widths=[2.2, 2.4, 3])
a.h2('Safety first')
stop('This is an adult prototype build, not a toy for children. A lithium cell can burn if it is punctured, shorted, over-charged or wired '
     'backwards: the battery goes in LAST, after everything works on USB power, and its polarity is checked with a meter first. A soldering '
     'iron is 350 °C: always return it to its stand. Work ventilated, wash your hands after soldering.')
a.p('You cannot damage the board by building or flashing software. You CAN damage it with a short circuit, a reversed battery, or a wire on '
    'the wrong pin. Be relaxed with commands and careful with wires.')

# ======================================================================================================
# QUICK START
# ======================================================================================================
chapter('QUICK START — the build in eleven gates', None)
fig(FG('p01_path.png'), 'The build path. Colours: computer, bench build on USB power, custom parts, the handheld.')
a.table(['Gate', 'What you do', 'PASS means', 'Menu / step'], [
    ['0', 'Install ESP-IDF 5.5.5; run the setup doctor and the desktop checks', 'Doctor: no FAIL. Desktop: GOLDEN REPLAY all 5 traces bit-exact', '1, D · Step 3'],
    ['1', 'Flash Waveshare\'s own example over USB-C', 'Display, USB and flashing work on your board', 'Step 4'],
    ['2', 'GREYBOX test: STRUTHIO with a flat-colour picture', 'Log reaches NEW RUN; a flat-colour game on screen', '4 · Step 5'],
    ['3', 'Wire two wing switches to GPIO17 / GPIO18 + GND', 'Service mode: each press counts +1', 'Step 6'],
    ['4', 'Service mode: the on-device golden replay', 'GOLDEN PASS 10011 TICKS', 'Step 7'],
    ['5', 'FULL ART: flash the art pack and the soundtrack', 'Log says renderer panel (asset pack); the real picture', '5 · Step 5'],
    ['6', 'Play a round on the loose switches', 'A complete round: the bench build PASSES', 'Step 7'],
    ['7', 'Speaker: vendor audio example, then STRUTHIO sound', 'AUDIO OK, MUSIC OK; clean sound at volume 1–2', 'Step 8'],
    ['8', 'Order STRUTHIO-CP1, get STRUTHIO-CM1 samples', 'Parts in hand, checked against the drawings', 'Step 9'],
    ['9', 'Print the shell: front fit coupon first, then the back', 'Keys free, no preload, nothing pinched', 'Step 10'],
    ['10', 'Lens and sticker; battery and power switch; close the shell', 'Shop Sheet C complete: the handheld PASSES', 'Steps 11–13'],
], widths=[0.6, 3.6, 3.4, 1.3], size=9)
ok('BENCH PASS: power on → STRUTHIO starts → a playable round is completed using only the physical buttons.\n'
   'HANDHELD PASS: both wings and both DART-rocker ends register cleanly; sound is clean; 20 hard OFF/ON cycles boot without errors; '
   'the shell closes without pinching anything.')
a.h2('The commands, in one place')
code('cd handheld                                  # desktop checks (gate 0)',
     'make -C host test',
     'make -C firmware/host_test run',
     '',
     'cd handheld/firmware                         # the board (gates 2 and 5)',
     'idf.py set-target esp32s3                    # once per fresh folder',
     'idf.py -p PORT -D STRUTHIO_ART=greybox build flash monitor',
     'idf.py -p PORT -D STRUTHIO_ART=full build flash monitor')
a.p('PORT is your board\'s serial port: COM5 or similar on Windows, /dev/cu.usbmodem… on macOS, /dev/ttyACM0 on Linux. Leave the log '
    'window with Ctrl + ]. The menu runs exactly these commands for you.')

# ======================================================================================================
# STEP 1
# ======================================================================================================
chapter('Step 1 — Understand what you are building', 1)
a.p('The STRUTHIO handheld is not a development board with a game added at the end. It is a dedicated handheld in the spirit of the early '
    '1990s: power on, play at once, two dominant controls, a bold front graphic, and a body shaped to be held.')
fig(FG('p11_front_back.png'), 'The finished handheld: front and back, rendered from the real CAD parts.')
a.audio('AUDIO GUIDE — Chapter 1: What you are building', [
    'The project has two physical stages. The bench build proves that the Waveshare ESP32-S3-Touch-LCD-3.5B runs STRUTHIO, reads real '
    'buttons, draws the game, survives power cycles and completes a round. The handheld is the finished object: the sculpted shell, the gold '
    'silicone wings and DART rocker, the printed art, the lens, the speaker, the battery and the power switch. Do not combine those jobs on '
    'day one. The bench build exists so that a problem is easy to find on the desk instead of hidden inside a finished enclosure.',
    'The software is already proven. The game was first written for the browser, STRUTHIO ARCADE 1.8.0. The handheld runs the same game '
    'rewritten in portable C, and on the desktop five recorded games covering 75,144 ticks match the browser exactly, tick for tick. Your job '
    'is not to redesign the game. Your job is to make the proven C system run on the real board.',
    'Reduce the project to three milestones: make the bare board show STRUTHIO; make physical switches control it; then put the proven machine '
    'into the shell. Sound, battery and finish come after those.'])
a.source('REAL HARDWARE REFERENCES — the Tiger and Konami handhelds below are real units supplied for the project. They show proportion, bezel '
         'depth, button dominance and how period hardware hides its technical parts. They are mood references, not fabrication authority.')
fig(UI('06.png'), 'Heritage references: the buttons dominate, the screen sits in a moulded bezel, the body is shaped for hands.', 6.0)
a.h2('The handheld at a glance')
a.table(['Item', 'STRUTHIO handheld'], [
    ['Board', 'Waveshare ESP32-S3-Touch-LCD-3.5B: ESP32-S3, 8 MB PSRAM, 16 MB flash, 3.5-inch 320 x 480 IPS display'],
    ['Size', '88 x 137.4 x 23 mm; sculpted shell: concave top and bottom, waist, flared hips, rolled pillow back'],
    ['Controls', 'STRUTHIO-CM1 gold silicone keys on STRUTHIO-CP1: LEFT and RIGHT WING (28 x 18.5 mm), a 44 x 9 mm DART rocker'],
    ['Sound', 'The browser game\'s sound effects and its 160-second soundtrack; PUI AS02808MR-R 28 mm speaker'],
    ['Power', 'USB-C (charge, flash, logs) and a THOR-503450 1000 mAh protected LiPo through an E-Switch hard cut in BAT+'],
    ['Game', 'STRUTHIO ARCADE 1.8.0 rules, 60 ticks per second; the picture is the browser\'s, drawn at panel size'],
], widths=[1.4, 6])
fig(FG('p12_colours.png'), 'Colour options: the shell and keys are printed and moulded, so the colours are yours to choose.')
a.h2('What stays a hands-on job')
a.bullets(['The first moulded STRUTHIO-CM1 sample confirms force, travel, snap and rebound against the targets.',
           'Runtime on the THOR-503450 is measured, never assumed.',
           'Header pin positions, the board\'s USB-C and connector positions, and the E-Switch pins are confirmed on the parts in your hand.',
           'Small fit adjustments for your printer and filament.'])

# ======================================================================================================
# FOUNDATIONS
# ======================================================================================================
chapter('FOUNDATIONS — the electronics and software you need, in plain words', 'F')
a.p('You need about a dozen ideas, one meter and a soldering iron you are not afraid of. This chapter gives you exactly those, using this '
    'project\'s parts as the examples. If you know them already, skim the tables.')
a.audio('AUDIO GUIDE — Foundations A: Electricity for this build', [
    'Think of voltage as pressure and current as flow. The board works at 3.3 volts inside. USB supplies 5 volts, and a single lithium cell '
    'sits around 3.7 volts on average, more when full, less when empty. The board\'s power chip turns whatever arrives into the steady 3.3 '
    'volts the processor needs.',
    'Ground, written GND, is the zero-volt reference every voltage is measured from. Every circuit is a loop: current leaves a supply, does its '
    'work and returns to ground. That is why each control needs only two wires: one to its input pin, one to ground.',
    'A short circuit is a loop with nothing in it to limit the current: a wire, a solder bridge or a dropped screwdriver joining a supply '
    'straight to ground. On USB it usually just resets the board. On a lithium cell it can make wires glow and the cell swell. That is why the '
    'battery comes last and why you check for shorts with the meter before applying power.',
    'Polarity means which side is plus and which is minus. Switches do not care. Batteries, speakers and many connectors do, and the battery '
    'cares most. A red wire is not proof of plus: check with the meter.'])
a.table(['Word', 'What it means on this build', 'Where you meet it'], [
    ['Voltage (V)', '"Pressure". 3.3 V logic, 5 V USB, 3.0–4.2 V lithium cell.', 'Meter test 3, battery'],
    ['Current (A, mA)', '"Flow". The board draws a few hundred mA; measure it.', 'Step 8, Shop Sheet E'],
    ['GND (ground)', 'The 0 V return every circuit shares.', 'Every control, every measurement'],
    ['Short circuit', 'A supply joined straight to GND. Dangerous with a battery.', 'Meter test 2, before power'],
    ['Polarity', 'Which lead is + and which is −.', 'Battery, speaker'],
    ['Pull-up resistor', 'Holds an input HIGH until a switch pulls it LOW.', 'Inside the ESP32, every control'],
    ['Active low', 'Pressed reads 0 (LOW), released reads 1 (HIGH).', 'Every control'],
    ['Normally open', 'A contact that closes only while pressed.', 'Silicone keys, bench switches'],
    ['Continuity', 'An unbroken path: the meter beeps.', 'Meter test 1'],
    ['Bounce', 'Contacts chatter for a few ms; the firmware waits 8 ms.', 'All four controls'],
    ['GPIO', 'A processor pin the firmware can read or drive.', 'GPIO17, 18, 21, 38'],
    ['I2C, QSPI, I2S', 'Chip-to-chip "languages": control, display data, audio.', 'Sheets S1, S4 (on the board)'],
], widths=[1.5, 4, 2.2], size=9)
fig(FG('f01_pullup.png'), 'Why a control needs only two wires: the internal pull-up holds GPIO17 at 3.3 V (reads 1); the closed contact pulls it to 0 V (reads 0).')
a.h2('The multimeter: the only test instrument you need')
fig(FG('f02_multimeter.png'), 'Continuity (beep) for wires and switches, the same beep as a short check before power, and DC volts for the battery. The 3.95 reading is an example.')
a.bullets(['Continuity and resistance only on an UNPOWERED circuit: unplug USB and the battery first.',
           'For volts, the red lead stays in the VΩ socket. Never use the 10 A / mA socket for voltage: it is a near short.',
           'Touch the probes together at the start: the meter beeps, so you know it works.',
           'Write every reading down (Shop Sheet E).'])
a.h2('Soldering for first-timers')
a.steps(['Set up: iron in its stand, tip wiped, 320–350 °C for leaded solder or 350–380 °C for lead-free. Fan on. Safety glasses for clipping.',
         'Tin the tip: melt a little solder onto it so it shines.',
         'Heat both parts: the tip touches the pad and the leg together for two seconds.',
         'Feed solder into the joint on the side opposite the iron. It flows and wraps the leg.',
         'Remove the solder, then the iron. Keep still for three seconds.',
         'Inspect against Figure F.3: shiny and concave is good.',
         'Pre-tin wires: strip 3 mm, twist, melt a little solder in.'])
fig(FG('f03_solder.png'), 'Good and bad joints from the side. A bridge joins signal to ground: that control then reads "pressed" all the time.')
a.h2('Practice (20 minutes)')
a.steps(['Solder five short wires into scrap perfboard.', 'Bridge two on purpose, then remove the bridge with wick.',
         'Prove with the beep which holes are joined.', 'Solder a spare 4-leg tactile switch and find its joined leg pairs (Figure 6.1).'])
a.h2('Software words in plain language')
a.table(['Word', 'What it means', 'On this project'], [
    ['Host / desktop', 'Your computer.', 'Runs the checks in handheld/host'],
    ['Target / device', 'The ESP32-S3 board.', 'Runs handheld/firmware'],
    ['Terminal', 'A text window for commands.', 'Windows: "ESP-IDF 5.5 CMD"; macOS / Linux: Terminal'],
    ['Build', 'Turn C source into a program.', 'idf.py build → build/struthio.bin'],
    ['Flash', 'Write it into the board over USB.', 'idf.py flash'],
    ['Monitor / log', 'Watch the text the board prints.', 'idf.py monitor (leave: Ctrl + ])'],
    ['Partition', 'A named region of the 16 MB flash chip.', 'factory (program), assets (art), music, nvs (settings)'],
    ['ESP-IDF', 'Espressif\'s tools for the ESP32.', 'Version 5.5.5'],
    ['Tick', 'One step of the game; 60 per second.', 'Traces are counted in ticks'],
    ['Trace', 'A recording of inputs plus the expected state each tick.', 'golden/climb.trace'],
    ['Digest / SHA-256', 'A 64-hex-digit fingerprint of the whole game state.', 'One wrong bit changes it completely'],
    ['Art pack', 'Every picture the device draws, in one file.', 'build/assets/struthio.pak (8.3 MB)'],
], widths=[1.5, 3, 3.2], size=9)

# ======================================================================================================
# STEP 2
# ======================================================================================================
chapter('Step 2 — Gather tools, parts and a safe workspace', 2)
a.p('Gather the first-day parts before you start, and leave the rest in their boxes. Buy by exact part number, never by appearance: the '
    'manufacturer\'s documentation, the board revision and your measurements are the authority.')
a.audio('AUDIO GUIDE — Chapter 2: Put only the first-day parts on the table', [
    'For the first bench session you need the Waveshare ESP32-S3-Touch-LCD-3.5B, a USB-C DATA cable, two Omron B3F-4050 tactile switches (or the '
    'firmer B3F-4055), two scraps of perfboard, hookup wire, a soldering iron and solder, a multimeter, and a computer that can run ESP-IDF 5.5.',
    'Do not start with the battery, the power switch, the speaker or the shell. USB power is enough to prove the machine, and leaving the other '
    'systems out makes the first troubleshooting session much easier.',
    'One board rule belongs on the table from the start: leave the camera connector empty. The controls use GPIO17, 18, 21 and 38, which are '
    'also camera pins. STRUTHIO has no camera; the controls work because no camera is fitted.'])
a.h2('Tools')
a.table(['Tool', 'Why', 'Note'], [
    ['Computer + USB-C DATA cable', 'Build, flash, read the log', 'Many cables are charge-only: they show no port'],
    ['Soldering iron, solder, wick', 'Switches, CP1 wires, speaker, power', 'Practise first (Foundations)'],
    ['Flush cutters, wire stripper', 'Clean wire preparation', ''],
    ['Multimeter', 'Continuity, shorts, polarity, volts', 'Essential before the battery'],
    ['Small screwdrivers (M2), tweezers', 'Assembly and service', 'A 1.5 mm hex key for M2 socket heads'],
    ['Kapton tape / heat-shrink', 'Insulation and strain relief', ''],
    ['3D printer or print service', 'The shell', 'Front fit coupon first'],
    ['Inline USB-C power meter', 'Current draw (Step 8)', 'Optional, recommended'],
], widths=[2.4, 2.6, 2.6], size=9)
a.h2('Parts')
a.table(['Part', 'For', 'When'], [
    ['Waveshare ESP32-S3-Touch-LCD-3.5B', 'Everything', 'Now'],
    ['2 x Omron B3F-4050 (or -4055) + perfboard', 'Bench wing switches', 'Now'],
    ['PUI Audio AS02808MR-R speaker (28 mm, 8 Ω, 1 W)', 'Sound', 'Now / after the board works'],
    ['STRUTHIO-CP1 control PCB (order from the Gerbers)', 'Handheld controls', 'After the bench PASS (Step 9)'],
    ['STRUTHIO-CM1 silicone keys (from the drawing)', 'Handheld controls', 'After the bench PASS (Step 9)'],
    ['THOR-503450 protected LiPo, 3.7 V 1000 mAh', 'Portable power', 'After everything works on USB'],
    ['E-Switch 500SSP1S1M7QEA slide switch', 'Hard power cut in BAT+', 'With the battery'],
    ['Short USB-C male-to-female extension, full data', 'USB-C to the bottom of the shell', 'When fitting the shell'],
    ['4 x M2 x 10 socket-head screws, thread-forming', 'Close the shell', 'When printing'],
    ['1.0–1.5 mm clear acrylic or polycarbonate', 'Screen lens', 'Finishing'],
    ['Sticker paper + clear laminate', 'Front art', 'Finishing'],
], widths=[3.6, 2.4, 2], size=9)
a.p('The full list with quantities and notes is Shop Sheet A.')
fig(UI('12.png'), 'Illustrated recognition aid for the core electronics. Not a manufacturer photograph: use Waveshare\'s own pictures for the exact board.', 6.0)

# ======================================================================================================
# STEP 3
# ======================================================================================================
chapter('Step 3 — Set up your computer', 3)
a.p('Prepare the software before the hardware. At the end of this step the setup doctor shows no FAIL and the desktop checks prove that the C '
    'game on your computer is the browser game, bit for bit.')
a.audio('AUDIO GUIDE — Chapter 3: Prepare the computer before touching wiring', [
    'Install ESP-IDF 5.5.5 and make sure your terminal can see idf.py. The project expects an ESP32-S3 with 16 MB of flash, octal PSRAM, a '
    '240 MHz CPU, a one-kilohertz FreeRTOS tick, the task watchdog and the USB Serial/JTAG console. You do not need to understand those '
    'settings: they are in the project\'s sdkconfig.defaults. What matters is that the build commands run without an installation error.',
    'Before the board arrives, run the desktop checks. They prove the portable core, the button logic and the recorded games are healthy '
    'before any board-specific problem can appear. If they fail, fix that before blaming hardware.',
    'Keep the package you unzipped untouched as your known-good copy, and keep a build log: what you flashed, what you measured, what changed.'])
a.h2('Put the package in the right place')
a.steps(['Windows: right-click STRUTHIO_HANDHELD.zip → Extract All… → type C:\\ as the destination. You get C:\\struthio.',
         'macOS / Linux: unzip it in your home folder. You get ~/struthio.',
         'No spaces in the path, and not inside OneDrive, Dropbox or iCloud: syncing can lock build files.'])
a.table(['In C:\\struthio (~/struthio)', 'What it is', 'You use it'], [
    ['STRUTHIO.bat / struthio.sh', 'The build menu', 'From Step 3 on'],
    ['README_FIRST.txt', 'A one-page start', 'Once'],
    ['manual\\', 'This manual (PDF and Word)', 'Always'],
    ['handheld\\firmware\\', 'The program for the board (ESP-IDF)', 'Build and flash'],
    ['handheld\\build\\assets\\', 'struthio.pak (art, 8.3 MB) and struthio_music.ima (soundtrack, 1.8 MB)', 'Flashed for you; never edit'],
    ['handheld\\core, render, audio', 'The game itself, in portable C', 'Built for you'],
    ['handheld\\host, golden', 'The desktop checks and the five recorded games', 'Gate 0'],
    ['handheld\\cad\\handheld\\', 'Shell STLs, sticker, CP1 Gerbers, drawings, renders, CAD source', 'Steps 9–11'],
    ['handheld\\docs\\', 'Pin and wiring card', 'Wiring'],
    ['handheld\\tools\\struthio_doctor.py', 'The setup doctor', 'Menu option 1'],
    ['SHA256SUMS.txt', 'Fingerprints of every file', 'The doctor checks them'],
], widths=[2.6, 3.6, 1.6], size=9)
a.h2('Install ESP-IDF 5.5.5')
a.p('ESP-IDF is Espressif\'s free toolkit for the ESP32. This build is checked against v5.5.5: install exactly that version.')
a.table(['System', 'Install', 'Open a ready terminal'], [
    ['Windows 10 / 11', 'Download the ESP-IDF Tools Installer from Espressif (the offline installer is the most reliable). Choose ESP-IDF v5.5.5. '
     'Keep the installation path short, with no spaces or brackets (90 characters at most).', 'Start menu: "ESP-IDF 5.5 CMD" (or "ESP-IDF 5.5 PowerShell")'],
    ['macOS', 'Install the prerequisites from Espressif\'s Get Started guide (Homebrew: cmake ninja dfu-util python3), then the commands below.', 'In each new Terminal: . ~/esp/esp-idf/export.sh'],
    ['Linux', 'Prerequisites: git wget flex bison gperf python3 python3-venv cmake ninja-build ccache libffi-dev libssl-dev dfu-util libusb-1.0-0, then the commands below.', 'In each new terminal: . ~/esp/esp-idf/export.sh'],
], widths=[1.3, 4.3, 2.2], size=9)
code('# macOS / Linux, once:', 'mkdir -p ~/esp && cd ~/esp',
     'git clone -b v5.5.5 --recursive https://github.com/espressif/esp-idf.git',
     'cd esp-idf && ./install.sh esp32s3', '# every new terminal:', '. ~/esp/esp-idf/export.sh',
     'idf.py --version          # prints ESP-IDF v5.5.5')
a.bullets(['Linux only: add yourself to the serial-port group once — sudo usermod -a -G dialout $USER — then log out and in.',
           '"idf.py: command not found" (or "not recognized") means this terminal has not been set up: use the ESP-IDF shortcut, or run export.sh.'])
a.h2('The build menu')
a.p('Windows: open "ESP-IDF 5.5 CMD" from the Start menu, then type cd /d C:\\struthio and STRUTHIO.bat. (Double-clicking STRUTHIO.bat also '
    'works: it looks for ESP-IDF in the usual places.) macOS / Linux: cd ~/struthio, then ./struthio.sh.')
fig(FG('p03_menu.png'), 'The build menu. Every option prints the command it runs; the board\'s port is remembered in struthio_port.txt.', 5.4)
a.table(['Option', 'What it does', 'The command it runs'], [
    ['1', 'Check my setup (the doctor)', 'python handheld/tools/struthio_doctor.py'],
    ['2', 'Find the board\'s port and remember it', 'struthio_doctor.py --port (or you type it)'],
    ['3', 'Build (first time: set the chip)', 'idf.py -C handheld/firmware [set-target esp32s3] build'],
    ['4', 'GREYBOX test: build, flash, watch', 'idf.py … -p PORT -D STRUTHIO_ART=greybox build flash monitor'],
    ['5', 'FULL ART: build, flash, watch', 'idf.py … -p PORT -D STRUTHIO_ART=full build flash monitor'],
    ['6', 'Quick flash: the program only', 'idf.py … -p PORT app-flash monitor'],
    ['7', 'Watch the log', 'idf.py … -p PORT monitor'],
    ['8', 'Download-mode help (BOOT + RESET)', '—'],
    ['9', 'Erase the whole board (asks first)', 'idf.py … -p PORT erase-flash'],
    ['D', 'Desktop checks (WSL on Windows)', 'make -C host test; make -C firmware/host_test run'],
], widths=[0.6, 2.8, 4.4], size=9)
a.p('Shortcuts: on Windows, STRUTHIO.bat greybox (or full, build, monitor, doctor, port, quick, desktop, bootmode) runs one option and exits.')
a.h2('The setup doctor')
a.p('Option 1 checks everything this manual asks you to check by hand: every package file against SHA256SUMS.txt, that the art and soundtrack '
    'fit their flash areas, the folder path, Python, the ESP-IDF version, the firmware folder, and which serial port is the board. Each FAIL '
    'or WARN line says what to do.')
fig(FG('p04_doctor.png'), 'The doctor on a ready computer (example output). Before the board is plugged in, the port line is a WARN: that is normal.', 5.6)
a.h2('Windows 11, step by step')
a.table(['Stage', 'What to do', 'PASS means'], [
    ['W1 install', 'ESP-IDF Tools Installer, v5.5.5.', '"ESP-IDF 5.5 CMD" is in the Start menu; idf.py --version prints v5.5.5'],
    ['W2 folder', 'Extract the package to C:\\ (Extract All…).', 'C:\\struthio\\handheld\\firmware exists'],
    ['W3 doctor', 'In ESP-IDF 5.5 CMD: cd /d C:\\struthio, STRUTHIO.bat, option 1.', 'No FAIL lines'],
    ['W4 port', 'Plug the board in with a DATA cable; option 2.', '"Found the board on COMx" (Device Manager → Ports shows it too)'],
    ['W5 vendor example', 'Flash Waveshare\'s own example first (Step 4).', 'The stock demo runs'],
    ['W6 greybox', 'Option 4.', 'Step 5 greybox PASS'],
    ['W7 full art', 'Option 5.', 'Step 5 full-art PASS'],
    ['W8 recovery', 'If flashing cannot connect: option 8 (BOOT + RESET), then retry.', 'esptool connects and writes'],
], widths=[1.3, 3.6, 2.9], size=9)
a.p('Desktop checks on Windows run in WSL (Ubuntu). Once, in an Administrator PowerShell: wsl --install. Restart, open Ubuntu, then: '
    'sudo apt update && sudo apt install -y build-essential. After that, menu option D runs the checks for you.')
a.h2('Gate 0: the desktop checks')
a.p('These prove, before any hardware, that the C game on your computer equals the browser game. You need a C compiler and make: WSL on '
    'Windows, xcode-select --install on macOS, build-essential on Linux. Menu option D, or:')
code('cd handheld', 'make -C host test               # the C game vs the browser, every tick',
     'make -C firmware/host_test run  # button and rocker tests + DART mode report')
a.p('PASS looks exactly like this (the chain fingerprints must match too):')
a.code(['PASS climb    10011 ticks  score  60250  round  4  deaths   0  jousts  13  eggs   3  darts  30  chain 3c9d8a4075eebdab',
        'PASS duel     20000 ticks  score  37750  round  3  deaths  23  jousts  37  eggs   3  darts 237  chain 88879e49392e99c1',
        'PASS late     10990 ticks  score 136250  round 11  deaths   0  jousts  60  eggs  13  darts  67  chain 66e9011ca571b5f7',
        'PASS mortal   14143 ticks  score  77500  round  5  deaths  12  jousts  23  eggs   3  darts  81  chain 25b7dd681c36acce',
        'PASS raw      20000 ticks  score  65750  round  5  deaths  30  jousts  65  eggs  15  darts 194  chain cfa154009f20e9e1',
        'GOLDEN REPLAY: all 5 traces bit-exact',
        'PASS: wing buttons (debounce, chord, DART trials A/B/C, rocker, service)'], size=6.8)
a.p('The second command then prints a DART mode report: how often each mode fires on recorded play. The ROCKER lines end "every press darts, '
    'nothing else does".')

# ======================================================================================================
# STEP 4
# ======================================================================================================
chapter('Step 4 — Prove the stock board on the bench', 4)
a.p('The first hardware gate. The Waveshare board proves itself with its own example before STRUTHIO touches it.')
a.audio('AUDIO GUIDE — Chapter 4: Prove the Waveshare board with its own example', [
    'Connect only the board and a USB-C data cable. No switches, no battery, no speaker, camera connector empty. Write down the board '
    'revision printed on it.',
    'Flash Waveshare\'s own example, unchanged. This is not wasted time: it proves the computer can talk to the ESP32, flashing works, the '
    'display is alive, and the power system runs, before STRUTHIO enters the picture.',
    'If the vendor example fails, stop. Do not solder anything and do not change STRUTHIO. Solve the cable, port, toolchain or board problem first.'])
fig(SCH('s1_system.png'), 'Sheet S1 — what the ESP32-S3 talks to: display, backlight, power chip, audio, and the four controls you will add.')
a.h2('Bring-up sequence')
a.steps(['Record the board revision (Shop Sheet E).', 'Leave the camera connector empty.',
         'Flash and run Waveshare\'s example, unchanged.', 'Confirm the display lights, the board appears as a serial port, and the example behaves normally.'])
ok('PASS: the board powers from USB-C, the screen is alive, flashing and the log work. You have a known-good baseline.')
a.p('If it fails: another known-good DATA cable and USB port; re-run the unmodified example; compare the board revision with Waveshare\'s current documentation.')

# ======================================================================================================
# STEP 5
# ======================================================================================================
chapter('Step 5 — First STRUTHIO boot: greybox, then full art', 5)
a.p('STRUTHIO boots twice at this step. First as a GREYBOX test: the game with flat colours, which proves the power chip, display path, '
    'tasks and simple drawing with nothing else in the way. Then with the full art pack and the soundtrack.')
a.audio('AUDIO GUIDE — Chapter 5: First STRUTHIO boot: use the greybox on purpose', [
    'The greybox is not a failure and not an unfinished game. It is a diagnostic stage. We only want to know whether the AXP2101 power '
    'chip, the TCA9554 reset line, the AXS15231B display, the backlight, the game task and the simple renderer are alive. The panel is 320 by 480 '
    'pixels over QSPI at 40 MHz.',
    'You do not move any files for this. The build has a switch, STRUTHIO_ART. With greybox, the flash step writes a small marker where the '
    'art pack would go, so the board draws flat colours even if it held the art before. With full, it writes the 8.3 MB art pack. The build '
    'remembers your choice, so always say which one you want.',
    'If the screen stays dark, the first suspects are the TCA9554 reset pulse and the backlight. If the build or flash fails, treat it as a '
    'toolchain, cable or port problem: never change the game to fix it.'])
fig(FG('f11_bench.png'), 'The bench build. Until the bench PASS, nothing else is connected.')
a.h2('The greybox test (gate 2)')
a.p('Menu option 4, or:')
code('cd handheld/firmware', 'idf.py set-target esp32s3                                   # once per fresh folder',
     'idf.py -p PORT -D STRUTHIO_ART=greybox build flash monitor')
a.p('The first build takes several minutes. In the log you see "STRUTHIO_ART=greybox: flashing the greybox marker" during the build, then the boot log below with '
    '"assets: greybox marker" and "renderer greybox".')
fig(DR('a0_greybox_sheet.png'), 'The greybox renderer: the same game, flat colours. This is what the greybox test looks like.', 5.8)
ok('GREYBOX PASS: the log reaches NEW RUN and "renderer greybox"; the screen shows the flat-colour game; no error lines.')
a.h2('The full-art flash (gate 5, after Steps 6 and 7)')
a.p('Once the controls work and service mode says GOLDEN PASS, flash the real picture. Menu option 5, or:')
code('idf.py -p PORT -D STRUTHIO_ART=full build flash monitor')
a.p('This flash writes the program, the 8.3 MB art pack and the 1.8 MB soundtrack, so it takes a few minutes. Later, menu option 6 '
    '(idf.py app-flash) rewrites only the program in seconds and leaves the art and music alone.')
ok('FULL-ART PASS: the boot line says "renderer panel (asset pack)" and the real STRUTHIO picture is on screen.')
a.h2('What idf.py flash writes')
a.table(['Address', 'What', 'Size'], [
    ['0x0', 'bootloader', 'small'], ['0x8000', 'partition table', '3 KB'], ['0x10000', 'the program, build/struthio.bin', 'up to 4 MB'],
    ['0x410000', 'art pack, handheld/build/assets/struthio.pak (or the greybox marker)', '8.3 MB of 9 MB'],
    ['0xD10000', 'soundtrack, handheld/build/assets/struthio_music.ima', '1.8 MB of 2.9 MB'],
], widths=[1.2, 5, 1.6], size=9)
fig(FG('f06_flashmap.png'), 'The 16 MB flash chip (firmware/partitions.csv). High score, DART mode and volume live in nvs; "idf.py erase-flash" clears them.')
a.h2('Finding PORT')
a.table(['System', 'PORT is usually', 'How to find it'], [
    ['Windows', 'COM3, COM5, …', 'Menu option 2; or Device Manager → Ports (COM & LPT): the entry that appears when you plug the board in'],
    ['macOS', '/dev/cu.usbmodem…', 'ls /dev/cu.* before and after plugging in'],
    ['Linux', '/dev/ttyACM0', 'ls /dev/ttyACM* before and after plugging in'],
], widths=[1.2, 1.8, 4.8], size=9)
a.bullets(['Flashing says it cannot connect: hold BOOT, press and release RESET, release BOOT, flash again; press RESET afterwards to run.',
           'In the log window: Ctrl + ] leaves; Ctrl + T then Y pauses; Ctrl + T then L saves the log to a file; Ctrl + T then R resets the board.'])
a.h2('Reading the boot log, line by line')
a.p('These are the lines STRUTHIO prints, in order. Angle brackets are filled in by the board.')
a.table(['Log line (as printed)', 'What it means', 'Good when'], [
    ['STRUTHIO handheld boot (core: STRUTHIO ARCADE 1.8.0 port)', 'Your firmware is running.', 'After every reset'],
    ['AXP2101 id 0x<id>, battery present|absent', 'The power chip answered and was set up.', 'On the bench: "absent"'],
    ['AXS15231B 320x480 QSPI at 40 MHz', 'The display controller started.', 'Always'],
    ['ES8311 audio 48000 Hz mono', 'The audio codec answered.', 'Always (speaker fitted or not)'],
    ['audio ok|OFF, music 160 s loop|none, volume <n>/4', 'Sound started; soundtrack found; saved volume.', '"audio ok, music 160 s loop"'],
    ['assets: greybox marker (STRUTHIO_ART=greybox): flat-colour renderer by request', 'The greybox test, as asked.', 'Greybox test only'],
    ['NEW RUN seed <n>', 'A game started.', 'After boot and after each restart'],
    ['DART trial <mode>, best <n>, display ok, renderer greybox|panel (asset pack)', 'DART mode, high score, which renderer runs.', '"panel (asset pack)" after the full-art flash'],
    ['tick <n> sim <us> us (max <us>) scene <us> us render <us> us present <us> us missed <n> band-order <n> audio <us> us (max <us>) per 5333', 'Performance report (Step 7).', 'band-order 0'],
    ['ROUND <n> CLEAR score <n>', 'You cleared a round.', ''],
    ['GAME OVER score <n> (best <n>)', 'All Joust Marks used.', ''],
], widths=[3.4, 2.6, 1.8], size=8.5)
a.h2('Error lines and what to do first')
a.table(['If the log says', 'Likely cause', 'First action'], [
    ['I2C bus failed', 'The I2C driver could not start.', 'Re-flash the unmodified firmware; check the board revision.'],
    ['AXP2101 not found', 'The power chip did not answer at 0x34.', 'Is it the 3.5B board? Run the vendor example again.'],
    ['TCA9554 not found: the LCD stays in reset', 'The I/O expander that releases the LCD did not answer.', 'Board revision / I2C problem; the screen stays dark.'],
    ['SPI bus failed / panel IO failed / AXS15231B failed', 'The display path could not be created.', 'Vendor example first; compare the board revision.'],
    ['backlight PWM failed', 'The backlight timer did not start.', 'The picture may be there but dark: shine a torch on the glass.'],
    ['band at y <n>: transfer timeout', 'A display transfer did not finish.', 'Note how often; report with the log. Do not edit the art.'],
    ['no assets partition / no music partition', 'The board holds another partition table.', 'Flash with idf.py flash (it writes the table).'],
    ['assets: mmap failed / music: mmap failed', 'The area could not be mapped.', 'Flash again; if it persists, erase-flash, then flash.'],
    ['assets: not an asset pack (flash build/assets/struthio.pak; see README)', 'The art area is empty or damaged.', 'Menu option 5 (STRUTHIO_ART=full); run the doctor.'],
    ['assets: out of memory', 'No RAM for the renderer\'s buffers.', 'Report with the log; the greybox still runs.'],
    ['ES8311 not found', 'The codec did not answer.', 'Vendor audio example; the game plays silently.'],
    ['audio: no I2C bus / I2S channel failed / I2S init failed / codec interfaces failed / codec device failed / codec open failed', 'The audio path could not start.', 'Re-flash the unmodified firmware; report with the log.'],
    ['music: not a STRUTHIO music file (…)', 'The soundtrack area is empty or damaged.', 'Flash again (option 5); sound effects still play.'],
], widths=[3.2, 2.4, 2.2], size=8.5)

# ======================================================================================================
# STEP 6
# ======================================================================================================
chapter('Step 6 — Bench controls: two wing switches', 6)
a.p('The bench build uses two ordinary tactile switches for the wings. They prove the inputs and let you play long before the custom '
    'silicone keys exist. DART on the bench is DART mode C: hold both wings for about 200 ms.')
a.audio('AUDIO GUIDE — Chapter 6: Build the LEFT WING switch', [
    'Add one switch first. GPIO17 is LEFT WING and its other side goes to GND. Confirm the header position on your board before soldering.',
    'The ESP32 input has an internal pull-up, so an untouched switch reads high. Pressing closes the circuit to ground and the input reads low. '
    'That is why the switch needs only a signal and a ground, and no extra resistor.',
    'Enter service mode and press the switch repeatedly. You want a clean count, one per press, with no phantom double presses. If LEFT does not '
    'register, fix it before adding RIGHT.'])
a.audio('AUDIO GUIDE — Chapter 7: Add RIGHT WING and the shared ground', [
    'Add RIGHT WING on GPIO18 with the same ground. Test each switch alone, then both together. If a switch works until the display turns on and '
    'then becomes unstable, look at the pin and the board revision before suspecting the game.'])
fig(FG('f04_switchboard.png'), 'One wing switch board (make two). Wire two diagonally opposite legs and prove them with the meter before soldering wires.')
a.h2('Build one switch board')
a.steps(['Cut perfboard to about 18 x 18 mm (7 x 7 holes). Sand the edges.',
         'Push the B3F-4050 through so all four legs come out underneath and the body sits flat.',
         'Solder all four legs (stronger), though only two carry signal.',
         'Meter on beep: find two diagonally opposite legs that are silent released and beep pressed. Mark them S (signal) and G (ground).',
         'Pre-tin the wires. LEFT: white wire to S, black to G. RIGHT: blue wire to S, black daisy-chained from the LEFT board\'s G.',
         'Heat-shrink or a dab of hot glue over the joints. Label the far ends LEFT / RIGHT / GND.',
         'Meter check: S to G silent, pressed beeps; S of one board to S of the other: silent.'])
stop('Control wires go to GPIO17, GPIO18 and GND only. Never to 3V3 or 5V: a switch that joins a supply pin to GND is a dead short every time you press it.')
fig(SCH('s2_controls.png'), 'Sheet S2 — the controls. The bench build wires only the two wings; the handheld adds the two DART-rocker ends on CP1.')
a.h2('From thumb to flap')
fig(FG('f05_timing.png'), 'What the firmware does with one press: 1 kHz sampling, 8 ms debounce, the first press flaps at once, the 100 ms chord window.')
a.table(['Timing', 'Value', 'Why'], [
    ['Sampling', 'every 1 ms (1 kHz input task, core 0)', 'Fine enough to measure thumb timing'],
    ['Debounce', '8 ms stable before a change counts', 'Hides switch bounce; the press keeps its first-edge time'],
    ['Chord window', '100 ms', 'Opposite wing inside it = STRAIGHT (up)'],
    ['Flap buffer', '8 ticks (133 ms)', 'A flap that cannot fire yet is kept, not lost'],
    ['Service mode', 'both wings held 650 ms within the first 800 ms after power-on', 'Hard to trigger by accident'],
    ['DART mode C (bench)', 'both wings held 200 ms', 'The default, for boards without the rocker'],
], widths=[1.6, 3, 3.2], size=9)

# ======================================================================================================
# STEP 7
# ======================================================================================================
chapter('Step 7 — Service mode, GOLDEN PASS, and play', 7)
a.audio('AUDIO GUIDE — Chapter 8: Service mode and the GOLDEN PASS', [
    'Hold both wings while powering the board, and keep holding for about a second. Service mode is a hidden diagnostic screen: normal play '
    'never uses it.',
    'It shows the build, the reset reason, free memory, live control states with press counts, the DART mode, and runs an on-device golden '
    'replay: the recorded climb game, 10,011 ticks, run through the C game on the ESP32 with every tick\'s fingerprint checked.',
    'The words you want are GOLDEN PASS. That is much stronger than watching a bird move: it says the chip in your hands runs the same game, '
    'not an imitation. Write down the timings: they are your board\'s first real measurements.',
    'If the replay fails, keep the log line: it names the tick and the reason. Run the desktop checks before changing anything.'])
fig(FG('service.png'), 'The service screen, drawn on the desktop with the firmware\'s own text and layout. The numbers are EXAMPLES.', 3.0)
a.table(['Line', 'Meaning', 'What you want'], [
    ['HANDHELD / CORE 1.8.0 / <date>', 'When this firmware was built.', 'Today\'s date after you flash'],
    ['RESET <n>  PSRAM <n>K  RAM <n>K', 'Why the chip last reset; free memory.', 'Record in Shop Sheet E'],
    ['LEFT UP|DOWN <n>   RIGHT UP|DOWN <n>', 'Each wing\'s live state and press count.', 'DOWN only while pressed; +1 per press'],
    ['DART <mode>  FIRED <n>', 'DART mode and darts fired.', 'Bench: C BOTH-HOLD. Handheld: ROCKER ONLY'],
    ['ROCKER L UP|DOWN <n>   R UP|DOWN <n>', 'Each DART-rocker end (GPIO21 / 38).', 'Handheld: +1 per press, FIRED rises with it'],
    ['GOLDEN PASS <n> TICKS', 'The on-device golden replay.', 'GOLDEN PASS 10011 TICKS (green)'],
    ['SIM <n> US/TICK  +DIGEST <n>', 'Time per game tick, and with the fingerprint.', 'SIM far below 16,667 us'],
    ['PANEL <n> MS/FRAME <n> FPS', 'Time to send a full picture.', 'Record it; under 33 ms allows 30 fps'],
    ['AUDIO OK|NO CODEC  MUSIC OK|NONE  VOL <n>/4', 'Codec, soundtrack, volume.', 'AUDIO OK, MUSIC OK'],
], widths=[2.6, 2.8, 2.4], size=8.5)
a.table(['In service mode', 'Does'], [
    ['LEFT tap (acts on release)', 'Next DART mode: A HOLD → B TAP-HOLD → C BOTH-HOLD → ROCKER ONLY → … (saved)'],
    ['LEFT held 1 s', 'Next volume level 0–4 (saved; a ring chime plays)'],
    ['RIGHT tap', 'Run the checks again (the round-clear sting plays when they finish)'],
    ['Power off and on', 'Back to the game'],
], widths=[2.2, 5.6], size=9)
ok('GATE 4 PASS: GOLDEN PASS 10011 TICKS on the device, and each control counts +1 per press.')
a.h2('DART modes')
a.table(['Mode', 'How a dart fires', 'Use it on'], [
    ['C BOTH-HOLD (default)', 'Hold both wings 200 ms', 'The bench build (no rocker)'],
    ['ROCKER ONLY', 'Press an end of the DART rocker: left end darts left, right end darts right; the wings never dart', 'The handheld'],
    ['A HOLD, B TAP-HOLD', 'Experimental wing gestures (hold one wing; tap then hold)', 'Comparison only'],
], widths=[1.8, 4, 2], size=9)
a.p('The rocker darts in every mode. Played through four recorded games, the rocker fired every dart the player asked for and nothing else '
    '(27 of 27, 291 of 304, 63 of 63, 82 of 84: the few missing were re-presses faster than a thumb can make). The wing gestures A and B '
    'misfired 40–78 times a minute, because steering holds a wing; C fired 0.3–2 times a minute.')
a.h2('How to play STRUTHIO')
a.audio('AUDIO GUIDE — Chapter 9: Play on loose switches before printing anything', [
    'Power-cycle normally. There is no start button and no menu: a new run begins after boot.',
    'A LEFT or RIGHT press flaps at once in that direction. Holding a wing steers. Pressing the other wing within 100 milliseconds turns the '
    'flap into STRAIGHT up, as in the browser game; the first press is never delayed while the firmware waits for a chord.',
    'Your first milestone is not a beautiful enclosure. It is completing one playable round on the loose switches: the bench PASS.'])
a.bullets(['Flap: tap LEFT to flap up and left, RIGHT to flap up and right. Both within 100 ms: straight up. Hold a wing to steer.',
           'Joust: meet a rival; the higher lance wins, nearly level is a clash. A beaten rival falls and becomes an egg.',
           'Eggs: collect them before they hatch: an egg lasts 6 s, hatches for 1 s, then the rival remounts in 1.5 s.',
           'Rings: fly through all six rings in any order. Then the gold ring at the moon opens: take it to blast every rival and clear the round.',
           'Lava: touch it and you sink. Flap within 0.3 s to escape, or you lose a Joust Mark (a life).',
           'Restart after GAME OVER: press both wings together; it works from one second after GAME OVER, so a stray flap cannot skip the score.'])
a.table(['Scoring event', 'Points (the rulebook)'], [
    ['Joust win', 'BOUNDER 500, HUNTER 750, SHADOW 1,000, plus 250 per tier'],
    ['Eggs in a row', '250, 500, 750, then 1,000 each (the chain resets when you lose a life)'],
    ['Ring', '500'], ['Gold-ring blast', 'each armed rival scores as a joust win'],
    ['Round clear', '5,000 + 1,000 per round, up to 15,000'], ['Survival bonus', '3,000 when you clear a round without losing a life'],
    ['Joust Marks (lives)', 'start with 11 (also the maximum); extra at 30,000, then every 100,000'],
], widths=[2, 5.8], size=9)
fig(FG('f09_hud.png'), 'The game screen as the C panel renderer draws it, with the browser game\'s HUD.')
a.h2('How the picture is made')
fig(FG('f10_pipeline.png'), 'From button to glass. The same C files run in the desktop checks.')
fig(DR('panel_vs_browser_2809.png'), 'The C panel renderer (left) and the browser (right), the same tick. Measured closeness 24.9–30.3 dB PSNR; 30 dB looks identical to most eyes.', 5.6)
fig(FG('f07_cores.png'), 'Two cores, one panel: bands must reach the display top to bottom. A band-order count above 0 in the log means the hand-off is broken.')
a.audio('AUDIO GUIDE — Chapter 10: Watch the picture', [
    'The panel renderer draws in 16-line bands, and the two cores take turns so the display receives them top to bottom: the panel has no '
    'row address, so order matters. The band-order count in the log must stay zero.',
    'If graphics appear but horizontal sections are shifted or torn, do not redesign the art: check the transfer-timeout lines and the '
    'band-order count first.',
    'The game always runs at 60 ticks a second. The picture aims for up to about 30 frames a second; if drawing is slow, frames are dropped, '
    'never game ticks. Record the scene, render and present times in a busy part of the tower.'])
a.h2('The performance line')
code('tick 3600 sim 180 us (max 410) scene 2100 us render 9800 us present 7400 us missed 0 band-order 0 audio 310 us (max 520) per 5333',
     '                                                                   ^ EXAMPLE numbers')
a.table(['Field', 'Meaning', 'Good'], [
    ['tick', 'Game ticks since boot (60 per second)', 'Rises by 60 per second'],
    ['sim / max', 'Time for one game step, average and worst', 'Far below 16,667 us'],
    ['scene', 'Building the list of textured quads', 'Record it'], ['render', 'Drawing the frame', 'Record it'],
    ['present', 'Sending it to the display', 'Record it'], ['missed', 'Game deadlines missed', '0, or very rare'],
    ['band-order', 'Bands that reached the panel out of order', 'Always 0'],
    ['audio / max … per 5333', 'Time to make 5.33 ms of sound', 'Far below 5,333 us'],
], widths=[1.8, 3.8, 2.2], size=9)
a.p('If render + present is above about 33 ms, the screen runs below 30 fps; the game still runs at 60 Hz. Investigate in this order: the '
    'renderer\'s tables and band buffers in internal RAM rather than PSRAM; the scene builder; flash-cache misses on the busiest textures. '
    'Lowering the picture to 20 fps is the last resort; the 60 Hz game is never sacrificed.')
ok('BENCH PASS: one complete round on the loose switches, with the full art, band-order 0.')

# ======================================================================================================
# STEP 8
# ======================================================================================================
chapter('Step 8 — Sound and power on the bench', 8)
a.p('With the game proven, add the speaker, then learn the power system on USB. The battery itself still waits until the handheld is assembled.')
a.audio('AUDIO GUIDE — Chapter 11: Prove the speaker with the vendor audio example', [
    'The speaker is the PUI Audio AS02808MR-R: 28 mm across, 5.2 mm thick, 8 ohms, 1 watt rated, about 500 hertz resonance. Connect it to the '
    'board\'s speaker header with a matching two-wire lead, and confirm the header on your board.',
    'Run Waveshare\'s audio example at low volume first. If it causes resets, noise or display trouble, remove the speaker and go back to the '
    'last good state. When it plays cleanly, boot STRUTHIO: service mode should say AUDIO OK and MUSIC OK, and the round-clear sting plays when '
    'the checks finish.'])
a.audio('AUDIO GUIDE — Chapter 12: Hear STRUTHIO', [
    'Game sound has two halves. The sound effects are not recordings: like the browser game, the handheld synthesises every flap, chime and '
    'crash from a few numbers the instant the game reports the event. The music is a recording: the browser\'s 160-second loop, stored in its own '
    'area of the flash chip.',
    'Start quiet. The firmware remembers a volume from 0 to 4 and starts at 2. In service mode, hold LEFT for one second to step it; a ring chime '
    'plays at each level. Level 0 is silent.',
    'Then play. Every flap ticks, a ring chimes and dips the music for a moment, a joust crashes, a death falls in pitch. If sound stutters '
    'while the screen is busy, note the log\'s audio time: the sound task runs above the renderer, so the picture should drop a frame first.'])
fig(FG('f12_audio.png'), 'The sound path. Up to the "+" it is the browser game\'s own sound engine, ported to C and checked against it sample by sample.')
a.table(['Game event', 'Sound', 'Music ducks?'], [
    ['Flap', 'short noise tick (at most one per 85 ms)', 'no'], ['Ring', 'bright rising chime', 'yes, briefly'],
    ['Joust clash', 'low crash', 'yes, if you are in it'], ['Joust win', 'rising call', 'yes'],
    ['Player death', 'long falling tone (19 semitones)', 'yes'], ['Egg / hatch', 'plink', 'no'],
    ['Gold ring open / round start', 'sting on the next beat', 'no'], ['Round clear', 'long sting on the next beat', 'yes'],
], widths=[2.2, 3.6, 2], size=9)
a.table(['Volume level', 'Codec output', 'Use'], [
    ['0', 'muted', 'silent play'], ['1', '45 %', 'first power-up with a new speaker'], ['2 (default)', '60 %', 'normal'],
    ['3', '72 %', 'louder rooms'], ['4', '85 %', 'maximum; listen for distortion'],
], widths=[1.6, 1.6, 4.6], size=9)
a.p('The percentages live in firmware/main/main.c (VOLUME_PERCENT). If level 4 distorts on your speaker, lower them there and flash again (menu option 6).')
a.h2('Why the sound fits on the ESP32')
a.table(['Piece', 'Size', 'Where'], [
    ['Synth, conductor, music player', 'a few KB of code, about 4 KB of memory', 'the program, internal RAM'],
    ['Soundtrack', '1.8 MB: 160 s, 24 kHz, 4-bit IMA ADPCM', 'the "music" flash area, 2.9 MB'],
    ['Work per 5.33 ms of sound', 'a few voices, a few multiplies each', 'audio task, core 0, above the renderer'],
], widths=[2.4, 3, 2.4], size=9)
fig(SCH('s4_display_audio.png'), 'Sheet S4 — display and audio wiring on the board: not wired by hand, shown so you can probe it.')
a.h2('The power system')
fig(SCH('s3_power.png'), 'Sheet S3 — power: USB-C, the THOR-503450 cell, and the E-Switch hard cut in BAT+. Fitted in Step 12.')
a.table(['Power-chip setting (AXP2101)', 'Value', 'What it means for you'], [
    ['Charge current', '200 mA', 'Gentle; the THOR cell accepts it'], ['Charge target', '4.1 V', 'Slightly below the cell\'s 4.2 V: kinder to it, a little less runtime'],
    ['Pre / end of charge', '50 mA / 25 mA', 'Standard lithium charging'], ['USB input limit', '4.36 V min, 1,500 mA max', 'A weak USB port may not charge while playing'],
    ['System shut-down', '2.6 V', 'The board switches off before the cell is too empty; the cell\'s own protection is the second guard'],
    ['Power key', 'hold 4 s = off, 128 ms = on', 'The board\'s own key; the E-Switch is the real off'],
    ['Battery temperature pin', 'not measured', 'Use a protected cell (THOR-503450 is)'],
], widths=[2.3, 1.8, 3.7], size=9)
a.p('These are Waveshare\'s own settings (firmware/main/board_pmu.cpp).')
a.h2('LiPo safety rules')
a.table(['Always', 'Never'], [
    ['Use a protected single cell (1S): THOR-503450.', 'Use an unprotected cell, a 2S pack, or AA / NiMH cells on the lithium connector.'],
    ['Check polarity with the meter before the first plug-in.', 'Trust wire colours or "it fits".'],
    ['Insulate bare leads the moment you cut them.', 'Cut both battery leads at once with the same cutters.'],
    ['Charge on a non-flammable surface while you are there.', 'Charge a puffy, dented or hot cell. Retire it.'],
    ['Leave room: the cell must not be squeezed.', 'Squeeze, puncture, bend, or solder onto the cell body.'],
    ['Switch BAT+ only.', 'Switch BAT−.'],
], widths=[3.9, 3.9], size=9)
a.h2('Measuring current draw')
a.steps(['Put an inline USB-C power meter between the charger and the board, battery disconnected.',
         'Record the current at boot, in service mode, in normal play and in a busy scene (Shop Sheet E).',
         'Runtime estimate: hours ≈ 1000 mAh × 0.8 ÷ play current (mA). Example arithmetic only: at 250 mA, about 3.2 hours.',
         'The real runtime is measured later, from a full charge to shutdown, on the finished handheld.'])

# ======================================================================================================
# STEP 9
# ======================================================================================================
chapter('Step 9 — Order the custom controls: STRUTHIO-CP1 and STRUTHIO-CM1', 9)
a.p('The handheld\'s controls are one gold silicone mat (STRUTHIO-CM1) over a small control board (STRUTHIO-CP1). Each key carries a carbon '
    'pill; pressing it bridges a gold comb on CP1, exactly like a game-controller button. Four contacts: LEFT WING, RIGHT WING, DART LEFT, DART RIGHT.')
fig(CAD('drawings', 'face_layout.png'), 'The control face, seen from the front. Dimensions from the speaker-window centre (0, −47).')
a.h2('The control stack')
a.table(['Depth from the front face', 'Layer'], [
    ['0 – 3.0 mm', 'Front shell'], ['3.0 – 4.6 mm', 'Printed carrier: holds CM1, locates CP1 on two heat-stake pins'],
    ['4.6 – 5.6 mm', 'CM1 web (wing travel 1.5 mm, rocker-end travel 1.3 mm)'], ['5.6 – 6.6 mm', 'STRUTHIO-CP1, 1.0 mm FR-4'],
    ['6.6 – 7.2 mm', 'Speaker front gasket'], ['7.2 – 12.4 mm', 'PUI speaker; a closed tube carries its rear cavity to the back shell'],
], widths=[2.2, 5.6], size=9)
a.p('The rocker has a centre stop 1.1 mm deep: a flat press on the middle stops before either pill touches, so it never fires both ends. '
    'A one-end press moves the centre only 0.84 mm. The speaker fires through a 13 mm window in CP1 and the mat into the grille between the wings.')
a.h2('Ordering STRUTHIO-CP1 (control PCB)')
a.steps(['Upload handheld/cad/handheld/cp1/cp1_gerbers.zip to any PCB maker that accepts Gerber + Excellon files.',
         'Choose: 2 layers, FR-4, 1.0 mm thick, 1 oz copper, ENIG finish (not HASL: the contacts must be flat gold), any mask colour, white legend.',
         'Board size 82.25 x 35.53 mm. The outline already includes the speaker window and the two screw notches.',
         'Check the maker\'s preview against Figure 9.3: four combs on the front, five wire pads labelled G, L, DL, DR, R on the back.'])
fig(CAD('drawings', 'STRUTHIO-CP1_drawing.png'), 'STRUTHIO-CP1 drawing (PDF: cad/handheld/drawings/STRUTHIO-CP1_drawing.pdf).')
fig(CAD('cp1', 'cp1_layers.png'), 'CP1 copper as generated: front combs and GND bus, back traces and the wire-pad row.')
a.h2('Quoting STRUTHIO-CM1 (silicone keys)')
a.steps(['Send cad/handheld/drawings/STRUTHIO-CM1_drawing.pdf (and the STL, stl/struthio_mat.stl, if asked) to a silicone keypad moulder.',
         'Ask for the values on the drawing: gold VMQ silicone, 50 Shore A ±5, 6.0 x 0.5 mm carbon pills ≤100 Ω; wings 1.5 mm / 125 g / 45–55 % snap; '
         'rocker ends 1.3 mm / 150 g / 40–50 % snap.',
         'Ask for first samples with measured force-travel curves. The moulder designs the web that gives the feel; the drawing fixes the outline, '
         'key faces, pill positions and heights.',
         'Before samples arrive, print the mat STL in TPU or resin as a shape check only: it will not feel right or make contact.'])
fig(CAD('drawings', 'STRUTHIO-CM1_drawing.png'), 'STRUTHIO-CM1 manufacturer drawing (PDF: cad/handheld/drawings/STRUTHIO-CM1_drawing.pdf).')
a.audio('AUDIO GUIDE — Chapter 13: Tune the silicone with a measured first sample', [
    'Do not judge silicone from a render. Measure travel and force, then let several people play a real session. Watch for missed flaps, double '
    'flaps, fatigue, clean STRAIGHT chords, rocker-end separation, and whether the keys rebound quickly without feeling clicky.',
    'The targets are about 1.5 mm and 125 grams on the wings, and 1.3 mm and 150 grams on each rocker end. Ask the moulder to adjust the web '
    'only if real play proves a change is needed.'])

# ======================================================================================================
# STEP 10
# ======================================================================================================
chapter('Step 10 — Print and prove the shell', 10)
a.p('Treat the plastic like the electronics: prove it in stages. The front first, as a fit coupon in cheap PLA; the back only when the '
    'front, the controls and the speaker fit.')
a.audio('AUDIO GUIDE — Chapter 14: Begin the plastic with a fit coupon', [
    'The shell is sculpted: a concave top and bottom, a waist below the screen, flared hips around the wings, a rounded front edge, and sides '
    'that roll into a pillow back. It is 88 by 137.4 by 23 millimetres.',
    'Print the front first. Check the screen opening, the board width and the lens land, then seat the carrier, CP1, a CM1 sample or its '
    'printed stand-in, and the speaker. Nothing may be pressed at rest: every key must move freely and return.',
    'Only then print the back. It carries the screw posts, the battery cavity, the speaker\'s rear tube, the E-Switch cradle on the player\'s '
    'left wall, and the USB-C jack opening in the bottom, right of centre.'])
fig(CAD('renders', 'internals_angle.png'), 'Inside the shell: the board, CP1 with the speaker behind it, the E-Switch on the left wall, the USB-C channel.', 4.6)
a.h2('Print files and settings')
a.table(['File (handheld/cad/handheld/stl/)', 'Part', 'Material and settings'], [
    ['struthio_front.stl', 'Front shell with the carrier', 'Fit coupon: PLA, 0.2 mm, 3 walls, 20 %. Final: PETG or ASA, 0.2 mm, 4 walls, 25–30 %'],
    ['struthio_back.stl', 'Back shell', 'PETG or ASA, 0.2 mm, 4 walls, 25–30 %; open side down on the bed'],
    ['struthio_mat.stl', 'CM1 shape check only', 'TPU or resin; never the real keys'],
], widths=[2.4, 2, 3.4], size=9)
a.bullets(['Front shell: print it face down for the smoothest face; check the slicer preview for supports under the carrier.',
           'Back shell: print it open side down, so the pillow back is the top surface.',
           'These are common starting values, not project measurements: your printer may need others. Change one thing at a time and write it down.'])
a.h2('What to confirm during fit')
a.checks(['The display glass is untouched; the lens land is flat.', 'CP1 and the CM1 sample seat freely; no key is pressed at rest.',
          'The speaker seats on its gasket; the grille slots are clear.', 'The battery cavity takes the THOR cell without squeezing.',
          'The E-Switch actuator moves through its slot over the full travel.', 'The USB-C jack lines up with your extension.',
          'The four M2 x 10 screws pull the shells together without cracking a post.'])
a.h2('CAD numbers (handheld/cad/handheld/struthio_handheld.scad)')
a.p('Millimetres. x to the right as seen from the front, y up, z from the front face back. Change a number at the top of the file, export '
    'again and run the checks; never edit the STL files.')
a.table(['Parameter', 'Value', 'What it controls'], [
    ['Centre line', 'y +64 … −70', 'Screen, board and rocker datums'],
    ['TOP_LIFT / BOTTOM_DROP', '2.0 / 1.8', 'Concave top and bottom; overall 88 x 137.4 x 23'],
    ['SHELL_RF / SHELL_ZS / SHELL_RB', '1.6 / 9.0 / 12.0', 'Front edge radius / straight side wall depth / how far the back rolls in'],
    ['BTN_X, BTN_Y', '±24, −46', 'Wing key centres; faces 28 x 18.5'],
    ['Rocker', '44 x 9 face at y −61.2; contacts x ±12', 'DART rocker; contacts 24.0 apart'],
    ['Travel', 'wings 1.5, rocker ends 1.3', 'Pill face above CP1 at rest; rocker centre stop 1.1'],
    ['SPKR_X, SPKR_Y', '0, −52.6', 'Speaker behind CP1; window Ø13 at (0, −47); pocket Ø29.2'],
    ['Battery cavity', '37.4 x 55.4 x 6.35 at y 13.5', 'THOR-503450 (36 x 54 x 6.2 needed)'],
    ['Screws', '±35, 55.5 and ±35, −63', 'M2 x 10 socket head from the back; head seat 13 mm deep; 1.7 mm pilots in the front bosses'],
    ['USB_PLUG_*', 'x −6…16, y −37.5…−32.8', 'Right-angle plug keep-out at the board (position: confirm)'],
    ['USB jack', 'x +19.25 in the bottom wall', 'Panel jack'],
    ['E-Switch', 'player\'s left wall, y 12', 'BAT+ hard cut; actuator 2.1 mm proud'],
], widths=[2.3, 2.3, 3.2], size=8.5)
stop('USB-C: the position of the board\'s own USB-C connector is NOT confirmed. The CAD assumes bottom centre with a right-angle plug. If your '
     'board differs, change USB_PLUG_* in struthio_handheld.scad and re-run the checks before printing the back.')
a.h2('Export and check (optional: only if you change the CAD)')
code('cd handheld/cad/handheld', './export_handheld.sh     # OpenSCAD 2021.01+, Python trimesh + shapely + manifold3d',
     '#  -> stl/struthio_front.stl, struthio_back.stl, struthio_mat.stl, svg/, dxf/, renders/, art/',
     '#  -> HANDHELD CAD CHECK: all pass   (55 checks)',
     'python3 check_handheld.py   # the checks alone', 'python3 cp1/make_cp1.py     # CP1 Gerbers + "CP1 DRC: all pass"')
a.p('The checks prove: every part is one watertight solid; each key passes its opening with clearance and is captured by its flange; each '
    'pill rests at its exact travel; CP1 and the mat clear the board and the screw posts; the speaker window is sealed; the battery, board and '
    'E-Switch volumes are free of plastic; the wall is at least 1.8 mm through the roll; each screw has a pilot, a clearance hole, a seat and '
    'at least 4 mm of thread; the printed back has the power switch on the player\'s left; every sticker hole sits inside the sticker.')

# ======================================================================================================
# STEP 11
# ======================================================================================================
chapter('Step 11 — Lens, sticker art and the front face', 11)
a.p('The face is what turns a working prototype into a convincing handheld. Do it only when the shell fit is already right.')
a.audio('AUDIO GUIDE — Chapter 15: Finish the face', [
    'A clear 1.0 to 1.5 millimetre acrylic or polycarbonate lens sits in the recessed lens land. Keep a gap between the lens and the display '
    'glass and never clamp the glass.',
    'The art is a laminated sticker in its own shallow recess below the screen, cut around the two wings, the rocker and the five grille slots. '
    'Print it at true size: the PDF is the safest file.'])
a.table(['File (handheld/cad/handheld/)', 'Use'], [
    ['art/sticker_front_print.pdf', 'THE PRINT FILE: exactly 87.0 x 43.9 mm including bleed'],
    ['art/sticker_front_print.png', 'The same at 600 dpi (2056 x 1038 px), for programs that need an image'],
    ['art/sticker_front_proof.png', 'The art with the cut lines drawn on, to check on screen'],
    ['svg/struthio_sticker_cut.svg', 'The cut outline: edge, two wing holes, the rocker hole, five grille slots'],
], widths=[2.8, 5], size=9)
a.steps(['Print the PDF on sticker paper at 100 % / "Actual size". Turn off "Fit to page" and any scaling.',
         'Measure the print: it must be 87.0 mm wide. If not, fix the printer scaling first.',
         'Cover it with clear laminating film (cold laminate, or clear packing tape for a prototype).',
         'Cut along the outline: edge, both wing holes, the rocker hole, the five grille slots (the proof shows where).',
         'Dry-fit on the printed front before peeling: the wings, the rocker and the grille must line up with clearance.',
         'Peel a corner, align the top edge first, then smooth down from the centre.'])
fig(CAD('art', 'sticker_front_proof.png'), 'The sticker proof with its cut lines.', 5.2)
fig(CAD('renders', 'struthio_front_art.png'), 'The face as the player sees it: the sticker composed onto the CAD front, with a real frame from the panel renderer.', 3.4)
a.h2('Cosmetic rules')
a.bullets(['Lens 1.0–1.5 mm; at least about 0.4 mm between the lens and the display glass.', 'Never clamp the LCD glass.',
           'Print the sticker with its bleed, laminate it, cut it carefully.', 'The finish must never get in the way of service.'])

# ======================================================================================================
# STEP 12
# ======================================================================================================
chapter('Step 12 — Final assembly', 12)
a.p('By now you have a proven board, a proven game, proven controls and sound, a fitted shell and a finished face. Assembly is packaging, not faith.')
fig(FG('p13_exploded.png'), 'Every part of the handheld, front to back.')
a.audio('AUDIO GUIDE — Chapter 16: USB extension, power switch and battery come last', [
    'The board sits inside the shell, so a short full-data USB-C extension carries its connector to the panel jack in the bottom wall. Full data '
    'matters: the same connector charges, flashes and carries the log.',
    'The power switch is a real cut, like a classic handheld. The battery\'s plus lead goes to the E-Switch\'s common pin; one throw goes on to '
    'the board\'s BAT+; the other throw stays unconnected and insulated, and that position is OFF. The minus lead goes straight to the board.',
    'Switching off cuts power at any moment, and that is fine: the firmware saves the high score, DART mode and volume only when they change, '
    'never on a timer, and reads back every flash write. The settings store is built to survive power loss.',
    'The battery goes in last, after a meter check of polarity, held softly, never clamped.'])
fig(SCH('s5_harness.png'), 'Sheet S5 — the harness inside the shell, seen from the back (the player\'s left is on the right), to scale.')
a.h2('Assembly order')
a.steps(['Fit the lens and sticker on the front (Step 11).',
         'Seat CM1 in the carrier, then CP1 on its two heat-stake pins (a touch of a hot iron on each pin). Every key and both rocker ends move freely.',
         'Solder the five control wires to CP1\'s back pads: G (black), L (white), DL (yellow), DR (orange), R (blue). Shop Sheet F gives the other ends.',
         'Seat the PUI speaker on its front gasket behind CP1; lead to the board\'s speaker header.',
         'Fit the USB-C extension: panel jack in the bottom wall, plug into the board.',
         'Mount the board, screen to the front; check the screen sits square behind the lens.',
         'Wire the controls to GPIO17, 18, 21, 38 and GND. Power on USB: service mode, each control counts +1, then set DART mode to ROCKER ONLY.',
         'Fit the E-Switch in its cradle on the player\'s left wall. Meter the COMMON pin. Wire THOR BAT+ → COMMON, ON throw → board BAT+; insulate the other throw.',
         'Meter-check the THOR cell\'s polarity at the connector, then plug it in, switch OFF. Battery in its cavity, soft retention only.',
         'Close the back: four M2 x 10 screws, snug, not tight. Switch on.'])
a.h2('Assembly discipline')
a.bullets(['Keep wires away from the speaker cone and the battery.', 'Leave enough slack to open the shell again.',
           'Strain-relieve the wires at CP1.', 'Insulate anything that could touch a screw, a solder joint or a sharp edge.',
           'Photograph the wiring before closing the shell.'])

# ======================================================================================================
# STEP 13
# ======================================================================================================
chapter('Step 13 — Acceptance and troubleshooting', 13)
a.p('A finished build boots every time, plays correctly, charges sensibly, and can still be serviced.')
a.audio('AUDIO GUIDE — Chapter 17: Final acceptance', [
    'Think of acceptance as a checklist, not an exam. Power-cycle twenty times: every boot reaches a live run. Press each control a hundred '
    'times: no phantom double flaps. Try fifty two-wing chords at different timings: straight-up engages inside 100 milliseconds without '
    'delaying the first press. Play long enough to notice any accidental darts.',
    'Run the golden replay in service mode. Play a busy scene for ten minutes and watch for tearing or missed deadlines. Leave it playing for '
    'thirty to sixty minutes. Measure the runtime from a full charge to shutdown.'])
a.audio('AUDIO GUIDE — Chapter 18: Troubleshooting rules', [
    'When something fails, remove the newest change and go back to the last gate that passed. If the vendor example never worked, you do not '
    'have a STRUTHIO problem yet. If the greybox works and the full art does not, look at the art flash, not the buttons. If loose switches '
    'work and the silicone keys do not, it is the mechanical stack, not a GPIO. If USB power works and battery power does not, it is the power '
    'wiring and polarity, not the game.',
    'Keep notes. Stop when a gate fails: the sequence is designed so you never debug ten systems at once.'])
a.h2('Acceptance checklist')
a.checks(['USB-C power, flashing and the log all work through the panel jack.', 'Twenty cold boots, twenty live runs.',
          'LEFT, RIGHT, DART LEFT and DART RIGHT each register once per press.', 'Chords and DART behave in real play (DART mode ROCKER ONLY).',
          'GOLDEN PASS on the finished handheld.', 'Sound: effects and music clean at the chosen volume, no stutter in a 10-minute session.',
          'The battery charges; twenty hard OFF/ON cycles boot cleanly; the high score survives.',
          'The shell closes without crushing the screen, the battery or a wire.', 'The face, lens and keys look and feel intentional.'])
fig(FG('p02_flow.png'), 'The troubleshooting flow (also Shop Sheet D).', 6.2)
a.h2('Fault-finding by symptom')
a.table(['Symptom', 'Check in this order'], [
    ['Nothing on screen and no log', 'Data cable (not charge-only) → another USB port → vendor example → BOOT + RESET flash'],
    ['Log runs, screen dark', 'Torch on the glass (backlight) → "TCA9554 not found" in the log → board revision'],
    ['Picture in stripes or shifted blocks', 'band-order count → "transfer timeout" lines → report with the log'],
    ['Greybox after the FULL ART flash', 'Boot line says "renderer greybox"? → "assets:" lines → flash with option 5 (STRUTHIO_ART=full) → doctor'],
    ['GOLDEN FAIL', 'Copy the whole log line (it names the tick) → do the desktop checks pass?'],
    ['A control never registers', 'Service screen → meter the key or switch → the wire → the header pin → GND'],
    ['A control always DOWN', 'Solder bridge → wrong leg pair → wire touching GND → a key pressed by the shell'],
    ['Double flaps from one press', 'Count rises by 2? → cracked or cold joint → loose wire'],
    ['Controls fine until the screen turns on', 'A camera fitted? (GPIO17/18/21/38 are camera pins) → board revision'],
    ['Resets during play', 'Reason after reset (watchdog, brown-out) → USB supply → the newest part removed?'],
    ['High score lost', 'Was erase-flash run? (it clears nvs) → otherwise report with the log'],
    ['Charges on USB, dead on battery', 'Polarity at the connector → E-Switch position and wiring (COMMON?) → cell protection tripped (charge on USB)'],
    ['No sound', 'Service screen AUDIO line → volume not 0 → vendor audio example → speaker header'],
    ['Effects but no music', '"MUSIC NONE" → flash with option 5 → doctor (struthio_music.ima)'],
    ['Crackle or stutter', 'Lower the volume → log "audio" max time → USB supply → speaker rubbing in the shell'],
], widths=[2.6, 5.2], size=9)

# ======================================================================================================
# SOFTWARE
# ======================================================================================================
chapter('How the STRUTHIO software works (for the curious)', 'S')
a.p('You can build the whole handheld without this chapter. Read it when you want to know why the project trusts a board it has never seen.')
a.audio('AUDIO GUIDE — Software: one game, proven twice', [
    'STRUTHIO began as a browser game, STRUTHIO ARCADE 1.8.0, written in JavaScript. A handheld cannot run a browser, so the game was rewritten '
    'in portable C. A rewrite is easy to get almost right and very hard to get exactly right, and almost right is not good enough: one '
    'different bounce changes everything after it.',
    'So the project records golden traces from the browser: the inputs for every tick, and a SHA-256 fingerprint of the whole game state after '
    'every tick. The C game replays the same inputs and must produce the same fingerprint, tick after tick. Five traces cover 75,144 ticks, '
    'about 21 minutes of play, including deaths, rounds up to 11 and hundreds of jousts. All five match exactly.',
    'The firmware carries one of those traces. Service mode replays it on the ESP32 itself. GOLDEN PASS means the chip in your hands runs the '
    'same game, not an imitation of it.'])
fig(FG('f08_golden.png'), 'The golden replay: one trace proves the C game on the desktop and on the device.')
a.table(['Trace', 'Ticks', 'Score', 'Round', 'Deaths', 'Jousts', 'Eggs', 'Darts'], [
    ['climb', '10,011', '60,250', '4', '0', '13', '3', '30'], ['duel', '20,000', '37,750', '3', '23', '37', '3', '237'],
    ['late', '10,990', '136,250', '11', '0', '60', '13', '67'], ['mortal', '14,143', '77,500', '5', '12', '23', '3', '81'],
    ['raw', '20,000', '65,750', '5', '30', '65', '15', '194'],
], size=9)
a.h2('Map of the source')
a.table(['File', 'Job'], [
    ['core/struthio_sim.c', 'The game rules and physics, one tick at a time (st_step)'],
    ['core/struthio_tower.c, struthio_rules.h', 'Tower layout and rulebook values, generated from the browser game'],
    ['core/struthio_input.c', 'The input normalizer: presses → flaps, STRAIGHT chord, steering, DART'],
    ['core/struthio_digest.c, struthio_replay.c', 'SHA-256 of the state; golden-trace replay'],
    ['render/struthio_scene.c', 'The textured quads for a frame, exactly as the browser builds them'],
    ['render/struthio_panel.c', 'Draws those quads in 16-row bands at 320 x 480'],
    ['render/struthio_pak.c', 'Reads the art pack mapped from flash'],
    ['render/struthio_greybox.c', 'The flat-colour renderer and the service-screen text'],
    ['audio/struthio_audio.c', 'The browser\'s sound engine in C: conductor, 7-voice synth, soundtrack, output'],
    ['firmware/main/main.c', 'The tasks: controls (1 kHz), game (60 Hz), render (two cores), audio, saving'],
    ['firmware/main/struthio_buttons.c', 'Debounce, press counts, DART modes and the rocker, service-mode entry'],
    ['firmware/main/service.c', 'The service screen and the on-device golden replay'],
    ['firmware/main/board_waveshare_35b.c, board_pmu.cpp', 'The board adapter, from Waveshare\'s example: I2C, power chip, LCD, backlight, codec'],
    ['firmware/main/board_pins.h', 'The full pin map (Shop Sheet F)'],
], widths=[3.2, 4.6], size=9)

# ======================================================================================================
# SHOP SHEETS
# ======================================================================================================
chapter('SHOP SHEET A — Parts list', None)
a.table(['Qty', 'Part', 'Specification', 'When', 'Note'], [
    ['1', 'Main board', 'Waveshare ESP32-S3-Touch-LCD-3.5B', 'Now', 'Record the revision'],
    ['2', 'Bench wing switches', 'Omron B3F-4050 (or -4055) + perfboard', 'Now', 'Bench build only'],
    ['1', 'Speaker', 'PUI Audio AS02808MR-R, 28 mm, 8 Ω, 1 W, 5.2 mm', 'After gate 6', 'Volume 1–2 first'],
    ['1', 'Control PCB', 'STRUTHIO-CP1, 2 layers, 1.0 mm FR-4, ENIG', 'After the bench PASS', 'cad/handheld/cp1/cp1_gerbers.zip'],
    ['1', 'Silicone keys', 'STRUTHIO-CM1, gold VMQ, 50 Shore A ±5, 4 carbon pills', 'After the bench PASS', 'cad/handheld/drawings/STRUTHIO-CM1_drawing.pdf'],
    ['1', 'Battery', 'THOR-503450, 3.7 V 1000 mAh, protected, about 5 x 34 x 52 mm', 'Last', 'Matching MX1.25 2-pin lead; meter the polarity'],
    ['1', 'Power switch', 'E-Switch 500SSP1S1M7QEA, SPDT slide', 'With the battery', 'Hard cut in BAT+'],
    ['1', 'USB-C extension', 'Short male-to-female, full data + power', 'Fitting the shell', 'Fit-selected'],
    ['1 set', 'Shell', 'struthio_front.stl + struthio_back.stl', 'Step 10', 'Front coupon first'],
    ['4', 'Screws', 'M2 x 10 socket head, thread-forming for plastics', 'Step 10', 'Into 1.7 mm pilots'],
    ['1', 'Lens', '1.0–1.5 mm clear acrylic or polycarbonate, about 56 x 80 mm', 'Step 11', 'Cut to the lens land'],
    ['1', 'Art sticker', 'art/sticker_front_print.pdf on sticker paper + laminate', 'Step 11', 'Print at 100 %'],
    ['', 'Wire', '~24 AWG stranded (controls), ≥ 22 AWG (battery path); heat-shrink', 'Now', 'Colours: Shop Sheet F'],
], widths=[0.6, 1.5, 3, 1.3, 2.2], size=8.5)
rule('Battery capacity is 1000 mAh. Do not print a runtime claim until you have measured one, full charge to shutdown.')

chapter('SHOP SHEET B — Build checklists', None)
for title_, items in [
    ('Computer', ['ESP-IDF v5.5.5 installed; idf.py --version prints v5.5.5', 'Package at C:\\struthio (or ~/struthio), no spaces',
                  'Doctor (option 1): no FAIL', 'Desktop checks: GOLDEN REPLAY all 5 traces bit-exact; PASS: wing buttons (…)']),
    ('Bench board', ['Board revision recorded', 'Camera connector empty', 'Known-good USB-C DATA cable', 'Waveshare example runs',
                     'GREYBOX test boots (option 4)', 'Service mode opens', 'GOLDEN PASS 10011 TICKS', 'FULL ART flash: renderer panel (asset pack)', 'band-order stays 0']),
    ('Controls', ['GPIO17 = LEFT WING', 'GPIO18 = RIGHT WING', 'GPIO21 = DART LEFT (handheld)', 'GPIO38 = DART RIGHT (handheld)',
                  'All contacts return to GND', 'High when idle, low when pressed', '100 ms straight-up chord tested',
                  'Bench: DART mode C works. Handheld: ROCKER L and R count +1 per press; DART mode ROCKER ONLY']),
    ('Sound', ['Speaker on the confirmed speaker header', 'Vendor audio example clean at low volume', 'Service mode: AUDIO OK, MUSIC OK, round-clear sting heard',
               'Volume chosen (LEFT hold) and noted', 'In play: flap, ring, joust, death over the music', 'Log "audio" time recorded (budget 5,333 us)']),
    ('Custom parts and shell', ['CP1 delivered: ENIG, 1.0 mm; each comb beeps to its pad; no comb shorted to GND', 'CM1 sample measured: travel, force, snap',
                                'Front coupon: glass untouched; CP1 and CM1 seat freely; no key pressed at rest', 'Board USB-C position measured; USB_PLUG_* matches',
                                'E-Switch pins checked against the part', 'Back shell: speaker, battery cavity, E-Switch, jack all fit']),
    ('Power and battery', ['Protected 1-cell LiPo (THOR-503450)', 'Polarity metered before plug-in', 'BAT+ through the E-Switch COMMON → ON throw; other throw insulated',
                           'Charging works with the switch ON', 'Twenty hard OFF/ON cycles boot cleanly', 'Runtime measured before any label is printed'])]:
    a.h2(title_); a.checks(items)

chapter('SHOP SHEET C — Acceptance record', None)
a.table(['Test', 'Method', 'Pass requirement', 'Result'], [
    ['Cold boot', 'Power-cycle 20 times', '20 of 20 reach a live run', '________'],
    ['Input bounce', 'Each control 100 times', 'No phantom double presses; counts match', '________'],
    ['Chord', '50 two-wing chords', 'Straight-up inside 100 ms; no lag on the first press', '________'],
    ['DART', '100 left + 100 right rocker presses', 'Direction always right; no accidental darts', '________'],
    ['Simulation', 'Service-mode golden replay', 'GOLDEN PASS on the device', '________'],
    ['Frame pacing', 'Busiest scene, 10 minutes', 'No tearing; missed 0; band-order 0', '________'],
    ['Sound', '10-minute session', 'Clean at the chosen volume; no stutter', '________'],
    ['Persistence', 'Set a high score, hard OFF / ON', 'The high score returns', '________'],
    ['Hard power', '20 E-Switch OFF / ON cycles', 'Clean boot every time', '________'],
    ['Soak', '30–60 minutes of play', 'No crash, no corruption, nothing hot', '________'],
    ['Runtime', 'Full charge → shutdown', 'Hours: ________', '________'],
], widths=[1.4, 2.4, 3, 1.2], size=9)

chapter('SHOP SHEET D — Troubleshooting flow', None)
a.figure(FG('p02_flow.png'), 'Go down until a question says NO; fix only that; then start again from the top of that step.', 6.8)

chapter('SHOP SHEET E — Measurement log', None)
a.p('Print this page and fill it in as you go. These numbers are the project\'s real data: nobody has them yet but you.')
a.h2('Board and firmware')
a.table(['Item', 'Your value'], [['Board revision printed on the PCB', ''], ['ESP-IDF version (idf.py --version)', ''],
                                  ['Firmware build date (service screen)', ''], ['Serial port', ''], ['AXP2101 id (boot log)', '']], widths=[3.6, 4.2])
a.h2('Service screen')
a.table(['Run', 'RESET', 'PSRAM K', 'RAM K', 'GOLDEN', 'SIM us', '+DIGEST us', 'PANEL ms', 'FPS'], [[str(i), '', '', '', '', '', '', '', ''] for i in (1, 2, 3)], size=9)
a.h2('Performance line during play')
a.table(['Scene', 'sim / max', 'scene', 'render', 'present', 'missed', 'band-order', 'audio'],
        [[s_, '', '', '', '', '', '', ''] for s_ in ('Start of a run', 'Normal play', 'Busy scene', 'After 10 min')], size=9)
a.h2('Current and battery')
a.table(['Condition', 'mA', 'Notes'], [[c_, '', ''] for c_ in ('Boot', 'Service screen', 'Normal play', 'Busy play', 'Charging (battery fitted)', 'Runtime full → shutdown (hours)')], widths=[3.2, 1.2, 3.4])
a.h2('Controls and fit')
a.table(['Sample / print', 'Part', 'Travel (mm)', 'Force (g) / snap', 'Result'], [[str(i), '', '', '', ''] for i in range(1, 5)], size=9)

chapter('SHOP SHEET F — Pin and wire card', None)
a.p('From firmware/main/board_pins.h and Waveshare\'s example (commit 840daf2). Header pin numbers are from Waveshare\'s published pinout image: confirm them on your board.')
a.table(['#', 'From', 'To', 'Wire', 'Notes'], [
    ['W1', 'GPIO17 (header pin 16, confirm)', 'CP1 pad L — LEFT WING', 'white, ~24 AWG', 'Bench: LEFT switch S leg'],
    ['W2', 'GPIO18 (header pin 18, confirm)', 'CP1 pad R — RIGHT WING', 'blue, ~24 AWG', 'Bench: RIGHT switch S leg'],
    ['W3', 'GPIO21 (header pin: confirm)', 'CP1 pad DL — DART LEFT', 'yellow, ~24 AWG', 'Handheld'],
    ['W4', 'GPIO38 (header pin: confirm)', 'CP1 pad DR — DART RIGHT', 'orange, ~24 AWG', 'Handheld'],
    ['W5', 'GND (e.g. header pin 30, confirm)', 'CP1 pad G — common ground', 'black, ~24 AWG', 'Bench: both switches\' G legs'],
    ['W6', 'Board speaker header + / −', 'PUI AS02808MR-R', '2-core lead', 'Confirm the header'],
    ['W7', 'THOR-503450 BAT+', 'E-Switch COMMON', 'red, ≥ 22 AWG', 'Meter COMMON first'],
    ['W8', 'E-Switch ON throw', 'Board BAT+', 'red, ≥ 22 AWG', 'Other throw: insulated = OFF'],
    ['W9', 'THOR-503450 BAT−', 'Board BAT−', 'black, ≥ 22 AWG', 'Never switched'],
    ['W10', 'USB-C panel jack', 'Board USB-C', 'full-data extension', 'Flashing needs data'],
], widths=[0.6, 2.4, 2.3, 1.4, 1.9], size=8.5)
a.table(['Function', 'GPIO', 'Notes'], [
    ['LEFT / RIGHT WING', '17 / 18', 'Input, pull-up, active low'], ['DART LEFT / RIGHT', '21 / 38', 'Input, pull-up, active low'],
    ['LCD (AXS15231B, QSPI)', 'CS 12, SCLK 5, D0–D3 1–4', 'On the board'], ['Backlight', '6 (PWM)', 'On the board'],
    ['LCD reset', 'TCA9554 EXIO1', 'Through the I/O expander'], ['I2C', 'SDA 8, SCL 7', 'Power chip, expander, codec, touch, IMU, clock'],
    ['I2S audio', 'MCLK 44, BCLK 13, LRCK 15, DOUT 16, DIN 14', 'ES8311 codec'], ['SD card', 'CMD 10, CLK 11, D0 9', 'Unused'],
    ['Camera (never fit)', 'XCLK 38, PCLK 41, VSYNC 17, HREF 18, D 45 47 48 46 42 40 39 21', 'Shares the control pins'],
    ['BOOT / USB / UART0 TX', '0 / 19, 20 / 43', 'Do not use'], ['Spare (no camera)', '39, 40, 41, 42, 47, 48', 'Avoid 45 / 46 (strapping)'],
], widths=[2, 3.4, 2.4], size=8.5)
a.table(['I2C device', 'Address', 'Job'], [['AXP2101', '0x34', 'Power, charging, power key'], ['TCA9554', '0x20', 'I/O expander (LCD reset)'],
                                           ['ES8311', '0x18', 'Audio codec'], ['Touch controller', '0x3B', 'Unused'], ['QMI8658', '0x6B', 'Motion sensor, unused'],
                                           ['PCF85063', '0x51', 'Real-time clock, unused']], widths=[2, 1.4, 4.4], size=8.5)

chapter('SHOP SHEET G — Glossary', None)
a.table(['Term', 'Meaning'], [
    ['ADPCM', 'Sound stored in 4 bits per sample; the soundtrack uses it (1.8 MB for 160 s).'],
    ['Active low', 'A signal that means "on" when it reads 0 V.'],
    ['Art pack (struthio.pak)', 'Every texture and HUD layer at panel resolution, 8.3 MB, in the "assets" flash area.'],
    ['AXP2101', 'The power chip: charger, supply rails, power key.'], ['AXS15231B', 'The display controller behind the 320 x 480 panel.'],
    ['Band', '16 rows of the screen, drawn and sent as one piece; 30 bands make a frame.'],
    ['Bench build', 'The bare board on the desk with two switches: proves the electronics and the game.'],
    ['Bounce / debounce', 'A contact chatters as it closes; the firmware waits for 8 ms of stable signal.'],
    ['Chord', 'Both wings within 100 ms: STRAIGHT (fly straight up).'],
    ['CM1 / CP1', 'STRUTHIO-CM1, the silicone key mat; STRUTHIO-CP1, the control PCB under it.'],
    ['Codec', 'The chip that turns numbers into a speaker signal (ES8311).'],
    ['DART', 'The forward dash attack. Handheld: the two-end rocker. Bench: DART mode C (both wings held 200 ms).'],
    ['dB / PSNR', 'How close two pictures are; 30 dB looks identical to most eyes.'],
    ['Digest / SHA-256', 'A fingerprint of the whole game state.'], ['Ducking', 'Turning the music down for a moment under a sound effect.'],
    ['E-Switch', 'The slide switch that cuts the battery\'s plus lead: the real OFF.'],
    ['ESP32-S3', 'The dual-core 240 MHz processor, with 8 MB PSRAM and 16 MB flash.'], ['ESP-IDF / idf.py', 'Espressif\'s toolkit / its command.'],
    ['Golden trace', 'A browser recording of inputs plus the expected state every tick.'],
    ['Greybox', 'The flat-colour renderer: the first-boot test, or when the art pack is absent.'],
    ['Handheld', 'The finished machine: silicone controls, speaker, battery, sculpted shell.'],
    ['HUD', 'The score, round, rings, rivals and Joust Marks at the top of the screen.'],
    ['Joust Marks', 'Your lives: 11 at the start.'], ['Monitor', 'The log window (idf.py monitor). Leave with Ctrl + ].'],
    ['NVS', 'The small flash area for settings: high score, DART mode, volume.'],
    ['Partition', 'A named flash area: factory (program), assets, music, nvs, phy_init.'],
    ['Pull-up', 'A resistor that holds an input high until something pulls it low.'],
    ['Service mode', 'The hidden diagnostic screen: hold both wings at power-on.'],
    ['STRUTHIO_ART', 'The build switch: full (the art pack) or greybox (the flat-colour test).'],
    ['Tick', 'One game step; 60 per second.'], ['Watchdog', 'Resets the chip if the game hangs (3 s), back into play.'],
], widths=[2, 5.8], size=9)

# ======================================================================================================
# FAQ
# ======================================================================================================
chapter('Frequently asked questions', None)
for q, ans in [
    ('Do I need to know C?', 'No. You build and flash the code as it is, with the commands in this manual or the menu.'),
    ('Can I use a different ESP32 board?', 'Not without changing the board adapter: the firmware targets the Waveshare ESP32-S3-Touch-LCD-3.5B.'),
    ('Why is the touch screen not used?', 'Play is physical by design: two silicone wings and a DART rocker.'),
    ('Why can\'t I fit the camera?', 'Its pins are the control pins (17, 18, 21, 38). Fitting it would fight the buttons.'),
    ('Why does DART have its own rocker?', 'Steering holds a wing, so wing gestures misfire. A rocker end is a clear, separate press: one dart, the way you meant.'),
    ('The first boot shows flat colours. Is it broken?', 'No: that is the greybox test (STRUTHIO_ART=greybox). Menu option 5 flashes the real art.'),
    ('I restored the art but still see greybox.', 'The build remembers STRUTHIO_ART. Flash with option 5, or -D STRUTHIO_ART=full.'),
    ('Do I need Node or the browser game?', 'No. The package has everything the handheld needs, including the prebuilt art and soundtrack.'),
    ('Will flashing erase my high score?', 'No. Only "idf.py erase-flash" (menu option 9) clears the high score, DART mode and volume.'),
    ('How do I get to service mode?', 'Power off, hold both wings, power on, keep holding for about a second.'),
    ('Is there sound?', 'Yes: the browser game\'s effects and its music. No sound? Check the AUDIO line and the volume in service mode.'),
    ('Can I really switch it off like a Game Boy?', 'Yes. The E-Switch cuts the battery. Settings are saved only when they change, and the store survives power loss.'),
    ('Why is the shell 137.4 mm tall?', 'The rocker sits below the wings and the speaker between them must clear the board\'s USB-C plug: 134 mm on the centre line. '
     'The concave top and bottom lift the corners by 3.4 mm more (TOP_LIFT, BOTTOM_DROP).'),
    ('Which side is the power switch?', 'The player\'s left side, seen from the front. The USB-C jack is in the bottom, right of centre.'),
    ('Can I order CP1 now?', 'Yes, once the bench build passes: cp1_gerbers.zip goes straight to a PCB maker. It is cheap; order it before the silicone samples.'),
    ('The log scrolls too fast.', 'Ctrl + T then Y pauses it; Ctrl + T then L saves it to a file.'),
    ('Something smells hot.', 'Unplug USB and the battery at once. Wait until it is cool. Look for a short with the meter, power off.')]:
    a.p(ans, bold_lead=q + '  ')

# ======================================================================================================
# APPENDIX
# ======================================================================================================
chapter('Appendix — How this edition was checked', None)
a.p('Every step of this manual was simulated against the release package before printing: unzipped fresh into a folder without spaces and '
    'followed exactly as written. What a computer can prove was run; what needs your hands is marked as yours.')
a.table(['Check', 'Result'], [
    ['Desktop checks from the package', 'make -C host test: all 5 traces bit-exact; make -C firmware/host_test run: PASS, DART report as shown in Step 3'],
    ['Partition table (ESP-IDF 5.5.5 gen_esp32part.py)', 'Valid; fills the 16 MB flash exactly; art 8.3 MB fits 9 MB, music 1.8 MB fits 2.9 MB'],
    ['idf.py set-target esp32s3 (ESP-IDF 5.5.5 CMake, Kconfig, component manager)', 'Configures; flash plan: bootloader 0x0, table 0x8000, struthio.bin 0x10000, art 0x410000, music 0xD10000'],
    ['STRUTHIO_ART=greybox / full', 'greybox writes the 8-byte marker to 0x410000; full writes struthio.pak; adding or removing a file in build/assets re-runs the configure step'],
    ['Firmware sources', 'Compile against the real ESP-IDF 5.5.5 headers and drivers with -Wall -Wextra -Werror (the Xtensa link happens on your computer)'],
    ['Build menu', 'Every option run through Windows cmd (Wine) with a stand-in idf.py; struthio.sh run on Linux'],
    ['Setup doctor', 'Run from the package: 168 files match SHA256SUMS.txt'],
    ['CAD from the package', 'export_handheld.sh: HANDHELD CAD CHECK all pass (55 checks); CP1 DRC: all pass'],
    ['C game vs browser', '5 traces, 75,144 ticks, SHA-256 equal every tick; scene builder equal every tick'],
    ['Pictures and sound vs browser', 'Panel renderer 24.9–30.3 dB; HUD 43.2 dB; sound: 8,031 notes, 76–77 dB, max difference 2 LSB'],
    ['Sticker print file', 'PDF page exactly 87.0 x 43.9 mm; PNG carries 600 dpi'],
], widths=[3, 4.8], size=8.5)
a.h2('Still to confirm on the parts in your hand')
a.bullets(['The board\'s USB-C position (the CAD assumes bottom centre, right-angle plug).', 'Header pins for GPIO21 and GPIO38 (and 17, 18, GND).',
           'The board\'s speaker and battery connector positions and battery polarity.',
           'E-Switch 500SSP1S1M7QEA pin positions and actuator width (2.0 mm assumed).',
           'PUI AS02808MR-R frame: modelled round; re-check the 29.2 mm pocket for a square frame.',
           'CM1 feel: travel and snap come from the moulder\'s web; the CAD fixes only the geometry.'])
a.h2('References')
a.bullets(['Waveshare ESP32-S3-Touch-LCD-3.5B documentation, schematics and examples',
           'ESP-IDF v5.5.5 Get Started — https://docs.espressif.com/projects/esp-idf/en/v5.5.5/esp32s3/get-started/index.html',
           'PUI Audio AS02808MR-R — https://puiaudio.com/product/speakers-and-receivers/as02808mr-r',
           'THOR-503450 — https://thorbattery.com/product/thor-503450/',
           'E-Switch 500 Series — https://www.e-switch.com/product/500-series-miniature-slide-switch/',
           'Silicone keypad design guidance — https://www.epectec.com/keypads/design/'])
a.h2('A last word')
a.p('The most important discipline in this project is not speed. It is separation of variables. Each time you prove one layer before adding '
    'the next, the handheld becomes easier, safer and more achievable. Prove one thing, record the pass, then add the next.')

# ======================================================================================================
# CONTENTS TABLE (page numbers from a previous render, if given)
# ======================================================================================================
toc_rows = [[t, str(PAGES.get(t, '')).strip()] for lvl, t in TOC if lvl == 1]
tb = K.At(TOC_ANCHOR._p)
t = tb.table(['Section', 'Page'], toc_rows, widths=[6.4, 0.8], size=10)
# drop the template's own pictures: nothing in this edition refers to them
used = set(x.get(qn('r:embed')) for x in body.iter(qn('a:blip')))
part = doc.part
for rid, rel in list(part.rels.items()):
    if rel.reltype.endswith('/image') and rid not in used: del part.rels[rid]
doc.save(OUT)
json.dump([t for lvl, t in TOC if lvl == 1], open(OUT + '.toc.json', 'w'))
print('wrote', OUT, len(TOC), 'sections')
