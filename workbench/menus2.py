"""Eight desktop menus over the original actions, shortcuts and menu objects.

File is files, Edit is text, View is the window, Tools is Ledger's tools, Help is help. Every command from the older
engineering desktop (builds, cartridges, hardware workspaces, the phone link…) lives in one place, Tools › Engineering,
shown when a project is attached. Nothing is removed: each action keeps its shortcut and is found by Ctrl K.

Menus are words, with no pictures: the one mark kept is a graphite dot beside Master Stop. (paper_icon remains for
any place that must show an icon: the old icon's outline in graphite, nothing else.)
The menus are the same QMenu objects as before (the release checks hold on to them); only what is inside them changes.
"""
from __future__ import annotations
from PySide6.QtGui import QAction, QColor, QIcon, QImage, QPainter, QPixmap

GRAPHITE = '#6c675e'
# Display proposals from the Interface Companion; stable dictionary keys,
# QMenu instances, QAction identities and keyboard commands are preserved.
DISPLAY_TITLES={'File':'Work','Edit':'Revise','Tools':'Tools','Options':'Arrange',
                'Commands':'Commands','Settings':'Rules','Properties':'Properties','Help':'Guide'}
# File: getting files in and working on them. Edit: text. View: where you are and how the window looks.
# Tools: who you type to, the chain menu, and Ledger's own tools. Help: how to begin, and what is new.
FILE = ['new', '@new_idea', '@new_project', 'open', 'viewer', 'quick', '@recent', None, '@receive', '@import', '@export', '@work_copy', None, 'save', 'save_all', 'close', None, 'recovery',
        None, '@leave']      # 0.7.0: leaving (Log out, Exit Graphite, Restart, Shut down) at the foot of the first menu; it was the System menu's last group
EDIT = ['undo', 'redo', None, 'cut', 'copy', 'paste', 'select', None, 'find', 'find_next', 'replace', 'goto']
VIEW = ['home', '@field', '@files', '@library', '@project_desk', '@changes', '@continuing', '@deployment', '@agenda', '@slate_panel', None, '@console_sizes', '@cabinet', '@machine_refresh', None,
        'fullscreen', 'reading', 'prose_more', 'prose_less', None, 'wrap', 'split_editor', 'pin', 'reopen', None, 'reset']      # Desk artwork is under Rules, once (0.4.9)
TOOLS = ['discovery','algorithms','atlas', '@type_to', '@chain', 'ledger_commands', None,
         'ledger_settings', 'doctor', '@computer', '@pills', None, 'master_stop', None, '@engineering', '@service']
HELP = ['@getting_started', '@whats_new', 'keys', 'setup_guide', None, 'orange_book', None, 'about']
ENGINEERING = [('Projects and code', ['definition', 'completion', 'engineering', 'development', 'ledger', 'desk', 'native_game', 'newgame', 'browse', 'refresh', 'project_search',
                                      'engineering_layout', 'focus_layout', 'object_glass', 'output', 'problems', 'dual', 'developer_tools', 'arcos', 'trace', 'register', 'cartdock']),
               ('Build and run', ['build', 'build_all', 'tests', 'run', 'stop', 'next', 'prev', 'boot', '@targets']),
               ('Cartridges', ['pkg', 'import', 'inspect_cart', 'stream', 'compare']),
               ('Hardware', ['brain_link', 'board', 'native_pcb', 'cad_checks', 'kibot_outputs', 'spice_checks', 'yosys_synthesis', 'fpga_implementation',
                             'hdl_waveforms', 'schematics', 'nor', 'hardware_proof', 'hardware_review', 'budgets', 'readiness', 'hw', 'inventory']),
               ('Knowledge and assets', ['manual', 'database_rom', 'vendor_vault', 'assets', 'genesis', 'clip', 'ledger_activity', 'stacy_knowledge', 'palette']),
               ('Phone link', ['remote_link'])]


