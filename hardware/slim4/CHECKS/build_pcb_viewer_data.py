#!/usr/bin/env python3
"""Bring the studio's PCB data (model-data.js) up to date with the package.

    python -B CHECKS/build_pcb_viewer_data.py

The board geometry (outline, parts, pads, segments, vias, nets) is copied from the PCB layer file
LAYERS/01_PCB/SLIM4_R28_PCB_LAYER.json (written from the board by CHECKS/export_pcb_layer.py);
the legacy mechanical block and notes already in model-data.js are kept. This adds, from files in
the package:
  zones   copper pours: the filled polygons stored in LAYERS/01_PCB/SLIM4_R28.kicad_pcb,
          merged per net and layer and simplified to 0.03 mm for drawing
  parts   mpn, lcsc, package, land ('vendor', 'audited' or 'proxy') and sourcing note for every part,
          read from the footprint descriptions the same way CHECKS/build_builder_packs.py
          writes the BOM
  fab     CHECKS/R28_FAB_SUMMARY.json (written by build_builder_packs.py), if present
  gates   the GATE and FAIL rows and counts of CHECKS/R33_CONVERGENCE_REPORT.json
and, when kicad-cli (KiCad 7.0.x) is on PATH, rewrites R28_REAR_BOARD.svg, the studio's KiCad plot of the
board's back (B.Cu, B.Mask, B.SilkS, Edge.Cuts; plot date pinned).
Re-running it gives the same file. Needs only Python and shapely (requirements.txt).
"""
from pathlib import Path
import json, re, runpy, shutil, subprocess, sys, tempfile
sys.dont_write_bytecode = True
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'model-data.js'
PRE = 'window.STRUTHIO_MODEL = '
NOTE = 'Studio data: '
PACKAGE = 'R33'
GEOMETRY = ('board', 'parts', 'pads', 'segments', 'vias', 'nets', 'stats')
SIMPLIFY = 0.03


def rings(geom):
    polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
    out = []
    for p in polys:
        if p.is_empty:
            continue
        loops = [p.exterior] + list(p.interiors)
        out.append([[round(c, 2) for xy in list(l.coords)[:-1] for c in xy] for l in loops])
    return out


