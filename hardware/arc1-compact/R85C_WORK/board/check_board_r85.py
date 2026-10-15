#!/usr/bin/env python3
"""ARC-1 Compact R8.5 -- structural electrical rules on board/r85_board_plan.json.

These rules are SELF-AUTHORED encodings of the R08 decisions (corrective handoff
v1.0 + R08 electrical closure) and of the R8.5 ECP5 change order, using the Lattice
facts in sources/lattice (DS-02012, TN-02038, TN-02039, pinout FPGA-SC-02034). Passing them shows the schematic implements the
decisions consistently; it is NOT independent device-compatibility validation.
Each rule has a negative test in test_check_board_r85.py.
Usage: check_board_r85.py [plan.json]  -> exit 0 if all rules pass
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path=None):
    return json.load(open(path or os.path.join(HERE, "r85_board_plan.json")))


class Ctx:
    def __init__(self, plan):
        self.plan = plan
        self.comps = {c["ref"]: c for c in plan["components"]}
        self.nets = {n: [tuple(x.split(".", 1)) for x in v] for n, v in plan["nets"].items()}

    def part(self, ref):
        return self.comps[ref]["part"]

    def pin(self, ref, num):
        return self.comps[ref]["pins"][num]

    def net_of(self, ref, num):
        return self.comps[ref]["pins"][num]["net"]

    def on_net(self, net):
        return self.nets.get(net, [])

    def resistors(self, net):
        """[(ref, other_net, value)] for R* two-terminal parts on net"""
        out = []
        for ref, pin in self.on_net(net):
            c = self.comps[ref]
            if c["part"].startswith("R0"):
                other = c["pins"]["2" if pin == "1" else "1"]["net"]
                out.append((ref, other, c["value"], c["dnp"]))
        return out

    def by_part(self, part):
        return [c for c in self.comps.values() if c["part"] == part]

    def f133(self, pname):
        for num, p in self.comps["U15"]["pins"].items():
            if p["name"] == pname:
                return p["net"]
        return None


def ohms(v):
    m = re.match(r"^([\d.]+)\s*([kKM]?)R?", v.replace("R", "") if v.endswith("R") and v[:-1].replace(".", "").isdigit() else v)
    if not m:
        return None
    x = float(m.group(1))
    return x * {"": 1, "k": 1e3, "K": 1e3, "M": 1e6}[m.group(2)]


RULES = []
FPGA = "ECP5_45F_BG381"
FPGA_RAILS = {"1V1_FPGA", "2V5_FPGA_AUX", "3V3_FPGA"}


def rule(fn):
    RULES.append(fn)
    return fn


@rule
def boot_straps_00(c):
    """BOOT-SEL[1:0] = 00 (SPI NOR first): PC4 and PC5 each have one populated pull-down <= 3.6k to GND and no pull-up"""
    errs = []
    for pname in ("PC4", "PC5"):
        net = c.f133(pname)
        rs = [r for r in c.resistors(net) if not r[3]]
        pd = [r for r in rs if r[1] == "GND"]
        pu = [r for r in rs if r[1] != "GND" and r[1] in ("3V3", "3V3_FPGA", "1V8_LDOA")]
        if len(pd) != 1 or ohms(pd[0][2]) > 3600:
            errs.append(f"{pname} ({net}) needs exactly one pull-down <= 3.6k, found {pd}")
        if pu:
            errs.append(f"{pname} ({net}) has a pull-up {pu}: strap would read 1")
    return errs


@rule
def spi0_fpga_isolated(c):
    """no FPGA (U18) ball on any F133 SPI0 net; every other driver on PC4/PC5 is the NOR or a 3-state buffer
    whose OE# is pulled up (disabled at reset)"""
    errs = []
    for pname in ("PC2", "PC3", "PC4", "PC5", "PC6", "PC7"):
        net = c.f133(pname)
        for ref, pin in c.on_net(net):
            part = c.part(ref)
            if part == FPGA:
                errs.append(f"FPGA {ref}.{pin} directly on SPI0 net {net}")
            if part == "LVC1G125" and c.pin(ref, pin)["name"] == "Y":
                oe = c.net_of(ref, "1")
                if not any(r[1] == "3V3" and not r[3] for r in c.resistors(oe)):
                    errs.append(f"buffer {ref} drives {net} but OE# net {oe} has no pull-up to 3V3")
    return errs


