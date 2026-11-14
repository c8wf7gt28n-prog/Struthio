"""Scope: which sheets belong. (a) the profile's own Office workspace with the same profile, (b) a notebook copy made in this
workspace, (c) a CSV imported from outside the workspace folder, (d) a sheet whose PDF admission was revoked."""
from common import *
from workbench.field_source import read_field, problems
from workbench import locations
k = Kernel(RUN / 'ws'); hold_processes()
def journal(kern):
    with kern.db() as db: return db.execute('SELECT count(*) FROM activity_journal').fetchone()[0], db.execute('SELECT count(*) FROM audit').fetchone()[0]
def offices(f):
    for o in f.objects:
        if o.id.startswith('office:'): print('    %-9s tag=%-9r %-30s state=%-12r lines=%s' % (o.kind, o.tag, o.title[:30], o.state, o.lines))
# (b) a notebook of THIS workspace copied into an Office document
nb = call(k, 'notebook.create', {'title': 'Field notes of this workspace'})
doc = call(k, 'office.from.notebook', {'notebook': nb['id'], 'expected_revision': nb['revision']})
print('(b) notebook copy:', doc.get('id'), '| source_state here:', call(k, 'office.get', {'id': doc['id']})['source_state']['state'])
# (c) a CSV imported from outside the workspace folder (the owner's Downloads)
down = HOME / 'Downloads'; down.mkdir(); csv = down / 'parts_from_downloads.csv'; csv.write_text('part,qty\nR1,2\n')
plan = call(k, 'office.import.preview', {'path': str(csv)}); done = call(k, 'office.import.commit', {'plan': plan['id'], 'expected_digest': plan['digest']})
print('(c) imported from Downloads:', done.get('document_id'), done.get('state'))
print('office.list now:', [(r['title'], r['kind']) for r in call(k, 'office.list')['documents']])
a = journal(k)
f, reader = read_field(k, P)
b = journal(k)
print('THIS workspace: census', f.census(), '| problems:', repr(problems(reader)), '| journal/audit rows %s -> %s' % (a, b)); offices(f)
print('   notebook copy shown here:', f.get('office:' + doc['id']) is not None, '| Downloads sheet shown here:', f.get('office:' + done['document_id']) is not None)
# (a) the profile's own Office workspace
root = locations.office(HOME / 'Concern' / 'Office'); ko = Kernel(root)
a = journal(ko)
fo, ro = read_field(ko, P)
b = journal(ko)
print('OFFICE workspace (%s): census %s | problems: %r | journal/audit rows %s -> %s' % (root.name, fo.census(), problems(ro), a, b)); offices(fo)
for r in call(ko, 'office.list')['documents']:
    got = call(ko, 'office.get', {'id': r['id']})
    print('   from the Office kernel:', r['title'][:30], '| source_state', got.get('source_state') if 'REFUSED' not in got else got, '| origin keys', sorted((got.get('origin') or {}).keys()))
