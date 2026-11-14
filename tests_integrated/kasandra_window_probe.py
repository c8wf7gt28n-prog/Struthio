"""A helper for the 0.8.3 tests, not a test module: the real window in one appearance, offscreen at one size, on a temporary
workspace and profile, with every hold of test_context_menu in place (no provider request, no worker launch, no job, no
session or power call, no process). It runs one case and prints its measurements as JSON on its last line.

    python -B tests_integrated/kasandra_window_probe.py APPEARANCE WIDTH HEIGHT CASE

APPEARANCE is kasandra or graphite; CASE is one of the functions named in CASES.
"""
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0, str(ROOT))


def run(appearance, width, height, case):
    folder = tempfile.TemporaryDirectory(prefix='graphite-083-');run = Path(folder.name)
    screen = run / 'screen.json'
    screen.write_text(json.dumps({'screens': [{'name': 'probe', 'x': 0, 'y': 0, 'width': width, 'height': height, 'logicalDpi': 96,
                                               'logicalBaseDpi': 96, 'dpr': 1.0}]}))
    os.environ.update(QT_QPA_PLATFORM='offscreen:configfile=' + str(screen), ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
                      ARC1_WORKBENCH_CONFIG_HOME=str(run / 'profile'), ARC_LEDGER_CONCERN=str(run / 'Concern'), HOME=str(run / 'home'),
                      GRAPHITE_APPEARANCE=appearance)
    (run / 'home').mkdir()
    os.environ.pop('ARC_LEDGER_XSESSION', None)
    from PySide6.QtCore import QProcess
    from PySide6.QtWidgets import QMessageBox
    from workbench import clip, locations, session_power
    from workbench.engineering_kernel import Kernel
    from workbench.qt_app import WorkbenchWindow, make_app
    from workbench.session import Session
    holds = [patch.object(clip, '_request', side_effect=AssertionError('No provider request')),
             patch.object(Kernel, 'launch', side_effect=AssertionError('No worker launch')),
             patch.object(Kernel, 'submit', side_effect=AssertionError('No job submission')),
             patch.object(session_power, 'system', side_effect=OSError('no login session (held)')),
             patch.object(QMessageBox, 'question', return_value=QMessageBox.No)]
    for hold in holds:hold.start()
    app = make_app([]);root = locations.office(run / 'workspace');session = Session(run / 'profile/session.json', root)
    w = WorkbenchWindow(root, session, restore=False);platform.processor()
    for hold in (patch.object(subprocess, 'Popen', side_effect=AssertionError('No process start')),
                 patch.object(os, 'system', side_effect=AssertionError('No shell command')),
                 patch.object(QProcess, 'startDetached', side_effect=AssertionError('No detached program'))):hold.start()
    w.resize(width, height);w.show();w.activateWindow()
    probe = Probe(app, w)
    probe.settle(60, 10)
    try:w.ledger_bridge.timer.stop()
    except AttributeError:pass
    out = CASES[case](probe)
    w._closing = True
    print(json.dumps(out, default=str))
    sys.stdout.flush();os._exit(0)


class Probe:
    def __init__(self, app, w):self.app, self.w = app, w

    def settle(self, ms=30, n=4):
        from PySide6.QtTest import QTest
        for name in ('agenda_runner', 'study_idle'):
            obj = getattr(self.w, name, None)
            if obj is not None and hasattr(obj, 'timer'):obj.timer.stop()
        for _ in range(n):self.app.processEvents();QTest.qWait(ms)

    def rect(self, widget):
        from PySide6.QtCore import QPoint
        tl = widget.mapTo(self.w, QPoint(0, 0));return [tl.x(), tl.y(), widget.width(), widget.height()]


def case_delete(p):
    import math
    from PySide6.QtGui import QFont
    from workbench import pane_qt, trash_can_qt
    can = p.w.trash_can;font = can.word_font
    expected = pane_qt.trash_size(1.0, math.ceil(can.extent(font, 'DELETE')[2]), math.ceil(can.extent(can.count_font, '999')[2]),
                                  trash_can_qt.can_ink(can.can), can.count_gap)
    return dict(word=trash_can_qt.WORD, name=can.accessibleName(), tip=can.toolTip(), spacing=font.letterSpacing(),
                absolute=font.letterSpacingType() == QFont.AbsoluteSpacing, family=font.family(), size=[can.width(), can.height()],
                expected=list(expected), rect=p.rect(can))


