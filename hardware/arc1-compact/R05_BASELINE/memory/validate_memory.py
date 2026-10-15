#!/usr/bin/env python3
"""Check the selected MN820 DDR planning map, including its top reservation.

Public API: validate_memory(plan: dict) -> dict.
CLI: python memory/validate_memory.py [plan.json] [--output report.json]
Exit 0 checks declared allocations only; no physical RAM or workload is tested.
"""

import argparse
import json
from pathlib import Path
import sys


CAPACITY = 128 * 1024 * 1024
RESERVED = 5 * 1024 * 1024 // 2
MIB = 1024 * 1024


def validate_memory(plan):
    errors, warnings = [], []
    report = {
        "schema": "arc1-bt820-memory-report-v1", "valid": False,
        "status": "INVALID_PLANNING_DATA", "evidence_level": "DECLARED_ALLOCATION_ARITHMETIC_ONLY",
        "hardware_verified": False, "errors": errors, "warnings": warnings,
        "interval_convention": "half-open [start,end)", "allocations": [],
        "free_intervals": [], "calculated": {},
    }
    if not isinstance(plan, dict):
        errors.append("Plan must be a JSON object.")
        return report

    def integer(parent, key, path, minimum=0):
        value = parent.get(key)
        if type(value) is not int or value < minimum:
            errors.append(f"{path} must be an integer >= {minimum}; booleans are not accepted.")
            return None
        return value

    if plan.get("schema") != "arc1-bt820-memory-plan-v1":
        errors.append("Unsupported or missing memory schema.")
    if plan.get("device") != "BT820B" or plan.get("prototype_module") != "MN820":
        errors.append("This source-bounded plan applies to BT820B on MN820 only.")
    capacity = integer(plan, "capacity_bytes", "capacity_bytes", 1)
    reserved = integer(plan, "reserved_upper_bytes", "reserved_upper_bytes", 1)
    alignment = integer(plan, "planning_alignment_bytes", "planning_alignment_bytes", 1)
    refresh = integer(plan, "nominal_refresh_hz", "nominal_refresh_hz", 1)
    if capacity is not None and capacity != CAPACITY:
        errors.append("MN820's selected installed capacity is 128 MiB; do not silently resize it.")
    if reserved is not None and reserved != RESERVED:
        errors.append("The reviewed upper 2.5 MiB DDR reservation cannot be reduced or relabeled as free.")
    if alignment is not None and alignment & (alignment - 1):
        errors.append("planning_alignment_bytes must be a power of two.")
    # Keep the known reserved boundary effective even if declarations are corrupt.
    user_end = CAPACITY - RESERVED
    report["reserved_interval"] = {"start": user_end, "end": CAPACITY, "size": RESERVED}

    rows = plan.get("allocations")
    if not isinstance(rows, list):
        errors.append("allocations must be an array.")
        rows = []
    names, intervals, frames = set(), [], []
    for index, allocation in enumerate(rows):
        path = f"allocations[{index}]"
        if not isinstance(allocation, dict):
            errors.append(f"{path} must be an object.")
            continue
        name = allocation.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{path}.name must be nonempty text.")
            name = f"invalid_name_{index}"
        if name in names:
            errors.append(f"Duplicate allocation name: {name}.")
        names.add(name)
        if allocation.get("owner") != "BT820":
            errors.append(f"{name}: only BT820 owns this address space.")
        start = integer(allocation, "start", f"{path}.start")
        size = integer(allocation, "size", f"{path}.size", 1)
        if start is None or size is None:
            continue
        end = start + size
        if alignment and start % alignment:
            errors.append(f"{name}: start violates the declared planning alignment.")
        if end > CAPACITY:
            errors.append(f"{name}: allocation exceeds physical RAM.")
        elif end > user_end:
            errors.append(f"{name}: allocation enters the reserved upper 2.5 MiB.")
        intervals.append((start, end, name))
        report["allocations"].append({"name": name, "start": start, "end": end, "size": size})
        if allocation.get("role") == "render_scanout":
            frame = {key: integer(allocation, key, f"{path}.{key}", 1)
                     for key in ("width", "height", "stride_bytes")}
            slot = integer(allocation, "slot", f"{path}.slot")
            chain = integer(allocation, "swapchain", f"{path}.swapchain")
            if allocation.get("format") != "RGB8":
                errors.append(f"{name}: this selected render/scanout budget supports RGB8, not an assumed RGB565 scanout mode.")
            if chain is not None and chain != 0:
                errors.append(f"{name}: render/scanout buffers belong to Swapchain0 in this plan.")
            if all(value is not None for value in frame.values()):
                if (frame["width"], frame["height"]) != (1024, 600):
                    errors.append(f"{name}: frame dimensions do not match the selected 1024x600 scanout plan.")
                if frame["stride_bytes"] < frame["width"] * 3:
                    errors.append(f"{name}: RGB8 stride is smaller than one active pixel row.")
                if frame["stride_bytes"] % 64:
                    errors.append(f"{name}: stride violates this plan's 64-byte row-alignment policy.")
                if frame["stride_bytes"] * frame["height"] > size:
                    errors.append(f"{name}: allocated size cannot contain stride times height.")
                frames.append((slot, frame["width"], frame["height"], frame["stride_bytes"]))

    intervals.sort()
    high_water, previous_name = 0, None
    for start, end, name in intervals:
        if start < high_water:
            errors.append(f"Allocation overlap: {name} intersects {previous_name} or an earlier covering allocation.")
        if end > high_water:
            high_water, previous_name = end, name
    if not 2 <= len(frames) <= 4:
        errors.append("Declare 2..4 render/scanout frames for the reviewed Swapchain0 plan.")
    if frames:
        slots = [frame[0] for frame in frames]
        if None in slots or sorted(slots) != list(range(len(frames))):
            errors.append("Swapchain0 slots must be unique and contiguous from zero.")
        if len({frame[1:] for frame in frames}) != 1:
            errors.append("Swapchain0 buffers must have matching dimensions and stride.")

    capture = plan.get("optional_capture")
    if not isinstance(capture, dict) or capture.get("allocated") is not False:
        errors.append("Optional capture is not allocated by this plan; create a separately reviewed memory profile before enabling it.")
    else:
        capture_values = {key: integer(capture, key, f"optional_capture.{key}", 1)
                          for key in ("width", "height", "buffers")}
        if capture.get("format") != "RGB8":
            errors.append("The optional capture planning allowance uses RGB8 only.")
        if capture_values["buffers"] is not None and not 2 <= capture_values["buffers"] <= 4:
            errors.append("Optional capture allowance must declare 2..4 buffers.")
        if all(value is not None for value in capture_values.values()) and capture.get("format") == "RGB8":
            report["calculated"]["optional_capture_payload_bytes_not_allocated"] = (
                capture_values["width"] * capture_values["height"] * 3 * capture_values["buffers"])

    for field in ("workload_size_verified", "hardware_measured"):
        if type(plan.get(field)) is not bool:
            errors.append(f"{field} must be boolean.")
        elif plan[field]:
            warnings.append(f"{field} is a caller declaration, not proof checked by this tool.")
        else:
            warnings.append(f"OPEN: {field}.")
    if not errors:
        cursor = 0
        for start, end, _ in intervals:
            if start > cursor:
                report["free_intervals"].append({"start": cursor, "end": start, "size": start - cursor})
            cursor = end
        if cursor < user_end:
            report["free_intervals"].append({"start": cursor, "end": user_end, "size": user_end - cursor})
        allocated = sum(end - start for start, end, _ in intervals)
        free = user_end - allocated
        report["calculated"].update({
            "physical_bytes": CAPACITY, "user_region_bytes_before_allocations": user_end,
            "allocated_bytes": allocated, "allocated_mib": allocated / MIB,
            "free_bytes": free, "free_mib": free / MIB,
            "largest_free_interval_bytes": max((row["size"] for row in report["free_intervals"]), default=0),
        })
        if frames and refresh:
            _, width, height, stride = frames[0]
            report["calculated"].update({
                "one_rgb8_frame_payload_bytes": width * height * 3,
                "one_frame_storage_bytes": stride * height,
                "active_rgb8_scanout_MB_per_second_at_declared_refresh": width * height * 3 * refresh / 1_000_000,
            })
    warnings.append("Declared allowances are not measured STRUTHIO asset requirements or sustainable DDR bandwidth.")
    report["valid"] = not errors
    report["status"] = "VALID_PLANNING_DATA" if report["valid"] else "INVALID_PLANNING_DATA"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", nargs="?", type=Path, default=Path(__file__).with_name("bt820_memory.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate_memory(json.loads(args.plan.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        report = {"valid": False, "status": "INVALID_INPUT", "hardware_verified": False, "errors": [str(exc)]}
    output = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
