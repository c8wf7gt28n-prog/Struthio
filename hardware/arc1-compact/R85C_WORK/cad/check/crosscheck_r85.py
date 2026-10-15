#!/usr/bin/env python3
"""ARC-1 Compact R8.5 -- 1:1 cross-check between independent representations.

  A  KiCad netlist (kicad-cli export of the native schematic)  <->  board plan JSON (design source)
  B  every symbol pin number  <->  the pad names of the footprint actually assigned (KiCad 9 library or ARC1_R85.pretty)
  C  LPF (generated)  <->  schematic U18 balls/nets  <->  Lattice pinout CSV  <->  RTL top-level ports
     <->  nextpnr routed placement (fpga_ecp5/build/repro/routed.json, when present)
  D  firmware board_pins_r85.h  <->  schematic F133 pin/net assignment

This proves the representations AGREE. It does not prove the design is right:
the rules encoded in check_board_r85.py are self-authored (handoff rule).
Usage: crosscheck_r85.py <R85_WORK dir> <report.json>
"""
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

R85 = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
STD_FP = os.environ.get("KICAD_FOOTPRINTS", "/usr/share/kicad/footprints")
plan = json.load(open(os.path.join(R85, "board", "r85_board_plan.json")))
res = {"A_netlist_vs_plan": [], "B_symbol_vs_footprint": [], "C_lpf_vs_schematic_vs_rtl": [],
       "D_firmware_vs_schematic": [], "info": {}}


def fail(sec, msg):
    res[sec].append(msg)


# ------------------------------------------------------------------ A
root = ET.parse(os.path.join(R85, "cad", "NETLIST.xml")).getroot()
kcomp = {c.get("ref"): c for c in root.find("components")}
knets = {}
for n in root.find("nets"):
    knets[n.get("name")] = {f'{x.get("ref")}.{x.get("pin")}' for x in n.findall("node")}
pcomps = {c["ref"]: c for c in plan["components"]}
res["info"]["netlist_components"] = len(kcomp)
res["info"]["plan_components"] = len(pcomps)
for ref in sorted(set(pcomps) ^ set(kcomp)):
    fail("A_netlist_vs_plan", f"component {ref} only in {'plan' if ref in pcomps else 'netlist'}")
for ref, c in pcomps.items():
    if ref in kcomp:
        fp = kcomp[ref].findtext("footprint") or ""
        if fp != c["footprint"]:
            fail("A_netlist_vs_plan", f"{ref} footprint netlist={fp!r} plan={c['footprint']!r}")
        val = kcomp[ref].findtext("value") or ""
        if val != c["value"]:
            fail("A_netlist_vs_plan", f"{ref} value netlist={val!r} plan={c['value']!r}")
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
        if len(v) != 1:
            fail("A_netlist_vs_plan", f"{k} has {len(v)} nodes")
        nc_net |= v
for x in sorted(nc_plan ^ nc_net):
    fail("A_netlist_vs_plan", f"no-connect mismatch {x}")
res["info"]["named_nets"] = len(named)
res["info"]["no_connect_pins"] = len(nc_net)


# ------------------------------------------------------------------ B
def fp_pads(fp):
    lib, name = fp.split(":", 1)
    if lib == "ARC1_R85":
        path = os.path.join(R85, "cad", "symbols-and-footprints", "ARC1_R85.pretty", name + ".kicad_mod")
    else:
        path = os.path.join(STD_FP, lib + ".pretty", name + ".kicad_mod")
    if not os.path.exists(path):
        return None, path
    t = open(path).read()
    pads = {a or b for a, b in re.findall(r'\(pad\s+(?:"([^"]*)"|([^\s")]+))', t)}   # quoted or legacy unquoted
    pads.discard("")
    return pads, path


fp_cache = {}
fp_status_count = {}
for ref, c in sorted(pcomps.items()):
    fp = c["footprint"]
    fp_status_count[c["footprint_status"]] = fp_status_count.get(c["footprint_status"], 0) + 1
    if not fp:
        continue
    if fp not in fp_cache:
        fp_cache[fp] = fp_pads(fp)
    pads, path = fp_cache[fp]
    if pads is None:
        fail("B_symbol_vs_footprint", f"{ref}: footprint file not found {path}")
        continue
    pins = set(c["pins"])
    if pins - pads:
        fail("B_symbol_vs_footprint", f"{ref} ({fp}): symbol pins without pad {sorted(pins - pads)}")
    if pads - pins:
        fail("B_symbol_vs_footprint", f"{ref} ({fp}): pads without symbol pin {sorted(pads - pins)}")
res["info"]["footprints_checked"] = len(fp_cache)
res["info"]["footprint_status_count"] = fp_status_count

