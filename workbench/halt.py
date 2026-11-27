"""HALT, the master stop of her managed work (1.0 P2; widened by 1.0 K3; the plan's "complete", item 10: "HALT (upper left)
stops all of her managed work and nothing else: never the desktop, never the owner's programs").

One function behind the button in the head's upper-left slot, and one to lift what it did:

  press(host)    the owner's press. In this order:
                   1. HALT's own hold and the Kernel's part of the stop (halt_gate.press, the operation halt.press): no step
                      starts and her model is not asked while it holds; every running assignment is stopped through
                      assignment.stop with HALT's words, so its journal says what was done, what was only prepared and that
                      a step was running when you pressed HALT (recorded as it ends); every other open assignment is held,
                      its journal saying the same; her model's reply jobs are cancelled and a turn running here is closed;
                      the sandboxes' stop hooks run (K6);
                   2. her hand is stopped before its next press, if it is acting (her_hand_qt.HerHand.stop);
                   3. the older assignments of AGENT-01 pause with the reason (the agent driver), as Stop all pauses them;
                   4. the moment that matters is shown in her column (her_column_qt.moment(host, 'halt'), P1);
                   5. her column says in words what was stopped.
                 Returns {'held', 'stopped' (titles), 'held_work' (titles), 'hand' (bool), 'turns', 'jobs', 'words', 'error'}.
  release(host)  RESUME: lifts HALT's hold (halt.release, the owner's approve scope). Nothing stopped is restarted: each
                 assignment is resumed by its own Resume, which inspects before it repeats anything.
  held(host)     whether HALT holds her work now: the button reads RESUME while it does. 1.0 K3: HALT's own hold only; Stop
                 all's hold of Graphite's jobs is Stop all's, read and lifted on its own card.

What HALT never touches: the desktop, Graphite's window, the owner's programs and their windows, Graphite's own jobs and
builds and the console (those are Stop all's, on the meters' card), the network, the machine. Nothing here kills a
process. Nothing here asks the model anything.
"""
from __future__ import annotations

