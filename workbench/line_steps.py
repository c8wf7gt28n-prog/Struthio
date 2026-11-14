"""The right-click's line panel, without a window: a line read once, and every step offered with what it would give.

0.8.1, the owner: "right click was too complex. We need to make its power easy to use and chain/pipe."

Then › on a thing shows its line on its slab: the read it starts from and the steps after it. Held reads that line once,
through the Kernel, exactly as a run would begin it: language.parse (the seed and the read permission checked, the plan's one
source call), then that call itself. Every count and preview after that is typed_pipeline.apply on the value already held,
the same function language.run applies, so choosing steps reads nothing more; a step is parsed here and must keep the
held source. Show it is the one more read: the finished line run in the working area.

No Qt here: the panel (context_menu.LinePanel) draws what this module says. Words shown to the owner never name the
language and never begin with the line's own keywords; plain() turns the parser's refusals into such words.
"""
from __future__ import annotations
import json
import re
from collections import Counter, namedtuple

from sdk.cli.arc1cli import typed_pipeline

LIMIT = 200          # what a line gives at most (language.run); counting here goes further so the owner hears the true size
READ_LIMIT = 2000    # what the source may hold (typed_pipeline.apply's row budget)
MOST_STAGES = 8      # one source and at most seven steps (typed_pipeline.split)
OFFERS = 6           # values offered for one column
UNSAFE = ('`', '$(', '${', ';', '>', '<', '\n', '\r', '\x00', '"', '\\')      # a value with these is typed by hand, not offered
LENS_ORDER = ('rows', 'headings', 'layers', 'texts', 'lines', 'facts')

Offer = namedtuple('Offer', 'key words glyph step count enabled reason')
Step = namedtuple('Step', 'key words glyph')
# The steps the panel offers, in its order. Their words are the owner's, never the line's keywords.
STEPS = (Step('read', 'Read it as', 'table'), Step('where', 'Keep rows where', 'filter'), Step('sort', 'Sort by', 'sort'),
         Step('count', 'Count', 'count'), Step('group', 'Count by', 'group'), Step('first', 'First', 'limit'))


class Refusal(ValueError):
    """The line cannot be read or carried on; the message is already plain."""


def plain(message):
    """A refusal in the window's words: the language is never named; its terms become the panel's."""
    text = str(message or 'It cannot be read now').strip()
    swaps = ((r'Shell syntax and command substitution are not part of Stacy language', 'Those signs cannot be part of a line'),
             (r'Pipeline source exceeds its row/byte budget; narrow the query', 'It is too big to read here; narrow it first'),
             (r'Output exceeds (\d+) rows; add take', r'The answer is more than \1 rows · keep fewer first'),
             (r'Use one source and at most seven transforms', 'A line reads one thing and takes at most seven steps'),
             (r'\bStacy language\b', 'a line'), (r'\bstaC\b', 'a line'), (r'(?i)\bpipelines?\b', 'line'), (r'(?i)\btransforms?\b', 'step'),
             (r'(?i)\blanguage\b', 'line'))
    for pattern, words in swaps:text = re.sub(pattern, words, text)
    return text


def stages(line):
    """The line's parts: its source and its steps (the parser's own split, quotes kept whole)."""
    return typed_pipeline.split(str(line))


def steps_left(line):
    try:return max(0, MOST_STAGES - len(stages(line)))
    except ValueError:return 0


def ending_ready(count):
    """(whether Show it and Copy the rows can act, why not) for an answer of `count` rows."""
    if count is not None and count > LIMIT:
        return False, 'The answer is %d rows; a line gives at most %d · keep fewer first' % (count, LIMIT)
    return True, ''


def firsts(count):
    """First › choices: round sizes below the count, and 200 when the answer is longer than a line gives."""
    out = [n for n in (5, 10, 20, 50, 100) if count is None or n < count]
    if count is not None and count > LIMIT:out.append(LIMIT)
    return out


def with_step(line, step):
    return '%s | %s' % (str(line).rstrip(), step)


def back_a_step(line):
    parts = stages(line)
    return line if len(parts) <= 1 else ' | '.join(parts[:-1])


