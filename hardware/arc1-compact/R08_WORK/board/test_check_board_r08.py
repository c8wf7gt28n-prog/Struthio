#!/usr/bin/env python3
"""Negative tests: each mutation reintroduces a real R07/R08 hazard; the named rule must FAIL."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_board_r08 as cb  # noqa: E402

BASE = cb.load()


def results(plan):
    return {name: errs for name, doc, errs in cb.run(plan)}


def comp(plan, ref):
    return [c for c in plan["components"] if c["ref"] == ref][0]


def rewire(plan, ref, pin, new_net):
    c = comp(plan, ref)
    old = c["pins"][pin]["net"]
    node = f"{ref}.{pin}"
    if old:
        plan["nets"][old] = [x for x in plan["nets"][old] if x != node]
    c["pins"][pin]["net"] = new_net
    plan["nets"].setdefault(new_net, []).append(node)


def find_r(plan, a, b):
    for c in plan["components"]:
        if c["part"].startswith("R0") and {c["pins"]["1"]["net"], c["pins"]["2"]["net"]} == {a, b}:
            return c
    raise KeyError((a, b))


class Base(unittest.TestCase):
    def test_baseline_passes(self):
        r = results(copy.deepcopy(BASE))
        self.assertEqual({k: v for k, v in r.items() if v}, {})


class Mutations(unittest.TestCase):
    def fails(self, plan, rule):
        r = results(plan)
        self.assertTrue(r[rule], f"rule {rule} did not catch the mutation")

    def test_r07_strap_11_is_rejected(self):          # R07 straps (pull-ups) would boot SD first
        p = copy.deepcopy(BASE)
        r = find_r(p, "SPI0_MISO", "GND")
        rewire(p, r["ref"], "2" if r["pins"]["2"]["net"] == "GND" else "1", "3V3")
        self.fails(p, "boot_straps_00")

    def test_weak_strap_pulldown(self):
        p = copy.deepcopy(BASE)
        find_r(p, "SPI0_MOSI", "GND")["value"] = "10k"
        self.fails(p, "boot_straps_00")

    def test_t35_directly_on_spi0(self):              # R07 topology: T35 MISO straight onto PC5
        p = copy.deepcopy(BASE)
        rewire(p, "U18", "H14", "SPI0_MISO")
        self.fails(p, "spi0_t35_isolated")

    def test_isolation_buffer_enabled_at_reset(self):
        p = copy.deepcopy(BASE)
        r = find_r(p, "T35_SS_N_F", "3V3")
        r["dnp"] = True
        self.fails(p, "spi0_t35_isolated")

    def test_mn820_miso_direct(self):                 # R07: module VOH 2.4 V straight into F133 (+0.02 V)
        p = copy.deepcopy(BASE)
        rewire(p, "J3", "84", "BT_MISO")
        self.fails(p, "mn820_miso_buffered")

    def test_nor_reset_without_fel_button(self):
        p = copy.deepcopy(BASE)
        sw = [c for c in p["components"] if c["part"] == "SW_B3U" and c["pins"]["1"]["net"] == "NOR_RESET_N"][0]
        rewire(p, sw["ref"], "1", "UNUSED_X")
        self.fails(p, "nor_boot_device")

    def test_psram_r07_static_2k2_pulldown(self):     # R07: 2.2k permanent pull-downs (VOH outside spec)
        p = copy.deepcopy(BASE)
        find_r(p, "PSRAM_SIO1", "GND")["value"] = "2.2k"
        self.fails(p, "psram_power_architecture")

    def test_psram_always_powered(self):
        p = copy.deepcopy(BASE)
        rewire(p, "U25", "8", "3V3_T35")
        self.fails(p, "psram_power_architecture")

    def test_psram_power_not_gated_by_cdone(self):
        p = copy.deepcopy(BASE)
        rewire(p, "U13", "2", "3V3")
        self.fails(p, "psram_power_architecture")

    def test_ce_pullup_to_unswitched_rail(self):
        p = copy.deepcopy(BASE)
        r = find_r(p, "PSRAM_CE_N", "PSRAM_VDD")
        rewire(p, r["ref"], "2" if r["pins"]["2"]["net"] == "PSRAM_VDD" else "1", "3V3_T35")
        self.fails(p, "psram_power_architecture")

    def test_back_power_pullup(self):
        p = copy.deepcopy(BASE)
        r = find_r(p, "T35_CDONE", "3V3_T35")
        rewire(p, r["ref"], "2" if r["pins"]["2"]["net"] == "3V3_T35" else "1", "3V3")
        self.fails(p, "switched_domain_pullups")

    def test_core_buck_not_sequenced(self):
        p = copy.deepcopy(BASE)
        rewire(p, "U5", "1", "VBUS_5V")
        self.fails(p, "power_sequencing")

    def test_t35_vccio_before_core(self):
        p = copy.deepcopy(BASE)
        rewire(p, "U10", "3", "3V3")
        self.fails(p, "power_sequencing")

    def test_usb_host_reintroduced(self):
        p = copy.deepcopy(BASE)
        u = comp(p, "U15")
        num = [n for n, x in u["pins"].items() if x["name"] == "USB1-DP"][0]
        rewire(p, "U15", num, "USB1_DP")
        self.fails(p, "usb_device_only")

    def test_missing_decoupling(self):
        p = copy.deepcopy(BASE)
        for c in p["components"]:
            if c["part"] == "C0402" and c["value"] == "100nF" and c["pins"]["1"]["net"] == "PSRAM_VDD":
                c["dnp"] = True
        self.fails(p, "every_ic_decoupled")


if __name__ == "__main__":
    unittest.main(verbosity=2)
