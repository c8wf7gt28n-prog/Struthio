"""Tools and observation receipts: every tool Kasandra may use, and what each of her observations proves (Graphite 1.0, K2).

The owner's paper, section 10 ("Observation receipts and tool awareness") and section 12: a file reader, a calculator, an
application bridge and a window controller each describe what they can do and report in one way. An observation carries
which tool supplied it, which file or window it described, which revision was read and whether it was complete. "Clicked
Save" and "the expected revision exists on disk" are different observations; only the second makes a step done.

THE REGISTRY (TOOLS) is the one list her planner and her model choose from, by number (K4). Each entry says:
  number, key       stable: a number is never moved or reused and a key never renamed (a retired tool keeps its number)
  words             what it does, in plain words
  operations        the Kernel operation(s) it goes through, or `callable`, the Python function where it is not one
  arguments         each with where it may come from: your words, a record at a revision, a source line, a deduction or an
                    earlier step's output; the model's pick only for a read, never for a change, a move of your desktop or a send
  preconditions     what must hold before it is used: unmet() checks them, and a step whose precondition fails is blocked
                    with nothing sent
  effects, undo     what it changes; its undo class (read, navigate, change, send) and how it is undone, in words
  grant             the grant it needs (K3 enforces it at dispatch): none for a read; an operation on a target in a scope
                    for a change; your press each time for a send
  verify            how its effect is verified: a check (assignments.Check) whose verify() returns an observation receipt
  available         whether it can be used on this computer now, and why not
Families: the Kernel's read operations are one entry (1) and the desk acts two (10, 11); the member is named by the
`operation` (for the desk, the `act`). Named slots keep their numbers for the slices still to come: the LibreOffice bridge
(K5), the sandbox (K6), the accessibility reader (K7) and the network fetch (K8). Until a slice fills its slot with fill(),
the slot says "not built yet" as its reason.

RECEIPTS (graphite.receipt/1, in the Kernel's own database: tool_receipts). Every observation is one record: the tool (its
key and number), the operation, the object (files:<path>, office:<sheet>, documents:<page>, windows, window:<id>,
machine:<section>), the revision (a digest, a record's revision, a window list's digest), the place (path, page, sheet and
cell, line, window and its title), complete or partial, observed or inferred (or unavailable, and why), and its status:

  dispatched     the call was sent and came back; its effect is NOT yet verified
  verified       the check saw the effect (the new revision's digest on disk, the cell holding the value, the window gone)
  not verified   sent, and the check did not see it: never called done
  refused        the desk refused the call; nothing happened
  observed       an observation read from a structured interface (a window's title, its program, which is active)
  inferred       what an observation probably means and has not been established ("possibly a Save changes? prompt")
  unavailable    it could not be observed here, with the reason
  changed since  verified once; on a later look it has changed

"Dispatched" and "verified" are two receipts, never one: the second follows the first by its id. Receipts are append-only
and each carries its digest. A step of an assignment (K1) writes its receipts in the same transaction as its journal row
(SENT gives "dispatched"; DONE, FOUND_DONE and STILL_DONE "verified"; NOT_VERIFIED "not verified"), linked by the row's number.

Operations (registered in engineering_kernel under "1.0 K2"; the reads are observers, so showing them is not an event):
  tools.list        {key?, number?, family?, members?}       read     the registry, numbered, with what is available now
  tools.receipts    {assignment?, step?, object?, tool?, ...} read     receipts, newest first
  tools.use         {tool or number, operation?, arguments, origins?, basis?}  execute  one tool through its door: its
                    preconditions, its grant (K3), a sleep lock while it writes a file (S1), the call ("dispatched"), the
                    check ("verified" or "not verified"); a change only the model chose is refused; a send always asks
  windows.observe   {since?}                                  read     the open windows, as receipts (not kept: a look)
  windows.activate  {window}                                  execute  bring a window forward; verified when it is active
  windows.minimise  {window}                                  execute  minimise it; verified when it is minimised
  windows.close     {window}                                  approve  ask it to close, politely; verified when it is gone

No floating point in anything checked: times are whole milliseconds, digests are compared as text.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from . import assignments as _asg

SCHEMA = 'graphite.tools/1'
RECEIPT = 'graphite.receipt/1'
UNDO = ('read', 'navigate', 'change', 'send')
UNDO_WORDS = {'read': 'it only reads: there is nothing to undo',
              'navigate': 'it moves what is shown, never a file or a record',
              'change': 'it changes a file, a record or your desktop: how it is undone is said with it',
              'send': 'it sends something off this computer: that cannot be taken back, so it asks you every time'}
STATUSES = ('dispatched', 'verified', 'not verified', 'refused', 'observed', 'inferred', 'unavailable', 'changed since')
STATUS_WORDS = {'dispatched': 'sent, not yet verified', 'verified': 'verified', 'not verified': 'sent, not verified',
                'refused': 'refused', 'observed': 'observed', 'inferred': 'inferred, not established', 'unavailable': 'unavailable here',
                'changed since': 'verified once, changed since'}
HOW = ('observed', 'inferred', 'unavailable')
CHANGE_FROM = ('OWNER_WORDS', 'RECORD', 'SOURCE', 'DEDUCTION', 'STEP')
READ_FROM = CHANGE_FROM + ('MODEL_PICK',)
FROM_WORDS = {'OWNER_WORDS': 'your words', 'RECORD': 'a record at a revision', 'SOURCE': 'a line of a source', 'DEDUCTION': 'a deduction',
              'STEP': "an earlier step's output", 'MODEL_PICK': "the model's pick"}
PLACE_KEYS = ('path', 'page', 'sheet', 'cell', 'line', 'window', 'title', 'program')
OF_JOURNAL = {'SENT': 'dispatched', 'DONE': 'verified', 'FOUND_DONE': 'verified', 'STILL_DONE': 'verified', 'NOT_VERIFIED': 'not verified',
              'REFUSED': 'refused', 'CHANGED_SINCE': 'changed since', 'CANNOT_TELL': 'not verified', 'NOT_FOUND': 'not verified'}
MAX_RECEIPT = 8192            # bytes of one receipt, canonical
MAX_INFERENCES = 8            # inferred receipts from one look at the windows
APP_WAIT_MS = 8000            # how long an App's window is looked for after it started
WINDOW_WAIT_S = 2             # how long a window action's effect is looked for
GRANT_CHECK = None            # K3 sets it: callable(kernel, tool, operation, arguments, principal) -> '' or why it needs a grant
GRANTED = None                # 1.0 K3 sets it: callable(kernel, tool, operation, arguments, principal) -> the context around the dispatch
ACCESSIBILITY = None          # K7 sets it: callable(window_row) -> {'available', 'reason', 'title', 'text', 'buttons'}
ID = {'type': 'string', 'minLength': 32, 'maxLength': 32}
KEY = {'type': 'string', 'minLength': 1, 'maxLength': 64}
WINDOW = {'type': 'string', 'minLength': 3, 'maxLength': 20}

# What a window's title says, read as a hint only: a title is observed, what it means is inferred.
SAVE_PROMPT = re.compile(r'save (the |your )?changes|unsaved|do you want to save|save before|keep (the )?current format|discard changes'
                         r'|close without saving|not (been )?saved|has been modified|changes will be lost|save document', re.I)
ERROR_PROMPT = re.compile(r'\berror\b|\bfailed\b|\bcannot\b|\bcan\'t\b|could not|\bwarning\b|not responding|\bcrash', re.I)


class Refused(ValueError):
    """A tool's door refused the use: nothing was sent."""


# ---------------------------------------------------------------- the registry

@dataclass(frozen=True)
class Arg:
    name: str
    words: str
    comes_from: tuple = CHANGE_FROM
    required: bool = True


@dataclass
class Tool:
    number: int
    key: str
    words: str
    family: str
    undo: str
    operations: tuple = ()
    callable: str = ''
    arguments: tuple = ()
    preconditions: tuple = ()
    effects: str = ''
    undone: str = ''
    grant: str = ''
    target: str = ''              # the argument naming its target, for K3 ('path', 'window', 'id', ...)
    verify: str = ''
    writes_files: bool = False
    slice: str = ''               # the slice that fills this slot ('K5' ...); '' when it is built
    filled: dict = field(default_factory=dict)

    @property
    def model_may(self):
        """Whether the model's pick alone may be why it is used: a read, or a move of what Graphite's own window shows (as
        0.8.7's table of what a reading may do); never a change, a move of your program windows or a send."""
        return self.undo == 'read' or (self.undo == 'navigate' and self.family == 'desk')


