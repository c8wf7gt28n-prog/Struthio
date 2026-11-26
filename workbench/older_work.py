"""Graphite 1.0 F2b · A 0.8.x assignment left running, in ACTIVE WORK.

PLAN_1.0.md, F2b: "Also list a 0.8.x assignment left running in ACTIVE WORK (F2's drill found only the new kind listed)."
The coordinator's note: "show it in ACTIVE WORK with its own words and its own Stop, through the old path."

A workspace from 0.8.x can hold an assignment of hers made by the old loop (agent.assign; agent_loop), still RUNNING,
READY, PAUSED or waiting for the owner. 1.0's ACTIVE WORK lists K1's assignments (assignment.list); the old one was
reachable only through the old Work block and Today. Here it becomes one more row of ACTIVE WORK, shaped as her column's
rows are, read through the old path's own observer (agent.list), with:

  - its own words: the request as it was given (working_on), and the old path's own state word (agent_qt.STATE_WORDS:
    running, ready, paused, needs you), with a shape beside the word;
  - no bar and no time left of K1's (the old loop keeps neither): the steps it has taken, and why it waits or paused;
  - its own Stop: the row's stop is agent.stop on its id, the old path's write, pressed by the owner like any Stop.

Nothing here steps, resumes or changes an old assignment; it only lists what agent.list says and offers its Stop.
"""
from __future__ import annotations

OPEN = ('RUNNING', 'READY', 'WAITING', 'PAUSED')      # agent_loop.STATES that are not finished (DONE, STOPPED, FAILED)
ORDER = {'RUNNING': 0, 'WAITING': 1, 'PAUSED': 2, 'READY': 3}


def words(state):
    """The old path's own word for a state (agent_qt.STATE_WORDS)."""
    try:
        from .agent_qt import STATE_WORDS
    except Exception:  # noqa: BLE001 - the words as agent_qt has them, kept here if it cannot be imported
        STATE_WORDS = {'READY': 'ready', 'RUNNING': 'running', 'PAUSED': 'paused', 'WAITING': 'needs you'}
    return STATE_WORDS.get(state, str(state or '').lower())


def steps_words(n):
    return '%d step%s taken' % (n, '' if n == 1 else 's')


def row_of(summary):
    """An agent.list row as one of ACTIVE WORK's rows (its keys as K1's rows have them, marked older)."""
    state = str(summary.get('state') or '')
    said = words(state);used = int(summary.get('steps_used') or 0)
    why = str((summary.get('paused_reason') or summary.get('reason') or '') if state in ('PAUSED', 'WAITING') else '')
    title = str(summary.get('working_on') or summary.get('request') or 'An assignment from Graphite 0.8')
    return {'id': summary['id'], 'older': True, 'title': title, 'state': state, 'state_words': said, 'state_word': said.upper(),
            'progress': 0, 'time_left': steps_words(used), 'steps_short': '%d step%s' % (used, '' if used == 1 else 's'), 'line': why,
            'stop': {'operation': 'agent.stop', 'arguments': {'id': summary['id'], 'reason': 'Stop'}}}


def rows(read):
    """The open 0.8.x assignments, as rows: read('agent.list') as the column reads (None when it cannot be read)."""
    listing = read('agent.list', None) or {}
    found = [r for r in (listing.get('assignments') or ()) if isinstance(r, dict) and r.get('id') and r.get('state') in OPEN]
    found.sort(key=lambda r: (ORDER.get(r.get('state'), 9), -float(r.get('updated') or 0)))
    return [row_of(r) for r in found]


def journal_words(view):
    """agent.status's row in words for the exchange (a click on its title): what it works on, its state, what it does now."""
    rows = (view or {}).get('assignments') or []
    row = next((r for r in rows if isinstance(r, dict)), None)
    if row is None:return ''
    lines = ['“%s”, %s (an assignment from Graphite 0.8).' % (row.get('working_on') or '', words(row.get('state')))]
    if row.get('doing_now'):lines.append('Now: %s' % row['doing_now'])
    for item in (row.get('found') or ())[:4]:lines.append('Found: %s (%s)' % (item.get('text'), str(item.get('evidence_state') or '').lower()))
    for item in (row.get('needs_you') or ())[:3]:lines.append('Needs you: %s' % (item.get('text') if isinstance(item, dict) else item))
    lines.append(steps_words(int(row.get('steps_used') or 0)) + '.')
    return '\n'.join(lines)
