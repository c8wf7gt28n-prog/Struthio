"""The one grammar builder for model turns (0.8.7: slice E0 started it; lane A's A3 grows it to one grammar per kind).

Every turn kind's answer is a terse line under a per-request GBNF grammar with no free whitespace (design 3.3): the same
two-step reading is 22 tokens as a line, 46 as compact JSON and 102 as the JSON a small model writes under a schema that
allows whitespace, and writing is the slow half on the owner's computer. A kind's `grammar(inputs)` returns the text these
functions build; turns.ask sends it with the question, refuses a grammar with free whitespace (`check`), and never sends a
grammar that admits an answer longer than the kind's answer cap (`fits`).

A3 · one grammar per kind, each admitting only answers within its cap
---------------------------------------------------------------------
    GOAL    goal(count)                     1, "1 2" or 0                                   cap 6
    PICK    pick(count)                     n or 0                                          cap 4
    BIND    bind(count)                     n, "n n" or 0                                   cap 6
    NEXT    next_pick(count)                "n why", why one of REASONS                     cap 8
    ORDER   order(count)                    n                                               cap 4
    READ    read_line(...)                  kind|verb Dn "your words" [column] ["value"]|...  cap 24 (48 for four steps)
    MARKS   marks(lines, kinds, words)      up to 8 "L<n> <kind> | <label> | <value>", or NONE   cap 140
    ASK     ask_lines(lines, words)         up to 3 "L<n> | <value>", or NONE                cap 48
    COLUMNS columns(count, roles)           "C1=role C2=role ..."                           cap 30
    FRAME   frame(slots, words)             "{ANSWER} joining words {SLOT} ..."             cap 90
    TALK    none (free text, streamed, marked as the model's own; Stop, no grammar)          cap 256

Free words are never free characters: a quoted span of your words is built from your request's own words, a page value
from that page's own words, a frame's joining words from her lexicon. Lines a page's doorway flagged are not in a page
grammar at all, so the model cannot even point at them.

The cap, before anything is sent. `worst_tokens(grammar)` is an upper estimate of the tokens of the longest answer the
grammar admits, summed piece by piece with `estimate` (digits one each, letters one per three, other signs one each, a
non-ASCII letter two); the builders shrink their optional repetitions until the worst case fits the kind's cap, and refuse
(OverCap) a shape that cannot. `fits` is what turns.ask checks; a grammar that admits unbounded answers (`*`, `+`,
recursion) never fits. The estimate is checked against the 4B's own vocabulary by fuzzing (`sample`) in the build's smoke
script; whatever a model does inside the grammar, an answer cut at its cap (finish `length`) is refused whole by ask().

Only a small GBNF subset is built here (literals, character classes, rule references, groups, `?` and `{m,n}`), so what a
grammar admits can be matched (`matches`), listed (`admits`), sampled (`sample`) and measured (`longest_bytes`) exactly.
"""
from __future__ import annotations

import math
import random
import re
from functools import lru_cache

FREE_WHITESPACE = re.compile(r'\[[^\]]*(?:\\t|\\n|\\r| )[^\]]*\][*+]|\bws\b|\\s')
_LITERALS = re.compile(r'"(?:[^"\\]|\\.)*"')
REASONS = ('settles_most', 'cheapest', 'owner_asked', 'keeps_undo', 'unblocks')    # NEXT's whys (design 3.3)
READ_KINDS = ('desk', 'app', 'talk', 'unclear')                                    # READ's kinds (design 3.3)
CAPS = {'GOAL': 6, 'PICK': 4, 'BIND': 6, 'NEXT': 8, 'ORDER': 4, 'READ': 24, 'READ4': 48, 'MARKS': 140, 'ASK': 48,
        'COLUMNS': 30, 'FRAME': 90, 'TALK': 256}                                    # answer caps (design 3.3 and 4.3)


class OverCap(ValueError):
    """The smallest answer of this shape cannot fit the kind's cap: the question is not asked."""


def literal(text):
    """A GBNF string literal for `text`, escaped."""
    if not isinstance(text, str) or not text:raise ValueError('GRAMMAR_LITERAL: a literal is non-empty text')
    out = text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
    return '"' + out + '"'


