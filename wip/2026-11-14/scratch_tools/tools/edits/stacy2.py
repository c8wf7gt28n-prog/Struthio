import os
os.chdir('/home/user/Struthio')
def edit(p, pairs):
    s=open(p).read()
    for a,b in pairs:
        assert s.count(a)==1, (p, s.count(a), a[:80]); s=s.replace(a,b)
    open(p,'w').write(s)

# ---- the Field page: `this`, and T to trace -----------------------------------------------------------------------------------
edit('workbench/field_page.py', [
("""from PySide6.QtCore import QSize, Qt""", """import re

from PySide6.QtCore import QSize, Qt"""),
("""        self.view.go_asked.connect(lambda: go(self.host))""", """        self.view.go_asked.connect(lambda: go(self.host))
        self.view.trace_asked.connect(lambda obj: trace(self.host, obj))"""),
("""def full_window(host, obj):""", '''THIS = re.compile(r'^(explain\\s+)?this\\b\\s*(\\|.*)?$', re.IGNORECASE | re.DOTALL)


def expand_this(host, text):
    """`this` at the start of a staC line is the sheet selected in the Field. Alone it is that sheet's own line; before a `|`
    it is the read that line starts with, so `this | pick … | select …` goes on from the same record the rail shows. The line
    is written out before it runs, so what ran is always visible. Text that does not start with `this` comes back unchanged;
    when there is nothing `this` could mean, ValueError says so in words."""
    found = THIS.match(str(text).strip())
    if not found:return text
    page = getattr(host, 'field_page', None);obj = page.view.selected() if page is not None else None
    if obj is None or not obj.stac:
        raise ValueError('“this” is the sheet selected in the Field (F9), and nothing is selected there')
    lead = found.group(1) or '';rest = found.group(2)
    return lead + (obj.stac if rest is None else obj.stac.split(' | ', 1)[0] + ' ' + rest.strip())


def trace(host, obj):
    """T: where this comes from and what rests on it, hop by hop along the wires. Stacy reads it (field.trace, a staC line like
    any other) and shows the rows; with a model she then tells it in her own words."""
    from .field_do import js
    shell = getattr(host, 'shell2', None)
    if shell is None or obj is None:return None
    line = 'field.trace %s | pick rows | select way,steps,kind,title,state,by' % js(id=obj.id)
    shell.face.thing = {**thing_of(host, obj), 'stac': line, 'explicit': True,
                        'intro': 'Where “%s” comes from, farthest first, then what rests on it:' % obj.title}
    shell.ask('Where does “%s” come from, and what rests on it?' % obj.title)
    if getattr(host, '_field_active', False):host.field_page.view.setFocus(Qt.OtherFocusReason)


def full_window(host, obj):'''),
])
edit('workbench/field_qt.py', [
("""    go_asked = Signal()                # G: the owner's go for what waits in Talk. Never a digit: digits only choose
""", """    go_asked = Signal()                # G: the owner's go for what waits in Talk. Never a digit: digits only choose
    trace_asked = Signal(object)       # T: where the selected object comes from and what rests on it
"""),
("""        elif key == Qt.Key_G and plain:      # G: go. Only while something waits in Talk and says so here""",
 """        elif key == Qt.Key_T and plain:      # T: trace
            if self.selected() is not None:self.trace_asked.emit(self.selected())
            return
        elif key == Qt.Key_G and plain:      # G: go. Only while something waits in Talk and says so here"""),
("""(2, 'D  do'), (4, 'C  check all'), (5, 'S  staC'), (7, 'Menu  more'), (6, 'A  next waiting'), (8, 'R  look again'), (0, 'Esc  back')]""",
 """(2, 'D  do'), (4, 'C  check all'), (5, 'T  trace'), (6, 'S  staC'), (8, 'Menu  more'), (7, 'A  next waiting'), (9, 'R  look again'), (0, 'Esc  back')]"""),
("""        legend = [(9, '%s  %s' % (letter.upper(), name)) for name, letter in self.faces if name != self.face] + legend""",
 """        legend = [(10, '%s  %s' % (letter.upper(), name)) for name, letter in self.faces if name != self.face] + legend"""),
])

