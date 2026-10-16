"""Game projects: `arc1 new`, `arc1 build`, `arc1 sim`, `arc1 test`."""

import json
import os
import re
import shutil
from pathlib import Path

from . import assets as asset_tool
from .core import (COMPILE_TIMEOUT_S, SCHEMA_REVISION, SDK_ROOT, SIM_TIMEOUT_S, UsageError,
                   bounded, canonical_json, digest_files, display_path, find_cc, load_json,
                   load_lock, rel_posix, run_tool, schema_validator, sha256_bytes, sha256_file,
                   toolchain_digest, write_report)
from .hardware import DEFAULT_BOARD, HOST_SIM

MANIFEST = "arc1.game.json"
TEST_PLAN = "tests/arc1.tests.json"
TEMPLATE = SDK_ROOT / "sdk" / "templates" / "game"
RUNTIME_SOURCES = [SDK_ROOT / "sdk" / "runtime" / "host" / "arc1_host.c"]
PUBLIC_HEADERS = [SDK_ROOT / "sdk" / "include" / "arc1" / "game.h"]
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")

# Package resource keys -> memory pool ids in the board manifest.
RESOURCE_POOLS = {
    "f133_ram_limit_bytes": "f133_ddr2",
    "d213_ram_limit_bytes": "d213_ddr3",
    "gpu45_sdram_limit_bytes": "gpu45_sdram",
    "fpga12_psram_limit_bytes": "fpga12_psram",
}

HOST_WARNINGS = ["Physical ARC-1 was not used",
                 "Host reference model is deterministic but not cycle accurate"]


class Project:
    def __init__(self, path):
        self.root = Path(path).resolve()
        if not (self.root / MANIFEST).is_file():
            raise UsageError("%s is not an ARC-1 project (no %s)" % (display_path(self.root), MANIFEST))
        self.build_dir = self.root / "build"
        self.reports_dir = self.root / "reports"

    @property
    def label(self):
        return display_path(self.root)

    def manifest(self):
        return load_json(self.root / MANIFEST, "package manifest")

    def binary(self, name):
        return self.build_dir / "host" / (name + (".exe" if os.name == "nt" else ""))

    def build_inputs(self):
        files = [self.root / MANIFEST]
        for sub in ("src", "assets"):
            d = self.root / sub
            if d.is_dir():
                files += [p for p in d.rglob("*") if p.is_file()]
        return files

    def build_digest(self):
        proj = digest_files(self.root, self.build_inputs())
        sdk = digest_files(SDK_ROOT, RUNTIME_SOURCES + PUBLIC_HEADERS)
        return sha256_bytes(("%s\n%s\n%s" % (proj, sdk, toolchain_digest()[0])).encode())


# ---------------------------------------------------------------- package checks

def check_package(project, doc):
    """PKG-001 / API-001 checks. Returns list of (code, pointer, message)."""
    errs = [("SCHEMA", p, m) for p, m in schema_validator("game-package.schema.json").errors(doc)]
    if errs:
        return errs
    if doc["required"]["sdk_version"] != SCHEMA_REVISION:
        errs.append(("PKG-001", "/required/sdk_version",
                     "project targets SDK %s, this SDK is %s" % (doc["required"]["sdk_version"], SCHEMA_REVISION)))
    declared = set()
    for i, a in enumerate(doc["assets"]):
        try:
            p = bounded(project.root, a["path"], "asset path")
        except UsageError as e:
            errs.append(("CLI-003", "/assets/%d/path" % i, str(e)))
            continue
        declared.add(p)
        if not p.is_file():
            errs.append(("PKG-001", "/assets/%d/path" % i, "asset file missing: %s" % a["path"]))
        elif sha256_file(p) != a["sha256"]:
            errs.append(("PKG-001", "/assets/%d/sha256" % i, "digest mismatch for %s" % a["path"]))
    adir = project.root / "assets"
    if adir.is_dir():
        for p in sorted(adir.rglob("*.sprite")):
            if p.resolve() not in declared:
                errs.append(("PKG-001", "/assets", "undeclared asset %s" % rel_posix(p, project.root)))
    board = load_json(DEFAULT_BOARD, "board manifest")
    pools = {m["id"]: m["capacity_bytes"] for c in board["chips"] for m in c["memory"]}
    for key, pool in RESOURCE_POOLS.items():
        if doc["resources"][key] > pools.get(pool, 0):
            errs.append(("PKG-001", "/resources/" + key,
                         "%d bytes exceeds the %s pool (%d bytes)" % (doc["resources"][key], pool, pools.get(pool, 0))))
    if doc["accelerators"]:
        errs.append(("API-001", "/accelerators",
                     "requested accelerators %s are not available on the host target" % doc["accelerators"]))
    if doc["verification"]["status"] == "board_tested":
        errs.append(("CLI-002", "/verification/status",
                     "board_tested cannot be declared: no board verification path exists in SDK 0.2"))
    return errs


