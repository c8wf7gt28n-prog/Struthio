"""Compile typed staC engineering pipelines without reading source data.

Only registered operations enter the IR. The runtime binds native sources.
"""
from __future__ import annotations
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
import re
import shlex
from typing import Optional

from .. import record_io
from .quantities import Quantity, DimensionError

SCHEMA = 'arc.stac.ir/0.2'
SCHEMA_04 = 'arc.stac.ir/0.4'  # New constructs only; historic v0.2 identities remain unchanged
SCHEMA_05 = 'arc.stac.ir/0.5'  # Trusted claim/witness semantics; old versions retain their digests
SCHEMA_06 = 'arc.stac.ir/0.6'  # Registered Kernel evidence read/verification only
DIGEST_PROFILE = 'arc-record-io-json/1'  # NOT RFC 8785/JCS
REF = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,39}$')
PROPERTY = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,63}$')
JOBID = re.compile(r'^[0-9a-f]{32}$')  # Kernel-issued UUID4-style hex identifier
DOTTED = re.compile(r'^([A-Za-z][A-Za-z0-9_]{0,39})\.([A-Za-z][A-Za-z0-9_]{0,63})$')
MEASURE = re.compile(r'^([+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?)(us|µs|μs|ns|ms|s|Hz|kHz|MHz|V|mV)$')


class CompileError(ValueError):
    pass


@dataclass(frozen=True)
class Stage:
    verb: str
    arguments: tuple[str, ...]


@dataclass(frozen=True)
class Context:
    project: str
    board: str


# Allowed input types, output type, declared effect set, registered Kernel operation.
# Names not registered here are not staC capabilities, even if the Kernel has them.
SIGNATURES = {
    'part': (('Context',), 'PartInspection', ('read',), 'links.inspect'),
    'job': (('Context',), 'KernelJobInspection', ('read',), 'jobs.get'),
    'verify-test': (('KernelJobInspection',), 'KernelTestWitness', ('read',), 'stac.verify-test'),
    'trace': (('Context',), 'ConnectivityTrace', ('read',), 'links.trace'),
    'rom': (('Context',), 'ROMStatus', ('read',), 'records.status'),
    'vendor': (('Context',), 'VendorStatus', ('read',), 'vendor.status'),
    'fact': (('PartInspection',), 'FactInquiry', ('read',), 'stac.fact'),
    'why': (('PartInspection', 'FactInquiry', 'ConnectivityTrace', 'ROMStatus', 'VendorStatus',
             'QualificationAssessment', 'ScenarioAssessment', 'PredicateAssessment', 'KnowledgePacket',
             'EngineeringQuestion', 'ObligationReport', 'ClaimCandidate', 'WitnessCandidate', 'WitnessJudgment', 'PredicateAssessment',
             'KernelJobInspection', 'KernelTestWitness'),
            'ProvenanceReport', ('read',), 'stac.why'),
    'gaps': (('PartInspection', 'FactInquiry', 'ConnectivityTrace', 'ProvenanceReport', 'ROMStatus', 'VendorStatus',
              'QualificationAssessment', 'ScenarioAssessment', 'KnowledgePacket', 'ChallengeReport',
              'EngineeringQuestion', 'ObligationReport', 'ClaimCandidate', 'WitnessCandidate', 'WitnessJudgment', 'PredicateAssessment',
              'KernelJobInspection', 'KernelTestWitness'),
             'GapReport', ('read',), 'stac.gaps'),
    'assess': (('FactInquiry', 'WitnessJudgment'), 'QualificationAssessment', ('read',), 'stac.assess'),
    'suppose': (('FactInquiry',), 'ScenarioAssessment', ('read',), 'stac.suppose'),
    'compare': (('ScenarioAssessment',), 'PredicateAssessment', ('read',), 'stac.compare'),
    'challenge': (('FactInquiry', 'QualificationAssessment', 'ScenarioAssessment'),
                  'ChallengeReport', ('read',), 'stac.challenge'),
    'question': (('FactInquiry',), 'EngineeringQuestion', ('read',), 'stac.question'),
    'obligations': (('FactInquiry', 'QualificationAssessment', 'ScenarioAssessment', 'EngineeringQuestion',
                     'WitnessJudgment'),
                    'ObligationReport', ('read',), 'stac.obligations'),
    'claim': (('FactInquiry',), 'ClaimCandidate', ('read',), 'stac.claim'),
    'witness': (('ClaimCandidate',), 'WitnessCandidate', ('read',), 'stac.witness'),
    'verify': (('WitnessCandidate',), 'WitnessJudgment', ('read',), 'stac.verify'),
    'packet': (('FactInquiry', 'QualificationAssessment', 'ScenarioAssessment', 'PredicateAssessment', 'ChallengeReport',
                'EngineeringQuestion', 'WitnessJudgment'),
               'KnowledgePacket', ('read',), 'stac.packet'),
}


def _check_text(text: str | None) -> None:
    if not isinstance(text, str) or not text.strip() or len(text) > 4096:
        raise CompileError('Expected a line of 1–4096 characters')
    if '\x00' in text or '\n' in text or '\r' in text:
        raise CompileError('One line at a time')


