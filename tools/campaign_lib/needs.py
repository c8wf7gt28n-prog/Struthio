"""What a case needs from the machine, checked when the run starts; Blocked is the runner's decision, never a label.

A case lists its needs (Case.needs). The parent checks each one at run time, without importing Graphite, and an
attempt runs only when all are met. Otherwise its outcome is Blocked and the reason names what is missing and what
is present. An anchor whose needs are all met but whose steps are not written yet is still Blocked, and says so:
"steps not written yet; its needs are here".

  model             the owner's 35B model registered in --workspace: a registration whose weights file has the
                    owner's SHA-256 (registration hashed it in full), and that file still present at its size
  projector         the same registration also carries a vision projector (mmproj) file, present
  ram               at least 24 GiB of RAM available to this process (cgroup when there is one, /proc/meminfo)
  thinkpad          this host is the owner's ThinkPad (CPU: AMD Ryzen 7 7735HS)
  desktop           a desktop session: DISPLAY or WAYLAND_DISPLAY is set
  network           network access; a simulation run never reaches the network, by design
  app:<Name>        a native application, found on PATH by shutil.which (APPS lists the executables tried)
  ocr:<lang>        Tesseract with that language's trained data
  owner:<what>      the owner's own files for this situation, in <fixtures>/<situation>/ (at least one file)
  after_hours_07    the owner's After Hours 07 backup (zip or Graphite_Backup folder) under --fixtures
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
from pathlib import Path

from . import fixture, gguf_fixture

REAL_MIN_AVAILABLE = 24 * 1024 ** 3
THINKPAD_CPU = '7735HS'
APPS = {
    'LibreOffice': ('libreoffice', 'soffice'),
    'LibreOffice Calc': ('localc', 'libreoffice', 'soffice'),
    'LibreOffice Writer': ('lowriter', 'libreoffice', 'soffice'),
    'Blender': ('blender',),
    'Kdenlive': ('kdenlive',),
    'FreeCAD': ('freecad', 'FreeCAD', 'freecadcmd'),
    'KiCad': ('kicad',),
    'Scribus': ('scribus',),
    'Audacity': ('audacity',),
    'GIMP': ('gimp',),
    'Inkscape': ('inkscape',),
    'Firefox': ('firefox', 'firefox-esr'),
    'Zotero': ('zotero',),
    'Thunderbird': ('thunderbird',),
}
TESSDATA = ('/usr/share/tesseract-ocr/*/tessdata', '/usr/share/tessdata', '/usr/local/share/tessdata')
MODEL = ['model', 'ram']                    # running the real model needs both


def registered(workspace):
    """Models registered in a workspace, read from its kernel database without changing it."""
    path = Path(workspace).expanduser() / '.ledger' / 'engineering.sqlite3'
    if not path.is_file():
        return []
    with sqlite3.connect('file:%s?mode=ro' % path, uri=True) as db:
        rows = db.execute("SELECT value FROM settings WHERE key LIKE 'brain.model.%'").fetchall()
    return [json.loads(r[0]) for r in rows]


class Probe:
    """Checks needs on this machine. Every input can be replaced (tests give a fake PATH, environment or host)."""

    def __init__(self, fixtures=None, workspace=None, backup=None, mode='sim', environ=None, which=None,
                 host=None, memory=None):
        self.fixtures = Path(fixtures) if fixtures else fixture.fixtures_dir()
        self.workspace = Path(workspace).expanduser() if workspace else None
        self.backup = backup
        self.mode = mode
        self.environ = os.environ if environ is None else environ
        self.which = which or shutil.which
        self._host = host
        self._memory = memory
        self._seen = {}

    def host(self):
        if self._host is None:
            self._host = fixture.host_summary()
        return self._host

    def memory(self):
        if self._memory is None:
            self._memory = fixture.memory()
        return self._memory

    def check(self, need, situation=None):
        """(met, what it is, evidence): evidence says where it was found, or why it is missing."""
        key = (need, situation if need.startswith('owner:') else None)
        if key not in self._seen:
            self._seen[key] = self._check(need, situation)
        return self._seen[key]

    # -- each kind -------------------------------------------------------------------------------
    def _check(self, need, situation):
        kind, _, arg = need.partition(':')
        method = getattr(self, '_need_' + kind, None)
        if method is None:
            return False, need, 'no check is defined for this need'
        return method(arg, situation)

    def _owner_model(self):
        if self.workspace is None:
            return None, 'no --workspace was given'
        try:
            models = registered(self.workspace)
        except (OSError, sqlite3.Error, ValueError) as error:
            return None, 'its database in %s could not be read (%s)' % (self.workspace, error)
        owner = gguf_fixture.OWNER_FILE
        for model in models:
            weights = [f for f in model.get('files', []) if f.get('role') == 'weights']
            if any(f.get('sha256') == owner['sha256'] for f in weights):
                return model, None
        return None, 'no model registered in %s has the owner\'s SHA-256' % self.workspace

    def _need_model(self, arg, situation):
        what = 'the owner\'s 35B model registered in --workspace'
        model, why = self._owner_model()
        if model is None:
            return False, what, why
        owner = gguf_fixture.OWNER_FILE
        weights = next(f for f in model['files'] if f.get('role') == 'weights' and f.get('sha256') == owner['sha256'])
        path = Path(weights.get('path') or '')
        if not path.is_file():
            return False, what, 'registered, but its file is not at %s' % path
        if path.stat().st_size != owner['bytes']:
            return False, what, 'registered, but %s is %d bytes, not %d' % (path, path.stat().st_size, owner['bytes'])
        return True, what, 'registered as %s, file %s present at %d bytes' % (model.get('id', '?')[:12], path, owner['bytes'])

    def _need_projector(self, arg, situation):
        what = 'the 35B model\'s vision projector (mmproj) registered with it'
        model, why = self._owner_model()
        if model is None:
            return False, what, why
        files = [f for f in model.get('files', []) if f.get('role') == 'projector']
        present = [f for f in files if Path(f.get('path') or '').is_file()]
        if not present:
            return False, what, 'the registration has no projector file' if not files else 'its projector file is missing'
        return True, what, 'projector %s present' % present[0]['path']

    def _need_ram(self, arg, situation):
        what = 'at least 24 GiB of RAM available'
        mem = self.memory()
        available = mem.get('available_bytes')
        if available is None:
            return False, what, 'available RAM could not be measured'
        text = '%.1f GiB available (%s)' % (available / 1024 ** 3, mem.get('basis'))
        return available >= REAL_MIN_AVAILABLE, what, text

    def _need_thinkpad(self, arg, situation):
        what = 'the owner\'s ThinkPad (Ryzen 7 7735HS)'
        cpu = str(self.host().get('cpu'))
        return THINKPAD_CPU in cpu, what, 'this host\'s CPU is ' + cpu

    def _need_desktop(self, arg, situation):
        what = 'a desktop session'
        shown = [k for k in ('DISPLAY', 'WAYLAND_DISPLAY') if self.environ.get(k)]
        if shown:
            return True, what, ', '.join('%s=%s' % (k, self.environ[k]) for k in shown)
        return False, what, 'DISPLAY and WAYLAND_DISPLAY are not set'

    def _need_network(self, arg, situation):
        what = 'network access'
        if self.mode == 'sim':
            return False, what, 'a simulation run does not reach the network, by design'
        return False, what, 'no run mode grants network access yet'

    def _need_app(self, arg, situation):
        names = APPS.get(arg, (arg.lower(),))
        for name in names:
            found = self.which(name)
            if found:
                return True, arg, found
        return False, arg, 'none of %s is on PATH' % ', '.join(names)

    def _need_ocr(self, arg, situation):
        what = 'Tesseract with %s language data' % arg
        if not self.which('tesseract'):
            return False, what, 'tesseract is not on PATH'
        folders = [Path(self.environ['TESSDATA_PREFIX'])] if self.environ.get('TESSDATA_PREFIX') else []
        for pattern in TESSDATA:
            folders += sorted(Path('/').glob(pattern.lstrip('/'))) if '*' in pattern else [Path(pattern)]
        for folder in folders:
            if (folder / (arg + '.traineddata')).is_file():
                return True, what, str(folder / (arg + '.traineddata'))
        return False, what, '%s.traineddata was not found' % arg

    def _need_owner(self, arg, situation):
        what = 'the owner\'s %s' % arg
        folder = self.fixtures / (situation or 'owner')
        if folder.is_dir() and any(p.is_file() for p in folder.rglob('*')):
            return True, what, str(folder)
        return False, what, 'put it in %s' % folder

    def _need_after_hours_07(self, arg, situation):
        what = 'the owner\'s After Hours 07 backup'
        found = self.backup or fixture.ah07_available(self.fixtures)
        if found:
            return True, what, str(found)
        return False, what, 'not found under %s' % self.fixtures


def decide(case, probe):
    """Whether the attempt can run here: (None, checked) or (the Blocked reason, checked)."""
    checked = []
    for need in case.needs:
        met, what, evidence = probe.check(need, case.situation)
        checked.append({'need': need, 'met': met, 'what': what, 'evidence': evidence})
    missing = [c for c in checked if not c['met']]
    present = [c for c in checked if c['met']]
    if missing:
        reason = 'Needs %s' % _join(['%s (%s)' % (c['what'], c['evidence']) for c in missing])
        if present:
            reason += '; present here: %s' % _join(['%s (%s)' % (c['what'], c['evidence']) for c in present])
        return reason + '.', checked
    if case.fn is None:
        here = _join(['%s (%s)' % (c['what'], c['evidence']) for c in present]) if present else 'it needs nothing'
        return 'steps not written yet; its needs are here: %s.' % here, checked
    return None, checked


def _join(items):
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]