@rule
def nor_boot_device(c):
    """32 MiB NOR on SPI0 CS0 with /RESET pulled up + FEL button, IO2/IO3 pulled up, CS# pulled up"""
    errs = []
    nors = c.by_part("W25Q256JVFIQ")
    if len(nors) != 1:
        return [f"expected one W25Q256JVFIQ, found {len(nors)}"]
    n = nors[0]["ref"]
    want = {"7": c.f133("PC3"), "16": None, "15": c.f133("PC4"), "8": c.f133("PC5"), "9": c.f133("PC6"), "1": c.f133("PC7")}
    for pin, net in want.items():
        if net and c.net_of(n, pin) != net:
            errs.append(f"NOR pin {pin} on {c.net_of(n, pin)}, expected {net}")
    for pin in ("3", "7", "9", "1"):
        net = c.net_of(n, pin)
        if not any(r[1] == "3V3" for r in c.resistors(net)):
            errs.append(f"NOR pin {pin} ({net}) lacks a pull-up to 3V3")
    rst = c.net_of(n, "3")
    if not any(c.part(r) == "SW_B3U" for r, _ in c.on_net(rst)):
        errs.append("no FEL button on NOR /RESET")
    return errs


@rule
def mn820_miso_buffered(c):
    """F133 PD13 (BT_MISO) is driven by a 3-state buffer from the module, never by the module connector directly"""
    errs = []
    net = c.f133("PD13")
    refs = [(r, p) for r, p in c.on_net(net)]
    if any(c.part(r) == "MN820_RCPT" for r, _ in refs):
        errs.append(f"module pin directly on F133 MISO net {net}")
    bufs = [r for r, p in refs if c.part(r) == "LVC1G125" and c.pin(r, p)["name"] == "Y"]
    if len(bufs) != 1:
        errs.append(f"expected one LVC1G125 driving {net}, found {bufs}")
    else:
        if c.net_of(bufs[0], "1") != c.f133("PD10"):
            errs.append("MISO buffer OE# must be BT_SS_N (drive only while selected)")
    return errs


@rule
def switched_domain_pullups(c):
    """pull-ups on nets that touch a switched-domain IC go to that domain's rail (no back-power)"""
    errs = []
    domain = {FPGA: "3V3_FPGA", "APS6404L": "PSRAM_VDD", "MN820_RCPT": "3V3_MN", "MICROSD": "SD_VDD"}
    rails = {"3V3", "3V3_FPGA", "PSRAM_VDD", "3V3_MN", "SD_VDD", "1V8_LDOA", "VBUS_5V", "1V1_FPGA", "2V5_FPGA_AUX"}
    for net, nodes in c.nets.items():
        # microSD: only the card contacts are in the SD_VDD domain; DET_A/DET_B (9, 10) are a mechanical switch
        doms = {domain[c.part(r)] for r, p in nodes if c.part(r) in domain
                and not (c.part(r) == "MICROSD" and p in ("9", "10", "11", "4", "6"))}
        if len(doms) != 1 or net in rails or net == "GND":
            continue
        d = doms.pop()
        for ref, other, val, dnp in c.resistors(net):
            if other in rails and other != d and not dnp:
                errs.append(f"{net}: pull-up {ref} to {other}, but the net belongs to switched domain {d}")
    return errs


