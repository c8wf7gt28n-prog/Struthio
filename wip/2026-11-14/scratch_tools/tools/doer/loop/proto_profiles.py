"""PROTOTYPES, kept outside the tree: two new kinds of job for the existing agent loop, registered at run time in a throwaway
process to prove the seam. Every step is one registered operation (or a staC line through language.run); the program
enumerates the steps from the records; reads run; what changes something is refused by the Kernel for a read-only budget
and the assignment waits with the words in Needs you; Resume then verifies by reading again.

  finding_again   "check the finding about … again"   investigation.list -> investigation.sheet -> investigation.path (staC)
                                                       -> CHOICE(refresh sources | run checks) -> ... -> verdict
  total_current   "bring the total on this page up to date"  conditions.list -> conditions.recheck (a write) -> conditions.get
"""
import json, re
from workbench import agent_profiles as base

WORDS = re.compile(r'[^\W_]+')
STOP = {'the', 'a', 'an', 'again', 'check', 'recheck', 'verify', 'finding', 'about', 'this', 'that', 'is', 'it', 'still', 'holds', 'and', 'tell', 'me', 'if', 'of', 'to'}


def words_of(text): return {w for w in WORDS.findall(str(text or '').casefold()) if w not in STOP and len(w) > 1}


class FindingAgain(base.Profile):
    name = 'finding_again'
    title = 'Check a finding again'
    words = 'Finds the finding in the records, reads what it stands on, reads its sources again or runs its checks again, and says whether it still holds.'
    needs = ()

    def fits(self, words): return bool(re.search(r'\b(check|recheck|verify|confirm)\b.*\bfinding\b', words))

    def plan(self, context, kernel, principal):
        return [base.step('list', 'Looking through the investigations for the finding', 'investigation.list', {})]

    def arguments(self, step, state, kernel, principal):
        c = state.get('context') or {}; key = step['key']
        if key == 'sheet': return {'id': c['target']}
        if key == 'path': return {'text': 'investigation.path %s | pick path | select kind,address,direction,source_state,outcome,counts' % json.dumps({'claim': c['claim']}, separators=(',', ':'))}
        if key in ('refresh', 'checks'): return {'id': c['target']}
        if key == 'verdict': return {'claim': c['claim']}
        if key == 'review': return {'claim': c['claim'], 'decision': 'ACCEPT_CHANGE'}
        return dict(step.get('arguments') or {})

    def options(self, c):
        done = set(c.get('did') or [])
        rows = [{'key': 'refresh', 'purpose': 'Read its sources again and compare them with what was read before',
                 'step': base.step('refresh', 'Reading its sources again', 'investigation.refresh', {}), 'acceptable': 'refresh' not in done},
                {'key': 'checks', 'purpose': 'Run its checks again on the records as they are now',
                 'step': base.step('checks', 'Running its checks again', 'investigation.continue', {}), 'acceptable': 'checks' not in done},
                {'key': 'verdict', 'purpose': 'Say how the finding stands now',
                 'step': base.step('verdict', 'Reading how the finding stands now', 'investigation.path', {}), 'acceptable': bool(done)}]
        return rows

    def interpret(self, step, result, state, kernel, principal):
        c = state.get('context') or {}; key = step['key']
        if key == 'list':
            rows = [r for r in (result.get('investigations') or []) if r.get('id') != state.get('investigation')]
            if not rows: return {'waiting': 'There is no investigation with findings in this workspace yet.'}
            return {'context_updates': {'candidates': [r['id'] for r in rows[:8]], 'target': rows[0]['id']},
                    'steps': [base.step('sheet', 'Reading the findings of “%s”' % str(rows[0].get('question'))[:80], 'investigation.sheet', {})]}
        if key == 'sheet':
            want = words_of(state.get('request')); best = None
            for claim in (result.get('learned') or []) + (result.get('unresolved') or []):
                if claim.get('role') != 'FINDING': continue
                score = len(want & words_of(claim.get('text')))
                if best is None or score > best[0]: best = (score, claim)
            if best is None or best[0] == 0:
                return {'waiting': 'I could not tell which finding you mean. Name some of its words.',
                        'claims': [{'role': 'QUESTION', 'text': 'Which finding should be checked again?'}]}
            claim = best[1]
            return {'context_updates': {'claim': claim['id'], 'claim_text': claim['text'], 'was': claim.get('evidence_state'), 'did': []},
                    'steps': [base.step('path', 'Reading what “%s” stands on (a staC line)' % claim['text'][:60], 'language.run', {})]}
        if key == 'path':
            rows = result.get('rows') or []
            return {'context_updates': {'stands_on': rows[:12]}, 'options': self.options(c),
                    'situation': 'checking the finding “%s” again; it stands on %d records' % (str(c.get('claim_text'))[:80], len(rows))}
        if key == 'refresh':
            did = list(c.get('did') or []) + ['refresh']; changed = result.get('changed') or []
            out = {'context_updates': {'did': did, 'changed': changed}}
            if changed:
                out['claims'] = [{'role': 'QUESTION', 'text': 'A source of “%s” changed since it was read: %s' % (c.get('claim_text'), ', '.join(changed))}]
                out['steps'] = [base.step('review', 'Accepting the changed source as the new snapshot (your decision)', 'investigation.review', {})]
                return out
            out['options'] = self.options({**c, 'did': did}); out['situation'] = 'the sources of “%s” are unchanged' % str(c.get('claim_text'))[:80]
            return out
        if key == 'checks':
            did = list(c.get('did') or []) + ['checks']; ran = result.get('ran') or []
            return {'context_updates': {'did': did, 'ran': ran}, 'options': self.options({**c, 'did': did}),
                    'situation': '%d check%s ran for “%s”' % (len(ran), '' if len(ran) == 1 else 's', str(c.get('claim_text'))[:80])}
        if key == 'verdict':
            state_now = result.get('evidence_state'); counted = [l for l in result.get('path') or [] if l.get('counts')]
            text = '“%s” %s: %s on %d current record%s (it was %s); sources read again: %s; checks run again: %s.' % (
                c.get('claim_text'), 'still holds' if state_now == 'SUPPORTED' else 'needs you', state_now, len(counted), '' if len(counted) == 1 else 's', c.get('was'),
                'yes, none changed' if 'refresh' in (c.get('did') or []) and not c.get('changed') else 'no' if 'refresh' not in (c.get('did') or []) else 'changed: ' + ', '.join(c.get('changed') or []),
                ('%d ran' % len(c.get('ran') or [])) if 'checks' in (c.get('did') or []) else 'no')
            return {'claims': [{'role': 'FINDING', 'text': text}], 'done': True, 'reason': 'Checked again: ' + text[:300]}
        return {}

    def failed(self, step, error, state, kernel, principal):
        if step['key'] == 'review':
            return {'waiting': 'A source changed. Accepting it is yours to decide (Investigation, the finding, Accept change); then Resume and I read the finding again.',
                    'steps': [base.step('verdict', 'Reading how the finding stands now', 'investigation.path', {})]}
        return {'waiting': 'Step %s did not run: %s' % (step['key'], error)}

    def done(self, state): return False


