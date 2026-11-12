"""Quiet connections (HATCH AGENT-01): while the owner writes, the records that share the page's words, found by word match.

CONTRACT (registered by the integrator; the implementer fills this module without changing names, arguments or shapes).

  ledger.related {text, limit?, exclude?} -> {related:[{id, kind, label, words:[...], score, open}], basis:'WORD_MATCH_NO_MODEL', searched:{...}}   read

The text is the page (or the selection) the owner is writing; tokens come from tool_selection.tokens; candidates are the
owner's own records: ideas (text), projects (title and intent), documents (title and words, excluding the document named
in exclude), investigations (question) and agent assignments (request); each candidate's id is its cabinet identity
('idea:<id>', 'project:<id>', 'document:<id>', 'investigation:<id>') so the right column can select it; 'open' names the
destination route (documents:<id>, project_desk, investigations). Bounded: at most 400 candidates read, at most limit (10)
returned, scored by shared words with rarer words weighing more; a record sharing fewer than two words is not related.
No model, no network, no job.

How it is filled (WI-C). Each candidate is reduced to its token set once; a page word and a record word are the same word
when tool_selection's spellings meet (number / numbers, quantity / quantities), and such a pair counts as one shared word,
not two, so the two-word minimum means two different words. A word's weight is 1 + ln(candidates / records that carry it):
a word every record uses adds about 1, a word only one record shares adds more. The score is the sum over the shared
words, so a record sharing two rare words outranks one sharing two common ones. Sources that are not available yet
(their operation raises NotImplementedError until its work item lands, or is refused) are skipped and named in
'searched' with the reason, never raised. Reads: one desk listing per record kind (full records, which is how the desk
reads), investigation.list and agent.list through the kernel (both observer operations: no Timeline noise).
"""
from __future__ import annotations
import math
from . import project_desk as records
from .tool_selection import forms, tokens

FIELDS = {
    'ledger.related': ({'text': {'type': 'string', 'minLength': 1, 'maxLength': 40000}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 10},
                        'exclude': {'type': 'array', 'maxItems': 20, 'items': {'type': 'string', 'maxLength': 120}}}, ['text']),
}
SCOPES = {op: 'read' for op in FIELDS}
OBSERVERS = ('ledger.related',)

BASIS = 'WORD_MATCH_NO_MODEL'
MAX_CANDIDATES = 400      # read in all, over every source
PER_SOURCE = 100          # the desk listing's page size, and the cap per record kind
MIN_SHARED = 2            # a record sharing fewer words than this is not related
LABEL = 80
DEFAULT_LIMIT = 10


def label_of(text, limit=LABEL):
    words = ' '.join(str(text or '').split())
    return words if len(words) <= limit else words[:limit - 1].rstrip() + '…'


def shared_words(page, candidate):
    """The words a page and a record share, one entry per word: when both a spelling and its root are shared
    ('numbers' and 'number'), the longer spelling stands for the word."""
    both = set(page) & set(candidate)
    kept = set(both)
    for form in both:
        for other in forms(form) - {form}:
            if other in kept and form in kept: kept.discard(other)
    return sorted(kept)


def weights(candidates):
    """1 + ln(N / df) per token: rarer words weigh more. df counts the records whose token set carries the token."""
    total = max(1, len(candidates)); df = {}
    for row in candidates:
        for token in row['tokens']: df[token] = df.get(token, 0) + 1
    return {token: 1.0 + math.log(total / count) for token, count in df.items()}


def rank(words, candidates, limit=DEFAULT_LIMIT, minimum=MIN_SHARED):
    """Score every candidate ({id, kind, label, open, tokens}) against the page's words; the best first, at most limit,
    none sharing fewer than `minimum` words. Pure: no reads."""
    page = set(words or ()); limit = DEFAULT_LIMIT if limit is None else max(1, min(int(limit), DEFAULT_LIMIT))
    if len(page) < minimum or not candidates: return []
    weight = weights(candidates); out = []
    for row in candidates:
        shared = shared_words(page, row['tokens'])
        if len(shared) < minimum: continue
        # one weight per word whatever its spelling here: the most widely shared form's (the root's) weight
        score = sum(min(weight.get(form, 1.0) for form in (forms(word) & set(row['tokens'])) or {word}) for word in shared)
        out.append({'id': row['id'], 'kind': row['kind'], 'label': row['label'], 'words': shared, 'score': round(score, 3), 'open': row['open']})
    out.sort(key=lambda r: (-r['score'], -len(r['words']), r['label'], r['id']))
    return out[:limit]


