"""Documents: a page in the centre that the owner writes on and Slate edits with them (Commission v2.1's simple demonstration).

The page is a QTextEdit over the ``documents`` store. The owner types, selects words and uses the marks row or the keys
(Ctrl B, Ctrl I, Ctrl U, Ctrl 1/2/3 for headings, Ctrl 0 for body, Ctrl ` for code). Writing is saved a moment after it
stops (and before any Slate request), always against the revision the page last saw. A request typed to Slate in the
strip ("make these words bold") is resolved by the explicit rules in ``documents.interpret``; the edit goes through
``documents.edit`` with the selection and its quoted words, lands as a revision, and is applied to the page through the
same undo stack as the owner's typing, so Ctrl Z takes Slate's change back like any other. A request the rules do not
recognise goes to the model path with the document and selection as context. Reopening a document from the list or the
cabinet reads the saved revision. Nothing here starts a job, a worker or a model.
"""
from __future__ import annotations
from .assistant_identity import named
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence, QPalette, QShortcut, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextDocument, QTextFormat
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLayout, QLineEdit, QListWidget, QListWidgetItem, QSplitter, QTextEdit, QVBoxLayout, QWidget
from .shell2 import AMBER, CARD, ERASER_DEEP, PENCIL_DEEP, QUIET, TEXT, call, call_write, escape_text, role, sentence
from .settings_qt import action
from .text_prompts import writing_prompt
from . import documents as store

STYLE_PROPERTY = QTextFormat.UserProperty + 41   # the block's style word, kept on the block format
AUTOSAVE_MS = 1500
STYLE_SCALE = {'Normal': 1.0, 'Heading1': 1.6, 'Heading2': 1.3, 'Heading3': 1.12, 'Code': 0.95}
STYLE_WEIGHT = {'Heading1': QFont.DemiBold, 'Heading2': QFont.DemiBold, 'Heading3': QFont.DemiBold}
PAGE_STYLE = ('QTextEdit#DocumentPage {background:%s;color:%s;border:0;padding:0;selection-background-color:%s;selection-color:%s;}'
              'QLineEdit#DocumentTitle {background:%s;color:%s;border:0;border-radius:0;padding:8px 10px;selection-background-color:%s;selection-color:%s;}'
              'QLineEdit#DocumentTitle:focus {border-bottom:2px solid %s;}'
              'QListWidget#DocumentList {background:transparent;border:0;color:%s;} QListWidget#DocumentList::item {padding:6px 4px;}'
              'QListWidget#DocumentList::item:selected {background:%s;color:%s;}' % (CARD, TEXT, PENCIL_DEEP, TEXT, AMBER, TEXT, ERASER_DEEP, TEXT, TEXT, TEXT, ERASER_DEEP, TEXT))
UNDO_WORDS = {'undo', 'undo that', 'undo it', 'take that back', 'revert that', 'go back'}
REDO_WORDS = {'redo', 'redo that', 'redo it'}
# AGENT-02 (D19): a model edit is shown by a pencil-yellow wash over the changed range that fades out over FLASH_MS in
# FLASH_STEPS steps (under Reduce motion it stays FLASH_MS and then clears). It is an ExtraSelection, never a format.
FLASH_MS = 1500
FLASH_STEPS = 10


def profile_of(host):
    from .reading_profile import DEFAULT, clean
    return clean(getattr(host, 'reading_profile', None) or host.session.state.get('reading_profile', DEFAULT))


def fonts_of(host):
    from .reading_preferences import font
    profile = profile_of(host)
    return font(profile['prose_family'], profile['prose_pt']), font(profile['code_family'], profile['code_pt'], True)


def char_format(on, prose, code, style='Normal'):
    fmt = QTextCharFormat()
    base = QFont(code if style == 'Code' else prose)
    base.setPointSizeF(base.pointSizeF() * STYLE_SCALE[style])
    if style in STYLE_WEIGHT: base.setWeight(STYLE_WEIGHT[style])
    fmt.setFont(base)
    if 'bold' in on: fmt.setFontWeight(QFont.Bold)
    if 'italic' in on: fmt.setFontItalic(True)
    if 'underline' in on: fmt.setFontUnderline(True)
    return fmt


def block_format(style):
    fmt = QTextBlockFormat(); fmt.setProperty(STYLE_PROPERTY, style)
    fmt.setTopMargin({'Heading1': 18, 'Heading2': 14, 'Heading3': 10}.get(style, 4)); fmt.setBottomMargin(4)
    return fmt


def to_qt(doc, text_document, prose, code):
    """Fill a QTextDocument from the stored blocks (the undo stack is cleared: this is a load, not an edit)."""
    text_document.clear(); text_document.setDefaultFont(prose)
    cursor = QTextCursor(text_document); cursor.beginEditBlock()
    for index, b in enumerate(doc['blocks']):
        if index: cursor.insertBlock(block_format(b['style']), char_format(frozenset(), prose, code, b['style']))
        else: cursor.setBlockFormat(block_format(b['style'])); cursor.setBlockCharFormat(char_format(frozenset(), prose, code, b['style']))
        for text, on in store.runs(b): cursor.insertText(text, char_format(on, prose, code, b['style']))
    cursor.endEditBlock(); text_document.clearUndoRedoStacks(); text_document.setModified(False)


def marks_of(fmt):
    on = set()
    if fmt.fontWeight() >= QFont.Bold: on.add('bold')
    if fmt.fontItalic(): on.add('italic')
    if fmt.fontUnderline(): on.add('underline')
    return frozenset(on)


def from_qt(text_document, ids=None):
    """Read the page back into stored blocks; block ids are kept by position where the page still has them."""
    blocks = []; ids = ids or []
    block = text_document.firstBlock(); index = 0
    while block.isValid():
        style = block.blockFormat().property(STYLE_PROPERTY) or 'Normal'
        if style not in store.STYLES: style = 'Normal'
        text = block.text().replace(' ', '').replace(' ', ' ').replace('\r', '').replace('\n', ' ')
        marks = []; at = 0
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid():
                piece = fragment.text().replace(' ', '').replace(' ', ' ').replace('\r', '').replace('\n', ' ')
                on = marks_of(fragment.charFormat())
                if on and piece: marks.append({'start': at, 'end': at + len(piece), **{k: True for k in on}})
                at += len(piece)
            it += 1
        row = {'style': style, 'text': text, 'marks': marks}
        if index < len(ids): row['id'] = ids[index]
        blocks.append(row); block = block.next(); index += 1
    return store.normalize_blocks(blocks)