# ------------------------------------------------------------------ C
SEC = "C_lpf_vs_schematic_vs_rtl"
lpf = open(os.path.join(R85, "fpga_ecp5", "constraints", "arc1_ecp5_r85.lpf")).read()
loc = {m.group(1): m.group(2) for m in re.finditer(r'LOCATE COMP "([^"]+)" SITE "([A-Z]+\d+)"', lpf)}
iob = {m.group(1): m.group(2) for m in re.finditer(r'IOBUF PORT "([^"]+)" ([^;]+);', lpf)}
u18 = pcomps["U18"]["pins"]
pin_csv = {r["ball"]: r for r in csv.DictReader(open(os.path.join(R85, "sources", "lattice", "lfe5u45_cabga381_pinout.csv")))}
rtl = open(os.path.join(R85, "fpga_ecp5", "rtl", "arc1_ecp5_top.sv")).read()
hdr = rtl[rtl.index("module arc1_ecp5_top"):]
hdr = hdr[hdr.index(") (") + 3:hdr.index(");")]
ports = {}
for m in re.finditer(r"\b(input|output|inout)\s+wire\s*(\[(\d+):(\d+)\])?\s*(\w+)", hdr):
    d, rng, msb, lsb, name = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    if rng:
        for i in range(int(lsb), int(msb) + 1):
            ports[f"{name}[{i}]"] = d
    else:
        ports[name] = d
for p in sorted(set(ports) ^ set(loc)):
    fail(SEC, f"port {p} only in {'RTL' if p in ports else 'LPF'}")
for p, ball in loc.items():
    if ball not in pin_csv:
        fail(SEC, f"{p}: {ball} is not an LFE5U-45F caBGA381 ball")
        continue
    if pin_csv[ball]["pin_type"] != "IO":
        fail(SEC, f"{p}: {ball} is {pin_csv[ball]['pin_type']} {pin_csv[ball]['pin_function']}, not user I/O")
    if not u18.get(ball, {}).get("net"):
        fail(SEC, f"{p}: schematic ball {ball} unconnected")
    if "IO_TYPE=LVCMOS33" not in iob.get(p, ""):
        fail(SEC, f"{p}: IOBUF not LVCMOS33")
# every schematic user-I/O ball with a signal net that an RTL port should own
for ball, d in u18.items():
    if pin_csv[ball]["pin_type"] == "IO" and d["net"] and d["net"] not in ("GND",) and ball not in loc.values():
        if d["net"] not in ("FPGA_HOLDN",):
            fail(SEC, f"schematic ball {ball} ({d['net']}) carries a signal but no RTL port")
routed = os.path.join(R85, "fpga_ecp5", "build", "repro", "routed.json")
if os.path.exists(routed):
    rj = json.load(open(routed))
    mod = list(rj["modules"].values())[0]
    placed = {}
    for n, c in mod["cells"].items():
        if c["type"] == "TRELLIS_IO":
            a = {**c.get("attributes", {}), **c.get("parameters", {})}
            placed[n.split("$tr_io")[0]] = a.get("LOC")
    for p, ball in loc.items():
        if placed.get(p) != ball:
            fail(SEC, f"routed placement {p} @ {placed.get(p)} != LPF {ball}")
    res["info"]["routed_io_checked"] = len(placed)
else:
    res["info"]["routed_io_checked"] = "routed.json absent (run make -C fpga_ecp5 repro)"
res["info"]["lpf_ports"] = len(loc)
res["info"]["rtl_top_ports"] = len(ports)

# ------------------------------------------------------------------ D
h = open(os.path.join(R85, "firmware", "include", "board_pins_r85.h")).read()
fwpins = {m.group(1): (m.group(2), int(m.group(3))) for m in
          re.finditer(r"#define\s+PIN_(\w+)\s+ARC1_PIN\(\s*'([A-G])'\s*,\s*(\d+)\s*\)", h)}
f133 = pcomps["U15"]["pins"]
byname = {d["name"]: d["net"] for d in f133.values()}
for net, (port, idx) in fwpins.items():
    pname = f"P{port}{idx}"
    if byname.get(pname) != net:
        fail("D_firmware_vs_schematic", f"firmware PIN_{net} = {pname}, schematic {pname} -> {byname.get(pname)}")
gp = {n: net for n, net in byname.items() if re.match(r"^P[A-G]\d+$", n) and net}
for pname, net in gp.items():
    if net not in fwpins:
        fail("D_firmware_vs_schematic", f"schematic {pname} -> {net} has no firmware PIN_ define")
res["info"]["firmware_pins"] = len(fwpins)

total = sum(len(v) for k, v in res.items() if k != "info")
res["result"] = "PASS" if total == 0 else "FAIL"
json.dump(res, open(OUT, "w"), indent=1)
for k, v in res.items():
    if k not in ("info", "result"):
        print(f"{k}: {len(v)} mismatch(es)")
        for x in v[:20]:
            print("   ", x)
print("info:", json.dumps(res["info"]))
print("CROSSCHECK", res["result"])
sys.exit(0 if total == 0 else 1)
