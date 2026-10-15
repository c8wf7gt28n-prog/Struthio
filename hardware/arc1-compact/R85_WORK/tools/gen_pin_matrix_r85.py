#!/usr/bin/env python3
"""ARC-1 Compact R8.5 -- pin matrices and LPF, all generated from board/r85_board_plan.json (itself generated
from cad/gen/design.py, the single electrical source).

Outputs
  board/F133_PINMUX_MATRIX_R85.csv / .json   every F133 pin: net, mux function, interface class, state per phase
  board/ECP5_BALL_MAP_R85.csv                all 381 LFE5U-45F caBGA381 balls -> net, role, I/O standard, pull mode
  board/ECP5_BANK_TABLE_R85.csv              VCCIO per bank, balls used, I/O standard
  fpga_ecp5/constraints/arc1_ecp5_r85.lpf    nextpnr-ecp5 constraints (LOCATE/IOBUF/FREQUENCY/SYSCONFIG)
Checks (exit 1 on failure): every RTL top-level port has exactly one ball; every located ball is a user I/O of the
ECP5 pinout; no RTL port on a RESERVED/NC/dedicated ball; every used bank's VCCIO matches the I/O standard; every
F133 pin with a net has an interface class and a function index from DS Table 4-3 (or GPIO/EINT).
Usage: gen_pin_matrix_r85.py [--check-only]
"""
import csv
import json
import os
import re
import sys

R85 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PLAN = json.load(open(os.path.join(R85, "board", "r85_board_plan.json")))
COMPS = {c["ref"]: c for c in PLAN["components"]}
ECP5_CSV = list(csv.DictReader(open(os.path.join(R85, "sources", "lattice", "lfe5u45_cabga381_pinout.csv"))))
MUX = json.load(open(os.path.join(R85, "sources", "f133", "f133_boot_usb_facts.json")))["pin_mux_from_DS_Table_4_3"]
errors = []