def zones(text):
    merged = {}
    for blk in re.split(r'\n  \(zone ', text)[1:]:
        net = re.search(r'\(net_name "([^"]*)"\)', blk)[1]
        for layer, pts in re.findall(r'\(filled_polygon\s*\(layer "([^"]+)"\)\s*\(pts((?:\s*\(xy [^)]*\))*)\s*\)', blk):
            xy = [(float(a), float(b)) for a, b in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', pts)]
            merged.setdefault((net, layer), []).append(Polygon(xy).buffer(0))   # KiCad stores fills fractured; buffer(0) restores the holes
    out = []
    for (net, layer), polys in sorted(merged.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        g = unary_union(polys)
        out.append({'net': net, 'layer': layer, 'area': round(g.area, 1), 'polys': rings(g.simplify(SIMPLIFY, preserve_topology=True))})
    return out


def rear_plot():
    if not shutil.which('kicad-cli'):
        return 'kicad-cli not found: R28_REAR_BOARD.svg kept'
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'R28_REAR_BOARD.svg'
        subprocess.run(['kicad-cli', 'pcb', 'export', 'svg', '--layers', 'B.Cu,B.Mask,B.SilkS,Edge.Cuts', '--page-size-mode', '2',
                        '--exclude-drawing-sheet', '-o', str(out), str(ROOT / 'LAYERS/01_PCB/SLIM4_R28.kicad_pcb')], check=True, capture_output=True)
        t = re.sub(r'date \d{4}/\d\d/\d\d \d\d:\d\d:\d\d', 'date 2026/10/07 00:00:00', out.read_text())
    (ROOT / 'R28_REAR_BOARD.svg').write_text(t)
    return 'R28_REAR_BOARD.svg plotted'


# Functional systems for the studio's SYSTEMS view. Every net and every part is assigned here, by rule, and the build
# fails if one is left over, so the colours can be checked against this table rather than guessed in the browser.
SYSTEMS = {
    'compute': {'label': 'COMPUTE', 'color': '#68c7ff', 'what': 'ESP32-P4, flash, crystal, reset supervisor, straps and their supplies'},
    'power': {'label': 'POWER', 'color': '#ffcf58', 'what': 'charger, battery switch, 3.3 V buck-boost, 1.2 V core buck, rails'},
    'display': {'label': 'DISPLAY', 'color': '#65e6cf', 'what': 'J1, DSI pairs, panel LDOs, reset gate, backlight boost'},
    'audio': {'label': 'AUDIO', 'color': '#d798ff', 'what': 'two MAX98357A amplifiers, I2S, speaker sockets'},
    'controls': {'label': 'CONTROLS', 'color': '#ff8e58', 'what': 'flaps, DART, power, reset and BOOT switches and their pull-ups'},
    'usb': {'label': 'USB / DEBUG', 'color': '#94df75', 'what': 'USB-C data, ESD, CC detection, USB PHY supply'},
    'radio': {'label': 'RADIO', 'color': '#ff7aa8', 'what': 'RAK3172-SiP LoRa radio, its DC-DC, beads and decoupling, RF pi network, U.FL antenna socket'},
}
NET_RULES = [   # first match wins; GND and the no-connect nets are not assigned
    ('radio', ('RADIO_',)),
    ('display', ('MIPI_DSI_', 'DSI_REXT', 'LCD_', 'BL_', 'BACKLIGHT_PWM', 'VDDO_MIPI_2V5')),
    ('audio', ('I2S_', 'AUDIO_SD_', 'SPK_')),
    ('controls', ('BTN_', 'DART_', 'PWR_WAKE', 'RESET_MR', 'BOOT_STRAP')),
    ('usb', ('USB_DP_CONN', 'USB_DM_CONN', 'USB_JTAG_', 'USB_CC', 'USB_CURR_OUT', 'USB_VBUS_SENSE', 'VDD_USBPHY_LOCAL', 'USB_RECOVERY_', 'UART0_', 'CHASSIS_GND', 'NC_SBU', 'NC_TUSB_')),
    ('compute', ('FLASH_', 'XTAL_', 'VDDO_FLASH_3V3', 'VDDO_PSRAM_1V9', 'CHIP_PU', 'STRAP_GPIO34', 'DOWNLOAD_STRAP_GPIO36', 'NC_U14_')),
    ('power', ('1V1_HP', '3V3_SYS', '3V3_ENABLE', 'SYS_RAW', 'BAT_', 'BQ_', 'CHG_STATUS', 'PGOOD_STATUS', 'EN_DCDC', 'FB_DCDC', 'CORE_SW', 'U4_', 'NC_U4_', 'USB_VBUS')),
]
RAILS = {'GND', '3V3_SYS', 'SYS_RAW', '1V1_HP'}      # shared: they do not decide a part's system
PART_RULES = {   # chips, connectors and parts on several systems' nets
    'compute': ('U1', 'U2', 'U14', 'Y1'), 'power': ('U3', 'U4', 'U10', 'Q2', 'L1', 'L2', 'D1', 'J3', 'C135'),
    'display': ('U5', 'U6', 'U7', 'Q1', 'L3', 'D2', 'J1'), 'audio': ('U8', 'U9', 'J4', 'J5'),
    'usb': ('J2', 'U11', 'U12', 'U13', 'R416'), 'radio': ('U15', 'J701'), 'controls': ('SW1', 'SW2', 'SW3', 'SW4', 'SW5', 'SW6', 'SW7'),
}
SERIES = {'1': 'compute', '2': 'compute', '3': 'display', '4': 'power', '5': 'audio', '6': 'controls'}   # decoupling on a rail


def net_system(name):
    for key, prefixes in NET_RULES:
        if name.startswith(prefixes):
            return key
    return None


def classify(model):
    nets = {}
    for n in sorted({p['netName'] for p in model['pads'] if p.get('netName')} | {s['netName'] for s in model['segments']}):
        k = net_system(n)
        if k:
            nets[n] = k
        else:
            assert n == 'GND' or n.startswith('NC_') or n == 'BQ_TMR', 'net with no system: ' + n
    fixed = {r: k for k, refs in PART_RULES.items() for r in refs}
    pad_nets = {}
    for p in model['pads']:
        if p.get('netName'):
            pad_nets.setdefault(p['ref'], set()).add(p['netName'])
    for p in model['parts']:
        if p['ref'] in fixed:
            p['system'] = fixed[p['ref']]
            continue
        votes = {}
        for n in pad_nets.get(p['ref'], ()):
            if n not in RAILS and n in nets:
                votes[nets[n]] = votes.get(nets[n], 0) + 1
        if votes:
            best = sorted(votes.items(), key=lambda kv: -kv[1])
            assert len(best) == 1 or best[0][1] > best[1][1], f"{p['ref']} sits on two systems' nets: {votes}"
            p['system'] = best[0][0]
        else:
            series = p['ref'][1] if p['ref'][0] in 'RCL' and p['ref'][1:].isdigit() and len(p['ref']) == 4 else None
            assert series in SERIES, 'part with no system: ' + p['ref']
            p['system'] = SERIES[series]
    return nets

def main():
    src = DATA.read_text()
    assert src.startswith(PRE) and src.endswith(';\n'), 'unexpected model-data.js layout'
    model = json.loads(src[len(PRE):-2])
    layer = json.loads((ROOT / 'LAYERS/01_PCB/SLIM4_R28_PCB_LAYER.json').read_text())
    for k in GEOMETRY:
        model[k] = layer[k]
    model['source'], model['status'] = layer['source'], layer['status']
    text = (ROOT / 'LAYERS/01_PCB/SLIM4_R28.kicad_pcb').read_text()

    packs = runpy.run_path(str(ROOT / 'CHECKS/build_builder_packs.py'))      # same parser as the BOM
    info = {p['ref']: p for p in packs['board_parts'](text)}
    for p in model['parts']:
        b = info[p['ref']]
        p['mpn'], p['lcsc'], p['package'] = b['mpn'], b['lcsc'], b['pkg']
        p['land'] = 'proxy' if 'package proxy' in b['descr'] else 'audited' if 'R22 land-pattern audit' in b['descr'] else 'vendor'
        p['sourcing'] = ('LCSC ' + b['lcsc']) if b['lcsc'] else ('part not bound yet' if 'BIND_BEFORE_FAB' in b['descr'] else 'by manufacturer part number')

    model['zones'] = zones(text)
    model['systems'] = SYSTEMS
    model['netSystems'] = classify(model)

    fab = ROOT / 'CHECKS/R28_FAB_SUMMARY.json'
    if fab.exists():
        model['fab'] = json.loads(fab.read_text())
    else:
        model.pop('fab', None)

    rep = json.loads((ROOT / 'CHECKS/R33_CONVERGENCE_REPORT.json').read_text())
    model['gates'] = {'counts': {k: rep['counts'].get(k, 0) for k in ('PASS', 'FAIL', 'GATE', 'INFO')}, 'source': 'CHECKS/R33_CONVERGENCE_REPORT.md',
                      'open': [{'id': c['id'], 'interface': c['interface'], 'title': c['title'], 'detail': c['detail'], 'status': c['status']}
                               for c in rep['checks'] if c['status'] in ('FAIL', 'GATE')]}

    model['name'] = f'STRUTHIO SLIM4 {PACKAGE} · R28 PCB'
    model['notes'] = [n for n in model['notes'] if not n.startswith((NOTE, 'R25 studio data: ', 'R25 KiCad DRC', 'R26 KiCad DRC', 'R27 KiCad DRC', 'R28 KiCad DRC', 'Board outline, footprint XY', 'R21 connectivity'))]
    model['notes'][:0] = ['Board outline, footprint XY, pads, routed copper segments and vias are exported from the R28 KiCad board '
                          '(LAYERS/01_PCB/SLIM4_R28_PCB_LAYER.json, CHECKS/export_pcb_layer.py).',
                          'R28 KiCad DRC: 0 violations, 0 unconnected pads, 0 footprint errors. The JLCPCB order files are generated by '
                          'CHECKS/build_builder_packs.py; U1 (ESP32-P4NRW32X) stock is the open ordering item.']
    model['notes'].append(
        NOTE + 'zones are the filled copper pours stored in the R28 board (merged per net and layer, simplified to '
        f'{SIMPLIFY} mm); part mpn/lcsc/package/land come from the footprint descriptions; fab is CHECKS/R28_FAB_SUMMARY.json; '
        'gates are the open FAIL and GATE rows of the convergence report. Written by CHECKS/build_pcb_viewer_data.py.')

    DATA.write_text(PRE + json.dumps(model, separators=(',', ':'), ensure_ascii=False) + ';\n')
    print(rear_plot())
    pts = sum(len(r) // 2 for z in model['zones'] for p in z['polys'] for r in p)
    by = {k: sum(p['system'] == k for p in model['parts']) for k in SYSTEMS}
    print('systems: ' + ', '.join(f'{k} {v} parts' for k, v in by.items()) + f", {len(model['netSystems'])} nets assigned")
    print(f"model-data.js: {len(model['zones'])} pours ({pts} points), {len(model['parts'])} parts with sourcing, "
          f"fab {'yes' if 'fab' in model else 'missing'}, {len(model['gates']['open'])} open gates, {DATA.stat().st_size:,} bytes")


if __name__ == '__main__':
    main()