def _tools():
    path = Arg('path', 'the path inside Files')
    rows = (
        Tool(1, 'kernel.read', "Read a record through the Kernel: a sheet, a page, a finding, a source, the board, the Agenda, by any of "
             "its registered reads.", 'kernel', 'read', callable='', arguments=(
                 Arg('operation', 'which read (one of the members)', READ_FROM), Arg('arguments', 'its arguments, as that read takes them', READ_FROM)),
             preconditions=('it is a registered read of the Kernel', "it is not one of her own controls (assignments, the Night Shift's orders)"),
             effects='nothing: a read', undone='nothing to undo', verify='read again: the same revision (or the same values)'),
        Tool(2, 'files.read', 'Read a file in Files: its kind, its text or its table, at the digest it has on disk.', 'files', 'read',
             ('files.get',), arguments=(Arg('path', 'the path inside Files', READ_FROM),),
             preconditions=('the file is there, inside Files',), effects='nothing: a read', undone='nothing to undo',
             verify='its digest on disk is the same before and after the read'),
        Tool(3, 'files.write.new', 'Write a new file in Files, holding the text given.', 'files', 'change', ('files.write',),
             arguments=(path, Arg('text', 'the text it holds')),
             preconditions=('the path is inside Files', 'nothing is there yet (a file already holding exactly this text is recorded, not '
                                                        'written again)', 'her hand may write there (her own area, or your grant)'),
             effects='a new file', undone='Delete it (DELETE gives it back)', grant='write a new file in the folder', target='path',
             verify='the file on disk has the digest of the text prepared for it', writes_files=True),
        Tool(4, 'files.write.revision', 'Save a new revision of a file in Files: the text given replaces its text, and the revision '
             'before is kept.', 'files', 'change', ('files.write',), arguments=(path, Arg('text', 'its new text')),
             preconditions=('the file is there', 'it is still at the revision the plan read, when its origin names one',
                            'her hand may change it (her own area, or your grant)'),
             effects='a new revision of the file; the one before kept as a version', undone='Revert to the kept version (yours to press)',
             grant='change a file in the folder', target='path',
             verify="the file on disk has the digest of the new text (the new revision's digest is on disk)", writes_files=True),
        Tool(5, 'files.rename', 'Rename a file or a folder in Files; it keeps its identity.', 'files', 'change', ('files.rename',),
             arguments=(path, Arg('name', 'its new name')),
             preconditions=('it is there', 'the new name is free in its folder', "it is not Graphite's own area or Egress"),
             effects='the same file under a new name; its object id goes with it', undone='Rename it back',
             grant='rename files in the folder', target='path',
             verify='the new name holds the same content (digest) and the old name is gone', writes_files=True),
        Tool(6, 'files.move', 'Move a file or a folder into another folder of Files; it keeps its identity.', 'files', 'change',
             ('files.move',), arguments=(path, Arg('to', 'the folder it goes into')),
             preconditions=('it is there', 'the folder is there', 'it does not go into itself', "it is not Graphite's own area or Egress"),
             effects='the same file in another folder (a taken name gets a number); its object id goes with it',
             undone='Move it back', grant='move files out of the folder and into the other', target='path',
             verify='the same content (digest) is in the folder and gone from where it was', writes_files=True),
        Tool(7, 'files.folder.new', 'Make a folder in Files.', 'files', 'change', ('files.mkdir',),
             arguments=(Arg('path', 'the folder it goes in (empty: the top of Files)', required=False), Arg('name', 'its name')),
             preconditions=('the folder it goes in is there', 'the name is free there'), effects='a new, empty folder',
             undone='Delete it (DELETE gives it back)', grant='make folders in the folder', target='path', verify='the folder is there',
             writes_files=True),
        Tool(8, 'calculation.recheck', 'Work a calculation page again from its sheet as it is now: a new page replaces the old one.',
             'calculation', 'change', ('office.datasheet.recheck',),
             arguments=(Arg('id', 'the calculation page', ('RECORD', 'DEDUCTION', 'STEP')), Arg('expected_revision', 'its revision as read', ('RECORD', 'STEP'))),
             preconditions=('the page is at the revision the plan names', 'it was not worked again already'),
             effects='a new calculation page, worked from the sheet as it is now, replacing the old one',
             undone='the old page stays; the new one can be deleted', grant='work a calculation again (the records mark it for your approval)',
             target='id', verify='a new page replaces the old one, worked from the sheet as it is now, with an exact result'),
        Tool(9, 'sheet.set', 'Set a value in a cell of a sheet.', 'calculation', 'change', ('field.set',),
             arguments=(Arg('id', 'the sheet', ('RECORD', 'DEDUCTION', 'STEP')), Arg('cell', 'the cell'), Arg('value', 'the value')),
             preconditions=('the sheet is at the revision the plan read, when one is given',), effects='a value set in a cell',
             undone="her hand's Undo puts the value back", grant='set values on the sheet', target='id',
             verify='the sheet, read again, holds the value in that cell'),
        Tool(10, 'desk.navigate', "Move what Graphite's window shows: open, select, zoom, read back (a desk act).", 'desk', 'navigate',
             callable='workbench.desk_doers:run', arguments=(Arg('act', 'which act (one of the members)', READ_FROM),
                                                            Arg('arguments', 'its arguments', READ_FROM)),
             preconditions=("Graphite's window is open, in her hand's turn", 'the act is hers to do at the dial (desk_acts.desk_hers)'),
             effects='what the window shows', undone='go back, or put the window back as it was', grant='move your window (the dial)',
             verify='read back what the window shows (read.desk)'),
        Tool(11, 'desk.change', "A change through her hand on the window: write, rename or delete a file, set a cell, take a step.",
             'desk', 'change', ('files.write', 'files.rename', 'files.trash', 'field.set'), callable='workbench.desk_doers:run',
             arguments=(Arg('act', 'which act (one of the members)'), Arg('arguments', 'its arguments')),
             preconditions=("Graphite's window is open, in her hand's turn", 'the act is hers to do at the dial (desk_acts.desk_hers)'),
             effects="the act's Kernel operation's effect", undone="her hand's Undo, where the act has one",
             grant="the grant of the act's own operation", target='path',
             verify="the check of the act's own operation (as the file and sheet tools)"),
        Tool(12, 'windows.observe', 'See the open program windows: their titles and programs, which is active, and the windows and '
             'dialogs that appeared since the last look.', 'windows', 'read', ('windows.observe',), callable='workbench.windows_x11:observe',
             arguments=(Arg('since', 'the last look (its sequence number)', READ_FROM, required=False),),
             preconditions=('this computer has a window list (X11)',), effects='nothing: a look', undone='nothing to undo',
             verify="it is itself an observation of the windows' X11 properties; what a dialog's title means is marked inferred"),
        Tool(13, 'windows.activate', 'Bring a program window forward.', 'windows', 'navigate', ('windows.activate',),
             callable='workbench.windows_x11:Watcher.activate', arguments=(Arg('window', 'the window, as the last look named it'),),
             preconditions=('this computer has a window list', 'the window is open now'), effects='the window is the active one',
             undone='bring the one before forward again', grant='bring program windows forward', target='window',
             verify='a fresh look shows it active'),
        Tool(14, 'windows.minimise', 'Minimise a program window.', 'windows', 'navigate', ('windows.minimise',),
             callable='workbench.windows_x11:Watcher.minimise', arguments=(Arg('window', 'the window, as the last look named it'),),
             preconditions=('this computer has a window list', 'the window is open now'), effects='the window is minimised',
             undone='bring it forward again', grant='minimise program windows', target='window', verify='a fresh look shows it minimised'),
        Tool(15, 'windows.close', 'Ask a program window to close, politely: the program may ask to save; nothing is ever forced.',
             'windows', 'change', ('windows.close',), callable='workbench.windows_x11:Watcher.close',
             arguments=(Arg('window', 'the window, as the last look named it'),),
             preconditions=('this computer has a window list', 'the window is open now', 'its program takes a polite close'),
             effects='the window closes (its program may ask first)', undone='Graphite cannot undo it: open the program again',
             grant='close program windows (the records mark it for your approval)', target='window',
             verify='a fresh look no longer lists it'),
        Tool(16, 'apps.open', 'Open one of the Apps, with files when it takes them.', 'apps', 'change', ('apps.open',),
             arguments=(Arg('id', 'the App'), Arg('files', 'whole paths of the files it opens', required=False)),
             preconditions=('the App is installed here', 'the files are there'), effects='a program of yours starts, in a session of its own',
             undone='close its window: it is a program of yours from then on', grant='open the App', target='id',
             verify="a window of the program appears in the window list (with no window list: its process runs, a partial receipt)"),
        Tool(17, 'machine.state', "Read this computer's storage, power, network, sound and screens.", 'machine', 'read', ('machine.state',),
             arguments=(Arg('section', 'one section (empty: all)', READ_FROM, required=False),), preconditions=(),
             effects='nothing: a read', undone='nothing to undo', verify='read now through its own services; each section says available, or why not'),
        Tool(18, 'office.read', "Read a Writer document or a Calc sheet through LibreOffice's own interface: its paragraphs, its cells.",
             'office', 'read', arguments=(Arg('path', 'the document in Files', READ_FROM),), preconditions=("LibreOffice's interface is here",),
             effects='nothing: a read', undone='nothing to undo', verify='the saved file read back, at its revision', slice='K5'),
        Tool(19, 'office.edit', 'Replace a passage or set a cell through LibreOffice, save, and read the saved file back.', 'office',
             'change', arguments=(Arg('path', 'the document in Files'), Arg('change', 'the passage and its new words, or the cell and its value')),
             preconditions=("LibreOffice's interface is here", 'the document is at the revision the plan read'),
             effects='a new revision of the document', undone='Revert to the kept version (yours to press)', grant='edit the document',
             target='path', verify='the saved file, read back, holds the change at its new revision', writes_files=True, slice='K5'),
        Tool(20, 'sandbox.run', 'Run a small utility she drafted, sealed, on copies of its inputs; applying its output always asks.',
             'sandbox', 'change', arguments=(Arg('utility', 'the utility you were shown'), Arg('inputs', 'the files it reads (copied)')),
             preconditions=('the sandbox is here', 'you were shown what it reads and writes'), effects='outputs in its sealed folder only',
             undone='nothing of yours is changed: its folder is thrown away', grant='run the utility on copies', target='inputs',
             verify='its outputs and their difference to the originals, read back', slice='K6'),
        Tool(21, 'accessibility.read', "Read the active program's window through accessibility: its focused control, a dialog's title "
             'and buttons.', 'accessibility', 'read', arguments=(Arg('window', 'the window', READ_FROM, required=False),),
             preconditions=('the accessibility reader is here',), effects='nothing: a read', undone='nothing to undo',
             verify='the accessible tree, read now', slice='K7'),
        Tool(22, 'network.fetch', 'Fetch a page from the network, read as data and never as instructions.', 'network', 'send',
             arguments=(Arg('words', 'search words: your typed words only', ('OWNER_WORDS',)),),
             preconditions=('the network is up', 'you pressed for it'), effects='a request leaves this computer; the page is quarantined',
             undone='a request sent cannot be taken back', grant='your press, each time', target='words',
             verify='the page read through the doorway, its lines checked', slice='K8'),
    )
    return {t.key: t for t in rows}