class TotalCurrent(base.Profile):
    name = 'total_current'
    title = 'Bring a page total up to date'
    words = 'Reads the totals bound to this page, says which are stale, proposes the recheck (a change to the page, which waits for you unless you allowed it) and reads the card again.'
    needs = ('document',)

    def fits(self, words): return bool(re.search(r'\b(bring|update|refresh)\b.*\b(total|result)s?\b.*\b(up\s+to\s+date|current)\b', words))

    def plan(self, context, kernel, principal):
        return [base.step('cards', 'Reading the totals bound to this page', 'conditions.list', {'document': context['document']})]

    def interpret(self, step, result, state, kernel, principal):
        c = state.get('context') or {}; key = step['key']
        if key == 'cards':
            cards = result.get('conditions') or []; stale = [x for x in cards if x.get('state') == 'STALE']
            claims = [{'role': 'FINDING', 'text': 'Total %s is %s%s' % ((x.get('result') or {}).get('text'), x.get('state'), (': ' + x['reason']) if x.get('reason') else '')} for x in cards]
            if not stale: return {'claims': claims, 'done': True, 'reason': 'Every total on this page is current (%d card%s)' % (len(cards), '' if len(cards) == 1 else 's')}
            steps = []
            for x in stale[:4]:
                steps += [base.step('recheck_' + x['id'][:6], 'Recalculating the total from the page as it reads now (changes the page)', 'conditions.recheck', {'id': x['id']}, card=x['id']),
                          base.step('verify_' + x['id'][:6], 'Reading the card again', 'conditions.get', {'id': x['id']}, card=x['id'])]
            return {'claims': claims, 'context_updates': {'conditions': [x['id'] for x in cards]}, 'steps': steps}
        if key.startswith('verify_'):
            card = result.get('condition') or {}
            claim = {'role': 'FINDING' if card.get('state') == 'CURRENT' else 'QUESTION', 'text': 'After the recheck the total reads %s and its card is %s' % ((card.get('result') or {}).get('text'), card.get('state'))}
            last = self.next(state) is None
            return {'claims': [claim], **({'done': True, 'reason': claim['text']} if last else {})}
        return {}

    def failed(self, step, error, state, kernel, principal):
        plan = state.get('plan') or []; cursor = state.get('cursor', 0)
        if step['key'].startswith('recheck_'):
            return {'waiting': 'A total on this page is stale. Recalculating it changes the page, so it waits for you: use the recheck word, then Resume and I read the card again. (%s)' % error,
                    'steps': [dict(s) for s in plan[cursor + 1:]]}
        return {'waiting': 'Step %s did not run: %s' % (step['key'], error)}

    def done(self, state): return False


def install():
    for profile in (FindingAgain(), TotalCurrent()): base.register(profile)
    return [p for p in ('finding_again', 'total_current') if p in base.PROFILES]
