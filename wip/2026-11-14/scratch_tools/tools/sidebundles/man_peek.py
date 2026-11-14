import sys, json, os, re
man = json.load(open(sys.argv[1], encoding="utf-8"))
print({k: (v if not isinstance(v, (dict, list)) else type(v).__name__ + ":" + str(len(v))) for k, v in man.items()})
files = man["files"]
names = list(files.keys()) if isinstance(files, dict) else [e["path"] for e in files]
print("count", len(names))
for pat in sys.argv[2:]:
    hit = [n for n in names if re.search(pat, n, re.I)]
    print("PATTERN", pat, len(hit))
    for h in hit[:60]: print("   ", h, files[h] if isinstance(files, dict) else "")
