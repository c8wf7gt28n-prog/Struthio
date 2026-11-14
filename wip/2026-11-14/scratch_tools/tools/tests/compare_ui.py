"""compare_ui.py base.json now.json : the window gate, script by script, with the line each failing script stopped at."""
import json, re, sys
def rows(path):
    scripts = json.load(open(path))['ui_checks']['scripts']; out = {}
    items = scripts if isinstance(scripts, list) else [dict(v, script=k) if isinstance(v, dict) else {'script': k, 'value': v} for k, v in scripts.items()]
    for r in items:
        name = r.get('script') or r.get('name'); text = json.dumps(r)
        ok = r.get('ok') if 'ok' in r else (r.get('state') in ('PASS', 'PASSED', 'OK') if 'state' in r else r.get('returncode') == 0)
        own = re.findall(re.escape(str(name).split('/')[-1]) + r'\\?", line (\d+)', text) or re.findall(r'line (\d+)', text)
        out[str(name)] = (bool(ok), own[-1] if own and not ok else '')
    return out
a, b = rows(sys.argv[1]), rows(sys.argv[2])
print('base: passing', sum(v[0] for v in a.values()), 'of', len(a), '| now: passing', sum(v[0] for v in b.values()), 'of', len(b))
differs = 0
for k in sorted(set(a) | set(b)):
    same = a.get(k) == b.get(k); differs += not same
    print('  %-28s base %-14s now %-14s%s' % (k, a.get(k), b.get(k), '' if same else '   <-- DIFFERS'))
print('scripts that differ from the baseline:', differs)
