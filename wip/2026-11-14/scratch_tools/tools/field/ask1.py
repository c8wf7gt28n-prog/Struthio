# rehearsal script: executed inside model.py once the brain is READY
from PySide6.QtWidgets import QLabel
face = w.shell2.face; bar = w.type_bar
def bubbles():
    return [face.lines.itemAt(i).widget() for i in range(face.lines.count()) if face.lines.itemAt(i).widget() is not None]
def words(card):
    return [l.text().replace('​', '') for l in card.findChildren(QLabel)]
def ask(text, seconds=400):
    t = time.time(); n = len(bubbles()); w.shell2.ask(text); settle(50, 3)
    while face.job and time.time() - t < seconds: settle(150, 3)
    settle(120, 4); took = time.time() - t
    print('\nQ: %r  (%.1f s%s)' % (text, took, ', STILL RUNNING' if face.job else ''))
    for card in bubbles()[n + 1:]:
        for line in words(card): print('   |', line[:700].replace('\n', '\n   |   '))
        print('   +', 'stac=%r' % getattr(card, 'stac', None) if hasattr(card, 'stac') else '(no staC line on this card)')
    return took
w.shell2.show_slate_face(); settle(); face.refresh(); print('line under her name:', face.model.text())
w.a_field.trigger(); settle(); v = w.field_page.view
calc = next(o for o in v.field.objects if o.kind == 'calculation'); v.field.select(calc.id); v.update(); settle(5, 2)
print('selected sheet:', calc.title, '|', calc.stac)
ask('what went into this?')
save('Graphite_Model_01_Asked_About_A_Calculation_%s.png' % tag)
finding = next(o for o in v.field.objects if o.kind == 'finding'); v.field.select(finding.id); v.update(); settle(5, 2)
print('selected sheet:', finding.title)
ask('why do we believe this?')
save('Graphite_Model_02_Asked_About_A_Finding_%s.png' % tag)
for kind, q in (('question', 'what is still open here?'), ('sheet', 'where did this table come from, and is it still good?'), ('source', 'what is this file?'), ('document', 'what is this page?')):
    obj = next((o for o in v.field.objects if o.kind == kind), None)
    if obj is None: continue
    v.field.select(obj.id); v.update(); settle(5, 2); print('selected sheet:', kind, '|', obj.title); ask(q)
v.field.select(calc.id); v.update(); settle(5, 2); ask('what is the capital of France?')