def _lex_tokens(text: str) -> list[str]:
    lexer = shlex.shlex(text, posix=True, punctuation_chars='|;&<>`$()')
    lexer.whitespace_split = True
    lexer.commenters = ''
    return list(lexer)


def tokenize(text: str) -> list[Stage]:
    _check_text(text)
    try:
        toks = _lex_tokens(text)
    except ValueError as exc:
        raise CompileError('Malformed quoting: ' + str(exc)) from exc
    return _stages(toks)


def _stages(toks: Sequence[str]) -> list[Stage]:
    if not toks or len(toks) > 80:
        raise CompileError('Too many tokens or empty program')
    # Angle operators are allowed ONLY inside an explicitly typed compare stage.
    # Other shell punctuation remains unavailable, including >> and <<.
    if any(tok in (';', '&&', '&', '>>', '<<', '<>', '`', '$', '(', ')', '||') for tok in toks):
        raise CompileError('A line here has no shell execution, redirection, variables or grouping')
    parts = [[]]
    for t in toks:
        if t == '|':
            if not parts[-1]:
                raise CompileError('Empty pipeline stage')
            parts.append([])
        else:
            parts[-1].append(t)
    if not parts[-1]:
        raise CompileError('Pipeline cannot end with |')
    stages = [Stage(tokens[0].lower(), tuple(tokens[1:])) for tokens in parts]
    for stage in stages:
        if any(t in ('<', '>') for t in stage.arguments) and stage.verb != 'compare':
            raise CompileError('Angle comparisons are valid only within a compare stage; file redirection is not supported')
    return stages


def _context(token: str) -> Context:
    if '@' not in token:
        raise CompileError('Context must be PROJECT@REVISION; e.g. ARC1@R10')
    project, board = token.split('@', 1)
    if project.upper() in ('ARC1', 'ARC-1') and board.upper() == 'R10':
        return Context('ARC-1', 'R10')
    if project.upper() == 'LEDGER' and board.upper() == 'CURRENT':
        return Context('Ledger', 'CURRENT')
    raise CompileError('Contexts: ARC1@R10 for hardware; LEDGER@CURRENT for recorded Kernel jobs')


def _identifier(value: str, pattern, kind: str):
    if not pattern.fullmatch(value):
        raise CompileError('Invalid ' + kind + ': ' + repr(value))
    return value


def _measure(value: str) -> dict:
    match = MEASURE.fullmatch(value)
    if not match:
        raise CompileError('Usage: suppose 2.5us (exact decimal and supported unit; no floats)')
    number, unit = match.groups()
    unit = {'µs': 'us', 'μs': 'us'}.get(unit, unit)
    try:
        q = Quantity(Decimal(number), unit)
    except (DimensionError, ValueError) as exc:
        raise CompileError('Invalid exact quantity') from exc
    if q.dimension != 'time':
        raise CompileError('suppose currently requires a duration, such as 2.5us')
    value_si = q.as_base()
    if value_si < 0 or value_si > Decimal('86400'):
        raise CompileError('Hypothetical duration must be between 0 and 86400 seconds')
    # Equivalent spellings 2.500us and 0.0025ms produce identical IR arguments.
    return {'value_si': format(value_si.normalize(), 'f'), 'unit': 's', 'dimension': 'time'}


def lower_surface(stages: list[Stage]) -> list[Stage]:
    """Expand a tiny expert shorthand into EXISTING typed operations.

    The compiled IR of `spec U45.tCEM` is byte-identical to the expanded
    vendor witness pipeline; no AI or source access is used in this step.
    There is deliberately no arbitrary macro language or generic eval.
    """
    expanded: list[Stage] = []
    for stage in stages:
        if stage.verb in ('spec', 'assess', 'why', 'gaps') and stage.arguments:
            if len(stage.arguments) != 1:
                raise CompileError('Use: ' + stage.verb + ' U45.tCEM')
            match = DOTTED.fullmatch(stage.arguments[0])
            if not match:
                raise CompileError('Expected exact dotted engineering property: U45.tCEM')
            component, prop = match.groups()
            expanded.extend((Stage('part', (component,)), Stage('fact', (prop,))))
            if stage.verb == 'spec':
                expanded.extend((Stage('claim', ()), Stage('witness', ()), Stage('verify', ())))
            elif stage.verb == 'assess':
                expanded.extend((Stage('claim', ()), Stage('witness', ()), Stage('verify', ()), Stage('assess', ())))
            else:
                expanded.extend((Stage('claim', ()), Stage('witness', ()), Stage('verify', ()), Stage(stage.verb, ())))
        elif stage.verb == 'result':
            if len(stage.arguments) != 1 or not JOBID.fullmatch(stage.arguments[0]):
                raise CompileError('Use: result 32_character_lowercase_kernel_job_id')
            expanded.extend((Stage('job', stage.arguments), Stage('verify-test', ())))
        else:
            expanded.append(stage)
    if len(expanded) > 20:
        raise CompileError('The line, written out, has more than 20 stages')
    return expanded


