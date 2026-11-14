import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
print(list(d.keys()))
it = d['integrated_tests']
print('command:', it['command'])
for k in it:
    if k == 'command': continue
    print(k, ':')
    v = it[k]
    if isinstance(v, list):
        for x in v: print('   ', x)
    else: print('   ', v)
for k in d:
    if k not in ('integrated_tests', 'artwork', 'captures', 'art_plates', 'motion', 'modes', 'worksheet', 'journal', 'release'):
        print(k, '=', json.dumps(d[k], ensure_ascii=False)[:1200])
