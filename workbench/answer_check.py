"""The checker: what stands between a model's answer and the owner (0.8.6 S7, "Kas's mind, no model"; lane A).

Three checks, all exact, none asking a model:

    check_pick(brief, picks)      a GOAL answer (the numbers a model picked from a brief) -> turns.Verdict
    check_words(sentence, desk)   written words against the desk (the WORDS check; 0.8.7's gate composes it) -> Verdict
    marks(text, desk)             every number of a page against the desk: one Mark each (the page check)
    page(kernel, principal, id)   the page check of one of the owner's pages, read from the desk as it stands
    replay(path)                  the half-build's recorded GOAL answers, judged again (the acceptance examples)

**A GOAL answer** (design 4.1, rule 3) is taken only after five checks, in order:
  shape       one to three different numbers in range, or 0 alone (none of these)
  licence     each pick is backed by a clause of the request that holds both the words naming what the option is about
              and one of its verbs ("trace" and "bench readings" in the same clause); a pick no clause backs is trimmed,
              and an answer left with nothing is refused
  authority   a pick that differs from another option only in a revision, where the request does not name the revision,
              is refused: which revision applies is the owner's to say, never the model's
  coverage    a clause that backs some option and backs none of the picks leaves the answer unsettled (the buttons decide)
  joint plan  the picked desk goals together have a plan on the desk (planner.plan); none: refused
TAKEN, TRIMMED (taken without what went too far), REFUSED or UNSETTLED. The model's raw answer is always kept as its own.

**The page check** (design 2.9). Each number with a unit, and each day, gets one mark; a mark never says "true":
    on the desk      a value the desk holds now, exactly
    made from        not on the desk, but one of its values less another, or two added (45 ms less 40 ms)
    rounded          a desk value rounded to the places written (333 mA for 1/3 A in whole mA)
    differs          the place it came from now says something else (row 3 now says 300 mA)
    unit slip        the digits of a desk value under another unit of the same kind (250 A for 250 mA)
    not on the desk  none of these
    not checked      a unit the maths does not read
**The WORDS check** takes a sentence only when every number is on the desk, made from it or rounded from it, no number is
hedged ("about 3.1 W"), a word of holding agrees with the goal's state (never "holds" for an UNDECIDED goal), and an absence
is said of the desk ("nothing on the desk shows a payment") unless the owner agreed the sheet is complete.

Exact throughout: Fraction, never float (field_doubt's float comparison is not used for these marks).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from datetime import date
from fractions import Fraction
from pathlib import Path

from . import hand_words, model_words, reading
from .turns import Verdict

MARKS = ('ON_DESK', 'MADE_FROM', 'ROUNDED', 'DIFFERS', 'UNIT_SLIP', 'NOT_ON_DESK', 'NOT_CHECKED')
MARK_WORDS = {'ON_DESK': 'on the desk', 'MADE_FROM': 'made from the desk', 'ROUNDED': 'rounded', 'DIFFERS': 'differs',
              'UNIT_SLIP': 'unit slip', 'NOT_ON_DESK': 'not on the desk', 'NOT_CHECKED': 'not checked'}
WORDS_TAKE = ('ON_DESK', 'MADE_FROM', 'ROUNDED')
HOLDING = ('HOLDS', 'SUPPORTED', 'TRUE', 'HOLDS_EITHER_WAY')
FAILING = ('DOES_NOT_HOLD', 'REFUTED', 'FALSE', 'FAILS')
MONTHS = reading.MONTHS
NUMBER = re.compile(r"(?<![\w.,/])(?P<hedge>(?:about|around|roughly|approximately|approx\.?|nearly|almost|circa|some|~)\s*)?"
                    r"(?P<int>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<frac>\d+))?\s?(?P<unit>[A-Za-zµΩ]{1,3})\b", re.I)
DAY = re.compile(r"\b(?P<hedge>(?:about|around|roughly|nearly)\s+)?(?:(?P<d>\d{1,2})\s+(?P<m>%s)(?:\s+(?P<y>\d{4}))?|(?P<iso>\d{4}-\d{2}-\d{2}))\b"
                 % '|'.join(MONTHS), re.I)
HOLD_WORDS = re.compile(r"\b(?:holds?|inside|within|passes|meets|in\s+spec|is\s+ok|is\s+fine)\b", re.I)
FAIL_WORDS = re.compile(r"\b(?:does\s+not\s+hold|doesn't\s+hold|over|outside|fails?|exceeds?|beyond)\b", re.I)
ABSENCE = re.compile(r"\b(?:no|never|nothing|none|not\s+any|neither)\b", re.I)
DESK_SCOPE = re.compile(r"\b(?:on\s+(?:the|your)\s+desk|in\s+your\s+records|the\s+desk\s+(?:shows|has|holds|gives|carries)|"
                        r"(?:your|the)\s+records\s+(?:show|hold|have)|i\s+(?:can\s+)?find)\b", re.I)


# == the GOAL answer ===================================================================================================================
def _backed(b, o):
    """The clauses that back option `o`: they hold its naming words and, for a desk goal, one of its verbs."""
    return tuple(i for i, s in enumerate(b.stems) if (s & o.names) and (not o.verbs or (s & o.verbs)))


def _names_revision(b, o, clauses):
    if not o.revision:return True
    for i in clauses:
        words = b.stems[i];low = b.clauses[i].casefold()
        marks = {m.lower() for m in o.revision.split()}
        if re.search(r'\b(?:rev|revision)\.?\s*(?:%s)\b' % '|'.join(re.escape(m) for m in marks), low):return True
        title_marks = {reading._mark(t)[1].lower() for t in (v for g in o.goals() for v in g[1].values()) if reading._mark(t)[1]}
        if words & title_marks:return True
    return False


def shape(picks, count):
    """The picks as a tuple of option numbers (() for none), from a list, a tuple, the turn contract's line ("1 2", "0"),
    or the half-build's JSON ({"pick": [...]} with count + 1 for none). Anything else raises model_words.Invalid."""
    if isinstance(picks, model_words.ModelSaid):return model_words.options(picks, count, 3, none=True)
    if isinstance(picks, str):
        text = picks.strip()
        if text.startswith('{'):
            try:return tuple(hand_words.read_pick(text, count + 1))
            except hand_words.Invalid as exc:raise model_words.Invalid('SHAPE: %s' % exc) from None
        return model_words.options(model_words.ModelSaid(text), count, 3, none=True)
    if isinstance(picks, dict):
        try:return tuple(hand_words.read_pick(picks, count + 1))
        except hand_words.Invalid as exc:raise model_words.Invalid('SHAPE: %s' % exc) from None
    if not isinstance(picks, (list, tuple)):raise model_words.Invalid('SHAPE: not a list of numbers')
    picks = tuple(picks)
    if picks in ((), (0,)):return ()
    if any(type(n) is not int for n in picks):raise model_words.Invalid('NOT_NUMBERS')
    if 0 in picks:raise model_words.Invalid('NONE_WITH_OTHERS')
    if len(picks) > 3:raise model_words.Invalid('TOO_MANY')
    if len(set(picks)) != len(picks):raise model_words.Invalid('REPEATED')
    if any(not 1 <= n <= count for n in picks):raise model_words.Invalid('OUT_OF_RANGE')
    return picks


