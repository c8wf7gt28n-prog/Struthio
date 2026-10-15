import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

DISPLAY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DISPLAY))
from validate_display import validate_display


class DisplayPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((DISPLAY / "compact_display.json").read_text())

    def test_selected_clock_and_intervals_close_at_nominal_sixty(self):
        report = validate_display(self.plan)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["calculated"]["pixel_clock_hz"], 48_000_000)
        self.assertEqual(report["calculated"]["nominal_refresh_hz"], 60)
        self.assertTrue(all(check["pass"] for check in report["checks"]))
        self.assertFalse(report["hardware_verified"])
        self.assertIsNone(report["register_writes"])

    def test_source_interval_conversion_yields_conditional_bt_positions(self):
        report = validate_display(self.plan)
        registers = report["bt_register_model"]
        self.assertEqual((registers["REG_HSYNC0"], registers["REG_HSYNC1"], registers["REG_HOFFSET"]), (96, 112, 256))
        self.assertEqual((registers["REG_VSYNC0"], registers["REG_VSYNC1"], registers["REG_VOFFSET"]), (2, 3, 25))
        self.assertEqual(report["calculated"]["horizontal_post_sync_back_porch"], 144)
        self.assertEqual(report["calculated"]["vertical_post_sync_back_porch"], 22)

    def test_r04_porch_assumption_cannot_be_silently_promoted(self):
        legacy = json.loads((DISPLAY / "r04_porch_assumption.json").read_text())
        self.plan["raster"]["horizontal"] = legacy["horizontal"]
        self.plan["raster"]["vertical"] = legacy["vertical"]
        report = validate_display(self.plan)
        self.assertFalse(report["valid"])
        self.assertEqual(report["calculated"]["horizontal_total_from_intervals"], 1264)
        self.assertEqual(report["calculated"]["vertical_total_from_intervals"], 624)
        self.assertTrue(any("horizontal interval total" in error for error in report["errors"]))
        self.assertTrue(any("vertical interval total" in error for error in report["errors"]))

    def test_typical_panel_totals_with_changed_clock_miss_refresh_target(self):
        h, v = self.plan["raster"]["horizontal"], self.plan["raster"]["vertical"]
        h.update(total=1344, front_porch=160)
        v.update(total=635, front_porch=12)
        report = validate_display(self.plan)
        self.assertFalse(report["valid"])
        self.assertLess(report["calculated"]["nominal_refresh_hz"], 57)
        self.assertTrue(any("target/tolerance" in error for error in report["errors"]))

    def test_declared_clock_cannot_disagree_with_derived_clock(self):
        self.plan["clock"]["declared_pixel_clock_hz"] = 51_200_000
        report = validate_display(self.plan)
        self.assertFalse(report["valid"])
        self.assertTrue(any("Declared pixel clock" in error for error in report["errors"]))

    def test_bt_legal_clock_can_still_be_outside_panel_range(self):
        self.plan["clock"].update(txclkdiv=9, declared_pixel_clock_hz=28_800_000)
        report = validate_display(self.plan)
        self.assertFalse(report["valid"])
        self.assertTrue(any("pixel_clock_hz" in error and "outside" in error for error in report["errors"]))

    def test_illegal_sync_width_is_not_hidden_by_unchanged_totals(self):
        self.plan["raster"]["horizontal"]["sync"] = 141
        report = validate_display(self.plan)
        self.assertFalse(report["valid"])
        self.assertTrue(any("horizontal.sync" in error for error in report["errors"]))

    def test_invalid_front_porch_and_fixed_back_interval_are_rejected(self):
        for field, value in (("front_porch", 15), ("back_porch", 159)):
            with self.subTest(field=field):
                plan = copy.deepcopy(self.plan)
                plan["raster"]["horizontal"][field] = value
                self.assertFalse(validate_display(plan)["valid"])

    def test_unknown_or_exclusive_porch_semantics_require_review(self):
        for convention in ("unknown", "excludes_sync"):
            with self.subTest(convention=convention):
                self.plan["raster"]["panel_back_porch_definition"] = convention
                self.assertFalse(validate_display(self.plan)["valid"])

    def test_dual_channel_change_requires_new_model(self):
        self.plan["scanout"]["channels"] = 2
        self.assertFalse(validate_display(self.plan)["valid"])

    def test_unsupported_pll_reference_and_fractional_or_boolean_fields_reject(self):
        mutations = (("syspll_ns", 14), ("reference_hz", 37_125_000), ("txclkdiv", 5.0), ("reference_hz", True))
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                plan = copy.deepcopy(self.plan)
                plan["clock"][field] = value
                self.assertFalse(validate_display(plan)["valid"])

    def test_caller_confirmation_never_creates_hardware_evidence(self):
        self.plan["confirmations"] = {key: True for key in self.plan["confirmations"]}
        report = validate_display(self.plan)
        self.assertTrue(report["valid"])
        self.assertFalse(report["hardware_verified"])
        self.assertTrue(any("caller declaration" in warning for warning in report["warnings"]))

    def test_unbounded_numeric_input_returns_errors_without_float_overflow(self):
        self.plan["clock"]["reference_hz"] = 10**400
        self.plan["raster"]["horizontal"]["total"] = 10**400
        report = validate_display(self.plan)
        self.assertFalse(report["valid"])
        self.assertTrue(report["errors"])

    def test_cli_reports_invalid_input_with_nonzero_exit(self):
        with tempfile.TemporaryDirectory(dir=DISPLAY / "tests") as temp:
            path = Path(temp) / "invalid.json"
            path.write_text("{not valid JSON")
            result = subprocess.run([sys.executable, str(DISPLAY / "validate_display.py"), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["status"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
