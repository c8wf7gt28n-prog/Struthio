# Stacy doubts: the untouched worked case first, then traps made on purpose
import json, copy
from PySide6.QtWidgets import QLabel
k = w.ledger_bridge.kernel; p = operator(); face = w.shell2.face
def op(name, args=None):
    r = k.dispatch(name, args or {}, p); return r['result'] if r['ok'] else {'REFUSED': r['error']['message']}
def cards(): return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def said(card, n=4): return [l.text().replace('​', '')[:900] for l in card.findChildren(QLabel)][:n]
def show(ident, title):
    r = op('field.doubt', {'id': ident}); print('\n%s  [%s doubt, %s cannot tell, %s hold]' % (title[:70], r.get('doubts'), r.get('cannot_tell'), r.get('holds')))
    for row in r.get('rows', []): print('   %-11s %-24s %s' % (row['verdict'], row['about'], row['why'][:230]))
    return r
w.a_field.trigger(); settle(); v = w.field_page.view
print('=== THE WORKED CASE AS IT WAS DELIVERED ===')
for o in v.field.objects:
    if o.kind in ('finding', 'calculation', 'sheet'): show(o.id, '%s · %s' % (o.kind, o.title))
d = op('field.doubt'); print('\nthe whole desk: looked at %s things · %s doubts · %s cannot tell' % (d['looked_at'], d['doubts'], d['cannot_tell']))
r = k.dispatch('language.run', {'text': 'field.doubt | pick rows | where verdict=doubt | select title,about'}, p); print('staC › field.doubt | pick rows | where verdict=doubt | select title,about ->', [(x['title'][:40], x['about']) for x in r['result']['rows']] if r['ok'] else r['error'])
# the see line of the vacuous check: does the narrowed read really read the cell
vac = next((row for row in op('field.doubt', {'id': next(o.id for o in v.field.objects if 'keeps the 80 ms' in o.title)})['rows'] if row['about'] == 'a check that can fail'), None)
if vac:
    r = k.dispatch('language.run', {'text': vac['see']}, p); print('its see line:', vac['see'][:120], '->', r['result']['rows'] if r['ok'] else r['error'])
# X in the Field
f = next(o for o in v.field.objects if 'keeps the 80 ms' in o.title); v.field.select(f.id); v._reveal(); v._describe(); v.update(); settle(5, 2)
QTest.keyClick(v, Qt.Key_X); settle(100, 5); c = cards()[-1]; print('\nX on that finding -> Field in front: %s | keyboard: %s' % (w._field_active, type(app.focusWidget()).__name__))
for line in said(c, 3): print('   |', line.replace('\n', '\n   |   ')[:1100])
save('Graphite_Doubt_01_A_Check_That_Cannot_Fail_%s.png' % tag)
QTest.keyClick(v, Qt.Key_C); settle(120, 5); c = cards()[-1]; print('\nC ->', said(c, 1)[0], '| doubts listed:', [(r_['title'][:32], r_['about']) for r_ in getattr(c, 'doubts', [])])
save('Graphite_Doubt_02_Desk_Check_%s.png' % tag)
print('\n=== TRAPS MADE ON PURPOSE ===')
calc = next(o for o in v.field.objects if o.kind == 'calculation' and 'Settled' in o.title)
doc = op('documents.get', {'id': calc.target['id']})['document']; der = doc['derivation']
sheet = op('office.get', {'id': der['sheet']}); dd = copy.deepcopy(sheet['document']); dd['sheets'][0]['cells']['B3']['value'] = '300'
op('office.save', {'id': der['sheet'], 'expected_revision': sheet['revision'], 'document': dd})
show('office:' + der['sheet'], 'the sheet after B3 was changed to 300')
show(calc.id, 'the calculation, behind its sheet')
new = op('office.datasheet.recheck', {'id': calc.target['id'], 'expected_revision': doc['revision']})['document']
show('document:' + new['id'], 'the calculation brought up to date from the edited sheet')
s2 = op('office.get', {'id': der['sheet']})
mixed = op('office.datasheet.report', {'id': der['sheet'], 'expected_revision': s2['revision'], 'expression': 'startup_current - settled_current', 'inputs': {'startup_current': 'B4', 'settled_current': 'B3'}, 'output_unit': 'mA'})
print('\na calculation that mixes a startup reading with a settled one:', mixed.get('REFUSED') or mixed['document']['title'])
if 'document' in mixed: show('document:' + mixed['document']['id'], 'that calculation')
