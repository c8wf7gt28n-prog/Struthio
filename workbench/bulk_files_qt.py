"""Bulk files in the window (Graphite 1.0 L6c): choose many rows in the Files tree, act on all of them in one press, one Undo.

The owner's power user (X4, session 3) tidied 48 invoices with 48 presses and 48 Undos. Here:

    choosing many      the Files tree chooses many rows: a click chooses one (and focuses it on the board, as before), a
                       click with the range key chooses every row between, a click with the add key adds or takes away one
                       (the keys are the system's usual ones; no key is named on screen). A click that only adds to the
                       choice does not move the board. The choice outlives the tree's own readings.
    the band           with two or more files or folders of your home (or of Files) chosen, a band under the tab's header
                       says how many and where ("48 chosen in ~/Downloads") with Move to…, Copy to…, Delete and Choose
                       none. The right-click on a chosen row offers the same for all of them, and "A utility on copies of
                       these…" (K6's sandbox takes a folder's worth). Dragging a chosen row onto a folder moves them all.
    one press          the batch (bulk_files: files.batch) runs on the floor's worker (the window never waits on it); the
                       line under the tab's header says what was done, with one Undo for the whole batch
                       (files.batch_undo). What could not be put back is named there; the rest is put back.
    a line             in Line (the foot), a line whose last step is `move to FOLDER`, `copy to FOLDER` or `delete` reads
                       what it lists as every line reads, then shows what one press would do (the count, the folder, the
                       first few names, what is left out) with the press and "not now". Nothing moves before the press;
                       the answer then carries "undo the batch" beside the Undo line.

Every change is the owner's press through the Kernel (files.batch and files.batch_undo with the owner's principal).
"""
from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import QEvent, QItemSelectionModel, QObject, QSignalBlocker, Qt, QTimer
from PySide6.QtWidgets import QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import boss_theme as bt
from . import bulk_files as bf
from . import home_reach as hr

KIND = 'home-many'
ADDING = Qt.ShiftModifier | Qt.ControlModifier | Qt.MetaModifier
WORKING = {'move': 'Moving', 'copy': 'Copying', 'delete': 'Deleting'}


def kernel_of(host):
    return getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)


def say(host, words, ms=9000):
    try:host.statusBar().showMessage(words, ms)
    except (AttributeError, RuntimeError):pass
    return words


def note_of(host):
    watch = getattr(host, 'home_files', None)
    return getattr(watch, 'note', None)


# ---- what is chosen in the tree ---------------------------------------------------------------------------------------------
def chosen_rows(host, page=None):
    """The chosen rows of the Files tree that a batch may act on: [(row id, path, 'file'|'folder')], in the tree's order; and
    how many other rows are chosen (records, drives, system folders: not files of your home)."""
    page = page or getattr(host, 'cabinet_page', None);kernel = kernel_of(host)
    if page is None or kernel is None:return [], 0
    from .home_files_qt import path_of_row
    out, other = [], 0
    try:items = page.tree.selectedItems()
    except RuntimeError:
        return [], 0
    if len(items) < 2:return [], 0      # one row: the tree's own right-click and the board serve it
    order = {id(item): n for n, item in enumerate(page.items.values())}
    reach = bf.Reach(kernel)
    for item in sorted(items, key=lambda i: order.get(id(i), 0)):
        node = item.data(0, Qt.UserRole) or {}
        path = path_of_row(node.get('id')) if node.get('role') in ('file', 'folder') else ''
        if not path or not reach(path)[0]:other += 1;continue
        out.append((node['id'], path, node['role']))
    return out, other


def chosen_ids(page):
    """cabinet_qt.refresh: the rows chosen before the tree is read again."""
    try:return [ident for ident, item in page.items.items() if item.isSelected()]
    except RuntimeError:
        return []


def choose(page, ids, current=None):
    """cabinet_qt.refresh: the rows chosen before are chosen again (the current row stays current)."""
    model = page.tree.selectionModel()
    page.tree.clearSelection()      # the current row is chosen only when it was (a row taken out of the choice stays out)
    for ident in ids:
        item = page.items.get(ident)
        if item is not None and not item.isHidden():item.setSelected(True)
    if current is not None and current in page.items:
        model.setCurrentIndex(page.tree.indexFromItem(page.items[current]), QItemSelectionModel.NoUpdate)