def candidate(ident, kind, label, open_, text):
    return {'id': ident, 'kind': kind, 'label': label_of(label) or kind, 'open': open_, 'tokens': tokens(text)}


def gather(kernel, principal, exclude=()):
    """The owner's own records as candidates, bounded, with a note per source: a count, or why it was skipped."""
    excluded = set(exclude or ()); rows = []; searched = {'candidates': 0, 'bound': MAX_CANDIDATES, 'skipped': {}}

    def keep(row):
        """True when the record became a candidate; the excluded page and anything past the bound are not counted."""
        if row['id'] in excluded or row['id'].split(':', 1)[1] in excluded: return False
        if len(rows) >= MAX_CANDIDATES: return False
        rows.append(row); return True

    def desk(kind):
        with kernel.db() as db:
            records.ensure(db)
            return records.listing(db, kind, {'limit': PER_SOURCE}, principal)['records']

    for kind in ('idea', 'project', 'document'):
        name = kind + 's'
        try: found = desk(kind)
        except (ValueError, OSError, KeyError, TypeError) as exc: searched['skipped'][name] = str(exc)[:160]; continue
        count = 0
        for r in found:
            if kind == 'idea': count += keep(candidate('idea:' + r['id'], 'idea', r.get('text', ''), 'project_desk', r.get('text', '')))
            elif kind == 'project': count += keep(candidate('project:' + r['id'], 'project', r.get('title', ''), 'project_desk', (r.get('title') or '') + ' ' + (r.get('original_intent') or '')))
            else:
                if r.get('document_schema') is None and 'blocks' not in r: continue
                words = ' '.join(b.get('text', '') for b in r.get('blocks', []) if isinstance(b, dict))
                count += keep(candidate('document:' + r['id'], 'document', r.get('title', ''), 'documents:' + r['id'], (r.get('title') or '') + ' ' + words))
        searched[name] = count
    for name, op, key in (('investigations', 'investigation.list', 'investigations'), ('assignments', 'agent.list', 'assignments')):
        try: response = kernel.dispatch(op, {}, principal)
        except NotImplementedError as exc: searched['skipped'][name] = 'not available yet: ' + str(exc)[:120]; continue
        except (ValueError, OSError, KeyError, TypeError, RuntimeError) as exc: searched['skipped'][name] = str(exc)[:160]; continue
        if not isinstance(response, dict) or not response.get('ok'):
            searched['skipped'][name] = ((response or {}).get('error') or {}).get('message', 'refused')[:160] if isinstance(response, dict) else 'unavailable'; continue
        found = (response.get('result') or {}).get(key) or []; count = 0; seen = {r['id'] for r in rows}
        for r in found[:PER_SOURCE]:
            if not isinstance(r, dict): continue
            if name == 'investigations':
                ident = 'investigation:' + str(r.get('id', '')); text = r.get('question', '')
                if ident in seen: continue
                kept = keep(candidate(ident, 'investigation', text, 'investigations', text))
            else:
                inv = r.get('investigation'); ident = 'investigation:' + str(inv) if inv else 'assignment:' + str(r.get('id', ''))
                text = r.get('request') or r.get('working_on') or ''
                if ident in seen: continue
                kept = keep(candidate(ident, 'assignment', text, 'investigations', text))
            seen.add(ident); count += kept
        searched[name] = count
    searched['candidates'] = len(rows)
    return rows, searched


def related(kernel, args, principal):
    words = tokens(args['text']); limit = args.get('limit', DEFAULT_LIMIT); exclude = args.get('exclude') or []
    if len(words) < MIN_SHARED:
        return {'related': [], 'basis': BASIS, 'searched': {'candidates': 0, 'words': len(words), 'note': 'fewer than two words to match; nothing was read'}}
    rows, searched = gather(kernel, principal, exclude)
    searched['words'] = len(words); searched['limit'] = limit; searched['minimum_shared'] = MIN_SHARED
    return {'related': rank(words, rows, limit), 'basis': BASIS, 'searched': searched}


def dispatch(kernel, op, args, principal):
    if op == 'ledger.related': return related(kernel, args, principal)
    raise ValueError('Unknown related operation')
