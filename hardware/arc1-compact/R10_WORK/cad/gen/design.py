"""ARC-1 Compact R10 -- the board as code: components, values and nets per sheet.

Single electrical source for the R10 schematic. gen_kicad.py turns it into the native KiCad 9 hierarchical schematic and
board/r10_board_plan.json. Baseline: R85C_WORK/cad/gen/design.py (frozen); R10 deltas: hardware/R10_change_sheet.md,
hardware/R10_INTERCONNECT_DECISIONS.md and DECISIONS.md D1-D7.

Pin assignments of the inter-chip links are NOT typed here: they are read from the generated pin plans
(architecture/R10_interface_matrix.csv, hardware/R10_flash_pinmux.csv) so the schematic, LPFs and firmware share one
source. Status: SELECTED_UNVERIFIED engineering capture. No board exists. Fabrication HOLD.
"""
import csv
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parts import PARTS, R10   # noqa: E402

SLIM4_PASSIVES = {
    ("C0402", "100nF"): ("CL05B104KO5NNNC", "Samsung", "C1525"),
    ("C0402", "10nF"): ("CL05B103KB5NNNC", "Samsung", "C15195"),
    ("C0402", "1uF"): ("CL05A105KA5NQNC", "Samsung", "C52923"),
    ("C0402", "220nF"): ("CL05B224KO5NNNC", "Samsung", "C16772"),
    ("C0402", "12pF"): ("0402CG120J500NT", "FH", "C1547"),
    ("C0603", "4.7uF"): ("CL10A475KO8NNNC", "Samsung", "C19666"),
    ("C0603", "10uF"): ("CL10A106KP8NNNC", "Samsung", "C19702"),
    ("C0603", "1uF"): ("CL10A105KB8NNNC", "Samsung", "C15849"),
    ("C0805", "10uF"): ("CL21A106KAYNNNE", "Samsung", "C15850"),
    ("C0805", "22uF"): ("CL21A226MQQNNNE", "Samsung", "C5674"),
    ("R0402", "10k"): ("0402WGF1002TCE", "UNI-ROYAL", "C25744"),
    ("R0402", "100k"): ("0402WGF1003TCE", "UNI-ROYAL", "C25741"),
    ("R0402", "0R"): ("0402WGF0000TCE", "UNI-ROYAL", "C17168"),
    ("R0402", "4.7k"): ("0402WGF4701TCE", "UNI-ROYAL", "C25900"),
    ("R0402", "1k"): ("0402WGF1001TCE", "UNI-ROYAL", "C11702"),
    ("R0402", "22R"): ("0402WGF220JTCE", "UNI-ROYAL", "C25092"),
    ("R0402", "33R"): ("0402WGF330JTCE", "UNI-ROYAL", "C25105"),
    ("L4035", "2.2uH"): ("ASWPA4035S2R2MT", "Sunlord", "C340207"),
}


class Comp:
    def __init__(self, ref, part, value, conn, sheet, mpn=None, note="", dnp=False, lcsc=None, mfr=None):
        self.ref, self.part, self.value, self.conn, self.sheet = ref, part, value, conn, sheet
        p = PARTS[part]
        sl = SLIM4_PASSIVES.get((part, value))
        self.mpn = mpn or (sl[0] if sl else (p.mpn if not p.small or part in ("LED", "TVS_SMF", "SCHOTTKY", "SW_B3U") else ""))
        self.mfr = mfr or (sl[1] if sl else p.mfr)
        self.lcsc = lcsc if lcsc is not None else (sl[2] if sl else p.lcsc)
        self.note, self.dnp = note, dnp
        self.slim4 = bool(sl)


class Design:
    def __init__(self):
        self.comps = []
        self.sheets = []
        self.cur = None
        self.counters = {}
        self.intent_nc = {}

    def sheet(self, name, file, title):
        self.sheets.append((name, file, title))
        self.cur = name

    def add(self, ref, part, value, conn, **kw):
        assert all(c.ref != ref for c in self.comps), ref
        nums = {x[0] for x in PARTS[part].pins}
        for k in conn:
            assert k in nums, (ref, part, k)
        c = Comp(ref, part, value, conn, self.cur, **kw)
        self.comps.append(c)
        return c

    def auto(self, prefix):
        n = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = n
        return f"{prefix}{n}"

    def U(self, part, value, conn, **kw):
        return self.add(self.auto(PARTS[part].prefix), part, value, conn, **kw)

    def R(self, value, a, b, pkg="R0402", note="", dnp=False):
        return self.add(self.auto("R"), pkg, value, {"1": a, "2": b}, note=note, dnp=dnp)

    def C(self, value, a, b="GND", pkg=None, note="", dnp=False):
        pkg = pkg or ("C0805" if value in ("22uF",) else "C0603" if value in ("4.7uF", "10uF", "2.2uF") else "C0402")
        return self.add(self.auto("C"), pkg, value, {"1": a, "2": b}, note=note, dnp=dnp)

    def decouple(self, net, n=1, value="100nF"):
        for _ in range(n):
            self.C(value, net)

    def flag(self, net):
        self.add(self.auto("#FLG"), "PWR_FLAG", "PWR_FLAG", {"1": net})

    def tp(self, net, note=""):
        self.add(self.auto("TP"), "TP", net, {"1": net}, note=note)

    def nc(self, ref, pin, why):
        self.intent_nc[(ref, pin)] = why


# ------------------------------------------------------------------ pin plans (single source)
def _rows(path):
    return list(csv.DictReader(open(os.path.join(R10, path))))


MATRIX = _rows("architecture/R10_interface_matrix.csv")
PINMUX = _rows("hardware/R10_flash_pinmux.csv")


def pm(group, chip=None):
    return [r for r in PINMUX if r["group"] == group and (chip is None or r["chip"].startswith(chip))]


def pin_of(cell):
    """'121 (PG3)' -> '121'; 'B11 (bank 0)' -> 'B11'; '54' -> '54'"""
    return cell.split()[0]


def net_of(sig):
    return re.sub(r"[\[\]]", "", sig).upper()


