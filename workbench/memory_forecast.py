"""Short-horizon loss of uncommitted RAM, shared by admission and replay."""


SAMPLE_INTERVAL_SECONDS = 1
MAX_SAMPLE_AGE_SECONDS = 8
HALF_LIFE_SECONDS = 2
HORIZON_SECONDS = 4
MAX_FORECAST_WAIT_SECONDS = 8

WAIT_REASON = "Forecast shared-memory headroom is below this background job's memory budget"


def _number(value):
    return type(value) in (float, int) and -(2**63) <= value < 2**63


def _headroom(value):
    return _number(value) and value >= 0


def _valid(state):
    return (isinstance(state, dict) and _number(state.get('observed_at'))
            and _headroom(state.get('headroom_bytes'))
            and (state.get('loss_bytes_per_second') is None or _number(state['loss_bytes_per_second'])))


def observe(previous, observed_at, headroom_bytes):
    """Update a time-weighted slope at most once per second. Never rewind a sample."""
    if not _number(observed_at) or not _headroom(headroom_bytes):
        return previous
    loss = None
    if _valid(previous):
        elapsed = observed_at - previous['observed_at']
        if elapsed < SAMPLE_INTERVAL_SECONDS:
            return previous
        if elapsed <= MAX_SAMPLE_AGE_SECONDS:
            change = (previous['headroom_bytes'] - headroom_bytes) / elapsed
            prior_loss = previous.get('loss_bytes_per_second')
            weight = 1 - 2 ** (-elapsed / HALF_LIFE_SECONDS)
            loss = change if prior_loss is None else prior_loss + weight * (change - prior_loss)
    return dict(observed_at=observed_at, headroom_bytes=headroom_bytes, loss_bytes_per_second=loss)


def evaluate(state, observed_at, headroom_bytes, requested_bytes, deferred_since=None):
    """Forecast from current headroom. The caller must check current capacity first."""
    room_known = _headroom(headroom_bytes) and _headroom(requested_bytes)
    eligible = (room_known and _number(observed_at) and _valid(state)
                and state.get('loss_bytes_per_second') is not None
                and 0 <= observed_at - state['observed_at'] <= MAX_SAMPLE_AGE_SECONDS)
    loss = max(0, state['loss_bytes_per_second']) if eligible else 0
    projected = max(0, int(headroom_bytes - HORIZON_SECONDS * loss)) if room_known else None
    margin = projected - requested_bytes if room_known else None
    outcome = 'admit'
    if eligible and margin < 0:
        if not _number(deferred_since) or deferred_since > observed_at:
            deferred_since = observed_at
        outcome = ('defer' if observed_at - deferred_since < MAX_FORECAST_WAIT_SECONDS
                   else 'wait_budget_elapsed')
    return dict(eligible=eligible, projected_headroom_bytes=projected, margin_bytes=margin,
                loss_bytes_per_second=loss, horizon_seconds=HORIZON_SECONDS,
                outcome=outcome, reason=WAIT_REASON if outcome == 'defer' else None,
                deferred_since=deferred_since)
