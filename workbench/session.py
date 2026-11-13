"""ARC-1 Workbench session memory (R10). Importable without Qt.

Remembers what you were doing so you can return after weeks away: the project,
open documents with cursor positions, the active document, the selected target,
whether the output panel was open, panel sizes and the window layout. Every
value is validated on load; anything unexpected is ignored, never executed.
`reset_layout()` restores the factory layout without forgetting documents.
"""
from __future__ import annotations

import base64
import json
import re
import os
from pathlib import Path
import tempfile

from .engine import TARGETS, DEFAULT_TARGET
from sdk.cli.arc1cli.workspace_view import DEFAULT as VIEW_DEFAULT, clean as clean_view
from sdk.cli.arc1cli.selection_context import clean as clean_selection

SCHEMA = 'arc1.workbench-session/1'
LAYOUT_VERSION = 2          # bump when the dock layout changes; old saved layouts are then ignored
MAX_FILE = 128 * 1024
MAX_DOCS = 20
MAX_RECENT = 10
from .presentation_preferences import DEFAULTS, OUTPUT_TABS, CURSIVE_DEFAULT
SELF_TREE_IDS = {'root', 'interface', 'source', 'clip', 'tools', 'simulator', 'tests', 'settings', 'recovery'}
# Desktop fields restored with bounds since INTEGRATION-01 (they were written on every save but never read back).
TYPE_TARGETS = ('slate', 'stac', 'kernel', 'find', 'shell', 'log')   # typebar_qt.MAPPED keys (D3: the four modes and the old targets); Qt-free
LOG_STREAMS = ('events', 'network')                                  # log_qt.STREAMS: the Log view's remembered stream (D3)
CONSOLE_PAGES = ('log', 'stac', 'kernel', 'find', 'shell')    # console_qt.MODES keys
CONSOLE_HISTORY_LINES = 50                                    # typed console lines kept per page on disk
MAX_LIBRARY_SECTIONS = 50
NAVIGATOR_WIDTHS = (160, 600)   # layout.navigator_width (the public setting keeps this range)
SIMULATOR_WIDTHS = (160, 900)   # layout.simulator_width: the right column, remembered since DESKTOP-01 (LP01: each width its own)
NAVIGATION_MODES = ('cabinet', 'settings', 'machine')   # settings_navigation.mode; 'machine' is the DESKTOP-01 navigator view
IDLE_DISPLAY_MINUTES = (0, 5, 15, 30)


def config_dir():
    override = os.environ.get('ARC1_WORKBENCH_CONFIG_HOME')
    if override:
        return Path(override)
    if os.name == 'nt':
        return Path(os.environ.get('APPDATA', str(Path.home() / 'AppData' / 'Roaming'))) / 'ARC-1' / 'Workbench'
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'arc1-workbench'


def _relpath_ok(p):
    return (isinstance(p, str) and 0 < len(p) < 300 and '\x00' not in p and not Path(p).is_absolute()
            and not p.startswith(('/', '\\')) and '..' not in Path(p.replace('\\', '/')).parts
            and ':' not in p)


def _b64_ok(v, limit):
    if not isinstance(v, str) or len(v) > limit:
        return False
    try:
        base64.b64decode(v.encode('ascii'), validate=True)
        return True
    except (ValueError, UnicodeError):
        return False


def _int_in(v, lo, hi):
    return type(v) is int and lo <= v <= hi


def _clip_position_ok(value):
    return isinstance(value, list) and len(value) == 2 and all(
        type(number) in (int, float) and 0 <= number <= 1 for number in value)


def _pill_link_ok(value):
    # host:port or [ipv6]:port for the workstation pill service; never a URL, path or credential.
    return isinstance(value, str) and re.fullmatch(r'(?:[A-Za-z0-9.\-]{1,253}|\[[0-9A-Fa-f:.]{2,45}\]):\d{1,5}', value) is not None


