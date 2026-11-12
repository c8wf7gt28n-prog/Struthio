"""Simulation-first R10 inspection and bounded, causally connected experiments.

An owner confidence goal is retained without inventing a probability. Fixture
success, target model completeness and fabrication permission are separate.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

BASE = Path("hardware/compact-arc1/R10_WORK")
MODEL_FILES = (
    "sdk/cli/arc1cli/causal_sim.py", "workbench/console_simulation.py",
    "workbench/simulation_tools.py",
)
HARDWARE_FILES = (
    "board/r10_board_plan.json", "cad/NETLIST.xml", "cad/ARC1_R10.kicad_pcb",
    "spec/ARC1_R10.txt", "spec/ARC1_MEMORY_R10.txt",
    "firmware/d213_flashless_proof/loader/r10_d213_start.c",
    "firmware/d213_flashless_proof/loader/r10_d213_start.h",
    "firmware/d213_flashless_proof/loader/test_r10_d213_start.c",
    "firmware/d213_video_diag/r10_video_start.c", "firmware/d213_video_diag/r10_video_start.h",
    "firmware/d213_video_diag/r10_video_diag.c", "firmware/d213_video_diag/r10_video_diag.h",
    "firmware/d213_video_diag/r10_adv7513.c", "firmware/d213_video_diag/r10_adv7513.h",
    "closure_p9/test_host_sequence.c",
)
FIELDS = {"simulation.inspect": ({}, [])}
EXPECTED_ACTORS = {"F133": "U18", "D213": "U20", "FPGA45": "U35", "FPGA12": "U40",
                   "HDMI bridge": "U33", "F133 NOR": "U19", "D213 NOR": "U22",
                   "FPGA45 SDRAM": "U39", "FPGA12 PSRAM": "U45"}

# These are required areas, not equal-risk percentages or a complete reviewed
# qualification inventory. Nothing silently closes because a tool is installed.
GATES = (
    ("POWER", "Power sequencing, rail tolerances, brown-out, reset and clock startup", "electrical transient and corner models"),
    ("F133_CPU", "F133 instruction execution and peripheral map", "qualified CPU/peripheral backend"),
    ("F133_BOOT", "F133 ROM image, boot straps, first stage and DRAM initialization", "actual startup image plus modeled ROM/DDR behavior"),
    ("NOR", "NOR reset state, image validation and interrupted reads/writes", "exact-part protocol model connected to firmware"),
    ("USB", "USB controllers, mux roles, enumeration, transfer lengths and recovery", "controller/device models connected to both processors"),
    ("D213_CPU", "D213 instruction execution and peripheral map", "qualified D213 backend"),
    ("D213_BOOT", "D213 preboot, DDR initialization, application loading and licensing", "qualified vendor startup and DDR model"),
    ("FPGA45_RTL", "FPGA45 RTL, SDRAM and graphics command results", "connected RTL co-simulation, not pass-through callbacks"),
    ("FPGA12_RTL", "FPGA12 RTL, PSRAM and per-title job results", "connected RTL co-simulation and exact-package implementation"),
    ("LINK_TIMING", "RGMII setup/hold, skew, queues and cross-clock behavior", "I/O timing constraints and routed interconnect model"),
    ("VIDEO", "D213 display engine, ADV7513, pixel clock and HDMI signaling", "display/peripheral models and output checks"),
    ("INPUT_STORAGE", "Controllers, cartridge storage, removal and reconnect", "drivers executing against device models"),
    ("PCB", "Routed PCB, DRC, schematic parity and manufacturability", "clean routed board and reviewed physical constraints"),
    ("INTEGRATION", "Reset through executable game, first picture and recovery", "whole-chain execution without assumed success callbacks"),
    ("STRESS", "Long runs, timeout/overflow faults and worst-case concurrent workloads", "source-bound integration campaign over all modeled components"),
    ("REVIEW", "Reviewed requirement inventory, acceptance criteria and residual risk", "independent acceptance of models, tests and evidence"),
)


def safe_file(root, relative):
    root = Path(root).resolve()
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError("Missing or unsafe simulation input: " + str(relative))
    return path


def input_hashes(root):
    paths = [Path(p) for p in MODEL_FILES] + [BASE / p for p in HARDWARE_FILES]
    hw = Path(root) / BASE
    for folder in ("fpga45/rtl", "fpga45/tb", "fpga45/constraints", "fpga12/rtl", "fpga12/tb", "fpga12/timing"):
        for path in sorted((hw / folder).glob("*")):
            if path.suffix in (".c", ".h", ".sv", ".v", ".lpf"):
                paths.append(path.relative_to(root))
    return {path.as_posix(): hashlib.sha256(safe_file(root, path).read_bytes()).hexdigest()
            for path in sorted(set(paths))}


def fingerprint(inputs):
    return hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def kernel_module(root):
    path = safe_file(root, MODEL_FILES[0])
    # Import the same local SDK module used by the CLI, without changing sys.path.
    import sys
    name = "arc1_causal_sim"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is not None:
            sys.modules[name] = previous
        else:
            sys.modules.pop(name, None)
    return module


def inspect(root):
    root = Path(root).resolve()
    inputs = input_hashes(root)
    plan = json.loads(safe_file(root, BASE / "board/r10_board_plan.json").read_text())
    by_ref = {c["ref"]: c for c in plan["components"]}
    actors = []
    for name, ref in EXPECTED_ACTORS.items():
        component = by_ref.get(ref)
        actors.append(dict(actor=name, reference=ref, present=component is not None,
                           part=component.get("mpn") if component else None,
                           pins=len(component["pins"]) if component else 0,
                           target_model="NOT_INTEGRATED"))
    if not all(a["present"] for a in actors):
        raise ValueError("R10 actor binding changed; review the simulation map")
    gates = [dict(id=id, requirement=title, status="BLOCKED", needed=needed, critical=True)
             for id, title, needed in GATES]
    latest = None
    report_path = root / "build/console_simulation/campaign.json"
    if report_path.is_file():
        report_path = safe_file(root, "build/console_simulation/campaign.json")
        report = json.loads(report_path.read_text())
        current = report.get("input_hashes") == inputs
        latest = {k: report.get(k) for k in ("experiment_status", "status", "created", "case_counts", "host_firmware")}
        latest["source_current"] = current
        latest["evidence_eligible"] = current
    return dict(schema="arc-ledger.console-simulation/1", board_revision=plan["revision"],
                source_fingerprint=fingerprint(inputs), input_hashes=inputs,
                design_components=len(plan["components"]), design_nets=len(plan["nets"]),
                actors=actors, critical_gates=gates, latest=latest,
                confidence_goal_percent=96, estimated_first_boot_probability=None,
                confidence_goal_met=False, fabrication="HOLD", physical_hardware=False,
                requirement_inventory_reviewed=False,
                metric_policy="96% is the owner's confidence goal; scenario pass rate is not a first-boot probability",
                model_scope="Logical transaction fixture plus actual firmware C on host mocks; no CPU or FPGA execution",
                backends=[
                    dict(name="host C firmware", tool=shutil.which("gcc") or shutil.which("cc") or shutil.which("clang"),
                         scope="actual C coordinator and video orchestration on mocks"),
                    dict(name="RISC-V CPU", tool=shutil.which("qemu-system-riscv64"), status="NOT_INTEGRATED"),
                    dict(name="D213 CPU", tool=shutil.which("qemu-system-riscv64"), status="NOT_INTEGRATED"),
                    dict(name="FPGA RTL", tool=shutil.which("iverilog"), status="NOT_INTEGRATED"),
                    dict(name="Electrical", tool=shutil.which("ngspice"), status="NOT_INTEGRATED"),
                ])


def run_cases(root):
    model = kernel_module(root)
    scenarios = [None, "nor_corrupt", "ddr_fail", "usb_detach", "usb_drop", "usb_corrupt",
                 "usb_truncate", "usb_duplicate", "usb_sequence", "gpu_fail", "memory_corrupt",
                 "sink_absent", "reset_in_flight", "power_loss", "queue_overflow"]
    cases = []
    expected_errors = {
        "nor_corrupt": "NOR_IMAGE_REJECTED", "ddr_fail": "D213_DDR_NOT_READY",
        "usb_detach": "USB_DETACHED", "usb_drop": "REQUEST_TIMEOUT",
        "usb_corrupt": "TRANSFER_INTEGRITY", "usb_truncate": "TRANSFER_INTEGRITY",
        "usb_sequence": "SEQUENCE_MISMATCH", "gpu_fail": "GPU_NOT_READY",
        "memory_corrupt": "TRANSFER_INTEGRITY", "sink_absent": "HDMI_SINK_ABSENT",
        "reset_in_flight": "RESET_ABORTED_REQUEST", "power_loss": "RESET_ABORTED_REQUEST",
    }
    for fault in scenarios:
        outcome = model.ConsoleFixture(fault, explicit_contract=True).run()
        frames, errors = outcome["frames"], outcome["errors"]
        if fault is None:
            passed = len(frames) == 1 and not errors and outcome["pending_requests"] == 0
        elif fault == "reset_in_flight":
            passed = len(frames) == 1 and frames[0]["epoch"] == 1 and bool(errors)
        elif fault == "usb_duplicate":
            passed = len(frames) == 1 and any(e["code"] == "DUPLICATE_DELIVERY" for e in errors)
        elif fault == "queue_overflow":
            passed = len(frames) == 2 and any("queue overflow" in e["code"] for e in errors)
        else:
            passed = not frames and bool(errors)
        if fault in expected_errors:
            passed &= any(e["code"] == expected_errors[fault] for e in errors)
        # Every emitted image is verified independently against its submitted seed.
        for frame in frames:
            seed = (8 if fault == "reset_in_flight" else 7 + frame["request"])
            expected = hashlib.sha256(model.diagnostic_pixels(seed)).hexdigest()
            passed &= frame["sha256"] == expected
        passed &= outcome["pending_requests"] == 0
        cases.append(dict(id=fault or "baseline", status="PASS" if passed else "FAIL", outcome=outcome))
    return cases


def dispatch(kernel, operation, args):
    if operation != "simulation.inspect" or args:
        raise ValueError("simulation.inspect takes no parameters")
    return inspect(kernel.root)
