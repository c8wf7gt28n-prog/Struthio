"""The console: the working area above the lower band, one line that grows into a terminal (Half, Tall). The writing line in
the band is the only place to type; this is where its answers stay.

HATCH DESK D3: the writing line's four modes choose the page shown here (typebar_qt.CONSOLE_PAGE). Choosing a mode never
opens or closes the area; running a line opens it at Half (open), and Line closes it to the band.

  Log     the Log view (workbench/log_qt.py): Events (Graphite's events, the Timeline's words) or Network. The Timeline's own
          list stays alive for Activity's recent lines, out of sight here.
  staC    Typed commands run with Ctrl+Enter. Prefix `explain` to preview the plan.
          Result tables can be saved as a sheet, watched, or added to the Agenda.
  Kernel  Assistant's / lines (Commands > Run an operation…): files.list path=Slate, copies.review id=…, help files.find,
          ops copies. The same operations and the same permissions as the window; anything that needs your approval asks for
          a second Enter. Since 0.8.2 a desk act runs here by its name too (/go.field face=apps, /point.sheet title="…"):
          something you can do in the window, done on the window itself (desk_acts, desk_doers); help acts lists them.
  Find    Search: names and words across Files, what the Office received, the cabinet, settings, commands and the Timeline.
  Shell   Shell: the configured shell (typebar_qt.configured_shell; Bash when it is bash) in your Files folder, for your own
          commands. Output is shown as plain text (terminal control sequences are removed), stdin is closed, Stop and Master
          Stop end it, and each command is noted in the Timeline.

Up and Down walk each page's own history; Tab completes operation names, their arguments, staC words and @files: paths.
Ctrl+` opens it (and gives it room); Esc returns it to one line. The console sizes are one line, half, and tall.
"""
from __future__ import annotations
from .assistant_identity import named
from .text_prompts import writing_prompt
import json
import re
import shlex
import time
from html import escape
from pathlib import Path
from textwrap import wrap
from PySide6.QtCore import QProcess, QProcessEnvironment, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QTextBrowser, QTextEdit, QVBoxLayout, QWidget
from .shell2 import AMBER, ERASER, ERASER_MARK, LINE, QUIET, TEXT, button, call, call_write, mono_font
from .boss_theme import AMBER_TEXT, MONO, TERMINAL_GROUND
from .stac_bridge import route_program

MODES = (('log', 'Log', '', 'filter the Timeline'),
         ('stac', 'Lines', '@', '@files:parts.csv | rows | where Qty over 3'),
         ('kernel', 'Kernel', '/', 'files.list path=Slate  ·  help copies.review  ·  ops agenda'),
         ('find', 'Find', '?', 'names and words in Files, received files, the cabinet, settings and commands'),
         ('shell', 'Shell', '$', 'a command in your Files folder'))
PREFIX = {'@': 'stac', '/': 'kernel', '?': 'find', '$': 'shell'}
STAC_VERBS = ('where', 'take', 'select', 'sort', 'count', 'group', 'sum', 'avg', 'min', 'max', 'add', 'join', 'missing',
              'sheet', 'rows', 'facts', 'layers', 'lines', 'headings', 'texts', 'pick')
ANSI = re.compile(r'\x1b(\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(\x07|\x1b\\)|[@-Z\\-_])')
CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
BLOCKS = 300
SHOWN_ROWS = 200


def plain(text):
    """Terminal output as text: colour and cursor sequences removed, carriage-return overwrites resolved, other controls dropped."""
    text = ANSI.sub('', text)
    text = '\n'.join(line.rsplit('\r', 1)[-1] if '\r' in line else line for line in text.split('\n'))
    return CONTROL.sub('', text)


def coerce(value):
    if value in ('true', 'false'):return value == 'true'
    if value[:1] in '[{':return json.loads(value)
    if re.fullmatch(r'-?\d+', value):return int(value)
    if re.fullmatch(r'-?\d+\.\d+', value):return float(value)
    return value


def parse_command(text):
    """'files.list path=Slate all=true' or 'files.list {"path": "Slate"}' → (operation, arguments)."""
    head, _, rest = text.strip().partition(' ');rest = rest.strip()
    if not head:raise ValueError('Type an operation name, or help, or ops')
    if rest.startswith('{'):
        args = json.loads(rest)
        if not isinstance(args, dict):raise ValueError('Arguments in braces must be an object')
        return head, args
    args = {}
    for token in shlex.split(rest):
        key, eq, value = token.partition('=')
        if not eq or not key:raise ValueError('Write arguments as name=value (quote values with spaces): ' + token)
        try:args[key] = coerce(value)
        except json.JSONDecodeError:raise ValueError("Put JSON values in single quotes, as in a shell: find='{\"text\": \"C4\"}'") from None
    return head, args


TIME_WORDS = ('at', 'created', 'updated', 'finished', 'started', 'paired', 'when', 'time', 'modified', 'mtime', 'restored', 'due', 'seen')


def when(name, value):
    """A stored moment (seconds since 1970) as people read it: 'today 11:50', 'yesterday 09:12', '28 Oct 14:03', '2025-06-01'.
    Only for fields whose name says it is a time, and only for plausible moments; every other number stays as it is."""
    import datetime
    key = str(name).lower()
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not (key in TIME_WORDS or key.endswith(('_at', '_time', '_mtime'))):return None
    seconds = value / 1e9 if value > 1e15 else value  # nanoseconds, as file times are kept
    if not 946684800 <= seconds <= 4102444800:return None  # 2000 to 2100: anything else is not a moment
    moment = datetime.datetime.fromtimestamp(seconds);today = datetime.date.today()
    if moment.date() == today:return 'today ' + moment.strftime('%H:%M')
    if moment.date() == today - datetime.timedelta(days=1):return 'yesterday ' + moment.strftime('%H:%M')
    return moment.strftime('%d %b %H:%M') if moment.year == today.year else moment.strftime('%Y-%m-%d')