def check_pick(b, picks, world=None):
    """A GOAL answer against its brief (see the module's words) -> turns.Verdict; value is the tuple of picks kept."""
    checks = []
    try:
        picks = shape(picks, len(b.options))
    except model_words.Invalid as exc:
        return Verdict('REFUSED', None, ('SHAPE',), (('shape', False, str(exc)[:120]),))
    checks.append(('shape', True, ' '.join(str(n) for n in picks) or '0'))
    backing = {o.n: _backed(b, o) for o in b.options}
    asked = sorted({i for c in backing.values() for i in c})
    if not picks:
        if asked:
            checks.append(('coverage', False, 'the request asks for %s' % '; '.join(o.words for o in b.options if backing[o.n])[:200]))
            return Verdict('UNSETTLED', (), ('NOT_COVERED',), tuple(checks))
        checks.append(('coverage', True, 'none of these, and no clause asks for any of them'))
        return Verdict('TAKEN', (), (), tuple(checks))
    kept = tuple(n for n in picks if backing[n]);trimmed = tuple(n for n in picks if not backing[n])
    checks.append(('licence', bool(kept), 'kept %s; trimmed %s' % (' '.join(map(str, kept)) or 'none', ' '.join(map(str, trimmed)) or 'none')))
    if not kept:return Verdict('REFUSED', None, ('UNLICENSED',), tuple(checks))
    for n in kept:
        o = b.option(n)
        twins = [p for p in b.options if p.n != n and p.same == o.same]
        if (twins or o.revision) and o.revision and not _names_revision(b, o, backing[n]):
            checks.append(('authority', False, 'option %d differs from %d only in its revision, and the request does not name it' % (n, twins[0].n if twins else n)))
            return Verdict('REFUSED', None, ('AUTHORITY',), tuple(checks))
    checks.append(('authority', True, 'no revision, tolerance or rule is chosen by the pick'))
    covered = {i for n in kept for i in backing[n]}
    missing = [i for i in asked if i not in covered]
    if missing:
        checks.append(('coverage', False, 'nothing picked for “%s”' % b.clauses[missing[0]][:120]))
        return Verdict('UNSETTLED', kept, ('NOT_COVERED',), tuple(checks))
    checks.append(('coverage', True, 'every clause that asks for an option has its pick'))
    world = world if world is not None else b.world
    goals = [g for n in kept for g in b.option(n).goals()]
    if goals and world is not None:
        from . import desk_ops, goals as G, planner
        goal_list = hand_words.goals_of([g for g in goals if g[0] != 'tidy']) ;goal_list.append(G.tidy(len(goal_list) + 1))
        found = planner.plan(desk_ops.State(), world, goal_list)
        if found.state not in ('FOUND', 'HOLDS'):
            checks.append(('joint plan', False, found.words or found.state))
            return Verdict('REFUSED', None, ('NO_JOINT_PLAN',), tuple(checks))
        checks.append(('joint plan', True, '%d acts' % len(found.steps)))
    return Verdict('TRIMMED' if trimmed else 'TAKEN', kept, ('TRIMMED',) if trimmed else (), tuple(checks))


