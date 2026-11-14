"""Do the staC lines return the object they are for (non-empty value)?"""
from common import *
from workbench.field_source import read_field, read_network
k = Kernel(RUN / 'ws'); hold_processes()
f, _ = read_field(k, P); n, _ = read_network(k, P)
first = True
for tag, field in (('work', f), ('network', n)):
    for o in field.objects:
        a = k.dispatch('language.run', {'text': o.stac}, operator())
        res = a.get('result') or {}
        if first: print('result keys:', sorted(res.keys())); first = False
        val = res.get('rows')
        empty = val in (None, [], {}, '')
        print('%-8s %-11s %-30s ok=%s empty=%s value=%s' % (tag, o.kind, o.title[:30], a.get('ok'), empty, json.dumps(val, default=str)[:170]))