def build():
    d = Design()
    for k in ("R", "C", "U", "J", "TP", "SW", "D", "L", "FB", "#FLG", "H", "Y", "X", "F", "FID"):
        d.counters[k] = 0

    # ================================================================ USB-C sink (unchanged R8.5-C)
    d.sheet("usb_power", "usb_power.kicad_sch", "USB-C sink, VBUS protection, F133 USB0 device / FEL")
    j1 = d.U("USB_C", "USB-C receptacle", {
        "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
        "A4": "VBUS_RAW", "A9": "VBUS_RAW", "B4": "VBUS_RAW", "B9": "VBUS_RAW",
        "A5": "USB_CC1", "B5": "USB_CC2", "A6": "USB0_DP", "B6": "USB0_DP", "A7": "USB0_DM", "B7": "USB0_DM"},
        note="power input + F133 USB0 (console / FEL); sink only")
    d.nc(j1.ref, "A8", "SBU unused"); d.nc(j1.ref, "B8", "SBU unused")
    d.flag("VBUS_RAW")
    d.U("F1812", "PTC hold>=3A", {"1": "VBUS_RAW", "2": "VBUS_5V"}, mpn="TBD (1812 PTC, hold >= 3 A, 6 V)", mfr="TBD",
        lcsc="", note="hold current from analysis/R10_POWER_BUDGET.md")
    d.U("TVS_SMF", "SMF5.0A", {"1": "VBUS_5V", "2": "GND"})
    d.flag("VBUS_5V")
    d.C("22uF", "VBUS_5V"); d.C("22uF", "VBUS_5V"); d.C("100nF", "VBUS_5V")
    u = d.U("TUSB320LAI", "TUSB320LAI", {
        "1": "USB_CC1", "2": "USB_CC2", "3": "GND", "4": "TUSB_VBUS_DET", "7": "USB_CUR_OUT1", "8": "USB_CUR_OUT2",
        "10": "GND", "11": "GND", "12": "3V3"}, note="GPIO mode (ADDR open), UFP; OUT1/OUT2 = advertised source current")
    d.nc(u.ref, "5", "ADDR open selects GPIO mode"); d.nc(u.ref, "6", "INT_N/OUT3 unused"); d.nc(u.ref, "9", "ID unused (UFP)")
    d.R("910k", "VBUS_RAW", "TUSB_VBUS_DET", note="DS: 900k; E24 910k")
    d.decouple("3V3")
    d.R("10k", "USB_CUR_OUT1", "3V3"); d.R("10k", "USB_CUR_OUT2", "3V3")
    d.R("5.1k", "USB_CC1", "GND", dnp=True, note="DNP fallback Rd (then TUSB320 DNP)")
    d.R("5.1k", "USB_CC2", "GND", dnp=True, note="DNP fallback Rd")
    d.U("TPD2EUSB30", "TPD2EUSB30", {"1": "USB0_DP", "2": "USB0_DM", "3": "GND"})
    d.R("150k", "VBUS_5V", "VBUS_SENSE"); d.R("200k", "VBUS_SENSE", "GND")
    d.tp("VBUS_5V"); d.tp("USB0_DP", note="FEL probe"); d.tp("USB0_DM")

    # ================================================================ power tree
    d.sheet("power", "power.kicad_sch", "Regulators: system 3V3, F133, D213, 45F and 12F rails; supervisors; staged links")

    def buck(name, en, fb_top, out, note, pg=None, link_net=None):
        """TLV62569(P) from VBUS_5V: Vout = 0.6 V * (1 + Rtop / 100k)."""
        sw, fb = f"SW_{name}", f"FB_{name}"
        reg = out + "_REG" if link_net else out
        if pg:
            d.U("TLV62569P", name, {"1": en, "2": "GND", "3": sw, "4": "VBUS_5V", "5": pg, "6": fb}, note=note)
        else:
            d.U("TLV62569", name, {"1": en, "2": "GND", "3": sw, "4": "VBUS_5V", "5": fb}, note=note)
        d.C("10uF", "VBUS_5V", pkg="C0805")
        d.U("L4035", "2.2uH", {"1": sw, "2": reg})
        d.R(fb_top, reg, fb, note="1 % E96"); d.R("100k", fb, "GND", note="1 %")
        d.C("22uF", reg); d.C("22uF", reg)
        d.flag(reg)
        if link_net:
            d.R("0R", reg, out, pkg="R0603", note="staged power-on link / current measurement")
            d.flag(out)
        d.tp(out)

    # system 3V3 (F133 IO, D213 IO, TFP410, HDMI companion, NORs, USB mux, glue)
    buck("3V3", "VBUS_5V", "453k", "3V3", "calc 0.6*(1+453k/100k)=3.318 V; soft-start sets 3V3 ramp (D21x: 150 us..5 ms)",
         pg="PG_3V3_BUCK", link_net=True)
    d.R("100k", "PG_3V3_BUCK", "3V3_REG")
    d.U("TPS3808", "TPS3808G33", {"1": "PG_3V3", "2": "GND", "3": "SUP33_MR_N", "4": "SUP33_CT", "5": "3V3", "6": "3V3"},
        mpn="TPS3808G33DBVR", note="VIT 3.07 V; enables the core/DRAM bucks after VCC-IO (F133 DS 5.12)")
    d.C("2.2nF", "SUP33_CT", note="tD = 2.2/175 ms + 0.5 ms = 13 ms")
    d.R("100k", "SUP33_MR_N", "3V3"); d.R("10k", "PG_3V3", "3V3")
    d.decouple("3V3")
    # F133 core 0.95 V and DRAM 1.8 V (R8.5-C U5/U6), 1V8 analog LDO
    buck("F133_CORE", "PG_3V3", "57.6k", "VDD_CORE", "0.6*(1+57.6k/100k)=0.946 V (F133 0.85/0.95/0.99)", link_net=True)
    buck("F133_DRAM", "PG_3V3", "200k", "1V8_DRAM", "0.6*(1+200k/100k)=1.80 V (F133 VCC-DRAM 1.7/1.8/1.9)")
    d.U("TLV75518P", "1V8_AN", {"1": "3V3", "2": "GND", "3": "3V3", "5": "1V8_AN"})
    d.C("1uF", "3V3"); d.C("1uF", "1V8_AN"); d.tp("1V8_AN")
    # F133 reset supervisor (R8.5-C U8)
    d.U("TPS3808", "TPS3808G09", {"1": "F133_RESET_N", "2": "GND", "3": "RST_BTN_N", "4": "SUPC_CT", "5": "VDD_CORE", "6": "3V3"},
        mpn="TPS3808G09DBVR", note="RESET# >= 64 ms after rails stable (F133 DS 5.12)")
    d.C("15nF", "SUPC_CT", note="tD = 15/175 ms + 0.5 ms = 86 ms")
    d.R("100k", "RST_BTN_N", "3V3")
    d.R("10k", "F133_RESET_N", "1V8_LDOA", note="RESET in the VCC-RTC (1.8 V) domain")
    d.U("SW_B3U", "F133 RESET", {"1": "RST_BTN_N", "2": "GND"})
    d.tp("F133_RESET_N"); d.tp("PG_3V3")
    # D213 core 1.2 V and DRAM 1.5 V (D21x HW guide 2.2.1: >= 500 mA each, external DC-DC, no sequencing requirement)
    buck("D213_CORE", "PG_3V3", "100k", "1V2_D213", "0.6*(1+100k/100k)=1.20 V: CPU 600 MHz / DDR3 672 MHz (HW guide 4.1 item 4); "
         "FB divider top at the D213 decoupling capacitors (4.1 item 3)", link_net=True)
    buck("D213_DRAM", "PG_3V3", "150k", "1V5_D213", "0.6*(1+150k/100k)=1.50 V DDR3 (HW guide 2.2.1)", link_net=True)

    # ECP5 rail set (R8.5-C topology, per FPGA): one enable starts VCC (1.1 V buck with PG), the VCCIO load switch and,
    # through the VCCIO rail, the VCCAUX LDO. The 25 MHz oscillator OE is the VCC power-good (PG pulled up to the
    # switched VCCIO rail): no external driver toggles a left/right-bank pin before VCC and VCCIO are valid
    # (R10_INTERCONNECT_DECISIONS.md "Electrical interlock"; ECP5 hot-socket facts).
    def fpga_rails(tag, en_src, en_name, pg_name, note_owner):
        vcc, io, aux = f"1V1_{tag}", f"3V3_{tag}", f"2V5_{tag}"
        buck(f"{tag}_VCC", en_name, "82.5k", vcc, "0.6*(1+82.5k/100k)=1.095 V (ECP5 VCC 1.045/1.10/1.155)", pg=pg_name,
             link_net=True)
        d.R("1k", en_src, en_name, note=f"{note_owner} drive; jumper override below")
        d.R("100k", en_name, "GND", note="FPGA unpowered until its owner enables it")
        d.R("100k", pg_name, io, note="PG pulled to the switched VCCIO rail: high only with VCC and VCCIO up")
        d.U("HDR_1x3", f"{tag} power override", {"1": "3V3", "2": en_name, "3": "GND"},
            note="JTAG service without firmware: jumper 1-2 powers the FPGA rails (1k limits contention)")
        d.U("TPS22918", f"{io} switch", {"1": "3V3", "2": "GND", "3": en_name, "4": f"SW_{tag}_CT", "5": io, "6": io},
            note="VCCIO with VCC (TN-02038 s.4); 1 nF CT -> ~1.9 ms ramp")
        d.C("1nF", f"SW_{tag}_CT"); d.C("1uF", "3V3"); d.C("10uF", io, pkg="C0603")
        d.tp(io)                          # driven by the switch VOUT (power_out): no flag
        u = d.U("TLV75525P", aux, {"1": io, "2": "GND", "3": io, "5": f"{aux}_REG"}, note="ECP5 VCCAUX 2.375-2.625 V")
        d.nc(u.ref, "4", "NC per datasheet")
        d.C("1uF", io); d.C("1uF", f"{aux}_REG")
        d.U("FB0603", "ferrite 120R@100MHz", {"1": f"{aux}_REG", "2": aux}, mpn="BLM18PG121SN1D (CANDIDATE)",
            note="TN-02038 Table 3.1: ferrite on VCCAUX")
        d.flag(aux); d.tp(aux); d.tp(pg_name); d.tp(en_name)

    fpga_rails("F45", "FPGA45_PWR_EN_D", "FPGA45_PWR_EN", "FPGA45_VCC_PG", "D213 PA2")
    fpga_rails("F12", "FPGA12_PWR_EN_F", "FPGA12_PWR_EN", "FPGA12_VCC_PG", "F133 PE0")
    for _ in range(4):
        d.tp("GND")
    d.flag("GND")
    for i in range(3):
        d.add(f"FID{i + 1}", "FID", "fiducial", {})
    for i in range(1, 5):
        d.add(f"H{i}", "MH", "M2.5", {"1": "GND"})

    # ================================================================ F133
    d.sheet("f133", "f133.kicad_sch", "F133-B: supplies, clock, reset, pin assignment")
    power = {
        "VDD-CORE0": "VDD_CORE", "VDD-CORE1": "VDD_CORE", "VDD-SYS0": "VDD_CORE", "VDD-SYS1": "VDD_CORE", "VDD-SYS2": "VDD_CORE",
        "VCC-IO": "3V3", "VCC-PD": "3V3", "VCC-PE": "3V3", "VCC-PG": "3V3", "VCC-TVOUT": "3V3", "LDO-IN": "3V3",
        "VCC-DRAM0": "1V8_DRAM", "VCC-DRAM1": "1V8_DRAM",
        "VCC-PLL": "1V8_LDOA", "VCC-RTC": "1V8_LDOA", "VDD18-DRAM": "1V8_LDOA", "VCC-LVDS": "1V8_LDOA",
        "LDOA-OUT": "1V8_LDOA", "LDOB-OUT": "F133_LDOB",
        "AVCC": "1V8_AN", "HPVCC": "1V8_AN", "VCC-TVIN": "1V8_AN", "AGND": "GND", "EPAD": "GND",
    }
    gpio = {
        "PC2": "SPI0_CLK_F", "PC3": "SPI0_CS0_N", "PC4": "SPI0_MOSI", "PC5": "SPI0_MISO", "PC6": "SPI0_IO2", "PC7": "SPI0_IO3",
        "PF0": "SD_D1", "PF1": "SD_D0", "PF2": "SD_CLK_F", "PF3": "SD_CMD", "PF4": "SD_D3", "PF5": "SD_D2", "PF6": "SD_DET_N",
        "PE2": "UART0_TX", "PE3": "UART0_RX",
        # 12F control (R8.5-C ECP5 control pins, now serving the 12F; hardware/R10_flash_pinmux.csv CFG12)
        "PE4": "FPGA12_SS_N_F", "PE5": "FPGA12_IRQ_N", "PE6": "FPGA12_BUS_EN_N", "PE8": "FPGA12_PROGRAMN_F",
        "PE9": "FPGA12_DONE", "PE0": "FPGA12_PWR_EN_F", "PD0": "FPGA12_INITN", "PD1": "FPGA12_VCC_PG",
        # D213 control (decision D5): open-drain reset and boot-pin hold through U(LVC2G07); ready from D213 PB6
        "PD10": "D213_RESET_REQ_N", "PD11": "D213_BOOT_REQ_N", "PD12": "D213_RDY",
        "PB4": "I2S_DOUT", "PB5": "I2S_BCLK", "PB6": "I2S_LRCK", "PE10": "AMP_EN",
        "PE1": "VBUS_SENSE", "PE12": "USB_CUR_OUT1", "PE13": "USB_CUR_OUT2", "PD20": "SD_PWR_EN",
        "PD2": "BTN_UP", "PD3": "BTN_DOWN", "PD4": "BTN_LEFT", "PD5": "BTN_RIGHT", "PD6": "BTN_A", "PD7": "BTN_B",
        "PD8": "BTN_X", "PD9": "BTN_Y", "PD14": "BTN_L", "PD15": "BTN_R", "PD22": "BTN_START", "PB2": "BTN_SELECT",
        "PB3": "BTN_HOME", "PD18": "LED_STATUS", "PD19": "LED_ERROR",
    }
    # F133 <-> 12F RGMII (architecture/R10_interface_matrix.csv): F133 side net ETH_<sig>_F for its outputs
    eth12 = [r for r in MATRIX if r["link"] == "F133<->12F"]
    assert len(eth12) == 12, len(eth12)
    for r in eth12:
        sig = r["signal"].replace("TXCTRL", "TXCTL").replace("RXCTRL", "RXCTL")
        gpio[r["a_pad"]] = f"ETH_{sig}_F" if r["direction_a_to_b"] == "F133->12F" else f"ETH_{sig}"
    analog = {"DXIN": "XTAL24_IN", "DXOUT": "XTAL24_OUT", "RESET": "F133_RESET_N", "USB0-DP": "USB0_DP", "USB0-DM": "USB0_DM",
              "USB1-DP": "F133_USB1_DP", "USB1-DM": "F133_USB1_DM",
              "VRA1": "F133_VRA1", "VRA2": "F133_VRA2", "NC": "F133_PIN47_DZQ"}
    nc_why = {
        "REFCLK-OUT": "24 MHz fan-out unused", "X32KIN": "RTC 32k crystal optional (internal RC)", "X32KOUT": "RTC 32k optional",
        "TVOUT0": "CVBS out unused", "TVIN0": "unused", "TVIN1": "unused", "TVIN-VRP": "CVBS ref unused (OPEN: no termination given)",
        "TVIN-VRN": "CVBS ref unused (OPEN)", "MICIN3P": "codec unused", "MICIN3N": "codec unused", "FMINR": "unused",
        "FMINL": "unused", "LINEINR": "unused", "LINEINL": "unused", "HPOUTR": "analog HP out unused (I2S amps)",
        "HPOUTL": "unused", "HPOUTFB": "unused", "GPADC0": "spare ADC", "TP-X1": "unused", "TP-X2": "unused",
        "TP-Y1": "unused", "TP-Y2": "unused", "NC0": "datasheet NC",
    }
    conn = {}
    for num, name, et, side in PARTS["F133"].pins:
        if name in power:
            conn[num] = power[name]
        elif name in gpio:
            conn[num] = gpio[name]
        elif name in analog and num != "106":
            conn[num] = analog[name]
    used = {n for n in gpio}
    missing = used - {p[1] for p in PARTS["F133"].pins}
    assert not missing, missing
    uf = d.U("F133", "F133-B", conn)
    for num, name, et, side in PARTS["F133"].pins:
        if num not in conn:
            d.nc(uf.ref, num, nc_why.get(name, "spare GPIO"))
    for net, n in (("VDD_CORE", 5), ("3V3", 6), ("1V8_DRAM", 2), ("1V8_LDOA", 4), ("1V8_AN", 3)):
        d.decouple(net, n)
    d.C("10uF", "VDD_CORE", pkg="C0603"); d.C("10uF", "3V3", pkg="C0603"); d.C("4.7uF", "1V8_DRAM", pkg="C0603")
    d.C("4.7uF", "1V8_LDOA", pkg="C0603")
    d.C("2.2uF", "F133_LDOB", pkg="C0603", note="LDOB-OUT unused (DRAM from buck), cap per MangoPi MQ")
    d.C("1uF", "F133_VRA1", note="value per reference design -- OPEN"); d.C("1uF", "F133_VRA2", note="OPEN")
    d.R("240R", "F133_PIN47_DZQ", "GND", dnp=True, note="pin 47 DZQ option (OPEN)")
    d.U("XTAL_3225", "24MHz", {"1": "XTAL24_IN", "2": "GND", "3": "XTAL24_OUT", "4": "GND"})
    d.C("12pF", "XTAL24_IN", note="CL match to crystal"); d.C("12pF", "XTAL24_OUT")
    d.R("100k", "D213_RDY", "GND", note="reads 'not ready' while the D213 is in reset or unprogrammed")
    d.tp("UART0_TX"); d.tp("UART0_RX"); d.tp("D213_RDY")

    # ================================================================ boot NOR (F133 SPI0), straps, FEL
    d.sheet("boot_nor", "boot_nor.kicad_sch", "64 MiB system NOR (F133 SPI0, BOOT-SEL 00), straps, FEL / clip recovery")
    nor = [r for r in PINMUX if r["group"] == "NOR"]
    assert {r["signal"] for r in nor} == {"SPI0_CLK", "SPI0_CS0_N", "SPI0_MOSI", "SPI0_MISO", "SPI0_IO2", "SPI0_IO3"}
    un = d.U("W25Q512JVFIQ", "W25Q512JVFIQ", {"1": "SPI0_IO3", "2": "3V3", "3": "NOR_RESET_N", "7": "SPI0_CS0_N",
                                             "8": "SPI0_MISO", "9": "SPI0_IO2", "10": "GND", "15": "SPI0_MOSI",
                                             "16": "SPI0_CLK"}, note="the only persistent system store (memory/R10_nor_partition.csv)")
    for p in ("4", "5", "6", "11", "12", "13", "14"):
        d.nc(un.ref, p, "NC per datasheet")
    d.decouple("3V3"); d.C("1uF", "3V3")
    d.R("22R", "SPI0_CLK_F", "SPI0_CLK", note="source series termination at F133")
    d.R("3.3k", "SPI0_MOSI", "GND", note="BOOT-SEL0 = 0")
    d.R("3.3k", "SPI0_MISO", "GND", note="BOOT-SEL1 = 0")
    d.R("10k", "SPI0_CS0_N", "3V3"); d.R("10k", "SPI0_IO2", "3V3"); d.R("10k", "SPI0_IO3", "3V3")
    d.R("10k", "NOR_RESET_N", "3V3")
    d.U("SW_B3U", "FEL (NOR reset)", {"1": "NOR_RESET_N", "2": "GND"},
        note="hold during F133 reset: NOR unreadable -> BROM falls through to USB FEL (bench)")
    for net in ("SPI0_CLK", "SPI0_MOSI", "SPI0_MISO", "SPI0_CS0_N", "NOR_RESET_N", "SPI0_IO2", "SPI0_IO3"):
        d.tp(net, note="SOIC-16 clip / probe")
    d.U("HDR_2x5_127", "LA SPI0", {"1": "SPI0_CLK", "2": "GND", "3": "SPI0_MOSI", "4": "GND", "5": "SPI0_MISO", "6": "GND",
                                   "7": "SPI0_CS0_N", "8": "FPGA12_SS_N_F", "9": "NOR_RESET_N", "10": "F133_RESET_N"},
        dnp=True, note="logic-analyser / external programmer header, DNP")

    # ================================================================ D213ECV
    d.sheet("d213", "d213.kicad_sch", "D213ECV display SoC: supplies, 24 MHz, reset/boot control (D5), boot NOR, UART")
    dpins = {p[1]: p[0] for p in PARTS["D213ECV"].pins if p[1] not in ("VCC33_IO0", "VCC33_IO1", "VDD11_SYS", "VCC_DRAM", "NC")}
    dc = {}
    for num, name, et, side in PARTS["D213ECV"].pins:
        if name in ("VCC33_IO0", "VCC33_IO1"):
            dc[num] = "3V3"
        elif name == "VDD11_SYS":
            dc[num] = "1V2_D213"
        elif name == "VCC_DRAM":
            dc[num] = "1V5_D213"
        elif name == "GND":
            dc[num] = "GND"
    dmap = {"LDO1x": "D213_LDO1X", "LDO25": "D213_LDO25", "VCC30_ANA": "D213_VCC30", "RESETN": "D213_RESET_N",
            "PLL_XO": "D213_XO", "PLL_XI": "D213_XI", "PU0": "D213_USB0_DM", "PU1": "D213_USB0_DP",
            "PA0": "D213_UART0_TX", "PA1": "D213_UART0_RX", "PA2": "FPGA45_PWR_EN_D", "PA3": "FPGA45_VCC_PG",
            "PA7": "TFP_MSEN", "PA8": "HDMI_SCL", "PA9": "HDMI_SDA", "PA10": "HDMI_HPD", "PA11": "TFP_PD_N",
            "PB0": "D213_NOR_IO3", "PB1": "D213_NOR_IO2", "PB2": "D213_NOR_CS_N", "PB3": "D213_NOR_MISO",
            "PB4": "D213_NOR_MOSI", "PB5": "D213_NOR_CLK_D", "PB6": "D213_RDY", "PB7": "D213_LED"}
    # 45F configuration (hardware/R10_flash_pinmux.csv CFG45, D213 side) -> D213-side nets (_D: before the Ioff buffers)
    cfgd = {"FPGA45_SCK": "FPGA45_SCK_D", "FPGA45_MOSI": "FPGA45_MOSI_D", "FPGA45_MISO": "FPGA45_MISO",
            "FPGA45_SS_N": "FPGA45_SS_N_D", "FPGA45_PROGRAMN": "FPGA45_PROGRAMN_D", "FPGA45_INITN": "FPGA45_INITN",
            "FPGA45_DONE": "FPGA45_DONE"}
    for r in pm("CFG45", "D213"):
        pad = r["pin"].split("(")[1].rstrip(")")
        dmap[pad] = cfgd[r["signal"]]
    # RGMII + GMAC reference clock (architecture/R10_interface_matrix.csv, D213<->45F, decision D1/D7)
    eth45 = [r for r in MATRIX if r["link"] == "D213<->45F" and "SELECTED D1" in r["status"]]
    assert len(eth45) == 13, len(eth45)
    for r in eth45:
        dmap[r["a_pad"]] = f"G_{r['signal']}_D" if r["direction_a_to_b"] == "D213->45F" else f"G_{r['signal']}"
    # RGB888 -> TFP410 (decision D6)
    vid = [r for r in MATRIX if r["link"] == "D213->video" and "SELECTED D6" in r["status"]]
    assert len(vid) == 28, len(vid)
    for r in vid:
        dmap[r["a_pad"]] = r["signal"] if re.fullmatch(r"LCD_D\d+", r["signal"]) else r["signal"] + "_D"
    for name, net in dmap.items():
        dc[dpins[name]] = net
    ud = d.U("D213ECV", "D213ECV", dc, note="EPAD = GND, many vias (HW guide 3.1)")
    why = {"RTC_IO": "RTC wake/32k output unused (OD)", "RTC_VCOIN": "may float: internal diode from VCC33_IO (HW guide 2.2.3)",
           "RTC_XO": "RTC unused: may float (Table 2-5)", "RTC_XI": "RTC unused: may float (Table 2-5)",
           "NC": "datasheet: floating, connect nothing", "PU2": "USB1 unused", "PU3": "USB1 unused",
           "PE8": "GMAC0_MDC unused (no PHY)", "PE9": "GMAC0_MDIO unused (no PHY)", "PE10": "CLK_OUT unused"}
    for num, name, et, side in PARTS["D213ECV"].pins:
        if num not in dc:
            d.nc(ud.ref, num, why.get(name, "spare GPIO"))
    # decoupling: one 100 nF per supply pin at the pin + bulk (HW guide 3.1), LDO outputs 1 uF (2.2.1)
    d.decouple("1V2_D213", 6); d.C("10uF", "1V2_D213", pkg="C0603"); d.C("10uF", "1V2_D213", pkg="C0603")
    d.decouple("1V5_D213", 5); d.C("10uF", "1V5_D213", pkg="C0603"); d.C("10uF", "1V5_D213", pkg="C0603")
    d.decouple("3V3", 5); d.C("10uF", "3V3", pkg="C0603")
    d.C("1uF", "D213_LDO1X"); d.C("1uF", "D213_LDO25"); d.C("1uF", "D213_VCC30")
    # 24 MHz crystal, +-20 ppm; 0R in series on PLL_XO (HW guide 2.2.2)
    d.U("XTAL_3225", "24MHz +-20ppm", {"1": "D213_XI", "2": "GND", "3": "D213_XO_X", "4": "GND"},
        note="+-20 ppm required (HW guide 2.2.2); load caps per crystal CL")
    d.R("0R", "D213_XO", "D213_XO_X", note="HW guide 2.2.2: series 0R on PLL_XO to tune drive")
    d.C("12pF", "D213_XI", note="CL match to crystal"); d.C("12pF", "D213_XO_X")
    # reset / boot-pin control from the F133 (D5): open-drain, inactive while the F133 is in reset
    d.U("LVC2G07", "D213 ctl OD", {"1": "D213_BOOT_REQ_N", "2": "GND", "3": "D213_RESET_REQ_N", "4": "D213_RESET_N",
                                   "5": "3V3", "6": "D213_UART0_TX"},
        note="1Y holds PA0 (boot/upgrade pin, also UART0_TX) low across a D213 reset; 2Y pulls RESETN (internal 30k "
             "pull-up). Hi-Z when the F133 lets the inputs float high.")
    d.decouple("3V3")
    d.R("100k", "D213_BOOT_REQ_N", "3V3", note="inactive while F133 PD11 is hi-Z")
    d.R("100k", "D213_RESET_REQ_N", "3V3", note="inactive while F133 PD10 is hi-Z")
    d.U("SW_B3U", "D213 RESET", {"1": "D213_RESET_N", "2": "GND"}, note="HW guide 2.2.5: reserve a key/jumper")
    d.U("SW_B3U", "D213 BOOT (PA0)", {"1": "D213_UART0_TX", "2": "GND"},
        note="hold while pressing D213 RESET -> USB burn mode (HW guide 2.2.4 / 4.6 item 1)")
    d.C("100nF", "D213_RESET_N", dnp=True, note="optional delay cap (<= 4.7 uF allowed)")
    d.U("HDR_1x3", "D213 UART0", {"1": "GND", "2": "D213_UART0_TX", "3": "D213_UART0_RX_J"}, note="3.3 V TTL console")
    d.R("100R", "D213_UART0_RX_J", "D213_UART0_RX", note="EOS series R on an exposed pin (HW guide 4.7 item 1)")
    d.R("100k", "D213_UART0_TX", "3V3", note="PA0 idles high: normal boot unless the F133 or the BOOT key holds it low")
    # D213 boot NOR (D5): SPI0 PB0-PB5; CS/WP/HOLD pull-ups mandatory (HW guide 2.3.1)
    un2 = d.U("W25Q512JVFIQ", "W25Q512JVFIQ", {"1": "D213_NOR_IO3", "2": "3V3", "3": "D213_NOR_RESET_N",
                                               "7": "D213_NOR_CS_N", "8": "D213_NOR_MISO", "9": "D213_NOR_IO2",
                                               "10": "GND", "15": "D213_NOR_MOSI", "16": "D213_NOR_CLK"},
              note="prototype bring-up/recovery boot flash (D5); same part as the system NOR (3-byte mode at power-up); "
                   "DNP in production once F133 flashless boot is PROTOTYPE_MEASURED")
    for p in ("4", "5", "6", "11", "12", "13", "14"):
        d.nc(un2.ref, p, "NC per datasheet")
    d.decouple("3V3")
    d.R("22R", "D213_NOR_CLK_D", "D213_NOR_CLK", note="source series termination")
    for n in ("D213_NOR_CS_N", "D213_NOR_IO2", "D213_NOR_IO3", "D213_NOR_RESET_N"):
        d.R("10k", n, "3V3", note="HW guide 2.3.1: CS/WP/HOLD must be pulled up")
    for n in ("D213_NOR_CLK", "D213_NOR_MOSI", "D213_NOR_MISO", "D213_NOR_CS_N"):
        d.tp(n, note="SOIC-16 clip / probe")
    d.U("LED", "D213 LED", {"1": "GND", "2": "D213_LED_R"}); d.R("1k", "D213_LED", "D213_LED_R")
    d.tp("D213_RESET_N"); d.tp("D213_UART0_TX"); d.tp("D213_XI")

    # ================================================================ USB link F133 USB1 host -> D213 USB0 (+ recovery)
    d.sheet("usb_link", "usb_link.kicad_sch", "F133 USB1 host -> D213 USB0 device; power-off service mux to recovery USB-C")
    d.U("TS3USB221A", "TS3USB221A", {"1": "F133_USB1_DP", "2": "F133_USB1_DM", "3": "REC_USB_DP", "4": "REC_USB_DM",
                                    "5": "GND", "6": "USBMUX_OE_N", "7": "D213_USB0_DM", "8": "D213_USB0_DP",
                                    "9": "USBMUX_SEL", "10": "3V3"},
        note="S=L (default): D213 USB0 <-> F133 USB1 host. S=H (jumper, change only with power off): D213 USB0 <-> "
             "recovery USB-C. The F133 host is then disconnected on both data lines (decision 6). 90 ohm diff routing.")
    d.decouple("3V3")
    d.R("10k", "USBMUX_SEL", "GND", note="default: internal host link")
    d.R("10k", "USBMUX_OE_N", "GND", note="mux enabled")
    d.U("HDR_1x3", "USB path select", {"1": "3V3", "2": "USBMUX_SEL", "3": "GND"},
        note="jumper 1-2 = recovery connector (power off first); no jumper / 2-3 = F133 host")
    jr = d.U("USB_C", "recovery USB-C", {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
                                         "A4": "REC_VBUS", "A9": "REC_VBUS", "B4": "REC_VBUS", "B9": "REC_VBUS",
                                         "A5": "REC_CC1", "B5": "REC_CC2", "A6": "REC_USB_DP", "B6": "REC_USB_DP",
                                         "A7": "REC_USB_DM", "B7": "REC_USB_DM"},
             note="D213 recovery / AiBurn port (device only). REC_VBUS is NOT connected to the board 5 V (no back-feed); "
                  "the D213 has no VBUS-sense pin (pin table).")
    d.nc(jr.ref, "A8", "SBU unused"); d.nc(jr.ref, "B8", "SBU unused")
    d.R("5.1k", "REC_CC1", "GND", note="Rd: PC host sees a device"); d.R("5.1k", "REC_CC2", "GND")
    d.R("100k", "REC_VBUS", "GND", note="defined level; VBUS only to a test point")
    d.U("TVS_SMF", "SMF5.0A", {"1": "REC_VBUS", "2": "GND"})
    d.U("TPD2EUSB30", "TPD2EUSB30", {"1": "REC_USB_DP", "2": "REC_USB_DM", "3": "GND"})
    d.tp("REC_VBUS"); d.tp("D213_USB0_DP"); d.tp("D213_USB0_DM")

    # ================================================================ video: TFP410 + TPD12S016 + HDMI-A (decision D6)
    d.sheet("video", "video.kicad_sch", "D213 RGB888 -> TFP410 (DVI, strap mode) -> TPD12S016 -> HDMI type-A")
    tconn = {"1": "3V3_TFP_D", "12": "3V3_TFP_D", "33": "3V3_TFP_D", "18": "3V3_TFP_P", "23": "3V3_TFP_T", "29": "3V3_TFP_T",
             "16": "GND", "48": "GND", "64": "GND", "17": "GND", "20": "GND", "26": "GND", "32": "GND", "65": "GND",
             "3": "3V3_TFP_D",                         # VREF = DVDD: 3.3 V high-swing input (SLDS145D 6.3.2)
             "13": "TFP_ISEL", "15": "TFP_BSEL", "14": "TFP_DSEL", "9": "TFP_EDGE", "35": "TFP_DKEN",
             "6": "TFP_DK3", "7": "TFP_DK2", "8": "TFP_DK1", "10": "TFP_PD_N", "11": "TFP_MSEN", "34": "GND",
             "19": "TFP_TFADJ", "56": "GND",            # IDCK- tied low: single-ended clock
             "21": "TMDS_CK_N", "22": "TMDS_CK_P", "24": "TMDS_D0_N", "25": "TMDS_D0_P", "27": "TMDS_D1_N",
             "28": "TMDS_D1_P", "30": "TMDS_D2_N", "31": "TMDS_D2_P"}
    for r in vid:
        tpin = r["b_pin"]
        tconn[tpin] = r["signal"]
    tu = d.U("TFP410", "TFP410PAP", tconn, note="24-bit single-edge (BSEL=1), high swing (VREF=DVDD), I2C off (ISEL=0)")
    d.nc(tu.ref, "49", "NC per datasheet")
    for s in ("LCD_DCLK", "LCD_HS", "LCD_VS", "LCD_DE"):
        d.R("22R", s + "_D", s, note="series R at the D213 (HW guide 4.7 item 3)")
    d.C("10pF", "LCD_DCLK", dnp=True, note="DNP RC filter footprint on the pixel clock (HW guide 4.7 item 3)")
    d.R("10k", "TFP_ISEL", "GND", note="I2C disabled: configuration from pins")
    d.R("10k", "TFP_BSEL", "3V3_TFP_D", note="24-bit, single edge")
    d.R("10k", "TFP_DSEL", "GND", note="don't care in high-swing mode")
    d.R("10k", "TFP_EDGE", "3V3_TFP_D", note="latch on rising IDCK (fitted)")
    d.R("10k", "TFP_EDGE", "GND", dnp=True, note="alternative: latch on falling edge (fit instead of the pull-up)")
    d.R("10k", "TFP_DKEN", "GND", note="de-skew off (fitted)")
    d.R("10k", "TFP_DKEN", "3V3_TFP_D", dnp=True, note="de-skew on: then DK[3:1] select the setup/hold trim")
    for k in ("TFP_DK3", "TFP_DK2", "TFP_DK1"):
        d.R("10k", k, "GND", note="DK step 000 (fitted)")
        d.R("10k", k, "3V3_TFP_D", dnp=True, note="trim option")
    d.R("10k", "TFP_PD_N", "3V3", note="TFP410 on by default (display works before any GPIO setup); D213 PA11 may power it down")
    d.R("4.7k", "TFP_MSEN", "3V3_TFP_D", note="SLDS145D: 5k pull-up required on MSEN (open drain); 4.7k E12")
    d.R("510R", "TFP_TFADJ", "3V3_TFP_T", note="RTFADJ 510 ohm 1 %: DVI-compliant swing (SLDS145D 5.3)")
    # supplies: ferrite + 22 uF + 10 nF per pin (SLDS145D 7.3), separate DVDD / TVDD / PVDD
    for rail, n in (("3V3_TFP_D", 3), ("3V3_TFP_T", 2), ("3V3_TFP_P", 3)):
        d.U("FB0603", "ferrite 120R@100MHz", {"1": "3V3", "2": rail}, mpn="BLM18PG121SN1D (CANDIDATE)")
        d.C("22uF", rail, note="SLDS145D 7.3: 22 uF (tantalum or ceramic) after the ferrite")
        d.decouple(rail, n, "10nF")
        d.flag(rail)
    # HDMI companion: flow-through TMDS ESD, DDC level shift with internal pull-ups, HPD, 5 V load switch (55 mA)
    d.U("TPD12S016", "TPD12S016", {"1": "TPD_CEC_A", "2": "HDMI_SCL", "3": "HDMI_SDA", "4": "HDMI_HPD", "5": "TPD_LS_OE",
                                  "6": "GND", "7": "HDMI_CEC", "8": "HDMI_SCL_5V", "9": "HDMI_SDA_5V", "10": "HDMI_HPD_5V",
                                  "11": "VBUS_5V", "12": "TPD_CT_HPD", "13": "HDMI_5V", "14": "GND",
                                  "15": "TMDS_CK_N", "16": "TMDS_CK_P", "17": "TMDS_D0_N", "18": "TMDS_D0_P", "19": "GND",
                                  "20": "TMDS_D1_N", "21": "TMDS_D1_P", "22": "TMDS_D2_N", "23": "TMDS_D2_P", "24": "3V3"},
        note="no external DDC/CEC/HPD pull-ups needed (SLLSE96F 7.3.15); TMDS pass-through placed at the connector")
    d.R("10k", "TPD_LS_OE", "3V3", note="level shifters on"); d.R("10k", "TPD_CT_HPD", "3V3", note="load switch + HPD on")
    d.R("10k", "TPD_CEC_A", "3V3", dnp=True, note="CEC unused at the D213; internal 10k pull-up suffices")
    d.decouple("3V3"); d.C("100nF", "VBUS_5V"); d.C("100nF", "HDMI_5V")
    jh = d.U("HDMI_A", "HDMI type-A", {"1": "TMDS_D2_P", "2": "GND", "3": "TMDS_D2_N", "4": "TMDS_D1_P", "5": "GND",
                                  "6": "TMDS_D1_N", "7": "TMDS_D0_P", "8": "GND", "9": "TMDS_D0_N", "10": "TMDS_CK_P",
                                  "11": "GND", "12": "TMDS_CK_N", "13": "HDMI_CEC", "15": "HDMI_SCL_5V",
                                  "16": "HDMI_SDA_5V", "17": "GND", "18": "HDMI_5V", "19": "HDMI_HPD_5V", "SH": "GND"},
        note="DVI video over HDMI connector (no HDMI audio, D6); TMDS 100 ohm differential")
    d.nc(jh.ref, "14", "Utility/HEAC+ unused")
    d.tp("LCD_DCLK"); d.tp("HDMI_HPD"); d.tp("TFP_MSEN"); d.tp("HDMI_5V")

    # ================================================================ 45F
    d.sheet("fpga45", "fpga45.kicad_sch", "LFE5U-45F-6BG381C tile GPU: rails, slave-SPI config from the D213, JTAG, RGMII")
    used45 = {"P3": "F45_OSC_25M", "A7": "F45_LED0"}
    for r in eth45:
        used45[pin_of(r["b_pin"])] = f"G_{r['signal']}" if r["direction_a_to_b"] == "D213->45F" else f"G_{r['signal']}_F"
    for r in pm("SDRAM45"):
        used45[r["pin"]] = "SD_" + net_of(r["signal"].replace("sd_", "")) + ("_F" if r["signal"] == "sd_clk" else "")
    cfg45 = {r["signal"]: r["pin"] for r in pm("CFG45", "LFE5U-45F")}
    used45.update({cfg45["FPGA45_SCK"]: "FPGA45_SCK", cfg45["FPGA45_MOSI"]: "FPGA45_MOSI", cfg45["FPGA45_MISO"]: "FPGA45_MISO",
                   cfg45["FPGA45_SS_N"]: "FPGA45_SS_N", cfg45["FPGA45_PROGRAMN"]: "FPGA45_PROGRAMN",
                   cfg45["FPGA45_INITN"]: "FPGA45_INITN", cfg45["FPGA45_DONE"]: "FPGA45_DONE",
                   cfg45["FPGA45_CFG0"]: "FPGA45_CFG0", "T4": "GND", "R4": "GND", "R2": "FPGA45_HOLDN",
                   "T5": "FPGA45_TCK", "R5": "FPGA45_TDI", "V4": "FPGA45_TDO", "U5": "FPGA45_TMS"})
    t = {}
    for ball, name, et, side in PARTS["ECP5_45F_BG381"].pins:
        fn = name.split("/")[0]
        if ball in used45:
            t[ball] = used45[ball]
        elif fn == "GND":
            t[ball] = "GND"
        elif fn == "VCC":
            t[ball] = "1V1_F45"
        elif fn == "VCCAUX":
            t[ball] = "2V5_F45"
        elif fn.startswith("VCCIO"):
            t[ball] = "3V3_F45"
    u45 = d.U("ECP5_45F_BG381", "LFE5U-45F-6BG381C", t)
    for ball, name, et, side in PARTS["ECP5_45F_BG381"].pins:
        if ball not in t:
            fn = name.split("/")[0]
            d.nc(u45.ref, ball, "RESERVED: do not connect" if fn == "RESERVED" else "NC ball" if et == "no_connect" else
                 "unused user I/O (weak pull-down after configuration)")
    # RGMII: 22R source series at each driver; CTL pull-downs keep both MACs idle while the other side is off
    for r in eth45:
        s = r["signal"]
        if r["direction_a_to_b"] == "D213->45F":
            d.R("22R", f"G_{s}_D", f"G_{s}", note=f"D213->45F series R at the D213 ({s})")
        else:
            d.R("22R", f"G_{s}_F", f"G_{s}", note=f"45F->D213 series R at the 45F ({s})")
    d.R("100k", "G_TXCTL", "GND", note="45F RX idle while the D213 PE7 is hi-Z")
    d.R("100k", "G_RXCTL", "GND", note="D213 GMAC RX idle while the 45F is off/unconfigured")
    d.R("0R", "G_RXCK", "G_CLKIN", dnp=True, note="D7 fallback: feed GMAC0_CLKIN from the 45F RGMII TX clock")
    d.U("OSC_3225", "125MHz", {"1": "3V3", "2": "GND", "3": "G_CLKIN_OSC", "4": "3V3"}, dnp=True,
        note="D7 fallback: independent 125 MHz MAC reference (DNP)")
    d.R("0R", "G_CLKIN_OSC", "G_CLKIN", dnp=True, note="D7 fallback oscillator link (DNP)")
    d.tp("G_TXCK"); d.tp("G_RXCK"); d.tp("G_CLKIN")
    # decoupling (TN-02038 Table 3.1/3.2), as R8.5-C
    d.decouple("1V1_F45", 20)
    for _ in range(3):
        d.C("10uF", "1V1_F45", pkg="C0603")
    d.decouple("2V5_F45", 4); d.C("10uF", "2V5_F45", pkg="C0603")
    d.decouple("3V3_F45", 18)
    for _ in range(7):
        d.C("10uF", "3V3_F45", pkg="C0603", note="one per VCCIO bank")
    # sysCONFIG slave SPI from the D213 SPI1 (decision: 45F configured by the D213; no 45F flash). Ioff buffers
    # powered from 3V3_F45 isolate the D213 drivers from the unpowered FPGA (bank 8 pull-ups are on 3V3_F45).
    for src, dst in (("FPGA45_SCK_D", "FPGA45_SCK_B"), ("FPGA45_MOSI_D", "FPGA45_MOSI"), ("FPGA45_SS_N_D", "FPGA45_SS_N")):
        d.U("LVC1G125", "iso " + dst, {"1": "GND", "2": src, "3": "GND", "4": dst, "5": "3V3_F45"},
            note="Ioff: no current into the FPGA rail while 3V3_F45 is off")
    d.decouple("3V3_F45", 3)
    d.R("33R", "FPGA45_SCK_B", "FPGA45_SCK", note="CCLK series 22-80R (TN-02038 Table 6.2)")
    d.R("10k", "FPGA45_SS_N_D", "3V3", note="D213 side: deselected while the D213 is in reset")
    d.R("100k", "FPGA45_SCK_D", "GND"); d.R("100k", "FPGA45_MOSI_D", "GND")
    d.R("100k", "FPGA45_MISO", "GND", note="defined at the D213 while the FPGA is off/unconfigured")
    d.R("4.7k", "FPGA45_PROGRAMN", "3V3_F45", note="TN-02038: 4.7k to VCCIO8")
    d.R("470R", "FPGA45_PROGRAMN_D", "FPGA45_PROGRAMN", note="D213 PA4 used open-drain (low or input)")
    d.R("4.7k", "FPGA45_INITN", "3V3_F45"); d.R("4.7k", "FPGA45_DONE", "3V3_F45")
    d.R("4.7k", "FPGA45_SS_N", "3V3_F45", note="SN pull-up (TN-02039 6.2)")
    d.R("4.7k", "FPGA45_CFG0", "3V3_F45", note="CFG[2:0] = 001 slave SPI")
    d.R("10k", "FPGA45_HOLDN", "3V3_F45")
    d.R("1k", "FPGA45_SCK", "3V3_F45", note="CCLK 510R-1k pull-up")
    d.R("4.7k", "FPGA45_TCK", "GND")
    d.R("4.7k", "FPGA45_TMS", "3V3_F45"); d.R("4.7k", "FPGA45_TDI", "3V3_F45"); d.R("4.7k", "FPGA45_TDO", "3V3_F45")
    jt = d.U("HDR_2x5_127", "45F JTAG", {"1": "3V3_F45", "2": "FPGA45_TMS", "3": "GND", "4": "FPGA45_TCK", "5": "GND",
                                         "6": "FPGA45_TDO", "8": "FPGA45_TDI", "9": "GND", "10": "FPGA45_PROGRAMN"},
             note="always-available configuration path independent of the D213 (openFPGALoader)")
    d.nc(jt.ref, "7", "key")
    d.U("OSC_3225", "25MHz", {"1": "FPGA45_VCC_PG", "2": "GND", "3": "F45_OSC_25M_X", "4": "3V3_F45"},
        note="OE = VCC power-good: no clock into bank 6 before VCC and VCCIO are valid")
    d.R("33R", "F45_OSC_25M_X", "F45_OSC_25M"); d.decouple("3V3_F45")
    d.U("LED", "45F LED", {"1": "GND", "2": "F45_LED0_R"}); d.R("1k", "F45_LED0", "F45_LED0_R")
    d.tp("FPGA45_DONE"); d.tp("FPGA45_PROGRAMN"); d.tp("FPGA45_INITN"); d.tp("FPGA45_SCK"); d.tp("F45_OSC_25M")

    # ================================================================ 45F SDRAM
    d.sheet("sdram45", "sdram45.kicad_sch", "AS4C16M16SA 32 MiB x16 SDR SDRAM, private 45F memory, on 3V3_F45")
    sdc = {}
    for r in pm("SDRAM45"):
        sdc[r["peer_pin"]] = "SD_" + net_of(r["signal"].replace("sd_", ""))
    for r in pm("SDRAM45_POWER"):
        if r["signal"] in ("VDD", "VDDQ"):
            sdc[r["pin"]] = "3V3_F45"
        elif r["signal"] in ("VSS", "VSSQ"):
            sdc[r["pin"]] = "GND"
    us = d.U("AS4C16M16SA", "AS4C16M16SA-6TIN", sdc, note="powered with the 45F VCCIO (banks 2/3 not hot-socket safe)")
    d.nc(us.ref, "40", "NC must remain unconnected")
    d.R("22R", "SD_CLK_F", "SD_CLK", note="clock source series R at the 45F; phase calibrated (fpga45/rtl/sdram_cal.sv)")
    d.R("10k", "SD_CKE", "GND", note="CKE low while the 45F is unconfigured (commands ignored)")
    d.decouple("3V3_F45", 7); d.C("10uF", "3V3_F45", pkg="C0603"); d.C("10uF", "3V3_F45", pkg="C0603")
    d.tp("SD_CLK")

    # ================================================================ 12F
    d.sheet("fpga12", "fpga12.kicad_sch", "LFE5U-12F-6TG144C adaptive coprocessor: rails, slave-SPI config from the F133, JTAG, RGMII")
    used12 = {"37": "F12_OSC_25M", "121": "F12_LED0", "124": "FPGA12_IRQ_N"}
    for r in eth12:
        sig = r["signal"].replace("TXCTRL", "TXCTL").replace("RXCTRL", "RXCTL")
        used12[r["b_pin"]] = f"ETH_{sig}" if r["direction_a_to_b"] == "F133->12F" else f"ETH_{sig}_E"
    for r in pm("PSRAM12"):
        used12[r["pin"]] = "PSRAM_" + net_of(r["signal"].replace("psram_", "")) + ("_F" if r["signal"] == "psram_sclk" else "")
    cfg12 = {r["signal"]: r["pin"] for r in pm("CFG12", "LFE5U-12F")}
    used12.update({cfg12["FPGA12_SCK"]: "FPGA12_SCK", cfg12["FPGA12_MOSI"]: "FPGA12_MOSI", cfg12["FPGA12_MISO"]: "FPGA12_MISO",
                   cfg12["FPGA12_SS_N"]: "FPGA12_SS_N", cfg12["FPGA12_PROGRAMN"]: "FPGA12_PROGRAMN",
                   cfg12["FPGA12_INITN"]: "FPGA12_INITN", cfg12["FPGA12_DONE"]: "FPGA12_DONE",
                   cfg12["FPGA12_CFG0"]: "FPGA12_CFG0", cfg12["FPGA12_CFG1"]: "GND", cfg12["FPGA12_CFG2"]: "GND",
                   "63": "FPGA12_TCK", "61": "FPGA12_TDI", "60": "FPGA12_TDO", "64": "FPGA12_TMS"})
    t = {}
    for pin, name, et, side in PARTS["ECP5_12F_TQ144"].pins:
        fn = name.split("/")[0]
        if pin in used12:
            t[pin] = used12[pin]
        elif fn == "GND":
            t[pin] = "GND"
        elif fn == "VCC":
            t[pin] = "1V1_F12"
        elif fn == "VCCAUX":
            t[pin] = "2V5_F12"
        elif fn.startswith("VCCIO"):
            t[pin] = "3V3_F12"
    u12 = d.U("ECP5_12F_TQ144", "LFE5U-12F-6TG144C", t)
    for pin, name, et, side in PARTS["ECP5_12F_TQ144"].pins:
        if pin not in t:
            d.nc(u12.ref, pin, "NC pin" if et == "no_connect" else "unused user I/O (weak pull-down after configuration)")
    for r in eth12:
        sig = r["signal"].replace("TXCTRL", "TXCTL").replace("RXCTRL", "RXCTL")
        if r["direction_a_to_b"] == "F133->12F":
            d.R("22R", f"ETH_{sig}_F", f"ETH_{sig}", note=f"F133->12F series R at the F133 ({sig})")
        else:
            d.R("22R", f"ETH_{sig}_E", f"ETH_{sig}", note=f"12F->F133 series R at the 12F ({sig})")
    d.R("100k", "ETH_TXCTL", "GND", note="12F RX idle while F133 PG12 is hi-Z")
    d.R("100k", "ETH_RXCTL", "GND", note="F133 EMAC RX idle while the 12F is off/unconfigured")
    d.tp("ETH_TXCK"); d.tp("ETH_RXCK")
    d.decouple("1V1_F12", 6); d.C("10uF", "1V1_F12", pkg="C0603"); d.C("10uF", "1V1_F12", pkg="C0603")
    d.decouple("2V5_F12", 4); d.C("10uF", "2V5_F12", pkg="C0603")
    d.decouple("3V3_F12", 9)
    for _ in range(3):
        d.C("10uF", "3V3_F12", pkg="C0603")
    # sysCONFIG from the F133 SPI0 through the R8.5-C isolation buffers (boot-strap pins never loaded by the FPGA)
    d.U("LVC1G125", "iso SCK", {"1": "FPGA12_BUS_EN_N", "2": "SPI0_CLK", "3": "GND", "4": "FPGA12_SCK_B", "5": "3V3"})
    d.R("33R", "FPGA12_SCK_B", "FPGA12_SCK", note="CCLK series R")
    d.U("LVC1G125", "iso MOSI", {"1": "FPGA12_BUS_EN_N", "2": "SPI0_MOSI", "3": "GND", "4": "FPGA12_MOSI", "5": "3V3"})
    d.U("LVC1G125", "iso SS", {"1": "FPGA12_BUS_EN_N", "2": "FPGA12_SS_N_F", "3": "GND", "4": "FPGA12_SS_N", "5": "3V3"})
    d.U("LVC1G125", "iso MISO", {"1": "FPGA12_SS_N_F", "2": "FPGA12_MISO", "3": "GND", "4": "SPI0_MISO", "5": "3V3"},
        note="drives PC5 only while the F133 selects the FPGA")
    d.decouple("3V3", 4)
    d.R("10k", "FPGA12_BUS_EN_N", "3V3", note="buffers disabled at reset")
    d.R("10k", "FPGA12_SS_N_F", "3V3", note="FPGA deselected, MISO buffer off at reset")
    d.R("100k", "FPGA12_MOSI", "GND"); d.R("100k", "FPGA12_MISO", "GND")
    d.R("4.7k", "FPGA12_PROGRAMN", "3V3_F12")
    d.R("470R", "FPGA12_PROGRAMN_F", "FPGA12_PROGRAMN", note="F133 PE8 open-drain use")
    d.R("4.7k", "FPGA12_INITN", "3V3_F12"); d.R("4.7k", "FPGA12_DONE", "3V3_F12")
    d.R("4.7k", "FPGA12_SS_N", "3V3_F12"); d.R("4.7k", "FPGA12_CFG0", "3V3_F12", note="CFG[2:0] = 001 slave SPI")
    d.R("1k", "FPGA12_SCK", "3V3_F12")
    d.R("4.7k", "FPGA12_TCK", "GND")
    d.R("4.7k", "FPGA12_TMS", "3V3_F12"); d.R("4.7k", "FPGA12_TDI", "3V3_F12"); d.R("4.7k", "FPGA12_TDO", "3V3_F12")
    d.R("4.7k", "FPGA12_IRQ_N", "3V3_F12", note="open drain to F133 PE5")
    jt = d.U("HDR_2x5_127", "12F JTAG", {"1": "3V3_F12", "2": "FPGA12_TMS", "3": "GND", "4": "FPGA12_TCK", "5": "GND",
                                         "6": "FPGA12_TDO", "8": "FPGA12_TDI", "9": "GND", "10": "FPGA12_PROGRAMN"})
    d.nc(jt.ref, "7", "key")
    d.U("OSC_3225", "25MHz", {"1": "FPGA12_VCC_PG", "2": "GND", "3": "F12_OSC_25M_X", "4": "3V3_F12"},
        note="OE = VCC power-good (bank 6 hot-socket rule)")
    d.R("33R", "F12_OSC_25M_X", "F12_OSC_25M"); d.decouple("3V3_F12")
    d.U("LED", "12F LED", {"1": "GND", "2": "F12_LED0_R"}); d.R("1k", "F12_LED0", "F12_LED0_R")
    d.tp("FPGA12_DONE"); d.tp("FPGA12_PROGRAMN"); d.tp("FPGA12_INITN"); d.tp("FPGA12_SCK")

    # ================================================================ 12F PSRAM
    d.sheet("psram12", "psram12.kicad_sch", "APS3204L 4 MiB QSPI PSRAM on the 12F (3V3_F12)")
    pc = {"1": "PSRAM_CE_N", "2": "PSRAM_SIO1", "3": "PSRAM_SIO2", "4": "GND", "5": "PSRAM_SIO0", "6": "PSRAM_SCLK",
          "7": "PSRAM_SIO3", "8": "3V3_F12"}
    d.U("APS3204L", "APS3204L-3SQNA-SN", pc, note="VDD with the 12F VCCIO (bank 3 not hot-socket safe)")
    d.decouple("3V3_F12"); d.C("1uF", "3V3_F12")
    d.R("22R", "PSRAM_SCLK_F", "PSRAM_SCLK", note="source termination near the FPGA")
    d.R("10k", "PSRAM_CE_N", "3V3_F12", note="CE# tracks VDD during power-up (APS3204L s8)")
    for n in ("PSRAM_SCLK", "PSRAM_SIO0", "PSRAM_SIO1", "PSRAM_SIO2", "PSRAM_SIO3"):
        d.R("100k", n, "GND", note="static idle level")

    # ================================================================ microSD + audio (unchanged R8.5-C)
    d.sheet("sd_audio", "sd_audio.kicad_sch", "microSD game media (not boot), 2x MAX98357A I2S speakers")
    d.U("MICROSD", "microSD", {"1": "SD_D2", "2": "SD_D3", "3": "SD_CMD", "4": "SD_VDD", "5": "SD_CLK", "6": "GND",
                               "7": "SD_D0", "8": "SD_D1", "9": "SD_DET_N", "10": "GND", "11": "GND"})
    d.U("TPS22918", "SD power switch", {"1": "3V3", "2": "GND", "3": "SD_PWR_EN", "4": "SW_SD_CT", "5": "SD_VDD", "6": "SD_VDD"})
    d.C("1nF", "SW_SD_CT"); d.C("10uF", "SD_VDD", pkg="C0603"); d.decouple("SD_VDD")
    d.R("100k", "SD_PWR_EN", "GND")
    d.R("33R", "SD_CLK_F", "SD_CLK")
    for n in ("SD_CMD", "SD_D0", "SD_D1", "SD_D2", "SD_D3"):
        d.R("47k", n, "SD_VDD")
    d.R("10k", "SD_DET_N", "3V3")
    d.tp("SD_VDD"); d.tp("SD_DET_N")
    for side, sdm in (("L", "AMP_EN"), ("R", "AMP_R_SDMODE")):
        u = d.U("MAX98357A", f"MAX98357A {side}", {"1": "I2S_DOUT", "3": "GND", "4": sdm, "7": "VBUS_5V", "8": "VBUS_5V",
                                                   "9": f"SPK_{side}_P", "10": f"SPK_{side}_N", "11": "GND", "14": "I2S_LRCK",
                                                   "15": "GND", "16": "I2S_BCLK", "17": "GND"})
        for p in ("5", "6", "12", "13"):
            d.nc(u.ref, p, "NC")
        d.nc(u.ref, "2", "GAIN_SLOT open = default gain")
        d.C("10uF", "VBUS_5V", pkg="C0805"); d.C("100nF", "VBUS_5V")
        d.U("JST_PH2", f"SPK {side}", {"1": f"SPK_{side}_P", "2": f"SPK_{side}_N", "MP": "GND"})
    d.R("210k", "AMP_EN", "AMP_R_SDMODE", note="right channel (MAX98357A DS Table 6)")
    d.R("100k", "AMP_EN", "GND", note="amps off while F133 in reset")

    # ================================================================ controls + debug
    d.sheet("controls", "controls.kicad_sch", "Game buttons, LEDs, F133 debug UART")
    for b in ("UP", "DOWN", "LEFT", "RIGHT", "A", "B", "X", "Y", "L", "R", "START", "SELECT", "HOME"):
        d.U("SW_B3U", b, {"1": f"BTN_{b}", "2": "GND"}, note="F133 internal pull-up")
    d.U("LED", "STATUS", {"1": "GND", "2": "LED_STATUS_R"}); d.R("1k", "LED_STATUS", "LED_STATUS_R")
    d.U("LED", "ERROR", {"1": "GND", "2": "LED_ERROR_R"}); d.R("1k", "LED_ERROR", "LED_ERROR_R")
    d.U("LED", "3V3", {"1": "GND", "2": "LED_3V3_R"}); d.R("2k", "3V3", "LED_3V3_R")
    d.U("HDR_1x3", "F133 UART0", {"1": "GND", "2": "UART0_TX", "3": "UART0_RX"}, note="3.3 V TTL console")

    for c in d.comps:
        for num, nm, et, side in PARTS[c.part].pins:
            if et == "no_connect" and num not in c.conn and (c.ref, num) not in d.intent_nc:
                d.nc(c.ref, num, "NC per datasheet pin table")
    return d


if __name__ == "__main__":
    dd = build()
    print(len(dd.comps), "components on", len(dd.sheets), "sheets")
