"""The dynamic right-click menu (HATCH DESK D4; the owner's brief of 2026-11-06: "Make the right-click menu a defining capability
of Graphite. Take the Fluxbox pipe-menu idea seriously. When I right-click, build the menu for the thing under the pointer, the
current selection, and what is possible in that workspace. I want to reach an action while my attention is still on the work.")

How it is assembled, in the Fluxbox pipe-menu spirit: a right-click (or the Menu key, or Shift+F10) asks small functions.

  finders     FINDERS: one small function per surface (a document page, Files, the Finder, the cabinet tree, the Machine and
              Settings trees, the Library, Today, the Log view's two streams, Activity, the System menu's process list, the
              Engineering room's Jobs list). Each
              looks at one widget and the point under the pointer and returns a Target (the thing under the pointer and the
              selection: a passage, a page, a file, two files, a drawing or datasheet, a folder, a tree node, a job, a queued
              item, an event, a network connection or packet, an empty place) or None. target_at walks from the widget under
              the pointer up to its parents and stops at a widget with a menu of its own (a text field, a list that keeps its
              own chain menu), so those keep theirs.
  providers   PROVIDERS: small functions that take the Target and return entries (Entry: a label, the section it belongs
              to, what it runs, whether it is available and why not, a submenu). Modifications that apply to the target;
              typed staC commands with the target as input (Inspect in the line, Run); installed capabilities that take it
              (open, compare, extract, the adapters and the Tool Atlas); job actions by state; the network and event words;
              tree actions; the owner's chain menu (chain_menu, with its menu file) is one provider.
  the menu    ContextMenu: the desk's own menu (programs_qt.DeskMenu: one row height, one icon column, one margin with the
              programs list and the System menu), the target named at its top (an icon, its readable name and what it is),
              the sections in one order (SECTIONS) with a hairline between them, submenus cascading beside their row.

Every action goes through Kernel.dispatch with the owner's principal (operator()), with the same scopes and checks as the
rooms use. An action that changes work carries the target's id and the revision seen at the right-click: documents.edit
takes the page's expected_revision (the Kernel refuses REVISION_CHANGED and SELECTION_CHANGED); a file is re-read by
files.get and refused when its modification time or size moved; a job or a queued item is re-read and refused when its state
moved; the cabinet's actions re-resolve their own signature (cabinet_actions_qt.perform). The result shows where it belongs:
the page with the change on it, the console's answer in the working area, the Compare room, the job row's state.

install(host) puts one event filter on the application (Router): a ContextMenu event for a widget of this window (or of one of
its popups, the System menu's list) is answered here when a finder knows the place; the Menu key and Shift+F10 open the same
menu for the keyboard focus (open_at_focus), its first row under focus.
"""
from __future__ import annotations
from .assistant_identity import named
import json
import os
import re
import time
from pathlib import Path
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QContextMenuEvent, QCursor, QFontMetricsF, QGuiApplication, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QAbstractSlider, QAbstractSpinBox, QApplication, QComboBox, QLabel, QLineEdit, QListWidget, QMenu,
                               QPlainTextEdit, QTextEdit, QTreeWidget, QWidget)
from . import programs_qt
from .programs_qt import DeskMenu, MenuRow, Rule

# The sections, in the order the menu shows them: the common way in first, then what the selected thing decides, the edit words
# and the destructive ones last.
SECTIONS = ('open', 'modify', 'state', 'command', 'capability', 'tree', 'edit', 'danger')
SECTION_WORDS = {'open': 'open and show', 'modify': 'change it', 'state': 'its state', 'command': 'as a line', 'capability': 'capabilities',
                 'tree': 'the tree', 'edit': 'edit and copy', 'danger': 'remove'}
CAPTION = 'what you can do right here'          # the menu's small caption, in the script (the quiet-script rule)
HOVER_MS = 240                                  # a submenu opens after the pointer rests on its row this long
REQUEST = 'Right-click · '                      # the request words an edit carries into the page's history
# What a target is called at the menu's top, and its icon (programs_qt's icons and this module's EXTRA ones).
NOUNS = {'passage': ('passage', 'passage'), 'page': ('page', 'documents'), 'file': ('file', 'documents'), 'drawing': ('drawing', 'kicad'),
         'datasheet': ('datasheet', 'references'), 'table': ('table', 'calculate'), 'folder': ('folder', 'files'), 'files': ('files', 'files'),
         'cabinet': ('record', 'memory'), 'tree': ('tree', 'agenda'), 'work': ('work', 'projects'), 'machine': ('this computer', 'brain'),
         'setting': ('setting', 'settings'), 'job': ('job', 'job'), 'queued': ('Agenda work', 'agenda'), 'event': ('event', 'event'),
         'connection': ('network connection', 'network'), 'packet': ('packet', 'packet'), 'empty': ('here', 'explore'), 'library': ('received file', 'office'), 'program': ('capability', 'tools'), 'command': ('command', 'line')}
DRAWINGS = ('.dxf', '.dwg', '.svg', '.kicad_pcb', '.kicad_sch', '.sch', '.brd', '.gbr', '.ger', '.gtl', '.gbl', '.gto', '.gbo', '.gts', '.gbs', '.gko',
            '.gm1', '.drl', '.xln', '.step', '.stp', '.stl', '.obj', '.3mf', '.iges', '.igs')
DATASHEETS = ('.pdf',)
TABLES = ('.csv', '.tsv', '.xlsx', '.xls', '.ods')
# The staC lens that reads a kind of file as rows first (Inspect in the line puts it after the file's address).
LENS = {'.csv': 'rows', '.tsv': 'rows', '.xlsx': 'rows', '.ods': 'rows', '.md': 'headings', '.markdown': 'headings', '.dxf': 'layers',
        '.txt': 'lines', '.json': 'facts'}
# The installed capabilities (explore.VIEWS keys) that take a kind of file as their input, most fitting first: Open in <adapter>.
ADAPTERS = {'.kicad_pcb': ('kicad', 'kibot'), '.kicad_sch': ('kicad',), '.gbr': ('kibot',), '.ger': ('kibot',), '.gtl': ('kibot',), '.gbl': ('kibot',),
            '.drl': ('kibot',), '.pdf': ('references',), '.cir': ('spice',), '.sp': ('spice',), '.spice': ('spice',), '.v': ('hdl', 'yosys'),
            '.sv': ('hdl', 'yosys'), '.csv': ('calculate',), '.tsv': ('calculate',), '.xlsx': ('office', 'calculate'), '.ods': ('office', 'calculate'),
            '.md': ('documents',), '.txt': ('documents',), '.py': ('laboratory',),
            '.eml': ('mail',), '.blend': ('blender',), '.nes': ('cartridge',),
            '.svg': ('inkscape',), '.fcstd': ('freecad',), '.wav': ('media',), '.flac': ('media',),
            '.mp3': ('media',), '.mp4': ('media',), '.m4a': ('media',), '.png': ('print',), '.zip': ('delivery',)}
# Revisions of one file in a name: "board rev B", "notes v2", "draft (2)", "plan_r3".
REVISION = re.compile(r'(?:[ _.-]*\b(?:rev|revision|ver|version|r|v)[ _.-]*(?:[0-9]+[a-z]?|[a-z])\b|[ _.-]*\(?[0-9]+\)?)$', re.I)
LEADING = re.compile(r'^(?:rev|revision|ver|version|v|r)[ _.-]*(?:[0-9]+[a-z]?|[a-z])\b[ _.-]+', re.I)  # "Rev C notes", "v2 plan"
FILE_KINDS = ('file', 'drawing', 'datasheet', 'table')


class Refused(Exception):
    """The target moved since the right-click (or is gone): nothing was done."""


class Target:
    """The thing under the pointer and the selection. kind: one of NOUNS' keys; label: its readable name for the menu's top;
    noun: what it is (with its state when it has one); ident and revision: what an action that changes work carries; data: the
    surface's own record (a file entry, a job row, a Log entry); items: every selected record when there are several; owner:
    the room or view it lives in; surface: where it was found."""
    def __init__(self, kind, label, noun=None, ident=None, revision=None, data=None, items=None, surface='', owner=None, icon=None):
        self.kind = kind;self.label = str(label or '');self.noun = noun or NOUNS.get(kind, (kind,))[0];self.ident = ident;self.revision = revision
        self.data = data if data is not None else {};self.items = items or [];self.surface = surface;self.owner = owner
        self.icon = icon or NOUNS.get(kind, ('', 'window'))[1];self.widget = None;self.where = None;self.extra = {}

    def heading(self):
        return self.label, self.noun

    def as_dict(self):
        return dict(kind=self.kind, label=self.label, noun=self.noun, ident=self.ident, revision=self.revision, surface=self.surface)

    def __repr__(self):return 'Target(%s)' % ', '.join('%s=%r' % kv for kv in self.as_dict().items())


class Entry:
    """One row the providers offer: key (stable, for readers and tests), label (the readable words), section (SECTIONS), run (what
    it does), caption (a key or a status, quiet print at the right), enabled and reason (why not), operation (the Kernel operation
    it dispatches, said in its tooltip), submenu (a function returning entries, read when it opens), qmenu (a function returning a
    QMenu, for the chain builder's own cascade), checked (an active choice: the short yellow mark)."""
    __slots__ = ('key', 'label', 'section', 'run', 'icon', 'caption', 'enabled', 'reason', 'tip', 'submenu', 'qmenu', 'operation', 'checked', 'provider')

    def __init__(self, key, label, section, run=None, icon='', caption='', enabled=True, reason='', tip='', submenu=None, qmenu=None, operation=None,
                 checked=False):
        self.key = key;self.label = label;self.section = section if section in SECTIONS else 'capability';self.run = run;self.icon = icon
        self.caption = caption;self.enabled = bool(enabled);self.reason = reason;self.tip = tip;self.submenu = submenu;self.qmenu = qmenu
        self.operation = operation;self.checked = bool(checked);self.provider = ''

    def tooltip(self):
        lines = [self.reason] if not self.enabled and self.reason else []
        if self.tip:lines.append(self.tip)
        if self.operation:lines.append('Through Kernel.dispatch: ' + self.operation)
        return '\n'.join(lines)

    def as_dict(self):
        return dict(key=self.key, label=self.label, section=self.section, enabled=self.enabled, reason=self.reason, operation=self.operation,
                    submenu=bool(self.submenu or self.qmenu), checked=self.checked, provider=self.provider, caption=self.caption)

    def __repr__(self):return 'Entry(%r, %r, %s%s)' % (self.key, self.label, self.section, '' if self.enabled else ', unavailable')


# -- the Kernel, words and small facts ---------------------------------------------------------------------------------------------

def kernel_of(host):
    bridge = getattr(host, 'ledger_bridge', None);kernel = getattr(bridge, 'kernel', None)
    if kernel is None:
        from .engine import engineering
        kernel = engineering(host.root)
    return kernel


def dispatch(host, operation, arguments):
    """The one door: Kernel.dispatch with the owner's principal, the scopes and checks every room uses."""
    from .engineering_kernel import operator
    try:return kernel_of(host).dispatch(operation, arguments, operator())
    except Exception as exc:return {'ok': False, 'error': {'message': str(exc)}}


def message(response, default='Not done'):
    error = (response or {}).get('error') or {}
    return str(error.get('message') or default)


def say(host, words, ms=9000):
    """The result in the status line (where a result without a room of its own belongs), and kept for readers."""
    host._context_said = words
    bar = getattr(host, 'statusBar', None)
    if callable(bar):
        try:bar().showMessage(words, ms)
        except RuntimeError:pass
    return words


def copy_text(host, text, what='Copied'):
    QGuiApplication.clipboard().setText(str(text));return say(host, '%s: %s' % (what, str(text)[:160]), 5000)


def short(text, most=60):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= most else text[:most - 1].rstrip() + '…'


def stamp(at):
    try:return time.strftime('%H:%M:%S', time.localtime(float(at)))
    except (TypeError, ValueError, OSError):return 'unknown'


def suffix(name):
    name = str(name or '').casefold()
    for s in ('.kicad_pcb', '.kicad_sch'):
        if name.endswith(s):return s
    return os.path.splitext(name)[1]


def file_kind(name):
    """What a file is for the menu's words: a drawing, a datasheet, a table, or a file."""
    s = suffix(name)
    if s in DRAWINGS:return 'drawing'
    if s in DATASHEETS:return 'datasheet'
    if s in TABLES:return 'table'
    return 'file'


def stem_of(name):
    base, ext = os.path.splitext(str(name));base = base.strip()
    previous = None
    while previous != base:previous = base;base = LEADING.sub('', REVISION.sub('', base)).strip(' _.-')
    return base.casefold(), ext.casefold()


def revisions_of_one(a, b):
    """Two names that are revisions of one file: the same name once revision words are taken off ("board rev B" and "board rev
    C", "notes v1" and "notes v2", "draft" and "draft (2)"), the same kind, different files."""
    if str(a) == str(b):return False
    sa, sb = stem_of(Path(str(a)).name), stem_of(Path(str(b)).name)
    return bool(sa[0]) and sa == sb


def staC_for_file(rel):
    """The staC that reads a file in Files: its address, and the lens that gives rows first for its kind."""
    lens = LENS.get(suffix(rel))
    return '@files:' + rel + (' | ' + lens if lens else '')


def needs_quotes(rel):
    return bool(re.search(r'\s|\|', str(rel)))


# -- the writing line: Inspect in the line, Run, Ask Stacy ---------------------------------------------------------------------

def inspect_in_line(host, text, mode='slate'):
    """Put the equivalent command in the writing line, in Assignment (or the given mode), for inspection or editing; nothing runs.
    Typed staC runs on Ctrl+Enter; an operation line (the / lead) runs on Enter, an approve-scope one on a second Enter."""
    bar = getattr(host, 'type_bar', None)
    if bar is None:return None
    bar.set_target(mode, focus=False);bar.box.setText(text);bar.box.setFocus(Qt.OtherFocusReason);bar.box.end(False)
    if hasattr(bar, 'typed'):
        try:bar.typed(text)
        except Exception:pass
    say(host, 'In the line for you to inspect: ' + short(text, 120) + ('  ·  Ctrl+Enter runs it' if not text.startswith('/') else '  ·  Enter runs it'))
    return bar.box.text()


def run_stac(host, program):
    """Run typed staC through its normal path (the staC page of the working area: Console.run_stac, through Kernel.dispatch);
    the answer shows in the working area. A refusal is reported as one (Refused, with the Kernel's reason), never as done: the
    staC page keeps the program it ran (Console.last_program, set only when the Kernel answered), so the menu reads that back."""
    from .shell2 import to_console
    console = getattr(host, 'console', None)
    watched = console is not None and hasattr(console, 'last_program')
    before = console.last_program if watched else None
    if watched:console.last_program = None  # set again by Console.run_stac only when the program ran
    to_console(host, 'stac', program)
    if watched and console.last_program != program:
        console.last_program = before  # the output's right-click carries on from the last program that did run
        raise Refused('Not run: %s · the working area shows the refusal' % (stac_refusal(console, program) or 'the line was refused'))
    say(host, 'Ran in the working area: ' + short(program, 120))
    return program


def stac_refusal(console, program):
    """The Kernel's reason as the staC page wrote it under the program ("refused <reason>"), or '' when it cannot be read."""
    try:text = console.output.toPlainText()
    except (AttributeError, RuntimeError):return ''
    echo = 'line › ' + program;at = text.rfind(echo)      # the console's prompt (console_qt.Console.prompt)
    if at < 0:return ''
    for line in text[at + len(echo):].splitlines():
        line = line.strip()
        if line:return line[len('refused'):].strip() if line.startswith('refused') else ''
    return ''


def ask_graphite(host, words):
    """An assignment in the line with the thing as its context, the cursor after it (the Log view's own way: log_qt.ask_about)."""
    bar = getattr(host, 'type_bar', None)
    if bar is None:
        shell = getattr(host, 'shell2', None)
        return shell.ask(words) if shell is not None else None
    bar.set_target('slate', focus=False);bar.box.setText(words);bar.box.setFocus(Qt.OtherFocusReason);bar.box.end(False)
    return bar.box.text()


def ask_about_sheet(host, obj):
    """Ask Stacy about one sheet of the Field. Its name goes in the line for the owner to finish, and she is told which sheet
    it is, so she can answer from the records in staC even with no model. The Field stays in front; her answer is in Talk."""
    face = getattr(getattr(host, 'shell2', None), 'face', None)
    from . import field_page
    if face is not None:face.thing = {**field_page.thing_of(host, obj), 'explicit': True}
    return ask_graphite(host, 'About “%s”: ' % obj.title)


def operation_line(operation, arguments):
    return '/' + operation + ' ' + json.dumps(arguments, ensure_ascii=False, separators=(', ', ': '))


# -- documents: a passage and a page ------------------------------------------------------------------------------------------------

def document_target(tab, page):
    """The passage under the pointer (the selection), or the page at the caret. The page is saved first, so the target's revision
    is the saved one the menu's edits carry (as the strip's requests do)."""
    if tab.document_id is None:return None
    if tab.dirty:tab.flush()
    from .document_qt import STYLE_PROPERTY, marks_of
    selection = tab.slate_selection();title = tab.title_box.text().strip() or 'Untitled document'
    cursor = page.textCursor();block = cursor.block();style = block.blockFormat().property(STYLE_PROPERTY) or 'Normal'
    if selection and selection['text'].strip():
        marks = set(marks_of(cursor.charFormat()))
        if cursor.hasSelection():  # every selected character: a mark is on only when it is on all of them
            doc = page.document();marks = {'bold', 'italic', 'underline'}
            from PySide6.QtGui import QTextCursor
            probe = QTextCursor(doc)
            for at in range(cursor.selectionStart() + 1, cursor.selectionEnd() + 1):
                probe.setPosition(at);marks &= set(marks_of(probe.charFormat()))
                if not marks:break
        return Target('passage', '“%s”' % short(selection['text'], 48), 'passage · %s · revision %s' % (short(title, 24), tab.revision), ident=tab.document_id,
                      revision=tab.revision, data=dict(selection=selection, marks=marks, style=style, title=title), surface='document', owner=tab)
    caret = {'block': block.blockNumber(), 'start': 0, 'end': 0}
    return Target('page', short(title, 48), 'page · revision %s' % tab.revision, ident=tab.document_id, revision=tab.revision,
                  data=dict(selection=caret, marks=set(), style=style, title=title), surface='document', owner=tab)


def document_now(host, target):
    """The page the target was on, or Refused when it is not open any more."""
    tab = target.owner
    try:alive = tab is not None and tab.document_id == target.ident
    except RuntimeError:alive = False
    if not alive:raise Refused('That page is no longer open, so nothing changed.')
    return tab