def one_of(words):
    """root admits exactly one of `words`."""
    words = list(dict.fromkeys(words))
    if not words:raise ValueError('GRAMMAR_EMPTY: nothing to admit')
    return 'root ::= ' + ' | '.join(literal(w) for w in words) + '\n'


def choice(count, none=True):
    """One option number from 1 to `count`, or 0 for "none of these" when `none`."""
    if not 1 <= count <= 99:raise ValueError('GRAMMAR_COUNT: 1 to 99 options')
    return one_of((['0'] if none else []) + [str(n) for n in range(1, count + 1)])


def picks(count, most, none=True):
    """1 to `most` option numbers separated by single spaces, or 0 alone for none. (That they differ is the parser's check.)"""
    if not 1 <= count <= 99 or not 1 <= most <= 8:raise ValueError('GRAMMAR_COUNT: 1 to 99 options, at most 8 picks')
    tail = ''
    for _ in range(most - 1):tail = '( " " n ' + tail + ')?'
    head = ('"0" | ' if none else '') + 'n ' + tail
    return 'root ::= ' + head.strip() + '\nn ::= ' + ' | '.join(literal(str(n)) for n in range(1, count + 1)) + '\n'


def check(grammar):
    """The grammar a turn sends: None (a kind with no grammar, Talk only) or GBNF with a root rule and no free whitespace."""
    if grammar is None:return None
    if not isinstance(grammar, str) or not re.search(r'(?m)^root\s*::=', grammar):raise ValueError('GRAMMAR_NO_ROOT')
    if FREE_WHITESPACE.search(_LITERALS.sub('""', grammar)):   # a word such as "ws" inside a literal is not whitespace
        raise ValueError('GRAMMAR_FREE_WHITESPACE: a turn grammar admits no free whitespace')
    if len(grammar) > 65536:raise ValueError('GRAMMAR_TOO_LONG')
    return grammar


# -- the token estimate -------------------------------------------------------------------------------------------------------
LETTERS_PER_TOKEN = 4                    # checked against the 4B's vocabulary by the build's fuzz (A3 smoke)
_PIECE = re.compile(r'[\r\n]+|[ \t]+|[0-9]|[A-Za-z]+|[^\x00-\x7f]|[^A-Za-z0-9\s]')


def estimate(text):
    """An upper estimate of the tokens a byte-level BPE vocabulary (the Qwen family) gives `text`: a digit is one token, a
    run of ASCII letters one per LETTERS_PER_TOKEN letters, a non-ASCII letter two, any other sign one; a single space
    before a letter or a sign joins it (none), before a digit or at the end it is one."""
    total = 0;pieces = _PIECE.findall(text)
    for i, p in enumerate(pieces):
        if p[0] in ' \t':
            following = pieces[i + 1] if i + 1 < len(pieces) else ''
            total += 0 if (len(p) == 1 and following[:1] and not following[:1].isdigit() and not following[:1].isspace()) else 1
        elif p[0] in '\r\n':total += 1
        elif p.isascii() and p.isalpha():total += math.ceil(len(p) / LETTERS_PER_TOKEN)
        elif not p.isascii():total += 2
        else:total += 1
    return total


