import sys, re, html
t = open(sys.argv[1], encoding="utf-8").read()
print(len(t))
# strip tags roughly, show Records-related region
i = t.find("Records")
txt = re.sub(r"<[^>]+>", "\n", t)
txt = html.unescape(re.sub(r"\n+", "\n", txt))
lines = txt.split("\n")
for n, l in enumerate(lines):
    if "Record" in l or "record" in l:
        print(n, repr(l[:300]))
        for k in range(n+1, min(n+8, len(lines))): print("   ", repr(lines[k][:200]))
# list hrefs (domains only + filename text)
hrefs = re.findall(r'href="([^"]+)"', t)
import collections
doms = collections.Counter(re.sub(r"^(https?://[^/]+).*$", r"\1", h) for h in hrefs)
print("href domains", doms)
names = re.findall(r">(Graphite_[A-Za-z0-9_.]+\.zip)<", t)
print(len(names), names[:5], names[-5:])
print([n for n in names if "Record" in n or "START" in n])
# headings
print(re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", t))