def case_wiring(p):
    from workbench import boss_theme as bt, reading_preferences as rp, shell2
    from PySide6.QtGui import QFontDatabase
    return dict(MONO=bt.MONO, FACE=bt.FACE, DISPLAY=bt.DISPLAY, shell_mono=shell2.MONO, shell_sans=shell2.SANS,
                in_force=list(rp.in_force(('IBM Plex Sans', 'IBM Plex Sans', 'IBM Plex Mono'))),
                own=list(rp.in_force(('DejaVu Sans', 'DejaVu Serif', 'DejaVu Sans Mono'))),
                families=[f for f in QFontDatabase.families() if 'Elite' in f or 'Plex' in f])


def tree_rows(tree):
    from PySide6.QtCore import QRect
    rects = [];item = tree.topLevelItem(0) if tree.topLevelItemCount() else None
    while item is not None:
        r = tree.visualItemRect(item)
        if r.isValid():rects.append(r)
        item = tree.itemBelow(item)
    return rects


def case_hologram(p):
    import random
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtGui import QGuiApplication, QImage
    from workbench import hologram as holo, hologram_qt, kasandra_art
    w = p.w;stage = w.hologram;nav = w.settings_navigator;out = {}
    out['installed'] = stage is not None
    if stage is None:return out
    path = kasandra_art.mark(kasandra_art.folder(w.root), 'hologram.webp')
    cut = kasandra_art.cutout(path)
    out['cutout'] = dict(alpha=cut.hasAlphaChannel(), corner=cut.pixelColor(2, 2).alpha(), same=kasandra_art.cutout(path) is cut)
    nav.cabinet.click();p.settle(40, 6)
    out['active'] = hologram_qt.app_active()
    out['files'] = dict(visible=stage.isVisible(), stance=stage.stance, interval=stage._timer.interval(), running=stage._timer.isActive(),
                        figure=list(stage.figure.translated(stage.mapTo(w, QPoint(0, 0))).getRect()), stage=p.rect(stage))
    # her stage never meets a visible row or DELETE
    tree = w.cabinet_page.tree;viewport = tree.viewport()
    box = QRect(*p.rect(stage))
    hit = [r for r in tree_rows(tree) if QRect(r.translated(viewport.mapTo(w, QPoint(0, 0)))).intersects(box)]
    out['meets_rows'] = len(hit);out['meets_delete'] = box.intersects(QRect(*p.rect(w.trash_can)))
    # asleep when the application is not active
    with patch.object(hologram_qt, 'app_active', return_value=False):
        stage.wake_or_sleep();out['inactive_running'] = stage._timer.isActive()
    stage.wake_or_sleep()
    # the tree scrolls: she is hidden within the same signal (no events processed)
    def open_all(item):
        item.setExpanded(True)
        for i in range(item.childCount()):open_all(item.child(i))
    for k in range(40):
        tree.topLevelItem(0).addChild(type(tree.topLevelItem(0))(['probe row %d' % k]))
    for i in range(tree.topLevelItemCount()):open_all(tree.topLevelItem(i))
    out['scrolls_hidden_at_once'] = stage.isHidden()
    p.settle(40, 4);out['scroll_range'] = tree.verticalScrollBar().maximum();out['scrolls_hidden'] = stage.isHidden()
    for k in range(40):tree.topLevelItem(0).removeChild(tree.topLevelItem(0).child(tree.topLevelItem(0).childCount() - 1))
    for i in range(tree.topLevelItemCount()):tree.topLevelItem(i).setExpanded(False)
    p.settle(40, 4);out['back'] = stage.isVisible()
    # Settings: she stands aside
    nav.settings.click();p.settle(40, 4);out['settings_hidden'] = stage.isHidden();out['settings_running'] = stage._timer.isActive()
    nav.cabinet.click();p.settle(40, 4)
    # motion, measured on composed frames at 1/12 s steps (tears off), on the stage's own painting
    def frames(state, still=False, n=24):
        stage.state = state;stage.state_at = 100.0;stage.power_at = None;stage.memo = None      # no memo: no tears
        clock = [200.0];stage.clock = lambda: clock[0]
        keep = stage.still
        if still:stage.still = lambda: True
        shots = []
        for i in range(n):
            clock[0] = 200.0 + i / holo.FPS;image = QImage(stage.size(), QImage.Format_ARGB32);image.fill(0)
            stage.memo = None;stage.render(image);shots.append(image)
        stage.still = keep
        return shots
    def lum(image):
        data = bytes(image.constBits());return [0.2126 * data[i + 2] + 0.7152 * data[i + 1] + 0.0722 * data[i] for i in range(0, len(data), 8)]
    def motion(shots):
        values = [lum(s) for s in shots];deltas = [];means = [sum(v) / len(v) for v in values]
        for a, b in zip(values, values[1:]):deltas.append(sum(abs(x - y) for x, y in zip(a, b)) / len(a))
        swing = max(abs(b - a) / max(1.0, a) for a, b in zip(means, means[1:]))
        return round(sum(deltas) / len(deltas), 3), round(swing, 4)
    out['motion'] = {state: motion(frames(state)) for state in ('idle', 'working', 'awaiting_approval')}
    out['motion']['still'] = motion(frames('idle', still=True))
    # paint time at this size
    stage.clock = None;stage.memo = {};stage.paint_ms.clear()
    image = QImage(stage.size(), QImage.Format_ARGB32)
    started = time.perf_counter()
    for i in range(50):stage.render(image)
    out['paint_ms'] = round((time.perf_counter() - started) * 1000 / 50, 3);out['size'] = [stage.width(), stage.height()]
    # Reduce motion: no timer, and two grabs 300 ms apart are the same
    w.session.state.setdefault('reading_profile', {})['reduce_motion'] = True
    stage.place_now();p.settle(20, 2)
    out['still_running'] = stage._timer.isActive()
    a = stage.grab().toImage();p.settle(100, 3);b = stage.grab().toImage()
    out['still_same'] = bytes(a.constBits()) == bytes(b.constBits())
    w.session.state['reading_profile']['reduce_motion'] = False
    # the Clean desk: hidden, its layers dropped, no timer
    from workbench.boss_qt import choose_art
    choose_art(w, 'clean');p.settle(20, 2)
    out['clean'] = dict(hidden=stage.isHidden(), layers=stage.layers is None, running=stage._timer.isActive())
    choose_art(w, 'illustrated');p.settle(20, 2);out['illustrated_back'] = stage.isVisible()
    # states: the word, the cursor and the base agree
    face = w.shell2.face;states = {}
    for state in ('idle', 'working', 'awaiting_approval', 'completed', 'blocked'):
        with patch.object(kasandra_art, 'current_state', return_value=state):
            stage.follow(force=True)
        mast = face.masthead
        states[state] = dict(word=mast.word.text(), cursor=mast.cursor.colour.name(), base=stage.base_colour().name(),
                             role=getattr(__import__('workbench.boss_theme', fromlist=['x']), holo.look(state)[1]).lower())
    out['states'] = states
    return out


