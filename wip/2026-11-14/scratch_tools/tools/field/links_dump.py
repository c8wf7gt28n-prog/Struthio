w.a_field.trigger(); settle(300, 4); v = w.field_page.view
for l in v.field.links:
    a = v.field.get(l.source); b = v.field.get(l.target)
    print('LINK', (a.title if a else l.source)[:34], '->', (b.title if b else l.target)[:34], '|', l.label, '| stale', l.stale)
print('DUMP DONE')