def edit_document(host, target, change, words):
    """documents.edit through the Kernel with the page's id, the revision seen at the right-click and the selection with its
    quoted words; the change lands on the page through its own undo stack (Ctrl Z takes it back), the page shows it, and its foot
    says the revision. A moved revision or changed words are refused by the Kernel; the page then shows the saved revision."""
    tab = document_now(host, target)
    if tab.dirty:tab.flush()  # the owner's unsaved words first: if they moved the revision, the Kernel refuses below
    selection = dict(target.data['selection'])
    arguments = {'id': target.ident, 'expected_revision': target.revision, 'selection': selection, 'change': change, 'origin': 'HUMAN',
                 'request': (REQUEST + words)[:400]}
    r = dispatch(host, 'documents.edit', arguments)
    if not r.get('ok'):
        text = message(r)
        if text.startswith(('REVISION_CHANGED', 'SELECTION_CHANGED')):
            value = dispatch(host, 'documents.get', {'id': target.ident})
            if value.get('ok'):tab.load(value['result']['document']);tab.reload_list()
            seen = target.revision;now = tab.revision
            raise Refused('The page moved on since you right-clicked it (revision %s, now %s), so nothing changed. Select the words again.' % (seen, now)
                          if text.startswith('REVISION_CHANGED') else 'Those words changed on the saved page, so nothing changed. Select them again.')
        raise Refused('Not done: ' + text)
    result = r['result'];doc = result['document']
    from .document_qt import from_qt
    tab.apply_locally(selection, change)
    try:same = from_qt(tab.page.document(), tab.block_ids) == doc['blocks']
    except ValueError:same = False
    if not same:tab.load(doc)  # the page shows exactly the saved revision, whatever the local application did
    else:
        tab.loading = True
        try:tab.revision = doc['revision'];tab.block_ids = [b['id'] for b in doc['blocks']];tab.dirty = False;tab.save_timer.stop()
        finally:tab.loading = False
        tab.reload_list()
    tab.describe(doc, prefix='Right-click');tab.refresh_conditions(result.get('conditions_stale'))
    say(host, 'Done on the page: %s · revision %d · Ctrl Z takes it back.' % (result['applied']['words'], doc['revision']))
    return result


def move_to_notes(host, target):
    """Move to notes: the passage kept, in its own words, as an idea in the cabinet's notes (ideas.capture, the cabinet's Keep idea
    path), then taken off the page through documents.edit (Ctrl Z puts it back on the page). The revision is checked before
    anything is kept, so a moved page keeps both."""
    tab = document_now(host, target)
    now = dispatch(host, 'documents.get', {'id': target.ident})
    if not now.get('ok'):raise Refused('Not done: ' + message(now))
    if now['result']['document']['revision'] != target.revision or tab.dirty:
        raise Refused('The page moved on since you right-clicked it (revision %s, now %s), so nothing was moved. Select the words again.'
                      % (target.revision, now['result']['document']['revision']))
    text = target.data['selection']['text']
    kept = dispatch(host, 'ideas.capture', {'text': text, 'origin': 'HUMAN'})
    if not kept.get('ok'):raise Refused('Not kept in notes: ' + message(kept))
    ident = kept['result'].get('id')
    try:edit_document(host, target, {'replace': ''}, 'moved “%s” to notes' % short(text, 40))
    except Refused as exc:
        raise Refused('Kept in notes as idea %s, but the words stay on the page: %s' % (ident, exc))
    page = getattr(host, 'cabinet_page', None)
    if page is not None:
        try:page.refresh(force=True)
        except Exception:pass
    return say(host, 'Moved to notes: “%s” is kept as an idea in the cabinet (Ideas) and off the page · Ctrl Z puts it back on the page.' % short(text, 50))


def document_entries(host, t):
    """Bold and the other page edits on a passage, Move to notes, the paragraph's style, the equivalent command to inspect in the
    line, Ask Stacy, Search; on the page alone, its paragraph's style; the text edits the page always had."""
    if t.kind not in ('passage', 'page'):return []
    tab = t.owner;out = [];selection = t.data['selection'];marks = t.data.get('marks') or set()
    from .document_qt import STYLE_SCALE
    if t.kind == 'passage':
        for key, word, keys, icon in (('bold', 'Bold', 'Ctrl B', 'bold'), ('italic', 'Italic', 'Ctrl I', ''), ('underline', 'Underline', 'Ctrl U', '')):
            on = key in marks;label = ('Not ' + word.lower()) if on else word
            out.append(Entry('mark:' + key, label, 'modify', lambda key=key, on=on, label=label:edit_document(host, t, {key: not on}, label.lower()),
                             icon=icon, caption=keys, operation='documents.edit', tip='%s the selected words on revision %s of this page' % (label, t.revision)))
        out.append(Entry('mark:clear', 'Plain', 'modify', lambda:edit_document(host, t, {'clear': True}, 'plain'), caption='', operation='documents.edit',
                         enabled=bool(marks), reason='The selected words carry no bold, italic or underline.'))
    styles = (('Heading1', 'Heading', 'Ctrl 1'), ('Heading2', 'Subheading', 'Ctrl 2'), ('Heading3', 'Minor heading', 'Ctrl 3'), ('Normal', 'Body', 'Ctrl 0'), ('Code', 'Code', 'Ctrl `'))
    current = t.data.get('style') or 'Normal'
    def style_entries():
        return [Entry('style:' + style, word, 'modify', lambda style=style, word=word:edit_document(host, t, {'style': style}, 'made the paragraph ' + word.lower()),
                      caption=keys, checked=style == current, operation='documents.edit') for style, word, keys in styles]
    out.append(Entry('style', 'Paragraph style', 'modify', submenu=style_entries, tip='The style of paragraph %d' % (selection['block'] + 1)))
    if t.kind == 'passage':
        out.append(Entry('notes', 'Move to notes', 'modify', lambda:move_to_notes(host, t), icon='notes', operation='ideas.capture, documents.edit',
                         tip='Keep the words as an idea in the cabinet (your notes) and take them off the page'))
        line = operation_line('documents.edit', {'id': t.ident, 'expected_revision': t.revision, 'selection': selection,
                                                  'change': {'bold': 'bold' not in marks}, 'origin': 'HUMAN'})
        out.append(Entry('inspect', 'Inspect in the line', 'command', lambda:inspect_in_line(host, line), icon='line', operation='documents.edit',
                         tip='The equivalent command for Bold with this passage as its target, in the writing line to read or change; Enter runs it'))
        about = 'About this passage (“%s”, paragraph %d of “%s”, revision %s): ' % (short(selection['text'], 80), selection['block'] + 1, short(t.data.get('title'), 40), t.revision)
        out.append(Entry('ask', named('Ask Stacy about this'), 'capability', lambda:ask_graphite(host, about), icon='inquiries',
                         tip='An assignment in the line with this passage as its context'))
        out.append(Entry('search', 'Search for these words', 'capability', lambda:search_words(host, selection['text']), icon='investigations',
                         tip='The writing line in Search with these words: files, their words, the cabinet, settings, the Timeline'))
    page = tab.page
    def can(name):
        try:return bool(getattr(page.document(), name)())
        except RuntimeError:return False
    has = page.textCursor().hasSelection()
    out += [Entry('edit:undo', 'Undo', 'edit', page.undo, caption='Ctrl Z', enabled=can('isUndoAvailable'), reason='Nothing to undo on this page.'),
            Entry('edit:redo', 'Redo', 'edit', page.redo, caption='Ctrl Y', enabled=can('isRedoAvailable'), reason='Nothing to redo on this page.'),
            Entry('edit:cut', 'Cut', 'edit', page.cut, caption='Ctrl X', enabled=has, reason='Select words first.'),
            Entry('edit:copy', 'Copy', 'edit', page.copy, caption='Ctrl C', enabled=has, reason='Select words first.', icon='copy'),
            Entry('edit:paste', 'Paste', 'edit', page.paste, caption='Ctrl V', enabled=page.canPaste(), reason='Nothing to paste.'),
            Entry('edit:delete', 'Delete', 'edit', lambda:page.textCursor().removeSelectedText(), enabled=has, reason='Select words first.'),
            Entry('edit:all', 'Select all', 'edit', page.selectAll, caption='Ctrl A')]
    out += [Entry('doc:new', 'New document', 'tree', tab.new_document, icon='new', operation='documents.create'),
            Entry('doc:export', 'Export…', 'tree', tab.export_document, icon='leave', operation='documents.render',
                  tip='Write this document to a Markdown, HTML or text file you choose (Egress first)')]
    return out


def search_words(host, words):
    bar = getattr(host, 'type_bar', None)
    if bar is None:return None
    bar.set_target('find', focus=False);bar.box.setText(short(words, 200));bar.box.setFocus(Qt.OtherFocusReason)
    if hasattr(bar.box, 'update_results'):
        try:bar.box.update_results(bar.box.text())
        except Exception:pass
    return bar.box.text()


# -- files (Files, the Finder, the Library) -----------------------------------------------------------------------------------------

def file_revision(entry):
    """A file's revision as the menu carries it: its modification time and size as the listing read them."""
    modified = entry.get('modified');size = entry.get('size')
    return (round(float(modified), 6) if isinstance(modified, (int, float)) else None, size)


def file_now(host, rel):
    r = dispatch(host, 'files.get', {'path': rel})
    if not r.get('ok'):raise Refused('%s cannot be read now, so nothing was done: %s' % (rel, message(r)))
    return r['result']


def still_file(host, entry):
    """Refused when the file moved since the right-click (its modification time or size); the live entry otherwise."""
    live = file_now(host, entry['path'])
    if file_revision(live) != file_revision(entry):
        raise Refused('%s changed since you right-clicked it (changed %s, now %s), so nothing was done. Right-click it again to act on it as it is now.'
                      % (entry['name'], stamp(entry.get('modified')), stamp(live.get('modified'))))
    return live


def files_tab(host, target):
    tab = target.owner
    try:tab.objectName()
    except (RuntimeError, AttributeError):raise Refused('The Files room is closed, so nothing was done.')
    return tab


def act_on_files(host, target, operation, arguments, done):
    """A files.* change through the Files room's own act (Kernel.dispatch, then the room reloads), after the revision check."""
    tab = files_tab(host, target)
    for e in target.items or [target.data]:still_file(host, e)
    r = tab.act(operation, arguments, done)
    if r.get('ok'):say(host, done)
    return r


def rename_file(host, target):
    from PySide6.QtWidgets import QInputDialog
    e = target.data;tab = files_tab(host, target)
    name, ok = QInputDialog.getText(tab, 'Rename', 'New name for ' + e['name'], text=e['name'])
    if not ok or not name.strip() or name.strip() == e['name']:return None
    return act_on_files(host, target, 'files.rename', {'path': e['path'], 'name': name.strip()}, 'Renamed %s to %s' % (e['name'], name.strip()))


def trash_files(host, target):
    tab = files_tab(host, target);entries = target.items or [target.data]
    for e in entries:still_file(host, e)
    for e in entries:tab.act('files.trash', {'path': e['path']}, 'Moved to Trash. Restore it from Trash.')
    return say(host, 'Moved %s to Trash · Trash puts %s back.' % (entries[0]['name'] if len(entries) == 1 else '%d items' % len(entries), 'it' if len(entries) == 1 else 'them'))


def place_files(host, target, operation):
    from PySide6.QtWidgets import QFileDialog
    tab = files_tab(host, target);entries = target.items or [target.data]
    folder = QFileDialog.getExistingDirectory(tab, 'Copy to' if operation == 'files.copy' else 'Move to', str(tab.root))
    if not folder:return None
    try:to = Path(folder).resolve().relative_to(Path(tab.root).resolve()).as_posix()
    except ValueError:raise Refused('Choose a folder inside Files.')
    for e in entries:still_file(host, e)
    for e in entries:tab.act(operation, {'path': e['path'], 'to': '' if to == '.' else to}, 'Copied' if operation == 'files.copy' else 'Moved')
    return say(host, ('Copied' if operation == 'files.copy' else 'Moved') + ' to Files › ' + (to if to != '.' else ''))


def export_file(host, target):
    """Export with its file or folder (files.export: a copy into Egress, the originals stay as they are)."""
    tab = files_tab(host, target);still_file(host, target.data)
    return tab.export(target.data)


def revert_file(host, target):
    tab = files_tab(host, target);still_file(host, target.data)
    return tab.versions(target.data)


def compare_files(host, a, b, words='Compare'):
    """files.compare on the two actual files (a read): the Compare room opens with them side by side, ready to read."""
    from .compare_qt import show
    room = show(host, path=b, other=a)  # files.compare reads `other` as the older (before) and `path` as the newer (after)
    say(host, '%s: %s and %s, in the Compare room' % (words, Path(a).name, Path(b).name))
    return room


def compare_version(host, rel, version):
    from .compare_qt import show
    room = show(host, path=rel, version=version)
    say(host, 'Compared %s with the version kept at %s, in the Compare room' % (Path(rel).name, version))
    return room


def versions_of(host, rel):
    r = dispatch(host, 'files.versions', {'path': rel})
    return (r.get('result') or {}).get('versions', []) if r.get('ok') else []


def lenses_of(host, rel):
    """Extract: the readings of a file that give rows (staC lenses, read-only through language.run), each with its count."""
    from .chain_menu import LENS_ORDER, records, rows_words, run
    out = [];program = '@files:' + rel
    _, refused = run(host, program)  # the file itself first: a refusal here (the address, the source binding) is said, not hidden
    if refused is not None:
        return [Entry('extract:refused', 'Not readable now: ' + short(refused, 48), 'capability', enabled=False, reason='the line refused %s: %s' % (program, refused),
                      operation='language.run')]
    sheets, _ = run(host, program + ' | pick data.sheets')
    if sheets and isinstance(sheets[0], dict):
        for name in list(sheets[0])[:8]:
            p = program + ' | sheet ' + name;rows, error = run(host, p)
            if error is None and rows:out.append(Entry('extract:sheet:' + name, 'sheet ' + name, 'capability', lambda p=p:run_stac(host, p), caption=rows_words(rows), operation='language.run'))
    for lens in LENS_ORDER:
        p = program + ' | ' + lens;rows, error = run(host, p)
        if error is None and records(rows):out.append(Entry('extract:' + lens, lens, 'capability', lambda p=p:run_stac(host, p), caption=rows_words(rows), operation='language.run',
                                                          tip='Run %s in the working area' % p))
    if not out:out.append(Entry('extract:none', 'Nothing to read as rows here', 'capability', enabled=False, reason='No reading gives rows for this file.'))
    return out


def adapters_for(name):
    """The installed adapters (explore.VIEWS rows) that take this kind of file as input, by its suffix (ADAPTERS): Open in
    <adapter> (navigation only; the tool runs from there with its own checks)."""
    from . import explore
    rows = {row[0]: row for row in explore.VIEWS}
    keys = ('godot',) if Path(name).name == 'project.godot' else ADAPTERS.get(suffix(name), ())
    return [rows[key] for key in keys if key in rows]


def adapter_entries(host, name, relative=None):
    from .programs_qt import PLAIN
    out = []
    for row in adapters_for(name):
        def open_it(key=row[0], route=row[4]):
            from .explore_qt import open_instrument
            tab = open_instrument(host, {'id': 'instrument:' + key})
            if route.startswith('program:') and tab is not None and relative and not tab.busy:
                tab.source.setText(relative)
            return tab
        out.append(Entry('adapter:' + row[0], 'Open in ' + PLAIN.get(row[0], row[1]), 'capability', open_it, icon=row[0], operation='ledger.explore',
                         tip=row[2] + ' Opening runs no tool.'))
    bridge = getattr(host, 'ledger_bridge', None)
    out.append(Entry('atlas', 'Find tools in the Tool Atlas', 'capability', lambda:bridge.show_atlas(), icon='tools', enabled=bridge is not None and hasattr(bridge, 'show_atlas'),
                     reason='The Tool Atlas is not available.', tip='The registered operations and tool passports, to choose a check for this file'))
    def explore_it():
        from .explore_qt import show
        return show(host)
    out.append(Entry('explore', 'Explore capabilities…', 'capability', explore_it, icon='explore', operation='ledger.explore',
                     tip='The Explore workspace: every workspace, method and registered operation (the strip\'s old Explore word)'))
    return out


def stage_for_delivery(host, entries):
    from .program_rooms_qt import show
    room = show(host, 'delivery')
    room.stage({entry['path']: None for entry in entries})