def table_html(rows, limit=SHOWN_ROWS, raw=()):
    rows = list(rows)
    columns = list(dict.fromkeys(k for r in rows[:limit] if isinstance(r, dict) for k in r))[:10] or ['value']
    def cell(v, name=''):
        moment = when(name, v)
        if moment:return escape(moment)
        text = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else ('' if v is None else str(v))
        return escape(text if len(text) < 72 else text[:70] + '…')
    head = ''.join('<th align="left" style="padding:2px 14px 2px 0;border-bottom:1px solid %s;color:%s;">%s</th>' % (LINE, QUIET, escape(str(c))) for c in columns)
    body = ''.join('<tr>' + ''.join('<td style="padding:1px 14px 1px 0;white-space:nowrap;">%s</td>' % (r.get(c, '') if c in raw else cell(r.get(c) if isinstance(r, dict) else r, c)) for c in columns) + '</tr>'
                   for r in rows[:limit])
    more = '<div style="color:%s;">… %d more rows</div>' % (QUIET, len(rows) - limit) if len(rows) > limit else ''
    return '<table cellspacing="0">%s%s</table>%s' % ('<tr>%s</tr>' % head, body, more)


def result_html(value):
    """A Kernel result as a reader wants it: its longest list of records as a table, the rest as name: value lines."""
    if isinstance(value, list) and value and all(isinstance(r, dict) for r in value):return table_html(value)
    if isinstance(value, dict):
        lists = [(k, v) for k, v in value.items() if isinstance(v, list) and v and all(isinstance(r, dict) for r in v)]
        main = max(lists, key=lambda kv:len(kv[1]))[0] if lists else None
        lines = []
        for k, v in value.items():
            if k == main:continue
            text = when(k, v) or (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v))
            lines.append('<span style="color:%s;">%s</span>  %s' % (QUIET, escape(str(k)), escape(text if len(text) < 300 else text[:298] + '…')))
        out = '<br>'.join(lines)
        if main:out += ('<br>' if out else '') + '<span style="color:%s;">%s · %d</span>' % (QUIET, escape(main), len(value[main])) + table_html(value[main])
        return out or '<span style="color:%s;">(empty)</span>' % QUIET
    text = json.dumps(value, ensure_ascii=False, indent=2) if not isinstance(value, str) else value
    return '<pre style="margin:0;">%s</pre>' % escape(text[:20000])


def inspection_html(value, continuation=''):
    """Render the plan separately from executed rows and their actions."""
    binding = value['source_binding']
    state = binding['state']
    if state == 'VERIFIED_SEED':
        source = 'Verified seed ' + binding['seed_id'][:12]
    elif state == 'SYMBOLIC_UNPINNED':
        context = binding.get('context') or {}
        source = 'Symbolic source plan'
        if context:
            source += ' · ' + json.dumps(context, ensure_ascii=False, sort_keys=True)
    else:
        source = 'Runtime source check required'
    lines = ['<b>Plan</b> · preview only']
    if continuation:
        lines.append(continuation)
    if value['operation']:
        lines.extend(map(escape, wrap('Kernel operation · ' + value['operation'], width=48)))
    lines.extend(map(escape, wrap('Source binding · ' + source, width=48)))
    lines.append('Scope · ' + escape(value['required_scope']) + '  |  Effects · ' + escape(', '.join(value['effects'])))
    for number, step in enumerate(value['steps'], 1):
        command = step['command']
        operation = step.get('operation')
        heading = f'{number}. <b>{escape(command)}</b>'
        lines.append(heading + (' · ' + escape(operation) if operation and operation != command else ''))
        types = ' → '.join(step[field] for field in ('input', 'output') if step.get(field))
        details = [types] if types else []
        details.extend(f'{key} · {json.dumps(item, ensure_ascii=False, sort_keys=True)}'
                       for key, item in sorted(step.get('arguments', {}).items()) if key != 'kind' or item != command)
        for detail in details:
            lines.extend(f'<span style="color:{QUIET};">&nbsp;&nbsp;{escape(line)}</span>' for line in wrap(detail, width=48))
    return '<br>'.join(lines)


class Prompt(QLineEdit):
    def __init__(self, console):
        super().__init__();self.console = console;self.setObjectName('ConsolePrompt');self.setFont(mono_font(15))
        self.setAccessibleName('Console: Log, Lines, Kernel, Find and Shell')

    def keyPressEvent(self, event):
        c = self.console
        if event.key() in (Qt.Key_Up, Qt.Key_Down):c.walk_history(-1 if event.key() == Qt.Key_Up else 1);return
        if event.key() == Qt.Key_Tab:c.complete();return
        if event.key() == Qt.Key_Escape:c.set_size(0);self.clearFocus();return
        if event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier and c.process is not None and not self.hasSelectedText():c.stop_shell();return
        if not self.text() and event.text() in PREFIX and c.mode != PREFIX[event.text()]:
            c.set_mode(PREFIX[event.text()])  # the first character chooses the page; only staC keeps it, as its @
            if event.text() != '@':return
        if not self.text() and event.key() == Qt.Key_Backspace and c.mode != 'log':c.set_mode('log');return
        super().keyPressEvent(event)

    def focusNextPrevChild(self, forward):
        return False  # Tab completes here; it never leaves the prompt


