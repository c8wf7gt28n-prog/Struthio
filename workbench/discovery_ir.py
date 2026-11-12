"""Finite, versioned inquiry syntax. All imported/model-authored content is data."""
import copy
from . import adaptive_contract as types, algorithm_atlas as algorithms, project_desk as desk

SCHEMA = 'ledger.discovery-ir/1'
KEY = {'type': 'string', 'minLength': 1, 'maxLength': 40, 'pattern': '^[A-Za-z][A-Za-z0-9_]{0,39}$'}
TEXT = types.text(2000)
DEPENDENCIES = {**types.array(KEY, 24), 'uniqueItems': True}
BASE = {'key': KEY, 'depends_on': DEPENDENCIES}
STATEMENT = types.obj({**BASE, 'text': TEXT, 'scope': TEXT})
SOURCE = types.obj({'key': KEY, 'address': desk.ADDRESS, 'role': TEXT})
ASSUMPTION = types.obj({'key': KEY, 'text': TEXT, 'scope': TEXT,
    'origin': {'type': 'string', 'enum': ['HUMAN', 'MODEL', 'IMPORTED']},
    'certainty': {'type': 'string', 'enum': ['DECLARED', 'UNKNOWN']}})
CONSTRAINT = types.obj({**BASE, 'context': algorithms.CONTEXT})
METHOD = types.obj({**BASE, 'algorithm': algorithms.NAME, 'constraint': KEY})
EXPERIMENT = types.obj({**BASE, 'question': TEXT, 'method': KEY, 'expected': types.array(TEXT, 8)})
NEXT = types.obj({**BASE, 'kind': {'type': 'string', 'enum': ['ASK', 'PROPOSE_CHECK', 'REVIEW']}, 'text': TEXT})
IR = types.obj({'schema': {'type': 'string', 'enum': [SCHEMA]}, 'title': desk.TITLE,
    'goal': types.obj({'question': TEXT, 'stopping_criteria': {**types.array(TEXT, 8), 'minItems': 1}}),
    'sources': types.array(SOURCE, 8), 'assumptions': types.array(ASSUMPTION, 16),
    'hypotheses': types.array(STATEMENT, 8), 'constraints': types.array(CONSTRAINT, 8),
    'candidate_methods': types.array(METHOD, 8), 'experiments': types.array(EXPERIMENT, 8),
    'claims': types.array(STATEMENT, 8), 'next_actions': types.array(NEXT, 8), 'budget': desk.BUDGET})


def template():
    return {'schema': SCHEMA, 'title': 'New inquiry',
        'goal': {'question': 'What would make this idea testable?', 'stopping_criteria': ['Identify a concrete check and the information it needs.']},
        **{name: [] for name in ('sources', 'assumptions', 'hypotheses', 'constraints', 'candidate_methods', 'experiments', 'claims', 'next_actions')},
        'budget': copy.deepcopy(desk.DEFAULT_BUDGET)}


def validate(document):
    if len(desk.canonical(document).encode()) > 128 * 1024: raise ValueError('DISCOVERY_DOCUMENT_BOUND')
    types.validate_schema(document, IR)
    def meaningful(value):
        if isinstance(value, str) and not value.strip(): raise ValueError('DISCOVERY_BLANK_TEXT')
        if isinstance(value, dict):
            for item in value.values(): meaningful(item)
        elif isinstance(value, list):
            for item in value: meaningful(item)
    meaningful(document)
    nodes = {'goal': {'kind': 'goal', 'body': {'title': document['title'], **document['goal']}, 'depends_on': []}}
    for family in ('sources', 'assumptions', 'hypotheses', 'constraints', 'candidate_methods', 'experiments', 'claims', 'next_actions'):
        for value in document[family]:
            key = value['key']
            if key in nodes: raise ValueError('DISCOVERY_DUPLICATE_KEY: ' + key)
            parents = list(value.get('depends_on', []))
            if family not in ('sources', 'assumptions'): parents.append('goal')
            if family == 'candidate_methods': parents.append(value['constraint'])
            if family == 'experiments': parents.append(value['method'])
            nodes[key] = {'kind': family, 'body': copy.deepcopy(value), 'depends_on': sorted(set(parents))}
    for key, node in nodes.items():
        for parent in node['depends_on']:
            if parent not in nodes: raise ValueError('DISCOVERY_DEPENDENCY_NOT_DECLARED: ' + parent)
            if parent == key: raise ValueError('DISCOVERY_DEPENDENCY_CYCLE: ' + key)
        body = node['body']
        if node['kind'] == 'candidate_methods' and nodes[body['constraint']]['kind'] != 'constraints':
            raise ValueError('DISCOVERY_METHOD_NEEDS_CONSTRAINT')
        if node['kind'] == 'experiments' and nodes[body['method']]['kind'] != 'candidate_methods':
            raise ValueError('DISCOVERY_EXPERIMENT_NEEDS_METHOD')
    order = []; active = set(); visited = set()
    def visit(key):
        if key in active: raise ValueError('DISCOVERY_DEPENDENCY_CYCLE: ' + key)
        if key in visited: return
        active.add(key)
        for parent in nodes[key]['depends_on']: visit(parent)
        active.remove(key); visited.add(key); order.append(key)
    for key in nodes: visit(key)
    return nodes, order


def closure(nodes, key):
    result = set()
    def add(name):
        if name in result: return
        result.add(name)
        for parent in nodes[name]['depends_on']: add(parent)
    add(key); return result


def digests(nodes, order, sources, methods, protocol=None):
    result = {}
    for key in order:
        value = {'body': nodes[key]['body'], 'parents': {p: result[p] for p in nodes[key]['depends_on']}}
        if key == 'goal': value['protocol'] = protocol
        if key in sources:
            binding = sources[key]
            value['source'] = {k: binding[k] for k in ('operation', 'arguments', 'operation_schema', 'revision')}
        if key in methods: value['method_definition'] = methods[key]['definition_digest']
        result[key] = desk.digest(value)
    return result