class Session:
    def __init__(self, path=None, project=None):
        self.path = Path(path) if path else config_dir() / 'session-r10.json'
        self.project = str(Path(project).resolve()) if project else None
        self.state = self.fresh()
        self.load()

    def fresh(self):
        return {'schema': SCHEMA, 'project': self.project, 'documents': [], 'active': None,
                'view_preferences': dict(VIEW_DEFAULT), 'cursive':CURSIVE_DEFAULT,
                'target': DEFAULT_TARGET, 'last_game': None, 'recent': [], 'toolbar_favorites': {}, 'toolbar_favorites_version':2,
                'layout': dict(DEFAULTS, self_tree_expanded=['root'], hardware_tree_expanded=['root'], version=LAYOUT_VERSION,
                               geometry=None, dock_state=None)}

    # ---------------------------------------------------------------- load / save
    def load(self):
        try:
            if self.path.stat().st_size > MAX_FILE:
                return
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError):
            return
        if not isinstance(data, dict) or data.get('schema') != SCHEMA:
            return
        # Documents belong to one project; a different project starts clean.
        if self.project and data.get('project') not in (None, self.project):
            return
        s = self.state
        cabinet=data.get('cabinet_navigation')
        if isinstance(cabinet,dict):
            def cabinet_id(value):return isinstance(value,str) and 1<=len(value)<=600 and not any(ord(c)<32 for c in value)
            expanded=cabinet.get('expanded',[])
            if (cabinet_id(cabinet.get('selected')) and type(cabinet.get('legacy',False)) is bool
                    and isinstance(expanded,list) and len(expanded)<=2400 and all(cabinet_id(value) for value in expanded)
                    and type(cabinet.get('scroll',0)) is int and 0<=cabinet.get('scroll',0)<=10000000):
                s['cabinet_navigation']={key:cabinet.get(key,default) for key,default in
                    [('selected','cabinet:concern'),('expanded',[]),('legacy',False),('scroll',0)]}
        if data.get('desk_art') in ('illustrated','ascii','clean'):s['desk_art']=data['desk_art']
        idle_minutes = data.get('idle_display_minutes')
        if type(idle_minutes) is int and idle_minutes in IDLE_DISPLAY_MINUTES:
            s['idle_display_minutes'] = idle_minutes
        if type(data.get('cursive')) is bool:s['cursive']=data['cursive']
        if data.get('buttons') in ('words','icons'):s['buttons']=data['buttons']     # tool buttons as words on plates, or as Graphite's glyphs (tool_faces)
        if type(data.get('page_own_light')) is bool:s['page_own_light']=data['page_own_light']     # a PDF page shown as the file has it, not in the desk's light
        if type(data.get('writing_marker')) is bool:s['writing_marker']=data['writing_marker']  # appearance.writing_marker (VS03)
        navigation=data.get('settings_navigation')
        if isinstance(navigation,dict):
            from .settings_registry import nodes
            allowed={r['id'] for r in nodes()}
            if (navigation.get('mode') in NAVIGATION_MODES and navigation.get('selected') in allowed
                    and isinstance(navigation.get('expanded'),list) and len(navigation['expanded'])<=len(allowed)
                    and all(isinstance(x,str) and x in allowed for x in navigation['expanded'])):
                s['settings_navigation']={**navigation,'expanded':list(navigation['expanded'])}
        if isinstance(data.get('selection_context'),dict):
            try:s['selection_context']=clean_selection(data['selection_context'])
            except (ValueError,TypeError):pass
        if 'view_preferences' in data:
            try:
                s['view_preferences'] = clean_view(data['view_preferences'])
            except (ValueError, TypeError):
                pass
        elif data.get('documents') or data.get('workspace'):
            # An existing installation retains its working-view launch behavior.
            s['view_preferences']['last_surface'] = 'workspace'
        if 'reading_profile' in data:
            from .reading_profile import clean
            try:s['reading_profile']=clean(data['reading_profile'])
            except (ValueError,TypeError):pass
        workspace=data.get('workspace')
        if isinstance(workspace,dict):
            clean={}
            for key in ('tabs','deferred'):
                clean[key]=[r for r in workspace.get(key,[])[:100] if isinstance(r,dict)
                            and isinstance(r.get('kind'),str) and len(r['kind'])<100
                            and ('path' not in r or _relpath_ok(r['path']))
                            and all(key not in r or isinstance(r[key],str) and len(r[key])<300 for key in ('device','group'))
                            and all(key not in r or isinstance(r[key],str) and 0 < len(r[key]) <= 80 for key in ('concern','concern_context'))
                            and all(key not in r or isinstance(r[key],str) and re.fullmatch(r'[0-9a-f]{32}',r[key]) for key in ('pdf_namespace','pdf_item'))
                            and ('pdf_sha256' not in r or isinstance(r['pdf_sha256'],str) and re.fullmatch(r'[0-9a-f]{64}',r['pdf_sha256']))
                            and ('pdf_page' not in r or _int_in(r['pdf_page'],0,511))
                            and ('case' not in r or isinstance(r['case'],bool))
                            and _int_in(r.get('line',1),1,10000000)
                            and _int_in(r.get('column',1),1,100000)
                            and isinstance(r.get('pinned',False),bool)] if isinstance(workspace.get(key,[]),list) else []
            clean['active']=workspace.get('active',0) if _int_in(workspace.get('active',0),0,99) else 0
            s['workspace']=clean
        docs = data.get('documents')
        if isinstance(docs, list):
            for d in docs[:MAX_DOCS]:
                if isinstance(d, dict) and _relpath_ok(d.get('path')) \
                        and _int_in(d.get('line', 1), 1, 10_000_000) and _int_in(d.get('column', 1), 1, 100_000):
                    s['documents'].append({'path': d['path'], 'line': d.get('line', 1), 'column': d.get('column', 1)})
        s['toolbar_favorites_version']=2 if data.get('toolbar_favorites_version')==2 else 1
        saved_favorites = data.get('toolbar_favorites')
        modes=data.get('category_views',{})
        if isinstance(modes,dict):
            s['category_views']={k:v for k,v in list(modes.items())[:100] if isinstance(k,str) and len(k)<300 and v in ('Auto view','Details','Thumbnails')}
        if isinstance(saved_favorites, dict):
            # Only a tiny collection of strings. Actual command eligibility is
            # validated against the active five menus by the desktop client.
            for group in ('File', 'Edit', 'View', 'Options', 'Help'):
                slots = saved_favorites.get(group)
                if (isinstance(slots, list) and len(slots) <= 3
                        and all(isinstance(value, str) and 0 < len(value) <= 32 for value in slots)
                        and len(set(slots)) == len(slots)):
                    s['toolbar_favorites'][group] = list(slots)
        library = data.get('library_open')
        if isinstance(library, dict):
            s['library_open'] = {k: v for k, v in list(library.items())[:MAX_LIBRARY_SECTIONS]
                                 if isinstance(k, str) and 0 < len(k) < 300 and type(v) is bool}
        dismissed = data.get('related_dismissed')  # AGENT-01: the Related rows the owner dismissed, kept across starts
        if isinstance(dismissed, list):
            s['related_dismissed'] = [i for i in dismissed if isinstance(i, str) and 0 < len(i) <= 120 and ':' in i][-200:]
        finder = data.get('finder')  # UI-04: the Finder's last place, view, preview and hidden choice, kept across starts
        if isinstance(finder, dict):
            place = finder.get('place')
            if place == 'today' or (isinstance(place, str) and 0 < len(place) <= 4096 and place.startswith('/') and '\0' not in place):
                s['finder'] = {'place': place, 'view': finder.get('view') if finder.get('view') in ('icons', 'list', 'columns') else 'list',
                               'preview': bool(finder.get('preview', True)), 'hidden': bool(finder.get('hidden', False))}
        if data.get('type_target') in TYPE_TARGETS:
            s['type_target'] = data['type_target']
        if data.get('log_stream') in LOG_STREAMS:
            s['log_stream'] = data['log_stream']
        console = data.get('console')
        if isinstance(console, dict):
            kept = {}
            if console.get('mode') in CONSOLE_PAGES:
                kept['mode'] = console['mode']
            history = console.get('history')
            if isinstance(history, dict):
                kept['history'] = {page: [line for line in lines[-CONSOLE_HISTORY_LINES:] if isinstance(line, str) and len(line) <= 2000]
                                   for page, lines in history.items() if page in CONSOLE_PAGES and isinstance(lines, list)}
            if kept:
                s['console'] = kept
        if _pill_link_ok(data.get('pill_link')):
            s['pill_link'] = data['pill_link']
        if _relpath_ok(data.get('active')):
            s['active'] = data['active']
        if data.get('target') in TARGETS:
            s['target'] = data['target']
        if _relpath_ok(data.get('last_game')):
            s['last_game'] = data['last_game']
        recent = data.get('recent')
        if isinstance(recent, list):
            s['recent'] = [r for r in recent if _relpath_ok(r)][:MAX_RECENT]
        lay = data.get('layout')
        if isinstance(lay, dict):
            L = s['layout']
            if _int_in(lay.get('navigator_width'), *NAVIGATOR_WIDTHS):
                L['navigator_width'] = lay['navigator_width']
            if _int_in(lay.get('simulator_width'), *SIMULATOR_WIDTHS):
                L['simulator_width'] = lay['simulator_width']
            if _int_in(lay.get('output_height'), 80, 700):
                L['output_height'] = lay['output_height']
            if type(lay.get('output_visible')) is bool:
                L['output_visible'] = lay['output_visible']
            if lay.get('output_tab') in OUTPUT_TABS:
                L['output_tab'] = lay['output_tab']
            if _clip_position_ok(lay.get('clip_position')):
                L['clip_position'] = lay['clip_position']
            if type(lay.get('clip_collapsed')) is bool:
                L['clip_collapsed'] = lay['clip_collapsed']
            if type(lay.get('stacy_reactions')) is bool:
                L['stacy_reactions'] = lay['stacy_reactions']
            if self._self_tree_ok(lay.get('self_tree_expanded')):
                L['self_tree_expanded'] = lay['self_tree_expanded']
            if self._hardware_tree_ok(lay.get('hardware_tree_expanded')):
                L['hardware_tree_expanded'] = list(lay['hardware_tree_expanded'])
            if _b64_ok(lay.get('geometry'), 8192):
                L['geometry'] = lay['geometry']
            if _b64_ok(lay.get('engineering_state'), 32768):
                L['engineering_state'] = lay['engineering_state']
            # A layout saved by a different layout version is ignored, not misapplied.
            if lay.get('version') == LAYOUT_VERSION and _b64_ok(lay.get('dock_state'), 32768):
                L['dock_state'] = lay['dock_state']

    def save(self):
        from .config_lock import locked
        with locked(self.path):self._save()

    def _persistable(self):
        """What reaches disk: the state, with typed console lines capped so the profile never grows with every command."""
        console = self.state.get('console')
        if not isinstance(console, dict) or not isinstance(console.get('history'), dict):
            return self.state
        history = {page: lines[-CONSOLE_HISTORY_LINES:] if isinstance(lines, list) else lines for page, lines in console['history'].items()}
        return {**self.state, 'console': {**console, 'history': history}}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.arc1-session-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self._persistable(), f, sort_keys=True, indent=2)
                f.write('\n')
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    # ---------------------------------------------------------------- updates
    def remember_documents(self, documents, active):
        """documents: [(relative path, line, column)] in tab order."""
        self.state['documents'] = [{'path': p, 'line': max(1, int(l)), 'column': max(1, int(c))}
                                   for p, l, c in documents if _relpath_ok(p)][:MAX_DOCS]
        self.state['active'] = active if _relpath_ok(active) else None

    def touch_recent(self, relpath):
        if not _relpath_ok(relpath):
            return
        r = [x for x in self.state['recent'] if x != relpath]
        self.state['recent'] = [relpath] + r[:MAX_RECENT - 1]

    def set_target(self, target):
        if target in TARGETS:
            self.state['target'] = target

    def set_last_game(self, project):
        if _relpath_ok(project):
            self.state['last_game'] = project

    def set_layout(self, **values):
        L = self.state['layout']
        for k, v in values.items():
            if k in ('geometry', 'dock_state', 'engineering_state'):
                if v is None or _b64_ok(v, 32768):
                    L[k] = v
            elif k == 'navigator_width' and _int_in(v, *NAVIGATOR_WIDTHS):
                L[k] = v
            elif k == 'simulator_width' and _int_in(v, *SIMULATOR_WIDTHS):
                L[k] = v
            elif k == 'output_height' and _int_in(v, 80, 700):
                L[k] = v
            elif k == 'output_visible' and type(v) is bool:
                L[k] = v
            elif k == 'output_tab' and v in OUTPUT_TABS:
                L[k] = v
            elif k in ('clip_collapsed', 'stacy_reactions') and type(v) is bool:
                L[k] = v
            elif k == 'clip_position' and (v is None or _clip_position_ok(v)):
                L[k] = v
            elif k == 'self_tree_expanded' and self._self_tree_ok(v):
                L[k] = list(v)
            elif k == 'hardware_tree_expanded' and self._hardware_tree_ok(v):
                L[k] = list(v)
        L['version'] = LAYOUT_VERSION

    @staticmethod
    def _self_tree_ok(value):
        return (isinstance(value, list) and len(value) <= len(SELF_TREE_IDS)
                and len(value) == len(set(str(x) for x in value))
                and all(type(x) is str and x in SELF_TREE_IDS for x in value))

    @staticmethod
    def _hardware_tree_ok(value):
        return (isinstance(value, list) and len(value) <= 100
                and len(value) == len(set(str(x) for x in value))
                and all(isinstance(x, str) and 0 < len(x) <= 160
                        and (x == 'root' or x.startswith('device:') or x.startswith('group:') or x.startswith('workspace:'))
                        for x in value))

    def reset_layout(self):
        """Factory layout; open documents, recent files and target are kept."""
        self.state['layout'] = dict(DEFAULTS, self_tree_expanded=['root'], hardware_tree_expanded=['root'], version=LAYOUT_VERSION,
                                    geometry=None, dock_state=None)

    @property
    def layout(self):
        return self.state['layout']


def encode_bytes(data):
    return base64.b64encode(bytes(data)).decode('ascii')


def decode_bytes(text):
    return base64.b64decode(text.encode('ascii'))