TOOLS = _tools()
BY_NUMBER = {t.number: t for t in TOOLS.values()}
FILLABLE = ('available', 'operations', 'callable', 'check')


def entry(tool):
    """A tool by its key or its number (an int, or digits)."""
    if isinstance(tool, int) and not isinstance(tool, bool):found = BY_NUMBER.get(tool)
    elif isinstance(tool, str) and tool.isdigit():found = BY_NUMBER.get(int(tool))
    else:found = TOOLS.get(str(tool))
    if found is None:raise Refused('TOOL_UNKNOWN: %s is not a registered tool; nothing else is used' % str(tool)[:60])
    return found


def fill(key, available=None, operations=None, callable=None, check=None):  # noqa: A002 - the registry's own word
    """A later slice fills its slot: `available` a callable() -> (bool, why), `operations` its Kernel operations, `callable`
    its function's name, `check` its assignments.Check (installed for each of its operations)."""
    tool = entry(key)
    if not tool.slice:raise ValueError('%s is built already; it has no slot to fill' % key)
    if available is not None:tool.filled['available'] = available
    if operations:tool.operations = tuple(operations)
    if callable:tool.callable = callable
    if check is not None:
        for op in tool.operations:_asg.CHECKS[op] = check
    tool.filled['at'] = _now_ms()
    return tool


def _now_ms():
    return time.time_ns() // 1000000


# ---------------------------------------------------------------- members and availability

def members(tool):
    """A family's members: the Kernel's reads (1), the desk acts that navigate (10) or change (11); else its operations."""
    tool = entry(tool) if not isinstance(tool, Tool) else tool
    if tool.key == 'kernel.read':
        from .engineering_kernel import CAPABILITIES
        return sorted(op for op, scope in CAPABILITIES.items() if scope == 'read' and not op.startswith(_asg.NOT_HERE))
    if tool.family == 'desk':
        from . import desk_acts
        mark = 'navigates' if tool.undo == 'navigate' else 'changes'
        return [a.name for a in desk_acts.ACTS.values() if a.exported and a.mark == mark]
    return list(tool.operations)


_DESK = []


def set_desk(host):
    """The window says it is open (desk acts can be done on it, in her hand's turn); None when it closes."""
    import weakref
    _DESK.clear()
    if host is not None:_DESK.append(weakref.ref(host))


def available(tool):
    """(whether the tool can be used on this computer now, why not in words)."""
    tool = entry(tool) if not isinstance(tool, Tool) else tool
    if tool.slice:
        check = tool.filled.get('available')
        if check is None:
            if tool.filled and (tool.operations or tool.callable):return True, ''
            return False, 'not built yet: slice %s is not in this Graphite' % tool.slice
        try:return check()
        except Exception as exc:  # noqa: BLE001 - a slot that cannot say is not available, with the reason
            return False, 'it could not tell (%s)' % str(exc)[:160]
    if tool.family == 'desk':
        host = _DESK[0]() if _DESK else None
        if host is None:return False, "Graphite's window is not open in this process: a desk act is done on the window, in her hand's turn"
        return True, ''
    if tool.family == 'windows':
        try:
            from . import windows_x11
            state = windows_x11.status()
        except Exception as exc:  # noqa: BLE001
            return False, 'no window list on this computer: %s' % str(exc)[:160]
        return bool(state.get('available')), state.get('reason') or ''
    if tool.family == 'apps':
        try:
            from . import apps_catalog  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            return False, 'the Apps catalogue cannot be read here: %s' % str(exc)[:160]
    return True, ''


def view(tool, with_members=False, kernel=None):
    """One entry as the planner, the model and the window read it."""
    tool = entry(tool) if not isinstance(tool, Tool) else tool
    ok, why = available(tool)
    out = {'number': tool.number, 'key': tool.key, 'words': tool.words, 'family': tool.family, 'undo': tool.undo,
           'undo_words': UNDO_WORDS[tool.undo], 'undone': tool.undone, 'operations': list(tool.operations), 'callable': tool.callable,
           'arguments': [{'name': a.name, 'words': a.words, 'required': a.required, 'from': list(a.comes_from),
                          'from_words': ', '.join(FROM_WORDS[k] for k in a.comes_from)} for a in tool.arguments],
           'model_alone': tool.model_may, 'preconditions': list(tool.preconditions), 'effects': tool.effects,
           'grant': grant_of(tool), 'verify': tool.verify, 'available': ok, 'why_not': '' if ok else why, 'slice': tool.slice,
           'family_of': len(members(tool)) if tool.key in ('kernel.read', 'desk.navigate', 'desk.change') else None}
    if with_members:out['members'] = members(tool)
    return out


def grant_of(tool, arguments=None):
    """The grant a tool needs, for K3: {'needs': 'none' | 'grant' | 'your press', 'operation', 'target', 'scope', 'words'}."""
    tool = entry(tool) if not isinstance(tool, Tool) else tool
    if tool.undo == 'read':return {'needs': 'none', 'words': 'none: reading needs no grant'}
    if tool.undo == 'send':return {'needs': 'your press', 'operations': list(tool.operations), 'words': 'your press, each time: ' + tool.grant}
    target = ''
    if isinstance(arguments, dict) and isinstance(arguments.get(tool.target), str):
        value = arguments[tool.target]
        target = ('files:' + (value.rsplit('/', 1)[0] + '/' if '/' in value else '')) if tool.target == 'path' else '%s:%s' % (tool.target, value)
    return {'needs': 'grant', 'operations': list(tool.operations), 'target_from': tool.target, 'target': target,
            'scope': 'this assignment', 'words': tool.grant}


def menu(undo=None):
    """The numbered list her planner and her model choose from: [{n, key, words, undo, arguments: {name: [from]}, available}]."""
    out = []
    for tool in sorted(TOOLS.values(), key=lambda t: t.number):
        if undo and tool.undo not in undo:continue
        ok, why = available(tool)
        out.append({'n': tool.number, 'key': tool.key, 'words': tool.words, 'undo': tool.undo,
                    'arguments': {a.name: list(a.comes_from) for a in tool.arguments}, 'available': ok, 'why_not': '' if ok else why})
    return out


KEY_OF = {'files.get': 'files.read', 'files.rename': 'files.rename', 'files.move': 'files.move', 'files.mkdir': 'files.folder.new',
          'office.datasheet.recheck': 'calculation.recheck', 'field.set': 'sheet.set', 'windows.observe': 'windows.observe',
          'windows.activate': 'windows.activate', 'windows.minimise': 'windows.minimise', 'windows.close': 'windows.close',
          'apps.open': 'apps.open', 'machine.state': 'machine.state'}


def key_for(operation, step=None, prepared=None):
    """The registry's key for a Kernel operation (and a step's own tool_key, when it names one)."""
    if step and step.get('tool_key'):return step['tool_key']
    if operation == 'files.write':return 'files.write.new' if (prepared or {}).get('before') is None and prepared is not None else 'files.write.revision'
    if operation in KEY_OF:return KEY_OF[operation]
    for tool in TOOLS.values():
        if tool.slice and operation in tool.operations:return tool.key
    from .engineering_kernel import CAPABILITIES
    return 'kernel.read' if CAPABILITIES.get(operation) == 'read' else 'unregistered'


def as_step(tool, arguments, origins=None, operation=None, title=None, basis='owner_words', outputs=None, require=None, expected=None, key=None):
    """A step of an assignment (K1's assignment.start / .plan) for a tool of the registry. Every argument says where it came
    from (or reads an earlier step); for a change, never the model alone."""
    tool = entry(tool)
    op = _operation(tool, operation)
    _origins_hold(tool, arguments, origins or {}, basis)
    source = {'operation': op, 'arguments': arguments, 'origins': {k: v for k, v in (origins or {}).items() if k in arguments},
              'tool_key': tool.key, 'basis': basis}
    for name, value in (('key', key), ('title', title), ('outputs', outputs), ('require', require), ('expected', expected)):
        if value is not None:source[name] = value
    return source


def _operation(tool, operation):
    if tool.key == 'kernel.read':
        if operation not in members(tool):raise Refused('TOOL_MEMBER: %s is not a registered read' % str(operation)[:80])
        return operation
    if tool.family == 'desk':raise Refused("TOOL_DESK: a desk act is done on the window, in her hand's turn, never as a step")
    if not tool.operations:raise Refused('TOOL_UNAVAILABLE: %s is %s' % (tool.key, available(tool)[1]))
    if operation is not None and operation not in tool.operations:raise Refused('TOOL_MEMBER: %s does not go through %s' % (tool.key, operation))
    return operation or tool.operations[0]