class WordRow(QLayout):
    """The page's format words in one row while they fit, wrapping to the next line where the page is narrow (the desk's review
    set found them squeezed and cut at 1366 by 768: "Bolc", "Ital"). Each word keeps its own width; add(widget, gap) leaves a
    group's gap before a word that does not start a line."""

    def __init__(self, parent=None, spacing=2, line_spacing=2):
        super().__init__(parent);self.items = [];self.gaps = [];self._gap = 0;self._spacing = spacing;self._line = line_spacing
        self.setContentsMargins(0, 0, 0, 0)

    def add(self, widget, gap=0):self._gap = gap;self.addWidget(widget)

    def addItem(self, item):self.items.append(item);self.gaps.append(self._gap);self._gap = 0

    def count(self):return len(self.items)

    def itemAt(self, index):return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        if 0 <= index < len(self.items):self.gaps.pop(index);return self.items.pop(index)
        return None

    def expandingDirections(self):return Qt.Orientations(0)

    def hasHeightForWidth(self):return True

    def heightForWidth(self, width):return self.arrange(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):super().setGeometry(rect);self.arrange(rect, False)

    def sizeHint(self):
        """One line: every word and gap side by side."""
        shown = [(i, g) for i, g in zip(self.items, self.gaps) if not i.isEmpty()]
        width = sum(i.sizeHint().width() for i, _ in shown) + sum(self._spacing + g for _, g in shown[1:])
        return QSize(width, max((i.sizeHint().height() for i, _ in shown), default=0))

    def minimumSize(self):
        """The widest word: the row wraps rather than squeeze one."""
        return QSize(max((i.sizeHint().width() for i in self.items if not i.isEmpty()), default=0), max((i.sizeHint().height() for i in self.items if not i.isEmpty()), default=0))

    def arrange(self, rect, test):
        x, y, line = rect.x(), rect.y(), 0
        for item, gap in zip(self.items, self.gaps):
            if item.isEmpty():continue
            size = item.sizeHint();space = self._spacing + gap if x > rect.x() else 0
            if x + space + size.width() > rect.right() + 1 and x > rect.x():x, y, line, space = rect.x(), y + line + self._line, 0, 0
            if not test:item.setGeometry(QRect(QPoint(x + space, y), size))
            x += space + size.width();line = max(line, size.height())
        return y + line - rect.y()


class DocumentPage(QTextEdit):
    """The writing surface: plain paste, visible selection while the strip has focus, style-aware Return."""
    focus_left = Signal()

    def __init__(self, tab):
        super().__init__(); self.tab = tab; self.setObjectName('DocumentPage'); self.setAcceptRichText(False)
        self.setProperty('arcReadingRole', 'prose'); self.setAccessibleName('Document page: write here; Graphite edits the same page')
        self.setFrameStyle(0); self.setTabChangesFocus(False); self.document().setDocumentMargin(44)
        palette = self.palette()
        palette.setColor(QPalette.Active, QPalette.Highlight, QColor(PENCIL_DEEP)); palette.setColor(QPalette.Active, QPalette.HighlightedText, QColor(TEXT))
        palette.setColor(QPalette.Inactive, QPalette.Highlight, QColor(ERASER_DEEP)); palette.setColor(QPalette.Inactive, QPalette.HighlightedText, QColor(TEXT))
        palette.setColor(QPalette.Base, QColor(CARD)); palette.setColor(QPalette.Text, QColor(TEXT)); self.setPalette(palette)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers() & Qt.ShiftModifier:
            cursor = self.textCursor(); style = cursor.blockFormat().property(STYLE_PROPERTY) or 'Normal'
            super().keyPressEvent(event)
            if style.startswith('Heading'):  # a heading ends at Return; the next paragraph is body text
                self.tab.set_style('Normal', cursor=self.textCursor(), note=False)
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event); self.focus_left.emit()

    def contextMenuEvent(self, event):
        """HATCH DESK D4: the right-click menu (workbench/context_menu.py) for the passage under the pointer (Bold and the other page
        edits through documents.edit with this page's revision, Move to notes, the equivalent command to inspect, Ask Stacy) or
        the page at the caret; the text edits this page's own menu had are in it too."""
        from .context_menu import open_at
        if open_at(self.tab.host, self.viewport(), event.pos(), keyboard=event.reason() == event.Reason.Keyboard) is None:super().contextMenuEvent(event)

    def insertFromMimeData(self, source):  # pasted writing arrives as plain paragraphs in the current style
        if source.hasText(): self.insertPlainText(source.text().replace('\r\n', '\n'))
        else: super().insertFromMimeData(source)


