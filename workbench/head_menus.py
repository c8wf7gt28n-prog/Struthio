"""1.1 K0 · the head's six menus: File, Edit, View, Go, Tools, Help, over the same actions as 1.0's eight.

DESIGN_DIRECTION_1.1.md section 2: the head (32 px) says what can be done here, in the words a Windows hand looks for.
1.0's eight menus (Work, Revise, Tools, Arrange, Commands, Rules, Properties, Guide; menus2) carried every action; the six
carry the same actions, the same QAction objects with the same keys, and nothing is lost (MOVED says where each went; the
test checks every 1.0 row is still on a head menu). menus2.rebuild lays the rows out from LAYOUT and asks add() for the rows
that are K0's own (the details pane, the views, and the old Rules rows split between View and Tools).

Kas's rules (Kasandra's hand), HALT and the Master Stop keep their own rows (Tools); HALT and Apps stay in the head itself.
Show keys (W1) lives in View now and still turns every printed key off.
"""
from __future__ import annotations

HEAD = ('File', 'Edit', 'View', 'Go', 'Tools', 'Help')

# View: the window and its panes; Go: the places (1.0's Arrange places); Tools: the tools, the commands, her rules and the stop.
VIEW = ['@details', '@views', None, 'inspector', '@slate_panel', None,
        'fullscreen', 'reading', '@appearance', '@artwork', '@buttons', 'prose_more', 'prose_less', None,
        'wrap', 'split_editor', 'pin', 'reopen', None,
        '@log', '@console_sizes', '@cabinet', '@machine_refresh', None,      # 1.1 B4: Log, the foot's Log mode, has its home in View
        '@show_keys', 'reset']
GO = ['home', '@field', '@files', '@library', '@project_desk', '@changes', '@continuing', '@deployment', '@agenda']
TOOLS = ['@explore', 'discovery', 'algorithms', 'atlas', '@work_copy', '@utility', 'doctor', '@computer', '@pills', None,
         '@commands', None,
         '@hand', 'master_stop', None,
         'ledger_settings', '@dos_words', '@bin_name', None,
         '@engineering', '@service']
COMMANDS = ['ledger_commands', '@run_operation', '@chain', '@chain_desk', '@type_to', 'palette']
KEYS = frozenset(('@details', '@views', '@artwork', '@buttons', '@show_keys', '@commands', '@hand', '@dos_words', '@bin_name',
                  '@log'))      # 1.1 B4: '@log'

# Old place -> new place (the owner reads this table; the release notes carry it).
MOVED = (
    ('Work (every row, in its order: New File … Recover Unsaved Work, then Lock … Exit Graphite)', 'File'),
    ('Revise (every row: Undo … Go to Line)', 'Edit'),
    ("Arrange: Today, Field, Files, Library, Project Desk, Changes, Continuing work, Exchange & deployment, Graphite's Agenda", 'Go'),
    ('Arrange: Kasandra (her column)', 'View'),
    ('Arrange: Console, Cabinet, Refresh Machine View, Full Screen, Reading and Layout…, Appearance, Larger / Smaller prose, '
     'Word Wrap, Split Editor, Pin / Unpin workspace, Reopen deferred tabs, Reset Window Layout', 'View'),
    ('Tools (every row: Explore capabilities … STOP / KILL all Graphite operations…, Engineering)', 'Tools'),
    ('Commands (every row: Graphite Commands…, Run an operation…, Chain Menu, Constructed chain, Writing Line, Command Palette…, '
     'Favorite commands)', 'Tools ▸ Commands'),
    ('Rules: Graphite Settings…', 'Tools'),
    ("Rules: Kasandra's hand (her rules)", 'Tools'),
    ("Rules: DOS words, The bin's name", 'Tools'),
    ('Rules: Desk artwork, Buttons', 'View'),
    ('Rules: Show keys', 'View'),
    ('Properties: Inspector', 'View'),
    ('Properties: This Computer…, Pills and Paired Computers…', 'Tools'),
    ('Guide (every row: Getting Started … About Graphite)', 'Help'),
    ('new: Details pane (Alt+P), List, Icons, Board', 'View'),
    ('Commands: Writing Line ▸ Log (Alt+6)', 'View ▸ Log'),      # 1.1 B4
)


def layout(file_rows, edit_rows, help_rows):
    """(group key, row keys) for menus2.rebuild: the six head menus (File, Edit and Help keep menus2's own lists) and the
    Commands menu that Tools holds."""
    return (('File', file_rows), ('Edit', edit_rows), ('View', VIEW), ('Go', GO), ('Commands', COMMANDS), ('Help', help_rows),
            ('Tools', TOOLS))      # Tools last, as in 1.0: its Engineering ▸ More takes whatever no menu placed before it