def extending(page):
    """cabinet_qt.clicked: whether the click only added to the choice (a range, or one more): the board stays where it is."""
    bulk = getattr(page.host, 'bulk_files', None)
    if bulk is None:return False
    mods, bulk.mods = bulk.mods, Qt.NoModifier
    return bool(mods & ADDING)


def where_words(paths):
    folders = sorted({str(Path(p).parent) for p in paths})
    return 'in ' + hr.tilde(folders[0]) if len(folders) == 1 else 'in %d folders' % len(folders)


# ---- the band under the tab's header ----------------------------------------------------------------------------------------
class Chosen(QWidget):
    """'48 chosen in ~/Downloads' with Move to…, Copy to…, Delete and Choose none."""

    def __init__(self, bulk, parent=None):
        super().__init__(parent)
        self.bulk = bulk;self.host = bulk.host;self.setObjectName('BulkChosen')
        self.setAccessibleName('The files and folders chosen in the tree, with what to do to all of them')
        column = QVBoxLayout(self);column.setContentsMargins(8, 5, 8, 6);column.setSpacing(4)
        self.words = QLabel(self);self.words.setObjectName('BulkChosenWords');self.words.setWordWrap(True);column.addWidget(self.words)
        self.quiet = QLabel(self);self.quiet.setObjectName('BulkChosenQuiet');self.quiet.setWordWrap(True);column.addWidget(self.quiet)
        box = QHBoxLayout();box.setContentsMargins(0, 0, 0, 0);box.setSpacing(6);column.addLayout(box)
        self.buttons = {}
        for key, words, name, tip in (('move', 'Move to…', 'Move all the chosen to another folder', 'All of them into a folder you choose, in one press; one Undo puts them all back'),
                                      ('copy', 'Copy to…', 'Copy all the chosen to another folder', 'A copy of each in a folder you choose; the originals stay; one Undo puts the copies in DELETE'),
                                      ('delete', 'Delete', 'Delete all the chosen (into DELETE)', 'All of them into DELETE, each restorable; one Undo puts them all back')):
            button = QPushButton(words, self);button.setObjectName('BulkDelete' if key == 'delete' else 'BulkButton');button.setCursor(Qt.PointingHandCursor)
            button.setAccessibleName(name);button.setToolTip(tip);button.clicked.connect(lambda _=False, k=key: self.bulk.press(k))
            box.addWidget(button);self.buttons[key] = button
        box.addStretch(1)
        self.none = QPushButton('Choose none', self);self.none.setObjectName('BulkNone');self.none.setCursor(Qt.PointingHandCursor)
        self.none.setAccessibleName('Choose none: the tree keeps one row');self.none.clicked.connect(self.bulk.choose_none);box.addWidget(self.none)
        self.restyle();self.hide()

    def restyle(self):
        try:
            from .living_nav_qt import scale_of
            px = max(12, round(13 * scale_of(self.host)))
        except Exception:  # noqa: BLE001
            px = 13
        danger = getattr(bt, 'STOP', None) or getattr(bt, 'DANGER', None) or bt.LINE_STRONG
        self.setStyleSheet(
            'QWidget#BulkChosen {background:%s;border:1px solid %s;border-radius:6px;}'
            'QLabel#BulkChosenWords {font-family:"%s";font-size:%dpx;color:%s;background:transparent;border:0;font-weight:600;}'
            'QLabel#BulkChosenQuiet {font-family:"%s";font-size:%dpx;color:%s;background:transparent;border:0;}'
            'QPushButton {font-family:"%s";font-size:%dpx;color:%s;background:%s;border:1px solid %s;border-radius:5px;padding:2px 8px;}'
            'QPushButton:hover, QPushButton:focus {border-color:%s;}'
            'QPushButton#BulkDelete {border-color:%s;}'
            'QPushButton#BulkNone {background:transparent;border-color:transparent;color:%s;text-decoration:underline;}'
            % (bt.CARD, bt.LINE_STRONG, bt.FACE, px, bt.TEXT, bt.FACE, max(11, px - 1), bt.QUIET, bt.FACE, px, bt.TEXT, bt.RAISED, bt.LINE_STRONG,
               bt.TEXT, danger, bt.QUIET))
        self.setAttribute(Qt.WA_StyledBackground, True)

    def show_for(self, rows, other):
        if len(rows) < 2:
            self.hide();return
        paths = [p for _, p, _ in rows]
        kinds = {p: r for _, p, r in rows}
        self.words.setText('%s chosen %s' % (bf.counted(paths, kinds), where_words(paths)))
        first = ', '.join(Path(p).name for p in paths[:3]) + (' and %d more' % (len(paths) - 3) if len(paths) > 3 else '')
        self.quiet.setText(first + ('  ·  %d other row%s chosen %s not a file of your home' % (other, '' if other == 1 else 's', 'is' if other == 1 else 'are') if other else ''))
        busy = self.bulk.busy
        for button in self.buttons.values():button.setEnabled(not busy)
        self.show()


