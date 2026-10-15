#!/usr/bin/env python3
"""Validate one source-bounded display planning model; never emit hardware writes.

Public API: validate_display(plan: dict) -> dict.
CLI: python display/validate_display.py [plan.json] [--output report.json]
Exit 0 means internally valid planning arithmetic, not electrical/hardware proof.
"""

import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys


PANEL = "NHD-7.0-1024600AF-LSXP"
# Newhaven specification, printed p7. Inclusive-back interpretation is an
# explicitly recorded inference; changing these limits requires source review.
PANEL_LIMITS = {
    "pixel_clock_hz": (44_900_000, 63_000_000),
    "horizontal": {
        "active": (1024, 1024), "total": (1200, 1400),
        "sync": (1, 140), "back_porch": (160, 160),
        "front_porch": (16, 216),
    },
    "vertical": {
        "active": (600, 600), "total": (624, 750),
        "sync": (1, 20), "back_porch": (23, 23),
        "front_porch": (1, 127),
    },
}


def validate_display(plan):
    errors, warnings = [], []
    report = {
        "schema": "arc1-display-report-v1", "valid": False, "status": "INVALID_PLANNING_DATA",
        "evidence_level": "PLANNING_ARITHMETIC_ONLY",
        "hardware_verified": False, "errors": errors, "warnings": warnings,
        "checks": [], "calculated": {}, "bt_register_model": None,
        "register_writes": None,
    }
    if not isinstance(plan, dict):
        errors.append("Plan must be a JSON object.")
        return report

    def obj(parent, key, path):
        value = parent.get(key)
        if not isinstance(value, dict):
            errors.append(f"{path} must be an object.")
            return {}
        return value

    def integer(parent, key, path, minimum=1, maximum=2**32 - 1):
        value = parent.get(key)
        if type(value) is not int or value < minimum or (maximum is not None and value > maximum):
            bounds = f"{minimum}..{maximum}" if maximum is not None else f">={minimum}"
            errors.append(f"{path} must be an integer {bounds}; booleans are not integers here.")
            return None
        return value

    def check(label, value, low, high):
        ok = low <= value <= high
        report["checks"].append({"constraint": label, "value": value,
                                 "minimum": low, "maximum": high, "pass": ok})
        if not ok:
            errors.append(f"{label}: {value} outside {low}..{high}.")

    if plan.get("schema") != "arc1-compact-display-plan-v1":
        errors.append("Unsupported or missing display schema.")
    if plan.get("panel") != PANEL:
        errors.append("Panel does not match this validator's reviewed source limits.")

    clock = obj(plan, "clock", "clock")
    raster = obj(plan, "raster", "raster")
    target = obj(plan, "target", "target")
    scanout = obj(plan, "scanout", "scanout")
    confirmations = obj(plan, "confirmations", "confirmations")
    ref = integer(clock, "reference_hz", "clock.reference_hz")
    multiplier = integer(clock, "syspll_ns", "clock.syspll_ns")
    divider = integer(clock, "txclkdiv", "clock.txclkdiv", 0, 15)
    declared = integer(clock, "declared_pixel_clock_hz", "clock.declared_pixel_clock_hz")
    target_hz = integer(target, "nominal_refresh_hz", "target.nominal_refresh_hz")
    ppm = integer(target, "allowed_nominal_error_ppm", "target.allowed_nominal_error_ppm", 0, 1_000_000)

    if ref is not None and ref != 38_400_000:
        errors.append("Only the reviewed 38.4 MHz BT reference is supported by this model.")
    if multiplier is not None and multiplier not in (13, 15):
        errors.append("SYSPLL_NS is outside the reviewed documented set {13, 15}.")
    for field, expected in (("channels", 1), ("pixels_per_link_clock", 1), ("bt_so_mode_candidate", 0)):
        value = integer(scanout, field, f"scanout.{field}", 0)
        if value is not None and value != expected:
            errors.append(f"This calculation supports single-channel one-pixel scanout only: {field} must be {expected}.")
    if scanout.get("format") != "RGB8":
        errors.append("This reviewed scanout budget uses RGB8 only.")

    convention = raster.get("panel_back_porch_definition")
    if convention not in ("includes_sync", "excludes_sync"):
        errors.append("Declare panel_back_porch_definition as includes_sync or excludes_sync; do not hide this ambiguity.")
    elif convention == "excludes_sync":
        # The printed typical values would not close if sync were added again.
        errors.append("An exclusive-back interpretation contradicts this source-bound model; independently review the panel diagram first.")

    axes = {}
    for name in ("horizontal", "vertical"):
        raw = obj(raster, name, f"raster.{name}")
        values = {key: integer(raw, key, f"raster.{name}.{key}") for key in PANEL_LIMITS[name]}
        axes[name] = values
        for key, value in values.items():
            if value is not None:
                check(f"{name}.{key}", value, *PANEL_LIMITS[name][key])
        if all(value is not None for value in values.values()):
            expected = values["active"] + values["back_porch"] + values["front_porch"]
            if convention == "excludes_sync":
                expected += values["sync"]
            report["calculated"][f"{name}_total_from_intervals"] = expected
            if expected != values["total"]:
                errors.append(f"{name} interval total {expected} does not equal declared {values['total']}.")
            if convention == "includes_sync" and values["sync"] > values["back_porch"]:
                errors.append(f"{name} sync pulse cannot extend beyond the inclusive back interval.")
            report["calculated"][f"{name}_post_sync_back_porch"] = values["back_porch"] - values["sync"]

    pixel_clock = None
    if None not in (ref, multiplier, divider):
        pixel_clock = Fraction(ref * multiplier, 2 * (divider + 1))
        report["calculated"]["pixel_clock_hz"] = float(pixel_clock)
        check("pixel_clock_hz", float(pixel_clock), *PANEL_LIMITS["pixel_clock_hz"])
        if declared is not None and pixel_clock != declared:
            errors.append("Declared pixel clock does not equal the clock derived from the BT parameters.")
    h, v = axes["horizontal"], axes["vertical"]
    if h["active"] and h["active"] % 16:
        errors.append("Reviewed BT scanout width must be a multiple of 16 pixels.")
    if h["active"] and v["active"] and h["active"] * v["active"] % 128:
        errors.append("Reviewed BT scanout pixel area must be a multiple of 128 pixels.")
    if pixel_clock is not None and h["total"] and v["total"]:
        refresh = pixel_clock / (h["total"] * v["total"])
        report["calculated"]["nominal_refresh_hz"] = float(refresh)
        report["calculated"]["frame_period_ms"] = float(1000 / refresh)
        if target_hz is not None and ppm is not None:
            error_ppm = abs(refresh - target_hz) * 1_000_000 / target_hz
            report["calculated"]["nominal_refresh_error_ppm"] = float(error_ppm)
            if error_ppm > ppm:
                errors.append("Calculated nominal refresh misses the declared target/tolerance.")

    if convention == "includes_sync" and all(value is not None for axis in axes.values() for value in axis.values()):
        report["bt_register_model"] = {
            "status": "CONDITIONAL_MODEL_NOT_AN_INITIALIZATION_SEQUENCE",
            "origin_assumption": "AN097 front-porch-first origin; panel BP includes its pulse.",
            "REG_HSIZE": h["active"], "REG_HCYCLE": h["total"],
            "REG_HSYNC0": h["front_porch"], "REG_HSYNC1": h["front_porch"] + h["sync"],
            "REG_HOFFSET": h["front_porch"] + h["back_porch"],
            "REG_VSIZE": v["active"], "REG_VCYCLE": v["total"],
            "REG_VSYNC0": v["front_porch"], "REG_VSYNC1": v["front_porch"] + v["sync"],
            "REG_VOFFSET": v["front_porch"] + v["back_porch"],
            "REG_SO_MODE_candidate": 0,
        }
    for field in (
        "panel_porch_definition_confirmed", "bt_register_encoding_confirmed",
        "lvds_bit_mapping_confirmed", "lvds_electrical_and_termination_confirmed",
        "power_sequence_backlight_confirmed", "motion_quality_accepted", "hardware_measured",
    ):
        value = confirmations.get(field)
        if type(value) is not bool:
            errors.append(f"confirmations.{field} must be boolean.")
        elif value:
            warnings.append(f"{field} is a caller declaration, not proof checked by this tool.")
        else:
            warnings.append(f"OPEN: {field}.")
    warnings.append("Nominal arithmetic excludes oscillator tolerance and does not prove distinct frame cadence.")
    report["valid"] = not errors
    report["status"] = "VALID_PLANNING_DATA" if report["valid"] else "INVALID_PLANNING_DATA"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", nargs="?", type=Path, default=Path(__file__).with_name("compact_display.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate_display(json.loads(args.plan.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        report = {"valid": False, "status": "INVALID_INPUT", "hardware_verified": False, "errors": [str(exc)]}
    output = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
