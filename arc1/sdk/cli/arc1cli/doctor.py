"""`arc1 doctor`: toolchain, schema and manifest health, with honest absences."""

import platform
import shutil
import tempfile
from pathlib import Path

from .core import (COMPILE_TIMEOUT_S, LOCK_FILE, SCHEMA_DIR, SDK_ROOT, UsageError, digest_files,
                   display_path, find_cc, load_json, python_ok, run_tool, schema_validator)
from .hardware import MANIFEST_DIR, check_manifest
from .jsonschema_lite import SchemaError
from .project import Project, check_package

PROBE = b"#include <stdint.h>\n_Static_assert(sizeof(uint32_t) == 4, \"c11\");\nint main(void) { return 0; }\n"


def doctor(result):
    result.command = "arc1 doctor"
    checks = []

    def record(name, status, detail):
        checks.append({"check": name, "status": status, "detail": detail})

    inputs = [LOCK_FILE] + sorted(SCHEMA_DIR.glob("*.json")) + sorted(MANIFEST_DIR.glob("*.json"))
    result.input_digest = digest_files(SDK_ROOT, inputs)

    # Schemas load and only use supported keywords.
    for p in sorted(SCHEMA_DIR.glob("*.schema.json")):
        try:
            schema_validator(p.name)
            record("schema " + p.name, "ok", "loads; keywords supported")
        except SchemaError as e:
            record("schema " + p.name, "fail", str(e))
            result.fail("G0", str(e), display_path(p))

    lock = load_json(LOCK_FILE, "toolchain lock")
    errs = schema_validator("toolchain-lock.schema.json").errors(lock)
    if errs:
        result.fail("SCHEMA", "toolchain lock: %s" % (errs,), display_path(LOCK_FILE))
        return

    py = platform.python_version()
    if python_ok(lock):
        record("python", "ok", py)
        if py not in lock["python"]["tested"]:
            result.warn("Python %s is not in the lock's tested list" % py)
    else:
        record("python", "fail", "%s < %s" % (py, lock["python"]["min"]))
        result.fail("DOCTOR", "Python %s is older than locked minimum %s" % (py, lock["python"]["min"]))

    cc, version = find_cc(lock)
    if not cc:
        record("c_compiler", "missing", version)
        result.fail("DOCTOR", version)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "probe.c"
            src.write_bytes(PROBE)
            code, out = run_tool([cc, "-std=c11"] + lock["c_compiler"]["flags"] + ["probe.c", "-o", "probe"],
                                 tmp, COMPILE_TIMEOUT_S)
        if code == 0:
            record("c_compiler", "ok", "%s (C11 probe compiled with locked flags)" % version)
            if version not in lock["c_compiler"]["tested"]:
                result.warn("C compiler '%s' is not in the lock's tested list" % version)
        else:
            record("c_compiler", "fail", out.strip()[-300:])
            result.fail("DOCTOR", "C11 probe failed with %s" % version)

    for p in sorted(MANIFEST_DIR.glob("*.json")):
        try:
            doc = load_json(p, "hardware manifest")
            errs = check_manifest(doc)
        except UsageError as e:
            errs = [("SCHEMA", "/", str(e))]
        if errs:
            record("manifest " + p.name, "fail", "%d finding(s)" % len(errs))
            for code, ptr, msg in errs:
                result.fail(code, "%s: %s" % (ptr, msg), display_path(p))
        else:
            label = "simulation_only" if doc["simulation_only"] else "board design (unverified)"
            record("manifest " + p.name, "ok", "%s, revision %s" % (label, doc["revision"]))

    for d in sorted((SDK_ROOT / "examples").iterdir()):
        if (d / "arc1.game.json").is_file():
            proj = Project(d)
            errs = check_package(proj, proj.manifest())
            record("example " + d.name, "fail" if errs else "ok",
                   "%d finding(s)" % len(errs) if errs else "package manifest valid")
            for code, ptr, msg in errs:
                result.fail(code, "%s: %s" % (ptr, msg), display_path(d / "arc1.game.json"))

    for tool in lock["optional_tools"]:
        found = shutil.which(tool["name"])
        record("optional " + tool["name"], "found" if found else "absent", tool["purpose"])

    record("physical_board", "NOT_AVAILABLE", "no device transport is implemented; G4 board gates not established")
    record("target_toolchain", "NOT_AVAILABLE", "no F133 RISC-V cross toolchain is locked yet")
    result.warn("No physical ARC-1 board: device commands report NOT_AVAILABLE")
    result.warn("Hardware manifest facts are DESIGN-level; physical boot, HDMI audio and 60 fps are not tested")
    result.extra["details"] = {"checks": checks}
