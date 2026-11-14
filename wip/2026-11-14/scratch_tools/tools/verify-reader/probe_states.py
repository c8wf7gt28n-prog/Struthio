import sys, time, json, os
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-reader')
from wincommon import *
from workbench import field_page, conditions
from workbench.engineering_kernel import operator
open_window(); settle(50, 10)
k = w.ledger_bridge.kernel; p = operator()
def call(op, args=None, quiet=False):
    r = k.dispatch(op, args or {}, p)
    if not r.get('ok'):
        if not quiet: print('   REFUSED', op, r.get('error'))
        return None
    return r['result']
OUT = L / 'out/states'; OUT.mkdir(parents=True, exist_ok=True)
def show(tag, png=None):
    w.show_field(); settle(30, 4); v = w.field_page.view
    print('[%s] census: %s | refused: %s' % (tag, v.field.census(), (w.field_page.problem, sorted(w.field_page.unread))))
    if png: align(); w.grab().save(str(OUT / png), 'PNG')
    return v
# --- A. a finding supported by a page; then the page changes and the investigation is refreshed (the owner's recheck case)
doc = call('documents.create', {'title': 'Probe page', 'text': 'Rail A draws 2 W.\nRail B draws 3 W.\nTotal: 5 W.'})
blocks = doc['blocks']; print('page blocks:', [(b['id'][:6], b['text']) for b in blocks])
mine = call('investigation.create', {'question': 'Probe: what do the rails draw?'})
src = call('investigation.add_source', {'id': mine['id'], 'address': 'document:' + doc['id']})
claim = call('investigation.claim', {'id': mine['id'], 'text': 'Rail A draws 2 W.', 'role': 'FINDING'})
ev = call('investigation.evidence', {'claim': claim['claim'], 'direction': 'SUPPORTS', 'source': src['source']})
sh = call('investigation.sheet', {'id': mine['id']})
print('before the change: learned=%s unresolved=%s' % ([(c['text'], c['evidence_state'], c['review']) for c in sh['learned']], [(c['text'], c['evidence_state'], c['review']) for c in sh['unresolved']]))
v = show('finding supported, source unchanged')
obj = v.field.get('claim:' + claim['claim']); print('   Field shows it as: kind=%s state=%s lines=%s | wires in: %s' % (obj.kind, obj.state, obj.lines, [(l.source, l.label, l.stale) for l in v.field.fed_by(obj.id)]))
field_page.leave_field(w)
# --- B. a condition card on that page (the record Slate makes for a total), CURRENT at first
text0 = blocks[0]['text']; text1 = blocks[1]['text']
card = conditions.create(k, p, document=doc['id'], inputs=[
    {'block': blocks[0]['id'], 'index': 0, 'start': text0.index('2 W'), 'end': text0.index('2 W') + 3, 'text': '2 W', 'value': '2', 'unit': 'W'},
    {'block': blocks[1]['id'], 'index': 1, 'start': text1.index('3 W'), 'end': text1.index('3 W') + 3, 'text': '3 W', 'value': '3', 'unit': 'W'}],
    expression='sum', result={'value': '5', 'unit': 'W', 'text': '5 W'}, method=conditions.METHOD, assignment=None, result_block=blocks[2]['id'])
print('condition card made:', card['id'], card['state'])
# the owner edits the page: rail A now draws 4 W
new_blocks = [dict(b) for b in blocks]; new_blocks[0]['text'] = 'Rail A draws 4 W.'
saved = call('documents.save', {'id': doc['id'], 'expected_revision': doc['revision'], 'blocks': new_blocks})
print('page saved:', saved['saved'], 'conditions_stale:', saved.get('conditions_stale'))
print('conditions.list row:', [(c['state'], c['result']) for c in call('conditions.list')['conditions']])
ref = call('investigation.refresh', {'id': mine['id']})
print('after refresh: changed=%s learned=%s unresolved=%s' % (ref.get('changed'), [(c['text'], c['evidence_state'], c['review']) for c in ref['learned']], [(c['text'], c['evidence_state'], c['review']) for c in ref['unresolved']]))
print('   path now:', [(s['kind'], s.get('address'), s.get('counts'), s.get('source_state')) for s in call('investigation.path', {'claim': claim['claim']})['path']])
v = show('after the source page changed', 'field_after_source_changed.png')
obj = v.field.get('claim:' + claim['claim']); print('   Field shows the finding as: kind=%s tag state=%s lines=%s | wires in: %s' % (obj.kind, obj.state, obj.lines, [(l.source, l.label, l.stale) for l in v.field.fed_by(obj.id)]))
for o in v.field.objects:
    if o.id.startswith('condition:'):
        print('   Field condition object: title=%r role=%r state=%s lines=%s' % (o.title, o.role, o.state, o.lines))
        v.field.select(o.id); v._describe(); v.update(); settle(20, 2); print('   accessible description:', v.accessibleDescription()); align(); w.grab().save(str(OUT / 'field_condition_selected.png'), 'PNG')
print('stale links in the whole field:', [(l.source, l.target, l.label) for l in v.field.links if l.stale])
w._closing = True; print('DONE')