def case_hologram_absent(p):
    return dict(hologram=getattr(p.w, 'hologram', 'missing'))


def case_column(p):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QFontInfo
    from PySide6.QtWidgets import QLabel
    from workbench import boss_qt, shell2
    from workbench.boss_qt import PanelInk
    w = p.w;face = w.shell2.face;out = {};left = w.left_pane
    out['portrait'] = None if face.portrait is None else type(face.portrait).__name__
    out['face_inks'] = len([x for x in face.findChildren(PanelInk) if x.kind == 'face'])
    out['margin'] = face.lines.contentsMargins().right();out['pane'] = w.desk.pane
    mast = getattr(face, 'masthead', None)
    out['masthead'] = mast is not None
    if mast is not None:
        p.settle(40, 4)
        out['rule_y'] = mast.mapTo(w, QPoint(0, mast.rule_y())).y()
        out['left_rule_y'] = left.tabs.mapTo(w, QPoint(0, left.tabs.height() - 1)).y()
        out['name'] = [mast.name.text(), QFontInfo(mast.name.font()).family()]
        out['model_family'] = QFontInfo(face.model.font()).family()
        long_name = 'a-very-long-model-name-' + 'x' * 30 + '-instruct-q4'
        face.model.setText(long_name);face.model.setToolTip(long_name);p.settle(20, 2)
        out['model_long'] = [face.model.text(), face.model.toolTip(), long_name]
    bubble = next((c for c in (face.lines.itemAt(i).widget() for i in range(face.lines.count())) if isinstance(c, shell2.Bubble)), None)
    out['bubble_text_width'] = bubble.text.width() if bubble is not None else None
    out['bubble_plain'] = bubble.text.property('plain') if bubble is not None else None
    text = 'one line of her words\nand a second\nand a third, a little longer than the others\nand a fourth'
    lead = shell2.Bubble(text);plain = QLabel(text);plain.setWordWrap(True);plain.setFont(lead.text.font());lead.text.ensurePolished()
    out['lead_ratio'] = round(lead.text.heightForWidth(297) / max(1, plain.heightForWidth(297)), 3)
    out['lead_plain'] = lead.text.property('plain') == text
    card = face.say('A card to read back:\nits second line')
    from workbench.desk_doers import read_desk
    out['read_last'] = read_desk(w, 'talk')['last']
    face.answer_in_stac({'stac': '@files | rows | where kind=csv, unit=mA | count', 'title': 'files', 'kind': 'files'}, 'Reading it in a line.')
    p.settle(30, 3)
    cards = [c for c in (face.lines.itemAt(i).widget() for i in range(face.lines.count())) if c is not None]
    slab = next((l for l in cards[-1].findChildren(QLabel) if l.toolTip().startswith('@files')), None)
    if slab is not None:
        slab.ensurePolished();out['slab'] = [slab.font().family(), slab.font().pixelSize(), slab.text()]
    if mast is not None:      # a pixel of empty thread space: her terminal's ground
        image = face.grab().toImage();out['ground'] = image.pixelColor(face.width() // 2, face.height() - 20).name()
    out['scroll'] = p.rect(face.scroll)
    prog = w.shell2.top.programs
    out['apps'] = dict(icon=[prog.iconSize().width(), prog.iconSize().height()], name=prog.accessibleName(), text=prog.text(), rect=p.rect(prog))
    from workbench import kasandra_art
    real = kasandra_art.mark
    def without(*names):
        return lambda base, name: None if name in names else real(base, name)
    with patch.object(kasandra_art, 'mark', without('kp_emblem_38.png')):
        shell2.apps_mark(prog, w);out['apps_monogram'] = [prog.iconSize().width(), prog.iconSize().height()]
    with patch.object(kasandra_art, 'mark', without('kp_emblem_38.png', 'kp_monogram.png')):
        shell2.apps_mark(prog, w);out['apps_words'] = prog.text()
    shell2.apps_mark(prog, w)
    from workbench.graphite_brand import window_icon_source
    out['icon_source'] = window_icon_source(w.root)
    return out


def case_graphite_column(p):
    from workbench.graphite_brand import window_icon_source
    from PySide6.QtWidgets import QLabel
    w = p.w;face = w.shell2.face
    face.answer_in_stac({'stac': '@files | rows | count', 'title': 'files', 'kind': 'files'}, 'Reading it in a line.')
    p.settle(30, 3)
    cards = [c for c in (face.lines.itemAt(i).widget() for i in range(face.lines.count())) if c is not None]
    slab = next((l for l in cards[-1].findChildren(QLabel) if l.toolTip().startswith('@files')), None)
    slab.ensurePolished()
    return dict(portrait=type(face.portrait).__name__, masthead=getattr(face, 'masthead', 'missing'), margin=face.lines.contentsMargins().right(),
                hologram=getattr(w, 'hologram', 'missing'), icon_source=window_icon_source(w.root), slab=[slab.font().family(), slab.font().pixelSize()],
                delete=[w.trash_can.word_font.letterSpacing(), w.trash_can.word_font.family()])


CASES = dict(delete=case_delete, wiring=case_wiring, hologram=case_hologram, hologram_absent=case_hologram_absent, column=case_column,
             graphite_column=case_graphite_column)


def probe(appearance, width, height, case, extra_env=None, timeout=300):
    """Run one case in a subprocess; its JSON."""
    env = dict(os.environ);env.update(extra_env or {})
    env['QT_QPA_PLATFORM'] = 'offscreen'
    done = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), appearance, str(width), str(height), case],
                          cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=timeout)
    lines = [line for line in done.stdout.splitlines() if line.startswith('{')]
    if not lines:raise AssertionError('probe %s %s gave nothing:\n%s\n%s' % (appearance, case, done.stdout[-2000:], done.stderr[-4000:]))
    return json.loads(lines[-1])


if __name__ == '__main__':
    if os.environ.get('GRAPHITE_083_NO_MARKS'):      # the hologram's mark refused: the left pane stays as it was
        from workbench import kasandra_art
        kasandra_art.mark = lambda base, name: None
    run(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
