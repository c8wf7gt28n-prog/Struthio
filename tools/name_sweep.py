"""The name sweep: no word a person reads or hears on the desk says a name that is never shown.

Two names are held here (NEVER). The language's own name: on screen a pipeline is "a line" (0.8.0; until 0.8.4 this sweep
was kept outside the repository and run by hand at a release). And Stacy, the name the first look showed for the assistant
until 0.8.3: she is Kasandra in every look (workbench/assistant_identity.py; the owner, 19 November 2026: "Just kas.
Otherwise we have too many people").

  words_of(widget)       every word a widget carries: its text, tip, status tip, placeholder, accessible name and
                         description, window title; a combo's rows, a tab bar's titles and tips, and the rows and tips of
                         a tree or a list. Hidden or shown: a word that waits in a hidden widget is read when it shows.
  sweep(window, where)   every widget, every menu and every menu line of the program against NEVER
                         -> [{name, where, widget, kind, words}]
  walk(window, settle)   the places a sweep visits, reached by desk acts (workbench/desk_doers.run, door 'script'): the
                         start, Today, every menu across the head and the Apps list, the meters' cards, both panes in
                         each of their views, Files and its right-click, the Field in its three faces with a sheet
                         selected, its right-click and what is shown over the work, the writing line for each of its five
                         names with a line typed and a line refused, and her hand at each place of its dial with an act
                         of hers on its card. And the places no desk act reaches where the earlier name was last read
                         (0.8.4's review): a brain event, written as the program writes every one of them, in
                         Activity's timeline, in the listing of recorded commands, pinned in the Log and in Search's
                         timeline; Guide's About Graphite (a dialog that waits: shown here instead); her art plate of
                         the Rules menu opened in the viewer -> {found, places, words, named}
  in_code(root)          every sentence in the program's code that carries her earlier name and does not go through
                         assistant_identity.named() -> [(file, line, words)]

KEPT is what may still be read on purpose. History keeps the name it was written with (a stored agenda row, her trail),
and so does an identity shown as it is stored, always lowercase and joined by . : / - or _ (an operation, a settings key,
a schema). An event keeps its actor 'STACY' in the record. Decided in 0.8.4: words made for reading say her name for it
(a timeline's row, the Log's pinned line and its details, the listings of recorded events with a column for who acted:
workbench/tail_words.shown_origin), so "origin STACY" there is a fault; an event printed whole as it is stored (the JSON
in the tip of a row of Activity's timeline) keeps it, as it keeps its operation and its state, and RECORD sets exactly
that pair aside. CODE_KEPT is the same for the code: each entry says why its words are not a shown name.

  python3 tools/name_sweep.py           the code alone (no window is made): prints what in_code finds; exit 1 when any

The window is swept by tests_integrated/test_one_name.py, in both looks, on the bench seed the desk acts' tests use.
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# name -> (what must not be read, why). A word here is a whole word: 'stack' and 'Stacy' are not the language's name.
NEVER = {'language': (re.compile(r'\bstac\b', re.I), 'the language is never named on screen: a pipeline is "a line"'),
         'stacy': (re.compile(r'Stacy|STACY'), 'she is Kasandra in every look')}
KEPT = re.compile(r'\b[a-z0-9_]+(?:[.:/_-][a-z0-9_]+)+\b')      # an identity shown as it is stored
RECORD = re.compile(r'"origin": "STACY"')                        # her actor in an event printed whole, as it is stored
BRAIN_EVENT = 'name_sweep'      # the walk's own brain event: brain.name_sweep, state CHECKED
SHOWN_NAME = 'Kasandra'

# The code's words that carry the earlier name and are not a sentence a person reads as her name: (file, the words' start) -> why.
# An empty start is the whole file (the lineage grows by a release at its head, so its first words change).
CODE_KEPT = {
    ('workbench/assistant_identity.py', 'Stacy'): 'the one place that says what is shown for the name',
    ('workbench/assistant_identity.py', 'STACY'): 'the one place that says what is shown for the name',
    ('workbench/line_steps.py', 'Shell syntax and command substitution are not part of Stacy language'): 'a pattern: the parser\'s refusal is put in the window\'s words here',
    ('workbench/line_steps.py', r'\bStacy language\b'): 'a pattern: the parser\'s refusal is put in the window\'s words here',
    ('workbench/local_brain.py', 'STACY'): 'the activity actor, a record identifier; read as her name through tail_words.shown_origin',
    ('workbench/project_desk.py', 'List<StacyQueryRow>'): 'a result type in a stored plan, a record identifier',
    ('workbench/shell2.py', 'StacyHand'): 'an object name',
    ('workbench/stacy_presence.py', 'StacyReaction'): 'an object name',
    ('workbench/stacy_foundation.py', 'docs/STACY_'): 'file names of her foundation\'s documents',
    ('workbench/version.py', ''): 'the lineage: what each release was, in the words of its day',
    ('sdk/cli/arc1cli/typed_pipeline.py', 'Shell syntax and command substitution are not part of Stacy language'): 'the parser\'s own refusal; the window says it through line_steps.plain',
}
CODE_FOLDERS = ('workbench', 'sdk')


def words_of(widget):
    """Every word a widget carries, as (kind, words)."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QAbstractItemView, QComboBox, QHeaderView, QTabBar, QTabWidget, QTreeView
    out = []
    for get in ('text', 'toPlainText', 'toolTip', 'statusTip', 'placeholderText', 'accessibleName', 'accessibleDescription', 'windowTitle', 'title'):
        f = getattr(type(widget), get, None)      # the class's own reader: a page may keep a label under the same name
        if not callable(f):continue
        try:value = f(widget)
        except (TypeError, RuntimeError):continue
        if isinstance(value, str) and value:out.append((get, value))
    if isinstance(widget, QComboBox):out += [('row', widget.itemText(i)) for i in range(widget.count())]
    if isinstance(widget, (QTabBar, QTabWidget)):
        for i in range(widget.count()):out += [('tab', widget.tabText(i)), ('tab tip', widget.tabToolTip(i))]
    if isinstance(widget, QAbstractItemView) and not isinstance(widget, QHeaderView) and widget.model() is not None:
        model = widget.model();seen = [0];tree = isinstance(widget, QTreeView)
        try:columns = range(model.columnCount(widget.rootIndex()))
        except TypeError:columns = range(1)      # a list model keeps columnCount private: one column
        if tree:out += [('header', str(model.headerData(c, Qt.Horizontal) or '')) for c in columns]
        def rows(parent, depth):
            for r in range(model.rowCount(parent)):
                seen[0] += 1
                if seen[0] > 4000:return      # a long list says its names in its first rows
                for c in columns:
                    index = model.index(r, c, parent)
                    out.extend(('row' if role == Qt.DisplayRole else 'row tip', v) for role in (Qt.DisplayRole, Qt.ToolTipRole)
                               for v in (index.data(role),) if isinstance(v, str))
                first = model.index(r, 0, parent)
                if tree and depth < 6 and model.hasChildren(first):rows(first, depth + 1)
        rows(widget.rootIndex(), 0)
    return [(kind, words) for kind, words in out if words]


