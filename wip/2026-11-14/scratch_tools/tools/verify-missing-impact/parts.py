import sys, json
d = json.load(open(sys.argv[1]))
print(list(d.keys()))
for k,v in d.items():
    if not isinstance(v,(list,dict)): print(k, v)
print("parts:", len(d.get('parts',[])))
for p in d.get('parts',[]):
    print({k:(v if not isinstance(v,(list,dict)) else '<%d>'%len(v)) for k,v in p.items()})
fc = d.get('file_chunks')
print(type(fc), len(fc) if fc else None)
if isinstance(fc, dict):
    for k,v in fc.items(): print(k, json.dumps(v)[:1500])
elif isinstance(fc, list):
    for v in fc: print(json.dumps(v)[:1500])
