"""Desk acts: one named act for each thing a person can do in Graphite's window.

The owner, 14 November 2026: "a pass that builds as much capabilities of Kasandra to control the graphite interface ...
eventually we're going to do that, and that opens up more testing options and simulating options". Until this pass only a
person could drive the window (open the Field, select a sheet, open a right-click and choose a row, carry the line panel,
put words in the writing line, zoom, choose the appearance, read back what is open); tests and probes reached into widgets.

This module is the registry, with no Qt in it: each act's name, its words, its mark, its argument schema, the Kernel
operation a change goes through, whether only the owner may do it, and the forms it has (pointer, keys). The window side,
the function that does each act on the live window, is desk_doers.py; scripts of acts are desk_scene.py.

Two marks. An act that "navigates" changes nothing: it opens, selects, zooms or reads back. An act that "changes" goes
through Stacy's hand exactly as a Kernel operation asked of her does (shell2.SlateFace.stage: its card, its trail entry, its
Undo; what always asks still asks). Every hand.* act and look.set changes; every other act navigates.

Three doors over the one registry: the owner types an act in the writing line (/go.field face=apps); tests and the
campaign run scripts of acts; and later her model. This pass does not offer acts to her model: tools() and plan_variants()
only describe them, and desk_hers() is her hand's rule for them, written and tested, with nothing calling it yet.

Every word here is shown to a person: no key is named, the line language is called "a line", and the list of programs is
"Apps".
"""
import json
import re
from dataclasses import dataclass, field

from . import stacy_hand
from .agent_operations import validate
from .assistant_identity import named

ACT_HEADS = ('go', 'point', 'head', 'menu', 'then', 'sheet', 'type', 'hand', 'look', 'read')
MARKS = ('navigates', 'changes')
OWNER_ONLY = ('hand.approve', 'hand.undo', 'hand.dial', 'look.set', 'type.send')
HEAD_MENUS = ('Work', 'Revise', 'Tools', 'Arrange', 'Commands', 'Rules', 'Properties', 'Guide')
# The head's rows an act may choose: each goes somewhere and changes nothing. A row that asks, leaves, stops work or opens a
# window that asks stays the owner's (head.row refuses it). The words are the rows' own, as the menus print them.
HEAD_ROWS = {'Arrange': ('Today', 'Field', 'Files', 'Library', 'Project Desk', 'Changes', 'Continuing work', "Graphite's Agenda"),
             'Tools': ('Explore capabilities', 'Tool Atlas', 'Algorithm & Theory Atlas')}
# The right-click's rows an act may choose (menu.choose, and the acts that walk a menu for the owner: Then, trace, doubt,
# compare, the steps). Each goes somewhere in Graphite, shows, reads, selects or copies; none changes a record, leaves
# Graphite, asks her model or opens a window that asks. Every other row stays the owner's: the review of 0.8.2 found rows
# that name no operation and still change (Stage in Delivery, Delete in a document, Edit the Graphite menu) or leave (Open
# with this computer's app), so a row is chosen only when it is listed here, never because it names nothing. A key ending
# in ':' or ' ' stands for the rows made from it (one per file, sheet, step or value). A row that opens further rows is not
# listed: opening it chooses nothing. The row's operation and its "asks" are still checked as well.
MENU_ROWS = ('open', 'open:viewer', 'show:folder', 'show:files', 'show:log', 'show:finder', 'job:show', 'copy:original', 'change:files',
             'follow', 'process', 'atlas', 'algorithms', 'explore', 'search', 'expand', 'collapse', 'view:', 'hidden', 'preview', 'refresh',
             'run', 'inspect', 'extract:', 'compare:version:', 'job:output', 'line:', 'start:',
             'copy:path', 'copy:paths', 'copy:address', 'copy:name', 'copy:id', 'copy:key', 'copy:row', 'copy', 'edit:copy', 'edit:all',
             'field:open', 'field:back', 'field:face:', 'field:go:', 'field:again', 'field:check', 'field:brief', 'field:inspect', 'field:run',
             'field:trace', 'field:trace:', 'field:doubt', 'field:doubt:', 'field:do', 'field:do:', 'field:revisions', 'field:stac:', 'field:copy')
