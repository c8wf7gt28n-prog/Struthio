import os; os.environ['PROBE_W'] = '1366'; os.environ['PROBE_H'] = '768'
from winbase import *
bridge = w.ledger_bridge
del w.ledger_bridge
v = field(); where('F9 without the records'); print('   objects:', len(v.field.objects), '| problem:', repr(w.field_page.problem), '| status line:', repr(status()), '| accessible description:', repr(v.accessibleDescription()))
save('w12_no_records.png')
w.ledger_bridge = bridge
QTest.keyClick(v, Qt.Key_R); settle(); print('   records back, R ->', v.field.census(), '| problem:', repr(w.field_page.problem))
finish()
