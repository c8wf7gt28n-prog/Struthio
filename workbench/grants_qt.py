"""Grants in the window (Graphite 1.0, K3): a grant asked for in her column, and the Grants page.

In her column, under ACTIVE WORK (GrantFold):
  - when a step of an assignment needs your grant: ◆ NEEDS YOUR GRANT, the assignment, the grant in plain words exactly
    as it would be given ("set values on the sheet “Rail Demo bench readings”, for this assignment"), and one press,
    "Grant this for this assignment" (grant.give with the digest of those words, then the assignment carries on);
  - else, while grants are in force: one line, "GRANTS [n] · see them", which opens the Grants page.

The Grants page (GrantsTab, a tab in the centre; open_destination(host, 'grants')):
  - in force: each grant in its words, when it was given, how often it was used, and Revoke (your press);
  - her own area: Files/Slate, hers by the Files rules (a standing line, never revoked here);
  - waiting for your grant: each step that stopped for one, with its press;
  - give a grant: what (a family), where (a folder inside Files), for how long (one hour, until tonight, always, or one
    open assignment); the words are shown before the press and the press gives exactly those words;
  - ended: revoked, run out or with their assignment done.

Every colour that means something also has a word or a shape; no key is named in any words here.
"""
from __future__ import annotations

import re
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSizePolicy,
                               QVBoxLayout, QWidget)

from . import boss_theme as bt
from .her_column_qt import Clickable, heading, ink, plain, px, read, row_label, small_button

LIST_EVERY = 4                # her column reads the grants in force every this many of its ticks (asks come every tick)


class GrantFold(QWidget):
    """Her column's fold: a grant asked for, in plain words, with its one press; else the grants in force, in one line."""

    def __init__(self, column):
        super().__init__();self.column = column;host = column.host;self.setObjectName('HerGrants')
        self.ticks = 0;self.in_force = 0;self.ask = None
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(px(host, 3))
        top = QHBoxLayout();top.setSpacing(px(host, 6))
        self.head = heading(host, 'GRANTS');top.addWidget(self.head)
        self.link = Clickable(self.open_page, 'The Grants page: what she may change without asking you again, and Revoke')
        ll = QHBoxLayout(self.link);ll.setContentsMargins(0, 0, 0, 0)
        self.link_words = ink(QLabel('see them ›'), px(host, 12), bt.QUIET, None, bt.FACE, 'text-decoration:underline;')
        self.link_words.setAttribute(Qt.WA_TransparentForMouseEvents);ll.addWidget(self.link_words)
        top.addWidget(self.link);top.addStretch(1);box.addLayout(top)
        self.card = QFrame();self.card.setObjectName('HerGrantAsk')
        self.card.setStyleSheet('QFrame#HerGrantAsk {border:1px solid %s;border-left:3px solid %s;border-radius:4px;background:transparent;}' % (bt.LINE_MID, bt.OWNER))
        cb = QVBoxLayout(self.card);cb.setContentsMargins(px(host, 8), px(host, 4), px(host, 6), px(host, 5));cb.setSpacing(px(host, 2))
        line = QHBoxLayout();line.setSpacing(px(host, 5))
        self.shape = ink(QLabel('◆'), px(host, 13), bt.OWNER, 700, bt.MONO)
        self.word = ink(QLabel('NEEDS YOUR GRANT'), px(host, 11), bt.OWNER, 600, bt.MONO, 'letter-spacing:1px;')
        self.title = row_label(host, '', quiet=True, size=12)
        line.addWidget(self.shape);line.addWidget(self.word);line.addWidget(self.title, 10);line.addStretch(1);cb.addLayout(line)
        self.words = QLabel();self.words.setWordWrap(True);self.words.setTextFormat(Qt.PlainText)
        ink(self.words, px(host, 13), bt.TEXT, None, bt.FACE);self.words.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        cb.addWidget(self.words)
        row = QHBoxLayout();row.setSpacing(px(host, 6))
        self.give = small_button(host, 'Grant this for this assignment', 'Your press: gives exactly the grant in the words above, '
                                 'for this assignment only, and carries on. What always asks still asks.', primary=True)
        self.give.setObjectName('HerGrantGive');self.give.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed);self.give.clicked.connect(self.press_give)
        row.addWidget(self.give);row.addStretch(1);cb.addLayout(row)
        box.addWidget(self.card)
        self.card.hide();self.hide()

    def show_from(self, rows, force=False):
        """rows: assignment.list rows (her column's, read this tick). The first step that needs your grant is asked for."""
        self.ticks += 1
        if force or self.ticks % LIST_EVERY == 1:
            got = read(self.column.host, 'grant.list', {'waiting': False}) or {}
            self.in_force = len(got.get('in_force') or ())
        ask = None
        for row in rows or ():
            action = next((a for a in row.get('actions') or () if a.get('operation') in ('grant.give', 'grant.give.set')), None)  # 1.0 K10
            if action:ask = (row, action);break
        if getattr(self.column, 'waits', None) is not None:ask = None      # 1.0 D1: a grant asked for is in "Waits for you" (one place)
        self.ask = ask;compact = self.column.compact();host = self.column.host
        if ask:
            row, action = ask
            words = plain(action.get('grant_words') or '')
            if compact:words = re.sub(r' \(“[^”]*”\)', '', words)      # a short column: the assignment is named in ACTIVE WORK above
            self.title.setText(plain(row.get('title') or ''));self.title.setVisible(not compact)
            self.words.setText(('I need your grant to %s.' if compact else 'I need your grant to %s. Nothing was sent.') % words)      # 1.1 KV
            ink(self.words, px(host, 12 if compact else 13), bt.TEXT, None, bt.FACE)
            self.words.setAccessibleName(self.words.text());self.card.show()
        else:
            self.card.hide()
        self.head.setText('GRANTS [%d]' % self.in_force if self.in_force else 'GRANTS')
        for w in (self.head, self.link):w.setVisible(not (compact and ask))      # a short column: the card alone
        self.setVisible(bool(ask) or self.in_force > 0)

    def press_give(self):
        if not self.ask:return
        row, action = self.ask
        self.column.take_step({'kind': 'assignment', 'call': action, 'title': plain(row.get('title') or '')})
        self.show_from(self.column.rows, force=True)

    def open_page(self):
        show(self.column.host)


