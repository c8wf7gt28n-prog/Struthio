"""A small relevant set of registered operations for one request: the Tool Atlas as working knowledge for Slate's turn.

Commission v2.1 asks that the model receive a few relevant tools for the task rather than reconsider the whole
catalogue on every request. The choice here is explicit word matching, never a model: the words of the request against
each operation's name, the capability family it belongs to (the Hatch and Explore adapters in ``explore.VIEWS``, with
their titles, descriptions and keywords) and the names of its arguments. The default offers read and execute operations.
A private local plan can also pass a specific set of Programs operations for owner review. The plan path adds the chosen
contracts to its small fixed direct set, so a local model reads a
handful of relevant schemas with a one-line reason for each. Nothing here runs a tool.
"""
from __future__ import annotations
import re
from . import explore

STOP = {'a', 'an', 'the', 'and', 'or', 'of', 'to', 'in', 'on', 'for', 'with', 'from', 'by', 'at', 'into', 'about', 'it', 'its', 'this', 'that', 'these', 'those',
        'is', 'are', 'be', 'was', 'were', 'do', 'does', 'did', 'can', 'could', 'would', 'should', 'will', 'please', 'me', 'my', 'our', 'your', 'we', 'you', 'i',
        'slate', 'ledger', 'make', 'get', 'use', 'using', 'then', 'now', 'all', 'any', 'some', 'what', 'which', 'how', 'when', 'where', 'why', 'open', 'existing',
        'current', 'new', 'one', 'two', 'there', 'here', 'also', 'just', 'like', 'so', 'if', 'not', 'no', 'up', 'out', 'as', 'than', 'more', 'most', 'other', 'own',
        'ledgers', 'controls', 'control', 'inspect', 'work', 'working', 'record', 'records', 'saved', 'read', 'list', 'status', 'result', 'results', 'thing', 'things'}
DENY = {'jobs.submit', 'ledger.settings.set', 'ledger.settings.undo', 'ledger.settings.restore', 'ledger.settings.apply', 'language.run', 'ledger.navigate', 'ledger.open'}
GENERIC = {'get', 'list', 'status', 'read', 'result', 'results', 'preview', 'run', 'save', 'create', 'add', 'delete', 'update', 'check', 'commit', 'discard'}
PROGRAM_VERBS = {
    'inspect': {'inspect', 'read', 'review', 'examine', 'identify'},
    'check': {'check', 'measure', 'count'},
    'export': {'export', 'render', 'save', 'convert', 'generate'},
    'clip': {'clip', 'trim', 'excerpt', 'cut'},
    'extract': {'extract', 'attachment'},
    'draft': {'draft', 'reply'},
    'build': {'build', 'assemble', 'bundle', 'package'},
    'verify': {'verify', 'validate'},
    'open': {'open', 'editor', 'edit'},
    'play': {'play', 'run'},
    'launch': {'launch', 'play', 'start'},
    'list': {'list', 'browse'},
    'download': {'download', 'retrieve'},
    'status': {'status', 'availability'},
}


def stem(word):
    """The singular: plural and past endings drop; -ing stays (heading, writing) so the forms below carry the shorter root."""
    if word.endswith('ies') and len(word) > 5: return word[:-3] + 'y'
    if word.endswith(('ses', 'xes', 'zes', 'ches', 'shes')) and len(word) > 5: return word[:-2]
    if word.endswith('s') and not word.endswith('ss') and len(word) > 3: return word[:-1]
    if word.endswith('ed') and len(word) > 4: return word[:-2]
    return word


def forms(word):
    """Every spelling a word may meet: itself, its singular, and its root without -ing (writing → writ, write)."""
    out = {word, stem(word)}
    if word.endswith('ing') and len(word) > 5: out |= {word[:-3], word[:-3] + 'e'}
    return out


def tokens(text):
    return {form for w in re.findall(r'[a-z0-9]+', str(text or '').casefold()) if w not in STOP and len(w) > 1 for form in forms(w) if form not in STOP and len(form) > 1}


# Words the adapters' own keywords do not carry but owners use for them, and families with no Hatch adapter.
EXTRA_WORDS = {'calculate': 'plot graph chart curve sweep voltage current resistance power csv data values calculation calculate compute evaluate solve units',
               'office': 'spreadsheet sheet table cells workbook xlsx ods docx writer calc document',
               'knowledge': 'notes note search find facts source',
               'files': 'file folder note notes text find search',
               'documents': 'document page paragraph heading bold italic underline write writing text words sentence edit revision',
               'brain': 'model gguf llama load replace stop',
               'memory': 'remember recollection lesson preference task'}
