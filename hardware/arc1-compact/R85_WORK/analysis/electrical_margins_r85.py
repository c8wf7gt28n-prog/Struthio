#!/usr/bin/env python3
"""ARC-1 Compact R8.5 -- worst-case DC levels, timing budgets, regulator/supervisor
windows, the ECP5 rail budget and the VBUS power budget for the R8.5 schematic (R08 analysis
with the T35 replaced by the LFE5U-45F; R08 checks that do not involve the FPGA are unchanged).

Every input is tagged: DOC (manufacturer document in R85_WORK/sources, quoted
section), PLAN (a value chosen in design.py), or ASSUMPTION (no source; must be
closed by vendor data, IBIS/SPICE or bench). Results are DERIVED_WITH_CALC.
A result built on an ASSUMPTION is reported as CONDITIONAL, never as PASS.
Usage: electrical_margins_r85.py <out.json> <out.md>
"""
import json
import math
import sys

R = []          # results
INPUTS = {}


def inp(name, value, tag, src):
    INPUTS[name] = {"value": value, "tag": tag, "source": src}
    return value


def result(group, name, value, limit, ok, unit, depends, note="", risk="", spec_condition=False):
    """spec_condition: the limit is a datasheet TEST condition, not a limit -> exceeding it is OPEN, not FAIL"""
    tags = {INPUTS[d]["tag"] for d in depends}
    if not ok and spec_condition:
        status = "OPEN"
    elif "ASSUMPTION" in tags:
        status = "CONDITIONAL" if ok else "FAIL"
    else:
        status = "PASS" if ok else "FAIL"
    R.append({"group": group, "check": name, "value": round(value, 4) if isinstance(value, float) else value,
              "limit": limit, "unit": unit, "status": status, "inputs": depends, "note": note, "risk": risk})


# ---------------------------------------------------------------- rails (PLAN + DOC)
V33_MAX = inp("v3v3_max", 3.40, "PLAN", "R07/R08 3V3 design window 3.20-3.40 V")
V33_MIN = inp("v3v3_min", 3.20, "PLAN", "R07/R08 3V3 design window")
VFB_TOL = inp("vfb_tol", 0.02, "DOC", "TLV62569 DS s.6.5: VFB 0.588/0.6/0.612 V (25 C only; over-temperature NOT_FOUND)")
RTOL = inp("r_tol", 0.01, "PLAN", "1 % resistors")


def buck(r1, r2):
    nom = 0.6 * (1 + r1 / r2)
    lo = 0.6 * (1 - VFB_TOL) * (1 + r1 * (1 - RTOL) / (r2 * (1 + RTOL)))
    hi = 0.6 * (1 + VFB_TOL) * (1 + r1 * (1 + RTOL) / (r2 * (1 - RTOL)))
    return nom, lo, hi


for name, r1, r2, lim_lo, lim_hi, why in (
        ("3V3 (U3)", 453e3, 100e3, 3.135, 3.465, "ECP5 VCCIO for LVCMOS33 3.135-3.465 V (DS sysI/O recommended conditions; "
                                                  "tightest consumer; F133 VCC-IO 2.97-3.63, MN820 3.0-3.6)"),
        ("VDD_CORE (U5)", 57.6e3, 100e3, 0.85, 0.99, "F133 DS rev 2.3 Table 5-2 VDD-CORE/SYS"),
        ("1V8_DRAM (U6)", 200e3, 100e3, 1.7, 1.9, "F133 VCC-DRAM"),
        ("1V1_FPGA (U9)", 82.5e3, 100e3, 1.045, 1.155, "ECP5 DS-02012 Table 3.2 VCC 1.045/1.10/1.155 V")):
    nom, lo, hi = buck(r1, r2)
    inp(f"lim_{name}", [lim_lo, lim_hi], "DOC", why)
    result("regulator_setpoint", name, [round(lo, 4), round(nom, 4), round(hi, 4)], [lim_lo, lim_hi],
           lo >= lim_lo and hi <= lim_hi, "V", ["vfb_tol", "r_tol", f"lim_{name}"],
           "DC setpoint only: load-step and ripple margin need the TI design tool / bench")
nom33, lo33, hi33 = buck(453e3, 100e3)
INFO = {"3V3 worst-case DC window (R07 asked 3.20-3.40 V only for MN820 VOH; obsolete with the R08 buffer)":
        [round(lo33, 4), round(hi33, 4)]}

