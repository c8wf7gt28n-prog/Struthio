#!/usr/bin/env python3
# STRUTHIO HANDHELD · wiring schematics for the manual. Every pin, address and
# value comes from firmware/main/board_pins.h / board_waveshare_35b.c (which
# follow Waveshare's ESP-IDF example, commit 840daf2), the A0 wiring lock
# (docs/A0_PINOUT_AND_WIRING.md) or the A1 CAD (cad/a1/STRUTHIO084.scad).
# Anything not known from those sources is drawn dashed and marked "confirm".
# Writes svg/*.svg; render_schematics.mjs turns them into png/*.png.
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'svg')
os.makedirs(OUT, exist_ok=True)

INK, GREY, PAPER = '#17191C', '#60656C', '#FFFFFF'
NET = {'pwr': '#C8321E', 'gnd': '#17191C', 'sig': '#1F5FBF', 'i2c': '#7A3FB0', 'qspi': '#0F8A8A',
       'i2s': '#B86E00', 'bl': '#C49000', 'usb': '#3B7D23', 'unused': '#A7ABB2'}
FONT = 'Aptos, Helvetica, Arial, sans-serif'


class Sheet:
    def __init__(self, w, h, title, subtitle, trim=0):
        # content is drawn in sheet coordinates and moved up by `trim` px on save
        self.w, self.h, self.trim, self.e = w, h - trim, trim, []
        self.title, self.subtitle = title, subtitle

    def text(self, x, y, s, size=13, fill=INK, weight=400, anchor='middle', italic=False, mono=False):
        fam = 'Consolas, Menlo, monospace' if mono else FONT
        st = ' font-style="italic"' if italic else ''
        self.e.append(f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}"{st}>{s}</text>')

    def box(self, x, y, w, h, title, sub=None, fill='#F4F4F1', stroke=INK, dash=False, title_size=15):
        d = ' stroke-dasharray="6 4"' if dash else ''
        self.e.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.6"{d}/>')
        self.text(x + w / 2, y + 22, title, title_size, INK, 800)
        if sub:
            for k, line in enumerate(sub if isinstance(sub, list) else [sub]):
                self.text(x + w / 2, y + 40 + 15 * k, line, 11.5, GREY)

    def wire(self, pts, net='sig', width=2.2, dash=False):
        d = ' stroke-dasharray="7 5"' if dash else ''
        p = ' '.join(f'{x},{y}' for x, y in pts)
        self.e.append(f'<polyline points="{p}" fill="none" stroke="{NET[net]}" stroke-width="{width}" stroke-linejoin="round"{d}/>')

    def dot(self, x, y, net='sig'):
        self.e.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{NET[net]}"/>')

    def pin(self, x, y, label, side='right', net='sig', num=None):
        """A labelled pin stub on an IC edge; the wire attaches at the stub's far end."""
        L = 18
        x2 = x + L if side == 'right' else x - L
        self.e.append(f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y}" stroke="{NET[net]}" stroke-width="2.2"/>')
        if side == 'right':
            self.text(x - 6, y + 4, label, 11.5, INK, 600, 'end', mono=True)
            if num: self.text(x + 24, y - 6, num, 10.5, GREY, 400, 'start')
        else:
            self.text(x + 6, y + 4, label, 11.5, INK, 600, 'start', mono=True)
            if num: self.text(x - 9, y - 5, num, 10, GREY, 400)
        return (x2, y)

    def label(self, x, y, s, net='sig', anchor='start', size=11.5):
        self.text(x, y, s, size, NET[net], 700, anchor, mono=True)

    def gnd(self, x, y):
        self.e.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 10}" stroke="{INK}" stroke-width="2"/>')
        for k, w in enumerate((16, 10, 4)):
            yy = y + 10 + 4 * k
            self.e.append(f'<line x1="{x - w / 2}" y1="{yy}" x2="{x + w / 2}" y2="{yy}" stroke="{INK}" stroke-width="2"/>')

    def resistor(self, x, y, vertical=True, label=None, net='pwr'):
        """Zig-zag resistor, 40 px long, starting at (x, y)."""
        if vertical:
            pts = [(x, y), (x, y + 6)] + [(x + (6 if k % 2 else -6), y + 9 + 4 * k) for k in range(6)] + [(x, y + 34), (x, y + 40)]
        else:
            pts = [(x, y), (x + 6, y)] + [(x + 9 + 4 * k, y + (6 if k % 2 else -6)) for k in range(6)] + [(x + 34, y), (x + 40, y)]
        self.wire(pts, net, 2)
        if label: self.text(x + (14 if vertical else 20), y + (24 if vertical else -12), label, 11, GREY, 400, 'start' if vertical else 'middle')

    def switch(self, x, y, label=None, net='sig'):
        """Normally-open push switch, horizontal, 60 px from (x, y)."""
        e = self.e
        e.append(f'<line x1="{x}" y1="{y}" x2="{x + 18}" y2="{y}" stroke="{NET[net]}" stroke-width="2.2"/>')
        e.append(f'<line x1="{x + 42}" y1="{y}" x2="{x + 60}" y2="{y}" stroke="{NET[net]}" stroke-width="2.2"/>')
        e.append(f'<circle cx="{x + 18}" cy="{y}" r="3" fill="{PAPER}" stroke="{INK}" stroke-width="1.8"/>')
        e.append(f'<circle cx="{x + 42}" cy="{y}" r="3" fill="{PAPER}" stroke="{INK}" stroke-width="1.8"/>')
        e.append(f'<line x1="{x + 14}" y1="{y - 12}" x2="{x + 46}" y2="{y - 12}" stroke="{INK}" stroke-width="2.2"/>')
        e.append(f'<line x1="{x + 30}" y1="{y - 12}" x2="{x + 30}" y2="{y - 22}" stroke="{INK}" stroke-width="2.2"/>')
        e.append(f'<line x1="{x + 24}" y1="{y - 22}" x2="{x + 36}" y2="{y - 22}" stroke="{INK}" stroke-width="2.2"/>')
        if label: self.text(x + 30, y + 22, label, 11.5, INK, 700)

    def slide_switch(self, x, y, label=None, net='pwr'):
        """SPST latching switch (lever), 60 px."""
        e = self.e
        e.append(f'<line x1="{x}" y1="{y}" x2="{x + 18}" y2="{y}" stroke="{NET[net]}" stroke-width="2.4"/>')
        e.append(f'<line x1="{x + 44}" y1="{y}" x2="{x + 60}" y2="{y}" stroke="{NET[net]}" stroke-width="2.4"/>')
        e.append(f'<circle cx="{x + 18}" cy="{y}" r="3" fill="{INK}"/>')
        e.append(f'<circle cx="{x + 44}" cy="{y}" r="3" fill="{PAPER}" stroke="{INK}" stroke-width="1.8"/>')
        e.append(f'<line x1="{x + 18}" y1="{y}" x2="{x + 42}" y2="{y - 14}" stroke="{INK}" stroke-width="2.4"/>')
        if label: self.text(x + 30, y + 22, label, 11.5, INK, 700)

    def battery(self, x, y, label=None):
        """Single cell, vertical: + on top at (x, y), - at bottom (y + 50)."""
        e = self.e
        e.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 18}" stroke="{NET["pwr"]}" stroke-width="2.4"/>')
        e.append(f'<line x1="{x - 16}" y1="{y + 18}" x2="{x + 16}" y2="{y + 18}" stroke="{INK}" stroke-width="2.6"/>')
        e.append(f'<line x1="{x - 8}" y1="{y + 26}" x2="{x + 8}" y2="{y + 26}" stroke="{INK}" stroke-width="5"/>')
        e.append(f'<line x1="{x}" y1="{y + 26}" x2="{x}" y2="{y + 50}" stroke="{INK}" stroke-width="2.4"/>')
        self.text(x + 22, y + 16, '+', 14, NET['pwr'], 800, 'start')
        if label:
            for k, line in enumerate(label if isinstance(label, list) else [label]):
                self.text(x + 26, y + 30 + 14 * k, line, 11.5, INK, 600 if k == 0 else 400, 'start')

    def speaker(self, x, y, label=None):
        e = self.e
        e.append(f'<rect x="{x}" y="{y - 12}" width="12" height="24" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>')
        e.append(f'<polygon points="{x + 12},{y - 12} {x + 30},{y - 26} {x + 30},{y + 26} {x + 12},{y + 12}" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>')
        if label: self.text(x + 40, y + 4, label, 11.5, INK, 700, 'start')

    def note(self, x, y, lines, size=11.5, color=GREY):
        for k, line in enumerate(lines):
            self.text(x, y + 16 * k, line, size, color, 400, 'start')

    def legend(self, x, y, nets):
        names = {'pwr': 'power', 'gnd': 'ground', 'sig': 'GPIO signal', 'i2c': 'I2C', 'qspi': 'QSPI',
                 'i2s': 'I2S audio', 'bl': 'backlight PWM', 'usb': 'USB', 'unused': 'unused / do not fit'}
        for k, n in enumerate(nets):
            yy = y + 18 * k
            self.e.append(f'<line x1="{x}" y1="{yy}" x2="{x + 28}" y2="{yy}" stroke="{NET[n]}" stroke-width="3"/>')
            self.text(x + 36, yy + 4, names[n], 11.5, INK, 400, 'start')
        dy = y + 18 * len(nets)
        self.e.append(f'<line x1="{x}" y1="{dy}" x2="{x + 28}" y2="{dy}" stroke="{GREY}" stroke-width="2" stroke-dasharray="7 5"/>')
        self.text(x + 36, dy + 4, 'proposal / confirm on the board', 11.5, INK, 400, 'start')

    def save(self, name):
        w, h, body = self.w, self.h, self.e
        self.e = []
        self.e.append(f'<rect width="{w}" height="{h}" fill="{PAPER}"/>')
        self.e.append(f'<rect x="8" y="8" width="{w - 16}" height="{h - 16}" fill="none" stroke="{INK}" stroke-width="1.5"/>')
        self.text(24, 40, self.title, 22, INK, 800, 'start')
        self.text(24, 62, self.subtitle, 13, GREY, 400, 'start')
        self.e.append(f'<rect x="{w - 330}" y="{h - 58}" width="322" height="50" fill="none" stroke="{INK}" stroke-width="1"/>')
        self.text(w - 320, h - 38, 'STRUTHIO HANDHELD  ·  A0 / A1 wiring', 12, INK, 700, 'start')
        self.text(w - 320, h - 20, 'Waveshare ESP32-S3-Touch-LCD-3.5B  ·  manual v0.10', 11, GREY, 400, 'start')
        self.e.append(f'<g transform="translate(0,{-self.trim})">' + ''.join(body) + '</g>')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
               + ''.join(self.e) + '</svg>')
        open(os.path.join(OUT, name + '.svg'), 'w').write(svg)
        print('svg/' + name + '.svg')