class Console(QWidget):
    def __init__(self, host, tail):
        super().__init__();self.host = host;self.tail = tail;self.setObjectName('Console')
        self.mode = 'log';self.size_level = 0;self.process = None;self.pending_approval = None;self.links = {};self.blocks = 0
        state = host.session.state.setdefault('console', {}) if hasattr(host, 'session') else {}
        self.history = state.setdefault('history', {});self.at = None
        self.cwd = None
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(4)
        self.output = QTextBrowser();self.output.setObjectName('ConsoleOutput');self.output.setOpenLinks(False);self.output.setFont(mono_font(14))
        self.output.anchorClicked.connect(self.follow);self.output.setAccessibleName('Console output');self.output.hide()
        self.last_program = None;self.output.setContextMenuPolicy(Qt.CustomContextMenu);self.output.customContextMenuRequested.connect(self.output_menu)
        self.output.setLineWrapMode(QTextEdit.NoWrap)  # a terminal scrolls sideways; it never folds a table into letters
        self.output.document().setDefaultFont(mono_font(14))
        self.output.document().setDefaultStyleSheet('a {color:%s; text-decoration: underline; text-decoration-color:%s;}' % (TEXT, ERASER_MARK))
        self.at_end = True  # the output keeps to its end while the owner is there, as a terminal does; reading back stops it
        scroll = self.output.verticalScrollBar();scroll.actionTriggered.connect(self.moved);scroll.rangeChanged.connect(self.keep_end)
        box.addWidget(self.output)
        words = QHBoxLayout();words.setSpacing(0);self.chips = {}
        for key, label, prefix, _ in MODES:
            chip = button(label + ('  ' + prefix if prefix else ''), 'filter');chip.setCheckable(True);chip.clicked.connect(lambda checked=False, k=key:self.set_mode(k, focus=True))
            chip.setToolTip({'log': 'The Timeline: what Graphite did, in words', 'stac': 'Lines that read', 'kernel': 'Kernel operations by name',
                             'find': 'Find anything', 'shell': 'Your own shell commands'}[key])
            self.chips[key] = chip;words.addWidget(chip)
        self.sign = QLabel();self.sign.setFont(mono_font(15));self.sign.setStyleSheet('color:%s;padding-left:6px' % QUIET);words.addWidget(self.sign)
        self.prompt = Prompt(self);self.prompt.returnPressed.connect(self.enter);self.prompt.textEdited.connect(self.typed);words.addSpacing(8);words.addWidget(self.prompt, 1)
        self.prompt.hide();self.sign.hide()  # one place to type: the box at the top. This prompt only carries lines the box hands over.
        hint = QLabel('type in the box above  ·  @ a line   / Kernel   ? find   $ shell');hint.setStyleSheet('color:%s;padding-left:10px' % QUIET);words.addWidget(hint, 1)
        # The integration of the desk items: a status message shows here while it lasts (TypeBar.note). Unwrapped, a long one
        # (an unavailable row's whole reason on F1) made the workspace's least width its whole length, and the desk narrowed
        # both panes to the slots' floor for good; wrapped, it asks for its longest word and takes another line instead.
        hint.setWordWrap(True)
        self.hint = hint;self.words_row = words
        words.addSpacing(10)
        self.sizes = {}
        for level, label in ((0, 'line'), (1, 'half'), (2, 'tall')):
            b = button(label, 'filter');b.setCheckable(True);b.clicked.connect(lambda checked=False, l=level:self.set_size(l));self.sizes[level] = b;words.addWidget(b)
        box.addLayout(words)
        size = self.px = max(12, mono_font(14).pixelSize())
        self.setStyleSheet(
            f"QTextBrowser#ConsoleOutput, QLineEdit#ConsolePrompt {{background:{TERMINAL_GROUND};"
            f"color:{AMBER_TEXT};border:1px solid {LINE};border-radius:2px;font-family:'{MONO}';}} "
            f"QTextBrowser#ConsoleOutput {{padding:4px 8px;font-size:{size}px;}} "
            f"QLineEdit#ConsolePrompt {{padding:3px 8px;font-size:{size + 1}px;}}"
        )
        self.set_mode(state.get('mode', 'log') if state.get('mode') in dict((m[0], m) for m in MODES) else 'log');self.set_size(0)

    # -- pages and sizes ------------------------------------------------------------------
    def set_mode(self, mode, focus=False):
        """Show a page (D3: choosing a page never opens the area; running a line does, open())."""
        self.mode = mode;self.at = None;self.pending_approval = None
        for key, chip in self.chips.items():chip.setChecked(key == mode)
        spec = next(m for m in MODES if m[0] == mode)
        writing_prompt(self.prompt, spec[3])
        self.sign.setText(self.sign_text())
        if mode != 'log':self.tail.search.setText('')
        self.show_page()
        if not getattr(self.tail, 'desk_foot', False):self.tail.follow.setVisible(mode == 'log')  # D1b: Follow latest lives in Activity
        if mode != 'log' and not self.blocks:self.welcome()
        if hasattr(self.host, 'session'):self.host.session.state.setdefault('console', {})['mode'] = mode
        if focus:self.focus_box()
        self.fit();self.quiet_foot()

    def show_page(self):
        """The page in the working area: the Log view in Log (the Timeline's list where there is no Log view), the output
        otherwise; in Line none (the band holds the line, the area is closed)."""
        view = getattr(self.host, 'log_view', None);line = self.size_level == 0 and getattr(self.tail, 'desk_foot', False)
        if view is not None:
            self.tail.list.setVisible(False);view.setVisible(self.mode == 'log' and not line)
        else:self.tail.list.setVisible(self.mode == 'log' and not line)
        self.output.setVisible(self.mode != 'log' and not line)

    def sign_text(self):
        if self.mode == 'shell':return self.short(self.working_dir()) + ' $'
        return {'log': 'log ›', 'stac': 'line ›', 'kernel': 'graphite ›', 'find': 'find ›'}[self.mode]

    def set_size(self, level):
        self.size_level = level
        for l, b in self.sizes.items():b.setChecked(l == level)
        self.tail.expand.blockSignals(True);self.tail.expand.setChecked(level > 0);self.tail.expand.setText('Collapse' if level else 'Expand');self.tail.expand.blockSignals(False)
        self.fit();self.quiet_foot()
        bar = getattr(self.host, 'type_bar', None)
        if bar is not None and getattr(bar, 'target', None) == 'log':bar.refresh_context()  # Line: the band's quiet word sums the stream up
        if bar is not None and getattr(bar, 'expand', None) is not None:bar.expand.say()      # the line's expand control shows the size it is at

    def quiet_foot(self):
        """HATCH DESK D1b: in Line the centre foot is empty, the workspace reaching the lower band (the Timeline's line, the
        Return thread, Follow latest and the Work trail are in the right pane's Activity; Half and Tall show the console as
        before). A status message still shows there while it lasts (TypeBar.note)."""
        if not getattr(self.tail, 'desk_foot', False):return
        line = self.size_level == 0
        self.show_page()
        self.tail.setVisible(not line or not self.hint.isHidden())

    def fit(self):
        line = self.tail.list.fontMetrics().height() + 8
        tall = max(line * 12, int(self.host.height() * 0.42)) if self.host.height() else line * 20
        height = {0: line + 4, 1: line * 12, 2: tall}[self.size_level]
        self.tail.list.setFixedHeight(height);self.output.setFixedHeight(height)
        view = getattr(self.host, 'log_view', None)
        if view is not None:view.setFixedHeight(height)

    def open(self, mode=None, focus=True):
        if mode:self.set_mode(mode)
        if self.size_level == 0:self.set_size(1)
        if focus:self.focus_box()

    def focus_box(self):
        """Put the cursor in the box, ready with this page's first character."""
        bar = getattr(self.host, 'type_bar', None)
        if bar is not None:bar.set_target({'stac': 'slate', 'kernel': 'kernel'}.get(self.mode, self.mode));return
        box = getattr(getattr(getattr(self.host, 'shell2', None), 'top', None), 'box', None)
        if box is None:return
        lead = {'stac': '@', 'kernel': '/', 'find': '?', 'shell': '$'}.get(self.mode, '')
        if not box.text().strip() or box.text().strip() in ('@', '/', '?', '$'):box.setText(lead)
        box.setFocus();box.end(False)

    def take_box(self, box):
        """The one box sits in this row, where the hint was: words ask Slate or find; @ / ? $ run here."""
        self.hint.hide();self.words_row.insertWidget(self.words_row.indexOf(self.hint), box, 1);box.show()

    def recall(self, page, step, current):
        """↑ ↓ in the box for a console line: this page's own history, as the box would show it."""
        items = self.history.get(page, [])
        if not items:return None
        if self.mode != page:self.mode = page;self.at = None
        self.at = (len(items) if self.at is None else self.at) + step
        self.at = max(0, min(len(items), self.at))
        text = items[self.at] if self.at < len(items) else ''
        lead = '' if getattr(self.host, 'type_target', None) == page else {'stac': '', 'kernel': '/', 'find': '?', 'shell': '$'}[page]
        return lead + text if text and not (page == 'stac' and text.startswith('@')) else (text or lead)

    def complete_line(self, page, line):
        """Tab in the box for a console line: completion for that page; the line comes back as the box shows it."""
        lead = line[:1] if page != 'stac' and line[:1] in '/?$' else ''
        if self.mode != page:self.set_mode(page)
        self.prompt.setText(line[len(lead):]);self.prompt.setCursorPosition(len(self.prompt.text()))
        self.complete()
        return lead + self.prompt.text()

    # -- typing ----------------------------------------------------------------------------
    def typed(self, text):
        if self.mode == 'log':self.tail.search.setText(text)  # the Timeline filters as you type
        if self.pending_approval and text != self.pending_approval:self.pending_approval = None

    def walk_history(self, step):
        items = self.history.get(self.mode, [])
        if not items:return
        self.at = (len(items) if self.at is None else self.at) + step
        self.at = max(0, min(len(items), self.at))
        self.prompt.setText(items[self.at] if self.at < len(items) else '')

    def remember(self, text):
        items = self.history.setdefault(self.mode, [])
        if not items or items[-1] != text:items.append(text)
        del items[:-200];self.at = None
        try:self.host.session.save()
        except Exception:pass

    def complete(self):
        text = self.prompt.text();cursor = self.prompt.cursorPosition();before = text[:cursor]
        word = re.split(r'[\s|]', before)[-1]
        options = []
        if self.mode == 'kernel':
            from . import desk_acts
            from .engineering_kernel import CAPABILITIES
            head = before.split(' ', 1)
            if len(head) == 1:options = sorted([op for op in CAPABILITIES if op.startswith(word)] + [act for act in desk_acts.ACTS if act.startswith(word)])
            else:
                from .engineering_cli import schemas
                definition = desk_acts.schema(head[0]) if desk_acts.is_act(head[0]) else (schemas().get(head[0]) or {})
                options = [name + '=' for name in definition.get('properties', {}) if name.startswith(word)]
        elif self.mode == 'stac':
            if word.startswith('@files:'):
                folder, _, stem = word[len('@files:'):].rpartition('/')
                entries = (call(self.host, 'files.list', {'path': folder}) or {}).get('entries', [])
                options = ['@files:' + e['path'] + ('/' if e['kind'] == 'folder' else '') for e in entries if e['name'].startswith(stem)]
            elif word.startswith('@'):
                kinds = (call(self.host, 'ledger.address.kinds') or {})
                names = [k['kind'] if isinstance(k, dict) else k for k in (kinds.get('kinds') if isinstance(kinds, dict) else kinds) or []]
                options = ['@' + k + ':' for k in names if ('@' + k).startswith(word)]
            else:options = [v + ' ' for v in STAC_VERBS if v.startswith(word)]
        if not options:return
        import os
        common = os.path.commonprefix(options)
        if len(options) > 1 and common == word:
            self.say('<span style="color:%s;">%s</span>' % (QUIET, escape('   '.join(options[:60]) + ('   …' if len(options) > 60 else ''))));return
        self.prompt.setText(before[:len(before) - len(word)] + (options[0] if len(options) == 1 else common) + text[cursor:])

    def enter(self):
        text = self.prompt.text().strip()
        if self.mode == 'log':return
        if not text:return
        if text[0] in PREFIX and PREFIX[text[0]] == self.mode and self.mode != 'stac':text = text[1:].strip()  # a typed prefix is not part of the command
        if text in ('clear', 'cls'):self.output.clear();self.blocks = 0;self.links = {};self.prompt.clear();return
        self.remember(text);self.prompt.clear()
        getattr(self, 'run_' + self.mode)(text)

    # -- output ----------------------------------------------------------------------------
    def welcome(self):
        """The area's first words: an explanation you may skip, so the Paper script (the quiet-script rule), its keys and
        lead characters printed."""
        from .shell2 import keyed_html
        # 0.7.0: no key is named here either (the owner: no shortcut printed anywhere); the keys work as they did.
        lines = ('Answers stay here; the name lit in the band says who the line goes to.',
                 'A line you type is run by the arrow. Put explain before it to see the plan first.',
                 'A leading / runs an operation by name.')
        self.say('<br>'.join(keyed_html(line, round(self.px * 1.3), self.px) for line in lines))  # short lines: the area never folds

    def font_css(self):
        return "font-family:'%s';font-size:%dpx;" % (MONO, getattr(self, 'px', 13))

    def link(self, label, fn):
        key = 'c%d' % (len(self.links) + 1);self.links[key] = fn
        return '<a href="console:%s">%s</a>' % (key, escape(label))

    def follow(self, url):
        fn = self.links.get(url.toString().partition(':')[2])
        if fn:fn()

    def say(self, html, echo=None, *, wrap_output=False):
        self.output.setLineWrapMode(QTextEdit.WidgetWidth if wrap_output else QTextEdit.NoWrap)
        cursor = self.output.textCursor();cursor.movePosition(QTextCursor.End)
        if not cursor.atBlockStart():cursor.insertBlock()  # streamed output never runs into the next line
        if wrap_output:
            start = QTextCursor(cursor)
            start.setKeepPositionOnInsert(True)
        top = '<div style="margin-top:8px;color:%s;%s">%s</div>' % (AMBER_TEXT, self.font_css(), escape(echo)) if echo else ''
        cursor.insertHtml(top + '<div style="color:%s;%s">%s</div><br>' % (TEXT, self.font_css(), html));self.blocks += 1
        self.at_end = not wrap_output
        if self.blocks > BLOCKS:
            trim = self.output.textCursor();trim.movePosition(QTextCursor.Start)
            trim.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 40);trim.removeSelectedText();self.blocks -= 20
        if wrap_output:
            self.output.setTextCursor(start)
            self.output.ensureCursorVisible()
        else:
            self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def moved(self, action):
        """The owner moved the output (wheel, scroll bar, page keys): it keeps to its end only while they are at the end."""
        scroll = self.output.verticalScrollBar();self.at_end = scroll.sliderPosition() >= scroll.maximum()

    def keep_end(self, low, high):
        """The last answer stays in sight when the area is laid out after it was written (D3-fix: the output was scrolled to
        its end before the area opened and the horizontal scroll bar appeared, and the text view then kept its old position,
        so a search's last rows sat out of sight): to the end now, and again once the layout has settled."""
        if not self.at_end:return
        self.output.verticalScrollBar().setValue(high)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.to_end)

    def to_end(self):
        if self.at_end:self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def refused(self, message):
        return '<span style="background:%s;">refused</span>  %s' % (ERASER, escape(str(message)))

    def output_menu(self, point):
        """Right-click on the output: copy, and carry on from the last staC answer as a chain."""
        menu = self.output.createStandardContextMenu()
        if self.last_program:
            from .chain_menu import fill
            menu.addSeparator();fill(menu, self.host, self.last_program)
        menu.exec(self.output.viewport().mapToGlobal(point))

    # -- staC ------------------------------------------------------------------------------
    def run_stac(self, text):
        op, args = route_program(text, allow_inspection=True)
        program = args.get('program', args.get('text'))
        inspecting = op == 'stac.inspect'
        if not program and not inspecting:return
        echo = 'line › ' + program
        if inspecting:
            echo = 'line › explain ' + (program if len(program) <= 32 else program[:31] + '…')
            self.last_program = None
        started = time.monotonic();r = call_write(self.host, op, args);took = time.monotonic() - started
        if not r.get('ok'):self.say(self.refused((r.get('error') or {}).get('message', 'did not run')), echo=echo, wrap_output=inspecting);return
        if inspecting:
            load = self.link('Load exact command', lambda: self.host.shell2.top.box.use_program(program))
            self.say(inspection_html(r['result'], load + ' · The arrow runs it from the writing line.'), echo=echo, wrap_output=True)
            return
        value = r['result'];rows = value.get('rows') if isinstance(value, dict) else None
        self.last_program = program  # a right-click on the output carries on from here, as a chain
        if rows is None:self.say(result_html(value), echo=echo);return
        face = self.host.shell2.face
        words = '  ·  '.join([self.link('save as a sheet', lambda p=program, rs=rows:face.save_rows(p, rs)), self.link('watch it', lambda p=program:face.watch(p)),
                              self.link('add to the Agenda', lambda p=program:face.keep_in_agenda(p)), self.link('again', lambda p=program:self.run_stac(p))])
        self.say(table_html(rows) + '<div style="color:%s;">%d row%s · %.2f s · read only · </div>' % (QUIET, len(rows), '' if len(rows) == 1 else 's', took) + words,
                 echo=echo)

    # -- Kernel ----------------------------------------------------------------------------
    def argument_rows(self, definition):
        required = set(definition.get('required', []))
        return [{'argument': k, 'needed': 'yes' if k in required else '', 'kind': v.get('type', '') + (' · one of ' + ', '.join(map(str, v['enum'])) if v.get('enum') else ''),
                 'limit': v.get('maxLength') or v.get('maximum') or ''} for k, v in definition.get('properties', {}).items()]

    def help_act(self, name, text):
        """help NAME for a desk act: what it is (it navigates; it changes, through her hand; or it is the owner's alone), its
        words and its arguments. An act's name is printed only here, in ops, and in the echo of a line that ran one."""
        from . import desk_acts
        act = desk_acts.ACTS[name]
        if act.owner_only:mark = 'yours only'
        elif act.mark == 'changes':mark = named("changes, through Stacy's hand: %s") % (act.kernel or 'the step\'s own line')
        else:mark = 'navigates'
        rows = self.argument_rows(act.schema)
        self.say('<b>%s</b> · %s<br>%s' % (escape(name), escape(mark), escape(act.words)) + (table_html(rows) if rows else '<br>No arguments.'), echo='graphite › ' + text)

    def run_kernel(self, text):
        from . import desk_acts
        from .engineering_kernel import CAPABILITIES
        from .engineering_cli import schemas
        words = text.split()
        if words[0] in ('help', 'ops', 'history'):
            if words[0] == 'history':self.say(escape('\n'.join(self.history.get('kernel', [])[-30:])).replace('\n', '<br>'), echo='graphite › history');return
            if words[0] == 'ops':
                needle = words[1] if len(words) > 1 else ''
                acts = sorted(name for name in desk_acts.ACTS if needle in name)      # 0.8.2: the desk's acts first, then the operations
                found = sorted(op for op in CAPABILITIES if needle in op)
                head = ('%d act%s' % (len(acts), '' if len(acts) == 1 else 's') + table_html([{'act': name, 'mark': 'yours only' if desk_acts.ACTS[name].owner_only else desk_acts.ACTS[name].mark,
                                                                                        'use': self.link('help', lambda n=name:self.run_kernel('help ' + n))} for name in acts], raw=('use',)) + '<br>') if acts else ''
                self.say(head + '%d operation%s' % (len(found), '' if len(found) == 1 else 's') +
                         table_html([{'operation': op, 'scope': CAPABILITIES[op], 'use': self.link('help', lambda o=op:self.run_kernel('help ' + o))} for op in found[:400]], raw=('use',)),
                         echo='graphite › ' + text);return
            if len(words) > 1 and words[1] == 'acts':
                rows = [{'act': name, 'mark': 'yours only' if act.owner_only else act.mark, 'words': act.words} for name, act in desk_acts.ACTS.items()]
                self.say('%d acts, each something you can do in the window; a line runs one by its name' % len(rows) + table_html(rows), echo='graphite › ' + text);return
            if len(words) > 1 and desk_acts.is_act(words[1]):self.help_act(words[1], text);return
            if len(words) < 2 or words[1] not in CAPABILITIES:self.say(self.refused('help needs an operation name; try ops files'), echo='graphite › ' + text);return
            op = words[1];d = schemas()[op]
            rows = self.argument_rows(d)
            self.say('<b>%s</b> · scope %s%s' % (escape(op), CAPABILITIES[op], ' · asks for a second Enter' if CAPABILITIES[op] == 'approve' else '') + (table_html(rows) if rows else '<br>No arguments.'),
                     echo='graphite › ' + text);return
        try:op, args = parse_command(text)
        except (ValueError, json.JSONDecodeError) as exc:self.say(self.refused(exc), echo='graphite › ' + text);return
        if desk_acts.is_act(op) or desk_acts.looks_like_act(op):      # 0.8.2: a desk act, by its name (desk_doers): the owner's door
            from .desk_doers import run as run_act
            done = run_act(self.host, op, args, door='owner', word='/' + text)
            self.say(escape(desk_acts.said(done)) if done['ok'] else self.refused(desk_acts.said(done)), echo='graphite › ' + text);return
        if op not in CAPABILITIES:
            near = [o for o in CAPABILITIES if op.split('.')[0] in o][:8]
            self.say(self.refused('no operation named ' + op) + ('<br>Perhaps: ' + escape(', '.join(near)) if near else ''), echo='graphite › ' + text);return
        if CAPABILITIES[op] == 'approve' and self.pending_approval != text:
            self.pending_approval = text;self.prompt.setText(text)
            self.say('<span style="background:%s;">%s acts with your approval.</span> Press Enter again to run it as written; change it or press Esc to leave it.' % (AMBER, escape(op)),
                     echo='graphite › ' + text);return
        self.pending_approval = None
        r = call_write(self.host, op, args)
        self.say(result_html(r['result']) if r.get('ok') else self.refused((r.get('error') or {}).get('code', '') + ' ' + (r.get('error') or {}).get('message', '')), echo='graphite › ' + text)

    # -- Find ------------------------------------------------------------------------------
    def run_find(self, text):
        from .shell2 import library_files
        parts = []
        files = (call(self.host, 'files.find', {'text': text, 'limit': 30}) or {}).get('records', [])
        if files:
            root = Path((call(self.host, 'files.list', {}) or {}).get('root', '.'))
            lines = ['%s  %s  <span style="color:%s;">%s</span>' % (self.link('open', lambda p=root / e['path']:self.host.open_in_viewer(p)), escape(e['path']), QUIET, escape(e.get('found') or e.get('kind_words', '')))
                     for e in files]
            from .files_qt import show as files_show
            more = '  ' + self.link('show in Files', lambda t=text:files_show(self.host).show_question(t)) + '  ·  ' + \
                   self.link('keep as a smart folder', lambda t=text:self.keep_smart(t))
            parts.append('<span style="color:%s;">FILES · %d</span>%s<br>' % (QUIET, len(files), more) + '<br>'.join(lines))
        # HATCH DESK D1b: the cabinet's query box and the settings filter left the left pane; finding a record or a setting by
        # its words is here, in Search (D3). The same match as the boxes: label and role, label and key.
        records = cabinet_records(self.host, text)
        if records:
            lines = ['%s  %s  <span style="color:%s;">%s</span>' % (self.link('open', lambda i=n['id']:reveal_record(self.host, i)), escape(n['label']), QUIET, escape(n['role'].replace('_', ' ')))
                     for n in records]
            parts.append('<span style="color:%s;">CABINET · %d</span><br>' % (QUIET, len(records)) + '<br>'.join(lines))
        found = setting_rows(text)
        if found:
            lines = ['%s  %s  <span style="color:%s;">%s</span>' % (self.link('open', lambda k=n['target']:self.host.ledger_bridge.show_settings(key=k)), escape(n['label']), QUIET, escape(n['target']))
                     for n in found]
            parts.append('<span style="color:%s;">SETTINGS · %d</span><br>' % (QUIET, len(found)) + '<br>'.join(lines))
        received = [e for e in library_files(self.host, limit=400) if text.casefold() in e['name'].casefold()][:15]
        if received:
            lines = ['%s  %s  <span style="color:%s;">%s</span>' % (self.link('open', lambda e=e:self.host.shell2.open_library_file(e)), escape(e['name']), QUIET, escape(e['delivery'])) for e in received]
            parts.append('<span style="color:%s;">RECEIVED · %d</span><br>' % (QUIET, len(received)) + '<br>'.join(lines))
        commands = self.host.shell2.top.box.commands(text)[:10]
        if commands:
            lines = ['%s  <span style="color:%s;">%s</span>' % (self.link(label, fn), QUIET, escape(hint)) for label, hint, fn in commands]
            parts.append('<span style="color:%s;">COMMANDS</span><br>' % QUIET + '<br>'.join(lines))
        from . import activity
        from .tail_words import readable
        events = [e for e in activity.tail(self.host.root, query=text, limit=200).get('events', []) if e.get('state') != 'REQUEST_RECEIVED'][-12:]
        if events:
            lines = ['%s  %s' % (time.strftime('%H:%M:%S', time.localtime(e['at'])), escape(readable(e))) for e in reversed(events)]
            parts.append('<span style="color:%s;">TIMELINE · %d</span><br>' % (QUIET, len(events)) + '<br>'.join(lines))
        self.say('<br><br>'.join(parts) if parts else '<span style="color:%s;">Nothing found for that.</span>' % QUIET, echo='find › ' + text)

    def keep_smart(self, words):
        r = call_write(self.host, 'files.smart', {'name': words[:60], 'find': {'text': words}})
        self.host.statusBar().showMessage(('Kept as the smart folder “%s” in Files.' % words[:60]) if r.get('ok') else (r.get('error') or {}).get('message', 'Not kept'), 7000)
        from .shell2 import refresh_library
        refresh_library(self.host)

    # -- Shell -----------------------------------------------------------------------------
    def working_dir(self):
        if self.cwd is None:
            root = (call(self.host, 'files.list', {}) or {}).get('root')
            self.cwd = Path(root) if root else Path.home()
        return self.cwd

    def short(self, path):
        text = str(path);home = str(Path.home())
        return '~' + text[len(home):] if text.startswith(home) else text

    def run_shell(self, text, extra_env=None):
        if self.process is not None:self.say(self.refused('a command is still running; stop it first'), echo=self.sign_text() + ' ' + text);return
        if text == 'cd' or text.startswith('cd '):
            target = text[2:].strip() or '~'
            path = Path(target).expanduser();path = path if path.is_absolute() else self.working_dir() / path
            try:path = path.resolve(strict=True)
            except OSError:self.say(self.refused('no such folder: ' + target), echo=self.sign_text() + ' ' + text);return
            if not path.is_dir():self.say(self.refused('not a folder: ' + target), echo=self.sign_text() + ' ' + text);return
            self.cwd = path;self.sign.setText(self.sign_text());return
        echo = self.sign_text() + ' ' + text
        self.process = p = QProcess(self);p.setProcessChannelMode(QProcess.MergedChannels);p.setWorkingDirectory(str(self.working_dir()))
        env = QProcessEnvironment.systemEnvironment()
        for key, value in (('TERM', 'dumb'), ('PAGER', 'cat'), ('GIT_PAGER', 'cat'), ('NO_COLOR', '1')) + tuple((extra_env or {}).items()):env.insert(key, value)
        p.setProcessEnvironment(env);self.shell_started = time.monotonic();self.shell_text = text;self.shell_bytes = 0
        cursor = self.output.textCursor();cursor.movePosition(QTextCursor.End)
        if not cursor.atBlockStart():cursor.insertBlock()
        cursor.insertHtml('<div style="margin-top:8px;color:%s;%s">%s</div>' % (AMBER_TEXT, self.font_css(), escape(echo)));cursor.insertBlock();self.blocks += 1
        self.running_word = self.link('stop', self.stop_shell)
        p.readyRead.connect(self.shell_output);p.finished.connect(self.shell_done);p.errorOccurred.connect(self.shell_error)
        from .typebar_qt import configured_shell, shell_argv
        argv = shell_argv(configured_shell(), text);p.start(argv[0], argv[1:]);p.closeWriteChannel()  # D3: the configured shell
        from . import activity
        activity.record(self.host.root, 'desktop-owner', 'console.shell', 'REQUEST_RECEIVED', text[:160])

    def shell_output(self):
        if self.process is None:return
        data = bytes(self.process.readAll()).decode('utf-8', 'replace');self.shell_bytes += len(data)
        if self.shell_bytes > 4 * 1024 * 1024:self.stop_shell();return  # a runaway command does not fill the window
        cursor = self.output.textCursor();cursor.movePosition(QTextCursor.End)
        cursor.insertHtml('<pre style="margin:0;color:%s;%s">%s</pre>' % (AMBER_TEXT, self.font_css(), escape(plain(data))))
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def shell_done(self, code, status):
        took = time.monotonic() - self.shell_started;p = self.process;self.process = None
        crashed = status == QProcess.CrashExit
        self.say('<span style="color:%s;">%s · %.1f s</span>' % (QUIET, 'stopped' if crashed else 'exit %d' % code, took))
        from . import activity
        activity.record(self.host.root, 'desktop-owner', 'console.shell', 'REQUEST_COMPLETED' if not crashed and code == 0 else 'FAILED', self.shell_text[:160])
        if p is not None:p.deleteLater()

    def shell_error(self, error):
        if error == QProcess.FailedToStart and self.process is not None:
            self.process = None;self.say(self.refused('the shell could not start'))

    def stop_shell(self):
        if self.process is not None:self.process.kill()


