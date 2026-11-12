"""Bounded, strict record IO shared by engineering views and the Orange Book."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile


def canonical(value):
    """ARC JSON digest profile 1: sorted keys, UTF-8, finite values, no whitespace.

    This is a documented ARC profile, not an implementation of RFC 8785 JCS.
    Exact engineering decimals are strings. JSON numbers are finite metadata.
    """
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("DUPLICATE_MEMBER: " + key)
            result[key] = value
        return result
    def bad(value):
        raise ValueError("NON_FINITE_NUMBER: " + value)
    value = json.loads(data, object_pairs_hook=pairs, parse_constant=bad)
    def finite(obj):
        if isinstance(obj, float) and not math.isfinite(obj):
            raise ValueError("NON_FINITE_NUMBER")
        if isinstance(obj, dict):
            for x in obj.values(): finite(x)
        elif isinstance(obj, list):
            for x in obj: finite(x)
    finite(value)
    return value


def project_path(root, name, must_exist=True, private=False):
    root = Path(root).resolve()
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or "\x00" in name:
        raise ValueError("INVALID_PATH")
    parts = name.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError("INVALID_PATH")
    if any(p.startswith(".") for p in parts) and not (private and parts[0] == ".ledger" and all(not p.startswith(".") for p in parts[1:])):
        raise ValueError("PRIVATE_PATH")
    path = root.joinpath(*parts)
    if not path.resolve().is_relative_to(root):
        raise ValueError("PATH_ESCAPE")
    if any(p.is_symlink() for p in (path, *path.parents) if p == root or root in p.parents):
        raise ValueError("SYMLINK_PATH")
    if must_exist and not path.is_file():
        raise ValueError("MISSING_SOURCE: " + name)
    return path


def load(root, name, limit=4 * 1024 * 1024):
    path = project_path(root, name)
    if path.stat().st_size > limit:
        raise ValueError("RECORD_SIZE_LIMIT: " + name)
    return strict_json(path.read_bytes())


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, staged = tempfile.mkstemp(prefix=".arc-stage-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data.encode("utf-8") if isinstance(data, str) else data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
    finally:
        if os.path.exists(staged): os.unlink(staged)


def write_json(path, value):
    atomic(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def manifest(root, names):
    result = {}
    for name in sorted(set(names)):
        try:
            path = project_path(root, name)
            result[name] = {"sha256": sha(path), "bytes": path.stat().st_size}
        except ValueError as exc:
            if not str(exc).startswith("MISSING_SOURCE:"): raise
            result[name] = {"sha256": None, "bytes": None, "state": "MISSING"}
    return result


def currency(root, recorded):
    if not recorded:
        return "UNASSESSED", []
    changed = []
    missing = False
    current = manifest(root, recorded)
    for path, prior in recorded.items():
        now = current[path]
        expected = prior.get("sha256") if isinstance(prior, dict) else prior
        if now["sha256"] is None:
            missing = True
        if now["sha256"] != expected:
            changed.append({"path": path, "expected_sha256": expected, "current_sha256": now["sha256"]})
    return ("MISSING" if missing else "STALE" if changed else "CURRENT"), changed
