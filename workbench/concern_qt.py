"""Concern navigation and workspaces over the portable organizational catalog."""
from .assistant_identity import named
from .text_prompts import writing_prompt
import hashlib
import sqlite3
import html
import uuid
import datetime
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QTreeWidgetItem, QInputDialog, QPlainTextEdit, QTabWidget, QTreeWidget, QHeaderView, QMessageBox, QFileDialog, QGridLayout, QToolButton, QMenu, QSizePolicy
from sdk.cli.arc1cli.concern_catalog import Catalog, CatalogError, tree, source_state, attention, shown


def plain(value='', role=None):
    widget = QLabel(value); widget.setTextFormat(Qt.PlainText); widget.setWordWrap(True)
    widget.setMinimumWidth(0)
    if role:
        widget.setProperty('arcRole', role)
        widget.setProperty('arcReadingRole', 'heading' if role == 'section' else role)
    return widget


class ConcernController(QObject):
    changed = Signal()
    attention = Signal(object)

    def __init__(self, host):
        super().__init__(host); self.host = host; self.error = None
        self.has_rendered = False; self.view = 'works'; self.current_attention = None
        try:
            self.store = Catalog(host.session.path.parent / 'concern' / 'catalog.sqlite3')
            self.view = self.store.preference('view', 'works')
        except (CatalogError, sqlite3.Error, OSError) as exc:
            self.store = None; self.error = str(exc)

    def attach_controls(self, column):
        row = QHBoxLayout()
        self.selector = QComboBox()
        for label, key in (('Properties & works', 'works'), ('Offices', 'offices'),
                           ('Work & ideas', 'work'), ('Archive', 'archive')):
            self.selector.addItem(label, key)
        self.selector.setAccessibleName('Concern navigator view')
        self.selector.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.selector.setMinimumContentsLength(8)
        self.selector.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.selector.setCurrentIndex(max(0, self.selector.findData(self.view)))
        self.selector.setEnabled(self.store is not None)
        self.selector.currentIndexChanged.connect(self.choose_view)
        row.addWidget(self.selector, 1)
        self.overview_button = QPushButton('Concern')
        self.overview_button.setAccessibleName('Open the concern overview')
        self.overview_button.clicked.connect(lambda: self.open('concern'))
        self.overview_button.setEnabled(self.store is not None)
        row.addWidget(self.overview_button); column.addLayout(row)
        if self.error:
            column.addWidget(plain('Concern catalog unavailable. Existing workspaces remain available.'))
            self.overview_button.setToolTip(self.error)

    def install_context(self):
        self.context_strip = QWidget(); row = QHBoxLayout(self.context_strip)
        row.setContentsMargins(8, 4, 8, 4)
        self.context_label = plain('Working area · ARC Concern', 'metadata')
        self.context_label.setAccessibleName('Graphite working context')
        row.addWidget(self.context_label, 1)
        area = QPushButton('Working area'); area.clicked.connect(lambda: self.open(
            self.current_attention['object_id'] if self.current_attention else 'concern'))
        ask = QPushButton(named('Ask Stacy')); ask.clicked.connect(self.ask_slate)
        row.addWidget(area); row.addWidget(ask)
        self.host.center_layout.insertWidget(1, self.context_strip)
        # The strip is no longer shown (0.4.9, the audit of what repeats what). It said the name of what is open, which the
        # bar above the work says; "Working area" opened the record that Activity's "Open record" opens; and "Ask Stacy"
        # opened a second place to talk to her, with the name typed in, when the writing line under the window already
        # carries what is open. It is still made, because the window's own code keeps it in step; it is only never shown.
        self.context_strip.setVisible(False)
        # The controls that carry across whatever is open (Field, Find, size, Undo, Redo, Save, Actions) are the centre's
        # bar, above the work and always in the same place (workbench/centre_bar.py). Back to the Field is its first
        # control: where the eye and the hand look for a way back, not at the far end of a strip under the page.
        from .centre_bar import install as install_centre_bar
        self.field_button = install_centre_bar(self.host).field; self.field_button.setAccessibleName('Back to the Field')
        self.changed.connect(self.track_current); self.track_current()

    def track_current(self):
        if not hasattr(self, 'context_label'):
            return
        tab = self.host.tabs.currentWidget()
        ident = 'concern' if self.host._home_active else (
            tab.property('concern_id') or tab.property('concern_context') if tab else None)
        if not ident and tab:
            ident = {'OrangeBookTab': 'orange_book', 'ClipWorkspaceTab': 'slate',
                     'GenesisTab': 'legal', 'ProjectDeskTab': 'ledger', 'SettingsTab': 'ledger',
                     'HardwareOverviewTab': 'arc1', 'HardwareGroupTab': 'arc1',
                     'AssemblyTab': 'arc1', 'DatabaseROMTab': 'library'}.get(type(tab).__name__)
        previous = self.current_attention; self.current_attention = None
        if ident and self.store:
            try:
                row = self.store.get(ident)
                self.current_attention = attention(row, dirty=bool(hasattr(tab, 'is_dirty') and tab.is_dirty()))
            except (CatalogError, sqlite3.Error):
                pass
        if self.current_attention:  # GRAPHITE-01: the seed record 'ledger' keeps its stored title; untouched, it reads Graphite
            self.context_label.setText('Working area · ' + shown(self.current_attention.get('object_id'), self.current_attention['title']))
        else:
            title = str(tab.property('ledgerTitle') or 'Workspace') if tab else 'Workspace'
            self.context_label.setText('Working area · ' + title)
        bar = getattr(self.host, 'centre_bar', None)      # the centre's controls say what is open now, and what it can do
        if bar is not None:bar.sync()
        if self.current_attention != previous:
            self.attention.emit(self.current_attention)
            if hasattr(self.host, 'arc_inspector'):
                self.host.arc_inspector.refresh()
            if hasattr(self.host, 'clip') and self.current_attention:
                self.host.clip.presence.cue(('context', self.current_attention['object_id'], self.current_attention['version']))

    def ask_slate(self):
        context = self.current_attention
        if self.host.clip_overlay is None or not self.host.clip_overlay.isVisible():
            self.host.open_clip()
        overlay = self.host.clip_overlay
        if overlay is not None and context and not overlay.input.text():
            overlay.input.setText('About ' + shown(context.get('object_id'), context['title']) + ': ')
            overlay.input.setFocus()

    def remember(self):
        if not self.store or not self.has_rendered or self.view != getattr(self, 'rendered_view', None):
            return
        if getattr(self.host, 'tree_search', None) and self.host.tree_search.text():
            return  # A filter's temporary expansion is not a saved preference.
        existing = self.store.preference('expanded', [])
        prefix = 'workspace:concern:' + self.view + ':'
        saved = [key for key in existing if not key.startswith(prefix)]
        saved += [item.data(0, Qt.UserRole+3) for item in self.host._nav_items()
                  if item.data(0, Qt.UserRole+2) == 'nav_catalog' and item.isExpanded()]
        self.store.set_preference('expanded', saved[:1000])

    def choose_view(self, index):
        if self.selector.itemData(index)==self.view:return # Consumer sync still updates the visible view sentence.
        bridge=getattr(self.host,'ledger_bridge',None)
        if bridge is None:return
        from . import ledger_control
        from .engineering_kernel import operator
        from PySide6.QtCore import QSignalBlocker
        row=next(r for r in ledger_control.settings(bridge.kernel)['settings'] if r['key']=='catalog.view')
        response=bridge.kernel.dispatch('ledger.settings.set',dict(key='catalog.view',
            value=self.selector.itemData(index),expected_revision=row['revision']),operator())
        if not response['ok']:
            with QSignalBlocker(self.selector):self.selector.setCurrentIndex(self.selector.findData(self.view))
            self.host.statusBar().showMessage(response['error']['message'],6000);return
        bridge.publish_settings_readback()

    def rebuild(self):
        if not self.store:
            return
        host = self.host
        # The live Office and Slate branches sit above the Concern; rebuild only the Concern.
        first = next((i for i in range(host.nav.topLevelItemCount()) if host.nav.topLevelItem(i).data(0, Qt.UserRole+2) != 'nav_live'), 0)
        old = host.nav.takeTopLevelItem(first)
        if old is None:
            return
        legacy = {}
        for child in old.takeChildren():
            kind = child.data(0, Qt.UserRole+2)
            ident = child.data(0, Qt.UserRole+4)
            key = ('arc1' if kind == 'nav_root' else 'legal' if kind == 'nav_legal' else
                   {'ledger_active': 'ledger', 'platform': 'arc1', 'database_rom': 'library',
                    'ai_clip': 'slate', 'orange_book': 'orange_book', 'struthio': 'struthio'}.get(ident, 'other'))
            child.setText(0, {'nav_root': 'Hardware', 'nav_legal': 'Charter & instruments'}.get(kind,
                {'ledger_active': 'Graphite tools', 'platform': 'Operating system & firmware',
                 'database_rom': 'Reference tools', 'ai_clip': 'Conversation & tools',
                 'orange_book': 'Read Orange Book', 'struthio': 'Game workspace'}.get(ident, child.text(0))))
            legacy.setdefault(key, []).append(child)
        model = tree(self.store.snapshot(), self.view)
        saved = set(self.store.preference('expanded', []))
        def add(row, parent=None, path=()):
            title = shown(row['id'], row['title'])  # GRAPHITE-01: an untouched pre-rename seed title reads in Graphite words
            item = QTreeWidgetItem([title + (' · ' + row['state'] if row['state'] != 'active' else '')])
            route = '/'.join((*path, row['id']))
            placement = 'workspace:concern:' + self.view + ':' + hashlib.sha256(route.encode()).hexdigest()[:20]
            item.setData(0, Qt.UserRole+2, 'nav_catalog')
            item.setData(0, Qt.UserRole+3, placement)
            item.setData(0, Qt.UserRole+4, row['id'])
            item.setIcon(0, host.nav_icon('source-fact' if row['kind'] in ('concern', 'office') else 'folder'))
            item.setToolTip(0, html.escape(row['kind'].capitalize() + ' · ' + title + '\nOpen its working area'))
            if parent is None:
                host.nav.addTopLevelItem(item)
            else:
                parent.addChild(item)
            for child in row['children']:
                add(child, item, (*path, row['id']))
            for child in legacy.pop(row['id'], []):
                item.addChild(child)
            item.setExpanded(row['id'] == 'concern' or placement in saved)
            return item
        root = add(model)
        if legacy:
            tools = QTreeWidgetItem(['Workspaces & tools'])
            tools.setData(0, Qt.UserRole+2, 'nav_folder')
            tools.setIcon(0, host.nav_icon('folder')); root.addChild(tools)
            for nodes in legacy.values():
                for node in nodes:
                    tools.addChild(node)
        if model.get('bounded'):
            notice = QTreeWidgetItem(['More items · use search'])
            notice.setData(0, Qt.UserRole+2, 'nav_folder')
            notice.setToolTip('This view reached its display limit. Search can still find deeper catalog items.')
            root.addChild(notice)
        self.has_rendered = True
        self.rendered_view = self.view
        if getattr(host, 'tree_search', None):
            from .arc_desktop import filter_tree
            host._tree_expanded_before_filter = None
            filter_tree(host, host.tree_search.text())

    def open(self, ident='concern'):
        if not self.store:
            return None
        from .office_qt import is_office,open_office
        if is_office(self.store,ident):return open_office(self.host,ident)
        from .notebook_qt import is_notebook,open_notebook
        if is_notebook(self.store,ident):
            self.host._close_start()
            return open_notebook(self.host,ident)
        self.store.get(ident)
        host = self.host; host._close_start()
        for index in range(host.tabs.count()):
            tab = host.tabs.widget(index)
            if isinstance(tab, ConcernDossier) and tab.ident == ident:
                host.tabs.setCurrentWidget(tab); tab.refresh(); return tab
        tab = ConcernDossier(self, ident)
        index = host.tabs.addTab(tab, host.nav_icon('folder'), tab.title())
        if index < 0:
            return None
        host.tabs.setCurrentIndex(index)
        return tab


