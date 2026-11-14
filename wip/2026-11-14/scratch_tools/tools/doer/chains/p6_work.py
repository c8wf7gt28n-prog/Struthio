exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/chains/common.py').read())
import os, time
from pathlib import Path
home = Path(os.environ['HOME'])
def source(name, note, parts):
    d = home / name; d.mkdir(exist_ok=True); (d / 'note.md').write_text(note); (d / 'parts.csv').write_text(parts); return d
A = source('Clock', 'hands: blue\n', 'Part,Need,Have\nHand,2,1\nFace,1,1\n')
B = source('Lamp', 'shade: green\n', 'Part,Need,Have\nBulb,4,1\nBase,1,0\n')
def imp(src):
    pre = L('imports.preview', {'source': str(src), 'profile': 'CODE'}, n=300)
    return L('imports.accept', {'id': pre['id'], 'expected_digest': pre['content_digest'], 'for_slate': True}, n=500)
ca = imp(A); cb = imp(B)
proj = L('projects.create', {'title': 'Clock', 'intent': 'Make a working clock'}, n=200)
asg = L('assignments.create', {'project': proj['id'], 'request': 'Use black hands', 'interpretation': 'Prepare a revised working note',
        'intended_output': 'A reviewed note', 'success': ['Note says black'], 'stop': ['Changed inputs'], 'inputs': ['files:' + ca['work'] + '/note.md']}, n=300)
steps = [
 {'key': 'Read', 'operation': 'work.read', 'arguments': {'copy': ca['id'], 'path': 'note.md'}, 'after': []},
 {'key': 'Draft', 'operation': 'changes.propose', 'arguments': {'copy': ca['id'], 'note': 'probe', 'operations': [
     {'op': 'WRITE', 'path': 'note.md', 'base_sha256': {'$step': 'Read', 'path': ['sha256']}, 'text': 'hands: black\n'}]}, 'after': ['Read'],
  'require': [{'path': ['target'], 'equals': 'WORKING'}]},
]
budget = {'seconds': 300, 'steps': 10, 'tokens': 0, 'memory_mb': 128, 'output_bytes': 1048576, 'files': 10}
wk = L('work.create', {'title': 'Two steps: read then draft', 'assignment': asg['id'], 'copies': [ca['id']], 'steps': steps, 'budget': budget, 'expires': time.time() + 3600}, quiet=True)
print('   work', wk['plan']['id'], 'state', wk['state']['state'], wk['state']['reason'], '| digest', wk['content_digest'][:16], '| operations', wk['plan']['operations'], '| effects', wk['plan']['effects'], '| agenda row', wk['agenda'])
print('   agenda waiting:', [(r['kind'], r.get('state'), r.get('reason'), r['title']) for r in k.dispatch('agenda.view', {}, p)['result']['waiting']])
r = L('work.advance', {'id': wk['plan']['id']}, 'before the grant')
L('work.authorize', {'id': wk['plan']['id'], 'expected_digest': '0' * 64}, 'wrong digest')
g = L('work.authorize', {'id': wk['plan']['id'], 'expected_digest': wk['content_digest']}, quiet=True); print('   authorized ->', g['state']['state'], g['grant'])
for i in range(3):
    r = L('work.advance', {'id': wk['plan']['id']})
got = L('work.get', {'id': wk['plan']['id']}, quiet=True)
print('   state', got['state']['state'], got['state']['reason'], 'used', got['state']['used'])
for s in got['steps']:
    res = s.get('result') or {}
    print('   STEP %-6s %-8s attempts=%s args=%s' % (s['key'], s['state'], s.get('attempts'), short(s.get('arguments'), 260)))
    print('        result keys=%s digest=%s  %s' % (sorted(res)[:14], (s.get('result_digest') or '')[:16], short({kk: res[kk] for kk in ('text', 'sha256', 'id', 'content_digest', 'target', 'state') if kk in res}, 300)))
print('   events:', [e['event'] for e in got['events']])
print('   working file now:', repr((Path(k.root) / 'Files' / ca['work'] / 'note.md').read_text()), '| original:', repr((A / 'note.md').read_text()))
draft = next(s for s in got['steps'] if s['key'] == 'Draft')['result']
L('changes.review', {'id': draft['id']}, n=500)
L('procedures.save', {'work': wk['plan']['id'], 'title': 'Read and redraft a note', 'parameters': {}}, 'before acceptance')
L('work.review', {'id': wk['plan']['id'], 'decision': 'ACCEPT', 'note': 'looked at the proposal'}, quiet=True)
params = {'replacement': {'step': 'Draft', 'path': ['operations', '0', 'text'], 'type': 'string'}}
proc = L('procedures.save', {'work': wk['plan']['id'], 'title': 'Read and redraft a note', 'parameters': params}, n=900)
L('procedures.list', {}, quiet=True); print('   procedures:', [(r['title'], r['id'][:8], list(r['parameters'])) for r in k.dispatch('procedures.list', {}, p)['result']['records']])
print('\n======== run it again on OTHER material (the Lamp copy), with another value')
L('procedures.instantiate', {'id': proc['id'], 'assignment': asg['id'], 'copies': [cb['id']], 'values': {}, 'budget': budget, 'expires': time.time() + 3600, 'title': 'again'}, 'missing value')
w2 = L('procedures.instantiate', {'id': proc['id'], 'assignment': asg['id'], 'copies': [cb['id']], 'values': {'replacement': 'shade: black\n'}, 'budget': budget, 'expires': time.time() + 3600, 'title': 'Read and redraft: Lamp'}, quiet=True)
if w2:
    print('   new work', w2['plan']['id'], w2['state']['state'], w2['state']['reason'], '| procedure', w2['plan']['procedure'], '| steps', short([(s['key'], s['arguments']) for s in w2['plan']['steps']], 700))
    L('work.advance', {'id': w2['plan']['id']}, 'ungranted instance')
    L('work.authorize', {'id': w2['plan']['id'], 'expected_digest': w2['content_digest']}, quiet=True)
    for i in range(3): L('work.advance', {'id': w2['plan']['id']})
    got2 = L('work.get', {'id': w2['plan']['id']}, quiet=True)
    print('   state', got2['state']['state'], got2['state']['reason'])
    for s in got2['steps']:
        res = s.get('result') or {}
        print('   STEP %-6s %-8s %s %s' % (s['key'], s['state'], s.get('reason', ''), short({kk: res[kk] for kk in ('text', 'sha256', 'id', 'content_digest', 'target') if kk in res}, 300)))
    d2 = next(s for s in got2['steps'] if s['key'] == 'Draft').get('result')
    if d2:
        rv = L('changes.review', {'id': d2['id']}, quiet=True); print('   review keys:', sorted(rv)[:20]); print('   ', short(rv, 900))
print('\n======== staC over the kept records')
S('procedures.list | pick records | select title,id,operations,effects')
S('procedures.get {"id":"%s"} | pick steps | select key,operation,after' % proc['id'])
S('work.get {"id":"%s"} | pick steps | select key,state,attempts,result_digest' % wk['plan']['id'])
S('@procedure:%s' % proc['id'])
S('@work:%s | pick state | select state,reason' % wk['plan']['id'])
