#!/usr/bin/env python3
"""ARC-1 Compact R10 -- cross-checks between independent representations of the board.

  A  KiCad netlist (kicad-cli export of the native schematic)  <->  board plan JSON (design source)
  B  every symbol pin number  <->  pad names of the footprint actually assigned
  C  45F: LPF (constraints/r10_45f.lpf + hardware/lpf/r10_45f_sdram.lpf)  <->  RTL top r10_raster_mem_top ports
     <->  Lattice caBGA381 pin file  <->  schematic ball nets  <->  pin plans
  D  12F: TQFP144 LPF fragments (fpga12/timing/r10_12f_tqfp144.lpf + hardware/lpf/r10_12f_mem_tqfp144.lpf)  <->  RTL
     top r10_support_mem_top ports  <->  Lattice TQFP144 pin file  <->  schematic pin nets
  E  connectivity sanity: no single-pin net; every signal net reaches at least one IC/connector pin (a net that only
     joins passives and test points is almost always a typo)
  F  power domains: every left/right-bank (2/3/6/7) FPGA pin may only meet IC pins powered by that FPGA's switched
     VCCIO rail (ECP5 hot-socket rule, R10_INTERCONNECT_DECISIONS.md); every cross-rail IC-to-IC signal is listed
  G  supply pins: each IC supply pin sits on the rail its datasheet requires (table below)

This proves the representations AGREE and that a set of written rules hold. It does not prove the design is right.
Usage: crosscheck_r10.py <R10_WORK dir> <report.json>
"""
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

R10 = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
STD_FP = os.environ.get("KICAD_FOOTPRINTS", "/usr/share/kicad/footprints")
R85C = os.path.normpath(os.path.join(R10, "..", "R85C_WORK"))
plan = json.load(open(os.path.join(R10, "board", "r10_board_plan.json")))
res = {k: [] for k in ("A_netlist_vs_plan", "B_symbol_vs_footprint", "C_45f_lpf_rtl_schematic",
                       "D_12f_lpf_rtl_schematic", "E_connectivity", "F_power_domains", "G_supply_pins",
                       "H_multi_ic_nets", "I_handoff_rev1_1")}
res["info"] = {}


def fail(sec, msg):
    res[sec].append(msg)


pcomps = {c["ref"]: c for c in plan["components"]}
by_part = {}
for r, c in pcomps.items():
    by_part.setdefault(c["part"], []).append(r)

# ------------------------------------------------------------------ A
root = ET.parse(os.path.join(R10, "cad", "NETLIST.xml")).getroot()
kcomp = {c.get("ref"): c for c in root.find("components")}
knets = {n.get("name"): {f'{x.get("ref")}.{x.get("pin")}' for x in n.findall("node")} for n in root.find("nets")}
for ref in sorted(set(pcomps) ^ set(kcomp)):
    fail("A_netlist_vs_plan", f"component {ref} only in {'plan' if ref in pcomps else 'netlist'}")
for ref, c in pcomps.items():
    if ref in kcomp:
        if (kcomp[ref].findtext("footprint") or "") != c["footprint"]:
            fail("A_netlist_vs_plan", f"{ref} footprint differs")
        if (kcomp[ref].findtext("value") or "") != c["value"]:
            fail("A_netlist_vs_plan", f"{ref} value differs")
named = {k.lstrip("/"): v for k, v in knets.items() if not k.startswith("unconnected-")}
for net, nodes in plan["nets"].items():
    got = named.get(net)
    if got is None:
        fail("A_netlist_vs_plan", f"net {net} missing in netlist")
    elif got != set(nodes):
        fail("A_netlist_vs_plan", f"net {net}: only-plan {sorted(set(nodes) - got)} only-netlist {sorted(got - set(nodes))}")
for net in sorted(set(named) - set(plan["nets"])):
    fail("A_netlist_vs_plan", f"net {net} only in netlist")
nc_plan = {f"{r}.{p}" for r, c in pcomps.items() for p, d in c["pins"].items() if d["net"] is None}
nc_net = set()
for k, v in knets.items():
    if k.startswith("unconnected-"):
        nc_net |= v
