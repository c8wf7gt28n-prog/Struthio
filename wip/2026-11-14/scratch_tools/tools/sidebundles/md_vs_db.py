import sys, sqlite3, json, os
db, d = sys.argv[1], sys.argv[2]
con = sqlite3.connect("file:" + db + "?mode=ro&immutable=1", uri=True)
docs = {}
for rid, pl in con.execute("select id, payload from desk_records where kind='document'"):
    j = json.loads(pl)
    docs[rid] = (j.get("title"), [b.get("text", "") for b in j.get("blocks", [])], sorted(j.keys()))
for rid, (title, blocks, keys) in docs.items():
    print("DB doc", rid[:8], repr(title), "blocks", len(blocks), "keys", keys)
for n in ("Case_Readout.md", "Settled_Calculation.md", "Startup_Calculation.md"):
    lines = open(os.path.join(d, n), encoding="utf-8").read().split("\n")
    head = lines[0].lstrip("# ").strip()
    body = [l for l in lines[1:] if l.strip()]
    match = None
    for rid, (title, blocks, keys) in docs.items():
        nb = [b for b in blocks if b.strip()]
        if nb == body: match = (rid[:8], title, title == head)
    print(n, "heading", repr(head), "-> body equals DB document:", match)
