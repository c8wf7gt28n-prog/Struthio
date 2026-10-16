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
    d.sheet("usb_power", "usb_power.kicad_sch", "Rear USB-C: power input + F133 USB0 device/recovery path (via the USB0 role mux)")
    j1 = d.U("USB_C", "USB-C receptacle", {
        "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
        "A4": "VBUS_RAW", "A9": "VBUS_RAW", "B4": "VBUS_RAW", "B9": "VBUS_RAW",
        "A5": "USB_CC1", "B5": "USB_CC2", "A6": "USBC_DP", "B6": "USBC_DP", "A7": "USBC_DM", "B7": "USBC_DM"},
        note="REAR. Power input (auto-start, no switch) + F133 USB0 device/FEL through U(TS3USB221A) port 1; sink only")
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
    d.U("TPD2EUSB30", "TPD2EUSB30", {"1": "USBC_DP", "2": "USBC_DM", "3": "GND"})
    d.R("150k", "VBUS_5V", "VBUS_SENSE"); d.R("200k", "VBUS_SENSE", "GND")
    d.tp("VBUS_5V"); d.tp("USBC_DP", note="FEL probe"); d.tp("USBC_DM")

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

    # system 3V3 (F133 IO, D213 IO, ADV7513 DVDD_3V, HDMI companion, USB hub + muxes, NORs, eMMC, glue)
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
    d.U("PADS_1x2", "F133 RESET pads", {"1": "RST_BTN_N", "2": "GND"}, dnp=True,
        note="internal fixture pads (handoff: no exterior controls); software restart in normal use")
    d.tp("F133_RESET_N"); d.tp("PG_3V3")
    # D213 core 1.2 V and DRAM 1.5 V (D21x HW guide 2.2.1: >= 500 mA each, external DC-DC, no sequencing requirement)
    buck("D213_CORE", "PG_3V3", "100k", "1V2_D213", "0.6*(1+100k/100k)=1.20 V: CPU 600 MHz / DDR3 672 MHz (HW guide 4.1 item 4); "
         "FB divider top at the D213 decoupling capacitors (4.1 item 3)", link_net=True)
    buck("D213_DRAM", "PG_3V3", "150k", "1V5_D213", "0.6*(1+150k/100k)=1.50 V DDR3 (HW guide 2.2.1)", link_net=True)
    buck("HDMI_1V8", "PG_3V3", "200k", "1V8_HDMI", "0.6*(1+200k/100k)=1.80 V ADV7513 DVDD/AVDD/PVDD/BGVDD (1.71-1.90 V, 256 mW typ)",
         link_net=True)

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
        d.U("HDR_1x3", f"{tag} power override", {"1": "3V3", "2": en_name, "3": "GND"}, dnp=True,
            note="internal fixture: JTAG service without firmware, jumper 1-2 powers the FPGA rails (1k limits contention)")
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
        # PF0-PF6 (SMHC0) unused: eMMC removed by D12 (games run from the top USB cartridge)
        "PE2": "UART0_TX", "PE3": "UART0_RX",
        # 12F control (R8.5-C ECP5 control pins, now serving the 12F; hardware/R10_flash_pinmux.csv CFG12)
        "PE4": "FPGA12_SS_N_F", "PE5": "FPGA12_IRQ_N", "PE6": "FPGA12_BUS_EN_N", "PE8": "FPGA12_PROGRAMN_F",
        "PE9": "FPGA12_DONE", "PE0": "FPGA12_PWR_EN_F", "PD0": "FPGA12_INITN", "PD1": "FPGA12_VCC_PG",
        # D213 control (decision D5): open-drain reset and boot-pin hold through U(LVC2G07); ready from D213 PB6
        "PD10": "D213_RESET_REQ_N", "PD11": "D213_BOOT_REQ_N", "PD12": "D213_RDY",
        # I2S2 -> ADV7513 (HDMI embedded audio, D8)
        "PB4": "I2S_DOUT", "PB5": "I2S_BCLK", "PB6": "I2S_LRCK",
        "PE1": "VBUS_SENSE", "PE12": "USB_CUR_OUT1", "PE13": "USB_CUR_OUT2",
        # USB0 role mux select + hub reset (D9); no buttons (handoff s1: controllers are USB)
        "PD2": "USB0_SEL", "PD3": "HUB_RESET_N",
        "PD18": "LED_STATUS", "PD19": "LED_ERROR",
    }
    # F133 <-> 12F RGMII (architecture/R10_interface_matrix.csv): F133 side net ETH_<sig>_F for its outputs
    eth12 = [r for r in MATRIX if r["link"] == "F133<->12F"]
    assert len(eth12) == 12, len(eth12)
    for r in eth12:
        sig = r["signal"].replace("TXCTRL", "TXCTL").replace("RXCTRL", "RXCTL")
        gpio[r["a_pad"]] = f"ETH_{sig}_F" if r["direction_a_to_b"] == "F133->12F" else f"ETH_{sig}"
    analog = {"DXIN": "XTAL24_IN", "DXOUT": "XTAL24_OUT", "RESET": "F133_RESET_N", "USB0-DP": "F133_USB0_DP",
              "USB0-DM": "F133_USB0_DM",
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
    d.U("PADS_1x2", "FEL pads (NOR reset)", {"1": "NOR_RESET_N", "2": "GND"}, dnp=True,
        note="internal fixture: short while USB-C power is applied -> NOR unreadable -> BROM falls through to USB FEL on "
             "the rear USB-C (mux default). Firmware independent; OPEN until bench-proven")
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
            "PA7": "HDMI_INT", "PA8": "HDMI_I2C_SCL", "PA9": "HDMI_I2C_SDA", "PA10": "HDMI_HPD", "PA11": "HDMI_PD",
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
    # RGB888 -> ADV7513 (decision D8, supersedes D6)
    vid = [r for r in MATRIX if r["link"] == "D213->video" and "SELECTED D8" in r["status"]]
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
    d.U("PADS_1x2", "D213 RESET pads", {"1": "D213_RESET_N", "2": "GND"}, dnp=True, note="internal fixture (HW guide 2.2.5)")
    d.U("PADS_1x2", "D213 BOOT pads (PA0)", {"1": "D213_UART0_TX", "2": "GND"}, dnp=True,
        note="internal fixture: short during D213 reset -> USB burn mode (HW guide 2.2.4); normally the F133 does this (D5)")
    d.C("100nF", "D213_RESET_N", dnp=True, note="optional delay cap (<= 4.7 uF allowed)")
    d.U("HDR_1x3", "D213 UART0", {"1": "GND", "2": "D213_UART0_TX", "3": "D213_UART0_RX_J"}, dnp=True,
        note="internal fixture: 3.3 V TTL console")
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

    # ================================================================ internal USB link F133 USB1 host -> D213 USB0
    d.sheet("usb_link", "usb_link.kicad_sch", "Internal: F133 USB1 host -> D213 USB0 device; service mux to internal D213 recovery pads")
    d.U("TS3USB221A", "TS3USB221A", {"1": "F133_USB1_DP", "2": "F133_USB1_DM", "3": "REC_USB_DP", "4": "REC_USB_DM",
                                    "5": "GND", "6": "USBMUX_OE_N", "7": "D213_USB0_DM", "8": "D213_USB0_DP",
                                    "9": "USBMUX_SEL", "10": "3V3"},
        note="S=L (default): D213 USB0 <-> F133 USB1 host. S=H (internal fixture, power off): D213 USB0 <-> internal "
             "recovery pads; the F133 host is then disconnected on both data lines. 90 ohm diff routing.")
    d.decouple("3V3")
    d.R("10k", "USBMUX_SEL", "GND", note="default: internal host link")
    d.R("10k", "USBMUX_OE_N", "GND", note="mux enabled")
    d.U("HDR_1x3", "D213 USB path select", {"1": "3V3", "2": "USBMUX_SEL", "3": "GND"}, dnp=True,
        note="internal fixture only (not reachable from outside): 1-2 = D213 recovery pads")
    d.U("PADS_1x4", "D213 recovery USB pads", {"1": "GND", "2": "REC_USB_DM", "3": "REC_USB_DP", "4": "GND"}, dnp=True,
        note="internal AiBurn fixture (D5). No VBUS pin: the D213 has no VBUS-sense pin; nothing back-feeds the board")
    d.U("TPD2EUSB30", "TPD2EUSB30", {"1": "REC_USB_DP", "2": "REC_USB_DM", "3": "GND"})
    d.tp("D213_USB0_DP"); d.tp("D213_USB0_DM")

    # ================================================================ USB host: F133 USB0 role mux, hub, two front USB-A ports
    d.sheet("usb_host", "usb_host.kicad_sch",
            "F133 USB0 role mux: rear USB-C (device/FEL, default) or USB2514B hub -> 2x front USB-A + top cartridge USB-A")
    d.U("TS3USB221A", "TS3USB221A", {"1": "USBC_DP", "2": "USBC_DM", "3": "HUB_UP_DP", "4": "HUB_UP_DM", "5": "GND",
                                    "6": "USB0MUX_OE_N", "7": "F133_USB0_DM", "8": "F133_USB0_DP", "9": "USB0_SEL",
                                    "10": "3V3"},
        note="D9. S=L (pull-down, at every cold boot and whenever the F133 is in reset): F133 USB0 <-> rear USB-C, so the "
             "boot ROM FEL path never depends on firmware. S=H (F133 PD2, after boot): F133 USB0 host <-> hub; the rear "
             "USB-C data lines are then disconnected (mutual exclusion is physical).")
    d.decouple("3V3")
    d.R("10k", "USB0_SEL", "GND", note="default = rear USB-C device/recovery path")
    d.R("10k", "USB0MUX_OE_N", "GND", note="mux enabled")
    # D12: USB2514B 4-port hub; ports 1-2 front controllers, port 3 top cartridge, port 4 disabled by strap
    hub = {"1": "USBA1_DM", "2": "USBA1_DP", "3": "USBA2_DM", "4": "USBA2_DP", "5": "3V3", "6": "USBA3_DM",
           "7": "USBA3_DP", "8": "HUB_DN4_DIS", "9": "HUB_DN4_DIS", "10": "3V3", "11": "GND",
           "12": "HUB_PRTPWR1", "13": "HUB_OCS1_N", "14": "HUB_CRFILT", "15": "3V3", "16": "HUB_PRTPWR2",
           "17": "HUB_OCS2_N", "18": "HUB_PRTPWR3", "19": "HUB_OCS3_N", "21": "HUB_OCS4_N",
           "22": "HUB_NON_REM1", "23": "3V3", "24": "HUB_CFG_SEL0", "25": "HUB_CFG_SEL1", "26": "HUB_RESET_N",
           "27": "3V3", "28": "HUB_NON_REM0", "29": "3V3", "30": "HUB_UP_DM", "31": "HUB_UP_DP", "32": "HUB_XO",
           "33": "HUB_XI", "34": "HUB_PLLFILT", "35": "HUB_RBIAS", "36": "3V3", "37": "GND"}
    uh = d.U("USB2514B", "USB2514B-I/M2", hub,
             note="D12. Strap mode CFG_SEL[1:0]=00 (Table 5-1): self-powered, individual port power + over-current. "
                  "Port 4 disabled (PRT_DIS_M4/P4 pulled up). VBUS_DET to 3.3 V (permanently attached host). "
                  "TEST to ground (DS 3.2). Held in reset by F133 PD3 until host mode is selected.")
    d.nc(uh.ref, "20", "PRTPWR4: port 4 disabled")
    d.decouple("3V3", 6); d.C("4.7uF", "3V3", pkg="C0603")
    d.C("100nF", "HUB_CRFILT", note="<= 0.1 uF low ESR (DS 3.2)"); d.C("100nF", "HUB_PLLFILT", note="<= 0.1 uF")
    d.R("12k", "HUB_RBIAS", "GND", note="12.0k 1 % (DS 3.2)")
    d.R("10k", "HUB_CFG_SEL0", "GND", note="CFG_SEL0 = 0")
    d.R("100k", "HUB_CFG_SEL1", "GND", note="CFG_SEL1 = 0 (HS_IND pin: 47-100k strap, Table 3-3)")
    d.R("100k", "HUB_NON_REM1", "GND", note="NON_REM[1:0] = 00: all ports removable (47-100k)")
    d.R("100k", "HUB_NON_REM0", "GND")
    d.R("10k", "HUB_DN4_DIS", "3V3", note="port 4 disable strap: both DN4 pins pulled up (DS 3.2)")
    d.R("10k", "HUB_OCS4_N", "3V3", note="unused over-current input held inactive")
    d.R("10k", "HUB_RESET_N", "GND", note="hub in reset until F133 PD3 releases it")
    d.U("XTAL_3225", "24MHz +-50ppm", {"1": "HUB_XI", "2": "GND", "3": "HUB_XO", "4": "GND"},
        note="24 MHz fundamental; load caps per crystal CL")
    d.C("18pF", "HUB_XI", note="match to crystal CL"); d.C("18pF", "HUB_XO")
    for n in ("1", "2", "3"):
        d.R("100k", f"HUB_PRTPWR{n}", "GND", note="BC_EN strap = 0 and port power off in reset")
    for n, side, part, face in (("1", "Player 1", "USB_A", "FRONT"), ("2", "Player 2", "USB_A", "FRONT"),
                                ("3", "game cartridge", "USB_A_V", "TOP")):
        vb = f"USBA{n}_VBUS"
        d.U("TPS2051C", f"USB-A{n} power", {"1": vb, "2": "GND", "3": f"HUB_OCS{n}_N", "4": f"HUB_PRTPWR{n}", "5": "VBUS_5V"},
            note="0.5 A current limit, fault -> hub OCS")
        d.C("1uF", "VBUS_5V", note="IN cap (>= 0.1 uF, DS)")
        d.R("10k", f"HUB_OCS{n}_N", "3V3", note="FLT open drain")
        d.C("100uF", vb, pkg="C1210", note="downstream VBUS bulk (USB 2.0: >= 120 uF per port incl. the 22 uF)")
        d.C("22uF", vb); d.C("100nF", vb)
        d.U("TVS_SMF", "SMF5.0A", {"1": vb, "2": "GND"})
        d.U("TPD2EUSB30", "TPD2EUSB30", {"1": f"USBA{n}_DP", "2": f"USBA{n}_DM", "3": "GND"})
        d.U(part, f"USB-A {side}", {"1": vb, "2": f"USBA{n}_DM", "3": f"USBA{n}_DP", "4": "GND", "5": "GND"},
            note=f"{face}. " + ("Controller port (handoff s1)" if face == "FRONT" else
                                "Game cartridge: games run directly from the USB drive (D12). Vertical, through-hole "
                                "shell; case boss/rib around it for repeated insertion"))
        d.tp(vb)
    d.tp("USB0_SEL"); d.tp("HUB_RESET_N"); d.tp("HUB_UP_DP"); d.tp("HUB_UP_DM")

    # ================================================================ video + audio: ADV7513 + TPD12S016 + HDMI-A (D8)
    d.sheet("video", "video.kicad_sch", "D213 RGB888 + F133 I2S -> ADV7513 HDMI transmitter (embedded audio) -> TPD12S016 -> HDMI-A")
    aconn = {"1": "1V8_ADV_D", "11": "1V8_ADV_D", "31": "1V8_ADV_D", "51": "1V8_ADV_D", "12": "1V8_ADV_P", "13": "1V8_ADV_P",
             "15": "1V8_ADV_A", "19": "1V8_ADV_A", "25": "1V8_ADV_A", "29": "3V3", "65": "GND",
             "3": "ADV_SPDIF", "4": "ADV_MCLK", "5": "I2S_DOUT", "6": "ADV_I2S1", "7": "ADV_I2S2", "8": "ADV_I2S3",
             "9": "I2S_BCLK", "10": "I2S_LRCK", "14": "ADV_REXT", "16": "HDMI_HPD", "22": "HDMI_PD", "28": "HDMI_INT",
             "30": "HDMI_CEC_A", "32": "ADV_CEC_CLK", "33": "HDMI_DDC_SCL", "34": "HDMI_DDC_SDA", "35": "HDMI_I2C_SCL",
             "36": "HDMI_I2C_SDA",
             "17": "TMDS_CK_N", "18": "TMDS_CK_P", "20": "TMDS_D0_N", "21": "TMDS_D0_P", "23": "TMDS_D1_N", "24": "TMDS_D1_P",
             "26": "TMDS_D2_N", "27": "TMDS_D2_P"}
    for r in vid:
        aconn[r["b_pin"]] = r["signal"]
    d.U("ADV7513", "ADV7513BSWZ", aconn,
        note="24-bit RGB 4:4:4 + I2S stereo LPCM (48 kHz baseline, no MCLK needed). Init over I2C from the D213 "
             "(7-bit 0x39 with PD low at power-up): ADI AN-1270 List 4 + Linux adv7511 fixed registers")
    for s in ("LCD_DCLK", "LCD_HS", "LCD_VS", "LCD_DE"):
        d.R("22R", s + "_D", s, note="series R at the D213 (HW guide 4.7 item 3)")
    d.C("10pF", "LCD_DCLK", dnp=True, note="DNP RC filter footprint on the pixel clock")
    d.R("887R", "ADV_REXT", "GND", note="887 ohm 1 % close to pin 14 (ADV7513 HW user guide, quoted; OPEN: read the guide)")
    for n in ("ADV_SPDIF", "ADV_MCLK", "ADV_I2S1", "ADV_I2S2", "ADV_I2S3"):
        d.R("10k", n, "GND", note="unused audio input held low")
    d.R("10k", "ADV_CEC_CLK", "GND", note="CEC unused: clock input held low (OPEN: confirm with the HW user guide)")
    d.U("OSC_3225", "12MHz", {"1": "3V3", "2": "GND", "3": "ADV_CEC_CLK_X", "4": "3V3"}, dnp=True,
        note="DNP: CEC clock (3-100 MHz, 12 MHz default) if CEC is ever used")
    d.R("0R", "ADV_CEC_CLK_X", "ADV_CEC_CLK", dnp=True)
    d.R("10k", "HDMI_PD", "GND", note="PD low at power-up: device active, I2C main map 0x72/0x39 (DS Table 3; Linux pd-gpios)")
    d.R("10k", "HDMI_INT", "3V3", note="INT pull-up (OPEN: output type per HW user guide; D213 may poll over I2C instead)")
    d.R("2.2k", "HDMI_I2C_SCL", "3V3", note="D213 I2C2 -> ADV7513 (5 V tolerant, 400 kHz max)")
    d.R("2.2k", "HDMI_I2C_SDA", "3V3")
    for rail, n in (("1V8_ADV_D", 4), ("1V8_ADV_A", 3), ("1V8_ADV_P", 2)):
        d.U("FB0603", "ferrite 120R@100MHz", {"1": "1V8_HDMI", "2": rail}, mpn="BLM18PG121SN1D (CANDIDATE)",
            note="separate quiet 1.8 V domains (DS: DVDD 'filtered and as quiet as possible')")
        d.C("10uF", rail, pkg="C0603"); d.decouple(rail, n)
        d.flag(rail)
    d.decouple("3V3"); d.C("1uF", "3V3", note="DVDD_3V")
    d.U("TPD12S016", "TPD12S016", {"1": "HDMI_CEC_A", "2": "HDMI_DDC_SCL", "3": "HDMI_DDC_SDA", "4": "HDMI_HPD",
                                  "5": "TPD_LS_OE", "6": "GND", "7": "HDMI_CEC", "8": "HDMI_SCL_5V", "9": "HDMI_SDA_5V",
                                  "10": "HDMI_HPD_5V", "11": "VBUS_5V", "12": "TPD_CT_HPD", "13": "HDMI_5V", "14": "GND",
                                  "15": "TMDS_CK_N", "16": "TMDS_CK_P", "17": "TMDS_D0_N", "18": "TMDS_D0_P", "19": "GND",
                                  "20": "TMDS_D1_N", "21": "TMDS_D1_P", "22": "TMDS_D2_N", "23": "TMDS_D2_P", "24": "3V3"},
        note="TMDS/DDC/CEC/HPD ESD, internal DDC/CEC/HPD pull-ups (SLLSE96F 7.3.15), 55 mA HDMI 5 V load switch")
    d.R("10k", "TPD_LS_OE", "3V3", note="level shifters on"); d.R("10k", "TPD_CT_HPD", "3V3", note="load switch + HPD on")
    d.decouple("3V3"); d.C("100nF", "VBUS_5V"); d.C("100nF", "HDMI_5V")
    jh = d.U("HDMI_A", "HDMI type-A", {"1": "TMDS_D2_P", "2": "GND", "3": "TMDS_D2_N", "4": "TMDS_D1_P", "5": "GND",
                                       "6": "TMDS_D1_N", "7": "TMDS_D0_P", "8": "GND", "9": "TMDS_D0_N", "10": "TMDS_CK_P",
                                       "11": "GND", "12": "TMDS_CK_N", "13": "HDMI_CEC", "15": "HDMI_SCL_5V",
                                       "16": "HDMI_SDA_5V", "17": "GND", "18": "HDMI_5V", "19": "HDMI_HPD_5V", "SH": "GND"},
             note="REAR. HDMI video + embedded stereo audio; TMDS 100 ohm differential")
    d.nc(jh.ref, "14", "Utility/HEAC+ unused")
    d.tp("LCD_DCLK"); d.tp("HDMI_HPD"); d.tp("HDMI_INT"); d.tp("HDMI_5V"); d.tp("I2S_BCLK"); d.tp("I2S_LRCK")

    # ================================================================ 45F
    d.sheet("fpga45", "fpga45.kicad_sch", "LFE5U-45F-6BG381C tile GPU: rails, slave-SPI config from the D213, JTAG, RGMII")
    used45 = {"P3": "F45_OSC_25M", "A7": "F45_LED0"}
    for r in eth45:
        used45[pin_of(r["b_pin"])] = f"G_{r['signal']}" if r["direction_a_to_b"] == "D213->45F" else f"G_{r['signal']}_F"
    for r in pm("SDRAM45"):
        used45[r["pin"]] = "SDR_" + net_of(r["signal"].replace("sd_", "")) + ("_F" if r["signal"] == "sd_clk" else "")
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
        sdc[r["peer_pin"]] = "SDR_" + net_of(r["signal"].replace("sd_", ""))
    for r in pm("SDRAM45_POWER"):
        if r["signal"] in ("VDD", "VDDQ"):
            sdc[r["pin"]] = "3V3_F45"
        elif r["signal"] in ("VSS", "VSSQ"):
            sdc[r["pin"]] = "GND"
    us = d.U("AS4C16M16SA", "AS4C16M16SA-6TIN", sdc, note="powered with the 45F VCCIO (banks 2/3 not hot-socket safe)")
    d.nc(us.ref, "40", "NC must remain unconnected")
    d.R("22R", "SDR_CLK_F", "SDR_CLK", note="clock source series R at the 45F; phase calibrated (fpga45/rtl/sdram_cal.sv)")
    d.R("10k", "SDR_CKE", "GND", note="CKE low while the 45F is unconfigured (commands ignored)")
    d.decouple("3V3_F45", 7); d.C("10uF", "3V3_F45", pkg="C0603"); d.C("10uF", "3V3_F45", pkg="C0603")
    d.tp("SDR_CLK")

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
    # R10 change vs R8.5-C: the three F133->FPGA buffers are powered from 3V3_F12 (Ioff), so an enabled bus can never
    # back-power the unpowered FPGA rail through the bank-8 pull-ups; with 3V3_F12 off their inputs are hi-Z and never
    # load the F133 boot-strap pins. The MISO buffer drives an F133 strap pin and therefore stays on 3V3.
    for src, dst, nm in (("SPI0_CLK", "FPGA12_SCK_B", "iso SCK"), ("SPI0_MOSI", "FPGA12_MOSI", "iso MOSI"),
                         ("FPGA12_SS_N_F", "FPGA12_SS_N", "iso SS")):
        d.U("LVC1G125", nm, {"1": "FPGA12_BUS_EN_N", "2": src, "3": "GND", "4": dst, "5": "3V3_F12"},
            note="Ioff: powered with the FPGA it drives")
    d.R("33R", "FPGA12_SCK_B", "FPGA12_SCK", note="CCLK series R")
    d.decouple("3V3_F12", 3)
    d.U("LVC1G125", "iso MISO", {"1": "FPGA12_SS_N_F", "2": "FPGA12_MISO", "3": "GND", "4": "SPI0_MISO", "5": "3V3"},
        note="drives PC5 only while the F133 selects the FPGA")
    d.decouple("3V3")
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

    # ================================================================ internal debug + indicators (no exterior controls)
    d.sheet("debug", "debug.kicad_sch", "Internal: status LEDs, F133 UART0 fixture header")
    d.U("LED", "STATUS", {"1": "GND", "2": "LED_STATUS_R"}); d.R("1k", "LED_STATUS", "LED_STATUS_R")
    d.U("LED", "ERROR", {"1": "GND", "2": "LED_ERROR_R"}); d.R("1k", "LED_ERROR", "LED_ERROR_R")
    d.U("LED", "3V3", {"1": "GND", "2": "LED_3V3_R"}); d.R("2k", "3V3", "LED_3V3_R")
    d.U("HDR_1x3", "F133 UART0", {"1": "GND", "2": "UART0_TX", "3": "UART0_RX"}, dnp=True, note="internal fixture: 3.3 V TTL console")

    for c in d.comps:
        for num, nm, et, side in PARTS[c.part].pins:
            if et == "no_connect" and num not in c.conn and (c.ref, num) not in d.intent_nc:
                d.nc(c.ref, num, "NC per datasheet pin table")
    return d


if __name__ == "__main__":
    dd = build()
    print(len(dd.comps), "components on", len(dd.sheets), "sheets")
