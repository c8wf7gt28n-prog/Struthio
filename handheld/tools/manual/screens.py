#!/usr/bin/env python3
"""STRUTHIO HANDHELD · the manual's screenshots, from real captures.

    python3 tools/manual/screens.py OUT_DIR

Reads tools/manual/captures/ (see HOW.md there: every text file is the real
output of a command run on the release package; the qemu_* logs and fw_*
frames come from the firmware running in Espressif's ESP32-S3 emulator) and
writes s01..s15 PNGs. Lines are only ever left out (shown as a dim · · · line),
never edited; the commands shown are the commands that were run.
"""
import os, re, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from termshot import shot, SANS, SANS_B

CAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'captures')
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
read = lambda n: open(os.path.join(CAP, n), encoding='utf-8', errors='replace').read().replace('\r', '').split('\n')
GAP = '  · · ·'

def pick(lines, *pats, after=0):
    """the first line matching each pattern (plus `after` lines), in file order, with ⋮ for gaps"""
    idx = []
    for p in pats:
        for i, l in enumerate(lines):
            if re.search(p, l) and i not in idx:
                idx.extend(range(i, min(len(lines), i + 1 + after))); break
        else:
            raise SystemExit('capture line not found: ' + p)
    idx = sorted(set(idx)); out = []
    for k, i in enumerate(idx):
        if k and i != idx[k - 1] + 1: out.append(GAP)
        out.append(lines[i])
    return out

def block(lines, start, end, drop=()):
    """the lines from the first match of `start` to the next match of `end`, without blank lines or `drop` matches"""
    i = next(k for k, l in enumerate(lines) if re.search(start, l))
    j = next(k for k in range(i, len(lines)) if re.search(end, lines[k]))
    return [l for l in lines[i:j + 1] if l.strip() and not any(re.search(d, l) for d in drop)]

def marks(lines, **want):
    """{index: number} for the first line containing each text; keys are m1, m2... or m1_green"""
    m = {}
    for key, text in want.items():
        num = int(re.match(r'm(\d+)', key).group(1)); col = key.split('_')[1] if '_' in key else 'gold'
        for i, l in enumerate(lines):
            if text in l and i not in m and not l.startswith('$ '): m[i] = (num, col); break
        else:
            raise SystemExit('mark text not found: ' + text)
    return m

T_IDF = 'ESP-IDF terminal — ~/struthio'
T_FW = 'ESP-IDF terminal — ~/struthio/handheld/firmware'
P_FW = 'maker@bench:~/struthio/handheld/firmware$'

# s01: the version check -------------------------------------------------------------------------------
L = ['$ idf.py --version'] + [l for l in read('version.txt') if l]
shot(f'{OUT}/s01_version.png', T_IDF, L, marks(L, m1_green='v5.5.5'))

# s02: the setup doctor --------------------------------------------------------------------------------
L = ['$ python3 handheld/tools/struthio_doctor.py'] + read('doctor.txt')
while not L[-1]: L.pop()
shot(f'{OUT}/s02_doctor.png', T_IDF, L, marks(L, m1='package complete', m2='ESP-IDF v5.5.5', m3='WARN', m4_green='0 FAIL'))

# s03: the build menu on macOS / Linux -----------------------------------------------------------------
L = [re.sub(r'^\x1b\S*', '', l).replace('\x1b[H\x1b[J\x1b[3J', '') for l in read('menu_sh.txt')]
L = ['$ ./struthio.sh'] + [l for l in L if l.strip() or True][:21]
while not L[-1].strip(): L.pop()
shot(f'{OUT}/s03_menu_sh.png', 'Terminal — ~/struthio', L, cols=72)

# s04: desktop checks ----------------------------------------------------------------------------------
d = read('desktop.txt')
L = ['$ cd handheld', '$ make -C host test'] + pick(d, r'^PASS climb', r'^PASS duel', r'^PASS late', r'^PASS mortal', r'^PASS raw', r'^GOLDEN REPLAY') \
    + ['$ make -C firmware/host_test run'] + pick(d, r'^PASS: wing buttons', r'climb.trace  ROCKER')
