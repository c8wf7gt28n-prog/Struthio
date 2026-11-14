import sys, sqlite3, json, collections
p = sys.argv[1]
con = sqlite3.connect("file:" + p + "?mode=ro&immutable=1", uri=True)
c = con.cursor()
print("audit actors:", c.execute("select actor, count(*) from audit group by actor").fetchall())
print("audit operations:", c.execute("select operation, outcome, count(*) from audit group by operation, outcome order by 3 desc").fetchall()[:40])
print("owners in jobs:", c.execute("select owner, state, count(*) from jobs group by owner, state").fetchall())
for (pl,) in c.execute("select payload from jobs"):
    try:
        d = json.loads(pl); print("  job keys:", sorted(d.keys())[:30]); print("   tool/kind:", {k: d.get(k) for k in ("tool", "kind", "name", "class", "command", "title") if k in d}); 
    except Exception as e: print("  job payload not json", str(pl)[:100])
    break
print("job tools:", collections.Counter((json.loads(pl).get("tool") or json.loads(pl).get("kind") or "?") for (pl,) in c.execute("select payload from jobs")))
print("desk_records:")
for r in c.execute("select id, kind, owner, project, revision, substr(payload,1,400) from desk_records"): print("  ", r)
print("evidence sample:")
for r in c.execute("select id, substr(payload,1,300) from evidence limit 3"): print("  ", r)
print("activity_journal first/last:")
rows = c.execute("select seq, event_id, substr(payload,1,260) from activity_journal order by seq").fetchall()
print("  ", rows[0]); print("  ", rows[-1])
kinds = collections.Counter()
for (pl,) in c.execute("select payload from activity_journal"):
    try: d = json.loads(pl); kinds[d.get("kind") or d.get("type") or d.get("event") or "?"] += 1
    except Exception: kinds["nonjson"] += 1
print("activity kinds:", kinds.most_common(20))
print("ref_pdf_annotations:", c.execute("select id, owner, item, version, substr(payload,1,500) from ref_pdf_annotations").fetchall())
print("intake names:", c.execute("select name, admission from intake_items").fetchall())
print("ledger_trail sample:", c.execute("select owner, substr(payload,1,300) from ledger_trail limit 2").fetchall())