def paper_icon(icon, size=18, colour=GRAPHITE):
    """An icon as a single-colour shape: its outline kept, its colours replaced by graphite (transparent stays transparent)."""
    if icon is None or icon.isNull():return QIcon()
    source = icon.pixmap(size * 2, size * 2)
    if source.isNull():return QIcon()
    mask = source.toImage().convertToFormat(QImage.Format_ARGB32_Premultiplied)
    out = QImage(mask.size(), QImage.Format_ARGB32_Premultiplied);out.fill(0)
    p = QPainter(out);p.drawImage(0, 0, mask);p.setCompositionMode(QPainter.CompositionMode_SourceIn);p.fillRect(out.rect(), QColor(colour));p.end()
    pix = QPixmap.fromImage(out);pix.setDevicePixelRatio(2)
    return QIcon(pix)


def dot(colour=GRAPHITE, size=18):
    pix = QPixmap(size * 2, size * 2);pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setBrush(QColor(colour));p.setPen(QColor(colour));p.drawEllipse(size - 7, size - 7, 14, 14);p.end()
    pix.setDevicePixelRatio(2);return QIcon(pix)


def direct_actions(menu):
    """A menu's own items, without its submenus' title items. (QAction.menu() is not used: in PySide it can take ownership.)"""
    from PySide6.QtWidgets import QMenu
    from shiboken6 import isValid
    titles = {m.menuAction() for m in menu.findChildren(QMenu)}
    return [a for a in menu.actions() if isValid(a) and not a.isSeparator() and a not in titles]


