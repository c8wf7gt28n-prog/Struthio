import os
os.chdir('/home/user/Struthio')
def edit(p, pairs):
    s=open(p).read()
    for a,b in pairs:
        assert s.count(a)==1, (p, s.count(a), a[:80]); s=s.replace(a,b)
    open(p,'w').write(s)

edit('workbench/field_model.py', [
("""    column: int = -1                    # a fixed column for a face that is a shelf, not a flow (the programs); -1: by kind and by wires
""", """    column: int = -1                    # a fixed column for a face that is a shelf, not a flow (the programs); -1: by kind and by wires
    touched: float = 0.0                # when its record last changed (seconds since 1970), where the records say; 0: not known

    def lately(self, now, within=LATELY):
        \"\"\"Whether its record changed in the last hours: what the owner, or Graphite for the owner, has just been working on.\"\"\"
        return bool(self.touched) and 0 <= now - self.touched <= within
"""),
("""@dataclass
class FieldObject:""", """LATELY = 12 * 3600                       # "lately": the last twelve hours, a working day's reach


@dataclass
class FieldObject:"""),
("""        recheck = sum(1 for obj in self.objects if obj.state == STATE_RECHECK)
        if recheck:
            parts.append('%d to recheck' % recheck)
        return parts""", """        recheck = sum(1 for obj in self.objects if obj.state == STATE_RECHECK)
        if recheck:
            parts.append('%d to recheck' % recheck)
        import time
        now = time.time();lately = sum(1 for obj in self.objects if obj.lately(now))
        if lately:
            parts.append('%d changed lately' % lately)
        return parts"""),
])
edit('workbench/field_source.py', [
("""        self.results = {}            # a calculation's result as words ("3.36 W"), by its id
""", """        self.results = {}            # a calculation's result as words ("3.36 W"), by its id
        self.touched = {}            # object id -> when its record last changed, where a record says (pages, findings, jobs)
"""),
("""            ident = 'document:' + row['id'];target = {'kind': 'document', 'id': row['id']}
            got = self.call('documents.get', {'id': row['id']}, record=ident)""", """            ident = 'document:' + row['id'];target = {'kind': 'document', 'id': row['id']}
            self.touched[ident] = row.get('updated') or 0
            got = self.call('documents.get', {'id': row['id']}, record=ident)"""),
("""                ident = 'claim:' + claim['id'];question = str(claim.get('role', '')).upper() == 'QUESTION'""",
 """                ident = 'claim:' + claim['id'];question = str(claim.get('role', '')).upper() == 'QUESTION'
                self.touched[ident] = claim.get('created') or 0"""),
("""    moved = _moved(reader)""", """    for obj in reader.objects:   # what the records say of when each thing last changed; a thing with no such record stays unmarked
        try:obj.touched = float(reader.touched.get(obj.id) or 0)
        except (TypeError, ValueError):obj.touched = 0.0
    moved = _moved(reader)"""),
])
edit('workbench/field_qt.py', [
("""        pad = 12 * s;inner = r.adjusted(pad, pad - 2 * s, -pad, -pad + 2 * s)
        # Kind at the left, state at the right.""", """        if obj.lately(self._now):            # its record changed in the last hours: a small turned corner, the mark of what was just worked on
            fold = 9 * s;p.save();p.setPen(Qt.NoPen);p.setBrush(ink(t.AMBER_EDGE, 0.55 + 0.4 * keep))
            p.drawPolygon(QPolygonF([QPointF(r.right() - fold, r.top()), QPointF(r.right(), r.top()), QPointF(r.right(), r.top() + fold)]));p.restore()
        pad = 12 * s;inner = r.adjusted(pad, pad - 2 * s, -pad, -pad + 2 * s)
        # Kind at the left, state at the right."""),
("""        self.steps = ()                     # what can be done about the selected sheet, while the owner looks at it: (words, kind) pairs
""", """        self.steps = ()                     # what can be done about the selected sheet, while the owner looks at it: (words, kind) pairs
        self._now = 0.0                     # the time of this painting, for "changed lately"
"""),
])
s=open('workbench/field_qt.py').read()
a="""            p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
            p.fillRect(self.rect(), QColor(t.TERMINAL_GROUND))"""
