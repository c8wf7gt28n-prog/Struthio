"""Markdown: the note as it reads, beside the text it is written in. Qt renders CommonMark and GitHub tables itself.

A ```stac block in a note is live: when the note is read, the block runs (read-only, through the Kernel) and its answer
appears beneath it as a table, so a note can be a small report that is always current.

Links stay links but are not followed automatically; pictures referenced by the note are not fetched from the network.
"""
from __future__ import annotations
import re

KINDS = ('markdown',)
CSS = ("body{color:#504d46;font-family:'IBM Plex Sans';} h1,h2,h3{color:#504d46;font-weight:600;} "
       "a{color:#504d46;text-decoration:underline;text-decoration-color:#cba5a4;} code,pre{font-family:'IBM Plex Mono';background:#eee9df;} "
       "table{border-collapse:collapse;} td,th{border:1px solid #dad4c8;padding:4px 8px;} blockquote{color:#6c675e;}")


FENCE = re.compile(r'^```stac[ \t]*\n(.*?)\n```[ \t]*$', re.S | re.M)
LIVE_ROWS = 20


def cell(value):
    text = str(value) if value is not None else ''
    return text.replace('|', '\\|').replace('\n', ' ')[:80]


def living(text, run):
    """A note that computes: each ```stac block runs (read-only) and its answer is written beneath it as a table.
    run(program) returns rows, or raises ValueError with the reason. The note's own text is never changed."""
    def answer(match):
        program = ' '.join(line.strip() for line in match.group(1).splitlines() if line.strip())
        block = match.group(0)
        try:rows = run(program)
        except ValueError as exc:return block + '\n\n*This staC did not run: %s*\n' % cell(exc)
        if not rows:return block + '\n\n*Live: no rows.*\n'
        columns = list(dict.fromkeys(k for row in rows[:LIVE_ROWS] if isinstance(row, dict) for k in row))[:8] or ['value']
        lines = ['| ' + ' | '.join(columns) + ' |', '|' + '---|' * len(columns)]
        for row in rows[:LIVE_ROWS]:
            lines.append('| ' + ' | '.join(cell(row.get(c) if isinstance(row, dict) else row) for c in columns) + ' |')
        more = ' (first %d shown)' % LIVE_ROWS if len(rows) > LIVE_ROWS else ''
        return block + '\n\n' + '\n'.join(lines) + '\n\n*Live: %d row%s%s, read just now.*\n' % (len(rows), '' if len(rows) == 1 else 's', more)
    return FENCE.sub(answer, text)


def living_html(text, run):
    """The same live note for the screen: each answer becomes a marker in the Markdown, then a real table in Paper's style."""
    from html import escape
    tables = {}
    def answer(match):
        program = ' '.join(line.strip() for line in match.group(1).splitlines() if line.strip())
        marker = 'LIVESTAC%dMARK' % len(tables)
        try:rows = run(program)
        except ValueError as exc:
            tables[marker] = '<p style="color:#6c675e;font-style:italic;">This staC did not run: %s</p>' % escape(str(exc)[:200]);return match.group(0) + '\n\n' + marker + '\n'
        columns = list(dict.fromkeys(k for row in rows[:LIVE_ROWS] if isinstance(row, dict) for k in row))[:8] or ['value']
        head = ''.join('<th style="text-align:left;padding:4px 10px;border-bottom:1px solid #7d776d;">%s</th>' % escape(str(c)) for c in columns)
        body = ''.join('<tr>' + ''.join('<td style="padding:3px 10px;border-bottom:1px solid #dad4c8;">%s</td>' % escape(cell(r.get(c) if isinstance(r, dict) else r))
                                       for c in columns) + '</tr>' for r in rows[:LIVE_ROWS])
        note = 'Live: %d row%s%s, read just now.' % (len(rows), '' if len(rows) == 1 else 's', ' (first %d shown)' % LIVE_ROWS if len(rows) > LIVE_ROWS else '')
        tables[marker] = (('<table cellspacing="0" style="background:#fffdf8;"><tr>%s</tr>%s</table>' % (head, body)) if rows else '') + \
            '<p style="color:#6c675e;font-style:italic;">%s</p>' % (note if rows else 'Live: no rows.')
        return match.group(0) + '\n\n' + marker + '\n'
    return FENCE.sub(answer, text), tables


def kernel_runner(host):
    from ..engine import engineering
    from ..engineering_kernel import operator
    def run(program):
        r = engineering(host.root).dispatch('language.run', {'text': program}, operator())
        if not r.get('ok'):raise ValueError((r.get('error') or {}).get('message', 'did not run'))
        return r['result']['rows']
    return run


def ReadingPage(tab):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QPlainTextEdit, QSplitter, QTextBrowser
    text = tab.view.get('text') or ''
    shown, tables = living_html(text, kernel_runner(tab.host)) if FENCE.search(text) and getattr(tab, 'host', None) is not None else (text, {})
    split = QSplitter(Qt.Horizontal)
    reading = QTextBrowser();reading.setOpenLinks(False);reading.setOpenExternalLinks(False);reading.setProperty('arcReadingRole', 'prose')
    reading.document().setDefaultStyleSheet(CSS);reading.setMarkdown(shown);reading.setAccessibleName('Markdown, as it reads')
    from PySide6.QtGui import QTextCursor
    for marker, html in tables.items():  # each marker paragraph becomes its live table
        found = reading.document().find(marker)
        if not found.isNull():
            found.select(QTextCursor.BlockUnderCursor);found.removeSelectedText();found.insertBlock();found.insertHtml(html)
    source = QPlainTextEdit(text);source.setReadOnly(True);source.setAccessibleName('Markdown source')
    split.addWidget(reading);split.addWidget(source);split.setSizes([620, 420])
    return split


def pages(tab, view):
    if view.get('kind') != 'markdown' or view.get('text') is None:return []
    return [('Reading', lambda:ReadingPage(tab))]


def thumbnail(path, kind, size):
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QImage, QPainter, QTextDocument
    with open(path, 'rb') as f:text = f.read(4096).decode('utf-8', 'replace')
    document = QTextDocument();document.setDefaultStyleSheet(CSS);document.setMarkdown(text);document.setTextWidth(size * 2.2)
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied);image.fill(QColor('#fffdf8'))
    p = QPainter(image);p.scale(0.45, 0.45);document.drawContents(p, QRectF(0, 0, size * 2.2, size * 2.2));p.end()
    return image
