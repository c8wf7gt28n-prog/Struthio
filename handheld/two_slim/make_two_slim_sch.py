#!/usr/bin/env python3
"""STRUTHIO TWO SLIM · writes the KiCad 7 schematic from netlist.py, then checks it with KiCad itself.

    python3 make_two_slim_sch.py        -> out/struthio_two_slim.kicad_sch, .net, _schematic.pdf

Every pin carries a label with its net name (a "labelled" schematic: no wires to route by hand, and nothing to
misread). After writing, KiCad's netlist is exported from the drawing and compared with netlist.py pin by pin, so
the drawing and the data cannot disagree. (KiCad 7's command line has no ERC; open it in KiCad 8+ to run one.)
"""
import os, re, subprocess, uuid, datetime
import netlist as N

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
NAME = 'struthio_two_slim'
G = 2.54
U = lambda: str(uuid.uuid4())
ROOT = U()
FONT = '(effects (font (size 1.27 1.27)))'
HIDE = '(effects (font (size 1.27 1.27)) hide)'
CH = 1.0                                         # mm per character of 1.27 mm text (generous)

BLOCKS = [  # name, title, x, y, width of the block (mm), on an A2 sheet (594 x 420)
    ('USB', 'USB-C, ESD', 15, 30, 175),
    ('ESP32', 'ESP32-S3-WROOM-1-N16R8, RESET, BOOT', 200, 30, 185),
    ('PANEL', 'PANEL: 40-pin FPC, backlight', 395, 30, 185),
    ('POWER', 'POWER: AXP2101, battery, power key', 15, 145, 370),
    ('AUDIO', 'AUDIO: ES8311 -> NS4150B -> speaker', 395, 230, 185),
    ('IOEXP', 'I/O EXPANDER TCA9554 (0x20)', 15, 330, 175),
    ('KEYS', 'GAME KEYS', 200, 330, 185),
]

def gr(v): return round(v / G) * G

def symbol_kind(p):
    """one library symbol per part: ICs and connectors get their own; 2-pin parts share one per prefix"""
    pre = re.match(r'[A-Z]+', p['ref']).group(0)
    if len(p['pins']) == 2 and set(p['pins']) == {'1', '2'}: return f'TWO_{pre}'
    return f'{pre}_{re.sub(r"[^A-Za-z0-9]", "_", p["value"])}'

def layout(p):
    """pins split left/right; returns (pins with lib coords, body w, h)"""
    nums = list(p['pins'])
    if len(nums) == 2 and set(nums) == {'1', '2'}:
        return [('1', p['pins']['1'][0], -5.08, 0, 0), ('2', p['pins']['2'][0], 5.08, 0, 180)], 5.08, 2.54
    def key(n):
        m = re.match(r'([A-Z]*)(\d+)', n)
        return (m.group(1), int(m.group(2))) if m else (n, 0)
    nums.sort(key=key)
    half = (len(nums) + 1) // 2
    left, right = nums[:half], nums[half:]
    names = [p['pins'][n][0] for n in nums]
    w = gr(max(12.7, 2 * max(len(s) for s in names) * CH + 5.08))
    h = max(len(left), len(right)) * G + G
    pins = []
    for i, n in enumerate(left): pins.append((n, p['pins'][n][0], -w / 2 - G, h / 2 - G - i * G, 0))
    for i, n in enumerate(right): pins.append((n, p['pins'][n][0], w / 2 + G, h / 2 - G - i * G, 180))
    return pins, w, h

def lib_symbol(kind, p, pins, w, h):
    pre = re.match(r'[A-Z]+', p['ref']).group(0)
    two = kind.startswith('TWO_')
    body = f'(rectangle (start {-w / 2:.2f} {h / 2:.2f}) (end {w / 2:.2f} {-h / 2:.2f}) (stroke (width 0.254) (type default)) (fill (type background)))'
    ps = ''.join(f'(pin passive line (at {x:.2f} {y:.2f} {a}) (length 2.54) (name "{nm if not two else "~"}" {FONT}) (number "{n}" {FONT}))'
                 for n, nm, x, y, a in pins)
    pn = '(pin_numbers hide) (pin_names hide)' if two else '(pin_names (offset 0.508))'
    return (f'(symbol "two_slim:{kind}" {pn} (in_bom yes) (on_board yes)'
            f'(property "Reference" "{pre}" (at 0 {h / 2 + 1.5:.2f} 0) {FONT})(property "Value" "{kind}" (at 0 {-h / 2 - 1.5:.2f} 0) {FONT})'
            f'(property "Footprint" "" (at 0 0 0) {HIDE})(property "Datasheet" "" (at 0 0 0) {HIDE})'
            f'(symbol "{kind}_0_1" {body})(symbol "{kind}_1_1" {ps}))')

def esc(s): return s.replace('"', "'")