shot(f'{OUT}/s04_desktop.png', T_IDF, L, marks(L, m1='PASS climb', m2_green='GOLDEN REPLAY', m3_green='PASS: wing buttons'), max_cols=118)

# s05: set the chip (once) -----------------------------------------------------------------------------
st = read('settarget.txt')
L = ['$ idf.py set-target esp32s3'] + pick(st, r'^Set Target to: esp32s3', r'^-- The C compiler identification is GNU',
                                           r'^NOTICE: Processing 7 dependencies', r'^-- STRUTHIO_ART=', r'^-- Configuring done', r'^-- Build files have been written')
shot(f'{OUT}/s05_settarget.png', T_FW, L, marks(L, m1='Set Target to', m2='STRUTHIO_ART=full'), prompt=P_FW)

# s06: the greybox build -------------------------------------------------------------------------------
b = read('build_grey.txt')
L = ['$ idf.py -p /dev/ttyACM0 -D STRUTHIO_ART=greybox build'] + pick(b, r'^-- STRUTHIO_ART=greybox', r'^-- Build files have been written',
     r'Linking CXX executable struthio.elf', r'^Generated .*struthio.bin', r'^struthio.bin binary size', r'^Project build complete', after=0) \
    + pick(b, r'^ idf.py -p PORT flash')
shot(f'{OUT}/s06_build.png', T_FW, L, marks(L, m1='STRUTHIO_ART=greybox', m2='binary size', m3_green='Project build complete'), prompt=P_FW)

# s07: flashing ----------------------------------------------------------------------------------------
f = [l for l in read('flash_grey.txt') if 'VID/PID' not in l and 'reset the chip manually' not in l]
keep = []
for i, l in enumerate(f):   # a terminal redraws the progress bar in place: keep its last state per file
    if l.startswith('Writing at ') and i + 1 < len(f) and f[i + 1].startswith('Writing at '): continue
    keep.append(l)
f = keep
L = ['$ idf.py -p socket://localhost:5555 -D STRUTHIO_ART=greybox flash'] + block(f, r'^esptool v', r'^Stub flasher running', drop=[r'^WARNING']) \
    + [GAP] + block(f, r"^Writing 'struthio.bin'", r'^Hash of data verified') \
    + [GAP] + block(f, r"^Writing 'greybox_marker", r'^Hash of data verified', drop=[r'^NOTE']) \
    + [GAP] + block(f, r'^Hard resetting', r'^Done')
shot(f'{OUT}/s07_flash.png', T_FW, L, marks(L, m1='Chip type', m2='Wrote 603424', m3_green='Hash of data verified', m4="greybox_marker", m5='Hard resetting'), prompt=P_FW, max_cols=112)

# s08: the full-art switch -----------------------------------------------------------------------------
r = read('reconf_full.txt')
L = ['$ idf.py -D STRUTHIO_ART=full reconfigure'] + pick(r, r'^-- STRUTHIO_ART=full')
shot(f'{OUT}/s08_full_switch.png', T_FW, L, marks(L, m1='STRUTHIO_ART=full'), prompt=P_FW, max_cols=112)

# s09: the boot log (full art) -------------------------------------------------------------------------
q = read('qemu_boot_full.txt')
L = block(q, r'^ESP-ROM:esp32s3', r'^rst:0x1') + [GAP] + block(q, r'boot: ESP-IDF v5.5.5 2nd stage', r'boot: ESP-IDF v5.5.5 2nd stage') \
    + [GAP] + block(q, r'boot: Partition Table', r'boot: End of partition table') + [GAP] + block(q, r'boot: Loaded app', r'boot: Loaded app') \
    + [GAP] + pick(q, r'STRUTHIO handheld boot') + [GAP] + block(q, r'STRUTHIO: audio', r'STRUTHIO: DART trial')
shot(f'{OUT}/s09_bootlog.png', 'ESP32-S3 serial log (emulator)', L, marks(L, m1='rst:0x1', m2='3 assets', m3='STRUTHIO handheld boot', m4='NEW RUN', m5_green='renderer panel'),
     max_cols=104)

