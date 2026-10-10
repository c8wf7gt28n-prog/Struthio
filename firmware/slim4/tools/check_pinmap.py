#!/usr/bin/env python3
"""Check the firmware's GPIO assignments against the PCB R27 board (pins unchanged from R23).

Every SLIM4_GPIO_* in components/slim4_bsp/include/slim4_pins.h is looked up in the ESP32-P4 QFN-104 pin table
(GPIO -> package pad, datasheet section 2.2 / chip revision v3) and the board net on that U1 pad is read from
tools/u1_pad_nets.json, which ships with the firmware (U1's pad -> net table, taken from the board export
hardware/slim4/LAYERS/01_PCB/SLIM4_R27_PCB_LAYER.json). The net must be the one the define is named for. The display,
I2S and active-low control code paths are checked to use the defines.

The hardware self-test's table (SLIM4_ST_PINS in components/slim4_bsp/slim4_selftest_logic.c) is checked the same way:
each GPIO on its pad, each net on that pad (the unused pads it drives must have no net), and, where the board export is
at hand (inside the repository, or --board), each pull resistor's value and rail and the PWR_WAKE capacitor.

    python3 tools/check_pinmap.py                      # the bundled table: works from the firmware folder alone
    python3 tools/check_pinmap.py --board EXPORT.json  # a board export instead (e.g. a newer PCB revision)
    python3 tools/check_pinmap.py --write-table EXPORT.json   # refresh tools/u1_pad_nets.json from an export

Inside the full repository the bundled table is also compared with the repository's board export.
"""
import json, re, sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
table = root / 'tools/u1_pad_nets.json'
repo_board = root.parents[1] / 'hardware/slim4/LAYERS/01_PCB/SLIM4_R27_PCB_LAYER.json'


def u1_pads(export):
    """U1 pad number -> net name from a board export (*_PCB_LAYER.json)."""
    return {p['num']: p['netName'] for p in json.loads(Path(export).read_text())['pads']
            if p['ref'] == 'U1' and p['num'].isdigit()}


args = sys.argv[1:]
if args[:1] == ['--write-table']:
    src = Path(args[1])
    table.write_text(json.dumps({'board': src.name, 'u1_pads': dict(sorted(u1_pads(src).items(), key=lambda kv: int(kv[0])))},
                                indent=1) + '\n')
    print(f'wrote {table.relative_to(root)} from {src.name}')
    sys.exit(0)
if args[:1] == ['--board']:
    board_src = Path(args[1]); pads_by_num = u1_pads(board_src)
else:
    t = json.loads(table.read_text()); board_src = Path(t['board']); pads_by_num = t['u1_pads']
    if repo_board.exists() and u1_pads(repo_board) != pads_by_num:
        print(f'FAIL: tools/u1_pad_nets.json ({t["board"]}) differs from {repo_board.name}; '
              f'refresh it with --write-table {repo_board}')
        sys.exit(1)

# ESP32-P4 QFN-104: GPIO -> package pad, for the GPIOs this board uses (pin 9 is VDD_LP, so GPIO9.. sit one pad up;
# GPIO0 is pad 104, beside CHIP_PU on 103).
P4_PAD = {0: 104, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 10, 10: 11, 11: 12, 13: 14, 16: 17, 17: 18,
          24: 52, 25: 53, 35: 66, 43: 84, 44: 86, 46: 88,
          # unused GPIOs the self-test drives, beside tested nets (pads 13-19 run GPIO12-18; 85 is a supply pad,
          # so GPIO43/44/45/46 are pads 84/86/87/88)
          12: 13, 14: 15, 15: 16, 18: 19, 45: 87}
# define name -> board net, where they differ
NET = {'BOOT_BTN': 'BOOT_STRAP'}

pins = {m[1]: int(m[2]) for m in re.finditer(r'#define\s+SLIM4_GPIO_(\w+)\s+GPIO_NUM_(\d+)', (root / 'components/slim4_bsp/include/slim4_pins.h').read_text())}
pads = {int(k): v for k, v in pads_by_num.items()}

bad = []
for name, gpio in sorted(pins.items(), key=lambda t: t[1]):
    want = NET.get(name, name)
    pad = P4_PAD.get(gpio)
    got = pads.get(pad, 'no pad') if pad else 'GPIO not in the pin table'
    print(f'  GPIO{gpio:<3} pad {pad!s:>4}  {name:16} board net {got}')
    if got != want:
        bad.append(f'SLIM4_GPIO_{name} = GPIO{gpio}: board pad {pad} is {got!r}, expected {want!r}')