def _plan(line):
    """The parser's plan for a line, locally (no Kernel): an address source is written as the read it stands for."""
    from .stacy_language import source
    text, address = source(str(line))
    plan = typed_pipeline.parse(text)
    if address:plan['address'] = address
    return plan


class Held:
    """A line's source, read once. dispatch(operation, arguments) is the Kernel's door (context_menu.dispatch for the
    window); read() makes the only two calls, rows() and count() carry on from what is held."""
    def __init__(self, dispatch):
        self.dispatch = dispatch;self.call = None;self.value = None;self.line = None;self.address = None;self.reads = 0

    def read(self, line):
        parsed = self.dispatch('language.parse', {'text': str(line)})
        if not parsed.get('ok'):raise Refusal(plain(((parsed.get('error') or {}).get('message'))))
        plan = parsed['result'];call = plan['call']
        got = self.dispatch(call['operation'], call['arguments'])
        if not got.get('ok'):raise Refusal(plain(((got.get('error') or {}).get('message'))))
        result = got['result']
        self.value = result['object'] if 'address' in plan and isinstance(result, dict) and 'object' in result else result
        self.call = call;self.line = str(line);self.address = plan.get('address');self.reads += 1
        return self

    def source(self):
        """The line's first part: what it reads (its address, or the operation and its arguments)."""
        return stages(self.line)[0] if self.line else ''

    def rows(self, line):
        """The rows `line` gives, from the held value (every step here, no read). A line that reads another source is refused."""
        if self.call is None:raise Refusal('Nothing is read yet')
        try:
            plan = _plan(line)
            if plan['call'] != self.call:raise Refusal('That line reads something else')
            return typed_pipeline.apply(self.value, plan['transforms'], READ_LIMIT)
        except Refusal:raise
        except (ValueError, KeyError, TypeError) as exc:raise Refusal(plain(str(exc))) from None

    def count(self, line):
        rows = self.rows(line)
        return len(rows)

    def readings(self):
        """Read it as ›: the lenses (and sheets) of the held source that give rows, each with its count, when there is more
        than one. The line for each is the source and that lens."""
        out = [];base = self.source()
        for lens in LENS_ORDER:
            try:rows = typed_pipeline.apply(self.value, [{'kind': 'pick', 'path': typed_pipeline.LENSES[lens]}], READ_LIMIT)
            except (ValueError, KeyError, TypeError):continue
            if rows and all(isinstance(r, dict) for r in rows[:20]):out.append((lens, '%s | %s' % (base, lens), len(rows)))
        sheets = typed_pipeline.field(self.value, 'data.sheets') if isinstance(self.value, dict) else None
        if isinstance(sheets, dict):
            for name, rows in list(sheets.items())[:8]:
                if isinstance(rows, list) and rows and re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', str(name)):
                    out.append(('sheet ' + name, '%s | sheet %s' % (base, name), len(rows)))
        return out if len(out) > 1 else []


def columns(rows):
    """The fields the rows have that a step can name, in the order they are first seen."""
    out = []
    for row in rows[:200]:
        if not isinstance(row, dict):continue
        for name in row:
            if name not in out and typed_pipeline.FIELD.fullmatch(str(name)):out.append(name)
    return out


def number(value):
    """The number a value stands for (numeric text too), or None."""
    if isinstance(value, bool):return None
    if isinstance(value, (int, float)):return value
    if isinstance(value, str) and value.strip():
        try:found = float(value.replace(',', ''))
        except ValueError:return None
        return int(found) if found.is_integer() else found
    return None


def said(value):
    """A number as the owner reads it."""
    return str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)


def literal(value):
    """A text value as a where step writes it: bare when the parser reads it back as the same text, quoted otherwise."""
    text = str(value)
    try:back = json.loads(text)
    except json.JSONDecodeError:back = None
    if back is None and text and text == text.strip() and '|' not in text:return text
    return json.dumps(text, ensure_ascii=False)


def spread(values, most):
    if len(values) <= most:return list(values)
    return [values[round(i * (len(values) - 1) / (most - 1))] for i in range(most)]


