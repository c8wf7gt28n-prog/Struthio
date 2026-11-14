"""Files on the Desk: a Finder-style browser of the workspace's Files folder (the Files mockup, board 1).

Folders and files as large thumbnails or as a list; machine files hidden unless asked; actions are words (4.1).
Everything that changes a file goes through the Kernel's files.* operations, so Trash, versions and Slate's limits apply.
Working copies (4.7) of files elsewhere in your home folder live in Files › Working copies; their originals change only
through copies.* (review, then Update original).
"""
from __future__ import annotations
from .assistant_identity import named
from .text_prompts import writing_prompt
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QListWidget, QListWidgetItem, QMenu,
                               QMessageBox, QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)
from .shell2 import QUIET, call, call_write, escape_text, role, sentence

ICON = 112
WORKING = 'Working copies'


def size_words(size):
    if size is None:return ''
    for unit in ('bytes', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':return ('%d %s' % (size, unit)) if unit == 'bytes' else ('%.1f %s' % (size, unit))
        size /= 1024


def when(stamp):
    moment = datetime.fromtimestamp(stamp);today = datetime.now().date()
    if moment.date() == today:return 'Today ' + moment.strftime('%H:%M')
    if (today - moment.date()).days == 1:return 'Yesterday'
    return moment.strftime('%d %b %Y')


class FilesTab(QWidget):
    def __init__(self, host, path=''):
        super().__init__();self.host = host;self.folder = path;self.show_all = False;self.mode = 'icons';self.listing = None
        self.question = None;self.question_name = None  # a search or a smart folder, when one is open
        self.setObjectName('LibraryTab');self.setProperty('ledgerRoom', True)
        box = QVBoxLayout(self);box.setContentsMargins(28, 18, 28, 12);box.setSpacing(10)
        top = QHBoxLayout();top.setSpacing(16)
        self.crumbs = QLabel();self.crumbs.setStyleSheet('color:%s' % QUIET);top.addWidget(self.crumbs, 1)
        self.crumbs.hide();top.addStretch(1)  # the path at the top of the window says where you are; not said twice
        from PySide6.QtWidgets import QLineEdit
        self.search = QLineEdit();writing_prompt(self.search, 'Find in Files…');self.search.setClearButtonEnabled(True);self.search.setMaximumWidth(280)
        self.search.setAccessibleName('Find in Files: names and words inside');self.search.returnPressed.connect(self.find_words);top.addWidget(self.search)
        self.search.hide()  # one place to type: ? words in the box at the foot finds in Files too, with show in Files
        box.addLayout(top)
        self.heading = role(QLabel('Files'), 'title');box.addWidget(self.heading)
        self.actions = QLabel();box.addWidget(self.actions)  # its own line: the words never squeeze into a column
        self.lead = QLabel();self.lead.setWordWrap(True);self.lead.setStyleSheet('color:%s' % QUIET);box.addWidget(self.lead)
        self.copy_line = QLabel();self.copy_line.setWordWrap(True);self.copy_line.hide();box.addWidget(self.copy_line);self.copies = {}
        self.stack = QStackedWidget()
        self.icons = QListWidget();self.icons.setViewMode(QListWidget.IconMode);self.icons.setIconSize(QSize(ICON, ICON))
        self.icons.setGridSize(QSize(ICON + 44, ICON + 56));self.icons.setResizeMode(QListWidget.Adjust);self.icons.setMovement(QListWidget.Static)
        self.icons.setWordWrap(True);self.icons.setSelectionMode(QAbstractItemView.ExtendedSelection);self.icons.setAccessibleName('Files, as thumbnails')
        self.table = QTreeWidget();self.table.setHeaderLabels(['Name', 'Kind', 'Changed', 'Size', 'staC address']);self.table.setRootIsDecorated(False)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection);self.table.setAccessibleName('Files, as a list')
        self.table.header().setSectionResizeMode(0, QHeaderView.Stretch)
        for column in (1, 2, 3):self.table.header().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.icons.setStyleSheet('QListWidget::item:selected {border-left:0;}')  # a selected thumbnail is a pencil wash, nothing more
        for view in (self.icons, self.table):
            view.setContextMenuPolicy(Qt.CustomContextMenu);view.customContextMenuRequested.connect(self.menu)
            view.itemSelectionChanged.connect(self.tell_inspector)
        self.icons.itemActivated.connect(lambda item:self.activate(item.data(Qt.UserRole)))
        self.table.itemActivated.connect(lambda item, column:self.activate(item.data(0, Qt.UserRole)))
        self.stack.addWidget(self.icons);self.stack.addWidget(self.table);box.addWidget(self.stack, 1)
        self.foot = QLabel();self.foot.setWordWrap(True);self.foot.setStyleSheet('color:%s' % QUIET);box.addWidget(self.foot)
        self.reload()

    def title(self):return 'Files'

    def path_steps(self):
        """For the path at the top: Files › each folder, each one a step back up."""
        parts = [p for p in self.folder.split('/') if p]
        out = [('Files', lambda:(setattr(self, 'question', None), self.go('')))]
        for i, part in enumerate(parts):out.append((part, lambda p='/'.join(parts[:i + 1]):self.go(p)))
        if self.question is not None:out.append((self.question_name or 'found', None))
        return out

    def info(self):return 'Your Files folder'

    # -- what is shown ------------------------------------------------------------------
    def reload(self):
        if self.question is not None:return self.show_found()
        r = call_write(self.host, 'files.list', {'path': self.folder, 'all': self.show_all})
        if not r.get('ok'):
            self.folder = '';r = call_write(self.host, 'files.list', {'path': '', 'all': self.show_all})
        self.listing = r.get('result') or {'entries': [], 'hidden': 0, 'root': '', 'path': ''}
        self.root = Path(self.listing.get('root') or '.')
        parts = [p for p in self.folder.split('/') if p]
        self.heading.setText(parts[-1] if parts else 'Files')
        crumb = {'top': ('Files', lambda:self.go(''))};text = '{top}'
        for i, part in enumerate(parts[:-1]):
            crumb['c%d' % i] = (part, lambda p='/'.join(parts[:i + 1]):self.go(p));text += '  ›  {c%d}' % i
        if parts:text += '  ›  ' + escape_text(parts[-1])
        sentence(escape_text(self.root.parent.as_posix().replace(str(Path.home()), '~')) + '/' + text, crumb, self.crumbs)
        words = {'new': ('New folder', self.new_folder), 'smart': ('New smart folder…', self.new_smart), 'import': ('Import…', self.import_files),
                 'work': ('Work on a copy…', self.work_on_copy),
                 'export': ('Export…', lambda:self.export(None)), 'view': ('List' if self.mode == 'icons' else 'Thumbnails', self.toggle_view),
                 'all': ('Hide machine files' if self.show_all else 'Show all files', self.toggle_all)}
        sentence('{new}  ·  {smart}  ·  {work}  ·  {import}  ·  {export}  ·  {view}  ·  {all}', words, self.actions)
        area = parts[:1] == ['Slate'];working = parts[:1] == [WORKING]
        self.copies = {c['work']: c for c in (call(self.host, 'copies.list') or {}).get('copies', []) if c['state'] == 'WORKING'} if working else {}
        self.lead.setText(("Graphite's area (the Slate folder). Graphite writes here directly; every change keeps the version before it, and deletions go to Trash."
                           if area else 'Working copies of files elsewhere in your home folder. Edit them freely: the originals stay as they are '
                           'until you review a copy and choose to update its original.' if working else 'An ordinary folder on this computer: any Debian program can open it too. Deleting moves to Trash, '
                           'and every change Graphite makes keeps the version before it.'))
        self.fill()
        hidden = self.listing.get('hidden', 0)
        self.foot.setText(('%d machine file%s hidden.' % (hidden, '' if hidden == 1 else 's')) if hidden and not self.show_all else '')
        self.tell_inspector()

    def fill(self):
        from .thumbnails import thumbnail
        from PySide6.QtGui import QIcon
        self.icons.clear();self.table.clear()
        line = self.icons.fontMetrics().height()
        self.icons.setGridSize(QSize(max(ICON + 44, line * 9), ICON + 2 * line + 18))  # two lines of name at any text size
        for e in self.listing['entries']:
            shown = e['name'][:-5] if e['kind'] == 'smart' and e['name'].endswith('.find') else e['name']
            item = QListWidgetItem(shown);item.setData(Qt.UserRole, e)
            item.setToolTip(e['kind_words'] + ('' if e['size'] is None or e['kind'] == 'smart' else ' · ' + size_words(e['size'])) + ('\nFound in the ' + e['found'] if e.get('found') else '')
                            + ('\n' + e['path'] if self.question is not None else ''))
            item.setIcon(QIcon(thumbnail(self.root / e['path'], e['kind'], ICON)));item.setTextAlignment(Qt.AlignHCenter | Qt.AlignTop)
            self.icons.addItem(item)
            detail = e['kind_words'] + (' · %d items' % e['items'] if e['kind'] == 'folder' and e.get('items') is not None else '')
            row = QTreeWidgetItem([e['name'] + ('/' if e['kind'] == 'folder' else ''), detail, when(e['modified']), size_words(e['size']), e['address']])
            row.setData(0, Qt.UserRole, e);self.table.addTopLevelItem(row)
        self.stack.setCurrentWidget(self.icons if self.mode == 'icons' else self.table)

    def selected(self):
        if self.mode == 'icons':return [i.data(Qt.UserRole) for i in self.icons.selectedItems()]
        return [i.data(0, Qt.UserRole) for i in self.table.selectedItems()]

    def slate_file(self):
        chosen = self.selected()
        return chosen[0]['path'] if len(chosen) == 1 and chosen[0]['kind'] not in ('folder', 'smart') else None

    def slate_context(self):
        rel = self.slate_file()
        return (Path(rel).name + ' (@files:' + rel + ')') if rel else None

    def inspector(self):
        chosen = self.selected()
        if len(chosen) != 1:
            entries = (self.listing or {}).get('entries', [])
            return 'Files · ' + (self.heading.text()), [('Here', '%d folders · %d files' % (sum(e['kind'] == 'folder' for e in entries), sum(e['kind'] != 'folder' for e in entries))),
                                                        ('Where', str(self.root / self.folder))]
        e = chosen[0];r = call_write(self.host, 'files.get', {'path': e['path']});value = r.get('result') or {}
        rows = [('Kind', e['kind_words']), ('Changed', when(e['modified']))]
        if e['size'] is not None:rows.append(('Size', size_words(e['size'])))
        for label, text in (value.get('view') or {}).get('summary', [])[:6]:
            if label not in ('Size',):rows.append((str(label), str(text)))
        versions = value.get('versions') or []
        rows.append(('Versions', ('%d kept · last %s' % (len(versions), versions[0]['version'][:15])) if versions else 'None kept yet'))
        rows.append(('staC address', e['address']))
        story = (call(self.host, 'files.story', {'path': e['path']}) or {}).get('events', [])
        rows[2:2] = [('History' if i == 0 else '', when(event['at']) + ' · ' + event['what']) for i, event in enumerate(story[:6])]  # near the top: where it has been
        c = self.copy_for(e['path'])
        if c:rows[:0] = [('Working copy of', c['source_words']), ('State', c['status']), ('Graphite may edit', 'Yes' if c['for_slate'] else 'No')]
        return 'Files · ' + e['name'], rows

    def tell_inspector(self):
        self.show_copy()
        inspector = getattr(self.host, 'arc_inspector', None)
        if inspector is not None and self.host.tabs.currentWidget() is self:inspector.refresh()

    # -- moving around -------------------------------------------------------------------
    def go(self, path):
        self.folder = path;self.reload()

    def activate(self, e):
        if e['kind'] not in ('folder', 'smart') and e['name'].lower().endswith('.pill'):  # a pill is checked, never opened as a file
            from .pills_qt import show
            show(self.host, self.root / e['path']);return
        if e['kind'] == 'folder':self.question = None;self.go(e['path'])
        elif e['kind'] == 'smart':self.open_smart(e)
        else:self.host.open_in_viewer(self.root / e['path'])

    # -- searching and smart folders --------------------------------------------------
    def show_question(self, words):
        """Show what ? words found, here in Files (from the console's Find)."""
        self.search.setText(words);self.find_words()

    def find_words(self):
        words = self.search.text().strip()
        if not words:self.question = None;self.reload();return
        self.question = {'text': words, **({'under': self.folder} if self.folder else {})};self.question_name = None;self.reload()

    def open_smart(self, e):
        import json
        try:question = json.loads((self.root / e['path']).read_text(encoding='utf-8'))['find']
        except (OSError, ValueError, KeyError):QMessageBox.information(self, 'Smart folder', 'This smart folder could not be read.');return
        self.question = question;self.question_name = e['name'][:-len('.find')] if e['name'].endswith('.find') else e['name'];self.reload()

    def describe_question(self, q):
        parts = []
        if q.get('text'):parts.append('“%s” in the name or inside' % q['text'])
        if q.get('kind'):parts.append('kind: ' + q['kind'])
        if q.get('days'):parts.append('changed in the last %g day%s' % (q['days'], '' if q['days'] == 1 else 's'))
        if q.get('under'):parts.append('in ' + q['under'])
        return ' · '.join(parts) or 'everything'

    def show_found(self):
        r = call_write(self.host, 'files.find', self.question);value = r.get('result') or {'records': []}
        self.listing = {'entries': value['records'], 'hidden': 0, 'root': (call(self.host, 'files.list', {}) or {}).get('root', str(self.root)), 'path': ''}
        self.root = Path(self.listing['root'])
        self.heading.setText(self.question_name or 'Found')
        back = {'back': ('back to ' + (self.folder or 'Files'), self.leave_question)}
        sentence(escape_text(self.root.parent.as_posix().replace(str(Path.home()), '~')) + '/Files  ›  {back}', back, self.crumbs)
        words = {'keep': ('keep as a smart folder', self.keep_question), 'view': ('List' if self.mode == 'icons' else 'Thumbnails', self.toggle_view)}
        sentence(('{view}' if self.question_name else '{keep}  ·  {view}'), words, self.actions)
        found = len(value['records'])
        self.lead.setText(('A smart folder: ' if self.question_name else 'Looking for ') + self.describe_question(self.question) +
                          '.  %d found among %d files.' % (found, value.get('looked_at', 0)) if r.get('ok') else (r.get('error') or {}).get('message', 'Could not search'))
        self.fill();self.foot.setText('');self.tell_inspector()

    def leave_question(self):
        self.question = None;self.question_name = None;self.search.clear();self.reload()

    def keep_question(self):
        name, ok = QInputDialog.getText(self, 'Keep as a smart folder', 'Name', text=(self.question.get('text') or 'Found')[:60])
        if ok and name.strip():
            r = call_write(self.host, 'files.smart', {'path': self.folder, 'name': name.strip(), 'find': self.question})
            if r.get('ok'):self.question_name = name.strip();self.host.statusBar().showMessage('Kept as a smart folder in ' + (self.folder or 'Files'), 5000);self.reload()
            else:QMessageBox.information(self, 'Smart folder', (r.get('error') or {}).get('message', 'Not kept').replace('_', ' ').capitalize())

    def new_smart(self):
        from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLineEdit
        dialog = QDialog(self);dialog.setWindowTitle('New smart folder');form = QFormLayout(dialog)
        name = QLineEdit();words = QLineEdit();writing_prompt(words, 'any words, in the name or inside')
        kind = QComboBox();kind.addItems(['any kind', 'gerber', 'excellon', 'spreadsheet', 'csv', 'markdown', 'text', 'code', 'pdf', 'image', 'stl', 'dxf', 'audio', 'video'])
        days = QDoubleSpinBox();days.setRange(0, 3650);days.setDecimals(0);days.setSpecialValueText('any time');days.setSuffix(' days')
        for label, field in (('Name', name), ('Words', words), ('Kind', kind), ('Changed within', days)):form.addRow(label, field)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec() != QDialog.Accepted or not name.text().strip():return
        question = {**({'text': words.text().strip()} if words.text().strip() else {}), **({'kind': kind.currentText()} if kind.currentIndex() else {}),
                    **({'days': days.value()} if days.value() else {}), **({'under': self.folder} if self.folder else {})}
        self.act('files.smart', {'path': self.folder, 'name': name.text().strip(), 'find': question or {'limit': 200}}, 'Made a smart folder')

    def toggle_view(self):
        self.mode = 'list' if self.mode == 'icons' else 'icons';self.reload()

    def toggle_all(self):
        self.show_all = not self.show_all;self.reload()

    # -- actions -------------------------------------------------------------------------
    def act(self, op, args, done=None):
        r = call_write(self.host, op, args)
        if not r.get('ok'):QMessageBox.information(self, 'Files', (r.get('error') or {}).get('message', 'Not done').replace('_', ' ').capitalize())
        else:self.host.statusBar().showMessage(done or 'Done', 5000)
        self.reload();return r

    # -- working copies ----------------------------------------------------------------------
    def show_copy(self):
        if not self.folder.split('/')[:1] == [WORKING] or self.question is not None:self.copy_line.hide();return
        chosen = self.selected();c = self.copy_for(chosen[0]['path']) if len(chosen) == 1 else None
        if c is None:
            self.copy_line.setText('Select a working copy to see where it came from and what it would change.' if self.copies else '')
            self.copy_line.setTextFormat(Qt.PlainText);self.copy_line.setVisible(bool(self.copies));return
        head = escape_text(('%s %s. %s.' if c.get('pill') else '%s is a working copy of %s. %s.') % (c['name'], c['source_words'], c['status']))
        words = {'review': ('review changes', lambda:self.review_copy(c)), 'show': ('show the original', lambda:self.show_original(c)),
                 'discard': ('discard this draft', lambda:self.discard_copy(c))}
        order = ['review', 'show', 'discard']
        if c.get('pill'):  # its original is on the computer that sent it: the way back is a result pill
            from .pills_qt import return_copy
            words['show'] = ('return it as a pill', lambda:return_copy(self.host, c, self))
        if c['status'].startswith('Same as the original — updated') and c.get('last_update'):
            words['undo'] = ('undo the update', lambda:self.undo_copy(c));order.insert(1, 'undo')
        sentence(head + '<br>' + '  ·  '.join('{%s}' % w for w in order), words, self.copy_line);self.copy_line.show()

    def confined_look(self, c):
        """Every file of a folder copy read by Ledger's own readers, but inside confinement: untrusted files never get
        parsed in Ledger's own process."""
        r = call_write(self.host, 'confine.inspect', {'copy': c['id']})
        if not r.get('ok'):QMessageBox.warning(self, 'Look inside', r['error']['message']);return
        v = r['result'];bad = [f for f in v['files'] if not f['read']]
        lines = ['%s · %s · %s' % (f['path'], f['kind'], f['note']) for f in v['files'][:40]]
        QMessageBox.information(self, 'Look inside, confined', ('%d file(s) read with %s; %d could not be read as their kind.\n\n' % (len(v['files']), v['mechanism'], len(bad)))
                                + '\n'.join(lines) + ('\n…' if len(v['files']) > 40 else '') + (('\n\n' + v['problems']) if v.get('problems') else ''))

    def confined_run(self, c):
        """A command in the copy's folder: no network, only that folder writable, limits; never unconfined."""
        import shlex
        text, ok = QInputDialog.getText(self, 'Run a command, confined', 'Command (runs in the working copy; no network; only this folder can change):')
        if not ok or not text.strip():return
        try:argv = shlex.split(text)
        except ValueError as exc:QMessageBox.warning(self, 'Run', str(exc));return
        r = call_write(self.host, 'confine.run', {'copy': c['id'], 'command': argv, 'seconds': 120})
        if not r.get('ok'):QMessageBox.warning(self, 'Run, confined', r['error']['message']);return
        v = r['result']
        QMessageBox.information(self, 'Run, confined', 'Exit %s%s · %s · %.1f s\n\n%s%s' % (v['exit'], (' · ' + v['killed']) if v['killed'] else '', v['mechanism'], v['seconds'],
                                                                                      v['stdout'][-3000:], ('\n' + v['stderr'][-2000:]) if v['stderr'] else ''))
        self.reload()

    def copy_for(self, rel):
        """The working copy a path is, or is inside (a folder copy)."""
        return self.copies.get(rel) or next((c for w, c in self.copies.items() if rel.startswith(w + '/')), None)

    def work_on_copy(self):
        what, ok = QInputDialog.getItem(self, 'Work on a copy', 'Of what?', ['A file', 'A folder (a project)'], 0, False)
        if not ok:return
        if what.startswith('A folder'):chosen = QFileDialog.getExistingDirectory(self, 'Work on a copy of a folder', str(Path.home()))
        else:chosen, _ = QFileDialog.getOpenFileName(self, 'Work on a copy of a file', str(Path.home()))
        if not chosen:return
        give = QMessageBox.question(self, 'Work on a copy', 'Graphite keeps the original where it is and makes a working copy in Files.\n\n'
                                    'May Graphite edit this working copy too? (The original stays yours either way.)')
        r = call_write(self.host, 'copies.start', {'source': chosen, 'for_slate': give == QMessageBox.Yes})
        if not r.get('ok'):QMessageBox.information(self, 'Work on a copy', (r.get('error') or {}).get('message', 'Not started').split(': ', 1)[-1]);return
        self.host.statusBar().showMessage('Working copy made. %s is unchanged.' % r['result']['source_words'], 7000)
        self.question = None;self.go(WORKING);self.select_path(r['result']['work'])

    def select_path(self, rel):
        for i in range(self.icons.count()):
            if self.icons.item(i).data(Qt.UserRole)['path'] == rel:self.icons.setCurrentRow(i);break
        for i in range(self.table.topLevelItemCount()):
            if self.table.topLevelItem(i).data(0, Qt.UserRole)['path'] == rel:self.table.setCurrentItem(self.table.topLevelItem(i));break

    def slate_on_copy(self, c):
        what, ok = QInputDialog.getText(self, named('Ask Stacy to work on ') + c['name'], 'What should it do? (It works on the copy; you review its revision.)')
        if ok and what.strip():self.act('agenda.add', {'title': what.strip()[:400], 'copy': c['id']}, "In Graphite's Agenda. Its revision will wait for your review.")

    def review_copy(self, c):
        from .compare_qt import show
        show(self.host, _op='copies.review', id=c['id'])

    def show_original(self, c):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(c['source']).parent)))

    def discard_copy(self, c):
        if QMessageBox.question(self, 'Discard draft', 'Move this working copy to Trash? %s is not touched, and the record of the work is kept.' % c['source_words']) == QMessageBox.Yes:
            self.act('copies.discard', {'id': c['id']}, 'Moved the draft to Trash. The original is unchanged.')

    def undo_copy(self, c):
        if QMessageBox.question(self, 'Undo the update', 'Put back %s as it was before the update? This is checked first: if it changed since, nothing happens.' % c['source_words']) == QMessageBox.Yes:
            self.act('copies.undo', {'id': c['id']}, 'Put back as it was. Both versions are kept.')

    def new_folder(self):
        name, ok = QInputDialog.getText(self, 'New folder', 'Name')
        if ok and name.strip():self.act('files.mkdir', {'path': self.folder, 'name': name.strip()}, 'Made ' + name.strip())

    def import_files(self):
        chosen, _ = QFileDialog.getOpenFileNames(self, 'Import into Files')
        if not chosen:return
        import shutil
        from .files_service import free_name, resolve
        from .engine import engineering
        folder = resolve(engineering(self.host.root), self.folder)
        for source in chosen:shutil.copy2(source, free_name(folder, Path(source).name))  # copies: the originals stay where they are
        self.host.statusBar().showMessage('Imported %d file%s (copies)' % (len(chosen), '' if len(chosen) == 1 else 's'), 5000);self.reload()

    def rename(self, e):
        name, ok = QInputDialog.getText(self, 'Rename', 'New name', text=e['name'])
        if ok and name.strip() and name.strip() != e['name']:self.act('files.rename', {'path': e['path'], 'name': name.strip()}, 'Renamed')

    def place(self, entries, op):
        folder = QFileDialog.getExistingDirectory(self, 'Copy to' if op == 'files.copy' else 'Move to', str(self.root))
        if not folder:return
        try:to = Path(folder).resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:QMessageBox.information(self, 'Files', 'Choose a folder inside Files.');return
        for e in entries:self.act(op, {'path': e['path'], 'to': '' if to == '.' else to}, 'Copied' if op == 'files.copy' else 'Moved')

    def trash(self, entries):
        for e in entries:self.act('files.trash', {'path': e['path']}, 'Moved to Trash. Restore it from Trash.')

    def export(self, e):
        target = e['path'] if e else self.folder
        purpose, ok = QInputDialog.getItem(self, 'Export', 'What it is for', ['Share as is (a ZIP with SHA256SUMS)',
                                           'Manufacturing (Gerber, drill and BOM files only)'], 0, False)
        if not ok:return
        r = self.act('files.export', {'path': target, 'purpose': 'manufacturing' if purpose.startswith('Manufacturing') else 'share'}, 'Exported a copy')
        if r.get('ok'):self.host.statusBar().showMessage('Exported %d files to %s. Your files stay as they are.' % (r['result']['files'], r['result']['export']), 8000)

    def versions(self, e):
        found = (call(self.host, 'files.versions', {'path': e['path']}) or {}).get('versions', [])
        if not found:QMessageBox.information(self, 'Versions', 'No earlier versions are kept for ' + e['name'] + ' yet.');return
        choice, ok = QInputDialog.getItem(self, 'Versions of ' + e['name'], 'Go back to', [v['version'] for v in found], 0, False)
        if ok:self.act('files.revert', {'path': e['path'], 'version': choice}, 'Went back; the version before is kept too.')

    def compare_with(self, e):
        other, _ = QFileDialog.getOpenFileName(self, 'Compare ' + e['name'] + ' with', str(self.root / self.folder))
        if not other:return
        try:rel = Path(other).resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:QMessageBox.information(self, 'Files', 'Choose a file inside Files.');return
        from .compare_qt import show
        show(self.host, path=e['path'], other=rel)

    def compare_version(self, e):
        found = (call(self.host, 'files.versions', {'path': e['path']}) or {}).get('versions', [])
        if not found:QMessageBox.information(self, 'Versions', 'No earlier versions are kept for ' + e['name'] + ' yet.');return
        choice, ok = QInputDialog.getItem(self, 'Compare ' + e['name'], 'With the version kept at', [v['version'] for v in found], 0, False)
        if ok:
            from .compare_qt import show
            show(self.host, path=e['path'], version=choice)

    def explain(self, e):
        self.host.shell2.show_slate_face();self.host.shell2.face.explain_file(e['path'])

    def ask(self, e):
        question, ok = QInputDialog.getText(self, named('Ask Stacy'), 'About ' + e['name'] + ':', text='What should I check in ' + e['name'] + '?')
        if ok and question.strip():self.host.shell2.ask(question.strip(), e['name'] + ' (@files:' + e['path'] + ')')

    def investigate(self, e):
        from .investigations_qt import investigate
        investigate(self.host, 'files:' + e['path'], e['name'])

    def add_to_agenda(self, e):
        from .explain import explain
        value = call(self.host, 'files.get', {'path': e['path']}) or {}
        options = (explain(value)['suggestions'] if value else []) + ['Look at ' + e['name'] + ' and tell me what needs attention']
        choice, ok = QInputDialog.getItem(self, 'Add to the Agenda', 'What Graphite should do (staC runs as written; words wait for its brain):', options, 0, True)
        if ok and choice.strip():
            text = choice.strip()
            self.act('agenda.add', {'title': text[:400], **({'program': text} if text.startswith('@') else {})}, 'Added to the Agenda')

    def open_outside(self, e):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root / e['path'])))

    def menu(self, point):
        """HATCH DESK D4: the right-click menu (workbench/context_menu.py) for the file, the files or the folder under the pointer:
        every word of the old menu below, folded into its sections (open; change it through files.*; staC: Inspect in the line, Run,
        the chain from here; capabilities: compare, Compare revisions for two revisions, extract, the adapters for its kind; Trash
        last), each change checked against the file's revision first. old_menu keeps the old words for readers."""
        from .context_menu import open_at
        view = self.icons if self.mode == 'icons' else self.table
        return open_at(self.host, view.viewport(), point)

    def old_menu(self, point=None):
        """The menu as it was before HATCH DESK D4 (built, not shown): the folded list's source (context_menu.FOLDED)."""
        chosen = self.selected();view = self.icons if self.mode == 'icons' else self.table
        menu = QMenu(view);chain_menu = None
        if len(chosen) == 1:
            e = chosen[0]
            menu.addAction('Open pill…' if e['name'].lower().endswith('.pill') else 'Open', lambda:self.activate(e))
            c = None
            if e['kind'] not in ('folder', 'smart'):  # the file's own words gather in one submenu; the menu itself is a chain (Pass A)
                chain_menu = menu;menu = QMenu(e['name'], chain_menu)
                menu.addAction('Explain this file', lambda:self.explain(e))
                menu.addAction(named('Ask Stacy about this…'), lambda:self.ask(e))
                menu.addAction('Investigate…', lambda:self.investigate(e))
                menu.addAction('Add to the Agenda…', lambda:self.add_to_agenda(e))
                menu.addSeparator()
                c = self.copy_for(e['path'])
                if c:
                    if c['for_slate'] and c.get('kind', 'file') == 'file':menu.addAction(named('Ask Stacy to work on this…'), lambda:self.slate_on_copy(c))
                    menu.addAction('Review changes to the original…', lambda:self.review_copy(c))
                    menu.addAction('Show the original', lambda:self.show_original(c))
                    menu.addAction('Discard this draft…', lambda:self.discard_copy(c))
                    menu.addSeparator()
            if e['kind'] == 'folder' and self.copies.get(e['path']):  # a working copy of a folder: the same words as for a file
                c = self.copies[e['path']]
                menu.addAction('Look inside, confined…', lambda c=c:self.confined_look(c))
                menu.addAction('Run a command here, confined…', lambda c=c:self.confined_run(c))
                if str(c.get('source', '')).startswith('pill:'):  # it came in a pill: its way back is a result pill
                    from .pills_qt import return_copy
                    menu.addAction('Return as a pill…', lambda c=c:return_copy(self.host, c, self))
                    menu.addAction('Review the changes…', lambda c=c:self.review_copy(c))
                    menu.addAction('Discard this draft…', lambda c=c:self.discard_copy(c))
                    menu.addSeparator();c = None
            if e['kind'] == 'folder' and self.copies.get(e['path']) and c is not None:
                c = self.copies[e['path']]
                menu.addAction('Review changes to the original…', lambda:self.review_copy(c))
                menu.addAction('Show the original', lambda:self.show_original(c))
                menu.addAction('Discard this draft…', lambda:self.discard_copy(c))
                menu.addSeparator()
            if e['kind'] not in ('folder', 'smart'):menu.addAction("Open with this computer's app", lambda:self.open_outside(e))
            menu.addAction('Rename…', lambda:self.rename(e))
            if e['kind'] not in ('folder', 'smart'):
                menu.addAction('Versions…', lambda:self.versions(e))
                menu.addAction('Compare with…', lambda:self.compare_with(e))
                menu.addAction('Compare with a version…', lambda:self.compare_version(e))
            menu.addAction('Export…', lambda:self.export(e))
        if chosen:
            menu.addAction('Copy to…', lambda:self.place(chosen, 'files.copy'));menu.addAction('Move to…', lambda:self.place(chosen, 'files.move'))
            menu.addSeparator();menu.addAction('Move to Trash', lambda:self.trash(chosen))
        else:
            menu.addAction('New folder…', self.new_folder);menu.addAction('Import…', self.import_files);menu.addAction('Work on a copy of a file…', self.work_on_copy)
            from .chain_menu import root_menu
            menu.addSeparator();chains = root_menu(self.host, menu);chains.setTitle('chains');menu.addMenu(chains)
        if chain_menu is not None:
            chain_menu.addMenu(menu);menu = chain_menu  # the chain from @files: followed (fill), here only its place is kept
        return menu

    def chain_start(self):
        rel = self.slate_file()
        return '@files:' + rel if rel else None


