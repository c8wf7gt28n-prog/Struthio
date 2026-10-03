#!/usr/bin/env python3
"""STRUTHIO TWO SLIM · the circuit, as data: every part, its value, footprint, LCSC number and what each pin
connects to. The schematic (make_two_slim_sch.py) and, later, the board are generated from this file only.

Source of every block: Waveshare ESP32-S3-Touch-LCD-3.5B rev 2.0 schematic (REF) and the chip datasheets (DS).
Where TWO SLIM differs from REF, the line says so.

    python3 netlist.py          prints the nets, flags nets with only one pin, and a part count
"""
from collections import defaultdict

P0402, P0603, P0805 = 'Resistor_SMD:R_0402_1005Metric', 'Resistor_SMD:R_0603_1608Metric', 'Resistor_SMD:R_0805_2012Metric'
C0402, C0603, C0805 = 'Capacitor_SMD:C_0402_1005Metric', 'Capacitor_SMD:C_0603_1608Metric', 'Capacitor_SMD:C_0805_2012Metric'

PARTS = []      # dicts: ref, value, fp, lcsc, block, pins {number: (name, net)}, note

def part(ref, value, fp, block, pins, lcsc='', note=''):
    PARTS.append(dict(ref=ref, value=value, fp=fp, lcsc=lcsc, block=block, pins=pins, note=note))

def two(ref, value, fp, block, a, b, lcsc='', note=''):
    part(ref, value, fp, block, {'1': ('1', a), '2': ('2', b)}, lcsc, note)

R = lambda ref, v, a, b, block, fp=P0402, lcsc='', note='': two(ref, v, fp, block, a, b, lcsc, note)
C = lambda ref, v, a, b, block, fp=C0402, lcsc='', note='': two(ref, v, fp, block, a, b, lcsc, note)

# ---- USB-C (REF: J5, R24/R26 5.1k, LRC4 bead, D3 ESD, R18/R19 22R, D1/D2 ESD) --------------------------------------
part('J2', 'USB-C 16P', 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12', 'USB', {
    'A1': ('GND', 'GND'), 'B12': ('GND', 'GND'), 'A12': ('GND', 'GND'), 'B1': ('GND', 'GND'),
    'A4': ('VBUS', 'VBUS_C'), 'B9': ('VBUS', 'VBUS_C'), 'A9': ('VBUS', 'VBUS_C'), 'B4': ('VBUS', 'VBUS_C'),
    'A5': ('CC1', 'CC1'), 'B5': ('CC2', 'CC2'), 'A6': ('DP1', 'USB_CP'), 'B6': ('DP2', 'USB_CP'),
    'A7': ('DN1', 'USB_CN'), 'B7': ('DN2', 'USB_CN'), 'A8': ('SBU1', None), 'B8': ('SBU2', None), 'S1': ('SHIELD', 'GND'),
}, lcsc='C165948', note='HRO TYPE-C-31-M-12, the common JLC USB-C receptacle')
R('R24', '5.1k', 'CC1', 'GND', 'USB'); R('R26', '5.1k', 'CC2', 'GND', 'USB')
two('FB1', '120R@100MHz', 'Inductor_SMD:L_0603_1608Metric', 'USB', 'VBUS_C', 'VBUS', note='REF LRC4 BTREF1608A3R121')
two('D3', 'ESD 5V', 'Diode_SMD:D_SOD-523', 'USB', 'VBUS', 'GND', note='REF LESD8LH5.0CT5G; LCSC to pick')
C('C24', '10uF', 'VBUS', 'GND', 'USB', C0603)
R('R18', '22R', 'USB_CP', 'USB_DP', 'USB'); R('R19', '22R', 'USB_CN', 'USB_DN', 'USB')
two('D1', 'ESD 5V', 'Diode_SMD:D_SOD-523', 'USB', 'USB_CP', 'GND', note='REF LESD8LH5.0CT5G')
two('D2', 'ESD 5V', 'Diode_SMD:D_SOD-523', 'USB', 'USB_CN', 'GND', note='REF LESD8LH5.0CT5G')

