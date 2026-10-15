#!/usr/bin/env python3
"""ARC-1 Compact R08 -- 1:1 cross-check between independent representations.

  A  KiCad netlist (kicad-cli export of the native schematic)  <->  board plan JSON (design source)
  B  every symbol pin number  <->  the pad names of the footprint actually assigned (KiCad 9 library or ARC1_R08.pretty)
  C  Efinity pin table  <->  schematic U18 balls/nets  <->  RTL top-level ports
  D  firmware board_pins_r08.h  <->  schematic F133 pin/net assignment

This proves the representations AGREE. It does not prove the design is right:
the rules encoded in check_board_r08.py are self-authored (handoff rule).
Usage: crosscheck_r08.py <R08_WORK dir> <report.json>
"""
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

R08 = os.path.abspath(sys.argv[1])
OUT = sys.argv[2]
STD_FP = os.environ.get("KICAD_FOOTPRINTS", "/usr/share/kicad/footprints")
plan = json.load(open(os.path.join(R08, "board", "r08_board_plan.json")))
res = {"A_netlist_vs_plan": [], "B_symbol_vs_footprint": [], "C_efinity_vs_schematic_vs_rtl": [],
       "D_firmware_vs_schematic": [], "info": {}}


def fail(sec, msg):
    res[sec].append(msg)


# ------------------------------------------------------------------ A
root = ET.parse(os.path.join(R08, "cad", "NETLIST.xml")).getroot()
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
    if lib == "ARC1_R08":
        path = os.path.join(R08, "cad", "symbols-and-footprints", "ARC1_R08.pretty", name + ".kicad_mod")
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
efin = list(csv.DictReader(open(os.path.join(R08, "fpga", "efinity", "arc1_t35_r08_pins.csv"))))
u18 = pcomps["U18"]["pins"]
balls_csv = {r["ball"]: r for r in csv.DictReader(open(os.path.join(R08, "sources", "efinix", "t35f400_balls_by_rail.csv")))}
for r in efin:
    b = r["ball"]
    if b not in u18:
        fail("C_efinity_vs_schematic_vs_rtl", f"Efinity {r['instance']} ball {b} not a T35F400 ball")
        continue
    if u18[b]["net"] != r["net"]:
        fail("C_efinity_vs_schematic_vs_rtl", f"{r['instance']}@{b}: schematic net {u18[b]['net']} != Efinity net {r['net']}")
    if balls_csv[b]["name"] != r["resource"]:
        fail("C_efinity_vs_schematic_vs_rtl", f"{b}: resource {r['resource']} != pinout {balls_csv[b]['name']}")
    if balls_csv[b]["bank"] != r["bank"]:
        fail("C_efinity_vs_schematic_vs_rtl", f"{b}: bank mismatch")
rtl = open(os.path.join(R08, "fpga", "rtl", "arc1_t35_top_r08.sv")).read()
hdr = rtl[rtl.index("module arc1_t35_top_r08"):rtl.index(");")]
ports = {}
for m in re.finditer(r"\b(input|output)\s+wire\s*(\[(\d+):(\d+)\])?\s*(\w+)", hdr):
    d, rng, msb, lsb, name = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    if rng:
        for i in range(int(lsb), int(msb) + 1):
            ports[f"{name}[{i}]"] = d
    else:
        ports[name] = d
need = set()
for r in efin:
    for p in r["rtl_ports"].split():
        need.add(p)
        if p not in ports:
            fail("C_efinity_vs_schematic_vs_rtl", f"Efinity port {p} not in RTL top")
        else:
            exp = "input" if p.endswith("_IN") or ("_IN[" in p) or r["mode"] == "input" else "output"
            if ports[p] != exp:
                fail("C_efinity_vs_schematic_vs_rtl", f"RTL port {p} is {ports[p]}, Efinity expects {exp}")
for p in sorted(set(ports) - need - {"sys_clk", "psram_mclk", "pll_locked"}):
    fail("C_efinity_vs_schematic_vs_rtl", f"RTL top port {p} has no Efinity GPIO / PLL source")
res["info"]["efinity_gpio"] = len(efin)
res["info"]["rtl_top_ports"] = len(ports)

# ------------------------------------------------------------------ D
h = open(os.path.join(R08, "firmware", "include", "board_pins_r08.h")).read()
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
