import sys, sqlite3, re, os, zlib
p = sys.argv[1]
con = sqlite3.connect('file:' + p + '?mode=ro&immutable=1', uri=True)
for ns, item, sid, body in con.execute('select ns,item,id,body from ref_segments'):
    print('=== item', item); print(body)
print('=== ref_pdf_annotations')
for r in con.execute('select id, item, version, payload from ref_pdf_annotations'): print(r)
print('=== ref_meta')
for r in con.execute('select * from ref_meta'): print(r)
print('=== distinct activity operations')
import json, collections
c = collections.Counter(); st = collections.Counter(); origins = collections.Counter(); keys=collections.Counter()
for (pl,) in con.execute('select payload from activity_journal'):
    d = json.loads(pl); c[d.get('operation')] += 1; st[d.get('state')] += 1; origins[d.get('origin')] += 1
    for k in d: keys[k]+=1
print(c); print(st); print(origins); print(keys)
print('=== settings keys + sizes')
for k, v in con.execute('select key, value from settings'): print(k, len(v))
k, v = con.execute("select key,value from settings where key='ledger.desktop_catalog'").fetchone()
d = json.loads(v)
print('desktop_catalog keys', list(d.keys()), 'actions', len(d.get('actions', [])))
print(collections.Counter(a.get('status') for a in d['actions']))
for a in d['actions']:
    if re.search(r'model|brain|stac|slate|provider', json.dumps(a), re.I): print('  ', a.get('command'), '|', a.get('label'), '|', a.get('status'))
k, v = con.execute("select key,value from settings where key like 'ledger.settings_runtime%'").fetchone()
d = json.loads(v)
for kk, vv in d['values'].items(): print('  ', kk, vv)
# PDF metadata
for n in sorted(os.listdir(sys.argv[2])):
    b = open(os.path.join(sys.argv[2], n), 'rb').read()
    print('=== PDF', n, b[:8], 'objs', b.count(b' obj'))
    for m in re.finditer(rb'/(Producer|Creator|Author|Title|CreationDate|ModDate|Subject|Keywords)\s*(\([^)]*\)|<[0-9A-Fa-f]+>)', b):
        print('   ', m.group(1).decode(), m.group(2)[:120])