# ---- power: AXP2101 (REF UP1; DS figure 7-1) --------------------------------------------------------------------------
AXP = {
    '37': ('VBUS', 'VBUS'), '36': ('VMID', 'VMID'), '34': ('VSYS', 'VSYS'), '35': ('SW', 'SW'), '32': ('GPIO1', None),
    '33': ('BAT', 'VBAT'), '31': ('TS', 'TS'), '1': ('CHGLED', None), '2': ('VREF', 'VREF'),
    '17': ('ALDOIN', 'VSYS'), '18': ('ALDO1', 'LVCC3V3'), '19': ('ALDO2', 'ALDO2'), '16': ('ALDO3', 'ALDO3'), '15': ('ALDO4', 'ALDO4'),
    '13': ('BLDOIN', 'VSYS'), '12': ('BLDO1', 'BLDO1'), '14': ('BLDO2', 'BLDO2'),
    '39': ('SDA', 'I2C_SDA'), '40': ('SCK', 'I2C_SCL'), '38': ('IRQ', 'AXP_IRQ'), '29': ('PWROK', 'PWROK'), '30': ('PWRON', 'PWRON'),
    '23': ('VIN1', 'VSYS'), '22': ('LX1', 'LX1'), '21': ('FB1', 'VCC3V3'), '20': ('DLDO1/DC1SW', 'DLDO1'),
    '24': ('VIN2', 'VSYS'), '25': ('LX2', None), '26': ('FB2', None),
    '6': ('VIN3', 'VSYS'), '5': ('LX3', None), '4': ('FB3', None),
    '7': ('VIN4', 'VSYS'), '8': ('LX4', None), '9': ('FB4', None),
    '10': ('CPUSLDO', 'CPUSLDO'), '11': ('DLDO2/DC4SW', 'DLDO2'), '28': ('RTCLDO', 'VRTC'), '27': ('VBACKUP', 'VBACKUP'),
    '3': ('GND', 'GND'), '41': ('EP', 'GND'),
}
part('U2', 'AXP2101', 'Package_DFN_QFN:QFN-40-1EP_5x5mm_P0.4mm_EP3.6x3.6mm', 'POWER', AXP, lcsc='C3036461',
     note='DS: 5x5 QFN-40, 0.4 pitch, EP 3.4 nom')
C('C20', '10uF', 'VBUS', 'GND', 'POWER', C0603); C('C23', '10uF', 'VMID', 'GND', 'POWER', C0603)
two('L6', '2.2uH', 'Inductor_SMD:L_1210_3225Metric', 'POWER', 'SW', 'VSYS', note='buck to VSYS (DS fig 7-1); REF L6')
C('C28', '22uF', 'VSYS', 'GND', 'POWER', C0805); C('C29', '22uF', 'VSYS', 'GND', 'POWER', C0805)
C('C26', '100nF', 'VSYS', 'GND', 'POWER')
C('C31', '2.2uF', 'VBAT', 'GND', 'POWER')
two('RT1', 'NTC 10k', P0402, 'POWER', 'TS', 'GND', note='REF R29; the firmware turns TS sensing off, so a 10k resistor also works')
C('C32', '2.2uF', 'VREF', 'GND', 'POWER')
C('C33', '2.2uF', 'VSYS', 'GND', 'POWER', note='ALDOIN'); C('C34', '2.2uF', 'LVCC3V3', 'GND', 'POWER')
C('C35', '2.2uF', 'VSYS', 'GND', 'POWER', note='BLDOIN')
for ref, net in (('C36', 'BLDO1'), ('C38', 'BLDO2'), ('C84', 'ALDO2'), ('C85', 'ALDO3'), ('C86', 'ALDO4'),
                 ('C87', 'DLDO1'), ('C88', 'DLDO2'), ('C89', 'CPUSLDO')):
    C(ref, '2.2uF', net, 'GND', 'POWER', note='unused rail the firmware enables: a cap keeps the LDO stable (REF leaves some bare)')