# ---- S1: system overview -------------------------------------------------------------------------
def s1():
    s = Sheet(1600, 1000, 'S1  System overview: what the ESP32-S3 talks to',
              'Every bus on the Waveshare 3.5B as STRUTHIO uses it. Pins and addresses: firmware/main/board_pins.h (from the vendor example).', trim=170)
    cx, cy, cw, ch = 610, 260, 360, 470
    s.box(cx, cy, cw, ch, 'ESP32-S3R8', ['240 MHz dual core', '8 MB octal PSRAM · 16 MB flash'], fill='#EAF4F4')
    # left side: wings, USB, unused camera / SD
    L = cx
    def lp(y, lab, net, num=None): return s.pin(L, y, lab, 'left', net, num)
    a = lp(360, 'GPIO17', 'sig'); b = lp(395, 'GPIO18', 'sig')
    s.box(250, 320, 220, 110, 'WING BUTTONS', ['LEFT WING  GPIO17', 'RIGHT WING GPIO18', 'switch to GND, pull-up'], fill='#FFF6E0')
    s.wire([a, (470, 360)], 'sig'); s.wire([b, (470, 395)], 'sig')
    u = lp(470, 'GPIO19/20', 'usb')
    s.box(250, 450, 220, 60, 'USB-C', ['flash · log · 5 V in'], fill='#EEF6EA')
    s.wire([u, (470, 470)], 'usb')
    c = lp(560, 'cam pins', 'unused')
    s.box(250, 530, 220, 80, 'CAMERA FPC', ['NOT FITTED: shares', 'GPIO17/18 (VSYNC/HREF)'], fill='#F7F7F7', stroke=NET['unused'], dash=True)
    s.wire([c, (470, 560)], 'unused', dash=True)
    d = lp(650, 'GPIO9-11', 'unused')
    s.box(250, 630, 220, 60, 'microSD', ['empty: 9-11 spare'], fill='#F7F7F7', stroke=NET['unused'], dash=True)
    s.wire([d, (470, 650)], 'unused', dash=True)
    # right side: QSPI LCD, backlight, I2C devices, I2S audio
    R = cx + cw
    def rp(y, lab, net, num=None): return s.pin(R, y, lab, 'right', net, num)
    q = rp(330, 'QSPI 1-5,12', 'qspi')
    s.box(1080, 290, 240, 80, 'AXS15231B LCD', ['320 x 480 · SPI2 quad · 40 MHz'], fill='#E6F4F4')
    s.wire([q, (1080, 330)], 'qspi', 3.5)
    bl = rp(400, 'GPIO6', 'bl')
    s.box(1080, 380, 240, 50, 'BACKLIGHT', ['LEDC PWM 5 kHz'], fill='#FFF7DA')
    s.wire([bl, (1080, 400)], 'bl')
    i2 = rp(520, 'I2C 8/7', 'i2c')
    s.wire([i2, (1040, 520), (1040, 455), (1040, 700)], 'i2c', 3)
    devs = [('AXP2101 PMIC', '0x34'), ('TCA9554 expander', '0x20 · EXIO1 = LCD reset'), ('ES8311 codec', 'control'),
            ('touch (unused)', '0x3B'), ('QMI8658 IMU (unused)', '0x6B'), ('PCF85063 RTC (unused)', '0x51')]
    for k, (n, a_) in enumerate(devs):
        y = 455 + 49 * k
        s.wire([(1040, y), (1080, y)], 'i2c', 2.2)
        s.dot(1040, y, 'i2c')
        unused = 'unused' in n
        s.box(1080, y - 20, 240, 40, n, None, fill='#F7F7F7' if unused else '#F3ECFA', stroke=NET['unused'] if unused else INK, dash=unused, title_size=13)
        s.text(1335, y + 4, a_, 11.5, GREY, 400, 'start', mono=True)
    i2s = rp(640, 'I2S', 'i2s')
    s.wire([i2s, (1000, 640), (1000, 760), (1080, 760)], 'i2s', 3)
    s.box(1080, 735, 240, 50, 'ES8311 → NS4150B', ['MCLK 44 BCLK 13 LRCK 15 DIN 14'], fill='#FFF1DE')
    s.wire([(1320, 760), (1380, 760)], 'i2s', 2.4)
    s.speaker(1385, 760, '8 Ω ~1 W')
    # power along the bottom
    s.box(610, 800, 360, 80, 'AXP2101 rails → board', ['USB-C 5 V or LiPo in · 3.3 V system', 'charger 200 mA / 4.1 V (vendor values)'], fill='#FBEFEA')
    s.wire([(790, 730), (790, 800)], 'pwr', 3)
    s.battery(400, 800, ['LiPo 1 cell', 'protected', '36 x 52 x 6.2 mm'])
    s.wire([(400, 800), (400, 780), (560, 780), (560, 840), (610, 840)], 'pwr', 3)
    s.wire([(400, 850), (400, 870)], 'gnd', 2.4); s.gnd(400, 870)
    s.legend(60, 760, ['pwr', 'gnd', 'sig', 'i2c', 'qspi', 'i2s', 'bl', 'usb', 'unused'])
    s.save('s1_system')


