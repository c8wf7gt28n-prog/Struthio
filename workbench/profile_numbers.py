"""Numbers on the page (HATCH AGENT-01): the first end-to-end assignment the resident loop runs without a model.

Owner decision 8: the first task is numbers on the page. Owner decision 6: every step is local computation or one registered
operation; no model is consulted. The profile plans five steps and interprets each actual result:

  read     documents.get                  the page as saved: its revision, its paragraphs
  extract  helpers:quantities_from_text   quantities.extract over every paragraph except the result paragraphs already on the
                                          page (known by the condition cards' result_block ids, never by their words); the
                                          helper's use is recorded; zero quantities -> WAITING with a kind sentence; inputs of
                                          two dimensions -> a QUESTION claim naming both and WAITING (the sum is never attempted)
  sum      math.evaluate                  the exact calculator adds quantities.sum_model's model; the total is read back in the
                                          first quantity's unit
  write    documents.edit                 change {append}: the result paragraph after the last paragraph, bound to the revision
                                          read in the first step (a page that moved on is refused by the store, never merged)
  card     helpers:condition_card         conditions.create binds the total to the exact spans it came from; a FINDING claim says
                                          what the page's numbers total; the assignment is done

The WAITING branches put a fresh read and extract after the current step, so Resume reads the page again instead of
reusing what it found before. Nothing here starts a worker, a model or a native tool.
"""
from __future__ import annotations
import hashlib
from . import agent_profiles as base
from . import conditions, helpers, quantities

HELPER_EXTRACT = 'quantities_from_text'
HELPER_SUM = 'sum_model'
HELPER_CARD = 'condition_card'
NO_NUMBERS = 'I found no numbers to add up on this page. Write them with their units, like 12.5 kg or 3 A, and ask again.'
PAGE_MOVED = 'The page changed while Graphite was working on it; ask again and Graphite reads it afresh.'
PURPOSES = {'read': 'Reading the page', 'extract': 'Finding the numbers with units on the page', 'sum': 'Adding them up with the exact calculator',
            'write': 'Writing the total under the page', 'card': 'Binding the total to the words it came from'}


def page_digest(doc):
    return hashlib.sha256('\n'.join(b['text'] for b in doc['blocks']).encode()).hexdigest()


def finding_words(total):
    n = total['count']
    return 'The %d quantit%s on this page total %s.' % (n, 'y' if n == 1 else 'ies', total['text'])


