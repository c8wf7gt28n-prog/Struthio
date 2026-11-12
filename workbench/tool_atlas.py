"""Versioned Tool Atlas projections over the existing Kernel contracts.

Passports are owner-private observations, never executable adapters or grants.
No probe is launched and no capability is promoted by this module.
"""
from __future__ import annotations
import copy
import hashlib
import json
import platform
from pathlib import Path
import shlex
import shutil
from . import capability_catalog as catalog, project_desk as desk

NAME = {'type': 'string', 'minLength': 1, 'maxLength': 160}
KIND = {'type': 'string', 'enum': ['OPERATION', 'JOB_TOOL']}
SELECT = {'name': NAME, 'kind': KIND}
PAGE = {'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100},
        'offset': {'type': 'integer', 'minimum': 0}}
FIELDS = {
    'atlas.lookup': ({'query': catalog.TEXT, 'kind': KIND, **PAGE}, []),
    'atlas.operation_schema': (SELECT, ['name']),
    'atlas.invocation': ({'operation': NAME, 'arguments': {'type': 'object'}}, ['operation', 'arguments']),
    'atlas.passport.save': (SELECT, ['name']),
    'atlas.passport.get': ({'id': desk.ID}, ['id']),
    'atlas.passports.list': (PAGE, []),
}
SCOPES = {op: 'execute' if op == 'atlas.passport.save' else 'read' for op in FIELDS}
PROFILE = 'ledger.tool-atlas/1'
NOTICE = 'Discovery only. Dispatch rechecks arguments, ownership, grants and runtime. No qualification is inferred.'
# Search vocabulary only; IDs, scopes and schemas always come from the registry.
WORDS = {'discovery': 'inquiry question assumptions hypotheses sources observations revisions','algo': 'algorithm theory method assumptions applicability','office': 'LibreOffice Calc Writer spreadsheet document',
         'math': 'mathematics quantities units Calc symbolic schedule',
         'lab': 'protected Python WASI experiment board',
         'cad': 'KiCad PCB circuit design rules', 'kibot': 'KiCad BOM fabrication',
         'spice': 'ngspice circuit simulation', 'brain': 'local model GGUF inference',
         'yosys': 'RTL synthesis', 'nextpnr': 'FPGA place route',
         'trellis': 'FPGA bitstream pack', 'icarus': 'Verilog simulation',
         'verilator': 'Verilog simulation', 'surfer': 'waveform viewer'}


def host():
    """A passive session binding, not a hardware qualification or unique host ID."""
    try:
        session = hashlib.sha256(Path('/proc/sys/kernel/random/boot_id').read_bytes()).hexdigest()
    except OSError:
        session = None
    return {'system': platform.system(), 'release': platform.release(),
            'machine': platform.machine(), 'session_digest': session,
            'basis': 'PASSIVE_PLATFORM_AND_BOOT_SESSION_NOT_HARDWARE_ACCEPTANCE' if session
                else 'PLATFORM_ONLY_HOST_NOT_IDENTIFIED'}


def entries(kernel, principal):
    from .engineering_kernel import TOOLS
    view = catalog.catalogue(kernel, principal)
    result = []
    for kind, key, rows in (('OPERATION', 'operation', view['operations']), ('JOB_TOOL', 'tool', view['tools'])):
        for row in rows:
            name = row[key]
            binding = {'profile': PROFILE, 'kind': kind, 'name': name,
                       'source': row['source']}
            if kind == 'OPERATION':
                binding.update(scope=row['scope'], arguments=row['arguments'], handler=row['handler'])
            else:
                binding.update(scope='execute', route='jobs.submit', target=list(TOOLS[name]), native=row['native'])
            result.append({'kind': kind, 'name': name, 'legacy_id': name,
                'search_words': WORDS.get(name.split('.')[0], ''),
                'contract': binding, 'contract_digest': desk.digest(binding),
                'assessment': row['assessment'], 'summary': row['summary'],
                'qualification': 'UNTESTED', 'qualification_basis': 'NO_HOST_BOUND_PROBE_ADAPTER',
                'execution_authority': 'EXISTING_ENGINEERING_KERNEL',
                'effect_detail': 'REQUIRED_KERNEL_SCOPE_ONLY_NOT_A_COMPLETE_FILE_OR_PROCESS_EFFECT_MODEL'})
    return result


def lookup(kernel, principal, query='', kind=None, limit=40, offset=0):
    terms = query.casefold().split()
    rows = [r for r in entries(kernel, principal) if (kind is None or r['kind'] == kind)
            and all(t in (r['name'] + ' ' + r['search_words'] + ' ' + r['contract']['scope']).casefold() for t in terms)]
    return {'schema': PROFILE, 'entries': rows[offset:offset + limit], 'matches': len(rows),
            'offset': offset, 'has_more': offset + limit < len(rows), 'notice': NOTICE,
            'model_calls': 0, 'native_invocations': 0, 'network_calls': 0}