def _validated_manifest(result, project):
    doc = project.manifest()
    errs = check_package(project, doc)
    for code, ptr, msg in errs:
        result.fail(code, "%s: %s" % (ptr, msg), display_path(project.root / MANIFEST))
    return None if errs else doc


# ---------------------------------------------------------------- new

def new(result, name, parent):
    if not NAME_RE.match(name or ""):
        raise UsageError("project name must match %s" % NAME_RE.pattern)
    dest = Path(parent).resolve() / name
    if dest.exists():
        raise UsageError("%s already exists; refusing to overwrite" % display_path(dest))
    result.command = "arc1 new %s" % name
    shutil.copytree(TEMPLATE, dest)
    for p in sorted(dest.rglob("*")):
        if p.is_file() and p.suffix in (".c", ".h", ".json", ".md", ".replay"):
            text = p.read_text(encoding="utf-8")
            if "{{name}}" in text:
                p.write_text(text.replace("{{name}}", name), encoding="utf-8")
    manifest = dest / MANIFEST
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    for a in doc["assets"]:
        a["sha256"] = sha256_file(dest / a["path"])
    manifest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    project = Project(dest)
    result.input_digest = digest_files(dest, [p for p in dest.rglob("*") if p.is_file()])
    if _validated_manifest(result, project) is None:
        return
    for p in sorted(dest.rglob("*")):
        if p.is_file():
            result.artifact(p)
    result.extra["details"] = {"project": display_path(dest),
                               "next": ["arc1 build %s" % display_path(dest),
                                        "arc1 test %s" % display_path(dest)]}


# ---------------------------------------------------------------- build

def build(result, project):
    result.command = "arc1 build %s" % project.label
    result.input_digest = project.build_digest()
    doc = _validated_manifest(result, project)
    if doc is None:
        return
    lock = load_lock()
    cc, cc_version = find_cc(lock)
    if not cc:
        result.verdict = "NOT_AVAILABLE"
        result.fail("DOCTOR", cc_version)
        return

    gen = project.build_dir / "gen"
    host = project.build_dir / "host"
    logs = project.build_dir / "logs"
    for d in (gen, host, logs):
        d.mkdir(parents=True, exist_ok=True)

    sprites = []
    for a in doc["assets"]:
        p = project.root / a["path"]
        try:
            w, h, px = asset_tool.parse_sprite(p.read_text(encoding="utf-8"), a["path"])
        except asset_tool.AssetError as e:
            result.fail("ASSET", str(e), a["path"])
            return
        sprites.append((p.stem.upper(), w, h, px, a["path"], a["sha256"]))
    header = gen / "arc1_assets.h"
    header.write_text(asset_tool.header_for(sprites), encoding="utf-8")

    sources = sorted((project.root / "src").rglob("*.c"))
    if not sources:
        result.fail("BUILD", "no C sources under src/")
        return

    inside_sdk = SDK_ROOT in project.root.parents

    def rel(p):
        # Relative paths keep logs machine-independent for projects in the SDK tree.
        if inside_sdk or project.root in Path(p).resolve().parents:
            return os.path.relpath(p, project.root).replace(os.sep, "/")
        return str(p)

    binary = project.binary(doc["name"])
    argv = ([cc, "-std=c11"] + lock["c_compiler"]["flags"] +
            ["-I", rel(SDK_ROOT / "sdk" / "include"), "-I", rel(gen)] +
            [rel(s) for s in sources + RUNTIME_SOURCES] + ["-o", rel(binary)])
    code, out = run_tool(argv, project.root, COMPILE_TIMEOUT_S)
    log = logs / "build.log"
    shown = [os.path.basename(cc)] + argv[1:]
    log.write_text("# compiler: %s\n$ %s\n%sexit: %s\n" % (cc_version, " ".join(shown), out, code),
                   encoding="utf-8")
    result.extra["log_sha256"] = sha256_file(log)
    result.artifact(log)
    if code != 0:
        result.fail("BUILD", "compiler exited with %s; see %s" % (code, display_path(log)))
        return
    stamp = host / "build-stamp.json"
    stamp.write_text(canonical_json({"input_digest": result.input_digest,
                                     "binary_sha256": sha256_file(binary)}), encoding="utf-8")
    for p in (binary, header, stamp):
        result.artifact(p)
    result.warn("Host build only; no ARC-1 target toolchain exists yet")
    result.extra["details"] = {"compiler": cc_version, "abi": "0.2-proposed", "target": "host"}