def _holder(host):
    """A menu never shown that owns the rows W1 and E1 make for the old Rules menu, made once per window."""
    held = getattr(host, '_k0_rule_rows', None)
    if held is None:
        from PySide6.QtWidgets import QMenu
        from .windows_keys_qt import rules_lines
        from .explorer_qt import rules_lines as bin_lines
        holder = QMenu(host);line, words = rules_lines(host, holder);bin_name = bin_lines(host, holder)
        held = host._k0_rule_rows = {'holder': holder, 'show_keys': line, 'dos_words': words, 'bin_name': bin_name}
    return held


def view_actions(host):
    """View ▸ List, Icons, Board: the Explorer's three views (the same set_view as the centre bar's switch)."""
    made = getattr(host, '_k0_views', None)
    if made is None:
        from PySide6.QtGui import QAction, QActionGroup
        from .explorer import VIEWS, VIEW_WORDS
        group = QActionGroup(host);group.setExclusive(True);made = {}
        for view in VIEWS:
            a = QAction(VIEW_WORDS[view], host);a.setCheckable(True);group.addAction(a);made[view] = a
            a.setToolTip('Show the place in %s' % VIEW_WORDS[view]);a.setStatusTip(a.toolTip())
            a.triggered.connect(lambda checked=False, view=view: set_view(host, view))
        host._k0_views = made
    return list(made.values())


def set_view(host, view):
    explorer = getattr(host, 'explorer', None)
    return explorer.set_view(view) if explorer is not None else False


def current_view(host):
    explorer = getattr(host, 'explorer', None)
    if explorer is None:return ''
    if explorer.in_front():return explorer.view
    board = getattr(getattr(host, 'field_page', None), 'board', None)
    try:
        return 'board' if board is not None and board.isVisible() else ''
    except RuntimeError:
        return ''


def sync(host):
    """The checks say what is true now (View opens)."""
    view = current_view(host);has = getattr(host, 'explorer', None) is not None
    for key, a in (getattr(host, '_k0_views', None) or {}).items():
        a.setEnabled(has);a.setChecked(key == view)
    pane = getattr(host, 'details_pane', None);a = getattr(host, 'a_details', None)
    if a is not None:a.setChecked(bool(pane is not None and pane.wanted))


def add(host, menu, key, placed, groups):
    """menus2.rebuild's rows that are K0's own. True when key was one of them (placed or not)."""
    if key not in KEYS:return False
    sub = None
    if key == '@details':
        from .details_pane_qt import action
        a = action(host);menu.addAction(a);placed.add(a)
    elif key == '@views':
        for a in view_actions(host):menu.addAction(a);placed.add(a)
        if not menu.property('k0Synced'):
            menu.setProperty('k0Synced', True);menu.aboutToShow.connect(lambda host=host:sync(host))
    elif key == '@artwork':
        from .boss_qt import appearance_menu
        sub = appearance_menu(host)
    elif key == '@buttons':
        from .tool_faces import menu as buttons_menu
        sub = buttons_menu(host)
    elif key == '@hand':      # her rules: how far she acts by herself, a row of its own
        from .shell2 import hand_menu
        sub = hand_menu(host)
    elif key == '@show_keys':
        line = _holder(host)['show_keys'];menu.addAction(line);placed.add(line)
    elif key == '@dos_words':
        sub = _holder(host)['dos_words']
    elif key == '@bin_name':
        sub = _holder(host)['bin_name']
    elif key == '@log':      # 1.1 B4: View ▸ Log (Alt+6), the same action as the foot's Log word; the Log in the working area once the foot folds
        a = (getattr(host, 'a_talk', None) or {}).get('log')
        if a is not None:menu.addAction(a);placed.add(a)
    elif key == '@commands':
        sub = groups.get('Commands')
        if sub is not None:sub.setTitle('Commands')
    if sub is not None:
        menu.addMenu(sub);placed.add(sub.menuAction())
    return True


def words_of(action):
    """A row's words as shown, without the key mark (&) or a key written after a tab."""
    return action.text().replace('&&', '\0').replace('&', '').replace('\0', '&').split('\t')[0].strip()


def rows(menu, depth=0, subs=None):
    """Every row of a menu and its submenus as (depth, words, action), separators left out. (QAction.menu() is not used: in
    PySide it can take ownership; submenus are found among the application's menus by their title row.)"""
    from PySide6.QtWidgets import QApplication, QMenu
    from shiboken6 import isValid
    if subs is None:
        subs = {}
        for m in QApplication.allWidgets():
            if isinstance(m, QMenu) and isValid(m):subs.setdefault(m.menuAction(), m)
    out = []
    for a in menu.actions():
        if not isValid(a) or a.isSeparator():continue
        out.append((depth, words_of(a), a))
        sub = subs.get(a)
        if sub is not None and sub is not menu and depth < 4:out.extend(rows(sub, depth + 1, subs))
    return out