def named_in(words):
    """Which of NEVER these words say, an identity shown as it is stored set aside."""
    rest = KEPT.sub(' ', RECORD.sub(' ', words))
    return [name for name, (pattern, _) in NEVER.items() if pattern.search(rest)]


def sweep(window, where, found=None, read=None):
    """Read every widget of the program (the window's, and whatever stands beside it: a menu, a card, a page over the work)
    and every menu line. `found` gathers what names a NEVER; `read` gathers every word read, so that a caller can tell a
    sweep that found nothing from one that read nothing."""
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QApplication, QWidget
    found = [] if found is None else found
    seen = {(f['name'], f['widget'], f['kind'], f['words']) for f in found}
    def note(owner, kind, words):
        if read is not None:read.add(words)
        for name in named_in(words):
            row = (name, owner, kind, words[:200])
            if row not in seen:
                seen.add(row);found.append(dict(name=name, where=where, widget=owner, kind=kind, words=words[:200]))
    widgets, actions = {}, {}
    for top in [window] + list(QApplication.topLevelWidgets()):
        for widget in [top] + top.findChildren(QWidget):widgets[id(widget)] = widget
        for action in top.findChildren(QAction):actions[id(action)] = action
    for widget in widgets.values():
        owner = type(widget).__name__
        for kind, words in words_of(widget):note(owner, kind, words)
        for action in QWidget.actions(widget):actions[id(action)] = action
    for action in actions.values():
        for kind in ('text', 'toolTip', 'statusTip', 'whatsThis'):
            words = getattr(action, kind)()
            if words:note('QAction', kind, words)
    return found


