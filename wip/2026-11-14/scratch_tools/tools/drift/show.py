import json, sys, re
d = json.load(open(sys.argv[1]))
pat = re.compile(sys.argv[2])
for r in d['result']:
    if pat.search(r['module']):
        print(r['module'], r['lines'], '| wb:', len(r['wb']), [w.replace('workbench/','') for w in r['wb']][:8], '| tests:', len(r['tests']), '| tools:', len(r['tools']), '| launch:', r['launch'][:3])