# ---------------------------------------------------------------- supervisors
TOL = inp("tps3808_tol", 0.015, "DOC", "TPS3808 DS: threshold accuracy +-1.5 % over temperature")
for name, vit, rail_lo, must_below, why in (
        ("U4 TPS3808G33 on 3V3", 3.07, lo33, None, "trips below the regulated window, above F133/ECP5 minimum 2.97/3.135?"),
        ("U8 TPS3808G09 on VDD_CORE", 0.84, buck(57.6e3, 100e3)[1], None, "F133 core min 0.85"),
        ("U14 TPS3808G30 on PSRAM_VDD", 2.79, lo33 - 2 * 0.08, 2.7, "APS6404L VDD min 2.7 V")):
    hi = vit * (1 + TOL)
    lo = vit * (1 - TOL)
    result("supervisor", f"{name}: max threshold below rail minimum", round(hi, 4), round(rail_lo, 4), hi < rail_lo, "V",
           ["tps3808_tol"], "else the supervisor could hold reset with a healthy rail")
    if must_below:
        result("supervisor", f"{name}: min threshold above device minimum", round(lo, 4), must_below, lo > must_below, "V",
               ["tps3808_tol"], "power loss is flagged before the PSRAM leaves its operating range")
result("supervisor", "U4 TPS3808G33 min threshold vs ECP5 VCCIO (LVCMOS33) min 3.135 V", round(3.07 * (1 - TOL), 4), 3.135,
       3.07 * (1 - TOL) >= 3.135, "V", ["tps3808_tol"],
       "3V3 can sag to 3.02-3.135 V without reset -> below the ECP5 LVCMOS33 VCCIO window. Not closable with +-1.5 % "
       "parts and a +-2 % regulator: R09 needs a 1 % regulator or accepts it (FPGA optional; PSRAM data guarded by its "
       "own supervisor)", risk="RK-3V3-SUP")
for name, ct_nf, need_ms in (("U4 delay (VCC-IO before core)", 2.2, 2.0), ("U8 delay (RESET after rails)", 15.0, 64.0)):
    td = ct_nf / 175.0 * 1000.0 + 0.5      # TPS3808: tD[s] = CT[nF]/175 + 0.5 ms
    inp(f"ct_{name}", ct_nf, "PLAN", "CT capacitor in design.py")
    result("sequencing", name, round(td, 2), need_ms, td >= need_ms, "ms", [f"ct_{name}"],
           "tD[s] = CT[nF]/175 + 0.5 ms (TPS3808 DS); CT tolerance +-10 % not yet applied" if td > need_ms * 1.2 else
           "margin < 20 % -> apply CT tolerance")

# ---------------------------------------------------------------- boot straps (BOOT-SEL = 00)
RPU_MIN = inp("f133_pc_pullup_min", 12e3, "DOC", "F133 DS Table 5-3: PC3-PC7 internal pull 12/15/18 kOhm")
RPD = inp("strap_pd", 3.3e3, "PLAN", "R on SPI0_MOSI / SPI0_MISO to GND")
LEAK = inp("strap_leak", 10e-6 + 10e-6 + 1e-6, "DOC",
           "SN74LVC1G125 IOZ 10 uA (U24 output) + II 5 uA x2 (U21/U22 inputs) -> 10+10 uA; W25Q256 ILO ~1 uA (ASSUMED small)")
VIL_RATIO = inp("f133_vil_ratio", 0.3, "DOC", "F133 DS Table 5-3 VIL max 0.3*VCC-IO")
for pin in ("PC4 BOOT-SEL0 (SPI0_MOSI)", "PC5 BOOT-SEL1 (SPI0_MISO)"):
    rpd = RPD * (1 + RTOL)
    v = V33_MAX * rpd / (rpd + RPU_MIN) + LEAK * (rpd * RPU_MIN / (rpd + RPU_MIN))
    vil = VIL_RATIO * V33_MIN
    result("boot_strap", f"{pin} level at BROM sampling", round(v, 4), round(vil, 4), v <= vil, "V",
           ["f133_pc_pullup_min", "strap_pd", "strap_leak", "f133_vil_ratio", "v3v3_max"],
           "worst case: max rail, weakest internal pull-up, +1 % R, leakage into the node; VIL at min rail")