def file_entries(host, t):
    """A file, a drawing, a datasheet or a table in Files (and, read-only, in the Finder): open it; change it through files.*
    (rename, copy, move, versions, export, Trash); its staC (Inspect in the line, Run, the chain builder); the capabilities that
    take it (compare, extract, the adapters for its kind, the Tool Atlas, Explain, Ask Stacy, Investigate, the Agenda)."""
    if t.kind not in FILE_KINDS + ('folder',) or t.surface != 'files':return []
    tab = t.owner;e = t.data;rel = e['path'];out = [];folder = t.kind == 'folder';smart = e.get('kind') == 'smart'
    root = Path(getattr(tab, 'root', '.'))
    pill = e['name'].lower().endswith('.pill')
    out.append(Entry('open', 'Open pill…' if pill else 'Open', 'open', lambda:tab.activate(e), icon='window'))
    if not folder and not smart:
        out.append(Entry('open:outside', "Open with this computer's app", 'open', lambda:tab.open_outside(e)))
        out.append(Entry('show:folder', 'Show in its folder', 'open', lambda:show_in_folder(tab, rel), icon='files',
                         enabled=tab.question is not None, reason='It is shown in its folder already.'))
    out.append(Entry('rename', 'Rename…', 'modify', lambda:rename_file(host, t), icon='rename', operation='files.rename'))  # a smart folder too (files.rename takes it)
    out.append(Entry('copy:to', 'Copy to…', 'modify', lambda:place_files(host, t, 'files.copy'), operation='files.copy'))
    out.append(Entry('move:to', 'Move to…', 'modify', lambda:place_files(host, t, 'files.move'), operation='files.move'))
    if not folder and not smart:
        out.append(Entry('versions', 'Versions…', 'modify', lambda:revert_file(host, t), operation='files.versions, files.revert',
                         tip='Go back to a kept version; the version before is kept too'))
    out.append(Entry('export', 'Export…', 'modify', lambda:export_file(host, t), icon='leave', operation='files.export',
                     tip='A copy into Egress: as it is (a ZIP with SHA256SUMS) or for manufacturing; your files stay as they are'))
    if not folder and not smart:
        program = staC_for_file(rel)
        quoted = needs_quotes(rel)
        out.append(Entry('inspect', 'Inspect in the line', 'command', lambda:inspect_in_line(host, program), icon='line', operation='language.run',
                         enabled=not quoted, reason='An address is one word: this name has a space or a bar.', tip=program))
        out.append(Entry('run', 'Run', 'command', lambda:run_stac(host, program), icon='run', operation='language.run', enabled=not quoted,
                         reason='An address is one word: this name has a space or a bar.', tip='Run %s; the answer shows in the working area' % program))
        out.append(Entry('chain', 'Chain from here', 'command', qmenu=lambda:chain_qmenu(host, '@files:' + rel), icon='chain', enabled=not quoted,
                         reason='An address is one word: this name has a space or a bar.', tip='The chain builder: each link a menu, each showing what it gives'))
        out.append(Entry('compare:with', 'Compare with…', 'capability', lambda:tab.compare_with(e), icon='compare', operation='files.compare'))
        found = versions_of(host, rel)
        def kept():
            return [Entry('compare:version:' + v['version'], v['version'], 'capability', lambda v=v:compare_version(host, rel, v['version']), operation='files.compare')
                    for v in found[:12]]
        out.append(Entry('compare:version', 'Compare with a kept version', 'capability', submenu=kept, enabled=bool(found),
                         reason='No earlier versions are kept for %s yet.' % e['name']))
        out.append(Entry('extract', 'Extract', 'capability', submenu=lambda:lenses_of(host, rel), icon='extract', enabled=not quoted,
                         reason='An address is one word: this name has a space or a bar.', tip='Read it as rows, headings, layers, texts, lines or facts'))
        out += adapter_entries(host, e['name'], rel)
        out.append(Entry('delivery:stage', 'Stage in Delivery', 'capability',
                         lambda:stage_for_delivery(host, [e]), icon='delivery',
                         tip='Add this file to the review list. Inspect it there before building a ZIP.'))
        out.append(Entry('explain', 'Explain this file', 'capability', lambda:tab.explain(e), icon='inquiries', operation='files.get'))
        out.append(Entry('ask', named('Ask Stacy about this…'), 'capability', lambda:tab.ask(e)))
        out.append(Entry('investigate', 'Investigate…', 'capability', lambda:tab.investigate(e), icon='investigations', operation='investigation.create'))
        out.append(Entry('agenda', 'Add to the Agenda…', 'capability', lambda:tab.add_to_agenda(e), icon='agenda', operation='agenda.add'))
    c = tab.copy_for(rel) if hasattr(tab, 'copy_for') else None
    if c and not folder:
        if c['for_slate'] and c.get('kind', 'file') == 'file':out.append(Entry('copy:slate', named('Ask Stacy to work on this…'), 'capability', lambda:tab.slate_on_copy(c), operation='agenda.add'))
        out.append(Entry('copy:review', 'Review changes to the original…', 'capability', lambda:tab.review_copy(c), icon='compare', operation='copies.review'))
        out.append(Entry('copy:original', 'Show the original', 'open', lambda:tab.show_original(c)))
        out.append(Entry('copy:discard', 'Discard this draft…', 'danger', lambda:tab.discard_copy(c), operation='copies.discard'))
    if folder and tab.copies.get(rel):
        c = tab.copies[rel]
        out.append(Entry('copy:look', 'Look inside, confined…', 'capability', lambda:tab.confined_look(c), operation='confine.inspect'))
        out.append(Entry('copy:run', 'Run a command here, confined…', 'capability', lambda:tab.confined_run(c), operation='confine.run'))
        if str(c.get('source', '')).startswith('pill:'):
            from .pills_qt import return_copy
            out.append(Entry('copy:pill', 'Return as a pill…', 'capability', lambda:return_copy(host, c, tab)))
            out.append(Entry('copy:review', 'Review the changes…', 'capability', lambda:tab.review_copy(c), icon='compare', operation='copies.review'))
        else:
            out.append(Entry('copy:review', 'Review changes to the original…', 'capability', lambda:tab.review_copy(c), icon='compare', operation='copies.review'))
            out.append(Entry('copy:original', 'Show the original', 'open', lambda:tab.show_original(c)))
        out.append(Entry('copy:discard', 'Discard this draft…', 'danger', lambda:tab.discard_copy(c), operation='copies.discard'))
    out.append(Entry('copy:path', 'Copy path', 'edit', lambda:copy_text(host, str(root / rel), 'Copied the path'), icon='copy'))
    out.append(Entry('copy:address', 'Copy the address', 'edit', lambda:copy_text(host, e.get('address') or '@files:' + rel, 'Copied the address')))
    out.append(Entry('trash', 'Move to Trash', 'danger', lambda:trash_files(host, t), icon='trash', operation='files.trash', tip='Trash keeps it; Restore puts it back'))
    return out


def show_in_folder(tab, rel):
    """From a search or a smart folder: the file's own folder in Files, the file selected."""
    parent = Path(rel).parent.as_posix()
    tab.question = None;tab.question_name = None;tab.go('' if parent == '.' else parent);tab.select_path(rel)
    return tab


def files_entries(host, t):
    """Two or more files selected in Files: Compare revisions when two are revisions of one file (the actual files passed to
    files.compare, the result in the Compare room), else Compare these two; copy, move and Trash for all of them."""
    if t.kind != 'files' or t.surface != 'files':return []
    out = [];items = t.items
    files = [e for e in items if e.get('kind') not in ('folder', 'smart')]
    if len(files) == len(items) and files:
        out.append(Entry('delivery:stage', 'Stage selected files in Delivery', 'capability',
                         lambda:stage_for_delivery(host, files), icon='delivery',
                         tip='Add these selected files to the review list. Inspect them there before building a ZIP.'))
    if len(items) == 2 and len(files) == 2:
        a, b = sorted(files, key=lambda e:(e.get('modified') or 0, e['name']))  # the older first: what changed reads left to right
        same = revisions_of_one(a['name'], b['name'])
        out.append(Entry('compare:revisions' if same else 'compare:two', 'Compare revisions' if same else 'Compare these two', 'open',
                         lambda:compare_files(host, a['path'], b['path'], 'Compared revisions' if same else 'Compared'), icon='compare', operation='files.compare',
                         tip='%s (older) and %s, side by side in the Compare room' % (a['name'], b['name'])))
    out.append(Entry('copy:to', 'Copy to…', 'modify', lambda:place_files(host, t, 'files.copy'), operation='files.copy'))
    out.append(Entry('move:to', 'Move to…', 'modify', lambda:place_files(host, t, 'files.move'), operation='files.move'))
    out.append(Entry('copy:paths', 'Copy paths', 'edit', lambda:copy_text(host, '\n'.join(str(Path(t.owner.root) / e['path']) for e in items), 'Copied the paths'), icon='copy'))
    out.append(Entry('trash', 'Move to Trash', 'danger', lambda:trash_files(host, t), icon='trash', operation='files.trash'))
    return out


def files_place_entries(host, t):
    """An empty place in Files: the root menu (as the old chains › held it), new folder, import where material enters, work on a
    copy, a smart folder, the view."""
    if t.kind != 'empty' or t.surface != 'files':return []
    tab = t.owner
    return [root_entry(host),
            Entry('new:folder', 'New folder…', 'tree', tab.new_folder, icon='new', operation='files.mkdir'),
            Entry('new:smart', 'New smart folder…', 'tree', tab.new_smart, operation='files.smart'),
            Entry('import', 'Import…', 'tree', tab.import_files, icon='office', tip='Copies of files you choose, into this folder (the originals stay where they are)'),
            Entry('work:copy', 'Work on a copy of a file…', 'tree', tab.work_on_copy, operation='copies.start'),
            Entry('view', 'View as', 'tree', icon='view', submenu=lambda:[Entry('view:icons', 'Thumbnails', 'tree', lambda:tab.mode != 'icons' and tab.toggle_view(), checked=tab.mode == 'icons'),
                                                                           Entry('view:list', 'List', 'tree', lambda:tab.mode != 'list' and tab.toggle_view(), checked=tab.mode == 'list')]),
            Entry('view:all', 'Hide machine files' if tab.show_all else 'Show all files', 'tree', tab.toggle_all),
            Entry('refresh', 'Refresh', 'tree', tab.reload, icon='restart', operation='files.list')]


def finder_entries(host, t):
    """The Finder's words for an entry, folded as they were (open, look, show, copy, ask; nothing here creates, renames, moves or
    deletes: Change it in Files) with staC and the capabilities for a file inside Files."""
    if t.surface != 'finder' or t.kind == 'empty':return []
    page = t.owner;entry = t.data;path = page.entry_path(entry);out = []
    from .finder_qt import inside
    files = page.files_root();folder = entry['kind'] == 'folder'
    out.append(Entry('open', 'Open', 'open', lambda:page.open_entry(entry), icon='window'))
    if not folder:out.append(Entry('open:viewer', 'Open in viewer', 'open', lambda:host.open_in_viewer(Path(path))))
    in_files = files is not None and inside(path, files)
    if in_files and Path(path).resolve() != Path(files).resolve():
        out.append(Entry('show:files', 'Show in Files', 'open', lambda:page.show_in_files(path), icon='files'))
    out.append(Entry('copy:path', 'Copy path', 'edit', lambda:page.copy_path(path), icon='copy'))
    out.append(Entry('ask', named('Ask Stacy about this ') + ('folder' if folder else 'file'), 'capability', lambda:page.ask_slate(path), icon='inquiries'))
    if in_files:
        rel = Path(path).resolve().relative_to(Path(files).resolve()).as_posix()
        out.append(Entry('change:files', 'Change it in Files', 'modify', lambda:page.show_in_files(path), tip='Files keeps its own changes: rename, versions, export, Trash'))
        if not folder and rel and not needs_quotes(rel):
            program = staC_for_file(rel)
            out.append(Entry('inspect', 'Inspect in the line', 'command', lambda:inspect_in_line(host, program), icon='line', tip=program, operation='language.run'))
            out.append(Entry('run', 'Run', 'command', lambda:run_stac(host, program), icon='run', operation='language.run'))
            out.append(Entry('extract', 'Extract', 'capability', submenu=lambda:lenses_of(host, rel), icon='extract'))
    else:
        out.append(Entry('change:none', 'Nothing changes here · Files keeps its own changes', 'modify', enabled=False,
                         reason='The Finder only reads; Files changes its own files.'))
    if not folder:out += adapter_entries(host, entry['name'], rel if in_files else None)[:-2]  # the Atlas and Explore are on the place
    return out


def finder_place_entries(host, t):
    if t.surface != 'finder' or t.kind != 'empty':return []
    page = t.owner;out = [root_entry(host)]
    if page.place not in (None, 'today') and hasattr(page, 'set_view'):
        from .finder_qt import VIEW_WORDS, VIEWS
        out.append(Entry('view', 'View as', 'tree', icon='view', submenu=lambda:[Entry('view:' + key, VIEW_WORDS[key], 'tree', lambda key=key:page.set_view(key), checked=page.view == key)
                                                                               for key in VIEWS]))
        out.append(Entry('hidden', 'Hide hidden files' if page.hidden else 'Show hidden files', 'tree', lambda:page.set_hidden(not page.hidden)))
        out.append(Entry('preview', 'Hide the preview' if page.preview_visible else 'Show the preview', 'tree', page.toggle_preview, caption='Space'))
        out.append(Entry('copy:path', 'Copy path', 'edit', lambda:page.copy_path(page.place), icon='copy'))
        out.append(Entry('refresh', 'Refresh', 'tree', page.reload, icon='restart', operation='ledger.browse'))
    return out


def library_entries(host, t):
    """A received file in the Library: Open and Keep a copy in Files (folded as they were), Ask Stacy, Copy its name."""
    if t.surface != 'library' or t.kind != 'library':return []
    tab = t.owner;e = t.data
    return [Entry('open', 'Open', 'open', lambda:host.shell2.open_library_file(e), icon='window'),
            Entry('keep', 'Keep a copy in Files', 'modify', lambda:tab.keep([e]), icon='files', operation='files.keep'),
            Entry('ask', named('Ask Stacy about this file'), 'capability', lambda:host.shell2.ask('Tell me about this file: ' + e['name']), icon='inquiries'),
            Entry('copy:name', 'Copy the name', 'edit', lambda:copy_text(host, e['name']), icon='copy')]


def library_place_entries(host, t):
    if t.surface != 'library' or t.kind != 'empty':return []
    bridge = host.ledger_bridge
    return [root_entry(host),
            Entry('import', 'Receive files…', 'tree', lambda:bridge.navigation()['office']().pick_files(), icon='office',
                  tip='Where material enters: the Office receives copies (Ingress)'),
            Entry('refresh', 'Refresh', 'tree', lambda:(t.owner.reload(), t.owner.fill()), icon='restart')]


# -- the cabinet, the Machine and Settings trees ------------------------------------------------------------------------------------

def cabinet_entries(host, t):
    """A cabinet record: the cabinet's own checked actions (ledger.cabinet.actions: read its details, prepare writing, the provider's
    checks, the workspaces for its kind, Explore), each re-resolving the record before it runs (cabinet_actions_qt.perform refuses
    a changed record or action list), with Open and the record's staC address."""
    if t.kind != 'cabinet':return []
    from .cabinet_actions_qt import explanation, model, perform
    ident = t.ident;out = [Entry('open', 'Open', 'open', lambda:host.cabinet_page.open(ident), icon='window', operation='ledger.cabinet.get')]
    try:value = model(host, ident)
    except (ValueError, OSError) as exc:
        out.append(Entry('actions:none', 'Actions unavailable', 'capability', enabled=False, reason=str(exc)));return out
    t.data['actions'] = value
    if value['context'] is None:
        out.append(Entry('actions:none', short(value.get('notice') or 'Selection unavailable', 70), 'capability', enabled=False, reason=value.get('notice', '')))
        return out
    section = {'READ': 'capability', 'PREPARE': 'modify', 'WORKSPACE': 'capability', 'EXPLORE': 'capability'}
    def run(key, signature=value['signature']):
        try:return perform(host, ident, key, signature)
        except (ValueError, OSError, ImportError) as exc:raise Refused(str(exc))
    for spec in value['actions']:
        label = spec['label'] + ('…' if spec['kind'] == 'PREPARE' else '')
        where = 'open' if spec['id'] == 'record' else section.get(spec['kind'], 'capability')
        icon = {'record': 'window', 'explore': 'explore'}.get(spec['id'], 'documents' if spec['kind'] == 'PREPARE' else '')
        if spec['kind'] == 'WORKSPACE':icon = spec.get('instrument', '').split(':')[-1]
        out.append(Entry('cabinet:' + spec['id'], label, where, lambda key=spec['id']:run(key), icon=icon, enabled=spec['enabled'],
                         reason=spec.get('unavailable_reason') or '', tip=explanation(spec), operation=spec.get('operation')))
    canonical = str((value['context'] or {}).get('canonical_id') or '')
    from . import addresses
    kind = canonical.split(':', 1)[0]
    if kind in addresses.KINDS and kind not in addresses.SELECTOR_KINDS:
        program = '@' + canonical
        out.append(Entry('inspect', 'Inspect in the line', 'command', lambda:inspect_in_line(host, program), icon='line', tip=program, operation='ledger.address.read'))
        out.append(Entry('run', 'Run', 'command', lambda:run_stac(host, program), icon='run', operation='ledger.address.read'))
    if t.data.get('node', {}).get('role') == 'project':
        out.append(Entry('export', 'Export (Egress)…', 'tree', lambda:host.a_export.trigger(), icon='leave', enabled=hasattr(host, 'a_export'),
                         tip='Export with its project: Files ▸ Egress, the copies that leave'))
    out.append(Entry('copy:id', 'Copy the identity', 'edit', lambda:copy_text(host, canonical or ident, 'Copied the identity'), icon='copy'))
    return out


def view_as(host):
    page = host.cabinet_page
    return [Entry('view:logical', 'Logical cabinet', 'tree', lambda:page.set_legacy(False), checked=not page.using_legacy),
            Entry('view:existing', 'Existing views', 'tree', lambda:page.set_legacy(True), checked=page.using_legacy)]


def creation_entries(host, section='tree'):
    """New Idea and New Project (Work's own actions, the brief's place for creation on the Work tree)."""
    out = []
    for name, key, icon in (('a_new_idea', 'new:idea', 'projects'), ('a_new_project', 'new:project', 'new')):
        action = getattr(host, name, None)
        word = 'New Idea…' if key == 'new:idea' else 'New Project…'
        out.append(Entry(key, word, section, (lambda a=action:a.trigger()) if action is not None else None, icon=icon, enabled=action is not None,
                         reason='Work has no such action in this window.', caption='Ctrl Shift N' if key == 'new:idea' else '',
                         operation='ideas.capture' if key == 'new:idea' else 'projects.create'))
    return out


def transfer_entries(host):
    """Import where material enters (Ingress) and Export with its file or project (Egress): the cabinet's transfers."""
    out = []
    for name, key, word, icon, tip in (('a_import', 'import', 'Import (Ingress)…', 'office', 'Where material enters: the Office\'s receiving controls'),
                                       ('a_export', 'export', 'Export (Egress)…', 'leave', 'Files ▸ Egress: the copies that leave')):
        action = getattr(host, name, None)
        out.append(Entry(key, word, 'tree', (lambda a=action:a.trigger()) if action is not None else None, icon=icon, enabled=action is not None,
                         reason='Work has no such action in this window.', tip=tip))
    return out


def cabinet_tree_entries(host, t):
    """The cabinet tree's own words on any row and on its empty place: Refresh, View as (Logical cabinet or Existing views),
    New Idea and New Project, Import where material enters, Export (the homes of the cabinet's old Refresh, view words and
    Import / Export beside Trash)."""
    if t.surface != 'cabinet':return []
    page = host.cabinet_page
    out = [Entry('refresh', 'Refresh', 'tree', lambda:page.refresh(force=True), icon='restart', operation='ledger.cabinet'),
           Entry('view', 'View as', 'tree', submenu=lambda:view_as(host), icon='view')]
    node = t.data.get('node') or {}
    if t.kind == 'tree' or node.get('role') in ('project',) or t.ident in ('cabinet:projects', 'catalog:projects', 'cabinet:unassigned', 'cabinet:concern'):
        out += creation_entries(host)
    if t.kind == 'tree':out += transfer_entries(host)
    elif node.get('role') != 'project':out += transfer_entries(host)[:1]
    return out