def values(held, line, name):
    """Keep rows where › NAME ›: up to six offers, each with how many rows it keeps. A number column (numeric text too) offers
    at least and at most over values spread across it; a text column offers the most common values, then three to leave out.
    An offer that keeps every row or none is left out."""
    rows = held.rows(line);total = len(rows);seen = [r.get(name) for r in rows if isinstance(r, dict)]
    present = [v for v in seen if v not in (None, '')]
    out = [];steps = []
    numbers = [number(v) for v in present]
    if present and all(n is not None for n in numbers):
        distinct = sorted(set(numbers))
        for value in spread(distinct[1:], OFFERS // 2):steps.append(('at least ' + said(value), 'where %s at least %s' % (name, said(value))))
        for value in spread(distinct[:-1], OFFERS // 2):steps.append(('at most ' + said(value), 'where %s at most %s' % (name, said(value))))
    else:
        texts = [v for v in present if isinstance(v, str) and not any(sign in v for sign in UNSAFE) and len(v) <= 120]
        common = [v for v, _ in sorted(Counter(texts).items(), key=lambda kv:(-kv[1], texts.index(kv[0])))]
        for value in common[:OFFERS]:steps.append(('is ' + value, '%s=%s' % (name, literal(value))))
        for value in common[:3]:steps.append(('is not ' + value, '%s is not %s' % (name, literal(value))))
        steps = [(words, step if step.startswith('where ') else 'where ' + step) for words, step in steps]
    for words, step in steps:
        try:count = held.count(with_step(line, step))
        except Refusal:continue
        if 0 < count < total:out.append(Offer(step, words, 'filter', step, count, True, ''))
    return out


def sortable(held, line):
    """The columns Sort by can honestly order: numbers that are numbers, or text that is not numbers written as text (that
    would sort 110 before 12)."""
    rows = held.rows(line);out = []
    for name in columns(rows):
        present = [r.get(name) for r in rows if isinstance(r, dict) and r.get(name) not in (None, '')]
        if not present:continue
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in present):out.append(name)
        elif all(isinstance(v, str) and number(v) is None for v in present):out.append(name)
    return out


def groupable(held, line):
    """The columns Count by can gather: those with a few repeated values (not every row its own)."""
    rows = held.rows(line);out = []
    for name in columns(rows):
        present = [str(r.get(name)) for r in rows if isinstance(r, dict) and r.get(name) not in (None, '')]
        if present and len(set(present)) < len(present):out.append(name)
    return out


PREFERRED = ('name', 'title', 'parameter', 'part', 'value', 'unit', 'count', 'state', 'kind', 'process', 'path', 'size')


def preview_columns(rows, most=4):
    """The columns a preview shows: plain values (no lists, no yes/no flags), short ones before long text."""
    names = columns(rows);sample = [r for r in rows[:20] if isinstance(r, dict)]
    def plain(name):
        values = [r.get(name) for r in sample if r.get(name) not in (None, '')]
        return values and all(isinstance(v, (str, int, float)) and not isinstance(v, bool) for v in values)
    def long(name):
        values = [str(r.get(name)) for r in sample if r.get(name) not in (None, '')]
        return sum(len(v) for v in values) / max(1, len(values)) > 24
    chosen = [n for n in names if plain(n)]
    known = [n for word in PREFERRED for n in chosen if n.casefold() == word]       # the columns a person reads a table by
    rest = [n for n in chosen if n not in known]
    return (known + [n for n in rest if not long(n)] + [n for n in rest if long(n)])[:most] or names[:most]


def preview(rows, most_rows=3, most_columns=4):
    """(columns, the first rows as text, how many more) for the panel's preview."""
    names = preview_columns(rows, most_columns)
    shown = []
    for row in rows[:most_rows]:
        if isinstance(row, dict):shown.append([said(row.get(n)) if row.get(n) is not None else '' for n in names])
        else:shown.append([str(row)[:60]])
    return names, shown, max(0, len(rows) - most_rows)


def rows_words(count):
    return '%d row%s' % (count, '' if count == 1 else 's')


def as_csv(rows):
    """The rows as CSV text for the clipboard (Copy the rows)."""
    import csv
    import io
    names = columns(rows) or ['value'];out = io.StringIO();writer = csv.writer(out)
    writer.writerow(names)
    for row in rows:
        writer.writerow([row.get(n, '') if isinstance(row, dict) else row for n in names] if isinstance(row, dict) else [row])
    return out.getvalue()
