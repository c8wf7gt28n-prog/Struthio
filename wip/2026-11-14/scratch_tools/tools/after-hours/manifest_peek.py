import sys, json, hashlib, os
m = json.load(open(sys.argv[1], 'rb'))
print(type(m).__name__, list(m.keys())[:30] if isinstance(m, dict) else len(m))
for k, v in m.items():
    if not isinstance(v, (list, dict)): print(k, '=', v)
    else: print(k, type(v).__name__, len(v))
# look for hashes from after-hours bundle in manifest
needles = sys.argv[2:]
s = json.dumps(m)
for n in needles:
    print(n[:16], 'in manifest:', n in s)
# paths that mention relevant words
files = m.get('files') if isinstance(m, dict) else None
if isinstance(files, dict):
    names = list(files.keys())
elif isinstance(files, list):
    names = [f.get('path') if isinstance(f, dict) else str(f) for f in files]
else: names = []
print('names', len(names))
for n in names:
    ln = n.lower()
    if any(w in ln for w in ('backup', 'restore', 'investigat', 'reference_volume', 'reference_service', 'intake_service', 'datasheet', 'office_')):
        print('  ', n)