class DocumentsTab(QWidget):
    def __init__(self, host):
        super().__init__(); self.host = host; self.document_id = None; self.revision = None; self.block_ids = []; self.dirty = False; self.loading = False
        self.setObjectName('LibraryTab'); self.setProperty('ledgerRoom', True); self.setStyleSheet(PAGE_STYLE)
        outer = QVBoxLayout(self); outer.setContentsMargins(28, 18, 28, 12); outer.setSpacing(8)
        head = QHBoxLayout(); head.addWidget(role(QLabel('Documents'), 'title'), 1); outer.addLayout(head)
        self.lead = QLabel(named('Write here. Select words and ask Stacy in the strip below: “make these words bold”. Saving is automatic, and any change can be taken back, hers too.'))
        self.lead.setWordWrap(True); self.lead.setStyleSheet('color:%s' % QUIET); outer.addWidget(self.lead)
        split = QSplitter(Qt.Horizontal); split.setChildrenCollapsible(False); outer.addWidget(split, 1)
        left = QWidget(); left_box = QVBoxLayout(left); left_box.setContentsMargins(0, 0, 12, 0); left_box.setSpacing(6)
        words = QHBoxLayout(); words.setSpacing(2)
        self.new_word = action('New document', self.new_document); self.new_word.setAccessibleDescription('Start an empty document; it is saved as you write')
        self.export_word = action('Export…', self.export_document); self.export_word.setAccessibleDescription('Write the current document to a Markdown, HTML or text file you choose')
        from .theme2 import tool        # the page's actions are buttons: New, Export, and the row that shapes the writing
        tool(self.new_word, 'Start an empty document; it is saved as you write'); tool(self.export_word, 'Write the current document to a Markdown, HTML or text file you choose'); words.setSpacing(8)
        words.addWidget(self.new_word); words.addWidget(self.export_word); words.addStretch(1); left_box.addLayout(words)
        self.list = QListWidget(); self.list.setObjectName('DocumentList'); self.list.setAccessibleName('Saved documents, newest first')
        # The desk's review set found a saved page's line cut at its time and the list scrolling sideways in its 230 px column:
        # each line wraps at its words instead, every word whole, nothing sideways.
        self.list.setWordWrap(True); self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.list.setResizeMode(QListWidget.Adjust)
        self.list.itemActivated.connect(lambda item: self.open_document(item.data(Qt.UserRole))); self.list.itemClicked.connect(lambda item: self.open_document(item.data(Qt.UserRole)))
        left_box.addWidget(self.list, 1); split.addWidget(left)
        right = QWidget(); box = QVBoxLayout(right); box.setContentsMargins(0, 0, 0, 0); box.setSpacing(6)
        self.title_box = QLineEdit(); self.title_box.setObjectName('DocumentTitle'); self.title_box.setMaxLength(200)
        writing_prompt(self.title_box, 'Document title'); self.title_box.setAccessibleName('Document title'); self.title_box.textEdited.connect(self.changed); box.addWidget(self.title_box)
        marks = WordRow(spacing=6, line_spacing=6); self.mark_words = {}  # one row while it fits, wrapping where the page is narrow
        for label, key, tip in (('Bold', 'bold', 'Ctrl B'), ('Italic', 'italic', 'Ctrl I'), ('Underline', 'underline', 'Ctrl U')):
            word = action(label, lambda checked=False, k=key: self.toggle_mark(k)); word.setToolTip(label + ' the selected words'); word.setAccessibleDescription(tip + ' · applies to the selected words'); marks.add(word); self.mark_words[key] = word
        for n, (label, style, tip) in enumerate((('Heading', 'Heading1', 'Ctrl 1'), ('Subheading', 'Heading2', 'Ctrl 2'), ('Minor heading', 'Heading3', 'Ctrl 3'), ('Body', 'Normal', 'Ctrl 0'), ('Code', 'Code', 'Ctrl `'))):
            word = action(label, lambda checked=False, s=style: self.set_style(s)); word.setToolTip('Make this paragraph: ' + label.lower()); word.setAccessibleDescription(tip + ' · applies to the paragraph'); marks.add(word, 14 if n == 0 else 0); self.mark_words[style] = word
        plain = action('Plain', self.clear_marks); plain.setToolTip('Remove bold, italic and underline from the selected words'); marks.add(plain, 14); self.mark_words['clear'] = plain
        for word in self.mark_words.values():       # a row of tools, as every writing program has: the words they were, drawn as buttons
            said = word.toolTip(); tool(word); word.setToolTip(said)
        box.addLayout(marks)
        self.page = DocumentPage(self); self.page.textChanged.connect(self.changed); self.page.focus_left.connect(self.flush); box.addWidget(self.page, 1)
        # AGENT-01: a result on this page bound to words that changed reads stale here, and one word rechecks it
        self.stale = QLabel(); self.stale.setWordWrap(True); self.stale.setStyleSheet('color:%s' % QUIET); self.stale.setAccessibleName('Stale results on this page')
        self.stale.hide(); box.addWidget(self.stale); self.stale_ids = []
        self.report_derivation = None
        self.report_bar = QWidget()
        report_row = QHBoxLayout(self.report_bar)
        report_row.setContentsMargins(0, 0, 0, 0)
        self.report_hint = QLabel()
        self.report_hint.setTextFormat(Qt.PlainText)
        self.report_hint.setWordWrap(True)
        self.report_hint.setAccessibleName('Calculation source state')
        report_row.addWidget(self.report_hint, 1)
        report_row.addWidget(action('Sheet', self.open_report_sheet))
        report_row.addWidget(action('Source page', self.open_report_page))
        self.recheck_report_word = action('Recheck', self.recheck_report)
        self.recheck_report_word.setToolTip('Calculate a new editable report from the current sheet')
        report_row.addWidget(self.recheck_report_word)
        self.report_bar.hide()
        box.addWidget(self.report_bar)
        self.foot = QLabel(); self.foot.setWordWrap(True); self.foot.setStyleSheet('color:%s' % QUIET); self.foot.setAccessibleName('Document state: saved revision and the last change'); box.addWidget(self.foot)
        split.addWidget(right); split.setStretchFactor(0, 0); split.setStretchFactor(1, 1); split.setSizes([230, 900]); split.setHandleWidth(8)      # a divider the hand can take hold of
        for keys, slot in (('Ctrl+B', lambda: self.toggle_mark('bold')), ('Ctrl+I', lambda: self.toggle_mark('italic')), ('Ctrl+U', lambda: self.toggle_mark('underline')),
                           ('Ctrl+1', lambda: self.set_style('Heading1')), ('Ctrl+2', lambda: self.set_style('Heading2')), ('Ctrl+3', lambda: self.set_style('Heading3')),
                           ('Ctrl+0', lambda: self.set_style('Normal')), ('Ctrl+`', lambda: self.set_style('Code')), ('Ctrl+S', self.flush)):
            shortcut = QShortcut(QKeySequence(keys), self.page); shortcut.setContext(Qt.WidgetWithChildrenShortcut); shortcut.activated.connect(slot)
        self.save_timer = QTimer(self, singleShot=True, interval=AUTOSAVE_MS); self.save_timer.timeout.connect(self.flush)
        self.flash_timer = QTimer(self); self.flash_timer.timeout.connect(self.flash_step); self.flash_left = 0; self.flash_cursor = None; self.flash_whole = False; self.flash_record = []; self.model_edit = None
        self.reload_list(); self.installEventFilter(self)
        if self.document_id is None: self.open_first_or_new()

    # -- host contract -------------------------------------------------------------------------------------------------------
    saves_itself = True       # for the centre's bar: this page saves as it is written, so its Save has nothing to do
    def title(self): return 'Documents'
    def centre_title(self): return (self.title_box.text().strip() or 'A page without a name') if self.document_id is not None else 'Documents'      # for the centre's bar: the page that is open, by its own name
    def is_dirty(self): return bool(self.dirty)
    def save_concern_note(self): return self.flush()          # the window's save-all walk saves the page like a note
    def can_close_concern(self): self.flush(); return True     # closing the tab never loses writing: it is saved first

    def slate_context(self):
        """What the typing strip and the model path see: the document, its revision and the selected words."""
        if self.document_id is None: return 'Documents (nothing open)'
        if self.dirty: self.flush()   # AGENT-02: the model sees, and binds its proposal to, the saved revision
        selection = self.slate_selection(); title = self.title_box.text().strip() or 'Untitled document'
        where = 'document “%s” (id %s, revision %s)' % (title, self.document_id, self.revision)
        # AGENT-02: one short line the model can copy (under 200 characters), so its proposal names this page and revision
        hint = ('\nTo change this page use documents.edit with id %s, expected_revision %s, selection {block, start, end, text} '
                'and change {bold|italic|underline|style|replace|append}.' % (self.document_id, self.revision))
        if selection: return '%s · selected words %d–%d of paragraph %d (block index %d): “%s”%s' % (where, selection['start'], selection['end'], selection['block'] + 1, selection['block'], selection['text'][:120], hint)
        return '%s · no words selected · caret in paragraph %d (block index %d)%s' % (where, self.caret_block() + 1, self.caret_block(), hint)

    def slate_selection(self):
        cursor = self.page.textCursor()
        if not cursor.hasSelection(): return None
        start, end = cursor.selectionStart(), cursor.selectionEnd(); doc = self.page.document()
        first = doc.findBlock(start); last = doc.findBlock(end)
        if first.blockNumber() != last.blockNumber():  # one paragraph at a time: the first selected paragraph's part
            end = first.position() + first.length() - 1
        block_start = first.position(); text = first.text()[start - block_start:end - block_start]
        return {'block': first.blockNumber(), 'start': start - block_start, 'end': end - block_start, 'text': text}

    def caret_block(self):
        return self.page.textCursor().block().blockNumber()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.FontChange, QEvent.ApplicationFontChange, QEvent.StyleChange, QEvent.Polish) and watched is self and self.document_id is not None and not self.loading:
            QTimer.singleShot(0, self.refont)
        return super().eventFilter(watched, event)

    def refont(self):
        """Reading preferences changed: the page is rebuilt from the current blocks (an owner-visible restyle, not an edit)."""
        if self.document_id is None or self.loading: return
        self.flush(); blocks = from_qt(self.page.document(), self.block_ids); position = self.page.textCursor().position()
        self.loading = True
        try:
            prose, code = fonts_of(self.host); to_qt({'blocks': blocks}, self.page.document(), prose, code)
            cursor = self.page.textCursor(); cursor.setPosition(min(position, self.page.document().characterCount() - 1)); self.page.setTextCursor(cursor)
        finally: self.loading = False

    # -- the list --------------------------------------------------------------------------------------------------------------
    def reload_list(self, select=None):
        rows = (call(self.host, 'documents.list', {'limit': 100}) or {}).get('documents', [])
        self.list.blockSignals(True); self.list.clear()
        for row in rows:
            item = QListWidgetItem('%s · rev %d · %s' % (row['title'], row['revision'], when(row['updated']))); item.setData(Qt.UserRole, row['id'])
            item.setToolTip('%d words · %d paragraphs · last change: %s' % (row['words'], row['blocks'], (row.get('last_change') or {}).get('words', '')))
            self.list.addItem(item)
            if row['id'] == (select or self.document_id): self.list.setCurrentItem(item)
        self.list.blockSignals(False); self.rows = rows

    def open_first_or_new(self):
        if self.rows: self.open_document(self.rows[0]['id'])
        else: self.new_document()

    def new_document(self):
        self.flush()
        r = call_write(self.host, 'documents.create', {})
        if not r.get('ok'): self.foot.setText('Could not start a document: ' + r['error']['message']); return None
        self.reload_list(select=r['result']['id']); self.open_document(r['result']['id']); self.page.setFocus(); return r['result']['id']

    def open_document(self, ident):
        if ident is None: return False
        if ident == self.document_id and not self.dirty:
            if self.report_derivation:
                value = call(self.host, 'documents.get', {'id': ident})
                self.show_report_state((value or {}).get('source_state'))
            self.page.setFocus()
            return True
        self.flush()
        value = call(self.host, 'documents.get', {'id': ident})
        if not value: self.foot.setText('That document is not available right now.'); return False
        self.load(value['document'], value.get('source_state')); self.reload_list(select=ident); return True

    def load(self, doc, source_state=None):
        self.loading = True
        try:
            prose, code = fonts_of(self.host); self.document_id = doc['id']; self.revision = doc['revision']; self.block_ids = [b['id'] for b in doc['blocks']]
            self.title_box.setText(doc['title']); to_qt(doc, self.page.document(), prose, code); self.dirty = False; self.save_timer.stop()
            self.setProperty('document_id', doc['id']); self.describe(doc); self.refresh_conditions()
            self.report_derivation = doc.get('derivation')
            self.show_report_state(source_state)
        finally: self.loading = False

    def show_report_state(self, value):
        self.report_bar.setVisible(bool(self.report_derivation))
        if not self.report_derivation:
            return
        from .boss_theme import READY, AMBER_TEXT
        state = (value or {}).get('state')
        messages = {'CURRENT': 'Calculation bound to the current sheet.',
                    'RECHECK_SHEET_CHANGED': 'The sheet changed. Recheck the calculation.',
                    'PDF_SOURCE_REVIEW_REQUIRED': 'The source page needs review.',
                    'SHEET_UNAVAILABLE': 'The source sheet is unavailable.'}
        self.report_hint.setText(messages.get(state, 'Calculation from a saved sheet.'))
        self.report_hint.setStyleSheet('color:' + (READY if state == 'CURRENT' else AMBER_TEXT))

    def open_report_sheet(self):
        if self.report_derivation:
            from .office_qt import open_office
            open_office(self.host, self.report_derivation['sheet'])

    def open_report_page(self):
        if self.report_derivation:
            from .pdf_qt import open_pdf
            source = self.report_derivation['pdf']
            open_pdf(self.host, source['namespace'], source['item'], source['source_sha256'],
                     source['page_index'], source['rect'])

    def recheck_report(self):
        if not self.report_derivation or not self.flush():
            return
        value = call_write(self.host, 'office.datasheet.recheck', {'id': self.document_id, 'expected_revision': self.revision})
        if not value['ok']:
            self.report_hint.setText(value['error']['message'])
            return
        self.open_document(value['result']['document']['id'])

    def describe(self, doc, prefix=None):
        change = doc.get('last_change') or {}; actor = {'SLATE': 'Graphite', 'SLATE_MODEL': 'Graphite (model)', 'HUMAN': 'You', 'IMPORTED': 'Import'}.get(change.get('actor'), change.get('actor', ''))
        words = ('%s %s' % (actor, change.get('words', ''))).strip()
        self.foot.setText(((prefix + ' · ') if prefix else '') + 'Saved · revision %d · %s%s' % (doc['revision'], words, (' · ' + when(change['at'])) if change.get('at') else ''))

    # -- writing and saving ------------------------------------------------------------------------------------------------
    def changed(self, *_):
        if self.loading or self.document_id is None: return
        self.dirty = True; self.foot.setText('Writing… (saved a moment after you pause)'); self.save_timer.start()

    def flush(self):
        """Save the page against the revision it saw. True when nothing is left unsaved."""
        if self.document_id is None or not self.dirty or self.loading: return True
        self.save_timer.stop()
        try: blocks = from_qt(self.page.document(), self.block_ids)
        except ValueError as exc: self.foot.setText('Not saved: ' + str(exc)); return False
        title = self.title_box.text().strip()
        r = call_write(self.host, 'documents.save', {'id': self.document_id, 'expected_revision': self.revision, 'blocks': blocks, **({'title': title} if title else {})})
        if not r.get('ok'):
            message = r['error']['message']
            if message.startswith('REVISION_CHANGED'):
                self.foot.setText('The saved document moved on (another edit landed first); reloading the saved revision. Your last words are in the Timeline as text below.')
                self.host.statusBar().showMessage('Document reloaded: a newer revision was saved first. Unsaved words: ' + store.plain_text({'blocks': blocks})[:300], 15000)
                value = call(self.host, 'documents.get', {'id': self.document_id})
                if value: self.load(value['document'])
                return False
            self.foot.setText('Not saved: ' + message); return False
        doc = r['result']['document']; self.revision = doc['revision']; self.block_ids = [b['id'] for b in doc['blocks']]; self.dirty = False
        if doc['title'] != title and not self.title_box.hasFocus(): self.title_box.setText(doc['title'])  # an unnamed page is called by its first words
        self.describe(doc); self.reload_list(); self.refresh_conditions(r['result'].get('conditions_stale')); return True

    # -- marks and styles ---------------------------------------------------------------------------------------------------
    def toggle_mark(self, key):
        cursor = self.page.textCursor(); fmt = cursor.charFormat() if cursor.hasSelection() else self.page.currentCharFormat()
        on = key not in marks_of(fmt); self.apply_mark(cursor, key, on); self.page.setFocus()

    def apply_mark(self, cursor, key, on):
        fmt = QTextCharFormat()
        if key == 'bold': fmt.setFontWeight(QFont.Bold if on else QFont.Normal)
        elif key == 'italic': fmt.setFontItalic(on)
        elif key == 'underline': fmt.setFontUnderline(on)
        if cursor.hasSelection(): cursor.mergeCharFormat(fmt)
        else: self.page.mergeCurrentCharFormat(fmt)

    def clear_marks(self):
        cursor = self.page.textCursor()
        if not cursor.hasSelection(): self.foot.setText('Select the words first.'); return
        fmt = QTextCharFormat(); fmt.setFontWeight(QFont.Normal); fmt.setFontItalic(False); fmt.setFontUnderline(False); cursor.mergeCharFormat(fmt); self.page.setFocus()

    def set_style(self, style, cursor=None, note=True):
        cursor = cursor or self.page.textCursor(); prose, code = fonts_of(self.host)
        cursor.beginEditBlock(); cursor.setBlockFormat(block_format(style))
        body = QTextCursor(cursor); body.select(QTextCursor.BlockUnderCursor)
        base = char_format(frozenset(), prose, code, style); keep = QTextCharFormat(); keep.setFont(base.font())
        if body.hasSelection(): body.mergeCharFormat(keep)
        cursor.mergeBlockCharFormat(keep); cursor.endEditBlock()
        if note: self.page.setFocus()

    # -- Slate's turn ----------------------------------------------------------------------------------------------------------
    def slate_request(self, text):
        """Resolve a typed request on this document without a model where the rules can; None hands it to the model path."""
        if self.document_id is None: return None
        words = ' '.join(text.casefold().split()).rstrip('.!')
        if words in UNDO_WORDS:
            if not self.page.document().isUndoAvailable(): return 'Nothing to undo on this page.'
            self.page.undo(); self.flush(); return 'Took the last change back (revision %d). Ctrl Y or “redo” brings it back.' % (self.revision or 0)
        if words in REDO_WORDS:
            if not self.page.document().isRedoAvailable(): return 'Nothing to redo on this page.'
            self.page.redo(); self.flush(); return 'Redid the change (revision %d).' % (self.revision or 0)
        selection = self.slate_selection()
        reading = call(self.host, 'documents.interpret', {'text': text, **({'selected': selection['text']} if selection else {})})
        if not reading or not reading.get('recognized'): return None
        if reading.get('problem'): return reading['problem'] + ' Select the words to change and ask again.'
        if reading['needs_selection'] and selection is None:
            return 'Select the words first, then ask me again. (I can %s without a model.)' % reading['words']
        if not self.flush(): return 'I could not save the page first, so I made no change: ' + self.foot.text()
        if selection is None: selection = {'block': self.caret_block(), 'start': 0, 'end': 0}
        elif reading.get('narrow'):
            a, b = reading['narrow']; selection = {'block': selection['block'], 'start': selection['start'] + a, 'end': selection['start'] + b, 'text': selection['text'][a:b]}
        r = call_write(self.host, 'documents.edit', {'id': self.document_id, 'expected_revision': self.revision, 'selection': selection, 'change': reading['change'],
                                                     'origin': 'SLATE', 'request': text[:store.MAX_REQUEST]})
        if not r.get('ok'):
            message = r['error']['message']
            if message.startswith(('SELECTION_CHANGED', 'REVISION_CHANGED')):
                value = call(self.host, 'documents.get', {'id': self.document_id})
                if value: self.load(value['document'])
                return 'The page changed before I could edit it, so I made no change and reloaded the saved revision. Select the words again.'
            return 'I could not make that change: ' + message
        result = r['result']; self.apply_locally(selection, reading['change'])
        doc = result['document']
        try: same = from_qt(self.page.document(), self.block_ids) == doc['blocks']
        except ValueError: same = False
        if not same: self.load(doc)                    # the page shows exactly the saved revision, whatever the local application did
        else:
            self.loading = True
            try: self.revision = doc['revision']; self.block_ids = [b['id'] for b in doc['blocks']]; self.dirty = False; self.save_timer.stop(); self.describe(doc)
            finally: self.loading = False
            self.reload_list()
        self.refresh_conditions(result.get('conditions_stale'))
        return 'Done: %s · revision %d · a direct edit, no model needed · Ctrl Z or “undo” takes it back.' % (result['applied']['words'], doc['revision'])

    def apply_locally(self, selection, change):
        """The same change on the page, through its undo stack as ONE step; the selection stays where the owner left it.
        AGENT-02: one outer edit block holds the words part (marks, clear, replace), the paragraph style and an appended
        paragraph; the edit blocks set_style and append_locally open nest inside it (Qt counts edit blocks per document), so
        one Ctrl Z or “undo” takes the whole change back, never half of it. The paragraph style goes first: set_style resets
        the paragraph's font, so a mark in the same change is laid over it rather than wiped by it."""
        doc = self.page.document(); block = doc.findBlockByNumber(selection['block'])
        if not block.isValid(): return
        whole = QTextCursor(block); whole.beginEditBlock()
        try:
            if 'style' in change: self.set_style(change['style'], cursor=QTextCursor(block), note=False)
            cursor = QTextCursor(block); cursor.setPosition(block.position() + selection['start']); cursor.setPosition(block.position() + selection['end'], QTextCursor.KeepAnchor)
            cursor.beginEditBlock()
            if 'replace' in change:
                fmt = cursor.charFormat(); cursor.insertText(change['replace'], fmt)
                cursor.setPosition(block.position() + selection['start']); cursor.setPosition(block.position() + selection['start'] + len(change['replace']), QTextCursor.KeepAnchor)
            if cursor.hasSelection():
                fmt = QTextCharFormat()
                if change.get('clear'): fmt.setFontWeight(QFont.Normal); fmt.setFontItalic(False); fmt.setFontUnderline(False)
                if 'bold' in change: fmt.setFontWeight(QFont.Bold if change['bold'] else QFont.Normal)
                if 'italic' in change: fmt.setFontItalic(change['italic'])
                if 'underline' in change: fmt.setFontUnderline(change['underline'])
                if fmt.properties(): cursor.mergeCharFormat(fmt)
            cursor.endEditBlock()
            if 'append' in change: self.append_locally(block, change['append'], change.get('append_style', 'Normal'))
        finally: whole.endEditBlock()
        self.page.setTextCursor(cursor)

    def append_locally(self, block, text, style='Normal'):
        """AGENT-02: a paragraph added after ``block`` (documents.edit's append), through the same undo stack (inside
        apply_locally's outer edit block, so it is part of the one undo step)."""
        prose, code = fonts_of(self.host)
        cursor = QTextCursor(block); cursor.movePosition(QTextCursor.EndOfBlock); cursor.beginEditBlock()
        cursor.insertBlock(block_format(style), char_format(frozenset(), prose, code, style))
        if text: cursor.insertText(text, char_format(frozenset(), prose, code, style))
        cursor.endEditBlock()

    # -- the model's turn (AGENT-02, owner decision D19) --------------------------------------------------------------------
    def model_page(self):
        """What model_turn.decide reads: this page's document, revision, paragraphs and their words, caret and selection."""
        from .model_turn import page_of
        try: blocks = from_qt(self.page.document(), self.block_ids); texts = [b['text'] for b in blocks]; styles = [b.get('style', 'Normal') for b in blocks]
        except ValueError: texts = styles = None
        return page_of(self.document_id, self.revision, self.page.document().blockCount(), self.caret_block(), self.slate_selection(), texts, styles)

    def apply_model_edit(self, arguments, request='', model_id=None):
        """D19: a documents.edit the model proposed for this page applies at once, visibly and undoably. The page is
        saved first; model_turn.decide checks it against the page (this document, its revision, a paragraph it has, the
        quoted words, a change the store accepts) and completes it; the edit lands as a revision with the model's origin
        and the owner's request, then on the page through its one undo stack, exactly as slate_request does; the changed
        range is washed pencil yellow and fades. Returns what Slate says; ``self.model_edit`` keeps the outcome."""
        from . import model_turn
        self.model_edit = {'applied': False, 'verdict': None, 'result': None}
        if self.document_id is None: return 'No document is open, so the model’s edit was not applied.'
        if not self.flush(): return 'I could not save the page first, so the model’s edit was not applied: ' + self.foot.text()
        verdict = model_turn.decide({'operation': model_turn.OPERATION, 'arguments': arguments}, self.model_page()); self.model_edit['verdict'] = verdict
        if not verdict['apply']: return model_turn.not_applied_words(verdict)
        args = verdict['arguments']
        r = call_write(self.host, 'documents.edit', {**args, 'request': model_turn.request_words(request, model_id)})
        if not r.get('ok'):
            message = r['error']['message']
            if message.startswith(('SELECTION_CHANGED', 'REVISION_CHANGED')):
                value = call(self.host, 'documents.get', {'id': self.document_id})
                if value: self.load(value['document'])
                return 'The page changed before the model’s edit could land, so I made no change and reloaded the saved revision.'
            return 'The model’s edit was refused: ' + message
        result = r['result']; doc = result['document']; ids = [b['id'] for b in doc['blocks']]
        self.apply_locally(args['selection'], args['change'])
        try: same = from_qt(self.page.document(), ids) == doc['blocks']
        except ValueError: same = False
        if not same: self.load(doc)                    # the page shows exactly the saved revision, whatever the local application did
        else:
            self.loading = True
            try: self.revision = doc['revision']; self.block_ids = ids; self.dirty = False; self.save_timer.stop(); self.describe(doc)
            finally: self.loading = False
            self.reload_list()
        self.refresh_conditions(result.get('conditions_stale'))
        where = model_turn.changed_range(result)
        caret = self.page.textCursor(); caret.clearSelection(); self.page.setTextCursor(caret)   # a selection would cover the wash
        self.flash(where); self.model_edit.update(applied=True, result=result, undoable=same)
        return model_turn.words(result, {'operation': model_turn.OPERATION, 'arguments': arguments}, model_id, undoable=same,
                                corrections=verdict.get('corrections'))   # what decide changed in the proposal is said, never hidden

    def flash(self, where):
        """The visible part of a model edit: a pencil-yellow wash over the changed range that fades out over about 1.5 s
        (Reduce motion: it stays 1.5 s, then clears). It is an ExtraSelection on the view: the document, its undo stack
        and the store never see it."""
        doc = self.page.document(); block = doc.findBlockByNumber(where['block'])
        if not block.isValid(): return None
        end = where['end'] if where.get('end') is not None else block.length() - 1
        cursor = QTextCursor(doc); cursor.setPosition(block.position() + where['start']); cursor.setPosition(block.position() + end, QTextCursor.KeepAnchor)
        self.flash_cursor = cursor; self.flash_whole = where.get('end') is None
        reduce = bool(profile_of(self.host).get('reduce_motion'))
        self.flash_left = 1 if reduce else FLASH_STEPS; self.flash_timer.setInterval(FLASH_MS if reduce else FLASH_MS // FLASH_STEPS)
        self.flash_record.append({'block': where['block'], 'range': [cursor.selectionStart(), cursor.selectionEnd()], 'whole_paragraph': self.flash_whole,
                                  'reduce_motion': reduce, 'alphas': [], 'cleared': False})
        self.paint_flash(255); self.flash_timer.start(); return self.flash_record[-1]

    def paint_flash(self, alpha):
        if self.flash_cursor is None: return
        wash = QTextEdit.ExtraSelection(); wash.cursor = self.flash_cursor
        color = QColor(AMBER); color.setAlpha(max(0, min(255, int(alpha)))); wash.format.setBackground(color)
        if self.flash_whole: wash.format.setProperty(QTextFormat.FullWidthSelection, True)
        self.page.setExtraSelections([wash])
        if self.flash_record: self.flash_record[-1]['alphas'].append(color.alpha())

    def flash_step(self):
        self.flash_left -= 1
        if self.flash_left <= 0: self.clear_flash(); return
        self.paint_flash(255 * self.flash_left / FLASH_STEPS)

    def clear_flash(self):
        self.flash_timer.stop(); self.flash_cursor = None; self.page.setExtraSelections([])
        if self.flash_record: self.flash_record[-1]['cleared'] = True

    # -- the right column and Slate's assignment (AGENT-01) -----------------------------------------------------------------
    def related_text(self):
        """The page's words for the quiet connections in the right column: the title and the text, read once per look."""
        if self.document_id is None: return ''
        return (self.title_box.text().strip() + '\n' + self.page.toPlainText()).strip()

    def refresh_conditions(self, changed=None):
        """The quiet line under the page: a result bound to words that changed reads stale, and one word rechecks it.
        ``changed`` is a save result's conditions_stale (the cards this write turned stale); the saved state is read when
        the cards can be read, so a card that went stale earlier stays named until it is rechecked."""
        if self.document_id is None: self.stale_ids = []; self.stale.hide(); return []
        cards = stale_cards(self.host, self.document_id)
        if cards is None: cards = [{'id': i, 'state': 'STALE'} for i in (changed or []) if isinstance(i, str)]
        self.stale_ids = [c['id'] for c in cards]
        if not cards: self.stale.hide(); return []
        html, actions = stale_sentence(cards, self.recheck)
        sentence(html, actions, self.stale); self.stale.show(); return self.stale_ids

    def recheck(self, ids=None):
        """The recheck word: the card's inputs are read again from the saved page, the total recomputed and the result
        paragraph rewritten by Slate (conditions.recheck); the page applies the rewritten paragraph through its undo stack."""
        ids = [i for i in (ids or self.stale_ids) if isinstance(i, str)]
        if not ids: return False
        if not self.flush(): return False
        message = None; words = []
        for ident in ids:
            r = call_write(self.host, 'conditions.recheck', {'id': ident})
            if not r.get('ok'): message = (r.get('error') or {}).get('message', 'not rechecked'); break
            result = r.get('result') or {}; words.append(str(result.get('words') or 'rechecked'))
            doc = result.get('document')
            if isinstance(doc, str): doc = (call(self.host, 'documents.get', {'id': doc}) or {}).get('document')
            if isinstance(doc, dict) and doc.get('id') == self.document_id: self.show_revision(doc)
        self.refresh_conditions()
        if message: self.foot.setText('Not rechecked: ' + message); return False
        self.foot.setText('Rechecked · ' + ' · '.join(words) + ' · ' + self.foot.text()); return True

    def sync(self, doc=None):
        """Another actor saved a newer revision of this document (Slate's assignment writing its result): show it. The
        owner's unsaved words come first: a dirty page saves instead, and a REVISION_CHANGED save reloads by itself."""
        if self.document_id is None or self.loading: return False
        if doc is None:
            value = call(self.host, 'documents.get', {'id': self.document_id}); doc = value['document'] if value else None
        if not isinstance(doc, dict) or doc.get('id') != self.document_id or doc.get('revision') == self.revision: return False
        if self.dirty: self.flush(); return True
        self.show_revision(doc); return True

    def show_revision(self, doc):
        """A saved revision made on this page by Slate: one changed paragraph, or one appended after the last, lands
        through the undo stack, so Ctrl Z takes his change back like any other (owner decision 4); any other shape
        reloads. The page ends up showing exactly the saved revision either way."""
        ids = [b['id'] for b in doc['blocks']]; prose, code = fonts_of(self.host); applied = False; text_document = self.page.document()
        if ids == self.block_ids:
            differing = [i for i, b in enumerate(doc['blocks']) if b['text'] != text_document.findBlockByNumber(i).text()]
            if len(differing) == 1:
                i = differing[0]; old = text_document.findBlockByNumber(i).text()
                self.apply_locally({'block': i, 'start': 0, 'end': len(old)}, {'replace': doc['blocks'][i]['text']}); applied = True
            elif not differing: applied = True
        elif len(ids) == len(self.block_ids) + 1 and ids[:-1] == self.block_ids:
            new = doc['blocks'][-1]; position = self.page.textCursor().position()
            cursor = QTextCursor(text_document); cursor.movePosition(QTextCursor.End); cursor.beginEditBlock()
            cursor.insertBlock(block_format(new['style']), char_format(frozenset(), prose, code, new['style']))
            for text, on in store.runs(new): cursor.insertText(text, char_format(on, prose, code, new['style']))
            cursor.endEditBlock(); applied = True
            keep = self.page.textCursor(); keep.setPosition(min(position, text_document.characterCount() - 1)); self.page.setTextCursor(keep)
        try: same = applied and from_qt(text_document, ids) == doc['blocks']
        except ValueError: same = False
        if same:
            self.loading = True
            try:
                self.revision = doc['revision']; self.block_ids = ids; self.dirty = False; self.save_timer.stop(); self.describe(doc)
                if doc['title'] != self.title_box.text().strip() and not self.title_box.hasFocus(): self.title_box.setText(doc['title'])
            finally: self.loading = False
            self.reload_list(); self.refresh_conditions()
        else: self.load(doc); self.reload_list()
        return same

    # -- export ------------------------------------------------------------------------------------------------------------
    def export_document(self):
        if self.document_id is None or not self.flush(): return None
        from . import files_service
        folder = files_service.root(self.host.ledger_bridge.kernel) / files_service.EXPORTS  # Egress: the folder files leave from
        safe = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in (self.title_box.text().strip() or 'document')).strip() or 'document'
        path, _ = QFileDialog.getSaveFileName(self, 'Export the document', str(folder / (safe + '.md')), 'Markdown (*.md);;HTML (*.html);;Plain text (*.txt)')
        if not path: return None
        fmt = {'.html': 'html', '.htm': 'html', '.txt': 'plain'}.get(Path(path).suffix.casefold(), 'markdown')
        value = call(self.host, 'documents.render', {'id': self.document_id, 'format': fmt})
        if not value: self.foot.setText('Export failed: the document could not be read.'); return None
        try: Path(path).write_text(value['text'], encoding='utf-8')
        except OSError as exc: self.foot.setText('Export failed: ' + str(exc)); return None
        self.foot.setText('Exported revision %d as %s to %s' % (value['revision'], fmt, path)); return path


