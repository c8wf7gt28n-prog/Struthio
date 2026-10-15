#!/usr/bin/env python3
"""Package ARC1_R08_ENGINEERING_SOURCE.zip (R08_DELIVERY_TEMPLATE layout).
Usage: package_r08.py <out_dir> <ARC1_R07_SOURCE_ORIGINAL.zip>"""
import hashlib, os, shutil, sys, zipfile
R08 = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
out_dir, r07zip = sys.argv[1], sys.argv[2]
NAME = "ARC1_R08_ENGINEERING_SOURCE"
stage = os.path.join(out_dir, NAME)
shutil.rmtree(stage, ignore_errors=True)
shutil.copytree(R08, os.path.join(stage, "R08_WORK"), ignore=shutil.ignore_patterns("build", "__pycache__", "*.pyc"))
os.makedirs(os.path.join(stage, "R07_PRESERVED"))
shutil.copy(r07zip, os.path.join(stage, "R07_PRESERVED", "ARC1_R07_SOURCE_ORIGINAL.zip"))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
d = sha(os.path.join(stage, "R07_PRESERVED", "ARC1_R07_SOURCE_ORIGINAL.zip"))
assert d == "c152f0ca88db1214157392b7db919b555ca34c76d9f1299ba7a15a69fa71c039", d
open(os.path.join(stage, "R07_PRESERVED", "DIGEST.txt"), "w").write(
    f"{d}  ARC1_R07_SOURCE_ORIGINAL.zip\n(unchanged copy of the R08 handoff's 00_FROZEN_R07_BASELINE; its tree is identical to the repo's hardware/arc1-compact at R07 commit 1262c1a)\n")
shutil.copy(os.path.join(R08, "tools", "START_HERE_ARCHIVE.md"), os.path.join(stage, "START_HERE.md"))
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
