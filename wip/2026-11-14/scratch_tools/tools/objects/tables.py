import sqlite3, sys
for p in sys.argv[1:]:
    con = sqlite3.connect('file:' + p + '?mode=ro&immutable=1', uri=True); cur = con.cursor()
    print('==', p.split('/demo/')[-1], 'user_version', cur.execute('pragma user_version').fetchone()[0])
    for (t,) in cur.execute("select name from sqlite_master where type='table' and name not like '%_fts%' and name not like 'sqlite_%' order by name").fetchall():
        try: n = cur.execute('select count(*) from "%s"' % t).fetchone()[0]
        except Exception as e: n = 'ERR'
        if n: print('  %5s %-28s (%s)' % (n, t, ', '.join(c[1] for c in cur.execute('pragma table_info("%s")' % t).fetchall())))
    if 'catalog' in p:
        print('  objects:', cur.execute('select id,kind,title,state,version from objects').fetchall())
        print('  relations:', cur.execute('select * from relations').fetchall())
        print('  office_documents:', cur.execute('select id,version,length(payload),length(origin) from office_documents').fetchall())