# the console pins must stay the USB-Serial-JTAG pair
for gpio, net in ((24, 'USB_JTAG_DM'), (25, 'USB_JTAG_DP')):
    if pads.get(P4_PAD[gpio]) != net:
        bad.append(f'GPIO{gpio} pad {P4_PAD[gpio]} is {pads.get(P4_PAD[gpio])!r}, expected {net}')
source = (root / 'components/slim4_bsp/slim4_board.c').read_text()
for token in ['SLIM4_GPIO_BTN_LEFT', 'SLIM4_GPIO_BTN_RIGHT', 'SLIM4_GPIO_DART_LEFT', 'SLIM4_GPIO_DART_RIGHT', 'GPIO_PULLUP_DISABLE',
              'I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG', 'SLIM4_GPIO_I2S_BCLK', 'SLIM4_GPIO_I2S_LRCLK', 'SLIM4_GPIO_I2S_DOUT',
              'SLIM4_GPIO_AUDIO_SD_CTRL', 'SLIM4_GPIO_BACKLIGHT_PWM', 'SLIM4_GPIO_LCD_RESET_GATE']:
    if token not in source:
        bad.append(f'slim4_board.c does not use {token}')

# the self-test's pin table
ST = re.compile(r'\{(\d+), (\d+), "(\w+)", SLIM4_PULL_(\w+), SLIM4_ROLE_(\w+), (NULL|"[^"]*"), "([^"]*)", (true|false), (true|false), (true|false)\}')
st = [m.groups() for m in ST.finditer((root / 'components/slim4_bsp/slim4_selftest_logic.c').read_text())]
if len(st) < 20:
    bad.append(f'SLIM4_ST_PINS: only {len(st)} entries parsed')
export = Path(args[1]) if args[:1] == ['--board'] else (repo_board if repo_board.exists() else None)
parts = {}
if export:
    ex = json.loads(export.read_text())
    values = {p['ref']: p['value'] for p in ex['parts']}
    for p in ex['pads']:
        parts.setdefault(p['ref'], {})[p['num']] = p['netName']
VALUE = {'10K': '1002', '100K': '1003'}
for gpio, pad, net, pull, role, pull_part, load, drive_ok, cap, rc in st:
    gpio, pad = int(gpio), int(pad)
    want = '' if role == 'UNUSED' else net
    got = pads.get(pad, 'no pad')
    if P4_PAD.get(gpio) != pad:
        bad.append(f'self-test {net}: GPIO{gpio} is pad {P4_PAD.get(gpio)}, table says pad {pad}')
    if got != want:
        bad.append(f'self-test {net}: U1 pad {pad} is {got!r}, expected {want!r}')
    if gpio in pins.values() and NET.get(next(k for k, v in pins.items() if v == gpio), next(k for k, v in pins.items() if v == gpio)) != net:
        bad.append(f'self-test {net}: GPIO{gpio} is named differently in slim4_pins.h')
    if export and pull != 'NONE':
        ref = pull_part.strip('"').split()[0]
        rail = '3V3_SYS' if pull.startswith('UP') else 'GND'
        ends = set(parts.get(ref, {}).values())
        if ends != {net, rail}:
            bad.append(f'self-test {net}: {ref} joins {sorted(ends)}, expected {net} and {rail}')
        if VALUE[pull.split('_')[1]] not in values.get(ref, ''):
            bad.append(f'self-test {net}: {ref} is {values.get(ref)!r}, expected {pull.split("_")[1].lower()}')
    if export and cap == 'true':
        caps = [r for r, nets in parts.items() if r.startswith('C') and net in nets.values() and '104' in values.get(r, '')
                and set(nets.values()) == {net, 'GND'}]
        if not caps:
            bad.append(f'self-test {net}: marked with a capacitor, but no 100 nF from it to GND on the board')
    if export and role != 'UNUSED':
        on_board = [r for r, nets in parts.items() if r.startswith('C') and net in nets.values()]
        if on_board and cap != 'true':
            bad.append(f'self-test {net}: {", ".join(on_board)} on the net, but the table has no capacitor')
print(f'  self-test table: {len(st)} pins' + (f', pull resistors and capacitors checked in {export.name}' if export else
                                              ', resistor values not checked (no board export at hand)'))
if bad:
    print('FAIL:\n  ' + '\n  '.join(bad))
    sys.exit(1)
print(f'PASS: {len(pins)} firmware GPIO assignments and {len(st)} self-test pins match the board nets on U1 '
      f'({board_src.name}); USB-Serial-JTAG pair intact')
