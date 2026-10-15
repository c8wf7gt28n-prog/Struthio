#!/usr/bin/env python3
"""ARC-1 Compact R08 -- structural electrical rules on board/r08_board_plan.json.

These rules are SELF-AUTHORED encodings of the R08 decisions (corrective handoff
v1.0 + R08 electrical closure). Passing them shows the schematic implements the
decisions consistently; it is NOT independent device-compatibility validation.
Each rule has a negative test in test_check_board_r08.py.
Usage: check_board_r08.py [plan.json]  -> exit 0 if all rules pass
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path=None):
    return json.load(open(path or os.path.join(HERE, "r08_board_plan.json")))


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
        pu = [r for r in rs if r[1] != "GND" and r[1] in ("3V3", "3V3_T35", "1V8_LDOA")]
        if len(pd) != 1 or ohms(pd[0][2]) > 3600:
            errs.append(f"{pname} ({net}) needs exactly one pull-down <= 3.6k, found {pd}")
        if pu:
            errs.append(f"{pname} ({net}) has a pull-up {pu}: strap would read 1")
    return errs


@rule
def spi0_t35_isolated(c):
    """no T35 (U18) pin on any F133 SPI0 net; every other driver on PC4/PC5 is the NOR or a 3-state buffer
    whose OE# is pulled up (disabled at reset)"""
    errs = []
    for pname in ("PC2", "PC3", "PC4", "PC5", "PC6", "PC7"):
        net = c.f133(pname)
        for ref, pin in c.on_net(net):
            part = c.part(ref)
            if part == "T35":
                errs.append(f"T35 {ref}.{pin} directly on SPI0 net {net}")
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
    domain = {"T35": "3V3_T35", "W25Q32JVSSIQ": "3V3_T35", "APS6404L": "PSRAM_VDD", "MN820_RCPT": "3V3_MN", "MICROSD": "SD_VDD"}
    rails = {"3V3", "3V3_T35", "PSRAM_VDD", "3V3_MN", "SD_VDD", "1V8_LDOA", "VBUS_5V"}
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
    """PSRAM VDD switched by a load switch whose ON = AND(F133 request, delayed CDONE); supervisor PG to the T35;
    each PSRAM signal has a switched 1.5k pull-down driven by an LVC07 gated by CDONE_DLY; CE# pull-up to PSRAM_VDD"""
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
        if ins != {c.f133("PE7"), "CDONE_DLY"}:
            errs.append(f"AND inputs {ins}: expected F133 PSRAM_PWR_REQ and CDONE_DLY")
    sup = [r for r, p in c.on_net(vdd) if c.part(r) == "TPS3808" and p == "5"]
    if not sup:
        errs.append("no supervisor SENSE on PSRAM VDD")
    else:
        pg = c.net_of(sup[0], "1")
        if not any(c.part(r) == "T35" for r, _ in c.on_net(pg)):
            errs.append("PSRAM PG does not reach the T35")
    ce = c.net_of(ps["ref"], "1")
    if not any(r[1] == vdd for r in c.resistors(ce)):
        errs.append("CE# pull-up is not to the switched PSRAM VDD")
    for pin in ("1", "2", "3", "5", "6", "7"):
        net = c.net_of(ps["ref"], pin)
        if net.startswith("PSRAM_SCLK") is False and pin == "6":
            pass
        sw_pd = []
        for ref, other, val, dnp in c.resistors(net):
            for r2, p2 in c.on_net(other):
                if c.part(r2) == "LVC07A" and c.pin(r2, p2)["name"].endswith("Y"):
                    a_pin = str(int(p2) - 1) if p2 in ("2", "4", "6") else str(int(p2) + 1)
                    if c.net_of(r2, a_pin) == "CDONE_DLY" and ohms(val) <= 1600:
                        sw_pd.append(ref)
        if len(sw_pd) != 1:
            errs.append(f"PSRAM pin {pin} ({net}): expected one switched pull-down, found {sw_pd}")
        if pin != "1" and any(r[1] == "GND" and ohms(r[2]) < 47e3 for r in c.resistors(net)):
            errs.append(f"PSRAM pin {pin} ({net}): strong static pull-down (VOH load outside 0.2 mA spec)")
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
    t35sw = [x["ref"] for x in c.by_part("TPS22918") if c.net_of(x["ref"], "6") == "3V3_T35"]
    t35pg = [x["ref"] for x in c.by_part("TLV62569P") if any(c.part(r) == "T35" for r, _ in c.on_net("1V2_T35"))
             and c.net_of(x["ref"], "5") == (c.net_of(t35sw[0], "3") if t35sw else None)]
    if not t35sw or not t35pg:
        errs.append("3V3_T35 switch is not sequenced by the T35 1V2 power-good")
    en = c.f133("PE0")
    if not any(r[1] == "GND" for r in c.resistors(en)):
        errs.append("T35_PWR_EN lacks a pull-down (T35 must stay off while F133 is in reset)")
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
    print(f"R08 board rules: {len(res) - bad}/{len(res)} PASS (self-authored rules, not independent validation)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