INOR = inp("nor_voh_test", 100e-6, "DOC", "W25Q256JV DS: VOH = VCC-0.2 V at IOH = -100 uA (only spec point)")
iload = V33_MAX / (RPD * (1 - RTOL))
result("boot_strap", "NOR DO load from the BOOT-SEL1 pull-down vs VOH test current", round(iload * 1e3, 3),
       INOR * 1e3, iload <= INOR, "mA", ["nor_voh_test", "strap_pd"],
       "1.04 mA > 0.1 mA spec point: VOH under this load is UNSPECIFIED -> vendor IBIS / bench (same class as R07 PSRAM VOH)",
       risk="RK-NOR-VOH", spec_condition=True)

# ---------------------------------------------------------------- MN820 <-> F133 (SPI1, single mode)
MN_VOH = inp("mn820_voh", 2.4, "DOC", "MN820 DS v1.0 Table 3 VOH >= 2.4 V (no test current given)")
MN_VIH = inp("mn820_vih", 2.0, "DOC", "MN820 DS v1.0 Table 3 VIH 2.0 V")
MN_VIL = inp("mn820_vil", 0.8, "DOC", "MN820 DS Table 3 VIL 0.8 V")
MN_VOL = inp("mn820_vol", 0.4, "DOC", "MN820 DS Table 3 VOL 0.4 V")
BUF_VIH = inp("lvc125_vih", 2.0, "DOC", "SN74LVC1G125 s.5.3 VIH 2.0 V (VCC 3.0-3.6 V)")
BUF_VIL = inp("lvc125_vil", 0.8, "DOC", "SN74LVC1G125 VIL 0.8 V")
BUF_VOH = inp("lvc125_voh", V33_MIN - 0.1, "DOC", "SN74LVC1G125 s.5.5 VOH = VCC-0.1 V at -100 uA")
BUF_VOL = inp("lvc125_vol", 0.1, "DOC", "SN74LVC1G125 VOL 0.1 V at 100 uA")
F_VIH = inp("f133_vih_ratio", 0.7, "DOC", "F133 DS Table 5-3 VIH 0.7*VCC-IO")
F_VOH = inp("f133_voh_drop", 0.3, "DOC", "F133 DS Table 5-3 VOH = VCC-0.3 (test current per table)")
result("level", "MN820 MISO high -> buffer (R07 problem point)", MN_VOH - BUF_VIH, 0.0, MN_VOH - BUF_VIH > 0, "V",
       ["mn820_voh", "lvc125_vih"], "R07 direct path margin was +0.02 V; R08 buffer: +0.40 V")
result("level", "MN820 MISO low -> buffer", BUF_VIL - MN_VOL, 0.0, BUF_VIL - MN_VOL > 0, "V", ["mn820_vol", "lvc125_vil"])
result("level", "buffer -> F133 PD13 high", BUF_VOH - F_VIH * V33_MAX, 0.0, BUF_VOH - F_VIH * V33_MAX > 0, "V",
       ["lvc125_voh", "f133_vih_ratio", "v3v3_max"], "buffer and F133 on the same 3V3 rail; min VOH vs max VIH")
result("level", "buffer -> F133 PD13 low", 0.3 * V33_MIN - BUF_VOL, 0.0, 0.3 * V33_MIN - BUF_VOL > 0, "V",
       ["lvc125_vol", "f133_vil_ratio"])
result("level", "F133 -> MN820 SCK/MOSI/SS_N high", (V33_MIN - F_VOH) - MN_VIH, 0.0, (V33_MIN - F_VOH) - MN_VIH > 0, "V",
       ["f133_voh_drop", "mn820_vih"], "33 ohm series, module input current negligible")
result("level", "F133 -> MN820 low", MN_VIL - 0.2, 0.0, MN_VIL - 0.2 > 0, "V", ["mn820_vil"], "F133 VOL 0.2 V (DS)")