# ---- S2: the wing buttons ------------------------------------------------------------------------
def s2():
    s = Sheet(1600, 900, 'S2  Wing buttons: GPIO17 / GPIO18, active low',
              'The only wiring STRUTHIO adds to the board. Internal pull-ups; no external parts needed. 1 kHz sampling, 8 ms debounce in firmware.', trim=110)
    s.box(120, 205, 380, 415, 'ESP32-S3', None, fill='#EAF4F4')
    s.text(310, 600, '(on the Waveshare 3.5B)', 11.5, GREY)
    for k, (gpio, name, hp, y) in enumerate([('GPIO17', 'LEFT WING', 'header pin 16', 300), ('GPIO18', 'RIGHT WING', 'header pin 18', 470)]):
        # internal pull-up
        s.text(290, y - 22, 'internal pull-up', 11, GREY, 400, 'end')
        s.wire([(300, y - 50), (300, y - 44)], 'pwr', 2)
        s.label(300, y - 56, '3V3', 'pwr', 'middle', 11)
        s.resistor(300, y - 44, True, '~45 kΩ', 'pwr')
        s.wire([(300, y - 4), (300, y), (500, y)], 'sig')
        s.dot(300, y)
        a = s.pin(500, y, '', 'right', 'sig', hp)
        s.text(492, y - 8, gpio, 12, INK, 700, 'end', mono=True)
        # harness to the switch daughterboard
        s.wire([a, (760, y)], 'sig', 2.6)
        s.text(680, y + 18, ['white wire (proposal)', 'blue wire (proposal)'][k], 11, GREY, 400)
        s.box(760, y - 70, 330, 140, f'{name} switch board', ['~18 x 18 mm perfboard', 'Omron B3F-4050 (or rubber dome)'], fill='#FFF6E0')
        s.switch(860, y + 30, 'SW ' + ('L' if k == 0 else 'R'))
        s.wire([(780, y), (780, y + 30), (860, y + 30)], 'sig')
        s.wire([(920, y + 30), (1060, y + 30), (1060, y + 90), (1180, y + 90)], 'gnd', 2.4)
    s.wire([(1180, 390), (1180, 560)], 'gnd', 2.6)
    s.dot(1180, 390, 'gnd'); s.dot(1180, 560, 'gnd')
    s.wire([(1180, 560), (1180, 700), (500, 700), (500, 620)], 'gnd', 2.6)
    s.text(840, 690, 'black wire: GND, header pin 30 (any GND pin)', 11.5, INK, 600)
    s.gnd(1180, 700)
    s.note(1220, 230, ['Pressed  → GPIO reads 0 (LOW)', 'Released → GPIO reads 1 (pull-up)', '',
                       'Firmware: gpio_config INPUT,', 'pull_up_en, active level 0;', '1 kHz sample, 8 ms stable,',
                       'raw-edge time kept for the', '100 ms straight-up chord.', '',
                       'DART (trial C) needs no wire:', 'both wings held 200 ms.'], 12.5, INK)
    s.note(130, 650, ['Both lines are the camera FPC\'s VSYNC (17) / HREF (18):',
                      'keep the camera connector EMPTY.'], 12.5, NET['pwr'])
    s.note(130, 760, ['Optional per line, only if bench tests show noise: 100 nF from GPIO to GND',
                      'and/or an external 10 kΩ pull-up to 3V3. Not fitted by default.'], 12, GREY)
    s.legend(1220, 470, ['pwr', 'gnd', 'sig'])
    s.save('s2_wings')


