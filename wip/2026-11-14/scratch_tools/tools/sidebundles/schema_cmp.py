import sys, os, re, sqlite3
tree = sys.argv[1]; dbs = sys.argv[2:]
src = {}
for dp, dn, fn in os.walk(tree):
    for n in fn:
        if n.endswith(".py"):
            p = os.path.join(dp, n)
            try: t = open(p, encoding="utf-8").read()
            except Exception: continue
            for m in re.finditer(r"CREATE\s+(?:VIRTUAL\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"'`]?([A-Za-z_][A-Za-z0-9_]*)", t, re.I):
                src.setdefault(m.group(1), set()).add(os.path.relpath(p, tree))
print("tables named in CREATE TABLE statements in source:", len(src))
for db in dbs:
    con = sqlite3.connect("file:" + db + "?mode=ro&immutable=1", uri=True)
    names = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
    base = [n for n in names if not re.search(r"_(config|content|data|docsize|idx)$", n) and n != "sqlite_sequence"]
    missing = [n for n in base if n not in src]
    print(os.path.basename(db), "tables", len(names), "non-FTS-shadow", len(base), "not found in source CREATE statements:", missing)
    # where are backup schema / workspace schema strings
    con.close()
# schema markers present in source?
for marker in ("arc.workspace-backup/1", "arc.reference-volume/1", "arc.reference-volume-manifest/1", "arc.ledger-workspace/1", "arc1.workbench-session/1", "arc.pdf-annotation/1", "arc.intake-job-result/1", "arc.reference-job-result/1", "arc.office-table/1"):
    hits = []
    for dp, dn, fn in os.walk(tree):
        for n in fn:
            if n.endswith(".py"):
                p = os.path.join(dp, n)
                try:
                    if marker in open(p, encoding="utf-8").read(): hits.append(os.path.relpath(p, tree))
                except Exception: pass
    print(marker, "->", hits[:4])