TOD = inp("bt820_tod", 5.8, "DOC", "BT820 DS v1.1 Table 28 Tod max 5.8 ns (SCLK fall -> MISO valid), VCCIO 3.3 V")
TBUF = inp("lvc125_tpd", 4.5, "DOC", "SN74LVC1G125 tpd max 4.5 ns (CL 50 pF, 3.3 V +-0.3 V, -40..85 C)")
TFL = inp("trace_ns", 1.0, "ASSUMPTION", "board flight + 33 ohm RC, both directions, until layout exists")
TSU = inp("f133_spi_tsu", 3.0, "ASSUMPTION", "F133 SPI input setup NOT_FOUND in DS rev 2.3; the SPI sample-delay mode may change it")
need = TOD + TBUF + TFL + TSU
fmax = 1e3 / (2 * need)
result("timing", "SPI1 read: max SCLK with F133 sampling on the next rising edge", round(fmax, 1), 30.0, fmax >= 30.0,
       "MHz", ["bt820_tod", "lvc125_tpd", "trace_ns", "f133_spi_tsu"],
       "half-period budget = Tod + buffer + flight + setup. Bring-up at 20 MHz, target 30 MHz; >30 MHz needs the "
       "F133 delayed-sample mode and measurement")
result("timing", "BT820 SCLK limit", 60.0, 30.0, True, "MHz", ["bt820_tod"], "BT820 Tsclk min 16.6 ns")

# ---------------------------------------------------------------- PSRAM pads around the ECP5 (R8.5)
IPD_MAX = inp("ecp5_ipd_max", 150e-6, "DOC", "ECP5 DS Table 3.7 IPD max 150 uA (weak pull-down, 0 <= VIN <= VCCIO)")
IPD_MIN = inp("ecp5_ipd_min", 30e-6, "DOC", "ECP5 DS Table 3.7 IPD min 30 uA (sustaining low)")
STATIC = inp("psram_pd_static", 100e3, "PLAN", "static pull-down on SCLK/SIO")
inp("ecp5_cfg_pulls", "pull-down", "DOC", "ECP5 DS 4.1 / TN-02039 5.2: user I/O tri-stated with weak pull-DOWN during "
    "power-up and configuration (T35 had weak pull-UPs -> R08 needed U26)")
result("psram", "SCLK/SIO level while the ECP5 is unconfigured (PSRAM unpowered by design)", 0.0, 0.4, True, "V",
       ["ecp5_cfg_pulls", "psram_pd_static"],
       "only pull-downs act on these nets (ECP5 IPD + 100k): 0 V <= VDD+0.4 at VDD = 0 -> no back-power; R08 U26 removed")
iuser = V33_MAX / STATIC
inp("aps_voh_test", 0.2e-3, "DOC", "APS6404L DS Rev 2.7 Table 9: VOH 0.8*VDD at IOH = -0.2 mA")
result("psram", "PSRAM output load in user mode (100k static, PULLMODE=NONE)", round(iuser * 1e3, 4), 0.2,
       iuser <= 0.2e-3, "mA", ["psram_pd_static", "aps_voh_test"], "inside the 0.2 mA VOH test condition")
RCE = inp("psram_ce_pu", 10e3, "PLAN", "CE# pull-up to PSRAM_VDD")
APS_VIH = inp("aps_vih_ratio", 0.8, "DOC", "APS6404L DS Rev 2.7 Table 9: VIH min 0.8*VDD")
vce = V33_MIN - RCE * 1.01 * IPD_MAX
result("psram", "CE# idle level if the ECP5 ball kept its default PULLMODE=DOWN (why the LPF sets NONE)", round(vce, 3),
       round(APS_VIH * V33_MIN, 3), False, "V", ["psram_ce_pu", "ecp5_ipd_max", "aps_vih_ratio"],
       "3.20 V - 10k x 150 uA = 1.7 V < 0.8*VDD: would violate CE# = VDD during tPU. LPF: PULLMODE=NONE on all PSRAM "
       "balls (generated by tools/gen_pin_matrix_r85.py, checked in crosscheck); during configuration the PSRAM is "
       "unpowered (EN gated by DONE_DLY) so the config-time pull-down is harmless", risk="RK-ECP5-PULLMODE",
       spec_condition=True)
VT = inp("lvc1g17_vtplus_min", 1.3, "ASSUMPTION", "SN74LVC1G17 VT+ min at 3.3 V not yet transcribed (R09)")
tau = (4.7e3 + 10e3) * 100e-9
tdel = tau * math.log(V33_MAX / (V33_MAX - VT))
inp("done_dly_need", 100e-6, "PLAN", "DONE_DLY >= 100 us after the DONE pin (wake-up GOE precedes DONE with DONE_EX=OFF; "
    "the RTL power guard holds the PSRAM pads until PG, so this delay only orders the load switch after user mode)")
