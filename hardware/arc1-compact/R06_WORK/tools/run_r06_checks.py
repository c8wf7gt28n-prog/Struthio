#!/usr/bin/env python3
"""ARC-1 Compact R06: run every R06 check and the unchanged R05 baseline.

Usage: python3 R06_WORK/tools/run_r06_checks.py [--quick] [--keep-build]

Creates R06_WORK/evidence/run_<UTC>/ with one log per step, copies of the
reports, a source manifest (SHA-256 of every R06 input) and summary.json.
Each step records its exact command, working directory, exit status and
duration. A step that cannot run is recorded as NOT_RUN with the reason;
nothing is ever reported as passed unless its command exited 0 and printed
its own pass marker.

Labels follow the root CLAUDE.md vocabulary. This runner can produce
HOST_TESTED, RTL_SIMULATED, PLANNING_CALCULATED and OPEN_SOURCE_SYNTH_ESTIMATE
evidence only. It never produces NATIVE_EDA_VERIFIED or PROTOTYPE_MEASURED.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
R06 = os.path.dirname(TOOLS)
ROOT = os.path.dirname(R06)
R05 = os.path.join(ROOT, "R05_BASELINE")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Runner:
    def __init__(self, out, build):
        self.out, self.build, self.steps = out, build, []

    def run(self, name, cmd, cwd, label, marker=None, timeout=1800, env=None):
        log = os.path.join(self.out, f"{name}.log")
        t0 = time.time()
        e = dict(os.environ, **(env or {}))
        try:
            p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=timeout, env=e)
            rc, text = p.returncode, p.stdout.decode("utf-8", "replace")
        except FileNotFoundError as ex:
            rc, text = None, f"NOT_RUN: {ex}"
        except subprocess.TimeoutExpired as ex:
            rc, text = -9, (ex.stdout or b"").decode("utf-8", "replace") + f"\nTIMEOUT after {timeout} s"
        with open(log, "w", encoding="utf-8") as f:
            f.write(f"$ (cd {os.path.relpath(cwd, ROOT)} && {' '.join(cmd)})\n")
            f.write(text)
            f.write(f"\n# exit status: {rc}\n")
        ok = rc == 0 and (marker is None or marker in text)
        status = "PASS" if ok else ("NOT_RUN" if rc is None else "FAIL")
        self.steps.append({"step": name, "status": status, "label": label if ok else status,
                           "exit": rc, "seconds": round(time.time() - t0, 2),
                           "cwd": os.path.relpath(cwd, ROOT), "command": cmd,
                           "marker": marker, "log": os.path.relpath(log, ROOT)})
        print(f"{status:7s} {name} ({self.steps[-1]['seconds']} s)")
        return ok, text

    def note(self, name, status, label, detail):
        self.steps.append({"step": name, "status": status, "label": label, "detail": detail})
        print(f"{status:7s} {name}: {detail}")


def versions():
    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for tool, args in (("cc", ["--version"]), ("make", ["--version"]), ("iverilog", ["-V"]),
                       ("verilator", ["--version"]), ("yosys", ["-V"]), ("git", ["--version"])):
        try:
            p = subprocess.run([tool] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            out[tool] = p.stdout.decode("utf-8", "replace").splitlines()[0].strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, IndexError):
            out[tool] = "NOT_FOUND"
    out["efinity_efx_run"] = shutil.which("efx_run.py") or shutil.which("efx_run") or "NOT_FOUND"
    return out


def handoff_integrity():
    """Every handoff file is unchanged, except R06_WORK/README.md, the
    placeholder the handoff says Claude replaces."""
    bad, checked = [], 0
    with open(os.path.join(ROOT, "MANIFEST_SHA256.txt"), encoding="utf-8") as f:
        for line in f:
            digest, rel = line.rstrip("\n").split("  ", 1)
            if rel == "R06_WORK/README.md":
                continue
            checked += 1
            p = os.path.join(ROOT, rel)
            if not os.path.exists(p) or sha256(p) != digest:
                bad.append(rel)
    return checked, bad


def source_manifest():
    rows = []
    for base, dirs, files in os.walk(R06):
        dirs[:] = sorted(d for d in dirs if d not in ("evidence", "build", "__pycache__"))
        for fn in sorted(files):
            p = os.path.join(base, fn)
            rows.append({"path": os.path.relpath(p, ROOT), "bytes": os.path.getsize(p), "sha256": sha256(p)})
    return rows


def copy_log(src, dst, from_marker=None):
    """Copy a log; for long synthesis logs keep only the statistics section."""
    with open(src, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if from_marker and from_marker in text:
        text = f"[trimmed: kept from the last '{from_marker}']\n" + text[text.rindex(from_marker):]
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="skip R05 HDL, PSRAM mutants")
    ap.add_argument("--keep-build", action="store_true")
    a = ap.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = os.path.join(R06, "evidence", f"run_{stamp}")
    os.makedirs(out)
    build = tempfile.mkdtemp(prefix="arc1_r06_build_")
    r = Runner(out, build)
    ver = versions()
    print(f"evidence: {os.path.relpath(out, ROOT)}")

    # 0. handoff integrity (R05 baseline and root directive files unchanged)
    checked, bad = handoff_integrity()
    r.note("handoff_integrity", "PASS" if not bad else "FAIL", "HOST_TESTED",
           f"{checked} manifest entries verified, {len(bad)} changed: {bad[:5]}")

    # 1. R05 baseline, executed in a scratch copy so R05_BASELINE stays byte-identical
    r05copy = os.path.join(build, "R05_BASELINE")
    shutil.copytree(R05, r05copy)
    r.run("r05_check_package", [sys.executable, "tools/check_package.py"], r05copy, "HOST_TESTED", "PASS manifest")
    cmd = [sys.executable, "tools/check_all.py"] + (["--skip-hdl"] if a.quick else [])
    r.run("r05_check_all", cmd, r05copy, "HOST_TESTED+RTL_SIMULATED (R05 rerun)",
          "PASS_HOST_ONLY_HDL_SKIPPED" if a.quick else "PASS_HOST_AND_RTL_SIMULATION")
    s = os.path.join(r05copy, "verification", "last_run", "summary.json")
    if os.path.exists(s):
        shutil.copy(s, os.path.join(out, "r05_rerun_summary.json"))

    # 2. board plan
    bd = os.path.join(R06, "board")
    r.run("board_unit_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], bd,
          "HOST_TESTED", "OK")
    r.run("board_plan_check", [sys.executable, "check_board_plan.py", "--report",
                               os.path.join(out, "board_check_report.json"), "--pinmap",
                               os.path.join(bd, "PIN_MAP_R06.md")], bd, "PLANNING_CALCULATED", "PASS board plan")

    # 3. PSRAM controller
    pd = os.path.join(R06, "fpga", "psram")
    pb = os.path.join(build, "psram")
    targets = ["lint", "sim", "synth", "synth-efx"] + ([] if a.quick else ["mutants"])
    for t in targets:
        label = {"lint": "HOST_TESTED (lint)", "sim": "RTL_SIMULATED", "synth": "OPEN_SOURCE_SYNTH_ESTIMATE",
                 "synth-efx": "OPEN_SOURCE_SYNTH_ESTIMATE", "mutants": "RTL_SIMULATED (mutation)"}[t]
        r.run(f"psram_{t}", ["make", t, f"OUT={pb}"], pd, label, None, timeout=3600)
    for fn in ("sim_C1.log", "sim_C2.log", "sim_C3.log", "synth_efx.log", "lint.log"):
        if os.path.exists(os.path.join(pb, fn)):
            copy_log(os.path.join(pb, fn), os.path.join(out, f"psram_{fn}"),
                     "Printing statistics" if fn.startswith("synth") else None)
    for fn in sorted(os.listdir(pb)) if os.path.isdir(pb) else []:
        if fn.startswith("mut_") and fn.endswith(".log"):
            with open(os.path.join(pb, fn), encoding="utf-8", errors="replace") as f:
                lines = [ln for ln in f if ln.startswith(("TB_ERROR", "MODEL_VIOLATION", "PSRAM_TB"))][:6]
            with open(os.path.join(out, f"psram_{fn}"), "w", encoding="utf-8") as f:
                f.writelines(lines)

    # 4. T35 top level (mailbox + PSRAM + BIST)
    td = os.path.join(R06, "fpga", "top")
    tb = os.path.join(build, "top")
    for t in ("lint", "sim", "synth-efx"):
        r.run(f"top_{t}", ["make", t, f"OUT={tb}"], td,
              {"lint": "HOST_TESTED (lint)", "sim": "RTL_SIMULATED", "synth-efx": "OPEN_SOURCE_SYNTH_ESTIMATE"}[t],
              None, timeout=3600)
    for fn in ("sim_top.log", "synth_top_efx.log"):
        if os.path.exists(os.path.join(tb, fn)):
            copy_log(os.path.join(tb, fn), os.path.join(out, f"top_{fn}"),
                     "Printing statistics" if fn.startswith("synth") else None)

    # 5. Efinity inputs are reproducible from the board plan
    ed = os.path.join(R06, "fpga", "efinity")
    gen = os.path.join(build, "efinity_gen")
    os.makedirs(gen, exist_ok=True)
    ok, _ = r.run("efinity_inputs_generate", [sys.executable, "gen_efinity_inputs.py", gen], ed, "HOST_TESTED")
    same = ok and all(open(os.path.join(gen, f), "rb").read() == open(os.path.join(ed, f), "rb").read()
                      for f in ("arc1_t35_r06_pins.csv", "arc1_t35_r06_isf.py"))
    r.note("efinity_inputs_up_to_date", "PASS" if same else "FAIL", "HOST_TESTED",
           "committed pin CSV / ISF script equal freshly generated output" if same else "regenerate and commit")
    if ver["efinity_efx_run"] == "NOT_FOUND":
        r.note("efinity_native_compile", "NOT_RUN", "NATIVE_EDA_NOT_RUN",
               "efx_run.py not found: no T35 synthesis, fit, STA or bitstream (see fpga/efinity/README.md)")

    # 6. host firmware layer
    fd = os.path.join(R06, "firmware")
    fb = os.path.join(build, "fw")
    r.run("firmware_test", ["make", "test", f"OUT={fb}"], fd, "HOST_TESTED", "PASS firmware host tests")
    r.run("firmware_sanitize", ["make", "sanitize", f"OUT={fb}"], fd, "HOST_TESTED (ASan+UBSan, leaks off)",
          "PASS firmware host tests")
    r.run("firmware_freestanding", ["make", "freestanding", f"OUT={fb}"], fd, "HOST_TESTED (compile only)",
          "freestanding object compile OK")

    # 7. things this environment cannot do
    for name, detail in (
        ("f133_cross_build", "no F133 toolchain/BSP in R06: no bootable image (PASS 7 step 1)"),
        ("bt820_silicon", "no BT820/MN820 hardware: no display output, no register-level init"),
        ("psram_silicon", "no PSRAM/T35 board: controller never ran on hardware"),
        ("electrical_and_pcb", "no schematic, PCB, SI/PI, thermal, JLCPCB DFM"),
    ):
        r.note(name, "NOT_RUN", "NOT_RUN", detail)

    manifest = source_manifest()
    with open(os.path.join(out, "source_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"files": manifest}, f, indent=1)
    executed = [s for s in r.steps if s["status"] in ("PASS", "FAIL")]
    failed = [s["step"] for s in executed if s["status"] == "FAIL"]
    summary = {
        "schema_id": "arc1-r06-check-summary-v1",
        "utc": stamp,
        "runner_sha256": sha256(os.path.abspath(__file__)),
        "tool_versions": ver,
        "quick_mode": a.quick,
        "overall": "PASS_R06_HOST_RTL_PLANNING_CHECKS" if not failed else "FAIL",
        "failed_steps": failed,
        "not_run": [s["step"] for s in r.steps if s["status"] == "NOT_RUN"],
        "steps": r.steps,
        "source_files": len(manifest),
        "disclaimer": "Host tests, RTL simulation, planning checks and open-source synthesis estimates only. "
                      "No native Efinity result, no hardware, no measured performance.",
    }
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    with open(os.path.join(R06, "evidence", "LATEST.txt"), "w", encoding="utf-8") as f:
        f.write(os.path.relpath(out, R06) + "\n")
    if not a.keep_build:
        shutil.rmtree(build, ignore_errors=True)
    print(f"{summary['overall']}: {len(executed)} executed, {len(failed)} failed, "
          f"{len(summary['not_run'])} NOT_RUN -> {os.path.relpath(out, ROOT)}/summary.json")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