def machine_entries(host, t):
    """The Machine tab's tree: the Work branch (open a project, New Idea, New Project, Export), this computer's rows (Refresh, Copy
    what the row says, a storage row shown in the Finder), Settings."""
    if t.surface != 'machine':return []
    page = host.machine_page;data = t.data;kind = data.get('kind');out = []
    if kind in ('work_root', 'work_empty', 'work'):
        if kind == 'work':
            out.append(Entry('open', 'Open', 'open', lambda:page.open_work(data['id']), icon='window', operation='ledger.cabinet.get'))
            out.append(Entry('inspect', 'Inspect in the line', 'command', lambda:inspect_in_line(host, '@' + data['node']['canonical_id']), icon='line',
                             tip='@' + data['node']['canonical_id'], operation='ledger.address.read'))
            out.append(Entry('export', 'Export (Egress)…', 'tree', lambda:host.a_export.trigger(), icon='leave', enabled=hasattr(host, 'a_export')))
        out += creation_entries(host)
        if kind != 'work':out += transfer_entries(host)[:1]  # the Work tree is where material enters: Import (Ingress)
    else:
        place = page.finder_place(data)
        if place:out.append(Entry('show:finder', 'Show in the Finder', 'open', lambda:host.finder.show_place(place), icon='files', enabled=getattr(host, 'finder', None) is not None))
        if kind == 'settings':out.append(Entry('open', 'Open Settings', 'open', lambda:host.ledger_bridge.show_settings(), icon='settings'))
        out.append(Entry('copy:row', 'Copy what it says', 'edit', lambda:copy_text(host, page.describe(data), 'Copied'), icon='copy'))
    out.append(Entry('refresh', 'Refresh', 'tree', lambda:page.build(force=True), icon='restart', operation='ledger.machine'))
    return out


def settings_entries(host, t):
    if t.surface != 'settings':return []
    node = t.data;key = node.get('target');out = []
    if key:
        out.append(Entry('open', 'Open this setting', 'open', lambda:host.ledger_bridge.show_settings(key=key), icon='settings', operation='ledger.settings'))
        out.append(Entry('copy:key', 'Copy the key', 'edit', lambda:copy_text(host, key, 'Copied the key'), icon='copy'))
    nav = host.settings_navigator
    out.append(Entry('expand', 'Expand all', 'tree', nav.tree.expandAll));out.append(Entry('collapse', 'Collapse all', 'tree', nav.tree.collapseAll))
    out.append(Entry('search', 'Search settings…', 'tree', lambda:search_words(host, node.get('label', '')), icon='investigations',
                     tip='The writing line in Search: SETTINGS rows as you type'))
    return out


# -- jobs and queued work (the System menu's process list) -------------------------------------------------------------------------

JOB_STOPPABLE = ('Queued', 'Running', 'Waiting for Approval', 'Waiting for Agent', 'Waiting for Execution Approval', 'Waiting for Provider', 'Paused', 'Interrupted')


def job_now(host, target):
    r = dispatch(host, 'jobs.get', {'id': target.ident})
    if not r.get('ok'):raise Refused('That job cannot be read now, so nothing was done: ' + message(r))
    job = r['result'];state = job.get('state') if isinstance(job, dict) else None
    if state != target.revision:
        raise Refused('The job moved on since you right-clicked it (%s, now %s), so nothing was done. Right-click it again.' % (target.revision, state))
    return job


def job_action(host, target, operation, done):
    """jobs.pause, jobs.resume or jobs.cancel with the job's id, after its state is read again (refused when it moved); the job row
    in the System menu's list reads its new state."""
    job_now(host, target)
    r = dispatch(host, operation, {'id': target.ident})
    if not r.get('ok'):raise Refused('%s refused: %s' % (operation, message(r)))
    show_row(host, target)
    job = r.get('result') or {};state = job.get('state')
    if state == 'Running' and operation in ('jobs.pause', 'jobs.cancel'):  # the Kernel marks it; the job stops at its next safe point
        return say(host, '%s · %s · it %s at its next safe point' % ('Asked to pause' if operation == 'jobs.pause' else 'Asked to stop', short(target.label, 60),
                                                                     'pauses' if operation == 'jobs.pause' else 'stops'))
    return say(host, '%s · %s · now %s' % (done, short(target.label, 60), str(state or 'updated').lower()))


def show_row(host, target):
    owner = target.owner
    try:
        if owner is not None and hasattr(owner, 'refresh'):owner.signature = None;owner.active_signature = None;owner.refresh()
    except RuntimeError:pass
    panel = getattr(host, 'operations_panel', None)
    if panel is not None:
        try:panel.refresh()
        except Exception:pass


# The tools whose jobs the Kernel will not pause or resume (engineering_kernel.dispatch, jobs.pause / jobs.resume), by the module
# that names them, with the words the menu says. test_context_menu asks the Kernel itself for every JOB_TOOLS it imports.
NO_PAUSE = ((('lab_service', 'math_service', 'office_service', 'local_brain', 'intake_service', 'reference_service', 'study_service',
              'knowledge_service', 'evidence_compiler', 'investigation_service'), 'A %s job does not pause: Stop it and ask again when you want it.'),
            (('network_capture',), 'A capture (%s) is stopped, never paused or resumed: Stop it and start a new one.'))


def no_pause(job):
    """Why the Kernel would refuse Pause and Resume for this job ('' when it would not): the conditions jobs.pause checks
    (engineering_kernel.dispatch: the service tools support Stop and a fresh request, a network capture is stopped and started
    anew, and external tasks have no process). The Kernel still has the last word."""
    tool = str((job or {}).get('tool') or '')
    if (job or {}).get('external_driver'):return 'An external task has no running process here; read its handoff instead.'
    try:from . import engineering_kernel as ek
    except ImportError:return ''
    for names, words in NO_PAUSE:
        tools = set()
        for name in names:tools |= set(getattr(getattr(ek, name, None), 'JOB_TOOLS', ()) or ())
        if tool in tools:return words % tool
    return ''


def job_entries(host, t):
    """A job by its state: Inspect output (its record, through staC's @job: address, in the working area), Show in Jobs (the
    Engineering room's Jobs list with its evidence, as Activity opens a job), Pause (running or queued), Resume (paused or
    interrupted), Stop (any live state), through jobs.*; Inspect in the line; Copy its id."""
    if t.kind != 'job':return []
    state = t.revision or '';program = '@job:' + str(t.ident);live = state in JOB_STOPPABLE;held = no_pause(t.data)
    evidence = str((t.data or {}).get('evidence') or '')
    output = '@evidence:' + evidence if evidence else program  # its output is kept in its evidence record; until then its record
    return [Entry('job:output', 'Inspect output', 'state', lambda:run_stac(host, output), icon='investigations', operation='language.run',
                  tip=('The job\'s output as kept in its evidence (%s), in the working area' % output) if evidence else
                      ('No output is kept for this job yet: its record and state (%s), in the working area' % program)),
            Entry('job:pause', 'Pause', 'state', lambda:job_action(host, t, 'jobs.pause', 'Paused'), icon='pause', operation='jobs.pause',
                  enabled=state in ('Running', 'Queued') and not held,
                  reason=held or 'Only a running or queued job pauses; this one is %s.' % (state.lower() or 'unknown')),
            Entry('job:resume', 'Resume', 'state', lambda:job_action(host, t, 'jobs.resume', 'Resumed'), icon='run', operation='jobs.resume',
                  enabled=state in ('Paused', 'Interrupted') and not held,
                  reason=held or 'Only a paused or interrupted job resumes; this one is %s.' % (state.lower() or 'unknown')),
            Entry('job:stop', 'Stop', 'state', lambda:job_action(host, t, 'jobs.cancel', 'Stopped'), icon='stop', operation='jobs.cancel',
                  enabled=live, reason='This job has ended (%s).' % (state.lower() or 'unknown')),
            Entry('inspect', 'Inspect in the line', 'command', lambda:inspect_in_line(host, program), icon='line', tip=program, operation='jobs.get'),
            Entry('copy:id', 'Copy the job id', 'edit', lambda:copy_text(host, t.ident, 'Copied the job id'), icon='copy')] + (
        [] if t.surface == 'jobs' else [Entry('job:show', 'Show in Jobs', 'open', lambda:show_job(host, t.ident), icon='window', operation='workspace.job',
                                              tip='The Engineering room\'s Jobs list, this job selected with its evidence')])


def show_job(host, ident):
    """The job in the Engineering room's Jobs list, selected, its evidence page showing (Activity's way to open a job)."""
    tab = host.show_engineering()
    tab.refresh()
    for i in range(tab.jobs.topLevelItemCount()):
        item = tab.jobs.topLevelItem(i)
        if item.data(0, Qt.UserRole) == ident:
            tab.pages.setCurrentWidget(tab.jobs);tab.jobs.setCurrentItem(item);tab.select_job();break
    return tab


def job_target(host, ident, surface='', owner=None):
    """A job read now (jobs.get) as a target: its state is the revision its actions carry."""
    r = dispatch(host, 'jobs.get', {'id': ident})
    if not r.get('ok') or not isinstance(r.get('result'), dict):return None
    job = r['result'];state = str(job.get('state') or '')
    from .operations import tool_words
    title = str(job.get('title') or job.get('goal') or '').strip() or tool_words(job.get('tool') or ident)  # its own name, else its family
    return Target('job', short(title, 60), 'job · ' + state.lower(), ident=ident, revision=state, data=job, surface=surface, owner=owner)


# The Agenda's own rules (agenda.dispatch: agenda.pause takes NEXT or LATER work, agenda.resume PAUSED work, agenda.cancel any
# open work, a running item too, as the Agenda room's running row offers it). test_context_menu asks the Kernel for each state.
AGENDA_PAUSES = ('NEXT', 'LATER')
AGENDA_RESUMES = ('PAUSED',)


def agenda_open():
    try:from .agenda import OPEN
    except ImportError:OPEN = ('NEXT', 'LATER', 'RUNNING', 'PAUSED', 'SUGGESTED')
    return tuple(OPEN)


def queued_now(host, target):
    r = dispatch(host, 'agenda.view', {})
    if not r.get('ok'):raise Refused('The queue cannot be read now, so nothing was done: ' + message(r))
    rows = [row for part in ('now', 'next', 'waiting', 'later', 'suggested', 'done') for row in (r['result'].get(part) or []) if isinstance(row, dict)]
    row = next((row for row in rows if row.get('id') == target.ident), None)
    if row is None or row.get('state') != target.revision:
        raise Refused('That queued work moved on since you right-clicked it (%s, now %s), so nothing was done.' % (target.revision, (row or {}).get('state', 'gone')))
    return row


def queued_action(host, target, operation, done):
    queued_now(host, target)
    r = dispatch(host, operation, {'id': target.ident})
    if not r.get('ok'):raise Refused('%s refused: %s' % (operation, message(r)))
    show_row(host, target)
    return say(host, '%s · %s' % (done, short(target.label, 60)))


def queued_entries(host, t):
    """Agenda work (queued or running) by its state, as the Agenda's rules allow: Pause (waiting work), Resume (paused work), Stop
    (any open work: a running item is cancelled, as the Agenda room's running row does) through agenda.pause, agenda.resume and
    agenda.cancel; its job by its state now when it runs one; its staC program in the line; Open Agenda."""
    if t.kind != 'queued':return []
    state = str(t.revision or '');program = str(t.data.get('program') or '');words = state.lower() or 'unknown'
    running = state == 'RUNNING'
    out = [Entry('queued:pause', 'Pause', 'state', lambda:queued_action(host, t, 'agenda.pause', 'Paused'), icon='pause', operation='agenda.pause',
                 enabled=state in AGENDA_PAUSES,
                 reason='Running Agenda work does not pause; Stop cancels it.' if running else 'Only waiting work pauses; this is %s.' % words),
           Entry('queued:resume', 'Resume', 'state', lambda:queued_action(host, t, 'agenda.resume', 'Resumed'), icon='run', operation='agenda.resume',
                 enabled=state in AGENDA_RESUMES, reason='Only paused work resumes; this is %s.' % words),
           Entry('queued:stop', 'Stop', 'state', lambda:queued_action(host, t, 'agenda.cancel', 'Stopped' if running else 'Stopped and removed from the queue'),
                 icon='stop', operation='agenda.cancel', enabled=state in agenda_open(), reason='This work has ended (%s).' % words,
                 tip='Cancel it while it runs; what it already did stays' if running else 'Take it out of the queue')]
    job = str(t.data.get('job') or '')
    if job:
        def its_job(ident=job):
            found = job_target(host, ident, surface='queued')
            return job_entries(host, found) if found is not None else [Entry('job:gone', 'That job is gone', 'state', enabled=False, reason='jobs.get does not find it.')]
        out.append(Entry('job', 'Its job', 'state', submenu=its_job, icon='job', tip='The Kernel job this Agenda work runs, by its state now'))
    if program:
        out.append(Entry('inspect', 'Inspect in the line', 'command', lambda:inspect_in_line(host, program), icon='line', tip=program))
    from .shell2 import open_destination
    out.append(Entry('agenda', 'Open Agenda', 'open', lambda:open_destination(host, 'agenda'), icon='agenda'))
    return out


# -- the Log view: events and the network -------------------------------------------------------------------------------------------

def log_focus(host, entry):
    from . import log_qt
    return log_qt.focus(host, entry)


def far_address(entry):
    """The far side of a connection or packet (a packet: the side with the lower port, the service's)."""
    from .log_qt import address
    if entry.get('kind') == 'packet':
        sport, dport = entry.get('sport'), entry.get('dport')
        if isinstance(sport, int) and isinstance(dport, int) and sport < dport:return address(entry.get('src'), sport)
        return address(entry.get('dst'), dport)
    return address(entry.get('remote'), entry.get('rport'))


def known_process(entry):
    """The program behind a connection or packet when it is known: its first word. D5's reader (network_watch) writes 'another
    user' for a process of another account, whose name is not this account's to read and is never guessed: not a program."""
    try:from .network_watch import ANOTHER_USER
    except ImportError:ANOTHER_USER = 'another user'
    words = str(entry.get('process') or '').split()
    return '' if not words or ' '.join(words) == ANOTHER_USER else words[0]


def show_process(host, entry):
    """The process behind a connection or packet: the Network stream filtered to it (every connection and packet of that
    program), the entry pinned with its details."""
    from . import log_qt
    name = known_process(entry)
    view = log_qt.focus(host, entry)
    if view is None or not name:return view
    text = 'proc ' + name;bar = getattr(host, 'type_bar', None)
    if bar is not None:bar.box.setText(text)
    view.apply_filter(text);view.pin(entry)
    say(host, 'The Network stream filtered to %s%s' % (name, (' (pid %s)' % entry['pid']) if entry.get('pid') else ''))
    return view


def network_entries(host, t):
    """A network connection or packet (the owner replaced Log's notes with the network): Ask Stacy about this (an assignment
    with the entry as its context), Follow this conversation (the stream filtered to it, the entry pinned), Show the process
    (when known), Copy address."""
    if t.kind not in ('connection', 'packet'):return []
    from . import log_qt
    entry = t.data;process = known_process(entry)
    unknown = ('Its program belongs to another user of this computer; Graphite does not read or guess its name.' if entry.get('process') and not process
               else 'The process is not known for this %s.' % t.noun)
    return [Entry('ask', named('Ask Stacy about this'), 'state', lambda:log_qt.ask_about(host, entry), icon='inquiries',
                  tip='An assignment in the line with this %s as its context' % t.noun),
            Entry('follow', 'Follow this conversation', 'state', lambda:log_focus(host, entry), icon='network',
                  enabled=bool(log_qt.conversation(entry)), reason='No far host or port to follow.', tip='The Network stream filtered to ' + (log_qt.conversation(entry) or 'it')),
            Entry('process', 'Show the process', 'state', lambda:show_process(host, entry), icon='brain', enabled=bool(process),
                  reason=unknown, caption=str(process or entry.get('process') or '')[:18]),
            Entry('copy:address', 'Copy address', 'edit', lambda:copy_text(host, far_address(entry), 'Copied the address'), icon='copy', caption=far_address(entry)[:24])]


def event_entries(host, t):
    """An event (the Log's Events stream or Activity's timeline): Ask Stacy about this, Show in Log (the Events stream with the
    event pinned), Copy; in Activity also Open, as its activation does. No notes: the owner replaced them with the network."""
    if t.kind != 'event':return []
    from . import log_qt
    entry = t.data;event = entry.get('event') or {}
    out = [Entry('ask', named('Ask Stacy about this'), 'state', lambda:log_qt.ask_about(host, entry), icon='inquiries', tip='An assignment in the line with this event as its context'),
           Entry('show:log', 'Show in Log', 'state', lambda:log_focus(host, entry), icon='event', enabled=getattr(host, 'log_view', None) is not None,
                 reason='The Log view is not in this window.', tip='The writing line in Log on the Events stream, this event pinned')]
    if t.surface == 'activity' and t.owner is not None and hasattr(t.owner, 'open_event'):
        item = t.extra.get('item')
        out.insert(0, Entry('open', 'Open', 'open', lambda:t.owner.open_event(item) if item is not None else None, icon='window',
                            tip='Where the event happened: its job, the Settings or the commands'))
    if event.get('job_id'):
        def its_job(ident=str(event['job_id'])):
            job = job_target(host, ident, surface='event')
            return job_entries(host, job) if job is not None else [Entry('job:gone', 'That job is gone', 'state', enabled=False, reason='jobs.get does not find it.')]
        out.append(Entry('job', 'Its job', 'state', submenu=its_job, icon='job', tip='The job behind this event, by its state now: Pause, Resume, Stop'))
    out.append(Entry('copy', 'Copy', 'edit', lambda:copy_text(host, entry.get('line') or log_qt.event_line(event)), icon='copy'))
    return out


# -- an empty place: the root (the owner's chain menu as one provider) ---------------------------------------------------------------

def chain_qmenu(host, program):
    """The chain builder from a staC start (chain_menu.fill), a QMenu cascade dressed in the desk's menu metrics."""
    from .chain_menu import Chain, desk_style
    menu = Chain(host, program, program, host);desk_style(menu, host);return menu


