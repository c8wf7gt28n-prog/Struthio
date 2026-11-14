import sys, json, os, collections
tree = sys.argv[1]
man = json.load(open(os.path.join(tree, "MANIFEST.json"), encoding="utf-8"))["files"]
sm = json.load(open(os.path.join(tree, "project/stacy_seed/current/manifest.json"), encoding="utf-8"))
inp = sm["inputs"]
present = [n for n in inp if n in man]
absent = sorted(n for n in inp if n not in man)
same = [n for n in present if man[n]["sha256"] == inp[n]]
print("seed inputs:", len(inp), "| shipped as files in App MANIFEST:", len(present), "(sha equal to seed input sha:", len(same), ") | carried notes NOT shipped as files:", len(absent))
print("by top dir:", collections.Counter(a.split("/")[0] for a in absent).most_common())
for a in absent: print("   ", a)
