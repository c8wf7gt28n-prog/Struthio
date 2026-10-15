#!/usr/bin/env python3
"""Run Compact host/planning/RTL checks and retain fresh logs; no hardware proof.

Default: HDL simulation is required. Use --skip-hdl only for an explicitly partial
host-only run. This runner uses only the Python standard library and local tools.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class VerificationFailure(RuntimeError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_snapshot():
    """Bind executed source/tests plus planning inputs, excluding generated output."""
    paths = {Path(__file__).resolve(), ROOT / "VERIFY.md"}
    for directory in ("display", "memory", "protocol", "compute", "integration"):
        for path in (ROOT / directory).rglob("*"):
            relative_parts = path.relative_to(ROOT / directory).parts
            if any(part in ("build", "__pycache__", "verification", "verification_logs") for part in relative_parts):
                continue
            if path.is_file() and (path.suffix in (".py", ".c", ".h", ".sv") or path.name == "Makefile"):
                paths.add(path)
    for name in ("display/compact_display.json", "display/r04_porch_assumption.json",
                 "memory/bt820_memory.json", "protocol/reference/golden_vectors.json",
                 "compute/CONTRACT.md", "integration/SCENE_PAYLOAD_V1.md",
                 "engineering/sources.json", "engineering/architecture.json",
                 "engineering/tasks.json", "engineering/calculations.json"):
        path = ROOT / name
        require(path.is_file(), "Missing source/input artifact: " + name)
        paths.add(path)
    return {str(path.relative_to(ROOT)): {"sha256": digest(path), "bytes": path.stat().st_size}
            for path in sorted(paths)}


def executable(name):
    resolved = shutil.which(name)
    if resolved is None:
        raise VerificationFailure(f"Required executable unavailable: {name}")
    return str(Path(resolved).resolve())


def hdl_executable(name):
    resolved = executable(name)
    # Existing compute Makefile expands tool paths in recipes without quoting.
    # Reject make/shell metacharacters instead of interpreting them as code.
    if re.fullmatch(r"[A-Za-z0-9_./+\-]+", resolved) is None:
        raise VerificationFailure("HDL executable path must contain no whitespace or make/shell metacharacters: " + resolved)
    return resolved


def require(condition, message):
    if not condition:
        raise VerificationFailure(message)


def unit_test_count(output, minimum):
    matches = re.findall(r"Ran (\d+) tests? in ", output)
    require(bool(matches), "Missing unittest execution count; an empty discovery is not a pass.")
    count = int(matches[-1])
    require(count >= minimum, f"Only {count} tests ran; expected at least {minimum}.")
    require(re.search(r"(?m)^OK\s*$", output) is not None, "Missing unqualified unittest OK marker.")
    require(re.search(r"(?i)skipped\s*=|\bskipped\b", output) is None, "Skipped tests are not accepted for this required suite.")
    return {"tests_run": count, "skipped_tests_accepted": False}


def planning_report(path):
    report = json.loads(path.read_text(encoding="utf-8"))
    require(report.get("valid") is True and report.get("status") == "VALID_PLANNING_DATA",
            "Planning validator did not report valid planning data.")
    require(report.get("hardware_verified") is False, "Planning output must not claim hardware verification.")
    return {"report": str(path.relative_to(ROOT)), "report_sha256": digest(path),
            "evidence_level": report.get("evidence_level")}


def compute_c_markers(output):
    runner = re.search(r"PASS C vector runner: (\d+) cases", output)
    abi = re.search(r"PASS C ABI: (\d+) batch and (\d+) scalar oracle comparisons", output)
    require(bool(runner and abi), "Missing explicit compute C oracle PASS markers.")
    require(not re.search(r"(?m)^(ERROR:|FATAL:)", output), "Compute emitted an ERROR/FATAL diagnostic.")
    counts = (int(runner[1]), int(abi[1]), int(abi[2]))
    require(counts == (1165, 1165, 1165), "Compute C oracle counts do not match the current 1165-case contract.")
    return {"c_ubsan_oracle_cases": counts[0], "c_batch_oracle_cases": counts[1], "c_scalar_oracle_cases": counts[2]}


def compute_full_report(path, started_ns, destination):
    require(path.is_file(), "Compute verification report was not created.")
    require(path.stat().st_mtime_ns >= started_ns, "Compute verification report predates this invocation.")
    report = json.loads(path.read_text(encoding="utf-8"))
    require(report.get("schema_id") == "arc1-compute-verification-v1", "Unsupported compute verification schema.")
    require(report.get("status") == "PASS_HOST_AND_RTL_SIMULATION", "Compute report explicitly failed or omitted the required full PASS.")
    require(report.get("exit_code") == 0 and report.get("error_diagnostic_present") is False,
            "Compute report contains a failed exit or error diagnostic.")
    for name in ("c_ubsan_oracle_cases", "c_batch_oracle_cases", "c_scalar_oracle_cases", "rtl_oracle_cases"):
        require(report.get(name) == 1165, f"Compute report has missing/wrong {name}.")
    for name in ("rtl_input_stall_cycles", "rtl_output_stall_cycles", "rtl_simultaneous_retire_accept"):
        require(type(report.get(name)) is int and report[name] > 0, f"Compute report lacks exercised {name}.")
    require(report.get("reset_during_compute_and_held_result_checked") is True, "Compute reset coverage was not reported.")
    for name in ("efinity_run", "synthesis_run", "static_timing_run", "physical_fpga_test", "acceleration_measured"):
        require(report.get(name) is False, f"Unexpected hardware/EDA assertion in compute report: {name}.")
    write_json(destination, report)
    return {"report": str(destination.relative_to(ROOT)), "report_sha256": digest(destination),
            "status": report["status"], "rtl_oracle_cases": report["rtl_oracle_cases"]}


class Runner:
    def __init__(self, args):
        self.args = args
        self.run_id = datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%S_%fZ")
        self.last_run = ROOT / "verification" / "last_run"
        self.directory = self.last_run / self.run_id
        self.directory.mkdir(parents=True, exist_ok=False)
        self.summary = {
            "schema_id": "arc1-compact-check-all-v1", "run_id": self.run_id,
            "started_at_utc": utc_now(), "finished_at_utc": None, "status": "RUNNING",
            "evidence_scope": "HOST_SOFTWARE_PLANNING_AND_OPTIONAL_RTL_SIMULATION",
            "hardware_verified": False, "efinity_run": False, "synthesis_run": False,
            "static_timing_run": False, "measured_spi_throughput": None,
            "hdl_required": not args.skip_hdl,
            "hdl_status": "SKIPPED_EXPLICITLY" if args.skip_hdl else "NOT_RUN",
            "partial_run": bool(args.skip_hdl), "all_required_steps_completed": False,
            "runner_sha256": digest(Path(__file__).resolve()),
            "steps": [], "tools": {}, "failure": None,
            "notes": ["Planning and simulation success does not qualify Compact hardware.",
                      "Protocol ASan/UBSan uses detect_leaks=0: LeakSanitizer is not verified.",
                      "A host-only skip is never reported as an HDL pass."],
        }
        self.sources = source_snapshot()
        source_manifest = self.directory / "source_manifest.json"
        write_json(source_manifest, {"schema_id": "arc1-check-all-source-manifest-v1",
                                    "run_id": self.run_id, "recorded_at_utc": utc_now(),
                                    "meaning": "Current local source/input byte identity, not vendor authentication or hardware proof.",
                                    "files": self.sources})
        self.summary["source_manifest"] = str(source_manifest.relative_to(ROOT))
        self.summary["source_manifest_sha256"] = digest(source_manifest)
        self.summary["sources_unchanged_during_run"] = None
        self.persist()
        write_json(ROOT / "integration" / "demo_report.json", {
            "schema_id": "arc1-integration-demo-run-status-v1", "run_id": self.run_id,
            "status": "NOT_RUN_THIS_INVOCATION", "hardware_verified": False,
        })

    def persist(self):
        write_json(self.directory / "summary.json", self.summary)
        write_json(self.last_run / "summary.json", self.summary)

    def run(self, name, command, *, cwd=ROOT, validate=None):
        step = {"name": name, "command": [str(x) for x in command],
                "cwd": str(cwd.relative_to(ROOT)) or ".", "started_at_utc": utc_now(),
                "status": "RUNNING", "exit_code": None,
                "log": str((self.directory / (name + ".log")).relative_to(ROOT))}
        self.summary["steps"].append(step)
        self.persist()
        print(f"RUN  {name}", flush=True)
        started = time.monotonic()
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHON"] = PYTHON
        try:
            with (ROOT / step["log"]).open("w", encoding="utf-8") as stream:
                process = subprocess.Popen(step["command"], cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                           stdout=stream, stderr=subprocess.STDOUT,
                                           start_new_session=(os.name == "posix"))
                try:
                    exit_code = process.wait(timeout=self.args.timeout)
                except BaseException:
                    if process.poll() is None:
                        if os.name == "posix":
                            os.killpg(process.pid, signal.SIGKILL)
                        else:
                            process.kill()
                    process.wait()
                    raise
            step["exit_code"] = exit_code
            require(exit_code == 0, f"{name} exited {exit_code}; see {step['log']}")
            if validate is not None:
                step["details"] = validate((ROOT / step["log"]).read_text(encoding="utf-8"))
            step["status"] = "PASS"
        except Exception as exc:
            step["status"] = "FAIL"
            step["failure"] = f"{type(exc).__name__}: {exc}"
            raise VerificationFailure(step["failure"]) from exc
        finally:
            step["elapsed_seconds"] = round(time.monotonic() - started, 6)
            step["finished_at_utc"] = utc_now()
            if (ROOT / step["log"]).is_file():
                step["log_sha256"] = digest(ROOT / step["log"])
            self.persist()
        print(f"PASS {name}", flush=True)

    def execute(self):
        tools = {"python": PYTHON, "cc": executable("cc"), "make": executable("make")}
        if not self.args.skip_hdl:
            tools.update(iverilog=hdl_executable(self.args.iverilog), vvp=hdl_executable(self.args.vvp))
        self.summary["tools"] = tools
        self.persist()
        self.run("python_version", [PYTHON, "--version"])
        self.run("compiler_version", [tools["cc"], "--version"])
        self.run("make_version", [tools["make"], "--version"])

        self.run("display_tests", [PYTHON, "-m", "unittest", "discover", "-s", "display/tests", "-p", "test_validate_display.py", "-v"],
                 validate=lambda text: unit_test_count(text, 14))
        display_report = self.directory / "display_planning.json"
        self.run("display_planning", [PYTHON, "display/validate_display.py", "display/compact_display.json", "--output", display_report],
                 validate=lambda _: planning_report(display_report))
        self.run("memory_tests", [PYTHON, "-m", "unittest", "discover", "-s", "memory/tests", "-p", "test_validate_memory.py", "-v"],
                 validate=lambda text: unit_test_count(text, 18))
        memory_report = self.directory / "memory_planning.json"
        self.run("memory_planning", [PYTHON, "memory/validate_memory.py", "memory/bt820_memory.json", "--output", memory_report],
                 validate=lambda _: planning_report(memory_report))

        def protocol_pass(text):
            details = unit_test_count(text, 14)
            require("ALL PORTABLE PROTOCOL CHECKS PASSED; no SPI or physical hardware exercised" in text,
                    "Missing C protocol behavioral PASS marker.")
            return details

        self.run("protocol_tests", [tools["make"], "-B", "test"], cwd=ROOT / "protocol", validate=protocol_pass)
        self.run("protocol_sanitizers", [tools["make"], "sanitize", "SANITIZER_OPTIONS=detect_leaks=0"], cwd=ROOT / "protocol",
                 validate=lambda text: require("ALL PORTABLE PROTOCOL CHECKS PASSED; no SPI or physical hardware exercised" in text,
                                               "Missing sanitized C protocol PASS marker."))
        self.run("protocol_freestanding", [tools["cc"], "-Iinclude", "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wpedantic",
                                            "-Wconversion", "-Wshadow", "-ffreestanding", "-c", "src/arc1_protocol.c", "-o", "build/arc1_protocol_freestanding.o"],
                 cwd=ROOT / "protocol")

        compute_report = self.directory / "compute_report.json"
        if self.args.skip_hdl:
            def c_only(text):
                report = {"schema_id": "arc1-compute-host-only-run-v1", "run_id": self.run_id,
                          "status": "PASS_HOST_ONLY_HDL_SKIPPED", "hdl_status": "SKIPPED_EXPLICITLY",
                          "hardware_verified": False, **compute_c_markers(text)}
                write_json(compute_report, report)
                return {"report": str(compute_report.relative_to(ROOT)), "status": report["status"]}
            self.run("compute_host_only", [tools["make"], "-B", "check-c"], cwd=ROOT / "compute", validate=c_only)
        else:
            started_ns = time.time_ns()
            self.run("compute_host_and_hdl", [PYTHON, "compute/tests/run_verification.py", "--iverilog", tools["iverilog"], "--vvp", tools["vvp"]],
                     validate=lambda _: compute_full_report(ROOT / "compute/verification_results.json", started_ns, compute_report))
            self.summary["hdl_status"] = "PASS_RTL_SIMULATION_ONLY"
            self.persist()

        self.run("integration_tests", [PYTHON, "-m", "unittest", "discover", "-s", "integration", "-p", "test_pipeline.py", "-v"],
                 validate=lambda text: unit_test_count(text, 13))

        def integration_demo(text):
            report = json.loads(text)
            require(report.get("scope") == "HOST_ONLY_C_CODEC_SESSION_AND_C_COMPUTE_REFERENCE", "Unexpected integration evidence scope.")
            require((report.get("objects"), report.get("visible"), report.get("culled"), report.get("job_batches")) == (256, 218, 38, 4),
                    "Integration scene counts differ from the current deterministic contract.")
            require(report.get("hardware_verified") is False and report.get("measured_spi_throughput") is None and report.get("measured_game_fps") is None,
                    "Integration output must not claim physical measurements.")
            require(report.get("duplicate_reexecutions") == 0, "Integration reports duplicate re-execution.")
            report["runner"] = {"run_id": self.run_id, "recorded_at_utc": utc_now(), "pipeline_sha256": digest(ROOT / "integration/pipeline.py")}
            write_json(self.directory / "integration_demo.json", report)
            write_json(ROOT / "integration/demo_report.json", report)
            return {"report": "integration/demo_report.json", "objects": report["objects"], "scope": report["scope"]}

        self.run("integration_demo", [PYTHON, "integration/pipeline.py"], validate=integration_demo)
        self.summary["sources_unchanged_during_run"] = source_snapshot() == self.sources
        require(self.summary["sources_unchanged_during_run"], "Source/configuration changed during this run; rerun against one stable revision.")
        self.summary["all_required_steps_completed"] = True
        self.summary["status"] = "PASS_HOST_ONLY_HDL_SKIPPED" if self.args.skip_hdl else "PASS_HOST_AND_RTL_SIMULATION"

    def finish(self, error=None):
        if error is not None:
            self.summary["status"] = "FAIL"
            self.summary["failure"] = f"{type(error).__name__}: {error}"
            write_json(ROOT / "integration/demo_report.json", {
                "schema_id": "arc1-integration-demo-run-status-v1", "run_id": self.run_id,
                "status": "NOT_VALIDATED_RUN_FAILED", "hardware_verified": False,
                "failure": self.summary["failure"],
            })
        self.summary["finished_at_utc"] = utc_now()
        self.persist()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iverilog", default="iverilog", help="Icarus compiler executable; default: PATH iverilog")
    parser.add_argument("--vvp", default="vvp", help="Icarus runtime executable; default: PATH vvp")
    parser.add_argument("--skip-hdl", action="store_true", help="Explicit partial host-only run; does not certify RTL simulation")
    parser.add_argument("--timeout", type=int, default=300, metavar="SECONDS", help="Timeout per subprocess (default: 300 seconds)")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    runner = Runner(args)
    error = None
    try:
        runner.execute()
    except (Exception, KeyboardInterrupt) as exc:
        error = exc
    runner.finish(error)
    print(runner.summary["status"], flush=True)
    print("Summary: " + str((runner.last_run / "summary.json").relative_to(ROOT)), flush=True)
    if error is not None:
        print(runner.summary["failure"], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