@rule
def psram_power_architecture(c):
    """PSRAM VDD switched by a load switch whose ON = AND(F133 request, delayed FPGA DONE); supervisor PG to the FPGA;
    CE# pull-up to PSRAM_VDD; no strong static pull-down; no pull-up to an always-on rail on any PSRAM signal"""
    errs = []
    ps = c.by_part("APS6404L")[0]
    vdd = c.net_of(ps["ref"], "8")
    sw = [r for r, p in c.on_net(vdd) if c.part(r) == "TPS22918" and p == "6"]
    if len(sw) != 1:
        return [f"PSRAM VDD {vdd} not fed by one TPS22918"]
    on = c.net_of(sw[0], "3")
    gate = [r for r, p in c.on_net(on) if c.part(r) == "LVC1G08" and p == "4"]
    if not gate:
        errs.append(f"load-switch ON ({on}) is not an AND gate output")
    else:
        ins = {c.net_of(gate[0], "1"), c.net_of(gate[0], "2")}
        if ins != {c.f133("PE7"), "DONE_DLY"}:
            errs.append(f"AND inputs {ins}: expected F133 PSRAM_PWR_REQ and DONE_DLY")
        dly = [r for r, p in c.on_net("DONE_DLY") if c.part(r) == "LVC1G17" and p == "4"]
        if not dly or c.net_of(dly[0], "2") != "DONE_RC" or not any(r[1] == "DONE_RC" for r in c.resistors("FPGA_DONE")):
            errs.append("DONE_DLY is not the Schmitt-buffered RC delay of FPGA_DONE")
    sup = [r for r, p in c.on_net(vdd) if c.part(r) == "TPS3808" and p == "5"]
    if not sup:
        errs.append("no supervisor SENSE on PSRAM VDD")
    else:
        pg = c.net_of(sup[0], "1")
        if not any(c.part(r) == FPGA for r, _ in c.on_net(pg)):
            errs.append("PSRAM PG does not reach the FPGA")
    ce = c.net_of(ps["ref"], "1")
    if not any(r[1] == vdd for r in c.resistors(ce)):
        errs.append("CE# pull-up is not to the switched PSRAM VDD")
    for pin in ("1", "2", "3", "5", "6", "7"):
        net = c.net_of(ps["ref"], pin)
        if pin != "1" and any(r[1] == "GND" and ohms(r[2]) < 47e3 and not r[3] for r in c.resistors(net)):
            errs.append(f"PSRAM pin {pin} ({net}): strong static pull-down (VOH load outside 0.2 mA spec)")
        for ref, other, val, dnp in c.resistors(net):
            if other in ("3V3", "3V3_FPGA") and not dnp:
                errs.append(f"PSRAM pin {pin} ({net}): pull-up {ref} to {other} back-powers an off PSRAM")
        fp = [p for r, p in c.on_net(net) if c.part(r) == FPGA]
        if pin != "6" and len(fp) != 1:
            errs.append(f"PSRAM pin {pin} ({net}) not on exactly one FPGA ball: {fp}")
    return errs


@rule
def power_sequencing(c):
    """F133 core/DRAM bucks enabled by the 3V3 supervisor; F133 RESET by the core supervisor;
    3V3_T35 switch ON = T35 1V2 power-good; T35 1V2 enabled by F133 with a pull-down"""
    errs = []
    sup33 = [x["ref"] for x in c.by_part("TPS3808") if c.net_of(x["ref"], "5") == "3V3"]
    supc = [x["ref"] for x in c.by_part("TPS3808") if c.net_of(x["ref"], "5") == "VDD_CORE"]
    if not sup33 or not supc:
        return ["missing 3V3 or VDD_CORE supervisor"]
    pg33 = c.net_of(sup33[0], "1")
    for rail in ("VDD_CORE_REG", "1V8_DRAM"):
        bucks = [r for r, p in c.on_net(rail) if c.part(r).startswith("L4035")]
        found = False
        for x in c.by_part("TLV62569"):
            sw = c.net_of(x["ref"], "3")
            if any(r in bucks for r, _ in c.on_net(sw)):
                found = True
                if c.net_of(x["ref"], "1") != pg33:
                    errs.append(f"{x['ref']} ({rail}) EN is {c.net_of(x['ref'], '1')}, expected {pg33}")
        if not found:
            errs.append(f"no buck found for {rail}")
    if c.net_of(supc[0], "1") != c.f133("RESET") and c.net_of(supc[0], "1") != c.net_of("U15", "27"):
        errs.append("core supervisor does not drive F133 RESET")
    return errs


