import json, copy, hashlib
from workbench import field_source
k = w.ledger_bridge.kernel; p = operator()
LINES = []
def short(x, n=220):
    s = json.dumps(x, sort_keys=True, default=str); return s if len(s) <= n else s[:n] + '…'
def L(op, args=None, note='', hide=()):
    """One operation line, exactly as typed, and its answer."""
    args = args or {}
    shown = {kk: ('<…>' if kk in hide else vv) for kk, vv in args.items()}
    line = op + (' ' + json.dumps(shown, sort_keys=True, separators=(',', ':')) if shown else '')
    r = k.dispatch(op, args, p)
    from workbench.engineering_kernel import CAPABILITIES
    LINES.append('[%s] %s' % (CAPABILITIES.get(op), line))
    print('\nOP [%s] %s%s' % (CAPABILITIES.get(op), line[:600], ('   # ' + note) if note else ''))
    if not r['ok']:
        print('   REFUSED:', r['error']); return None
    return r['result']
def field(tag=''):
    f, reader = field_source.read_field(k, p)
    print('\n=== FIELD %s: %s | refused=%s unread=%s' % (tag, f.title, reader.refused, reader.unread))
    for o in f.objects:
        print('  %-11s %-9s %-52s %s' % (o.kind, o.state or '-', o.title[:52], ' ; '.join(o.lines)))
    for l in f.links:
        if l.stale: print('    STALE wire %s -> %s  [%s]' % (l.source[:26], l.target[:26], l.label))
    return f
def sha_obj(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
BENCH = 'owner:db5f669f863d4c71b89fa7ba348957da'; REVA = 'owner:5a43beee28224c4e818af7b985cdb535'; REVB = 'owner:4f357ff3c843489a9758db71e23bf4b4'
SETTLED = '0e39bf65e24740a29a504a6be6e00885'; STARTUP = '500cd60ebe49411bb9b9e5bbe0570214'; PAGE = '218f9efb3315412099761113f1ef2e5d'
INV = 'c574ae94d79542f582932d151fad631f'; NS = '34259ad099cfdec0a683ff3ef5b90773'
PDF_BENCH = 'c1d3fc85730d57bc35404c6065dbe1dc'; PDF_REVA = 'b60c03c9f5ac6c02b7d1c1c0b09a2026'; PDF_REVB = '496798047c86ccc5f46a4120f1c0e7f8'
F_SETTLED = 'f2a610f24ca84112a400e02d6ad04869'; F_STARTUP = 'c3bfcad59ccf4868b419107ef1b5288c'; F_REVS = 'a4f277d22a654bfbbd82d919fa9671b0'; F_SHEET = '606d27fa927e423e9eab95a44d986412'; QUESTION = '9a2fb93a5e37466f8fc30cfbb3c63230'
def calc_state(ident, tag=''):
    g = L('documents.get', {'id': ident}, tag)
    if g: print('   -> title=%r revision=%s source_state=%s' % (g['document']['title'], g['document']['revision'], g.get('source_state')))
    return g
def inv_state(tag=''):
    s = L('investigation.sheet', {'id': INV}, tag)
    print('   -> state=%s reason=%r next=%s' % (s['state'], s['reason'], s['next']))
    print('   -> read:', [(r['address'][:20], r['state'], r['digest'][:8], r['current'][:8]) for r in s['read']])
    print('   -> checked:', [(c['id'][:8], c['program'][:60], c['expect'], c['value'], c['last_outcome']) for c in s['checked']])
    print('   -> learned:', [(c['text'][:40], c['evidence_state'], c['review']) for c in s['learned']])
    print('   -> unresolved:', [(c['role'], c['text'][:40], c['evidence_state'], c['review']) for c in s['unresolved']])
    return s
