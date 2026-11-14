# with the real small model loaded: Stacy still reads first and says it; and the doer is unchanged (no model takes part in a step)
import copy
exec(open(S / 'tools/field/ask1.py').read().split("w.shell2.show_slate_face()")[0])
w.shell2.show_slate_face(); settle(); face.refresh(); print('line under her name:', face.model.text())
w.a_field.trigger(); settle(); v = w.field_page.view
calc = next(o for o in v.field.objects if o.kind == 'calculation' and 'Settled' in o.title); v.field.select(calc.id); v._describe(); v.update(); settle(5, 2)
ask('what went into this?')
der = call('documents.get', {'id': calc.target['id']})['document']['derivation']
sheet = call('office.get', {'id': der['sheet']}); d = copy.deepcopy(sheet['document']); d['sheets'][0]['cells']['B3']['value'] = '300'
call('office.save', {'id': der['sheet'], 'expected_revision': sheet['revision'], 'document': d})
for key, name in ((Qt.Key_C, 'C'), (Qt.Key_1, '1'), (Qt.Key_G, 'G')):
    QTest.keyClick(v, key); settle(200, 5); print('%s -> %s' % (name, words(bubbles()[-1])[0][:120]))
print('calculations:', [(o.title, o.state) for o in v.field.objects if o.kind == 'calculation'])
new = next(o for o in v.field.objects if o.kind == 'calculation' and 'Settled' in o.title); v.field.select(new.id); v._describe(); v.update(); settle(5, 2)
ask('what went into this now?')
save('Graphite_Do_10_With_A_Model_%s.png' % tag)
