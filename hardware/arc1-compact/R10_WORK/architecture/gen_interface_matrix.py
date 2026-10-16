#!/usr/bin/env python3
"""ARC-1 R10 -- architecture/R10_interface_matrix.csv + R10_PINMUX_CONFLICTS.md, generated from the evidence tables:
  sources/d213ecv_pins.csv          D213ECV QFN128 pin multiplex (ArtInChip D21x pin-multiplex page, sha in sources.json)
  sources/lfe5u12_tqfp144_pinout.csv LFE5U-12F TQFP144 (Lattice FPGA-SC-02032 v2.1)
  ../../R85C_WORK/sources/f133/f133_elqfp128_all_pins.csv   F133 eLQFP128 (F133 DS rev 2.3)
  ../fpga12/timing/r10_12f_tqfp144.lpf                       12F RGMII pin plan (this pass)
Every row: link, option, signal, per-chip pin/pad/function, direction, I/O voltage, and the functions the pad loses
(mutually exclusive). Status column: DOCUMENTED (both ends' functions stated by the vendors), PROPOSED (our choice).
Usage: gen_interface_matrix.py  (from R10_WORK/architecture)"""
import csv, os, re, sys

H = os.path.dirname(os.path.abspath(__file__))
D213 = {r["name_func1"]: r for r in csv.DictReader(open(os.path.join(H, "sources", "d213ecv_pins.csv")))}
F133 = {r["pin_name"]: r for r in csv.DictReader(open(os.path.join(H, "..", "..", "R85C_WORK", "sources", "f133",
                                                                    "f133_elqfp128_all_pins.csv")))}
L12 = {}
for line in open(os.path.join(H, "..", "fpga12", "timing", "r10_12f_tqfp144.lpf")):
    m = re.match(r'# LOCATE COMP "([^"]+)" SITE "(\d+)" ;\s+# TQFP144 pin \d+ = (\S+) \((.*)\)', line)
    if m:
        L12[m.group(1)] = (m.group(2), m.group(3), m.group(4))
FUNCS = ["func2", "func3", "func4", "func5", "func6", "func7", "func8"]
errors, rows = [], []


def d213(pad, want):
    r = D213.get(pad)
    if not r:
        errors.append(f"D213 pad {pad} not in table"); return ("?", "?", "?", "")
    fn = [r[f] for f in FUNCS if r.get(f) and r[f] != "-"]
    if want not in fn:
        errors.append(f"D213 {pad}: {want} not among {fn}")
    others = [f for f in fn if f != want]
    return (r["pin"], pad, r["power_domain"], " / ".join(others))


def f133(pad):
    r = F133.get(pad)
    if not r:
        errors.append(f"F133 {pad} missing"); return ("?", "?")
    return (r["pin_number"], r["power_domain"])


def row(link, option, sig, a_chip, a_pin, a_pad, a_fn, a_dom, b_chip, b_pin, b_pad, b_fn, b_dom, direction, volts,
        lost, status):
    rows.append({"link": link, "option": option, "signal": sig, "chip_a": a_chip, "a_pin": a_pin, "a_pad": a_pad,
                 "a_function": a_fn, "a_io_domain": a_dom, "chip_b": b_chip, "b_pin": b_pin, "b_pad": b_pad,
                 "b_function": b_fn, "b_io_domain": b_dom, "direction_a_to_b": direction, "io_voltage": volts,
                 "functions_lost_on_these_pads": lost, "status": status})


# ---- L1 F133 <-> 12F RGMII (F133 PG function 4; 12F banks 0/1, R10 12F pin plan) ----
F133_RGMII = [("TXCK", "PG3", "rgmii_rxc", "out"), ("TXD0", "PG4", "rgmii_rxd[0]", "out"), ("TXD1", "PG5", "rgmii_rxd[1]", "out"),
              ("TXD2", "PG6", "rgmii_rxd[2]", "out"), ("TXD3", "PG7", "rgmii_rxd[3]", "out"), ("TXCTRL", "PG12", "rgmii_rx_ctl", "out"),
              ("RXCK", "PG10", "rgmii_txc", "in"), ("RXD0", "PG1", "rgmii_txd[0]", "in"), ("RXD1", "PG2", "rgmii_txd[1]", "in"),
              ("RXD2", "PG8", "rgmii_txd[2]", "in"), ("RXD3", "PG9", "rgmii_txd[3]", "in"), ("RXCTRL", "PG0", "rgmii_tx_ctl", "in")]