for x in sorted(nc_plan ^ nc_net):
    fail("A_netlist_vs_plan", f"no-connect mismatch {x}")
res["info"].update(netlist_components=len(kcomp), named_nets=len(named), no_connect_pins=len(nc_net))


# ------------------------------------------------------------------ B
def fp_pads(fp):
    lib, name = fp.split(":", 1)
    path = (os.path.join(R10, "cad", "symbols-and-footprints", "ARC1_R10.pretty", name + ".kicad_mod") if lib == "ARC1_R10"
            else os.path.join(STD_FP, lib + ".pretty", name + ".kicad_mod"))
    if not os.path.exists(path):
        return None, path
    pads = {a or b for a, b in re.findall(r'\(pad\s+(?:"([^"]*)"|([^\s")]+))', open(path).read())}
    pads.discard("")
    return pads, path


cache, status = {}, {}
for ref, c in sorted(pcomps.items()):
    status[c["footprint_status"]] = status.get(c["footprint_status"], 0) + 1
    fp = c["footprint"]
    if not fp:
        continue
    cache.setdefault(fp, fp_pads(fp))
    pads, path = cache[fp]
    if pads is None:
        fail("B_symbol_vs_footprint", f"{ref}: footprint file not found {path}")
        continue
    pins = set(c["pins"])
    if pins - pads:
        fail("B_symbol_vs_footprint", f"{ref} ({fp}): symbol pins without pad {sorted(pins - pads)}")
    if pads - pins:
        fail("B_symbol_vs_footprint", f"{ref} ({fp}): pads without symbol pin {sorted(pads - pins)}")
res["info"].update(footprints_checked=len(cache), footprint_status_count=status)


# ------------------------------------------------------------------ C / D
def lpf_locs(*paths, commented=False):
    loc, iob = {}, {}
    for p in paths:
        t = open(p).read()
        pre = r"#?\s*" if commented else r""
        for m in re.finditer(pre + r'LOCATE COMP "([^"]+)" SITE "([A-Z]*\d+)"', t):
            loc[m.group(1)] = m.group(2)
        for m in re.finditer(pre + r'IOBUF PORT "([^"]+)" ([^;]+);', t):
            iob[m.group(1)] = m.group(2)
    return loc, iob


def rtl_ports(path, module):
    t = open(path).read()
    hdr = t[t.index("module " + module):]
    hdr = hdr[hdr.index(") (") + 3 if ") (" in hdr[:2000] else hdr.index("(") + 1:hdr.index(");")]
    ports = {}
    for m in re.finditer(r"\b(input|output|inout)\s+wire\s*(\[(\d+):(\d+)\])?\s*(\w+)", hdr):
        rng, msb, lsb, name = m.group(2), m.group(3), m.group(4), m.group(5)
        if rng:
            for i in range(int(lsb), int(msb) + 1):
                ports[f"{name}[{i}]"] = m.group(1)
        else:
            ports[name] = m.group(1)
    return ports


def fpga_check(sec, ref, loc, iob, ports, pinfile, key, allowed_extra):
    pins = pcomps[ref]["pins"]
    pf = {r[key]: r for r in csv.DictReader(open(pinfile))}
    for p in sorted(set(ports) ^ set(loc)):
        fail(sec, f"port {p} only in {'RTL' if p in ports else 'LPF'}")
    for p, site in loc.items():
        if site not in pf:
            fail(sec, f"{p}: {site} not in the pin file")
            continue
        if pf[site]["pin_type"] not in ("IO",):
            fail(sec, f"{p}: {site} is {pf[site]['pin_type']}, not user I/O")
        if not pins.get(site, {}).get("net"):
            fail(sec, f"{p}: schematic pin {site} unconnected")
        if "IO_TYPE=LVCMOS33" not in iob.get(p, ""):
            fail(sec, f"{p}: IOBUF not LVCMOS33")
    sites = set(loc.values())
    for site, d in pins.items():
        if pf.get(site, {}).get("pin_type") == "IO" and d["net"] and d["net"] != "GND" and site not in sites \
                and d["net"] not in allowed_extra:
            fail(sec, f"schematic {site} ({d['net']}) carries a signal but no RTL port")
    return {p: pins[s]["net"] for p, s in loc.items() if s in pins}