# The line panel's rows (Then): each puts a reading step on the line or takes one off, or ends the line by showing its
# answer, putting it in the writing line, or copying it. The panel's line only reads.
PANEL_ROWS = ('back', 'read:', 'step:', 'field:', 'where ', 'where:other', 'sort:', 'group:', 'first:', 'end:show', 'end:line', 'end:copy', 'end:rows')
# Rows that only open further rows (the doer reads this from the live menu; her hand's rule, with no menu, reads it here).
SCREENS = ('then', 'more', 'group:', 'page:next', 'start', 'line', 'view', 'extract', 'compare:version', 'field:fed', 'field:feeds', 'field:stac', 'job')


def listed(key, rows):
    """Whether a row's key is on a list of rows (an exact key, or the rows made from a key ending in ':' or ' ')."""
    key = str(key or '')
    return any(key == row or (row.endswith((':', ' ')) and key.startswith(row)) for row in rows)


def S(least, most):
    return {'type': 'string', 'minLength': least, 'maxLength': most} if least else {'type': 'string', 'maxLength': most}


def I(least, most):
    return {'type': 'integer', 'minimum': least, 'maximum': most}


def E(*words):
    return {'type': 'string', 'enum': list(words)}


BY = E('pointer', 'keys')


def schema_of(properties, required=()):
    return {'type': 'object', 'properties': dict(properties), 'required': list(required), 'additionalProperties': False}


@dataclass
class Act:
    name: str
    words: str                      # what it does, in plain words (help shows them; no row prints them at rest)
    schema: dict
    kernel: str = ''                # the Kernel operation a change goes through ('' for an act that navigates)
    forms: str = 'P'                # P: by pointer; K: by keys; PK: both. A keys form that does not exist falls back to the pointer
    one_of: tuple = ()              # exactly one of these arguments
    at_least: tuple = ()            # at least one of these arguments
    line_decides: bool = False      # hand.step: the step's own line names the operation

    @property
    def mark(self):
        return 'changes' if self.name.startswith(('hand.', 'look.')) else 'navigates'

    @property
    def owner_only(self):
        return self.name in OWNER_ONLY

    @property
    def exported(self):
        return not self.owner_only