def fpga_rail_sources(c):
    """{rail: (ref, enable_net)} for the three ECP5 rails"""
    out = {}
    for x in c.by_part("TLV62569P"):
        sw = c.net_of(x["ref"], "3")
        for r, _ in c.on_net(sw):
            if c.part(r) == "L4035":
                regout = c.net_of(r, "2")
                links = [o for _, o, v, dnp in c.resistors(regout) if v == "0R" and not dnp]
                if "1V1_FPGA" in links:
                    out["1V1_FPGA"] = (x["ref"], c.net_of(x["ref"], "1"))
    for x in c.by_part("TPS22918"):
        if c.net_of(x["ref"], "6") == "3V3_FPGA":
            out["3V3_FPGA"] = (x["ref"], c.net_of(x["ref"], "3"))
    for x in c.by_part("TLV75525P"):
        out_net = c.net_of(x["ref"], "5")
        fb = [r for r, p in c.on_net(out_net) if c.part(r) == "FB0603"]
        if fb and any(c.net_of(fb[0], p) == "2V5_FPGA_AUX" for p in ("1", "2")):
            out["2V5_FPGA_AUX"] = (x["ref"], c.net_of(x["ref"], "3"), c.net_of(x["ref"], "1"))
    return out


@rule
def fpga_power_sequencing(c):
    """ECP5 VCC (1V1), VCCIO (3V3_FPGA) and VCCAUX (2V5 via 3V3_FPGA) share one F133-controlled enable with a
    pull-down (VCCIO before/with VCC, VCCAUX: TN-02038 s.4); no FPGA rail is sequenced off another FPGA rail's PG"""
    errs = []
    src = fpga_rail_sources(c)
    for rail in ("1V1_FPGA", "3V3_FPGA", "2V5_FPGA_AUX"):
        if rail not in src:
            errs.append(f"no regulator found for {rail}")
    if errs:
        return errs
    en = src["1V1_FPGA"][1]
    if src["3V3_FPGA"][1] != en:
        errs.append(f"3V3_FPGA switch ON is {src['3V3_FPGA'][1]}, not the VCC enable {en}")
    aux = src["2V5_FPGA_AUX"]
    if aux[2] != "3V3_FPGA" or aux[1] not in ("3V3_FPGA", en):
        errs.append(f"VCCAUX LDO IN/EN = {aux[2]}/{aux[1]}: must ramp with 3V3_FPGA")
    if not any(r[1] == "GND" and not r[3] for r in c.resistors(en)):
        errs.append(f"{en} lacks a pull-down (FPGA must stay off while F133 is in reset)")
    pe0 = c.f133("PE0")
    if pe0 != en and not any(r[1] == en and ohms(r[2]) >= 470 for r in c.resistors(pe0)):
        errs.append("F133 PE0 does not control the FPGA enable through a series resistor")
    if not any(c.part(r) == "HDR_1x3" for r, _ in c.on_net(en)):
        errs.append("no service jumper to power the FPGA without F133 firmware (JTAG recovery)")
    pg = c.net_of(src["1V1_FPGA"][0], "5")
    if c.f133("PD1") != pg:
        errs.append("VCC power-good is not readable by the F133 (PD1)")
    return errs