# -- the subset: parse, match, measure, sample, list ----------------------------------------------------------------------------
class _Parser:
    def __init__(self, text):
        self.s = text;self.i = 0

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in ' \t':self.i += 1

    def peek(self):
        self.ws();return self.s[self.i] if self.i < len(self.s) else ''

    def alt(self):
        options = [self.seq()]
        while self.peek() == '|':
            self.i += 1;options.append(self.seq())
        return options[0] if len(options) == 1 else ('alt', tuple(options))

    def seq(self):
        items = []
        while self.peek() not in ('', '|', ')'):items.append(self.item())
        return items[0] if len(items) == 1 else ('seq', tuple(items))

    def item(self):
        node = self.atom()
        while True:
            c = self.s[self.i] if self.i < len(self.s) else ''
            if c == '?':self.i += 1;node = ('rep', node, 0, 1)
            elif c == '*':self.i += 1;node = ('rep', node, 0, None)
            elif c == '+':self.i += 1;node = ('rep', node, 1, None)
            elif c == '{':
                end = self.s.index('}', self.i);body = self.s[self.i + 1:end];self.i = end + 1
                lo, _, hi = body.partition(',')
                lo = int(lo or 0);hi = (None if body.endswith(',') else int(hi)) if ',' in body else lo
                node = ('rep', node, lo, hi)
            else:return node

    def atom(self):
        c = self.peek()
        if c == '"':return ('lit', self.string())
        if c == '[':return self.cls()
        if c == '(':
            self.i += 1;node = self.alt()
            if self.peek() != ')':raise ValueError('GRAMMAR_PARSE: a group is not closed')
            self.i += 1;return node
        m = re.compile(r'[A-Za-z][A-Za-z0-9_-]*').match(self.s, self.i)
        if not m:raise ValueError('GRAMMAR_PARSE: at %r' % self.s[self.i:self.i + 12])
        self.i = m.end();return ('ref', m.group(0))

    def esc(self):
        c = self.s[self.i];self.i += 1
        if c == 'x':v = int(self.s[self.i:self.i + 2], 16);self.i += 2;return chr(v)
        if c == 'u':v = int(self.s[self.i:self.i + 4], 16);self.i += 4;return chr(v)
        return {'n': '\n', 'r': '\r', 't': '\t'}.get(c, c)

    def string(self):
        self.i += 1;out = []
        while self.s[self.i] != '"':
            c = self.s[self.i];self.i += 1
            out.append(self.esc() if c == '\\' else c)
        self.i += 1
        return ''.join(out)

    def cls(self):
        self.i += 1;negated = self.s[self.i] == '^'
        if negated:self.i += 1
        ranges = []
        while self.s[self.i] != ']':
            c = self.s[self.i];self.i += 1
            lo = self.esc() if c == '\\' else c;hi = lo
            if self.s[self.i] == '-' and self.s[self.i + 1] != ']':
                self.i += 1;c = self.s[self.i];self.i += 1;hi = self.esc() if c == '\\' else c
            ranges.append((ord(lo), ord(hi)))
        self.i += 1
        return ('cls', negated, tuple(ranges))


@lru_cache(maxsize=256)
def _rules(grammar):
    rules = {}
    for line in grammar.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        name, sep, body = line.partition('::=')
        if not sep:raise ValueError('GRAMMAR_PARSE: a rule is one line, name ::= body')
        p = _Parser(body);node = p.alt()
        if p.peek():raise ValueError('GRAMMAR_PARSE: left over %r' % p.s[p.i:p.i + 12])
        rules[name.strip()] = node
    if 'root' not in rules:raise ValueError('GRAMMAR_NO_ROOT')
    return rules


def _walk(grammar, fn):
    rules = _rules(grammar);seen = set()

    def go(node):
        if node[0] == 'ref':
            if node[1] not in rules:raise ValueError('GRAMMAR_PARSE: no rule %s' % node[1])
            if node[1] in seen:return fn(('recursive',), go)
            seen.add(node[1])
            try:return go(rules[node[1]])
            finally:seen.discard(node[1])
        return fn(node, go)
    return go(rules['root'])


def _members(node):
    _, negated, ranges = node
    return negated, ranges


def longest_bytes(grammar):
    """The most bytes any answer the grammar admits can take, or None when it admits unbounded answers."""
    def fn(node, go):
        k = node[0]
        if k == 'recursive':return None
        if k == 'lit':return len(node[1].encode('utf-8'))
        if k == 'cls':
            negated, ranges = _members(node)
            return 4 if negated else max(len(chr(hi).encode('utf-8')) for _, hi in ranges)
        if k == 'alt':
            parts = [go(x) for x in node[1]]
            return None if None in parts else max(parts)
        if k == 'seq':
            parts = [go(x) for x in node[1]]
            return None if None in parts else sum(parts)
        if k == 'rep':
            inner = go(node[1])
            return None if inner is None or node[3] is None else inner * node[3]
        raise ValueError(k)
    return _walk(grammar, fn)


