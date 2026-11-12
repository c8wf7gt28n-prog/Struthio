"""Fixed, bounded console simulation job for the shared Ledger kernel."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from . import console_simulation as sim


def host_firmware(root, output):
    compiler = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    if not compiler:
        return dict(status="BLOCKED", reason="No host C compiler", commands=[], cases=[])
    hw = root / sim.BASE
    loader = hw / "firmware/d213_flashless_proof/loader"
    video = hw / "firmware/d213_video_diag"
    definitions = [
        ("startup_video", [hw / "closure_p9/test_host_sequence.c", loader / "r10_d213_start.c",
                            video / "r10_video_start.c", video / "r10_video_diag.c", video / "r10_adv7513.c"]),
        ("d213_negative_paths", [loader / "test_r10_d213_start.c", loader / "r10_d213_start.c"]),
    ]
    commands, cases = [], []
    def execute(argv):
        started = time.monotonic()
        p = subprocess.run([str(a) for a in argv], cwd=root, capture_output=True, text=True,
                           timeout=45, stdin=subprocess.DEVNULL,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        commands.append(dict(argv=[str(a) for a in argv], exit_status=p.returncode,
                             stdout=p.stdout[:10000], stderr=p.stderr[:10000],
                             host_seconds=time.monotonic() - started))
        return p
    version = execute([compiler, "--version"])
    for name, sources in definitions:
        executable = output / (name + (".exe" if os.name == "nt" else ""))
        compiled = execute([compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                            "-I" + str(loader), "-I" + str(video), *sources, "-o", executable])
        ran = execute([executable]) if compiled.returncode == 0 else None
        passed = compiled.returncode == 0 and ran.returncode == 0
        cases.append(dict(id=name, status="PASS" if passed else "FAIL", evidence="HOST_SIM",
                          scope="Actual existing firmware C on mocks; not CPU emulation or a boot image",
                          executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest() if passed else None))
    return dict(status="PASS" if all(c["status"] == "PASS" for c in cases) else "FAIL",
                compiler=version.stdout.splitlines()[0] if version.stdout else compiler,
                cases=cases, commands=commands)


def render_report(report):
    escape = lambda value: html.escape(str(value))
    rows = "".join(f"<tr><td>{escape(c['id'])}</td><td class='{c['status'].lower()}'>{c['status']}</td>"
                   f"<td>{len(c['outcome']['frames'])}</td><td>{len(c['outcome']['errors'])}</td></tr>"
                   for c in report["cases"])
    gates = "".join(f"<tr><td>{escape(g['id'])}</td><td>{escape(g['requirement'])}</td><td>{escape(g['needed'])}</td></tr>"
                    for g in report["critical_gates"])
    blocks = []
    for c in report["cases"]:
        trace = json.dumps(c["outcome"]["trace"], indent=2)
        blocks.append(f"<details><summary>{escape(c['id'])}: event trace</summary><pre>{escape(trace)}</pre></details>")
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ARC-1 simulation — first causal pass</title><style>
body{font:16px/1.55 system-ui;background:#181a1c;color:#e8e8e8;max-width:1050px;margin:30px auto;padding:0 18px}
h1{font-size:27px;color:#ff8b50}h2{font-size:20px;margin-top:32px}.status{border:1px solid #ff8b50;padding:15px;border-radius:5px}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:9px;border-bottom:1px solid #454545;vertical-align:top}
.pass{color:#9dd6ac}.fail{color:#ff9b90}pre{white-space:pre-wrap;font-size:12px}summary{cursor:pointer;padding:8px}small{color:#bbb}
</style><h1>ARC-1 · simulation first</h1><div class="status"><b>Fabrication: HOLD · Target models: BLOCKED</b><br>
Confidence goal: 96%. Estimated first-boot probability: not established.<br>
This report exercises transaction contracts and real firmware C on host mocks. It does not execute the processors or FPGA RTL.</div>
<h2>Experiments completed</h2><p>""" + escape(report["case_counts"]) + """</p>
<p>A failed transfer changes whether a picture can reach the simulated sink. A reset aborts old work; a new boot must submit new work.</p>
<table><tr><th>Contract scenario</th><th>Check</th><th>Images delivered</th><th>Rejections recorded</th></tr>""" + rows + """</table>
<p>Host firmware checks: """ + escape(report["host_firmware"]["status"]) + """. The successful startup callbacks in these checks are mocks.</p>
<h2>Critical target work still open</h2><p>Passing the scenarios above does not close these requirements. The inventory and risk model still need review.</p>
<table><tr><th>Area</th><th>Requirement</th><th>Needed</th></tr>""" + gates + """</table>
<h2>Replayable traces</h2>""" + "".join(blocks) + """<p><small>Time uses fixture logical steps. It is not target latency, MHz or clock-cycle timing.<br>
Input fingerprint: """ + escape(report["source_fingerprint"]) + "</small></p></html>"


def campaign(root):
    created = time.time()
    inspected = sim.inspect(root)
    output = root / "build/console_simulation"
    if not output.resolve().is_relative_to(root.resolve()):
        raise ValueError("Simulation output must stay inside the project")
    output.mkdir(parents=True, exist_ok=True)
    cases = sim.run_cases(root)
    firmware = host_firmware(root, output)
    counts = {status: sum(c["status"] == status for c in cases) for status in ("PASS", "FAIL")}
    experiment = "FAIL" if counts["FAIL"] or firmware["status"] == "FAIL" else "BLOCKED" if firmware["status"] == "BLOCKED" else "PASS"
    report = dict(inspected, created=created, evidence="HOST_SIM", status="BLOCKED",
                  experiment_status=experiment, case_counts=counts, cases=cases, host_firmware=firmware,
                  confidence_goal_met=False, independent_acceptance=False,
                  target_timing_qualified=False, target_cpu_execution=False, target_fpga_execution=False)
    if sim.input_hashes(root) != report["input_hashes"]:
        raise ValueError("Simulation inputs changed during execution")
    (output / "campaign.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "report.html").write_text(render_report(report))
    for case in cases:
        if case["id"] == "baseline":
            pixels = bytes.fromhex(case["outcome"]["frames"][0]["pixels"])
            (output / "diagnostic_fixture.ppm").write_bytes(b"P6\n8 8\n255\n" + pixels)
    print(json.dumps(dict(experiment_status=experiment, target_status="BLOCKED", fabrication="HOLD",
                          scenarios=counts, host_firmware=firmware["status"], confidence_goal_percent=96,
                          estimated_first_boot_probability=None, report="build/console_simulation/report.html"), indent=2))
    return 1 if experiment == "FAIL" else 3 if experiment == "BLOCKED" else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["campaign", "inspect"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.action == "inspect":
            print(json.dumps(sim.inspect(root), indent=2))
            return 0
        return campaign(root)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps(dict(status="FAIL", reason=str(exc), fabrication="HOLD")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
