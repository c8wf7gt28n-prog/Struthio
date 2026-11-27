"""Graphite 1.0 F3 · Search as a power user searches (the walkthroughs' faults, item 7; X4's session 2).

X4 searched "invoice" with 48 invoices in ~/Downloads and found nothing; "startup duration" found nothing though both words
stand on one finding; "open" on a found record went to the old Cabinet record tab, and Back did not come back to the
results. Here, for the console's Search (console_qt.run_find):

    words(text)           the words typed, each matched on its own (all of them, in any order), never as one phrase
    holds(text, words)    whether every word is in a name or a line
    home_names(text)      files and folders of your home found by their names (hidden ones and Graphite's own workspace
                          left out; a walk with a budget, so the window never waits on a large home: what was not looked
                          through is said)
    records(host, text)   the cabinet's and the desk's rows by every word, each name once (a desk object before a cabinet
                          record of the same name: the board's is the one that opens)
    open_record / open_home
                          a hit is focused on the board as a click in the tree focuses it (the history notes it came from
                          Search), and the results stay in front in the console
    back_to_results(host) Back from a place Search opened brings the results in front again (living_nav_qt.back calls it)

Search only reads: nothing here writes a record, and a name is read from the file system, never a file's contents.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

HOME_BUDGET_MS = 80          # the walk of your home's names stops after this long (the rest is said, not hidden)
HOME_MOST = 20000            # names looked at, at most
HOME_DEPTH = 7               # folders deep, at most
HOME_HITS = 30


def words(text):
    return [w for w in str(text or '').casefold().split() if w]


def holds(text, wanted):
    text = str(text or '').casefold()
    return all(w in text for w in wanted)


def longest(text):
    """The longest of the words (what a phrase-matching reader is asked for; the rest are matched here)."""
    ws = words(text)
    return max(ws, key=len) if ws else ''


def home_names(host, text, limit=HOME_HITS):
    """[(path, is_folder)], and '' or the words saying the walk stopped before the end of your home."""
    wanted = words(text)
    if not wanted:return [], ''
    try:
        from .home_reach import home
        top = Path(home())
    except Exception:  # noqa: BLE001
        top = Path.home()
    skip = set()
    try:skip.add(str(Path(getattr(host, 'root', '')).resolve()))      # Graphite's own workspace: its Files are Search's FILES
    except OSError:
        pass
    found = [];seen = 0;stopped = '';began = time.monotonic()
    queue = [(top, 0)]
    while queue:
        folder, depth = queue.pop(0)
        try:entries = list(os.scandir(folder))
        except OSError:
            continue
        entries.sort(key=lambda e: e.name.casefold())
        for entry in entries:
            seen += 1
            if entry.name.startswith('.'):continue
            try:is_dir = entry.is_dir(follow_symlinks=False)
            except OSError:
                is_dir = False
            if is_dir and str(Path(entry.path).resolve()) in skip:continue
            if holds(entry.name, wanted):
                found.append((Path(entry.path), is_dir))
                if len(found) >= limit:return found, 'the first %d found' % limit
            if is_dir and depth + 1 < HOME_DEPTH:queue.append((Path(entry.path), depth + 1))
        if seen >= HOME_MOST or (time.monotonic() - began) * 1000 > HOME_BUDGET_MS:
            stopped = 'looked through the first %d names of your home' % seen if queue else ''
            break
    return found, stopped


def records(host, text, limit=15):
    """The tree's rows (the cabinet's records and the desk's objects) whose name and kind hold every word; each name once."""
    wanted = words(text)
    page = getattr(host, 'cabinet_page', None)
    nodes = (page.model or {}).get('nodes', []) if page is not None else []
    from .living_nav_qt import LIVING
    hits = [n for n in nodes if wanted and holds('%s %s' % (n.get('label', ''), n.get('role', '')), wanted)
            and n.get('role') not in ('drawer', 'folder_view') and not str(n.get('id', '')).startswith('living:fs:')]
    try:      # the desk's objects by what they say too (a sheet's lines, a finding's role), not their names alone
        from .living_nav_qt import living
        nav = living(host);desk = getattr(getattr(nav, 'desk_raw', None), 'objects', None) or ()
        named = {str(n.get('id')) for n in hits}
        for obj in desk:
            ident = LIVING + str(obj.id)
            if ident in named or ident not in (nav.nodes or {}):continue
            said = ' '.join(str(x) for x in (obj.title, obj.kind, obj.role, obj.where, ' '.join(str(l) for l in obj.lines or ())))
            if wanted and holds(said, wanted):
                node = nav.nodes[ident];hits.append(dict(node, role=node.get('role') or obj.kind))
    except Exception:  # noqa: BLE001 - the names alone, as before
        pass
    best = {}
    for n in hits:      # a desk object before a cabinet record of the same name; one row a name
        name = str(n.get('label', '')).casefold()
        mine = str(n.get('id', '')).startswith(LIVING)
        if name not in best or (mine and not str(best[name].get('id', '')).startswith(LIVING)):best[name] = n
    order = {id(n): i for i, n in enumerate(hits)}
    return sorted(best.values(), key=lambda n: (not str(n.get('id', '')).startswith(LIVING), order.get(id(n), 0)))[:limit]


def open_record(host, node_id):
    """A found row: a desk object is focused on the board; a cabinet record with the name of a desk object, that object;
    else the record opens where it belongs, as before. The results stay in front."""
    from .living_nav_qt import LIVING, living
    nav = living(host)
    if nav is not None:
        target = node_id if str(node_id).startswith(LIVING) else None
        if target is None:
            node = (nav.nodes or {}).get(node_id) or {}
            label = str(node.get('label', '')).casefold()
            target = next((i for i, n in (nav.nodes or {}).items() if str(i).startswith(LIVING) and not str(i).startswith('living:fs:')
                           and n.get('role') not in ('drawer', 'folder_view') and str(n.get('label', '')).casefold() == label), None) if label else None
        if target is not None and nav.go_node(target, via='search'):
            keep_results(host);return True
    from .console_qt import reveal_record
    reveal_record(host, node_id)
    keep_results(host)
    return False


def open_home(host, path):
    """A file or folder of your home found by its name: focused on the board as a click in the tree focuses it."""
    from .living_nav_qt import living
    nav = living(host);path = Path(path)
    if nav is None:return False
    found = nav.call('objects.get', {'path': str(path)})
    if not found or not found.get('id'):
        host.statusBar().showMessage('%s could not be focused: %s' % (path.name, nav.problem or 'not read'), 6000);return False
    if nav.computer is not None:nav.computer.hold(found)
    nav.go(found['id'], 'search', 'board', title=path.name)
    keep_results(host)
    return True


def keep_results(host):
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, lambda: back_to_results(host))


def back_to_results(host):
    """The console's Search results in front again (they are kept in its page; nothing is searched again)."""
    console = getattr(host, 'console', None)
    if console is None or getattr(host, '_closing', False):return False
    try:
        if console.mode != 'find':console.set_mode('find')
        console.open(focus=False)
    except Exception:  # noqa: BLE001 - the results stay where they are
        return False
    return True