ref45 = by_part["ECP5_45F_BG381"][0]
loc45, iob45 = lpf_locs(os.path.join(R10, "fpga45", "constraints", "r10_45f.lpf"),
                        os.path.join(R10, "hardware", "lpf", "r10_45f_sdram.lpf"))
ports45 = rtl_ports(os.path.join(R10, "fpga45", "rtl", "r10_raster_mem_top.sv"), "r10_raster_mem_top")
cfg_dual45 = {"FPGA45_MOSI", "FPGA45_MISO", "FPGA45_SS_N", "FPGA45_HOLDN"}   # sysCONFIG dual-purpose balls (bank 8)
net45 = fpga_check("C_45f_lpf_rtl_schematic", ref45, loc45, iob45, ports45,
                   os.path.join(R85C, "sources", "lattice", "lfe5u45_cabga381_pinout.csv"), "ball", cfg_dual45)
ref12 = by_part["ECP5_12F_TQ144"][0]
loc12, iob12 = lpf_locs(os.path.join(R10, "fpga12", "timing", "r10_12f_tqfp144.lpf"),
                        os.path.join(R10, "hardware", "lpf", "r10_12f_mem_tqfp144.lpf"), commented=True)
ports12 = rtl_ports(os.path.join(R10, "fpga12", "rtl", "r10_support_mem_top.sv"), "r10_support_mem_top")
cfg_dual12 = {"FPGA12_MOSI", "FPGA12_MISO", "FPGA12_SS_N"}
net12 = fpga_check("D_12f_lpf_rtl_schematic", ref12, loc12, iob12, ports12,
                   os.path.join(R10, "architecture", "sources", "lfe5u12_tqfp144_pinout.csv"), "pin", cfg_dual12)
res["info"].update(lpf45_ports=len(loc45), rtl45_ports=len(ports45), lpf12_ports=len(loc12), rtl12_ports=len(ports12))
# directional sanity: an RTL output must not land on a net that is driven by the peer chip's output (series-R naming)
for sec, nets, ports in (("C_45f_lpf_rtl_schematic", net45, ports45), ("D_12f_lpf_rtl_schematic", net12, ports12)):
    for p, net in nets.items():
        drv_side = net.endswith("_F") or net.endswith("_E")          # nets named after the FPGA driver (before series R)
        if ports.get(p) == "input" and drv_side:
            fail(sec, f"RTL input {p} sits on driver-side net {net}")

# ------------------------------------------------------------------ E
PASSIVE = {"R0402", "R0603", "C0402", "C0603", "C0805", "C1210", "PADS_1x2", "PADS_1x4", "FB0603", "L4035", "F1812", "TP", "PWR_FLAG", "MH", "FID", "LED",
           "TVS_SMF", "SCHOTTKY", "SW_B3U"}
for net, nodes in plan["nets"].items():
    if len(nodes) < 2:
        fail("E_connectivity", f"net {net} has a single pin {nodes}")
    parts = {pcomps[n.split(".")[0]]["part"] for n in nodes}
    if not parts - PASSIVE and net != "GND" and not parts & {"L4035", "LED", "FB0603"}:   # regulator output / LED anode / ferrite-fed rail nodes
        fail("E_connectivity", f"net {net} joins only passives/test points/switches: {nodes}")

# ------------------------------------------------------------------ F
banks45 = {r["ball"]: r["bank"] for r in csv.DictReader(open(os.path.join(R85C, "sources", "lattice", "lfe5u45_cabga381_pinout.csv")))}
banks12 = {r["pin"]: r["bank"] for r in csv.DictReader(open(os.path.join(R10, "architecture", "sources", "lfe5u12_tqfp144_pinout.csv")))}
SUPPLY_NAMES = re.compile(r"^(VCC|VDD|DVDD|TVDD|PVDD|VCCA|VCC5V|VIN|VBUS|IN$|VCCIO|VDDQ|LDO-IN)")