C('C22', '2.2uF', 'VSYS', 'GND', 'POWER', note='VIN1')
for ref in ('C76', 'C77', 'C78'): C(ref, '2.2uF', 'VSYS', 'GND', 'POWER', note='VIN2-4 (DCDC2-4 unused, as REF)')
two('L5', '1uH 3.5A', 'Inductor_SMD:L_1210_3225Metric', 'POWER', 'LX1', 'VCC3V3', note='REF L5 1uH/3.5A')
C('C81', '22uF', 'VCC3V3', 'GND', 'POWER', C0805); C('C82', '1uF', 'VCC3V3', 'GND', 'POWER'); C('C83', '100nF', 'VCC3V3', 'GND', 'POWER')
C('C39', '2.2uF', 'VRTC', 'GND', 'POWER'); C('C40', '2.2uF', 'VBACKUP', 'GND', 'POWER')
R('R39', '10k', 'VRTC', 'AXP_IRQ', 'POWER'); R('R66', '0R', 'PWROK', 'ESP_EN', 'POWER')
C('C79', '1nF', 'PWRON', 'GND', 'POWER')
R('R34', '2.2k', 'VCC3V3', 'I2C_SDA', 'POWER', note='DS: SDA/SCK need 2.2k pull-ups')
R('R35', '2.2k', 'VCC3V3', 'I2C_SCL', 'POWER')
# the power key: REF K3, R38 510R, R37 1k, R65 100k, T3 BSS138, R33 10k -> SYS_OUT
part('SW5', 'POWER key', 'Button_Switch_SMD:SW_SPST_TL3342', 'POWER', {'1': ('1', 'PWRON_K'), '2': ('2', 'GND')},
     note='side-push key at the left edge: part to pick at layout')
R('R38', '510R', 'PWRON', 'PWRON_K', 'POWER'); R('R37', '1k', 'PWRON_K', 'PWRK_G', 'POWER'); R('R65', '100k', 'VCC3V3', 'PWRK_G', 'POWER')
part('Q3', 'BSS138', 'Package_TO_SOT_SMD:SOT-23', 'POWER', {'1': ('G', 'PWRK_G'), '2': ('S', 'GND'), '3': ('D', 'SYS_OUT')}, lcsc='C52895')
R('R33', '10k', 'VCC3V3', 'SYS_OUT', 'POWER')

# ---- battery: JST PH 2.0 + reverse-battery guard (not in REF: the SLIM board's Q1, because cell leads vary) --------------
part('J3', 'BATTERY', 'Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal', 'POWER',
     {'1': ('+', 'VBAT_IN'), '2': ('-', 'GND'), 'MP': ('MP', None)}, lcsc='C295747')
part('Q2', 'AO3401A', 'Package_TO_SOT_SMD:SOT-23', 'POWER', {'1': ('G', 'GND'), '2': ('S', 'VBAT'), '3': ('D', 'VBAT_IN')},
     lcsc='C15127', note='P-FET: a reversed cell switches it off')

# ---- ESP32-S3-WROOM-1-N16R8 (REF: ESP32-S3R8 + W25Q128 + crystal + antenna, replaced by the module) --------------------
ESP = {'1': ('GND', 'GND'), '40': ('GND', 'GND'), '41': ('GND', 'GND'), '2': ('3V3', 'VCC3V3'), '3': ('EN', 'ESP_EN'),
       '39': ('IO1', 'LCD_D0'), '38': ('IO2', 'LCD_D1'), '15': ('IO3', 'LCD_D2'), '4': ('IO4', 'LCD_D3'), '5': ('IO5', 'LCD_CLK_M'),
       '6': ('IO6', 'LCD_BL'), '7': ('IO7', 'I2C_SCL'), '12': ('IO8', 'I2C_SDA'), '20': ('IO12', 'LCD_CS'),
       '21': ('IO13', 'I2S_SCLK_M'), '22': ('IO14', 'I2S_ASDOUT'), '8': ('IO15', 'I2S_LRCK'), '9': ('IO16', 'I2S_DSDIN'),
       '36': ('RXD0/IO44', 'I2S_MCLK_M'), '37': ('TXD0/IO43', 'ESP_TXD'),
       '10': ('IO17', 'BTN_LEFT'), '11': ('IO18', 'BTN_RIGHT'), '23': ('IO21', 'BTN_DART_L'), '31': ('IO38', 'BTN_DART_R'),
       '13': ('IO19', 'USB_DN'), '14': ('IO20', 'USB_DP'), '27': ('IO0', 'BOOT'),
       '32': ('IO39', None), '16': ('IO46', None), '17': ('IO9', None), '18': ('IO10', None), '19': ('IO11', None),
       '24': ('IO47', None), '25': ('IO48', None), '26': ('IO45', None), '28': ('IO35', None), '29': ('IO36', None),
       '30': ('IO37', None), '33': ('IO40', None), '34': ('IO41', None), '35': ('IO42', None)}