def _first(grammar, node):
    """What an answer of this node can begin with: a subset of {'digit', 'space', 'other', 'empty'}."""
    rules = _rules(grammar)

    def go(n, seen):
        k = n[0]
        if k == 'ref':
            return {'other'} if n[1] in seen else go(rules[n[1]], seen | {n[1]})
        if k == 'lit':
            c = n[1][:1]
            return {'digit'} if c.isdigit() else {'space'} if c.isspace() else {'other'}
        if k == 'cls':
            negated, ranges = _members(n)
            return {'digit', 'space', 'other'} if negated else {('digit' if chr(lo).isdigit() else 'space' if chr(lo).isspace() else 'other')
                                                               for lo, _ in ranges}
        if k == 'alt':return set().union(*(go(x, seen) for x in n[1]))
        if k == 'seq':
            out = set()
            for x in n[1]:
                f = go(x, seen);out |= f - {'empty'}
                if 'empty' not in f:return out
            return out | {'empty'}
        if k == 'rep':return go(n[1], seen) | ({'empty'} if n[2] == 0 else set())
        return {'other'}
    return go(node, frozenset())


def worst_tokens(grammar):
    """The upper estimate (see `estimate`) of the tokens of the longest answer the grammar admits; None when unbounded. A
    single space that cannot be followed by a digit, a space or the end joins what follows (no token of its own)."""
    def fn(node, go):
        k = node[0]
        if k == 'recursive':return None
        if k == 'lit':return estimate(node[1]) if node[1].strip(' ') else 1
        if k == 'cls':return 2
        if k == 'alt':
            parts = [go(x) for x in node[1]]
            return None if None in parts else max(parts)
        if k == 'seq':
            parts = []
            for i, x in enumerate(node[1]):
                if x[0] == 'lit' and x[1] == ' ' and i + 1 < len(node[1]):
                    if not (_first(grammar, ('seq', node[1][i + 1:])) & {'digit', 'space', 'empty'}):
                        parts.append(0);continue
                if x[0] == 'lit' and x[1].endswith(' ') and len(x[1]) > 1 and i + 1 < len(node[1]):
                    if not (_first(grammar, ('seq', node[1][i + 1:])) & {'digit', 'space', 'empty'}):
                        parts.append(estimate(x[1][:-1]) if x[1][:-1].strip(' ') else 1);continue
                parts.append(go(x))
            return None if None in parts else sum(parts)
        if k == 'rep':
            inner = go(node[1])
            if inner is None or node[3] is None:return None
            if node[1][0] == 'cls' and _letters_only(node[1]):return math.ceil(node[3] / 3) + 1
            return inner * node[3]
        raise ValueError(k)
    return _walk(grammar, fn)


def _letters_only(node):
    negated, ranges = _members(node)
    return not negated and all(chr(lo).isascii() and chr(hi).isascii() and chr(lo).isalpha() and chr(hi).isalpha() and
                               (chr(lo).islower() == chr(hi).islower()) for lo, hi in ranges)


def fits(grammar, cap):
    """True when every answer the grammar admits is within `cap` tokens by the estimate (never for an unbounded grammar)."""
    if grammar is None:return True
    worst = worst_tokens(grammar)
    return worst is not None and worst <= cap


def _class_regex(node):
    negated, ranges = _members(node)
    body = ''.join('\\U%08x' % lo if lo == hi else '\\U%08x-\\U%08x' % (lo, hi) for lo, hi in ranges)
    return '[' + ('^' if negated else '') + body + ']'


@lru_cache(maxsize=256)
def _regex(grammar):
    def fn(node, go):
        k = node[0]
        if k == 'recursive':raise ValueError('GRAMMAR_RECURSIVE: not matched here')
        if k == 'lit':return re.escape(node[1])
        if k == 'cls':return _class_regex(node)
        if k == 'alt':return '(?:' + '|'.join(go(x) for x in node[1]) + ')'
        if k == 'seq':return ''.join(go(x) for x in node[1])
        if k == 'rep':
            return '(?:' + go(node[1]) + '){%d,%s}' % (node[2], '' if node[3] is None else node[3])
        raise ValueError(k)
    return re.compile(_walk(grammar, fn), re.DOTALL)