# ---------------------------------------------------------------- F133 interface classes
# function index: DS Table 4-3 (sources/f133); F0 input, F1 output, F14 EINT are available on every GPIO (DS 4.3 note)
F133_ROLE = {
    "SPI0_CLK_F": ("NOR_BOOT+ECP5_CONFIG+ECP5_OPERATIONAL", "F2 SPI0-CLK", "out"),
    "SPI0_CS0_N": ("NOR_BOOT", "F2 SPI0-CS0", "out"),
    "SPI0_MOSI": ("NOR_BOOT+ECP5_CONFIG+ECP5_OPERATIONAL", "F2 SPI0-MOSI (F4 BOOT-SEL0 strap at reset)", "out"),
    "SPI0_MISO": ("NOR_BOOT+ECP5_OPERATIONAL", "F2 SPI0-MISO (F4 BOOT-SEL1 strap at reset)", "in"),
    "SPI0_IO2": ("NOR_BOOT", "F2 SPI0-WP (held high by 10k)", "io"),
    "SPI0_IO3": ("NOR_BOOT", "F2 SPI0-HOLD (held high by 10k)", "io"),
    "FPGA_SS_N_F": ("ECP5_CONFIG+ECP5_OPERATIONAL", "F1 GPIO-OUT (software CS: SN in sysCONFIG, mailbox CS after DONE)", "out"),
    "FPGA_BUS_EN_N": ("ECP5_CONFIG+ECP5_OPERATIONAL", "F1 GPIO-OUT (isolation buffers OE#)", "out"),
    "FPGA_PROGRAMN_F": ("ECP5_CONFIG", "F1 GPIO-OUT low / F0 input (open-drain use only)", "od"),
    "FPGA_INITN": ("ECP5_CONFIG", "F0 GPIO-IN", "in"),
    "FPGA_DONE": ("ECP5_CONFIG", "F14 PE-EINT9 (DONE edge)", "in"),
    "FPGA_IRQ_N": ("ECP5_OPERATIONAL+INTERRUPT", "F14 PE-EINT5", "in"),
    "FPGA_PWR_EN_F": ("ECP5_POWER", "F1 GPIO-OUT", "out"),
    "FPGA_VCC_PG": ("ECP5_POWER+DIAGNOSTIC", "F0 GPIO-IN", "in"),
    "PSRAM_PWR_REQ": ("ECP5_POWER", "F1 GPIO-OUT", "out"),
    "PSRAM_PG": ("ECP5_POWER+DIAGNOSTIC", "F0 GPIO-IN", "in"),
    "BT_SS_N": ("BT820_SPI1", "F4 SPI1-CS", "out"), "BT_SCK_F": ("BT820_SPI1", "F4 SPI1-CLK", "out"),
    "BT_MOSI_F": ("BT820_SPI1", "F4 SPI1-MOSI", "out"), "BT_MISO": ("BT820_SPI1", "F4 SPI1-MISO", "in"),
    "BT_RST_N_F": ("BT820_SPI1", "F1 GPIO-OUT", "out"), "BT_INT_N": ("BT820_SPI1+INTERRUPT", "F14 PD-EINT17", "in"),
    "SD_D1": ("MICROSD", "F2 SDC0-D1", "io"), "SD_D0": ("MICROSD", "F2 SDC0-D0", "io"), "SD_CLK_F": ("MICROSD", "F2 SDC0-CLK", "out"),
    "SD_CMD": ("MICROSD", "F2 SDC0-CMD", "io"), "SD_D3": ("MICROSD", "F2 SDC0-D3", "io"), "SD_D2": ("MICROSD", "F2 SDC0-D2", "io"),
    "SD_DET_N": ("MICROSD+INTERRUPT", "F14 PF-EINT6", "in"), "SD_PWR_EN": ("MICROSD", "F1 GPIO-OUT", "out"),
    "USB0_DP": ("USB0_DEVICE_FEL", "dedicated USB0-DP", "io"), "USB0_DM": ("USB0_DEVICE_FEL", "dedicated USB0-DM", "io"),
    "VBUS_SENSE": ("USB0_DEVICE_FEL", "F0 GPIO-IN", "in"),
    "USB_CUR_OUT1": ("USB0_DEVICE_FEL", "F0 GPIO-IN", "in"), "USB_CUR_OUT2": ("USB0_DEVICE_FEL", "F0 GPIO-IN", "in"),
    "I2S_DOUT": ("I2S", "F3 I2S2-DOUT0", "out"), "I2S_BCLK": ("I2S", "F3 I2S2-BCLK", "out"), "I2S_LRCK": ("I2S", "F3 I2S2-LRCK", "out"),
    "AMP_EN": ("I2S", "F1 GPIO-OUT", "out"),
    "UART0_TX": ("DIAGNOSTIC", "F6 UART0-TX", "out"), "UART0_RX": ("DIAGNOSTIC", "F6 UART0-RX", "in"),
    "LED_STATUS": ("DIAGNOSTIC", "F1 GPIO-OUT", "out"), "LED_ERROR": ("DIAGNOSTIC", "F1 GPIO-OUT", "out"),
    "MN_PWR_EN": ("BT820_SPI1", "F1 GPIO-OUT (default on by pull-up)", "out"),
}
for b in ("UP", "DOWN", "LEFT", "RIGHT", "A", "B", "X", "Y", "L", "R", "START", "SELECT", "HOME"):
    F133_ROLE[f"BTN_{b}"] = ("BUTTONS+INTERRUPT", "F14 EINT (internal pull-up)", "in")