def _origins_hold(tool, arguments, origins, basis, in_plan=True):
    """Every argument of a change says where it came from, from a place this tool allows; the model's pick alone is never
    the basis of a change, a move of your desktop or a send."""
    from . import stacy_hand
    if not isinstance(arguments, dict):raise Refused('TOOL_ARGUMENTS: arguments are named')
    if basis not in stacy_hand.BASES:raise Refused('TOOL_BASIS: %s is not why a tool is used' % str(basis)[:40])
    strict = not tool.model_may
    if strict and basis == stacy_hand.MODEL_PICK:raise Refused('TOOL_MODEL_PICK: ' + stacy_hand.MODEL_PICK_WHY)
    allowed = {a.name: a for a in tool.arguments}
    for name, value in arguments.items():
        if in_plan and _asg._references(value):
            if 'STEP' not in (allowed[name].comes_from if name in allowed else CHANGE_FROM):
                raise Refused('TOOL_ORIGIN: %s cannot come from an earlier step' % name)
            continue
        given = origins.get(name)
        if given is None:
            if strict:raise stacy_hand.NoOrigin('ORIGIN_MISSING: %s does not say where it came from' % name)
            continue
        checked = stacy_hand.origin(given.get('kind'), **{k: v for k, v in given.items() if k != 'kind'})
        if name in allowed and checked['kind'] not in allowed[name].comes_from:
            raise Refused('TOOL_ORIGIN: %s of %s comes from %s, never from %s' % (name, tool.key, ', '.join(FROM_WORDS[k] for k in allowed[name].comes_from),
                                                                              FROM_WORDS.get(checked['kind'], checked['kind'])))


# ---------------------------------------------------------------- preconditions

def _inside(kernel, rel, must_exist=False):
    from . import files_service
    return files_service.resolve(kernel, rel or '', must_exist=must_exist)


def file_sha(path):
    if not path.is_file():return None
    sha = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):sha.update(block)
    return sha.hexdigest()


def tree_digest(path, limit=4000):
    """A file's sha256, or a folder's: the digest of its files' relative paths and digests (at most `limit` files)."""
    if path.is_file():return file_sha(path)
    if not path.is_dir():return None
    rows = []
    for n, item in enumerate(sorted(p for p in path.rglob('*') if p.is_file() and not p.is_symlink())):
        if n >= limit:rows.append(['…', 'more']);break
        rows.append([item.relative_to(path).as_posix(), file_sha(item)])
    return _asg.digest({'folder': rows})


def _revision_named(origins, name, rel):
    """The revision a file's origin names (a RECORD of files:<path> at a revision), or None."""
    origin = (origins or {}).get(name) or {}
    if origin.get('kind') == 'RECORD' and str(origin.get('id')) in ('files:' + str(rel), str(rel)):return str(origin.get('rev'))
    return None


def _pre_files(kernel, tool, a, origins):
    from . import files_service
    unmet = []
    if tool.undo == 'change':  # 1.0 L6: her changes reach only inside your home, at every place of the dial
        from . import home_reach
        never = home_reach.never_words(kernel, (tool.operations or ('',))[0], a)
        if never:return [never]
    try:path = _inside(kernel, a.get('path'))
    except ValueError as why:return ['the path is not inside Files (%s)' % str(why)[:120]]
    rel = a.get('path') or ''
    if tool.key == 'files.read':
        if not path.is_file():unmet.append('the file %s is not there' % rel)
    elif tool.key in ('files.write.new', 'files.write.revision'):
        if path.is_dir():unmet.append('%s is a folder' % rel)
        elif tool.key == 'files.write.new' and path.exists():
            text = a.get('text')
            if not (isinstance(text, str) and file_sha(path) == hashlib.sha256(text.encode('utf-8')).hexdigest()):
                unmet.append('a file is already there at %s: saving over it is a new revision, not a new file' % rel)
        elif tool.key == 'files.write.revision':
            if not path.is_file():unmet.append('the file %s is not there: a new file is another tool' % rel)
            else:
                named = _revision_named(origins, 'path', rel)
                if named and file_sha(path) != named:
                    unmet.append('the file is no longer at the revision the plan read (%s); it changed since' % named[:12])
    elif tool.key in ('files.rename', 'files.move'):
        if not path.exists():unmet.append('%s is not there' % rel)
        elif path in (files_service.root(kernel) / files_service.SLATE, files_service.root(kernel) / files_service.EXPORTS):
            unmet.append("Graphite's own area and Egress stay where they are, as they are")
        if tool.key == 'files.rename':
            try:target = path.with_name(files_service.clean_name(a.get('name') or ''))
            except ValueError:unmet.append('the new name cannot be used')
            else:
                if target.exists() and target != path:unmet.append('the name %s is taken in its folder' % target.name)
        else:
            try:folder = _inside(kernel, a.get('to'))
            except ValueError as why:unmet.append('the folder is not inside Files (%s)' % str(why)[:120])
            else:
                if not folder.is_dir():unmet.append('the folder %s is not there' % a.get('to'))
                elif path.is_dir() and (folder == path or path in folder.parents):unmet.append('a folder does not go into itself')
    elif tool.key == 'files.folder.new':
        if not path.is_dir():unmet.append('the folder %s is not there' % (rel or 'Files'))
        else:
            try:target = path / files_service.clean_name(a.get('name') or '')
            except ValueError:unmet.append('the name cannot be used')
            else:
                if target.exists() and not target.is_dir():unmet.append('a file is already called %s there' % target.name)
    return unmet


def _pre_windows(kernel, tool, a, origins):
    from . import windows_x11
    watcher = windows_x11.shared()
    if not watcher.start():return [watcher.reason or windows_x11.NO_LIST]
    if tool.key == 'windows.observe':return []
    try:wid = int(str(a.get('window')), 16)
    except ValueError:return ['%s does not name a window' % str(a.get('window'))[:30]]
    watcher.refresh();row = watcher.row(wid)
    if row is None:return ['the window %s is not open now' % a.get('window')]
    if tool.key == 'windows.close' and 'WM_DELETE_WINDOW' not in (row.get('protocols') or ()):
        return ['%s does not take a polite close, and Graphite never forces one' % (row.get('program') or 'its program')]
    return []


def _pre_apps(kernel, tool, a, origins):
    from . import apps_catalog
    app = apps_catalog.find_app(a.get('id'))
    if app is None:return ['%s is not installed here' % str(a.get('id'))[:120]]
    unmet = [] if app.available else [app.reason or '%s cannot be started here' % app.name]
    for f in a.get('files') or ():
        if not (os.path.isabs(f) and os.path.exists(f)):unmet.append('%s is not there' % f)
    return unmet


def _pre_read(kernel, tool, a, origins, operation=None):
    from .engineering_kernel import CAPABILITIES
    if operation and CAPABILITIES.get(operation) != 'read':return ['%s is not a registered read' % operation]
    if operation and operation.startswith(_asg.NOT_HERE):return ['%s is one of her own controls, never a read of hers' % operation]
    return []


def unmet(kernel, tool, arguments, origins=None, operation=None):
    """The preconditions of using `tool` with these arguments that do not hold now, in words ([] when all hold)."""
    tool = entry(tool) if not isinstance(tool, Tool) else tool
    if tool.slice and not tool.filled:return [available(tool)[1]]
    if tool.family == 'files':return _pre_files(kernel, tool, arguments, origins)
    if tool.family == 'windows':return _pre_windows(kernel, tool, arguments, origins)
    if tool.family == 'apps':return _pre_apps(kernel, tool, arguments, origins)
    if tool.key == 'kernel.read':return _pre_read(kernel, tool, arguments, origins, operation)
    return []


def step_unmet(kernel, step, arguments):
    """K1's hook: the preconditions of a step's tool, in words, '' when they hold. The step's tool is its tool_key, else the
    registry's tool for its operation (files.write without a key: only what holds for both, new or revision)."""
    origins = {name: (given.get('origin') or {}) for name, given in (step.get('inputs') or {}).items()}
    key = step.get('tool_key') or key_for(step['operation'])
    if key == 'unregistered':return ''
    tool = entry(key)
    if step['operation'] == 'files.write' and not step.get('tool_key'):
        found = _pre_files(kernel, entry('files.write.revision'), arguments, origins) if _revision_named(origins, 'path', arguments.get('path')) else \
            [u for u in _pre_files(kernel, entry('files.write.new'), arguments, origins) if 'already there' not in u]
    else:
        found = unmet(kernel, tool, arguments, origins, step['operation'])
    return '; '.join(found)


@contextlib.contextmanager
def holding(operation, why):
    """While a tool writes a file: logind's delay lock on sleep (S1), so a suspend never lands mid-write. Nothing otherwise."""
    if operation not in WRITES_FILES:
        yield False;return
    try:
        from .session_power import sleep_held
    except Exception:  # noqa: BLE001 - without S1's inhibitor the write is not held up for it
        yield False;return
    with sleep_held('Kasandra is writing: %s' % str(why)[:80]) as held:
        yield held


WRITES_FILES = frozenset(op for t in TOOLS.values() if t.writes_files for op in t.operations) | {
    'files.cells', 'files.copy', 'files.trash', 'files.restore', 'files.revert'}


# ---------------------------------------------------------------- checks of an effect (assignments.CHECKS, widened)

class FileWrite(_asg.FileWrite):
    """files.write: a new file, or a new revision with the one before kept; done when the digest is on disk."""
    how = "the file on disk has the digest of the text prepared for it (a new revision: the new revision's digest is on disk)"

    @staticmethod
    def _observed(prepared, sha):
        before = prepared.get('before')
        what = 'a new file' if before is None else ('it already held exactly this text' if before == sha else 'a new revision')
        return {'object': 'files:' + prepared['path'], 'revision': sha, 'by': 'sha256', 'complete': True, 'how': 'observed',
                'path': prepared['path'], 'new': before is None, 'words': '%s: the file on disk has the digest %s' % (what, sha[:12])}

    def find(self, kernel, read, arguments, prepared):
        now = _asg._file_sha(kernel, prepared['path'])
        return self._observed(prepared, now) if now == prepared['sha256'] else None

    def verify(self, kernel, read, arguments, result, prepared, step):
        found = self.find(kernel, read, arguments, prepared)
        if not found:raise _asg.NotVerified('the file on disk does not hold the prepared text')
        kept = (result or {}).get('kept_version')
        if kept:found.update(kept_version=kept, words=found['words'] + '; the one before is kept as version %s' % kept[:15])
        return found


