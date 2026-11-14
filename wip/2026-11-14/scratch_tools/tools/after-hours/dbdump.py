import sys, sqlite3, os
p = sys.argv[1]; out = sys.argv[2]; lim = int(sys.argv[3]) if len(sys.argv) > 3 else 2500
con = sqlite3.connect('file:' + p + '?mode=ro&immutable=1', uri=True)
cur = con.cursor()
tables = [r[0] for r in cur.execute("select name from sqlite_master where type='table' order by name")]
with open(out, 'w') as f:
    for t in tables:
        if any(t.endswith(s) for s in ('_data', '_idx', '_docsize', '_content', '_config')) : continue
        try:
            rows = cur.execute(f'select * from "{t}"').fetchall()
        except Exception as e:
            f.write(f'### {t} ERR {e}\n'); continue
        if not rows: continue
        cols = [c[1] for c in cur.execute(f'pragma table_info("{t}")').fetchall()]
        f.write(f'\n### {t} ({len(rows)} rows) cols={cols}\n')
        for r in rows:
            cells = []
            for c, v in zip(cols, r):
                if isinstance(v, bytes):
                    try: v = v.decode('utf-8')
                    except Exception: v = f'<blob {len(v)} bytes>'
                s = str(v)
                if len(s) > lim: s = s[:lim] + f'...<+{len(s)-lim} chars>'
                cells.append(f'{c}={s}')
            f.write(' | '.join(cells) + '\n')
print('wrote', out, os.path.getsize(out))