# ---- installed once ---------------------------------------------------------------------------------------------------------------
class Bulk(QObject):
    """The tree chooses many; the band; the press; the batch on the floor; one Undo."""

    def __init__(self, tree):
        super().__init__(tree)
        self.tree = tree;self.host = tree.host;self.page = tree.page();self.mods = Qt.NoModifier;self.busy = False
        self.band = None
        self.calm = QTimer(self);self.calm.setSingleShot(True);self.calm.setInterval(60);self.calm.timeout.connect(self.changed)
        page = self.page
        if page is None:return
        page.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        page.tree.itemSelectionChanged.connect(self.calm.start)
        page.tree.viewport().installEventFilter(self)
        holder = page.stack.widget(0) if page.stack.count() else None
        layout = holder.layout() if holder is not None else None
        if layout is not None:
            self.band = Chosen(self, holder)
            note = note_of(self.host)
            at = layout.indexOf(note) + 1 if note is not None and layout.indexOf(note) >= 0 else 1
            layout.insertWidget(at, self.band)

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.MouseButtonPress:self.mods = event.modifiers()
        except RuntimeError:
            pass
        return False

    def changed(self):
        if self.band is None:return
        rows, other = chosen_rows(self.host, self.page)
        self.band.show_for(rows, other)

    def choose_none(self):
        page = self.page
        if page is None:return
        current = page.tree.currentItem()
        page.tree.clearSelection()
        if current is not None:current.setSelected(True)
        self.changed()

    def press(self, act):
        rows, _ = chosen_rows(self.host, self.page)
        if len(rows) < 1:return None
        return batch(self.host, act, [p for _, p, _ in rows])


def install(tree):
    """computer_tree_qt.install calls this once, with the computer's rows (after L6b's home_files)."""
    host = tree.host
    if getattr(host, 'bulk_files', None) is not None:return host.bulk_files
    host.bulk_files = Bulk(tree)
    return host.bulk_files


# ---- the batch, on the floor ------------------------------------------------------------------------------------------------------
def _on_floor(host, op, args, done):
    """A Kernel operation with the owner's principal on the floor's worker (the window never waits on it); done(answer) on
    the window's thread. Where the floor cannot be used, on the window's thread."""
    from .engineering_kernel import operator
    try:
        from . import floor
        root = floor._root_of(host)

        def work():
            return floor.kernel_for(root).dispatch(op, args, operator())

        def landed(result, error):
            done(result if error is None else {'ok': False, 'error': {'message': str(error)}})
        if floor.submit(work, landed):return True
    except Exception:  # noqa: BLE001 - no floor here: the same call on the window's thread
        pass
    kernel = kernel_of(host)
    answer = kernel.dispatch(op, args, operator()) if kernel is not None else {'ok': False, 'error': {'message': "Graphite's Kernel is not open"}}
    done(answer);return False


def _message(answer):
    return bf._why(str((answer.get('error') or {}).get('message') or 'not done'))


