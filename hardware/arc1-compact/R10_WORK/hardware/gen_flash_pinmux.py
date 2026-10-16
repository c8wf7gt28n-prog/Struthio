#!/usr/bin/env python3
"""ARC-1 R10 -- flash, FPGA-configuration and external-memory pin plan (ARC1_MEMORY_R10 v0.1 s7.3 item 3).
Writes hardware/R10_flash_pinmux.csv and the LPF fragments used by the memory builds:
  hardware/lpf/r10_12f_mem_tqfp144.lpf (commented, TQFP144 pins), hardware/lpf/r10_12f_mem_proxy256.lpf (same PIO sites
  on caBGA256 for nextpnr), hardware/lpf/r10_45f_sdram.lpf (CABGA381).
Checks (exit 1 on any failure): every pin exists in the vendor pin file with the stated PIO function and bank and is
a user I/O (or the named dedicated config pin); no pin is used twice on one chip, including the pins already locked
by the RGMII builds; each D213 pad offers the named function; D213 pads are not claimed by the interface matrix.
Sources: architecture/sources (Lattice FPGA-SC-02032 v2.1, D213ECV pin table), R85C_WORK/board/ECP5_BALL_MAP_R85.csv
(45F CABGA381), R85C_WORK/board/F133_PINMUX_MATRIX_R85.csv (F133)."""
import csv, os, re, sys

H = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(H, "..")
SRC = os.path.join(R, "architecture", "sources")
R85 = os.path.join(R, "..", "R85C_WORK", "board")
errs = []

# ---------------- vendor data ----------------
def lattice12():
    rows, hdr = [], None
    for line in csv.reader(open(os.path.join(SRC, "lattice_ECP5U-12_pinout_FPGA-SC-02032_v2.1.csv"))):
        if line and line[0] == "PAD": hdr = line; continue
        if hdr and line and line[0].isdigit(): rows.append(dict(zip(hdr, line)))
    by_tq = {r["TQFP144"]: r for r in rows if r["TQFP144"] not in ("", "-")}
    return by_tq
L12 = lattice12()
TQ = {r["pin"]: r for r in csv.DictReader(open(os.path.join(SRC, "lfe5u12_tqfp144_pinout.csv")))}
B45 = {r["ball"]: r for r in csv.DictReader(open(os.path.join(R85, "ECP5_BALL_MAP_R85.csv")))}
D213 = {}
for r in csv.DictReader(open(os.path.join(SRC, "d213ecv_pins.csv"))):
    D213[r["name_func1"]] = r
F133 = {r["name"]: r for r in csv.DictReader(open(os.path.join(R85, "F133_PINMUX_MATRIX_R85.csv")))}

def locked(path):
    pins = {}
    for line in open(path):
        m = re.match(r'\s*#?\s*LOCATE COMP "([^"]+)" SITE "([^"]+)"', line)
        if m: pins[m.group(2)] = m.group(1)
    return pins
USED12 = locked(os.path.join(R, "fpga12", "timing", "r10_12f_tqfp144.lpf"))       # TQFP144 pin -> port
USED45 = locked(os.path.join(R, "fpga45", "constraints", "r10_45f.lpf"))          # ball -> port
MATRIX_D213 = {r["a_pad"] for r in csv.DictReader(open(os.path.join(R, "architecture", "R10_interface_matrix.csv")))
               if r["chip_a"] == "D213ECV"}

rows, seen = [], {}
def add(group, signal, chip, pin, func, bank, volt, dirn, peer, peer_pin, status, note=""):
    k = (chip, pin)
    if k in seen: errs.append(f"{chip} pin {pin} used twice: {seen[k]} and {signal}")
    seen[k] = signal
    rows.append(dict(group=group, signal=signal, chip=chip, pin=pin, function=func, bank_or_domain=bank,
                     io_voltage=volt, direction=dirn, peer_chip=peer, peer_pin=peer_pin, status=status, note=note))

def f133(group, signal, pad, func, dirn, peer, peer_pin, status, note=""):
    r = F133.get(pad)
    if not r: errs.append(f"F133 {pad} not in the R8.5-C F133 matrix"); pin = "?"
    else: pin = r["pin"]
    add(group, signal, "F133-B", f"{pin} ({pad})", func, "VCC-IO 3V3", "3.3 V", dirn, peer, peer_pin, status, note)