part('U1', 'ESP32-S3-WROOM-1-N16R8', 'RF_Module:ESP32-S3-WROOM-1', 'ESP32', ESP, lcsc='C2913202',
     note='IO39 open = the SLIM model strap; 35-37 are the module\'s octal PSRAM, never used here')
C('C10', '10uF', 'VCC3V3', 'GND', 'ESP32', C0603); C('C11', '100nF', 'VCC3V3', 'GND', 'ESP32')
R('R14', '10k', 'VCC3V3', 'ESP_EN', 'ESP32'); C('C19', '1uF', 'ESP_EN', 'GND', 'ESP32', note='Espressif module guide: 1uF (REF 100nF)')
R('R15', '10k', 'VCC3V3', 'BOOT', 'ESP32'); C('C18', '100nF', 'BOOT', 'GND', 'ESP32')
part('SW6', 'RESET', 'Button_Switch_SMD:SW_SPST_TL3342', 'ESP32', {'1': ('1', 'ESP_EN'), '2': ('2', 'GND')}, note='pin hole in the side')
part('SW7', 'BOOT', 'Button_Switch_SMD:SW_SPST_TL3342', 'ESP32', {'1': ('1', 'BOOT'), '2': ('2', 'GND')}, note='pin hole in the side')
part('TP1', 'TXD', 'TestPoint:TestPoint_Pad_D1.0mm', 'ESP32', {'1': ('1', 'ESP_TXD')})

# ---- the four game keys (the SLIM's TS-1187A, under the caps) ------------------------------------------------------------
for ref, net in (('SW1', 'BTN_LEFT'), ('SW2', 'BTN_RIGHT'), ('SW3', 'BTN_DART_L'), ('SW4', 'BTN_DART_R')):
    part(ref, 'TS-1187A', 'STRUTHIO:TS-1187A-B-A-B', 'KEYS', {'A': ('A', net), 'D': ('D', 'GND'), 'B': ('B', None), 'C': ('C', None)},
         lcsc='C318884', note='diagonal pads A/D, as on the SLIM board')

# ---- panel: 40-pin 0.5 mm FPC (REF L1 pinout) + backlight (REF R3, R4, T1, R8) ------------------------------------------
FPC = {'1': ('GND', 'GND'), '2': ('TP_INT', 'TP_INT'), '3': ('TP_SDA', 'I2C_SDA'), '4': ('TP_SCL', 'I2C_SCL'), '5': ('VCC3V3', 'VCC3V3'),
       '6': ('GND', 'GND'), '7': ('TE', None), '8': ('CS', 'LCD_CS'), '9': ('QSPI_SCLK', 'LCD_CLK'), '10': ('QSPI_IO0', 'LCD_D0'),
       '11': ('QSPI_IO1', 'LCD_D1'), '12': ('RS', None), '13': ('QSPI_IO2', 'LCD_D2'), '14': ('HS/DC', None), '15': ('PCLK/RD', None),
       '16': ('QSPI_IO3', 'LCD_D3'), '17': ('RESET', 'LCD_RST'), '18': ('GND', 'GND'),
       '35': ('LEDA', 'LEDA'), '36': ('LEDK', 'LEDK'), '37': ('IM0', 'IM0'), '38': ('IM1', 'IM1'), '39': ('IM2', 'IM2'), '40': ('IM3', 'IM3'),
       'MP': ('MP', 'GND')}