def matches(grammar, text):
    """True when the grammar admits `text` exactly."""
    return isinstance(text, str) and _regex(grammar).fullmatch(text) is not None


_SAMPLE_EXTRA = 'éßøçñ中文Ж'


def _class_sample(node, rnd):
    negated, ranges = _members(node)
    if not negated:
        lo, hi = rnd.choice(ranges);return chr(rnd.randint(lo, hi))
    pool = [c for c in [chr(x) for x in range(33, 127)] + list(_SAMPLE_EXTRA)
            if not any(lo <= ord(c) <= hi for lo, hi in ranges)]
    return rnd.choice(pool)


def sample(grammar, rnd=None, longest=False):
    """One answer the grammar admits, drawn at random (with `longest`, every repetition at its most and the alternative with
    the most estimated tokens), for fuzzing against a tokenizer."""
    rnd = rnd or random.Random()

    def fn(node, go):
        k = node[0]
        if k == 'recursive':raise ValueError('GRAMMAR_RECURSIVE: not sampled here')
        if k == 'lit':return node[1]
        if k == 'cls':return _class_sample(node, rnd)
        if k == 'alt':
            if longest:
                drawn = [go(x) for x in node[1]]
                return max(drawn, key=lambda s: (estimate(s), len(s.encode('utf-8'))))
            return go(rnd.choice(node[1]))
        if k == 'seq':return ''.join(go(x) for x in node[1])
        if k == 'rep':
            hi = node[3] if node[3] is not None else node[2] + 3
            n = hi if longest else rnd.randint(node[2], hi)
            return ''.join(go(node[1]) for _ in range(n))
        raise ValueError(k)
    return _walk(grammar, fn)


def admits(grammar, limit=100000):
    """Every answer the grammar admits, listed (for finite shapes only; refuses more than `limit` or an open class)."""
    def fn(node, go):
        k = node[0]
        if k == 'recursive':raise ValueError('GRAMMAR_RECURSIVE')
        if k == 'lit':return [node[1]]
        if k == 'cls':
            negated, ranges = _members(node)
            if negated or sum(hi - lo + 1 for lo, hi in ranges) > 256:raise ValueError('GRAMMAR_NOT_LISTABLE')
            return [chr(c) for lo, hi in ranges for c in range(lo, hi + 1)]
        if k == 'alt':
            out = []
            for x in node[1]:out += go(x)
            return out
        if k == 'seq':
            out = ['']
            for x in node[1]:
                part = go(x);out = [a + b for a in out for b in part]
                if len(out) > limit:raise ValueError('GRAMMAR_NOT_LISTABLE')
            return out
        if k == 'rep':
            if node[3] is None:raise ValueError('GRAMMAR_NOT_LISTABLE')
            part = go(node[1]);out = [];row = ['']
            for n in range(node[3] + 1):
                if n >= node[2]:out += row
                row = [a + b for a in row for b in part]
                if len(out) + len(row) > limit:raise ValueError('GRAMMAR_NOT_LISTABLE')
            return out
        raise ValueError(k)
    listed = list(dict.fromkeys(_walk(grammar, fn)))
    return [t for _, t in sorted(enumerate(listed), key=lambda it: (it[1].count(' '), it[0]))]   # fewer parts first, as E0 listed them


# -- one grammar per kind --------------------------------------------------------------------------------------------------------
def _alts(words):
    words = list(dict.fromkeys(w for w in words if w))
    if not words:raise ValueError('GRAMMAR_EMPTY: nothing to admit')
    return ' | '.join(literal(w) for w in words)


def _fit(build, most, least, cap):
    """The grammar from build(n) for the largest n in [least, most] that fits the cap; OverCap when even `least` does not."""
    for n in range(most, least - 1, -1):
        grammar = build(n)
        if fits(grammar, cap):return grammar
    raise OverCap('GRAMMAR_OVER_CAP: the smallest answer of this shape is over %d tokens' % cap)


