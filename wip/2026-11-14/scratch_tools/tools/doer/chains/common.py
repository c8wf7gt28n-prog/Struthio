import json
from workbench.engineering_kernel import CAPABILITIES
k = w.ledger_bridge.kernel; p = operator()
def short(x, n=400):
    s = json.dumps(x, sort_keys=True, default=str, ensure_ascii=False); return s if len(s) <= n else s[:n] + '…'
def L(op, args=None, note='', n=400, quiet=False):
    args = args or {}
    r = k.dispatch(op, args, p)
    print('\nOP [%s] %s %s%s' % (CAPABILITIES.get(op), op, short(args, 500), ('   # ' + note) if note else ''))
    if not r['ok']:
        print('   REFUSED:', r['error']); return None
    if not quiet: print('   ->', short(r['result'], n))
    return r['result']
def S(text, note='', n=500):
    """one staC line through the route the writing strip uses"""
    from workbench.stac_bridge import route_program, blocked_reason
    op, args = route_program(text, allow_inspection=True)
    r = k.dispatch(op, args, p)
    print('\nSTAC %s%s\n   route: %s' % (text, ('   # ' + note) if note else '', op))
    if not r['ok']:
        print('   REFUSED:', r['error']); return None
    res = r['result']
    b = blocked_reason(res)
    if b: print('   BLOCKED:', b); return res
    rows = res.get('rows') if isinstance(res, dict) else None
    if rows is not None:
        print('   rows=%d' % len(rows))
        for row in rows[:6]: print('     ', short(row, n))
    else: print('   ->', short(res, n))
    return res
