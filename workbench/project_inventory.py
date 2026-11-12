"""Relocatable source inventory; inferred ownership is explicitly marked inferred."""

from __future__ import annotations
import hashlib
import json
import os
import ast
import re
from pathlib import Path

EXCLUDED = {
    ".git",
    ".ledger",
    "__pycache__",
    ".venv",
    "node_modules",
    "build",
    ".pytest_cache",
}


def paths(root):
    root = Path(root).resolve()
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in EXCLUDED
            and (Path(directory)/d).relative_to(root).as_posix() != 'examples/hello_arc1/reports'
            and not d.startswith(".")
            and not (Path(directory) / d).is_symlink()
        )
        for name in sorted(files):
            p = Path(directory) / name
            if name.startswith(".") and name not in ('.gitignore','.gitattributes','.editorconfig'):
                continue
            if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(root):
                yield p


def hashes(root):
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths(root)
    }


def revision(items):
    return hashlib.sha256(
        json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def relationships(name, text, names):
    """Resolve local static imports/includes plus literal project references.

    This intentionally does not execute modules or guess dynamic dependencies.
    """
    edges = {other for other in names if other != name and other in text}
    parent = Path(name).parent
    if name.endswith(".py"):
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [a.name for a in node.names]
                if isinstance(node, ast.ImportFrom):
                    prefix = (
                        parent.parts[: len(parent.parts) - node.level + 1]
                        if node.level
                        else ()
                    )
                    base = ".".join((*prefix, node.module or "")).strip(".")
                    modules = [base] + [
                        ".".join((base, a.name)).strip(".") for a in node.names
                    ]
                for module in modules:
                    for suffix in (".py", "/__init__.py"):
                        ref = module.replace(".", "/") + suffix
                        if ref in names and ref != name:
                            edges.add(ref)
        except SyntaxError:
            pass
    for local in re.findall(
        r"(?:#\s*include\s*|\bfrom\s*|\bimport\s*)[\"\']([^\"\']+)[\"\']", text
    ):
        ref = os.path.normpath(str(parent / local)).replace(os.sep, "/")
        if ref in names and ref != name:
            edges.add(ref)
    return sorted(edges)


def inventory(root):
    root = Path(root).resolve()
    sources = hashes(root)
    rows = []
    duplicates = {}
    texts = {}
    for name in sources:
        p = root / name
        if p.stat().st_size < 500000:
            try:
                texts[name] = p.read_text(encoding="utf-8")
            except (UnicodeError, OSError):
                pass
    graph = {
        name: relationships(name, texts.get(name, ""), sources) for name in sources
    }
    reverse = {name: [] for name in sources}
    for consumer, dependencies in graph.items():
        for dep in dependencies:
            reverse[dep].append(consumer)
    for name, sha in sources.items():
        if name.startswith("project/records/"):
            domain, kind, protected = "Database ROM catalog and reference data", "reference", True
        elif name.startswith("hardware/"):
            domain, kind, protected = "ARC-1 hardware engineering", "reference", True
        elif name.startswith("software/arcos/"):
            domain, kind, protected = "ARC-OS system software and SDK", "source", not name.startswith(("software/arcos/src/","software/arcos/games/"))
            if "/upstream/" in name:kind="reference"
        elif name.startswith("software/struthio/"):
            domain, kind, protected = "STRUTHIO native C", "source", False
        elif name.startswith("examples/struthio_arcade/"):
            domain, kind, protected = "STRUTHIO original reference", "reference", True
        elif name.startswith(("passes/", "evidence/")):
            domain, kind, protected = "Engineering evidence", "evidence", True
        elif name.startswith(("tests/", "workbench/tests/")):
            domain, kind, protected = "Tests and simulations", "source", True
        elif name.startswith(("firmware/", "rtl/")):
            domain, kind, protected = "Firmware and FPGA development", "source", True
        elif name.startswith(("sdk/", "runtime/", "examples/")):
            domain, kind, protected = "ARC-1 SDK and runtime", "source", True
        else:
            domain, kind, protected = "Ledger application and tools", "source", False
        consumers = reverse[name]
        dependencies = graph[name]
        target = (
            "struthio.host"
            if domain == "STRUTHIO native C"
            else "ledger"
            if name.startswith("workbench/")
            else None
        )
        if name.startswith("sdk/"):
            target = "arc1.host-sdk"
        if name.startswith("software/arcos/"):
            target = "arcos.host" if "/upstream/" not in name else "arcos.kernel-reference"
        if name.startswith("examples/struthio_arcade/"):
            target = "struthio.javascript-reference"
        for chip in ("f133", "d213", "fpga45", "fpga12"):
            if "/" + chip + "/" in name or "/" + chip + "_" in name:
                target = (
                    "firmware." + chip if chip in ("f133", "d213") else "rtl." + chip
                )
        generated = name.endswith(("_generated.h", ".elf", ".bin", ".o", ".ppm"))
        if generated and not protected:
            kind = "generated"
        if name.startswith('software/struthio/') and (Path(name).name.startswith(('test_','state_oracle','ring_oracle')) or generated):
            protected=True
        purpose = (
            "Test or oracle"
            if Path(name).name.startswith(("test_", "state_oracle", "ring_oracle"))
            else "Build/replay output"
            if generated
            else "Interface declaration"
            if name.endswith(".h")
            else "Source implementation"
            if name.endswith((".c", ".py", ".js", ".mjs", ".sv", ".v"))
            else "Engineering document"
            if name.endswith((".md", ".txt", ".docx", ".pdf"))
            else domain + " input"
        )
        rows.append(
            dict(
                path=name,
                sha256=sha,
                type=Path(name).suffix or "extensionless",
                purpose=purpose,
                subsystem=domain,
                owning_build_target=target,
                dependencies=dependencies,
                consumers=consumers,
                classification=kind,
                editable=not protected,
                protected=protected,
                reproducible=False,
                relationship_method="static local Python/JS imports, C includes, literal full-path references; dynamic edges not exhaustive",
                ownership_confidence="inferred; unassigned targets require review",
            )
        )
        duplicates.setdefault(sha, []).append(name)
    return dict(
        schema="arc-ledger.inventory/1",
        revision=revision(sources),
        files=rows,
        duplicates=[v for v in duplicates.values() if len(v) > 1],
        consolidation={
            "removed": [],
            "policy": "No deletion without semantic reference review",
            "javascript_authority": "examples/struthio_arcade",
            "native_authority": "software/struthio",
            "immutable_native_origin": "hardware/compact-arc1/R10_WORK/closure_p11_struthio/port",
        },
    )
