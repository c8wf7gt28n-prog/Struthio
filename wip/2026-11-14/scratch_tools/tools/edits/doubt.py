import os
os.chdir('/home/user/Struthio')
def edit(p, pairs):
    s=open(p).read()
    for a,b in pairs:
        assert s.count(a)==1, (p, s.count(a), a[:80]); s=s.replace(a,b)
    open(p,'w').write(s)

edit('workbench/field_service.py', [
("""  field.whatif  read   {id, set}    a calculation worked again with other values for some inputs, changing nothing
""", """  field.whatif  read   {id, set}    a calculation worked again with other values for some inputs, changing nothing
  field.doubt   read   {id?}        what a plausible result may hide: one thing cross-examined, or every doubt on the desk
"""),
("""  field.whatif {"id":"document:<id>","set":{"B3":"320"}} | select says_now,would_be,exact
""", """  field.whatif {"id":"document:<id>","set":{"B3":"320"}} | select says_now,would_be,exact
  field.doubt {"id":"claim:<id>"} | pick rows | select verdict,about,why
  field.doubt | pick rows | where verdict=doubt | select title,about,why
"""),
("""    'field.whatif': ({'id': TEXT, 'set': {'type': 'object'}}, ['id', 'set']),
}""", """    'field.whatif': ({'id': TEXT, 'set': {'type': 'object'}}, ['id', 'set']),
    'field.doubt': ({'id': TEXT}, []),
}"""),
("""def dispatch(kernel, operation, args, principal):
    if operation == 'field.read':return read(kernel, principal)""", '''def doubt(kernel, principal, ident=None):
    """One thing cross-examined (workbench/field_doubt.py), worst first; or, with no id, every doubt and every cannot-tell on
    the desk. Exact questions put to the records: no model, nothing changed."""
    from .field_doubt import desk, doubts_for
    from .field_source import read_field
    field, _ = read_field(kernel, principal)
    if ident:
        obj = field.get(ident)
        if obj is None:
            raise ValueError('Nothing on the desk has the id %s. field.read lists the ids.' % ident[:80])
        found = doubts_for(kernel, principal, obj, field)
        rows = [{'verdict': d.verdict, 'about': d.about, 'why': d.why, 'see': d.see} for d in found]
        return {'schema': SCHEMA, 'id': obj.id, 'title': obj.title, 'kind': obj.kind, 'rows': rows,
                'doubts': sum(1 for d in found if d.verdict == 'doubt'), 'cannot_tell': sum(1 for d in found if d.verdict == 'cannot tell'),
                'holds': sum(1 for d in found if d.verdict == 'holds')}
    found = desk(kernel, principal, field)
    rows = [{'title': obj.title, 'kind': obj.kind, 'id': obj.id, 'verdict': d.verdict, 'about': d.about, 'why': d.why, 'see': d.see} for obj, d in found]
    return {'schema': SCHEMA, 'rows': rows, 'doubts': sum(1 for _, d in found if d.verdict == 'doubt'),
            'cannot_tell': sum(1 for _, d in found if d.verdict == 'cannot tell'), 'looked_at': sum(1 for obj in field.objects if obj.kind in ('calculation', 'sheet', 'finding', 'condition', 'source'))}


def dispatch(kernel, operation, args, principal):
    if operation == 'field.doubt':return doubt(kernel, principal, args.get('id'))
    if operation == 'field.read':return read(kernel, principal)'''),
])
edit('workbench/activity.py', [(""" 'field.read','field.trace','field.whatif'})""", """ 'field.read','field.trace','field.whatif','field.doubt'})""")])

