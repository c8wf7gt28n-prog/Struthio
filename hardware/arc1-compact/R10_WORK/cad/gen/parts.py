"""ARC-1 Compact R10 -- part (symbol) definitions for the generated KiCad schematic.

Reuses the R8.5-C part library (R85C_WORK/cad/gen/parts.py, frozen; read only) for the F133, the 45F, the glue logic,
regulators, passives and connectors, and adds the R10 devices. Every new pin list is transcribed from a manufacturer
document recorded in R10_WORK/sources/*/sources.json or R10_WORK/architecture/sources (URL + SHA-256).

Footprint status (as R8.5-C): STD_LIB, GENERATED_DERIVED (generated here from a package drawing), SLIM4_CANDIDATE,
PLACEHOLDER, plus STD_LIB_CANDIDATE (a KiCad library footprint whose package variant still has to be matched to the
vendor drawing before layout).
"""
import copy
import csv
import importlib.util
import os
import sys

sys.dont_write_bytecode = True          # never write caches into the frozen R85C tree

HERE = os.path.dirname(os.path.abspath(__file__))
R10 = os.path.normpath(os.path.join(HERE, "..", ".."))
R85C_GEN = os.path.normpath(os.path.join(R10, "..", "R85C_WORK", "cad", "gen", "parts.py"))
ASRC = os.path.join(R10, "architecture", "sources")
SRC = os.path.join(R10, "sources")
LIB = "ARC1_R10"

_spec = importlib.util.spec_from_file_location("parts_r85c", R85C_GEN)
_r85 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_r85)
Part, side_split, P, two_pin = _r85.Part, _r85.side_split, _r85.P, _r85.two_pin

PARTS = {}
_SKIP = {"MN820_RCPT", "MH_NPTH", "W25Q256JVFIQ", "APS6404L", "LVC1G08"}     # R8.5-C parts not on the R10 board
for k, p in _r85.PARTS.items():
    if k in _SKIP:
        continue
    q = copy.copy(p)
    q.fp = q.fp.replace("ARC1_R85:", LIB + ":")
    PARTS[k] = q


def add(p):
    assert p.key not in PARTS, p.key
    PARTS[p.key] = p
    return p


# ---------------------------------------------------------------- D213ECV (QFN128 + EPAD 129)
def d213_pins():
    """D21x HW guide V2.0 Table 2-5 / DS 5.2.3 (architecture/sources/d213ecv_pins.csv)."""
    rows = list(csv.DictReader(open(os.path.join(ASRC, "d213ecv_pins.csv"), encoding="utf-8")))
    pins = []
    for r in rows:
        num, name, typ = r["pin"], r["name_func1"], r["type"]
        if typ == "POWER":
            et = "power_out" if name in ("LDO1x", "LDO25", "VCC30_ANA") else "power_in"
            if name == "RTC_VCOIN":
                et = "passive"
        elif typ == "-":
            et = "no_connect"                      # pins 50/56: "floating, must not connect any signal"
        elif name == "RESETN" or name == "PLL_XI" or name == "RTC_XI":
            et = "input"
        elif name in ("PLL_XO", "RTC_XO"):
            et = "output"
        elif name == "RTC_IO":
            et = "open_collector"
        else:
            et = "bidirectional"
        pins.append((num, name, et))
    assert len(pins) == 129 and len({p[0] for p in pins}) == 129, len(pins)
    return [(p[0], p[1], p[2], "L" if int(p[0]) <= 64 else "R") for p in pins]


add(Part("D213ECV", "U", d213_pins(), f"{LIB}:ArtInChip_QFN-128-1EP_12.3x12.3mm_P0.35mm_EP7.0x7.0mm", "GENERATED_DERIVED",
         "D213ECV", "ArtInChip", "RISC-V display SoC, 128 MiB DDR3 in package (SiP), QFN128 12.3 mm 0.35 mm, EPAD = GND",
         "D21x HW guide V2.0 Table 2-5; D21x DS v1.4 Fig 5-6 (package); architecture/sources/d213ecv_pins.csv"))


# ---------------------------------------------------------------- LFE5U-12F-6TG144C
ECP5_DED = {"CCLK": "input", "CFG_0": "input", "CFG_1": "input", "CFG_2": "input", "PROGRAMN": "input",
            "INITN": "open_collector", "DONE": "open_collector", "TCK": "input", "TMS": "input", "TDI": "input",
            "TDO": "tri_state"}


