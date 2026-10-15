#!/usr/bin/env python3
"""ARC-1 Compact R08 -- one command for every R08 check plus the R07 (and nested R06) regression.

    python3 R08_WORK/tools/run_r08_checks.py              # everything (~10 min, R07+R06 regression included)
    python3 R08_WORK/tools/run_r08_checks.py --skip-r07   # R08 steps only

Run from hardware/arc1-compact/. Writes R08_WORK/evidence/run_<UTC>/ (one log per step with the
exact command, cwd and exit code, plus summary.json) and updates R08_WORK/evidence/LATEST.txt.
Frozen inputs (R05_BASELINE, R06_WORK, R07_WORK, root handoff files) are verified unchanged and
the R07 regression runs in a scratch copy so no prior evidence is touched.
Environment: SLIM4_PRETTY = SLIM4 R26 SLIM4.pretty dir (only needed to regenerate the 3 copied
footprints; without it the committed copies are used), FROZEN_BASE = git rev of the R07 commit.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
R08 = os.path.join(ROOT, "R08_WORK")
FROZEN_BASE = os.environ.get("FROZEN_BASE", "1262c1a")
steps = []


def log_path(ev, name):
    return os.path.join(ev, name + ".log")


def run(ev, name, cmd, cwd, expect=0, timeout=3600, env=None):
    t0 = time.time()
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout, env=e)
        out, rc = p.stdout.decode(errors="replace"), p.returncode
    except subprocess.TimeoutExpired as ex:
        out, rc = (ex.stdout or b"").decode(errors="replace") + "\nTIMEOUT", -9
    dt = time.time() - t0
    with open(log_path(ev, name), "w") as fh:
        fh.write(f"$ {cmd if isinstance(cmd, str) else ' '.join(cmd)}\n# cwd: {os.path.relpath(cwd, ROOT)}\n# exit: {rc}\n\n{out}")
    status = "PASS" if rc == expect else "FAIL"
    steps.append({"step": name, "status": status, "exit": rc, "seconds": round(dt, 1),
                  "cmd": cmd if isinstance(cmd, str) else " ".join(cmd), "cwd": os.path.relpath(cwd, ROOT)})
    print(f"{status:7} {name} ({dt:.1f} s)")
    return status == "PASS", out


def note(name, status, detail):
    steps.append({"step": name, "status": status, "detail": detail})
    print(f"{status:7} {name}: {detail}")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tree_digest(d, exclude=()):
    out = {}
    for base, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x not in ("build", "__pycache__")]
        for f in files:
            p = os.path.join(base, f)
            r = os.path.relpath(p, d)
            if not any(r.startswith(x) for x in exclude):
                out[r] = sha(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-r07", action="store_true")
    a = ap.parse_args()
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ev = os.path.join(R08, "evidence", f"run_{ts}")
    os.makedirs(ev)
    print("evidence:", os.path.relpath(ev, ROOT))

    # ---------- frozen inputs ----------
    man = os.path.join(ROOT, "MANIFEST_SHA256.txt")
    bad = []
    n = 0
    for line in open(man):
        if not line.strip() or line.startswith("#"):
            continue
        h, f = line.split(None, 1)
        f = f.strip().lstrip("*")
        n += 1
        if f == "R06_WORK/README.md":      # the one intended R06 edit (same exemption as the R07 runner);
            continue                       # its R07-era content is still pinned by the git check below
        if not os.path.exists(os.path.join(ROOT, f)) or sha(os.path.join(ROOT, f)) != h:
            bad.append(f)
    note("handoff_integrity", "PASS" if not bad else "FAIL",
         f"{n} manifest entries (R06_WORK/README.md exempt as in R07), changed: {bad[:5]}")
    run(ev, "frozen_r05_r06_r07_unchanged",
        f"git diff --quiet {FROZEN_BASE} -- R05_BASELINE R06_WORK R07_WORK *.md *.json *.txt CLAUDE.md && "
        f"git diff --quiet {FROZEN_BASE} -- R05_BASELINE R06_WORK R07_WORK && echo 'no change vs {FROZEN_BASE}'", ROOT)
    r07zip = os.environ.get("R07_ZIP")
    if r07zip and os.path.exists(r07zip):
        d = sha(r07zip)
        note("r07_source_zip_digest", "PASS" if d == "c152f0ca88db1214157392b7db919b555ca34c76d9f1299ba7a15a69fa71c039" else "FAIL", d)
    else:
        note("r07_source_zip_digest", "NOT_RUN", "set R07_ZIP=<ARC1_R07_SOURCE_ORIGINAL.zip> to verify (verified manually 2026-10-15: c152f0ca...a039, tree identical to repo)")

    # ---------- R07 (+R06) regression in a scratch copy ----------
    if a.skip_r07:
        note("r07_regression_full", "NOT_RUN", "--skip-r07 given")
    else:
        tmp = tempfile.mkdtemp(prefix="r08_r07reg_")
        dst = os.path.join(tmp, "arc1-compact")
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns("R08_WORK", "build", ".git"))
        ok, out = run(ev, "r07_regression_full", [sys.executable, "R07_WORK/tools/run_r07_checks.py"], dst, timeout=5400)
        tail = [l for l in out.splitlines() if l.startswith("PASS_R07") or l.startswith("FAIL_R07")]
        steps[-1]["detail"] = tail[-1] if tail else ""
        shutil.rmtree(tmp, ignore_errors=True)

    # ---------- R08 firmware ----------
    fw = os.path.join(R08, "firmware")
    run(ev, "fw_r08_test", "make test", fw)
    run(ev, "fw_r08_sanitize", "make sanitize", fw)
    run(ev, "fw_r08_freestanding", "make freestanding", fw)
    run(ev, "fw_r08_mutants", "make mutants", fw)

    # ---------- R08 RTL ----------
    fp = os.path.join(R08, "fpga")
    run(ev, "rtl_r08_lint", "make lint", fp)
    run(ev, "rtl_r08_top_sim", "make sim", fp, timeout=3600)
    run(ev, "rtl_r08_synth_estimate", "make synth-efx", fp, timeout=1800)

    # ---------- KiCad (native) ----------
    cad = os.path.join(R08, "cad")
    before = tree_digest(cad, exclude=("ERC", "NETLIST", "ARC1_R08_schematic.pdf"))
    before_plan = sha(os.path.join(R08, "board", "r08_board_plan.json"))
    run(ev, "kicad_generate", [sys.executable, "gen/gen_kicad.py"], cad)
    after = tree_digest(cad, exclude=("ERC", "NETLIST", "ARC1_R08_schematic.pdf"))
    same = before == after and before_plan == sha(os.path.join(R08, "board", "r08_board_plan.json"))
    note("kicad_generate_reproducible", "PASS" if same else "FAIL",
         "regenerated sources identical to the committed files" if same else
         f"differs: {sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))[:6]}")
    ok, out = run(ev, "kicad_version", "kicad-cli version", cad)
    steps[-1]["detail"] = out.strip().splitlines()[-1] if out.strip() else ""
    ok, out = run(ev, "kicad_erc", "kicad-cli sch erc --format report --severity-all -o ERC.txt ARC1_R08.kicad_sch && "
                                 "grep -q 'ERC messages: 0  Errors 0  Warnings 0' ERC.txt && tail -3 ERC.txt", cad)
    shutil.copy(os.path.join(cad, "ERC.txt"), ev) if os.path.exists(os.path.join(cad, "ERC.txt")) else None
    run(ev, "kicad_erc_json", "kicad-cli sch erc --format json --severity-all -o ERC.json ARC1_R08.kicad_sch", cad)
    run(ev, "kicad_netlist", "kicad-cli sch export netlist --format kicadxml -o NETLIST.xml ARC1_R08.kicad_sch", cad)
    run(ev, "kicad_pdf", "kicad-cli sch export pdf -o ARC1_R08_schematic.pdf ARC1_R08.kicad_sch", cad)
    run(ev, "crosscheck_1to1", [sys.executable, "cad/check/crosscheck_r08.py", ".", os.path.join(ev, "crosscheck.json")], R08)
    run(ev, "board_rules", [sys.executable, "board/check_board_r08.py"], R08)
    run(ev, "board_rules_negative_tests", [sys.executable, "-m", "unittest", "-v", "test_check_board_r08"], os.path.join(R08, "board"))
    ok, out = run(ev, "electrical_margins", [sys.executable, "analysis/electrical_margins_r08.py",
                                             "analysis/electrical_margins_r08.json", "docs/ELECTRICAL_MARGINS_R08.md"], R08)
    steps[-1]["detail"] = (out.strip().splitlines() or [""])[0]
    run(ev, "reports_bom_pins", [sys.executable, "tools/gen_reports_r08.py"], R08)
    run(ev, "firmware_pin_header", [sys.executable, "firmware/tools/gen_board_pins.py"], R08)

    # ---------- Efinity ----------
    efd = os.path.join(R08, "fpga", "efinity")
    b = {f: sha(os.path.join(efd, f)) for f in os.listdir(efd) if f.startswith("arc1_t35_r08")}
    run(ev, "efinity_inputs_generate", [sys.executable, "gen_efinity_r08.py"], efd)
    a2 = {f: sha(os.path.join(efd, f)) for f in os.listdir(efd) if f.startswith("arc1_t35_r08")}
    note("efinity_inputs_reproducible", "PASS" if a2 == b else "FAIL", "identical" if a2 == b else "regenerated files differ")
    run(ev, "efinity_inputs_syntax", f"{sys.executable} -c \"import xml.dom.minidom as m; m.parse('arc1_t35_r08.xml')\" && "
                                     f"{sys.executable} -m py_compile arc1_t35_r08_isf.py && echo OK", efd)
    efx = shutil.which("efx_run.py") or shutil.which("efx_run")
    if efx:
        run(ev, "efinity_native", f"{efx} arc1_t35_r08.xml --flow compile", efd, timeout=7200)
    else:
        note("efinity_native", "NOT_RUN", "efx_run.py not found: NATIVE_EDA_NOT_RUN (no T35 fit/STA/bitstream). "
                                          "See fpga/efinity/RUN_EFINITY_LOCALLY.md")

    # ---------- F133 diagnostic image ----------
    dg = os.path.join(R08, "f133_diag")
    run(ev, "f133_diag_build", "make clean && make", dg)
    h1 = sha(os.path.join(dg, "build", "arc1_r08_diag.egon")) if os.path.exists(os.path.join(dg, "build", "arc1_r08_diag.egon")) else ""
    run(ev, "f133_diag_rebuild", "make clean && make", dg)
    h2 = sha(os.path.join(dg, "build", "arc1_r08_diag.egon")) if os.path.exists(os.path.join(dg, "build", "arc1_r08_diag.egon")) else "x"
    note("f133_diag_reproducible", "PASS" if h1 == h2 and h1 else "FAIL", f"sha256 {h1} / {h2}")
    if h1:
        shutil.copy(os.path.join(dg, "build", "arc1_r08_diag.egon"), ev)

    # ---------- ledger ----------
    led = json.load(open(os.path.join(R08, "EVIDENCE_LEDGER.json")))
    allowed = {"VERIFIED_BY_VENDOR_DOC", "DERIVED_WITH_CALC", "TOOL_VERIFIED_NATIVE", "BUILD_ONLY", "HOST_TESTED",
               "RTL_SIMULATED", "VENDOR_OPEN", "FABRICATION_BLOCKER", "PHYSICAL_NOT_TESTED", "ASSUMPTION", "NOT_RUN"}
    ids = [e["id"] for e in led["entries"]]
    inval = [e["id"] for e in led["entries"] if not set(e["labels"]) <= allowed or not e.get("evidence_paths")]
    note("evidence_ledger_schema", "PASS" if not inval and len(ids) == len(set(ids)) else "FAIL",
         f"{len(ids)} entries; invalid {inval}; duplicates {len(ids) - len(set(ids))}")

    # ---------- honest NOT_RUN ----------
    for n_, d_ in (("pcb_layout_drc", "no PCB layout exists (R09): no DRC, no SI/PI extraction, no Gerbers"),
                   ("si_pi_simulation", "no IBIS/SPICE/field-solver runs; NOR/PSRAM VOH under load OPEN"),
                   ("hardware_any", "no board, no silicon: PHYSICAL_NOT_TESTED for F133 boot, NOR, BT820, T35, PSRAM, USB, audio"),
                   ("vendor_answers", "Bridgetek / AP Memory / Efinix / Allwinner / Winbond questions unanswered (VENDOR_OPEN)"),
                   ("fabrication", "NOT approved: R08 is HOLD/PARTIAL with open P0 items")):
        note(n_, "NOT_RUN", d_)

    fails = [s for s in steps if s["status"] == "FAIL"]
    nr = [s for s in steps if s["status"] == "NOT_RUN"]
    verdict = ("PASS_R08_HOST_RTL_NATIVE_KICAD_CHECKS" if not fails else "FAIL_R08_CHECKS")
    summary = {"run": ts, "verdict": verdict, "pass": sum(s["status"] == "PASS" for s in steps), "fail": len(fails),
               "not_run": len(nr), "steps": steps,
               "tools": {"python": sys.version.split()[0]}}
    json.dump(summary, open(os.path.join(ev, "summary.json"), "w"), indent=1)
    open(os.path.join(R08, "evidence", "LATEST.txt"), "w").write(os.path.relpath(ev, R08) + "\n")
    with open(os.path.join(ev, "MANIFEST_SHA256.txt"), "w") as fh:
        for f in sorted(os.listdir(ev)):
            if f != "MANIFEST_SHA256.txt":
                fh.write(f"{sha(os.path.join(ev, f))}  {f}\n")
    print(f"{verdict}: {summary['pass']} pass, {len(fails)} fail, {len(nr)} NOT_RUN -> {os.path.relpath(ev, ROOT)}/summary.json")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