edit('workbench/field_qt.py', [
("""    trace_asked = Signal(object)       # T: where the selected object comes from and what rests on it
""", """    trace_asked = Signal(object)       # T: where the selected object comes from and what rests on it
    doubt_asked = Signal(object)       # X: cross-examine the selected object for what a plausible result may hide
"""),
("""        elif key == Qt.Key_T and plain:      # T: trace""", """        elif key == Qt.Key_X and plain:      # X: doubt it
            if self.selected() is not None:self.doubt_asked.emit(self.selected())
            return
        elif key == Qt.Key_T and plain:      # T: trace"""),
("""(2, 'D  do'), (4, 'C  check all'), (5, 'T  trace'), (6, 'S  staC'), (8, 'Menu  more'), (7, 'A  next waiting'), (9, 'R  look again'), (0, 'Esc  back')]""",
 """(2, 'D  do'), (4, 'X  doubt'), (5, 'C  check all'), (6, 'T  trace'), (7, 'S  staC'), (9, 'Menu  more'), (8, 'A  next waiting'), (10, 'R  look again'), (0, 'Esc  back')]"""),
("""        legend = [(10, '%s  %s' % (letter.upper(), name)) for name, letter in self.faces if name != self.face] + legend""",
 """        legend = [(11, '%s  %s' % (letter.upper(), name)) for name, letter in self.faces if name != self.face] + legend"""),
])
edit('workbench/field_page.py', [
("""        self.view.trace_asked.connect(lambda obj: trace(self.host, obj))""", """        self.view.trace_asked.connect(lambda obj: trace(self.host, obj))
        self.view.doubt_asked.connect(lambda obj: doubt(self.host, obj))"""),
("""def full_window(host, obj):
    \"\"\"F on the shelf:""", '''def doubt(host, obj):
    """X: cross-examine this for what a plausible result may hide. Exact questions are put to the records (field.doubt, a staC
    line like any other): what does not hold comes first, then what cannot be told, then what holds. With a model Stacy then
    says it in her own words. Nothing is changed."""
    from .field_do import js
    shell = getattr(host, 'shell2', None)
    if shell is None or obj is None:return None
    line = 'field.doubt %s | pick rows | select verdict,about,why' % js(id=obj.id)
    shell.face.thing = {**thing_of(host, obj), 'stac': line, 'explicit': True,
                        'intro': 'I doubted “%s”. What does not hold comes first, then what I cannot tell, then what holds:' % obj.title}
    shell.ask('What could be wrong with “%s”?' % obj.title)
    if getattr(host, '_field_active', False):host.field_page.view.setFocus(Qt.OtherFocusReason)


def full_window(host, obj):
    """F on the shelf:'''),
("""    plan = settling(waiting)
    def settle():""", """    plan = settling(waiting)
    answer = kernel.dispatch('field.doubt', {}, operator())      # the same check also cross-examines everything: what a plausible result may hide
    doubts = [row for row in (answer['result']['rows'] if answer.get('ok') else ()) if row['verdict'] == 'doubt']
    if answer.get('ok'):lines.append('field.doubt | pick rows | select title,verdict,about,why')
    def settle():"""),
("""    card = face.say_desk(len(page.view.field.objects), waiting, lines, go, plan, settle)""",
 """    def look(ident):
        obj = page.view.field.get(ident)
        if obj is None:return
        page.view.field.select(ident);page.view._reveal_pending = True;page.view._describe();page.view.update();doubt(host, obj)
    card = face.say_desk(len(page.view.field.objects), waiting, lines, go, plan, settle, doubts, look)"""),
])
edit('workbench/shell2.py', [
("""    def say_desk(self, count, waiting, lines, go, plan=(), settle=None):""", """    def say_desk(self, count, waiting, lines, go, plan=(), settle=None, doubts=(), look=None):"""),
("""        if plan and settle is not None:
            card.box.addWidget(sentence('{settle}', {'settle': ('Settle what I can: %d change%s, one Run' % (len(plan), '' if len(plan) == 1 else 's'), settle)}))""",
 """        if plan and settle is not None:
            card.box.addWidget(sentence('{settle}', {'settle': ('Settle what I can: %d change%s, one Run' % (len(plan), '' if len(plan) == 1 else 's'), settle)}))
        if doubts:                           # what a plausible result may hide: looked for on everything, said beside what waits
            head = QLabel('I doubt %d thing%s that look%s right:' % (len(doubts), '' if len(doubts) == 1 else 's', 's' if len(doubts) == 1 else ''));head.setWordWrap(True);card.box.addWidget(head)
            for row in doubts[:8]:
                if look is not None:card.box.addWidget(sentence('{go}', {'go': ('“%s”' % row['title'], lambda ident=row['id']:look(ident))}))
                said = QLabel(breakable(row['why']));said.setWordWrap(True);said.setStyleSheet('color:%s' % QUIET);said.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(said)
            if len(doubts) > 8:card.box.addWidget(QLabel('… and %d more: X on a sheet doubts it' % (len(doubts) - 8)))"""),
("""        card.waiting = waiting;card.plan = plan""", """        card.waiting = waiting;card.plan = plan;card.doubts = list(doubts)"""),
])
edit('workbench/context_menu.py', [
("""    out.append(Entry('field:trace', 'Trace it', 'command', lambda:view.trace_asked.emit(obj), icon='line', caption='T',""",
 """    out.append(Entry('field:doubt', 'Doubt it', 'command', lambda:view.doubt_asked.emit(obj), icon='line', caption='X',
                     tip='Cross-examine it for what a plausible result may hide: what does not hold, what cannot be told, what holds'))
    out.append(Entry('field:trace', 'Trace it', 'command', lambda:view.trace_asked.emit(obj), icon='line', caption='T',"""),
("""            lines = (('Everything that waits', 'field.read | pick waiting | select kind,title,state'),""",
 """            lines = (('Everything that waits', 'field.read | pick waiting | select kind,title,state'),
                     ('What I doubt', 'field.doubt | pick rows | where verdict=doubt | select title,about,why'),"""),
])
edit('workbench/field_do.py', [
("""        steps.insert(1, Step('Trace it along the wires', 'read', 'field.trace %s | pick rows | select way,steps,kind,title,state,by' % js(id=obj.id)))""",
 """        steps.insert(1, Step('Trace it along the wires', 'read', 'field.trace %s | pick rows | select way,steps,kind,title,state,by' % js(id=obj.id)))
    if steps and obj.kind in ('calculation', 'sheet', 'finding', 'condition', 'source'):   # it can be cross-examined
        steps.insert(1, Step('Doubt it', 'read', 'field.doubt %s | pick rows | select verdict,about,why' % js(id=obj.id)))"""),
])
print('edits applied')