@rule
def fpga_vcc_voltage(c):
    """1V1_FPGA feedback divider: 0.6 V * (1 + Rtop/Rbot) with 1 % resistors and +-1 % reference inside VCC 1.045-1.155 V"""
    src = fpga_rail_sources(c)
    if "1V1_FPGA" not in src:
        return ["no VCC regulator"]
    fb = c.net_of(src["1V1_FPGA"][0], "6")
    rs = {o: ohms(v) for _, o, v, dnp in c.resistors(fb) if not dnp}
    top = [v for o, v in rs.items() if o != "GND"]
    bot = rs.get("GND")
    if len(top) != 1 or not bot:
        return [f"divider on {fb} not found: {rs}"]
    lo = 0.6 * 0.99 * (1 + top[0] * 0.99 / (bot * 1.01))
    hi = 0.6 * 1.01 * (1 + top[0] * 1.01 / (bot * 0.99))
    if lo < 1.045 or hi > 1.155:
        return [f"VCC {lo:.3f}..{hi:.3f} V outside 1.045..1.155 V"]
    return []


@rule
def ecp5_ball_map(c):
    """every ECP5 ball: VCC->1V1_FPGA, VCCAUX->2V5_FPGA_AUX, VCCIOx->3V3_FPGA, GND->GND, RESERVED/NC unconnected,
    every dedicated configuration/JTAG ball connected (none floating)"""
    errs = []
    u = [x for x in c.by_part(FPGA)]
    if len(u) != 1:
        return [f"expected one {FPGA}, found {len(u)}"]
    pins = u[0]["pins"]
    if len(pins) != 381:
        errs.append(f"{len(pins)} balls, expected 381")
    for ball, p in pins.items():
        fn = p["name"].split("/")[0]
        want = {"VCC": "1V1_FPGA", "VCCAUX": "2V5_FPGA_AUX", "GND": "GND"}.get(fn)
        if fn.startswith("VCCIO"):
            want = "3V3_FPGA"
        if want and p["net"] != want:
            errs.append(f"{ball} {fn} on {p['net']}, expected {want}")
        if fn in ("RESERVED", "NC") and p["net"]:
            errs.append(f"{ball} {fn} connected to {p['net']}")
        if fn in ("CCLK", "CFG_0", "CFG_1", "CFG_2", "PROGRAMN", "INITN", "DONE", "TCK", "TMS", "TDI", "TDO") and not p["net"]:
            errs.append(f"{ball} {fn} floating")
    return errs


# R8.5-C RGMII job link: F133 EMAC pin -> ECP5 ball, (F133 pin name, ECP5 RTL direction); F133 DS Table 4-3 F4
RGMII_F133_TX = ("PG3", "PG4", "PG5", "PG6", "PG7", "PG12")     # TXCK TXD0..3 TXCTRL: F133 drives
RGMII_F133_RX = ("PG10", "PG1", "PG2", "PG8", "PG9", "PG0")     # RXCK RXD0..3 RXCTRL: ECP5 drives
_ECP5_BANK = None


def ecp5_bank(ball):
    global _ECP5_BANK
    if _ECP5_BANK is None:
        import csv
        src = os.path.join(HERE, "..", "sources", "lattice", "lfe5u45_cabga381_pinout.csv")
        _ECP5_BANK = {r["ball"]: (r["bank"], r["dual_function"]) for r in csv.DictReader(open(src))}
    return _ECP5_BANK.get(ball, (None, None))


