"""ARC-1 Compact R8.5 (ECP5-45F change order; from R08) -- the board as code: components, values and nets per sheet.

This file is the single electrical source. gen_kicad.py turns it into the
native KiCad 9 hierarchical schematic; export_plan.py turns it into
board/r85_board_plan.json for the rule checker and the 1:1 cross-check.

Status: SELECTED_UNVERIFIED engineering capture. No board exists. Values marked
'calc:' are derived in docs/POWER_TREE_AND_RESET.md / analysis scripts.
"""
from parts import PARTS

# SLIM4 R26 BOM lines reused as CANDIDATES (same value/package => same MPN/LCSC)
SLIM4_PASSIVES = {
    ("C0402", "100nF"): ("CL05B104KO5NNNC", "Samsung", "C1525"),
    ("C0402", "10nF"): ("CL05B103KB5NNNC", "Samsung", "C15195"),
    ("C0402", "1uF"): ("CL05A105KA5NQNC", "Samsung", "C52923"),
    ("C0402", "220nF"): ("CL05B224KO5NNNC", "Samsung", "C16772"),
    ("C0402", "22pF"): ("0402 C0G 22pF", "TBD", "C1555"),
    ("C0402", "12pF"): ("0402CG120J500NT", "FH", "C1547"),
    ("C0603", "4.7uF"): ("CL10A475KO8NNNC", "Samsung", "C19666"),
    ("C0603", "10uF"): ("CL10A106KP8NNNC", "Samsung", "C19702"),
    ("C0603", "1uF"): ("CL10A105KB8NNNC", "Samsung", "C15849"),
    ("C0805", "10uF"): ("CL21A106KAYNNNE", "Samsung", "C15850"),
    ("C0805", "22uF"): ("CL21A226MQQNNNE", "Samsung", "C5674"),
    ("R0402", "10k"): ("0402WGF1002TCE", "UNI-ROYAL", "C25744"),
    ("R0402", "100k"): ("0402WGF1003TCE", "UNI-ROYAL", "C25741"),
    ("R0402", "0R"): ("0402WGF0000TCE", "UNI-ROYAL", "C17168"),
    ("R0402", "150k"): ("0402WGF1503TCE", "UNI-ROYAL", "C25755"),
    ("R0402", "3.3k"): ("0402WGF3301TCE", "UNI-ROYAL", "C25890"),
    ("R0402", "1.5k"): ("0402WGF1501TCE", "UNI-ROYAL", "C25867"),
    ("R0402", "2k"): ("0402WGF2001TCE", "UNI-ROYAL", "C4109"),
    ("R0402", "470k"): ("0402WGF4703TCE", "UNI-ROYAL", "C25790"),
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
        self.sheets = []          # (name, file, title)
        self.cur = None
        self.counters = {}
        self.intent_nc = {}       # (ref, pin) -> reason for no-connect

    def sheet(self, name, file, title):
        self.sheets.append((name, file, title))
        self.cur = name

    def add(self, ref, part, value, conn, **kw):
        assert all(c.ref != ref for c in self.comps), ref
        p = PARTS[part]
        nums = {x[0] for x in p.pins}
        for k in conn:
            assert k in nums, (ref, part, k)
        c = Comp(ref, part, value, conn, self.cur, **kw)
        self.comps.append(c)
        return c

    def auto(self, prefix):
        n = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = n
        return f"{prefix}{n}"

    def R(self, value, a, b, pkg="R0402", note="", dnp=False, ref=None):
        return self.add(ref or self.auto("R"), pkg, value, {"1": a, "2": b}, note=note, dnp=dnp)

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


def build():
    d = Design()
    for k in ("R", "C", "U", "J", "TP", "SW", "D", "L", "FB", "#FLG", "H", "Y", "X", "F", "FID"):
        d.counters[k] = 0

    # ================================================================ USB-C sink + protection
    d.sheet("usb_power", "usb_power.kicad_sch", "USB-C sink (no host), VBUS protection, USB0 device/FEL")
    d.add("J1", "USB_C", "USB-C receptacle", {
        "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
        "A4": "VBUS_RAW", "A9": "VBUS_RAW", "B4": "VBUS_RAW", "B9": "VBUS_RAW",
        "A5": "USB_CC1", "B5": "USB_CC2", "A6": "USB0_DP", "B6": "USB0_DP", "A7": "USB0_DM", "B7": "USB0_DM"},
        note="sink only: no VBUS source, no host power switch (corrective handoff D-04)")
    d.nc("J1", "A8", "SBU unused"); d.nc("J1", "B8", "SBU unused")
    d.flag("VBUS_RAW")
    d.add("F1", "F1812", "PTC hold>=2.6A", {"1": "VBUS_RAW", "2": "VBUS_5V"}, mpn="TBD (1812 PTC, hold >= 2.6 A, 6 V)",
          mfr="TBD", lcsc="", note="hold current from the VBUS budget (analysis/electrical_margins_r08.py); MPN R09")
    d.add("D1", "TVS_SMF", "SMF5.0A", {"1": "VBUS_5V", "2": "GND"})
    d.flag("VBUS_5V")
    d.C("10uF", "VBUS_5V", pkg="C0805"); d.C("100nF", "VBUS_5V")
    d.add("U1", "TUSB320LAI", "TUSB320LAI", {
        "1": "USB_CC1", "2": "USB_CC2", "3": "GND", "4": "TUSB_VBUS_DET", "7": "USB_CUR_OUT1", "8": "USB_CUR_OUT2",
        "10": "GND", "11": "GND", "12": "3V3"},
        note="GPIO mode (ADDR open), UFP (PORT=GND); OUT1/OUT2 = advertised source current; dead-battery Rd: OPEN")
    d.nc("U1", "5", "ADDR open selects GPIO mode (TUSB320LA DS)")
    d.nc("U1", "6", "INT_N/OUT3 audio-accessory indication unused")
    d.nc("U1", "9", "ID unused (UFP)")
    d.R("910k", "VBUS_RAW", "TUSB_VBUS_DET", note="DS asks 900k: 910k E24 nearest, tolerance check R09")
    d.decouple("3V3")
    d.R("10k", "USB_CUR_OUT1", "3V3"); d.R("10k", "USB_CUR_OUT2", "3V3")
    d.R("5.1k", "USB_CC1", "GND", dnp=True, note="DNP fallback Rd if TUSB320LAI lacks dead-battery Rd (then U1 DNP)")
    d.R("5.1k", "USB_CC2", "GND", dnp=True, note="DNP fallback Rd")
    d.add("U2", "TPD2EUSB30", "TPD2EUSB30", {"1": "USB0_DP", "2": "USB0_DM", "3": "GND"})
    d.R("150k", "VBUS_5V", "VBUS_SENSE"); d.R("200k", "VBUS_SENSE", "GND")
    d.tp("VBUS_5V"); d.tp("USB0_DP", note="FEL/USB debug probe"); d.tp("USB0_DM")

    # ================================================================ power tree
    d.sheet("power", "power.kicad_sch", "Regulators, rail order, supervisors, staged-power links")
    # 3V3 main
    d.add("U3", "TLV62569P", "3V3 2A", {"1": "VBUS_5V", "2": "GND", "3": "SW_3V3", "4": "VBUS_5V", "5": "PG_3V3_BUCK",
                                       "6": "FB_3V3"}, note="calc: 0.6*(1+453k/100k)=3.318 V")
    d.C("10uF", "VBUS_5V", pkg="C0805")
    d.add("L1", "L4035", "2.2uH", {"1": "SW_3V3", "2": "3V3_REG"})
    d.R("453k", "3V3_REG", "FB_3V3"); d.R("100k", "FB_3V3", "GND")
    d.C("22uF", "3V3_REG", pkg="C0805"); d.C("22uF", "3V3_REG", pkg="C0805")
    d.R("100k", "PG_3V3_BUCK", "3V3_REG")
    d.flag("3V3_REG")
    d.R("0R", "3V3_REG", "3V3", pkg="R0603", note="staged power-on link: fit after 3V3_REG verified")
    d.flag("3V3")
    d.tp("3V3_REG"); d.tp("3V3"); d.tp("PG_3V3_BUCK")
    # 3V3 supervisor -> enables F133 core/DRAM bucks (VCC-IO >= 2 ms before core)
    d.add("U4", "TPS3808", "TPS3808G33", {"1": "PG_3V3", "2": "GND", "3": "SUP33_MR_N", "4": "SUP33_CT",
                                          "5": "3V3", "6": "3V3"}, mpn="TPS3808G33DBVR",
          note="VIT 3.07 V +-1.5%; tD = CT/175 + 0.5 ms")
    d.C("2.2nF", "SUP33_CT", note="calc tD = 2.2/175 ms + 0.5 ms = 13.1 ms >= 2 ms (F133 DS 5.12)")
    d.R("100k", "SUP33_MR_N", "3V3"); d.R("10k", "PG_3V3", "3V3")
    d.decouple("3V3")
    # VDD_CORE 0.95 V
    d.add("U5", "TLV62569", "VDD_CORE 0.95V", {"1": "PG_3V3", "2": "GND", "3": "SW_CORE", "4": "VBUS_5V", "5": "FB_CORE"},
          note="calc: 0.6*(1+57.6k/100k)=0.946 V (F133 0.85/0.95/0.99)")
    d.C("10uF", "VBUS_5V", pkg="C0805")
    d.add("L2", "L4035", "2.2uH", {"1": "SW_CORE", "2": "VDD_CORE_REG"})
    d.R("57.6k", "VDD_CORE_REG", "FB_CORE"); d.R("100k", "FB_CORE", "GND")
    d.C("22uF", "VDD_CORE_REG", pkg="C0805"); d.C("22uF", "VDD_CORE_REG", pkg="C0805")
    d.flag("VDD_CORE_REG")
    d.R("0R", "VDD_CORE_REG", "VDD_CORE", pkg="R0603", note="staged power-on link")
    d.flag("VDD_CORE")
    d.tp("VDD_CORE")
    # VCC-DRAM 1.8 V
    d.add("U6", "TLV62569", "1V8_DRAM", {"1": "PG_3V3", "2": "GND", "3": "SW_DRAM", "4": "VBUS_5V", "5": "FB_DRAM"},
          note="calc: 0.6*(1+200k/100k)=1.80 V (F133 VCC-DRAM 1.7/1.8/1.9)")
    d.C("10uF", "VBUS_5V", pkg="C0805")
    d.add("L3", "L4035", "2.2uH", {"1": "SW_DRAM", "2": "1V8_DRAM"})
    d.R("200k", "1V8_DRAM", "FB_DRAM"); d.R("100k", "FB_DRAM", "GND")
    d.C("22uF", "1V8_DRAM", pkg="C0805")
    d.flag("1V8_DRAM")
    d.tp("1V8_DRAM")
    # 1V8 analog LDO
    d.add("U7", "TLV75518P", "1V8_AN", {"1": "3V3", "2": "GND", "3": "3V3", "5": "1V8_AN"})
    d.C("1uF", "3V3"); d.C("1uF", "1V8_AN"); d.tp("1V8_AN")
    # F133 reset supervisor on VDD_CORE, delay >= 64 ms, manual reset button
    d.add("U8", "TPS3808", "TPS3808G09", {"1": "F133_RESET_N", "2": "GND", "3": "RST_BTN_N", "4": "SUPC_CT",
                                          "5": "VDD_CORE", "6": "3V3"}, mpn="TPS3808G09DBVR",
          note="VIT 0.84 V +-1.5%; RESET# held >= 64 ms after rails stable (F133 DS 5.12)")
    d.C("15nF", "SUPC_CT", note="calc tD = 15/175 ms + 0.5 ms = 86 ms >= 64 ms")
    d.R("100k", "RST_BTN_N", "3V3")
    d.R("10k", "F133_RESET_N", "1V8_LDOA", note="RESET is in the VCC-RTC (1.8 V) domain (F133 DS Table 4-2; MangoPi ref)")
    d.add("SW1", "SW_B3U", "RESET", {"1": "RST_BTN_N", "2": "GND"})
    d.tp("F133_RESET_N", note="hold low for external NOR clip programming"); d.tp("PG_3V3")
    # ECP5 rails (R8.5). One shared enable FPGA_PWR_EN starts VCC (1.1 V buck), the VCCIO switch (3V3_FPGA) and,
    # through 3V3_FPGA, the VCCAUX LDO: VCCIO "before or together with" VCC/VCCAUX (TN-02038 s.4); no rail is
    # sequenced off another FPGA rail's PG. Ramps 0.01..10 V/ms (DS Table 3.3): calc in docs/ECP5_POWER_R85.md.
    d.add("U9", "TLV62569P", "1V1_FPGA", {"1": "FPGA_PWR_EN", "2": "GND", "3": "SW_1V1", "4": "VBUS_5V", "5": "FPGA_VCC_PG",
                                         "6": "FB_1V1"},
          note="calc: 0.6*(1+82.5k/100k)=1.095 V (ECP5 VCC 1.045/1.10/1.155 V, DS Table 3.2); soft-start ~1 ms")
    d.C("10uF", "VBUS_5V", pkg="C0805")
    d.add("L4", "L4035", "2.2uH", {"1": "SW_1V1", "2": "1V1_FPGA_REG"})
    d.R("82.5k", "1V1_FPGA_REG", "FB_1V1", note="1 % (E96)"); d.R("100k", "FB_1V1", "GND", note="1 %")
    d.C("22uF", "1V1_FPGA_REG", pkg="C0805"); d.C("22uF", "1V1_FPGA_REG", pkg="C0805")
    d.flag("1V1_FPGA_REG")
    d.R("0R", "1V1_FPGA_REG", "1V1_FPGA", pkg="R0603", note="staged power-on link / ECP5 VCC current measurement")
    d.flag("1V1_FPGA")
    d.R("1k", "FPGA_PWR_EN_F", "FPGA_PWR_EN", note="F133 PE0 drive; lets jumper J11 force the FPGA on for JTAG service")
    d.R("100k", "FPGA_PWR_EN", "GND", note="FPGA unpowered until F133 firmware (or J11) enables it")
    d.R("100k", "FPGA_VCC_PG", "3V3", note="open-drain PG to F133 PD1 (rail-fault diagnosis)")
    d.add("J11", "HDR_1x3", "FPGA power override", {"1": "3V3", "2": "FPGA_PWR_EN", "3": "GND"},
          note="JTAG service without F133 firmware: jumper 1-2 powers all FPGA rails (1k limits PE0 contention)")
    d.tp("1V1_FPGA"); d.tp("FPGA_VCC_PG"); d.tp("FPGA_PWR_EN")
    # 3V3_FPGA: all ECP5 VCCIO banks 0,1,2,3,6,7,8 + oscillator + PSRAM switch input
    d.add("U10", "TPS22918", "3V3_FPGA switch", {"1": "3V3", "2": "GND", "3": "FPGA_PWR_EN", "4": "SW_FPGA_CT", "5": "3V3_FPGA",
                                                "6": "3V3_FPGA"}, note="same enable as VCC: VCCIO with VCC/VCCAUX (TN-02038 s.4)")
    d.C("1nF", "SW_FPGA_CT", note="calc SR = 0.55*1000+30 us/V -> ~1.9 ms ramp = 1.7 V/ms (ECP5: 0.01..10 V/ms)")
    d.C("1uF", "3V3"); d.C("10uF", "3V3_FPGA", pkg="C0603")
    d.tp("3V3_FPGA")
    # VCCAUX 2.5 V: LDO fed from 3V3_FPGA so that it ramps with VCCIO (output tracks the 1.7 V/ms input until regulation)
    d.add("U30", "TLV75525P", "2V5_FPGA_AUX", {"1": "3V3_FPGA", "2": "GND", "3": "3V3_FPGA", "5": "2V5_AUX_REG"},
          note="ECP5 VCCAUX 2.375-2.625 V; ICCAUX 17 mA typ static (DS Table 3.8); dropout margin calc in ECP5_POWER_R85.md")
    d.nc("U30", "4", "NC per datasheet")
    d.C("1uF", "3V3_FPGA"); d.C("1uF", "2V5_AUX_REG")
    d.add("FB2", "FB0603", "ferrite 120R@100MHz", {"1": "2V5_AUX_REG", "2": "2V5_FPGA_AUX"}, mpn="BLM18PG121SN1D (CANDIDATE)",
          note="TN-02038 Table 3.1: 120 ohm ferrite on VCCAUX")
    d.flag("2V5_FPGA_AUX")
    d.tp("2V5_FPGA_AUX")
    # MN820 supply switch (default ON; F133 may cut it for isolation tests)
    d.add("U11", "TPS22918", "3V3_MN switch", {"1": "3V3", "2": "GND", "3": "MN_PWR_EN", "4": "SW_MN_CT", "5": "3V3_MN",
                                               "6": "3V3_MN"}, note="MN820 module input 3.0-3.6 V, 245 mA typ")
    d.C("1nF", "SW_MN_CT"); d.C("1uF", "3V3"); d.C("22uF", "3V3_MN", pkg="C0805")
    d.R("100k", "MN_PWR_EN", "3V3", note="default ON even while F133 is in reset (graphics independent of FPGA)")
    d.tp("3V3_MN")
    # PSRAM supply switch, gated by F133 request AND delayed FPGA DONE
    d.add("U12", "TPS22918", "PSRAM_VDD switch", {"1": "3V3_FPGA", "2": "GND", "3": "PSRAM_EN", "4": "SW_PS_CT",
                                                  "5": "PSRAM_VDD", "6": "PSRAM_VDD"})
    d.C("1nF", "SW_PS_CT"); d.C("1uF", "3V3_FPGA"); d.C("4.7uF", "PSRAM_VDD", pkg="C0603")
    d.add("U13", "LVC1G08", "AND", {"1": "PSRAM_PWR_REQ", "2": "DONE_DLY", "3": "GND", "4": "PSRAM_EN", "5": "3V3"})
    d.decouple("3V3")
    d.R("100k", "PSRAM_PWR_REQ", "GND"); d.R("100k", "PSRAM_EN", "GND")
    d.add("U14", "TPS3808", "TPS3808G30", {"1": "PSRAM_PG", "2": "GND", "3": "PSRAM_SUP_MR_N", "4": "PSRAM_SUP_CT",
                                           "5": "PSRAM_VDD", "6": "3V3_FPGA"}, mpn="TPS3808G30DBVR",
          note="VIT 2.79 V +-1.5% -> min 2.748 V > APS6404L VDDmin 2.7 V")
    d.C("1nF", "PSRAM_SUP_CT"); d.R("100k", "PSRAM_SUP_MR_N", "3V3_FPGA")
    d.R("10k", "PSRAM_PG", "3V3_FPGA")
    d.decouple("3V3_FPGA")
    d.tp("PSRAM_VDD"); d.tp("PSRAM_PG"); d.tp("PSRAM_EN")
    for i in range(4):
        d.tp("GND")
    d.flag("GND")
    d.add("FID1", "FID", "fiducial", {}); d.add("FID2", "FID", "fiducial", {}); d.add("FID3", "FID", "fiducial", {})
    for i in range(1, 5):
        d.add(f"H{i}", "MH", "M2.5", {"1": "GND"})

    # ================================================================ F133
    d.sheet("f133", "f133.kicad_sch", "F133-B SoC: supplies, clock, reset, pin assignment")
    f = {}
    power = {
        "VDD-CORE0": "VDD_CORE", "VDD-CORE1": "VDD_CORE", "VDD-SYS0": "VDD_CORE", "VDD-SYS1": "VDD_CORE", "VDD-SYS2": "VDD_CORE",
        "VCC-IO": "3V3", "VCC-PD": "3V3", "VCC-PE": "3V3", "VCC-PG": "3V3", "VCC-TVOUT": "3V3", "LDO-IN": "3V3",
        "VCC-DRAM0": "1V8_DRAM", "VCC-DRAM1": "1V8_DRAM",
        "VCC-PLL": "1V8_LDOA", "VCC-RTC": "1V8_LDOA", "VDD18-DRAM": "1V8_LDOA", "VCC-LVDS": "1V8_LDOA",
        "LDOA-OUT": "1V8_LDOA", "LDOB-OUT": "F133_LDOB",
        "AVCC": "1V8_AN", "HPVCC": "1V8_AN", "VCC-TVIN": "1V8_AN", "AGND": "GND", "EPAD": "GND",
    }
    gpio = {
        # SPI0: boot NOR + (buffered) ECP5 configuration (sysCONFIG slave SPI) and, after DONE, the ECP5 mailbox
        "PC2": "SPI0_CLK_F", "PC3": "SPI0_CS0_N", "PC4": "SPI0_MOSI", "PC5": "SPI0_MISO", "PC6": "SPI0_IO2", "PC7": "SPI0_IO3",
        # SPI1: BT820 (single-SPI baseline)
        "PD10": "BT_SS_N", "PD11": "BT_SCK_F", "PD12": "BT_MOSI_F", "PD13": "BT_MISO", "PD16": "BT_RST_N_F", "PD17": "BT_INT_N",
        # microSD (games only)
        "PF0": "SD_D1", "PF1": "SD_D0", "PF2": "SD_CLK_F", "PF3": "SD_CMD", "PF4": "SD_D3", "PF5": "SD_D2", "PF6": "SD_DET_N",
        # debug UART0
        "PE2": "UART0_TX", "PE3": "UART0_RX",
        # ECP5 control (R8.5): PE4 SN (config + mailbox CS), PE8 PROGRAMN (open-drain use), PE9 DONE, PD0 INITN
        "PE4": "FPGA_SS_N_F", "PE5": "FPGA_IRQ_N", "PE6": "FPGA_BUS_EN_N", "PE7": "PSRAM_PWR_REQ", "PE8": "FPGA_PROGRAMN_F",
        "PE9": "FPGA_DONE", "PE11": "PSRAM_PG", "PE0": "FPGA_PWR_EN_F", "PD0": "FPGA_INITN", "PD1": "FPGA_VCC_PG",
        # audio I2S2 -> 2x MAX98357A
        "PB4": "I2S_DOUT", "PB5": "I2S_BCLK", "PB6": "I2S_LRCK", "PE10": "AMP_EN",
        # power / USB status
        "PE1": "VBUS_SENSE", "PE12": "USB_CUR_OUT1", "PE13": "USB_CUR_OUT2", "PD21": "MN_PWR_EN", "PD20": "SD_PWR_EN",
        # controls
        "PG0": "BTN_UP", "PG1": "BTN_DOWN", "PG2": "BTN_LEFT", "PG3": "BTN_RIGHT", "PG4": "BTN_A", "PG5": "BTN_B",
        "PG6": "BTN_X", "PG7": "BTN_Y", "PG8": "BTN_L", "PG9": "BTN_R", "PG10": "BTN_START", "PG11": "BTN_SELECT",
        "PG12": "BTN_HOME",
        # LEDs
        "PD18": "LED_STATUS", "PD19": "LED_ERROR",
    }
    analog = {"DXIN": "XTAL24_IN", "DXOUT": "XTAL24_OUT", "RESET": "F133_RESET_N", "USB0-DP": "USB0_DP", "USB0-DM": "USB0_DM",
              "VRA1": "F133_VRA1", "VRA2": "F133_VRA2", "NC": "F133_PIN47_DZQ"}
    nc_why = {
        "REFCLK-OUT": "24 MHz fan-out unused", "X32KIN": "RTC 32k crystal optional (internal RC) -- OPEN: confirm",
        "X32KOUT": "RTC 32k crystal optional", "USB1-DP": "USB1 host: removed (D-04)", "USB1-DM": "USB1 host: removed (D-04)",
        "TVOUT0": "CVBS out unused", "TVIN0": "CVBS in unused", "TVIN1": "CVBS in unused",
        "TVIN-VRP": "CVBS ref unused -- OPEN: datasheet gives no termination", "TVIN-VRN": "CVBS ref unused -- OPEN",
        "MICIN3P": "codec input unused (I2S audio)", "MICIN3N": "codec input unused", "FMINR": "unused", "FMINL": "unused",
        "LINEINR": "unused", "LINEINL": "unused", "HPOUTR": "analog HP out unused: audio = I2S amps (owner decision)",
        "HPOUTL": "analog HP out unused", "HPOUTFB": "unused", "GPADC0": "spare ADC", "TP-X1": "unused", "TP-X2": "unused",
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
    d.add("U15", "F133", "F133-B", conn)
    for num, name, et, side in PARTS["F133"].pins:
        if num not in conn:
            d.nc("U15", num, nc_why.get(name, "spare GPIO"))
    for net, n in (("VDD_CORE", 5), ("3V3", 6), ("1V8_DRAM", 2), ("1V8_LDOA", 4), ("1V8_AN", 3)):
        d.decouple(net, n)
    d.C("10uF", "VDD_CORE", pkg="C0603"); d.C("10uF", "3V3", pkg="C0603"); d.C("4.7uF", "1V8_DRAM", pkg="C0603")
    d.C("4.7uF", "1V8_LDOA", pkg="C0603")
    d.C("2.2uF", "F133_LDOB", pkg="C0603", note="LDOB-OUT unused (DRAM from buck), cap per MangoPi MQ")
    d.C("1uF", "F133_VRA1", note="value per reference design -- OPEN (no Allwinner reference schematic)")
    d.C("1uF", "F133_VRA2", note="value per reference design -- OPEN")
    d.R("240R", "F133_PIN47_DZQ", "GND", dnp=True, note="pin 47: DS says NC, D1s schematic shows DZQ 240R 1% -> DNP option, OPEN")
    d.add("Y1", "XTAL_3225", "24MHz", {"1": "XTAL24_IN", "2": "GND", "3": "XTAL24_OUT", "4": "GND"})
    d.C("12pF", "XTAL24_IN", note="CL match to crystal choice -- R09"); d.C("12pF", "XTAL24_OUT")
    d.tp("UART0_TX"); d.tp("UART0_RX")

    # ================================================================ boot NOR + SPI0 straps + FEL
    d.sheet("boot_nor", "boot_nor.kicad_sch", "32 MiB SPI NOR boot (BOOT-SEL 00), straps, FEL/clip recovery")
    d.add("U16", "W25Q256JVFIQ", "W25Q256JVFIQ", {"1": "SPI0_IO3", "2": "3V3", "3": "NOR_RESET_N", "7": "SPI0_CS0_N",
                                                   "8": "SPI0_MISO", "9": "SPI0_IO2", "10": "GND", "15": "SPI0_MOSI",
                                                   "16": "SPI0_CLK"})
    for p in ("4", "5", "6", "11", "12", "13", "14"):
        d.nc("U16", p, "NC per datasheet")
    d.decouple("3V3"); d.C("1uF", "3V3")
    d.R("22R", "SPI0_CLK_F", "SPI0_CLK", note="source series termination at F133")
    d.R("3.3k", "SPI0_MOSI", "GND", note="BOOT-SEL0 = 0 vs internal PU 12k min: 0.217*VCC < 0.3*VCC")
    d.R("3.3k", "SPI0_MISO", "GND", note="BOOT-SEL1 = 0; NOR DO hi-Z (CS# high) and FPGA MISO buffer hi-Z at sampling")
    d.R("10k", "SPI0_CS0_N", "3V3", note="NOR deselected while F133 in reset")
    d.R("10k", "SPI0_IO2", "3V3", note="QE=1 (IQ): IO2 must not float; xfel drives only PC2-PC5")
    d.R("10k", "SPI0_IO3", "3V3")
    d.R("10k", "NOR_RESET_N", "3V3")
    d.add("SW2", "SW_B3U", "FEL (NOR reset)", {"1": "NOR_RESET_N", "2": "GND"},
          note="hold during F133 reset: NOR unreadable -> BROM falls through (expected USB FEL; NOT documented -> bench)")
    for net in ("SPI0_CLK", "SPI0_MOSI", "SPI0_MISO", "SPI0_CS0_N", "NOR_RESET_N", "SPI0_IO2", "SPI0_IO3"):
        d.tp(net, note="SOIC-16 clip / probe")
    d.add("J2", "HDR_2x5_127", "LA SPI0", {"1": "SPI0_CLK", "2": "GND", "3": "SPI0_MOSI", "4": "GND", "5": "SPI0_MISO",
                                            "6": "GND", "7": "SPI0_CS0_N", "8": "FPGA_SS_N_F", "9": "NOR_RESET_N",
                                            "10": "F133_RESET_N"}, dnp=True,
          note="logic-analyser / external programmer header, DNP pads by default (stub)")

    # ================================================================ MN820 / BT820
    d.sheet("mn820", "mn820.kicad_sch", "MN820 (BT820B + 128 MiB DDR3L) module socket, host SPI1, LVDS to R09 panel")
    rows = PARTS["MN820_RCPT"].pins
    mconn = {}
    for num, name, et, side in rows:
        if name == "GND":
            mconn[num] = "GND"
        elif name == "VCC3V3":
            mconn[num] = "3V3_MN"
    mconn.update({"86": "BT_SCK", "88": "BT_SS_N_M", "90": "BT_MOSI", "84": "BT_MISO_M", "94": "BT_IO2_M", "92": "BT_IO3_M",
                  "96": "BT_INT_N", "98": "BT_RST_N"})
    d.add("J3", "MN820_RCPT", "DF40C-100DS-0.4V(51)", mconn, note="receptacle for MN820 CN1 (DF40C-100DP-0.4V(51))")
    for num, name, et, side in rows:
        if num not in mconn:
            why = "R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md)" if (name.startswith("LVDS_TX") or name in ("DISP", "BKLIT_PWM") or name.startswith("GPIO")) else \
                  "module NC" if name == "NC" else "module function unused in ARC-1 (CPU owns SD/audio/flash)"
            d.nc("J3", num, why)
    d.R("33R", "BT_SCK_F", "BT_SCK"); d.R("33R", "BT_MOSI_F", "BT_MOSI")
    d.R("33R", "BT_SS_N", "BT_SS_N_M"); d.R("33R", "BT_RST_N_F", "BT_RST_N")
    d.R("10k", "BT_SS_N_M", "3V3_MN", note="as VM820C; pull to module rail (no back-power)")
    d.R("10k", "BT_INT_N", "3V3_MN")
    d.R("10k", "BT_RST_N", "GND", note="BT820 held in reset until F133 drives it")
    d.R("10k", "BT_MISO_M", "GND", note="BT820 DS 4.5.1: data lines need pull-downs (VM820C 10k)")
    d.R("10k", "BT_IO2_M", "GND"); d.R("10k", "BT_IO3_M", "GND")
    d.R("47k", "BT_MISO", "GND", note="F133 side: defined level while buffer hi-Z")
    d.add("U17", "LVC1G125", "MISO buffer", {"1": "BT_SS_N", "2": "BT_MISO_M", "3": "GND", "4": "BT_MISO", "5": "3V3"},
          note="RK-MN-VOH fix: module VOH 2.4 V -> buffer VIH 2.0 V; F133 sees VOH >= 2.9 V. Drives only while BT selected.")
    d.decouple("3V3")
    d.decouple("3V3_MN", 2); d.C("10uF", "3V3_MN", pkg="C0603")
    d.add("H5", "MH_NPTH", "MN820 hole", {}); d.add("H6", "MH_NPTH", "MN820 hole", {})
    d.tp("BT_SCK"); d.tp("BT_MISO"); d.tp("BT_INT_N"); d.tp("BT_RST_N")
    d.add("J4", "HDR_2x5_127", "LA SPI1", {"1": "BT_SCK", "2": "GND", "3": "BT_MOSI", "4": "GND", "5": "BT_MISO",
                                            "6": "GND", "7": "BT_SS_N", "8": "BT_INT_N", "9": "BT_RST_N", "10": "GND"},
          dnp=True, note="logic-analyser header, DNP pads by default")

    # ================================================================ ECP5 + isolation + sysCONFIG
    d.sheet("fpga", "fpga_ecp5.kicad_sch", "LFE5U-45F-6BG381C (optional accelerator): rails, sysCONFIG slave SPI, JTAG, SPI0 isolation")
    # user I/O (all banks LVCMOS33 at 3V3_FPGA); LPF is generated from this table (tools/gen_pin_matrix_r85.py)
    used = {
        # bank 6: clock + PSRAM
        "P3": "FPGA_OSC_25M",          # LLC_GPLL0T_IN (PLL reference input)
        "L1": "PSRAM_CE_N", "L2": "PSRAM_SCLK_F", "L3": "PSRAM_SIO0", "M1": "PSRAM_SIO1", "M3": "PSRAM_SIO2",
        "M4": "PSRAM_SIO3", "N1": "PSRAM_PG", "N2": "PSRAM_EN",
        # bank 8: sysCONFIG slave SPI; after DONE the same balls are user I/O for the mailbox (SLAVE_SPI_PORT=DISABLE)
        "U3": "FPGA_SCK", "R1": "FPGA_SCK",      # CCLK (dedicated) + D7 user input: same board net
        "W2": "FPGA_MOSI", "V2": "FPGA_MISO", "T2": "FPGA_SS_N", "R2": "FPGA_HOLDN",
        "W3": "FPGA_PROGRAMN", "V3": "FPGA_INITN", "Y3": "FPGA_DONE",
        "U4": "FPGA_CFG0", "T4": "GND", "R4": "GND",   # CFG[2:0] = 001 slave SPI (TN-02039 Table 4.6)
        "T5": "FPGA_TCK", "R5": "FPGA_TDI", "V4": "FPGA_TDO", "U5": "FPGA_TMS",
        # bank 0 (hot-socket tolerant top bank): IRQ + debug
        "E6": "FPGA_IRQ_N", "A7": "FPGA_LED0", "A8": "FPGA_DBG_TX", "B8": "FPGA_DBG_RX",
    }
    t = {}
    for ball, name, et, side in PARTS["ECP5_45F_BG381"].pins:
        fn = name.split("/")[0]
        if ball in used:
            t[ball] = used[ball]
        elif fn == "GND":
            t[ball] = "GND"
        elif fn == "VCC":
            t[ball] = "1V1_FPGA"
        elif fn == "VCCAUX":
            t[ball] = "2V5_FPGA_AUX"
        elif fn.startswith("VCCIO"):
            t[ball] = "3V3_FPGA"         # every bank powered, unused ones included (TN-02038 3.6; DS Table 3.2 note 1)
    d.add("U18", "ECP5_45F_BG381", "LFE5U-45F-6BG381C", t)
    for ball, name, et, side in PARTS["ECP5_45F_BG381"].pins:
        if ball not in t:
            fn = name.split("/")[0]
            why = "RESERVED: do not connect (ECP5 DS 4.1)" if fn == "RESERVED" else \
                  "NC ball" if et == "no_connect" else \
                  "unused user I/O: tri-stated with weak pull-down after configuration (DS 4.1)"
            d.nc("U18", ball, why)
    # decoupling per TN-02038 Table 3.1/3.2: VCC 3x10uF + 100nF/ball (20), VCCAUX ferrite + 10uF + 100nF/ball (4),
    # VCCIO 10uF + 100nF per ball (18 balls, 7 banks)
    d.decouple("1V1_FPGA", 20)
    for _ in range(3):
        d.C("10uF", "1V1_FPGA", pkg="C0603")
    d.decouple("2V5_FPGA_AUX", 4); d.C("10uF", "2V5_FPGA_AUX", pkg="C0603")
    d.decouple("3V3_FPGA", 18)
    for _ in range(7):
        d.C("10uF", "3V3_FPGA", pkg="C0603", note="one per VCCIO bank 0/1/2/3/6/7/8")
    # sysCONFIG pull-ups to VCCIO8 (= 3V3_FPGA): TN-02038 Tables 6.1-6.3
    d.R("4.7k", "FPGA_PROGRAMN", "3V3_FPGA", note="TN-02038: 4.7k to VCCIO8")
    d.R("470R", "FPGA_PROGRAMN_F", "FPGA_PROGRAMN",
        note="F133 PE8 used open-drain (low or input only): worst case 0.50 V < VIL 0.8 V (analysis/electrical_margins_r85.py)")
    d.R("4.7k", "FPGA_INITN", "3V3_FPGA", note="TN-02038: 4.7k; reads 0 at F133 PD0 while the FPGA is off")
    d.R("4.7k", "FPGA_DONE", "3V3_FPGA", note="TN-02038: 4.7k; reads 0 at F133 PE9 while the FPGA is off")
    d.R("4.7k", "FPGA_SS_N", "3V3_FPGA", note="TN-02039 6.2: SN 4.7k pull-up to VCCIO8")
    d.R("4.7k", "FPGA_CFG0", "3V3_FPGA", note="CFG_0 = 1 (1-10k); CFG_1/CFG_2 tied to GND -> 001 slave SPI")
    d.R("10k", "FPGA_HOLDN", "3V3_FPGA", note="HOLDN inactive (conservative: TN lists HOLDN as optional SSPI input)")
    d.R("1k", "FPGA_SCK", "3V3_FPGA", note="TN-02038 Table 6.2: CCLK 510R-1k pull-up")
    d.R("4.7k", "FPGA_TCK", "GND", note="TCK pull-down 4.7k (no internal pull)")
    d.R("4.7k", "FPGA_TMS", "3V3_FPGA"); d.R("4.7k", "FPGA_TDI", "3V3_FPGA"); d.R("4.7k", "FPGA_TDO", "3V3_FPGA")
    d.R("4.7k", "FPGA_IRQ_N", "3V3_FPGA",
        note="open drain; 4.7k vs ECP5 config-time weak pull-down 150 uA max -> >= 2.6 V; PULLMODE=NONE in user mode")
    # independent JTAG service header (ARM 10-pin 1.27 mm layout; openFPGALoader with any JTAG adapter)
    d.add("J5", "HDR_2x5_127", "ECP5 JTAG", {"1": "3V3_FPGA", "2": "FPGA_TMS", "3": "GND", "4": "FPGA_TCK", "5": "GND",
                                              "6": "FPGA_TDO", "8": "FPGA_TDI", "9": "GND", "10": "FPGA_PROGRAMN"},
          note="pin 1 = VTref (VCCIO8); pin 10 (nRESET position) = PROGRAMN; pin 7 key/NC; see docs/JTAG_RECOVERY_R85.md")
    d.nc("J5", "7", "key position (ARM 10-pin layout)")
    d.add("X1", "OSC_3225", "25MHz", {"1": "3V3_FPGA", "2": "GND", "3": "FPGA_OSC_25M_X", "4": "3V3_FPGA"})
    d.R("33R", "FPGA_OSC_25M_X", "FPGA_OSC_25M"); d.decouple("3V3_FPGA")
    # DONE delay (PSRAM power only after wake-up; GOE precedes the DONE pin with DONE_EX=OFF, TN-02039 s.8)
    d.R("10k", "FPGA_DONE", "DONE_RC", note="calc: tau = (4.7k+10k) * 100nF = 1.5 ms; delay >= 0.5 ms")
    d.C("100nF", "DONE_RC")
    d.R("470R", "DONE_RC", "DONE_DIS")
    d.add("D2", "SCHOTTKY", "BAT54WS", {"1": "FPGA_DONE", "2": "DONE_DIS"}, note="fast discharge when DONE falls (PROGRAMN/reconfigure)")
    d.add("U20", "LVC1G17", "Schmitt", {"2": "DONE_RC", "3": "GND", "4": "DONE_DLY", "5": "3V3_FPGA"})
    d.nc("U20", "1", "NC")
    d.decouple("3V3_FPGA")
    d.R("100k", "DONE_DLY", "GND", note="defined low while 3V3_FPGA is off")
    # SPI0 isolation (unchanged R08 topology): the FPGA can never drive or load the boot-strap pins
    d.add("U21", "LVC1G125", "iso SCK", {"1": "FPGA_BUS_EN_N", "2": "SPI0_CLK", "3": "GND", "4": "FPGA_SCK_B", "5": "3V3"})
    d.R("33R", "FPGA_SCK_B", "FPGA_SCK", note="CCLK series 22-80R near the driver (TN-02038 Table 6.2)")
    d.add("U22", "LVC1G125", "iso MOSI", {"1": "FPGA_BUS_EN_N", "2": "SPI0_MOSI", "3": "GND", "4": "FPGA_MOSI", "5": "3V3"})
    d.add("U23", "LVC1G125", "iso SS", {"1": "FPGA_BUS_EN_N", "2": "FPGA_SS_N_F", "3": "GND", "4": "FPGA_SS_N", "5": "3V3"})
    d.add("U24", "LVC1G125", "iso MISO", {"1": "FPGA_SS_N_F", "2": "FPGA_MISO", "3": "GND", "4": "SPI0_MISO", "5": "3V3"},
          note="drives PC5 only while F133 selects the FPGA (OE# = FPGA_SS_N_F)")
    d.decouple("3V3", 4)
    d.R("10k", "FPGA_BUS_EN_N", "3V3", note="isolation buffers disabled at reset")
    d.R("10k", "FPGA_SS_N_F", "3V3", note="FPGA deselected and MISO buffer off at reset")
    d.R("100k", "FPGA_MOSI", "GND")
    d.R("100k", "FPGA_MISO", "GND", note="buffer input defined when the FPGA is off/unconfigured (MISO tri-stated)")
    d.add("D3", "LED", "FPGA LED", {"1": "GND", "2": "FPGA_LED0_R"}); d.R("1k", "FPGA_LED0", "FPGA_LED0_R")
    d.R("1k", "FPGA_DBG_RX_J", "FPGA_DBG_RX", note="limits injection from an external UART adapter into an unpowered FPGA")
    d.add("J6", "HDR_1x3", "FPGA UART", {"1": "GND", "2": "FPGA_DBG_TX", "3": "FPGA_DBG_RX_J"})
    d.tp("FPGA_DONE"); d.tp("DONE_DLY"); d.tp("FPGA_PROGRAMN"); d.tp("FPGA_INITN"); d.tp("FPGA_OSC_25M"); d.tp("FPGA_SCK")

    # ================================================================ PSRAM
    d.sheet("psram", "psram.kicad_sch", "APS6404L 8 MiB PSRAM: switched VDD (DONE-gated), static pulls")
    d.add("U25", "APS6404L", "APS6404L-3SQR", {"1": "PSRAM_CE_N", "2": "PSRAM_SIO1", "3": "PSRAM_SIO2", "4": "GND",
                                                "5": "PSRAM_SIO0", "6": "PSRAM_SCLK", "7": "PSRAM_SIO3", "8": "PSRAM_VDD"})
    d.decouple("PSRAM_VDD"); d.C("1uF", "PSRAM_VDD")
    d.R("22R", "PSRAM_SCLK_F", "PSRAM_SCLK", note="source termination near the FPGA")
    d.R("10k", "PSRAM_CE_N", "PSRAM_VDD", note="CE# tracks the switched VDD during the ramp (PULLMODE=NONE on the FPGA ball)")
    for n in ("PSRAM_SCLK", "PSRAM_SIO0", "PSRAM_SIO1", "PSRAM_SIO2", "PSRAM_SIO3"):
        d.R("100k", n, "GND", note="static: idle level in user mode, load 34 uA << 0.2 mA VOH test load")
    # R08 U26 (74LVC07 switched 1.5k pull-downs) removed: ECP5 user I/O are tri-stated with weak pull-DOWN during
    # power-up and configuration (DS 4.1; TN-02039 5.2), whereas the T35 had weak pull-ups that could back-power the PSRAM.

    # ================================================================ microSD + audio
    d.sheet("sd_audio", "sd_audio.kicad_sch", "microSD game media (not boot), 2x MAX98357A I2S speakers")
    d.add("J7", "MICROSD", "microSD", {"1": "SD_D2", "2": "SD_D3", "3": "SD_CMD", "4": "SD_VDD", "5": "SD_CLK", "6": "GND",
                                       "7": "SD_D0", "8": "SD_D1", "9": "SD_DET_N", "10": "GND", "11": "GND"})
    d.add("U27", "TPS22918", "SD power switch", {"1": "3V3", "2": "GND", "3": "SD_PWR_EN", "4": "SW_SD_CT", "5": "SD_VDD",
                                                 "6": "SD_VDD"}, note="card power-cycle for recovery; off until firmware")
    d.C("1nF", "SW_SD_CT"); d.C("10uF", "SD_VDD", pkg="C0603"); d.decouple("SD_VDD")
    d.R("100k", "SD_PWR_EN", "GND")
    d.R("33R", "SD_CLK_F", "SD_CLK")
    for n in ("SD_CMD", "SD_D0", "SD_D1", "SD_D2", "SD_D3"):
        d.R("47k", n, "SD_VDD", note="SD pull-ups to the card rail (no back-power when card power is off)")
    d.R("10k", "SD_DET_N", "3V3")
    d.tp("SD_VDD"); d.tp("SD_DET_N")
    d.add("U28", "MAX98357A", "MAX98357A L", {"1": "I2S_DOUT", "3": "GND", "4": "AMP_EN", "7": "VBUS_5V", "8": "VBUS_5V",
                                              "9": "SPK_L_P", "10": "SPK_L_N", "11": "GND", "14": "I2S_LRCK", "15": "GND",
                                              "16": "I2S_BCLK", "17": "GND"}, note="SD_MODE driven high = left channel")
    d.add("U29", "MAX98357A", "MAX98357A R", {"1": "I2S_DOUT", "3": "GND", "4": "AMP_R_SDMODE", "7": "VBUS_5V",
                                              "8": "VBUS_5V", "9": "SPK_R_P", "10": "SPK_R_N", "11": "GND", "14": "I2S_LRCK",
                                              "15": "GND", "16": "I2S_BCLK", "17": "GND"},
          note="SD_MODE via 210k (with internal 100k) = right channel (MAX98357A DS Table 6)")
    for u in ("U28", "U29"):
        for p in ("5", "6", "12", "13"):
            d.nc(u, p, "NC")
        d.nc(u, "2", "GAIN_SLOT open: gain setting per DS Table (R09 pick; open = default)")
    d.R("210k", "AMP_EN", "AMP_R_SDMODE")
    d.R("100k", "AMP_EN", "GND", note="amps in shutdown while F133 in reset")
    d.C("10uF", "VBUS_5V", pkg="C0805"); d.C("100nF", "VBUS_5V"); d.C("10uF", "VBUS_5V", pkg="C0805"); d.C("100nF", "VBUS_5V")
    d.add("J8", "JST_PH2", "SPK L", {"1": "SPK_L_P", "2": "SPK_L_N", "MP": "GND"})
    d.add("J9", "JST_PH2", "SPK R", {"1": "SPK_R_P", "2": "SPK_R_N", "MP": "GND"})

    # ================================================================ controls + debug
    d.sheet("controls", "controls.kicad_sch", "Game buttons, LEDs, debug UART")
    for b in ("UP", "DOWN", "LEFT", "RIGHT", "A", "B", "X", "Y", "L", "R", "START", "SELECT", "HOME"):
        d.add(d.auto("SW") if False else f"SW{len([c for c in d.comps if c.ref.startswith('SW')]) + 1}", "SW_B3U", b,
              {"1": f"BTN_{b}", "2": "GND"}, note="F133 internal pull-up enabled by firmware")
    d.add("D4", "LED", "STATUS", {"1": "GND", "2": "LED_STATUS_R"}); d.R("1k", "LED_STATUS", "LED_STATUS_R")
    d.add("D5", "LED", "ERROR", {"1": "GND", "2": "LED_ERROR_R"}); d.R("1k", "LED_ERROR", "LED_ERROR_R")
    d.add("D6", "LED", "3V3", {"1": "GND", "2": "LED_3V3_R"}); d.R("2k", "3V3", "LED_3V3_R")
    d.add("J10", "HDR_1x3", "F133 UART0", {"1": "GND", "2": "UART0_TX", "3": "UART0_RX"}, note="3.3 V TTL console")
    # pins the manufacturer marks NC are no-connect by definition
    for c in d.comps:
        for num, nm, et, side in PARTS[c.part].pins:
            if et == "no_connect" and num not in c.conn and (c.ref, num) not in d.intent_nc:
                d.nc(c.ref, num, "NC per datasheet pin table")
    return d


if __name__ == "__main__":
    dd = build()
    print(len(dd.comps), "components on", len(dd.sheets), "sheets")
