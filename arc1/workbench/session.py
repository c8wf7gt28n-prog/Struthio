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
import os
from pathlib import Path
import tempfile

from .engine import TARGETS, DEFAULT_TARGET

SCHEMA = 'arc1.workbench-session/1'
LAYOUT_VERSION = 1          # bump when the dock layout changes; old saved layouts are then ignored
MAX_FILE = 128 * 1024
MAX_DOCS = 20
MAX_RECENT = 10
DEFAULTS = {'navigator_width': 236, 'output_height': 170, 'output_visible': False, 'output_tab': 'Output'}
OUTPUT_TABS = ('Output', 'Problems', 'Debug', 'Agent Activity')


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


class Session:
    def __init__(self, path=None, project=None):
        self.path = Path(path) if path else config_dir() / 'session-r10.json'
        self.project = str(Path(project).resolve()) if project else None
        self.state = self.fresh()
        self.load()

    def fresh(self):
        return {'schema': SCHEMA, 'project': self.project, 'documents': [], 'active': None,
                'target': DEFAULT_TARGET, 'last_game': None, 'recent': [],
                'layout': dict(DEFAULTS, version=LAYOUT_VERSION, geometry=None, dock_state=None)}

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
        docs = data.get('documents')
        if isinstance(docs, list):
            for d in docs[:MAX_DOCS]:
                if isinstance(d, dict) and _relpath_ok(d.get('path')) \
                        and _int_in(d.get('line', 1), 1, 10_000_000) and _int_in(d.get('column', 1), 1, 100_000):
                    s['documents'].append({'path': d['path'], 'line': d.get('line', 1), 'column': d.get('column', 1)})
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
            if _int_in(lay.get('navigator_width'), 160, 600):
                L['navigator_width'] = lay['navigator_width']
            if _int_in(lay.get('output_height'), 80, 700):
                L['output_height'] = lay['output_height']
            if type(lay.get('output_visible')) is bool:
                L['output_visible'] = lay['output_visible']
            if lay.get('output_tab') in OUTPUT_TABS:
                L['output_tab'] = lay['output_tab']
            if _b64_ok(lay.get('geometry'), 8192):
                L['geometry'] = lay['geometry']
            # A layout saved by a different layout version is ignored, not misapplied.
            if lay.get('version') == LAYOUT_VERSION and _b64_ok(lay.get('dock_state'), 32768):
                L['dock_state'] = lay['dock_state']

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.arc1-session-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, sort_keys=True, indent=2)
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
            if k in ('geometry', 'dock_state'):
                if v is None or _b64_ok(v, 32768):
                    L[k] = v
            elif k == 'navigator_width' and _int_in(v, 160, 600):
                L[k] = v
            elif k == 'output_height' and _int_in(v, 80, 700):
                L[k] = v
            elif k == 'output_visible' and type(v) is bool:
                L[k] = v
            elif k == 'output_tab' and v in OUTPUT_TABS:
                L[k] = v
        L['version'] = LAYOUT_VERSION

    def reset_layout(self):
        """Factory layout; open documents, recent files and target are kept."""
        self.state['layout'] = dict(DEFAULTS, version=LAYOUT_VERSION, geometry=None, dock_state=None)

    @property
    def layout(self):
        return self.state['layout']


def encode_bytes(data):
    return base64.b64encode(bytes(data)).decode('ascii')


def decode_bytes(text):
    return base64.b64decode(text.encode('ascii'))
