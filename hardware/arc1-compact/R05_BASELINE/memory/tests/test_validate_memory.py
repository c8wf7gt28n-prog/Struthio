import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MEMORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MEMORY))
from validate_memory import CAPACITY, RESERVED, validate_memory

MIB = 1024 * 1024


class MemoryPlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((MEMORY / "bt820_memory.json").read_text())

    def append_region(self, start, size, name="additional"):
        self.plan["allocations"].append({"name": name, "owner": "BT820", "role": "scratch_budget", "start": start, "size": size})

    def test_selected_plan_conserves_capacity_with_private_reserved_region(self):
        report = validate_memory(self.plan)
        self.assertTrue(report["valid"], report["errors"])
        values = report["calculated"]
        self.assertEqual(values["allocated_bytes"] + values["free_bytes"] + RESERVED, CAPACITY)
        self.assertEqual(sum(row["size"] for row in report["free_intervals"]), values["free_bytes"])
        self.assertEqual(values["one_frame_storage_bytes"], 1_843_200)
        self.assertEqual(values["free_mib"], 76.984375)
        self.assertEqual(values["optional_capture_payload_bytes_not_allocated"], 3_686_400)
        self.assertFalse(report["hardware_verified"])

    def test_last_user_page_can_end_exactly_at_reserved_boundary(self):
        self.append_region(CAPACITY - RESERVED - 4096, 4096)
        self.assertTrue(validate_memory(self.plan)["valid"])

    def test_reserved_region_entry_rejected(self):
        self.append_region(CAPACITY - RESERVED, 4096)
        report = validate_memory(self.plan)
        self.assertFalse(report["valid"])
        self.assertTrue(any("reserved upper" in error for error in report["errors"]))

    def test_beyond_physical_end_rejected(self):
        self.append_region(CAPACITY - 4096, 8192)
        report = validate_memory(self.plan)
        self.assertFalse(report["valid"])
        self.assertTrue(any("exceeds physical" in error for error in report["errors"]))

    def test_nested_overlap_detected(self):
        self.append_region(8 * MIB, 4096)
        report = validate_memory(self.plan)
        self.assertFalse(report["valid"])
        self.assertTrue(any("overlap" in error for error in report["errors"]))

    def test_adjacent_half_open_intervals_are_legal(self):
        self.append_region(49 * MIB, MIB)
        self.assertTrue(validate_memory(self.plan)["valid"])

    def test_address_alignment_enforced(self):
        self.append_region(50 * MIB + 1, 4096)
        report = validate_memory(self.plan)
        self.assertFalse(report["valid"])
        self.assertTrue(any("alignment" in error for error in report["errors"]))

    def test_duplicate_names_or_cross_device_owner_rejected(self):
        for changes in ({"name": "render_scanout_0"}, {"owner": "CPU"}):
            with self.subTest(changes=changes):
                plan = copy.deepcopy(self.plan)
                plan["allocations"][2].update(changes)
                self.assertFalse(validate_memory(plan)["valid"])

    def test_zero_negative_fractional_and_boolean_sizes_rejected(self):
        for size in (0, -4096, 4096.5, True):
            with self.subTest(size=size):
                plan = copy.deepcopy(self.plan)
                plan["allocations"][2]["size"] = size
                self.assertFalse(validate_memory(plan)["valid"])

    def test_framebuffer_must_contain_full_stride_times_height(self):
        self.plan["allocations"][0]["size"] -= 1
        report = validate_memory(self.plan)
        self.assertFalse(report["valid"])
        self.assertTrue(any("stride times height" in error for error in report["errors"]))

    def test_invalid_stride_and_unqualified_scanout_format_rejected(self):
        for changes in ({"stride_bytes": 3000}, {"format": "RGB565"}):
            with self.subTest(changes=changes):
                plan = copy.deepcopy(self.plan)
                plan["allocations"][0].update(changes)
                self.assertFalse(validate_memory(plan)["valid"])

    def test_swapchain_slot_collision_or_mismatched_frames_rejected(self):
        for changes in ({"slot": 0}, {"height": 599}):
            with self.subTest(changes=changes):
                plan = copy.deepcopy(self.plan)
                plan["allocations"][1].update(changes)
                self.assertFalse(validate_memory(plan)["valid"])

    def test_unilateral_capacity_or_reservation_change_rejected(self):
        for field, value in (("capacity_bytes", 64 * MIB), ("reserved_upper_bytes", MIB)):
            with self.subTest(field=field):
                plan = copy.deepcopy(self.plan)
                plan[field] = value
                self.assertFalse(validate_memory(plan)["valid"])

    def test_optional_capture_cannot_be_enabled_without_allocations(self):
        self.plan["optional_capture"]["allocated"] = True
        self.assertFalse(validate_memory(self.plan)["valid"])

    def test_smaller_render_target_cannot_masquerade_as_full_scanout_buffers(self):
        for allocation in self.plan["allocations"][:2]:
            allocation.update(width=640, height=480, stride_bytes=1920)
        report = validate_memory(self.plan)
        self.assertFalse(report["valid"])
        self.assertTrue(any("selected 1024x600" in error for error in report["errors"]))

    def test_invalid_optional_capture_allowance_is_not_a_free_zero_cost_feature(self):
        self.plan["optional_capture"]["buffers"] = 0
        self.assertFalse(validate_memory(self.plan)["valid"])

    def test_caller_measurement_claim_does_not_certify_hardware(self):
        self.plan["hardware_measured"] = True
        report = validate_memory(self.plan)
        self.assertTrue(report["valid"])
        self.assertFalse(report["hardware_verified"])

    def test_cli_reports_malformed_input_without_traceback(self):
        with tempfile.TemporaryDirectory(dir=MEMORY / "tests") as temp:
            path = Path(temp) / "bad.json"
            path.write_text("null")
            result = subprocess.run([sys.executable, str(MEMORY / "validate_memory.py"), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(json.loads(result.stdout)["valid"])
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