for n in range(19, 35): FPC[str(n)] = (f'DB{n - 19}', None)
part('J1', 'PANEL 40P 0.5mm', 'Connector_FFC-FPC:Hirose_FH12-40S-0.5SH_1x40-1MP_P0.50mm_Horizontal', 'PANEL', FPC,
     lcsc='C54563269', note='flip-lock, bottom contact, 2.0 mm: CONFIRM contact side and footprint against the panel drawing')
R('R57', '10k', 'IM0', 'GND', 'PANEL'); R('R58', '10k', 'IM1', 'VCC3V3', 'PANEL')
R('R59', '10k', 'IM2', 'GND', 'PANEL'); R('R60', '10k', 'IM3', 'VCC3V3', 'PANEL')
R('R11', '10k', 'VCC3V3', 'LCD_RST', 'PANEL'); C('C8', '100nF', 'LCD_RST', 'GND', 'PANEL')
R('R16', '10k', 'LCD_CS', 'GND', 'PANEL', note='as REF')
R('R90', '0R', 'LCD_CLK_M', 'LCD_CLK', 'PANEL', note='REF LRC1 (a bead): 0R footprint, fit a bead if the clock rings')
C('C91', '10pF', 'LCD_CLK', 'GND', 'PANEL')
R('R3', '6.8R', 'VCC3V3', 'LEDA', 'PANEL', P0603); R('R4', '0R', 'LEDK', 'BL_D', 'PANEL')
part('Q1', 'AO3400A', 'Package_TO_SOT_SMD:SOT-23', 'PANEL', {'1': ('G', 'BL_G'), '2': ('S', 'GND'), '3': ('D', 'BL_D')}, lcsc='C20917')
R('R8', '1k', 'LCD_BL', 'BL_G', 'PANEL'); R('R67', '100k', 'BL_G', 'GND', 'PANEL', note='REF NC: fitted, backlight off until the firmware drives it')

# ---- I/O expander TCA9554 at 0x20 (REF U5) -------------------------------------------------------------------------------
part('U5', 'TCA9554PWR', 'Package_SO:TSSOP-16_4.4x5mm_P0.65mm', 'IOEXP', {
    '1': ('A0', 'GND'), '2': ('A1', 'GND'), '3': ('A2', 'GND'), '4': ('P0', None), '5': ('P1', 'LCD_RST'), '6': ('P2', 'TP_INT'),
    '7': ('P3', None), '8': ('GND', 'GND'), '9': ('P4', None), '10': ('P5', 'AXP_IRQ'), '11': ('P6', 'SYS_OUT'), '12': ('P7', 'PA_CTRL'),
    '13': ('INT', 'EXP_INT'), '14': ('SCL', 'I2C_SCL'), '15': ('SDA', 'I2C_SDA'), '16': ('VCC', 'VCC3V3')}, lcsc='C477924')
C('C37', '100nF', 'VCC3V3', 'GND', 'IOEXP'); R('R36', '10k', 'VCC3V3', 'EXP_INT', 'IOEXP', note='REF R35')

# ---- audio: ES8311 (REF U7) -> NS4150B (REF U6) -> speaker (REF J9) -------------------------------------------------------
part('U3', 'ES8311', 'Package_DFN_QFN:QFN-20-1EP_3x3mm_P0.4mm_EP1.65x1.65mm', 'AUDIO', {
    '1': ('CCLK', 'I2C_SCL'), '2': ('MCLK', 'I2S_MCLK'), '3': ('PVDD', 'AVCC'), '4': ('DVDD', 'AVCC'), '5': ('DGND', 'GND'),
    '6': ('SCLK', 'I2S_SCLK'), '7': ('ASDOUT', 'I2S_ASDOUT'), '8': ('LRCK', 'I2S_LRCK'), '9': ('DSDIN', 'I2S_DSDIN'), '10': ('AGND', 'GND'),
    '11': ('AVDD', 'AVDD'), '12': ('OUTP', 'COD_P'), '13': ('OUTN', 'COD_N'), '14': ('DACVREF', 'DACVREF'), '15': ('ADCVREF', 'ADCVREF'),
    '16': ('VMID', 'COD_VMID'), '17': ('MIC1N', None), '18': ('MIC1P', None), '19': ('CDATA', 'I2C_SDA'), '20': ('CE', 'GND'),
    '21': ('EP', 'GND')}, lcsc='C962342', note='no microphone (REF MIC1 left off)')