def goal(count, most=2, cap=CAPS['GOAL']):
    """GOAL (0.8.6's brief on turns.ask): `1`, `1 2` or `0`."""
    return _fit(lambda n: picks(count, n), most, 1, cap)


def pick(count, cap=CAPS['PICK']):
    """PICK: your typed answer placed among the question's options: `n` or `0`."""
    return _fit(lambda n: choice(count), 1, 1, cap)


def bind(count, most=2, cap=CAPS['BIND']):
    """BIND: listed column values your words mean: `n`, `n n` or `0`."""
    return _fit(lambda n: picks(count, n), most, 1, cap)


def order(count, cap=CAPS['ORDER']):
    """ORDER: the same options reversed: `n` (no none: it is compared with the first pick)."""
    return _fit(lambda n: choice(count, none=False), 1, 1, cap)


def next_pick(count, reasons=REASONS, cap=CAPS['NEXT']):
    """NEXT: `n why`, the option and which of the desk's own measures it wins on."""
    if not 1 <= count <= 4:raise ValueError('GRAMMAR_COUNT: NEXT offers 1 to 4 options')
    bad = [r for r in reasons if r not in REASONS]
    if bad or not reasons:raise ValueError('GRAMMAR_REASON: %s' % (bad or 'none'))
    return _fit(lambda n: 'root ::= n " " why\nn ::= %s\nwhy ::= %s\n' % (_alts(str(i) for i in range(1, count + 1)),
                                                                        _alts(reasons)), 1, 1, cap)


def _words_rule(name, words):
    return '%s ::= %s\n' % (name, _alts(words))


def _phrase(rule, most):
    """`most` words or fewer, one space between (nested optionals: no free whitespace)."""
    tail = ''
    for _ in range(most - 1):tail = '( " " %s %s)?' % (rule, tail)
    return ('%s %s' % (rule, tail)).strip()


def read_line(verbs, handles, request_words, columns=(), value_words=(), kinds=READ_KINDS, most_steps=2, quote_most=6,
              cap=None):
    """READ: `kind|verb Dn "your words" [column] ["value words"]` and up to `most_steps` steps joined by `|`. The verbs are the
    turn's verb table (lane B's view over desk_acts.ACTS: no App verb is ever in it), the handles this turn's numbered list,
    the quoted words your request's own words, the columns the listed things' columns. Within the cap it keeps, in order,
    the most steps, then the most quoted words, then the most value words."""
    cap = cap if cap is not None else (CAPS['READ4'] if most_steps > 2 else CAPS['READ'])
    if not verbs or not handles or not request_words:raise ValueError('GRAMMAR_EMPTY: verbs, handles and your words')

    def build(steps, q, v):
        lines = ['root ::= kind ("|" step){1,%d}\n' % steps, 'kind ::= %s\n' % _alts(kinds),
                 'step ::= verb " " handle " \\"" quote "\\""%s%s\n' % (' (" " column)?' if columns else '',
                                                                       ' (" \\"" value "\\"")?' if value_words else ''),
                 'quote ::= %s\n' % _phrase('qw', q), _words_rule('verb', verbs), _words_rule('handle', handles),
                 _words_rule('qw', request_words)]
        if columns:lines.append(_words_rule('column', columns))
        if value_words:lines += ['value ::= %s\n' % _phrase('vw', v), _words_rule('vw', value_words)]
        return ''.join(lines)
    for steps in range(most_steps, 0, -1):
        for q in range(quote_most, 0, -1):
            for v in range(min(q, 4) if value_words else 1, 0, -1):
                grammar = build(steps, q, v)
                if fits(grammar, cap):return grammar
    raise OverCap('GRAMMAR_OVER_CAP: not even one step of one word fits %d tokens' % cap)


def _line_numbers(lines):
    numbers = sorted({int(n) for n in lines})
    if not numbers or numbers[0] < 1:raise ValueError('GRAMMAR_EMPTY: no line may be pointed at')
    return 'line ::= ' + _alts('L%d' % n for n in numbers) + '\n'