def d213(group, signal, pad, func, dirn, peer, peer_pin, status, note="", allow_matrix=False):
    r = D213.get(pad)
    if not r: errs.append(f"D213 {pad} unknown"); return
    funcs = {v for k, v in r.items() if k.startswith("func") or k == "name_func1"}
    if func not in funcs and func != "GPIO": errs.append(f"D213 {pad} has no function {func}")
    if pad in MATRIX_D213 and not allow_matrix: errs.append(f"D213 {pad} already claimed in the interface matrix")
    add(group, signal, "D213ECV", f"{r['pin']} ({pad})", func, r["power_domain"], "3.3 V", dirn, peer, peer_pin, status, note)

def p12(group, signal, tq, expect_func, dirn, peer, peer_pin, status, note="", config=False):
    t = TQ.get(str(tq))
    if not t: errs.append(f"12F TQFP144 pin {tq} unknown"); return None
    if config:
        if t["pin_function"] != expect_func: errs.append(f"12F pin {tq} is {t['pin_function']}, expected {expect_func}")
    else:
        if t["pin_type"] != "IO": errs.append(f"12F pin {tq} not a user I/O")
        if expect_func and t["pin_function"] != expect_func: errs.append(f"12F pin {tq} is {t['pin_function']} not {expect_func}")
    if str(tq) in USED12: errs.append(f"12F pin {tq} already locked to {USED12[str(tq)]}")
    ball = L12.get(str(tq), {}).get("CABGA256", "")
    add(group, signal, "LFE5U-12F TQFP144", str(tq), t["pin_function"] + (f" [{t['dual_function']}]" if t["dual_function"] != "-" else ""),
        "bank " + t["bank"], "3.3 V", dirn, peer, peer_pin, status, note + (f" proxy caBGA256 {ball}" if ball and not config else ""))
    return t["pin_function"], ball

def p45(group, signal, ball, dirn, peer, peer_pin, status, note="", config=False):
    b = B45.get(ball)
    if not b: errs.append(f"45F ball {ball} unknown"); return
    if not config and b["pin_type"] != "IO": errs.append(f"45F ball {ball} not a user I/O")
    if ball in USED45: errs.append(f"45F ball {ball} already locked to {USED45[ball]}")
    add(group, signal, "LFE5U-45F CABGA381", ball, b["pin_function"] + (f" [{b['dual_function']}]" if b["dual_function"] != "-" else ""),
        "bank " + b["bank"], "3.3 V", dirn, peer, peer_pin, status, note)

# ---------------- 1. F133 system NOR (sole bus master, memory spec s3.1) ----------------
NOR_PART = "W25Q512JVFIQ (64 MiB, SOIC16 300 mil)"
NOR = [("SPI0_CLK", "PC2", "SPI0-CLK", "out", "16 CLK"), ("SPI0_CS0_N", "PC3", "SPI0-CS0", "out", "7 /CS"),
       ("SPI0_MOSI", "PC4", "SPI0-MOSI", "out", "15 DI/IO0"), ("SPI0_MISO", "PC5", "SPI0-MISO", "in", "8 DO/IO1"),
       ("SPI0_IO2", "PC6", "SPI0-WP", "io", "9 /WP/IO2"), ("SPI0_IO3", "PC7", "SPI0-HOLD", "io", "1 /HOLD/IO3")]
for sig, pad, fn, d, np in NOR:
    f133("NOR", sig, pad, fn, d, NOR_PART, np, "SELECTED; boot validation pending",
         "Winbond Rev.B Figure 1b; Q suffix QE defaults to 1; dedicated RESET pin 3")