for sig, pad, port, d in F133_RGMII:
    fp, fd = f133(pad)
    tp, pio, note = L12.get(port, ("?", "?", "?"))
    if tp == "?":
        errors.append(f"12F port {port} missing from LPF")
    row("F133<->12F", "RGMII (R10 4)", sig, "F133-B", fp, pad, f"RGMII-{sig} (F4)", fd, "LFE5U-12F TQFP144", tp, pio,
        port + (" (PCLKT0_0)" if port == "rgmii_rxc" else ""), note, "F133->12F" if d == "out" else "12F->F133", "3.3 V LVCMOS",
        "F133: buttons moved off PG (R8.5-C C3); SDC1/UART1/UART3/UART5/TWI on PG lost", "PROPOSED (pins DOCUMENTED)")

# ---- L2 F133 USB1 host <-> D213 USB0 device ----
for sig, fpad, dpad, dfn in (("D+", "USB1-DP", "PU1", "USB0_DP"), ("D-", "USB1-DM", "PU0", "USB0_DM")):
    fp, fd = f133(fpad)
    dp, dpd, ddom, lost = d213(dpad, dfn)
    row("F133<->D213", "USB 2.0 HS (R10 4, preferred)", sig, "F133-B", fp, fpad, "USB1 host (EHCI/OHCI)", fd, "D213ECV",
        dp, dpd, dfn + " (device)", ddom, "bidirectional", "USB 2.0 HS differential",
        f"D213: {lost}; D213 USB0 is also the documented USB upgrade/recovery port", "PROPOSED (functions DOCUMENTED)")

# ---- L3 D213 <-> 45F: option A PBUS on PD (only full 16-bit group) ----
pbus = [(f"AD{i}", f"PD{i}", f"PBUS_AD{i}") for i in range(16)] + [("CLK", "PD16", "PBUS_CLK"), ("NCS", "PD17", "PBUS_NCS"),
        ("NADV", "PD18", "PBUS_NADV"), ("NWE", "PD19", "PBUS_NWE"), ("NOE", "PD20", "PBUS_NOE")]
for sig, pad, fn in pbus:
    p, pd, dom, lost = d213(pad, fn)
    row("D213<->45F", "A: PBUS 16-bit on PD (R10 4 as written)", sig, "D213ECV", p, pd, fn, dom, "LFE5U-45F", "TBD", "TBD",
        "PBUS slave", "3.3 V bank TBD", "bidirectional" if sig.startswith("AD") else "D213->45F", "3.3 V LVCMOS",
        "D213: " + lost, "CONFLICT (pads DOCUMENTED)")
# option B: GMAC0 RGMII on PE
gm0 = [("TXCK", "PE6", "GMAC0_TXCK"), ("TXD0", "PE5", "GMAC0_TXD0"), ("TXD1", "PE4", "GMAC0_TXD1"), ("TXD2", "PE15", "GMAC0_TXD2"),
       ("TXD3", "PE14", "GMAC0_TXD3"), ("TXCTL", "PE7", "GMAC0_TXCTL"), ("RXCK", "PE13", "GMAC0_RXCK"), ("RXD0", "PE1", "GMAC0_RXD0"),
       ("RXD1", "PE0", "GMAC0_RXD1"), ("RXD2", "PE12", "GMAC0_RXD2"), ("RXD3", "PE11", "GMAC0_RXD3"), ("RXCTL", "PE2", "GMAC0_RXCTL")]
for sig, pad, fn in gm0:
    p, pd, dom, lost = d213(pad, fn)
    row("D213<->45F", "B: GMAC0 RGMII on PE (proposed alternative)", sig, "D213ECV", p, pd, fn, dom, "LFE5U-45F", "TBD (top bank)",
        "TBD", "rgmii endpoint (R8.5-C eth_link)", "3.3 V", "D213->45F" if sig.startswith("TX") else "45F->D213", "3.3 V LVCMOS",
        "D213: " + lost, "PROPOSED (pads DOCUMENTED; D21x DS Table 3-2 GMAC-1000M x2)")

# ---- L4 D213 video (one of these; all on PD) ----
for sig, pad, fn in [("LVDS0_D0N", "PD18", "LVDS0_D0N"), ("LVDS0_D0P", "PD19", "LVDS0_D0P"), ("LVDS0_D1N", "PD20", "LVDS0_D1N"),
                     ("LVDS0_D1P", "PD21", "LVDS0_D1P"), ("LVDS0_D2N", "PD22", "LVDS0_D2N"), ("LVDS0_D2P", "PD23", "LVDS0_D2P"),
                     ("LVDS0_CKN", "PD24", "LVDS0_CKN"), ("LVDS0_CKP", "PD25", "LVDS0_CKP"), ("LVDS0_D3N", "PD26", "LVDS0_D3N"),
                     ("LVDS0_D3P", "PD27", "LVDS0_D3P")]:
    p, pd, dom, lost = d213(pad, fn)
    row("D213->video", "LVDS0 to HDMI bridge (bridge TBD)", sig, "D213ECV", p, pd, fn, dom, "HDMI bridge", "TBD", "TBD", "LVDS in",
        "TBD", "D213->bridge", "LVDS", "D213: " + lost, "PROPOSED (pads DOCUMENTED)")