# == the desk's values ====================================================================================================================
@dataclass(frozen=True)
class Value:
    """One value the desk holds now: exact, in its base unit, with where it is and what that place said before."""
    base: Fraction                       # in the base unit of its kind (a day: its ordinal)
    kind: str                            # the dimension's name, or 'day'
    said: str                            # as written there ("300 mA")
    where: str                           # the place, in words ("row 3 of “Rail Demo bench readings”")
    name: str = ''                       # what it is ("settled current", "settled power")
    ref: dict = field(default_factory=dict)
    was: tuple = ()                      # ((base, said), ...): what this place said before (a reviewed reading, an earlier result)
    number: Fraction = None              # the number as written, in its own unit
    unit: str = ''


@dataclass(frozen=True)
class Quantity:
    text: str
    at: tuple
    number: Fraction
    places: int
    unit: str
    kind: str
    base: Fraction
    factor: Fraction
    hedged: bool = False


@dataclass(frozen=True)
class Mark:
    said: str
    at: tuple
    mark: str
    words: str                          # "“250 mA” differs (row 3 now says 300 mA)"
    refs: tuple = ()

    def as_record(self):
        return {'said': self.said, 'at': list(self.at), 'mark': self.mark, 'mark_words': MARK_WORDS[self.mark], 'words': self.words,
                'refs': list(self.refs)}


def _exact(int_part, frac):
    whole = int(int_part.replace(',', ''))
    return Fraction(whole) + (Fraction(int(frac), 10 ** len(frac)) if frac else 0), len(frac or '')


def unit_of(unit):
    """(kind, factor to the base unit) of a unit the maths reads, else None."""
    from . import math_units
    try:
        dimension, factor = math_units.unit_spec(unit)
    except ValueError:
        return None
    return str(math_units.dimension_name(dimension)), Fraction(factor)


def value(number, unit, where, name='', ref=None, was=()):
    """A Value from a number written as text (exact) and its unit; None when either cannot be read. `was`: earlier numbers
    (text) the same place said, in the same unit."""
    m = re.fullmatch(r'\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s*', str(number or ''))
    spec = unit_of(str(unit or '').strip()) if m else None
    if spec is None:
        r = re.fullmatch(r'\s*(\d+)/(\d+)\s*', str(number or ''))
        spec = unit_of(str(unit or '').strip()) if r else None
        if spec is None:return None
        n = Fraction(int(r.group(1)), int(r.group(2)))
    else:
        n, _ = _exact(m.group(1), m.group(2))
    kind, factor = spec
    earlier = []
    for w in was or ():
        e = value(w, unit, where)
        if e is not None and e.base != n * factor:earlier.append((e.base, e.said))
    return Value(n * factor, kind, '%s %s' % (str(number).strip(), str(unit).strip()), where, name, dict(ref or {}), tuple(earlier), n, str(unit).strip())