def ic_rail(ref):
    """the I/O supply of an IC: the most common non-ground net on its supply pins (FPGAs: per bank)"""
    c = pcomps[ref]
    cnt = {}
    for p, d in c["pins"].items():
        if d["etype"] == "power_in" and d["net"] and d["net"] != "GND" and (SUPPLY_NAMES.match(d["name"]) or d["name"].startswith("VCC")):
            cnt[d["net"]] = cnt.get(d["net"], 0) + 1
    return max(cnt, key=cnt.get) if cnt else None


io_rail = {}
for r, c in pcomps.items():
    if c["part"] in PASSIVE or c["part"].startswith(("HDR", "USB_C", "MICROSD", "JST", "HDMI")):
        continue
    io_rail[r] = ic_rail(r)
io_rail[ref45] = "3V3_F45"
io_rail[ref12] = "3V3_F12"
for r in by_part.get("D213ECV", []) + by_part.get("F133", []):
    io_rail[r] = "3V3"
cross = []
for net, nodes in plan["nets"].items():
    if net == "GND" or net.startswith(("1V", "2V5", "3V3", "VBUS", "VDD", "HDMI_5V")):
        continue
    ics = [n for n in nodes if n.split(".")[0] in io_rail]
    rails = {io_rail[n.split(".")[0]] for n in ics}
    for n in ics:
        ref, pin = n.split(".")
        bank = banks45.get(pin) if ref == ref45 else banks12.get(pin) if ref == ref12 else None
        if bank in ("2", "3", "6", "7"):
            own = io_rail[ref]
            for m in ics:
                if io_rail[m.split(".")[0]] != own:
                    fail("F_power_domains", f"{net}: {ref} bank {bank} pin {pin} meets {m} on rail {io_rail[m.split('.')[0]]}")
    if len(rails) > 1:
        cross.append({"net": net, "pins": sorted(ics), "rails": sorted(r for r in rails if r)})
res["cross_rail_signals"] = cross
res["info"]["cross_rail_signals"] = len(cross)

# ------------------------------------------------------------------ G
EXPECT = {  # part: {pin name: rail}
    "D213ECV": {"VDD11_SYS": "1V2_D213", "VCC_DRAM": "1V5_D213", "VCC33_IO0": "3V3", "VCC33_IO1": "3V3", "GND": "GND"},
    "ECP5_45F_BG381": {"VCC": "1V1_F45", "VCCAUX": "2V5_F45", "VCCIO": "3V3_F45", "GND": "GND"},
    "ECP5_12F_TQ144": {"VCC": "1V1_F12", "VCCAUX": "2V5_F12", "VCCIO": "3V3_F12", "GND": "GND"},
    "AS4C16M16SA": {"VDD": "3V3_F45", "VDDQ": "3V3_F45", "VSS": "GND", "VSSQ": "GND"},
    "APS3204L": {"VDD": "3V3_F12", "VSS": "GND"},
    "ADV7513": {"DVDD": "1V8_ADV_D", "AVDD": "1V8_ADV_A", "PVDD": "1V8_ADV_P", "BGVDD": "1V8_ADV_P", "DVDD_3V": "3V3",
                "EPAD_GND": "GND"},
    "USB2514B": {"VDD33": "3V3", "VDDA33": "3V3", "VSS_EP": "GND"},
    "EMMC_KLMAG1JETD": {"VCCQ": "3V3", "VCC": "3V3", "VSS": "GND"},
    "TPS2051C": {"IN": "VBUS_5V", "GND": "GND"},
    "TPD12S016": {"VCCA": "3V3", "VCC5V": "VBUS_5V", "GND": "GND"},
}
for part, exp in EXPECT.items():
    for ref in by_part.get(part, []):
        for p, d in pcomps[ref]["pins"].items():
            key = d["name"].split("/")[0]
            key = "VCCIO" if key.startswith("VCCIO") else key
            if key in exp and d["net"] != exp[key]:
                fail("G_supply_pins", f"{ref} pin {p} {d['name']} on {d['net']}, expected {exp[key]}")

