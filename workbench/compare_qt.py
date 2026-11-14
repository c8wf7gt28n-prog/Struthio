"""Compare on the Desk: two files, a file and an earlier version, or a file and Slate's proposed change.

Lines are marked in words, *added* on a pencil wash and *removed* on an eraser wash, so colour is never the only signal.
Spreadsheets compare cell by cell; anything with a picture is shown side by side; the facts the modules know are listed.
A proposal can be applied or declined from here, after you have seen exactly what it changes.
A working copy (4.7) is reviewed here too: the original as the work began against the frozen revision, and Update original
is offered only for that frozen revision, only while the original is unchanged.
"""
from __future__ import annotations
from html import escape
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QTextBrowser, QVBoxLayout, QWidget
from .shell2 import AMBER, ERASER, ERASER_MARK, AMBER_EDGE, MONO, QUIET, TEXT, call_write, escape_text, role, sentence

MAX_SHOWN = 1500


def lines_html(lines):
    rows = []
    for r in lines[:MAX_SHOWN]:
        op = r['op']
        if op == 'folded':
            rows.append('<tr><td colspan="4" style="color:%s;padding:4px 8px;">… %s …</td></tr>' % (QUIET, escape(r['text'])));continue
        wash = {'added': AMBER, 'removed': ERASER}.get(op, 'transparent');edge = {'added': AMBER_EDGE, 'removed': ERASER_MARK}.get(op, 'transparent')
        rows.append('<tr style="background:%s;"><td width="44" style="color:%s;padding:1px 8px;border-left:3px solid %s;">%s</td><td width="44" style="color:%s;padding:1px 8px;">%s</td>'
                    '<td style="font-family:\'%s\';padding:1px 8px;white-space:pre-wrap;">%s</td><td width="96" style="color:%s;padding:1px 8px;white-space:nowrap;">%s</td></tr>'
                    % (wash, QUIET, edge, r.get('before', ''), QUIET, r.get('after', ''), MONO, escape(r['text']) or '&nbsp;', QUIET, '' if op == 'same' else op))
    more = '' if len(lines) <= MAX_SHOWN else '<p style="color:%s">%d more lines not shown.</p>' % (QUIET, len(lines) - MAX_SHOWN)
    return '<table width="100%%" cellspacing="0" style="color:%s;">%s</table>%s' % (TEXT, ''.join(rows), more)


def fit(view, rows, most=1400):
    """A text box as tall as what it holds (up to a limit), so the page scrolls instead of a small box inside it.
    It follows the document's own laid-out height, which changes once the box has its real width and font."""
    view.setFixedHeight(int(min(most, 24 + view.fontMetrics().height() * 2.1 * rows)))
    layout = view.document().documentLayout()
    layout.documentSizeChanged.connect(lambda size, view=view:view.setFixedHeight(int(min(most, size.height() + 16))))