class ConcernDossier(QWidget):
    def __init__(self, controller, ident):
        super().__init__(); self.controller = controller; self.ident = ident
        self.loaded_note_version = None
        self.writer = uuid.uuid4().hex
        self.draft_timer = QTimer(self); self.draft_timer.setSingleShot(True)
        self.draft_timer.setInterval(600); self.draft_timer.timeout.connect(self.flush_draft)
        self._loading = False
        self._last_dirty = False
        self._has_recovery = False
        self.build()
        self.controller.changed.connect(self.refresh)
        self.refresh()

    def build(self):
        box = QVBoxLayout(self); box.setContentsMargins(12, 10, 12, 10)
        self.heading = plain('', 'section'); self.identity = plain('', 'metadata')
        box.addWidget(self.heading); box.addWidget(self.identity)
        controls = QWidget(); buttons = QGridLayout(controls); buttons.setContentsMargins(0, 0, 0, 0)
        self.control_grid = buttons; self.control_columns = 2
        self.open_button = QPushButton('Open workspace'); self.open_button.clicked.connect(self.open_workspace)
        self.new_button = QPushButton('New item'); self.new_button.clicked.connect(self.new_item)
        self.link_button = QPushButton('Link existing'); self.link_button.clicked.connect(self.link_existing)
        self.rename_button = QPushButton('Rename'); self.rename_button.clicked.connect(self.rename)
        self.more_button = QToolButton(); self.more_button.setText('More'); self.more_button.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(self.more_button)
        for title, action in (('New item…', self.new_item), ('Link existing…', self.link_existing), ('Rename…', self.rename)):
            menu.addAction(title, action)
        self.more_button.setMenu(menu); self.more_button.setAccessibleName('More working-area actions')
        self.more_button.hide()
        self.state = QComboBox()
        for value in ('active', 'planned', 'paused', 'archived'):
            self.state.addItem(value.capitalize(), value)
        self.state.setAccessibleName('Catalog item lifecycle')
        self.state.currentIndexChanged.connect(self.change_state)
        self.control_buttons = (self.open_button, self.new_button, self.link_button, self.rename_button, self.state)
        for i, widget in enumerate(self.control_buttons):
            buttons.addWidget(widget, i // 2, i % 2)
        box.addWidget(controls)
        self.pages = QTabWidget(); box.addWidget(self.pages, 1)
        overview = QWidget(); view = QVBoxLayout(overview)
        self.summary = plain('', 'prose'); view.addWidget(self.summary)
        self.children = QTreeWidget(); self.children.setRootIsDecorated(False)
        self.children.setHeaderLabels(['Item', 'Kind / state']); self.children.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.children.setAccessibleName('Items in this working area')
        self.children.itemActivated.connect(lambda item, _=0: self.controller.open(item.data(0, Qt.UserRole)))
        view.addWidget(self.children, 1)
        open_item = QPushButton('Open selected item'); open_item.clicked.connect(self.open_child)
        view.addWidget(open_item)
        self.backup_button = QPushButton('Back up catalog && notes'); self.backup_button.clicked.connect(self.backup)
        self.backup_button.setVisible(self.ident == 'concern'); view.addWidget(self.backup_button)
        self.pages.addTab(overview, 'Overview')
        self.exchange_button = QPushButton('Notes exchange…')
        self.exchange_button.setAccessibleName('Optional notes import and export')
        self.exchange_button.clicked.connect(self.open_exchange)
        view.addWidget(self.exchange_button)
        self.notebook_button = QPushButton('Engineering notebooks…')
        self.notebook_button.setAccessibleName('Open or create engineering notebook')
        self.notebook_button.clicked.connect(self.open_notebooks)
        view.addWidget(self.notebook_button)
        self.office_button=QPushButton('Tables and documents…');self.office_button.setAccessibleName('Open Office working tables and documents');self.office_button.clicked.connect(self.open_office);view.addWidget(self.office_button)
        notes = QWidget(); note_box = QVBoxLayout(notes)
        self.note = QPlainTextEdit(); self.note.setProperty('arcReadingRole', 'prose')
        self.note.setAccessibleName('Concern note draft')
        writing_prompt(self.note, 'Working notes for this item. Save commits the note.')
        self.note.textChanged.connect(self.draft_changed); note_box.addWidget(self.note, 1)
        self.note_status = plain(); note_box.addWidget(self.note_status)
        self.save_button = QPushButton('Save note'); self.save_button.clicked.connect(self.save_note)
        note_row = QHBoxLayout(); note_row.addWidget(self.save_button)
        self.recover_button = QPushButton('Recover draft'); self.recover_button.clicked.connect(self.recover_draft)
        self.reload_button = QPushButton('Reload saved'); self.reload_button.clicked.connect(self.reload_saved)
        self.draft_options = QToolButton(); self.draft_options.setText('Drafts'); self.draft_options.setPopupMode(QToolButton.InstantPopup)
        draft_menu = QMenu(self.draft_options)
        self.recover_action = draft_menu.addAction('Recover draft…', self.recover_draft)
        draft_menu.addAction('Reload saved note', self.reload_saved)
        self.draft_options.setMenu(draft_menu); self.draft_options.hide()
        note_row.addWidget(self.recover_button); note_row.addWidget(self.reload_button); note_row.addWidget(self.draft_options); note_box.addLayout(note_row)
        self.pages.addTab(notes, 'Notes')
        links = QWidget(); link_box = QVBoxLayout(links)
        self.links = QTreeWidget(); self.links.setRootIsDecorated(False)
        self.links.setHeaderLabels(['Relationship', 'Item']); self.links.header().setSectionResizeMode(0, QHeaderView.ResizeToContents); self.links.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.links.setAccessibleName('Shared item relationships'); link_box.addWidget(self.links, 1)
        row = QHBoxLayout(); follow = QPushButton('Open linked item'); follow.clicked.connect(self.open_link)
        remove = QPushButton('Remove selected link'); remove.clicked.connect(self.remove_link)
        row.addWidget(follow); row.addWidget(remove); link_box.addLayout(row)
        link_box.addWidget(plain('Removing a link keeps the item and its saved notes.'))
        self.pages.addTab(links, 'Links')
        sources = QWidget(); source_box = QVBoxLayout(sources)
        self.sources = QTreeWidget(); self.sources.setRootIsDecorated(False)
        self.sources.setHeaderLabels(['Source', 'Saved-file state']); self.sources.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.sources.setAccessibleName('Source references'); source_box.addWidget(self.sources, 1)
        row = QGridLayout()
        for i, (label, method) in enumerate((('Link source file', self.attach_file),
                ('Open source', self.open_source), ('Update reference', self.update_source), ('Check selected source', self.check_source))):
            button = QPushButton(label); button.clicked.connect(method); row.addWidget(button, i // 2, i % 2)
        source_box.addLayout(row)
        source_box.addWidget(plain('A source link records saved bytes. It does not accept a claim or grant tool permission.'))
        self.pages.addTab(sources, 'Sources')
        self.message = plain(); box.addWidget(self.message)

    def title(self):
        return shown(self.ident, self.data['title']) + (' •' if self.is_dirty() else '')

    def is_dirty(self):
        return self.note.document().isModified()

    def report_error(self, exc):
        self.message.setText(str(exc)); return False

    def refresh(self):
        self.data = self.controller.store.get(self.ident)
        self.heading.setText(shown(self.ident, self.data['title']))
        self.identity.setText(self.data['kind'].capitalize() + ' · ' + self.data['state'])
        self.setProperty('concern_id', self.ident)
        self.summary.setText(shown(self.ident, self.data['summary'], 'summary') or 'This working area has no description yet.')
        self._loading = True
        self.state.setCurrentIndex(self.state.findData(self.data['state']))
        self.state.setEnabled(self.ident != 'concern')
        if self.loaded_note_version is None or not self.is_dirty():
            self.note.setPlainText(self.data['note']['body'])
            self.note.document().setModified(False)
            self.loaded_note_version = self.data['note']['version']
        self._loading = False
        self._has_recovery = any(d['body'] != self.data['note']['body'] for d in self.controller.store.drafts(self.ident))
        self.draft_changed()
        catalog = {r['id']: r for r in self.controller.store.snapshot()['objects']}
        self.children.clear(); self.links.clear(); self.sources.clear()
        names = {'part_of': ('Part of', 'Contains'), 'maintained_by': ('Maintained by', 'Maintains'),
                 'related_to': ('Related to', 'Related from')}
        for relation in self.data['relations']:
            outgoing = relation['source'] == self.ident
            other = relation['target'] if outgoing else relation['source']
            linked = catalog[other]
            label = names[relation['kind']][0 if outgoing else 1]
            item = QTreeWidgetItem([label, shown(other, linked['title'])]); item.setData(0, Qt.UserRole, relation)
            item.setData(0, Qt.UserRole+1, other); self.links.addTopLevelItem(item)
            if not outgoing and relation['kind'] in ('part_of', 'maintained_by'):
                child = QTreeWidgetItem([shown(other, linked['title']), linked['kind'] + ' · ' + linked['state']])
                child.setData(0, Qt.UserRole, other); self.children.addTopLevelItem(child)
        for source in self.data['sources']:
            item = QTreeWidgetItem([source['path'], 'Saved reference · check when needed'])
            item.setData(0, Qt.UserRole, source); self.sources.addTopLevelItem(item)
        self.open_button.setEnabled(self.ident in WORKSPACES)
        self.open_button.setText(WORKSPACES.get(self.ident, ('Open workspace', None))[0])
        index = self.controller.host.tabs.indexOf(self)
        if index >= 0:
            self.controller.host.tabs.setTabText(index, self.title())
            if self.controller.host.tabs.currentWidget() is self:
                self.controller.host.update_document_info()

    def draft_changed(self):
        if self._loading:
            return
        dirty = self.is_dirty()
        conflict = self.loaded_note_version is not None and self.loaded_note_version != self.data['note']['version']
        self.note_status.setText('Saved note changed elsewhere; your draft is retained.' if dirty and conflict else
            'Unsaved draft' if dirty else 'Saved note' if self.loaded_note_version else 'No saved note yet')
        self.save_button.setEnabled(dirty)
        self.recover_button.setEnabled(self._has_recovery)
        self.recover_action.setEnabled(self._has_recovery)
        if dirty:
            self.draft_timer.start()
        else:
            self.draft_timer.stop()
        if dirty != self._last_dirty:
            self._last_dirty = dirty
            self.controller.track_current()
        index = self.controller.host.tabs.indexOf(self)
        if index >= 0:
            self.controller.host.tabs.setTabText(index, self.title())

    def save_note(self):
        self.draft_timer.stop()
        try:
            version = self.controller.store.save_note(self.ident, self.note.toPlainText(), self.loaded_note_version)
        except (CatalogError, sqlite3.Error, OSError) as exc:
            return self.report_error(exc)
        self.controller.store.discard_draft(self.ident, self.writer)
        self.loaded_note_version = version; self.note.document().setModified(False)
        self.message.setText('Note saved.'); self.controller.changed.emit(); return True

    def can_close_concern(self):
        if not self.is_dirty():
            return True
        recovered = self.flush_draft()
        box = QMessageBox(self); box.setWindowTitle('Keep your note draft')
        box.setTextFormat(Qt.PlainText); box.setText('Save this note before closing its working area?' +
            (' A recovery draft has been kept.' if recovered else ' A recovery draft could not be written.'))
        box.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        choice = box.exec()
        if choice == QMessageBox.Cancel:
            return False
        if choice == QMessageBox.Save:
            return self.save_note()
        return True

    def resizeEvent(self, event):
        compact = self.width() < 760
        mode = 'compact' if compact else 'wide'
        if mode != self.control_columns:
            while self.control_grid.count():
                self.control_grid.takeAt(0)
            for widget in self.control_buttons:
                widget.setVisible(not compact)
            self.more_button.setVisible(compact)
            widgets = ((self.open_button, self.more_button, self.state) if self.ident in WORKSPACES else (self.more_button, self.state)) if compact else self.control_buttons
            self.recover_button.setVisible(not compact); self.reload_button.setVisible(not compact); self.draft_options.setVisible(compact)
            for i, widget in enumerate(widgets):
                widget.show(); self.control_grid.addWidget(widget, i // 3, i % 3)
            self.control_columns = mode
        super().resizeEvent(event)

    def flush_draft(self):
        if not self.is_dirty():
            return True
        try:
            self.controller.store.save_draft(self.ident, self.writer, self.note.toPlainText(), self.loaded_note_version)
            self._has_recovery = True; self.recover_button.setEnabled(True); self.recover_action.setEnabled(True); return True
        except (CatalogError, sqlite3.Error, OSError) as exc:
            self.message.setText('Draft recovery unavailable: ' + str(exc)); return False

    def shutdown_engineering(self):
        self.draft_timer.stop(); self.flush_draft()

    def recover_draft(self):
        if self.is_dirty():
            self.message.setText('Save or copy your current draft before recovering another.'); return
        rows = [d for d in self.controller.store.drafts(self.ident) if d['body'] != self.data['note']['body']]
        labels = [datetime.datetime.fromtimestamp(d['at']).astimezone().isoformat(timespec='seconds') +
                  ' · ' + d['writer'][:10] for d in rows]
        if not labels:
            return
        label, ok = QInputDialog.getItem(self, 'Recover a note draft', 'Choose a saved recovery draft:', labels, 0, False)
        if ok:
            draft = rows[labels.index(label)]
            self._loading = True; self.note.setPlainText(draft['body'])
            self.loaded_note_version = draft['base_version']; self.note.document().setModified(True)
            self._loading = False; self.draft_changed()
            self.message.setText('Recovered draft. Review it before saving. If the saved note changed, copy wanted text, reload saved, and paste your edits.')

    def reload_saved(self):
        if self.is_dirty() and not self.flush_draft():
            return
        self.note.document().setModified(False); self.loaded_note_version = None; self.refresh()
        self.message.setText('Current saved note loaded. Recovery drafts are retained.')

    def open_exchange(self):
        from .notes_exchange_qt import show
        return show(self.controller.host,self.ident)

    def open_notebooks(self):
        from .notebook_qt import hub
        return hub(self.controller.host,self.ident)

    def open_office(self):
        from .office_qt import hub
        return hub(self.controller.host,self.ident)

    def backup(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Back up concern catalog and notes',
                            'Concern_catalog_backup.sqlite3', 'SQLite catalog (*.sqlite3)')
        if not filename:
            return
        for index in range(self.controller.host.tabs.count()):
            tab = self.controller.host.tabs.widget(index)
            if hasattr(tab,'flush_draft') and hasattr(tab,'save_concern_note') and not tab.flush_draft():
                self.message.setText('A recovery draft could not be written; backup was not started.'); return
        try:
            receipt = self.controller.store.backup(filename)
        except (CatalogError, sqlite3.Error, OSError) as exc:
            self.report_error(exc); return
        self.message.setText('Catalog, notes and recovery drafts backed up. Other Graphite records and original sources need their own backup.')
        self.message.setToolTip(receipt['sha256'])

    def mutate(self, action):
        try:
            result = action()
        except (CatalogError, sqlite3.Error, OSError) as exc:
            return self.report_error(exc)
        self.controller.changed.emit(); self.controller.host.refresh_navigator(); return result

    def new_item(self):
        kind, ok = QInputDialog.getItem(self, 'New concern item', 'Kind:',
                                      ['Note', 'Project', 'Work', 'Collection', 'Office'], 0, False)
        if not ok:
            return
        title, ok = QInputDialog.getText(self, 'New concern item', 'Title:')
        if ok:
            ident = self.mutate(lambda: self.controller.store.create(kind.lower(), title, self.ident))
            if ident:
                self.controller.open(ident)

    def rename(self):
        title, ok = QInputDialog.getText(self, 'Rename item', 'Title:', text=shown(self.ident, self.data['title']))
        if ok:
            self.mutate(lambda: self.controller.store.rename(self.ident, title, self.data['version']))

    def change_state(self, index):
        if not self._loading:
            self.mutate(lambda: self.controller.store.set_state(self.ident, self.state.itemData(index), self.data['version']))

    def link_existing(self):
        rows = [r for r in self.controller.store.snapshot()['objects'] if r['id'] not in (self.ident, 'concern')]
        labels = [shown(r['id'], r['title']) + ' · ' + r['kind'] + ' · ' + r['id'] for r in rows]
        if not labels:
            return
        label, ok = QInputDialog.getItem(self, 'Link existing item', 'One item, another entrance:', labels, 0, False)
        if ok:
            ident = rows[labels.index(label)]['id']
            kind = 'maintained_by' if self.data['kind'] == 'office' else 'part_of'
            self.mutate(lambda: self.controller.store.link(ident, kind, self.ident))

    def remove_link(self):
        item = self.links.currentItem()
        if item:
            relation = item.data(0, Qt.UserRole)
            self.mutate(lambda: self.controller.store.unlink(relation['source'], relation['kind'], relation['target']))

    def open_child(self):
        item = self.children.currentItem()
        if item:
            self.controller.open(item.data(0, Qt.UserRole))

    def open_link(self):
        item = self.links.currentItem()
        if item:
            self.controller.open(item.data(0, Qt.UserRole+1))

    def open_workspace(self):
        route = WORKSPACES.get(self.ident)
        if route:
            host = self.controller.host
            result = route[1](host)
            if host.tabs.last_open_cancelled:
                return
            tab = result if isinstance(result, QWidget) else host.tabs.currentWidget()
            if tab is not None:
                tab.setProperty('concern_context', self.ident); self.controller.track_current()

    def attach_file(self):
        host = self.controller.host
        filename, _ = QFileDialog.getOpenFileName(self, 'Link a saved source file', str(host.root))
        if not filename:
            return
        try:
            relative = Path(filename).absolute().relative_to(host.root).as_posix()
            self.mutate(lambda: self.controller.store.attach_source(self.ident, host.root, relative))
        except (OSError, ValueError) as exc:
            self.report_error(exc)

    def save_concern_note(self):
        return self.save_note()

    def check_source(self):
        item = self.sources.currentItem()
        if item:
            item.setText(1, source_state(item.data(0, Qt.UserRole), self.controller.host.root))

    def open_source(self):
        item = self.sources.currentItem()
        if not item:
            return
        source = item.data(0, Qt.UserRole); host = self.controller.host
        if source_state(source, host.root) in ('Unavailable', 'Different working directory'):
            self.message.setText('This source is unavailable in the current working directory.'); return
        tab = host.open_document(host.root / source['path'])
        if tab is not None:
            tab.setProperty('concern_context', self.ident); self.controller.track_current()

    def update_source(self):
        item = self.sources.currentItem()
        if not item:
            return
        source = item.data(0, Qt.UserRole); host = self.controller.host
        if source['root'] != str(host.root):
            self.message.setText('Select the original working directory before updating this reference.'); return
        self.mutate(lambda: self.controller.store.attach_source(self.ident, host.root,
                    source['path'], source['sha256']))


WORKSPACES = {
    'concern': ('Charter && instruments', lambda h: h.show_genesis()),
    'arc1': ('Open hardware workspace', lambda h: h.show_assembly()),
    'ledger': ('Open Graphite tools', lambda h: h.show_project_desk()),
    'slate': ('Open conversation', lambda h: h.show_clip_workspace()),
    'stac': ('Open Memory & staC', lambda h: h.ledger_bridge.navigation()['memory']()),
    'orange_book': ('Read Orange Book', lambda h: h.show_orange_book()),
    'struthio': ('Open game workspace', lambda h: h.show_native_game()),
    'library': ('Open reference tools', lambda h: h.show_database_rom()),
    'legal': ('Open legal records', lambda h: h.show_genesis()),
    'engineering': ('Open jobs & evidence', lambda h: h.show_engineering()),
    'operations': ('Open operations settings', lambda h: h.ledger_bridge.show_settings('Operations')),
}