assert s.count(a)==1
s=s.replace(a, """            p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.TextAntialiasing)
            import time
            self._now = time.time()
            p.fillRect(self.rect(), QColor(t.TERMINAL_GROUND))""")
open('workbench/field_qt.py','w').write(s)
print('QPolygonF imported:', 'QPolygonF' in s.split('class FieldView')[0])

edit('workbench/field_do.py', [
("""BY_KIND = {'calculation': _calculation, 'sheet': _sheet, 'finding': _claim, 'question': _claim, 'source': _source,
           'condition': _condition, 'job': _job, 'document': _page}""",
 """# The programs that have a window of their own, the kind of file each opens, and how the owner knows it. Each is started only
# through its own operation (programs.<key>.open), which takes a file and the digest it was just read with, and asks.
NATIVE = {'freecad': ('.fcstd', 'FreeCAD'), 'inkscape': ('.svg', 'Inkscape'), 'blender': ('.blend', 'Blender'),
          'godot': ('project.godot', 'Godot'), 'mail': ('.eml', 'the mail program')}


def _app(kernel, principal, obj, field):
    key = obj.target.get('key');out = [Step('See what it is and what it needs', 'read', obj.stac)] if obj.stac else []
    native = NATIVE.get(key)
    if not native:return out
    suffix, name = native
    out.append(Step('Find its files', 'read', 'files.find %s | pick records | select name,path,modified' % js(text=suffix, limit=20)))
    found = _read(kernel, principal, 'files.find', {'text': suffix, 'limit': 20}) or {}
    for row in [r for r in found.get('records', ()) if str(r.get('path', '')).lower().endswith(suffix)][:3]:
        seen = _read(kernel, principal, 'programs.%s.inspect' % key, {'path': row['path']})
        out.append(Step('Look at %s' % row.get('name', row['path']), 'read', 'programs.%s.inspect %s | select state,tool.available,sha256' % (key, js(path=row['path']))))
        if seen and seen.get('sha256'):
            out.append(Step('Open %s in %s' % (row.get('name', row['path']), name), 'write',
                            op('programs.%s.open' % key, path=row['path'], expected_sha256=seen['sha256']),
                            'its own full window, on this file as it was just read; refused if the file changed or the program is not installed', 'approve'))
    return out


BY_KIND = {'calculation': _calculation, 'sheet': _sheet, 'finding': _claim, 'question': _claim, 'source': _source,
           'condition': _condition, 'job': _job, 'document': _page, 'app': _app}"""),
])
edit('workbench/field_page.py', [
("""        self.view.check_asked.connect(lambda: check_desk(self.host))""", """        self.view.check_asked.connect(lambda: check_desk(self.host))
        self.view.full_asked.connect(lambda obj: full_window(self.host, obj))"""),
("""def check_desk(host):""", """def full_window(host, obj):
    \"\"\"F on the shelf: this program in its full window. A program with a window of its own is started on a file, through its
    own operation and with the owner's go, so F says what can be done with it (its files, and Open … in … for each); when
    there is exactly one file to open, that step is put up at once. A room of Graphite's own has no other window: it says so.\"\"\"
    from .field_do import NATIVE
    key = (obj.target or {}).get('key') if isinstance(obj.target, dict) else None
    if key not in NATIVE:
        host.statusBar().showMessage('Field · %s is a room of Graphite’s own: Enter opens it' % obj.title, 7000);return None
    steps = do(host, obj)
    opens = [n for n, step in enumerate(steps) if step.kind == 'write' and step.words.startswith('Open ')]
    if len(opens) == 1:return take(host, obj, opens[0])
    if not opens:host.statusBar().showMessage('Field · %s opens a file; none of its files is in Files yet' % obj.title, 7000)
    return None


def check_desk(host):"""),
])
print('edits applied')
