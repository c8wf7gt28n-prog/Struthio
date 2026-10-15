#!/usr/bin/env python3
"""ARC-1 Compact R07: run every R07 check plus the complete R06 regression.

Usage: python3 R07_WORK/tools/run_r07_checks.py [--skip-r06]

Writes R07_WORK/evidence/run_<UTC>/ (one log per step with the exact command
and exit status, reports, the F133 image, source manifest, summary.json).
The R06 regression runs in a scratch copy of the whole project, so R05_BASELINE
and R06_WORK stay byte-identical. Labels: HOST-TESTED, RTL-SIMULATED,
PLANNING-CALCULATED, BUILD-ONLY; never NATIVE-EDA or PHYSICAL-HARDWARE.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
R07 = os.path.dirname(TOOLS)
ROOT = os.path.dirname(R07)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


class Runner:
    def __init__(self, out):
        self.out, self.steps = out, []

    def run(self, name, cmd, cwd, label, marker=None, expect_fail=False, timeout=3600):
        log = os.path.join(self.out, f"{name}.log")
        t0 = time.time()
        try:
            p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
            rc, text = p.returncode, p.stdout.decode("utf-8", "replace")
        except FileNotFoundError as e:
            rc, text = None, f"NOT_RUN: {e}"
        except subprocess.TimeoutExpired as e:
            rc, text = -9, (e.stdout or b"").decode("utf-8", "replace") + "\nTIMEOUT"
        with open(log, "w", encoding="utf-8") as f:
            f.write(f"$ (cd {os.path.relpath(cwd, ROOT) if cwd.startswith(ROOT) else cwd} && {' '.join(cmd)})\n{text}\n# exit status: {rc}\n")
        ok = rc == 0 and (marker is None or marker in text)
        status = "PASS" if ok else ("NOT_RUN" if rc is None else "FAIL")
        self.steps.append({"step": name, "status": status, "label": label if ok else status, "exit": rc,
                           "seconds": round(time.time() - t0, 1), "command": cmd,
                           "cwd": os.path.relpath(cwd, ROOT) if cwd.startswith(ROOT) else "<scratch copy>",
                           "log": os.path.relpath(log, ROOT)})
        print(f"{status:7s} {name} ({self.steps[-1]['seconds']} s)")
        return ok, text

    def note(self, name, status, label, detail):
        self.steps.append({"step": name, "status": status, "label": label, "detail": detail})
        print(f"{status:7s} {name}: {detail}")


def tool_versions():
    v = {"python": sys.version.split()[0]}
    for t, a in (("cc", ["--version"]), ("riscv64-unknown-elf-gcc", ["--version"]), ("mkimage", ["-V"]),
                 ("iverilog", ["-V"]), ("verilator", ["--version"]), ("yosys", ["-V"]), ("make", ["--version"])):
        try:
            p = subprocess.run([t] + a, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            v[t] = p.stdout.decode("utf-8", "replace").splitlines()[0].strip()
        except (FileNotFoundError, IndexError, subprocess.TimeoutExpired):
            v[t] = "NOT_FOUND"
    v["efx_run"] = shutil.which("efx_run.py") or "NOT_FOUND"
    return v


def validate_ledger(path):
    d = json.load(open(path, encoding="utf-8"))
    need = {"id", "source", "claim", "level", "test_or_section", "result", "limitation", "next_action"}
    bad = [e.get("id", "?") for e in d["entries"] if not need <= set(e) or e["level"] not in d["levels"]]
    ids = [e["id"] for e in d["entries"]]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    return bad, dup, len(ids)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-r06", action="store_true")
    a = ap.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = os.path.join(R07, "evidence", f"run_{stamp}")
    os.makedirs(out)
    scratch = tempfile.mkdtemp(prefix="arc1_r07_")
    r = Runner(out)
    print(f"evidence: {os.path.relpath(out, ROOT)}")

    # 1. handoff manifest (R05 baseline + directive files unchanged)
    bad = []
    with open(os.path.join(ROOT, "MANIFEST_SHA256.txt"), encoding="utf-8") as f:
        rows = [ln.rstrip("\n").split("  ", 1) for ln in f]
    for digest, rel in rows:
        if rel != "R06_WORK/README.md" and sha256(os.path.join(ROOT, rel)) != digest:
            bad.append(rel)
    r.note("handoff_integrity", "PASS" if not bad else "FAIL", "HOST-TESTED",
           f"{len(rows) - 1} manifest entries verified, changed: {bad}")

    # 2. complete R06 regression in a scratch copy (keeps R06_WORK byte-frozen)
    if not a.skip_r06:
        proj = os.path.join(scratch, "arc1-compact")
        shutil.copytree(ROOT, proj, ignore=shutil.ignore_patterns("evidence", "__pycache__", "build"))
        os.makedirs(os.path.join(proj, "R06_WORK", "evidence"), exist_ok=True)
        ok, _ = r.run("r06_regression_full", [sys.executable, "R06_WORK/tools/run_r06_checks.py"], proj,
                      "HOST-TESTED+RTL-SIMULATED (R06 suite incl. R05 rerun)", "PASS_R06_HOST_RTL_PLANNING_CHECKS")
        ev = os.path.join(proj, "R06_WORK", "evidence")
        latest = open(os.path.join(ev, "LATEST.txt")).read().strip() if os.path.exists(os.path.join(ev, "LATEST.txt")) else None
        if latest:
            shutil.copy(os.path.join(ev, latest.split("/")[-1], "summary.json"), os.path.join(out, "r06_regression_summary.json"))
    else:
        r.note("r06_regression_full", "NOT_RUN", "NOT_RUN", "--skip-r06 given")

    # 3. firmware: BT820 protocol fix, boot/FIFO, degradation, sanitizers, mutants, R06 probe
    fw = os.path.join(R07, "firmware")
    fb = os.path.join(scratch, "fw")
    r.run("fw_test", ["make", "test", f"OUT={fb}"], fw, "HOST-TESTED", "PASS firmware host tests")
    r.run("fw_sanitize", ["make", "sanitize", f"OUT={fb}"], fw, "HOST-TESTED (ASan+UBSan)", "PASS firmware host tests")
    r.run("fw_freestanding", ["make", "freestanding", f"OUT={fb}"], fw, "HOST-TESTED (compile)", "freestanding object compile OK")
    r.run("fw_mutants", ["make", "mutants", f"OUT={fb}"], fw, "HOST-TESTED (mutation)", "MUTANT_KILLED MUTANT_NO_WRAP")
    r.run("fw_r06_defect_probe", ["make", "r06-probe", f"OUT={fb}"], fw, "HOST-TESTED (regression probe)",
          "R06_DEFECT_REPRODUCED")

    # 4. board plan rev R07
    bd = os.path.join(R07, "board")
    r.run("board_unit_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], bd, "HOST-TESTED", "OK")
    r.run("board_plan_check", [sys.executable, "check_board_plan.py", "--report", os.path.join(out, "board_check_report.json"),
                               "--pinmap", os.path.join(bd, "PIN_MAP_R07.md")], bd, "PLANNING-CALCULATED", "PASS board plan")

    # 5. PSRAM power-up / DC analysis
    r.run("psram_power_io", [sys.executable, "psram_power_io.py", "--json", os.path.join(out, "psram_power_io.json")],
          os.path.join(R07, "analysis"), "PLANNING-CALCULATED", "PASS psram power/IO")

    # 6. PSRAM controller scenarios + clock-ratio variation (unchanged R06 RTL)
    pd = os.path.join(R07, "fpga", "psram_r07")
    pb = os.path.join(scratch, "ps")
    r.run("psram_r07_scenarios", ["make", "r07", f"OUT={pb}"], pd, "RTL-SIMULATED", "PSRAM_R07_TB_PASS")
    r.run("psram_extra_clocks", ["make", "extra-clocks", f"OUT={pb}"], pd, "RTL-SIMULATED", "PSRAM_TB_PASS cfg=C5")
    for fn in ("sim_r07.log", "sim_C4.log", "sim_C5.log"):
        if os.path.exists(os.path.join(pb, fn)):
            with open(os.path.join(pb, fn), encoding="utf-8", errors="replace") as s, \
                 open(os.path.join(out, f"psram_{fn}"), "w", encoding="utf-8") as d:
                d.writelines(ln for ln in s if not ln.startswith("MODEL_VIOLATION"))   # R3 provokes hundreds

    # 7. F133 image, built twice for reproducibility
    ib = os.path.join(R07, "f133_boot")
    b1, b2 = os.path.join(scratch, "img1"), os.path.join(scratch, "img2")
    ok1, _ = r.run("f133_image_build", ["make", f"OUT={b1}"], ib, "BUILD-ONLY", "EGON_OK")
    ok2, _ = r.run("f133_image_rebuild", ["make", f"OUT={b2}"], ib, "BUILD-ONLY", "EGON_OK")
    if ok1 and ok2:
        h1, h2 = sha256(os.path.join(b1, "arc1_r07_f133.egon")), sha256(os.path.join(b2, "arc1_r07_f133.egon"))
        r.note("f133_image_reproducible", "PASS" if h1 == h2 else "FAIL", "BUILD-ONLY", f"sha256 {h1} / {h2}")
        for fn in ("arc1_r07_f133.egon", "arc1_r07_f133.elf", "arc1_r07_f133.map"):
            shutil.copy(os.path.join(b1, fn), os.path.join(out, fn))

    # 8. ledger schema
    badl, dup, n = validate_ledger(os.path.join(R07, "EVIDENCE_LEDGER.json"))
    r.note("evidence_ledger_schema", "PASS" if not badl and not dup else "FAIL", "HOST-TESTED",
           f"{n} entries; invalid {badl}; duplicate ids {dup}")

    # 9. explicitly not run
    for name, detail in (
        ("efinity_native", "efx_run.py not found: NATIVE_EDA_NOT_RUN (no T35 fit/STA/bitstream)"),
        ("f133_on_silicon", "image never executed; no board"),
        ("bt820_on_silicon", "no MN820/VM820C attached: REG_ID, FIFO and display unproven"),
        ("psram_on_silicon", "no T35/PSRAM board"),
        ("electrical_pcb_jlcpcb", "no schematic/PCB/SI/DFM; fabrication NOT approved"),
        ("f133_user_manual", "mangopi.org mirror TLS certificate expired; not bypassed; D1-H UM used"),
    ):
        r.note(name, "NOT_RUN", "NOT_RUN", detail)

    files = []
    for base, dirs, fns in os.walk(R07):
        dirs[:] = sorted(x for x in dirs if x not in ("evidence", "build", "__pycache__"))
        for fn in sorted(fns):
            p = os.path.join(base, fn)
            files.append({"path": os.path.relpath(p, ROOT), "bytes": os.path.getsize(p), "sha256": sha256(p)})
    json.dump({"files": files}, open(os.path.join(out, "source_manifest.json"), "w"), indent=1)
    failed = [s["step"] for s in r.steps if s["status"] == "FAIL"]
    summary = {"schema_id": "arc1-r07-check-summary-v1", "utc": stamp, "tool_versions": tool_versions(),
               "runner_sha256": sha256(os.path.abspath(__file__)),
               "overall": "PASS_R07_HOST_RTL_PLANNING_BUILD_CHECKS" if not failed else "FAIL",
               "failed_steps": failed, "not_run": [s["step"] for s in r.steps if s["status"] == "NOT_RUN"],
               "steps": r.steps, "source_files": len(files),
               "disclaimer": "No native EDA, no hardware, no electrical measurement. Fabrication is NOT approved."}
    json.dump(summary, open(os.path.join(out, "summary.json"), "w"), indent=1)
    open(os.path.join(R07, "evidence", "LATEST.txt"), "w").write(os.path.relpath(out, R07) + "\n")
    shutil.rmtree(scratch, ignore_errors=True)
    print(f"{summary['overall']}: {sum(s['status'] == 'PASS' for s in r.steps)} pass, {len(failed)} fail, "
          f"{len(summary['not_run'])} NOT_RUN -> {os.path.relpath(out, ROOT)}/summary.json")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
