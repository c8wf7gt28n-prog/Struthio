"""Unit tests for check_board_plan.py: the shipped plan passes, and each
class of planning error is caught. Run: python3 -m unittest discover -s tests -v"""
import copy
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location("cbp", os.path.join(BOARD, "check_board_plan.py"))
cbp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cbp)

with open(os.path.join(BOARD, "r06_board_plan.json"), encoding="utf-8") as f:
    PLAN = json.load(f)
with open(cbp.FACTS, encoding="utf-8") as f:
    FACTS = json.load(f)
T35 = cbp.load_csv(cbp.T35_CSV)
F133 = cbp.load_csv(cbp.F133_PINS)
MUX = cbp.load_csv(cbp.F133_MUX)
LINUX = cbp.load_csv(cbp.LINUX_MUX)


def run(plan):
    c = cbp.Checker(plan, FACTS, T35, F133, MUX, LINUX)
    ok = c.run()
    return ok, {r["rule"].split("[")[0] for r in c.results if not r["pass"]}


class TestBoardPlan(unittest.TestCase):
    def test_shipped_plan_passes(self):
        ok, fails = run(copy.deepcopy(PLAN))
        self.assertTrue(ok, fails)

    def test_source_tables_sane(self):
        self.assertEqual(len(T35), 400)
        self.assertEqual(len(F133), 72)               # eLQFP128 bonded GPIOs
        self.assertNotIn("PB8", {r["pin"] for r in F133})
        self.assertGreater(len(LINUX), 300)

    def mutate(self, fn, expect):
        p = copy.deepcopy(PLAN)
        fn(p)
        ok, fails = run(p)
        self.assertFalse(ok)
        self.assertIn(expect, fails)

    def test_unbonded_f133_pin(self):          # SPI1 alternate on PB8 does not exist on F133
        self.mutate(lambda p: p["f133"]["pins"].update({"PB8": {"func": 5, "net": "BT_IO3", "dir": "bidir"}}),
                    "f133.pin_bonded_on_eLQFP128")

    def test_wrong_mux_function(self):
        self.mutate(lambda p: p["f133"]["pins"]["PD11"].update({"func": 3}), "f133.mux_in_table43")

    def test_t35_bank_mismatch(self):
        self.mutate(lambda p: p["t35"]["pins"]["K19"].update({"bank": "BANK1D"}), "t35.bank_matches")

    def test_t35_name_mismatch(self):
        self.mutate(lambda p: p["t35"]["pins"]["K19"].update({"name": "GPIOL_47"}), "t35.name_matches")

    def test_configuration_pin_used_as_gpio(self):
        self.mutate(lambda p: p["t35"]["pins"].update({"Y17": {"name": "GPIOL_08_CDI0", "bank": "BANK1A",
                                                                 "net": "PSRAM_SIO3", "dir": "bidir"}}),
                    "t35.config_pin_policy")

    def test_illegal_bank_voltage(self):
        def f(p):
            p["rails"]["3V0"] = {"nominal": 3.0, "min": 2.9, "max": 3.1}
            p["t35"]["bank_rails"]["BANK1C"] = "3V0"
        self.mutate(f, "t35.bank_voltage_legal")

    def test_psram_on_1v8_bank_level_mismatch(self):
        def f(p):
            p["rails"]["1V8"] = {"nominal": 1.8, "min": 1.71, "max": 1.89}
            p["t35"]["bank_rails"]["BANK1C"] = "1V8"
        self.mutate(f, "level.compatible")

    def test_merged_banks_must_match(self):
        def f(p):
            p["rails"]["1V8"] = {"nominal": 1.8, "min": 1.71, "max": 1.89}
            p["t35"]["bank_rails"]["TR"] = "1V8"
        self.mutate(f, "t35.merged_banks_same_rail")

    def test_t35_on_bt820_bus_rejected(self):
        self.mutate(lambda p: p["t35"]["pins"].update({"G16": {"name": "GPIOL_89", "bank": "BANK1D",
                                                                 "net": "BT_SCK", "dir": "out"}}),
                    "topology.bt820_independent_of_t35")

    def test_second_bt820_master_rejected(self):
        self.mutate(lambda p: p["t35"]["pins"].update({"G16": {"name": "GPIOL_89", "bank": "BANK1D",
                                                                 "net": "BT_SS_N", "dir": "out"}}),
                    "net.single_push_pull_driver")

    def test_emmc_boot_conflicts_with_spi0(self):
        self.mutate(lambda p: p["f133"].update({"boot_medium": "EMMC_SMHC2"}),
                    "f133.boot_medium_not_emmc_when_spi0_used")

    def test_unacknowledged_boot_strap_sharing(self):
        self.mutate(lambda p: p.update({"acknowledged_risks": [a for a in p["acknowledged_risks"]
                                                               if a["id"] != "BOOTSEL_SHARED_WITH_SPI0"]}),
                    "f133.boot_strap_sharing_acknowledged")

    def test_psram_pulldown_too_weak(self):
        def f(p):
            for x in p["passives"]:
                if x["net"] == "PSRAM_SCLK":
                    x["ohms"] = 10000
        self.mutate(f, "psram.powerup_low_during_t35_config")

    def test_missing_bt820_data_pulldown(self):
        self.mutate(lambda p: p.update({"passives": [x for x in p["passives"] if x["net"] != "BT_IO2"]}),
                    "bt820.data_pulldown")

    def test_open_drain_without_pullup(self):
        self.mutate(lambda p: p.update({"passives": [x for x in p["passives"] if x["net"] != "BT_INT_N"]}),
                    "net.open_drain_pullup")

    def test_f133_domain_out_of_range(self):
        def f(p):
            p["rails"]["2V5"] = {"nominal": 2.5, "min": 2.38, "max": 2.63}
            p["f133"]["domain_rails"]["VCC-PD"] = "2V5"
        self.mutate(f, "f133.domain_voltage_legal")

    def test_psram_shared_outside_t35(self):
        self.mutate(lambda p: p["f133"]["pins"].update({"PG0": {"func": 1, "net": "PSRAM_SIO0", "dir": "bidir"}}),
                    "topology.psram_private_to_t35")


if __name__ == "__main__":
    unittest.main()
