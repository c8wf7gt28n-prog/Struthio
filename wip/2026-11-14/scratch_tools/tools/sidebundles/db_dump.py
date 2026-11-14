import sys, sqlite3
p = sys.argv[1]; lim = int(sys.argv[2]); tables = sys.argv[3:]
con = sqlite3.connect("file:" + p + "?mode=ro&immutable=1", uri=True)
cur = con.cursor()
for t in tables:
    print("#####", t)
    rows = cur.execute(f'select * from "{t}"').fetchall()
    cn = [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")').fetchall()]
    for r in rows:
        out = []
        for n, v in zip(cn, r):
            if isinstance(v, bytes): v = "<blob %d>" % len(v)
            s = str(v)
            if len(s) > lim: s = s[:lim] + "...[%d]" % len(s)
            out.append(f"{n}={s}")
        print("  " + " | ".join(out))
