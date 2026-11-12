"""Explain a file from what Ledger knows about it, with or without Slate's brain.

The words come from the facts the viewer modules measured and the data staC can read; nothing is guessed. Each
explanation ends with a few staC questions that fit this kind of file, which can be run as written or added to the Agenda.
"""
from __future__ import annotations


def numeric_columns(rows):
    if not rows:return []
    return [k for k in rows[0] if all(isinstance(r.get(k), (int, float)) and not isinstance(r.get(k), bool) for r in rows[:50] if r.get(k) not in (None, ''))
            and any(isinstance(r.get(k), (int, float)) for r in rows[:50])]


def explain(value):
    """value: a files.get result. Returns {'text': plain words, 'suggestions': [staC]}."""
    name, address, kind = value['name'], value['address'], value.get('kind_words', value.get('kind', 'file'))
    facts, data = value.get('facts') or {}, value.get('data') or {}
    said = ['%s is %s%s.' % (name, 'an ' if kind[:1].lower() in 'aeiou' else 'a ', kind.lower() if kind != 'PDF' else kind)]
    ask = []
    if data.get('sheets'):
        parts = []
        for sheet, rows in list(data['sheets'].items())[:4]:
            columns = list(rows[0])[:6] if rows else []
            parts.append('%s (%d rows%s)' % (sheet, len(rows), '; columns ' + ', '.join(columns) if columns else ''))
        said.append('Its sheets: ' + '; '.join(parts) + '.')
        sheet, rows = next(iter(data['sheets'].items()))
        ask += ['%s | sheet %s | take 10' % (address, sheet), '%s | sheet %s | count' % (address, sheet)]
        numbers = numeric_columns(rows)
        if numbers:ask.append('%s | sheet %s | sort -%s | take 5' % (address, sheet, numbers[0]))
    elif data.get('rows') is not None:
        rows = data['rows'];columns = list(rows[0])[:8] if rows else []
        said.append('It has %d rows%s.' % (len(rows), ' with columns ' + ', '.join(columns) if columns else ''))
        ask += ['%s | rows | take 10' % address, '%s | rows | count' % address]
        numbers = numeric_columns(rows)
        if numbers:ask.append('%s | rows | where %s over 0 | sort -%s' % (address, numbers[0], numbers[0]))
    if data.get('layers'):
        layers = data['layers']
        said.append('Layers: ' + ', '.join('%s (%s)' % (l['layer'], l.get('entities') if 'entities' in l else (l.get('role') or '')) for l in layers[:8]) + '.')
        ask.append('%s | layers' % address)
    if data.get('texts'):
        said.append('Text on the drawing: ' + ', '.join('“%s”' % t['text'] for t in data['texts'][:5]) + '.');ask.append('%s | texts' % address)
    if data.get('headings'):
        said.append('Headings: ' + ', '.join(h['text'] for h in data['headings'][:6]) + '.');ask.append('%s | headings' % address)
    if data.get('lines') is not None and not data.get('headings'):
        said.append('%d lines.' % len(data['lines']));ask.append('%s | lines | where text has TODO' % address)
    for label in ('Size (model units)', 'Triangles', 'Enclosed volume', 'Pixels', 'Camera make', 'Taken', 'Pages', 'Length', 'Sample rate',
                  'Layer', 'Contents', 'Extents', 'Size'):
        if label in facts and len(said) < 9:said.append('%s: %s.' % (label, facts[label]))
    if not data and facts:ask.append('%s | facts' % address)
    elif facts and '%s | facts' % address not in ask:ask.append('%s | facts' % address)
    said.append('Its staC address is %s.' % address)
    return {'text': ' '.join(said), 'suggestions': ask[:4]}
