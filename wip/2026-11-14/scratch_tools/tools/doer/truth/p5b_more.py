exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/truth/common.py').read())
def sheets(tag=''):
    for ident in (BENCH, REVA, REVB):
        g = k.dispatch('office.get', {'id': ident}, p)['result']; print('   sheet %-26s %s (bound to decision %s)' % (g['document']['title'], g['source_state']['state'], g['origin']['pdf']['decision'][:8]))
def items():
    r = k.dispatch('intake.items', {'namespace': NS}, p)['result']; print('   items:', [(i['name'][3:18], i['admission'], i['decision_id'][:8]) for i in r['items']], 'generation', r['generation']); return r
print('########## R1. does restoring a catalog checkpoint keep the sheets current?')
items(); sheets()
cp = L('intake.checkpoint', {'namespace': NS, 'label': 'rehearsal'}); print('   -> id', cp['id'], 'generation', cp['generation'])
gen = items()['generation']
r = L('intake.catalog.restore', {'id': cp['id'], 'expected_generation': gen, 'reason': 'Rehearsal: restore with nothing changed.'}); print('   ->', short(r, 300))
items(); sheets(); calc_state(SETTLED); field('after intake.catalog.restore with nothing changed')
print('\n########## R2. the investigation after a source went away and came back')
r = L('investigation.refresh', {'id': INV}); print('   -> changed=%s' % r['changed'])
s = inv_state()
r = L('investigation.review', {'claim': F_SETTLED, 'decision': 'ACCEPT_CHANGE'}); print('   -> review', r['review'], 'evidence', r['evidence_state'], 'support', r['independent_support'])
s = inv_state('after one ACCEPT_CHANGE (it supersedes every CHANGED source of the investigation)')
for c in s['unresolved']:
    if c['review'] == 'NEEDS_REVIEW': L('investigation.review', {'claim': c['id'], 'decision': 'ACCEPT_CHANGE'})
r = L('investigation.refresh', {'id': INV}, 'read again'); print('   -> changed=%s' % r['changed'])
s = inv_state()
for c in s['unresolved']:
    if c['review'] == 'NEEDS_REVIEW': L('investigation.review', {'claim': c['id'], 'decision': 'ACCEPT_CHANGE'})
r = L('investigation.continue', {'id': INV}); print('   -> ran=%s' % r['ran'])
s = inv_state('settled?')
for c in s['learned']:
    pth = k.dispatch('investigation.path', {'claim': c['id']}, p)['result']; print('   %-44s support=%s counts=%s' % (c['text'][:44], pth['independent_support'], [x['counts'] for x in pth['path']]))
field('after the investigation was brought back')
print('\n########## R3. the reference index')
r = L('references.status', {'namespace': NS}); print('   -> current_sources', r['current_sources'], '| unavailable', [(u['item'][:8], u['reason']) for u in r['unavailable']])
j = L('references.index', {'namespace': NS}); print('   -> job', j.get('id'), j.get('state'), j.get('tool'))
if j and j.get('id'): wait_job(j['id'], 120, 'index')
r = L('references.status', {'namespace': NS}); print('   -> current_sources', r['current_sources'], '| unavailable', [(u['item'][:8], u['reason']) for u in r['unavailable']])
r = L('references.search', {'namespace': NS, 'query': 'startup pulse'}); print('   -> hits', [(h.get('name') or h.get('item'), str(h.get('text') or h.get('snippet') or '')[:80]) for h in r['hits']][:3], '| keys of a hit', sorted(r['hits'][0]) if r['hits'] else None)
print('\n########## THE SEQUENCE'); print('\n'.join(LINES))
