#!/usr/bin/env python3
"""ARC-1 Compact R06 board-plan checker.

Checks r06_board_plan.json against independently extracted source tables:
  * T35F400 ball/bank/configuration facts (R05 system/T35F400_package_source_facts.csv,
    from the official Efinix T35 pinout workbook)
  * F133 eLQFP128 bonded GPIO + power domain (extracted from F133 DS Table 4-2)
  * F133 Table 4-3 multiplex rows (transcribed) cross-checked with the Linux
    sun20i-d1 pinctrl function table (machine-extracted, independent source)
  * device_facts.json (I/O levels, rail ranges, connector pins)

It is a PLANNING check (label PLANNING_CALCULATED). Passing it does not prove
electrical operation, signal integrity, layout feasibility or that any
board works.

Usage: check_board_plan.py [--plan PATH] [--report OUT.json] [--pinmap OUT.md]
Exit status 0 only if every rule passes.
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
T35_CSV = os.path.join(ROOT, "R05_BASELINE", "system", "T35F400_package_source_facts.csv")
F133_PINS = os.path.join(HERE, "sources", "f133_eLQFP128_gpio_pins.csv")
F133_MUX = os.path.join(HERE, "sources", "f133_mux_table43_transcribed.csv")
LINUX_MUX = os.path.join(HERE, "sources", "linux_sun20i_d1_pinmux.csv")
FACTS = os.path.join(HERE, "sources", "device_facts.json")

T35_WEAK_PULLUP_MIN_OHMS = 27000.0   # T35 DS Table 69, 3.3 V LVCMOS, min


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def level(expr, v):
    """Evaluate a datasheet level expression ('V-0.3', '0.7*V', 2.0) at rail voltage v."""
    if isinstance(expr, (int, float)):
        return float(expr)
    e = expr.replace(" ", "")
    if e.startswith("V-"):
        return v - float(e[2:])
    if e.endswith("*V"):
        return float(e[:-2]) * v
    raise ValueError(f"unsupported level expression {expr!r}")


class Checker:
    def __init__(self, plan, facts, t35_rows, f133_pins, f133_mux, linux_mux):
        self.plan, self.facts = plan, facts
        self.t35 = {r["ball"]: r for r in t35_rows}
        self.f133_pins = {r["pin"]: r for r in f133_pins}
        self.f133_mux = defaultdict(dict)
        for r in f133_mux:
            self.f133_mux[r["pin"]][int(r["function_index"])] = r
        self.linux = defaultdict(list)
        for r in linux_mux:
            self.linux[r["pin"]].append(r)
        self.results = []
        self.nets = defaultdict(list)   # net -> [(device, pin, dir, iolevel, rail)]

    # ------------------------------------------------------------------
    def rule(self, name, ok, detail=""):
        self.results.append({"rule": name, "pass": bool(ok), "detail": detail})
        return ok

    def rail(self, rid):
        r = self.plan["rails"].get(rid)
        if not r or r.get("nominal") is None:
            return None
        return r

    # ------------------------------------------------------------------
    def check_t35(self):
        t = self.plan["t35"]
        bank_rails = t["bank_rails"]
        expected_banks = set(self.facts["t35_bga400"]["banks"])
        self.rule("t35.all_banks_powered", expected_banks <= set(bank_rails),
                  f"missing VCCIO assignment: {sorted(expected_banks - set(bank_rails))}")
        for b, rid in bank_rails.items():
            r = self.rail(rid)
            ok = r is not None and any(abs(r["nominal"] - v) < 1e-6 for v in self.facts["t35_bga400"]["bank_voltages"])
            self.rule(f"t35.bank_voltage_legal[{b}]", ok, f"{b} on {rid}")
        for grp in self.facts["t35_bga400"]["merged"]:
            rails = {bank_rails.get(b) for b in grp}
            self.rule(f"t35.merged_banks_same_rail[{'_'.join(grp)}]", len(rails) == 1, str(rails))
        used = set()
        for ball, p in t["pins"].items():
            src = self.t35.get(ball)
            if not self.rule(f"t35.ball_exists[{ball}]", src is not None, ball):
                continue
            self.rule(f"t35.name_matches[{ball}]", src["manufacturer_pin_name"] == p["name"],
                      f"plan {p['name']} vs source {src['manufacturer_pin_name']}")
            self.rule(f"t35.bank_matches[{ball}]", src["bank"] == p["bank"], f"plan {p['bank']} vs source {src['bank']}")
            is_cfg = bool(src["configuration_functions"]) or p["name"] in ("CDONE", "CRESET_N")
            self.rule(f"t35.config_pin_policy[{ball}]", (not is_cfg) or p.get("config_pin", False),
                      f"{p['name']} has configuration function '{src['configuration_functions']}'")
            self.rule(f"t35.no_duplicate_ball[{ball}]", ball not in used, ball)
            used.add(ball)
            rid = bank_rails.get(p["bank"])
            self.nets[p["net"]].append(("T35", f"{ball}/{p['name']}", p["dir"], "T35_LVCMOS33", rid))

    # ------------------------------------------------------------------
    def check_f133(self):
        f = self.plan["f133"]
        drails = f["domain_rails"]
        for dom, rid in drails.items():
            r = self.rail(rid)
            allowed = self.facts["rails"].get(f"F133_{dom}", {}).get("allowed", [])
            ok = r is not None and any(lo <= r["min"] and r["max"] <= hi for lo, hi in allowed)
            # F133 ranges are 2.97-3.63 V: the plan rail window must sit inside one allowed window
            self.rule(f"f133.domain_voltage_legal[{dom}]", ok, f"{dom} on {rid} allowed {allowed}")
        used = set()
        for pin, p in list(f["pins"].items()) + [(k, dict(v, net=None, dir=None)) for k, v in f.get("reserved", {}).items()]:
            src = self.f133_pins.get(pin)
            if not self.rule(f"f133.pin_bonded_on_eLQFP128[{pin}]", src is not None, pin):
                continue
            self.rule(f"f133.no_duplicate_pin[{pin}]", pin not in used, pin)
            used.add(pin)
            fn = int(p["func"])
            if fn in (0, 1):
                self.rule(f"f133.mux_gpio[{pin}]", True, "plain GPIO")
            elif fn == 14:
                self.rule(f"f133.mux_eint[{pin}]", True, "EINT (Function14 for every GPIO, Table 4-3 header)")
            else:
                ds = self.f133_mux.get(pin, {}).get(fn)
                if self.rule(f"f133.mux_in_table43[{pin}]", ds is not None, f"Function{fn}"):
                    lin = [r for r in self.linux.get(pin, []) if int(r["mux"]) == fn]
                    ok = bool(lin) and lin[0]["function"] == ds["linux_function"]
                    self.rule(f"f133.mux_cross_checked_with_linux[{pin}]", ok,
                              f"datasheet {ds['datasheet_signal']} / linux {lin[0]['function'] if lin else None}")
            if p.get("net"):
                rid = drails[src["power_domain"]]
                self.nets[p["net"]].append(("F133", pin, p["dir"], "F133_GPIO", rid))
        # storage / boot constraints
        spi0_used = any(pin in f["pins"] for pin in ("PC2", "PC3", "PC4", "PC5"))
        self.rule("f133.boot_medium_not_emmc_when_spi0_used",
                  not (spi0_used and f["boot_medium"] == "EMMC_SMHC2"), f["boot_medium"])
        acks = {a["id"] for a in self.plan.get("acknowledged_risks", [])}
        straps_used = [pin for pin, p in f["pins"].items() if p.get("strap")]
        self.rule("f133.boot_strap_sharing_acknowledged", (not straps_used) or "BOOTSEL_SHARED_WITH_SPI0" in acks,
                  f"strap pins used as SPI: {straps_used}")
        quad = all(n in {p["net"] for p in f["pins"].values()} for n in ("BT_IO2", "BT_IO3"))
        self.rule("f133.quad_io_risk_acknowledged", (not quad) or "F133_QUAD_IO_UNCONFIRMED" in acks)

    # ------------------------------------------------------------------
    def check_external(self):
        ps = self.plan["psram"]
        sop8 = self.facts["aps6404l_sop8"]["pins"]
        for pin, net in ps["pins"].items():
            self.rule(f"psram.pin_exists[{pin}]", pin in sop8 and sop8[pin] not in ("VDD", "VSS"), f"{pin}={sop8.get(pin)}")
            d = "in" if net in ("PSRAM_CE_N", "PSRAM_SCLK") else "bidir"
            self.nets[net].append(("PSRAM", f"{pin}/{sop8.get(pin)}", d, "APS6404L", ps["vdd_rail"]))
        r = self.rail(ps["vdd_rail"])
        lo, hi = self.facts["rails"]["APS6404L_VDD"]["allowed"][0]
        self.rule("psram.vdd_in_range", r is not None and lo <= r["min"] and r["max"] <= hi, ps["vdd_rail"])
        mn = self.plan["mn820"]
        cn1 = self.facts["mn820_cn1"]["pins"]
        for pin, net in mn["pins"].items():
            self.rule(f"mn820.cn1_pin_matches[{pin}]", pin in cn1, f"CN1.{pin}={cn1.get(pin)}")
            role = cn1.get(pin, "")
            d = {"SPIS_SCLK": "in", "SPIS_SS_N": "in", "RESET_N": "in", "INT_N": "od"}.get(role, "bidir")
            self.nets[net].append(("MN820", f"CN1.{pin}/{role}", d, "BT820_VCCIO33", mn["io_rail"]))
        r = self.rail(mn["vin_rail"])
        self.rule("mn820.vin_in_range", r is not None and 3.0 <= r["min"] and r["max"] <= 3.6, mn["vin_rail"])

    # ------------------------------------------------------------------
    def check_nets(self):
        io = self.facts["io_levels"]
        passives = defaultdict(list)
        for p in self.plan.get("passives", []):
            passives[p["net"]].append(p)
        for net, ends in sorted(self.nets.items()):
            self.rule(f"net.has_two_ends[{net}]", len(ends) >= 2 or net.startswith("T35_DBG") or net.startswith("T35_LED")
                      or net.startswith("CFG_") or net.startswith("DBG_") or net.startswith("SD_") or net in
                      ("T35_OSC_25M", "AMP_SD_N"), f"{ends}")
            push = [e for e in ends if e[2] == "out"]
            self.rule(f"net.single_push_pull_driver[{net}]", len(push) <= 1, f"{push}")
            drivers = [e for e in ends if e[2] in ("out", "bidir", "tristate_out", "od")]
            receivers = [e for e in ends if e[2] in ("in", "bidir", "tristate_out")]
            for d in drivers:
                for r in receivers:
                    if d is r or d[0] == r[0]:
                        continue
                    self._check_levels(net, d, r, io)
        # pull-resistor rules
        for net in ("PSRAM_SCLK", "PSRAM_SIO0", "PSRAM_SIO1", "PSRAM_SIO2", "PSRAM_SIO3"):
            pd = [p for p in passives.get(net, []) if p["type"] == "pulldown"]
            vmax = self.rail(self.plan["psram"]["vdd_rail"])["max"]
            vil = level(io["APS6404L"]["vil_max"], vmax)
            ok = bool(pd)
            detail = "no pull-down"
            if pd:
                r = float(pd[0]["ohms"])
                v = vmax * r / (r + T35_WEAK_PULLUP_MIN_OHMS)
                ok = v <= vil
                detail = f"{r:.0f} ohm vs T35 weak pull-up {T35_WEAK_PULLUP_MIN_OHMS:.0f}: {v:.3f} V <= VIL {vil:.2f} V"
            self.rule(f"psram.powerup_low_during_t35_config[{net}]", ok, detail)
        self.rule("psram.ce_pullup", any(p["type"] == "pullup" for p in passives.get("PSRAM_CE_N", [])))
        for net in ("BT_IO0", "BT_IO1", "BT_IO2", "BT_IO3"):
            if net in self.nets:
                self.rule(f"bt820.data_pulldown[{net}]", any(p["type"] == "pulldown" for p in passives.get(net, [])))
        for net, ends in self.nets.items():
            if any(e[2] == "od" for e in ends):
                self.rule(f"net.open_drain_pullup[{net}]", any(p["type"] == "pullup" for p in passives.get(net, [])))

    def _check_levels(self, net, d, r, io):
        dl, rl = io[d[3]], io[r[3]]
        drail, rrail = self.rail(d[4]), self.rail(r[4])
        if drail is None or rrail is None:
            self.rule(f"level.rails_known[{net}]", False, f"{d[4]} / {rrail}")
            return
        corners = ([(v, v) for v in (drail["min"], drail["max"])] if d[4] == r[4] else
                   [(a, b) for a in (drail["min"], drail["max"]) for b in (rrail["min"], rrail["max"])])
        worst_hi, worst_lo = 1e9, 1e9
        for vd, vr in corners:
            if d[2] != "od":
                worst_hi = min(worst_hi, level(dl["voh_min"], vd) - level(rl["vih_min"], vr))
            worst_lo = min(worst_lo, level(rl["vil_max"], vr) - level(dl["vol_max"], vd))
        ok = (d[2] == "od" or worst_hi >= 0) and worst_lo >= 0
        hi_txt = "n/a (open drain)" if d[2] == "od" else f"{worst_hi:+.3f} V"
        self.rule(f"level.compatible[{net}:{d[0]}->{r[0]}]", ok, f"VOH-VIH margin {hi_txt}, VIL-VOL margin {worst_lo:+.3f} V")

    # ------------------------------------------------------------------
    def check_topology(self):
        bt_nets = set(self.plan["mn820"]["pins"].values())
        for net in sorted(bt_nets):
            devs = {e[0] for e in self.nets.get(net, [])}
            self.rule(f"topology.bt820_independent_of_t35[{net}]", "T35" not in devs and devs <= {"F133", "MN820"},
                      f"{sorted(devs)}")
        masters = {e[0] for n in bt_nets for e in self.nets.get(n, []) if e[2] == "out"}
        self.rule("topology.bt820_single_command_master", masters == {"F133"}, f"{sorted(masters)}")
        ps_nets = set(self.plan["psram"]["pins"].values())
        for net in sorted(ps_nets):
            devs = {e[0] for e in self.nets.get(net, [])}
            self.rule(f"topology.psram_private_to_t35[{net}]", devs == {"T35", "PSRAM"}, f"{sorted(devs)}")

    def run(self):
        self.check_t35()
        self.check_f133()
        self.check_external()
        self.check_nets()
        self.check_topology()
        return all(r["pass"] for r in self.results)

    # ------------------------------------------------------------------
    def pinmap_markdown(self):
        out = ["# ARC-1 Compact R06 draft pin / voltage map", "",
               "Generated by `check_board_plan.py` from `r06_board_plan.json`. Status: **SELECTED_UNVERIFIED** "
               "(planning only: no schematic, no layout, no electrical test).", "",
               "| Net | Endpoints (device pin / direction / I/O level / rail) | Pull |", "|---|---|---|"]
        pulls = defaultdict(list)
        for p in self.plan.get("passives", []):
            pulls[p["net"]].append(f"{p['type']} {p['ohms'] / 1000:g}k")
        for net, ends in sorted(self.nets.items()):
            e = "<br>".join(f"{d} {pin} ({di}, {lv}, {ra})" for d, pin, di, lv, ra in ends)
            out.append(f"| `{net}` | {e} | {', '.join(pulls.get(net, [])) or '-'} |")
        out += ["", "## Acknowledged risks", ""]
        for a in self.plan.get("acknowledged_risks", []):
            out.append(f"* **{a['id']}** ({', '.join(a['pins'])}): {a['mitigation']}")
        return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=os.path.join(HERE, "r06_board_plan.json"))
    ap.add_argument("--report")
    ap.add_argument("--pinmap")
    a = ap.parse_args(argv)
    with open(a.plan, encoding="utf-8") as f:
        plan = json.load(f)
    with open(FACTS, encoding="utf-8") as f:
        facts = json.load(f)
    c = Checker(plan, facts, load_csv(T35_CSV), load_csv(F133_PINS), load_csv(F133_MUX), load_csv(LINUX_MUX))
    ok = c.run()
    fails = [r for r in c.results if not r["pass"]]
    for r in fails:
        print(f"FAIL {r['rule']}: {r['detail']}")
    print(f"{'PASS' if ok else 'FAIL'} board plan: {len(c.results)} rules, {len(fails)} failures "
          f"(PLANNING_CALCULATED; not an electrical verification)")
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump({"schema_id": "arc1-r06-board-check-v1", "pass": ok, "rules": c.results,
                       "label": "PLANNING_CALCULATED"}, f, indent=1)
    if a.pinmap:
        with open(a.pinmap, "w", encoding="utf-8") as f:
            f.write(c.pinmap_markdown())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