class NumbersOnPage(base.Profile):
    name = 'numbers_on_page'
    title = 'Numbers on the page'
    words = 'Reads the page, finds the numbers with units, adds them exactly, writes the total under the page and binds it to the words it came from.'
    needs = ('document',)

    # -- planning ---------------------------------------------------------------------------------------------------------
    def plan(self, context, kernel, principal):
        document = context.get('document') if isinstance(context, dict) else None
        if not isinstance(document, str) or len(document) != 32: raise ValueError('This procedure needs the page: open a document and ask again.')
        helpers.ensure_built_in(kernel, principal, (HELPER_EXTRACT, HELPER_SUM, HELPER_CARD))
        return self.steps(document)

    def steps(self, document, keys=('read', 'extract', 'sum', 'write', 'card')):
        operations = {'read': ('documents.get', {'id': document}), 'extract': ('helpers:' + HELPER_EXTRACT, {'document': document}),
                      'sum': ('math.evaluate', {}), 'write': ('documents.edit', {}), 'card': ('helpers:' + HELPER_CARD, {'document': document})}
        return [base.step(key, PURPOSES[key], *operations[key]) for key in keys]

    def again(self, document):
        """A fresh read and extract, inserted after a step that has to wait for the owner."""
        return self.steps(document, ('read', 'extract'))

    def inputs(self, step, state):
        context = state.get('context') or {}
        if step['key'] != 'read' and context.get('document_digest'):
            return {'document:' + str(context.get('document')): context['document_digest']}
        return dict(step.get('inputs') or {})

    # -- arguments as known now ---------------------------------------------------------------------------------------------
    def arguments(self, step, state, kernel, principal):
        context = state.get('context') or {}; key = step['key']
        if key in ('extract', 'card', 'sum', 'write') and context.get('document_revision') is None:
            raise ValueError('Read the page first: no saved revision is known yet.')
        if key == 'read': return dict(step['arguments'])
        if key == 'extract': return {'document': context['document'], 'revision': context['document_revision']}
        if key == 'sum':
            chosen = context.get('quantities') or []
            if not chosen: raise ValueError(NO_NUMBERS)
            return {'model': quantities.sum_model(chosen)}
        if key == 'write':
            if not context.get('result_text'): raise ValueError('Nothing to write yet: the total has not been calculated.')
            return {'id': context['document'], 'expected_revision': context['document_revision'], 'selection': {'block': context.get('last_index', 0), 'start': 0, 'end': 0},
                    'change': {'append': context['result_text']}, 'origin': 'SLATE', 'request': ' '.join(str(state.get('request') or '').split())[:400]}
        if key == 'card':
            if not context.get('result_block'): raise ValueError('Nothing to bind yet: the total has not been written.')
            return {'document': context['document'], 'result_block': context['result_block'], 'inputs': len(context.get('quantities') or [])}
        return dict(step.get('arguments') or {})

    # -- the local steps ----------------------------------------------------------------------------------------------------
    def local(self, step, state, kernel, principal):
        context = state.get('context') or {}; operation = step['operation']
        if operation == 'helpers:' + HELPER_EXTRACT:
            from . import project_desk as records
            doc = records.result_of(kernel, 'documents.get', {'id': context['document']}, principal)['document']
            if context.get('document_revision') is not None and doc['revision'] != context['document_revision']:
                raise ValueError(PAGE_MOVED + ' (revision %s is now %s)' % (context['document_revision'], doc['revision']))
            exclude = conditions.result_blocks(kernel, doc['id'], principal)
            found = conditions.page_quantities(doc['blocks'], exclude=exclude)
            chosen, left_out, note = quantities.choose(found)
            helpers.record_use(kernel, principal, HELPER_EXTRACT, True, '%d quantities on page %s at revision %d; %d chosen' % (len(found), doc['id'][:8], doc['revision'], len(chosen)))
            return {'document': doc['id'], 'revision': doc['revision'], 'found': len(found), 'quantities': chosen, 'left_out': len(left_out), 'note': note,
                    'excluded_result_paragraphs': len(exclude), 'helper': HELPER_EXTRACT}
        if operation == 'helpers:' + HELPER_CARD:
            if 'execute' not in principal.scopes: raise ValueError('A condition card is a write; this assignment may only read.')
            chosen = context.get('quantities') or []; total = context.get('total')
            if not chosen or not total or not context.get('result_block'): raise ValueError('Nothing to bind yet: the total has not been written.')
            try:
                card = conditions.create(kernel, principal, document=context['document'], inputs=[conditions.span(q) for q in chosen], expression='sum',
                                         result={'value': total['value'], 'unit': total['unit'], 'text': total['text']}, method=[HELPER_EXTRACT, HELPER_SUM],
                                         assignment=state.get('id') if isinstance(state.get('id'), str) and len(state['id']) == 32 else None,
                                         result_block=context['result_block'], origin='SLATE', request=str(state.get('request') or ''))
            except ValueError as exc:
                helpers.record_use(kernel, principal, HELPER_CARD, False, str(exc)); raise
            helpers.record_use(kernel, principal, HELPER_CARD, True, 'card %s on page %s: %s' % (card['id'][:8], context['document'][:8], total['text']))
            return {'condition': card['id'], 'state': card['state'], 'document_revision': card['document_revision'], 'inputs': len(card['inputs']), 'helper': HELPER_CARD}
        return super().local(step, state, kernel, principal)

    # -- reading the results ----------------------------------------------------------------------------------------------
    def interpret(self, step, result, state, kernel, principal):
        context = state.get('context') or {}; key = step['key']; document = context.get('document')
        if key == 'read':
            doc = result['document']
            return {'context_updates': {'document_revision': doc['revision'], 'document_title': doc['title'], 'last_index': max(len(doc['blocks']) - 1, 0),
                                        'document_digest': page_digest(doc), 'documents': [doc['id']]}}
        if key == 'extract':
            chosen = result.get('quantities') or []
            updates = {'quantities': chosen, 'found': result.get('found', len(chosen)), 'left_out': result.get('left_out', 0), 'note': result.get('note', '')}
            if not chosen: return {'context_updates': updates, 'waiting': NO_NUMBERS, 'steps': self.again(document)}
            try: quantities.sum_model(chosen)
            except ValueError as exc:
                question = conditions.mismatch_question(exc) if str(exc).startswith('UNITS_DIFFER') else str(exc)
                helpers.record_use(kernel, principal, HELPER_SUM, False, str(exc)[:200])
                return {'context_updates': updates, 'claims': [{'role': 'QUESTION', 'text': question}], 'waiting': question, 'steps': self.again(document)}
            return {'context_updates': updates}
        if key == 'sum':
            chosen = context.get('quantities') or []
            try: total = quantities.total_of(result, chosen)
            except ValueError as exc:
                helpers.record_use(kernel, principal, HELPER_SUM, False, str(exc)[:200])
                words = 'The exact calculator could not add these: %s.' % (result.get('reason') or result.get('state') or str(exc))
                return {'claims': [{'role': 'QUESTION', 'text': words}], 'waiting': words, 'steps': self.again(document)}
            helpers.record_use(kernel, principal, HELPER_SUM, True, '%s from %d quantities' % (total['text'], total['count']))
            return {'context_updates': {'total': total, 'result_text': conditions.result_words(chosen, total, context.get('note') or '')}}
        if key == 'write':
            applied = result.get('applied') or {}
            if not applied.get('appended_block'): return {'waiting': 'The page did not take the result paragraph; ask again.', 'steps': self.again(document)}
            return {'context_updates': {'document_revision': result['document']['revision'], 'result_block': applied['appended_block'], 'result_index': applied.get('appended_index')}}
        if key == 'card':
            total = context.get('total') or {}
            return {'context_updates': {'conditions': list(context.get('conditions') or []) + [result['condition']]},
                    'claims': [{'role': 'FINDING', 'text': finding_words(total)}] if total else [], 'done': True}
        return {}

    def failed(self, step, error, state, kernel, principal):
        """After a failed step the loop replaces what came after it with these steps, so a moved page gets the whole procedure again."""
        context = state.get('context') or {}; document = context.get('document'); words = str(error)
        if (step['key'] == 'write' and 'REVISION_CHANGED' in words) or (step['key'] in ('extract', 'sum') and PAGE_MOVED.split(';')[0] in words):
            return {'waiting': PAGE_MOVED, 'steps': self.steps(document)}
        return {'waiting': words}

    def describe(self, state):
        context = state.get('context') or {}
        if state.get('state') == 'WAITING' and state.get('reason'): return str(state['reason'])
        if self.done(state) and context.get('total'): return 'Finished: ' + finding_words(context['total'])
        current = self.next(state)
        if current is None: return super().describe(state)
        plan = state.get('plan') or []
        return '%s (step %d of %d)' % (current['purpose'], min(state.get('cursor', 0) + 1, len(plan)), len(plan))


PROFILE = NumbersOnPage()