# state per phase (P0 reset/BROM .. P6 fault) for the pins that matter for NOR/FPGA ownership
PHASE = {
    "SPI0_CLK_F": ["BROM drives (NOR read)", "SPI0", "SPI0", "SPI0 (CCLK via U21)", "SPI0", "SPI0", "SPI0"],
    "SPI0_MOSI": ["strap 0 sampled, then BROM", "SPI0", "SPI0", "SPI0 (D0 via U22)", "SPI0", "SPI0", "SPI0"],
    "SPI0_MISO": ["strap 0 sampled, then BROM", "SPI0", "SPI0", "SPI0 (FPGA MISO unused in config)", "SPI0 (U24 when FPGA CS low)",
                  "SPI0 (U24 when FPGA CS low)", "SPI0"],
    "FPGA_BUS_EN_N": ["hi-Z: 10k pull-up -> buffers OFF", "1 (OFF)", "1 (OFF)", "0 (ON)", "0 (ON)", "0 (ON)", "1 (OFF)"],
    "FPGA_SS_N_F": ["hi-Z: 10k pull-up -> deselected", "1", "1", "SN for bitstream", "mailbox CS", "mailbox CS", "1"],
    "FPGA_PROGRAMN_F": ["hi-Z (PROGRAMN pulled up, FPGA unpowered)", "input", "input", "low pulse >= 110 ns, then input",
                        "input", "input", "low (hold FPGA unconfigured) or input"],
    "FPGA_PWR_EN_F": ["hi-Z: 100k pull-down -> FPGA rails OFF", "0 or 1 (policy)", "1", "1", "1", "1", "0 (power-cycle) or 1"],
    "PSRAM_PWR_REQ": ["hi-Z: 100k pull-down -> PSRAM OFF", "0", "0 (quiesce before reconfigure)", "0", "0 -> 1 after DONE",
                      "1", "0"],
}
PHASE_NAMES = ["P0_reset_BROM", "P1_launcher", "P2_select", "P3_configure", "P4_handshake", "P5_play", "P6_fault"]

f133 = COMPS["U15"]
rows = []
for num, p in sorted(f133["pins"].items(), key=lambda kv: int(kv[0])):
    net = p["net"]
    name = p["name"]
    gp = re.match(r"^P([A-G])(\d+)$", name)
    if net in F133_ROLE:
        cls, fn, d = F133_ROLE[net]
    elif net and not gp:
        cls, fn, d = ("POWER_CLOCK_RESET" if net not in ("USB0_DP", "USB0_DM") else "USB0_DEVICE_FEL"), "dedicated", "-"
    elif net:
        cls, fn, d = "UNCLASSIFIED", "?", "?"
        errors.append(f"F133 {name} ({net}) has no interface class")
    else:
        cls, fn, d = ("SPARE" if gp else "NC"), "-", "-"
        if name.startswith("USB1"):
            cls = "USB1_HOST_NOT_ROUTED"
    # function index must exist in the DS transcription where we have it
    m = re.match(r"^F(\d+) (\S+)", fn)
    if gp and m and m.group(1) not in ("0", "1", "14") and name in MUX:
        if MUX[name].get("F" + m.group(1), "").split("/")[0] != m.group(2).split("/")[0]:
            errors.append(f"F133 {name}: F{m.group(1)} {m.group(2)} does not match DS Table 4-3 ({MUX[name].get('F' + m.group(1))})")
    row = {"pin": num, "name": name, "net": net or "", "interface": cls, "function": fn, "direction": d,
           "domain": "3V3 (VCC-IO/PD/PE/PG)" if gp and name[1] in "CDEG" else ("3V3" if gp else "-"),
           "nc_reason": p.get("nc_reason") or ""}
    for i, ph in enumerate(PHASE_NAMES):
        row[ph] = PHASE.get(net, [""] * 7)[i]
    rows.append(row)

