import json, sys, re
d = json.load(open(sys.argv[1], encoding='utf-8'))
names = sorted(set(re.sub(r'^debs/', '', k).split('_')[0] for k in d['files'] if k.startswith('debs/')))
print(len(names))
print(' '.join(names))
