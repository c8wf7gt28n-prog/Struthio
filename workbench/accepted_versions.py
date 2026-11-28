"""1.1 PK1: which versions of Graphite's desktop libraries are accepted, for the doctor and the readiness check.

The folder install pins wheels (PySide6 6.8.3, cryptography 50.0.2). The Debian package uses Debian 13's own
python3-pyside6.* (6.8.2.1, Qt 6.8.2) and python3-cryptography (43.0.0), which ran Graphite with the same test results
(packaging audit, 27 Nov 2026). Both are accepted: the pin is PINNED, a tested Debian version is ACCEPTED, anything
else is DIFFERENT_VERSION.
"""
from __future__ import annotations

import re

PINS = {'PySide6': '6.8.3', 'cryptography': '50.0.2'}
ACCEPTED = {'PySide6': 'PySide6 6.8.2 or a later 6.8 (Debian 13: 6.8.2.1)',
            'cryptography': 'cryptography 43 or later (Debian 13: 43.0.0)'}
QT_ACCEPTED = 'Qt 6.8.2 or a later 6.8'


def numbers(version):
    """The leading numeric parts of a version: '6.8.2.1' -> (6, 8, 2, 1); '43.0.0+deb13u1' -> (43, 0, 0)."""
    found = re.match(r'\d+(?:\.\d+)*', str(version or '').strip())
    return tuple(int(x) for x in found.group(0).split('.')) if found else ()


def accepted(name, version):
    n = numbers(version)
    if not n: return False
    if name == 'PySide6': return n[:2] == (6, 8) and len(n) >= 3 and n[2] >= 2
    if name == 'cryptography': return n[0] >= 43
    return str(version) == PINS.get(name)


def state(name, version):
    if version is None: return 'MISSING'
    if version == PINS.get(name): return 'PINNED'
    return 'ACCEPTED' if accepted(name, version) else 'DIFFERENT_VERSION'


def qt_ready(version):
    """Qt itself (qVersion()): the pinned 6.8.3 or Debian 13's 6.8.2 and later 6.8 releases."""
    n = numbers(version)
    return len(n) >= 3 and n[:2] == (6, 8) and n[2] >= 2
