#!/usr/bin/env python3
"""STRUTHIO ONE SLIM · the one-page quick-start card (A4), for the bench next to the parts.

    /usr/bin/python3 tools/manual/quick_card.py OUT.pdf
"""
import os, sys, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
HH = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from one_manual import img, png, COMMIT, TODAY

ST = os.path.join(HH, 'docs', 'renders', 'slim', 'steps')
CAP = os.path.join(HERE, 'captures')
STEPS = [
    ('Order', None, 'Everything on <b>STRUTHIO_ORDER</b> (package 5): the screen board, cell, speaker, 5 screws, a header strip, foam tape. '
                    'Board from JLCPCB at <b>0.8 mm</b>; print the 7 parts in PETG.'),
    ('Flash', None, 'Plug the screen board in by USB-C. Double-click <b>FLASH_ME.bat</b> (package 1). Wait for <b>DONE</b>.'),
    ('Pins', 's05_pins', 'Board <b>face down</b> in the pin jig. A strip of 4 and a strip of 8 pins, long side first. Solder, slide the plastic off, snip flush.'),
    ('Speaker', None, 'Solder the Waveshare speaker lead to the new speaker\'s two pads, either way round.'),
    ('Front shell', 's04_waveshare', 'Wing buttons, rocker (axle cut in the jig\'s slot), power button, then the screen board face down.'),
    ('Board', 's06_one_slim', 'The ONE SLIM onto the screen board, pins into the long socket, flat on its posts.'),
    ('Back shell', 's07_back_shell', 'Speaker in its lip, cell taped in the corner, leads under the clips. Plug the speaker into <b>J9</b>, the cell into <b>J2</b>.'),
    ('Close', 's08_closed', 'Tongue into the groove. <b>5 × M2 × 6</b>, snug.'),
    ('Power', None, 'Press the button on the left side. The screen checks every button, the speaker and the battery. <b>Both wings</b>: play.'),
    ('Panel', 's10_panel', 'Peel the liner, drop the panel into its pocket inside the lip, press from the middle out.'),
]
CSS = """
@page { size: A4; margin: 10mm; }
body { font-family: 'DejaVu Sans', Arial, sans-serif; color: #16202b; margin: 0; font-size: 9.6pt; line-height: 1.35; }
h1 { font-size: 22pt; color: #0d2a4a; margin: 0; letter-spacing: .02em; }
.sub { color: #f29a1d; font-weight: bold; font-size: 10pt; margin: 2px 0 8px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.t { border: 1px solid #d7dee6; border-radius: 8px; padding: 6px 8px; display: flex; gap: 8px; align-items: center; min-height: 40mm; }
.t .n { flex: 0 0 26px; height: 26px; border-radius: 50%; background: #f29a1d; color: #fff; font-weight: bold; text-align: center; line-height: 26px; }
.t .p { flex: 0 0 30mm; text-align: center; } .t .p img { max-width: 30mm; max-height: 36mm; }
.t b.h { display: block; font-size: 11pt; color: #0d2a4a; margin-bottom: 2px; }
.foot { font-size: 8pt; color: #6b7783; margin-top: 6px; }
"""

def build(out_pdf):
    tiles = []
    for i, (title, pic, text) in enumerate(STEPS, 1):
        if pic: p = img(os.path.join(ST, pic + '.png'), crop_dark=True)
        elif title == 'Power': p = png(os.path.join(CAP, 'fw_selftest_example.png'))
        else: p = ''
        tiles.append(f'<div class="t"><div class="n">{i}</div><div class="p">{p}</div><div><b class="h">{title}</b>{text}</div></div>')
    doc = (f'<!doctype html><html><head><meta charset="utf-8"><title>STRUTHIO quick start</title><style>{CSS}</style></head><body>'
           f'<h1>STRUTHIO ONE SLIM</h1><div class="sub">Quick start · the whole build on one page · every step is in the manual with a picture and a check</div>'
           f'<div class="grid">{"".join(tiles)}</div>'
           f'<div class="foot">Off: hold the power button 4 s. Charge: USB-C, about 3 hours. Re-flash: FLASH_ME.bat again. '
           f'Full manual: STRUTHIO_ONE_SLIM_Build_Manual_Windows11.pdf · rev S3 · commit {COMMIT} · {TODAY}</div></body></html>')
    with tempfile.TemporaryDirectory() as t:
        hp = os.path.join(t, 'card.html'); open(hp, 'w', encoding='utf-8').write(doc)
        subprocess.check_call(['node', os.path.join(HH, 'tools', 'package', 'html2pdf.mjs'), hp, out_pdf])

if __name__ == '__main__':
    build(os.path.abspath(sys.argv[1]))