def stale_cards(host, document):
    """The condition cards on a document that no longer hold (STALE or BROKEN); None when the cards cannot be read."""
    value = call(host, 'conditions.list', {'document': document})
    if value is None: return None
    return [c for c in (value.get('conditions') or []) if isinstance(c, dict) and c.get('id') and c.get('state') in ('STALE', 'BROKEN')]


def stale_sentence(cards, recheck):
    """The quiet line's words and its one action: 'A result on this page is stale · recheck'."""
    if not cards: return '', {}
    ids = [c['id'] for c in cards]
    if len(cards) == 1:
        card = cards[0]; reason = ' '.join(str(card.get('reason') or '').split()).rstrip('.')
        head = 'A result on this page is stale' if card.get('state') == 'STALE' else 'A result paragraph on this page was removed; its card is broken'
        if reason and len(reason) <= 120: head += ': ' + reason
    else: head = '%d results on this page are stale' % len(cards)
    return escape_text(head) + ' · {recheck}', {'recheck': ('recheck', lambda ids=ids: recheck(ids))}


def when(stamp):
    try: moment = datetime.fromtimestamp(float(stamp))
    except (TypeError, ValueError, OSError): return ''
    today = datetime.now().date()
    if moment.date() == today: return 'today ' + moment.strftime('%H:%M')
    return moment.strftime('%d %b %Y %H:%M')


def show(host, ident=None):
    """Open (or reuse) the Documents room; with an id, open that document in it."""
    host._close_start()
    tab = next((host.tabs.widget(i) for i in range(host.tabs.count()) if isinstance(host.tabs.widget(i), DocumentsTab)), None)
    if tab is None:
        tab = DocumentsTab(host); host.tabs.addTab(tab, tab.title())
    host.tabs.setCurrentWidget(tab)
    if ident: tab.open_document(ident)
    tab.page.setFocus(); return tab
