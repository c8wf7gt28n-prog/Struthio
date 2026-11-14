import sys, sqlite3, os
for p in sys.argv[1:]:
    print('=' * 100); print(p, os.path.getsize(p))
    con = sqlite3.connect('file:' + p + '?mode=ro&immutable=1', uri=True)
    cur = con.cursor()
    for prag in ('user_version', 'application_id', 'schema_version', 'journal_mode', 'page_size', 'page_count', 'integrity_check'):
        try:
            print(prag, cur.execute('pragma ' + prag).fetchall())
        except Exception as e:
            print(prag, 'ERR', e)
    rows = cur.execute("select type,name,tbl_name from sqlite_master order by type,name").fetchall()
    tables = [r[1] for r in rows if r[0] == 'table']
    print('tables', len(tables), 'indexes', sum(1 for r in rows if r[0]=='index'), 'views', sum(1 for r in rows if r[0]=='view'), 'triggers', sum(1 for r in rows if r[0]=='trigger'))
    for t in tables:
        try:
            n = cur.execute(f'select count(*) from "{t}"').fetchone()[0]
        except Exception as e:
            n = 'ERR ' + str(e)
        cols = [c[1] for c in cur.execute(f'pragma table_info("{t}")').fetchall()]
        print(f'{n!s:>6} {t}  ({", ".join(cols)})')
    con.close()
