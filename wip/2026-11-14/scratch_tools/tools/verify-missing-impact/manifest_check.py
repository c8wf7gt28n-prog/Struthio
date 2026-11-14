import sys, json, hashlib, os
root = sys.argv[1]
m = json.load(open(os.path.join(root, 'MANIFEST.json')))
print("manifest top keys:", [k for k in m.keys()][:10])
files = m.get('files')
print(type(files), len(files))
if isinstance(files, dict):
    items = list(files.items())
else:
    items = [(f.get('path') or f.get('name'), f) for f in files]
print("sample:", items[0])
missing=[]; changed=[]; ok=0
for name, meta in items:
    p = os.path.join(root, name)
    if not os.path.isfile(p):
        missing.append(name); continue
    h = hashlib.sha256(open(p,'rb').read()).hexdigest()
    want = meta if isinstance(meta, str) else meta.get('sha256')
    if h != want: changed.append(name)
    else: ok+=1
print("ok", ok, "missing", missing, "changed", changed)
# extra files
have=set()
for d,_,fs in os.walk(root):
    for f in fs:
        have.add(os.path.relpath(os.path.join(d,f), root))
names=set(n for n,_ in items)
print("extra:", sorted(have-names)[:30], len(have-names))
