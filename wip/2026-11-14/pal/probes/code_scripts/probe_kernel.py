"""Clock Lab through the Kernel: staC math shorthand (compile, inspect, run, read-only principal, stale source),
math.sweep's exact boundary, and schedule_math with declared lifetimes."""
import json, os, sys, tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
scratch = Path(sys.argv[2])
from workbench.baseline import environment
from workbench import clock_lab, locations, stac_bridge, schedule_math
from workbench.problem_checks import invoke, bound


def short(value, n=1800):
    return json.dumps(value, default=str)[:n]


def counts(kernel):
    with kernel.db() as db:
        tables = [r[0] for r in db.execute("select name from sqlite_master where type='table'")]
        return {t: db.execute('select count(*) from "%s"' % t).fetchone()[0] for t in tables}


print('## compile with a dummy id')
print(short(stac_bridge.compile_program('math problem:' + '0' * 32 + ' | calculate "voltage * assumed_typical_current" | unit W')))
for bad in ['math problem:abc | calculate "voltage" | unit W', 'math problem:' + '0' * 32 + ' | calculate voltage * x | unit W',
            'math problem:' + '0' * 32 + ' | solve "voltage" | unit W']:
    try: stac_bridge.compile_program(bad); print('accepted', bad)
    except ValueError as e: print('refused', repr(bad[:60]), '->', e)
print('route', stac_bridge.route_program('math problem:x | calculate "a" | unit W'))

with tempfile.TemporaryDirectory(prefix='pal02-', dir=scratch) as temp:
    base = Path(temp); home = base / 'Home'; home.mkdir(); root = base / 'Office'; profile = base / 'profile'
    with patch.dict(os.environ, {**environment(os.environ, root, profile), 'HOME': str(home)}), patch.object(Path, 'home', return_value=home):
        from workbench.engineering_kernel import Kernel, operator, Principal
        locations.office(root); kernel = Kernel(root); p = operator()
        data = clock_lab.start(kernel, clock_lab.copy_inputs(home / 'Clock_Lab'), p); problem = data['problem']
        line = 'math problem:' + problem['id'] + ' | calculate "voltage * assumed_typical_current" | unit W'
        print('## stac.compile'); print(short(invoke(kernel, 'stac.compile', {'program': line}, p)))
        reader = Principal(p.identity)  # read scope only
        print('reader scopes', sorted(reader.scopes))
        print('## stac.inspect (reader)'); print(short(invoke(kernel, 'stac.inspect', {'program': line}, reader), 1200))
        before = counts(kernel)
        r = invoke(kernel, 'stac.run', {'program': line}, reader)
        after = counts(kernel)
        print('## stac.run (reader)'); print(short({k: r[k] for k in ('schema', 'result_type', 'effects', 'engineering_qualification')}))
        print('evaluation', short(r['result']['evaluation']['outputs'], 600), 'state', r['result']['evaluation']['state'])
        print('bindings', short(r['result']['variable_bindings'], 900))
        print('result keys', sorted(r['result']))
        print('db rows changed by stac.run:', {t: (before[t], after[t]) for t in after if before.get(t) != after[t]})
        # A write attempt by the same reader is refused
        resp = kernel.dispatch('math.prepare', {**bound(problem), 'expression': 'voltage * assumed_typical_current'}, reader)
        print('reader math.prepare ok?', resp['ok'], resp.get('error', {}).get('message', '')[:120])
        # Source change: power.csv edited in the working copy
        work = root / 'Files' / data['copy']['work'] / 'power.csv'; work.write_text(work.read_text().replace('120', '125'))
        sheet = invoke(kernel, 'problems.get', {'id': problem['id']}, p)
        print('freshness after edit:', sheet['freshness']['state'])
        r2 = kernel.dispatch('stac.run', {'program': line}, reader)
        print('stac.run after source edit ok?', r2['ok'], (r2.get('error') or {}).get('message', '')[:120],
              'freshness field in result?', 'freshness' in json.dumps(r2.get('result', {})))
        resp = kernel.dispatch('math.prepare', {**bound(problem), 'expression': 'voltage * assumed_typical_current'}, p)
        print('operator math.prepare after edit ok?', resp['ok'], resp.get('error', {}).get('message', '')[:120])
        work.write_text(work.read_text().replace('125', '120'))
        print('freshness after revert:', invoke(kernel, 'problems.get', {'id': problem['id']}, p)['freshness']['state'])
        # Sweep through the Kernel on a prepared action
        memory = invoke(kernel, 'math.prepare', {**bound(problem), 'expression': 'buffer_A + buffer_B + workspace <= memory_limit',
            'assumptions': ['All three allocations are concurrent.'], 'output_unit': 'MiB'}, p)
        run = invoke(kernel, 'math.run', {'action': memory['id']}, p)['receipt']['snapshot']
        print('## all-concurrent run', run['state'], short(run['outputs'][0], 500))
        graph = invoke(kernel, 'math.sweep', {'action': memory['id'], 'variable': 'workspace', 'start': '0', 'stop': '10', 'count': 21}, reader)
        print('## math.sweep boundaries (reader)', short(graph['boundaries']))
        print('samples at 4,5:', [(s['input']['rational'], s['satisfies']) for s in graph['samples'] if s['input']['rational'] in ('4', '9/2', '5')])
        # Schedule against the real fixture: lifetimes UNKNOWN
        try:
            print('## math.schedule on fixture', short(invoke(kernel, 'math.schedule', {**bound(problem), 'capacity': 'memory_limit',
                'allocations': [{'quantity': 'buffer_A', 'lifetime': 'lifetime_A'}, {'quantity': 'buffer_B', 'lifetime': 'lifetime_B'},
                                {'quantity': 'workspace', 'lifetime': 'lifetime_workspace'}]}, p)['snapshot'], 400))
        except ValueError as e: print('math.schedule on fixture refused', e)