def open_menus(window):
    """Have every menu fill its rows, as it does when it is about to show."""
    from PySide6.QtWidgets import QMenu
    for menu in window.findChildren(QMenu):
        try:menu.aboutToShow.emit()
        except Exception:pass      # noqa: BLE001 - a menu that cannot fill now is read as it stands


def walk(window, settle, log=None):
    """Visit the places and sweep each. `settle()` lets the window finish what an act began. Returns {found, places, words,
    named}: what names a NEVER, every place visited with whether its act was done, how many different words were read, and
    how many of them say her shown name. A place given `must` is done only when words read there hold it. Her hand is left
    at Do and show, the place a workspace opens on; the workspace keeps one setting more, brain.name_sweep."""
    from unittest.mock import patch
    from PySide6.QtWidgets import QDialog, QMenu
    from workbench import desk_acts, local_brain, log_qt
    from workbench.desk_doers import run
    found, places, read = [], [], set()
    def look(where, done=True, must=None):
        open_menus(window);settle();here = set()
        sweep(window, where, found, here);read.update(here)
        if must is not None and not any(must in words for words in here):done = False
        places.append(dict(where=where, done=bool(done)))
        if log:log('%s%s' % (where, '' if done else ' (the act was not done)'))
    def act(act_name, **args):
        out = run(window, act_name, args, door='script', origin='desk-script:name-sweep');settle()
        return out
    def visit(where, act_name, must=None, **args):
        out = act(act_name, **args);look(where, out['ok'], must);return out
    def listed():
        return (act('read.desk', part='files').get('result') or {}).get('names') or []
    # a brain event by the program's own writer, with the actor it gives every one of them; the row every timeline makes of it
    bridge = window.ledger_bridge;brain_row = '%s · brain.%s' % (SHOWN_NAME, BRAIN_EVENT)
    def brain_event():
        local_brain.put(bridge.kernel, BRAIN_EVENT, {}, 'CHECKED')
        bridge.tail.refresh();window._refresh_activity();settle()      # what the window's own tick and acts do: a test's window holds its clock
    brain_event()
    look('the start', must='%s  brain.%s  CHECKED' % (SHOWN_NAME.upper(), BRAIN_EVENT))      # the listing of recorded commands
    visit('Today', 'go.today')
    for menu in desk_acts.HEAD_MENUS + ('Apps',):
        visit('the head: ' + menu, 'head.open', menu=menu);act('menu.close')
    for which in ('CPU', 'GPU', 'RAM', 'TXT', 'equalizer'):
        visit('the meter: ' + which, 'head.meter', which=which);act('menu.close')
    for side, views in (('left', ('files', 'machine', 'settings')), ('right', ('activity', 'context', 'talk'))):
        for view in views:
            if view == 'activity':brain_event()      # among the last lines of its timeline
            visit('the %s pane: %s' % (side, view), 'go.pane', brain_row if view == 'activity' else None, **{side: view})
    visit('Files', 'go.files')
    folders = listed();file = None
    if folders:
        visit('Files: the right-click on a folder', 'menu.open', on='file', name=folders[0])
        visit('Files: the right-click on a folder, More', 'menu.choose', path='more');act('menu.close')
    for folder in folders[:6]:      # the first file there is, in the folders at the top of Files
        if act('go.files', folder=folder)['ok']:
            file = next((name for name in listed() if '.' in name), None)
            if file:break
    out = act('menu.open', on='file', name=file) if file else {'ok': False}
    look('Files: the right-click on a file', out['ok'])
    visit('Files: the right-click on a file, More', 'menu.choose', path='more');act('menu.close')
    visit('Files: the right-click here', 'menu.open', on='here');act('menu.close')
    for face in ('apps', 'network', 'work'):visit('the Field: ' + face, 'go.field', face=face)
    sheets = [o.title for o in window.field_page.view.field.objects if getattr(o, 'title', '')]
    if sheets:
        visit('the Field: a sheet selected', 'point.sheet', title=sheets[0])
        visit('the Field: the right-click on a sheet', 'menu.open', on='sheet', name=sheets[0])
        visit('the Field: the right-click on a sheet, More', 'menu.choose', path='more');act('menu.close')
        for act_name, where in (('sheet.steps', 'what can be done'), ('sheet.doubt', 'the doubt'), ('sheet.trace', 'the trace')):
            visit('the Field: ' + where, act_name);act('sheet.close')
    else:look('the Field: a sheet selected', False)
    act('go.back')
    for who in ('terminal', 'search', 'web', 'log', 'her'):visit('the writing line: to ' + who, 'type.to', who=who)
    act('type.room', size='half')
    for text, where in (('files.list', 'a line'), ('explain files.list', 'a line explained'), ('files.list ; rm -rf x', 'a line refused')):
        visit('the writing line: ' + where, 'type.put', text=text)
    brain_event()      # again: the Log opens on its last events, and the walk's own acts are many
    act('type.to', who='log');view = log_qt.view_of(window);row = None
    if view is not None:
        view.choose('events', remember=False);settle()
        row = next((item for item in (view.events.item(i) for i in range(view.events.count())) if brain_row in item.text()), None)
        if row is not None:view.chose(row)
    look('the Log: a brain event pinned', row is not None and view.pin_frame.isVisible(), 'origin ' + SHOWN_NAME.upper())
    if view is not None:view.unpin()
    act('type.to', who='search');act('type.put', text=BRAIN_EVENT)
    visit('Search: a brain event in its timeline', 'type.send', brain_row)
    act('type.to', who='her');window.type_bar.box.clear();act('type.room', size='line')
    for place in ('ask', 'free', 'show'):visit('her hand: ' + place, 'hand.dial', place=place)
    wrote = visit('her hand: an act of hers on its card', 'hand.write', path='name sweep.txt', text='one name\n')
    if wrote['ok']:visit('her hand: the act taken back', 'hand.undo')
    opened = []      # About waits for its Close (QDialog.exec): it is shown instead, read, and closed
    with patch.object(QDialog, 'exec', lambda dialog:(opened.append(dialog), dialog.show(), 0)[2]):
        window.show_about();settle()
    look('Guide: About Graphite', bool(opened), 'kept back (RIGHTS.md)')
    for dialog in opened:dialog.close();dialog.deleteLater()
    plates = next((menu for menu in window.findChildren(QMenu) if menu.title() == 'Art plates'), None);before = window.tabs.count()
    for row in ([a for a in plates.actions() if a.isEnabled() and SHOWN_NAME in a.text()] if plates is not None else []):row.trigger();settle()
    look('Rules: her art plate opened', window.tabs.count() > before, 'Preview · ' + SHOWN_NAME)      # the other plates' names are their rows
    for index in range(window.tabs.count() - 1, before - 1, -1):window.close_tab(index)
    settle()
    visit('Today, at the end', 'go.today')
    return dict(found=found, places=places, words=len(read), named=sum(SHOWN_NAME in words for words in read))