class TrashTab(QWidget):
    """What was moved to Trash, with where it came from. Restore puts it back without overwriting anything."""

    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('LibraryTab');self.setProperty('ledgerRoom', True)
        self.box = QVBoxLayout(self);self.box.setContentsMargins(28, 18, 28, 12);self.box.setSpacing(10);self.reload()

    def title(self):return 'Trash'

    def reload(self):
        while self.box.count():
            item = self.box.takeAt(0)
            if item.widget():item.widget().deleteLater()
        self.box.addWidget(role(QLabel('Trash'), 'title'))
        rows = (call(self.host, 'files.trash_list') or {}).get('trash', [])
        lead = QLabel('Nothing is in Trash.' if not rows else 'Everything here can go back where it came from.');lead.setStyleSheet('color:%s' % QUIET)
        self.box.addWidget(lead)
        for r in rows:
            self.box.addWidget(sentence(escape_text(r['original']) + '  ·  moved ' + when(r['at']) + '  ·  {restore}',
                                        {'restore': ('restore', lambda r=r:(call_write(self.host, 'files.restore', {'id': r['id']}), self.reload()))}))
        self.box.addStretch(1)


def show(host, path=''):
    host._close_start()
    for i in range(host.tabs.count()):
        tab = host.tabs.widget(i)
        if isinstance(tab, FilesTab):
            host.tabs.setCurrentWidget(tab);tab.go(path) if path != tab.folder else tab.reload();return tab
    tab = FilesTab(host, path);host.tabs.addTab(tab, tab.title());host.tabs.setCurrentWidget(tab);return tab


def show_trash(host):
    host._close_start()
    for i in range(host.tabs.count()):
        tab = host.tabs.widget(i)
        if isinstance(tab, TrashTab):host.tabs.setCurrentWidget(tab);tab.reload();return tab
    tab = TrashTab(host);host.tabs.addTab(tab, tab.title());host.tabs.setCurrentWidget(tab);return tab
