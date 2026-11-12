"""R10 driver/firmware components for the Ledger kernel, CLI and Workbench (PASS-0030).

One registry names each component's canonical source folder, its Make goals and its campaign script. Nothing is
copied: the kernel, `arc1 compact check` and the Workbench all build these same files into the project's build/
area. Host and generic-RV64 runs are HOST_SIM; every physical adapter reports BLOCKED or NOT INSTRUMENTED, and the
target status is always BLOCKED. Nothing here flashes, opens a device or downloads anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

R10 = "hardware/compact-arc1/R10_WORK/"
SDK_INC = "sdk/include/arc1/"
SDK_RT = "sdk/runtime/boot/"

COMPONENTS = {
    "federation_boot": dict(
        label="Portable F133 handoff / Federation contracts", folder=R10+"firmware/f133_bootloader",
        goals=("handoff","handoff-freestanding"), campaign=None,
        shared=(SDK_INC+"boot_info.h",SDK_INC+"load_bounds.h",SDK_INC+"federation.h",
                SDK_RT+"boot_info.c",SDK_RT+"load_bounds.c",SDK_RT+"federation.c",
                "software/boot/f133_app_load.h","software/arcos/bsp/virtual_console/federation_consumer.c",
                "software/arcos/bsp/virtual_console/federation_consumer.h","tests/federation/test_federation.c",
                R10+"firmware/f133_bootloader/src/r10_boot_info.c",R10+"firmware/f133_bootloader/include/r10_boot_info.h",
                R10+"firmware/f133_bootloader/include/r10_boot.h",R10+"firmware/f133_bootloader/include/r10_nor_layout.h",
                R10+"firmware/host_support/include/spi_nor.h",R10+"firmware/host_support/include/ecp5_cfg.h",
                R10+"firmware/host_support/include/arc1_hal.h",R10+"firmware/usb_media/r10_usb_media.c",R10+"firmware/usb_media/r10_usb_media.h"),
        model="Portable C producer/consumer, epoch/version/owned-window guards and USB admission/range failures; physical BSP unavailable"),
    "f133_ehci": dict(
        label="F133 USB0 EHCI0 backend (candidate)", folder=R10 + "firmware/f133_ehci", goals=("test", "sanitize"),
        campaign="tools/ehci29_campaign.py", shared=(SDK_INC + "usb_control.h", SDK_INC + "dma_window.h",
                                                   SDK_RT + "usb_control.c", SDK_RT + "dma_window.c",
                                                   R10 + "firmware/usb_hub/r10_hub.c", R10 + "firmware/usb_hub/r10_hub.h"),
        model="EHCI register, descriptor and non-coherent DMA visibility model (test_ehci.c)"),
    "usb_hub": dict(
        label="USB2514B hub port-power control", folder=R10 + "firmware/usb_hub", goals=("test", "sanitize"),
        campaign="tools/usb28_campaign.py", shared=(SDK_INC + "usb_control.h", SDK_RT + "usb_control.c"),
        model="Scripted USB2 control endpoint (test_hub.c)"),
    "power_control": dict(
        label="Power admission and staged load control", folder=R10 + "firmware/power_control",
        goals=("test", "sanitize"), campaign="tools/power27_campaign.py",
        shared=(SDK_INC + "power_budget.h", SDK_RT + "power_budget.c"),
        model="Synthetic source, rail and load observations (test_power.c)"),
    "d213_loader": dict(
        label="D213 flashless start coordinator", folder=R10 + "firmware/d213_flashless_proof/loader",
        goals=("test", "freestanding"), campaign=None, shared=(),
        model="Host model of the D213 start sequence (test_r10_d213_start.c)"),
    "d213_video_diag": dict(
        label="D213 first-light video diagnostics", folder=R10 + "firmware/d213_video_diag",
        goals=("test", "freestanding"), campaign=None, shared=(),
        model="Simulated I2C and framebuffer for the display engine and ADV7513 start (test_r10_video.c)"),
    "f133_board_diag": dict(
        label="F133 board diagnostics", folder=R10 + "firmware/f133_board_diag",
        goals=("test", "freestanding"), campaign=None, shared=(),
        model="Host callbacks standing in for F133 MMIO, clock and pin probes (test_r10_f133_diag.c)"),
}
SOURCE_SUFFIXES = (".c", ".h", ".S", ".ld", ".json", ".md")
PHYSICAL = "NOT INSTRUMENTED"


def _safe(root, rel):
    root = Path(root).resolve()
    path = root / rel
    if any(p.is_symlink() for p in [path, *path.parents] if p == root or root in p.parents):
        raise ValueError("symlink in firmware path: " + str(rel))
    if not path.resolve().is_relative_to(root):
        raise ValueError("path escapes the project: " + str(rel))
    return path


def sources(root, cid):
    """Canonical source files of one component (its folder plus the shared SDK/driver files it compiles)."""
    c = COMPONENTS[cid]
    folder = _safe(root, c["folder"])
    if not folder.is_dir():
        raise ValueError("firmware source folder missing: " + c["folder"])
    names = sorted(p.relative_to(Path(root).resolve()).as_posix() for p in folder.iterdir()
                   if p.is_file() and not p.is_symlink() and (p.suffix in SOURCE_SUFFIXES or p.name == "Makefile"))
    return names + [s for s in c["shared"] if s not in names]


def source_hashes(root, cid):
    return {name: hashlib.sha256(_safe(root, name).read_bytes()).hexdigest() for name in sources(root, cid)}


def adapters(root, cid):
    """What each layer actually is: the test model is SIMULATED, every physical layer is BLOCKED/NOT INSTRUMENTED."""
    c = COMPONENTS[cid]
    rows = [dict(name="test model", status="SIMULATED", detail=c["model"])]
    q = _safe(root, c["folder"] + "/qualification.json")
    if q.is_file():
        for key, value in json.loads(q.read_text()).items():
            if value == "NOT_AVAILABLE" or (value is False and key.startswith(("actual_", "physical_"))):
                rows.append(dict(name=key, status="BLOCKED", detail="adapter not implemented or not qualified"))
            elif value is None or (isinstance(value, dict) and value and all(v is None for v in value.values())):
                rows.append(dict(name=key, status=PHYSICAL, detail="target value unknown (null)"))
    else:
        rows.append(dict(name="target adapters", status="BLOCKED", detail="no qualification profile recorded"))
    rows.append(dict(name="physical board", status=PHYSICAL, detail="no ARC-1 board exists; nothing is flashed"))
    return rows


def report_path(root, cid):
    return _safe(root, "build/firmware/%s/campaign.json" % cid)


def inspect(root, cid=None):
    root = Path(root).resolve()
    out = []
    for name in ([cid] if cid else COMPONENTS):
        if name not in COMPONENTS:
            raise ValueError("unknown firmware component: " + str(name))
        c = COMPONENTS[name]
        hashes = source_hashes(root, name)
        latest = None
        path = report_path(root, name)
        if path.is_file():
            r = json.loads(path.read_text())
            latest = {k: r.get(k) for k in ("created", "experiment_status", "target_status", "rv64")}
            latest["source_current"] = r.get("source_hashes") == hashes
        out.append(dict(id=name, label=c["label"], folder=c["folder"], make_goals=list(c["goals"]),
                        campaign=c["campaign"], sources=[dict(path=k, sha256=v) for k, v in hashes.items()],
                        adapters=adapters(root, name), latest=latest, target_status="BLOCKED"))
    return dict(schema="arc-ledger.firmware-inventory/1", evidence="STATIC_CHECK", components=out,
                target_status="BLOCKED", physical=PHYSICAL, fabrication="HOLD", flashing="HOLD")


def rv64_tools():
    names = ("riscv64-unknown-elf-gcc", "riscv64-unknown-elf-objcopy", "qemu-system-riscv64")
    found = {n: shutil.which(n) for n in names}
    return found, [n for n, p in found.items() if not p]


def campaign(root, cid, rv64="auto"):
    root = Path(root).resolve()
    if cid not in COMPONENTS:
        raise ValueError("unknown firmware component: " + str(cid))
    c = COMPONENTS[cid]
    started = time.time()
    before = source_hashes(root, cid)
    area = _safe(root, "build/firmware/" + cid)
    if area.exists():
        if any(p.is_symlink() for p in area.rglob("*")):
            raise ValueError("firmware build area must not contain symlinks")
        shutil.rmtree(area)
    area.mkdir(parents=True)
    commands, cases = [], []

    def run(case_id, argv, cwd=root, timeout=300):
        p = subprocess.run([str(a) for a in argv], cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        commands.append(dict(id=case_id, argv=[str(a) for a in argv], cwd=str(cwd), exit_status=p.returncode,
                             stdout=p.stdout[-20000:], stderr=p.stderr[-10000:]))
        cases.append(dict(id=case_id, status="PASS" if p.returncode == 0 else "FAIL", evidence="HOST_SIM"))
        return p

    make = shutil.which("make")
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not make or not cc:
        cases.append(dict(id="host-toolchain", status="BLOCKED", reason="host C compiler and make required"))
    else:
        for goal in c["goals"]:
            run("make-" + goal, [make, "-f", _safe(root, c["folder"] + "/Makefile"), goal, "CC=" + cc,
                                 "OUT=" + str(area / "make")], cwd=_safe(root, c["folder"]))
    use_rv64 = False
    if c["campaign"]:
        found, missing = rv64_tools()
        use_rv64 = rv64 == "yes" or (rv64 == "auto" and not missing)
        if rv64 == "auto" and missing:
            cases.append(dict(id="rv64", status="NOT_RUN", reason="optional generic RV64 tools missing: " + ", ".join(missing)))
        argv = [sys.executable, "-I", _safe(root, c["campaign"]), "--output", area / "campaign"]
        p = run("campaign", argv + (["--rv64"] if use_rv64 else []), timeout=500)
        detail = area / "campaign/campaign.json"
        if detail.is_file():
            inner = json.loads(detail.read_text())
            for case in inner.get("cases", []):
                cases.append(dict(id="campaign:" + str(case.get("id")), status=case.get("status", "FAIL"),
                                  evidence=case.get("evidence", "HOST_SIM")))
            if inner.get("experiment_status") != "PASS" and p.returncode == 0:
                cases.append(dict(id="campaign-status", status="FAIL", reason="campaign did not report PASS"))
    status = ("FAIL" if any(x["status"] == "FAIL" for x in cases)
              else "BLOCKED" if any(x["status"] == "BLOCKED" for x in cases) else "PASS")
    if source_hashes(root, cid) != before:
        status = "FAIL"
        cases.append(dict(id="source-drift", status="FAIL", reason="sources changed during the campaign"))
    report = dict(schema="arc-ledger.firmware-campaign/1", component=cid, label=c["label"], created=started,
                  evidence="HOST_SIM", experiment_status=status, status=status, target_status="BLOCKED",
                  rv64=use_rv64, source_hashes=before, adapters=adapters(root, cid), cases=cases, commands=commands,
                  physical=PHYSICAL, fabrication="HOLD", flashing="HOLD",
                  scope="Host (and generic QEMU RV64 where available) execution of the canonical sources; "
                        "not F133/D213 silicon, PHY, DMA or electrical behaviour")
    report_path(root, cid).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(component=cid, experiment_status=status, target_status="BLOCKED", rv64=use_rv64,
                          report="build/firmware/%s/campaign.json" % cid,
                          failed=[x["id"] for x in cases if x["status"] != "PASS"]), indent=2))
    return 1 if status == "FAIL" else 3 if status == "BLOCKED" else 0


FIELDS = {"firmware.inspect": ({"component": {"type": "string", "enum": sorted(COMPONENTS)}}, [])}


def dispatch(kernel, operation, args):
    if operation != "firmware.inspect":
        raise ValueError("unknown firmware operation")
    args = args or {}
    if set(args) - {"component"}:
        raise ValueError("firmware.inspect takes only 'component'")
    return inspect(kernel.root, args.get("component"))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    for action in ("inspect", "campaign"):
        s = sub.add_parser(action)
        s.add_argument("--root", type=Path, default=Path.cwd())
        s.add_argument("--component", choices=sorted(COMPONENTS), required=action == "campaign")
        if action == "campaign":
            s.add_argument("--rv64", choices=("auto", "yes", "no"), default="auto")
    a = p.parse_args(argv)
    try:
        if a.action == "inspect":
            print(json.dumps(inspect(a.root, a.component), indent=2))
            return 0
        return campaign(a.root, a.component, a.rv64)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps(dict(status="FAIL", reason=str(exc), fabrication="HOLD", flashing="HOLD")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