def ecp5_12_pins():
    """Lattice FPGA-SC-02032 v2.1, TQFP144 column (architecture/sources/lfe5u12_tqfp144_pinout.csv)."""
    rows = list(csv.DictReader(open(os.path.join(ASRC, "lfe5u12_tqfp144_pinout.csv"))))
    pins = []
    for r in rows:
        num, fn, typ = r["pin"], r["pin_function"], r["pin_type"]
        if typ in ("GND", "power"):
            et = "power_in"
        elif typ == "NC":
            et = "no_connect"
        elif typ.startswith("config"):
            et = ECP5_DED[fn]
        else:
            et = "bidirectional"
        name = fn if r["dual_function"] in ("-", "") else f"{fn}/{r['dual_function'].split('/')[0]}"
        pins.append((num, name, et))
    assert len(pins) == 144 and len({p[0] for p in pins}) == 144, len(pins)
    return [(p[0], p[1], p[2], "L" if int(p[0]) <= 72 else "R") for p in sorted(pins, key=lambda x: int(x[0]))]


add(Part("ECP5_12F_TQ144", "U", ecp5_12_pins(), "Package_QFP:TQFP-144_20x20mm_P0.5mm", "STD_LIB",
         "LFE5U-12F-6TG144C", "Lattice", "ECP5 FPGA, 12K LUT, speed -6, commercial, TQFP144 20x20 mm 0.5 mm",
         "Lattice FPGA-DS-02012 v3.4 + pinout FPGA-SC-02032 v2.1 (architecture/sources)"))

# ---------------------------------------------------------------- memories
_NOR16 = P(("1", "IO3", "bidirectional"), ("2", "VCC", "power_in"), ("3", "~{RESET}", "input"),
           ("4", "NC", "no_connect"), ("5", "NC", "no_connect"), ("6", "NC", "no_connect"),
           ("7", "~{CS}", "input"), ("8", "DO_IO1", "tri_state"), ("9", "IO2", "bidirectional"),
           ("10", "GND", "power_in"), ("11", "NC", "no_connect"), ("12", "NC", "no_connect"),
           ("13", "NC", "no_connect"), ("14", "NC", "no_connect"), ("15", "DI_IO0", "bidirectional"),
           ("16", "CLK", "input"))
add(Part("W25Q512JVFIQ", "U", _NOR16, "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", "STD_LIB", "W25Q512JVFIQ", "Winbond",
         "512 Mbit (64 MiB) SPI NOR, SOIC-16 300 mil, dedicated /RESET (pin 3), QE=1 fixed (IQ)",
         "W25Q512JV DS Rev.B Figure 1b (hardware/gen_flash_pinmux.py; R10_INTERCONNECT_DECISIONS.md item 4)"))
add(Part("APS3204L", "U", P(("1", "~{CE}", "input"), ("2", "SO_SIO1", "bidirectional"), ("3", "SIO2", "bidirectional"),
                            ("4", "VSS", "power_in"), ("5", "SI_SIO0", "bidirectional"), ("6", "SCLK", "input"),
                            ("7", "SIO3", "bidirectional"), ("8", "VDD", "power_in")),
         "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "STD_LIB", "APS3204L-3SQNA-SN", "AP Memory",
         "32 Mbit (4 MiB) QSPI PSRAM, SOP-8 150 mil, 2.7-3.6 V (109 MHz max at 3.3 V)",
         "APS3204L-3SQNA-SN DS Rev 1.1 s3.1 (sources/apmemory)"))
_SD = {1: "VDD", 2: "DQ0", 3: "VDDQ", 4: "DQ1", 5: "DQ2", 6: "VSSQ", 7: "DQ3", 8: "DQ4", 9: "VDDQ", 10: "DQ5", 11: "DQ6",
       12: "VSSQ", 13: "DQ7", 14: "VDD", 15: "LDQM", 16: "~{WE}", 17: "~{CAS}", 18: "~{RAS}", 19: "~{CS}", 20: "BA0",
       21: "BA1", 22: "A10", 23: "A0", 24: "A1", 25: "A2", 26: "A3", 27: "VDD", 28: "VSS", 29: "A4", 30: "A5", 31: "A6",
       32: "A7", 33: "A8", 34: "A9", 35: "A11", 36: "A12", 37: "CKE", 38: "CLK", 39: "UDQM", 40: "NC", 41: "VSS",
       42: "DQ8", 43: "VDDQ", 44: "DQ9", 45: "DQ10", 46: "VSSQ", 47: "DQ11", 48: "DQ12", 49: "VDDQ", 50: "DQ13",
       51: "DQ14", 52: "VSSQ", 53: "DQ15", 54: "VSS"}


