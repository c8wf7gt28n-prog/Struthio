"""ARC-1 Compact R08 -- part (symbol) definitions for the generated KiCad schematic.

Every pin list is transcribed from a manufacturer document recorded in
R08_WORK/sources/*/sources.json (URL + SHA-256), or from the KiCad standard
library symbol named in `src`. Pin electrical types drive KiCad ERC.

Footprints: `fp` names either a KiCad 9 standard-library footprint
(LIB:NAME) or a generated/copied footprint in ARC1_R08.pretty (ARC1_R08:NAME).
`fp_status` is one of
  STD_LIB            KiCad library footprint for exactly this package
  GENERATED_DERIVED  generated here from datasheet dimensions (R09 must check vs drawing)
  SLIM4_CANDIDATE    copied from the SLIM4 R26 production library; re-validation required
  PLACEHOLDER        no verified land pattern yet (R09 blocker)
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "..", "sources"))

# electrical types (KiCad): input output bidirectional tri_state passive free
# unspecified power_in power_out open_collector open_emitter no_connect


class Part:
    def __init__(self, key, prefix, pins, fp, fp_status, mpn, mfr, desc, src, value=None,
                 lcsc="", datasheet="", evidence="VERIFIED_BY_VENDOR_DOC", small=False):
        self.key = key
        self.prefix = prefix
        self.pins = pins          # list of (number, name, etype, side) side in L/R
        self.fp = fp
        self.fp_status = fp_status
        self.mpn = mpn
        self.mfr = mfr
        self.desc = desc
        self.src = src
        self.value = value or mpn
        self.lcsc = lcsc
        self.datasheet = datasheet
        self.evidence = evidence
        self.small = small        # 2-pin passive drawing


def two_pin(key, prefix, fp, desc, value="", mpn="", mfr="", lcsc="", fp_status="STD_LIB", etype="passive"):
    return Part(key, prefix, [("1", "~", etype, "L"), ("2", "~", etype, "R")], fp, fp_status, mpn, mfr, desc,
                "generic two-terminal", value=value, lcsc=lcsc, small=True)


def side_split(pins):
    """assign L/R: first half left, second half right (keeps listed order)"""
    n = len(pins)
    out = []
    for i, p in enumerate(pins):
        out.append((p[0], p[1], p[2], "L" if i < (n + 1) // 2 else "R"))
    return out


# ---------------------------------------------------------------- F133-B
def f133_pins():
    rows = list(csv.DictReader(open(os.path.join(SRC, "f133", "f133_elqfp128_all_pins.csv"))))
    pins = []
    for r in rows:
        num, name, typ = r["pin_number"], r["pin_name"], r["type"]
        if num == "EPAD":
            pins.append(("129", "EPAD", "passive"))
            continue
        if typ == "power":
            et = "power_out" if name in ("LDOA-OUT", "LDOB-OUT") else "power_in"
        elif typ == "ground":
            et = "power_in"
        elif typ == "NC":
            et = "passive" if num == "47" else "no_connect"   # pin 47: optional DZQ resistor (OPEN)
        elif name == "RESET":
            et = "input"
        elif name == "DXIN":
            et = "input"
        elif name == "DXOUT":
            et = "output"
        elif typ.startswith("I/O"):
            et = "bidirectional"
        else:
            et = "passive"      # analog pins
        pins.append((num, name, et))
    assert len(pins) == 129, len(pins)
    # left: pins 1..64, right: 65..129 (package order keeps the drawing readable)
    return [(p[0], p[1], p[2], "L" if int(p[0]) <= 64 else "R") for p in pins]


# ---------------------------------------------------------------- T35F400C3
def t35_pins():
    rows = list(csv.DictReader(open(os.path.join(SRC, "efinix", "t35f400_balls_by_rail.csv"))))
    pins = []
    for r in rows:
        ball, name, func = r["ball"], r["name"], r["rail_or_function"]
        if func.startswith("GND"):
            et = "power_in"
        elif func.split(";")[0] in ("VCC", "VCCA_BL", "VCCA_BR", "VCCA_TR") or func.startswith("VCCIO"):
            et = "power_in"
        elif "VREF" in name or func.startswith("REF_RES"):
            et = "passive"
        elif func.startswith("CONFIG_DEDICATED_CDONE"):
            et = "open_collector"
        elif func.startswith("CONFIG_DEDICATED_CRESET_N"):
            et = "input"
        else:
            et = "bidirectional"
        pins.append((ball, name, et))
    assert len(pins) == 400, len(pins)

    def key(p):
        b = p[0]
        return (b[0], int(b[1:]))
    pins.sort(key=key)
    return side_split(pins)


def mn820_receptacle_pins():
    rows = list(csv.DictReader(open(os.path.join(SRC, "mn820", "mn820_cn1_pins.csv"))))
    pins = [(r["pin"], r["name"], "passive") for r in rows]
    assert len(pins) == 100
    return [(p[0], p[1], p[2], "L" if int(p[0]) % 2 == 1 else "R") for p in pins]


def P(*items):
    return side_split(list(items))


PARTS = {}


def add(p):
    PARTS[p.key] = p
    return p


add(Part("F133", "U", f133_pins(), "ARC1_R08:Allwinner_F133_eLQFP128_14x14_P0.4_EP5.72", "GENERATED_DERIVED",
         "F133-B", "Allwinner", "RISC-V C906 SoC, 64 MiB DDR2 in package, eLQFP128",
         "F133 Datasheet rev 2.3 Table 4-1/4-2 (sources/f133)"))
add(Part("T35", "U", t35_pins(), "ARC1_R08:Efinix_FBGA400_17x17_P0.8_GRID20", "GENERATED_DERIVED",
         "T35F400C3", "Efinix", "Trion T35 FPGA, 400-ball FBGA",
         "T35 DS v3.2 + T35-PINOUT v1.5 (sources/efinix/t35f400_balls_by_rail.csv)"))
add(Part("MN820_RCPT", "J", mn820_receptacle_pins(), "ARC1_R08:Hirose_DF40C-100DS-0.4V_51", "GENERATED_DERIVED",
         "DF40C-100DS-0.4V(51)", "Hirose", "100-pin 0.4 mm receptacle mating MN820 CN1 (1.5 mm stack)",
         "MN820 DS v1.0 Table 2; VM820C DS v1.1 CN6; Hirose DF40 catalog (sources/mn820)"))
add(Part("W25Q256JVFIQ", "U", P(("1", "IO3", "bidirectional"), ("2", "VCC", "power_in"), ("3", "~{RESET}", "input"),
                                ("4", "NC", "no_connect"), ("5", "NC", "no_connect"), ("6", "NC", "no_connect"),
                                ("7", "~{CS}", "input"), ("8", "DO_IO1", "tri_state"), ("9", "IO2", "bidirectional"),
                                ("10", "GND", "power_in"), ("11", "NC", "no_connect"), ("12", "NC", "no_connect"),
                                ("13", "NC", "no_connect"), ("14", "NC", "no_connect"), ("15", "DI_IO0", "bidirectional"),
                                ("16", "CLK", "input")),
         "Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm", "STD_LIB", "W25Q256JVFIQ", "Winbond",
         "256 Mbit (32 MiB) SPI NOR, SOIC-16 300 mil, dedicated /RESET, QE=1 fixed (IQ)",
         "W25Q256JV DS Rev I s.3.4 (sources/glue)"))
add(Part("W25Q32JVSSIQ", "U", P(("1", "~{CS}", "input"), ("2", "DO_IO1", "tri_state"), ("3", "IO2", "bidirectional"),
                                ("4", "GND", "power_in"), ("5", "DI_IO0", "bidirectional"), ("6", "CLK", "input"),
                                ("7", "IO3", "bidirectional"), ("8", "VCC", "power_in")),
         "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", "STD_LIB", "W25Q32JVSSIQ", "Winbond",
         "32 Mbit SPI NOR, T35 configuration flash (bitstream 8,139,168 bits)", "W25Q32JV DS s.3.1 (sources/glue)"))
add(Part("APS6404L", "U", P(("1", "~{CE}", "input"), ("2", "SO_SIO1", "bidirectional"), ("3", "SIO2", "bidirectional"),
                            ("4", "VSS", "power_in"), ("5", "SI_SIO0", "bidirectional"), ("6", "SCLK", "input"),
                            ("7", "SIO3", "bidirectional"), ("8", "VDD", "power_in")),
         "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", "STD_LIB", "APS6404L-3SQR-SN", "AP Memory",
         "64 Mbit QSPI PSRAM, SOP-8 150 mil", "APS6404L DS Rev 2.7 s.3.1",
         evidence="VERIFIED_BY_VENDOR_DOC (ordering suffix -SN to confirm)"))
add(Part("LVC1G125", "U", P(("1", "~{OE}", "input"), ("2", "A", "input"), ("3", "GND", "power_in"),
                            ("4", "Y", "tri_state"), ("5", "VCC", "power_in")),
         "Package_TO_SOT_SMD:SOT-353_SC-70-5", "STD_LIB", "SN74LVC1G125DCKR", "Texas Instruments",
         "single bus buffer, 3-state, Ioff", "SN74LVC1G125 DS pin functions (sources/glue)"))
add(Part("LVC1G08", "U", P(("1", "A", "input"), ("2", "B", "input"), ("3", "GND", "power_in"),
                           ("4", "Y", "output"), ("5", "VCC", "power_in")),
         "Package_TO_SOT_SMD:SOT-353_SC-70-5", "STD_LIB", "SN74LVC1G08DCKR", "Texas Instruments",
         "single 2-input AND, Ioff", "SN74LVC1G08 DS (pinout = TI standard 1G08 DCK; NOT in sources/glue -> R09 verify)",
         evidence="DERIVED (pinout not yet transcribed from its datasheet)"))
add(Part("LVC1G17", "U", P(("1", "NC", "no_connect"), ("2", "A", "input"), ("3", "GND", "power_in"),
                           ("4", "Y", "output"), ("5", "VCC", "power_in")),
         "Package_TO_SOT_SMD:SOT-353_SC-70-5", "STD_LIB", "SN74LVC1G17DCKR", "Texas Instruments",
         "single Schmitt-trigger buffer, Ioff", "SN74LVC1G17 DS (pinout = TI standard 1G17 DCK; R09 verify)",
         evidence="DERIVED (pinout not yet transcribed from its datasheet)"))
add(Part("LVC07A", "U", P(("1", "1A", "input"), ("2", "1Y", "open_collector"), ("3", "2A", "input"),
                          ("4", "2Y", "open_collector"), ("5", "3A", "input"), ("6", "3Y", "open_collector"),
                          ("7", "GND", "power_in"), ("8", "4Y", "open_collector"), ("9", "4A", "input"),
                          ("10", "5Y", "open_collector"), ("11", "5A", "input"), ("12", "6Y", "open_collector"),
                          ("13", "6A", "input"), ("14", "VCC", "power_in")),
         "Package_SO:TSSOP-14_4.4x5mm_P0.65mm", "STD_LIB", "SN74LVC07APWR", "Texas Instruments",
         "hex open-drain buffer, Ioff", "SN74LVC07A DS s.5 (sources/glue)"))
add(Part("TPS22918", "U", P(("1", "VIN", "power_in"), ("2", "GND", "power_in"), ("3", "ON", "input"),
                            ("4", "CT", "passive"), ("5", "QOD", "passive"), ("6", "VOUT", "power_out")),
         "Package_TO_SOT_SMD:SOT-23-6", "STD_LIB", "TPS22918DBVR", "Texas Instruments",
         "5.5 V 2 A load switch, quick output discharge (body diode VOUT->VIN!)", "TPS22918 DS s.5 (sources/glue)"))
add(Part("TPS3808", "U", P(("1", "~{RESET}", "open_collector"), ("2", "GND", "power_in"), ("3", "~{MR}", "input"),
                           ("4", "CT", "passive"), ("5", "SENSE", "input"), ("6", "VDD", "power_in")),
         "Package_TO_SOT_SMD:SOT-23-6", "STD_LIB", "TPS3808GxxDBVR", "Texas Instruments",
         "voltage supervisor, open-drain RESET#, programmable delay", "TPS3808 DS Table 5-1 (sources/glue)"))
add(Part("TLV62569", "U", P(("1", "EN", "input"), ("2", "GND", "power_in"), ("3", "SW", "power_out"),
                            ("4", "VIN", "power_in"), ("5", "FB", "input")),
         "Package_TO_SOT_SMD:SOT-23-5", "STD_LIB", "TLV62569DBVR", "Texas Instruments",
         "2 A synchronous buck, SOT-23-5", "TLV62569 DS s.5 (sources/glue)", lcsc="C141836"))
add(Part("TLV62569P", "U", P(("1", "EN", "input"), ("2", "GND", "power_in"), ("3", "SW", "power_out"),
                             ("4", "VIN", "power_in"), ("5", "PG", "open_collector"), ("6", "FB", "input")),
         "Package_TO_SOT_SMD:SOT-23-6", "STD_LIB", "TLV62569PDDCR", "Texas Instruments",
         "2 A synchronous buck with power-good, SOT-23-6 (DDC)", "TLV62569 DS s.5 (sources/glue)",
         evidence="VERIFIED_BY_VENDOR_DOC (DDC is a thin SOT-23-6: confirm land pattern in R09)"))
add(Part("TLV75518P", "U", P(("1", "IN", "power_in"), ("2", "GND", "power_in"), ("3", "EN", "input"),
                             ("4", "NC", "no_connect"), ("5", "OUT", "power_out")),
         "Package_TO_SOT_SMD:SOT-23-5", "STD_LIB", "TLV75518PDBVR", "Texas Instruments",
         "500 mA LDO 1.8 V", "TLV755P DS Table 4-1 (sources/glue)", lcsc="C2877863"))
add(Part("TUSB320LAI", "U", P(("1", "CC1", "bidirectional"), ("2", "CC2", "bidirectional"), ("3", "PORT", "input"),
                              ("4", "VBUS_DET", "input"), ("5", "ADDR", "input"), ("6", "INT_N_OUT3", "open_collector"),
                              ("7", "SDA_OUT1", "open_collector"), ("8", "SCL_OUT2", "open_collector"),
                              ("9", "ID", "open_collector"), ("10", "GND", "power_in"), ("11", "~{EN}", "input"),
                              ("12", "VDD", "power_in")),
         "ARC1_R08:SLIM4_FP_U13_TUSB320LAI_RWB_X2QFN12", "SLIM4_CANDIDATE", "TUSB320LAIRWBR", "Texas Instruments",
         "USB Type-C CC controller, GPIO mode reports source current", "TUSB320LA DS s.5 (sources/glue)", lcsc="C132554"))
add(Part("TPD2EUSB30", "U", P(("1", "D+", "passive"), ("2", "D-", "passive"), ("3", "GND", "power_in")),
         "ARC1_R08:SLIM4_FP_U11_TPD2EUSB30_DRT3", "SLIM4_CANDIDATE", "TPD2EUSB30DRTR", "Texas Instruments",
         "2-channel USB ESD protection", "TPD2EUSB30 DS Table 5-1 (sources/glue)", lcsc="C97502"))
add(Part("USB_C", "J", P(("A1", "GND", "passive"), ("A4", "VBUS", "passive"), ("A5", "CC1", "bidirectional"),
                         ("A6", "D+", "bidirectional"), ("A7", "D-", "bidirectional"), ("A8", "SBU1", "bidirectional"),
                         ("A9", "VBUS", "passive"), ("A12", "GND", "passive"), ("B1", "GND", "passive"),
                         ("B4", "VBUS", "passive"), ("B5", "CC2", "bidirectional"), ("B6", "D+", "bidirectional"),
                         ("B7", "D-", "bidirectional"), ("B8", "SBU2", "bidirectional"), ("B9", "VBUS", "passive"),
                         ("B12", "GND", "passive"), ("S1", "SHIELD", "passive")),
         "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal", "STD_LIB",
         "USB4105-GF-A", "GCT", "USB Type-C receptacle, USB 2.0, 16P", "GCT USB4105 pinout (sources/glue); KiCad symbol USB_C_Receptacle_USB2.0_16P",
         lcsc="C5184243"))
add(Part("MICROSD", "J", P(("1", "DAT2", "bidirectional"), ("2", "DAT3_CD", "bidirectional"), ("3", "CMD", "bidirectional"),
                           ("4", "VDD", "passive"), ("5", "CLK", "passive"), ("6", "VSS", "passive"),
                           ("7", "DAT0", "bidirectional"), ("8", "DAT1", "bidirectional"), ("9", "DET_B", "passive"),
                           ("10", "DET_A", "passive"), ("11", "SHIELD", "passive")),
         "Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5", "STD_LIB", "DM3AT-SF-PEJM5", "Hirose",
         "microSD push-push socket with detect switch",
         "KiCad symbol Micro_SD_Card_Det_Hirose_DM3AT (pin map); Hirose DM3 catalog to be checked in R09",
         evidence="KICAD_LIBRARY (vendor drawing check in R09)"))
add(Part("MAX98357A", "U", P(("1", "DIN", "input"), ("2", "GAIN_SLOT", "passive"), ("3", "GND", "power_in"),
                             ("4", "SD_MODE", "input"), ("5", "NC", "no_connect"), ("6", "NC", "no_connect"),
                             ("7", "VDD", "power_in"), ("8", "VDD", "power_in"), ("9", "OUTP", "output"),
                             ("10", "OUTN", "output"), ("11", "GND", "power_in"), ("12", "NC", "no_connect"),
                             ("13", "NC", "no_connect"), ("14", "LRCLK", "input"), ("15", "GND", "power_in"),
                             ("16", "BCLK", "input"), ("17", "EP", "passive")),
         "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.45x1.45mm", "PLACEHOLDER", "MAX98357AETE+T", "Analog Devices",
         "I2S class-D mono amplifier, 3.2 W / 4 ohm at 5 V",
         "MAX98357A DS Rev 7 pin description (sources/glue); EP size not checked -> footprint PLACEHOLDER",
         lcsc="C910544"))
add(Part("OSC_3225", "X", P(("1", "OE", "input"), ("2", "GND", "power_in"), ("3", "OUT", "output"), ("4", "VDD", "power_in")),
         "Oscillator:Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm", "STD_LIB", "25 MHz 3.3 V CMOS XO 3225 (MPN TBD)",
         "TBD", "25 MHz oscillator for T35 PLLIN0", "generic 4-pin XO pinout; exact part R09", evidence="CANDIDATE"))
add(Part("XTAL_3225", "Y", P(("1", "X1", "passive"), ("2", "GND", "passive"), ("3", "X2", "passive"), ("4", "GND", "passive")),
         "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "STD_LIB", "24 MHz 3225 crystal CL=12 pF +-20 ppm (MPN TBD)", "TBD",
         "24 MHz F133 DCXO crystal", "F133 DS: fundamental, +-50 ppm (20 recommended), C0 6.5 pF", evidence="CANDIDATE"))
add(Part("SW_B3U", "SW", P(("1", "1", "passive"), ("2", "2", "passive")),
         "Button_Switch_SMD:SW_SPST_B3U-1000P", "STD_LIB", "B3U-1000P", "Omron", "tactile switch",
         "SLIM4 R26 BOM (C231329), KiCad footprint", lcsc="C231329"))
add(Part("LED", "D", [("1", "K", "passive", "L"), ("2", "A", "passive", "R")],
         "LED_SMD:LED_0603_1608Metric", "STD_LIB", "LED 0603 (MPN TBD)", "TBD", "indicator LED", "generic", small=True,
         evidence="CANDIDATE"))
add(Part("TVS_SMF", "D", [("1", "K", "passive", "L"), ("2", "A", "passive", "R")],
         "Diode_SMD:D_SMF", "STD_LIB", "SMF5.0A", "Littelfuse", "5 V TVS on VBUS", "SMF series DS (to be archived R09)",
         small=True, evidence="CANDIDATE"))
add(Part("SCHOTTKY", "D", [("1", "K", "passive", "L"), ("2", "A", "passive", "R")],
         "Diode_SMD:D_SOD-323", "STD_LIB", "BAT54WS", "TBD", "small Schottky (CDONE delay discharge)", "generic",
         small=True, evidence="CANDIDATE"))
add(Part("HDR_1x3", "J", P(("1", "1", "passive"), ("2", "2", "passive"), ("3", "3", "passive")),
         "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", "STD_LIB", "header 1x3 2.54 (DNP-able)", "generic",
         "UART header", "generic"))
add(Part("HDR_2x5_127", "J", P(*[(str(i), str(i), "passive") for i in range(1, 11)]),
         "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD", "STD_LIB", "header 2x5 1.27 SMD", "generic",
         "JTAG / logic-analyser header", "generic"))
add(Part("JST_PH2", "J", P(("1", "1", "passive"), ("2", "2", "passive"), ("MP", "MP", "passive")),
         "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", "STD_LIB", "S2B-PH-SM4-TB(LF)(SN)", "JST",
         "speaker connector", "SLIM4 R26 BOM (C295747)", lcsc="C295747"))
add(Part("TP", "TP", [("1", "1", "passive", "L")], "TestPoint:TestPoint_Pad_D1.0mm", "STD_LIB", "test pad", "-",
         "test point", "generic", small=True))
add(Part("MH", "H", [("1", "1", "passive", "L")], "MountingHole:MountingHole_2.7mm_M2.5_Pad", "STD_LIB", "M2.5 hole", "-",
         "mounting hole", "generic", small=True))
add(Part("MH_NPTH", "H", [], "MountingHole:MountingHole_2.7mm_M2.5", "STD_LIB", "M2.5 NPTH", "-",
         "MN820 module standoff hole (no electrical connection assumed)", "MN820 DS mechanical", small=True))
add(Part("FID", "FID", [], "Fiducial:Fiducial_1mm_Mask2mm", "STD_LIB", "fiducial", "-", "fiducial", "generic", small=True))

# passives: (key, prefix, footprint)
for k, pre, fp in [("R0402", "R", "Resistor_SMD:R_0402_1005Metric"), ("R0603", "R", "Resistor_SMD:R_0603_1608Metric"),
                   ("C0402", "C", "Capacitor_SMD:C_0402_1005Metric"), ("C0603", "C", "Capacitor_SMD:C_0603_1608Metric"),
                   ("C0805", "C", "Capacitor_SMD:C_0805_2012Metric"), ("FB0603", "FB", "Inductor_SMD:L_0603_1608Metric"),
                   ("F1206", "F", "Fuse:Fuse_1206_3216Metric"), ("L4035", "L", "ARC1_R08:SLIM4_FP_L2_ASWPA4035")]:
    add(two_pin(k, pre, fp, "passive " + k, fp_status="SLIM4_CANDIDATE" if "SLIM4" in fp else "STD_LIB"))

add(Part("PWR_FLAG", "#FLG", [("1", "pwr", "power_out", "L")], "", "STD_LIB", "", "", "ERC power flag", "KiCad convention",
         small=True))