def _acts():
    path = S(1, 1000)
    rows = (
        Act('go.field', 'Bring the Field to the front, on its work, Apps or network face.',
            schema_of({'face': E('work', 'apps', 'network'), 'by': BY}), forms='PK'),
        Act('go.today', 'Go to Today.', schema_of({'by': BY}), forms='PK'),
        Act('go.files', 'Open Files, in a folder, shown as icons or as a list.',
            schema_of({'folder': S(0, 1000), 'view': E('icons', 'list'), 'by': BY}), forms='PK'),
        Act('go.open', 'Open a sheet of the Field, a file in Files, or one of the open tabs.',
            schema_of({'sheet': S(1, 200), 'path': path, 'tab': I(0, 200), 'by': BY}), forms='PK', one_of=('sheet', 'path', 'tab')),
        Act('go.app', 'Open one of the Apps by its key.', schema_of({'key': S(1, 120)}, ('key',))),
        Act('go.back', 'Leave the Field for the place you came from.', schema_of({'by': BY}), forms='PK'),
        Act('go.pane', named('Choose what the left pane shows (Files, Machine, Settings) and the right (Talk with Stacy, Activity, Context).'),
            schema_of({'left': E('files', 'machine', 'settings'), 'right': E('talk', 'activity', 'context')}), at_least=('left', 'right')),
        Act('point.sheet', 'Select a sheet in the Field by its title or its id; nothing opens.',
            schema_of({'title': S(1, 200), 'id': S(1, 200), 'by': E('direct', 'pointer', 'keys')}), forms='PK', one_of=('title', 'id')),
        Act('point.move', 'Move the selection in the Field: left, right, up, down, to the first or the last sheet, to the next that waits, or back.',
            schema_of({'way': E('left', 'right', 'up', 'down', 'first', 'last', 'next_waiting', 'before'), 'times': I(1, 20)}, ('way',)), forms='K'),
        Act('point.zoom', 'See the whole desk, the reading size, or the sheets larger or smaller.',
            schema_of({'to': E('whole', 'reading', 'larger', 'smaller'), 'by': BY}, ('to',)), forms='PK'),
        Act('head.open', 'Open one of the menus across the head, or the Apps list, and read its rows.',
            schema_of({'menu': E(*(HEAD_MENUS + ('Apps',))), 'by': BY}, ('menu',)), forms='PK'),
        Act('head.row', 'Choose a row of a head menu that goes somewhere: Today, the Field, Files, the Library and the like.',
            schema_of({'menu': E(*HEAD_MENUS), 'row': S(1, 120), 'by': BY}, ('menu', 'row')), forms='PK'),
        Act('head.meter', 'Open the card of a meter in the head, or of the equalizer, and read it.',
            schema_of({'which': E('CPU', 'GPU', 'RAM', 'TXT', 'equalizer')}, ('which',))),
        Act('menu.open', 'Open the right-click menu on a file in Files, on a sheet in the Field, or here.',
            schema_of({'on': E('file', 'sheet', 'here'), 'name': path, 'by': BY}, ('on',)), forms='PK'),
        Act('menu.choose', 'Choose a row of the open right-click menu by its key or its words; a deeper row after a slash.',
            schema_of({'path': S(1, 400), 'by': BY}, ('path',)), forms='PK'),
        Act('menu.close', 'Close whatever menu or card is open.', schema_of({'by': BY}), forms='PK'),
        Act('then.keep', 'In the line panel: keep the rows where a column has a value, by the words of that choice.',
            schema_of({'column': S(1, 120), 'words': S(1, 200), 'by': BY}, ('column', 'words')), forms='PK'),
        Act('then.count', 'In the line panel: count the rows.', schema_of({'by': BY}), forms='PK'),
        Act('then.back', 'In the line panel: take the last step off.', schema_of({'by': BY}), forms='PK'),
        Act('then.end', 'End the line panel: show the answer, put the line in the writing line, copy the line, or copy the rows.',
            schema_of({'how': E('show', 'line', 'copy', 'rows'), 'by': BY}, ('how',)), forms='PK'),
        Act('sheet.trace', 'Trace the selected sheet: where it comes from and what rests on it.', schema_of({'by': BY}), forms='PK'),
        Act('sheet.doubt', 'Doubt the selected sheet: what a plausible result may hide.', schema_of({'by': BY}), forms='PK'),
        Act('sheet.compare', 'Compare the selected sheet with its other revision on the desk, side by side.', schema_of({'by': BY}), forms='PK'),
        Act('sheet.close', 'Put away what is shown over the work: a comparison, a page, the steps, a what-if.', schema_of({'by': BY}), forms='PK'),
        Act('sheet.whatif', 'Ask what would move if a number of the selected sheet were another; nothing is changed.',
            schema_of({'cell': S(2, 8), 'value': S(1, 40)}, ('cell', 'value'))),
        Act('sheet.steps', 'List what can be done about the selected sheet; nothing is taken.', schema_of({'by': BY}), forms='PK'),
        Act('type.to', named('Choose whom the writing line goes to: Stacy, the Terminal, Search, the Web or the Log.'),
            schema_of({'who': E('her', 'terminal', 'search', 'web', 'log'), 'by': BY}, ('who',)), forms='PK'),
        Act('type.put', 'Put one line of words in the writing line; nothing is sent.', schema_of({'text': S(1, 4000), 'by': E('put', 'keys')}, ('text',)), forms='PK'),
        Act('type.send', 'Send what the writing line holds, as the arrow does.', schema_of({'by': E('arrow', 'keys')}), forms='PK'),
        Act('type.room', 'Give the working area above the line one line, half the window, or more.', schema_of({'size': E('line', 'half', 'tall')}, ('size',))),
        Act('hand.write', named("Write a file in Files through Stacy's hand."), schema_of({'path': path, 'text': S(0, 1000000)}, ('path', 'text')), kernel='files.write'),
        Act('hand.rename', named("Rename a file in Files through Stacy's hand."), schema_of({'path': path, 'name': S(1, 255)}, ('path', 'name')), kernel='files.rename'),
        Act('hand.trash', named("Move a file in Files to the Trash through Stacy's hand; the Trash gives it back."), schema_of({'path': path}, ('path',)), kernel='files.trash'),
        Act('hand.cell', named("Set a number of the selected sheet through Stacy's hand."), schema_of({'cell': S(2, 8), 'value': S(1, 40)}, ('cell', 'value')), kernel='field.set'),
        Act('hand.step', named("Take one of the steps offered for the selected sheet through Stacy's hand; the step's own line decides what it does."),
            schema_of({'n': I(1, 9)}, ('n',)), line_decides=True),
        Act('hand.approve', 'Approve the latest change that waits for you.', schema_of({'by': BY}), forms='PK'),
        Act('hand.undo', named("Take back the latest of Stacy's acts that can be taken back."), schema_of({})),
        Act('hand.dial', named("Set how far Stacy acts by herself: ask first, do and show, or a free hand."), schema_of({'place': E('ask', 'show', 'free')}, ('place',))),
        Act('look.set', 'Choose the appearance (from the next start), the glow, the desk art, the buttons, or less motion.',
            schema_of({'appearance': E('graphite', 'kasandra'), 'glow': E('soft', 'bright', 'neon'), 'art': E('illustrated', 'ascii', 'clean'),
                       'buttons': E('words', 'icons'), 'motion': E('normal', 'reduced')}),
            at_least=('appearance', 'glow', 'art', 'buttons', 'motion')),
        Act('read.desk', 'Read back what the window shows now.',
            schema_of({'part': E('all', 'where', 'field', 'menu', 'files', 'line', 'talk', 'look', 'motion', 'last')})),
    )
    return {act.name: act for act in rows}