# ---- S3: power -----------------------------------------------------------------------------------
def s3():
    s = Sheet(1600, 1000, 'S3  Power: USB-C, LiPo and the slide POWER switch',
              'The board\'s AXP2101 does charging and rails. STRUTHIO adds a panel USB-C extension, one protected LiPo and a slide switch (two wiring options).', trim=90)
    # USB path
    s.box(60, 170, 220, 90, 'USB-C panel jack', ['bottom of the shell', 'short full-data extension'], fill='#EEF6EA')
    s.wire([(280, 215), (430, 215)], 'usb', 4)
    s.text(355, 205, 'VBUS · D+/D- · GND', 11, GREY)
    s.box(430, 170, 220, 90, 'board USB-C', ['GPIO19/20 native USB', 'VBUS 5 V in'], fill='#EEF6EA')
    s.wire([(650, 215), (760, 215), (760, 300)], 'pwr', 3)
    # PMIC
    s.box(640, 300, 380, 300, 'AXP2101 PMIC', ['I2C 0x34 · board_pmu.cpp', 'VBUS limit 4.36 V / 1.5 A', 'charger 200 mA, 4.1 V target',
                                               'power key: 128 ms on, 4 s off', 'rails as the vendor example:', 'DC1-5, ALDO1-4, BLDO1-2,',
                                               'DLDO1-2, CPUSLDO all on'], fill='#FBEFEA')
    s.wire([(1020, 360), (1150, 360)], 'pwr', 3.5)
    s.box(1150, 320, 280, 80, '3.3 V system + rails', ['ESP32-S3, LCD, codec, ...', '(consumer per rail: schematic)'], fill='#FBEFEA')
    s.pin(1020, 470, 'PWRON', 'right', 'sig')
    s.wire([(1038, 470), (1150, 470)], 'sig')
    s.box(1150, 440, 280, 60, 'board PWR key', ['momentary · service slot'], fill='#F4F4F1')
    # battery + option A
    s.text(120, 330, 'OPTION A  ·  switch in the battery lead (simplest, true off)', 14, INK, 800, 'start')
    s.battery(170, 380, ['LiPo, 1 cell, protected', 'protection PCB on the cell', 'polarity: check before plugging'])
    s.wire([(170, 380), (170, 360), (300, 360)], 'pwr', 3)
    s.slide_switch(300, 360, 'SLIDE POWER', 'pwr')
    s.wire([(360, 360), (560, 360), (560, 420), (640, 420)], 'pwr', 3)
    s.label(570, 412, 'BAT+', 'pwr')
    s.wire([(170, 430), (170, 470), (560, 470), (560, 450), (640, 450)], 'gnd', 3)
    s.label(570, 444, 'BAT-', 'gnd')
    s.note(120, 500, ['Switch in BAT+ only, never BAT-. Rated for the peak current (≥ 2 A).',
                      'OFF: battery disconnected, zero drain. With USB in, the board still',
                      'runs from VBUS, but charging needs the switch ON.'], 11.5, INK)
    # option B
    s.text(120, 620, 'OPTION B  ·  switch as a signal (keeps charging when OFF)', 14, INK, 800, 'start')
    s.box(120, 650, 220, 150, 'ESP32-S3', ['spare GPIO, e.g. 21', '(no camera fitted)'], fill='#EAF4F4')
    a = s.pin(340, 700, 'GPIO21', 'right', 'sig')
    s.wire([a, (430, 700)], 'sig', 2.4, dash=True)
    s.slide_switch(430, 700, 'SLIDE POWER', 'sig')
    s.wire([(490, 700), (560, 700), (560, 740)], 'gnd', 2.4, dash=True); s.gnd(560, 740)
    s.note(620, 680, ['Pull-up on; switch closes to GND = ON. When it opens, firmware asks the AXP2101 to',
                      'power down (board_power_off). The PWR key or USB-in wakes it. Battery stays',
                      'connected and charges in either position. Needs firmware (not written yet).'], 11.5, INK)
    s.note(620, 760, ['Battery lead and BAT connector: the board\'s own LiPo connector (type, pitch and polarity',
                      'from the vendor drawing; confirm before crimping).'], 11.5, GREY)
    s.legend(1240, 600, ['pwr', 'gnd', 'sig', 'usb'])
    s.note(1240, 720, ['Never connect AA / NiMH packs', 'to the LiPo connector: the', 'charger would try to charge them.'], 11.5, NET['pwr'])
    s.save('s3_power')


