"""Profiles for the resident agent loop (HATCH AGENT-01): explicit Python that plans, interprets and describes one kind of assignment.

A profile is not a model prompt. It plans a short sequence of registered operations for a request, turns each actual result
into claims on the assignment's investigation, and says in words what Slate is doing now. Where several next steps are
reasonable it offers at most four options; agent_loop.choose_next picks one (the local model when one is READY, the
first option otherwise). Owner decision 6: most steps are local computation; the model only picks among options.

INTERFACE (profile_numbers.py and later profiles build on this; the loop in agent_loop.py calls exactly these):

  class Profile:
      name  = 'numbers_on_page'        registry key, also the value agent.assign takes as 'profile'
      title = 'Numbers on the page'    short words for the right column
      words = 'Reads the page, ...'    one sentence: what the profile does; it becomes the investigation's objective
      needs = ('document',)            context keys the profile cannot start without (checked by agent.assign)

      plan(context, kernel, principal) -> [step, ...]
          The first steps, as dicts built with step(key, purpose, operation, arguments=None, inputs=None):
            key        a short stable name for the step ('read', 'extract', 'sum', 'write', 'card')
            purpose    the words shown as doing_now and recorded in inv_steps.purpose
            operation  a registered operation name ('documents.get', 'math.evaluate', 'documents.edit', ...) that the loop
                       dispatches through kernel.dispatch with a principal bounded to the budget's effects, or
                       'helpers:<name>' for a local computation the profile performs itself in local(); the loop never
                       runs anything else and never starts a worker, a model or a native tool.
            arguments  the operation's arguments as known at plan time (may be {} and completed later in arguments()).
            inputs     optional {label: digest} of what the step reads, recorded as the step's input snapshot.
          Raise ValueError with plain words when the request cannot be planned (the assignment then WAITs with them).

      arguments(step, state, kernel, principal) -> dict
          The arguments to dispatch now; the default returns step['arguments']. Override when a step depends on an
          earlier result (documents.edit needs the revision and the last block read in the first step). Raise
          ValueError with words when they cannot be built; the step is recorded FAILED and the assignment WAITs.

      local(step, state, kernel, principal) -> result (a JSON-serialisable dict)
          Performs a 'helpers:<name>' step. Pure or read-only computation over state['context'] (quantities.extract over the
          page's paragraphs, for instance). The profile itself calls helpers.record_use for the helper it used. Raise
          ValueError with words on failure. The result is recorded like any other step's result.

      interpret(step, result, state, kernel, principal) -> dict with any of
            claims          [{'role': 'FINDING' | 'QUESTION' | 'CANDIDATE', 'text': words}] written to the investigation
            context_updates {key: value} merged into state['context'] (document ids, revisions, the extracted quantities,
                            'conditions': [ids] and 'documents': [ids] feed the status row's inspect list)
            done            True when the assignment is finished (the loop settles the investigation and reports DONE)
            reason          optional words for the DONE state ('Finished: …' when absent)
            waiting         words when the owner is needed (the assignment moves to WAITING with them; the cursor has
                            already advanced past this step, so put the steps to run after the owner answers in 'steps')
            options         [{'key', 'purpose', 'step': step dict, 'acceptable': bool}] (at most four) when a choice exists.
                            'acceptable' (default True) is the profile's own judgement for the current state; the default
                            is the first acceptable option. The loop asks the local model only when more than one option is
                            acceptable and a model is READY, takes the model's pick only when that option is acceptable, and
                            otherwise takes the default and records why. The chosen step is inserted after this one.
            situation       optional words for the model's prompt in place of the request (what is on the page, in short)
            steps           [step, ...] inserted right after this step (incremental planning)
          Called only for a step whose dispatch succeeded; the loop has already recorded the step in inv_steps, and
          state['cursor'] already points past this step (so done(state) with the default rule is true after the last one).

      failed(step, error, state, kernel, principal) -> dict with any of claims, waiting (default: the error words), steps
          Called when a dispatch was refused or failed; the step is already recorded FAILED. The cursor stays on the
          failed step, so agent.resume runs it again unless 'steps' replaces what comes next.

      done(state) -> bool        default: the cursor is past the end of the plan
      describe(state) -> words   doing_now for the right column; default: the purpose of the step at the cursor

  state (a plain dict the loop passes to every call; profiles read it and never write it directly):
      id, investigation, profile, request, state, reason, cursor, budget {max_steps, max_seconds, effects},
      context {...}  the context given at assign time plus every context_updates merged since,
      plan [step, ...] with, on each step that ran, outcome ('DONE' | 'FAILED'), summary, step_id (inv_steps.id), seconds.

  Registration: PROFILES maps name -> instance. profile_numbers (WI-B) defines PROFILE = NumbersOnPage() and this module
  registers it when the import succeeds; UNAVAILABLE says why a known profile is missing in this build. AGENT-02 (WI-C):
  profile_files defines PROFILE = FilesAbout() ('files_about', needs nothing) and is registered the same way; a profile may
  also define fits(words) -> bool (explicit words, never a model), which agent_loop.request_profile consults.
  HATCH DESK D5: profile_network defines PROFILE = NetworkTalk() ('network_talk', needs nothing; "What is talking to the
  network?"), registered the same way after files_about, so a request about files keeps going to files_about.
"""
from __future__ import annotations
import json