def day_value(day, where, name='', ref=None):
    day = date.fromisoformat(day) if isinstance(day, str) else day
    return Value(Fraction(day.toordinal()), 'day', '%d %s' % (day.day, MONTHS[day.month - 1].capitalize()), where, name, dict(ref or {}), (),
                 Fraction(day.toordinal()), 'day')


def quantities(text):
    """Every number with a unit the maths reads, in order: [Quantity]. A plain count, a page number or a word that is not a
    unit is not a quantity."""
    out = []
    for m in NUMBER.finditer(str(text or '')):
        spec = unit_of(m.group('unit'))
        if spec is None:continue
        n, places = _exact(m.group('int'), m.group('frac'))
        kind, factor = spec
        start = m.start('int')
        out.append(Quantity(text[start:m.end()], (start, m.end()), n, places, m.group('unit'), kind, n * factor, factor, bool(m.group('hedge'))))
    return out


def days(text):
    """Every day named in the text, as (said, at, month, day, year or None, hedged)."""
    out = []
    for m in DAY.finditer(str(text or '')):
        if m.group('iso'):
            try:d = date.fromisoformat(m.group('iso'))
            except ValueError:continue
            out.append((m.group(0), m.span(), d.month, d.day, d.year, bool(m.group('hedge'))))
        else:
            out.append((m.group(0).strip(), (m.start('d'), m.end()), MONTHS.index(m.group('m').lower()) + 1, int(m.group('d')),
                        int(m.group('y')) if m.group('y') else None, bool(m.group('hedge'))))
    return out


def _rounds(q, v):
    """Whether q is v rounded (half up) to the places q is written with, in q's unit."""
    there = v.base / q.factor * (10 ** q.places)
    return (there.numerator * 2 + there.denominator) // (2 * there.denominator) == q.number * (10 ** q.places)


def _place(q, desk):
    same = [v for v in desk if v.kind == q.kind]
    exact = [v for v in same if v.base == q.base]
    if exact:
        v = exact[0]
        return Mark(q.text, q.at, 'ON_DESK', '“%s” is on the desk (%s%s)' % (q.text, v.where, '' if v.said.replace(' ', '') == q.text.replace(' ', '') else ', %s' % v.said),
                    tuple(x.ref for x in exact if x.ref))
    rounded = [v for v in same if _rounds(q, v)]
    if rounded:
        v = rounded[0]
        return Mark(q.text, q.at, 'ROUNDED', '“%s” is rounded (%s gives %s)' % (q.text, v.where, v.said), (v.ref,) if v.ref else ())
    was = [v for v in same if any(b == q.base for b, _ in v.was)]
    if was:
        v = was[0]
        now = ('%s now says %s' % (v.where, v.said)) if v.ref.get('cell') else ('%s is now %s' % (v.name or v.where, v.said))
        return Mark(q.text, q.at, 'DIFFERS', '“%s” differs (%s)' % (q.text, now), (v.ref,) if v.ref else ())
    for a in same:
        for c in same:
            if a is not c and a.where != c.where and a.base - c.base == q.base:
                return Mark(q.text, q.at, 'MADE_FROM', '“%s” is made from the desk (%s less %s)' % (q.text, a.said, c.said), tuple(x.ref for x in (a, c) if x.ref))
    for n, a in enumerate(same):
        for c in same[n + 1:]:
            if a.where != c.where and a.base + c.base == q.base:
                return Mark(q.text, q.at, 'MADE_FROM', '“%s” is made from the desk (%s and %s together)' % (q.text, a.said, c.said), tuple(x.ref for x in (a, c) if x.ref))
    slip = [v for v in same if v.number == q.number and v.unit != q.unit]
    if slip:
        v = slip[0]
        return Mark(q.text, q.at, 'UNIT_SLIP', '“%s”: a unit slip (%s is %s)' % (q.text, v.where, v.said), (v.ref,) if v.ref else ())
    return Mark(q.text, q.at, 'NOT_ON_DESK', '“%s” is not on the desk' % q.text)