class FileRead(_asg.Check):
    """files.get: a read of a file; its digest on disk the same before and after."""
    kind = 'file';effect = 'nothing (a read)';standin_ms = 1000;repeatable = True
    how = 'its digest on disk is the same before and after the read'
    expected = 'the file, read at the digest it has on disk'

    def prepare(self, kernel, read, arguments):
        sha = file_sha(_inside(kernel, arguments['path']))
        if sha is None:raise _asg.Blocked('the file %s is not there' % arguments['path'])
        return {'path': arguments['path'], 'sha256': sha}

    def find(self, kernel, read, arguments, prepared):
        return None

    def verify(self, kernel, read, arguments, result, prepared, step):
        now = file_sha(_inside(kernel, prepared['path']))
        if now != prepared['sha256']:raise _asg.NotVerified('the file changed while it was read')
        summary = ((result or {}).get('view') or {}).get('summary')
        complete = not (isinstance(summary, str) and summary.startswith('Not readable'))
        return {'object': 'files:' + prepared['path'], 'revision': now, 'by': 'sha256', 'complete': complete, 'how': 'observed',
                'path': prepared['path'], 'words': 'read at the digest %s%s' % (now[:12], '' if complete else ', partly: ' + summary[:120])}

    def still(self, kernel, read, step):
        now = file_sha(_inside(kernel, step['prepared']['path']))
        return '' if now == (step['observation'] or {}).get('revision') else ('it has changed since it was read' if now else 'it is no longer there')


class Relocate(_asg.Check):
    """files.rename and files.move: the same content (digest) at the new place, and nothing left at the old one."""
    kind = 'file';standin_ms = 1000;repeatable = True

    def __init__(self, operation):
        self.operation = operation
        self.effect = 'a file renamed' if operation == 'files.rename' else 'a file moved'
        self.how = 'the %s holds the same content (digest) and the old place is empty' % ('new name' if operation == 'files.rename' else 'folder')
        self.expected = 'the same file under its new name' if operation == 'files.rename' else 'the same file in the folder'

    def prepare(self, kernel, read, arguments):
        from . import files_service
        source = _inside(kernel, arguments['path'])
        if not source.exists():raise _asg.Blocked('%s is not there' % arguments['path'])
        out = {'path': arguments['path'], 'digest': tree_digest(source), 'folder': source.is_dir(), 'name': source.name}
        if self.operation == 'files.rename':
            target = source.with_name(files_service.clean_name(arguments['name']))
            out['to'] = files_service.place_of(kernel, target)  # 1.0 L6: in your home, its whole path
        else:
            out['into'] = arguments['to']
        return out

    def _candidates(self, kernel, prepared):
        if 'to' in prepared:return [_inside(kernel, prepared['to'])]
        folder = _inside(kernel, prepared['into']);stem, suffix = Path(prepared['name']).stem, Path(prepared['name']).suffix
        if prepared['folder']:stem, suffix = prepared['name'], ''
        return [folder / prepared['name']] + [folder / ('%s %d%s' % (stem, n, suffix)) for n in range(2, 60)]

    def _observed(self, kernel, prepared, target):
        from . import files_service
        rel = files_service.place_of(kernel, target)  # 1.0 L6
        ident = ''
        try:
            from . import living_nav
            ident = living_nav.get(kernel, path=rel)['id']
        except Exception:  # noqa: BLE001 - the receipt stands without the object id
            ident = ''
        return {'object': 'files:' + rel, 'revision': prepared['digest'], 'by': 'sha256', 'complete': True, 'how': 'observed', 'path': rel,
                'was': prepared['path'], 'id': ident,
                'words': '%s is now %s, the same content (digest %s); nothing is left at the old place' % (prepared['path'], rel, prepared['digest'][:12])}

    def find(self, kernel, read, arguments, prepared):
        if _inside(kernel, prepared['path']).exists():return None
        for target in self._candidates(kernel, prepared):
            if target.exists() and tree_digest(target) == prepared['digest']:return self._observed(kernel, prepared, target)
        return None

    def verify(self, kernel, read, arguments, result, prepared, step):
        made = (result or {}).get('path')
        if isinstance(made, str):
            target = _inside(kernel, made)
            if target.exists() and tree_digest(target) == prepared['digest'] and not _inside(kernel, prepared['path']).exists():
                return self._observed(kernel, prepared, target)
        found = self.find(kernel, read, arguments, prepared)
        if not found:raise _asg.NotVerified('the same content is not at the new place, or something is left at the old one')
        return found

    def still(self, kernel, read, step):
        obs = step['observation'] or {}
        target = _inside(kernel, obs.get('path', ''))
        if not target.exists():return 'it is no longer at %s' % obs.get('path')
        return '' if tree_digest(target) == obs.get('revision') else 'it has changed since'


class FolderMake(_asg.Check):
    """files.mkdir: the folder is there."""
    kind = 'folder';effect = 'a folder made';standin_ms = 500;repeatable = True
    how = 'the folder is there';expected = 'the folder, there'

    def prepare(self, kernel, read, arguments):
        from . import files_service
        target = _inside(kernel, arguments.get('path', '')) / files_service.clean_name(arguments['name'])
        return {'path': files_service.place_of(kernel, target)}  # 1.0 L6

    def find(self, kernel, read, arguments, prepared):
        target = _inside(kernel, prepared['path'])
        if not target.is_dir():return None
        return {'object': 'files:' + prepared['path'], 'revision': 'folder', 'by': 'folder', 'complete': True, 'how': 'observed',
                'path': prepared['path'], 'words': 'the folder %s is there' % prepared['path']}

    def verify(self, kernel, read, arguments, result, prepared, step):
        found = self.find(kernel, read, arguments, prepared)
        if not found:raise _asg.NotVerified('the folder is not there')
        return found

    def still(self, kernel, read, step):
        return '' if _inside(kernel, step['prepared']['path']).is_dir() else 'the folder is no longer there'


def _window_digest(windows):
    return _asg.digest([[w.get('id'), w.get('title'), w.get('active'), w.get('minimised')] for w in windows])


def inferences(observation):
    """What a look at the windows may mean, each marked inferred: a dialog (or a window) whose title reads like a "Save
    changes?" prompt or an error. A title is observed; what it means is not established until its text and buttons are read
    (K7's accessibility reader, when it is here)."""
    out = [];seen = set()
    shown = {w['id']: w for w in observation.get('windows') or ()}
    appeared = {e['window'] for e in observation.get('events') or () if e.get('event') in ('a new dialog appeared', 'a new window appeared')}
    for w in list(shown.values()):
        title = w.get('title') or ''
        kind = 'a "Save changes?" prompt' if SAVE_PROMPT.search(title) else ('an error or a warning' if ERROR_PROMPT.search(title) else '')
        if not kind or w['id'] in seen or w.get('graphite'):continue
        seen.add(w['id'])
        basis = 'its title reads "%s"%s%s' % (title[:120], ' and it is a dialog' if w.get('dialog') else '',
                                              ', and it appeared since the last look' if w['id'] in appeared else '')
        reader = _read_inside(w)
        words = 'Possibly %s in %s: %s. %s' % (kind, w.get('program') or 'a program', basis, reader['words'])
        out.append({'kind': kind, 'window': w['id'], 'title': title[:200], 'program': w.get('program') or '', 'dialog': bool(w.get('dialog')),
                    'basis': basis, 'read_inside': reader['read'], 'words': words[:600]})
        if len(out) >= MAX_INFERENCES:break
    return out


def _read_inside(window):
    """K7's reader, when it is here: what the dialog says inside. Without it, why the meaning stays an inference."""
    if ACCESSIBILITY is None:
        return {'read': False, 'words': 'This is an inference from the title: its text and buttons were not read (no accessibility '
                                        'reader in this Graphite yet).'}
    try:inside = ACCESSIBILITY(window) or {}
    except Exception as exc:  # noqa: BLE001
        inside = {'available': False, 'reason': str(exc)[:160]}
    if not inside.get('available'):
        return {'read': False, 'words': 'This is an inference from the title: its inside could not be read (%s).' % str(inside.get('reason', ''))[:160]}
    buttons = ', '.join(str(b)[:40] for b in (inside.get('buttons') or ())[:8])
    return {'read': True, 'words': 'Its buttons, read through accessibility: %s. What pressing them does is still not established.' % (buttons or 'none')}


class WindowsObserve(_asg.Check):
    """windows.observe: a look at the windows is its own observation (the X11 properties, read now); what a title means is
    inferred. Windows move all the time, so a look is never re-checked later: it is of its moment."""
    kind = 'windows';effect = 'nothing (a look)';standin_ms = 500;repeatable = True
    how = "the windows' X11 properties, read now; what a dialog's title means is marked inferred"
    expected = 'the open windows and the active one, with what appeared since the last look'

    def find(self, kernel, read, arguments, prepared):
        return None

    def verify(self, kernel, read, arguments, result, prepared, step):
        return observation_of_windows(result)

    def still(self, kernel, read, step):
        return ''


def observation_of_windows(result):
    if not result.get('available'):
        raise _asg.NotVerified(str(result.get('reason') or 'no window list on this computer'))
    windows = result.get('windows') or [];active = result.get('active') or {}
    listed = [w for w in windows if w.get('listed', True) and not w.get('graphite')]
    return {'object': 'windows', 'revision': _window_digest(windows), 'by': 'window list', 'complete': bool(result.get('complete')),
            'how': 'observed', 'window': active.get('id', ''), 'title': (active.get('title') or '')[:200], 'program': active.get('program') or '',
            'seq': result.get('seq'), 'inferences': inferences(result),
            'words': '%d program window%s open; active: %s' % (len(listed), '' if len(listed) == 1 else 's',
                                                              ('"%s" (%s)' % (active.get('title', '')[:80], active.get('program', ''))) if active else 'none')}