ACTS = _acts()


class Refusal(Exception):
    """An act refused, with its code and its words (shown as they are)."""
    def __init__(self, code, words):
        super().__init__(words);self.code = code;self.words = words


REFUSALS = {
    'UNKNOWN_ACT': 'There is no act named “%s”.',
    'BAD_ARGUMENTS': '%s takes %s; it was given %s.',
    'NOT_HERE': 'The Field is not in front.',
    'CHANGES_ROW': named("That row changes something; %s does it through Stacy's hand."),
    'CHANGES_ROW_YOURS': 'That row changes something; it stays yours.',
    'NOT_ALLOWED_ROW': 'That row is not one an act may choose: it changes, asks, leaves or stops work, and stays yours.',
    'NO_SIBLING': 'This sheet has no other revision on the desk.',
    'DIALOG': 'It would open a window that asks, so it was stopped there.',
    'MAKES': 'Opening it would make %s; that stays yours.',
    'UNSEEN': '%s holds a line break or another character that is not seen; the writing line takes one line of words.',
    'UNSENT': 'The writing line holds words you have not sent; they stay.',
    'PENDING': 'An operation waits for your approval in the working area; it stays.',
    'LEAVES_OR_SHELL': 'The Web and the Terminal are yours to send to.',
    'NOTHING_WAITS': 'Nothing waits for your Approve.',
    'NOTHING_TO_UNDO': named("Nothing of Stacy's can be taken back now."),
    'NOT_OFFERED': named('Acts are not offered to Stacy yet.'),
    'FAILED': 'It could not be done: %s',
}

# Her hand's rule for acts, as data (for the export; desk_hers() is the same rule as a function).
HAND_RULE = {'read': 'never asks', 'navigates': {'ask': 'offered', 'show': 'done', 'free': 'done'},
             'changes': named("Stacy's hand decides on the act's Kernel operation; what always asks still asks"), 'owner_only': 'never hers'}


def is_act(name):
    return str(name) in ACTS


def looks_like_act(name):
    """Whether a typed name is meant as an act: its first part is one of the acts' heads (no Kernel operation starts so)."""
    head = str(name or '').split('.', 1)[0]
    return '.' in str(name or '') and head in ACT_HEADS


def schema(name):
    return ACTS[name].schema


def _plain_list(names):
    return ', '.join(names)


def unknown(name):
    """The words for an act that is not there, with the acts that start the same."""
    head = str(name).split('.', 1)[0]
    near = sorted(n for n in ACTS if n.split('.', 1)[0] == head)
    words = REFUSALS['UNKNOWN_ACT'] % str(name)[:80]
    return words + (' Acts that start the same: %s.' % _plain_list(near) if near else '')


def _argument_words(name, key, spec, value):
    """Why one argument does not fit, in words."""
    kind = spec.get('type')
    if 'enum' in spec:return '%s is one of %s.' % (key, _plain_list(spec['enum']))
    if kind == 'integer':
        if isinstance(value, int) and not isinstance(value, bool):return '%s is from %d to %d.' % (key, spec.get('minimum'), spec.get('maximum'))
        return '%s is a whole number.' % key
    if kind == 'string':
        if not isinstance(value, str):return '%s is words.' % key
        return ('%s is too long.' if len(value) > spec.get('maxLength', 10 ** 9) else '%s is too short.') % key
    return '%s does not fit.' % key