with open(os.path.join(R85, "board", "F133_PINMUX_MATRIX_R85.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
classes = {}
for r in rows:
    for k in r["interface"].split("+"):
        classes.setdefault(k, []).append(r["name"])
json.dump({"schema": "arc1-r85-f133-pinmux-v1", "source": "board/r85_board_plan.json (generated from cad/gen/design.py)",
           "function_source": "F133 DS rev 2.3 Table 4-3 (sources/f133/f133_boot_usb_facts.json)",
           "phases": PHASE_NAMES, "interfaces": {k: sorted(v) for k, v in sorted(classes.items())}, "pins": rows},
          open(os.path.join(R85, "board", "F133_PINMUX_MATRIX_R85.json"), "w"), indent=1)

# ---------------------------------------------------------------- ECP5 ball map + LPF
NET2PORT = {
    "FPGA_OSC_25M": ("clk_25m", "in", "NONE"),
    "PSRAM_CE_N": ("psram_ce_n", "io", "NONE"),       # NONE: weak pull-down vs 10k pull-up would hold CE# at ~1.8 V
    "PSRAM_SCLK_F": ("psram_sclk", "out", "NONE"),
    "PSRAM_SIO0": ("psram_sio[0]", "io", "NONE"), "PSRAM_SIO1": ("psram_sio[1]", "io", "NONE"),
    "PSRAM_SIO2": ("psram_sio[2]", "io", "NONE"), "PSRAM_SIO3": ("psram_sio[3]", "io", "NONE"),
    "PSRAM_PG": ("psram_pg", "in", "NONE"), "PSRAM_EN": ("psram_pwr_en", "in", "DOWN"),
    "FPGA_SCK": ("spi_sck", "in", "NONE"),            # R1 only; U3 (CCLK) is dedicated
    "FPGA_MOSI": ("spi_mosi", "in", "DOWN"), "FPGA_MISO": ("spi_miso", "io", "DOWN"), "FPGA_SS_N": ("spi_cs_n", "in", "NONE"),
    "FPGA_IRQ_N": ("irq_n", "io", "NONE"),
    "FPGA_LED0": ("led", "out", "NONE"), "FPGA_DBG_TX": ("dbg_tx", "out", "NONE"), "FPGA_DBG_RX": ("dbg_rx", "in", "UP"),
}
u18 = COMPS["U18"]
csvb = {r["ball"]: r for r in ECP5_CSV}
ballrows, lpf_loc, used_banks = [], [], {}
port_balls = {}
for ball, p in sorted(u18["pins"].items(), key=lambda kv: (kv[0][0], int(kv[0][1:]))):
    r = csvb[ball]
    net = p["net"] or ""
    role, port, pull = "", "", ""
    if r["pin_type"] == "IO" and net in NET2PORT:
        port, d, pull = NET2PORT[net]
        role = "user I/O (RTL port)"
        port_balls.setdefault(port, []).append(ball)
        used_banks.setdefault(r["bank"], set()).add(ball)
    elif r["pin_type"] == "IO" and net:
        role = "user I/O, board-only (not an RTL port)"
        used_banks.setdefault(r["bank"], set()).add(ball)
    elif r["pin_type"] == "IO":
        role = "unused I/O (tri-state, weak pull-down)"
    elif r["pin_type"] == "DEDICATED":
        role = "dedicated " + ("sysCONFIG" if r["bank"] == "8" else "JTAG")
    elif r["pin_function"] == "RESERVED" or r["pin_type"] == "NC":
        role = "do not connect"
        if net:
            errors.append(f"ECP5 {ball} {r['pin_function']} connected to {net}")
    else:
        role = "supply"
    if r["pin_type"] != "IO" and net in NET2PORT and r["pin_type"] == "DEDICATED" and net != "FPGA_SCK":
        errors.append(f"RTL net {net} on dedicated ball {ball}")
    ballrows.append({"ball": ball, "pin_function": r["pin_function"], "bank": r["bank"], "dual_function": r["dual_function"],
                     "pin_type": r["pin_type"], "net": net, "role": role, "rtl_port": port,
                     "io_type": "LVCMOS33" if port else "", "pullmode": pull, "nc_reason": p.get("nc_reason") or ""})
with open(os.path.join(R85, "board", "ECP5_BALL_MAP_R85.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(ballrows[0].keys()))
    w.writeheader()
    w.writerows(ballrows)

# RTL port list from the top module
rtl = open(os.path.join(R85, "fpga_ecp5", "rtl", "arc1_ecp5_top.sv")).read()
hdr = rtl[rtl.index("module arc1_ecp5_top"):]
hdr = hdr[hdr.index(") (") + 3:hdr.index(");")]
ports = []
for m in re.finditer(r"(input|output|inout)\s+wire\s*(\[(\d+):0\])?\s*([a-z0-9_]+)", hdr):
    if m.group(2):
        ports += [f"{m.group(4)}[{i}]" for i in range(int(m.group(3)) + 1)]
    else:
        ports.append(m.group(4))
for pt in ports:
    if len(port_balls.get(pt, [])) != 1:
        errors.append(f"RTL port {pt} on balls {port_balls.get(pt)}")
for pt in port_balls:
    if pt not in ports:
        errors.append(f"LPF port {pt} is not an RTL port")

# banks: every VCCIO ball's net and the I/O standard
bank_rows = []
vccio = {}
for ball, p in u18["pins"].items():
    m = re.match(r"^VCCIO(\d)$", p["name"])
    if m:
        vccio.setdefault(m.group(1), set()).add(p["net"])
RAILV = {"3V3_FPGA": 3.3}
for bank in sorted(vccio):
    nets = vccio[bank]
    v = {RAILV.get(n) for n in nets}
    if len(v) != 1 or None in v:
        errors.append(f"bank {bank} VCCIO nets {nets}")
    vv = v.pop() if len(v) == 1 else None
    if vv != 3.3 and used_banks.get(bank):
        errors.append(f"bank {bank} at {vv} V carries LVCMOS33 balls")
    bank_rows.append({"bank": bank, "vccio_net": "/".join(sorted(nets)), "vccio_V": vv,
                      "balls_used": " ".join(sorted(used_banks.get(bank, []))), "io_standard": "LVCMOS33",
                      "hot_socket": "tolerant (top/bottom bank)" if bank in ("0", "1", "8") else
                      "NOT hot-socket safe (left/right bank): VCCIO switched with VCC; no external source above VCCIO"})
with open(os.path.join(R85, "board", "ECP5_BANK_TABLE_R85.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(bank_rows[0].keys()))
    w.writeheader()
    w.writerows(bank_rows)

lpf = ["# GENERATED by tools/gen_pin_matrix_r85.py from board/r85_board_plan.json -- do not edit.",
       "# LFE5U-45F-6BG381C (caBGA381). Every bank VCCIO = 3V3_FPGA (3.3 V) -> LVCMOS33.",
       "# sysCONFIG: slave SPI (CFG[2:0]=001 strapped on the board); SLAVE_SPI_PORT=DISABLE makes D0/D1/SN/D7 user I/O",
       "# after DONE (TN-02039 Table 7.1). CCLK (U3) is dedicated and carries the same board net as spi_sck (R1).",
       "SYSCONFIG SLAVE_SPI_PORT=DISABLE CONFIG_IOVOLTAGE=3.3 COMPRESS_CONFIG=ON MCCLK_FREQ=2.4 ;",
       "FREQUENCY PORT \"clk_25m\" 25.000000 MHZ ;"]
for b in ballrows:
    if b["rtl_port"]:
        lpf.append(f"LOCATE COMP \"{b['rtl_port']}\" SITE \"{b['ball']}\" ;  # {b['net']}, bank {b['bank']}")
for b in ballrows:
    if b["rtl_port"]:
        extra = " SLEWRATE=FAST" if b["rtl_port"] in ("psram_sclk", "spi_miso") or b["rtl_port"].startswith("psram_sio") \
            or b["rtl_port"] == "psram_ce_n" else ""
        lpf.append(f"IOBUF PORT \"{b['rtl_port']}\" IO_TYPE=LVCMOS33 PULLMODE={b['pullmode']}{extra} ;")
out = os.path.join(R85, "fpga_ecp5", "constraints", "arc1_ecp5_r85.lpf")
if "--check-only" not in sys.argv:
    open(out, "w").write("\n".join(lpf) + "\n")

print(f"F133 pins {len(rows)}, interfaces {sorted(classes)}")
print(f"ECP5 balls {len(ballrows)}, RTL ports {len(ports)} located, banks {[(r['bank'], r['vccio_V']) for r in bank_rows]}")
for e in errors:
    print("ERROR", e)
print("PIN_MATRIX_PASS" if not errors else "PIN_MATRIX_FAIL")
sys.exit(1 if errors else 0)
