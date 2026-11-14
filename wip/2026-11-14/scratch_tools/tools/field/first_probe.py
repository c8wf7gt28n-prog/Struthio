settle(100, 4); save('Graphite_UX_First_01_Home_Empty_%s.png' % tag)
w.a_field.trigger(); settle(100, 4); save('Graphite_UX_First_02_Field_Empty_%s.png' % tag)
v = w.field_page.view; print('empty field objects:', len(v.field.objects), '| problem:', repr(v.problem))