for pin, fn, net in [(2, "VCC", "3V3"), (3, "/RESET", "NOR_RESET_N"), (10, "GND", "GND")] + [(p, "NC", "NO_CONNECT") for p in [4, 5, 6, 11, 12, 13, 14]]:
    add("NOR_AUX", fn, NOR_PART, str(pin), fn, "NOR", "3.3 V" if fn in ("VCC", "/RESET") else ("0 V" if fn == "GND" else "-"),
        "in" if fn == "/RESET" else ("nc" if fn == "NC" else "power"), net, "-", "SELECTED; schematic pending",
        "Independent hardware reset; do not use IO3 as reset" if fn == "/RESET" else "Winbond Rev.B Figure 1b")

# ---------------- 2. F133 -> 12F slave SPI configuration (shares SPI0 behind isolation buffers, as R8.5-C) -------------
CFG12 = [("FPGA12_SCK", "PC2", "SPI0-CLK", "out", 54, "CCLK", "via isolation buffer (R8.5-C U21)"),
         ("FPGA12_MOSI", "PC4", "SPI0-MOSI", "out", 47, "PB11B", "D0/MOSI, via buffer (U22)"),
         ("FPGA12_MISO", "PC5", "SPI0-MISO", "in", 46, "PB11A", "D1/MISO, via buffer (U24, enabled by SN low)"),
         ("FPGA12_SS_N", "PE4", "GPIO-OUT", "out", 48, "PB13A", "SN/CSN, software chip select")]
for sig, pad, fn, d, tq, pf, note in CFG12:
    p12("CFG12", sig, tq, pf, "in" if d == "out" else "out", "F133-B", pad, "SELECTED (R8.5-C loader, now for the 12F)",
        note, config=(pf == "CCLK"))
for sig, pad, fn, d, tq, pf in [("FPGA12_PROGRAMN", "PE8", "GPIO open-drain", "od", 57, "PROGRAMN"),
                                ("FPGA12_INITN", "PD0", "GPIO-IN", "in", 55, "INITN"),
                                ("FPGA12_DONE", "PE9", "PE-EINT9", "in", 56, "DONE")]:
    p12("CFG12", sig, tq, pf, "bidir" if pf != "PROGRAMN" else "in", "F133-B", pad, "SELECTED", "dedicated sysCONFIG pin", config=True)
for sig, tq, pf, lvl in [("FPGA12_CFG0", 62, "CFG_0", "pull-up 10k"), ("FPGA12_CFG1", 59, "CFG_1", "GND"), ("FPGA12_CFG2", 58, "CFG_2", "GND")]:
    p12("CFG12", sig, tq, pf, "in", "strap", lvl, "SELECTED", "CFG[2:0] = 001 slave SPI (TN-02039)", config=True)
for sig, pad, fn, d in [("FPGA12_BUS_EN_N", "PE6", "GPIO-OUT", "out"), ("FPGA12_PWR_EN", "PE0", "GPIO-OUT", "out"),
                        ("FPGA12_VCC_PG", "PD1", "GPIO-IN", "in")]:
    f133("CFG12", sig, pad, fn, d, "12F power / isolation", "-", "SELECTED (R8.5-C function, retargeted to the 12F)")

# ---------------- 3. 12F 4 MiB QSPI PSRAM (memory spec s2.4) on bank 3 ----------------
PS12 = [("psram_ce_n", 72, "PR44C", "1 CE#"), ("psram_sclk", 73, "PR41D", "6 SCLK"), ("psram_sio[0]", 74, "PR41C", "5 SI/SIO0"),
        ("psram_sio[1]", 76, "PR41B", "2 SO/SIO1"), ("psram_sio[2]", 77, "PR41A", "3 SIO2"), ("psram_sio[3]", 78, "PR35D", "7 SIO3")]
lpf12_tq, lpf12_px = [], []
for port, tq, pf, mp in PS12:
    r = p12("PSRAM12", port, tq, pf, "io" if "sio" in port else "out", "APS3204L-3SQN (4 MiB, candidate)", mp,
            "PROPOSED", "bank 3 (right), away from RGMII banks 0/1")
    if r:
        lpf12_tq.append(f'# LOCATE COMP "{port}" SITE "{tq}" ;  # TQFP144 pin {tq} = {pf} (bank 3)')
        lpf12_px.append(f'LOCATE COMP "{port}" SITE "{r[1]}" ;  # TQFP144 pin {tq} = {pf} (bank 3)')
        io = "SLEWRATE=FAST" + ("" if "sio" not in port else " PULLMODE=NONE")
        for lst in (lpf12_tq, lpf12_px):
            lst.append(("# " if lst is lpf12_tq else "") + f'IOBUF PORT "{port}" IO_TYPE=LVCMOS33 {io} ;')