# ---- S4: display and audio -----------------------------------------------------------------------
def s4():
    s = Sheet(1600, 940, 'S4  Display and audio: on-board wiring the firmware drives',
              'Not wired by hand: these traces are on the Waveshare board. Shown so bring-up can probe them. Values from board_waveshare_35b.c / the vendor BSP.', trim=60)
    s.box(120, 160, 330, 640, 'ESP32-S3', ['SPI2 · LEDC · I2C0 · I2S0'], fill='#EAF4F4')
    qs = [('GPIO12', 'CS'), ('GPIO5', 'SCLK'), ('GPIO1', 'D0'), ('GPIO2', 'D1'), ('GPIO3', 'D2'), ('GPIO4', 'D3')]
    s.box(780, 160, 330, 290, 'AXS15231B display', ['320 x 480 IPS · QSPI, mode 3, 40 MHz', 'RGB565 big-endian · no row address:', 'frames go top to bottom (RAMWR / RAMWRC)'], fill='#E6F4F4')
    for k, (g, n) in enumerate(qs):
        y = 260 + 28 * k
        a = s.pin(450, y, g, 'right', 'qspi')
        s.wire([a, (762, y)], 'qspi')
        s.pin(780, y, n, 'left', 'qspi')
    a = s.pin(450, 485, 'GPIO6', 'right', 'bl')
    s.wire([a, (780, 485)], 'bl')
    s.box(780, 460, 330, 50, 'backlight driver', ['LEDC 5 kHz, 10 bit; board_backlight()'], fill='#FFF7DA')
    # I2C → expander → LCD reset
    a = s.pin(450, 560, 'GPIO8 SDA', 'right', 'i2c'); b = s.pin(450, 590, 'GPIO7 SCL', 'right', 'i2c')
    s.wire([a, (600, 560)], 'i2c'); s.wire([b, (600, 590)], 'i2c')
    s.box(600, 540, 160, 70, 'TCA9554', ['I2C 0x20'], fill='#F3ECFA')
    s.wire([(760, 575), (1180, 575), (1180, 420), (1110, 420)], 'sig', 2.4)
    s.text(960, 565, 'EXIO1 → LCD RESET: low 100 ms, high 200 ms', 11.5, INK, 600)
    # audio
    i2s = [('GPIO44', 'MCLK'), ('GPIO13', 'BCLK'), ('GPIO15', 'LRCK'), ('GPIO14', 'DIN (play)'), ('GPIO16', 'DOUT (mic)')]
    s.box(780, 640, 260, 190, 'ES8311 codec', ['I2C control (esp_codec_dev)', 'driver: not wired yet'], fill='#FFF1DE')
    for k, (g, n) in enumerate(i2s):
        y = 680 + 28 * k
        a = s.pin(450, y, g, 'right', 'i2s')
        s.wire([a, (762, y)], 'i2s')
        s.pin(780, y, n, 'left', 'i2s')
    s.wire([(1040, 735), (1110, 735)], 'i2s', 2.4)
    s.box(1110, 705, 170, 60, 'NS4150B', ['mono class-D amp'], fill='#FFF1DE')
    s.wire([(1280, 735), (1330, 735)], 'i2s', 2.4)
    s.speaker(1335, 735, None)
    s.note(1300, 790, ['speaker header', '8 Ω, ~1 W, ~28 mm', 'low gain first'], 11.5, INK)
    s.legend(1240, 180, ['qspi', 'bl', 'i2c', 'i2s', 'sig'])
    s.save('s4_display_audio')