def kept_chain_entries(host):
    """The owner's menu file (~/Concern/Ledger menu) as entries: each kept chain runs as written (then console, sheet, watch or
    Agenda); a line that does not parse is shown greyed with its reason. The file is read, never run."""
    from . import chain_menu
    path = chain_menu.menu_path()
    if not path.is_file():
        return [Entry('chains:none', 'No kept chains yet', 'command', enabled=False, reason='End a chain with then › keep this chain…')]
    tree, problems = chain_menu.parse_menu(path.read_text(encoding='utf-8', errors='replace'))
    from .stacy_language import source
    from sdk.cli.arc1cli import typed_pipeline
    def build(items, prefix='chains:'):
        out = []
        for n, item in enumerate(items):
            if item[0] in ('shell', 'stock', 'separator'):continue
            if item[0] == 'submenu':
                out.append(Entry(prefix + 'sub:%d' % n, item[1], 'command', submenu=lambda items=item[2], p=prefix + '%d:' % n:build(items, p), icon='chain'));continue
            _, name, program, how = item
            try:typed_pipeline.parse(source(program)[0]);ok, reason = True, ''
            except ValueError as exc:ok, reason = False, str(exc)[:200]
            out.append(Entry(prefix + name, name, 'command', lambda p=program, h=how:chain_menu.then(host, p, h), icon='chain', enabled=ok,
                             reason='Does not parse: ' + reason if not ok else '', tip=program))
        return out
    out = build(tree)
    if problems:out.append(Entry('chains:problems', '%d line%s not understood' % (len(problems), '' if len(problems) == 1 else 's'), 'command', enabled=False,
                                 reason='\n'.join('line %d: %s' % p for p in problems[:10])))
    return out or [Entry('chains:none', 'No kept chains yet', 'command', enabled=False, reason='The menu file has no chains.')]


def start_entries(host):
    from .shell2 import call
    from .chain_menu import TABLE_KINDS
    found = [e for e in (call(host, 'files.find', {'limit': 80}) or {}).get('records', [])
             if e.get('kind') in TABLE_KINDS + ('markdown', 'dxf', 'stl', 'obj', '3mf', 'text', 'json')]
    out = [Entry('start:' + e['path'], e['path'], 'command', qmenu=lambda p=e['path']:chain_qmenu(host, '@files:' + p), icon='chain') for e in found[:30]]
    return out or [Entry('start:none', 'Nothing in Files to read yet', 'command', enabled=False)]


def writing_line_entries(host):
    bar = getattr(host, 'type_bar', None);out = []
    for key, word in (('slate', 'Assignment'), ('shell', getattr(bar, 'labels', {}).get('shell', 'Shell') if bar else 'Shell'), ('find', 'Search'), ('log', 'Log')):
        def choose(key=key):
            bar.set_target(key, focus=True)
            console = getattr(host, 'console', None)
            if console is not None and console.size_level == 0:console.set_size(1)
        out.append(Entry('line:' + key, word, 'command', choose if bar is not None else None, enabled=bar is not None, checked=getattr(bar, 'target', None) == key))
    return out


def root_entries(host):
    """The root of the owner's pipe menu (chain_menu.root_menu, folded): Inquiries, the Algorithm and Theory Atlas, the Tool
    Atlas, the kept chains, a chain from a file in Files, the writing line's modes, the menu file."""
    from . import chain_menu
    bridge = getattr(host, 'ledger_bridge', None)
    def bridged(name):
        return (lambda:getattr(bridge, name)()) if bridge is not None and hasattr(bridge, name) else None
    missing = 'Not available in this window.'
    return [Entry('inquiries', 'Inquiries…', 'capability', bridged('show_discovery'), icon='inquiries', enabled=bridged('show_discovery') is not None, reason=missing),
            Entry('algorithms', 'Algorithm & Theory Atlas…', 'capability', bridged('show_algorithms'), icon='methods', enabled=bridged('show_algorithms') is not None, reason=missing),
            Entry('atlas', 'Tool Atlas…', 'capability', bridged('show_atlas'), icon='tools', enabled=bridged('show_atlas') is not None, reason=missing),
            Entry('chains', 'Your chains', 'command', submenu=lambda:kept_chain_entries(host), icon='chain', tip='The chains kept in your Graphite menu file'),
            Entry('start', 'Start a chain from', 'command', submenu=lambda:start_entries(host), icon='chain', tip='A file in Files, read link by link'),
            Entry('line', 'Writing line', 'command', submenu=lambda:writing_line_entries(host), icon='line', tip='Assignment, Shell, Search or Log, the working area open'),
            Entry('menu:edit', 'Edit the Graphite menu…', 'command', lambda:chain_menu.edit_menu_file(host), tip=str(chain_menu.menu_path()).replace(str(Path.home()), '~'))]


def root_entry(host):
    """A room's empty place with words of its own (Files, a Finder folder, the Library) carries the whole root as one row, where
    Files' old chains › held it; Today and the workspace's empty place are the root itself (empty_entries)."""
    return Entry('root', 'Root menu', 'command', submenu=lambda:root_entries(host), icon='chain',
                 tip='The menu of an empty place, as on Today: Inquiries, the atlases, your chains, a chain from a file, the writing line, the Graphite menu file')


def empty_entries(host, t):
    """An empty place (Today, the workspace): the root of the owner's chain menu, folded (root_entries), and the creation and
    import that belong where nothing is selected."""
    if t.kind != 'empty' or t.surface not in ('today', 'workspace'):return []
    return root_entries(host) + creation_entries(host) + transfer_entries(host)[:1]


def _plain_number(value):
    text = format(value.normalize(), 'f') if value == value.to_integral_value() else format(value, 'f').rstrip('0').rstrip('.')
    return text if text not in ('', '-0') else '0'


def field_whatif_rows(host, obj):
    """What if ▸: one row for each number of the sheet (or each input of the calculation), with its cell, its words and its
    value; under each, the values worth trying. Choosing one asks Stacy the what-if (a read: nothing is changed), and the
    Field marks what would move. "Another value…" puts the question in the writing line to finish."""
    from decimal import Decimal, InvalidOperation
    from .engine import engineering
    from .engineering_kernel import operator
    from .field_doubt import unit_of
    from .field_ripple import _label, cells_named
    kernel = engineering(host.root);sheet, names = cells_named(kernel, operator(), obj)
    got = kernel.dispatch('office.get', {'id': sheet}, operator()) if sheet else {}
    if not got.get('ok') or not names:
        return [Entry('field:whatif:none', 'It has no number to set', 'capability', enabled=False, reason='A what-if sets a number of a sheet, or an input of a calculation')]
    cells = ((got['result'].get('document') or {}).get('sheets') or [{}])[0].get('cells') or {};out = []
    for cell in sorted(set(names.values()), key=lambda name: (len(name), name))[:24]:
        value = str((cells.get(cell) or {}).get('value') or '').strip();unit = unit_of(cells, cell);said = _label(cells, cell)
        try:
            number = Decimal(value)
        except (InvalidOperation, ValueError):
            continue
        def tries(cell=cell, number=number, unit=unit):
            rows = []
            for key, words, factor in (('more', '10 % more', Decimal('1.1')), ('less', '10 % less', Decimal('0.9')), ('twice', 'Twice', Decimal(2)), ('half', 'Half', Decimal('0.5'))):
                new = _plain_number(number * factor)
                rows.append(Entry('field:whatif:%s:%s' % (cell, key), ('%s · %s %s' % (words, new, unit)).strip(), 'command',
                                  lambda new=new: host.shell2.ask('what if %s were %s' % (cell, new)), icon='line', operation='field.ripple',
                                  tip=named('A read: nothing is changed. Stacy follows the wires and the Field marks what would move, until Esc')))
            rows.append(Entry('field:whatif:%s:other' % cell, 'Another value…', 'command', lambda: ask_graphite(host, 'what if %s were ' % cell), icon='ask',
                              tip='The question in the writing line for you to finish; Enter asks'))
            return rows
        out.append(Entry('field:whatif:' + cell, short(' · '.join(part for part in (cell, said, ('%s %s' % (value, unit)).strip()) if part), 58), 'command', icon='line', submenu=tries))
    return out or [Entry('field:whatif:none', 'It has no number to set', 'capability', enabled=False, reason='A what-if sets a number of a sheet, or an input of a calculation')]


def field_step_rows(host, view, obj):
    """What can be done ▸: the steps the records offer for this sheet, as D shows them. A read runs at once and Stacy shows
    its line and the answer; a step that changes something is put up in Talk and waits for G. Choosing here never approves."""
    from . import field_page
    from .engine import engineering
    from .engineering_kernel import operator
    from .field_do import steps_for
    steps = steps_for(engineering(host.root), operator(), obj, view.field)
    def take(line):
        offered = field_page.do(host, obj)         # the same steps D shows, read now; the one chosen is found by its exact line
        at = next((n for n, step in enumerate(offered) if step.line == line), None)
        if at is not None:field_page.take(host, obj, at)
    return [Entry('field:do:%d' % n, short(step.words, 56), 'command', lambda line=step.line: take(line), icon='line', caption='asks' if step.kind == 'write' else '',
                  tip=((step.why[:1].upper() + step.why[1:] + '.\n') if step.why else '') + ('It changes something: it is put up in Talk and waits for your go (G).' if step.kind == 'write' else 'A read: it runs at once.') + '\n' + step.line[:300])
            for n, step in enumerate(steps)] or [Entry('field:do:none', 'The records offer nothing to do about this', 'capability', enabled=False)]


def field_doubt_rows(host, view, obj):
    """Doubt it ▸: what Stacy finds when she cross-examines this, right in the menu, worst first. A row's reason is its tooltip;
    choosing a row shows the read that is its evidence, in Talk. The first row is the whole of it in Talk (X)."""
    from .engine import engineering
    from .engineering_kernel import operator
    answer = engineering(host.root).dispatch('field.doubt', {'id': obj.id}, operator())
    out = [Entry('field:doubt:all', 'All of it, in Talk', 'command', lambda: view.doubt_asked.emit(obj), icon='ask', caption='X')]
    if not answer.get('ok'):
        return out + [Entry('field:doubt:problem', 'It could not be looked at', 'capability', enabled=False, reason=str((answer.get('error') or {}).get('message'))[:200])]
    def show(row):
        face = getattr(getattr(host, 'shell2', None), 'show_slate_face', lambda: None)()
        if face is not None and row.get('see'):
            face.answer_in_stac({'title': obj.title, 'stac': row['see'], 'kind': obj.kind}, '%s: %s. The read that shows it:' % (row['about'][:1].upper() + row['about'][1:], row['why']))
        view.setFocus(Qt.OtherFocusReason)
    for n, row in enumerate(answer['result'].get('rows', ())[:16]):
        out.append(Entry('field:doubt:%d' % n, short('%s · %s' % (row['verdict'], row['about']), 58), 'state', (lambda row=row: show(row)) if row.get('see') else None,
                         icon='line', enabled=bool(row.get('see')), reason='' if row.get('see') else row['why'], tip=row['why'] + ('\nChoose it to see the read that shows this.' if row.get('see') else '')))
    return out


def field_trace_rows(host, view, obj, select):
    """Trace it ▸: where this comes from, farthest first, then what rests on it; choosing a row goes to that sheet. The first
    row tells the whole trace in Talk (T)."""
    from .engine import engineering
    from .engineering_kernel import operator
    answer = engineering(host.root).dispatch('field.trace', {'id': obj.id}, operator())
    out = [Entry('field:trace:all', 'The whole trace, in Talk', 'command', lambda: view.trace_asked.emit(obj), icon='ask', caption='T')]
    for row in (answer['result'].get('rows', ()) if answer.get('ok') else ()):
        if row['way'] == 'this':continue
        out.append(Entry('field:trace:' + row['id'], short(('← ' if row['way'] == 'from' else '→ ') + str(row['title']), 56), 'state', lambda ident=row['id']: select(ident),
                         caption=str(row['kind']), tip='%s, %d step%s %s%s' % (row['kind'], row['steps'], '' if row['steps'] == 1 else 's', 'back' if row['way'] == 'from' else 'on',
                                                                             (' · by ' + row['by']) if row.get('by') else '')))
    if len(out) == 1:
        out.append(Entry('field:trace:none', 'Nothing is wired to it', 'capability', enabled=False))
    return out


def word_rows(host, manage=False):
    """Your words ▸: the owner's own staC words (workbench/stac_words.py). On a sheet, choosing one runs it in Talk, and a word
    whose line starts with `this` reads the selected sheet. On the Field's own menu each word also goes to the line or is
    forgotten, and a new one can be started."""
    from .stac_words import known_to
    words = known_to(host, fresh=True);out = []
    for name, line in sorted(words.items()):
        run = lambda name=name: host.shell2.ask(name)
        if manage:
            out.append(Entry('words:' + name, name, 'command', icon='line', tip=line, submenu=lambda name=name, line=line, run=run: [
                Entry('words:%s:run' % name, 'Run it', 'command', run, icon='line', operation='language.run', tip=line),
                Entry('words:%s:line' % name, 'In the line', 'command', lambda: inspect_in_line(host, name), icon='line', tip='The word in the writing line, to go on from: ' + name + ' | …'),
                Entry('words:%s:forget' % name, 'Forget it', 'edit', lambda: inspect_in_line(host, 'forget ' + name), icon='line', tip='Puts “forget %s” in the line; Ctrl+Enter lets the word go' % name)]))
        else:
            out.append(Entry('words:' + name, name, 'command', run, icon='line', operation='language.run', tip=line))
    if manage or not out:
        out.append(Entry('words:new', 'Keep a new word…', 'edit', lambda: inspect_in_line(host, 'word '), icon='line',
                         tip='In the line: word NAME = a line that reads. Keep it, and then the word is the line'))
    return out


def field_entries(host, t):
    """The Field (workbench/field_page.py): the instruments for the selected sheet, the same ones Enter, the arrow keys and the
    writing line reach. A sheet of the work face opens its real page, shows what feeds it and what it feeds, goes to the line as
    its staC address, or becomes the subject of an assignment; a sheet of the network face opens the Log's Network stream on it.
    An empty place of the Field offers the Field's own commands. Nothing here changes a record."""
    if t.surface != 'field':return []
    from . import field_page
    view = t.owner;page = getattr(host, 'field_page', None);obj = t.data.get('object');out = []
    def select(ident):
        view.field.select(ident);view._layout();view._reveal();view._describe();view.update();view.setFocus(Qt.OtherFocusReason)
    if obj is None:
        other = [name for name, _ in view.faces if name != view.face]
        out.append(Entry('field:again', 'Look again', 'open', view.look_again.emit, icon='explore', caption='R', tip='Read the records again'))
        if view.face == 'work':
            out.append(Entry('field:check', 'Check the desk', 'command', view.check_asked.emit, icon='explore', caption='C',
                             tip=named('Everything is read again; Stacy says what waits for you and what would settle it')))
        for name in other:
            out.append(Entry('field:face:' + name, 'Show the %s' % name, 'open', lambda name=name:view.face_chosen.emit(name), icon='network' if name == 'network' else 'projects',
                             caption=dict(view.faces)[name].upper()))
        out.append(Entry('field:back', 'Back', 'open', view.left.emit, icon='explore', caption='Esc'))
        if view.face == 'network':
            lines = (('Every connection', 'network.observe | pick connections | select process,remote,rport,state'),
                     ('What is listening', 'network.observe | pick connections | where state=LISTEN | select process,local,lport'),
                     ('The interfaces', 'network.observe | pick interfaces | select name,up,rx_bps,tx_bps'))
        elif view.face == 'programs':
            lines = (('Every program', 'ledger.explore {"kind":"INSTRUMENT"} | pick instruments | select title,group,view_state,tool_status'),
                     ('What needs setting up', 'ledger.explore {"kind":"INSTRUMENT"} | pick instruments | select title,setup_needed,tool_status'),
                     ('What is running', 'ledger.explore {"kind":"INSTRUMENT"} | pick instruments | select title,running_jobs,queued_jobs'))
        else:
            lines = (('Everything that waits', 'field.read | pick waiting | select kind,title,state'),
                     ('What I doubt', 'field.doubt | pick rows | where verdict=doubt | select title,about,why'),
                     ('The brief, line by line', 'field.brief | pick lines | select text'),
                     ('What changed lately', 'field.read | pick objects | where lately=yes | select kind,title,changed_at'),
                     ('The wires', 'field.read | pick links | select from,to,label,stale'),
                     ('The pages', 'documents.list | pick documents | select title,revision,words'),
                     ('The sheets', 'office.list | pick documents | select title,kind,version'),
                     ('Work that is not finished', 'jobs | where state is not Completed | select tool,state'))
            out.append(Entry('field:brief', 'The brief', 'command', view.brief_asked.emit, icon='line', caption='B',
                             tip=named('The desk written up as one page, from the records. Stacy shows every line; keeping it as a page asks first')))
        try:                                  # the owner's own staC words go with the lines of every face
            from .stac_words import known_to
            lines = tuple(lines) + tuple(('Your word “%s”' % name, code) for name, code in sorted(known_to(host).items()))
        except Exception:  # noqa: BLE001 - the menu is never stopped because the words could not be read
            pass
        out.append(Entry('field:stac', 'This face as lines', 'command', icon='line', tip='Read-only lines for what the Field shows; each goes to the writing strip',
                         submenu=lambda:[Entry('field:stac:%d' % n, label, 'command', lambda code=code:inspect_in_line(host, code), icon='line', tip=code)
                                         for n, (label, code) in enumerate(lines)]))
        out.append(Entry('field:words', 'Your words', 'command', icon='line', submenu=lambda:word_rows(host, manage=True),
                         tip='Lines you keep under words of your own: run one, put it in the line, forget it, or keep a new one'))
        return out
    target = obj.target if isinstance(obj.target, dict) else {}
    network = target.get('kind') == 'network'
    out.append(Entry('field:open', 'Show in Log' if network else 'Open', 'open', lambda:field_page.open_object(host, obj), icon='network' if network else t.icon,
                     caption='Enter', tip='The Log\'s Network stream, filtered to this' if network else 'This program\'s room' if target.get('kind') == 'program' else 'The real page for this, in its own room'))
    fed = [view.field.get(l.source) for l in view.field.fed_by(obj.id)];feeds = [view.field.get(l.target) for l in view.field.feeds(obj.id)]
    def rows(objects):
        return lambda:[Entry('field:go:' + o.id, short(o.title, 54), 'state', lambda o=o:select(o.id), caption=(o.tag or o.kind).lower()) for o in objects]
    verb_from, verb_to = view.field.verbs
    out.append(Entry('field:fed', 'What it is %s' % verb_from if verb_from == 'held by' else 'What feeds it', 'state', enabled=bool(fed), reason='Nothing is recorded as feeding this',
                     submenu=rows(fed), caption='←'))
    out.append(Entry('field:feeds', 'What it %s' % verb_to, 'state', enabled=bool(feeds), reason='Nothing is recorded as coming from this', submenu=rows(feeds), caption='→'))
    if obj.stac:      # staC, said Stacy: the line that reads this object. In the line to read or change, or run as it is (a read).
        out.append(Entry('field:inspect', 'Inspect in the line', 'command', lambda:field_page.stac_in_line(host, obj), icon='line', caption='S',
                         tip='Its line in the writing strip; nothing runs until you run it:\n' + obj.stac))
        out.append(Entry('field:run', 'Run its line', 'command', lambda:field_page.stac_run(host, obj), icon='line', caption='Shift+Enter',
                         operation='language.run', tip='A read; the answer shows in the working area:\n' + obj.stac))
    work = view.face == 'work'
    if work and obj.kind in ('sheet', 'calculation'):      # the cascade for looking ahead: a number, then a value to try
        out.append(Entry('field:whatif', 'What if', 'command', icon='line', submenu=lambda:field_whatif_rows(host, obj),
                         tip='Set one of its numbers to another value without changing anything: the wires are followed and the Field marks what would move'))
    out.append(Entry('field:doubt', 'Doubt it', 'command', lambda:view.doubt_asked.emit(obj), icon='line', caption='X',
                     submenu=(lambda:field_doubt_rows(host, view, obj)) if work else None,
                     tip='Cross-examine it for what a plausible result may hide: what does not hold, what cannot be told, what holds (X shows all of it in Talk)'))
    out.append(Entry('field:trace', 'Trace it', 'command', lambda:view.trace_asked.emit(obj), icon='line', caption='T',
                     submenu=(lambda:field_trace_rows(host, view, obj, select)) if work else None,
                     tip='Where it comes from and what rests on it, hop by hop along the wires; choose one to go there (T tells it in Talk)'))
    out.append(Entry('field:do', 'What can be done', 'command', lambda:view.do_asked.emit(obj), icon='line', caption='D',
                     submenu=lambda:field_step_rows(host, view, obj),
                     tip='The steps the records offer for this. A read runs at once; one that changes something is put up and waits for your go (D shows them in the Field)'))
    if work and obj.stac:
        out.append(Entry('field:words', 'Your words', 'command', icon='line', submenu=lambda:word_rows(host),
                         tip='Run one of your own words here; a word whose line starts with `this` reads this sheet'))
    if view.face == 'work':
        out.append(Entry('field:brief', 'The brief of the desk', 'command', view.brief_asked.emit, icon='line', caption='B',
                         tip=named('The whole desk written up as one page, from the records. Stacy shows every line; keeping it as a page asks first')))
    if not network:
        out.append(Entry('field:ask', named('Ask Stacy about this'), 'command', lambda:ask_about_sheet(host, obj),
                         icon='ask', tip='Its name in the line for you to finish. Her answer is in Talk; with no model she answers from the records, with the line that reads them'))
    out.append(Entry('field:copy', 'Copy its name', 'edit', lambda:copy_text(host, obj.title), icon='copy'))
    return out


