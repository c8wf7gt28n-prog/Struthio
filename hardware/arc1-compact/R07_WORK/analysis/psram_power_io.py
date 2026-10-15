#!/usr/bin/env python3
"""ARC-1 Compact R07: worst-case DC analysis of the APS6404L power-up pull
network and T35<->PSRAM logic levels.  Label: PLANNING_CALCULATED (datasheet
limits, resistor tolerance, leakage). It is NOT an electrical simulation (no
transients, no ground bounce, no temperature model beyond datasheet ranges).

Usage: psram_power_io.py [--json OUT] ; exit 1 if any requirement fails.
"""
import argparse
import json
import sys

# ---- datasheet facts (see R06_WORK/docs/SOURCES_R06.json) ----
RAIL = (3.20, 3.40)            # R07 3V3 window (board plan)
T35_RPU = (27e3, 65e3)         # T35 DS Table 69, 3.3 V weak pull-up min/max
T35_LEAK = 10e-6               # T35 DS Table 67 input / tri-state leakage
PS_LEAK = 1e-6                 # APS6404L DS Table 9 ILI / ILO
PS_VIL = 0.4                   # APS6404L Table 9 VIL max
PS_VIH = lambda v: v - 0.4     # APS6404L Table 9
PS_VOH = lambda v: 0.8 * v     # @ IOH = -0.2 mA only
PS_VOL = lambda v: 0.2 * v     # @ IOL = +0.2 mA only
PS_IOH_SPEC = 0.2e-3
T35_VIH, T35_VIL = 2.0, 0.8    # T35 Table 66, 3.3 V LVCMOS
T35_VOH = lambda v: v - 0.2
T35_VOL = 0.2
T35_IOH_DS1 = 14.4e-3          # T35 Table 68, drive strength 1, 3.3 V (TJ 25 C, nominal supply)
CE_TRACK = 0.2                 # APS6404L sec. 8: CE# tracks VDD within 200 mV

R_PD, R_CE_PU = 2200.0, 10000.0
TOL = 0.05                     # assume 5 % resistors (1 % parts improve every result)

results = []


def req(name, value, limit, ok, unit="V", basis=""):
    results.append({"check": name, "value": round(value, 4), "limit": limit, "unit": unit,
                    "pass": bool(ok), "basis": basis})


vmax, vmin = RAIL[1], RAIL[0]
# 1. power-up LOW on SCLK/SIO while the T35 is unconfigured (weak pull-up active)
rpd = R_PD * (1 + TOL)
rpu = T35_RPU[0]
leak = T35_LEAK + PS_LEAK                       # both sourcing into the node (worst case)
v_low = (vmax / rpu + leak) / (1 / rpu + 1 / rpd)
req("powerup_sclk_sio_low", v_low, f"<= VIL {PS_VIL}", v_low <= PS_VIL,
    basis="Thevenin: T35 27k min pull-up to 3.40 V, 2.2k+5% pull-down, +11 uA leakage")
# 2. CE# HIGH tracking VDD within 200 mV (10k pull-up to the same rail)
drop = (T35_LEAK + PS_LEAK) * R_CE_PU * (1 + TOL)
req("powerup_ce_tracks_vdd", drop, f"<= {CE_TRACK}", drop <= CE_TRACK,
    basis="leakage x 10k+5%; T35 weak pull-up in parallel only helps")
# 3. static current the T35 sources into each pull-down when driving high
i_pd = vmax / (R_PD * (1 - TOL))
req("t35_drive_current_per_line", i_pd * 1e3, f"<< IOH {T35_IOH_DS1*1e3} mA (DS1)", i_pd < 0.25 * T35_IOH_DS1,
    unit="mA", basis="T35 Table 68 IOH is at TJ 25 C; 4x headroom required")
# 4. PSRAM VOH while sourcing the pull-down: datasheet only guarantees VOH at 0.2 mA
req("psram_voh_spec_condition", i_pd * 1e3, f"datasheet VOH only at {PS_IOH_SPEC*1e3} mA", False,
    unit="mA", basis="OPEN: the 2.2k load draws ~7x the VOH test current; vendor question Q6")
# estimate with a 50 ohm driver (APS6404L 'powers up in 50 ohm', sec. 9.3) -- ASSUMPTION
voh_est = PS_VOH(vmin) - i_pd * 50.0
req("psram_voh_estimate_vs_t35_vih", voh_est - T35_VIH, ">= 0 V margin", voh_est >= T35_VIH,
    basis="ASSUMPTION: 0.8*VDD at 3.20 V minus I*50 ohm")
# 5. logic margins over the rail window (same rail at both ends)
for v in RAIL:
    req(f"t35_to_psram_high@{v}", T35_VOH(v) - PS_VIH(v), ">= 0", T35_VOH(v) >= PS_VIH(v))
    req(f"t35_to_psram_low@{v}", PS_VIL - T35_VOL, ">= 0", PS_VIL >= T35_VOL)
    req(f"psram_to_t35_low@{v}", T35_VIL - PS_VOL(v), ">= 0", T35_VIL >= PS_VOL(v),
        basis="PSRAM VOL 0.2*VDD (at 0.2 mA; pull-down does not load a low output)")
    req(f"psram_to_t35_high@{v}", PS_VOH(v) - T35_VIH, ">= 0", PS_VOH(v) >= T35_VIH)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()
    hard = [r for r in results if not r["pass"] and not r["check"].startswith("psram_voh_spec_condition")]
    for r in results:
        print(f"{'PASS' if r['pass'] else ('OPEN' if r['check'].startswith('psram_voh_spec') else 'FAIL'):4s} "
              f"{r['check']:34s} {r['value']:>9} {r['unit']:2s} limit {r['limit']}  {r['basis']}")
    if a.json:
        json.dump({"label": "PLANNING_CALCULATED", "rail": RAIL, "results": results}, open(a.json, "w"), indent=1)
    print(("PASS" if not hard else "FAIL") + f" psram power/IO DC analysis: {len(results)} checks, "
          f"{len(hard)} failing, 1 OPEN vendor question (PLANNING_CALCULATED)")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