# ---------------- 4. D213 -> 45F slave SPI configuration (memory spec s3.1) ----------------
CFG45 = [("FPGA45_SCK", "PB11", "SPI1_CLK", "out", "U3", "CCLK"), ("FPGA45_MOSI", "PB10", "SPI1_MOSI", "out", "W2", "D0/MOSI"),
         ("FPGA45_MISO", "PB9", "SPI1_MISO", "in", "V2", "D1/MISO"), ("FPGA45_SS_N", "PB8", "SPI1_CS", "out", "T2", "SN/CSN")]
for sig, pad, fn, d, ball, what in CFG45:
    d213("CFG45", sig, pad, fn, d, "LFE5U-45F", ball, "PROPOSED", "D213 SPI1 (VCC33_IO0); PB0-PB5 stay free for a D213 boot NOR")
    p45("CFG45", sig, ball, "in" if d == "out" else "out", "D213ECV", pad, "PROPOSED", what, config=(ball == "U3"))
for sig, pad, ball in [("FPGA45_PROGRAMN", "PA4", "W3"), ("FPGA45_INITN", "PA5", "V3"), ("FPGA45_DONE", "PA6", "Y3")]:
    d213("CFG45", sig, pad, "GPIO", "od" if "PROG" in sig else "in", "LFE5U-45F", ball, "PROPOSED",
         "GPIO; PA0/PA1 (UART0) and PA8-PA11 (JTAG alternate) avoided")
    p45("CFG45", sig, ball, "in" if "PROG" in sig else "bidir", "D213ECV", pad, "PROPOSED", "dedicated sysCONFIG pin", config=True)
p45("CFG45", "FPGA45_CFG0", "U4", "in", "strap", "pull-up 10k", "SELECTED (R8.5-C)", "CFG[2:0] = 001 slave SPI", config=True)

# ---------------- 5. D213 boot NOR fallback (memory spec s7.2) and USB link ----------------
for sig, pad, fn in [("D213_NOR_HOLD", "PB0", "SPI0_HOLD"), ("D213_NOR_WP", "PB1", "SPI0_WP"), ("D213_NOR_CS", "PB2", "SPI0_CS"),
                     ("D213_NOR_MISO", "PB3", "SPI0_MISO"), ("D213_NOR_MOSI", "PB4", "SPI0_MOSI"), ("D213_NOR_CLK", "PB5", "SPI0_CLK")]:
    d213("D213NOR", sig, pad, fn, "io", "D213 boot NOR (DNP footprint)", "-", "RESERVED (fallback if flashless boot fails)",
         allow_matrix=True)

# ---------------- 6. 45F x16 SDR SDRAM (memory spec s2.3) on banks 2 (data) and 3 (address/control) ----------------
def free_balls(bank):
    out = [b for b, r in B45.items() if r["bank"] == bank and r["pin_type"] == "IO" and b not in USED45]
    plain = sorted([b for b in out if B45[b]["dual_function"] == "-"], key=lambda b: (b[0], int(b[1:])))
    dual = sorted([b for b in out if B45[b]["dual_function"] != "-"], key=lambda b: (b[0], int(b[1:])))
    return plain + dual                                      # keep clock/PLL/VREF-capable balls for last
data = [f"sd_dq[{i}]" for i in range(16)] + ["sd_dqm[0]", "sd_dqm[1]"]
ctrl = ["sd_clk", "sd_cke", "sd_cs_n", "sd_ras_n", "sd_cas_n", "sd_we_n", "sd_ba[0]", "sd_ba[1]"] + [f"sd_a[{i}]" for i in range(13)]
# Alliance AS4C16M16SA-C&I Rev.3.0, Figure 1, TSOP-II TOP VIEW.
# Freeze the industrial -6TIN package; these are NOT the FBGA ball assignments.
SDRAM_PART = "AS4C16M16SA-6TIN (32 MiB, TSOP-II 54)"
SDRAM_PINS = dict(zip([f"sd_dq[{i}]" for i in range(16)],
                     [2, 4, 5, 7, 8, 10, 11, 13, 42, 44, 45, 47, 48, 50, 51, 53]))
