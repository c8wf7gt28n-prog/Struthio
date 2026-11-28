"""The Guide menu's pages for Graphite 1.0 (slice X2): the Living Desktop, Kasandra as the ghost in the shell, and the
owner's first evening with 1.0 on the ThinkPad.

Each page is a Markdown file of the program, opened read-only in the universal viewer (host.open_in_viewer), the same form
as the Guide's other pages (Getting Started, An Evening with Kas's Mind). menus2 makes one QAction for each entry here and
places them in the Guide menu after What's New.

What the pages say is read on screen: "Apps", never the other word; no keyboard shortcut named; a pipeline is "a line";
her name is Kasandra (Kas); every colour named has its word or shape (tools/name_sweep.GUIDE_PAGES reads them).
"""
from __future__ import annotations

from pathlib import Path

# (menu key, the words in the Guide menu, the page in the program, the tip)
PAGES = (
    ('@living_desktop', 'The Living Desktop', 'docs/GUIDE_LIVING_DESKTOP.md',
     'The whole desktop on one screen: the session, Apps, Files from This computer, the Machine, the board, the foot, HALT'),
    ('@kas_ghost', 'Kas, the Ghost in the Shell', 'docs/GUIDE_KASANDRA.md',
     'Her column, how she does a task, grants and HALT, her hand in your apps, the network, her model'),
    ('@first_evening', 'Your First Evening with 1.0', 'docs/ACCEPTANCE_1.0.md',
     "The acceptance evening on the ThinkPad: the install, your paper's test, her model, the day on Rail Demo, what to send back"),
)
KEYS = tuple(key for key, _, _, _ in PAGES)


def page(program, key):
    """The page's file in the program folder for a menu key, or None."""
    for k, _, path, _ in PAGES:
        if k == key:return Path(program) / path
    return None


def actions(host, program):
    """One action per page, owned by the window: {menu key: QAction}, each opening its page in the viewer, with its tip."""
    from PySide6.QtGui import QAction
    out = {}
    for key, words, path, tip in PAGES:
        a = QAction(words, host)
        a.triggered.connect(lambda checked=False, path=path: host.open_in_viewer(Path(program) / path))
        a.setToolTip(tip);a.setStatusTip(tip);out[key] = a
    return out
