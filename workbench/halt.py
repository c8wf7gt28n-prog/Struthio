"""HALT, the master stop of her managed work (1.0 P2; the plan's "complete", item 10: "HALT (upper left) stops all of her
managed work and nothing else: never the desktop, never the owner's programs").

One function behind the button in the head's upper-left slot, and one to lift what it did:

  press(host)    the owner's press. In this order:
                   1. her work is held (the Night Shift's work gate, work_trail.hold, which K1's assignments obey): no step
                      starts while it is held, and a run that sees the hold stops at its next look;
                   2. every assignment that is running now is stopped through assignment.stop (K1), so its journal says
                      "stopped by you" with what was done and what was only prepared;
                   3. her hand is stopped before its next press, if it is acting (her_hand_qt.HerHand.stop);
                   4. the moment that matters is shown in her column (her_column_qt.moment(host, 'halt'), P1);
                   5. her column says in words what was stopped.
                 Returns {'held', 'stopped' (titles), 'hand' (bool), 'words', 'error'}.
  release(host)  lifts the hold (ledger.work.resume, the owner's approve scope). Nothing stopped is restarted: each
                 assignment is resumed by its own Resume, which inspects before it repeats anything.
  held(host)     whether her work is held now (by HALT or by Stop all): the button reads RESUME while it is.

What HALT never touches: the desktop, Graphite's window, the owner's programs and their windows, builds and the console
(those are Stop all's, on the meters' card), the network, the machine. Nothing here asks the model anything.

K3 widens press() later (grants, the model's turns, the utility sandboxes) and keeps this one small module.
"""
from __future__ import annotations

WORDS = {
    'stopped': 'HALT: I stopped %s and held all of my work. No step starts until you press RESUME; the desktop and your '
               'apps keep running.',
    'nothing': 'HALT: nothing of mine was running. All of my work is held until you press RESUME; the desktop and your apps '
               'keep running.',
    'hand': ' My hand stopped before its next press.',
    'not_held': 'HALT could not hold my work: %s. Use Stop all on the meters if anything of mine is still running.',
    'released': 'RESUME: the hold is lifted. Nothing stopped was restarted; each assignment resumes from its own Resume, '
                'which checks every step first.',
    'not_released': 'The hold stays: %s.',
}


def _kernel(host):
    from .engineering_kernel import operator
    kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None:
        from .engine import engineering
        kernel = engineering(host.root)
    return kernel, operator()


def _say(host, words):
    """Her column says it (P1's exchange); without her column, the status line does."""
    column = getattr(host, 'her_column', None)
    try:
        if column is not None:column.say_words(words);return
    except Exception:  # noqa: BLE001 - saying it never undoes the stop
        pass
    try:host.statusBar().showMessage(words, 12000)
    except Exception:  # noqa: BLE001
        pass


def held(host):
    """True while her managed work is held (HALT, or Stop all); False when it is not, or when the gate cannot be read."""
    try:
        from . import work_trail
        kernel, _ = _kernel(host)
        if getattr(kernel, 'is_host_client', False):
            answer = kernel.dispatch('ledger.work.status', {}, _kernel(host)[1])
            return bool((answer.get('result') or {}).get('held')) if answer.get('ok') else False
        return bool(work_trail.work_status(kernel).get('held'))
    except Exception:  # noqa: BLE001 - a gate that cannot be read is not said to be held
        return False


def press(host):
    """HALT: hold her work, stop what of hers runs, stop her hand, show the moment, say what was stopped."""
    kernel, owner = _kernel(host)
    out = {'held': False, 'stopped': [], 'hand': False, 'words': '', 'error': ''}
    try:
        if getattr(kernel, 'is_host_client', False):kernel.rpc('hold')
        else:
            from . import work_trail
            work_trail.hold(kernel, owner)
        out['held'] = True
    except Exception as exc:  # noqa: BLE001 - said in words, and the rest still stops what it can
        out['error'] = str(exc)[:200] or type(exc).__name__
    try:
        listing = kernel.dispatch('assignment.list', {'open': True, 'limit': 50}, owner)
        rows = (listing.get('result') or {}).get('assignments') or () if listing.get('ok') else ()
    except Exception:  # noqa: BLE001 - K1 absent or unreadable: the hold still holds
        rows = ()
    for row in rows:
        if row.get('state') != 'running':continue
        try:
            answer = kernel.dispatch('assignment.stop', {'id': row['id']}, owner)
            if answer.get('ok'):out['stopped'].append(str(row.get('title') or 'an assignment'))
        except Exception:  # noqa: BLE001
            pass
    hand = getattr(host, 'her_hand', None)
    try:
        if hand is not None and hand.active():
            hand.stop('HALT');out['hand'] = True
    except Exception:  # noqa: BLE001
        pass
    column = getattr(host, 'her_column', None)
    if column is not None:column.seen_held = True      # the column's own watch on the gate must not show the moment twice
    try:
        from .her_column_qt import moment
        moment(host, 'halt')
    except Exception:  # noqa: BLE001
        pass
    if out['held']:
        names = ['“%s”' % t for t in out['stopped']]
        words = WORDS['stopped'] % (', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else names[0]) if names else WORDS['nothing']
    else:
        words = WORDS['not_held'] % out['error']
    if out['hand']:words += WORDS['hand']
    out['words'] = words
    _say(host, words)
    _refresh(host)
    return out


def release(host):
    """RESUME: lift the hold. Nothing that was stopped is started again here."""
    kernel, owner = _kernel(host)
    try:
        answer = kernel.dispatch('ledger.work.resume', {}, owner)
    except Exception as exc:  # noqa: BLE001
        answer = {'ok': False, 'error': {'message': str(exc)}}
    if answer.get('ok'):
        words = WORDS['released'];done = True
    else:
        error = answer.get('error') or {}
        why = str(error.get('message') if isinstance(error, dict) else error or 'refused')
        words = WORDS['not_released'] % why.split(': ', 1)[-1][:200];done = False
    column = getattr(host, 'her_column', None)
    if column is not None and done:column.seen_held = False
    _say(host, words)
    _refresh(host)
    return {'released': done, 'words': words}


def _refresh(host):
    button = getattr(getattr(getattr(host, 'shell2', None), 'top', None), 'halt', None)
    try:
        if button is not None:button.refresh()
    except Exception:  # noqa: BLE001
        pass
    column = getattr(host, 'her_column', None)
    try:
        if column is not None:column.refresh(force=True)
    except Exception:  # noqa: BLE001
        pass
