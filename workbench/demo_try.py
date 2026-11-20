"""Try Rail Demo and Try Home Demo (0.8.6 W): the two invented desks of "An evening with Kas's mind", from the Guide menu.

Each demo is built through the Kernel's own doors (rail_demo.workspace, home_demo.workspace: Files, bring in, admit, review
the table, calculate, investigate), in a fresh folder of its own under "Graphite demos" in your home folder, with a profile
and a Concern folder of its own beside it. It is never built in your workspace and nothing of it reaches your profile.

Her card says so first, in her column, and nothing is built until you press Build it. The build runs in a process of its
own (python -m workbench.demo_try KEY FOLDER), so this window's own locations are never changed and it waits for nothing;
when the build is done the demo opens in a window of its own, on the Field, and your window stays as it is. The goals the
desk proposes are kept there, as you would keep them (goals.keep, your press, given by Build it), so their cards show.

Her words here are fixed templates (WORDS), registered with mind_words. No model is asked.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

DEMOS = {'rail': ('Rail Demo', 'workbench.rail_demo'), 'home': ('Home Demo', 'workbench.home_demo')}
FOLDER = 'Graphite demos'            # under your home folder: a fresh folder for each demo you try
BUILD_SECONDS = 240                  # a build that has not finished by then is stopped, and the card says so

WORDS = {
    'card': '{name}: {notice}',
    'where': 'I build it in a new folder of its own, {folder}, with a profile of its own. Nothing goes into your workspace or your profile.',
    'opens': 'It opens in a window of its own, on the Field. This window stays as it is.',
    'build': 'Build it',
    'not_now': 'Not now',
    'building': 'Building {name} through the Kernel’s own doors. It takes a few seconds.',
    'built': '{name} is open in a window of its own, on the Field. Its folder is {folder}.',
    'failed': '{name} could not be built: {why}',
    'left': 'Nothing was built.',
    'menu_rail': 'Try Rail Demo',
    'menu_home': 'Try Home Demo',
}
try:
    from . import mind_words
    mind_words.register('demo_try', WORDS, kind='sentence')
except ImportError:  # pragma: no cover - run as a script before the package is importable
    pass


def fresh_folder(name, now=None):
    """A new, empty folder for one demo: ~/Graphite demos/<name> <date and time>. Never inside the program, never a workspace
    of yours (your Concern folder), never one that is already there."""
    from . import locations
    stamp = time.strftime('%Y-%m-%d %H.%M.%S', time.localtime(now))
    base = Path.home() / FOLDER
    concern = locations.concern_home().resolve()
    candidate = base / ('%s %s' % (name, stamp))
    resolved = candidate.resolve()
    if resolved.is_relative_to(locations.PACKAGE.resolve()) or resolved.is_relative_to(concern):
        import tempfile
        return Path(tempfile.mkdtemp(prefix=name.replace(' ', '_') + '_'))
    n = 1
    while candidate.exists():
        n += 1;candidate = base / ('%s %s (%d)' % (name, stamp, n))
    candidate.mkdir(parents=True, mode=0o700)
    return candidate


def demo_environment(folder, appearance=''):
    """The environment a demo's window starts with: its own workspace, profile and Concern folder, and this window's look."""
    folder = Path(folder);env = dict(os.environ)
    env.update(ARC1_WORKBENCH_CONFIG_HOME=str(folder / 'profile'), ARC_LEDGER_WORKSPACE=str(folder / 'workspace'), ARC_LEDGER_CONCERN=str(folder / 'Concern'))
    env.pop('ARC_LEDGER_EDITION', None)
    if appearance:env['GRAPHITE_APPEARANCE'] = appearance
    return env


def build(key, folder):
    """In this process (the build's own): the demo built in `folder` through the Kernel's own doors, its proposed goals kept.
    Returns {'workspace', 'goals'}. Changes this process's Graphite locations (rail_demo.workspace does): never call it in
    the window's own process."""
    import importlib
    name, module = DEMOS[key]
    kernel, principal, _ = importlib.import_module(module).workspace(folder)
    kept = 0
    found = kernel.dispatch('goals.candidates', {}, principal)
    for candidate in ((found.get('result') or {}).get('candidates') or ()) if found.get('ok') else ():
        if kernel.dispatch('goals.keep', {'candidate': candidate['key']}, principal).get('ok'):kept += 1
    return {'workspace': str(Path(folder) / 'workspace'), 'goals': kept}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2 or argv[0] not in DEMOS:
        print(json.dumps({'ok': False, 'why': 'usage: python -m workbench.demo_try rail|home FOLDER'}));return 2
    try:
        made = build(argv[0], Path(argv[1]))
    except Exception as exc:  # noqa: BLE001 - the window says why, in words
        print(json.dumps({'ok': False, 'why': str(exc)[:300]}));return 1
    print(json.dumps({'ok': True, **made}));return 0


# ---- the window side ----------------------------------------------------------------------------------------------------------

def try_demo(host, key):
    """Guide ▸ Try Rail Demo / Try Home Demo: her card first, then (on Build it) the build in its own process, then the demo's
    own window, on the Field."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QSizePolicy, QVBoxLayout
    import importlib
    from .model_words import plain_only
    name, module = DEMOS[key]
    notice = getattr(importlib.import_module(module), 'NOTICE', '')
    words = [WORDS['card'].format(name=name, notice=notice), WORDS['where'].format(folder='~/%s/%s …' % (FOLDER, name)), WORDS['opens']]
    face = getattr(getattr(host, 'shell2', None), 'face', None)
    if face is None:                 # a window with no column of hers: the same words, in a question
        if QMessageBox.question(host, WORDS['menu_' + key], '\n\n'.join(plain_only(w) for w in words)) == QMessageBox.Yes:start(host, key, None)
        return None
    from .shell2 import button
    card = QFrame();card.setObjectName('KasDemoCard')
    from . import boss_theme as bt
    card.setStyleSheet('QFrame#KasDemoCard {border:1px solid %s; background:%s;}' % (bt.LINE, bt.CARD))
    box = QVBoxLayout(card);box.setContentsMargins(10, 8, 8, 8);box.setSpacing(6)
    card.lines = []
    for text in words:
        label = QLabel(plain_only(text));label.setWordWrap(True);label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse);box.addWidget(label);card.lines.append(label)
    row = QHBoxLayout();row.setSpacing(8)
    go = button(WORDS['build'], 'stac', 'Build %s in a new folder of its own and open it in a window of its own' % name);go.setObjectName('KasDemoBuild')
    no = button(WORDS['not_now'], 'quiet', 'Nothing is built');no.setObjectName('KasDemoNotNow')
    row.addWidget(go);row.addWidget(no);row.addStretch(1);box.addLayout(row)
    card.state = QLabel('');card.state.setWordWrap(True);card.state.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.state.hide();box.addWidget(card.state)

    def said(text):
        card.state.setText(plain_only(text));card.state.show()

    def build_it():
        go.setEnabled(False);no.setEnabled(False);start(host, key, said)

    def not_now():
        go.setEnabled(False);no.setEnabled(False);said(WORDS['left'])
    go.clicked.connect(build_it);no.clicked.connect(not_now)
    card.go, card.no = go, no
    face.add(card)
    return card


def start(host, key, said=None):
    """The build in a process of its own; when it is done, the demo's window. `said` puts her words on the card."""
    from PySide6.QtCore import QProcess, QProcessEnvironment, QTimer
    from . import boss_theme as bt
    from . import locations
    name, _ = DEMOS[key]
    say = said or (lambda text: host.statusBar().showMessage(text, 12000))
    try:folder = fresh_folder(name)
    except OSError as exc:
        say(WORDS['failed'].format(name=name, why=str(exc)[:200]));return None
    say(WORDS['building'].format(name=name))
    process = QProcess(host);process.setProgram(sys.executable);process.setArguments(['-m', 'workbench.demo_try', key, str(folder)])
    process.setWorkingDirectory(str(locations.PACKAGE))
    env = QProcessEnvironment()
    for k, v in os.environ.items():env.insert(k, v)
    process.setProcessEnvironment(env)
    stop = QTimer(process);stop.setSingleShot(True);stop.timeout.connect(process.kill)

    def finished(*_):
        stop.stop()
        out = bytes(process.readAllStandardOutput()).decode('utf-8', 'replace').strip().splitlines()
        try:answer = json.loads(out[-1]) if out else {}
        except ValueError:answer = {}
        if not answer.get('ok'):
            why = answer.get('why') or 'the build stopped before it was done'
            say(WORDS['failed'].format(name=name, why=why));return
        window = QProcess();window.setProgram(sys.executable);window.setArguments(['-m', 'workbench.launch'])
        window.setWorkingDirectory(str(locations.PACKAGE))
        shown = QProcessEnvironment()
        for k, v in demo_environment(folder, bt.APPEARANCE).items():shown.insert(k, v)
        window.setProcessEnvironment(shown);window.startDetached()
        say(WORDS['built'].format(name=name, folder=str(folder)))
    process.finished.connect(finished)
    process.start();stop.start(BUILD_SECONDS * 1000)
    host._demo_build = process
    return process


if __name__ == '__main__':
    sys.exit(main())