def _place_day(said, at, month, day, year, desk):
    held = [v for v in desk if v.kind == 'day']
    for v in held:
        d = date.fromordinal(int(v.base))
        if (d.month, d.day) == (month, day) and (year is None or year == d.year):
            return Mark(said, at, 'ON_DESK', '“%s” is on the desk (%s)' % (said, v.where), (v.ref,) if v.ref else ())
    has = ' or '.join(dict.fromkeys(v.said for v in held))
    return Mark(said, at, 'NOT_ON_DESK', '%s: not on the desk%s' % (said, ' (the desk has %s)' % has if held else ''))


def marks(text, desk):
    """One Mark for every number with a unit and every day in `text`, in order, against `desk` ([Value])."""
    out = []
    for q in quantities(text):out.append(_place(q, desk))
    for said, at, month, day, year, _ in days(text):out.append(_place_day(said, at, month, day, year, desk))
    return sorted(out, key=lambda m: m.at)


def margin(found):
    """The quiet margin note of a page: "2 numbers differ from the desk", or '' when nothing differs."""
    differ = sum(1 for m in found if m.mark in ('DIFFERS', 'UNIT_SLIP'))
    away = sum(1 for m in found if m.mark == 'NOT_ON_DESK')
    parts = []
    if differ:parts.append('%d number%s differ%s from the desk' % (differ, '' if differ == 1 else 's', 's' if differ == 1 else ''))
    if away:parts.append('%d %s not on the desk' % (away, 'is' if away == 1 else 'are'))
    return '; '.join(parts)


# == the WORDS check ======================================================================================================================
def check_words(sentence, desk, goals=None, complete=False):
    """Written words against the desk -> Verdict (state TAKEN or REFUSED; value the marks). `goals`: {name: state} of the
    goals the words may speak of; `complete`: whether the owner agreed (a COMPLETE word) that the sheet an absence is read
    from is complete."""
    text = str(sentence or '');checks = [];why = []
    found = marks(text, desk)
    hedged = [q.text for q in quantities(text) if q.hedged] + [d[0] for d in days(text) if d[5]]
    if hedged:why.append('HEDGED');checks.append(('numbers', False, 'a hedged number is not a desk value: %s' % ', '.join(hedged)))
    bad = [m for m in found if m.mark not in WORDS_TAKE]
    if bad:why.append(bad[0].mark);checks.append(('numbers', False, '; '.join(m.words for m in bad)))
    elif found:checks.append(('numbers', True, '; '.join(m.words for m in found)))
    claim = 'FAILS' if FAIL_WORDS.search(text) else 'HOLDS' if HOLD_WORDS.search(text) else None
    if claim and goals:
        said = reading.stems(text)
        named = [(n, s) for n, s in goals.items() if reading.stems(n) and reading.stems(n) <= said] or (list(goals.items()) if len(goals) == 1 else [])
        for name, state in named:
            agrees = state in HOLDING if claim == 'HOLDS' else state in FAILING
            checks.append(('state', agrees, '%s: the words say it %s; the desk says %s' % (name, 'holds' if claim == 'HOLDS' else 'does not hold', state)))
            if not agrees:why.append('STATE');break
    if ABSENCE.search(text) and not DESK_SCOPE.search(text) and not FAIL_WORDS.search(text):
        if complete:checks.append(('absence', True, 'the sheet is agreed complete'))
        else:
            why.append('ABSENT_IS_NOT_FALSE')
            checks.append(('absence', False, 'nothing on the desk shows it, but no sheet is agreed complete: say "nothing on the desk shows ..."'))
    return Verdict('REFUSED' if why else 'TAKEN', tuple(m.as_record() for m in found), tuple(why), tuple(checks), basis='deduction')


# == the page check, on the desk as it stands ===============================================================================================
def _call(kernel, principal, operation, arguments):
    try:
        answer = kernel.dispatch(operation, arguments, principal)
    except Exception:  # noqa: BLE001 - a record that cannot be read gives no value; it never crashes the check
        return None
    return answer['result'] if answer.get('ok') else None


def _short(title):
    return re.sub(r'^\s*\S+\s+Demo\s+', '', str(title or '').split(' · ')[0]).strip()