def activity_selection_entries(host, t):
    """Activity's cabinet selection: the record's own words (Open record, Explore) as the Activity words do."""
    if t.surface != 'activity' or t.kind != 'cabinet':return []
    panel = t.owner
    return [Entry('activity:explore', 'Explore', 'capability', panel.explore, icon='explore', tip='The Explore workspace with this record')]


# The providers, in the order they are asked (each a small function: target -> entries).
PROVIDERS = (('document', document_entries), ('file', file_entries), ('files', files_entries), ('files-place', files_place_entries),
             ('finder', finder_entries), ('finder-place', finder_place_entries), ('library', library_entries), ('library-place', library_place_entries),
             ('cabinet', cabinet_entries), ('cabinet-tree', cabinet_tree_entries), ('activity', activity_selection_entries), ('machine', machine_entries),
             ('settings', settings_entries), ('job', job_entries), ('queued', queued_entries), ('network', network_entries), ('event', event_entries),
             ('empty', empty_entries), ('field', field_entries))


def entries_for(host, target):
    """Ask every provider; keep the first entry for a key; order by section (SECTIONS), keeping each provider's order inside it."""
    seen = set();out = []
    from .command_context import entries as command_entries
    for name, provider in (('menu-objects', command_entries),) + PROVIDERS:
        try:found = provider(host, target) or []
        except Exception as exc:  # one provider's trouble never costs the others their rows
            found = [Entry('problem:' + name, 'Some actions are unavailable', 'capability', enabled=False, reason='%s: %s' % (name, exc))]
        for entry in found:
            if entry.key in seen:continue
            seen.add(entry.key);entry.provider = name;out.append(entry)
    order = {s: i for i, s in enumerate(SECTIONS)}
    return sorted(out, key=lambda e:order.get(e.section, len(SECTIONS)))


# -- finders: what is under the pointer ------------------------------------------------------------------------------------------------

def find_document(host, w, point):
    """A document page: the passage when the pointer is on the selection; elsewhere the caret moves there first, as editors do,
    and the target is the page at that paragraph."""
    from .document_qt import DocumentPage
    if not isinstance(w, DocumentPage):return None
    local = w.viewport().mapFrom(w, point)
    if not _in_selection(w, local):w.setTextCursor(w.cursorForPosition(local))
    return document_target(w.tab, w)


def _in_selection(page, local):
    cursor = page.textCursor()
    if not cursor.hasSelection():return False
    at = page.cursorForPosition(local).position()
    return cursor.selectionStart() <= at <= cursor.selectionEnd()


def find_files(host, w, point):
    from .files_qt import FilesTab
    tab = w.parentWidget()
    while tab is not None and not isinstance(tab, FilesTab):tab = tab.parentWidget()
    if tab is None or w not in (tab.icons, tab.table):return None
    view = w;item = view.itemAt(view.viewport().mapFrom(view, point))
    if item is None:view.clearSelection()  # an empty place: the folder itself
    elif item not in view.selectedItems():view.clearSelection();item.setSelected(True);view.setCurrentItem(item)
    chosen = tab.selected() if item is not None else []
    if not chosen:return Target('empty', tab.heading.text() or 'Files', 'folder in Files', surface='files', owner=tab, icon='files')
    if len(chosen) > 1:
        names = ', '.join(e['name'] for e in chosen[:2]) + (' and %d more' % (len(chosen) - 2) if len(chosen) > 2 else '')
        return Target('files', names, '%d items' % len(chosen), items=list(chosen), surface='files', owner=tab, data=chosen[0])
    e = chosen[0];folder = e['kind'] in ('folder', 'smart')
    kind = 'folder' if folder else file_kind(e['name'])
    return Target(kind, e['name'], NOUNS[kind][0] if kind != 'file' else (e.get('kind_words') or 'file').lower(), ident=e['path'], revision=file_revision(e),
                  data=e, items=[e], surface='files', owner=tab)


def find_finder(host, w, point):
    from .finder_qt import ENTRY, FinderPage
    page = w.parentWidget()
    while page is not None and not isinstance(page, FinderPage):page = page.parentWidget()
    if page is None:return None
    views = [page.list, page.icons] + [c[1] for c in getattr(page.columns, 'columns', [])]
    if w in views:
        item = w.itemAt(w.viewport().mapFrom(w, point))
        if item is not None:
            w.setCurrentItem(item);entry = item.data(0, ENTRY) if isinstance(w, QTreeWidget) else item.data(ENTRY)
            if entry:
                path = page.entry_path(entry);kind = 'folder' if entry['kind'] == 'folder' else file_kind(entry['name'])
                return Target(kind, entry['name'], NOUNS[kind][0], ident=path, data=entry, surface='finder', owner=page)
        if page.place in (None, 'today'):return None
        return Target('empty', page.place_name() or str(page.place), 'folder in the Finder', ident=page.place, surface='finder', owner=page, icon='files')
    return None


def find_cabinet(host, w, point):
    page = getattr(host, 'cabinet_page', None)
    if page is None or w is not page.tree:return None
    item = w.itemAt(w.viewport().mapFrom(w, point))
    if item is None:return Target('tree', 'Cabinet', 'tree · ' + ('existing views' if page.using_legacy else 'logical cabinet'), surface='cabinet', owner=page, icon='memory')
    w.setCurrentItem(item);page.remember();node = item.data(0, Qt.UserRole) or {}
    role = str(node.get('role', '')).replace('_', ' ')
    return Target('cabinet', node.get('label', ''), 'record · ' + role + ((' · revision %s' % node['revision']) if node.get('revision') is not None else ''),
                  ident=node.get('id'), revision=node.get('revision'), data=dict(node=node), surface='cabinet', owner=page)


def find_machine(host, w, point):
    page = getattr(host, 'machine_page', None)
    if page is None or w is not getattr(page, 'tree', None):return None
    item = w.itemAt(w.viewport().mapFrom(w, point))
    if item is None:return Target('machine', 'Machine', 'tree', data={'kind': 'none'}, surface='machine', owner=page)
    w.setCurrentItem(item);data = item.data(0, Qt.UserRole) or {}
    kind = 'work' if str(data.get('kind', '')).startswith('work') else 'machine'
    noun = {'work_root': 'the Work tree', 'work_empty': 'the Work tree', 'work': 'project on the Work tree', 'root': 'this computer', 'section': 'section',
            'item': 'observation', 'settings': 'Settings'}.get(data.get('kind'), 'row')
    return Target(kind, item.text(0), noun, ident=data.get('id'), data=data, surface='machine', owner=page)


def find_settings(host, w, point):
    nav = getattr(host, 'settings_navigator', None)
    if nav is None or w is not nav.tree:return None
    item = w.itemAt(w.viewport().mapFrom(w, point))
    if item is None:return None
    w.setCurrentItem(item);node = item.data(0, Qt.UserRole) or {}
    return Target('setting', node.get('label', item.text(0)), 'setting · ' + node['target'] if node.get('target') else 'settings group', ident=node.get('target'),
                  data=node, surface='settings', owner=nav)


def find_library(host, w, point):
    from .shell2 import LibraryTab
    tab = w.parentWidget()
    if not isinstance(tab, LibraryTab) or w is not tab.table:return None
    item = w.itemAt(w.viewport().mapFrom(w, point))
    if item is None:return Target('empty', 'Library', 'received files', surface='library', owner=tab, icon='office')
    w.setCurrentItem(item);entry = item.data(0, Qt.UserRole) or {}
    return Target('library', entry.get('name', item.text(0)), 'received file · ' + str(entry.get('delivery', '')), ident=entry.get('delivery_id'), data=entry,
                  surface='library', owner=tab)


def find_today(host, w, point):
    from .shell2 import TodayPage
    if not isinstance(w, TodayPage):return None
    return Target('empty', 'Today', 'an empty place', surface='today', owner=w, icon='explore')


def find_log(host, w, point):
    """The Log view's two streams (D3's log_qt): an event, a network connection or a packet under the pointer, or the pinned one."""
    from . import log_qt
    if not isinstance(w, QListWidget) and w.objectName() != 'LogPinned':return None
    view = getattr(host, 'log_view', None)
    if view is None or w not in (view.events, view.connections, view.packets, view.pin_frame):return None
    target_widget = w.viewport() if isinstance(w, QListWidget) else w
    entry = log_qt.entry_at(target_widget, target_widget.mapFrom(w, point) if target_widget is not w else point)
    if not entry:return None
    kind = entry.get('kind')
    if kind == 'event':
        e = entry.get('event') or {}
        return Target('event', short(entry.get('line') or log_qt.event_line(e), 64), 'event · ' + stamp(e.get('at')), ident=entry.get('id'), data=entry, surface='log', owner=view)
    if kind in ('connection', 'packet'):
        return Target(kind, network_label(entry), network_noun(entry), data=entry, surface='log', owner=view)
    return None


def network_label(entry):
    """A connection or packet named for the menu's top: who talks to whom ("firefox → 93.184.216.34:443"; a packet: its source and
    destination), the rest in its noun."""
    from .log_qt import address
    if entry.get('kind') == 'packet':
        return short('%s → %s' % (address(entry.get('src'), entry.get('sport')), address(entry.get('dst'), entry.get('dport'))), 64)
    near = known_process(entry) or address(entry.get('local'), entry.get('lport'))
    return short('%s → %s' % (near, far_address(entry)), 64)


def network_noun(entry):
    words = ['network connection' if entry.get('kind') == 'connection' else 'packet', str(entry.get('proto') or '').lower()]
    if entry.get('kind') == 'connection':words.append(str(entry.get('state') or '').lower().replace('_', ' '))
    elif entry.get('length') not in (None, ''):words.append('%s bytes' % entry['length'])
    return ' · '.join(w for w in words if w)


def find_activity(host, w, point):
    """Activity's timeline (its recent lines and the Timeline list): an event; its cabinet selection: the record."""
    panel = getattr(host, 'operations_panel', None)
    if panel is None:return None
    hook = getattr(panel, 'context_target', None)
    if hook is not None:
        found = hook(w, point)
        if found is not None:return found
    tail = getattr(getattr(host, 'ledger_bridge', None), 'tail', None)
    lists = [getattr(panel, 'recent', None), getattr(tail, 'list', None)]
    if w not in [x for x in lists if x is not None]:return None
    item = w.itemAt(w.viewport().mapFrom(w, point))
    event = item.data(Qt.UserRole) if item is not None else None
    if not isinstance(event, dict):return None
    from . import log_qt
    line = item.text()
    entry = dict(stream='events', kind='event', id=event.get('id'), line=log_qt.event_line(event), event=event)
    target = Target('event', short(line, 64), 'event · ' + stamp(event.get('at')), ident=event.get('id'), data=entry, surface='activity', owner=tail)
    target.extra['item'] = item;return target


def find_process_list(host, w, point):
    """The System menu's process list (desktop_header_qt.NicePopup): a Kernel job (its row's kind) or Agenda work by its row. The
    running list holds both the Kernel's running and pending jobs and the Agenda's running items, so the row's kind decides, never
    the list."""
    from .desktop_header_qt import NicePopup
    popup = w.parentWidget()
    while popup is not None and not isinstance(popup, NicePopup):popup = popup.parentWidget()
    if popup is None or w not in (popup.running, popup.queue):return None
    item = w.itemAt(w.viewport().mapFrom(w, point))
    ident = item.data(Qt.UserRole) if item is not None else None
    if not ident:return None
    data = popup._data or {}
    rows = list(data.get('now', [])) + list(data.get('next', []))
    row = next((r for r in rows if r.get('id') == ident), None)
    if row is None:return None
    w.setCurrentItem(item)
    if row.get('kind') == 'job':  # the job read again now: its state is the revision, its tool says what it allows
        found = job_target(host, ident, surface='process-list', owner=popup)
        if found is not None:return found
        from .operations import tool_words
        state = row.get('state', '');title = tool_words(row.get('title', ''), state) if row.get('title') else ident
        return Target('job', short(title, 60), 'job · ' + str(state).lower(), ident=ident, revision=state, data=row, surface='process-list', owner=popup)
    full = agenda_row(host, ident)  # the panel's snapshot leaves out programs and jobs: the Agenda's own row (agenda.view, a read) has them
    data = dict(row, **{key: full[key] for key in ('program', 'job') if full and full.get(key)})
    return Target('queued', short(row.get('title', ident), 60), 'Agenda work · ' + str(row.get('state', '')).lower(), ident=ident, revision=row.get('state'),
                  data=data, surface='process-list', owner=popup)


def agenda_row(host, ident):
    r = dispatch(host, 'agenda.view', {})
    if not r.get('ok'):return None
    return next((row for part in ('now', 'next', 'waiting', 'later', 'suggested') for row in (r['result'].get(part) or [])
                 if isinstance(row, dict) and row.get('id') == ident and row.get('kind') != 'job'), None)


def find_jobs(host, w, point):
    """The Engineering room's Jobs list (every job with its state, paused ones too): the job under the pointer, read again now."""
    from .engineering_tabs import EngineeringTab
    tab = w.parentWidget()
    while tab is not None and not isinstance(tab, EngineeringTab):tab = tab.parentWidget()
    if tab is None or w is not tab.jobs:return None
    item = w.itemAt(w.viewport().mapFrom(w, point))
    ident = item.data(0, Qt.UserRole) if item is not None else None
    if not ident:return None
    w.setCurrentItem(item)
    return job_target(host, ident, surface='jobs', owner=tab)


def find_field(host, w, point):
    """The Field: the sheet under the pointer (it becomes the selected one, as a click would make it), or an empty place of it."""
    if w.objectName() != 'GraphiteField' or not hasattr(w, 'field'):return None
    ident = w._hit(QPointF(point))
    if ident is None:
        return Target('empty', 'Field', 'an empty place of the Field', surface='field', owner=w, icon='explore')
    if ident != w.field.selected:
        w.field.select(ident);w._describe();w.update()
    obj = w.field.get(ident)
    from .field_model import KIND_TAG
    words = (obj.tag or KIND_TAG.get(obj.kind, obj.kind)).lower()
    icon = {'source': 'references', 'sheet': 'calculate', 'calculation': 'calculate', 'document': 'documents', 'finding': 'memory', 'question': 'memory',
            'interface': 'network', 'program': 'tools', 'endpoint': 'network', 'app': 'tools'}.get(obj.kind, 'window')
    return Target('field-sheet', obj.title, '%s · %s' % (words, obj.state) if obj.state else words, ident=obj.id, data={'object': obj}, surface='field', owner=w, icon=icon)


def find_workspace(host, w, point):
    """An empty place of the workspace (the walk reached the rooms' tabs or the central stack with nothing more particular under
    the pointer): the root of the owner's pipe menu, as on a Fluxbox desktop."""
    if w is not getattr(host, 'tabs', None) and w is not getattr(host, 'central_stack', None):return None
    tabs = getattr(host, 'tabs', None);room = ''
    try:
        if w is tabs and tabs.count():room = tabs.tabText(tabs.currentIndex()).replace('&', '')
    except RuntimeError:room = ''
    return Target('empty', room or 'Workspace', 'an empty place', surface='workspace', owner=w, icon='explore')


FINDERS = (find_document, find_files, find_finder, find_cabinet, find_machine, find_settings, find_library, find_log, find_activity,
           find_process_list, find_jobs, find_today, find_field, find_workspace)


def owns_menu(w):
    """A widget with a menu of its own (a text field, a slider, a list that keeps its chain menu): the walk stops there."""
    if isinstance(w, (QLineEdit, QAbstractSpinBox, QComboBox, QAbstractSlider, QTextEdit, QPlainTextEdit)):return True
    if isinstance(w, QLabel) and w.textInteractionFlags() & (Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse):return True  # its Copy and Copy link
    return w.contextMenuPolicy() in (Qt.CustomContextMenu, Qt.ActionsContextMenu) and not w.property('graphiteContext')