def _sd_et(n):
    if n.startswith("V"):
        return "power_in"
    if n == "NC":
        return "no_connect"
    return "bidirectional" if n.startswith("DQ") and "M" not in n else "input"


add(Part("AS4C16M16SA", "U", [(str(k), v, _sd_et(v), "L" if k <= 27 else "R") for k, v in sorted(_SD.items())],
         "Package_SO:TSOP-II-54_22.2x10.16mm_P0.8mm", "STD_LIB", "AS4C16M16SA-6TIN", "Alliance Memory",
         "256 Mbit (32 MiB) x16 SDR SDRAM, 166 MHz, industrial, TSOP-II 54",
         "Alliance AS4C16M16SA-C&I Rev 3.0 Figure 1 (same map as hardware/gen_flash_pinmux.py SDRAM_PINS)"))

# ---------------------------------------------------------------- video (decision D6)
def _csv_part(path, et_map):
    rows = list(csv.DictReader(open(path)))
    return [(r["pin"], r["name"], et_map[r["type"]]) for r in rows]


_ET = {"power": "power_in", "ground": "power_in", "output_diff": "output", "open_drain": "open_collector", "nc": "no_connect",
       "input": "input", "bidir": "bidirectional", "output": "output", "power_out": "power_out"}
_tfp = _csv_part(os.path.join(SRC, "ti", "tfp410_pap64_pins.csv"), _ET)
add(Part("TFP410", "U", [(n, nm, et, "L" if int(n) <= 32 else "R") for n, nm, et in _tfp],
         "Package_QFP:Texas_TQFP-64-1EP_10x10mm_P0.5mm_EP8x8mm_Mask4.44x4.44mm_ThermalVias", "STD_LIB_CANDIDATE",
         "TFP410PAP", "Texas Instruments", "DVI 1.0 transmitter, 25-165 MHz, 24-bit single-edge input, strap mode",
         "TI SLDS145D Figure 4-1 / Table 4-1 (sources/ti/tfp410_pap64_pins.csv); footprint = KiCad PAP0064M: confirm the "
         "PowerPAD size against the PAP0064 drawing orderable with TFP410PAP"))
_tpd = _csv_part(os.path.join(SRC, "ti", "tpd12s016_pw24_pins.csv"), _ET)
add(Part("TPD12S016", "U", side_split(_tpd), "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm", "STD_LIB", "TPD12S016PWR",
         "Texas Instruments", "HDMI companion: TMDS/DDC/CEC ESD, DDC + HPD level shift, 5 V load switch (55 mA)",
         "TI SLLSE96F Pin Functions, PW column (sources/ti/tpd12s016_pw24_pins.csv)"))
_HDMI = [("1", "D2+"), ("2", "D2S"), ("3", "D2-"), ("4", "D1+"), ("5", "D1S"), ("6", "D1-"), ("7", "D0+"), ("8", "D0S"),
         ("9", "D0-"), ("10", "CK+"), ("11", "CKS"), ("12", "CK-"), ("13", "CEC"), ("14", "UTILITY"), ("15", "SCL"),
         ("16", "SDA"), ("17", "DDC_GND"), ("18", "+5V"), ("19", "HPD"), ("SH", "SHIELD")]
add(Part("HDMI_A", "J", side_split([(n, nm, "passive") for n, nm in _HDMI]),
         "Connector_Video:HDMI_A_Molex_208658-1001_Horizontal", "STD_LIB", "2086581001", "Molex",
         "HDMI type-A receptacle, right angle", "HDMI 1.4 type-A contact assignment; KiCad footprint pads 1-19 + SH"))

# ---------------------------------------------------------------- USB path F133 USB1 host -> D213 USB0 (recovery mux)
add(Part("TS3USB221A", "U", P(("1", "1D+", "bidirectional"), ("2", "1D-", "bidirectional"), ("3", "2D+", "bidirectional"),
                              ("4", "2D-", "bidirectional"), ("5", "GND", "power_in"), ("6", "~{OE}", "input"),
                              ("7", "D-", "bidirectional"), ("8", "D+", "bidirectional"), ("9", "S", "input"),
                              ("10", "VCC", "power_in")),
         "Package_DFN_QFN:Texas_UQFN-10_1.5x2mm_P0.5mm", "STD_LIB", "TS3USB221ARSER", "Texas Instruments",
         "USB 2.0 HS 1:2 mux; S=L: D=1D, S=H: D=2D, OE#=H: all off", "TI SCDS277C Table 4-1 / 7-1 (sources/ti)"))