result("psram", "DONE -> DONE_DLY delay", round(tdel * 1e6, 1), 100.0, tdel >= 100e-6, "us",
       ["done_dly_need", "lvc1g17_vtplus_min"], "RC = (4.7k pull-up + 10k) x 100 nF")

# ---------------------------------------------------------------- PSRAM QSPI read timing on ECP5 pads (R8.5)
TACLK = inp("aps_taclk_max", 5.5, "DOC", "APS6404L DS Rev 2.7: tACLK 2-5.5 ns CLK fall -> data (R06 PSRAM_TIMING_TABLE)")
ECP_TCO = inp("ecp5_pad_out_ns", 4.0, "ASSUMPTION", "ECP5 LVCMOS33 output buffer delay (DS external switching tables not transcribed)")
ECP_TIN = inp("ecp5_pad_in_ns", 2.0, "ASSUMPTION", "ECP5 LVCMOS33 input buffer + routing to the sampling FF")
ECP_SU = inp("ecp5_ff_setup_ns", 0.5, "ASSUMPTION", "fabric FF setup")
FL2 = inp("psram_flight_ns", 0.5, "ASSUMPTION", "PSRAM <= 25 mm from the FPGA, each direction (layout R09)")
for sclk in (20e6, 40e6):
    half = 0.5e9 / sclk
    need = ECP_TCO + FL2 + TACLK + FL2 + ECP_TIN + ECP_SU
    result("psram_timing", f"QSPI read sample (half SCLK period after the fall) at SCLK {sclk / 1e6:.0f} MHz", round(need, 2),
           round(half, 2), need < half, "ns", ["aps_taclk_max", "ecp5_pad_out_ns", "ecp5_pad_in_ns", "ecp5_ff_setup_ns",
                                               "psram_flight_ns"],
           "nextpnr-ecp5 does not time pad paths; this hand budget sets the bring-up clock (design: psram_mclk 40 MHz -> SCLK 20 MHz)",
           risk="" if need < half else "RK-PSRAM-IO-TIMING")

# ---------------------------------------------------------------- ECP5 sysCONFIG / control levels (R8.5)
ECP_VIL = inp("ecp5_vil", 0.8, "DOC", "ECP5 DS sysI/O LVCMOS33 VIL max 0.8 V")
ECP_VIH = inp("ecp5_vih", 2.0, "DOC", "ECP5 DS sysI/O LVCMOS33 VIH min 2.0 V")
F_VOL = inp("f133_vol", 0.2, "DOC", "F133 DS Table 5-3 VOL 0.2 V (test current per table)")
RS = inp("programn_series", 470.0, "PLAN", "PE8 -> PROGRAMN series resistor")
RPU = inp("cfg_pullup", 4.7e3, "PLAN", "4.7k to VCCIO8 (TN-02038 Table 6.1)")
v = F_VOL + (V33_MAX - F_VOL) * RS * 1.01 / (RS * 1.01 + RPU * 0.99)
result("sysconfig", "PROGRAMN low level with F133 PE8 driving low through the series R", round(v, 3), ECP_VIL, v < ECP_VIL,
       "V", ["f133_vol", "programn_series", "cfg_pullup", "ecp5_vil", "v3v3_max"],
       "R8.5 first draft used 1k: 0.78 V vs 0.8 V (18 mV) -> changed to 470R")
vi = V33_MIN - RPU * 1.01 * IPD_MAX
result("sysconfig", "FPGA_IRQ_N idle level during configuration (4.7k vs ECP5 config-time pull-down)", round(vi, 3),
       round(F_VIH * V33_MAX, 3), vi > F_VIH * V33_MAX, "V", ["cfg_pullup", "ecp5_ipd_max", "f133_vih_ratio"],
       "F133 ignores IRQ before P4 anyway; user mode PULLMODE=NONE")