SDRAM_PINS.update(dict(zip([f"sd_a[{i}]" for i in range(13)],
                          [23, 24, 25, 26, 29, 30, 31, 32, 33, 34, 22, 35, 36])))
SDRAM_PINS.update(dict(zip(["sd_dqm[0]", "sd_dqm[1]"] + ctrl[:8],
                          [15, 39, 38, 37, 19, 18, 17, 16, 20, 21])))
SDRAM_SUPPLY = {"VDD": [1, 14, 27], "VDDQ": [3, 9, 43, 49],
                "VSS": [28, 41, 54], "VSSQ": [6, 12, 46, 52], "NC": [40]}
all_sd_pins = list(SDRAM_PINS.values()) + [p for ps in SDRAM_SUPPLY.values() for p in ps]
if set(SDRAM_PINS) != set(data + ctrl) or sorted(all_sd_pins) != list(range(1, 55)):
    errs.append("SDRAM package map must cover each of the 54 pins exactly once")
lpf45 = []
for sigs, bank in ((data, "2"), (ctrl, "3")):
    balls = free_balls(bank)
    if len(balls) < len(sigs): errs.append(f"45F bank {bank}: {len(balls)} balls for {len(sigs)} signals"); continue
    for s, b in zip(sigs, balls):
        p45("SDRAM45", s, b, "io" if "dq[" in s else "out", SDRAM_PART, str(SDRAM_PINS[s]), "SELECTED; schematic pending",
            "data bank" if bank == "2" else "address/control bank")
        lpf45.append(f'LOCATE COMP "{s}" SITE "{b}" ;  # {B45[b]["pin_function"]}, bank {bank}')
        lpf45.append(f'IOBUF PORT "{s}" IO_TYPE=LVCMOS33 SLEWRATE=FAST' + (" PULLMODE=NONE" if "dq[" in s else "") + " ;")

# Include package supplies explicitly; no implied power pins or NC connections.
for fn, pins in SDRAM_SUPPLY.items():
    for pin in pins:
        net = "NO_CONNECT" if fn == "NC" else ("GND" if fn.startswith("VSS") else "3V3_45_MEM")
        add("SDRAM45_POWER", fn, SDRAM_PART, str(pin), fn, "SDRAM", "-" if fn == "NC" else ("0 V" if net == "GND" else "3.3 V"),
            "nc" if fn == "NC" else "power", net, "-", "SELECTED; schematic pending",
            "NC must remain unconnected" if fn == "NC" else "See R10_INTERCONNECT_DECISIONS.md for rail sequencing")

# Fail before touching generated deliverables, so invalid input cannot overwrite them.
if errs:
    for e in errs: print("ERROR", e)
    sys.exit(1)

# ---------------- write ----------------
with open(os.path.join(H, "R10_flash_pinmux.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)
os.makedirs(os.path.join(H, "lpf"), exist_ok=True)
hdr = "# GENERATED by hardware/gen_flash_pinmux.py -- do not edit.\n"
open(os.path.join(H, "lpf", "r10_12f_mem_tqfp144.lpf"), "w").write(hdr + "\n".join(lpf12_tq) + "\n")
open(os.path.join(H, "lpf", "r10_12f_mem_proxy256.lpf"), "w").write(
    hdr + "# 12F PSRAM on the caBGA256 balls of the same PIO sites as the TQFP144 pins (nextpnr has no TQFP144)\n"
    + "\n".join(lpf12_px) + "\n")
open(os.path.join(H, "lpf", "r10_45f_sdram.lpf"), "w").write(hdr + "\n".join(lpf45) + "\n")
from collections import Counter
print(Counter(r["group"] for r in rows))
if errs:
    for e in errs: print("ERROR", e)
    sys.exit(1)
print(f"FLASH_PINMUX_PASS {len(rows)} rows, 0 errors")