# ---- the writing strip: `this` is written out before a line is recognised, previewed or run --------------------------------
edit('workbench/typebar_qt.py', [
("""        if self.target != 'slate':return False
        if not text:return True
        if popup is not None:popup.hide()""", """        if self.target != 'slate':return False
        if not text:return True
        try:                                  # `this` is the sheet selected in the Field: written out here, so what runs is what shows
            from .field_page import expand_this
            text = expand_this(self.host, text)
        except ValueError as exc:
            self.note(str(exc));return True
        if popup is not None:popup.hide()"""),
("""            kind = stac_hint_kind(self.box.text()) or kind""", """            written = self.box.text()
            try:
                from .field_page import expand_this
                written = expand_this(self.host, written)
            except ValueError:pass
            kind = stac_hint_kind(written) or kind"""),
])
edit('workbench/shell2.py', [
("""    from .engine import engineering
    from .engineering_kernel import operator
    try:r = engineering(host.root).dispatch('language.run', {'text': text}, operator())
    except Exception as exc:r = {'ok': False, 'error': {'message': str(exc)}}""", """    from .engine import engineering
    from .engineering_kernel import operator
    try:
        from .field_page import expand_this
        text = expand_this(host, text)        # `this`: the sheet selected in the Field
    except ValueError as exc:
        return [('section', 'PREVIEW', None), ('note', str(exc)[:110], None)]
    try:r = engineering(host.root).dispatch('language.run', {'text': text}, operator())
    except Exception as exc:r = {'ok': False, 'error': {'message': str(exc)}}"""),

# ---- Stacy: what if, and the intro and the way in of a question whose thing is known exactly --------------------------------
("""    def ask(self, text, about=None):
        thing = self.thing_asked_about(text)
        if thing and not about:about = '%s “%s”, read with the staC line: %s' % (thing['kind'], thing['title'], thing['stac'])
        about = about or self.current_item()
        self.mine(text)
        if self.job:self.say('I am still answering the last question. Stop it from the Brain room, or wait a moment.');return
        direct = self.direct_request(text)  # the open page may resolve the request by explicit rule, with no model (documents)""",
 '''    def what_if(self, text):
        """“What if B3 were 320?”, asked while a calculation is selected in the Field: the calculation's own recipe worked with
        that value, exactly, changing nothing (field.whatif, a read). The inputs are named by their cell, their symbol or
        their words; several go together with "and". Returns the thing to answer about, a dict with 'refusal' when the
        question is a what-if but names no input of this calculation, or None when it is not a what-if about a calculation."""
        asked = re.match(r'^\\s*what\\s+if\\b(.*)$', text, re.IGNORECASE | re.DOTALL)
        view = getattr(getattr(self.host, 'field_page', None), 'view', None)
        chosen = view.selected() if asked and view is not None and getattr(self.host, '_field_active', False) else None
        if chosen is None or chosen.kind != 'calculation' or not isinstance(chosen.target, dict):return None
        got = call(self.host, 'documents.get', {'id': chosen.target.get('id')}) or {}
        inputs = ((got.get('document') or {}).get('derivation') or {}).get('inputs') or []
        if not inputs:return None
        names = {}
        for item in inputs:
            for name in (str(item['cell']), str(item['symbol']), str(item['symbol']).replace('_', ' '), str(item.get('parameter') or '')):
                if name.strip():names[name.strip().lower()] = item['cell']
        filler = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'to', 'at', 'of', 'became', 'becomes', 'goes', 'went', 'equals', 'equal', 'cell', 'value', 'in', 'it', 'its'}
        setting = {}
        for part in re.split(r'\\band\\b|[,;]', asked.group(1).replace('=', ' ').replace('?', ' ')):
            tokens = part.split();at = next((i for i in range(len(tokens) - 1, -1, -1) if re.fullmatch(r'-?\\d+(?:\\.\\d+)?', tokens[i])), None)
            if at is None:continue
            name = ' '.join(t for t in tokens[:at] if t.lower() not in filler).lower()
            cell = names.get(name) or next((c for n, c in names.items() if name and all(word in n.split() for word in name.split())), None)
            if cell:setting[cell] = tokens[at]
        said = ', '.join('%s (%s, in %s)' % (i['cell'], i.get('parameter') or i['symbol'], i['unit']) for i in inputs)
        if not setting:
            return {'refusal': 'Say which input and its new value, for example “what if %s were %s”. This calculation reads %s.' % (inputs[-1]['cell'], inputs[-1]['value'], said)}
        from .field_do import js
        from .field_page import thing_of
        return {**thing_of(self.host, chosen), 'stac': 'field.whatif %s | select says_now,would_be,exact,set,changed' % js(id=chosen.id, set=setting),
                'explicit': True, 'intro': 'What if, for “%s”. Worked exactly with its own recipe; nothing is changed:' % chosen.title}

    def ask(self, text, about=None):
        thing = self.what_if(text)
        if thing and thing.get('refusal'):
            self.thing = None;self.mine(text);self.say(thing['refusal']);return
        thing = thing or self.thing_asked_about(text)
        if thing and not about:about = '%s “%s”, read with the staC line: %s' % (thing['kind'], thing['title'], thing['stac'])
        about = about or self.current_item()
        self.mine(text)
        if self.job:self.say('I am still answering the last question. Stop it from the Brain room, or wait a moment.');return
        # A question whose thing was named exactly (its menu, T, a what-if) is hers to read; any other may be the open page's to do.
        direct = None if thing and thing.get('explicit') else self.direct_request(text)'''),
("""            card = self.answer_in_stac(thing, 'The records about “%s”, and the staC that reads them:' % thing['title'])
            if not card.answered:return""", """            card = self.answer_in_stac(thing, thing.get('intro') or 'The records about “%s”, and the staC that reads them:' % thing['title'])
            if not card.answered:return"""),
("""            card = self.answer_in_stac(thing, 'No model is loaded, so this is not in my own words. This is what the records say about “%s”, and the staC that reads it:' % thing['title'])
            card.box.addWidget(sentence('{choose}', {'choose': ('Choose a model', lambda:open_destination(self.host, 'slate').pick_model())}))
            return""", """            card = self.answer_in_stac(thing, thing.get('intro') or 'No model is loaded, so this is not in my own words. This is what the records say about “%s”, and the staC that reads it:' % thing['title'])
            if not thing.get('intro'):         # a trace or a what-if is whole without a model; an open question about a sheet is not
                card.box.addWidget(sentence('{choose}', {'choose': ('Choose a model', lambda:open_destination(self.host, 'slate').pick_model())}))
            return"""),
])
edit('workbench/context_menu.py', [
("""    if face is not None:face.thing = field_page.thing_of(host, obj)""", """    if face is not None:face.thing = {**field_page.thing_of(host, obj), 'explicit': True}"""),
("""    out.append(Entry('field:do', 'What can be done', 'command', lambda:view.do_asked.emit(obj), icon='line', caption='D',""",
 """    out.append(Entry('field:trace', 'Trace it', 'command', lambda:view.trace_asked.emit(obj), icon='line', caption='T',
                     tip='Where it comes from and what rests on it, hop by hop along the wires'))
    out.append(Entry('field:do', 'What can be done', 'command', lambda:view.do_asked.emit(obj), icon='line', caption='D',"""),
("""            lines = (('The pages', 'documents.list | pick documents | select title,revision,words'),""",
 """            lines = (('Everything that waits', 'field.read | pick waiting | select kind,title,state'),
                     ('What changed lately', 'field.read | pick objects | where lately=yes | select kind,title,changed_at'),
                     ('The wires', 'field.read | pick links | select from,to,label,stale'),
                     ('The pages', 'documents.list | pick documents | select title,revision,words'),"""),
])
edit('workbench/field_do.py', [
("""    if not steps and obj.stac:
        steps = [Step('See what the records say about it', 'read', obj.stac)]""", """    if not steps and obj.stac:
        steps = [Step('See what the records say about it', 'read', obj.stac)]
    if field is not None and steps and (field.fed_by(obj.id) or field.feeds(obj.id)):      # it has wires: they can be followed
        steps.insert(1, Step('Trace it along the wires', 'read', 'field.trace %s | pick rows | select way,steps,kind,title,state,by' % js(id=obj.id)))"""),
])
print('edits applied')
