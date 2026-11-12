"""In-process work-order authority: never populated from client parameters."""
from contextlib import contextmanager
from contextvars import ContextVar

_SCOPE = ContextVar('ledger_work_order_scope', default=None)


@contextmanager
def entered(value):
    token = _SCOPE.set(value)
    try: yield
    finally: _SCOPE.reset(token)


def current(): return _SCOPE.get()


def check(db=None):
    value = current()
    if value: value['guard'](db)


def proposal_id():
    value = current()
    return value['proposal'] if value else None
