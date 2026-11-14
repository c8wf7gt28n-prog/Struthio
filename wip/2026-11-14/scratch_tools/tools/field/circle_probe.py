# the whole circle through the engine: change a cell, see the calculations go stale, bring one up to date, see what the Field says
import json, copy
from workbench.field_source import read_field
k = w.ledger_bridge.kernel; p = operator()
def call(op, args=None):
    r = k.dispatch(op, args or {}, p)
    if not r['ok']: raise RuntimeError('%s refused: %s' % (op, r['error']))
    return r['result']
def desk(tag):
    f, reader = read_field(k, p)
    calcs = [(o.title, o.state) for o in f.objects if o.kind == 'calculation']
    print('%-34s calculations: %s | aside: %r' % (tag, calcs, f.aside)); return f
f = desk('before')
calc = next(o for o in f.objects if o.kind == 'calculation' and 'Settled' in o.title); cid = calc.target['id']
doc = call('documents.get', {'id': cid}); der = doc['document']['derivation']; print('derivation keys:', sorted(der), '| sheet:', der['sheet'], '| inputs:', [(i['symbol'], i['cell'], i['value']) for i in der['inputs']])
sheet = call('office.get', {'id': der['sheet']}); d = copy.deepcopy(sheet['document']); d['sheets'][0]['cells']['B3']['value'] = '300'
call('office.save', {'id': der['sheet'], 'expected_revision': sheet['revision'], 'document': d})
f = desk('after B3 280 -> 300')
r = call('office.datasheet.recheck', {'id': cid, 'expected_revision': doc['document']['revision']})
new = r['document']; print('recheck made page:', new['id'] != cid, '| title:', repr(new['title']), '| replaces:', new.get('derivation', {}).get('replaces') == cid)
f = desk('after bringing it up to date')
print('new page state:', call('documents.get', {'id': new['id']})['source_state'], '| old page still readable:', call('documents.get', {'id': cid})['document']['title'])