def check(name, args):
    """The arguments an act takes, checked: returns them cleaned (a number written where words are wanted becomes its words,
    since the line reads `value=100` as a number), or raises Refusal with words that say what is wrong."""
    if name not in ACTS:raise Refusal('UNKNOWN_ACT', unknown(name))
    act = ACTS[name];props = act.schema['properties']
    if args is None:args = {}
    if not isinstance(args, dict):raise Refusal('BAD_ARGUMENTS', '%s takes its arguments as name=value.' % name)
    extra = [k for k in args if k not in props]
    if extra:
        raise Refusal('BAD_ARGUMENTS', '%s takes %s; it was given %s.' % (name, _plain_list(props) or 'nothing', _plain_list(map(str, extra))))
    clean = {}
    for key, value in args.items():
        spec = props[key]
        if spec.get('type') == 'string' and isinstance(value, (int, float)) and not isinstance(value, bool):value = str(value)
        try:validate(value, spec, key)
        except ValueError:raise Refusal('BAD_ARGUMENTS', _argument_words(name, key, spec, value)) from None
        clean[key] = value
    missing = [k for k in act.schema['required'] if k not in clean]
    if missing:raise Refusal('BAD_ARGUMENTS', '%s needs %s.' % (name, _plain_list(missing)))
    if act.one_of and sum(1 for k in act.one_of if k in clean) != 1:
        raise Refusal('BAD_ARGUMENTS', '%s needs one of %s.' % (name, _plain_list(act.one_of)))
    if act.at_least and not any(k in clean for k in act.at_least):
        raise Refusal('BAD_ARGUMENTS', '%s needs one of %s.' % (name, _plain_list(act.at_least)))
    # A carriage return typed in the writing line is its Return: it would send what type.put says it never sends. A
    # character no one sees could make the line say other than it shows. Neither is put there.
    if name == 'type.put' and unseen(clean['text']):raise Refusal('BAD_ARGUMENTS', REFUSALS['UNSEEN'] % 'text')
    if name == 'sheet.whatif' and not NUMBER.fullmatch(clean['value']):raise Refusal('BAD_ARGUMENTS', 'value is a number.')
    return clean


NUMBER = re.compile(r'-?\d+(?:\.\d+)?')
UNSEEN = ('Cc', 'Cf', 'Cs', 'Co', 'Cn', 'Zl', 'Zp')      # controls, format marks, surrogates, private and unassigned, line and paragraph breaks


def unseen(text):
    """The first character of `text` that is not seen on a line (a control such as a line break, a format mark, a line or
    paragraph separator), or ''."""
    import unicodedata
    return next((ch for ch in str(text) if unicodedata.category(ch) in UNSEEN), '')


def said(envelope):
    """An act's answer in words: what was done, or why it was refused."""
    if not isinstance(envelope, dict):return ''
    if envelope.get('ok'):return str(envelope.get('words') or 'Done.')
    return str((envelope.get('error') or {}).get('words') or envelope.get('words') or 'Refused.')


# -- her hand's rule for acts (written and tested; nothing calls it in this pass) ------------------------------------------------

def desk_hers(place, name, args=None, line=None):
    """(whether this act is hers to do now without asking, why not in words). A read never asks. An act that navigates moves
    the owner's window: at Ask first it is offered, not done; at Do and show and Free hand it is done. A change is her
    hand's rule on its own Kernel operation (stacy_hand.hers), so what always asks still asks; for hand.step the step's line
    names the operation. An act only the owner does is never hers.

    Given its arguments (`args` not None), the act's own rules come first: arguments its check refuses are never hers (a
    line break for type.put), and a right-click row is hers only by its key and only when it is on MENU_ROWS or PANEL_ROWS
    (its words could name any row). What this rule cannot see from the arguments alone, the doer sees on the window: that a
    file hand.write names is already there (it then waits), or that opening Documents would start a document (refused)."""
    if name not in ACTS:return False, 'there is no act by that name'
    act = ACTS[name]
    if act.owner_only:return False, 'only you do this'
    if args is not None:
        try:args = check(name, args)
        except Refusal as refusal:return False, refusal.words
        if name == 'menu.choose':
            # A path is the right-click's rows, or the line panel's (which starts with a step, an ending or Back): the panel's
            # column rows are named "field:" too, so the two lists are never mixed in one path.
            segments = [s.strip() for s in args['path'].split('/') if s.strip()]
            in_menu = bool(segments) and all(listed(s, MENU_ROWS + SCREENS) for s in segments)
            in_panel = bool(segments) and not segments[0].startswith('field:') and all(listed(s, PANEL_ROWS) for s in segments)
            if not (in_menu or in_panel):return False, 'that row is not one I choose by myself'
    why = stacy_hand.why_asks(name, args if isinstance(args, dict) else None)
    if why:return False, why
    if name == 'read.desk':return True, ''
    if act.mark == 'navigates':
        if place in ('show', 'free'):return True, ''
        return False, 'it moves your window, and my hand is at Ask first'
    operation, arguments = act.kernel, dict(args or {})
    if act.line_decides:
        if not line:return False, 'the step has no line to read'
        try:
            from .field_do import call
            operation, arguments = call(line)
        except Exception:  # noqa: BLE001 - a line that cannot be read is never hers to run
            return False, 'the step has no line to read'
    from .engineering_kernel import CAPABILITIES
    scope = CAPABILITIES.get(operation, 'approve')
    if stacy_hand.hers(place, scope, operation, arguments):return True, ''
    return False, stacy_hand.why_waits(place, scope, operation, arguments)