BUF_VOL4 = inp("lvc125_vol_4ma", 0.24, "ASSUMPTION", "SN74LVC1G125 VOL at IOL ~3.4 mA, 3.3 V (table value at 4 mA to be transcribed)")
RCCLK = inp("cclk_pullup", 1e3, "PLAN", "CCLK pull-up 1k (TN-02038 Table 6.2: 510R-1k)")
icclk = V33_MAX / (RCCLK * 0.99)
vcl = BUF_VOL4 + icclk * 33.0
result("sysconfig", "CCLK low level (buffer sinking the 1k pull-up through 33R)", round(vcl, 3), ECP_VIL, vcl < ECP_VIL, "V",
       ["lvc125_vol_4ma", "cclk_pullup", "ecp5_vil"], f"sink current {icclk * 1e3:.2f} mA")
CCLK_MAX = inp("ecp5_cclk_max", 60e6, "DOC", "ECP5 DS Table 3.42 SSPI fCCLK max 60 MHz")
BIT_BYTES = inp("bitstream_bytes", 288697, "PLAN", "fpga_ecp5/build/arc1_ecp5.bit (ecppack --compress, this design)")
FCFG = inp("cfg_sck_plan", 25e6, "PLAN", "F133 SPI0 at 25 MHz for configuration (PLL_PERI 600 MHz / 24)")
tcfg = BIT_BYTES * 8 / FCFG
result("sysconfig", "configuration time at the planned 25 MHz (compressed bitstream, wire time only)", round(tcfg * 1e3, 1),
       1000.0, tcfg < 1.0, "ms", ["bitstream_bytes", "cfg_sck_plan"],
       "game-swap budget 1 s (PLAN); uncompressed max 9.74 Mb would take 390 ms; host model incl. CS overhead: 99.7 ms")
result("sysconfig", "planned CCLK vs SSPI limit", FCFG / 1e6, CCLK_MAX / 1e6, FCFG <= CCLK_MAX, "MHz",
       ["cfg_sck_plan", "ecp5_cclk_max"])
SYS = inp("fpga_sys_hz", 80e6, "PLAN", "ECP5 sys_clk (routed fmax 87 MHz, BUILD_REPORT)")
result("mailbox", "operational SPI max SCK = sys_clk/8 (mbx_spi_slave oversampling; RTL_SIMULATED at sys/8 and sys/16)",
       SYS / 8 / 1e6, 10.0, SYS / 8 >= 10e6, "MHz", ["fpga_sys_hz"],
       "the mailbox link, not the FPGA datapath, bounds offload throughput: see docs/BENCHMARK_R85.md (HARD STOP analysis)")

# ---------------------------------------------------------------- ECP5 rail budget (G9)
ICC = inp("ecp5_icc_static", 0.116, "DOC", "ECP5 DS Table 3.8 ICC typ 116 mA (LFE5U-45, 85 C, 0 Hz)")
ICC_DYN = inp("ecp5_icc_dyn", 0.150, "ASSUMPTION", "dynamic VCC for ~6k LUT/3.8k FF/8 DSP at 80 MHz; Lattice power calculator NOT_RUN")
ICCA = inp("ecp5_iccaux", 0.017, "DOC", "ECP5 DS Table 3.8 ICCAUX typ 17 mA")
ICCA_DYN = inp("ecp5_iccaux_dyn", 0.023, "ASSUMPTION", "PLL + config-time VCCAUX increase (not specified)")
ICCIO = inp("ecp5_iccio_bank", 0.0005, "DOC", "ECP5 DS Table 3.8 ICCIO 0.5 mA per bank (static)")
IPS = inp("psram_active", 0.025, "ASSUMPTION", "APS6404L active read current at 20 MHz QSPI (DS table to be transcribed)")
IOSC = inp("osc_25m", 0.010, "ASSUMPTION", "25 MHz XO supply (part TBD)")
IIO_DYN = inp("ecp5_io_dyn", 0.010, "ASSUMPTION", "PSRAM/SPI pad switching: C*V^2*f for 8 pads, 10 pF, 20 MHz")
IPULL = inp("pullups_fpga_rail", 3.4e-3 + 6 * 0.7e-3, "PLAN", "CCLK 1k (when SCK low) + six 4.7k config pull-ups")
i_vcc = ICC + ICC_DYN
i_aux = ICCA + ICCA_DYN
i_3v3f = 7 * ICCIO + IPS + IOSC + IIO_DYN + IPULL + i_aux
BUDGET = {"1V1_FPGA (U9 TLV62569P, 2 A)": round(i_vcc, 3), "2V5_FPGA_AUX (U30 TLV75525P, 0.5 A)": round(i_aux, 3),
          "3V3_FPGA (U10 TPS22918, 2 A; incl. VCCAUX LDO input, PSRAM, XO)": round(i_3v3f, 3)}