def selected(kernel, principal, name, kind='OPERATION'):
    row = next((r for r in entries(kernel, principal) if r['kind'] == kind and r['name'] == name), None)
    if row is None: raise ValueError('ATLAS_ENTRY_NOT_REGISTERED')
    row = copy.deepcopy(row)
    runtime = row['contract'].get('native', {})
    command = runtime.get('command')
    # Only a selected passport reads native bytes. No --version/help execution.
    identity = {'state': 'NOT_ASSESSED', 'command': command}
    if command:
        path = shutil.which(command)
        identity = {'state': 'MISSING', 'command': command, 'path': path}
        if path:
            resolved = Path(path).resolve()
            try:
                if not resolved.is_file() or resolved.stat().st_size > 128 * 1024 * 1024:
                    identity['state'] = 'UNASSESSED_FILE_TYPE_OR_SIZE'
                else:
                    identity.update(state='FILE_HASHED_NOT_EXECUTED', resolved=str(resolved),
                                    sha256=hashlib.sha256(resolved.read_bytes()).hexdigest())
            except OSError:
                identity['state'] = 'UNREADABLE'
    row['binding'] = {'contract_digest': row['contract_digest'], 'native_file': identity, 'host': host()}
    row['binding_digest'] = desk.digest(row['binding'])
    row['passport'] = {'licence': runtime.get('licence', 'PROJECT_AND_DEPENDENCY_LICENCES_UNASSESSED'),
        'version': runtime.get('version'), 'documentation': ['docs/HATCH_TOOL_ATLAS.md'],
        'source': row['contract']['source'], 'probes': [],
        'limits': ['No operation-specific runtime qualification adapter in this pass.',
                   'Source/contract/native-file/session binding covers direct dependencies only.',
                   'A binary may be a launcher; hashing it does not identify every library or package.',
                   'Declared scopes do not fully describe effects or authorize execution.']}
    return row


def invocation(operation, arguments, principal):
    from .engineering_kernel import CAPABILITIES
    from .engineering_cli import schemas
    from .agent_operations import validate
    if operation not in CAPABILITIES: raise ValueError('ATLAS_ENTRY_NOT_REGISTERED')
    spec = schemas()[operation]
    if set(arguments) - set(spec['properties']) or set(spec['required']) - set(arguments):
        raise ValueError('ATLAS_ARGUMENTS_MISSING_OR_UNKNOWN')
    validate(arguments, spec)
    # Shape checking is deliberately separate from all runtime checks.
    return {'schema': 'ledger.atlas-invocation/1', 'operation': operation,
            'arguments': copy.deepcopy(arguments), 'contract_digest': desk.digest(spec),
            'required_scope': CAPABILITIES[operation],
            'scope_eligible': CAPABILITIES[operation] in principal.scopes
                and not (principal.mode == 'Tutor' and CAPABILITIES[operation] != 'read'),
            'state': 'SCHEMA_CHECKED_NOT_DISPATCHED', 'runtime_authorization': False,
            'notice': NOTICE}


def compile_read(program):
    tokens = shlex.split(program)
    if tokens == ['atlas']:
        operation, arguments = 'atlas.lookup', {}
    elif len(tokens) == 4 and tokens[:2] == ['atlas', '|'] and tokens[2] in ('find', 'operation', 'tool'):
        command, text = tokens[2:]
        operation = 'atlas.lookup' if command == 'find' else 'atlas.operation_schema'
        arguments = {'query': text} if command == 'find' else {'name': text, 'kind': 'JOB_TOOL' if command == 'tool' else 'OPERATION'}
    else:
        raise ValueError('STAC_ATLAS_READ_SYNTAX')
    from .engineering_cli import schemas
    from .agent_operations import validate
    validate(arguments, schemas()[operation])
    body = {'schema': 'ledger.stac-atlas-ir/1', 'operation': operation, 'arguments': arguments,
            'effects': ['read'], 'result_type': 'ToolAtlasObservation', 'authority': 'EXISTING_CALLER_PRINCIPAL_REQUIRED'}
    return {**body, 'program_id': desk.digest(body)}


def dispatch(kernel, op, args, principal):
    if op == 'atlas.lookup': return lookup(kernel, principal, **args)
    if op == 'atlas.operation_schema': return selected(kernel, principal, **args)
    if op == 'atlas.invocation': return invocation(principal=principal, **args)
    if op == 'atlas.passport.save':
        snapshot = selected(kernel, principal, **args)
        value = desk.new('tool_passport', principal, schema='ledger.tool-passport/1',
            state='SNAPSHOT_NOT_QUALIFICATION', entry=snapshot, binding=snapshot['binding'])
        with kernel.db() as db:
            return desk.write(db, value, principal, 'TOOL_PASSPORT_SNAPSHOT_SAVED_NO_GRANT')
    if op == 'atlas.passport.get':
        with kernel.db() as db: value = desk.read(db, 'tool_passport', args['id'], principal)
        try:
            current = selected(kernel, principal, value['entry']['name'], value['entry']['kind'])
            freshness = 'BINDING_UNCHANGED' if current['binding'] == value['binding'] else 'STALE'
            if freshness == 'BINDING_UNCHANGED' and not current['binding']['host']['session_digest']:
                freshness = 'HOST_BINDING_UNAVAILABLE'
        except ValueError:
            current, freshness = None, 'ENTRY_REMOVED'
        return {'schema': 'ledger.tool-passport-view/1', 'snapshot': value, 'current': current,
                'freshness': freshness, 'qualification': 'UNTESTED', 'notice': NOTICE}
    if op == 'atlas.passports.list':
        limit, offset = args.get('limit', 40), args.get('offset', 0)
        with kernel.db() as db:
            rows = db.execute('SELECT payload,digest FROM desk_records WHERE kind=? AND owner=? ORDER BY rowid DESC LIMIT ? OFFSET ?',
                              ('tool_passport', principal.identity, limit + 1, offset)).fetchall()
        values = []
        for raw, sha in rows[:limit]:
            value = json.loads(raw)
            if desk.digest(value) != sha: raise ValueError('PROJECT_DESK_RECORD_DAMAGED')
            values.append({'id': value['id'], 'created': value['created'], 'name': value['entry']['name'],
                           'kind': value['entry']['kind'], 'state': value['state']})
        return {'schema': 'ledger.tool-passport-list/1', 'passports': values,
                'has_more': len(rows) > limit, 'offset': offset, 'notice': 'Stored snapshots; open one to recheck its binding.'}
    raise ValueError('ATLAS_OPERATION_UNKNOWN')
