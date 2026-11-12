"""One address form for every Ledger object: ``kind:identifier``.

Each kind names the existing registered read operation that already shows one
such object, and the argument the identifier fills. Reading an address is that
same Kernel call with the caller's own principal: it grants nothing the caller
could not already read, and it adds no storage, cache or second copy.

  notebook:owner:<32 hex>   office:owner:<32 hex>   notes:owner:<32 hex>
  job:<id>   evidence:<id>   intake:<32 hex>   knowledge:<32 hex>   study:<32 hex>
  component:<ref>   net:<name>   requirement:<id>   file:<project path>  ...
"""
from __future__ import annotations

TEXT = {'type': 'string', 'minLength': 3, 'maxLength': 600}
FIELDS = {'ledger.address.kinds': ({}, []),
          'ledger.address.read': ({'address': TEXT}, ['address'])}
SCOPES = {op: 'read' for op in FIELDS}

# kind: (registered read operation, argument the identifier fills, what it shows)
KINDS = {
    'work': ('work.get','id','Frozen work order, owner grant, budgets and continuing progress'),
    'procedure': ('procedures.get','id','Owner-reviewed reusable staC call procedure'),
    'worker': ('workers.run','id','Private protected-worker execution receipt'),
    'context': ('slate.context.get', 'id', 'Frozen ranked Slate context, locators and exclusions'),
    'document': ('documents.get', 'id', 'Saved document and its revision'),
    'calculation': ('math.get', 'id', 'Saved calculation and current input applicability'),
    'reason': ('reasons.get', 'id', 'Declared dependencies and their current observations'),
    'artifact': ('artifacts.get', 'id', 'Checked application output and parent revisions'),
    'condition': ('conditions.get', 'id', 'Document calculation and its source condition'),
    'project': ('projects.get', 'id', 'Project intent and durable links'),
    'idea': ('ideas.get', 'id', 'Original idea and its project link'),
    'assignment': ('assignments.get', 'id', 'Assignment request and current interpretation'),
    'plan': ('plans.get', 'id', 'Frozen plan, typed interpretation and requested scope'),
    'review': ('reviews.get', 'id', 'Frozen owner review and output snapshots'),
    'job': ('jobs.get', 'id', 'Kernel job record and state'),
    'evidence': ('evidence.read', 'id', 'Recorded evidence of a job'),
    'trail': ('ledger.trail.inspect', 'id', 'Work trail entry'),
    'notebook': ('notebook.get', 'id', 'Saved engineering notebook (id begins owner:)'),
    'office': ('office.get', 'id', 'Saved Office table or document (id begins owner:)'),
    'notes': ('notes.exchange.get', 'collection', 'Imported notes collection (id begins owner:)'),
    'intake': ('intake.read', 'id', 'Reviewed intake item'),
    'package': ('intake.package.get', 'id', 'Inspected intake package'),
    'packet': ('references.packet', 'id', 'Reference packet'),
    'collection': ('references.collection', 'namespace', 'Admitted reference collection and index generation'),
    'knowledge': ('knowledge.get', 'id', 'Connected knowledge source'),
    'map': ('knowledge.map.get', 'id', 'Reference engineering map'),
    'study': ('study.get', 'id', 'Study'),
    'research': ('research.request', 'id', 'Research request'),
    'task': ('memory.task', 'id', 'Task memory'),
    'conversation': ('memory.conversation', 'id', 'Saved conversation'),
    'checkpoint': ('memory.checkpoint', 'id', 'Memory checkpoint'),
    'model': ('brain.model.inspect', 'id', 'Registered local model'),
    'seed': ('stacy.seed.record', 'id', 'Slate knowledge seed record'),
    'file': ('files.read', 'path', 'Project file (read-only)'),
    'files': ('files.get', 'path', 'A file or folder in Files'),
    'copies': ('copies.get', 'id', 'A working copy: its original, its state and its last revision'),
    'book': ('book.read', 'page', 'Orange Book page'),
    'component': ('ledger.object.inspect', 'selector', 'Board component (attached project)'),
    'net': ('ledger.object.inspect', 'selector', 'Board net (attached project)'),
    'requirement': ('ledger.object.inspect', 'selector', 'Working requirement'),
}
SELECTOR_KINDS = ('component', 'net', 'requirement')


def parse(address):
    """Return (kind, identifier). The identifier is data, validated by the target operation."""
    if not isinstance(address, str) or not 3 <= len(address) <= 600 or any(ord(c) < 32 for c in address):
        raise ValueError('ADDRESS_INVALID: use kind:identifier')
    # staC writes an address as @kind:identifier; the @ is accepted here too.
    kind, separator, identifier = address.strip().removeprefix('@').partition(':')
    if not separator or not identifier:raise ValueError('ADDRESS_INVALID: use kind:identifier')
    if kind not in KINDS:raise ValueError('ADDRESS_KIND_UNKNOWN: ' + kind[:40] + '; see ledger.address.kinds')
    return kind, identifier


def call(address):
    """The exact registered Kernel call an address stands for."""
    kind, identifier = parse(address)
    operation, argument, _ = KINDS[kind]
    value = {'kind': kind, 'target': identifier} if kind in SELECTOR_KINDS else identifier
    return kind, operation, {argument: value}


def kinds():
    from .engineering_kernel import CAPABILITIES
    return {'schema': 'arc.ledger-address-kinds/1', 'form': 'kind:identifier',
            'kinds': [{'kind': kind, 'operation': op, 'argument': arg, 'shows': shows,
                       'permission': CAPABILITIES.get(op)} for kind, (op, arg, shows) in sorted(KINDS.items())]}


def read(kernel, address, principal):
    from .engineering_kernel import CAPABILITIES
    kind, operation, arguments = call(address)
    if CAPABILITIES.get(operation) != 'read':raise ValueError('ADDRESS_TARGET_NOT_READ_ONLY')
    envelope = kernel.dispatch(operation, arguments, principal)
    if not envelope.get('ok'):
        error = envelope.get('error') or {}
        raise ValueError('ADDRESS_UNAVAILABLE: ' + str(error.get('message', 'not readable'))[:300])
    return {'schema': 'arc.ledger-address/1', 'address': kind + ':' + address.strip().partition(':')[2],
            'kind': kind, 'operation': operation, 'arguments': arguments, 'object': envelope['result']}


def dispatch(kernel, op, args, principal):
    if op == 'ledger.address.kinds':return kinds()
    if op == 'ledger.address.read':return read(kernel, args['address'], principal)
    raise ValueError('Unknown address operation')
