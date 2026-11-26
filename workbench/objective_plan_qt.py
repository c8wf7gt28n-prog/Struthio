"""An objective asked in her column, offered as a plan (Graphite 1.0, K4): the window's side of objective_plan.py.

Your words reach her from her column's ask line and from the writing line with Kasandra chosen (shell2.SlateFace.ask). When
they read as an objective (objective_plan.reads_as_objective: a verb of hers that changes something, or several clauses of
her verbs), they are taken here: your words go in the exchange, her line says she is planning, and the plan is made off the
window's thread (objective.offer, in a Kernel of its own on the same workspace: the desk's plan, or the model's, checked step
by step). Then her words say the steps and how each goes ahead, the plan stands in ACTIVE WORK, and its next press is in NEXT
STEPS (Carry on for the reads, Authorise step n for a change). Nothing is started by the offer.

"that one", "this" and "it" are the object in focus (the living desktop's navigation, L1, else the card selected on the
Field); "the earlier one" is the one in focus before it.
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QTimer

POLL_MS = 250


def focus_of(host):
    """(the object in focus, the one in focus before it), as ids; '' when there is none."""
    focus = earlier = ''
    nav = getattr(getattr(host, 'living_nav', None), 'nav', None)
    if nav is not None:
        try:
            focus = nav.focus or ''
            before = nav.peek(-1)
            earlier = (before.focus if before is not None else '') or ''
        except Exception:  # noqa: BLE001 - no navigation to read: the Field's selection
            focus = earlier = ''
    if not focus and getattr(host, '_field_active', False):
        view = getattr(getattr(host, 'field_page', None), 'view', None)
        try:
            chosen = view.selected() if view is not None else None
            if chosen is not None:
                target = chosen.target if isinstance(getattr(chosen, 'target', None), dict) else {}
                focus = str(target.get('id') or chosen.id)
        except Exception:  # noqa: BLE001
            pass
    return str(focus)[:400], str(earlier)[:400]


def asked(face, text):
    """True when the words were taken as an objective: the plan is being made and will be offered in her column."""
    from . import objective_plan
    if getattr(face, '_objective_planning', False) or not objective_plan.reads_as_objective(text):return False
    from .engineering_kernel import Kernel, operator
    from .her_column_qt import _kernel
    host = face.host
    focus, earlier = focus_of(host)
    kernel, _ = _kernel(host)
    root = kernel.root
    face.thing = None;face.mine(text)
    card = face.say(objective_plan.say('planning'))
    result = {}

    def work():
        try:
            result['answer'] = Kernel(root).dispatch('objective.offer', {'objective': str(text).strip()[:2000], 'focus': focus,
                                                                         'earlier': earlier}, operator())
        except Exception as exc:  # noqa: BLE001 - said in her words, never raised into the window
            result['answer'] = {'ok': False, 'error': {'message': str(exc)}}

    thread = threading.Thread(target=work, name='her-plan', daemon=True)
    face._objective_planning = True
    thread.start()

    def done():
        if thread.is_alive():
            QTimer.singleShot(POLL_MS, done);return
        face._objective_planning = False
        answer = result.get('answer') or {}
        if answer.get('ok'):words = (answer.get('result') or {}).get('words') or objective_plan.say('no_plan')
        else:words = objective_plan.say('refused_offer', why=str((answer.get('error') or {}).get('message') or 'refused').rstrip('.')[:240])
        try:card.set_text(words)
        except Exception:  # noqa: BLE001 - the card went with the window's exchange: said again
            try:face.say(words)
            except Exception:  # noqa: BLE001
                pass
        column = getattr(host, 'her_column', None)
        if column is not None:
            try:from . import floor;floor.column_soon(column)      # 1.0 F2: read again off the window's thread
            except Exception:  # noqa: BLE001 - her column reads it again at its next tick
                pass
        try:face.fit_soon() if hasattr(face, 'fit_soon') else None
        except Exception:  # noqa: BLE001
            pass

    QTimer.singleShot(POLL_MS // 2, done)
    return True