# s10: service mode in the log -------------------------------------------------------------------------
s = read('qemu_service.txt')
L = pick(s, r'SERVICE MODE', r'golden replay climb', r'simulation .* us/tick')
shot(f'{OUT}/s10_service_log.png', 'ESP32-S3 serial log (emulator)', L, marks(L, m1_green='PASS ticks=10011'), max_cols=100)

# s11: what a board whose chips do not answer prints ---------------------------------------------------
L = pick(q, r'STRUTHIO handheld boot', r'pmu: AXP2101 not found', r'tca9554: write_direction', r'board: TCA9554 not found', r'ES8311: Open fail',
         r'board: ES8311 not found', r'STRUTHIO: audio OFF')
shot(f'{OUT}/s11_no_chips.png', 'ESP32-S3 serial log (emulator)', L, marks(L, m1_red='AXP2101 not found', m2_red='TCA9554 not found', m3_red='board: ES8311 not found', m4='audio OFF'),
     max_cols=100)

# s12: the high score after a hard power-off ------------------------------------------------------------
p = read('qemu_reboot.txt')
L = pick(p, r'^rst:0x1', r'STRUTHIO: DART trial')
shot(f'{OUT}/s12_reboot.png', 'ESP32-S3 serial log (emulator)', L, marks(L, m1='POWERON', m2_green='best 2000'), max_cols=100)

# ---- firmware screens: frames the firmware drew, read out of the emulator's memory ----------------------
def label_strip(items, out, scale=1, pad=18):
    ims = [Image.open(os.path.join(CAP, n)).convert('RGB') for n, _ in items]
    w, h = ims[0].size
    f = ImageFont.truetype(SANS_B, 22); fs = ImageFont.truetype(SANS, 17)
    W = len(ims) * (w + pad) + pad; H = h + 70
    M = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(M)
    for k, (im, (_, cap)) in enumerate(zip(ims, items)):
        x = pad + k * (w + pad)
        d.rectangle([x - 3, 13, x + w + 2, 16 + h + 2], fill=(30, 30, 30))
        M.paste(im, (x, 16))
        d.text((x + w / 2, h + 34), cap[0], font=f, fill=(20, 20, 20), anchor='mm')
        d.text((x + w / 2, h + 57), cap[1], font=fs, fill=(90, 90, 90), anchor='mm')
    M.save(out, optimize=True)

label_strip([('fw_greybox.png', ('GREYBOX TEST', 'STRUTHIO_ART=greybox')), ('fw_full.png', ('FULL ART', 'round start')),
             ('fw_play.png', ('PLAY', 'rivals on the bottom tier')), ('fw_gameover.png', ('GAME OVER', 'both wings: new run'))],
            f'{OUT}/s13_fw_screens.png')
label_strip([('fw_service.png', ('SERVICE MODE', 'GOLDEN PASS 10011 TICKS'))], f'{OUT}/s14_fw_service.png')

# ---- CP1 as a Gerber viewer shows it (tracespace, from cp1_gerbers.zip) --------------------------------
a, b = Image.open(os.path.join(CAP, 'cp1_front_gerber.png')).convert('RGB'), Image.open(os.path.join(CAP, 'cp1_back_gerber.png')).convert('RGB')
w, h = a.size; pad = 30
M = Image.new('RGB', (w, h * 2 + pad * 4), 'white'); d = ImageDraw.Draw(M)
ft = ImageFont.truetype(SANS_B, 26)
d.text((10, 8), 'FRONT (top layer): four gold combs, the speaker window, the five wire holes', font=ft, fill=(20, 20, 20))
M.paste(a, (0, pad + 12))
d.text((10, h + pad * 2 + 8), 'BACK (bottom layer, seen from the back): pads R  DR  DL  L  G', font=ft, fill=(20, 20, 20))
M.paste(b, (0, h + pad * 3 + 12))
M.save(f'{OUT}/s15_cp1_gerber.png', optimize=True)
print('screens written to', OUT)
