#!/usr/bin/env python3
"""Package ARC1_R85_ENGINEERING_SOURCE.zip: R85_WORK (sources + latest evidence) and the frozen inputs needed to
reproduce it (R05_BASELINE, R06_WORK, R07_WORK, R08_WORK and the root handoff files), with a SHA-256 manifest.
Usage: package_r85.py <out_dir>"""
import hashlib
import os
import shutil
import sys
import zipfile

R85 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ROOT = os.path.dirname(R85)
out_dir = sys.argv[1]
NAME = "ARC1_R85_ENGINEERING_SOURCE"
stage = os.path.join(out_dir, NAME)
shutil.rmtree(stage, ignore_errors=True)
latest = open(os.path.join(R85, "evidence", "LATEST.txt")).read().strip()


def ign(d, names):
    rel = os.path.relpath(d, R85)
    out = {n for n in names if n in ("build", "__pycache__") or n.endswith(".pyc")}
    if rel == "evidence":
        out |= {n for n in names if n.startswith("run_") and os.path.join("evidence", n) != latest}
    return out


shutil.copytree(R85, os.path.join(stage, "R85_WORK"), ignore=ign)
fb = os.path.join(R85, "fpga_ecp5", "build")
os.makedirs(os.path.join(stage, "R85_WORK", "fpga_ecp5", "build"))
for f in ("arc1_ecp5.bit", "arc1_ecp5.bit.sha256", "BUILD_REPORT.json", "BUILD_REPORT.md", "TOOL_VERSIONS.txt"):
    shutil.copy(os.path.join(fb, f), os.path.join(stage, "R85_WORK", "fpga_ecp5", "build", f))
fz = os.path.join(stage, "FROZEN_INPUTS")
for d in ("R05_BASELINE", "R06_WORK", "R07_WORK", "R08_WORK"):
    shutil.copytree(os.path.join(ROOT, d), os.path.join(fz, d), ignore=shutil.ignore_patterns("build", "__pycache__", "*.pyc"))
for f in os.listdir(ROOT):
    if os.path.isfile(os.path.join(ROOT, f)):
        shutil.copy(os.path.join(ROOT, f), os.path.join(fz, f))
shutil.copy(os.path.join(R85, "tools", "START_HERE_ARCHIVE.md"), os.path.join(stage, "START_HERE.md"))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


rows = []
for base, dirs, files in os.walk(stage):
    dirs.sort()
    for f in sorted(files):
        p = os.path.join(base, f)
        rows.append(f"{sha(p)}  {os.path.relpath(p, stage)}")
open(os.path.join(stage, "MANIFEST_SHA256.txt"), "w").write("\n".join(rows) + "\n")
zpath = os.path.join(out_dir, NAME + ".zip")
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for base, dirs, files in os.walk(stage):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(base, f)
            z.write(p, os.path.join(NAME, os.path.relpath(p, stage)))
print(zpath, len(rows) + 1, "files", sha(zpath))
