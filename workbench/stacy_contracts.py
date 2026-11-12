"""Qt-free Pass 1 request, packet and deterministic-provider contracts.

This is a source-backed test adapter. It is not a local language model.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Protocol

PACKET_SCHEMA = 'arc.stacy-foundation-packet/1'
ANSWER_SCHEMA = 'arc.stacy-foundation-answer/1'
MAX_PACKET_BYTES = 160_000
VIEWS = ('settings', 'commands', 'hdl')
NOTICE = 'Deterministic source reader; no LLM, cloud request, job or physical qualification.'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def pointer(data, path):
    if not isinstance(path, str) or not path.startswith('/data/') or len(path) > 180:
        raise ValueError('Only declared context data may support a claim')
    current = data
    for segment in path[1:].split('/'):
        segment = segment.replace('~1', '/').replace('~0', '~')
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            raise ValueError('Claim points outside the supplied context')
    return current


def validate_packet(packet):
    if not isinstance(packet, dict) or packet.get('schema') != PACKET_SCHEMA:
        raise ValueError('Unsupported foundation packet')
    if len(json.dumps(packet, ensure_ascii=False).encode()) > MAX_PACKET_BYTES:
        raise ValueError('Context exceeds the foundation packet budget')
    if packet.get('view') not in VIEWS or packet.get('permission') != 'read':
        raise ValueError('Foundation packets are read-only supported views')
    expected = digest({k: v for k, v in packet.items() if k != 'packet_id'})
    if packet.get('packet_id') != expected:
        raise ValueError('Packet digest does not match its content')
    sources = packet.get('sources')
    if not isinstance(sources, list) or not sources or len(sources) > 40:
        raise ValueError('Packet requires bounded source bindings')
    ids = set()
    for source in sources:
        if not isinstance(source, dict) or not all(k in source for k in ('id', 'path', 'sha256')):
            raise ValueError('Incomplete packet source')
        if (source['id'] in ids or not isinstance(source['sha256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', source['sha256'])):
            raise ValueError('Invalid or duplicate packet source')
        ids.add(source['id'])
    if not isinstance(packet.get('data'), dict):
        raise ValueError('Missing context data')
    return packet


def validate_answer(answer, packet):
    validate_packet(packet)
    if not isinstance(answer, dict) or answer.get('schema') != ANSWER_SCHEMA:
        raise ValueError('Unsupported foundation answer')
    if set(answer) != {'schema','provider','packet_id','actions','claims','unknowns','notice'}:
        raise ValueError('Unknown answer fields')
    if answer.get('packet_id') != packet['packet_id']:
        raise ValueError('Answer belongs to another context')
    if answer.get('provider') != 'deterministic-seed-reader':
        raise ValueError('Pass 1 qualifies only the deterministic provider')
    claims = answer.get('claims')
    if not isinstance(claims, list) or not 1 <= len(claims) <= 12:
        raise ValueError('Answer must contain bounded structured claims')
    ids = {s['id'] for s in packet['sources']}
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {'pointer', 'value', 'sources'}:
            raise ValueError('Incomplete structured claim')
        actual = pointer(packet, claim['pointer'])
        if type(actual) is not type(claim['value']) or actual != claim['value']:
            raise ValueError('Unsupported claim value')
        if not isinstance(claim['sources'], list) or not claim['sources'] or not set(claim['sources']) <= ids:
            raise ValueError('Citation is absent from the packet')
    if answer.get('actions') != []:
        raise ValueError('The foundation provider cannot propose execution')
    if answer.get('unknowns') != packet.get('unknowns') or answer.get('notice') != NOTICE:
        raise ValueError('Answer removed or changed its qualification limits')
    return answer


class Provider(Protocol):
    def describe(self, packet: dict) -> dict: ...


class DeterministicProvider:
    """Produces field claims, not unchecked free-form technical conclusions."""
    provider_id = 'deterministic-seed-reader'

    def describe(self, packet):
        packet = validate_packet(copy.deepcopy(packet))
        fields = {
            'settings': ('key', 'label', 'value', 'description', 'unit', 'effect'),
            'commands': ('operation', 'scope', 'status', 'reason', 'qualification'),
            'hdl': ('profile', 'title', 'runtime_state', 'recorded_trace', 'evidence_scope'),
        }[packet['view']]
        citations = [s['id'] for s in packet['sources']]
        answer = {
            'schema': ANSWER_SCHEMA, 'provider': self.provider_id,
            'packet_id': packet['packet_id'], 'actions': [],
            'claims': [{'pointer': '/data/' + field,
                        'value': copy.deepcopy(packet['data'][field]),
                        'sources': citations} for field in fields],
            'unknowns': copy.deepcopy(packet.get('unknowns', [])),
            'notice': NOTICE,
        }
        return validate_answer(answer, packet)


def render_answer(answer, packet):
    validate_answer(answer, packet)
    values = {c['pointer'].split('/')[-1]: c['value'] for c in answer['claims']}
    if packet['view'] == 'settings':
        text = (f"{values['label']} is {values['value']} ({values['unit']}). "
                f"{values['description']} Effect: {values['effect']}.")
    elif packet['view'] == 'commands':
        text = (f"{values['operation']} requires the {values['scope']} scope. "
                f"Current status: {values['status']}. {values['reason']} "
                f"Qualification: {values['qualification']}.")
    else:
        text = (f"{values['title']} uses the {values['profile']} profile. "
                f"Runtime: {values['runtime_state']}. Recorded trace: {values['recorded_trace']}. "
                f"Evidence scope: {values['evidence_scope']}.")
    return text