# ------------------------------------------------------------------ H
# A signal net that reaches three or more ICs/connectors is either a deliberate bus or a naming collision (R10 found
# one: SDRAM and microSD clocks both named SD_CLK). Every such net must be listed here with its reason.
MULTI_OK = {
    "D213_UART0_TX": "PA0 = UART0 TX + boot pin: fixture header + F133 open-drain hold (D5) + fixture pads",
    "D213_RESET_N": "D213 + F133 open-drain driver + fixture pads",
    "F133_RESET_N": "supervisor + F133 + LA header", "FPGA12_BUS_EN_N": "F133 enables three config buffers",
    "FPGA12_PWR_EN": "enable fan-out: VCC buck + VCCIO switch + override header",
    "FPGA45_PWR_EN": "enable fan-out: VCC buck + VCCIO switch + override header",
    "FPGA12_SS_N_F": "F133 SS: SS buffer + MISO buffer OE + LA header", "FPGA12_VCC_PG": "PG: F133 + oscillator OE",
    "FPGA45_VCC_PG": "PG: D213 + oscillator OE", "PG_3V3": "enables the bucks",
    "REC_USB_DM": "fixture pads + ESD + mux", "REC_USB_DP": "fixture pads + ESD + mux",
    "SPI0_CLK": "NOR + config buffer + LA", "SPI0_CS0_N": "F133 + NOR + LA",
    "SPI0_MISO": "NOR + MISO buffer + F133 + LA", "SPI0_MOSI": "NOR + config buffer + F133 + LA",
    "NOR_RESET_N": "NOR + LA header + FEL fixture pads", "RST_BTN_N": "supervisor MR + fixture pads",
    "USBC_DM": "rear USB-C + ESD + USB0 mux", "USBC_DP": "rear USB-C + ESD + USB0 mux",
    "USBA1_DM": "hub + ESD + USB-A", "USBA1_DP": "hub + ESD + USB-A", "USBA2_DM": "hub + ESD + USB-A",
    "USBA2_DP": "hub + ESD + USB-A", "USBA1_VBUS": "switch + TVS + USB-A", "USBA2_VBUS": "switch + TVS + USB-A",
    "USBA3_DM": "hub + ESD + USB-A", "USBA3_DP": "hub + ESD + USB-A", "USBA3_VBUS": "switch + TVS + USB-A",
    "HDMI_HPD": "TPD12S016 HPD_A -> ADV7513 HPD + D213 PA10",
    **{f"TMDS_{s}": "ADV7513 + pass-through ESD + connector" for s in ("CK_N", "CK_P", "D0_N", "D0_P", "D1_N", "D1_P",
                                                                      "D2_N", "D2_P")},
}
for net, nodes in plan["nets"].items():
    if net == "GND" or net.startswith(("1V", "2V5", "3V3", "VBUS", "VDD", "HDMI_5V")):
        continue
    ics = {n.split(".")[0] for n in nodes if pcomps[n.split(".")[0]]["part"] not in PASSIVE}
    if len(ics) >= 3 and net not in MULTI_OK:
        fail("H_multi_ic_nets", f"net {net} reaches {sorted(ics)}: deliberate bus? add it to MULTI_OK with a reason")
for net in MULTI_OK:
    if net not in plan["nets"]:
        fail("H_multi_ic_nets", f"MULTI_OK lists {net}, which no longer exists")

