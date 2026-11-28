"""Graphite 1.1 N1 · Night is a phosphor monitor: the two choices it keeps, the phosphor and the CRT effects.

The owner, 28 Nov 2026: night mode is "to look like old computers that only had orange and black / green and black
monitors....but updated to 2026 but still old school modern", and then "Screen burns and all the fun". So Night is one
phosphor on a near-black ground, Amber (the default) or Green, chosen under View ▸ Appearance as "Night: Amber" or
"Night: Green"; and the CRT effects (burn-in, afterglow, warm-up, scanlines and a vignette, a block cursor and a faint bloom,
crt_qt) are one setting under View ▸ Appearance ▸ CRT effects: Off, Subtle (the default) or Full. They never cost legibility,
and Reduce motion turns off what moves.

Both are the window's own presentation preferences, kept in Graphite's session file beside 'appearance' (keys 'phosphor'
and 'crt'), read once at the start like the look (boss_theme imports this before any window). In the environment,
GRAPHITE_PHOSPHOR (amber, green) and GRAPHITE_CRT (off, subtle, full) win, as GRAPHITE_APPEARANCE does for the look; and
GRAPHITE_APPEARANCE=night-green (or night-amber) asks for Night in that phosphor. No Qt here: the session reads the lists.
"""
from __future__ import annotations

import json
import os

PHOSPHOR_KEY, CRT_KEY = 'phosphor', 'crt'
PHOSPHORS = (('duo', 'Night: Duo'), ('amber', 'Night: Amber'), ('green', 'Night: Green'))      # 1.1 N1duo: Duo, green and amber with grey
PHOSPHOR_DEFAULT = 'duo'      # 1.1 N1duo: the default Night (N1: amber); a phosphor the owner chose and saved is kept
CRT_LEVELS = (('off', 'Off'), ('subtle', 'Subtle'), ('full', 'Full'))
CRT_DEFAULT = 'subtle'
ASKED_LOOKS = {'night-duo': 'duo', 'night-amber': 'amber', 'night-green': 'green'}      # 1.1 N1duo: night-duo      # GRAPHITE_APPEARANCE words that name a phosphor


def phosphor_value(value):
    return value if isinstance(value, str) and value in dict(PHOSPHORS) else None


def crt_value(value):
    return value if isinstance(value, str) and value in dict(CRT_LEVELS) else None


def session_path(environ=None):
    environ = os.environ if environ is None else environ
    override = environ.get('ARC1_WORKBENCH_CONFIG_HOME')
    base = override if override else os.path.join(environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config')), 'arc1-workbench')
    return os.path.join(base, 'session-r10.json')


def _saved(key, environ=None, path=None):
    try:
        with open(path or session_path(environ), encoding='utf-8') as stream:
            data = json.load(stream)
        return data.get(key) if isinstance(data, dict) else None
    except (OSError, ValueError, AttributeError, RecursionError):
        return None


def chosen_phosphor(environ=None, path=None):
    """'duo', 'amber' or 'green': GRAPHITE_PHOSPHOR, else a phosphor named in GRAPHITE_APPEARANCE, else the session's, else Duo."""
    environ = os.environ if environ is None else environ
    wanted = str(environ.get('GRAPHITE_PHOSPHOR', '')).strip().lower()
    if phosphor_value(wanted):return wanted
    asked = ASKED_LOOKS.get(str(environ.get('GRAPHITE_APPEARANCE', '')).strip().lower())
    if asked:return asked
    return phosphor_value(_saved(PHOSPHOR_KEY, environ, path)) or PHOSPHOR_DEFAULT


def chosen_crt(environ=None, path=None):
    """'off', 'subtle' or 'full': GRAPHITE_CRT, else the session's, else Subtle."""
    environ = os.environ if environ is None else environ
    wanted = str(environ.get('GRAPHITE_CRT', '')).strip().lower()
    if crt_value(wanted):return wanted
    return crt_value(_saved(CRT_KEY, environ, path)) or CRT_DEFAULT


def asked_night(environ=None):
    """True when GRAPHITE_APPEARANCE names Night in a phosphor (night-amber, night-green)."""
    environ = os.environ if environ is None else environ
    return str(environ.get('GRAPHITE_APPEARANCE', '')).strip().lower() in ASKED_LOOKS
