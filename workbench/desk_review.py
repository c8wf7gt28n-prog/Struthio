"""A review of the desk asked in her ask line, answered from the records (Graphite 1.0, X1: the day of the paper's section 18).

The owner's paper, section 18: "Kas, review this assembly and tell me whether the proposed power supply is sufficient." ...
"Suppose the settled power is within the stated limit but startup demand remains unresolved. Kasandra should not collapse
those observations into an unconditional approval. She reports that the settled condition is supported and that startup
requires further evaluation."

Before this module such a question went to her model's free words (with a model: "from its memory, not from your files"; the
4B here said it could not review assembly files), or, with no model, to "I have no brain running yet". The desk already holds
the answer, finding by finding: each investigation's findings with their evidence state (supported, refuted, contested), the
ones the desk marks RECHECK because what they rest on changed since, and its open questions. This module says them, in the
table's words and shapes (state_words), and draws the one conclusion the records allow: "sufficient" only when every finding
is supported and nothing is refuted, in recheck or open; otherwise not cleared, naming what is not. No model is asked, so
nothing the model writes becomes the verdict (her rule: the model proposes, the desk disposes).

    REVIEW.search(text)      the words that ask for it: review this assembly / design / desk, whether … is sufficient,
                             adequate, enough, meets its limits, within its limits
    review(read)  -> {'rows': [(state, text)], 'open': [text], 'cleared': bool} | None (no finding on the desk)
    words(rows)   -> her answer, fixed templates registered with mind_words
    asked(face, text) -> True when she answered (shell2.ask calls it before the objective planner)
"""
from __future__ import annotations

import re

REVIEW = re.compile(r'\b(?:review\s+(?:this|the|my)\s+(?:assembly|design|circuit|desk|project|board|supply)|'
                    r'(?:in)?sufficient|adequate|good\s+enough|enough\s+for|'
                    r'meets?\s+(?:its|the|their)\s+(?:limits?|spec(?:ification)?s?|requirements?)|'
                    r'within\s+(?:its|the|their)\s+limits?)\b', re.I)

WORDS = {
    'head': 'What the records say, finding by finding (the desk’s findings and their evidence, not my own judgement):',
    'supported': '■ SUPPORTED · {text}',
    'refuted': '⊘ REFUTED · {text}',
    'contested': '◆ CONTESTED · {text}',
    'recheck': '◧ RECHECK · {text} (what it rests on changed since; it holds only once it is worked again)',
    'unknown': '□ OPEN · {text}',
    'question': '□ OPEN QUESTION · {text}',
    'not_cleared': 'So I cannot call it sufficient. What is supported holds; what is refuted, in recheck or open is not cleared, '
                   'and finishing one part does not clear the rest.',
    'cleared': 'Every finding on this desk is supported and no question is open. That is the records’ word, not a judgement of the design.',
    'how': 'Each line is a record of the desk; FINDINGS (live) and the board show the same, and DOUBT asks what a supported one may hide.',
}
try:
    from . import mind_words
    mind_words.register('desk_review', WORDS, kind='sentence')
except Exception:  # noqa: BLE001 - the words stand without the register
    pass

ORDER = ('refuted', 'recheck', 'contested', 'unknown', 'supported')
MOST_INVESTIGATIONS = 4
MOST_ROWS = 8


def review(read):
    """The desk's findings and open questions, as the records hold them now. read(operation, arguments) -> result or None."""
    listing = read('investigation.list', {}) or {}
    desk = read('field.read', {}) or {}
    stale = {str(r.get('id')) for r in desk.get('objects') or () if r.get('kind') == 'finding' and str(r.get('state')) == 'recheck'}
    rows, questions = [], []
    for inv in list(listing.get('investigations') or ())[:MOST_INVESTIGATIONS]:
        sheet = read('investigation.sheet', {'id': inv['id']}) or {}
        for claim in list(sheet.get('learned') or ()) + list(sheet.get('unresolved') or ()):
            if claim.get('retired'):continue
            text = ' '.join(str(claim.get('text') or '').split())
            if not text:continue
            if claim.get('role') == 'QUESTION':
                if str(claim.get('evidence_state') or '').upper() not in ('SUPPORTED', 'ANSWERED'):questions.append(text)
                continue
            if claim.get('role') != 'FINDING':continue
            state = str(claim.get('evidence_state') or 'UNKNOWN').lower()
            if state not in ORDER:state = 'unknown'
            if ('claim:%s' % claim.get('id')) in stale and state != 'refuted':state = 'recheck'
            rows.append((state, text))
    if not rows and not questions:return None
    rows.sort(key=lambda r: ORDER.index(r[0]))
    cleared = bool(rows) and all(s == 'supported' for s, _ in rows) and not questions
    return {'rows': rows[:MOST_ROWS], 'open': questions[:3], 'cleared': cleared}


def words(found):
    lines = [WORDS['head']]
    lines += [WORDS[state].format(text=text) for state, text in found['rows']]
    lines += [WORDS['question'].format(text=text) for text in found['open']]
    lines.append(WORDS['cleared'] if found['cleared'] else WORDS['not_cleared'])
    lines.append(WORDS['how'])
    return '\n'.join(lines)


def asked(face, text):
    """Her answer to a review question, from the records; False when the words are not one, or the desk has no finding."""
    if not REVIEW.search(text or ''):return False
    try:
        from .her_column_qt import read as column_read
        found = review(lambda op, args=None: column_read(face.host, op, args))
    except Exception:  # noqa: BLE001 - the usual way answers then
        return False
    if not found:return False
    face.mine(text)
    face.say(words(found))
    return True