# ---- L5 D213 boot SPI NOR (SPI0 on PB0-PB5, function 3) and debug UART0 ----
for sig, pad, fn in [("HOLD", "PB0", "SPI0_HOLD"), ("WP", "PB1", "SPI0_WP"), ("CS", "PB2", "SPI0_CS"), ("MISO", "PB3", "SPI0_MISO"),
                     ("MOSI", "PB4", "SPI0_MOSI"), ("CLK", "PB5", "SPI0_CLK")]:
    p, pd, dom, lost = d213(pad, fn)
    row("D213 boot", "SPI NOR (D21x boot order: SD, SPI NAND, SPI NOR, eMMC)", sig, "D213ECV", p, pd, fn, dom, "SPI NOR", "TBD", "-",
        "-", "-", "bidirectional", "3.3 V", "D213: " + lost + " (eMMC SDC0 boot excluded)", "PROPOSED (pads DOCUMENTED)")
for sig, pad, fn in [("TX", "PA0", "UART0_TX"), ("RX", "PA1", "UART0_RX")]:
    p, pd, dom, lost = d213(pad, fn)
    row("D213 debug", "UART0 (SDK default; PA0 is also the default BOOT pin)", sig, "D213ECV", p, pd, fn, dom, "debug header", "-",
        "-", "-", "-", "-", "3.3 V", "D213: " + lost, "PROPOSED (pads DOCUMENTED)")

out = os.path.join(H, "R10_interface_matrix.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

# ---- conflict analysis ----
pads = {}
for r in rows:
    if r["chip_a"] == "D213ECV":
        pads.setdefault(r["a_pad"], set()).add(r["link"] + " / " + r["option"].split(":")[0])
L = ["# R10 pin-mux conflicts (generated by architecture/gen_interface_matrix.py)", "",
     "D213ECV pads claimed by more than one proposed function:", "", "| D213 pad | pin | claimed by |", "|---|---|---|"]
dup = {p: s for p, s in pads.items() if len(s) > 1}
for p in sorted(dup, key=lambda x: (x[:2], int(re.sub(r"\D", "", x) or 0))):
    L.append(f"| {p} | {D213[p]['pin']} | {'; '.join(sorted(dup[p]))} |")
pd_pbus = {r["a_pad"] for r in rows if r["option"].startswith("A:")}
video_pd = {p for p, r in D213.items() if p.startswith("PD") and any(k in (r.get(f) or "") for f in FUNCS
                                                                    for k in ("LCD_", "LVDS", "DSI_"))}
lost_video = sorted(pd_pbus & video_pd, key=lambda x: int(x[2:]))
L += ["", f"Option A (PBUS on PD0-PD20) occupies {len(pd_pbus)} pads, {len(lost_video)} of which carry display functions "
      f"(LCD_D*, LVDS0/LVDS1, DSI): {', '.join(lost_video)}.",
      "Consequence: with a full 16-bit PBUS no D213 display output remains: parallel RGB needs PD0-PD27, LVDS1 is "
      "PD8-PD17, LVDS0 and DSI are PD18-PD27 (PD18-PD20 taken by NADV/NWE/NOE). The PF group offers only AD0-AD11 "
      "(PF11 shared between AD11 and CLK). R10 10.2 hold criterion 1 is therefore MET for option A as written.",
      "", "Option B (GMAC0 RGMII on PE) shares no pad with display, boot (PB/PC), debug UART0 (PA) or USB (PU) in this "
      "matrix; it gives up DVP, CAN0/1, I2S0, UART4-7 alternates on PE.", "",
      "F133<->12F: F133 PG0-PG12 (function 4), 12F banks 0/1; F133<->D213: F133 USB1 host to D213 USB0 device; D213 USB0 "
      "is also its USB upgrade/recovery port (R10 8.3 asks to reserve a recovery topology).", ""]
if errors:
    L += ["## Generator errors", ""] + [f"- {e}" for e in errors]
open(os.path.join(H, "R10_PINMUX_CONFLICTS.md"), "w").write("\n".join(L) + "\n")
print(f"{len(rows)} matrix rows, {len(dup)} multiply-claimed D213 pads, {len(errors)} errors")
for e in errors:
    print("ERROR", e)
sys.exit(1 if errors else 0)