def rebuild(host):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMenu, QToolButton
    from .project_context import detached
    from .shell2 import open_destination
    groups = getattr(host, 'menu_groups', None);actions = dict(getattr(host, 'favorite_actions', {}) or {})
    if not groups or not actions:return
    if not getattr(host,'_desktop_eight_menus',False):
        # Keep the original View and Tools QMenus alive for callers holding them.
        # View is now the visible Options menu; its old dictionary alias still works.
        groups['Tools']=groups['Options'];groups['Options']=groups['View']
        for title in ('Commands','Settings','Properties'):groups[title]=QMenu(title,host)
        order=('File','Edit','Tools','Options','Commands','Settings','Properties','Help')
        commands=getattr(host,'ribbon_commands',None)
        if commands is not None:
            for heading in host.command_menus.values():heading.parentWidget().hide()
            host.command_menus={}
            for title in order:
                groups[title].setTitle(title)
                heading=QToolButton(commands);heading.setObjectName('favoriteGroupMenu');heading.setText(title)
                heading.setMenu(groups[title]);heading.setPopupMode(QToolButton.InstantPopup)
                heading.setToolButtonStyle(Qt.ToolButtonTextOnly);heading.setAccessibleName(title+' menu')
                heading.setMinimumHeight(32);commands.layout().addWidget(heading);host.command_menus[title]=heading
            commands.adjustSize();commands.setProperty('paperTight',False)
        host._desktop_eight_menus=True
    for key,title in DISPLAY_TITLES.items():
        groups[key].setTitle(title)
        heading=host.command_menus.get(key)
        if heading is not None:heading.setText(title);heading.setAccessibleName(title+' menu')
    before = list(dict.fromkeys([a for menu in groups.values() for a in direct_actions(menu)] + list(actions.values())))
    if not hasattr(host, 'a_work_copy'):
        def make(text, fn):
            a = QAction(text, host);a.triggered.connect(lambda checked=False:fn());return a
        host.a_work_copy = make('Work on a Copy of a File…', lambda:open_destination(host, 'work_copy'))
        host.a_console = make('Console\tCtrl+`', lambda:host.console.open() if hasattr(host, 'console') else None)
        host.a_library = make('Library', lambda:open_destination(host, 'library:all'))
        host.a_pills = make('Pills and Paired Computers…', lambda:__import__('workbench.pills_qt', fromlist=['show']).show(host))
        host.a_computer = make('This Computer…', lambda:__import__('workbench.computer_qt', fromlist=['show']).show(host))
        host.a_chain = make('Chain Menu\tMenu', lambda:__import__('workbench.chain_menu', fromlist=['open_here']).open_here(host))
        host.a_explore = make('Explore capabilities…',lambda:__import__('workbench.explore_qt',fromlist=['show']).show(host))
        # HATCH DESK D1b: the left pane shows only its tabs, the tree and Trash; the controls it no longer shows are here.
        # Import and Export are where material enters and leaves (the cabinet's transfer words, the same route); the cabinet's
        # Refresh, its Logical / Existing views and the Existing views' catalogue choice are under Arrange ▸ Cabinet; the
        # Machine view's Refresh is under Arrange. D4 adds the trees' right-click for them.
        from .cabinet import TRANSFERS
        def transfer(index):
            page = getattr(host, 'cabinet_page', None)
            if page is not None:page.transfer(TRANSFERS[index])
        host.a_import = make('Import (Ingress)…', lambda:transfer(0));host.a_import.setToolTip(TRANSFERS[0]['description']);host.a_import.setStatusTip(TRANSFERS[0]['description'])
        host.a_export = make('Export (Egress)…', lambda:transfer(1));host.a_export.setToolTip(TRANSFERS[1]['description']);host.a_export.setStatusTip(TRANSFERS[1]['description'])
        def cabinet_view(legacy):
            page = getattr(host, 'cabinet_page', None);nav = getattr(host, 'settings_navigator', None)
            if page is None:return
            if nav is not None:nav.show_view('cabinet')
            page.set_legacy(legacy)
        from PySide6.QtGui import QActionGroup
        views = QActionGroup(host)
        host.a_cabinet_logical = make('Logical Cabinet', lambda:cabinet_view(False))
        host.a_cabinet_existing = make('Existing Views', lambda:cabinet_view(True))
        for a in (host.a_cabinet_logical, host.a_cabinet_existing):a.setCheckable(True);views.addAction(a)
        host.a_cabinet_refresh = make('Refresh Cabinet', lambda:host.cabinet_page.refresh(force=True) if hasattr(host, 'cabinet_page') else None)
        def concern_overview():
            overview = getattr(getattr(host, 'concern', None), 'overview_button', None)
            if overview is not None and overview.isEnabled():overview.click()
        host.a_concern_overview = make('Concern Overview', concern_overview)
        def machine_refresh():
            nav = getattr(host, 'settings_navigator', None);page = getattr(host, 'machine_page', None)
            if nav is not None:nav.show_view('machine')
            if page is not None:page.build(force=True)
        host.a_machine_refresh = make('Refresh Machine View', machine_refresh)
        from pathlib import Path
        from PySide6.QtGui import QActionGroup
        program = Path(__file__).resolve().parents[1]
        from .version import SHORT
        host.a_receive = make('Receive Files…', lambda:host.ledger_bridge.navigation()['office']().pick_files())
        host.a_files = make('Files', lambda:open_destination(host, 'files'))
        host.a_agenda = make("Graphite's Agenda", lambda:open_destination(host, 'agenda'))
        host.a_project_desk = make('Project Desk', lambda:open_destination(host, 'project_desk'))
        host.a_changes = make('Changes', lambda:open_destination(host, 'changes'))
        host.a_continuing = make('Continuing work', lambda:open_destination(host,'continuing'))
        host.a_deployment = make('Exchange & deployment', lambda:open_destination(host,'deployment'))
        host.a_slate_panel = make('Graphite', lambda:host.shell2.show_slate_face())
        host.a_getting_started = make('Getting Started', lambda:host.open_in_viewer(program / 'GETTING_STARTED.md'))
        release_notes = program / 'docs' / ('RELEASE_NOTES_%s.md' % SHORT)
        if not release_notes.is_file(): release_notes = program / 'docs' / 'STAGE6.md'
        host.a_whats_new = make("What's New in %s" % SHORT, lambda:host.open_in_viewer(release_notes))
        sizes = QActionGroup(host);host.a_sizes = {}
        for level, word in ((0, 'One Line'), (1, 'Half'), (2, 'Tall')):
            a = make(word, lambda level=level:host.console.set_size(level) if hasattr(host, 'console') else None);a.setCheckable(True);sizes.addAction(a);host.a_sizes[level] = a
        # HATCH DESK D3: the writing line's four modes, each with the key it had as a target (Alt+1 Graphite, Alt+4 Find, Alt+5
        # Shell) and Alt+6 for Log; Alt+2 (staC) is Assignment too (typed staC runs there on Ctrl+Enter) and Alt+3 (Kernel) is
        # Run an operation…, Kernel's home on this menu. host.a_talk keeps the old keys for callers.
        talk = QActionGroup(host);host.a_talk = {}
        bar_words = getattr(getattr(host, 'type_bar', None), 'labels', {})
        for key, word, number in (('slate', 'Assistant', 1), ('shell', bar_words.get('shell', 'Terminal'), 5), ('find', 'Search', 4), ('log', 'Log', 6)):
            a = make('%s\tAlt+%d' % (word, number), lambda key=key:host.type_bar.set_target(key) if hasattr(host, 'type_bar') else None)
            a.setCheckable(True);a.setShortcut('Alt+%d' % number);host.addAction(a);talk.addAction(a);host.a_talk[key] = a
        host.a_talk_stac = make('A line (Assignment)', lambda:host.type_bar.set_target('stac') if hasattr(host, 'type_bar') else None)
        host.a_talk_stac.setShortcut('Alt+2');host.addAction(host.a_talk_stac);host.a_talk['stac'] = host.a_talk['slate']
        host.a_run_operation = make('Run an operation…\tAlt+3', lambda:host.type_bar.run_operation() if hasattr(host, 'type_bar') else None)
        host.a_run_operation.setShortcut('Alt+3');host.addAction(host.a_run_operation);host.a_talk['kernel'] = host.a_run_operation
        host.a_run_operation.setToolTip('An operation by name in the writing line (Kernel\'s home): Tab completes, Enter runs, help NAME and ops WORD answer')
        def sync():  # the checks say what is true now
            console = getattr(host, 'console', None);target = getattr(host, 'type_target', 'slate')
            if console is not None:host.a_sizes[console.size_level].setChecked(True)
            if target in ('slate', 'shell', 'find', 'log'):host.a_talk[target].setChecked(True)
        host._menus_sync = sync
    if not hasattr(host, 'a_new_idea'):
        # HATCH DESK D2 (the brief: "Put New Idea and New Project under Work or on the relevant tree"): creation left the cat's
        # list for Work; the same routes as before (the Jot it down sheet, the Project Desk with a new title ready to type).
        from .shell2 import capture_dialog
        def new_project():
            from .project_desk_qt import show
            tab = show(host)
            if tab is not None and hasattr(tab, 'project_title'):tab.project_title.setFocus();tab.project_title.selectAll()
        host.a_new_idea = QAction('New Idea…\tCtrl+Shift+N', host);host.a_new_idea.triggered.connect(lambda checked=False:capture_dialog(host))
        host.a_new_idea.setToolTip('Jot an idea into Notes, exactly as written (Ctrl+Shift+N)');host.a_new_idea.setStatusTip(host.a_new_idea.toolTip())
        host.a_new_project = QAction('New Project…', host);host.a_new_project.triggered.connect(lambda checked=False:new_project())
        host.a_new_project.setToolTip('Open the Project Desk with a new title ready to type');host.a_new_project.setStatusTip(host.a_new_project.toolTip())
    if not hasattr(host, 'a_field'):
        # The Field (12 November): the overview of the work and what feeds what. One action, made once: the menu row, F9, and
        # the writing line's command search all reach the same thing. Plain text and a real shortcut so typing "field" finds it.
        host.a_field = QAction('Field', host);host.a_field.setShortcut('F9')
        host.a_field.triggered.connect(lambda checked=False:host.show_field() if hasattr(host, 'show_field') else None)
        host.a_field.setToolTip('The work in this workspace as sheets, with what feeds what; Enter opens one, Esc comes back (F9)')
        host.a_field.setStatusTip(host.a_field.toolTip());host.addAction(host.a_field)
    service = next((a for a in before if a.text().replace('&', '').startswith('Background service')), None)
    extras = {'@receive': host.a_receive, '@files': host.a_files, '@agenda': host.a_agenda, '@project_desk': host.a_project_desk, '@changes': host.a_changes, '@continuing':host.a_continuing, '@deployment':host.a_deployment, '@slate_panel': host.a_slate_panel,
              '@getting_started': host.a_getting_started, '@whats_new': host.a_whats_new,
              **{'@size_' + w: host.a_sizes[l] for l, w in ((0, 'line'), (1, 'half'), (2, 'tall'))},
              **{'@talk_' + k: a for k, a in host.a_talk.items()}, '@run_operation': host.a_run_operation,
              '@computer': host.a_computer, '@pills': host.a_pills, '@work_copy': host.a_work_copy, '@console': host.a_console, '@library': host.a_library, '@chain': host.a_chain,
              '@explore':host.a_explore,'@pleasantries': getattr(getattr(host, 'shell2', None), 'script_action', None), '@service': service,
              '@import': host.a_import, '@export': host.a_export, '@machine_refresh': host.a_machine_refresh,
              '@new_idea': host.a_new_idea, '@new_project': host.a_new_project, '@field': host.a_field}
    placed = {service} if service is not None else set()

    def add(menu, key):
        if key is None:menu.addSeparator();return
        if key == '@recent' and hasattr(host, 'recent_menu'):menu.addMenu(host.recent_menu);return
        if key in ('@type_to', '@console_sizes'):  # the bar's own words, as checkable choices
            sub = QMenu('Writing Line' if key == '@type_to' else 'Console', host)  # D3: the line's four modes
            for a in ([host.a_talk[k] for k in ('slate', 'shell', 'find', 'log')] if key == '@type_to' else host.a_sizes.values()):sub.addAction(a);placed.add(a)
            sub.aboutToShow.connect(host._menus_sync);menu.addMenu(sub);return
        if key == '@leave':
            from . import session_power as power
            made = getattr(host, '_leave_actions', None)
            if made is None:
                made = host._leave_actions = {};leave = power.session_exit()
                for name, word in (('logout', power.WORDS['logout']), ('leave', leave['label']), ('restart', power.WORDS['restart']), ('shutdown', power.WORDS['shutdown'])):
                    a = QAction(word, host);a.setToolTip(power.SCOPES[name]);a.setStatusTip(power.SCOPES[name])
                    a.triggered.connect(lambda checked=False, name=name:power.leave(host) if name == 'leave' else power.run_action(host, name))
                    made[name] = a
            for a in made.values():menu.addAction(a);placed.add(a)
            return
        if key == '@chain_desk':
            a = menu.addAction('Constructed chain')
            a.triggered.connect(lambda checked=False:__import__('workbench.chain_workbench_qt',fromlist=['tray']).tray(host).show());return
        if key == '@desk_art':
            from .boss_qt import appearance_menu
            from .tool_faces import menu as buttons_menu
            from .shell2 import hand_menu
            menu.addMenu(appearance_menu(host));menu.addMenu(buttons_menu(host));menu.addMenu(hand_menu(host));return      # the desk's art, its buttons (words or glyphs), and how far Stacy acts by herself
        if key == '@targets' and hasattr(host, 'target_menu'):menu.addMenu(host.target_menu);return
        if key == '@cabinet':  # HATCH DESK D1b: how the cabinet is arranged (it was the left pane's own words)
            sub = QMenu('Cabinet', host);host.cabinet_menu = sub
            def fill(sub=sub):
                for a in list(sub.actions()):
                    sub.removeAction(a)
                    if a.parent() is sub:a.deleteLater()  # this menu's own rows (the catalogue choices, the section): made afresh
                page = getattr(host, 'cabinet_page', None);legacy = bool(getattr(page, 'using_legacy', False))
                host.a_cabinet_logical.setChecked(not legacy);host.a_cabinet_existing.setChecked(legacy)
                sub.addAction(host.a_cabinet_logical);sub.addAction(host.a_cabinet_existing)
                selector = getattr(getattr(host, 'concern', None), 'selector', None)
                if selector is not None and selector.count():
                    sub.addSection('Existing views show')
                    for i in range(selector.count()):
                        a = sub.addAction(selector.itemText(i));a.setCheckable(True);a.setChecked(i == selector.currentIndex());a.setEnabled(selector.isEnabled())
                        a.triggered.connect(lambda checked=False, i=i:(selector.setCurrentIndex(i), host.a_cabinet_existing.trigger()))
                    sub.addAction(host.a_concern_overview)
                    overview = getattr(getattr(host, 'concern', None), 'overview_button', None)
                    host.a_concern_overview.setEnabled(bool(overview is not None and overview.isEnabled()))
                sub.addSeparator();sub.addAction(host.a_cabinet_refresh)
            sub.aboutToShow.connect(fill);fill();menu.addMenu(sub)
            for a in (host.a_cabinet_logical, host.a_cabinet_existing, host.a_cabinet_refresh, host.a_concern_overview):placed.add(a)
            return
        if key == '@engineering':
            sub = QMenu('Engineering', host);host.engineering_menu = sub
            for title, keys in ENGINEERING:
                part = QMenu(title, sub)
                for k in keys:add(part, k)
                if not part.isEmpty():sub.addMenu(part)
            leftover = [a for a in dict.fromkeys(before) if a not in placed and a.text().replace('&', '').strip()]
            if leftover:
                more = QMenu('More', sub)
                for a in leftover:more.addAction(a);placed.add(a)
                sub.addMenu(more)
            menu.addMenu(sub);sub.menuAction().setVisible(not detached(host.root))  # older engineering commands appear with a project
            return
        action = extras.get(key) if key.startswith('@') else actions.get(key)
        if action is None or action in placed:return
        menu.addAction(action);placed.add(action)

    for menu in groups.values():  # detach, never delete: the actions belong to the window or are re-placed below
        for action in list(menu.actions()):menu.removeAction(action)
    for group, keys in (
        ('File',FILE),('Edit',EDIT),('Options',VIEW),('Help',HELP),
        ('Commands',['ledger_commands','@run_operation','@chain','@chain_desk','@type_to','palette']),
        ('Settings',['ledger_settings','@desk_art','@service']),
        ('Properties',['inspector','@computer','@pills']),
        ('Tools',['@explore','discovery','algorithms','atlas','@work_copy','doctor','master_stop',None,'@engineering'])):
        menu = groups.get(group)
        if menu is not None:
            for key in keys:add(menu, key)
    from .presentation_qt import install_favorites_menu
    install_favorites_menu(host)
    # Menus are words. The one mark kept is a graphite dot on Master Stop, the item that should be found at once.
    stop = getattr(host, 'a_master_stop', None)
    for action in host.findChildren(QAction):
        action.setIconVisibleInMenu(action is stop)
        if action is stop and not action.property('paperIcon'):action.setIcon(dot());action.setProperty('paperIcon', True)
    from PySide6.QtWidgets import QAbstractButton
    for b in host.findChildren(QAbstractButton):  # buttons that still carry a picture get the same graphite outline
        if not b.icon().isNull() and not b.property('paperIcon') and b is not getattr(host, 'master_stop_button', None):
            b.setIcon(paper_icon(b.icon()));b.setProperty('paperIcon', True)
    for key, words in (('home', 'Today'), ('about', 'About Graphite')):  # && shows one &; a single & would mark a key  # today's names ('Inspector' keeps its name: a release check reads it)
        if key in actions:actions[key].setText(words)
    host._menus2 = True
