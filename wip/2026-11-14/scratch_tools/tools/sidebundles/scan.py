import sys, os, re, zipfile, io, collections
root = sys.argv[1]
pats = {
 "version_0.2": rb"0\.2\.?0?a\d+|0\.2a\d+|0\.2\.0",
 "home_path": rb"/home/[A-Za-z0-9_.-]+|/Users/[A-Za-z0-9_.-]+|C:\\\\Users\\\\[A-Za-z0-9_.-]+",
 "other_abs_path": rb"/(?:workspace|tmp|mnt|root|var|opt|srv|media|data)/[A-Za-z0-9_./-]{3,80}",
 "email": rb"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]{2,}",
 "url": rb"https?://[A-Za-z0-9./_%?=&#:-]{4,120}",
 "ipv4": rb"\b(?:\d{1,3}\.){3}\d{1,3}\b",
 "token_like": rb"(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})",
 "secret_words": rb"(?i)(?:password|passwd|api[_-]?key|secret|bearer |authorization)[\"' :=]{1,4}[^\s\"',}]{4,40}",
 "hostname_kw": rb"(?i)(?:hostname|nodename|host_name|machine|username|user_name|login)[\"' :=]{1,4}[^\s\"',}]{2,40}",
 "thinkpad": rb"(?i)thinkpad|debian",
 "after_hours": rb"After[ _]Hours[ _]?\d\d",
}
hits = collections.defaultdict(lambda: collections.Counter())
where = collections.defaultdict(lambda: collections.defaultdict(set))
def scan(name, data):
    for k, p in pats.items():
        for m in re.finditer(p, data):
            v = m.group(0)[:100].decode("utf-8", "replace")
            hits[k][v] += 1
            where[k][v].add(name)
for dp, dn, fn in os.walk(root):
    for n in fn:
        p = os.path.join(dp, n)
        rel = os.path.relpath(p, root)
        data = open(p, "rb").read()
        scan(rel, data)
        if n.lower().endswith(".zip"):
            try:
                z = zipfile.ZipFile(io.BytesIO(data))
                for i in z.infolist():
                    if not i.is_dir(): scan(rel + "!" + i.filename, z.read(i))
            except Exception as e:
                print("zip err", rel, e)
show_values = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else set()
for k in pats:
    c = hits[k]
    print(f"== {k}: distinct={len(c)} total={sum(c.values())}")
    if k in show_values:
        for v, n in c.most_common(40):
            fl = sorted(where[k][v])
            print(f"   {n:>4} {v!r}  in {len(fl)} file(s): {fl[:4]}")
    else:
        fl = sorted({f for v in c for f in where[k][v]})
        print("   files:", fl[:12], "..." if len(fl) > 12 else "")