def batch(host, act, paths, to=None, make=False, line='', said=None):
    """One press for many: Move to… and Copy to… ask the folder first (unless given); Delete goes straight into DELETE. The
    line under the tab's header says it, with one Undo for the batch; said(result) for the line's answer in the console."""
    paths = [str(p) for p in paths]
    if not paths:return None
    if act in ('move', 'copy') and not to:
        start = str(Path(paths[0]).parent)
        to = QFileDialog.getExistingDirectory(host, '%s %s to' % (bf.VERB[act], bf.counted(paths)), start)
        if not to:return None
    args = {'act': act, 'paths': paths[:bf.MOST]}
    if to:args['to'] = str(to)
    if make:args['make'] = True
    if line:args['line'] = str(line)[:8192]
    bulk = getattr(host, 'bulk_files', None)
    if bulk is not None:bulk.busy = True;bulk.changed()
    note = note_of(host)
    working = '%s %s%s…' % (WORKING[act], bf.counted(paths), (' to %s' % hr.tilde(to)) if to else ' into DELETE')
    if note is not None:note.tell(working)
    say(host, working)

    def landed(answer):
        if bulk is not None:bulk.busy = False
        if not answer.get('ok'):
            words = 'Not done: %s' % _message(answer)
            if note is not None:note.tell(words)
            say(host, words)
            if said is not None:said({'words': words, 'refused': True})
            if bulk is not None:bulk.changed()
            return
        result = answer['result']
        after(host, result['paths'] if act != 'delete' else [], result['words'],
              undo=undo_of(host, result['batch'], said) if result.get('done') else None, undo_words=result.get('undo_words', ''),
              trash=act in ('delete', 'copy'))
        if said is not None:said(result)
    _on_floor(host, 'files.batch', args, landed)
    return working


def undo_of(host, ident, said=None):
    """The Undo line's Undo for a batch: the whole batch put back as one (it says its own words when it lands)."""
    def go():
        undo(host, ident, said)
        return None
    go.says_itself = True
    return go


def undo(host, ident, said=None):
    note = note_of(host)
    if note is not None:note.tell('Putting the batch back…')
    say(host, 'Putting the batch back…')

    def landed(answer):
        if not answer.get('ok'):
            words = 'Not undone: %s' % _message(answer)
            if note is not None:note.tell(words)
            say(host, words)
            if said is not None:said({'words': words, 'refused': True})
            return
        result = answer['result']
        after(host, result.get('paths') or [], result['words'], undo=None, trash=result.get('act') == 'copy')
        if said is not None:said(result)
    _on_floor(host, 'files.batch_undo', {'batch': ident}, landed)


def after(host, paths, words, undo=None, undo_words='', trash=False):
    """After a batch (or its Undo): the tree reads the folders again, keeps them open, chooses the rows the batch left (so a
    second press acts on the same things where they are now), the board and DELETE's count follow; the words with Undo."""
    from .home_files_qt import branch_id
    living = getattr(host, 'living_nav', None);page = getattr(host, 'cabinet_page', None)
    if living is not None and living.computer is not None:
        tree = living.computer;chain = []
        for ident, entry in list((getattr(living, 'extra', None) or {}).items()):      # a thing of your home held beside Files' reading (the
            place = tree.whole(entry)                                                   # focus, a tile) that the batch moved: held at its new place
            if place and not Path(place).exists():
                try:
                    found = living.call('objects.get', {'id': ident})
                    if found is not None:tree.hold(found)
                except Exception:  # noqa: BLE001 - the next reading of the tree finds it all the same
                    pass
        for folder in sorted({Path(p).parent for p in paths}):
            while hr.within(folder, hr.home()):
                chain.append(branch_id(folder))
                if folder == hr.home():break
                folder = folder.parent
        if chain:
            tree.listed |= set(chain);tree.keep_open(list(dict.fromkeys(reversed(chain))));tree.remember()
    if page is not None:
        page.refresh(force=True)
        rows = [branch_id(p) for p in paths]
        rows = [r for r in rows if r in page.items]
        if rows:
            with QSignalBlocker(page.tree):
                page.tree.clearSelection()
                for r in rows:page.items[r].setSelected(True)
                page.tree.selectionModel().setCurrentIndex(page.tree.indexFromItem(page.items[rows[0]]), QItemSelectionModel.NoUpdate)
            page.tree.scrollToItem(page.items[rows[0]])
            page.remember()
    if living is not None:
        try:living.after_reading()
        except Exception:  # noqa: BLE001 - the breadcrumb is drawn again at the next move
            pass
    watch = getattr(host, 'home_files', None)
    if watch is not None:
        watch.note.tell(words, undo, undo_words, trash)
        watch.redraw()
    bulk = getattr(host, 'bulk_files', None)
    if bulk is not None:bulk.changed()
    return say(host, words)