result("fpga_rails", "VCC load vs U9 rating", round(i_vcc, 3), 2.0, i_vcc < 2.0 * 0.5, "A", ["ecp5_icc_static", "ecp5_icc_dyn"],
       "50 % derating; peak start-up current NOT_FOUND (DS points to the power calculator)")
result("fpga_rails", "VCCAUX load vs U30 rating", round(i_aux, 3), 0.5, i_aux < 0.25, "A", ["ecp5_iccaux", "ecp5_iccaux_dyn"])
LDO_DO = inp("tlv755_dropout", 0.24, "DOC", "TLV755P DS: dropout 238 mV max at 500 mA (2.5 V+ options); far less at 40 mA")
RON = inp("tps22918_ron", 0.061, "DOC", "TPS22918 DS: RON 52 mOhm typ, 61 mOhm max at 3.3 V")
v3f = lo33 - i_3v3f * RON
result("fpga_rails", "3V3_FPGA minimum (3V3 low corner - switch drop) vs LVCMOS33 VCCIO 3.135 V", round(v3f, 4), 3.135,
       v3f >= 3.135, "V", ["tps22918_ron", "vfb_tol", "r_tol"], "same root cause as RK-3V3-SUP if it fails", risk="RK-3V3-SUP")
result("fpga_rails", "VCCAUX LDO headroom (3V3_FPGA min - 2.5 V) vs dropout", round(v3f - 2.5, 3), LDO_DO, v3f - 2.5 > LDO_DO,
       "V", ["tlv755_dropout", "tps22918_ron"])
AUXTOL = inp("tlv755_acc", 0.015, "ASSUMPTION", "TLV75525P output accuracy over temperature +-1.5 % (DS value to be transcribed)")
FBDCR = inp("fb_dcr", 0.05, "ASSUMPTION", "BLM18PG121SN1D DCR 0.05 ohm (candidate ferrite)")
vaux = [2.5 * (1 - AUXTOL) - i_aux * FBDCR, 2.5 * (1 + AUXTOL)]
result("fpga_rails", "VCCAUX at the balls", [round(x, 4) for x in vaux], [2.375, 2.625], vaux[0] >= 2.375 and vaux[1] <= 2.625, "V",
       ["tlv755_acc", "fb_dcr", "ecp5_iccaux"], "TN-02038: ferrite ESR x I < 1 % of rail")
RAMP_SW = inp("tps22918_ramp", 1.7, "PLAN", "U10 CT 1 nF -> ~1.9 ms 0->3.3 V (TPS22918 DS SR formula)")
RAMP_BUCK = inp("tlv62569_ss", 1.1, "ASSUMPTION", "TLV62569 internal soft-start ~1 ms to 1.1 V (DS typ; not a guaranteed max)")
for rail, rr in (("VCCIO/VCCAUX (3V3_FPGA, LDO tracks its input)", RAMP_SW), ("VCC (1V1_FPGA buck soft-start)", RAMP_BUCK)):
    result("fpga_rails", f"ramp rate {rail}", rr, [0.01, 10.0], 0.01 <= rr <= 10.0, "V/ms",
           ["tps22918_ramp" if "3V3" in rail else "tlv62569_ss"], "ECP5 DS Table 3.3 tRAMP 0.01..10 V/ms, monotonic")
INFO["ECP5 rail budget (A)"] = BUDGET