# ---- S5: harness inside the shell ---------------------------------------------------------------
def s5():
    # A1 shell (A0.8.4 footprint 88 x 128) seen from the back, rear shell removed, to scale
    S, ox, oy = 5.2, 560, 470            # px per mm; model origin on the sheet
    s = Sheet(1600, 1080, 'S5  Harness inside the A1 shell (rear view, rear shell removed, to scale)',
              'Positions from cad/a1/STRUTHIO084.scad. Seen from the back, so the LEFT WING is on the right. Dashed: route or position still to confirm.', trim=60)
    X = lambda x: ox - x * S             # rear view mirrors x
    Y = lambda y: oy - y * S
    L, R = X(44), X(-44)                 # shell edges on the sheet (left / right)
    s.e.append(f'<rect x="{L}" y="{Y(64)}" width="{88 * S}" height="{128 * S}" rx="{9 * S}" fill="#F7F8FA" stroke="{INK}" stroke-width="2"/>')
    # board 61 x 92.44 centred at y 13.78; battery cavity behind it
    s.e.append(f'<rect x="{X(30.5)}" y="{Y(60)}" width="{61 * S}" height="{92.44 * S}" fill="#E3EFE6" stroke="{NET["usb"]}" stroke-width="2"/>')
    s.text(X(0), Y(55), 'Waveshare 3.5B, board back (61 x 92.44 mm)', 13, INK, 700)
    s.e.append(f'<rect x="{X(18)}" y="{Y(39.5)}" width="{36 * S}" height="{52 * S}" fill="#FBEFEA" stroke="{NET["pwr"]}" stroke-width="2" stroke-dasharray="7 5"/>')
    s.text(X(0), Y(14), 'LiPo cavity', 13, NET['pwr'], 700)
    s.text(X(0), Y(10.5), '36 x 52 x 6.2 mm', 11.5, NET['pwr'])
    # expansion header (position not in our sources): drawn on the board's lower right, dashed
    hx, hy0, hy1 = X(-24), Y(-4), Y(-28)
    s.e.append(f'<rect x="{hx - 12}" y="{hy0}" width="24" height="{hy1 - hy0}" fill="#FFF6E0" stroke="{GREY}" stroke-width="1.8" stroke-dasharray="6 4"/>')
    for k in range(8):
        for c in (-5, 5):
            s.e.append(f'<circle cx="{hx + c}" cy="{hy0 + 10 + k * (hy1 - hy0 - 20) / 7}" r="2" fill="{GREY}"/>')
    # switch boards (18 x 18 at x ±21.5, y -47.5) and the speaker (28 mm at y -43.5)
    for side, name in ((-1, 'LEFT WING'), (1, 'RIGHT WING')):
        cx, cy = X(side * 21.5), Y(-47.5)
        s.e.append(f'<rect x="{cx - 9 * S}" y="{cy - 9 * S}" width="{18 * S}" height="{18 * S}" fill="#FFF6E0" stroke="{INK}" stroke-width="1.8"/>')
        s.text(cx, cy + 22, name, 12, INK, 800)
        s.text(cx, cy + 37, 'switch board', 10.5, GREY)
    sx, sy = X(0), Y(-43.5)
    s.e.append(f'<circle cx="{sx}" cy="{sy}" r="{14 * S}" fill="#FFF1DE" stroke="{NET["i2s"]}" stroke-width="2"/>')
    s.text(sx, sy + 30, 'speaker', 12, INK, 700)
    s.text(sx, sy + 45, '28 mm', 11, GREY)
    # wing harness: three wires leave the header bottom and run left along y -34 / -35.5 / -37
    top = Y(-47.5) - 9 * S                # switch boards' top edge
    pads = {'L': X(-21.5), 'R': X(21.5)}
    runs = [(-34.0, 'sig', [(pads['L'] + 14, 'L')]), (-35.6, 'sig', [(pads['R'] + 14, 'R')]), (-37.2, 'gnd', [(pads['L'] - 14, 'L'), (pads['R'] - 14, 'R')])]
    for k, (yy, net, ends) in enumerate(runs):
        xs = hx - 6 + 6 * k
        far = min(x for x, _ in ends)
        s.wire([(xs, hy1), (xs, Y(yy)), (far, Y(yy))], net, 3)
        for x, _ in ends:
            s.wire([(x, Y(yy)), (x, top)], net, 3)
            s.dot(x, Y(yy) if x != far else Y(yy), net)
    # labels outside the shell, right side, with leaders
    def tag(y_px, text, net, x_from):
        s.wire([(x_from, y_px), (R + 30, y_px)], 'unused', 1)
        s.text(R + 36, y_px + 4, text, 12, NET[net], 700, 'start')
    tag(hy0 + 40, '2x16 expansion header (position: confirm)', 'sig', hx + 12)
    tag(Y(-34.0), 'white: GPIO17 (pin 16) → LEFT WING', 'sig', hx + 14)
    tag(Y(-35.6) + 16, 'blue: GPIO18 (pin 18) → RIGHT WING', 'sig', hx + 14)
    tag(Y(-37.2) + 32, 'black: GND (pin 30) → both boards', 'gnd', hx + 14)
    # battery lead and option-A slide switch on the right side wall (service-slot side)
    swx, swy0, swy1 = X(-40), Y(22), Y(6)
    s.wire([(X(-18), Y(30)), (swx, Y(30)), (swx, swy0)], 'pwr', 3, dash=True)
    s.e.append(f'<rect x="{swx - 8}" y="{swy0}" width="16" height="{swy1 - swy0}" fill="#FBEFEA" stroke="{NET["pwr"]}" stroke-width="2"/>')
    s.wire([(swx, swy1), (swx, Y(0)), (X(-26), Y(0))], 'pwr', 3, dash=True)
    tag(Y(30), 'LiPo + lead (option A, figure S3)', 'pwr', swx)
    tag((swy0 + swy1) / 2, 'slide POWER switch, side aperture', 'pwr', swx + 8)
    tag(Y(0), 'to the board BAT connector (position: confirm)', 'pwr', X(-26))
    # speaker leads: to the board's speaker header (position: confirm), labelled on the left
    s.wire([(sx - 8, sy - 14 * S), (sx - 8, Y(-20)), (X(14), Y(-20))], 'i2s', 2.4, dash=True)
    s.wire([(X(14), Y(-20)), (L - 30, Y(-20))], 'unused', 1)
    s.text(L - 36, Y(-20) + 4, 'speaker leads → SPK header (confirm)', 12, NET['i2s'], 700, 'end')
    # USB-C extension: bottom jack, up the left wall to the board's USB-C (internal edge, confirm)
    ux, uy = X(0), Y(-62.2)
    s.e.append(f'<rect x="{ux - 7 * S}" y="{uy - 3 * S}" width="{14 * S}" height="{3 * S}" fill="#EEF6EA" stroke="{NET["usb"]}" stroke-width="2"/>')
    s.wire([(ux - 7 * S, uy - 1.5 * S), (X(40), uy - 1.5 * S), (X(40), Y(8)), (X(30.5), Y(8))], 'usb', 3.5, dash=True)
    s.wire([(X(40), Y(8)), (L - 30, Y(8))], 'unused', 1)
    s.text(L - 36, Y(8) + 4, 'USB-C extension → board USB-C (edge: confirm)', 12, NET['usb'], 700, 'end')
    s.wire([(X(40), uy - 1.5 * S), (L - 30, uy - 1.5 * S)], 'unused', 1)
    s.text(L - 36, uy - 1.5 * S + 4, 'USB-C panel jack, bottom opening', 12, NET['usb'], 700, 'end')
    # notes and legend
    s.note(1150, 170, ['Harness: 3 wires, ~22 AWG stranded,', 'about 110 mm; colours are a proposal.',
                       'Header pins from the A0 wiring lock', '(published pinout image): confirm on', 'the board in hand before soldering.', '',
                       'Keep wires off the speaker cone and', 'the LiPo; leave slack so the shell', 'opens; strain-relieve at the switch', 'boards.'], 12.5, INK)
    s.legend(1150, 400, ['pwr', 'gnd', 'sig', 'i2s', 'usb'])
    s.save('s5_harness')


if __name__ == '__main__':
    s1(); s2(); s3(); s4(); s5()