def cabinet_records(host, text, limit=15):
    """The cabinet's records whose label or role holds the words (the cabinet query box's own match, D1b; Search's CABINET)."""
    query = str(text).casefold();page = getattr(host, 'cabinet_page', None)
    return [n for n in ((page.model or {}).get('nodes', []) if page is not None else []) if query in (n['label'] + ' ' + n['role']).casefold()][:limit]


def reveal_record(host, ident):
    """A record found by Search opens where it belongs: the Cabinet tab, the record selected and revealed, then opened."""
    page = getattr(host, 'cabinet_page', None);nav = getattr(host, 'settings_navigator', None)
    if page is None:return
    if nav is not None:nav.show_view('cabinet')
    if page.using_legacy:page.set_legacy(False)
    page.select(ident, reveal=True);page.open(ident)


def setting_rows(text, limit=12):
    """The settings whose label or key holds the words (the settings filter's own match, D1b; Search's SETTINGS)."""
    from . import settings_registry
    query = str(text).casefold()
    return [n for n in settings_registry.nodes() if n.get('target') and query in (n['label'] + ' ' + n['target']).casefold()][:limit]


def attach(host, tail):
    """The console takes over the Timeline strip: the Timeline is its Log page."""
    console = Console(host, tail);tail.layout().addWidget(console);tail.search.hide()
    tail.expand.hide()  # line · half · tall are the sizes; one control, not two
    tail.expanded = lambda on, c=console:c.set_size(1 if on else 0)
    tail.resize_lines = console.fit;tail.console = console
    tail.expand.toggled.disconnect();tail.expand.toggled.connect(lambda on, c=console:c.set_size(1 if on else 0))
    from .log_qt import install as install_log
    install_log(host, console);console.show_page()  # D3: the Log view, above the output in the working area
    QShortcut(QKeySequence('Ctrl+`'), host, activated=lambda:console.open())
    for key, mode in (('Ctrl+Alt+`', 'shell'),):QShortcut(QKeySequence(key), host, activated=lambda m=mode:console.open(m))
    host.console = console
    return console
