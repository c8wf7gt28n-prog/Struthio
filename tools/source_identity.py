"""Source identity and inventory of a Ledger tree (F00).

usage: python3 tools/source_identity.py [--root .] [--exclude PREFIX ...] [--inventory OUT.csv] [--json OUT.json]

Files: `git ls-files` in a git checkout, otherwise every file except .git/, .ledger/ (private state), build/,
examples/*/reports/ and caches, the same rule as tools/package_ledger15.py. RELEASE_MANIFEST.json is left out
because a release ZIP adds it.
The tree digest is SHA-256 over sorted lines "<sha256>  <bytes>  <path>\\n". It covers bytes only, not file modes
(a release ZIP sets launcher modes explicitly), and it is not Git ancestry: it documents what the tree contains.
The area column is a coarse path-based label for orientation; the release-profile inventory belongs to Pass 01.
"""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".ledger", "build", "__pycache__", ".ruff_cache"}
AREAS = (  # first matching prefix wins
    ("docs/vendor/", "vendor-original"), ("vendor_kb/", "vendor-index-source"), ("passes/", "pass-record-evidence"),
    ("hardware/compact-arc1/R10_WORK/cad/", "cad"), ("hardware/compact-arc1/R10_WORK/fpga", "fpga-rtl"),
    ("hardware/compact-arc1/R10_WORK/firmware/", "firmware"), ("hardware/", "hardware"), ("firmware/", "firmware"),
    ("software/", "software"), ("sdk/", "sdk"), ("workbench/", "ledger-application"), ("tests/", "tests"),
    ("tools/", "tools"), ("docs/", "docs"), ("examples/", "examples"), ("cartridges/", "games"),
    ("superclip/", "remote-client"), ("policy/", "policy"),
)


def files(root):
    if (root / ".git").exists():
        out = subprocess.run(["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True).stdout
        names = [p for p in out.decode().split("\0") if p and (root / p).is_file()]
    else:
        names = []
        for p in root.rglob("*"):
            parts = p.relative_to(root).parts
            skip = any(d in SKIP_DIRS for d in parts[:-1]) or (parts[0] == "examples" and "reports" in parts[:-1])
            if p.is_file() and not skip and p.suffix != ".pyc":
                names.append(p.relative_to(root).as_posix())
    return sorted(n for n in names if n != "RELEASE_MANIFEST.json")


def area(path):
    return next((a for prefix, a in AREAS if path.startswith(prefix)), "project-root" if "/" not in path else "other")


def identity(root, exclude=()):
    rows = []
    for name in files(root):
        if any(name.startswith(p) for p in exclude):
            continue
        data = (root / name).read_bytes()
        rows.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), area=area(name)))
    h = hashlib.sha256()
    for r in rows:
        h.update(("%s  %d  %s\n" % (r["sha256"], r["bytes"], r["path"])).encode())
    return h.hexdigest(), rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--exclude", nargs="*", default=[], help="path prefixes left out (e.g. the record holding the digest)")
    ap.add_argument("--inventory", help="write path,bytes,sha256,area CSV")
    ap.add_argument("--json", help="write the summary JSON")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    digest, rows = identity(root, a.exclude)
    summary = dict(schema="arc-ledger.source-identity/1", tree_sha256=digest, files=len(rows),
                   bytes=sum(r["bytes"] for r in rows), excluded_prefixes=a.exclude,
                   method="SHA-256 over sorted '<sha256>  <bytes>  <path>' lines; bytes only, no modes, no Git ancestry",
                   areas={k: sum(1 for r in rows if r["area"] == k) for k in sorted({r["area"] for r in rows})})
    if a.inventory:
        with open(a.inventory, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["path", "bytes", "sha256", "area"], lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    if a.json:
        Path(a.json).write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