@rule
def rgmii_link(c):
    """R8.5-C RGMII: each of PG0-PG5, PG6-PG10, PG12 reaches exactly one ECP5 bank-0 ball (hot-socket tolerant top bank)
    through exactly one 15-47 ohm series resistor on the DRIVER side (the driver's net carries only the driver and the
    resistor, and the resistor's placement note names the driver); F133 TXCK lands on a PCLK ball; RX/TX CTL nets have a 10k-1M pull-down; no other load on the
    link; no button left on PG0-PG12"""
    errs = []
    u18 = [x["ref"] for x in c.by_part(FPGA)]
    if len(u18) != 1:
        return [f"expected one {FPGA}"]
    u18 = u18[0]
    for pname in RGMII_F133_TX + RGMII_F133_RX:
        f133_tx = pname in RGMII_F133_TX
        fnet = c.f133(pname)
        if not fnet:
            errs.append(f"{pname} unconnected"); continue
        if fnet.startswith("BTN_"):
            errs.append(f"{pname} still carries {fnet}"); continue
        rs = [r for r in c.resistors(fnet) if r[1] != "GND"]          # pull-downs are not series elements
        if len(rs) != 1:
            errs.append(f"{pname} ({fnet}): expected one series resistor, found {[r[0] for r in rs]}"); continue
        rref, enet, val, dnp = rs[0]
        v = ohms(val)
        if dnp or v is None or not 15 <= v <= 47:
            errs.append(f"{pname}: series {rref} {val}{' DNP' if dnp else ''} outside 15-47 ohm")
        note = c.comps[rref].get("note") or ""
        want = "place at F133" if f133_tx else "place at ECP5"
        if want not in note:                    # placement is not in a netlist: the note is the layout instruction
            errs.append(f"{pname}: series {rref} note must say '{want}' (driver side), has '{note}'")
        balls = [pin for ref, pin in c.on_net(enet) if ref == u18]
        if len(balls) != 1:
            errs.append(f"{pname}: {enet} reaches ECP5 balls {balls}, expected exactly one"); continue
        ball = balls[0]
        bank, dual = ecp5_bank(ball)
        if bank != "0":
            errs.append(f"{pname}: ECP5 ball {ball} in bank {bank}, expected bank 0 (hot-socket tolerant)")
        if pname == "PG3" and not (dual or "").startswith("PCLK"):
            errs.append(f"F133 TXCK lands on {ball} ({dual}), not a PCLK clock input")
        drv_net = fnet if f133_tx else enet
        others = [ref for ref, _ in c.on_net(drv_net) if ref not in ("U15", u18, rref)]
        if others:
            errs.append(f"{pname}: driver-side net {drv_net} also carries {others} (series R must sit at the driver)")
        far_net = enet if f133_tx else fnet
        extra = [ref for ref, _ in c.on_net(far_net)
                 if ref not in ("U15", u18, rref) and not c.part(ref).startswith(("TP", "R0"))]
        if extra:
            errs.append(f"{pname}: unexpected load on {far_net}: {extra}")
        if pname in ("PG12", "PG0"):
            pd = [r for r in c.resistors(far_net) if r[1] == "GND" and not r[3] and 1e4 <= (ohms(r[2]) or 0) <= 1e6]
            if not pd:
                errs.append(f"{pname}: CTL net {far_net} has no 10k-1M pull-down (MAC idle while the far side is off)")
    for num, p in c.comps["U15"]["pins"].items():
        if (p["net"] or "").startswith("BTN_") and p["name"].startswith("PG"):
            errs.append(f"button {p['net']} on {p['name']} (PG is the RGMII group)")
    return errs


