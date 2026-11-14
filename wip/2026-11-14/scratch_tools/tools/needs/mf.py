import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
for k, v in d.items():
    if k == 'files':
        print('files:', type(v).__name__, len(v))
        if isinstance(v, dict):
            it = list(v.items())[:2]
        else:
            it = v[:2]
        print('  sample:', it)
    else:
        print(k, '=', json.dumps(v, ensure_ascii=False)[:600])
