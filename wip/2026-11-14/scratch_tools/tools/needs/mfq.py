import json, sys, re
d = json.load(open(sys.argv[1], encoding='utf-8'))['files']
for pat in sys.argv[2:]:
    hits = sorted(k for k in d if re.search(pat, k))
    print(f"## /{pat}/ -> {len(hits)}")
    for h in hits[:40]:
        print("   ", d[h]['bytes'], h)
