from common import *
from workbench.field_source import read_field
k = Kernel(RUN / 'ws'); hold_processes()
try:
    import docx
except ImportError:
    print('python-docx not installed in the venv; cannot build a .docx here'); raise SystemExit
d = docx.Document(); d.add_paragraph('A letter to the supplier about the pulse width.'); path = RUN / 'ws' / 'Supplier letter.docx'; d.save(str(path))
plan = call(k, 'office.import.preview', {'path': str(path)}); print('preview:', plan.get('mode'), plan.get('REFUSED'), plan.get('EXC'))
done = call(k, 'office.import.commit', {'plan': plan['id'], 'expected_digest': plan['digest']}); print('commit:', done.get('state'))
print('office.list:', [(r['title'], r['kind']) for r in call(k, 'office.list')['documents']])
f, _ = read_field(k, P)
for o in f.objects:
    if 'letter' in o.title.lower(): print('in the Field -> kind:', o.kind, '| role:', o.role, '| state:', o.state, '| column:', f.rank_title(f.rank_of(o.id)))
print('census:', f.census())
