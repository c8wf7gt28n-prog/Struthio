#!/usr/bin/env python3
"""ARC-1 Compact R08 -- worst-case DC levels, timing budgets, regulator/supervisor
windows and the VBUS power budget for the R08 schematic.

Every input is tagged: DOC (manufacturer document in R08_WORK/sources, quoted
section), PLAN (a value chosen in design.py), or ASSUMPTION (no source; must be
closed by vendor data, IBIS/SPICE or bench). Results are DERIVED_WITH_CALC.
A result built on an ASSUMPTION is reported as CONDITIONAL, never as PASS.
Usage: electrical_margins_r08.py <out.json> <out.md>
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
        ("3V3 (U3)", 453e3, 100e3, 3.14, 3.47, "T35 VCCIO 3.14-3.47 (tightest consumer; F133 VCC-IO 2.97-3.63, MN820 3.0-3.6)"),
        ("VDD_CORE (U5)", 57.6e3, 100e3, 0.85, 0.99, "F133 DS rev 2.3 Table 5-2 VDD-CORE/SYS"),
        ("1V8_DRAM (U6)", 200e3, 100e3, 1.7, 1.9, "F133 VCC-DRAM"),
        ("1V2_T35 (U9)", 100e3, 100e3, 1.15, 1.25, "T35 DS VCC 1.15/1.2/1.25")):
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
        ("U4 TPS3808G33 on 3V3", 3.07, lo33, None, "trips below the regulated window, above F133/T35 minimum 2.97/3.14?"),
        ("U8 TPS3808G09 on VDD_CORE", 0.84, buck(57.6e3, 100e3)[1], None, "F133 core min 0.85"),
        ("U14 TPS3808G30 on PSRAM_VDD", 2.79, lo33 - 2 * 0.08, 2.7, "APS6404L VDD min 2.7 V")):
    hi = vit * (1 + TOL)
    lo = vit * (1 - TOL)
    result("supervisor", f"{name}: max threshold below rail minimum", round(hi, 4), round(rail_lo, 4), hi < rail_lo, "V",
           ["tps3808_tol"], "else the supervisor could hold reset with a healthy rail")
    if must_below:
        result("supervisor", f"{name}: min threshold above device minimum", round(lo, 4), must_below, lo > must_below, "V",
               ["tps3808_tol"], "power loss is flagged before the PSRAM leaves its operating range")
result("supervisor", "U4 TPS3808G33 min threshold vs T35 VCCIO min 3.14 V", round(3.07 * (1 - TOL), 4), 3.14,
       3.07 * (1 - TOL) >= 3.14, "V", ["tps3808_tol"],
       "3V3 can sag to 3.02-3.14 V without reset -> below T35 VCCIO spec. A threshold window [3.14, 3.199] is not "
       "achievable with +-1.5 % parts and a +-2 % regulator: R09 needs a 1 % regulator or accepts it (T35 optional; "
       "PSRAM data guarded by its own supervisor)", risk="RK-3V3-SUP")
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

# ---------------------------------------------------------------- PSRAM pull-downs (switched) and loads
T35_PU = inp("t35_weak_pu_min", 27e3, "DOC", "T35 DS v3.2 Table 69 weak pull-up 27/40/65 kOhm at 3.3 V")
RPDS = inp("psram_pd_switched", 1.5e3, "PLAN", "1.5 kOhm to an SN74LVC07A output")
LVC07_VOL = inp("lvc07_vol", 0.2, "DOC", "SN74LVC07A VOL 0.2 V at IOL 100 uA (s.6.5); actual sink ~0.12 mA here")
STATIC = inp("psram_pd_static", 100e3, "PLAN", "static pull-down")
r = RPDS * (1 + RTOL)
par = 1 / (1 / r + 1 / STATIC)
v = LVC07_VOL + (V33_MAX - LVC07_VOL) * par / (par + T35_PU)
result("psram", "SCLK/SIO level while T35 unconfigured (PSRAM unpowered by design)", round(v, 4), 0.4, v <= 0.4, "V",
       ["t35_weak_pu_min", "psram_pd_switched", "lvc07_vol", "v3v3_max"],
       "limit 0.4 V = APS6404L VIN max VDD+0.4 at VDD = 0 (no back-power); also <= VIL 0.4")
iuser = V33_MAX / STATIC
inp("aps_voh_test", 0.2e-3, "DOC", "APS6404L DS Rev 2.7 Table 9: VOH 0.8*VDD at IOH = -0.2 mA")
result("psram", "PSRAM output load in user mode (switched pull-downs released)", round(iuser * 1e3, 4), 0.2,
       iuser <= 0.2e-3, "mA", ["psram_pd_static", "aps_voh_test"],
       "R07 needed 1.63 mA through 2.2 kOhm (outside the 0.2 mA VOH test condition); R08 load is inside it -> RK-PSRAM-VOH closed by design")
result("psram", "CE# vs VDD during ramp", 0.0, 0.2, True, "V", ["psram_pd_static"],
       "CE# pull-up goes to PSRAM_VDD itself and the T35 CE# pad is released (guard OFF): tracks exactly (RTL_SIMULATED P1)")
TUSER = inp("t35_tuser", 25e-6, "DOC", "Efinix: tUSER >= 25 us after CDONE high (AN006 / Software UG)")
VT = inp("lvc1g17_vtplus_min", 1.3, "ASSUMPTION", "SN74LVC1G17 VT+ min at 3.3 V not yet transcribed (R09)")
tau = (10e3 + 10e3) * 100e-9
tdel = tau * math.log(V33_MAX / (V33_MAX - VT))
result("psram", "CDONE -> CDONE_DLY delay vs tUSER", round(tdel * 1e6, 1), TUSER * 1e6, tdel >= 4 * TUSER, "us",
       ["t35_tuser", "lvc1g17_vtplus_min"], "requires >= 4x tUSER; RC = (10k pull-up + 10k) x 100 nF")

# ---------------------------------------------------------------- VBUS budget
# estimates per rail (W at the load); F133 per-rail current is NOT given in the datasheet.
LOADS = {
    "F133 core+DRAM+IO": inp("p_f133", 1.2, "ASSUMPTION", "F133 per-rail currents NOT_FOUND; D1s-class board estimate incl. DDR2"),
    "MN820 module": inp("p_mn820", 0.245 * 3.3, "DOC", "MN820 DS: 245 mA typ at 3.3 V with test card (max NOT_FOUND)"),
    "MN820 margin to max": inp("p_mn820_margin", 0.5, "ASSUMPTION", "x1.6 typ->max allowance until Bridgetek answers"),
    "T35 + PSRAM + flash": inp("p_t35", 0.6, "ASSUMPTION", "Efinity power estimator NOT_RUN"),
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
    json.dump({"schema": "arc1-r08-margins-v1", "summary": n, "info": INFO, "inputs": INPUTS, "results": R},
              open(out_json, "w"), indent=1)
    L = ["# R08 electrical margins (GENERATED by analysis/electrical_margins_r08.py)", "",
         "Evidence: **DERIVED_WITH_CALC** from datasheet limits. `CONDITIONAL` = passes only under a tagged ASSUMPTION. "
         "No SPICE/IBIS/SI simulation, no measurement.", "",
         f"Summary: PASS {n['PASS']}, CONDITIONAL {n['CONDITIONAL']}, OPEN {n['OPEN']}, FAIL {n['FAIL']}. "
         "Every FAIL/OPEN carries a risk ID in RISK_REGISTER_R08.md.", "",
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
