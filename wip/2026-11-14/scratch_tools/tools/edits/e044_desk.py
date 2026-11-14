import io
def edit(p, pairs):
    t = io.open(p, encoding='utf8').read()
    for old, new in pairs:
        assert t.count(old) == 1, (p, t.count(old), old[:80])
        t = t.replace(old, new)
    io.open(p, 'w', encoding='utf8').write(t)
W = '/home/user/Struthio/workbench/'
edit(W + 'field_qt.py', [('''        p.save();p.setClipRect(whole)
        p.fillRect(whole, ink(t.TERMINAL_GROUND, 0.72))        # the work recedes while the page is read
''', '''        p.save()
        p.fillRect(QRectF(0, self.height() - self.foot_height(), self.width(), self.foot_height()), ink(t.GROUND, 0.86))      # the foot's keys do not act while the page is read
        p.setClipRect(whole)
        p.fillRect(whole, ink(t.TERMINAL_GROUND, 0.72))        # the work recedes while the page is read
''')])
edit(W + 'field_page.py', [('''    card = face.say_desk(len(page.view.field.objects), waiting, lines, go, plan, settle, doubts, look)
    page.steps = ();page.steps_of = '';page.pending = None;page.star = None
    if plan:                                   # the desk's own step, numbered 1: it puts the changes up; G then gives the go
        words = 'Settle what I can: %d change%s' % (len(plan), '' if len(plan) == 1 else 's')
        page.steps = (words,);page.steps_of = '*';page.star = settle
        page.view.steps = ((words, 'write'),);page.view.update()
    return card
''', '''    card = face.say_desk(len(page.view.field.objects), waiting, lines, go, plan, settle, doubts, look)
    page.steps = ();page.steps_of = '';page.pending = None;page.star = None
    if plan:                                   # the desk's own step, numbered 1: it puts the changes up; G then gives the go
        words = 'Settle what I can: %d change%s' % (len(plan), '' if len(plan) == 1 else 's')
        page.steps = (words,);page.steps_of = '*';page.star = settle
        page.view.steps = ((words, 'write'),);page.view.update()
    # The same answer where the eyes are: a light page over the work. It steps aside at the next key, so 1 settles and A
    # goes to the next thing that waits exactly as they do without it. Talk keeps the card, with its links.
    count = len(page.view.field.objects);sheet = [('q', 'I read the desk: %d thing%s, each from its record. Nothing is changed.' % (count, '' if count == 1 else 's'))]
    sheet.append(('h', 'Waits for you' if waiting else 'Nothing waits for you'))
    for obj, why, steps in waiting[:12]:
        first = next((step for step in steps if step.settles), None) or next((step for step in steps if step.kind == 'write'), None)
        sheet.append(('b', '“%s” — %s%s' % (obj.title, why, ('. Next: ' + first.words[:1].lower() + first.words[1:]) if first else '')))
    if len(waiting) > 12:sheet.append(('q', '… and %d more: A goes to each in turn.' % (len(waiting) - 12)))
    if doubts:
        sheet.append(('h', 'Looks right, and I doubt it'))
        sheet.extend(('b', '“%s” — %s: %s' % (row['title'], row['about'], row['why'])) for row in doubts[:8])
        if len(doubts) > 8:sheet.append(('q', '… and %d more: X on a sheet doubts it.' % (len(doubts) - 8)))
    elif answer.get('ok'):
        sheet.append(('h', 'Nothing I doubt'));sheet.append(('q', 'By the questions I have. They are few: this is not a proof.'))
    keys = (['1  settle what I can (%d change%s)' % (len(plan), '' if len(plan) == 1 else 's')] if plan else []) + (['A  the next that waits'] if waiting else []) + ['Esc  close']
    page.view.show_reading('The desk, checked', sheet, '      '.join(keys), 'field.read | pick waiting | select kind,title,state', light=True)
    if plan:page.view.steps = ((words, 'write'),)      # showing the page describes the sheet again; the desk's own step stays offered
    page.view.setFocus(Qt.OtherFocusReason)
    return card
''')])
print('ok')