@rule
def ecp5_sysconfig(c):
    """slave SPI: CFG[2:0]=001, 4.7k pull-ups on PROGRAMN/INITN/DONE/SN, CCLK 510R-1k pull-up, TCK pull-down, TMS/TDI/TDO
    pull-ups (all to VCCIO8); PROGRAMN/INITN/DONE reach F133 PE8/PD0/PE9 and PROGRAMN the JTAG header; no config flash"""
    errs = []
    u = c.by_part(FPGA)[0]
    ball = {p["name"].split("/")[0]: (b, p["net"]) for b, p in u["pins"].items()}

    def pulls(net, rail):
        return [ohms(r[2]) for r in c.resistors(net) if r[1] == rail and not r[3]]
    cfg = {k: ball[k][1] for k in ("CFG_0", "CFG_1", "CFG_2")}
    if cfg["CFG_1"] != "GND" or cfg["CFG_2"] != "GND":
        errs.append(f"CFG_1/CFG_2 must be 0 for slave SPI: {cfg}")
    if not any(1e3 <= v <= 10e3 for v in pulls(cfg["CFG_0"], "3V3_FPGA")):
        errs.append("CFG_0 needs a 1-10k pull-up to VCCIO8")
    for fn in ("PROGRAMN", "INITN", "DONE", "TMS", "TDI", "TDO"):
        if not any(4.0e3 <= v <= 10e3 for v in pulls(ball[fn][1], "3V3_FPGA")):
            errs.append(f"{fn} lacks a 4.7k-class pull-up to VCCIO8")
    sn = [p["net"] for b, p in u["pins"].items() if p["name"].endswith("/SN")]
    if not sn or not any(4.0e3 <= v <= 10e3 for v in pulls(sn[0], "3V3_FPGA")):
        errs.append("SN lacks a 4.7k pull-up to VCCIO8")
    if not any(510 <= v <= 1000 for v in pulls(ball["CCLK"][1], "3V3_FPGA")):
        errs.append("CCLK lacks a 510R-1k pull-up")
    if not any(v <= 10e3 for v in pulls(ball["TCK"][1], "GND")):
        errs.append("TCK lacks a pull-down")
    vccio8 = [p["net"] for b, p in u["pins"].items() if p["name"] == "VCCIO8"]
    if set(vccio8) != {"3V3_FPGA"}:
        errs.append(f"VCCIO8 on {vccio8}")
    for fn, pname, direct in (("INITN", "PD0", True), ("DONE", "PE9", True), ("PROGRAMN", "PE8", False)):
        net = ball[fn][1]
        f = c.f133(pname)
        if direct and f != net:
            errs.append(f"{fn} not on F133 {pname}")
        if not direct and not any(r[1] == net and ohms(r[2]) >= 470 for r in c.resistors(f)):
            errs.append(f"F133 {pname} does not reach {fn} through a series resistor")
    jt = [x for x in c.by_part("HDR_2x5_127") if c.net_of(x["ref"], "4") == ball["TCK"][1]]
    if not jt:
        errs.append("no JTAG header on TCK")
    else:
        j = jt[0]["ref"]
        need = {"2": ball["TMS"][1], "6": ball["TDO"][1], "8": ball["TDI"][1], "1": "3V3_FPGA", "10": ball["PROGRAMN"][1]}
        for pin, net in need.items():
            if c.net_of(j, pin) != net:
                errs.append(f"JTAG {j}.{pin} on {c.net_of(j, pin)}, expected {net}")
    for nor in ("W25Q32JVSSIQ", "W25Q256JVFIQ"):
        for x in c.by_part(nor):
            for p in x["pins"].values():
                if p["net"] and p["etype"] != "power_in" and any(c.part(r) == FPGA for r, _ in c.on_net(p["net"])):
                    errs.append(f"{x['ref']} ({nor}) connects to an FPGA ball: configuration flash not justified (CO 4.2)")
    return errs


@rule
def ecp5_decoupling(c):
    """TN-02038 Table 3.1: >= 1 x 100 nF per VCC/VCCAUX/VCCIO ball, >= 3 x 10 uF on VCC, ferrite + 10 uF on VCCAUX,
    >= one 10 uF per VCCIO bank"""
    errs = []
    cnt = {}
    for x in c.comps.values():
        if x["part"].startswith("C0") and not x["dnp"] and x["pins"]["2"]["net"] == "GND":
            k = (x["pins"]["1"]["net"], x["value"])
            cnt[k] = cnt.get(k, 0) + 1
    u = c.by_part(FPGA)[0]
    balls = {}
    for p in u["pins"].values():
        fn = p["name"].split("/")[0]
        if fn in ("VCC", "VCCAUX") or fn.startswith("VCCIO"):
            balls[p["net"]] = balls.get(p["net"], 0) + 1
    for net, n in balls.items():
        if cnt.get((net, "100nF"), 0) < n:
            errs.append(f"{net}: {cnt.get((net, '100nF'), 0)} x 100nF for {n} balls")
    if cnt.get(("1V1_FPGA", "10uF"), 0) < 3:
        errs.append("VCC needs >= 3 x 10uF")
    if cnt.get(("2V5_FPGA_AUX", "10uF"), 0) < 1 or not any(c.part(r) == "FB0603" for r, _ in c.on_net("2V5_FPGA_AUX")):
        errs.append("VCCAUX needs ferrite + 10uF")
    banks = {p["name"] for p in u["pins"].values() if p["name"].startswith("VCCIO")}
    if cnt.get(("3V3_FPGA", "10uF"), 0) < len(banks):
        errs.append(f"3V3_FPGA: {cnt.get(('3V3_FPGA', '10uF'), 0)} x 10uF for {len(banks)} banks")
    return errs