# ------------------------------------------------------------------ I
# Owner change order ARC1_R10_Handoff rev 1.1 as amended by D12 (owner, 2026-10-16): rear USB-C + HDMI, two front
# USB-A controller ports, one TOP USB-A game cartridge (games run from the drive), no eMMC, zero exterior controls,
# HDMI with embedded audio. Exterior = notes start with FRONT/REAR/TOP.
SEC = "I_handoff_rev1_1"
ext = {r: c for r, c in pcomps.items() if c["note"].startswith(("FRONT", "REAR", "TOP"))}
kinds = sorted((c["part"], c["note"].split(".")[0]) for c in ext.values())
if kinds != sorted([("USB_C", "REAR"), ("HDMI_A", "REAR"), ("USB_A", "FRONT"), ("USB_A", "FRONT"), ("USB_A_V", "TOP")]):
    fail(SEC, f"exterior connectors {kinds} != USB-C rear, HDMI rear, 2x USB-A front, USB-A top (D12)")
for r, c in pcomps.items():
    if c["part"] in ("USB_C", "HDMI_A", "USB_A", "USB_A_V", "MICROSD", "JST_PH2") and r not in ext:
        fail(SEC, f"{r} {c['part']} is a connector type that would reach the case but is not declared FRONT/REAR")
    if c["part"].startswith("SW_"):
        fail(SEC, f"{r}: a switch is on the board (no exterior or user switches allowed)")
    if c["part"] in ("PADS_1x2", "PADS_1x4", "HDR_1x3", "HDR_2x5_127") and not c["dnp"] and c["part"] != "HDR_2x5_127":
        fail(SEC, f"{r}: service pads/headers must be DNP fixture features")
for part in ("ADV7513", "USB2514B"):
    if part not in by_part:
        fail(SEC, f"required part {part} missing")
for part in ("EMMC_KLMAG1JETD", "USB2422"):
    if part in by_part:
        fail(SEC, f"{part} present: removed by D12")
hubp = {n.split(".")[0] for k in ("USBA1_DP", "USBA2_DP", "USBA3_DP") for n in plan["nets"].get(k, [])}
if "USB2514B" not in by_part or by_part["USB2514B"][0] not in hubp:
    fail(SEC, "the three USB-A ports must hang off the hub")
if "TFP410" in by_part:
    fail(SEC, "TFP410 (DVI only) present")
adv = pcomps[by_part["ADV7513"][0]]["pins"] if "ADV7513" in by_part else {}
for pin, want in (("5", "I2S_DOUT"), ("9", "I2S_BCLK"), ("10", "I2S_LRCK")):
    if adv.get(pin, {}).get("net") != want or not any(n.startswith(by_part["F133"][0] + ".") for n in plan["nets"].get(want, [])):
        fail(SEC, f"HDMI audio: ADV7513 pin {pin} must carry {want} from the F133 I2S2")
f133 = {d["name"]: d["net"] for d in pcomps[by_part["F133"][0]]["pins"].values()}
if f133.get("USB1-DP") != "F133_USB1_DP" or not any(n.startswith(by_part["TS3USB221A"][0] + ".") or True for n in []):
    pass
usb1 = {n.split(".")[0] for n in plan["nets"].get("F133_USB1_DP", [])}
if not any(pcomps[r]["part"] == "TS3USB221A" for r in usb1):
    fail(SEC, "F133 USB1 must still reach the D213 (through the internal link mux)")
usb0 = {pcomps[n.split(".")[0]]["part"] for n in plan["nets"].get("F133_USB0_DP", [])}
if usb0 != {"F133", "TS3USB221A"}:
    fail(SEC, f"F133 USB0 must go only to the role mux, found {usb0}")
res["info"]["exterior_connectors"] = {r: c["part"] + " " + c["note"].split(".")[0] for r, c in ext.items()}

total = sum(len(v) for k, v in res.items() if k not in ("info", "cross_rail_signals"))
res["result"] = "PASS" if total == 0 else "FAIL"
json.dump(res, open(OUT, "w"), indent=1)
for k, v in res.items():
    if k not in ("info", "result", "cross_rail_signals"):
        print(f"{k}: {len(v)} finding(s)")
        for x in v[:25]:
            print("   ", x)
print("info:", json.dumps(res["info"]))
print("CROSSCHECK", res["result"])
sys.exit(0 if total == 0 else 1)