class CompareTab(QWidget):
    def __init__(self, host, args):
        super().__init__();self.host = host;self.args = dict(args);self.operation = self.args.pop('_op', 'files.compare');self.setObjectName('LibraryTab');self.setProperty('ledgerRoom', True)
        outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);outer.addWidget(self.scroll);self.reload()

    def title(self):return 'Review' if self.operation == 'copies.review' else 'Compare'

    def inspector(self):
        """The Context panel: what is being compared, and (for a working copy) where it came from and where it stands."""
        d = getattr(self, 'data', None) or {}
        rows = [('Before', str(d.get('before', ''))), ('After', str(d.get('after', '')))]
        if 'lines' in d:rows.append(('Lines', '%d added · %d removed' % (d.get('added', 0), d.get('removed', 0))))
        if d.get('sheets'):rows.append(('Cells', '%d differ' % sum(len(s['cells']) for s in d['sheets'])))
        if d.get('same_bytes'):rows.append(('Bytes', 'the same'))
        c = d.get('copy')
        if c:
            rows[:0] = [('Working copy of', c['source_words']), ('State', c['status']), ('Graphite may edit', 'Yes' if c['for_slate'] else 'No'),
                        ('Address', '@copies:' + c['id'])]
            if c.get('last_update'):rows.append(('Last update', 'revision applied · Undo is in Files'))
        return self.title(), rows

    def reload(self):
        r = call_write(self.host, self.operation, self.args)
        page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(40, 26, 40, 20);box.setSpacing(14)
        box.addWidget(role(QLabel(self.title()), 'title'))
        if not r.get('ok'):
            box.addWidget(QLabel((r.get('error') or {}).get('message', 'Could not compare').replace('_', ' ').capitalize()));box.addStretch(1)
            self.scroll.setWidget(page);return
        d = self.data = r['result']
        lead = QLabel('Before: %s\nAfter: %s' % (d['before'], d['after']));lead.setStyleSheet('color:%s' % QUIET);lead.setWordWrap(True);box.addWidget(lead)
        parts = []
        if d.get('same_bytes'):parts.append('The two are byte for byte the same.')
        if 'lines' in d:parts.append('%d line%s added, %d removed.' % (d['added'], '' if d['added'] == 1 else 's', d['removed']))
        changed_cells = sum(len(s['cells']) for s in d.get('sheets', []))
        if d.get('sheets'):parts.append('%d cells differ.' % changed_cells)
        changed_facts = [f for f in d.get('facts', []) if f['op'] == 'changed']
        if d.get('facts'):parts.append(('1 fact differs.' if len(changed_facts) == 1 else '%d facts differ.' % len(changed_facts)))
        words = {}
        if d.get('copy'):
            text, words = self.copy_words(d, parts)
        elif self.args.get('proposal'):
            text = ' '.join(parts) + '  {apply}  ·  {decline}'
            words = {'apply': ('apply this change', self.apply), 'decline': ('decline', self.decline)}
        else:text = ' '.join(parts)
        box.addWidget(sentence(text if d.get('copy') else escape_text(text), words))  # copy_words escapes its own text
        if d.get('kind') == 'folder':
            self.folder_review(box, d);box.addStretch(1);self.scroll.setWidget(page);self.tell_context();return
        if d.get('visual') and not self.args.get('proposal') and d.get('kind') != 'smart':box.addWidget(self.side_by_side())
        if 'lines' in d:
            box.addWidget(role(QLabel('LINES'), 'section'))
            view = QTextBrowser();view.setHtml(lines_html(d['lines']));view.setFrameShape(QFrame.NoFrame);view.setAccessibleName('Lines, added and removed')
            fit(view, min(len(d['lines']), MAX_SHOWN));box.addWidget(view)
            if d.get('cut'):box.addWidget(QLabel('Compared the first lines only; the files are longer.'))
        for sheet in d.get('sheets', []):
            box.addWidget(role(QLabel('SHEET · ' + sheet['sheet'].upper()), 'section'))
            if sheet['state'] in ('added', 'removed'):box.addWidget(QLabel('This sheet was ' + sheet['state'] + '.'));continue
            if not sheet['cells']:box.addWidget(QLabel('No cell differs.'));continue
            rows = ''.join('<tr style="background:%s;"><td width="64" style="padding:2px 8px;font-family:\'%s\';">%s</td><td width="30%%" style="padding:2px 8px;">%s</td>'
                           '<td width="30" style="padding:2px 8px;">→</td><td width="30%%" style="padding:2px 8px;">%s</td><td style="padding:2px 8px;color:%s;">%s</td></tr>'
                           % ({'added': AMBER, 'removed': ERASER}.get(c['op'], 'transparent'), MONO, c['cell'], escape(str(c['before'])), escape(str(c['after'])), QUIET, c['op'])
                           for c in sheet['cells'][:500])
            view = QTextBrowser();view.setHtml('<table width="100%%" cellspacing="0" style="color:%s">%s</table>' % (TEXT, rows));view.setFrameShape(QFrame.NoFrame)
            fit(view, min(len(sheet['cells']), 500));box.addWidget(view)
        if changed_facts:
            box.addWidget(role(QLabel('FACTS THAT DIFFER'), 'section'))
            for f in changed_facts[:20]:
                line = QLabel('%s:  %s  →  %s' % (f['fact'], f['before'] if f['before'] is not None else '—', f['after'] if f['after'] is not None else '—'))
                line.setWordWrap(True);box.addWidget(line)
        box.addStretch(1);self.scroll.setWidget(page);self.tell_context()

    def tell_context(self):
        inspector = getattr(self.host, 'arc_inspector', None)
        if inspector is not None and self.host.tabs.currentWidget() is self:inspector.refresh()

    def folder_review(self, box, d):
        """A folder's proposal: every operation in words, then the lines of each changed text file."""
        box.addWidget(role(QLabel('OPERATIONS'), 'section'))
        for f in d['operations']:
            extra = ('  ·  %d added, %d removed' % (f.get('added') or 0, f.get('removed') or 0)) if f.get('lines') is not None else ''
            line = QLabel(f['words'] + extra);line.setStyleSheet('background:%s;padding:2px 8px;' % {'create': AMBER, 'delete': ERASER}.get(f['op'], 'transparent'))
            box.addWidget(line)
        if d.get('more'):box.addWidget(QLabel('… and %d more files.' % d['more']))
        if d.get('skipped'):
            note = QLabel('Left out of the copy (never followed or copied): ' + ', '.join('%s (%s)' % tuple(s) for s in d['skipped'][:8]))
            note.setWordWrap(True);note.setStyleSheet('color:%s' % QUIET);box.addWidget(note)
        for f in d['operations']:
            if not f.get('lines'):continue
            box.addWidget(role(QLabel(f['path'].upper() if len(f['path']) < 40 else f['path']), 'section'))
            view = QTextBrowser();view.setHtml(lines_html(f['lines']));view.setFrameShape(QFrame.NoFrame);fit(view, min(len(f['lines']), 400), 700);box.addWidget(view)

    def side_by_side(self):
        from .thumbnails import thumbnail
        from .files_service import root
        from .engine import engineering
        holder = QWidget();row = QHBoxLayout(holder);row.setContentsMargins(0, 0, 0, 0);row.setSpacing(24)
        base = root(engineering(self.host.root))
        if self.data.get('paths'):
            paths = [(Path(self.data['paths']['before']), 'as the work began'), (Path(self.data['paths']['after']), 'the working copy')]
        elif self.args.get('version'):
            from .files_service import VERSIONS
            paths = [(base / VERSIONS / self.args['path'] / self.args['version'], 'before'), (base / self.args['path'], 'after')]
        else:paths = [(base / self.args['other'], 'before'), (base / self.args['path'], 'after')]
        for path, label in paths:
            col = QVBoxLayout();picture = QLabel();picture.setPixmap(thumbnail(path, self.data['kind'], 260));col.addWidget(picture)
            caption = QLabel(label);caption.setStyleSheet('color:%s' % QUIET);col.addWidget(caption);row.addLayout(col)
        row.addStretch(1);return holder

    def apply(self):
        r = call_write(self.host, 'files.decide', {'id': self.args['proposal'], 'apply': True})
        self.host.statusBar().showMessage('Applied; the version before is kept.' if r.get('ok') else (r.get('error') or {}).get('message', 'Not applied'), 6000)
        if r.get('ok'):self.host.tabs.removeTab(self.host.tabs.indexOf(self))

    def decline(self):
        r = call_write(self.host, 'files.decide', {'id': self.args['proposal'], 'apply': False})
        if r.get('ok'):self.host.statusBar().showMessage('Declined. Nothing changed.', 5000);self.host.tabs.removeTab(self.host.tabs.indexOf(self))


    # -- working copies -----------------------------------------------------------------
    def copy_words(self, d, parts):
        c = d['copy'];frozen = d.get('frozen');proposal = c.get('proposal') or {}
        lines = [escape_text(' '.join(parts))]
        words = {'new': ('save as a new file beside it', self.save_new)}
        if c.get('kind') == 'folder' and d.get('operations') is not None:
            n = len(d['operations']) + d.get('more', 0)
            lines.append(escape_text('%d file%s would change in %s.' % (n, '' if n == 1 else 's', c['source_words'])))
        if c.get('recovery'):
            lines.append(escape_text('An earlier update of this file needs a look: ' + (c['recovery'].get('outcome') or '')) + '  {close}')
            words['close'] = ('close it, I have looked', self.close_recovery)
        elif c['original'] == 'changed':
            outside = d.get('outside') or {}
            if c.get('kind') == 'folder':
                lines.append(escape_text('Files in the original folder changed outside Graphite since the work began. Nothing will be replaced.') + '  {refresh}  ·  {new}')
            else:
                lines.append(escape_text('The original changed outside Graphite since the work began (%s lines added, %s removed there). It will not be replaced.'
                                         % (outside.get('added', '?'), outside.get('removed', '?'))) + '  {merge}  ·  {refresh}  ·  {new}')
                words['merge'] = ('bring the outside change in', self.merge)
            words['refresh'] = ('compare with the changed original', self.refresh)
        elif frozen:
            what = 'what would change in' if c.get('kind') == 'folder' else 'what would replace'
            again = ' Part of it was applied before; updating again finishes it.' if c['status'].startswith('Partially') else ''
            lines.append(escape_text('Revision %d is frozen: this is exactly %s %s.%s' % (proposal.get('revision', 0), what, c['source_words'], again)) + '  {update}  ·  {new}')
            words['update'] = ('update the original now', self.update_original)
        elif c.get('edited'):
            lines.append(escape_text('This is the working copy as it is now.') + '  {freeze}  ·  {new}')
            words['freeze'] = ('freeze it for review', self.freeze)
        else:lines.append(escape_text('The working copy is the same as the original.'))
        return '<br>'.join(lines), words

    def copy_done(self, r, message):
        if not r.get('ok'):self.host.statusBar().showMessage((r.get('error') or {}).get('message', 'Not done').split(': ', 1)[-1], 9000)
        else:self.host.statusBar().showMessage(message, 8000)
        self.reload();refresh_files(self.host);return r

    def freeze(self):
        self.copy_done(call_write(self.host, 'copies.propose', {'id': self.args['id']}), 'Frozen for review. Later edits make a new revision.')

    def update_original(self):
        from PySide6.QtWidgets import QMessageBox
        c = self.data['copy'];proposal = c['proposal']
        if QMessageBox.question(self, 'Update original', 'Replace %s with revision %d?\n\nThe version before is kept, and Undo is there if you change your mind.'
                                % (c['source_words'], proposal['revision'])) != QMessageBox.Yes:return
        self.copy_done(call_write(self.host, 'copies.apply', {'id': c['id'], 'proposal': proposal['id']}), 'Updated %s. The version before is kept.' % c['source_words'])

    def save_new(self):
        from PySide6.QtWidgets import QInputDialog
        c = self.data['copy']
        if not self.data.get('frozen'):
            r = call_write(self.host, 'copies.propose', {'id': c['id']})
            if not r.get('ok'):self.copy_done(r, '');return
            c = call_write(self.host, 'copies.get', {'id': c['id']})['result']
        stem, dot, suffix = c['name'].rpartition('.')
        name, ok = QInputDialog.getText(self, 'Save as a new file', 'Beside the original, named:', text=(stem + ' (from Graphite).' + suffix) if dot else c['name'] + ' (from Graphite)')
        if not ok or not name.strip():return
        r = call_write(self.host, 'copies.save_new', {'id': c['id'], 'proposal': c['proposal']['id'], 'name': name.strip()})
        self.copy_done(r, ('Saved as %s. The original is unchanged.' % r['result']['saved_words']) if r.get('ok') else '')

    def merge(self):
        r = call_write(self.host, 'copies.merge', {'id': self.args['id']})
        self.copy_done(r, (r.get('result') or {}).get('note', 'Merged.'))

    def refresh(self):
        self.copy_done(call_write(self.host, 'copies.refresh', {'id': self.args['id']}), 'Now compared with the changed original. Your working copy is as it was.')

    def close_recovery(self):
        self.copy_done(call_write(self.host, 'copies.recover', {'close': self.data['copy']['recovery']['id']}), 'Closed. Nothing was overwritten.')


def refresh_files(host):
    from .files_qt import FilesTab
    for i in range(host.tabs.count()):
        if isinstance(host.tabs.widget(i), FilesTab):host.tabs.widget(i).reload()


def show(host, **args):
    host._close_start()
    tab = CompareTab(host, args);host.tabs.addTab(tab, tab.title());host.tabs.setCurrentWidget(tab);return tab
