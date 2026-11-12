"""Source-bound boot experiment inspection; host success never closes boot gates."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .console_simulation import BASE, safe_file, fingerprint

FIELDS = {"boot.inspect": ({}, []), "boot.first_stage.inspect": ({}, [])}
FILES = (
    "sdk/cli/arc1cli/boot_image.py", "sdk/cli/arc1cli/elf_image.py", "workbench/first_stage_tools.py", "tests/test_first_stage.py", "workbench/boot_loading.py", "workbench/boot_tools.py",
    "workbench/simulation_tools.py", "workbench/console_simulation.py",
    "tests/test_boot_loading.py", "software/boot/PROVENANCE.json",
    "tests/test_boot_handoff.py", "sdk/include/arc1/load_bounds.h", "sdk/runtime/boot/load_bounds.c",
    str(BASE / "memory/R10_nor_partition.csv"), str(BASE / "memory/gen_nor_partition.py"),
    str(BASE / "closure_p9/test_host_sequence.c"),
)
DIRECTORIES = (
    "software/boot", str(BASE / "firmware/f133_bootloader"),
    str(BASE / "firmware/host_support"), str(BASE / "firmware/d213_flashless_proof/loader"),
    str(BASE / "firmware/d213_video_diag"), str(BASE / "f133/graphics_link"),
    str(BASE / "d213/fpga45_loader"),
)
GATES = (
    "Exact-silicon ROM/SRAM load limit, boot media and reset entry qualification",
    "F133 startup, stack, linker sections, clocks/reset and board DDR initialization",
    "D213 licensed vendor preboot, DDR initialization and actual USB controller transport",
    "Whole-chain F133/D213 target instruction/peripheral/DDR execution (generic RV64 model is separate)",
    "Recovery and interrupted-power integration against modeled devices and final board",
    "Independent acceptance; physical bring-up, PCB routing and qualification remain open",
)


def input_hashes(root):
    root = Path(root).resolve()
    paths = set(FILES)
    for folder in DIRECTORIES:
        for path in (root/folder).rglob("*"):
            rel = path.relative_to(root)
            if "build" in rel.parts or "__pycache__" in rel.parts:
                continue
            if path.is_file() and (path.suffix in (".c", ".h", ".py", ".S", ".ld", ".json") or path.name in ("Makefile", "COPYING")):
                paths.add(rel.as_posix())
    return {name: hashlib.sha256(safe_file(root,name).read_bytes()).hexdigest() for name in sorted(paths)}


def inspect(root):
    root = Path(root).resolve()
    inputs = input_hashes(root)
    latest = None
    path = root / "build/boot_loading/campaign.json"
    if path.exists() or path.is_symlink():
        report = json.loads(safe_file(root, "build/boot_loading/campaign.json").read_text())
        current = report.get("input_hashes") == inputs
        latest = {k:report.get(k) for k in ("created", "experiment_status", "status", "cases")}
        latest.update(source_current=current, evidence_eligible=current)
    return dict(schema="arc-ledger.boot-loading/1", evidence="STATIC_CHECK", status="BLOCKED",
                input_hashes=inputs, source_fingerprint=fingerprint(inputs), latest=latest,
                critical_gates=[dict(requirement=g,status="BLOCKED") for g in GATES],
                target_cpu_execution=False, target_image_qualified=False, board_boot_qualified=False,
                estimated_first_boot_probability=None, confidence_goal_percent=96,
                confidence_goal_met=False, independent_acceptance=False,
                fabrication="HOLD", flashing="HOLD",
                scope="Minimal eGON format, bounded F133 application copy/read-back, actual host C startup/update behavior and source inventory; no target execution")


def dispatch(kernel, operation, args):
    if operation == "boot.first_stage.inspect" and not args:
        from .first_stage_tools import inspect as stage_inspect
        return stage_inspect(kernel.root)
    if operation != "boot.inspect" or args:
        raise ValueError("boot.inspect takes no parameters")
    return inspect(kernel.root)
