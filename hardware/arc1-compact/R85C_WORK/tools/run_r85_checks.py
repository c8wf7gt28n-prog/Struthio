#!/usr/bin/env python3
"""ARC-1 Compact R8.5 -- one command for every R8.5 check plus the R08 regression (which nests R07 and R06).

    python3 R85_WORK/tools/run_r85_checks.py              # everything (R08 regression in a scratch copy, ~15 min)
    python3 R85_WORK/tools/run_r85_checks.py --skip-r08   # R8.5 steps only (~6 min)

Run from hardware/arc1-compact/. Writes R85_WORK/evidence/run_<UTC>/ (one log per step with the exact command, cwd
and exit code, summary.json, copies of the key reports, the bitstream and its hash) and R85_WORK/evidence/LATEST.txt.
Frozen inputs (R05_BASELINE, R06_WORK, R07_WORK, R08_WORK, root files) are verified unchanged against R08_BASE_COMMIT.
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
R85 = os.path.join(ROOT, "R85_WORK")
BASE = open(os.path.join(R85, "R08_BASE_COMMIT.txt")).read().split()[0][:12]
steps = []


def run(ev, name, cmd, cwd, expect=0, timeout=3600, env=None, detail_from=None):
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
    with open(os.path.join(ev, name + ".log"), "w") as fh:
        fh.write(f"$ {cmd if isinstance(cmd, str) else ' '.join(cmd)}\n# cwd: {os.path.relpath(cwd, ROOT)}\n# exit: {rc}\n\n{out}")
    status = "PASS" if rc == expect else "FAIL"
    s = {"step": name, "status": status, "exit": rc, "seconds": round(dt, 1),
         "cmd": cmd if isinstance(cmd, str) else " ".join(cmd), "cwd": os.path.relpath(cwd, ROOT)}
    if detail_from:
        hits = [l for l in out.splitlines() if any(k in l for k in detail_from)]
        s["detail"] = " | ".join(hits[-3:])[:400]
    steps.append(s)
    print(f"{status:7} {name} ({dt:.1f} s){'  ' + s.get('detail', '') if s.get('detail') else ''}")
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
    ap.add_argument("--skip-r08", action="store_true")
    a = ap.parse_args()
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ev = os.path.join(R85, "evidence", f"run_{ts}")
    os.makedirs(ev)
    print("evidence:", os.path.relpath(ev, ROOT))

    # ---------- frozen inputs ----------
    run(ev, "frozen_r05_r06_r07_r08_unchanged",
        f"git diff --quiet {BASE} -- R05_BASELINE R06_WORK R07_WORK R08_WORK && "
        f"git diff --quiet {BASE} -- $(git ls-files -- '*.md' '*.json' '*.txt' | grep -v '/' ) && "
        f"echo 'R05/R06/R07/R08 + root files identical to {BASE}'", ROOT)
    note("change_order_input", "PASS" if sha(os.path.join(R85, "handoff_inputs", "ARC1_COMPACT_R8_5_ECP5_45F_BG381_CHANGE_ORDER_FINAL.docx")).startswith("2faa469e") else "FAIL",
         "change order .docx sha256 2faa469e...")

    # ---------- R08 (+R07, R06) regression in a scratch copy ----------
    if a.skip_r08:
        note("r08_regression_full", "NOT_RUN", "--skip-r08 given")
    else:
        tmp = tempfile.mkdtemp(prefix="r85_r08reg_")
        dst = os.path.join(tmp, "arc1-compact")
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns("R85_WORK", "build", "evidence"))
        subprocess.run("git init -q && git add -A && git -c user.email=x@y -c user.name=x commit -qm base", cwd=dst, shell=True)
        ok, out = run(ev, "r08_regression_full", [sys.executable, "R08_WORK/tools/run_r08_checks.py"], dst, timeout=7200,
                      env={"FROZEN_BASE": "HEAD"}, detail_from=("PASS_R08", "FAIL_R08"))
        shutil.rmtree(tmp, ignore_errors=True)

    # ---------- firmware (R08 NOR/layout/library + R8.5 loader/link/service) ----------
    fw = os.path.join(R85, "firmware")
    run(ev, "fw_r85_test", "make test", fw, detail_from=("host tests", "FIT_SUMMARY"))
    run(ev, "fw_r85_sanitize", "make sanitize", fw, detail_from=("host tests",))
    run(ev, "fw_r85_freestanding", "make freestanding", fw)
    run(ev, "fw_r85_mutants", "make mutants", fw, timeout=3600, detail_from=("MUTANT_SURVIVED",))
    steps[-1]["detail"] = "all mutants killed" if steps[-1]["status"] == "PASS" else steps[-1].get("detail", "")

    # ---------- RTL ----------
    fp = os.path.join(R85, "fpga_ecp5")
    run(ev, "rtl_ecp5_lint", "make lint", fp)
    run(ev, "rtl_transform_r05_testbench", "make transform", fp, detail_from=("PASS RTL",))
    run(ev, "rtl_ecp5_top_sim_crosssim", "make sim", fp, timeout=3600, detail_from=("SUMMARY", "AJOB_RTL_CHECK"))
    with tempfile.TemporaryDirectory() as t:
        run(ev, "rtl_psram_controller_r06_regression", f"make sim mutants OUT={t}", os.path.join(ROOT, "R06_WORK", "fpga", "psram"),
            timeout=3600, detail_from=("PASS", "KILLED", "SURVIVED"))

    # ---------- pin matrix + LPF (generated from the board plan; must be reproducible) ----------
    lpf = os.path.join(fp, "constraints", "arc1_ecp5_r85.lpf")
    b_lpf = sha(lpf)
    run(ev, "kicad_generate", [sys.executable, "gen/gen_kicad.py"], os.path.join(R85, "cad"))
    run(ev, "pin_matrix_and_lpf", [sys.executable, "tools/gen_pin_matrix_r85.py"], R85, detail_from=("PIN_MATRIX", "ECP5 balls"))
    note("lpf_reproducible", "PASS" if sha(lpf) == b_lpf else "FAIL", "regenerated LPF identical" if sha(lpf) == b_lpf else "LPF changed: commit it")

    # ---------- open-toolchain build ----------
    run(ev, "tool_versions", "sh build_scripts/record_tools.sh build/TOOL_VERSIONS.txt", fp)
    run(ev, "ecp5_build_bitstream", "rm -f build/arc1_ecp5.json build/arc1_ecp5.config build/arc1_ecp5.bit && make bit", fp, timeout=3600)
    run(ev, "ecp5_build_report", "make report", fp, detail_from=("result",))
    run(ev, "ecp5_build_reproducible", "make repro", fp, timeout=3600, detail_from=("REPRO_IDENTICAL",))
    run(ev, "ecp5_seed_sweep", "make seeds", fp, timeout=3600, detail_from=("seed 5",))
    for f in ("arc1_ecp5.bit", "arc1_ecp5.bit.sha256", "BUILD_REPORT.json", "BUILD_REPORT.md", "TOOL_VERSIONS.txt", "nextpnr.log",
              "yosys.log", "seeds.log", "repro.log"):
        if os.path.exists(os.path.join(fp, "build", f)):
            shutil.copy(os.path.join(fp, "build", f), ev)
    run(ev, "fw_r85_real_bitstream", "build/test_r85", fw, env={"ARC1_BIT": os.path.join(fp, "build", "arc1_ecp5.bit")},
        detail_from=("using real", "FIT_SUMMARY"))

    # ---------- KiCad (native) ----------
    cad = os.path.join(R85, "cad")
    before = tree_digest(cad, exclude=("ERC", "NETLIST", "ARC1_R85_schematic.pdf"))
    plan = os.path.join(R85, "board", "r85_board_plan.json")
    before_plan = sha(plan)
    run(ev, "kicad_generate_again", [sys.executable, "gen/gen_kicad.py"], cad)
    same = before == tree_digest(cad, exclude=("ERC", "NETLIST", "ARC1_R85_schematic.pdf")) and before_plan == sha(plan)
    note("kicad_generate_reproducible", "PASS" if same else "FAIL", "regeneration byte-identical" if same else "regeneration differs")
    ok, out = run(ev, "kicad_version", "kicad-cli version", cad)
    steps[-1]["detail"] = out.strip().splitlines()[-1] if out.strip() else ""
    run(ev, "kicad_erc", "kicad-cli sch erc --format report --severity-all -o ERC.txt ARC1_R85.kicad_sch && "
                         "grep -q 'ERC messages: 0  Errors 0  Warnings 0' ERC.txt && tail -1 ERC.txt", cad, detail_from=("ERC messages",))
    shutil.copy(os.path.join(cad, "ERC.txt"), ev) if os.path.exists(os.path.join(cad, "ERC.txt")) else None
    run(ev, "kicad_erc_json", "kicad-cli sch erc --format json --severity-all -o ERC.json ARC1_R85.kicad_sch", cad)
    run(ev, "kicad_netlist", "kicad-cli sch export netlist --format kicadxml -o NETLIST.xml ARC1_R85.kicad_sch", cad)
    run(ev, "kicad_pdf", "kicad-cli sch export pdf -o ARC1_R85_schematic.pdf ARC1_R85.kicad_sch", cad)
    run(ev, "crosscheck_1to1", [sys.executable, "cad/check/crosscheck_r85.py", ".", os.path.join(ev, "crosscheck.json")], R85,
        detail_from=("CROSSCHECK", "routed_io"))
    run(ev, "board_rules", [sys.executable, "board/check_board_r85.py"], R85, detail_from=("board rules",))
    run(ev, "board_rules_negative_tests", [sys.executable, "-m", "unittest", "test_check_board_r85"], os.path.join(R85, "board"),
        detail_from=("Ran ", "OK", "FAILED"))
    run(ev, "electrical_margins", [sys.executable, "analysis/electrical_margins_r85.py", "analysis/electrical_margins_r85.json",
                                   "docs/ELECTRICAL_MARGINS_R85.md"], R85, detail_from=("margins:",))
    run(ev, "reports_bom_pins_interconnect", [sys.executable, "tools/gen_reports_r85.py"], R85, detail_from=("BOM lines",))
    run(ev, "firmware_pin_header", [sys.executable, "firmware/tools/gen_board_pins.py"], R85)
    run(ev, "delta_table_t35_to_ecp5", [sys.executable, "tools/gen_delta_r85.py"], R85, detail_from=("delta rows",))
    run(ev, "migration_45f_85f", [sys.executable, "tools/check_migration_r85.py"], R85, detail_from=("RESULT",))

    # ---------- benchmark + failure-injection table ----------
    run(ev, "benchmark_hard_stop_analysis", [sys.executable, "-I", "tools/bench/benchmark_r85.py", "analysis/benchmark_r85.json",
                                             "docs/BENCHMARK_R85.md"], R85, detail_from=("verdict",))
    run(ev, "failure_injection_table", [sys.executable, "tools/gen_fit_doc_r85.py"], R85, detail_from=("FIT rows",))

    # ---------- F133 diagnostic image ----------
    dg = os.path.join(R85, "f133_diag")
    img = os.path.join(dg, "build", "arc1_r85_diag.egon")
    run(ev, "f133_diag_build", "make clean && make", dg, detail_from=("EGON_OK", "fits_sram"))
    h1 = sha(img) if os.path.exists(img) else ""
    run(ev, "f133_diag_rebuild", "make clean && make", dg)
    h2 = sha(img) if os.path.exists(img) else "x"
    note("f133_diag_reproducible", "PASS" if h1 == h2 and h1 else "FAIL", f"sha256 {h1}")
    if h1:
        shutil.copy(img, ev)

    # ---------- ledger ----------
    led = json.load(open(os.path.join(R85, "EVIDENCE_LEDGER.json")))
    allowed = set(led["labels_allowed"])
    ids = [e["id"] for e in led["entries"]]
    inval = [e["id"] for e in led["entries"] if not set(e["labels"]) <= allowed or not e.get("evidence_paths")
             or not all(os.path.exists(os.path.join(R85, p.split(' ')[0])) for p in e["evidence_paths"])]
    note("evidence_ledger_schema", "PASS" if not inval and len(ids) == len(set(ids)) else "FAIL",
         f"{len(ids)} entries; invalid/missing paths {inval}; duplicates {len(ids) - len(set(ids))}")

    # ---------- honest NOT_RUN ----------
    for n_, d_ in (("lattice_vendor_tools", "Lattice Diamond/Radiant timing sign-off and the Lattice Power Calculator not run (open flow only)"),
                   ("fpga_io_timing_signoff", "nextpnr-ecp5 does not time pad paths: PSRAM/SPI I/O budgets are hand calculations"),
                   ("pcb_layout_drc", "no PCB layout (R09 not entered by order): no DRC, no SI/PI, no Gerbers"),
                   ("hardware_any", "no board, no ECP5 silicon: PHYSICAL_NOT_TESTED for configuration, mailbox, PSRAM, power"),
                   ("part_identity_and_assembly_quote", "G1: distributor stock/price and a JLCPCB assembly quote for the caBGA381 not obtained"),
                   ("independent_review", "G10: independent R8.5 review not yet performed"),
                   ("fabrication", "NOT approved")):
        note(n_, "NOT_RUN", d_)

    fails = [s for s in steps if s["status"] == "FAIL"]
    nr = [s for s in steps if s["status"] == "NOT_RUN"]
    verdict = "PASS_R85_HOST_RTL_OPENFPGA_KICAD_CHECKS" if not fails else "FAIL_R85_CHECKS"
    summary = {"run": ts, "verdict": verdict, "pass": sum(s["status"] == "PASS" for s in steps), "fail": len(fails),
               "not_run": len(nr), "steps": steps, "base_commit": BASE, "tools": {"python": sys.version.split()[0]}}
    json.dump(summary, open(os.path.join(ev, "summary.json"), "w"), indent=1)
    open(os.path.join(R85, "evidence", "LATEST.txt"), "w").write(os.path.relpath(ev, R85) + "\n")
    with open(os.path.join(ev, "MANIFEST_SHA256.txt"), "w") as fh:
        for f in sorted(os.listdir(ev)):
            if f != "MANIFEST_SHA256.txt":
                fh.write(f"{sha(os.path.join(ev, f))}  {f}\n")
    print(f"{verdict}: {summary['pass']} pass, {len(fails)} fail, {len(nr)} NOT_RUN -> {os.path.relpath(ev, ROOT)}/summary.json")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
