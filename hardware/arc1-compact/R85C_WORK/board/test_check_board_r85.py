#!/usr/bin/env python3
"""Negative tests: each mutation reintroduces a real R07/R08/R8.5 hazard; the named rule must FAIL."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_board_r85 as cb  # noqa: E402

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

    def test_fpga_directly_on_spi0(self):             # R07 topology: FPGA MISO straight onto PC5
        p = copy.deepcopy(BASE)
        rewire(p, "U18", "V2", "SPI0_MISO")
        self.fails(p, "spi0_fpga_isolated")

    def test_isolation_buffer_enabled_at_reset(self):
        p = copy.deepcopy(BASE)
        r = find_r(p, "FPGA_SS_N_F", "3V3")
        r["dnp"] = True
        self.fails(p, "spi0_fpga_isolated")

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
        rewire(p, "U25", "8", "3V3_FPGA")
        self.fails(p, "psram_power_architecture")

    def test_psram_power_not_gated_by_done(self):
        p = copy.deepcopy(BASE)
        rewire(p, "U13", "2", "3V3")
        self.fails(p, "psram_power_architecture")

    def test_ce_pullup_to_unswitched_rail(self):
        p = copy.deepcopy(BASE)
        r = find_r(p, "PSRAM_CE_N", "PSRAM_VDD")
        rewire(p, r["ref"], "2" if r["pins"]["2"]["net"] == "PSRAM_VDD" else "1", "3V3_FPGA")
        self.fails(p, "psram_power_architecture")

    def test_back_power_pullup(self):
        p = copy.deepcopy(BASE)
        r = find_r(p, "FPGA_DONE", "3V3_FPGA")
        rewire(p, r["ref"], "2" if r["pins"]["2"]["net"] == "3V3_FPGA" else "1", "3V3")
        self.fails(p, "switched_domain_pullups")

    def test_core_buck_not_sequenced(self):
        p = copy.deepcopy(BASE)
        rewire(p, "U5", "1", "VBUS_5V")
        self.fails(p, "power_sequencing")

    def test_fpga_vccio_always_on(self):              # VCCIO on while VCC is off: bank 2/3/6/7 hot-socket hazard
        p = copy.deepcopy(BASE)
        rewire(p, "U10", "3", "3V3")
        self.fails(p, "fpga_power_sequencing")

    def test_vccaux_from_unswitched_rail(self):
        p = copy.deepcopy(BASE)
        rewire(p, "U30", "1", "3V3")
        rewire(p, "U30", "3", "3V3")
        self.fails(p, "fpga_power_sequencing")

    def test_fpga_enable_without_pulldown(self):
        p = copy.deepcopy(BASE)
        find_r(p, "FPGA_PWR_EN", "GND")["dnp"] = True
        self.fails(p, "fpga_power_sequencing")

    def test_no_jtag_power_override(self):
        p = copy.deepcopy(BASE)
        rewire(p, "J11", "2", "UNUSED_X")
        self.fails(p, "fpga_power_sequencing")

    def test_t35_core_divider_kept(self):             # R08 1.20 V divider (100k/100k) is outside ECP5 VCC
        p = copy.deepcopy(BASE)
        find_r(p, "1V1_FPGA_REG", "FB_1V1")["value"] = "100k"
        self.fails(p, "fpga_vcc_voltage")

    def test_reserved_ball_connected(self):
        p = copy.deepcopy(BASE)
        rewire(p, "U18", "W4", "GND")
        self.fails(p, "ecp5_ball_map")

    def test_vccaux_on_core_rail(self):
        p = copy.deepcopy(BASE)
        rewire(p, "U18", "F6", "1V1_FPGA")
        self.fails(p, "ecp5_ball_map")

    def test_master_spi_mode_straps(self):            # CFG = 010 (master SPI) would need a config flash
        p = copy.deepcopy(BASE)
        rewire(p, "U18", "T4", "FPGA_CFG0")
        rewire(p, "U18", "U4", "GND")
        self.fails(p, "ecp5_sysconfig")

    def test_programn_without_pullup(self):
        p = copy.deepcopy(BASE)
        find_r(p, "FPGA_PROGRAMN", "3V3_FPGA")["dnp"] = True
        self.fails(p, "ecp5_sysconfig")

    def test_initn_not_readable(self):
        p = copy.deepcopy(BASE)
        u = comp(p, "U15")
        num = [n for n, x in u["pins"].items() if x["name"] == "PD0"][0]
        rewire(p, "U15", num, "UNUSED_Y")
        self.fails(p, "ecp5_sysconfig")

    def test_cclk_pullup_too_weak(self):
        p = copy.deepcopy(BASE)
        find_r(p, "FPGA_SCK", "3V3_FPGA")["value"] = "10k"
        self.fails(p, "ecp5_sysconfig")

    def test_config_flash_reintroduced(self):         # R08 U19 W25Q32 on the FPGA config pins
        p = copy.deepcopy(BASE)
        p["components"].append({"ref": "U99", "part": "W25Q32JVSSIQ", "value": "W25Q32", "mpn": "W25Q32JVSSIQ", "dnp": False,
                                "footprint": "x", "pins": {"1": {"name": "~{CS}", "etype": "input", "net": "FPGA_SS_N"}}})
        p["nets"]["FPGA_SS_N"].append("U99.1")
        self.fails(p, "ecp5_sysconfig")

    def test_vcc_decoupling_short(self):
        p = copy.deepcopy(BASE)
        n = 0
        for c in p["components"]:
            if c["part"] == "C0402" and c["value"] == "100nF" and c["pins"]["1"]["net"] == "1V1_FPGA" and n < 2:
                c["dnp"] = True
                n += 1
        self.fails(p, "ecp5_decoupling")

    def test_psram_signal_pullup_always_on(self):
        p = copy.deepcopy(BASE)
        r = find_r(p, "PSRAM_SIO2", "GND")
        rewire(p, r["ref"], "2" if r["pins"]["2"]["net"] == "GND" else "1", "3V3_FPGA")
        self.fails(p, "psram_power_architecture")

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


    # ---- R8.5-C RGMII link
    def test_rgmii_series_r_missing(self):             # direct connection: no termination at the F133 driver
        p = copy.deepcopy(BASE)
        r = find_r(p, "ETH_TXD1_F", "ETH_TXD1")
        rewire(p, r["ref"], "1" if r["pins"]["1"]["net"] == "ETH_TXD1" else "2", "ETH_TXD1_F")
        self.fails(p, "rgmii_link")

    def test_rgmii_series_r_wrong_value(self):
        p = copy.deepcopy(BASE)
        find_r(p, "ETH_RXD2_E", "ETH_RXD2")["value"] = "100R"
        self.fails(p, "rgmii_link")

    def test_rgmii_series_r_placed_at_receiver(self):  # layout note sends an ECP5-driven resistor to the F133 end
        p = copy.deepcopy(BASE)
        find_r(p, "ETH_RXD0_E", "ETH_RXD0")["note"] = "RGMII series R, place at F133"
        self.fails(p, "rgmii_link")

    def test_rgmii_load_on_driver_side(self):          # stub between the driver and its series resistor
        p = copy.deepcopy(BASE)
        tp = [c for c in p["components"] if c["part"].startswith("TP")][0]
        rewire(p, tp["ref"], "1", "ETH_TXCK_F")
        self.fails(p, "rgmii_link")

    def test_rgmii_clock_not_on_pclk(self):
        p = copy.deepcopy(BASE)
        rewire(p, "U18", "B11", None)
        rewire(p, "U18", "A9", "ETH_TXCK")               # GR_PCLK0_1, not a primary PCLK input
        self.fails(p, "rgmii_link")

    def test_rgmii_on_left_bank(self):                  # bank 6 is not hot-socket tolerant
        p = copy.deepcopy(BASE)
        rewire(p, "U18", "C10", None)
        rewire(p, "U18", "K2", "ETH_TXD0")
        self.fails(p, "rgmii_link")

    def test_rgmii_ctl_pulldown_missing(self):
        p = copy.deepcopy(BASE)
        find_r(p, "ETH_RXCTL", "GND")["dnp"] = True
        self.fails(p, "rgmii_link")

    def test_button_left_on_pg(self):
        p = copy.deepcopy(BASE)
        u = comp(p, "U15")
        num = [n for n, x in u["pins"].items() if x["name"] == "PG11"][0]
        rewire(p, "U15", num, "BTN_SELECT")
        self.fails(p, "rgmii_link")


if __name__ == "__main__":
    unittest.main(verbosity=2)