EXTRA_FAMILIES = [{'key': 'machine', 'title': 'Machine', 'prefixes': ('ledger.machine',),
                   'words': 'machine computer host processor cpu core memory ram storage disk drive partition mount free space network connection interface device usb display screen installed tool'},
                  {'key': 'notes', 'title': 'Notes exchange', 'prefixes': ('notes.',), 'words': 'notes note idea thought exchange export import collection'},
                  {'key': 'math', 'title': 'Mathematics', 'prefixes': ('math.',), 'words': EXTRA_WORDS['calculate']},
                  {'key': 'agenda', 'title': 'Operations agenda', 'prefixes': ('agenda.',), 'words': 'agenda queue schedule later priority job'},
                  # AGENT-01: the resident agent loop, condition cards and retained helpers
                  {'key': 'assignments', 'title': 'Assignments', 'prefixes': ('agent.assign', 'agent.step', 'agent.run', 'agent.pause', 'agent.resume', 'agent.stop', 'agent.status', 'agent.list', 'agent.release'),
                   'words': 'assignment assign task investigate investigation work working continue pause resume stop status progress findings slate release closed service'},
                  {'key': 'conditions', 'title': 'Condition cards', 'prefixes': ('conditions.',), 'words': 'condition result total sum stale recheck bound inputs calculation changed'},
                  {'key': 'helpers', 'title': 'Retained helpers', 'prefixes': ('helpers.',), 'words': 'helper helpers procedure method reuse effective'},
                  # HATCH DESK D5: this computer's network; observe and capture.read are reads, capture.start is the owner's (a proposal here)
                  {'key': 'network', 'title': 'Network', 'prefixes': ('network.',), 'order': ('network.observe', 'network.capture.read', 'network.capture.start'),
                   'words': 'network traffic connection connections connected port ports packet packets bandwidth listening listen socket sockets '
                            'interface interfaces internet sniff sniffer capture talking upload download rate rates tcp udp'}]


def families():
    """One row per adapter (plus the families above): its operation prefixes and the words of its title, description and keywords."""
    rows = []
    for row in explore.VIEWS:
        words = tokens(row[1] + ' ' + row[2] + ' ' + row[8] + ' ' + EXTRA_WORDS.get(row[0], ''))
        rows.append({'key': row[0], 'title': row[1], 'prefixes': tuple(row[7]), 'words': words})
    for extra in EXTRA_FAMILIES: rows.append({**extra, 'words': tokens(extra['words'])})
    return rows


def relevant(text, capabilities, definitions, limit=6, exclude=(), *, review_actions=(), program_tools=None):
    """Up to ``limit`` operations with a reason each, best match first; [] when the request has no matching words."""
    words = tokens(text)
    program_tools = program_tools or {}
    if not (words or program_tools) or limit <= 0: return []
    raw_words = set(re.findall(r'[a-z]+', str(text or '').casefold()))
    rows = families(); excluded = set(exclude) | DENY; chosen = []
    for op, scope in capabilities.items():
        if op in excluded or (scope not in ('read', 'execute') and
                              (scope != 'approve' or not op.startswith('programs.') or op not in review_actions)):
            continue
        parts = {form for p in re.split(r'[._]', op.casefold()) if p and p not in STOP for form in forms(p)}
        by_name = sorted(words & parts - GENERIC); generic_name = bool(words & parts & GENERIC)
        family = next((row for row in rows if op.startswith(row['prefixes'])), None)
        by_family = sorted(words & family['words']) if family else []
        argument_names = {form for k in (definitions.get(op) or {}).get('properties', {}) for form in forms(k.casefold())}
        by_args = sorted(words & argument_names - GENERIC)
        score = 3 * len(by_name) + 2 * len(by_family) + len(by_args) + (1 if generic_name and (by_name or by_family) else 0)
        on_program = program_tools.get(op)
        if not (by_name or by_family or on_program): continue
        if op.startswith('programs.'):
            verb = op.rsplit('.', 1)[-1]
            score += 5 if raw_words & PROGRAM_VERBS.get(verb, set()) else 0
        if on_program:
            score += on_program['score']
        reason = '; '.join(filter(None, ['name: ' + ', '.join(by_name) if by_name else '', ('family %s: ' % family['title']) + ', '.join(by_family) if by_family else '',
                                         'arguments: ' + ', '.join(by_args) if by_args else '',
                                         on_program['reason'] if on_program else '',
                                         'requires owner review' if scope == 'approve' else '']))
        order = tuple((family or {}).get('order') or ())   # a family may say which of its operations come first (the reads)
        rank = (order.index(op) if op in order else len(order)) if order else None
        chosen.append({'operation': op, 'scope': scope, 'score': score, 'reason': reason, 'family': family['key'] if family else None, 'rank': rank})
    # A family with its own order (the network's: its reads before its controls) ranks its operations together at the family's
    # best score, so an argument name shared with one control never puts that control before the reads.
    best = {}
    for row in chosen:
        if row['rank'] is not None and row['family']: best[row['family']] = max(best.get(row['family'], 0), row['score'])
    for row in chosen:
        if row['rank'] is not None and row['family'] in best: row['score'] = best[row['family']]
    chosen.sort(key=lambda r: (-r['score'], r['rank'] or 0, r['operation']))
    # Breadth over depth: at most two operations per family before the rest fill the remaining places.
    first, rest, seen = [], [], {}
    for row in chosen:
        key = row['family'] or row['operation'].split('.')[0]; seen[key] = seen.get(key, 0) + 1
        (first if seen[key] <= 2 else rest).append(row)
    picked = (first + rest)[:limit]
    return [{**{k: v for k, v in row.items() if k != 'rank'}, 'arguments': definitions.get(row['operation'], {})} for row in picked]


def describe(rows):
    """The one-line list the model reads: operation, scope and why it was chosen. Data, not instructions."""
    return [{'operation': r['operation'], 'scope': r['scope'], 'why': r['reason']} for r in rows]