# schedule_math.evaluate with declared lifetimes (pure)
spec = clock_lab.specification()
def scenario(w, lives):
    variables = []
    for v in spec['variables']:
        v = dict(v)
        if v['name'] == 'workspace': v['value'] = w
        if v['name'] in lives:
            a, z = lives[v['name']]; v.update(state='KNOWN', value=json.dumps({'start': a, 'stop': z, 'unit': 'ms'}))
        variables.append(v)
    snap = schedule_math.evaluate({'variables': variables}, 'memory_limit', [
        {'quantity': 'buffer_A', 'lifetime': 'lifetime_A'}, {'quantity': 'buffer_B', 'lifetime': 'lifetime_B'},
        {'quantity': 'workspace', 'lifetime': 'lifetime_workspace'}])
    return snap['state'], snap.get('peak', {}).get('rational'), snap.get('peak', {}).get('unit')
cases = {
    'A,B overlap; W inside the overlap': {'lifetime_A': ('0', '10'), 'lifetime_B': ('5', '15'), 'lifetime_workspace': ('6', '9')},
    'A,B overlap; W overlaps A only (before B starts)': {'lifetime_A': ('0', '10'), 'lifetime_B': ('5', '15'), 'lifetime_workspace': ('0', '5')},
    'A,B overlap; W after both': {'lifetime_A': ('0', '10'), 'lifetime_B': ('5', '15'), 'lifetime_workspace': ('15', '20')},
    'A,B disjoint; W with each in turn': {'lifetime_A': ('0', '10'), 'lifetime_B': ('10', '20'), 'lifetime_workspace': ('0', '20')},
}
print('## schedule_math.evaluate with declared lifetimes (ms, half-open)')
for label, lives in cases.items():
    print(label, [(w,) + scenario(w, lives) for w in ('4', '4.000001', '5', '10', '10.5')])
print('lifetimes unknown ->', schedule_math.evaluate({'variables': spec['variables']}, 'memory_limit', [
    {'quantity': 'buffer_A', 'lifetime': 'lifetime_A'}, {'quantity': 'buffer_B', 'lifetime': 'lifetime_B'},
    {'quantity': 'workspace', 'lifetime': 'lifetime_workspace'}])['state'])