def marks(lines, kinds, words, label_words=(), most=8, field_most=5, cap=CAPS['MARKS']):
    """MARKS: up to `most` lines of `L<n> <kind> | <label> | <value>`, or NONE. `lines` are the page's line numbers the
    doorway did not flag (a flagged line is not in the grammar); `words` the page's own words (values are verbatim on their
    line: the checker proves it); `label_words` the words a label may use (the page's, by default)."""
    label_words = tuple(label_words) or tuple(words)
    if not kinds or not words:raise ValueError('GRAMMAR_EMPTY: kinds and page words')

    def build(n, f):
        return ('root ::= "NONE" | mark %s\n' % ''.join(['( "\\n" mark '] * (n - 1) + [')?'] * (n - 1)) +
                'mark ::= line " " kind " | " label " | " value\n' + _line_numbers(lines) + _words_rule('kind', kinds) +
                'label ::= %s\n' % _phrase('lw', f) + 'value ::= %s\n' % _phrase('pw', f) +
                _words_rule('lw', label_words) + _words_rule('pw', words))
    for f in range(field_most, 0, -1):
        try:return _fit(lambda n: build(n, f), most, 1, cap)
        except OverCap:continue
    raise OverCap('GRAMMAR_OVER_CAP: not even one mark fits %d tokens' % cap)


def ask_lines(lines, words, most=3, value_most=6, cap=CAPS['ASK']):
    """ASK: up to `most` lines of `L<n> | <value>` on the asked page, or NONE."""
    if not words:raise ValueError('GRAMMAR_EMPTY: page words')

    def build(n, f):
        return ('root ::= "NONE" | hit %s\n' % ''.join(['( "\\n" hit '] * (n - 1) + [')?'] * (n - 1)) +
                'hit ::= line " | " value\n' + _line_numbers(lines) + 'value ::= %s\n' % _phrase('pw', f) +
                _words_rule('pw', words))
    for f in range(value_most, 0, -1):
        try:return _fit(lambda n: build(n, f), most, 1, cap)
        except OverCap:continue
    raise OverCap('GRAMMAR_OVER_CAP: not even one line fits %d tokens' % cap)


def columns(count, roles, cap=CAPS['COLUMNS']):
    """COLUMNS: `C1=role C2=role ...`, every column once, in order (each role once is the checker's)."""
    if not 1 <= count <= 24:raise ValueError('GRAMMAR_COUNT: 1 to 24 columns')
    body = ' " " '.join('"C%d=" role' % i for i in range(1, count + 1))
    return _fit(lambda n: 'root ::= %s\nrole ::= %s\n' % (body, _alts(roles)), 1, 1, cap)


def frame(slots, words, must=('ANSWER',), most_pieces=24, cap=CAPS['FRAME']):
    """FRAME: `{ANSWER}` first, then slot names and joining words, one space between. Which slots, how often and which
    words are the gate's (voice_gate); the grammar keeps the frame short and makes digits and signs impossible."""
    if 'ANSWER' not in must:raise ValueError('GRAMMAR_FRAME: {ANSWER} comes first')
    if not words:raise ValueError('GRAMMAR_EMPTY: joining words')
    pieces = ['{%s}' % s for s in dict.fromkeys(slots) if s != 'ANSWER']

    def build(n):
        return ('root ::= "{ANSWER}" %s ("." )?\n' % ''.join(['( " " piece '] * n + [')?'] * n) +
                'piece ::= %s\n' % _alts(pieces + list(words)))
    return _fit(build, most_pieces, 1, cap)


def for_kind(name, **inputs):
    """The kind's grammar by name (a convenience for the lanes; each kind's grammar(inputs) may call its builder directly)."""
    builders = {'GOAL': goal, 'PICK': pick, 'BIND': bind, 'NEXT': next_pick, 'ORDER': order, 'READ': read_line,
                'MARKS': marks, 'ASK': ask_lines, 'COLUMNS': columns, 'FRAME': frame}
    if name == 'TALK':return None
    return builders[name](**inputs)