# ---------------------------------------------------------------------------------------------------------- the page

PERIODS = (('for one hour', 'hour'), ('until tonight (23:59)', 'tonight'), ('always, until you revoke it', 'always'))


def _until(kind):
    now = time.time_ns() // 1000000
    if kind == 'hour':return now + 3600 * 1000
    t = time.localtime();midnight = time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 23, 59, 0, 0, 0, -1))
    return int(midnight) * 1000


class GrantsTab(QWidget):
    """The Grants page: in force (with Revoke), her own area, waiting for your grant, give a grant, ended."""

    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('LibraryTab');self.setProperty('ledgerRoom', True)
        self.shown = None;self.form = {}
        outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame);outer.addWidget(self.scroll)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.timer = QTimer(self);self.timer.setInterval(3000);self.timer.timeout.connect(self.reload)
        self.reload()

    def title(self):return 'Grants'

    def showEvent(self, event):super().showEvent(event);self.reload();self.timer.start()

    def hideEvent(self, event):super().hideEvent(event);self.timer.stop()

    def note(self, words):
        try:self.host.statusBar().showMessage(words, 8000)
        except Exception:  # noqa: BLE001
            pass

    def act(self, op, args, then=None):
        from .shell2 import call_write
        r = call_write(self.host, op, args)
        if not r.get('ok'):      # 1.1 B3: a refusal in plain words, never the operation's name; the Kernel's own text in Log
            from .her_column_qt import refused, say as column_say
            self.note(column_say('press_refused', why=refused(self.host, op, (r.get('error') or {}).get('message', 'Not done'))))
        else:
            said = (r.get('result') or {}).get('said') or []
            if said:self.note(' '.join(said)[:300])
            if then:
                column = getattr(self.host, 'her_column', None)
                if column is not None:column.carry(then, '')
        self.reload();return r

    def reload(self):
        from .shell2 import call, role, sentence, escape_text
        view = call(self.host, 'grant.list', {'all': True}) or {'in_force': [], 'ended': [], 'waiting': [], 'own_area': None, 'families': {}}
        key = repr((view.get('in_force'), view.get('ended'), view.get('waiting')))
        if key == self.shown and getattr(self, 'page', None) is not None:return
        self.shown = key
        keep = {k: (w.currentIndex() if isinstance(w, QComboBox) else w.text()) for k, w in self.form.items()}
        page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(48, 32, 48, 24);box.setSpacing(16)
        box.addWidget(role(QLabel('Grants'), 'title'))
        lead = role(QLabel('What Kas may change without asking you again: each grant names what she may do, where, and for '
                           'how long. Only your press gives one, in these words; she can never give or widen one. Reading needs '
                           'no grant; what always asks still asks; a change only the model chose is never done; Undo stays as it was.'), 'lead')
        lead.setWordWrap(True);lead.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);box.addWidget(lead)
        waiting = view.get('waiting') or []
        if waiting:
            box.addWidget(role(QLabel('WAITING FOR YOUR GRANT'), 'section'))
            for w in waiting:
                label = sentence('◆ <b>%s</b>: it asks to %s. Nothing was sent.  ·  {give}' % (escape_text(w['title']), escape_text(w['words'])),
                                 {'give': ('Grant this for this assignment', lambda w=w: self.act('grant.give', w['press']['arguments'], w['press'].get('then')))})
                box.addWidget(label)
        box.addWidget(role(QLabel('IN FORCE'), 'section'))
        rows = view.get('in_force') or []
        if not rows:box.addWidget(self.quiet('No grant of yours is in force. Every change she proposes waits for your word.'))
        for g in rows:
            used = ('used %d times' % g['uses'] if g.get('uses') != 1 else 'used once') if g.get('uses') else 'not used yet'
            label = sentence('● %s<br><span style="color:%s">given %s by %s  ·  %s</span>  ·  {revoke}' % (
                escape_text(g['words']), bt.QUIET, escape_text(g.get('given_words', '')), escape_text(g.get('source', '')), used),
                {'revoke': ('Revoke', lambda g=g: self.act('grant.revoke', {'id': g['id']}))})
            label.setAccessibleName('In force: ' + g['words']);box.addWidget(label)
        own = view.get('own_area')
        if own:
            box.addWidget(self.quiet('▪ ' + own['words'] + '. It covers a call there; it never authorises a step by itself.'))
        box.addWidget(role(QLabel('GIVE A GRANT'), 'section'))
        box.addWidget(self.give_form(view, keep))
        ended = view.get('ended') or []
        if ended:
            box.addWidget(role(QLabel('ENDED'), 'section'))
            for g in ended[:10]:
                box.addWidget(self.quiet('○ %s  ·  ended: %s' % (g['words'], g.get('ended_words') or 'ended')))
        box.addStretch(1)
        self.page = page;self.scroll.setWidget(page)

    def quiet(self, text):
        label = QLabel(text);label.setWordWrap(True);label.setStyleSheet('color:%s' % bt.QUIET);label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        return label

    def give_form(self, view, keep):
        from .shell2 import call
        holder = QWidget();col = QVBoxLayout(holder);col.setContentsMargins(0, 0, 0, 0);col.setSpacing(8)
        row = QHBoxLayout();row.setSpacing(10)
        what = QComboBox();what.setAccessibleName('What she may do')
        for key, words in (view.get('families') or {}).items():
            if key.startswith('files.'):what.addItem(words, key)
        where = QLineEdit();where.setAccessibleName('In which folder inside Files');where.setPlaceholderText('a folder inside Files, e.g. Rail Demo/notes')
        when = QComboBox();when.setAccessibleName('For how long')
        for words, kind in PERIODS:when.addItem(words, kind)
        open_rows = (call(self.host, 'assignment.list', {'open': True, 'limit': 10}) or {}).get('assignments') or []
        for r in open_rows:when.addItem('for the assignment “%s”' % r['title'][:60], 'assignment:' + r['id'])
        for box_, least in ((what, 14), (when, 16)):      # 1.0 D2: a combo as wide as a short choice, not its longest one (an assignment's
            box_.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);box_.setMinimumContentsLength(least)      # title made the page wider than the centre, its words cut at the right)
        where.setMinimumWidth(80)
        for w, words in ((what, 'Do'), (where, 'in'), (when, 'for')):
            row.addWidget(QLabel(words));row.addWidget(w, 1 if w is where else 0)
        col.addLayout(row)
        self.form = {'what': what, 'where': where, 'when': when}
        if 'what' in keep:what.setCurrentIndex(max(0, keep['what']));where.setText(keep.get('where', ''));when.setCurrentIndex(max(0, keep.get('when', 0)))
        self.preview = QLabel();self.preview.setWordWrap(True);self.preview.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addWidget(self.preview)
        self.give = QPushButton('Give this grant');self.give.setCursor(Qt.PointingHandCursor);self.give.setProperty('arcButton', 'quiet')
        self.give.clicked.connect(self.give_it);col.addWidget(self.give, 0, Qt.AlignLeft)
        for w in (what, when):w.currentIndexChanged.connect(self.words_now)
        where.textChanged.connect(self.words_now)
        self.words_now()
        return holder

    def arguments(self):
        what, where, when = self.form['what'], self.form['where'], self.form['when']
        kind = when.currentData() or 'always'
        args = {'operation': what.currentData() or 'files.edit', 'folder': where.text().strip()}
        if kind.startswith('assignment:'):args.update(scope='assignment', assignment=kind.split(':', 1)[1])
        elif kind in ('hour', 'tonight'):args.update(scope='until', until=_until(kind))
        else:args['scope'] = 'always'
        return args

    def words_now(self, *_):
        from .shell2 import call
        self.pending = None
        if not self.form['where'].text().strip():
            self.preview.setText('Name a folder inside Files; the grant is then shown here in its words before you give it.')
            self.give.setEnabled(False);return
        shown = call(self.host, 'grant.words', self.arguments()) or {}
        if shown.get('grantable'):
            self.pending = (self.arguments(), shown['digest'])
            self.preview.setText('You would give: %s.' % shown['words']);self.give.setEnabled(True)
        else:
            self.preview.setText('No grant can be given for this: %s.' % (shown.get('why_not') or 'it cannot be read'));self.give.setEnabled(False)

    def give_it(self):
        if not self.pending:return
        args, sha = self.pending
        if self.act('grant.give', dict(args, expected_digest=sha)).get('ok'):self.form['where'].clear()


def show(host):
    """Open (or reuse) the Grants page in the centre."""
    try:host._close_start()
    except Exception:  # noqa: BLE001
        pass
    for i in range(host.tabs.count()):
        tab = host.tabs.widget(i)
        if isinstance(tab, GrantsTab):host.tabs.setCurrentWidget(tab);tab.shown = None;tab.reload();return tab
    tab = GrantsTab(host);host.tabs.addTab(tab, tab.title());host.tabs.setCurrentWidget(tab);return tab
