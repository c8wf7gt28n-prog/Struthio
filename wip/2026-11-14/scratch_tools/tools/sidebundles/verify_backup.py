import sys, os, json, hashlib, stat
root = sys.argv[1]  # Graphite_Backup dir
b = json.load(open(os.path.join(root, "BACKUP.json"), encoding="utf-8"))
print("schema", b.get("schema"), "created", b.get("created"), "models_included", b.get("models_included"))
print("top keys", list(b.keys()))
files = b["files"]; dirs = b["directories"]
ok = mism = absent = 0
listed = set()
tot = 0
kinds = {}
areas = {}
for f in files:
    p = os.path.join(root, f["area"], f["path"])
    listed.add(os.path.normpath(p))
    kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
    areas[f["area"]] = areas.get(f["area"], 0) + 1
    if not os.path.isfile(p) or os.path.islink(p):
        absent += 1; print("ABSENT", f["area"], f["path"]); continue
    data = open(p, "rb").read()
    tot += len(data)
    h = hashlib.sha256(data).hexdigest()
    if len(data) == f["bytes"] and h == f["sha256"]:
        ok += 1
    else:
        mism += 1; print("MISMATCH", f["area"], f["path"], len(data), f["bytes"], h, f["sha256"])
print("files listed", len(files), "ok", ok, "mismatch", mism, "absent", absent, "bytes", tot, "sum listed bytes", sum(f["bytes"] for f in files))
print("kinds", kinds, "areas", areas)
# present-but-unlisted
unl = []
for dp, dn, fn in os.walk(root):
    for n in fn:
        p = os.path.normpath(os.path.join(dp, n))
        if p == os.path.normpath(os.path.join(root, "BACKUP.json")): continue
        if p not in listed: unl.append(p)
print("present-but-unlisted files", len(unl))
for u in unl: print("  UNLISTED", os.path.relpath(u, root))
# directories
ldirs = set(os.path.normpath(os.path.join(root, d["area"], d["path"])) for d in dirs)
dabs = [d for d in ldirs if not os.path.isdir(d)]
print("dirs listed", len(dirs), "absent on disk", len(dabs))
for d in sorted(dabs): print("  DIR ABSENT", os.path.relpath(d, root))
ddisk = set()
for dp, dn, fn in os.walk(root):
    for n in dn:
        ddisk.add(os.path.normpath(os.path.join(dp, n)))
top = {os.path.normpath(os.path.join(root, a)) for a in ("workspace", "profile")}
extra = sorted(ddisk - ldirs - top)
print("dirs on disk not listed", len(extra))
for d in extra: print("  DIR UNLISTED", os.path.relpath(d, root))
print("skipped", b.get("skipped"))
print("scope", b.get("scope"))
# content-addressed objects: name == sha?
for f in files:
    if "/objects/" in f["path"]:
        parts = f["path"].split("/")
        print("object name==sha256:", (parts[-2] + parts[-1]) == f["sha256"])
