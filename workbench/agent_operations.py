"""Pass 1.4 read-only agent services. Hardware observations are not qualification."""

import hashlib
import json
import math
import platform
import runpy
import shutil
import subprocess
import sys
from .hardware_review import BASE, REFS
from .project_inventory import hashes, relationships, revision

CONTRACT = "arc-ledger.agent-operations/1.4"
FIELDS = {
    "system.inspect": ({}, []),
    "hardware.sources": ({}, []),
    "hardware.component_nets": (
        {
            "component": {"type": "string"},
            "pin": {"type": "string"},
            "expected_sources": {"type": "object"},
        },
        ["component"],
    ),
    "files.references": ({"path": {"type": "string"}}, ["path"]),
    "candidates.read": (
        {"id": {"type": "string"}, "path": {"type": "string"}},
        ["id", "path"],
    ),
    "evidence.compare": (
        {"baseline": {"type": "string"}, "candidate": {"type": "string"}},
        ["baseline", "candidate"],
    ),
}


def validate(value, spec, name="params"):
    types = {
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    kind = spec.get("type")
    if kind and (
        not isinstance(value, types[kind])
        or (kind in ("number", "integer") and isinstance(value, bool))
    ):
        raise ValueError("Invalid type: " + name)
    if kind in ("number", "integer") and (
        not math.isfinite(value)
        or value < spec.get("minimum", -math.inf)
        or value > spec.get("maximum", math.inf)
    ):
        raise ValueError("Out of bounds: " + name)
    if kind == "string" and not spec.get("minLength", 0) <= len(value) <= spec.get(
        "maxLength", 1200000
    ):
        raise ValueError("Invalid length: " + name)
    if "enum" in spec and value not in spec["enum"]:
        raise ValueError("Invalid choice: " + name)
    if kind == "array":
        if len(value) > 1000:
            raise ValueError("Too many items")
        for item in value:
            validate(item, spec.get("items", {}), name + "[]")
    if kind == "object":
        props = spec.get("properties", {})
        if set(spec.get("required", [])) - set(value):
            raise ValueError("Missing fields")
        if spec.get("additionalProperties") is False and set(value) - set(props):
            raise ValueError("Unknown fields")
        for key, item in value.items():
            if key in props:
                validate(item, props[key], name + "." + key)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment():
    tools = []
    commands = {
        "gcc": ["--version"],
        "clang": ["--version"],
        "node": ["--version"],
        "iverilog": ["-V"],
        "vvp": ["-V"],
        "yosys": ["-V"],
        "kicad-cli": ["version"],
        "riscv64-unknown-elf-gcc": ["--version"],
        "wsl": ["--status"],
    }
    for name, args in commands.items():
        executable = shutil.which(name)
        row = dict(name=name, executable=executable, status="BLOCKED", qualified=False)
        if executable:
            try:
                p = subprocess.run(
                    [executable, *args],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=3,
                    stdin=subprocess.DEVNULL,
                )
                row.update(
                    status="DETECTED" if p.returncode == 0 else "PROBE_FAILED",
                    argv=[executable, *args],
                    exit_status=p.returncode,
                    version=(p.stdout + p.stderr)[:12000],
                )
            except (OSError, subprocess.TimeoutExpired) as e:
                row.update(status="PROBE_FAILED", error=str(e))
        tools.append(row)
    return dict(
        schema=CONTRACT,
        platform=platform.platform(),
        distribution=platform.freedesktop_os_release()
        if sys.platform.startswith("linux")
        else {},
        python=sys.version,
        tools=tools,
        qualification={"Windows": "NOT_RUN", "Debian": "NOT_RUN"},
        notice="Detection is not qualification. Ubuntu is not native Debian.",
    )


def hardware_sources(k):
    from .hardware_nav import devices

    rows = []
    for device in devices(k.root):
        for group in device.groups:
            for name in group.sources:
                if not name.startswith("hardware/"):
                    continue
                path = k.root / name
                members = sorted(path.rglob("*")) if path.is_dir() else [path]
                rows.append(
                    dict(
                        component=device.id,
                        category=group.title,
                        path=name,
                        exists=path.exists(),
                        files={
                            p.relative_to(k.root).as_posix(): sha(p)
                            for p in members
                            if p.is_file()
                            and not p.is_symlink()
                            and "__pycache__" not in p.parts
                        },
                    )
                )
    index = k.safe(str(BASE / "closure_p8/P8_CROSSPROBE_INDEX.json"))
    checks = []
    for name, expected in json.loads(index.read_text())["source_hashes_sha256"].items():
        try:
            actual = sha(k.safe(name))
        except ValueError:
            actual = None
        checks.append(
            dict(
                path=name,
                expected=expected,
                actual=actual,
                state="MATCH"
                if actual == expected
                else "MISSING"
                if actual is None
                else "STALE",
            )
        )
    return dict(
        schema=CONTRACT,
        evidence_class="STATIC_CHECK",
        fabrication="HOLD",
        references=rows,
        missing_references=[r["path"] for r in rows if not r["exists"]],
        index_sha256=sha(index),
        index_references=checks,
        scope="Existing navigator and P8 bindings; not an exhaustive electrical audit",
    )


def component_nets(k, args):
    names = [
        str(BASE / x)
        for x in (
            "cad/NETLIST.xml",
            "cad/ARC1_R10.kicad_pcb",
            "board/r10_board_plan.json",
        )
    ]
    sources = {n: sha(k.safe(n)) for n in names}
    if "expected_sources" in args and args["expected_sources"] != sources:
        raise ValueError("Stale hardware source binding")
    checker = k.safe(str(BASE / "closure_p8/crossprobe.py"))
    index, _ = runpy.run_path(str(checker))["create_index"](k.root)
    if index["source_hashes_sha256"] != sources or any(
        sha(k.safe(n)) != h for n, h in sources.items()
    ):
        raise ValueError("Source changed during lookup")
    ref = REFS.get(args["component"].lower(), args["component"].upper())
    pins = [
        p
        for p in index["pin_crossprobe"]
        if p["component"] == ref and ("pin" not in args or p["pin"] == args["pin"])
    ]
    if not pins:
        raise ValueError("No component/pin found")
    nets = {
        p["net"]: index["nets"][p["net"]] for p in pins if p["net"] in index["nets"]
    }
    mentions = []
    for path in sorted((k.root / BASE).rglob("*.lpf")):
        for line, text in enumerate(path.read_text().splitlines(), 1):
            if any('"' + name + '"' in text for name in nets):
                mentions.append(
                    dict(
                        path=path.relative_to(k.root).as_posix(),
                        sha256=sha(path),
                        line=line,
                        text=text,
                    )
                )
    return dict(
        schema=CONTRACT,
        reference=ref,
        pins=pins,
        nets=nets,
        source_hashes=sources,
        checker_sha256=sha(checker),
        constraint_mentions=mentions,
        evidence_class="STATIC_CHECK",
        fabrication="HOLD",
        limitations=[
            "Netlist/PCB associations only. No native ERC/DRC executed.",
            "Literal LPF mentions do not prove legal pins, voltage or timing.",
            "Unassigned pads, absent constraints and export-to-schematic freshness remain unproven.",
        ],
    )


def dispatch(k, op, args):
    if op == "system.inspect":
        return environment()
    if op == "hardware.sources":
        return hardware_sources(k)
    if op == "hardware.component_nets":
        return component_nets(k, args)
    if op == "candidates.read":
        c = k.record("candidates", args["id"])
        path = k.safe(args["path"], k.candidate_root(c["id"]))
        data = path.read_bytes()
        if len(data) > 1048576:
            raise ValueError("Text read limit is 1 MiB")
        return dict(
            id=c["id"],
            path=args["path"],
            sha256=sha(path),
            content=data.decode("utf-8"),
        )
    if op == "files.references":
        path = k.safe(args["path"])
        sources = hashes(k.root)
        consumers = []
        for name in sources:
            p = k.root / name
            if p.stat().st_size > 2000000:
                continue
            try:
                if args["path"] in relationships(name, p.read_text(), sources):
                    consumers.append(name)
            except UnicodeError:
                pass
        return dict(
            path=args["path"],
            sha256=sha(path),
            dependencies=relationships(args["path"], path.read_text(), sources),
            consumers=consumers,
            method="Static imports/includes and literal paths; dynamic edges incomplete",
        )
    if op == "evidence.compare":
        b = k.record("evidence", args["baseline"])
        c = k.record("evidence", args["candidate"])
        if (
            b["candidate"] is not None
            or c["candidate"] is None
            or b["tool"] != c["tool"]
        ):
            raise ValueError("Choose baseline/candidate evidence for the same tool")
        record = k.record("candidates", c["candidate"])

        def brief(e):
            return {
                n: e.get(n)
                for n in (
                    "id",
                    "job",
                    "tool",
                    "revision",
                    "state",
                    "exit_status",
                    "duration_seconds",
                    "error",
                    "artifacts",
                    "tool_versions",
                    "diagnostics",
                )
            }

        return dict(
            schema=CONTRACT,
            baseline=brief(b),
            candidate=brief(c),
            baseline_matches_snapshot=b["revision"] == record["revision"],
            candidate_current=c["revision"]
            == revision(hashes(k.candidate_root(c["candidate"]))),
            accepted_source_current=hashes(k.root) == record["base"],
            baseline_passed=b["state"] == "Completed",
            candidate_passed=c["state"] == "Completed",
            approval_required=True,
        )
    raise ValueError("Unknown operation")