add(Part("LVC2G07", "U", P(("1", "1A", "input"), ("2", "GND", "power_in"), ("3", "2A", "input"), ("4", "2Y", "open_collector"),
                           ("5", "VCC", "power_in"), ("6", "1Y", "open_collector")),
         "Package_TO_SOT_SMD:SOT-23-6", "STD_LIB", "SN74LVC2G07DBVR", "Texas Instruments",
         "dual buffer, open-drain outputs, Ioff", "TI SCES308L DBV pin functions (sources/ti)"))

add(Part("HDR_1x2", "J", P(("1", "1", "passive"), ("2", "2", "passive")),
         "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", "STD_LIB", "header 1x2 2.54 + jumper", "generic",
         "jumper", "generic"))


# ================================================================ change order: ARC1_R10_Handoff rev 1.1 (2026-10-16)
# ---------------------------------------------------------------- HDMI with embedded audio (replaces the TFP410, D6 superseded)
_ADV = {1: "DVDD", 2: "VSYNC", 3: "SPDIF", 4: "MCLK", 5: "I2S0", 6: "I2S1", 7: "I2S2", 8: "I2S3", 9: "SCLK", 10: "LRCLK",
        11: "DVDD", 12: "PVDD", 13: "BGVDD", 14: "R_EXT", 15: "AVDD", 16: "HPD", 17: "TXC-", 18: "TXC+", 19: "AVDD",
        20: "TX0-", 21: "TX0+", 22: "PD", 23: "TX1-", 24: "TX1+", 25: "AVDD", 26: "TX2-", 27: "TX2+", 28: "INT",
        29: "DVDD_3V", 30: "CEC", 31: "DVDD", 32: "CEC_CLK", 33: "DDCSCL", 34: "DDCSDA", 35: "SCL", 36: "SDA", 51: "DVDD",
        53: "CLK", 63: "DE", 64: "HSYNC", 65: "EPAD_GND"}
for _p, _d in zip(list(range(37, 51)) + [52] + list(range(54, 63)), range(23, -1, -1)):
    _ADV[_p] = f"D{_d}"
assert sorted(_ADV) == list(range(1, 66))


def _adv_et(n):
    if n in ("DVDD", "PVDD", "BGVDD", "AVDD", "DVDD_3V", "EPAD_GND"):
        return "power_in"
    if n.startswith("TX"):
        return "output"
    if n in ("INT",):
        return "output"
    if n in ("CEC", "DDCSCL", "DDCSDA", "SDA", "SCL"):
        return "bidirectional"
    return "input"


add(Part("ADV7513", "U", [(str(k), v, _adv_et(v), "L" if k <= 32 else "R") for k, v in sorted(_ADV.items())],
         "Package_QFP:LQFP-64-1EP_10x10mm_P0.5mm_EP5x5mm_ThermalVias", "STD_LIB_CANDIDATE", "ADV7513BSWZ", "Analog Devices",
         "HDMI 1.4 transmitter, 165 MHz, 24-bit RGB input, I2S/S-PDIF audio embedding, LQFP-64 EP",
         "ADI ADV7513 DS Rev. B Figure 2 / Table 3 (sources/adi); EP 5.10-5.30 mm vs KiCad 5.0 mm land: confirm with SW-64-2"))

# ---------------------------------------------------------------- USB: hub + port power + front USB-A
add(Part("USB2422", "U", P(("1", "VDD33", "power_in"), ("2", "USBDM_DN1", "bidirectional"), ("3", "USBDP_DN1", "bidirectional"),
                           ("4", "USBDM_DN2", "bidirectional"), ("5", "USBDP_DN2", "bidirectional"), ("6", "NC", "no_connect"),
                           ("7", "PRTPWR1/BC_EN1", "output"), ("8", "OCS1_N", "input"), ("9", "VDD33", "power_in"),
                           ("10", "CRFILT", "passive"), ("11", "PRTPWR2", "output"), ("12", "OCS2_N", "input"),
                           ("13", "SMBDATA/NON_REM1", "bidirectional"), ("14", "SMBCLK/CFG_SEL0", "bidirectional"),
                           ("15", "RESET_N", "input"), ("16", "VBUS_DET", "input"),
                           ("17", "SUSP_IND/NON_REM0", "bidirectional"), ("18", "VDD33", "power_in"),
                           ("19", "USBDM_UP", "bidirectional"), ("20", "USBDP_UP", "bidirectional"),
                           ("21", "XTALOUT", "output"), ("22", "XTALIN", "input"), ("23", "PLLFILT", "passive"),
                           ("24", "RBIAS", "passive"), ("25", "VSS_EP", "power_in")),
         "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm_ThermalVias", "STD_LIB_CANDIDATE", "USB2422-I/MJ", "Microchip",
         "2-port USB 2.0 high-speed hub, strap-configured, 3.3 V, SQFN-24",
         "Microchip DS00001726A Figure 2.1 / Table 2.2 (sources/microchip); exposed-pad size to confirm with the MJ package drawing"))
