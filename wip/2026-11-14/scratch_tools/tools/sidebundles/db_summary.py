import sys, sqlite3, os, datetime, re
for p in sys.argv[1:]:
    print("=" * 100); print(p, os.path.getsize(p))
    head = open(p, "rb").read(100)
    print("magic", head[:16], "write/read ver", head[18], head[19], "page_size", int.from_bytes(head[16:18], "big"))
    con = sqlite3.connect("file:" + p + "?mode=ro&immutable=1", uri=True)
    cur = con.cursor()
    for pr in ("user_version", "application_id", "journal_mode", "schema_version", "page_count", "encoding"):
        try: print("PRAGMA", pr, cur.execute("PRAGMA " + pr).fetchone())
        except Exception as e: print("PRAGMA", pr, "ERR", e)
    try: print("integrity_check", cur.execute("PRAGMA integrity_check").fetchall()[:3])
    except Exception as e: print("integrity ERR", e)
    objs = cur.execute("select type,name,tbl_name from sqlite_master order by type,name").fetchall()
    tables = [o[1] for o in objs if o[0] == "table"]
    print("objects:", {t: sum(1 for o in objs if o[0] == t) for t in set(o[0] for o in objs)})
    tsmin = None; tsmax = None
    for t in tables:
        try:
            n = cur.execute(f'select count(*) from "{t}"').fetchone()[0]
        except Exception as e:
            print(f"  {t}: ERR {e}"); continue
        cols = cur.execute(f'PRAGMA table_info("{t}")').fetchall()
        cn = [c[1] for c in cols]
        print(f"  {t}: rows={n} cols={cn}")
        if n == 0: continue
        for c in cols:
            name = c[1]
            try:
                r = cur.execute(f'select min("{name}"), max("{name}") from "{t}" where typeof("{name}") in ("real","integer") and "{name}" > 1600000000 and "{name}" < 2200000000').fetchone()
            except Exception as e:
                continue
            if r and r[0] is not None:
                lo, hi = r
                print(f"      epoch-like {name}: {datetime.datetime.fromtimestamp(lo, datetime.timezone.utc).isoformat()} .. {datetime.datetime.fromtimestamp(hi, datetime.timezone.utc).isoformat()}")
                tsmin = lo if tsmin is None else min(tsmin, lo); tsmax = hi if tsmax is None else max(tsmax, hi)
            try:
                r = cur.execute(f'select min("{name}"), max("{name}") from "{t}" where typeof("{name}")="text" and "{name}" glob "20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]T*"').fetchone()
            except Exception as e:
                continue
            if r and r[0] is not None:
                print(f"      iso-like {name}: {r[0]} .. {r[1]}")
    if tsmin: print("OVERALL epoch range", datetime.datetime.fromtimestamp(tsmin, datetime.timezone.utc).isoformat(), "..", datetime.datetime.fromtimestamp(tsmax, datetime.timezone.utc).isoformat())
    con.close()
