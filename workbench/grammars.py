"""The one grammar builder for model turns (0.8.7, slice E0 starts it; lane A's A3 grows it).

Every turn kind's answer is a terse line under a per-request GBNF grammar with no free whitespace (design 3.3): the same
two-step reading is 22 tokens as a line, 46 as compact JSON and 102 as the JSON a small model writes under a schema that
allows whitespace, and writing is the slow half on the owner's computer. A kind's `grammar(inputs)` returns the text these
functions build; turns.ask sends it with the question and refuses a grammar with free whitespace (`check`).

Only literal alternatives are built here, so what a grammar admits can be listed exactly (`admits`), which is what A3's fuzz
against the tokenizer will read.
"""
from __future__ import annotations

import re

FREE_WHITESPACE = re.compile(r'\[[^\]]*(?:\\t|\\n|\\r| )[^\]]*\][*+]|\bws\b|\\s')


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
    if FREE_WHITESPACE.search(grammar):raise ValueError('GRAMMAR_FREE_WHITESPACE: a turn grammar admits no free whitespace')
    if len(grammar) > 65536:raise ValueError('GRAMMAR_TOO_LONG')
    return grammar


def admits(grammar):
    """Every answer a grammar built here admits, listed (for the caps check and A3's fuzz). Only the shapes above."""
    rules = dict(re.findall(r'(?m)^(\w+)\s*::=\s*(.*)$', grammar))
    lit = lambda s: [bytes(m, 'utf-8').decode('unicode_escape') for m in re.findall(r'"((?:[^"\\]|\\.)*)"', s)]
    if 'n' not in rules:return lit(rules['root'])
    numbers = lit(rules['n']);most = 1 + rules['root'].count('" " n')
    out = ['0'] if rules['root'].lstrip().startswith('"0"') else []
    rows = [[x] for x in numbers]
    for _ in range(most):
        out += [' '.join(r) for r in rows]
        rows = [r + [x] for r in rows for x in numbers]
    return out