class WindowAct(_asg.Check):
    """windows.activate, .minimise, .close: asked of the window manager; done only when a fresh look shows it."""
    kind = 'window';standin_ms = 1500

    def __init__(self, action):
        self.action = action
        self.repeatable = action != 'close'
        self.effect = {'activate': 'a window brought forward', 'minimise': 'a window minimised', 'close': 'a window closed, politely'}[action]
        self.how = {'activate': 'a fresh look shows it active', 'minimise': 'a fresh look shows it minimised',
                    'close': 'a fresh look no longer lists it'}[action]
        self.expected = self.effect

    @staticmethod
    def _watcher():
        from . import windows_x11
        watcher = windows_x11.shared()
        if not watcher.start():raise _asg.Blocked(watcher.reason or windows_x11.NO_LIST)
        return watcher

    def prepare(self, kernel, read, arguments):
        watcher = self._watcher();watcher.refresh()
        row = watcher.row(int(arguments['window'], 16))
        if row is None:raise _asg.Blocked('the window %s is not open now' % arguments['window'])
        return {'window': row['id'], 'title': row['title'][:200], 'program': row['program'], 'pid': row.get('pid')}

    def _seen(self, prepared):
        watcher = self._watcher();watcher.refresh()
        row = watcher.row(int(prepared['window'], 16))
        if self.action == 'close':seen = row is None
        elif self.action == 'activate':seen = bool(row and row['active'])
        else:seen = bool(row and row['minimised'])
        if not seen:return None
        return {'object': 'window:' + prepared['window'], 'revision': prepared['window'], 'by': 'window list', 'complete': True, 'how': 'observed',
                'window': prepared['window'], 'title': prepared['title'], 'program': prepared['program'],
                'words': '"%s" (%s) %s' % (prepared['title'][:80], prepared['program'],
                                          {'activate': 'is the active window', 'minimise': 'is minimised', 'close': 'is no longer listed'}[self.action])}

    def find(self, kernel, read, arguments, prepared):
        return self._seen(prepared)

    def verify(self, kernel, read, arguments, result, prepared, step):
        end = time.monotonic() + WINDOW_WAIT_S
        while True:
            found = self._seen(prepared)
            if found or time.monotonic() >= end:break
            time.sleep(0.1)
        if not found:
            raise _asg.NotVerified('asked (%s); a fresh look does not show it %s' % ((result or {}).get('how') or 'sent',
                                                                                   {'activate': 'active', 'minimise': 'minimised', 'close': 'gone'}[self.action]))
        return found

    def still(self, kernel, read, step):
        return ''