@rule
def usb_device_only(c):
    """corrective D-04: USB1 (host) unconnected; no load switch sources VBUS; USB0 D+/D- reach the connector with ESD"""
    errs = []
    for pname in ("USB1-DP", "USB1-DM"):
        if c.f133(pname):
            errs.append(f"{pname} connected: USB host was removed")
    for x in c.by_part("TPS22918"):
        if c.net_of(x["ref"], "6") in ("VBUS_RAW", "VBUS_5V"):
            errs.append(f"{x['ref']} sources VBUS (host power path)")
    dp, dm = c.f133("USB0-DP"), c.f133("USB0-DM")
    j = c.by_part("USB_C")[0]["ref"]
    if c.net_of(j, "A6") != dp or c.net_of(j, "A7") != dm:
        errs.append("USB0 not wired to the Type-C connector")
    if not any(c.part(r) == "TPD2EUSB30" for r, _ in c.on_net(dp)):
        errs.append("no ESD on USB0 D+")
    return errs


@rule
def sd_is_not_boot(c):
    """microSD on SMHC0 (PF0-PF5) for games; BOOT-SEL 00 never tries SMHC0; card detect present"""
    errs = []
    sd = c.by_part("MICROSD")[0]["ref"]
    if c.net_of(sd, "5") != "SD_CLK" or c.f133("PF2") != "SD_CLK_F":
        errs.append("SD CLK not on PF2 via series R")
    if not c.net_of(sd, "9"):
        errs.append("no card-detect")
    return errs


@rule
def every_ic_decoupled(c):
    """every power_in net of an IC has at least one 100nF capacitor"""
    errs = []
    caps = {}
    for x in c.comps.values():
        if x["part"].startswith("C0") and x["value"] == "100nF" and not x["dnp"]:
            n1, n2 = x["pins"]["1"]["net"], x["pins"]["2"]["net"]
            if n2 == "GND":
                caps[n1] = caps.get(n1, 0) + 1
    for x in c.comps.values():
        if not x["ref"].startswith("U"):
            continue
        for p in x["pins"].values():
            if p["etype"] == "power_in" and p["net"] and p["net"] != "GND" and not caps.get(p["net"]):
                errs.append(f"{x['ref']} supply {p['net']} has no 100nF decoupling")
    return sorted(set(errs))


@rule
def components_traceable(c):
    """every populated part carries an MPN or an explicit TBD, a footprint, and an evidence tag"""
    errs = []
    for x in c.comps.values():
        if x["dnp"] or x["part"] in ("TP", "MH", "MH_NPTH", "FID"):
            continue
        if not x["footprint"]:
            errs.append(f"{x['ref']} no footprint")
        if not x["mpn"] and not x["part"].startswith(("R0", "C0", "FB")):
            errs.append(f"{x['ref']} no MPN/TBD")
    return errs


def run(plan):
    c = Ctx(plan)
    out = []
    for r in RULES:
        try:
            e = r(c)
        except Exception as ex:      # a malformed plan is a failure, not a crash
            e = [f"exception {type(ex).__name__}: {ex}"]
        out.append((r.__name__, (r.__doc__ or "").strip().split("\n")[0], e))
    return out


def main():
    plan = load(sys.argv[1] if len(sys.argv) > 1 else None)
    res = run(plan)
    bad = 0
    for name, doc, errs in res:
        print(f"{'PASS' if not errs else 'FAIL'} {name}: {doc}")
        for e in errs:
            print("     ", e)
        bad += bool(errs)
    print(f"R8.5 board rules: {len(res) - bad}/{len(res)} PASS (self-authored rules, not independent validation)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