# ---- DELETE: what was deleted together, put back together -----------------------------------------------------------------------
def batch_rows(tab):
    """files_qt.TrashTab: the deletions made in one press, newest first, each with one press that puts back all of it that is
    still in DELETE (the batch's own Undo, at any later time: what was restored since is said, never forced)."""
    from .files_qt import when
    from .shell2 import QUIET, call, escape_text, role, sentence
    found = [b for b in ((call(tab.host, 'files.batches', {'limit': 20}) or {}).get('batches') or ()) if b.get('act') == 'delete' and b.get('state') == 'done'
             and b.get('in_delete', 1)]
    if not found:return
    tab.box.addWidget(role(QLabel('Deleted together'), 'item'))
    lead = QLabel('Each was one press of Delete for many. Put them back puts back all of it that is still in DELETE; what was restored since is said.')
    lead.setWordWrap(True);lead.setStyleSheet('color:%s' % QUIET);tab.box.addWidget(lead)

    def put_back(ident):
        undo(tab.host, ident, lambda result: tab.reload())
    for b in found[:8]:
        still = b.get('in_delete', b.get('count', 0))
        words = '%s from %s%s  ·  deleted %s  ·  {back}' % (escape_text(b.get('count_words') or 'nothing'), escape_text(b.get('from_words') or 'your home'),
                                                        '' if still == b.get('count') else ', %d of them still in DELETE' % still,
                                                        when(b['at'] // 1000) if b.get('at') else 'at a time not said')
        tab.box.addWidget(sentence(words, {'back': ('put them back', lambda i=b['id']: put_back(i))}))


# ---- the right-click on a chosen row ---------------------------------------------------------------------------------------------
def target_for_many(host, page, item):
    """context_menu.find_cabinet: a right-click on a row of a choice of two or more files or folders of your home: the choice
    as one target (the choice is kept); None otherwise."""
    try:
        if item is None or not item.isSelected() or len(page.tree.selectedItems()) < 2:return None
    except RuntimeError:
        return None
    rows, other = chosen_rows(host, page)
    if len(rows) < 2:return None
    from .context_menu import Target
    paths = [p for _, p, _ in rows];kinds = {p: r for _, p, r in rows}
    return Target(KIND, '%s chosen' % bf.counted(paths, kinds), 'chosen in the tree · %s' % where_words(paths),
                  data=dict(paths=paths, kinds=kinds, other=other), surface='cabinet', owner=page, icon='files')


def entries(host, t):
    """home_files_qt.entries for a choice of many: Move to…, Copy to…, Delete, the paths, a utility on copies of them."""
    if t.kind != KIND:return []
    from .context_menu import Entry, Refused, copy_text
    paths = list(t.data.get('paths') or ());kinds = t.data.get('kinds') or {}
    count = bf.counted(paths, kinds)

    def run(act):
        def go():
            try:return batch(host, act, paths)
            except ValueError as exc:raise Refused(bf._why(exc)) from None
        return go
    out = [Entry('move:to', 'Move %s to…' % count, 'modify', run('move'), operation='files.batch',
                 tip='All of them into a folder you choose, in one press; each keeps its identity; one Undo puts them all back'),
           Entry('copy:to', 'Copy %s to…' % count, 'modify', run('copy'), operation='files.batch',
                 tip='A copy of each in a folder you choose; the originals stay; one Undo puts the copies in DELETE'),
           Entry('trash', 'Delete %s' % count, 'danger', run('delete'), operation='files.batch',
                 tip='All of them into DELETE, each restorable; one Undo puts them all back where they were'),
           Entry('copy:paths', 'Copy the paths', 'edit', lambda: copy_text(host, '\n'.join(paths), 'Copied %d paths' % len(paths)))]
    files = [p for p in paths if kinds.get(p) == 'file']
    try:
        from .utility_sandbox import MOST_INPUTS
    except Exception:  # noqa: BLE001
        MOST_INPUTS = 0
    if files and len(files) == len(paths) and len(files) <= MOST_INPUTS:
        def utility():
            from .utility_sandbox_qt import open_panel
            return open_panel(host, inputs=files)
        out.append(Entry('utility:copies', 'A utility on copies of these…', 'capability', utility, operation='sandbox.draft',
                         tip='When no tool fits: a small utility, shown before it runs, run sealed on copies of these %d files; applying '
                             'what it makes always asks, and Undo puts it back' % len(files)))
    return out


# ---- a line that moves, copies or deletes what it lists ------------------------------------------------------------------------
def _plan(host, act, read):
    from .engineering_kernel import operator
    kernel = kernel_of(host)
    if kernel is None:return {'ok': False, 'error': {'message': "Graphite's Kernel is not open"}}
    args = {'act': act['act'], 'line': read}
    if act['to']:args['to'] = act['to']
    return kernel.dispatch('files.batch_plan', args, operator())


def line_act(console, text):
    """console_qt.run_stac: a line whose last step moves, copies or deletes what it lists: what one press would do, and the
    press. False for any other line (it runs as every line runs)."""
    words = str(text or '').replace('​', '').strip()
    first = words.split(maxsplit=1);explain = bool(first) and first[0].lower() == 'explain' and len(first) > 1
    read, act = bf.split_act(first[1] if explain else words)
    if act is None:return False
    host = console.host;echo = 'line › ' + words
    answer = _plan(host, act, read)
    if not answer.get('ok'):
        console.say(console.refused(_message(answer)), echo=echo, wrap_output=True);return True
    plan = answer['result'];console.last_program = None
    from .shell2 import QUIET as quiet
    parts = ['<b>A STEP THAT ASKS</b> · nothing changes until you press']
    if plan.get('read_from'):parts.append('The line read %s: %d rows%s.' % (html.escape(plan['read_from']), plan.get('rows', 0),
                                                                          '' if plan.get('rows') == len(plan.get('paths') or ()) else
                                                                          ', of which %d %s' % (len(plan['paths']), 'acts' if len(plan['paths']) == 1 else 'act')))
    parts.append(html.escape(plan['words']))
    if not plan.get('count') or explain:
        if explain and plan.get('count'):parts.append('<span style="color:%s;">Run the line without explain: it asks for your press here.</span>' % quiet)
        console.say('<br>'.join(parts), echo=echo, wrap_output=True);return True
    used = {'done': False}

    def said(result):
        if result.get('refused'):
            console.say(console.refused(result['words']), wrap_output=True);return
        more = ''
        if result.get('batch') and result.get('done'):
            more = '  ' + console.link('undo the batch', lambda b=result['batch']: undo(host, b, lambda r: console.say(html.escape(r['words']), wrap_output=True)))
        console.say(html.escape(result.get('words', '')) + more, wrap_output=True)

    def go():
        if used['done']:return None
        used['done'] = True
        return batch(host, act['act'], plan['paths'], to=plan.get('to') or None, make=bool(plan.get('make')), line=words, said=said)

    def not_now():
        if used['done']:return None
        used['done'] = True
        console.say('<span style="color:%s;">Not now: nothing was %s.</span>' % (quiet, {'move': 'moved', 'copy': 'copied', 'delete': 'deleted'}[act['act']]))
    parts.append(console.link(plan['press'], go) + '  ·  ' + console.link('not now', not_now))
    console.say('<br>'.join(parts), echo=echo, wrap_output=True)
    return True


def preview_act(host, text):
    """shell2.preview_rows: under the writing line, what a line that moves, copies or deletes would do (None: not such a line)."""
    read, act = bf.split_act(text)
    if act is None:return None
    answer = _plan(host, act, read)
    if not answer.get('ok'):return [('section', 'PREVIEW · A STEP THAT ASKS', None), ('note', 'Not yet: ' + _message(answer)[:110], None)]
    plan = answer['result']
    out = [('section', 'PREVIEW · A STEP THAT ASKS · NOTHING CHANGES UNTIL YOU PRESS', None)]
    words = plan['words'];line = ''
    for word in words.split(' '):
        if len(line) + len(word) + 1 > 104:out.append(('note', line, None));line = word
        else:line = (line + ' ' + word).strip()
        if len(out) > 5:break
    if line and len(out) <= 5:out.append(('note', line, None))
    return out
