"""Curated host checks for the current Compact ARC-1 R10 engineering targets."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# Fixed Make targets only. The Workbench never accepts a user-supplied command.
# Each target is one or more (folder, goals, out) steps; out, when set, is passed as OUT= so the build lands in the
# project's build/ area instead of the source folder or a shared /tmp path.
R10 = "hardware/compact-arc1/R10_WORK/"
FLOWS = {
    "f133": ([(R10 + "firmware/f133_bootloader", ["test", "sanitize", "freestanding", "readiness", "handoff", "handoff-freestanding"], None),
              (R10 + "firmware/f133_board_diag", ["test", "freestanding"], "build/compact/f133_board_diag")],
             "HOST_SIM"),
    "d213": ([(R10 + "d213/gpu_driver", ["test"], None),
              (R10 + "firmware/d213_flashless_proof/loader", ["test", "freestanding"], "build/compact/d213_loader"),
              (R10 + "firmware/d213_video_diag", ["test", "freestanding"], "build/compact/d213_video_diag")],
             "HOST_SIM"),
    "usb": ([(R10 + "firmware/f133_ehci", ["test", "sanitize"], "build/compact/f133_ehci"),
             (R10 + "firmware/usb_hub", ["test", "sanitize"], "build/compact/usb_hub")], "HOST_SIM"),
    "power": ([(R10 + "firmware/power_control", ["test", "sanitize"], "build/compact/power_control")], "HOST_SIM"),
    "fpga45": ([(R10 + "fpga45", ["ref", "sim", "build45"], None)], "RTL_SIM"),
    "fpga12": ([(R10 + "fpga12", ["lint", "rgmii"], None)], "RTL_SIM"),
}


def _check_one(result, target):
    result.command = "arc1 compact check --target %s" % target
    if target not in FLOWS:
        result.fail("COMPACT_TARGET", "unknown Compact R10 target: %s" % target)
        return
    steps, evidence = FLOWS[target]
    for folder, _, _ in steps:
        if not (ROOT / folder / "Makefile").is_file():
            result.verdict = "NOT_AVAILABLE"
            result.fail("COMPACT_SOURCE", "current R10 source or Makefile is missing: %s" % folder)
            return
    make = shutil.which("make")
    if not make:
        result.verdict = "NOT_AVAILABLE"
        result.fail("COMPACT_TOOL", "GNU make is required for the current R10 build/check flow")
        return
    result.evidence_level = evidence
    runs = []
    for folder, goals, out in steps:
        argv = [make, "-C", str(ROOT / folder), *goals] + (["OUT=" + str(ROOT / out)] if out else [])
        try:
            run = subprocess.run(argv, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=900, check=False)
        except subprocess.TimeoutExpired as exc:
            result.fail("COMPACT_TIMEOUT", "R10 %s flow exceeded 15 minutes in %s" % (target, folder))
            raw = exc.stdout or ""
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", "replace")
            result.extra["output"] = raw[-20000:]
            return
        runs.append({"folder": folder, "goals": goals, "returncode": run.returncode,
                     "output": (run.stdout or "")[-20000:]})
        if run.returncode:
            result.fail("COMPACT_BUILD", "R10 %s Make flow failed in %s with exit code %d"
                        % (target, folder, run.returncode))
    result.extra["details"] = {"target": target, "revision": "R10", "goals": [g for _, gs, _ in steps for g in gs],
                               "returncode": max(r["returncode"] for r in runs), "steps": runs,
                               "output": "\n".join(r["output"] for r in runs)[-20000:]}
    result.warn("Host or RTL simulation evidence only; no physical ARC-1 board was programmed")
    if target == "fpga12":
        result.warn("FPGA12 checks use the R10 proxy package; they do not prove the target package or silicon")
    if target == "f133":
        result.warn("Freestanding objects are compile checks, not a linked bootable firmware image")
    if target in ("usb", "power", "d213"):
        result.warn("Host models stand in for the F133/D213 controllers, PHY, DMA and rails: SIMULATED; "
                    "physical adapters are NOT INSTRUMENTED")


def check(result, target):
    if target != "all":
        return _check_one(result, target)
    from .core import Result
    outputs = {}
    for current in FLOWS:
        child = Result("arc1 compact check --target %s" % current, "HOST_SIM")
        _check_one(child, current)
        outputs[current] = child.extra.get("details", child.extra.get("output", {}))
        for warning in child.warnings:
            result.warn(warning)
        for failure in child.failures:
            result.fail(failure["code"], "%s: %s" % (current, failure["message"]))
    result.command = "arc1 compact check --target all"
    result.extra["details"] = {"revision": "R10", "targets": outputs}