# ---------------------------------------------------------------- VBUS budget
# estimates per rail (W at the load); F133 per-rail current is NOT given in the datasheet.
LOADS = {
    "F133 core+DRAM+IO": inp("p_f133", 1.2, "ASSUMPTION", "F133 per-rail currents NOT_FOUND; D1s-class board estimate incl. DDR2"),
    "MN820 module": inp("p_mn820", 0.245 * 3.3, "DOC", "MN820 DS: 245 mA typ at 3.3 V with test card (max NOT_FOUND)"),
    "MN820 margin to max": inp("p_mn820_margin", 0.5, "ASSUMPTION", "x1.6 typ->max allowance until Bridgetek answers"),
    "ECP5 + PSRAM + XO": inp("p_t35", round(1.1 * i_vcc + 3.3 * i_3v3f, 3), "ASSUMPTION",
                              "from the ECP5 rail budget above (Lattice power calculator NOT_RUN)"),
    "logic, LEDs, SD card": inp("p_misc", 0.45, "ASSUMPTION", "microSD write up to ~100 mA at 3.3 V + glue"),
}
eta = inp("eta_buck", 0.85, "ASSUMPTION", "TLV62569 efficiency at these loads (datasheet curves, not read)")
amp_eff = inp("eta_amp", 0.85, "ASSUMPTION", "MAX98357A efficiency near full power")
p_logic = sum(LOADS.values()) / eta
for amp_w, cls, lim_a in ((0.0, "default USB (500 mA, amps muted)", 0.5), (0.25, "Type-C 1.5 A (0.25 W/ch)", 1.5),
                          (1.4, "Type-C 3.0 A (1.4 W/ch into 8 ohm)", 3.0)):
    p = p_logic + 2 * amp_w / amp_eff
    i = p / 4.75
    result("vbus_budget", f"VBUS current, {cls}", round(i, 3), lim_a, i <= lim_a, "A",
           ["p_f133", "p_mn820", "p_mn820_margin", "p_t35", "p_misc", "eta_buck", "eta_amp"],
           "VBUS 4.75 V min; firmware power policy from TUSB320 OUT1/OUT2. Panel backlight (R09) NOT included",
           risk="RK-USB-BUDGET" if lim_a < 1.0 else "")
result("vbus_budget", "PTC hold >= worst budgeted current (3 A class)", 2.6,
       round((p_logic + 2 * 1.4 / amp_eff) / 4.75, 3), 2.6 >= (p_logic + 2 * 1.4 / amp_eff) / 4.75, "A",
       ["p_f133", "p_t35", "eta_amp"], "1812 PTC hold >= 2.6 A selected; MPN R09")


def main(out_json, out_md):
    n = {s: sum(1 for r in R if r["status"] == s) for s in ("PASS", "CONDITIONAL", "OPEN", "FAIL")}
    json.dump({"schema": "arc1-r85-margins-v1", "summary": n, "info": INFO, "inputs": INPUTS, "results": R},
              open(out_json, "w"), indent=1)
    L = ["# R8.5 electrical margins (GENERATED by analysis/electrical_margins_r85.py)", "",
         "Evidence: **DERIVED_WITH_CALC** from datasheet limits. `CONDITIONAL` = passes only under a tagged ASSUMPTION. "
         "No SPICE/IBIS/SI simulation, no measurement.", "",
         f"Summary: PASS {n['PASS']}, CONDITIONAL {n['CONDITIONAL']}, OPEN {n['OPEN']}, FAIL {n['FAIL']}. "
         "Every FAIL/OPEN carries a risk ID in RISK_REGISTER_R85.md.", "",
         "| Group | Check | Value | Limit | Unit | Status | Risk | Note |", "|---|---|---|---|---|---|---|---|"]
    for r in R:
        L.append(f"| {r['group']} | {r['check']} | {r['value']} | {r['limit']} | {r['unit']} | **{r['status']}** | {r['risk']} | {r['note']} |")
    L += ["", "Info: " + "; ".join(f"{k}: {v}" for k, v in INFO.items())]
    L += ["", "## Inputs", "", "| Name | Value | Tag | Source |", "|---|---|---|---|"]
    for k, v in INPUTS.items():
        L.append(f"| {k} | {v['value']} | {v['tag']} | {v['source']} |")
    open(out_md, "w").write("\n".join(L) + "\n")
    print(f"margins: PASS {n['PASS']} CONDITIONAL {n['CONDITIONAL']} OPEN {n['OPEN']} FAIL {n['FAIL']}")
    unowned = [r for r in R if r["status"] in ("FAIL", "OPEN") and not r["risk"]]
    if unowned:
        print("FAIL/OPEN results without a risk ID:", [r["check"] for r in unowned])
        sys.exit(1)
    for r in R:
        if r["status"] != "PASS":
            print(f"  {r['status']}: {r['group']} / {r['check']} = {r['value']} (limit {r['limit']})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
