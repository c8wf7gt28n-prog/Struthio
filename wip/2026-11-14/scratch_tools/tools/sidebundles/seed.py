import sys, json, os
tree = sys.argv[1]
man = json.load(open(os.path.join(tree, "MANIFEST.json"), encoding="utf-8"))["files"]
sm = json.load(open(os.path.join(tree, "project/stacy_seed/current/manifest.json"), encoding="utf-8"))
print("seed manifest top keys:", {k: (type(v).__name__ + ":" + str(len(v)) if isinstance(v, (list, dict)) else v) for k, v in sm.items()})
srcs = sm.get("sources") or sm.get("files") or sm.get("inputs")
if isinstance(srcs, dict): items = list(srcs.items())
elif isinstance(srcs, list): items = [(s.get("path") or s.get("name") or s.get("source"), s) for s in srcs]
else: items = []
print("seed source entries:", len(items))
if items: print("sample entry:", items[0])
present = [n for n, _ in items if n in man]
absent = [n for n, _ in items if n not in man]
print("seed sources shipped as files in App MANIFEST:", len(present), "| NOT shipped as files:", len(absent))
tot = 0
for n, v in items:
    if n in absent and isinstance(v, dict): tot += v.get("bytes", 0) or 0
print("bytes of not-shipped seed sources (if recorded):", tot)
for n in sorted(absent): print("   ", n)
