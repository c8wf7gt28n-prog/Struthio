"""Shared plumbing: SDK paths, digests, bounded paths, sandboxed subprocesses,
schema loading and the tool-result contract (CLI-001..CLI-003)."""

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .jsonschema_lite import SchemaError, Validator

SDK_VERSION = "0.2.0-dev"
SCHEMA_REVISION = "0.2"
RESULT_SCHEMA = "arc1.tool-result/0.2"

SDK_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = SDK_ROOT / "sdk" / "schemas"
LOCK_FILE = SDK_ROOT / "tools" / "lock" / "toolchain.lock.json"

# Evidence ladder (spec section 6.2). NONE: nothing was executed or observed.
EVIDENCE_LEVELS = ("NONE", "DESIGN", "STATIC_CHECK", "HOST_SIM", "RTL_SIM",
                   "FPGA_PNR", "BOARD_TEST")

VERDICTS = ("PASS", "FAIL", "ERROR", "NOT_AVAILABLE", "NOT_RUN")

# Documented exit codes (docs/CLI.md).
EXIT_CODES = {"PASS": 0, "FAIL": 1, "ERROR": 2, "NOT_AVAILABLE": 3, "NOT_RUN": 3}
EXIT_INTERNAL = 4

COMPILE_TIMEOUT_S = 120
SIM_TIMEOUT_S = 60


class UsageError(Exception):
    """Invalid invocation or input that the tool refuses to process."""


# ---------------------------------------------------------------- digests

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def digest_files(base, files):
    """Order-independent digest over (relative path, content hash) pairs."""
    lines = []
    for f in sorted(files, key=lambda p: rel_posix(p, base)):
        lines.append("%s  %s\n" % (sha256_file(f), rel_posix(f, base)))
    return sha256_bytes("".join(lines).encode())


def rel_posix(path, base):
    return Path(os.path.relpath(Path(path).resolve(), Path(base).resolve())).as_posix()


def display_path(path):
    """Path as shown in reports: relative to the SDK root when inside it."""
    p = Path(path).resolve()
    try:
        return p.relative_to(SDK_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


# ---------------------------------------------------------------- safety

def bounded(base, rel, what="path"):
    """Resolves rel inside base, refusing absolute paths and escapes (CLI-003)."""
    if not isinstance(rel, str) or not rel or "\x00" in rel:
        raise UsageError("%s must be a non-empty relative path" % what)
    if os.path.isabs(rel) or re.match(r"^[A-Za-z]:", rel):
        raise UsageError("%s %r must be relative" % (what, rel))
    base = Path(base).resolve()
    target = (base / rel).resolve()
    if target != base and base not in target.parents:
        raise UsageError("%s %r escapes %s" % (what, rel, display_path(base)))
    return target


def scrubbed_env():
    """Minimal environment for child processes: no credentials or tokens."""
    env = {"PATH": os.environ.get("PATH", os.defpath), "LC_ALL": "C", "LANG": "C",
           "TZ": "UTC", "SOURCE_DATE_EPOCH": "0"}
    for key in ("SYSTEMROOT", "TEMP", "TMP"):  # required by toolchains on Windows
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def _limits():  # pragma: no cover - runs in the child
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 << 20, 256 << 20))


def run_tool(argv, cwd, timeout):
    """Runs argv with a timeout, scrubbed env and POSIX resource limits.
    Returns (exit_code or None on timeout, combined output text)."""
    kwargs = {}
    if os.name == "posix":
        kwargs["preexec_fn"] = _limits
    try:
        p = subprocess.run(argv, cwd=str(cwd), env=scrubbed_env(), timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           stdin=subprocess.DEVNULL, **kwargs)
    except subprocess.TimeoutExpired as e:
        out = e.output.decode("utf-8", "replace") if e.output else ""
        return None, out + "\n[arc1] process exceeded %ss timeout\n" % timeout
    except OSError as e:
        return 127, "[arc1] cannot execute %s: %s\n" % (argv[0], e)
    return p.returncode, p.stdout.decode("utf-8", "replace")


# ---------------------------------------------------------------- schemas

_validators = {}


def schema_validator(name):
    if name not in _validators:
        path = SCHEMA_DIR / name
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise SchemaError("cannot load schema %s: %s" % (name, e))
        _validators[name] = Validator(schema)
    return _validators[name]