def compile_text(text: str, initial_context: Optional[Context] = None) -> dict:
    """Compile symbolic, read-only IR without dispatching any operation."""
    return _compile_stages(tokenize(text), initial_context)


def _compile_tokenized(text: str | None, tokens: Sequence[str], initial_context: Context | None) -> dict:
    # Preserve the character bound on the canonical program after stripping redirects.
    _check_text(text)
    return _compile_stages(_stages(tokens), initial_context)


def _compile_stages(stages: list[Stage], initial_context: Context | None) -> dict:
    pipeline = lower_surface(stages)
    context = initial_context
    if context is not None and context not in (Context('ARC-1', 'R10'), Context('Ledger', 'CURRENT')):
        raise CompileError('Unsupported inherited source context')
    typ = 'Context'
    nodes = []
    first = True
    for stage in pipeline:
        verb, args = stage.verb, stage.arguments
        if verb == 'use':
            if not first or len(args) != 1:
                raise CompileError('use PROJECT@REVISION must be the first context selector')
            context = _context(args[0]); typ = 'Context'
            nodes.append({'op': 'context.select', 'arguments': {'project': context.project, 'board': context.board},
                          'input_type': 'Context', 'output_type': 'Context', 'effects': []})
            first = False
            continue
        if context is None:
            raise CompileError('Select a context: use ARC1@R10 | part U45')
        if verb not in SIGNATURES:
            raise CompileError('Unknown or unavailable operation: ' + verb)
        if (context.project == 'Ledger' and verb not in ('job', 'verify-test', 'why', 'gaps')) or (context.project != 'Ledger' and verb in ('job', 'verify-test')):
            raise CompileError('This operation is unavailable for the selected context')
        allowed, outtype, effects, op = SIGNATURES[verb]
        if typ not in allowed:
            raise CompileError(verb + ' requires ' + '/'.join(allowed) + ', got ' + typ)
        if verb == 'part':
            if len(args) != 1:raise CompileError('Usage: part REFDES')
            params = {'component': _identifier(args[0], REF, 'component')}
        elif verb == 'job':
            if len(args) != 1 or not JOBID.fullmatch(args[0]):
                raise CompileError('Usage: job KERNEL_JOB_ID (32 lowercase hexadecimal characters)')
            params = {'id': args[0]}
        elif verb == 'trace':
            if len(args) != 2:raise CompileError('Usage: trace START END (components)')
            params = {'start': _identifier(args[0], REF, 'trace start'),
                      'end': _identifier(args[1], REF, 'trace end')}
        elif verb in ('rom', 'vendor'):
            if args != ('status',):raise CompileError('Usage: ' + verb + ' status')
            params = {}
        elif verb == 'fact':
            if len(args) != 1:raise CompileError('Usage: part REF | fact PROPERTY')
            params = {'property': _identifier(args[0], PROPERTY, 'property')}
        elif verb == 'suppose':
            if len(args) != 1:raise CompileError('Usage: part REF | fact PROPERTY | suppose 2.5us')
            params = _measure(args[0])
        elif verb == 'compare':
            # shlex tokenizes <= and >= as '<', '=', or '>', '='.
            if len(args) == 3 and args[:2] in (('<', '='), ('>', '=')):
                relation, measure = ''.join(args[:2]), args[2]
            elif len(args) == 2:
                relation, measure = args
            else:
                raise CompileError('Usage: suppose DURATION | compare <|<=|>|>=|==|!= DURATION')
            relation = {'≤': '<=', '≥': '>='}.get(relation, relation)
            if relation not in ('<', '<=', '>', '>=', '==', '!='):
                raise CompileError('Expected one of < <= > >= == != for typed comparison')
            params = {'relation': relation, **_measure(measure)}
        else:
            if args:raise CompileError('Usage: ' + verb + ' (no arguments)')
            params = {}
        nodes.append({'op': op, 'arguments': params,
                      'input_type': typ, 'output_type': outtype, 'effects': list(effects)})
        typ = outtype
        first = False
    witness_extension = any(node['op'] in ('stac.claim', 'stac.witness', 'stac.verify', 'stac.compare') for node in nodes)
    question_extension = any(node['op'] in ('stac.question', 'stac.obligations') for node in nodes)
    kernel_extension = any(node['op'] in ('jobs.get', 'stac.verify-test') for node in nodes)
    version = 6 if kernel_extension else (5 if witness_extension else (4 if question_extension else 2))
    schema = {2: SCHEMA, 4: SCHEMA_04, 5: SCHEMA_05, 6: SCHEMA_06}[version]
    ir = {'schema': schema,
          'version': version, 'digest_profile': DIGEST_PROFILE,
          'context': {'project': context.project, 'board': context.board} if context else None,
          'binding': {'state': 'SYMBOLIC_UNPINNED', 'source_generation': None},
          'nodes': nodes, 'result_type': typ,
          'effects': sorted(set(effect for node in nodes for effect in node['effects']))}
    if any(eff != 'read' for eff in ir['effects']):
        raise CompileError('A line here only reads')
    return ir


def intent_hash(ir: dict) -> str:
    """Local ARC digest profile; does NOT assert semantic equivalence or use RFC8785."""
    return record_io.digest(ir)