def step(key, purpose, operation, arguments=None, inputs=None, **more):
    """One planned step. Plain data: the loop stores it in the assignment's plan JSON."""
    if not isinstance(key, str) or not key: raise ValueError('STEP_KEY_REQUIRED')
    if not isinstance(operation, str) or not operation: raise ValueError('STEP_OPERATION_REQUIRED: ' + key)
    if arguments is not None and not isinstance(arguments, dict): raise ValueError('STEP_ARGUMENTS_ARE_AN_OBJECT: ' + key)
    row = {'key': key, 'purpose': str(purpose or key)[:300], 'operation': operation, 'arguments': dict(arguments or {})}
    if inputs: row['inputs'] = dict(inputs)
    row.update(more)
    json.dumps(row, default=str)  # must be storable
    return row


class Profile:
    name = 'profile'
    title = 'A profile'
    words = 'Plans a short sequence of operations for a request and reads their results.'
    needs = ()

    def plan(self, context, kernel, principal):
        return []

    def next(self, state):
        plan = state.get('plan') or []; cursor = state.get('cursor', 0)
        return plan[cursor] if 0 <= cursor < len(plan) else None

    def arguments(self, step, state, kernel, principal):
        return dict(step.get('arguments') or {})

    def inputs(self, step, state):
        return dict(step.get('inputs') or {})

    def local(self, step, state, kernel, principal):
        raise ValueError('NO_LOCAL_STEP: this profile has no local computation named ' + str(step.get('operation')))

    def interpret(self, step, result, state, kernel, principal):
        return {}

    def failed(self, step, error, state, kernel, principal):
        return {}

    def done(self, state):
        return state.get('cursor', 0) >= len(state.get('plan') or [])

    def describe(self, state):
        current = self.next(state)
        if current is not None: return current['purpose']
        ran = [s for s in (state.get('plan') or []) if s.get('outcome')]
        return 'Finished: ' + ran[-1]['purpose'] if ran else 'Nothing planned yet'


class OperationSequence(Profile):
    """An explicit list of operations from the context (tests and scripted work): runs them in order, claims nothing but a
    QUESTION when one fails, and is done when the list is finished."""
    name = 'operation_sequence'
    title = 'A given sequence of operations'
    words = 'Runs the operations listed in the request context, one bounded step each, and records every result.'
    needs = ('steps',)

    def plan(self, context, kernel, principal):
        rows = context.get('steps')
        if not isinstance(rows, list) or not rows: raise ValueError('The operation sequence needs context.steps: a list of {operation, arguments, purpose}')
        out = []
        for n, row in enumerate(rows, 1):
            if not isinstance(row, dict) or not isinstance(row.get('operation'), str): raise ValueError('Step %d of the sequence has no operation name' % n)
            out.append(step(row.get('key') or 'step%d' % n, row.get('purpose') or ('Run ' + row['operation']), row['operation'], row.get('arguments') or {},
                            row.get('inputs')))
        return out

    def interpret(self, step, result, state, kernel, principal):
        return {}  # done when the list is finished: the base rule (the cursor is past the plan) decides

    def failed(self, step, error, state, kernel, principal):
        return {'claims': [{'role': 'QUESTION', 'text': 'Step %s (%s) did not run: %s' % (step['key'], step['purpose'], error)}]}


PROFILES = {}
UNAVAILABLE = {}


def register(profile):
    if not isinstance(profile, Profile): raise ValueError('PROFILE_IS_NOT_A_PROFILE')
    PROFILES[profile.name] = profile
    UNAVAILABLE.pop(profile.name, None)
    return profile


register(OperationSequence())

try:
    from . import profile_numbers  # WI-B: numbers on the page
except ImportError as exc:
    UNAVAILABLE['numbers_on_page'] = 'profile_numbers is not in this build: ' + str(exc)
else:
    candidate = getattr(profile_numbers, 'PROFILE', None)
    if isinstance(candidate, Profile): register(candidate)
    else: UNAVAILABLE['numbers_on_page'] = 'profile_numbers defines no PROFILE instance'

try:
    from . import profile_files  # AGENT-02 WI-C: files about something (chosen by its own fits(words); needs no page)
except ImportError as exc:
    UNAVAILABLE['files_about'] = 'profile_files is not in this build: ' + str(exc)
else:
    candidate = getattr(profile_files, 'PROFILE', None)
    if isinstance(candidate, Profile): register(candidate)
    else: UNAVAILABLE['files_about'] = 'profile_files defines no PROFILE instance'

try:
    from . import profile_network  # HATCH DESK D5: what is talking to the network (chosen by its own fits(words); needs nothing)
except ImportError as exc:
    UNAVAILABLE['network_talk'] = 'profile_network is not in this build: ' + str(exc)
else:
    candidate = getattr(profile_network, 'PROFILE', None)
    if isinstance(candidate, Profile): register(candidate)
    else: UNAVAILABLE['network_talk'] = 'profile_network defines no PROFILE instance'
