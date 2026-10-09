#!/usr/bin/env python3
"""Check the firmware's GPIO assignments against the PCB R25 board itself (pins unchanged from R23).

Every SLIM4_GPIO_* in components/slim4_bsp/include/slim4_pins.h is looked up in the ESP32-P4 QFN-104 pin table
(GPIO -> package pad, datasheet section 2.2 / chip revision v3) and the board net on that U1 pad is read from
hardware/slim4/LAYERS/01_PCB/SLIM4_R25_PCB_LAYER.json (exported from SLIM4_R25.kicad_pcb). The net must be the
one the define is named for. The display, I2S and active-low control code paths are checked to use the defines.
"""
import json, re, sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
board = root.parents[1] / 'hardware/slim4/LAYERS/01_PCB/SLIM4_R25_PCB_LAYER.json'

# ESP32-P4 QFN-104: GPIO -> package pad, for the GPIOs this board uses (pin 9 is VDD_LP, so GPIO9.. sit one pad up;
# GPIO0 is pad 104, beside CHIP_PU on 103).
P4_PAD = {0: 104, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 10, 10: 11, 11: 12, 13: 14, 16: 17, 17: 18,
          24: 52, 25: 53, 35: 66, 43: 84, 44: 86, 46: 88}
# define name -> board net, where they differ
NET = {'BOOT_BTN': 'BOOT_STRAP'}

pins = {m[1]: int(m[2]) for m in re.finditer(r'#define\s+SLIM4_GPIO_(\w+)\s+GPIO_NUM_(\d+)', (root / 'components/slim4_bsp/include/slim4_pins.h').read_text())}
pads = {}
for p in json.loads(board.read_text())['pads']:
    if p['ref'] == 'U1' and p['num'].isdigit():
        pads[int(p['num'])] = p['netName']

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
if bad:
    print('FAIL:\n  ' + '\n  '.join(bad))
    sys.exit(1)
print(f'PASS: {len(pins)} firmware GPIO assignments match the R25 board nets on U1 ({board.name}); USB-Serial-JTAG pair intact')
