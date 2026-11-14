import sys, re, os, hashlib, json
patch, tree = sys.argv[1], sys.argv[2]
manifest = sys.argv[3] if len(sys.argv) > 3 else None
lines = open(patch, encoding="utf-8").read().split("\n")
if lines and lines[-1] == "": lines.pop()
files = []; cur = None; hunk = None
i = 0
while i < len(lines):
    l = lines[i]
    if l.startswith("--- ") and i + 1 < len(lines) and lines[i+1].startswith("+++ "):
        cur = {"a": l[4:], "b": lines[i+1][4:], "hunks": []}; files.append(cur); i += 2; continue
    m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", l)
    if m:
        hunk = {"a0": int(m.group(1)), "an": int(m.group(2) or 1), "b0": int(m.group(3)), "bn": int(m.group(4) or 1), "body": []}
        cur["hunks"].append(hunk); i += 1; continue
    if hunk is not None and l[:1] in (" ", "+", "-", "\\"):
        hunk["body"].append(l)
    elif hunk is not None and l == "":
        hunk["body"].append(" ")
    else:
        print("UNPARSED", i + 1, repr(l[:80]))
    i += 1
man = None
if manifest:
    man = json.load(open(manifest, encoding="utf-8"))
tot_h = ok_h = 0; tot_add = tot_rem = 0
for f in files:
    rel = f["b"][2:] if f["b"].startswith("b/") else f["b"]
    p = os.path.join(tree, rel)
    exists = os.path.isfile(p)
    print("FILE", rel, "exists" if exists else "MISSING", "hunks", len(f["hunks"]))
    if not exists: continue
    raw = open(p, "rb").read()
    text = raw.decode("utf-8").split("\n")
    fset = set(text)
    for h in f["hunks"]:
        tot_h += 1
        post = [b[1:] for b in h["body"] if b[:1] in (" ", "+")]
        pre = [b[1:] for b in h["body"] if b[:1] in (" ", "-")]
        added = [b[1:] for b in h["body"] if b[:1] == "+"]
        removed = [b[1:] for b in h["body"] if b[:1] == "-"]
        tot_add += len(added); tot_rem += len(removed)
        assert len(post) == h["bn"] and len(pre) == h["an"], (rel, h["a0"], len(post), h["bn"], len(pre), h["an"])
        at = text[h["b0"] - 1: h["b0"] - 1 + h["bn"]]
        post_ok = (at == post)
        # is pre-image present anywhere contiguous?
        pre_found = any(text[k:k + len(pre)] == pre for k in range(0, len(text) - len(pre) + 1)) if pre != post else None
        add_missing = [a for a in added if a not in fset]
        rem_present = [r for r in removed if r in fset and r.strip() != ""]
        if post_ok and not pre_found and not add_missing: ok_h += 1
        print(f"   hunk -{h['a0']},{h['an']} +{h['b0']},{h['bn']}: post-image at exact b-lines={post_ok} pre-image present={pre_found} +{len(added)} -{len(removed)} added-missing={len(add_missing)} removed-still-present-somewhere={len(rem_present)}")
        for r in rem_present: print("        removed line also occurs in file:", repr(r[:110]))
        for a in add_missing: print("        ADDED LINE MISSING:", repr(a[:110]))
    if man is not None:
        ent = None
        fl = man.get("files") if isinstance(man, dict) else None
        if isinstance(fl, dict): ent = fl.get(rel)
        elif isinstance(fl, list):
            for e in fl:
                if isinstance(e, dict) and e.get("path") == rel: ent = e
        print("   manifest entry:", ent, "| actual sha256", hashlib.sha256(raw).hexdigest(), len(raw))
print(f"TOTAL files={len(files)} hunks={tot_h} hunks fully consistent with post-image={ok_h} added_lines={tot_add} removed_lines={tot_rem}")
