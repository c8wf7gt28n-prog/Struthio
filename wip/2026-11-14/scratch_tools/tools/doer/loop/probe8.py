# probe8 (no model): which staC lines make usable CHECK programs (what the oracle sees).
import json
from workbench import investigations
k = w.ledger_bridge.kernel; p = operator()
def d(op, args=None): return k.dispatch(op, args or {}, p)
docs = d('documents.list')['result']['documents']; calc = next(x for x in docs if 'Settled' in x['title'])['id']; page = next(x for x in docs if 'conclusion' in x['title'])['id']
inv = d('investigation.list')['result']['investigations'][0]['id']
lines = ['@document:%s' % page,
         'documents.get {"id":"%s"} | pick document.blocks | select text' % page,
         'documents.get {"id":"%s"} | pick source_state | select state' % calc,
         'documents.get {"id":"%s"} | pick document.derivation.calculation.outputs | select value' % calc,
         'investigation.sheet {"id":"%s"} | pick checked | select oracle,last_outcome' % inv,
         'investigation.sheet {"id":"%s"} | pick learned | select text,evidence_state,review' % inv,
         'agent.list | pick assignments | select working_on,state']
for line in lines:
    op, args = investigations.run_with(line); r = k.dispatch(op, args, p)
    res = r.get('result') if r['ok'] else r['error']
    text = json.dumps(res, sort_keys=True, default=str)
    print('\nLINE', line[:150]); print('  routed to', op, '| ok', r['ok'], '| keys', sorted(res)[:12] if isinstance(res, dict) else type(res).__name__)
    print('  rows:', json.dumps(res.get('rows'), ensure_ascii=False, default=str)[:420] if isinstance(res, dict) else res)
    print('  items_of ->', (lambda v: None if v is None else len(v))(investigations.items_of(res)), '| CONTAINS "3.36 W":', investigations.oracle_holds('CONTAINS', '3.36 W', res) if r['ok'] else None,
          '| CONTAINS "CURRENT":', investigations.oracle_holds('CONTAINS', 'CURRENT', res) if r['ok'] else None, '| NONEMPTY:', investigations.oracle_holds('NONEMPTY', '', res) if r['ok'] else None)