def target_at(host, widget, point):
    """The target under `point` (in `widget`'s coordinates): the finders asked for the widget and then its parents, up to the window,
    stopping at a widget with a menu of its own."""
    w = widget;p = QPoint(point)
    from .command_context import find as find_command
    while w is not None:
        for finder in (find_command,) + FINDERS:
            try:found = finder(host, w, p)
            except RuntimeError:found = None
            if found is not None:
                found.widget = widget;found.where = widget.mapToGlobal(point);return found
        if owns_menu(w) or w.isWindow():return None
        parent = w.parentWidget()
        if parent is None:return None
        p = w.mapToParent(p);w = parent
    return None


# -- the menu -----------------------------------------------------------------------------------------------------------------------

def _extra_paths(key):
    """(strokes, fills) on the 18-unit grid for the icons programs_qt does not draw (the same line weight and grid)."""
    strokes, fills = [], []
    def path(*points, close=False):
        p = QPainterPath(QPointF(*points[0]))
        for pt in points[1:]:p.lineTo(QPointF(*pt))
        if close:p.closeSubpath()
        strokes.append(p);return p
    def rect(x, y, w, h, r=1.4, fill=False):
        p = QPainterPath();p.addRoundedRect(QRectF(x, y, w, h), r, r);(fills if fill else strokes).append(p);return p
    def circle(x, y, r, fill=False):
        p = QPainterPath();p.addEllipse(QPointF(x, y), r, r);(fills if fill else strokes).append(p);return p
    def curve(start, *segments):
        p = QPainterPath(QPointF(*start))
        for c, e in segments:p.quadTo(QPointF(*c), QPointF(*e))
        strokes.append(p);return p
    if key == 'passage':  # lines of words, one washed
        path((3, 4.5), (15, 4.5));rect(2.5, 7, 13, 4, 0.8);path((3, 13.5), (11, 13.5))
    elif key == 'bold':  # a B
        p = QPainterPath(QPointF(5, 3));p.lineTo(10, 3);p.quadTo(13.5, 3, 13.5, 6);p.quadTo(13.5, 9, 10, 9);p.lineTo(5, 9);p.closeSubpath();strokes.append(p)
        p = QPainterPath(QPointF(5, 9));p.lineTo(10.5, 9);p.quadTo(14.5, 9, 14.5, 12);p.quadTo(14.5, 15, 10.5, 15);p.lineTo(5, 15);p.closeSubpath();strokes.append(p)
    elif key == 'notes':  # a note with a folded corner
        path((3, 3), (15, 3), (15, 11), (11, 15), (3, 15), close=True);path((11, 15), (11, 11), (15, 11));path((6, 7), (12, 7))
    elif key == 'line':  # the writing line: a prompt and its line
        path((3.5, 5.5), (7.5, 9), (3.5, 12.5));path((9.5, 12.5), (15, 12.5))
    elif key == 'run':  # play
        path((5.5, 3.5), (14.5, 9), (5.5, 14.5), close=True)
    elif key == 'pause':  # two bars
        rect(4.5, 3.5, 3, 11, 0.6);rect(10.5, 3.5, 3, 11, 0.6)
    elif key == 'compare':  # two pages side by side
        rect(2.5, 3, 6, 12, 0.8);rect(9.5, 3, 6, 12, 0.8);path((4.5, 7), (6.5, 7));path((11.5, 7), (13.5, 7));path((4.5, 10), (6.5, 10));path((11.5, 10.5), (13.5, 10.5))
    elif key == 'extract':  # an arrow out of a tray
        path((3, 8), (3, 15), (15, 15), (15, 8));path((9, 12), (9, 2.5));path((6, 5.5), (9, 2.5), (12, 5.5))
    elif key == 'copy':  # two sheets
        rect(6, 6, 9, 9.5, 1);path((3, 12), (3, 3), (11.5, 3))
    elif key == 'trash':  # a can
        path((3.5, 5), (14.5, 5));path((7, 5), (7, 3), (11, 3), (11, 5));path((5, 5), (6, 15.5), (12, 15.5), (13, 5));path((8, 8), (8, 13));path((10, 8), (10, 13))
    elif key == 'view':  # an eye
        curve((2, 9), ((9, 2), (16, 9)));curve((2, 9), ((9, 16), (16, 9)));circle(9, 9, 2.2)
    elif key == 'network':  # three nodes linked
        circle(4.5, 13, 2);circle(13.5, 13, 2);circle(9, 4.5, 2);path((5.5, 11.3), (8, 6.2));path((12.5, 11.3), (10, 6.2));path((6.5, 13), (11.5, 13))
    elif key == 'packet':  # an envelope
        rect(2.5, 4.5, 13, 9, 1);path((2.8, 5), (9, 10), (15.2, 5))
    elif key == 'event':  # a moment on a line
        path((2.5, 9), (15.5, 9));circle(9, 9, 2.6, True);path((9, 3), (9, 5));path((9, 13), (9, 15))
    elif key == 'new':  # a plus
        path((9, 3.5), (9, 14.5));path((3.5, 9), (14.5, 9))
    elif key == 'rename':  # an I-beam on a line
        path((9, 3), (9, 13));path((6.5, 3), (11.5, 3));path((6.5, 13), (11.5, 13));path((2.5, 15.5), (15.5, 15.5))
    elif key == 'job':  # a gear
        circle(9, 9, 3);import math
        for k in range(8):
            a = k * math.pi / 4;path((9 + 4.6 * math.cos(a), 9 + 4.6 * math.sin(a)), (9 + 6.6 * math.cos(a), 9 + 6.6 * math.sin(a)))
    elif key == 'chain':  # two links
        rect(2.5, 6.5, 7.5, 5, 2.5);rect(8, 6.5, 7.5, 5, 2.5)
    else:return None
    return strokes, fills


EXTRA = ('passage', 'bold', 'notes', 'line', 'run', 'pause', 'compare', 'extract', 'copy', 'trash', 'view', 'network', 'packet', 'event', 'new', 'rename', 'job', 'chain')


def paint_icon(p, rect, key, colour):
    """One small graphite icon: programs_qt's set, with this menu's EXTRA ones in the same grid and line weight; none for ''."""
    if not key:return
    if key not in EXTRA:return programs_qt.paint_icon(p, rect, key, colour)
    import math
    strokes, fills = _extra_paths(key);s = min(rect.width(), rect.height()) / 18.0
    k = s * (math.sqrt(abs(p.deviceTransform().determinant())) or 1.0)
    p.save();p.setRenderHint(QPainter.Antialiasing);p.translate(rect.x() + (rect.width() - 18 * s) / 2, rect.y() + (rect.height() - 18 * s) / 2);p.scale(s, s)
    p.setPen(QPen(QColor(colour), max(1.5, 1.0 / k if k else 1.5), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin));p.setBrush(Qt.NoBrush)
    for path in strokes:p.drawPath(path)
    p.setPen(Qt.NoPen);p.setBrush(QColor(colour))
    for path in fills:p.drawPath(path)
    p.restore()


class Heading(QWidget):
    """The menu's top: the target named before you act (its icon, its readable name in print, what it is at the right in quiet
    print), one row's height, never focused."""
    def __init__(self, menu, target):
        super().__init__(menu.page);self.menu = menu;self.target = target;self.setFocusPolicy(Qt.NoFocus)
        label, noun = target.heading();self.label = label;self.noun = noun
        self.setAccessibleName('For: %s (%s)' % (label, noun));self.setToolTip('%s · %s' % (label, noun))

    def m(self):return self.menu.m

    def word_font(self):
        from PySide6.QtGui import QFont
        f = programs_qt.word_font(self.m());f.setWeight(QFont.DemiBold);return f

    def need(self):
        import math
        m = self.m()
        return math.ceil(2 * m.pad + m.icon_col + QFontMetricsF(self.word_font()).horizontalAdvance(self.label) + m.caption_gap +
                         QFontMetricsF(programs_qt.caption_font(m)).horizontalAdvance(self.noun))

    def sizeHint(self):return QSize(self.need(), self.m().row)

    def minimumSizeHint(self):return QSize(0, self.m().row)

    def icon_rect(self):
        m = self.m();return QRectF(m.pad, (self.height() - m.icon) / 2.0, m.icon, m.icon)

    def paintEvent(self, event):
        from .shell2 import QUIET, TEXT
        m = self.m();p = QPainter(self);p.setRenderHint(QPainter.TextAntialiasing)
        paint_icon(p, self.icon_rect(), self.target.icon, QColor(TEXT))
        from PySide6.QtGui import QFontMetrics
        cap_font = programs_qt.caption_font(m);font = self.word_font()
        x = m.pad + m.icon_col;avail = self.width() - x - m.pad
        label_w = QFontMetricsF(font).horizontalAdvance(self.label);cap_w = QFontMetricsF(cap_font).horizontalAdvance(self.noun) if self.noun else 0
        gap = m.caption_gap if self.noun else 0
        if label_w + gap + cap_w <= avail + 0.5:label_room, cap_room = label_w + 1, cap_w  # both whole (the menu is as wide as they need)
        else:  # a narrow window: what it is gives way first, the target's own name keeps most of the room
            cap_room = max(min(cap_w, 64.0), avail - gap - label_w);label_room = max(20.0, avail - gap - cap_room)
        def fitted(text, f, width, mode, whole):  # whole when it fits by the float metrics (the int ones round each glyph up)
            return text if whole <= width + 0.5 else QFontMetrics(f).elidedText(text, mode, int(width))
        p.setFont(font);p.setPen(QColor(TEXT))
        p.drawText(QRectF(x, 0, label_room + 2, self.height()), Qt.AlignLeft | Qt.AlignVCenter, fitted(self.label, font, label_room, Qt.ElideMiddle, label_w))
        if self.noun:
            p.setFont(cap_font);p.setPen(QColor(QUIET))
            p.drawText(QRectF(self.width() - m.pad - cap_room - 2, 0, cap_room + 2, self.height()), Qt.AlignRight | Qt.AlignVCenter,
                       fitted(self.noun, cap_font, cap_room, Qt.ElideRight, cap_w))
        p.end()

    def shown_label(self):
        """The target's name as the heading draws it at its width (whole unless the window is too narrow)."""
        from PySide6.QtGui import QFontMetrics
        m = self.m();font = self.word_font();avail = self.width() - m.pad - m.icon_col - m.pad
        cap_w = QFontMetricsF(programs_qt.caption_font(m)).horizontalAdvance(self.noun) if self.noun else 0
        label_w = QFontMetricsF(font).horizontalAdvance(self.label);gap = m.caption_gap if self.noun else 0
        if label_w + gap + cap_w <= avail + 0.5:return self.label
        cap_room = max(min(cap_w, 64.0), avail - gap - label_w);room = max(20.0, avail - gap - cap_room)
        return self.label if label_w <= room + 0.5 else QFontMetrics(font).elidedText(self.label, Qt.ElideMiddle, int(room))

    def shown_noun(self):
        """What it is, as the heading draws it (whole unless the window is too narrow)."""
        from PySide6.QtGui import QFontMetrics
        m = self.m();font = self.word_font();cap_font = programs_qt.caption_font(m);avail = self.width() - m.pad - m.icon_col - m.pad
        cap_w = QFontMetricsF(cap_font).horizontalAdvance(self.noun) if self.noun else 0
        label_w = QFontMetricsF(font).horizontalAdvance(self.label);gap = m.caption_gap if self.noun else 0
        if label_w + gap + cap_w <= avail + 0.5:return self.noun
        cap_room = max(min(cap_w, 64.0), avail - gap - label_w)
        return self.noun if cap_w <= cap_room + 0.5 else QFontMetrics(cap_font).elidedText(self.noun, Qt.ElideRight, int(cap_room))


class ContextRow(MenuRow):
    """One entry: the desk's menu row (programs_qt.MenuRow: the icon column, the word, a quiet caption), with this menu's icons, a
    › for a submenu, the short pencil-yellow mark under an active choice, and an unavailable row's reason as its tooltip."""
    def __init__(self, menu, entry):
        caption = entry.caption if entry.enabled else 'unavailable'
        if entry.submenu or entry.qmenu:caption = '›'
        super().__init__(menu, entry.label, entry.icon, caption, False, callback=None);self.entry = entry
        self.setEnabled(entry.enabled);self.setToolTip(entry.tooltip());self.describe()
        if entry.checked:self.setAccessibleDescription('Current choice · ' + self.accessibleDescription())
        self.hover = QTimer(self, singleShot=True, interval=HOVER_MS);self.hover.timeout.connect(lambda:self.menu.open_child(self, keyboard=False))

    def sub(self):return bool(self.entry.submenu or self.entry.qmenu)

    def choose(self):
        if not self.isEnabled():return
        if self.sub():self.menu.open_child(self, keyboard=self.hasFocus() and not self.underMouse());return
        self.menu.chosen(self);QTimer.singleShot(0, lambda:self.menu.perform(self.entry))

    def enterEvent(self, event):
        super().enterEvent(event)
        if self.sub() and self.isEnabled():self.hover.start()
        elif self.menu.child is not None:QTimer.singleShot(HOVER_MS, self.menu.close_child_if_away)

    def leaveEvent(self, event):
        self.hover.stop();super().leaveEvent(event)

    def paintEvent(self, event):
        from .shell2 import AMBER_EDGE, AMBER_SOFT, QUIET, TEXT
        m = self.m();p = QPainter(self);p.setRenderHint(QPainter.TextAntialiasing)
        if self.active() or (self.sub() and self.menu.child is not None and self.menu.child_row is self):p.fillRect(self.rect(), QColor(AMBER_SOFT))
        ink = QColor(TEXT if self.isEnabled() else QUIET)
        paint_icon(p, self.icon_rect(), self.icon_key, ink)
        p.setFont(self.font());p.setPen(ink);x = self.word_x()
        p.drawText(QRectF(x, 0, self.width() - x - m.pad, self.height()), Qt.AlignLeft | Qt.AlignVCenter, self.word)
        if self.entry.checked:  # the active choice: a short pencil-yellow mark under the word (the desk's sign for it)
            width = min(self.fontMetrics().horizontalAdvance(self.word), max(12, round(m.px * 1.6)))
            base = (self.height() + self.fontMetrics().ascent() - self.fontMetrics().descent()) // 2
            p.fillRect(QRect(int(x), int(min(self.height() - 3, base + 3)), int(width), 2), QColor(AMBER_EDGE))
        if self.caption:
            p.setFont(programs_qt.caption_font(m, self.script));p.setPen(QColor(QUIET));p.drawText(self.caption_rect(), Qt.AlignRight | Qt.AlignVCenter, self.caption)
        p.end()


