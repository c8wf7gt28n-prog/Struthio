from common import *
from workbench.field_source import read_field
import time
k = Kernel(RUN / 'ws'); hold_processes()
for i in range(110): call(k, 'documents.create', {'title': 'Note %03d' % i, 'text': 'n'})
with k.db() as db: total = db.execute("SELECT count(*) FROM desk_records WHERE kind='document'").fetchone()[0]
t0 = time.time(); f, refused = read_field(k, P); dt = time.time() - t0
pages = [o for o in f.objects if o.kind in ('document', 'calculation')]
print('documents in the workspace: %d | pages + calculations in the Field: %d | refused: %s | read in %.2fs' % (total, len(pages), refused.refused, dt))
print('the worked case\'s own calculations still shown:', [o.title for o in f.objects if o.kind == 'calculation'], '| conclusion page shown:', any('Case conclusion' in o.title for o in f.objects))
print('census:', f.census(), '| note:', repr(f.note), '| left_out:', refused.left_out, '| unread:', len(refused.unread), '| refused lists:', refused.refused)
for n in (10, 30):
    for i in range(n): call(k, 'documents.create', {'title': 'More %03d' % i, 'text': 'n'})
    with k.db() as db: total = db.execute("SELECT count(*) FROM desk_records WHERE kind='document'").fetchone()[0]
    t0 = time.time(); f, r = read_field(k, P); dt = time.time() - t0
    pages = [o for o in f.objects if o.kind in ('document', 'calculation')]
    print('documents: %d | shown: %d | note: %r | calculations: %s | conclusion shown: %s | read in %.2fs' % (total, len(pages), f.note, [o.title[:20] for o in f.objects if o.kind == 'calculation'], any('Case conclusion' in o.title for o in f.objects), dt))