def in_code(root=ROOT, folders=CODE_FOLDERS, kept=None):
    """Every sentence in the code that carries her earlier name outside named(), CODE_KEPT set aside. Documentation strings
    and comments are the builder's words, not the window's."""
    kept = CODE_KEPT if kept is None else kept
    out = []
    for folder in folders:
        for path in sorted((Path(root) / folder).rglob('*.py')):
            file = path.relative_to(root).as_posix()
            text = path.read_text(encoding='utf-8')
            if not NEVER['stacy'][0].search(text):continue
            tree = ast.parse(text);docs = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
                    first = node.body[0]
                    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):docs.add(id(first.value))
            def read(node, inside):
                if isinstance(node, ast.Call):
                    f = node.func
                    if (f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else '') == 'named':inside = True
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs and not inside \
                        and NEVER['stacy'][0].search(node.value) and not any(f == file and node.value.startswith(start) for f, start in kept):
                    out.append((file, node.lineno, node.value[:160]))
                for child in ast.iter_child_nodes(node):read(child, inside)
            read(tree, False)
    return out


if __name__ == '__main__':
    left = in_code()
    for file, line, words in left:print('%s:%d: %r' % (file, line, words))
    print('NAME SWEEP, the code: %d place%s' % (len(left), '' if len(left) == 1 else 's'))
    sys.exit(1 if left else 0)