add(Part("TPS2051C", "U", P(("1", "OUT", "power_out"), ("2", "GND", "power_in"), ("3", "~{FLT}", "open_collector"),
                            ("4", "EN", "input"), ("5", "IN", "power_in")),
         "Package_TO_SOT_SMD:SOT-23-5", "STD_LIB", "TPS2051CDBVR", "Texas Instruments",
         "USB port power switch, 0.5 A current limit, EN active high, fault flag", "TI SLVSAU6I Table 5-2 (sources/ti)"))
add(Part("USB_A", "J", P(("1", "VBUS", "passive"), ("2", "D-", "bidirectional"), ("3", "D+", "bidirectional"),
                         ("4", "GND", "passive"), ("5", "SHIELD", "passive")),
         "Connector_USB:USB_A_Molex_67643_Horizontal", "STD_LIB", "67643-0910", "Molex",
         "USB 2.0 type-A receptacle, right angle, through-hole shell (front panel)",
         "USB 2.0 type-A contact assignment; KiCad footprint pads 1-4 + 5 (shell); MPN variant to confirm with the drawing",
         evidence="CANDIDATE (orderable suffix to confirm)"))

# ---------------------------------------------------------------- eMMC (handoff s3), 153-FBGA 11.5 x 13
_EMMC_SIG = {"A3": "DAT0", "A4": "DAT1", "A5": "DAT2", "B2": "DAT3", "B3": "DAT4", "B4": "DAT5", "B5": "DAT6", "B6": "DAT7",
             "K5": "RST_N", "M5": "CMD", "M6": "CLK", "H5": "DS", "C2": "VDDI",
             **{b: "VCCQ" for b in ("C6", "M4", "N4", "P3", "P5")}, **{b: "VCC" for b in ("E6", "F5", "J10", "K9")},
             **{b: "VSS" for b in ("J5", "A6", "C4", "E7", "G5", "H10", "K8", "N2", "N5", "P4", "P6")}}


def _emmc_pins():
    fp = "/usr/share/kicad/footprints/Package_BGA.pretty/LFBGA-153_11.5x13mm_Layout14x14_P0.5mm.kicad_mod"
    import re as _re
    balls = sorted({m for m in _re.findall(r'\(pad "([A-Z]+\d+)"', open(fp).read())},
                   key=lambda b: (b.rstrip("0123456789"), int(b[len(b.rstrip("0123456789")):])))
    assert len(balls) == 153 and set(_EMMC_SIG) <= set(balls), (len(balls), set(_EMMC_SIG) - set(balls))
    out = []
    for b in balls:
        n = _EMMC_SIG.get(b, "NC")
        et = ("power_in" if n in ("VCCQ", "VCC", "VSS") else "passive" if n == "VDDI" else "no_connect" if n == "NC"
              else "input" if n in ("CLK", "RST_N") else "output" if n == "DS" else "bidirectional")
        out.append((b, n, et))
    return side_split(out)


add(Part("EMMC_KLMAG1JETD", "U", _emmc_pins(), "Package_BGA:LFBGA-153_11.5x13mm_Layout14x14_P0.5mm", "STD_LIB",
         "KLMAG1JETD-B041", "Samsung", "16 GB eMMC 5.1, 153-FBGA 11.5x13x0.8 mm (JEDEC ball map), VCCQ 2.7-3.6 V used",
         "Samsung KLMxGxJETD-B041 DS Rev 1.0 Table 2 (sources/samsung); NC/RFU balls left unconnected"))
add(Part("PADS_1x4", "J", P(("1", "1", "passive"), ("2", "2", "passive"), ("3", "3", "passive"), ("4", "4", "passive")),
         "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", "STD_LIB", "internal service pads (not populated)",
         "generic", "internal fixture pads", "generic"))
add(Part("PADS_1x2", "J", P(("1", "1", "passive"), ("2", "2", "passive")),
         "TestPoint:TestPoint_2Pads_Pitch2.54mm_Drill0.8mm", "STD_LIB", "internal service pad pair", "generic",
         "internal fixture pad pair (replaces a user-facing switch)", "generic"))
add(two_pin("C1210", "C", "Capacitor_SMD:C_1210_3225Metric", "passive C1210"))