WORDS = {
    'stopped': 'HALT: I stopped %s and hold all my work until you press RESUME. Each journal says what was done and what was '
               'only prepared. Your desktop, apps and Graphite’s jobs go on.',
    'nothing': 'HALT: nothing of mine was running. I hold all my work until you press RESUME. Your desktop, apps and '
               'Graphite’s jobs go on.',
    'held': ' Also held: %s.',
    'hand': ' My hand stopped before its next press.',
    'turns': ' My model’s answer was closed.',
    'nothing_turns': 'HALT: my model’s answer was closed, and nothing else of mine was running. I hold all my work until you '
                     'press RESUME. Your desktop, apps and Graphite’s jobs go on.',      # 1.0 F3 (X4 S11): never "nothing" and "closed" at once
    'not_held': 'HALT could not hold my work: %s. Use Stop all on the meters if anything of mine is still running.',
    'released': 'RESUME: the hold is lifted. Nothing stopped was restarted: what HALT stopped waits for your Resume on it '
                '(in “Waits for you”), which checks every step first.',      # 1.0 D2 (X3): say that her work waits for that press
    'released_jobs': ' Graphite’s jobs are still held by Stop all; lift that on its own card.',
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
    """True while HALT holds her managed work; False when it does not, or when its hold cannot be read (1.0 K3)."""
    try:
        kernel, owner = _kernel(host)
        answer = kernel.dispatch('halt.status', {}, owner)
        return bool((answer.get('result') or {}).get('held')) if answer.get('ok') else False
    except Exception:  # noqa: BLE001 - a hold that cannot be read is not said to be held
        return False


def _names(titles):
    names = ['“%s”' % t for t in titles]
    return ', '.join(names[:-1]) + ' and ' + names[-1] if len(names) > 1 else names[0]


def _alone(host, operation):
    """1.0 F3: the Kernel's part of a press on a thread of its own (a Kernel of its own on the same workspace), so the
    window's thread never waits for it; None when there is no workspace here (the caller does it as before)."""
    try:
        from .off_window import kernel_root, run_alone
    except Exception:  # noqa: BLE001
        return None
    root = kernel_root(host)
    if root is None:return None

    def work():
        from .engineering_kernel import Kernel, operator
        return Kernel(root).dispatch(operation, {}, operator())
    return work, run_alone


def press(host, then=None):
    """HALT: hold her work, stop what of hers runs, stop her hand, show the moment, say what was stopped. 1.0 F3: her hand,
    AGENT-01's older work and the moment stop at once here; the hold itself (each assignment's stop, the model's turns, the
    sandboxes) is made on a thread of its own, and her words come when it has landed (then(out), when given)."""
    out = {'held': False, 'stopped': [], 'held_work': [], 'hand': False, 'turns': 0, 'jobs': [], 'words': '', 'error': ''}
    hand = getattr(host, 'her_hand', None)
    try:
        if hand is not None and hand.active():
            hand.stop('HALT');out['hand'] = True
    except Exception:  # noqa: BLE001
        pass
    driver = getattr(host, 'agent_driver', None)      # 1.0 K3: AGENT-01's older assignments pause, as Stop all pauses them
    try:
        if driver is not None:driver.pause_all('HALT')
    except Exception:  # noqa: BLE001
        pass
    column = getattr(host, 'her_column', None)
    if column is not None:column.seen_held = True      # the column's own watch on the hold must not show the moment twice
    try:
        from .her_column_qt import moment
        moment(host, 'halt')
    except Exception:  # noqa: BLE001
        pass

    def landed(answer, error):
        try:_landed(answer, error)
        finally:
            if then is not None:then(out)

    def _landed(answer, error):
        if error is not None:answer = {'ok': False, 'error': {'message': str(error)[:200] or type(error).__name__}}
        if (answer or {}).get('ok'):
            report = answer['result']
            out.update(held=True, stopped=list(report.get('stopped') or ()), held_work=list(report.get('held_work') or ()),
                       turns=int(report.get('turns') or 0), jobs=list(report.get('jobs') or ()))
        else:
            err = (answer or {}).get('error') or {}
            out['error'] = str(err.get('message') if isinstance(err, dict) else err)[:200] or 'refused'
        if out['held']:
            words = WORDS['stopped'] % _names(out['stopped']) if out['stopped'] else (WORDS['nothing_turns'] if out['turns'] or out['jobs'] else WORDS['nothing'])
            if out['held_work']:words += WORDS['held'] % _names(out['held_work'][:3])
            if (out['turns'] or out['jobs']) and out['stopped']:words += WORDS['turns']
        else:
            words = WORDS['not_held'] % out['error']
        if out['hand']:words += WORDS['hand']
        out['words'] = words
        _say(host, words)
        _refresh(host)
    alone = _alone(host, 'halt.press')
    if alone is None:      # as before, here
        kernel, owner = _kernel(host)
        try:landed(kernel.dispatch('halt.press', {}, owner), None)
        except Exception as exc:  # noqa: BLE001 - said in words, and the rest still stops what it can
            landed(None, exc)
        return out
    work, run_alone = alone
    run_alone(work, landed, name='graphite-halt')
    return out


def release(host, then=None):
    """RESUME: lift HALT's hold. Nothing that was stopped is started again here. 1.0 F3: lifted on a thread of its own; her
    words when it has landed."""
    result = {'released': False, 'words': ''}

    def landed(answer, error):
        try:_landed(answer, error)
        finally:
            if then is not None:then(result)

    def _landed(answer, error):
        if error is not None:answer = {'ok': False, 'error': {'message': str(error)}}
        if (answer or {}).get('ok'):
            words = WORDS['released'];done = True
            if (answer.get('result') or {}).get('jobs_held'):words += WORDS['released_jobs']
        else:
            err = (answer or {}).get('error') or {}
            why = str(err.get('message') if isinstance(err, dict) else err or 'refused')
            words = WORDS['not_released'] % why.split(': ', 1)[-1][:200];done = False
        column = getattr(host, 'her_column', None)
        if column is not None and done:column.seen_held = False
        result.update(released=done, words=words)
        _say(host, words)
        _refresh(host)
    alone = _alone(host, 'halt.release')
    if alone is None:
        kernel, owner = _kernel(host)
        try:landed(kernel.dispatch('halt.release', {}, owner), None)
        except Exception as exc:  # noqa: BLE001
            landed(None, exc)
        return result
    work, run_alone = alone
    run_alone(work, landed, name='graphite-resume')
    return result


def _refresh(host):
    button = getattr(getattr(getattr(host, 'shell2', None), 'top', None), 'halt', None)
    try:
        if button is not None:button.refresh()
    except Exception:  # noqa: BLE001
        pass
    column = getattr(host, 'her_column', None)
    try:
        if column is not None:
            from . import floor;floor.column_soon(column)      # 1.0 F3: read again off the window's thread
    except Exception:  # noqa: BLE001
        pass