def load_json(path, what):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise UsageError("%s not found: %s" % (what, display_path(path)))
    except ValueError as e:
        raise UsageError("%s is not valid JSON (%s): %s" % (what, e, display_path(path)))


# ---------------------------------------------------------------- toolchain

def load_lock():
    return load_json(LOCK_FILE, "toolchain lock")


def find_cc(lock=None):
    """Returns (path, version line) of the C compiler, or (None, reason)."""
    lock = lock or load_lock()
    candidates = lock["c_compiler"]["candidates"]
    wanted = os.environ.get("ARC1_CC")
    if wanted:
        if wanted not in candidates:
            return None, "ARC1_CC=%r is not a locked candidate %r" % (wanted, candidates)
        candidates = [wanted]
    for name in candidates:
        path = shutil.which(name)
        if path:
            code, out = run_tool([path, "--version"], SDK_ROOT, 20)
            first = out.strip().splitlines()[0] if out.strip() else "unknown"
            if code == 0:
                return path, first
    return None, "no C compiler found among %r" % (candidates,)


_toolchain_cache = {}


def toolchain_digest():
    """Digest of the lock file plus the tool versions actually in use."""
    key = os.environ.get("ARC1_CC", "")
    if key not in _toolchain_cache:
        _, cc_version = find_cc()
        parts = {
            "lock_sha256": sha256_file(LOCK_FILE),
            "python": platform.python_version(),
            "cc": cc_version,
        }
        _toolchain_cache[key] = (sha256_bytes(canonical_json(parts).encode()), parts)
    return _toolchain_cache[key]


# ---------------------------------------------------------------- results

class Result:
    """Builds a tool result that conforms to sdk/schemas/tool-result.schema.json."""

    def __init__(self, command, evidence_level):
        assert evidence_level in EVIDENCE_LEVELS
        self.command = command
        self.evidence_level = evidence_level
        self.verdict = "PASS"
        self.warnings = []
        self.failures = []
        self.artifacts = []  # (display path, absolute path)
        self.input_digest = None
        self.board_id = None
        self.extra = {}

    def fail(self, code, message, path=None):
        entry = {"code": code, "message": message}
        if path is not None:
            entry["path"] = path
        self.failures.append(entry)
        if self.verdict == "PASS":
            self.verdict = "FAIL"

    def warn(self, message):
        if message not in self.warnings:
            self.warnings.append(message)

    def artifact(self, path):
        self.artifacts.append(Path(path).resolve())

    def to_dict(self):
        # CLI-001: never report success without the promised artifacts.
        arts = []
        for p in self.artifacts:
            if p.is_file():
                arts.append({"path": display_path(p), "sha256": sha256_file(p)})
            else:
                self.fail("CLI-001", "promised artifact missing", display_path(p))
        tc_digest, _ = toolchain_digest()
        inp = self.input_digest or sha256_bytes(self.command.encode())
        out = {
            "schema_version": RESULT_SCHEMA,
            "sdk_version": SDK_VERSION,
            "command": self.command,
            "invocation_id": sha256_bytes(
                ("%s\n%s\n%s" % (self.command, inp, tc_digest)).encode())[:32],
            "toolchain_digest": tc_digest,
            "input_digest": inp,
            "evidence_level": self.evidence_level,
            "verdict": self.verdict,
            "board_id": self.board_id,
            "warnings": self.warnings,
            "failure_reasons": self.failures,
            "artifacts": sorted(arts, key=lambda a: a["path"]),
        }
        out.update(self.extra)
        errs = schema_validator("tool-result.schema.json").errors(out)
        if errs:  # a malformed report is an SDK bug; refuse to emit it as valid
            out["verdict"] = "ERROR"
            out["failure_reasons"].append({
                "code": "CLI-001",
                "message": "internal: result violates tool-result schema: %s" % (errs,)})
        return out

    def exit_code(self, data):
        return EXIT_CODES[data["verdict"]]


def write_report(result, path):
    """Writes the report JSON and returns its dict (the report cannot list
    its own digest; consumers hash the file)."""
    data = result.to_dict()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(canonical_json(data), encoding="utf-8")
    return data


def python_ok(lock):
    need = tuple(int(x) for x in lock["python"]["min"].split("."))
    return sys.version_info[:len(need)] >= need