def build():
    os.makedirs(OUT, exist_ok=True)
    libs, items = {}, []
    by_block = {b[0]: [] for b in BLOCKS}
    for p in N.PARTS: by_block[p['block']].append(p)
    for bname, title, bx, by, bw in BLOCKS:
        items.append(f'(text "{title}" (at {bx} {by - 8} 0) (effects (font (size 4 4) (thickness 0.6) bold) (justify left bottom)) (uuid {U()}))')
        x, y, rowh = bx, by, 0
        for p in by_block[bname]:
            kind = symbol_kind(p); pins, w, h = layout(p)
            if kind not in libs: libs[kind] = lib_symbol(kind, p, pins, w, h)
            nets = {n: net for n, (nm, net) in p['pins'].items()}
            lab = max([len(net or '') for net in nets.values()] + [2]) * CH + 4
            fw = w + 2 * (G + lab) + 6
            fh = h + 10
            if x + fw > bx + bw and x > bx: x, y, rowh = bx, y + rowh, 0
            cx, cy = gr(x + fw / 2), gr(y + h / 2 + 4)
            props = (f'(property "Reference" "{p["ref"]}" (at {cx:.2f} {cy - h / 2 - 1.5:.2f} 0) {FONT})'
                     f'(property "Value" "{esc(p["value"])}" (at {cx:.2f} {cy + h / 2 + 1.5:.2f} 0) {FONT})'
                     f'(property "Footprint" "{p["fp"]}" (at {cx:.2f} {cy:.2f} 0) {HIDE})'
                     f'(property "Datasheet" "" (at {cx:.2f} {cy:.2f} 0) {HIDE})'
                     f'(property "LCSC" "{p["lcsc"]}" (at {cx:.2f} {cy:.2f} 0) {HIDE})')
            pinu = ''.join(f'(pin "{n}" (uuid {U()}))' for n in p['pins'])
            items.append(f'(symbol (lib_id "two_slim:{kind}") (at {cx:.2f} {cy:.2f} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {U()})'
                         f'{props}{pinu}(instances (project "{NAME}" (path "/{ROOT}" (reference "{p["ref"]}") (unit 1)))))')
            for n, nm, px, py, a in pins:
                sx, sy = cx + px, cy - py                                   # library y is up, the sheet's y is down
                net = nets[n]
                if net is None:
                    items.append(f'(no_connect (at {sx:.2f} {sy:.2f}) (uuid {U()}))')
                else:
                    ang, just = (180, 'right') if a == 0 else (0, 'left')
                    items.append(f'(global_label "{net}" (shape passive) (at {sx:.2f} {sy:.2f} {ang}) (fields_autoplaced) '
                                 f'(effects (font (size 1.27 1.27)) (justify {just})) (uuid {U()}) '
                                 f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {sx:.2f} {sy:.2f} 0) {HIDE}))')
            x += fw; rowh = max(rowh, fh)
    today = datetime.date.today().isoformat()
    doc = (f'(kicad_sch (version 20230121) (generator eeschema) (uuid {ROOT}) (paper "A2")'
           f'(title_block (title "STRUTHIO TWO SLIM") (date "{today}") (rev "0.1") (company "R.A. PEDDYCOART")'
           f'(comment 1 "Generated from handheld/two_slim/netlist.py. Reference: Waveshare ESP32-S3-Touch-LCD-3.5B rev 2.0 + datasheets."))'
           f'(lib_symbols {"".join(libs.values())})' + ''.join(items) +
           '(sheet_instances (path "/" (page "1"))))')
    path = os.path.join(OUT, NAME + '.kicad_sch')
    open(path, 'w').write(doc)
    open(os.path.join(OUT, NAME + '.kicad_pro'), 'w').write('{"meta": {"filename": "%s.kicad_pro", "version": 1}}\n' % NAME)
    return path

def check(path):
    # KiCad 7's command line has no ERC (it came in KiCad 8): the netlist comparison below is the check.
    erc = ''
    subprocess.run(['kicad-cli', 'sch', 'export', 'pdf', '-o', os.path.join(OUT, NAME + '_schematic.pdf'), path], capture_output=True)
    net = os.path.join(OUT, NAME + '.net')
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '-o', net, path], capture_output=True)
    got = {}
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]+)"\)(.*?)\)\s*(?=\(net |\)\s*\)\s*$)', open(net).read(), re.S):
        got[m.group(1).lstrip('/')] = sorted(re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"', m.group(2)))
    want = {k: sorted((r, p) for r, p, _ in v) for k, v in N.nets().items()}
    bad = [k for k in want if got.get(k) != want[k]]
    extra = [k for k in got if k not in want and not k.startswith('unconnected-') and not k.startswith('Net-')]
    return erc, bad, extra, len(got)

if __name__ == '__main__':
    p = build()
    erc, bad, extra, n = check(p)
    print('wrote', p)
    print('\n'.join(l for l in erc.splitlines() if 'Found' in l or 'error' in l.lower())[:2000])
    print(f'KiCad netlist: {n} nets; differ from netlist.py: {bad or "none"}; extra: {extra or "none"}')