class ContextMenu(DeskMenu):
    """The right-click menu: the desk's menu (one row height, one icon column and margin with the programs list and the System
    menu), the target named at its top, the sections with a hairline between them, the menu's small caption in the script at its
    foot; opened at the pointer (or, from the keyboard, at the focused place), submenus cascading beside their row."""
    def __init__(self, host, target, entries, parent_menu=None, name='ContextMenu'):
        super().__init__(host, None, 'pointer', name)
        order = {s: i for i, s in enumerate(SECTIONS)}
        self.target = target;self.entries = sorted(entries, key=lambda e:order.get(e.section, len(SECTIONS)));self.parent_menu = parent_menu;self.child = None;self.child_row = None;self.qchild = None
        self.setMouseTracking(True);self.rows_by_key = {}
        self.setAccessibleName(('Right-click menu: ' if parent_menu is None else 'Submenu: ') + (target.label if target is not None else ''))
        if parent_menu is None and target is not None:
            self.heading = Heading(self, target);self.box.addWidget(self.heading);self.box.addWidget(Rule(self))
        else:self.heading = None
        section = None
        for entry in self.entries:
            if section is not None and entry.section != section:self.box.addWidget(Rule(self))
            section = entry.section;row = ContextRow(self, entry);self.rows_by_key[entry.key] = row;self.box.addWidget(row)
        if not self.entries:
            row = ContextRow(self, Entry('none', 'Nothing to do here', 'open', enabled=False, reason='No provider offers an action for this place.'))
            self.box.addWidget(row)
        if parent_menu is None:
            self.caption = programs_qt.Caption(self, CAPTION);self.box.addWidget(self.caption)
        else:self.caption = None
        if hasattr(self, 'end_rows'):self.end_rows()  # the desk menu's bottom margin goes last (programs_qt.DeskMenu)

    # readers and checks
    def words(self):
        """The rows' words top to bottom, '—' for a hairline between sections (the heading's own hairline left out)."""
        out = []
        for i in range(self.box.count()):
            w = self.box.itemAt(i).widget()
            if isinstance(w, Rule):out.append('—')
            elif isinstance(w, ContextRow):out.append(w.word)
        return out[1:] if self.heading is not None and out[:1] == ['—'] else out

    def keys(self):return [e.key for e in self.entries]

    def row(self, key):return self.rows_by_key.get(key)

    def root(self):
        menu = self
        while menu.parent_menu is not None:menu = menu.parent_menu
        return menu

    def need_width(self):
        import math
        m = self.m;need = 0
        for i in range(self.box.count()):
            w = self.box.itemAt(i).widget()
            if isinstance(w, Heading):need = max(need, w.need())
            elif isinstance(w, ContextRow):need = max(need, w.sizeHint().width())
        outer = self.layout().contentsMargins() if self.layout() is not None else None
        chrome = 2 * max(1, self.frameWidth()) + ((outer.left() + outer.right()) if outer is not None else 2)  # the hairline and the frame's room
        return math.ceil(need) + chrome

    def width_rule(self):
        """One width rule with the launch menus: the panes' content column, or the widest row when that is more, never more than
        the window less an inset each side."""
        base = programs_qt.column(self.host) if self.parent_menu is None else 0
        width = max(base, self.need_width(), 160)
        host_w = self.host.width() if hasattr(self.host, 'width') else width
        inset = getattr(getattr(self.host, 'desk', None), 'inset', 16)
        return int(min(width, max(200, host_w - 2 * inset)))

    def sizeHint(self):
        """The whole height at this menu's own width (DeskMenu's is the launch menus' width)."""
        width = (self.width() if self.width() > 0 and self.minimumWidth() == self.maximumWidth() else self.width_rule()) - 2;self.box.activate()
        tall = self.box.heightForWidth(width) if self.box.hasHeightForWidth() else -1
        return QSize(width + 2, max(tall, self.page.sizeHint().height(), self.box.minimumSize().height()) + 2)

    def bounds(self):
        if hasattr(self.host, 'mapToGlobal') and self.host.isVisible():
            return QRect(self.host.mapToGlobal(QPoint(0, 0)), self.host.size())
        screen = QGuiApplication.screenAt(QPoint(0, 0)) or QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen is not None else QRect(0, 0, 1920, 1200)

    def open_at(self, point, keyboard=False, beside=None):
        """Show the menu with its top-left at `point` (global), opening up or to the left when it would leave the window; a submenu
        beside its row (`beside`: the row's global rect), on the right when it fits, else on the left."""
        self.return_focus = QApplication.focusWidget() if self.parent_menu is None else beside_row(self)
        self.keyboard = bool(keyboard);self.restyle();self.restyle_margins()
        width = self.width_rule();self.setFixedWidth(width);self.box.activate()
        area = self.bounds();height = min(self.sizeHint().height(), area.height())
        if beside is not None:
            x = beside.right() + 1 if beside.right() + 1 + width <= area.right() + 1 else beside.left() - width
            y = beside.top() - self.m.margin - 1
        else:
            x = point.x() if point.x() + width <= area.right() + 1 else point.x() - width
            y = point.y() if point.y() + height <= area.bottom() + 1 else point.y() - height
        rect = QRect(max(area.left(), x), max(area.top(), min(y, area.bottom() + 1 - height)), width, height)
        self.setFixedHeight(rect.height());self.setGeometry(rect)
        self.show();self.raise_();self.activateWindow()
        need = self.measured_height()
        if need != self.height():
            height = min(need, area.height());rect.setHeight(height)
            if rect.bottom() > area.bottom():rect.moveBottom(area.bottom())
            if rect.top() < area.top():rect.moveTop(area.top())
            self.setFixedHeight(height);self.setGeometry(rect)
        self.scroll.verticalScrollBar().setValue(0)
        first = self.first() if keyboard else None
        if first is not None:first.setFocus(Qt.TabFocusReason)
        else:self.setFocus(Qt.PopupFocusReason)
        return rect

    # submenus
    def open_child(self, row, keyboard=False):
        if self.child is not None and self.child_row is row and self.child.isVisible():
            if keyboard:
                first = self.child.first()
                if first is not None:first.setFocus(Qt.TabFocusReason)
            return self.child
        self.close_child()
        at = QRect(row.mapToGlobal(QPoint(0, 0)), row.size())
        entry = row.entry
        if entry.qmenu is not None:
            try:menu = entry.qmenu()
            except Exception as exc:say(self.host, 'Not available: %s' % exc);return None
            self.qchild = menu;self.child_row = row;row.update()
            menu.aboutToHide.connect(lambda:None if self.frameGeometry().contains(QCursor.pos()) else self.root().close_menu(restore=False))
            menu.popup(QPoint(at.right() + 1, at.top() - self.m.margin))
            return menu
        try:entries = entry.submenu() if callable(entry.submenu) else list(entry.submenu or [])
        except Exception as exc:
            entries = [Entry('problem', 'Unavailable', 'capability', enabled=False, reason=str(exc))]
        child = ContextMenu(self.host, self.target, entries, parent_menu=self, name='ContextSubmenu')
        self.child = child;self.child_row = row;row.update()
        child.open_at(at.topRight(), keyboard=keyboard, beside=at)
        return child

    def close_child(self):
        if self.child is not None:
            child, self.child = self.child, None
            try:child.close_child();child.hide();child.deleteLater()
            except RuntimeError:pass
        if self.qchild is not None:
            q, self.qchild = self.qchild, None
            try:q.hide()
            except RuntimeError:pass
        row, self.child_row = self.child_row, None
        if row is not None:
            try:row.update()
            except RuntimeError:pass

    def close_child_if_away(self):
        if self.child is None:return
        under = QApplication.widgetAt(QCursor.pos())
        if under is not None and (under.window() is self.child or (isinstance(under, ContextRow) and under is self.child_row)):return
        self.close_child()

    # choosing
    def chosen(self, row):
        """A row was chosen: the whole menu closes first (what opens is what you see)."""
        self.root().close_menu(restore=False)

    def perform(self, entry):
        return perform(self.host, self.target, entry)

    def close_menu(self, restore=True):
        self.close_child()
        if self.isVisible():self.hide()
        if self.parent_menu is not None:
            if restore and self.child_row is None:
                row = beside_row(self)
                if row is not None:row.setFocus(Qt.PopupFocusReason)
            return
        target = self.return_focus if restore else None
        if target is not None:
            try:target.setFocus(Qt.PopupFocusReason)
            except RuntimeError:pass

    def hideEvent(self, event):
        self.close_child();super().hideEvent(event)

    def eventFilter(self, obj, event):
        if not self.isVisible() or not isinstance(obj, QWidget) or (obj is not self and obj.window() is not self):return False
        if event.type() == QEvent.KeyPress:
            focus = QApplication.focusWidget();key = event.key()
            if key in (Qt.Key_Right,) and isinstance(focus, ContextRow) and focus.sub() and focus.isEnabled():self.open_child(focus, keyboard=True);return True
            if key in (Qt.Key_Left,) and self.parent_menu is not None:
                parent = self.parent_menu;row = parent.child_row;parent.close_child()
                if row is not None:row.setFocus(Qt.TabFocusReason)
                return True
            if key == Qt.Key_Escape and self.parent_menu is not None:
                parent = self.parent_menu;row = parent.child_row;parent.close_child()
                if row is not None:row.setFocus(Qt.TabFocusReason)
                return True
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event):
        """While a submenu is open the pointer's moves come to it; back over its parent, the submenu gives way."""
        gp = event.globalPosition().toPoint()
        if not self.rect().contains(self.mapFromGlobal(gp)) and self.parent_menu is not None:
            parent = self.parent_menu
            if parent.rect().contains(parent.mapFromGlobal(gp)):
                row = parent.childAt(parent.mapFromGlobal(gp))
                while row is not None and not isinstance(row, ContextRow):row = row.parentWidget()
                if row is not parent.child_row:parent.close_child()
                return
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """A press outside: on a parent menu, that menu takes it (its row is chosen); anywhere else every menu closes."""
        gp = event.globalPosition().toPoint()
        if self.rect().contains(self.mapFromGlobal(gp)):return super().mousePressEvent(event)
        menu = self.parent_menu
        while menu is not None:
            if menu.rect().contains(menu.mapFromGlobal(gp)):
                row = menu.childAt(menu.mapFromGlobal(gp))
                while row is not None and not isinstance(row, ContextRow):row = row.parentWidget()
                menu.close_child()
                if row is not None and row.isEnabled():row.click()
                return
            menu = menu.parent_menu
        self.root().close_menu(restore=True)


def beside_row(menu):
    parent = menu.parent_menu
    return parent.child_row if parent is not None else None


def perform(host, target, entry):
    """Run one entry; a refusal or a failure is said in the status line, never raised into the event loop. Readers find the outcome
    in host._context_last."""
    outcome = {'key': entry.key, 'label': entry.label, 'ok': True, 'words': None}
    try:
        if entry.run is not None:outcome['result'] = entry.run()
    except Refused as exc:outcome.update(ok=False, words=str(exc));say(host, str(exc), 12000)
    except Exception as exc:outcome.update(ok=False, words='Not done: %s' % exc);say(host, outcome['words'], 12000)
    if outcome['ok'] and outcome['words'] is None:outcome['words'] = getattr(host, '_context_said', None)
    host._context_last = outcome
    return outcome


def build(host, target):
    """The menu for a target, not yet shown (readers and checks look at it before it opens)."""
    previous = getattr(host, 'context_menu', None)
    if previous is not None:
        try:previous.close_menu(restore=False);previous.deleteLater()
        except RuntimeError:pass
    menu = ContextMenu(host, target, entries_for(host, target));host.context_menu = menu
    return menu


def open_for(host, target, global_point, keyboard=False):
    """Build and show the menu for a target at a global point."""
    menu = build(host, target);menu.open_at(global_point, keyboard=keyboard);return menu


def open_at(host, widget, point, keyboard=False):
    """From a right-click hook (customContextMenuRequested): the target under `point` in `widget`'s coordinates, its menu at the
    pointer. None when no finder knows the place."""
    target = target_at(host, widget, point)
    if target is None:return None
    return open_for(host, target, widget.mapToGlobal(point), keyboard)


def focus_point(widget):
    """Where the keyboard's menu opens for a widget: the current item's or the caret's place (in the coordinates of the widget it
    returns: an item view's or a text editor's viewport), else its middle."""
    if isinstance(widget, QMenu) and widget.activeAction() is not None:
        return widget, widget.actionGeometry(widget.activeAction()).center()
    if isinstance(widget, QAbstractItemView):
        index = widget.currentIndex()
        rect = widget.visualRect(index) if index.isValid() else QRect()
        if rect.isValid() and widget.viewport().rect().intersects(rect):return widget.viewport(), QPoint(rect.left() + min(24, rect.width() // 2), rect.center().y())
        return widget.viewport(), QPoint(12, 12)
    if isinstance(widget, (QTextEdit, QPlainTextEdit)):
        rect = widget.cursorRect();return widget.viewport(), QPoint(rect.right(), rect.bottom())
    if widget.objectName() == 'GraphiteField' and hasattr(widget, 'selected_point'):      # the Field: the selected sheet
        return widget, widget.selected_point()
    return widget, widget.rect().center()


def open_at_focus(host):
    """The Menu key and Shift+F10: the menu for the keyboard focus (the current item, the caret's passage), its first row under focus;
    a text field keeps its own menu; with nothing known there, the workspace's empty-place menu."""
    focus = QApplication.focusWidget()
    if focus is None or not belongs(host, focus):focus = getattr(getattr(host, 'tabs', None), 'currentWidget', lambda:None)() or host
    widget, point = focus_point(focus)
    target = target_at(host, widget, point)
    if target is None:
        if owns_menu(focus) and focus is not host:
            QApplication.sendEvent(focus, QContextMenuEvent(QContextMenuEvent.Keyboard, point if widget is focus else focus.mapFrom(widget, point),
                                                            widget.mapToGlobal(point)))
            return None
        target = Target('empty', 'Here', 'an empty place', surface='workspace', icon='explore');target.widget = widget;target.where = widget.mapToGlobal(point)
    return open_for(host, target, widget.mapToGlobal(point), keyboard=True)


def belongs(host, widget):
    """A widget of this window, or of one of its popups (the System menu and its list)."""
    w = widget.window() if widget is not None else None
    while w is not None:
        if w is host:return True
        w = w.parentWidget()
    return False


class Router(QObject):
    """The one event filter: a ContextMenu event for a widget of this window (or its popups) opens this menu when a finder knows the
    place; anything else keeps its own menu."""
    def __init__(self, host):
        super().__init__(host);self.host = host;self.enabled = True;self.secondary_press = False;self.secondary_until = 0.0;self.secondary_point = None

    def eventFilter(self, obj, event):
        if not self.enabled or not isinstance(obj, QWidget):return False
        # QMenu can activate an item on a right-button release. Claim secondary
        # presses on command objects before QMenu sees them; left clicks are untouched.
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.RightButton and self.secondary_press:
            self.secondary_press = False;event.accept();return True
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.RightButton:
            if not belongs(self.host,obj):return False
            target = target_at(self.host,obj,event.position().toPoint())
            if target is None or target.kind not in ('program','command'):return False
            self.secondary_press = True;self.secondary_until = time.monotonic() + .5;self.secondary_point = event.globalPosition().toPoint()
            open_for(self.host,target,event.globalPosition().toPoint());event.accept();return True
        if event.type() != QEvent.ContextMenu:return False
        if event.reason() != QContextMenuEvent.Keyboard and time.monotonic() < self.secondary_until and event.globalPos() == self.secondary_point:
            event.accept();return True
        try:
            if not belongs(self.host, obj):return False
            target = target_at(self.host, obj, event.pos())
        except RuntimeError:return False
        if target is None:return False
        open_for(self.host, target, event.globalPos(), keyboard=event.reason() == QContextMenuEvent.Keyboard)
        event.accept();return True


def install(host):
    """The router on the application and the Menu key and Shift+F10 on the window (chain_menu.install calls this)."""
    if getattr(host, 'context_router', None) is not None:return host.context_router
    router = Router(host);host.context_router = router
    app = QApplication.instance()
    if app is not None:app.installEventFilter(router)
    keys = []
    for sequence in (QKeySequence(Qt.Key_Menu), QKeySequence('Shift+F10')):
        shortcut = QShortcut(sequence, host);shortcut.setContext(Qt.WindowShortcut);shortcut.activated.connect(lambda:open_at_focus(host));keys.append(shortcut)
    host.context_keys = keys
    return router


# -- what the old menus held, and where each entry is now (nothing lost) ----------------------------------------------------------------
# (old menu, its words) -> (the target kind that offers it now, the entry's key; 'a/b' is the entry b in a's submenu). Tests build
# each new menu, open its submenus and find every key, and read every old builder's words (submenus too) back from the new menus.
FOLDED = (
    ('Files: a file', 'Open', 'file', 'open'), ('Files: a file', 'Open pill…', 'file', 'open'),
    ('Files: a file', 'Explain this file', 'file', 'explain'), ('Files: a file', named('Ask Stacy about this…'), 'file', 'ask'),
    ('Files: a file', 'Investigate…', 'file', 'investigate'), ('Files: a file', 'Add to the Agenda…', 'file', 'agenda'),
    ('Files: a working copy', named('Ask Stacy to work on this…'), 'file', 'copy:slate'), ('Files: a working copy', 'Review changes to the original…', 'file', 'copy:review'),
    ('Files: a working copy', 'Show the original', 'file', 'copy:original'), ('Files: a working copy', 'Discard this draft…', 'file', 'copy:discard'),
    ('Files: a folder copy', 'Look inside, confined…', 'folder', 'copy:look'), ('Files: a folder copy', 'Run a command here, confined…', 'folder', 'copy:run'),
    ('Files: a pill folder copy', 'Return as a pill…', 'folder', 'copy:pill'), ('Files: a pill folder copy', 'Review the changes…', 'folder', 'copy:review'),
    ('Files: a pill folder copy', 'Discard this draft…', 'folder', 'copy:discard'), ('Files: a folder copy', 'Review changes to the original…', 'folder', 'copy:review'),
    ('Files: a folder copy', 'Show the original', 'folder', 'copy:original'), ('Files: a folder copy', 'Discard this draft…', 'folder', 'copy:discard'),
    ('Files: a file', "Open with this computer's app", 'file', 'open:outside'), ('Files: a file', 'Rename…', 'file', 'rename'),
    ('Files: a file', 'Versions…', 'file', 'versions'), ('Files: a file', 'Compare with…', 'file', 'compare:with'),
    ('Files: a file', 'Compare with a version…', 'file', 'compare:version'), ('Files: a file', 'Export…', 'file', 'export'),
    ('Files: a selection', 'Copy to…', 'file', 'copy:to'), ('Files: a selection', 'Move to…', 'file', 'move:to'), ('Files: a selection', 'Move to Trash', 'file', 'trash'),
    ('Files: an empty place', 'New folder…', 'empty:files', 'new:folder'), ('Files: an empty place', 'Import…', 'empty:files', 'import'),
    ('Files: an empty place', 'Work on a copy of a file…', 'empty:files', 'work:copy'), ('Files: an empty place', 'chains ›', 'empty:files', 'root'),
    ('Files: an empty place › chains', 'Inquiries…', 'empty:files', 'root/inquiries'),
    ('Files: an empty place › chains', 'Algorithm & Theory Atlas…', 'empty:files', 'root/algorithms'),
    ('Files: an empty place › chains', 'Tool Atlas…', 'empty:files', 'root/atlas'), ('Files: an empty place › chains', 'your kept chains', 'empty:files', 'root/chains'),
    ('Files: an empty place › chains', 'start from ›', 'empty:files', 'root/start'), ('Files: an empty place › chains', 'writing line ›', 'empty:files', 'root/line'),
    ('Files: an empty place › chains › writing line', 'Shell', 'empty:files', 'root/line/line:shell'),
    ('Files: an empty place › chains', 'edit the Graphite menu…', 'empty:files', 'root/menu:edit'),
    ('Files: a smart folder', 'Rename…', 'smart', 'rename'), ('Files: a smart folder', 'Export…', 'smart', 'export'),
    ('Files: a file', 'the chain from @files: (the file\'s chain menu)', 'file', 'chain'),
    ('Finder: an entry', 'Open', 'finder', 'open'), ('Finder: an entry', 'Open in viewer', 'finder', 'open:viewer'), ('Finder: an entry', 'Show in Files', 'finder', 'show:files'),
    ('Finder: an entry', 'Copy path', 'finder', 'copy:path'), ('Finder: an entry', named('Ask Stacy about this file / folder'), 'finder', 'ask'),
    ('Finder: an entry', 'Change it in Files', 'finder', 'change:files'), ('Finder: an entry outside Files', 'Nothing changes here · Files keeps its own changes', 'finder-outside', 'change:none'),
    ('Cabinet: a record (cabinet_actions_qt.menu)', 'With <record> (the heading)', 'cabinet', 'heading'),
    ('Cabinet: a record', 'Read saved details', 'cabinet', 'cabinet:record'), ('Cabinet: a record', 'Write an idea here / Name a new project', 'cabinet', 'cabinet:write'),
    ('Cabinet: a record', 'the provider checks', 'cabinet', 'cabinet:check:*'), ('Cabinet: a record', 'Open <workspace>', 'cabinet', 'cabinet:workspace:*'),
    ('Cabinet: a record', 'Explore all capabilities', 'cabinet', 'cabinet:explore'),
    ('Library: a received file', 'Open', 'library', 'open'), ('Library: a received file', 'Keep a copy in Files', 'library', 'keep'),
    ('Today (root chain menu)', 'Inquiries…', 'empty:today', 'inquiries'), ('Today', 'Algorithm & Theory Atlas…', 'empty:today', 'algorithms'),
    ('Today', 'Tool Atlas…', 'empty:today', 'atlas'), ('Today', 'your kept chains', 'empty:today', 'chains'), ('Today', 'start from ›', 'empty:today', 'start'),
    ('Today', 'console › Log · Lines · Kernel · Find · Shell', 'empty:today', 'line'), ('Today', 'writing line ›', 'empty:today', 'line'),
    ('Today › writing line', 'Shell', 'empty:today', 'line/line:shell'), ('Today', 'edit the Graphite menu…', 'empty:today', 'menu:edit'),
    ('Document page (Qt\'s text menu)', 'Undo', 'passage', 'edit:undo'), ('Document page', 'Redo', 'passage', 'edit:redo'), ('Document page', 'Cut', 'passage', 'edit:cut'),
    ('Document page', 'Copy', 'passage', 'edit:copy'), ('Document page', 'Paste', 'passage', 'edit:paste'), ('Document page', 'Delete', 'passage', 'edit:delete'),
    ('Document page', 'Select All', 'passage', 'edit:all'),
    ('Activity\'s timeline (activation)', 'open the event', 'event:activity', 'open'),
)
