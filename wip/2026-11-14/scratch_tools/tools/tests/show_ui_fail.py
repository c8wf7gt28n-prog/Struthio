import json, sys
S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/reports2/'
want = sys.argv[1]
for name in sys.argv[2:]:
    scripts = json.load(open(S + name))['ui_checks']['scripts']
    items = scripts if isinstance(scripts, list) else [dict(v, script=k) for k, v in scripts.items()]
    r = next(x for x in items if want in str(x.get('script') or x.get('name')))
    text = json.dumps(r); i = text.rfind('Traceback')
    print(name, '|', (text[i:i + 1500] if i >= 0 else text[-900:]).replace('\\n', '\n').replace('\\"', '"')); print('-----')