R('R50', '0R', 'LVCC3V3', 'AVCC', 'AUDIO'); C('C58', '10uF', 'AVCC', 'GND', 'AUDIO', C0603); C('C59', '100nF', 'AVCC', 'GND', 'AUDIO')
R('R54', '0R', 'LVCC3V3', 'AVDD', 'AUDIO'); C('C60', '1uF', 'AVDD', 'GND', 'AUDIO')
R('R61', '0R', 'I2S_MCLK_M', 'I2S_MCLK', 'AUDIO'); R('R68', '0R', 'I2S_SCLK_M', 'I2S_SCLK', 'AUDIO')
C('C64', '22pF', 'I2S_SCLK', 'GND', 'AUDIO'); C('C65', '22pF', 'I2S_LRCK', 'GND', 'AUDIO')
C('C53', '1uF', 'COD_VMID', 'GND', 'AUDIO'); C('C54', '1uF', 'ADCVREF', 'GND', 'AUDIO'); C('C55', '1uF', 'DACVREF', 'GND', 'AUDIO')
C('C61', '22pF', 'COD_P', 'GND', 'AUDIO'); C('C62', '22pF', 'COD_N', 'GND', 'AUDIO')
C('C57', '1uF', 'COD_P', 'PA_INP', 'AUDIO'); C('C56', '1uF', 'COD_N', 'PA_INN', 'AUDIO')
part('U4', 'NS4150B', 'Package_SO:MSOP-8_3x3mm_P0.65mm', 'AUDIO', {
    '1': ('CTRL', 'PA_CTRL'), '2': ('BYPASS', 'PA_BYP'), '3': ('IN+', 'PA_IP'), '4': ('IN-', 'PA_IN'),
    '5': ('OUT-', 'SPK_N'), '6': ('VDD', 'VSYS'), '7': ('GND', 'GND'), '8': ('OUT+', 'SPK_P')}, lcsc='C189961')
R('R45', '10k', 'VSYS', 'PA_CTRL', 'AUDIO', note='keeps the amp on: the firmware never drives P7')
C('C45', '1uF', 'PA_BYP', 'GND', 'AUDIO')
C('C48', '100nF', 'PA_INP', 'PA_IP1', 'AUDIO'); R('R48', '150k', 'PA_IP1', 'PA_IP', 'AUDIO')
C('C49', '100nF', 'PA_INN', 'PA_IN1', 'AUDIO'); R('R49', '150k', 'PA_IN1', 'PA_IN', 'AUDIO')
C('C50', '100nF', 'VSYS', 'GND', 'AUDIO'); C('C51', '1uF', 'VSYS', 'GND', 'AUDIO'); C('C52', '10uF', 'VSYS', 'GND', 'AUDIO', C0603)
part('J4', 'SPEAKER', 'Connector_Molex:Molex_PicoBlade_53261-0271_1x02-1MP_P1.25mm_Horizontal', 'AUDIO',
     {'1': ('1', 'SPK_P'), '2': ('2', 'SPK_N'), 'MP': ('MP', None)}, note='1.25 mm 2-pin: the plug-in speaker\'s plug; LCSC to pick')

# ---------------------------------------------------------------------------------------------------------------------------
def nets():
    n = defaultdict(list)
    for p in PARTS:
        for num, (name, net) in p['pins'].items():
            if net: n[net].append((p['ref'], num, name))
    return n

if __name__ == '__main__':
    n = nets()
    single = {k: v for k, v in n.items() if len(v) < 2}
    for k in sorted(n): print(f'{k:12s} {len(n[k]):3d}  ' + ' '.join(f'{r}.{p}' for r, p, _ in n[k][:12]) + (' ...' if len(n[k]) > 12 else ''))
    print(f'\n{len(PARTS)} parts, {len(n)} nets; nets with one pin: {sorted(single) or "none"}')
    refs = [p['ref'] for p in PARTS]
    dup = {r for r in refs if refs.count(r) > 1}
    print('duplicate refs:', sorted(dup) or 'none')