class AppOpen(_asg.Check):
    """apps.open: the program started; done when a window of it appears (with no window list: its process runs, partial).
    Opening twice opens two, so after an interruption it is never repeated by itself."""
    kind = 'program';effect = 'a program started';standin_ms = 4000;repeatable = False
    how = 'a window of the program appears in the window list (with no window list: its process runs, a partial receipt)'
    expected = 'the program running, with its window'

    def prepare(self, kernel, read, arguments):
        from . import apps_catalog
        app = apps_catalog.find_app(arguments['id'])
        if app is None:raise _asg.Blocked('%s is not installed here' % arguments['id'][:120])
        seq = None
        try:
            from . import windows_x11
            watcher = windows_x11.shared()
            if watcher.start():seq = watcher.observe()['seq']
        except Exception:  # noqa: BLE001 - no window list: the receipt will be partial
            seq = None
        return {'app': arguments['id'], 'name': app.name, 'seq': seq, 'at': time.time()}

    def find(self, kernel, read, arguments, prepared):
        raise _asg.Unknowable('Graphite cannot tell whether the App was opened before it stopped: look at your windows')

    def verify(self, kernel, read, arguments, result, prepared, step):
        result = result or {}
        if not result.get('ok'):raise _asg.NotVerified(str(result.get('reason') or 'it did not start')[:300])
        pids = [s.get('pid') for s in result.get('started') or () if s.get('ok') and s.get('pid')]
        alive = [p for p in pids if _alive(p)]
        base = {'object': 'app:' + prepared['app'], 'by': 'process', 'how': 'observed', 'program': prepared['name']}
        if prepared.get('seq') is not None:
            from . import windows_x11
            from . import halt_gate      # 1.0 K3: HALT ends this wait at once; the App itself is yours and keeps running
            watcher = windows_x11.shared();end = time.monotonic() + APP_WAIT_MS / 1000;since = halt_gate.epoch(kernel);halted = False
            while True:
                look = watcher.observe(prepared['seq'])
                new = [e for e in look['events'] if e['event'] in ('a new window appeared', 'a new dialog appeared')]
                rows = {w['id']: w for w in look['windows']}
                mine = [e for e in new if (rows.get(e['window']) or {}).get('pid') in pids]
                named = [e for e in new if prepared['name'].casefold() in (e.get('program') or '').casefold()
                         or (e.get('program') or '').casefold() in prepared['name'].casefold() and e.get('program')]
                halted = not (mine or named) and halt_gate.pressed_since(kernel, since)
                if mine or named or halted or time.monotonic() >= end:break
                time.sleep(0.2)
            if halted:      # 1.0 K3
                raise _asg.NotVerified('you pressed HALT while its window was looked for: %s was started%s and is left running, not verified'
                                       % (prepared['name'], (' (process %s runs)' % alive[0]) if alive else ''))
            if mine:
                e = mine[0]
                return dict(base, revision=str(rows[e['window']].get('pid')), complete=True, window=e['window'], title=e['title'][:200],
                            words='%s started: its window "%s" appeared (process %s)' % (prepared['name'], e['title'][:80], rows[e['window']].get('pid')))
            if named:
                e = named[0]
                return dict(base, revision=e['window'], complete=False, window=e['window'], title=e['title'][:200],
                            words='%s started: a window of %s appeared ("%s"); it is linked to this start by its program, not its process'
                                  % (prepared['name'], e.get('program'), e['title'][:80]))
            if alive:raise _asg.NotVerified('%s started (process %s runs) and no window of it appeared within %d s' % (prepared['name'], alive[0], APP_WAIT_MS // 1000))
            raise _asg.NotVerified('%s started and ended at once; no window of it appeared' % prepared['name'])
        if alive:
            return dict(base, revision=str(alive[0]), complete=False,
                        words='%s started: its process %s runs; its window could not be seen (no window list on this computer)' % (prepared['name'], alive[0]))
        raise _asg.NotVerified('%s started and ended at once' % prepared['name'])

    def still(self, kernel, read, step):
        return ''


def _alive(pid):
    try:os.kill(int(pid), 0)
    except (OSError, ValueError, TypeError):return False
    return True


class MachineRead(_asg.Check):
    """machine.state: read now; each section says available or why not. The machine moves, so it is never re-checked."""
    kind = 'machine';effect = 'nothing (a read)';standin_ms = 1500;repeatable = True
    how = 'read now through its own services; each section says available, or why not'
    expected = "this computer's storage, power, network, sound and screens, as they are now"

    def find(self, kernel, read, arguments, prepared):
        return None

    def verify(self, kernel, read, arguments, result, prepared, step):
        sections = (result or {}).get('sections') or {}
        missing = {k: str(v.get('why') or v.get('short') or 'not available')[:120] for k, v in sections.items() if not v.get('available')}
        read_ = [k for k in sections if k not in missing]
        words = 'read now: %s' % (', '.join(read_) or 'nothing')
        if missing:words += '; not available here: ' + '; '.join('%s (%s)' % kv for kv in missing.items())
        return {'object': 'machine:' + (arguments.get('section') or 'all'), 'revision': _asg.digest(sections), 'by': 'digest',
                'complete': not missing, 'how': 'observed', 'words': words[:600]}

    def still(self, kernel, read, step):
        return ''


def install():
    """K2 widens K1's checks and words: every built tool's operation has its check."""
    _asg.CHECKS.update({'files.write': FileWrite(), 'files.get': FileRead(), 'files.rename': Relocate('files.rename'),
                        'files.move': Relocate('files.move'), 'files.mkdir': FolderMake(), 'windows.observe': WindowsObserve(),
                        'windows.activate': WindowAct('activate'), 'windows.minimise': WindowAct('minimise'),
                        'windows.close': WindowAct('close'), 'apps.open': AppOpen(), 'machine.state': MachineRead()})
    for head, words in (('windows', 'the window controller'), ('apps', 'Apps'), ('machine', 'the Machine'), ('tools', 'her tools')):
        _asg.TOOL_WORDS.setdefault(head, words)
    for op, words in (('files.rename', 'rename a file'), ('files.move', 'move a file'), ('windows.activate', 'bring a program window forward'),
                      ('windows.minimise', 'minimise a program window'), ('windows.close', 'ask a program window to close'),
                      ('apps.open', 'open an App')):
        _asg.GRANT_WORDS.setdefault(op, words)


install()


# ---------------------------------------------------------------- receipts

MIGRATIONS = [(1, (
    'CREATE TABLE tool_receipts(id TEXT PRIMARY KEY, owner TEXT NOT NULL, tool TEXT NOT NULL, operation TEXT NOT NULL, '
    'object TEXT NOT NULL, revision TEXT NOT NULL, status TEXT NOT NULL, how TEXT NOT NULL, complete INTEGER NOT NULL, '
    'assignment TEXT NOT NULL, step TEXT NOT NULL, journal INTEGER, follows TEXT NOT NULL, payload TEXT NOT NULL, '
    'digest TEXT NOT NULL, at INTEGER NOT NULL)',
    'CREATE INDEX tool_receipts_of ON tool_receipts(assignment, step, at)',
    'CREATE INDEX tool_receipts_object ON tool_receipts(object, at)',
    'CREATE INDEX tool_receipts_owner ON tool_receipts(owner, at)',
))]


def ensure(db):
    """Forward-only migrations of the receipts' table; other tables are left alone."""
    if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS tool_receipts_migrations(version INTEGER PRIMARY KEY, digest TEXT NOT NULL, applied INTEGER NOT NULL)')
    applied = dict(db.execute('SELECT version, digest FROM tool_receipts_migrations'))
    known = {version: _asg.digest(list(sql)) for version, sql in MIGRATIONS}
    if any(known.get(v) != d for v, d in applied.items()) or sorted(applied) != list(range(1, len(applied) + 1)):
        raise ValueError('RECEIPTS_MIGRATION_UNSUPPORTED: use a compatible program')
    for version, statements in MIGRATIONS:
        if version in applied:continue
        for statement in statements:db.execute(statement)
        db.execute('INSERT INTO tool_receipts_migrations VALUES(?,?,?)', (version, known[version], _now_ms()))


def _present(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tool_receipts'").fetchone() is not None


def _text(value, most=300):
    if value is None or isinstance(value, bool):return ''
    if isinstance(value, float):return ''                       # never a floating point in a receipt's checked fields
    return str(value)[:most]


def receipt(tool, operation, obj, status, how, complete, words, revision='', place=None, basis='', owner='', assignment='', step='',
            journal=None, follows='', detail=None):
    """One receipt, checked: its status, how it is known, complete or partial, and its place."""
    if status not in STATUSES:raise ValueError('RECEIPT_STATUS: %s is not a status of a receipt' % str(status)[:40])
    if how not in HOW:raise ValueError('RECEIPT_HOW: %s is not how an observation is known' % str(how)[:40])
    if type(complete) is not bool:raise ValueError('RECEIPT_COMPLETE: complete or partial is yes or no')
    tool_ = TOOLS.get(tool)
    value = {'schema': RECEIPT, 'id': uuid.uuid4().hex, 'owner': _text(owner, 200), 'tool': _text(tool, 64),
             'number': tool_.number if tool_ else None, 'operation': _text(operation, 120), 'object': _text(obj, 1100) or operation,
             'revision': _text(revision, 200), 'place': {k: _text(v, 300) for k, v in (place or {}).items() if k in PLACE_KEYS and _text(v)},
             'complete': complete, 'how': how, 'status': status, 'status_words': STATUS_WORDS[status], 'words': _text(words, 600),
             'basis': _text(basis, 300), 'assignment': _text(assignment, 32), 'step': _text(step, 32),
             'journal': journal if type(journal) is int else None, 'follows': _text(follows, 32), 'at': _now_ms(),
             'detail': detail if isinstance(detail, dict) else {}}
    if len(_asg.canonical(value).encode()) > MAX_RECEIPT:value['detail'] = {'note': 'detail too long to keep; its digest', 'digest': _asg.digest(detail)}
    return value


def place_of(arguments, observation=None):
    """Where an observation was made: the path, page, sheet and cell, line, window and its title."""
    place = {}
    for source in (arguments or {}, observation or {}):
        for k in PLACE_KEYS:
            if isinstance(source.get(k), (str, int)) and not isinstance(source.get(k), bool):place[k] = source[k]
    if isinstance((observation or {}).get('sheet'), str):place['sheet'] = observation['sheet']
    obj = str((observation or {}).get('object') or '')
    if obj.startswith('office:') and 'sheet' not in place:place['sheet'] = obj[len('office:'):]
    if isinstance((arguments or {}).get('id'), str) and str((arguments or {}).get('id')).startswith('office:') and 'sheet' not in place:
        place['sheet'] = arguments['id'][len('office:'):]
    return place


def object_of(operation, arguments):
    """What a call is about, before its effect is seen: files:<path>, documents:<page>, office:<sheet>, window:<id>,
    app:<id>, machine:<section>, windows; else the Kernel's own naming (assignments._object)."""
    a = arguments or {}
    if operation == 'office.datasheet.recheck' and isinstance(a.get('id'), str):return 'documents:' + a['id']
    if operation in ('windows.activate', 'windows.minimise', 'windows.close') and isinstance(a.get('window'), str):return 'window:' + a['window']
    if operation == 'windows.observe':return 'windows'
    if operation == 'apps.open' and isinstance(a.get('id'), str):return 'app:' + a['id']
    if operation == 'machine.state':return 'machine:' + str(a.get('section') or 'all')
    return _asg._object(operation, a)


def of_observation(tool, operation, arguments, observation, status, **more):
    """A receipt from a check's observation (K1's shape: object, revision, by, complete, how, words, and its place)."""
    obs = observation or {}
    how = obs.get('how') if obs.get('how') in HOW else 'observed'
    return receipt(tool, operation, obs.get('object') or object_of(operation, arguments), status, how,
                   bool(obs.get('complete', False)) if type(obs.get('complete', False)) is bool else False, obs.get('words', ''),
                   revision=obs.get('revision', ''), place=place_of(arguments, obs), basis=obs.get('by', ''), **more)


def inferred_receipts(tool, operation, observation, **more):
    """One receipt per inference of a look at the windows, each marked inferred."""
    out = []
    for item in (observation or {}).get('inferences') or ():
        out.append(receipt(tool, operation, 'window:' + item['window'], 'inferred', 'inferred', False, item['words'], revision=item['window'],
                           place={'window': item['window'], 'title': item['title'], 'program': item['program']}, basis=item['basis'],
                           detail={'kind': item['kind'], 'dialog': item['dialog'], 'read_inside': item['read_inside']}, **more))
    return out


def keep(db, value):
    """Write one receipt in the transaction the caller holds."""
    ensure(db)
    payload = _asg.canonical(value)
    db.execute('INSERT INTO tool_receipts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (value['id'], value['owner'], value['tool'], value['operation'], value['object'], value['revision'], value['status'],
                value['how'], int(value['complete']), value['assignment'], value['step'], value['journal'], value['follows'], payload,
                hashlib.sha256(payload.encode()).hexdigest(), value['at']))
    return value


def record(kernel, *values):
    """Keep receipts in one short transaction of their own."""
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        for value in values:keep(db, value)
    return list(values)


def journalled(db, value, step, entry, payload, seq):
    """K1's journal row `seq` was just written (same transaction): its receipts. SENT is "dispatched"; DONE, FOUND_DONE and
    STILL_DONE "verified" (following the dispatched one); NOT_VERIFIED "not verified"; REFUSED, CHANGED_SINCE likewise."""
    status = OF_JOURNAL.get(entry)
    if not step or not status:return []
    operation = step.get('operation') or ''
    arguments = step.get('resolved') or {}
    detail = (payload or {}).get('detail') or {}
    tool = key_for(operation, step, step.get('prepared'))
    common = {'owner': value.get('owner', ''), 'assignment': value.get('id', ''), 'step': step.get('key', ''), 'journal': seq}
    kept = []
    if status == 'dispatched':
        kept.append(receipt(tool, operation, object_of(operation, arguments), 'dispatched', 'observed', False,
                            'Step %s sent; its effect is not yet verified.' % step.get('n'), place=place_of(arguments),
                            basis='the call came back', detail={'result': detail.get('result', '')}, **common))
    else:
        ensure(db)
        last = db.execute("SELECT id FROM tool_receipts WHERE assignment=? AND step=? AND status='dispatched' ORDER BY at DESC, rowid DESC LIMIT 1",
                          (common['assignment'], common['step'])).fetchone()
        follows = last[0] if last and entry in ('DONE', 'NOT_VERIFIED') else ''
        observation = detail.get('observation') if isinstance(detail.get('observation'), dict) else None
        if observation is None and entry in ('STILL_DONE', 'CHANGED_SINCE'):observation = step.get('observation')
        if status == 'verified' and observation:
            words = observation.get('words', '')
            if entry == 'FOUND_DONE':words = 'already there, not made again: ' + words
            if entry == 'STILL_DONE':words = 'looked at again on resume: ' + words
            main = of_observation(tool, operation, arguments, dict(observation, words=words), 'verified', follows=follows, **common)
            kept.append(main)
            kept.extend(inferred_receipts(tool, operation, observation, **dict(common, follows=main['id'])))
        else:
            why = (payload or {}).get('words') or step.get('reason') or entry.lower()
            how = 'unavailable' if entry == 'CANNOT_TELL' else 'observed'
            kept.append(receipt(tool, operation, (observation or {}).get('object') or object_of(operation, arguments), status, how, False,
                                str(why)[:400], revision=(observation or {}).get('revision', ''), place=place_of(arguments, observation),
                                follows=follows, **common))
    for item in kept:keep(db, item)
    return kept


def _row(payload, sha):
    value = json.loads(payload)
    value['intact'] = hashlib.sha256(payload.encode()).hexdigest() == sha
    return value


def receipts(kernel, principal, assignment=None, step=None, obj=None, tool=None, limit=50, offset=0):
    """Receipts of yours, newest first (each says whether it still matches its digest)."""
    with kernel.db() as db:
        if not _present(db):return []
        where, args = ['owner=?'], [principal.identity]
        for column, value in (('assignment', assignment), ('step', step), ('object', obj), ('tool', tool)):
            if value:where.append('%s=?' % column);args.append(value)
        rows = db.execute('SELECT payload, digest FROM tool_receipts WHERE %s ORDER BY at DESC, rowid DESC LIMIT ? OFFSET ?' % ' AND '.join(where),
                          (*args, int(limit), int(offset))).fetchall()
    return [_row(p, s) for p, s in rows]


def of_assignment(db, ident):
    """An assignment's receipts by step, oldest first, compact (for assignment.status)."""
    if not _present(db):return {}
    out = {}
    for payload, sha in db.execute('SELECT payload, digest FROM tool_receipts WHERE assignment=? ORDER BY at, rowid', (ident,)):
        r = _row(payload, sha)
        out.setdefault(r['step'], []).append({k: r[k] for k in ('id', 'tool', 'number', 'status', 'status_words', 'how', 'complete', 'object',
                                                                 'revision', 'place', 'words', 'journal', 'follows', 'intact')})
    return out


# ---------------------------------------------------------------- using a tool, outside a plan

def _reader(kernel, principal):
    return _asg._reader(kernel, principal)


def use(kernel, tool, arguments, principal, origins=None, basis='owner_words', operation=None, why=''):
    """Use one tool through its door: who may (the model alone never for a change; a send always asks), its preconditions,
    its grant (K3), a sleep lock while it writes a file (S1); the call, kept as "dispatched"; its check, kept as "verified"
    or "not verified". A tool that cannot be used here is kept as "unavailable", with the reason."""
    tool = entry(tool)
    arguments = dict(arguments or {})
    owner = principal.identity
    out = {'schema': SCHEMA, 'tool': tool.key, 'number': tool.number, 'operation': operation or '', 'receipts': []}

    def finish(status, words, *kept, result=None):
        if kept:out['receipts'].extend(record(kernel, *kept))
        out.update(status=status, words=words)
        if result is not None and tool.undo == 'read':out['result'] = result
        return out

    ok, why_not = available(tool)
    if not ok:
        obj = 'tool:' + tool.key
        return finish('unavailable', why_not, receipt(tool.key, operation or '', obj, 'unavailable', 'unavailable', False, why_not,
                                                      basis='the tool says why', owner=owner))
    if tool.undo == 'send':
        raise Refused('TOOL_SENDS: %s sends something off this computer: it is done through its own door, with your press each time' % tool.key)
    op = _operation(tool, operation)
    out['operation'] = op
    _origins_hold(tool, arguments, origins or {}, basis, in_plan=False)
    missing = unmet(kernel, tool, arguments, origins, op)
    if missing:return finish('blocked', 'not used: ' + '; '.join(missing) + '. Nothing was sent.')
    if GRANT_CHECK is not None:
        need = GRANT_CHECK(kernel, tool, op, arguments, principal)
        from .home_reach import NEVER  # 1.0 L6: "outside your home: never" is said as it is, not as a grant to ask for
        if need:return finish('blocked', ('not used: %s. Nothing was sent.' if str(need).startswith(NEVER) else 'needs your grant: %s. Nothing was sent.') % str(need)[:300])
    check = _asg.check_for(op)
    read = _reader(kernel, principal)
    try:
        prepared = check.prepare(kernel, read, arguments)
        found = check.find(kernel, read, arguments, prepared) if tool.undo != 'read' else None
    except _asg.Unknowable:
        found = None
    except _asg.Blocked as blocked:
        return finish('blocked', 'not used: %s. Nothing was sent.' % blocked)
    key = key_for(op, {'tool_key': tool.key}, prepared)
    if found is not None:
        return finish('verified', 'already there; it was not made again: ' + found.get('words', ''),
                      of_observation(key, op, arguments, dict(found, words='already there, not made again: ' + found.get('words', '')),
                                     'verified', owner=owner))
    import contextlib
    granted = GRANTED(kernel, tool, op, arguments, principal) if GRANTED is not None else contextlib.nullcontext()  # 1.0 K3: its permit
    with holding(op, why or tool.words), granted:
        answer = kernel.dispatch(op, arguments, principal)
    if not answer.get('ok'):
        message = str((answer.get('error') or {}).get('message') or 'refused')[:300]
        return finish('refused', 'refused by the desk: %s. Nothing is called done.' % message,
                      receipt(key, op, object_of(op, arguments), 'refused', 'observed', False, message, place=place_of(arguments), owner=owner))
    result = answer['result']
    sent = receipt(key, op, object_of(op, arguments), 'dispatched', 'observed', False, 'sent; its effect is not yet verified',
                   place=place_of(arguments), basis='the call came back', owner=owner, detail={'result': _asg.digest(result)})
    record(kernel, sent);out['receipts'].append(sent)
    try:
        observation = check.verify(kernel, read, arguments, result, prepared, {'operation': op, 'resolved': arguments, 'outputs': {}})
    except _asg.NotVerified as not_seen:
        return finish('not verified', 'sent, and not verified: %s. It is not called done.' % not_seen,
                      receipt(key, op, object_of(op, arguments), 'not verified', 'observed', False, str(not_seen),
                              place=place_of(arguments), owner=owner, follows=sent['id']), result=result)
    main = of_observation(key, op, arguments, observation, 'verified', owner=owner, follows=sent['id'])
    return finish('verified', observation.get('words', 'verified'), main,
                  *inferred_receipts(key, op, observation, owner=owner, follows=main['id']), result=result)


def look_at_windows(kernel, principal, since=None, keep_it=False):
    """Her look at the windows, as receipts: the windows observed, and each possible prompt inferred. Kept only when asked
    (a look from her work); the window's own reading is never kept."""
    from . import windows_x11
    look = windows_x11.observe(since)
    owner = principal.identity
    if not look.get('available'):
        made = [receipt('windows.observe', 'windows.observe', 'windows', 'unavailable', 'unavailable', False,
                        look.get('reason') or windows_x11.NO_LIST, basis='no window list', owner=owner)]
    else:
        observation = observation_of_windows(look)
        main = of_observation('windows.observe', 'windows.observe', {}, observation, 'observed', owner=owner)
        made = [main] + inferred_receipts('windows.observe', 'windows.observe', observation, owner=owner, follows=main['id'])
    if keep_it:record(kernel, *made)
    return dict(look, receipts=made, kept=bool(keep_it))


# ---------------------------------------------------------------- the Kernel's operations (1.0 K2)

FIELDS = {
    'tools.list': ({'key': KEY, 'number': {'type': 'integer', 'minimum': 1, 'maximum': 999}, 'family': KEY, 'members': {'type': 'boolean'}}, []),
    'tools.receipts': ({'assignment': ID, 'step': {'type': 'string', 'minLength': 1, 'maxLength': 32}, 'object': {'type': 'string', 'maxLength': 1100},
                        'tool': KEY, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 200},
                        'offset': {'type': 'integer', 'minimum': 0, 'maximum': 100000}}, []),
    'tools.use': ({'tool': KEY, 'number': {'type': 'integer', 'minimum': 1, 'maximum': 999}, 'operation': {'type': 'string', 'maxLength': 120},
                   'arguments': {'type': 'object'}, 'origins': {'type': 'object'},
                   'basis': {'type': 'string', 'enum': ['owner_words', 'owner_click', 'deduction', 'model_pick']}}, ['arguments']),
    'windows.observe': ({'since': {'type': 'integer', 'minimum': 0, 'maximum': 1 << 40}}, []),
    'windows.activate': ({'window': WINDOW}, ['window']),
    'windows.minimise': ({'window': WINDOW}, ['window']),
    'windows.close': ({'window': WINDOW}, ['window']),
}
SCOPES = {'tools.list': 'read', 'tools.receipts': 'read', 'tools.use': 'execute', 'windows.observe': 'read',
          'windows.activate': 'execute', 'windows.minimise': 'execute', 'windows.close': 'approve'}
OBSERVERS = ('tools.list', 'tools.receipts', 'windows.observe')


def listing(args):
    if args.get('key') or args.get('number'):
        return {'schema': SCHEMA, 'tool': view(args.get('key') or args.get('number'), with_members=True)}
    rows = [view(t, with_members=bool(args.get('members'))) for t in sorted(TOOLS.values(), key=lambda t: t.number)
            if not args.get('family') or t.family == args['family']]
    return {'schema': SCHEMA, 'tools': rows, 'statuses': dict(STATUS_WORDS), 'undo': dict(UNDO_WORDS), 'from': dict(FROM_WORDS),
            'rule': 'The model proposes; the desk disposes: a change is used only with every argument from your words, a record, a '
                    'source line, a deduction or an earlier step, never the model alone; a send asks you every time; a step is done '
                    'only when its effect is verified.'}


def _window_action(action, args):
    from . import windows_x11
    wid = int(args['window'], 16)
    answer = getattr(windows_x11.shared(), action)(wid, wait=WINDOW_WAIT_S)
    answer['status'] = 'verified' if answer.get('verified') else ('dispatched' if answer.get('asked') else 'not sent')
    answer['status_words'] = {'verified': 'asked, and seen done', 'dispatched': 'asked; not seen done yet', 'not sent': 'not asked'}[answer['status']]
    return answer


def dispatch(kernel, op, args, principal):
    if op == 'tools.list':return listing(args)
    if op == 'tools.receipts':
        rows = receipts(kernel, principal, args.get('assignment'), args.get('step'), args.get('object'), args.get('tool'),
                        args.get('limit', 50), args.get('offset', 0))
        return {'schema': RECEIPT, 'receipts': rows, 'intact': all(r['intact'] for r in rows)}
    if op == 'tools.use':
        if not args.get('tool') and not args.get('number'):raise ValueError('Name the tool, by its key or its number')
        return use(kernel, args.get('tool') or args.get('number'), args['arguments'], principal, args.get('origins'),
                   args.get('basis', 'owner_words'), args.get('operation'))
    if op == 'windows.observe':return look_at_windows(kernel, principal, args.get('since'))
    if op in ('windows.activate', 'windows.minimise', 'windows.close'):return _window_action(op.split('.', 1)[1], args)
    raise ValueError('Unknown tools operation')