def _fresh_binary(result, project):
    """Returns (doc, binary) when an up-to-date host build exists, else fails."""
    doc = _validated_manifest(result, project)
    if doc is None:
        return None, None
    binary = project.binary(doc["name"])
    stamp = project.build_dir / "host" / "build-stamp.json"
    try:
        info = json.loads(stamp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        info = {}
    if not binary.is_file() or info.get("input_digest") != project.build_digest() \
            or info.get("binary_sha256") != sha256_file(binary):
        result.fail("BUILD_STALE", "no up-to-date host build; run `arc1 build %s` first" % project.label)
        return None, None
    return doc, binary


def run_game(project, binary, frames, replay, outdir, dump=()):
    """Runs the host binary. Returns (exit code, output, trace path, {frame: ppm path})."""
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    trace = outdir / "trace.txt"
    argv = [str(binary), "--frames", str(frames), "--trace", str(trace), "--dump-dir", str(outdir)]
    if replay is not None:
        argv += ["--replay", str(replay)]
    if dump:
        argv += ["--dump", ",".join(str(f) for f in sorted(dump))]
    code, out = run_tool(argv, project.root, SIM_TIMEOUT_S)
    frames_out = {f: outdir / ("frame_%06d.ppm" % f) for f in dump if f < frames}
    return code, out, trace, frames_out


def _replay_path(project, rel):
    if rel is None:
        return None
    p = bounded(project.root, rel, "replay path")
    if not p.is_file():
        raise UsageError("replay not found: %s" % rel)
    return p


# ---------------------------------------------------------------- sim

def sim(result, project, frames, replay, dump):
    result.command = "arc1 sim %s" % project.label
    result.input_digest = project.build_digest()
    doc, binary = _fresh_binary(result, project)
    if doc is None:
        return
    replay_p = _replay_path(project, replay)
    outdir = project.build_dir / "sim"
    code, out, trace, ppms = run_game(project, binary, frames, replay_p, outdir, dump)
    log = outdir / "sim.log"
    log.write_text(out + "exit: %s\n" % code, encoding="utf-8")
    result.artifact(log)
    result.extra["log_sha256"] = sha256_file(log)
    if code != 0:
        result.fail("SIM", "host runtime exited with %s; see %s" % (code, display_path(log)))
        return
    result.artifact(trace)
    for p in ppms.values():
        result.artifact(p)
    for w in HOST_WARNINGS:
        result.warn(w)
    lines = trace.read_text(encoding="utf-8").splitlines()
    result.extra["details"] = {
        "frames": frames, "replay": replay,
        "trace_sha256": sha256_file(trace),
        "last_frame_fnv1a64": lines[-1].split()[2] if lines else None,
        "hardware_descriptor": {"path": display_path(HOST_SIM), "sha256": sha256_file(HOST_SIM),
                                "simulation_only": True},
    }


# ---------------------------------------------------------------- test

def _first_divergence(a_text, b_text):
    a, b = a_text.splitlines(), b_text.splitlines()
    for i in range(max(len(a), len(b))):
        if i >= len(a) or i >= len(b) or a[i] != b[i]:
            return i
    return None


def _golden_paths(project, t):
    gjson = bounded(project.root, t["golden"], "golden path")
    gtrace = gjson.with_suffix(".trace")
    return gjson, gtrace


def _load_golden(project, t, failures):
    gjson, gtrace = _golden_paths(project, t)
    if not gjson.is_file():
        failures.append("golden %s missing; record it with `arc1 test --update-golden` "
                        "(review-sensitive, TST-003)" % t["golden"])
        return None, None
    g = load_json(gjson, "golden")
    errs = schema_validator("golden.schema.json").errors(g)
    if errs:
        failures.append("golden %s invalid: %s" % (t["golden"], errs[0]))
        return None, None
    tpath = bounded(project.root, g["trace"], "golden trace")
    if not tpath.is_file() or sha256_file(tpath) != g["trace_sha256"]:
        failures.append("golden trace %s missing or does not match its recorded digest" % g["trace"])
        return None, None
    return g, tpath.read_text(encoding="utf-8")


def _run_one(project, binary, t, outdir):
    replay_p = _replay_path(project, t["replay"])
    code, out, trace, ppms = run_game(project, binary, t["frames"], replay_p, outdir, t.get("dump", []))
    if code != 0 or not trace.is_file():
        return None, "host runtime exited with %s: %s" % (code, out.strip()[-300:])
    frames = {str(f): sha256_file(p) for f, p in ppms.items() if p.is_file()}
    if len(frames) != len(ppms):
        return None, "requested frame dumps were not produced"
    return {"trace": trace, "trace_text": trace.read_text(encoding="utf-8"),
            "trace_sha256": sha256_file(trace), "frames": frames,
            "replay_sha256": sha256_file(replay_p) if replay_p else None}, None


def _record_golden(project, t, run):
    gjson, gtrace = _golden_paths(project, t)
    gjson.parent.mkdir(parents=True, exist_ok=True)
    gtrace.write_text(run["trace_text"], encoding="utf-8")
    doc = {"schema": "arc1.golden/0.2", "test_id": t["id"], "frames": t["frames"],
           "replay_sha256": run["replay_sha256"], "trace": rel_posix(gtrace, project.root),
           "trace_sha256": run["trace_sha256"], "frame_sha256": run["frames"], "palette": "arc1-0.2",
           "note": "Recorded by `arc1 test --update-golden`. Changing this file is review-sensitive (SEC-002)."}
    gjson.write_text(canonical_json(doc), encoding="utf-8")
    return [gjson, gtrace]


def test(result, project, update_golden=False, only=None):
    result.command = "arc1 test %s%s" % (project.label, " --update-golden" if update_golden else "")
    result.input_digest = sha256_bytes(("%s\n%s" % (
        project.build_digest(),
        digest_files(project.root, [p for p in (project.root / "tests").rglob("*") if p.is_file()])
        if (project.root / "tests").is_dir() else "")).encode())
    doc, binary = _fresh_binary(result, project)
    if doc is None:
        return
    plan = load_json(project.root / TEST_PLAN, "test plan")
    errs = schema_validator("game-tests.schema.json").errors(plan)
    if errs:
        for ptr, msg in errs:
            result.fail("SCHEMA", "%s: %s" % (ptr, msg), TEST_PLAN)
        return
    ids = [t["id"] for t in plan["tests"]]
    if len(set(ids)) != len(ids):
        result.fail("SCHEMA", "duplicate test ids in %s" % TEST_PLAN)
        return
    tests = [t for t in plan["tests"] if not only or t["id"] in only]
    if only and len(tests) != len(set(only)):
        raise UsageError("unknown test id(s): %s" % sorted(set(only) - set(ids)))

    outcomes, log_lines, sensitive = [], [], []
    for t in tests:
        failures, notes = [], []
        outroot = project.build_dir / "test" / t["id"]
        try:
            if t["kind"] == "golden":
                run, err = _run_one(project, binary, t, outroot / "run1")
                if err:
                    failures.append(err)
                elif update_golden:
                    for p in _record_golden(project, t, run):
                        result.artifact(p)
                    sensitive.append(t["golden"])
                    notes.append("golden re-recorded")
                else:
                    g, gtext = _load_golden(project, t, failures)
                    if g:
                        if g["frames"] != t["frames"]:
                            failures.append("golden records %d frames, test runs %d" % (g["frames"], t["frames"]))
                        if g["replay_sha256"] != run["replay_sha256"]:
                            failures.append("replay input differs from the one the golden was recorded with")
                        if run["trace_sha256"] != g["trace_sha256"]:
                            i = _first_divergence(gtext, run["trace_text"])
                            failures.append("trace differs from golden; first divergent frame %s" % i)
                        if set(run["frames"]) != set(g["frame_sha256"]):
                            failures.append("dumped frame set %s differs from golden %s" % (
                                sorted(run["frames"], key=int), sorted(g["frame_sha256"], key=int)))
                        for f, h in sorted(run["frames"].items(), key=lambda kv: int(kv[0])):
                            if g["frame_sha256"].get(f, h) != h:
                                failures.append("frame %s image differs from golden" % f)
            elif t["kind"] == "determinism":
                runs = []
                for k in range(t.get("runs", 2)):
                    run, err = _run_one(project, binary, t, outroot / ("run%d" % (k + 1)))
                    if err:
                        failures.append(err)
                        break
                    runs.append(run)
                for k, r in enumerate(runs[1:], 2):
                    if r["trace_sha256"] != runs[0]["trace_sha256"] or r["frames"] != runs[0]["frames"]:
                        i = _first_divergence(runs[0]["trace_text"], r["trace_text"])
                        failures.append("run %d differs from run 1 (first divergent frame %s)" % (k, i))
            elif t["kind"] == "must_differ":
                run, err = _run_one(project, binary, t, outroot / "run1")
                if err:
                    failures.append(err)
                else:
                    g, _ = _load_golden(project, t, failures)
                    if g and run["trace_sha256"] == g["trace_sha256"]:
                        failures.append("negative control: output matches golden %s, so that golden "
                                        "cannot detect this input change" % t["golden"])
        except UsageError as e:
            failures.append(str(e))
        verdict = "FAIL" if failures else "PASS"
        outcomes.append({"id": t["id"], "kind": t["kind"], "verdict": verdict,
                         "failures": failures, "notes": notes})
        log_lines.append("%s %s %s" % (verdict, t["kind"], t["id"]))
        log_lines += ["    " + f for f in failures]

    log = project.build_dir / "test" / "test.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    result.artifact(log)
    result.extra["log_sha256"] = sha256_file(log)
    failed = [o for o in outcomes if o["verdict"] == "FAIL"]
    for o in failed:
        result.fail("TEST", "%s: %s" % (o["id"], "; ".join(o["failures"])))
    for path in sensitive:
        result.warn("TST-003 review-sensitive: golden baseline %s re-recorded; disclose it in the pass record" % path)
    for w in HOST_WARNINGS:
        result.warn(w)
    result.extra["test_count"] = len(outcomes)
    result.extra["failed_count"] = len(failed)
    result.extra["details"] = {"tests": outcomes, "sensitive_events": sensitive,
                               "hardware_descriptor": {"path": display_path(HOST_SIM),
                                                       "sha256": sha256_file(HOST_SIM)}}


def report_path(project, name):
    return project.reports_dir / ("%s.json" % name)


def finish(result, project, name):
    return write_report(result, report_path(project, name))