# -- the export, for later: what her model would be offered (nothing offers it now) -----------------------------------------

def offered(act):
    """An act's arguments as her model would be offered them: without `by` (how the hand moves, pointer or keys, is the
    script's and the owner's choice, never hers) and without an empty `required`."""
    properties = {k: v for k, v in act.schema['properties'].items() if k != 'by'}
    out = {'type': 'object', 'properties': properties, 'additionalProperties': False}
    if act.schema['required']:out['required'] = list(act.schema['required'])
    return out


def tools(place='show'):
    """The acts that could one day be offered to her, as tool descriptions: [{name, words, mark, arguments, kernel, asks}]
    (`asks` is her hand's rule for the act at that place, before any arguments are known)."""
    out = []
    for act in ACTS.values():
        if not act.exported:continue
        asks = True if act.line_decides else not desk_hers(place, act.name)[0]
        out.append({'name': act.name, 'words': act.words, 'mark': act.mark, 'arguments': offered(act), 'kernel': act.kernel, 'asks': asks})
    return out


def plan_variants():
    """The acts as a plan's choices: one object per act, keyed `act` (never `operation`, so a plan check can never take an act
    for an operation), its arguments beside it. Flat, so that the 35 choices stay within the plan's 9,000 bytes (wrapped in
    `arguments` they took 10,940); no act has an argument named `act`."""
    out = []
    for act in ACTS.values():
        if not act.exported:continue
        args = offered(act)
        out.append({'type': 'object', 'properties': {'act': {'const': act.name}, **args['properties']}, 'required': ['act'] + args.get('required', []),
                    'additionalProperties': False})
    return out


def compact(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False)


# -- the keys search over the Field's own model -----------------------------------------------------------------------------

WAYS = ('first', 'last', 'left', 'right', 'up', 'down', 'next_waiting')


def _moved(field, start, way):
    """Where one press of a way goes from `start` on this Field (its own moves; the selection is put back after)."""
    keep = field.selected
    try:
        field.selected = start
        if way == 'first':return field.select(field.first())
        if way == 'last':return field.select(field.last())
        if way == 'next_waiting':return field.next_attention()
        return field.move(way)
    finally:
        field.selected = keep


def key_path(field, start, goal):
    """The fewest presses that take the Field's selection from `start` to `goal`: a list of ways (first, last, left, right, up,
    down, next_waiting), [] when it is there, None when no press reaches it. A breadth-first search over field_model.Field's
    own moves, so the keys sent are the keys a person would press."""
    if start == goal:return []
    if field.get(goal) is None:return None
    seen = {start};frontier = [(start, [])]
    while frontier:
        following = []
        for at, path in frontier:
            for way in WAYS:
                there = _moved(field, at, way)
                if there == goal:return path + [way]
                if there and there not in seen:
                    seen.add(there);following.append((there, path + [way]))
        frontier = following
    return None


def row_words(text):
    """A menu row's words as a person reads them: no tab and what follows, no single &, '&&' read as '&', no dots at the end."""
    text = str(text or '').split('\t')[0].replace('&&', '\0').replace('&', '').replace('\0', '&')
    return re.sub(r'\s+', ' ', text).rstrip('….').strip()