def desk_values(kernel, principal):
    """Every value the desk holds now, exactly: each reviewed row of its sheets (the working cell, with what the reviewed
    reading said if the cell has since been set), and each calculation's result (with what it gave before it was worked
    again, from the Field's own record of moved results)."""
    from .field_source import read_field
    got = read_field(kernel, principal)
    fld = got[0] if isinstance(got, tuple) else got
    moved = {}
    for was, now, name in getattr(fld, 'moved', ()) or ():moved.setdefault(_short(name), []).append(was)
    out = []
    for obj in fld.objects:
        target = obj.target if isinstance(obj.target, dict) else {}
        if obj.kind == 'sheet' and target.get('id'):
            sheet = _call(kernel, principal, 'office.get', {'id': target['id']}) or {}
            cells = ((sheet.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
            for row in (sheet.get('origin') or {}).get('reviewed_rows') or ():
                at = row.get('sheet_row');now = str((cells.get('B%s' % at) or {}).get('value') or '').strip()
                unit = str((cells.get('C%s' % at) or {}).get('value') or '').strip()
                reviewed = str(row.get('value') or '').strip()
                v = value(now, unit, 'row %s' % at, str(row.get('parameter') or '').lower(),
                          {'sheet': target['id'], 'title': obj.title, 'cell': 'B%s' % at, 'parameter': row.get('parameter')},
                          was=(reviewed,) if reviewed and reviewed != now else ())
                if v is not None:out.append(v)
        elif obj.kind == 'calculation' and target.get('id'):
            doc = (_call(kernel, principal, 'documents.get', {'id': target['id']}) or {}).get('document') or {}
            result = ((((doc.get('derivation') or {}).get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value') or {}
            number = result.get('rational') if re.fullmatch(r'\d+/\d+', str(result.get('rational') or '')) else result.get('decimal')
            name = _short(obj.title)
            earlier = []
            for w in moved.get(name, ()):
                m = re.fullmatch(r'\s*([\d.,/]+)\s*(\S+)\s*', str(w))
                if m and m.group(2) == result.get('unit'):earlier.append(m.group(1))
            v = value(number, result.get('unit') or '', name, name.lower(), {'calculation': target['id'], 'title': obj.title}, was=earlier)
            if v is not None:out.append(replace(v, said='%s %s' % (result.get('decimal'), result.get('unit'))))
    return out


def page(kernel, principal, ident):
    """The page check of one page: {'marks', 'margin', 'model_calls': 0}. A read: nothing is written."""
    got = _call(kernel, principal, 'documents.get', {'id': ident})
    if not got:raise ValueError('That page cannot be read now')
    found = marks(str(got.get('plain') or ''), desk_values(kernel, principal))
    return {'schema': 'kas.page-marks/1', 'id': ident, 'marks': [m.as_record() for m in found], 'margin': margin(found), 'model_calls': 0}


ID = {'type': 'string', 'minLength': 1, 'maxLength': 80}
FIELDS = {'pages.marks': ({'id': ID}, ['id'])}
SCOPES = {'pages.marks': 'read'}


def dispatch(kernel, op, args, principal):
    if op == 'pages.marks':return page(kernel, principal, args['id'])
    raise ValueError('Unknown page check operation')


# == the half-build's recordings, judged again ==================================================================================================
RECORDINGS = Path(__file__).resolve().parent.parent / 'tests_integrated' / 'data' / 'everyday' / 'goal_answers_recorded.json'


def replay(path=None):
    """Every recorded GOAL answer judged by check_pick over the options the model was shown: [{'file', 'model', 'run',
    'name', 'text', 'pick', 'state', 'kept', 'why'}]."""
    from .hand_model_checks import WORLD
    from . import brief
    data = json.loads(Path(path or RECORDINGS).read_text(encoding='utf-8'))
    out = []
    for f in data['files']:
        for run in f['runs']:
            for turn in run['turns']:
                b = brief.from_candidates(turn['text'], [(t, p) for t, p in turn['candidates']], WORLD)
                v = check_pick(b, list(turn['pick']))
                out.append({'file': f['name'], 'model': f['model'], 'run': run['run'], 'name': turn['name'], 'text': turn['text'],
                            'pick': list(turn['pick']), 'state': v.state, 'kept': list(v.value) if v.value is not None else None, 'why': list(v.why)})
    return out
