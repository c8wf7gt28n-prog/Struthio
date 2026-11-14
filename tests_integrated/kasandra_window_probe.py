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
    # paint time at this size, into the format a window's backing store has (a plain ARGB32 image measures Qt's conversion)
    stage.clock = None;stage.memo = {};stage.paint_ms.clear()
    image = QImage(stage.size(), QImage.Format_ARGB32_Premultiplied)
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
    if mast is not None:      # her terminal's ground: a pixel of empty thread space, and the whole column round it
        pane = w.right_pane;image = pane.grab().toImage();inside = face.mapTo(pane, QPoint(face.width() // 2, face.height() - 20))
        out['ground'] = image.pixelColor(inside.x(), inside.y()).name()
        out['ground_round'] = [image.pixelColor(x, y).name() for x, y in ((10, pane.height() // 2), (pane.width() - 3, pane.height() // 2),
                                                                         (pane.width() // 2, pane.height() - 10), (pane.width() // 2, 3))]
    out['scroll'] = p.rect(face.scroll)
    out.update(apps_measures(p))
    return out


def apps_measures(p):
    """Apps in the head: the owner's neon kp logo (0.8.3), its size and place, its tip, the words when its bytes are not the
    recorded ones, its neon by the Glow dial (none on the Clean desk), its catch as the list opens (none with Reduce motion),
    and the window icon (Graphite's sharpened point in both appearances)."""
    from unittest.mock import patch
    from PySide6.QtCore import QRect
    from workbench import boss_qt, boss_theme as bt, kasandra_art, kp_logo, shell2
    from workbench.graphite_brand import mark_tile
    w = p.w;out = {};prog = w.shell2.top.programs
    out['apps'] = dict(icon=[prog.iconSize().width(), prog.iconSize().height()], name=prog.accessibleName(), text=prog.text(), rect=p.rect(prog),
                       tip=prog.toolTip(), logo=prog.logo is not None, kind=type(prog).__name__, band=w.desk.band)
    if prog.logo is not None:
        r = prog.logo_rect();out['apps']['logo_rect'] = [r.x(), r.y(), r.width(), r.height()]

        def outside(image):      # the light outside the drawing: summed luminance above the band's own, beside the logo
            box = QRect(round(r.x()), round(r.y()), round(r.width()), round(r.height()))
            total = 0.0
            for y in range(image.height()):
                for x in list(range(0, max(0, box.left() - 1))) + list(range(min(image.width(), box.right() + 2), image.width())):
                    c = image.pixelColor(x, y);total += 0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()
            return round(total, 1)
        lit = {}
        for key, level in (('neon', 3.0), ('bright', 1.9), ('soft', 1.0), ('zero', 0.0)):
            bt.GLOW[0] = level;prog.repaint();lit[key] = outside(prog.grab().toImage())
        bt.GLOW[0] = 3.0
        boss_qt.choose_art(w, 'clean');p.settle(20, 2);prog.repaint();lit['clean'] = outside(prog.grab().toImage());out['clean_level'] = prog.level()
        boss_qt.choose_art(w, 'illustrated');p.settle(20, 2)
        out['apps_light'] = lit
        hatch = w.type_bar.hatch
        out['catch_anchor'] = hatch.programs.anchor is prog
        hatch.open_list();p.settle(10, 1);out['catch_on_open'] = prog.caught_at is not None;hatch.programs.hide();p.settle(200, 2)
        out['catch_settled'] = prog.caught_at is None
        w.session.state.setdefault('reading_profile', {})['reduce_motion'] = True
        out['catch_reduce_motion'] = prog.catch();w.session.state['reading_profile']['reduce_motion'] = False
    real = kasandra_art.mark

    def without(*names):
        return lambda base, name: None if name in names else real(base, name)
    with patch.object(kasandra_art, 'mark', without('kp_neon.png')):
        shell2.apps_mark(prog, w);out['apps_words'] = prog.text();out['apps_words_logo'] = prog.logo is not None
    if bt.APPEARANCE == 'kasandra':shell2.apps_mark(prog, w)
    tile = mark_tile(256).toImage().convertToFormat(prog.grab().toImage().format())
    shown = w.windowIcon().pixmap(256, 256).toImage().convertToFormat(tile.format())
    out['window_icon_graphite'] = shown.size() == tile.size() and bytes(shown.constBits()) == bytes(tile.constBits())
    return out


def case_review(p):
    """The 0.8.3 review's findings, each measured in the real window (Kasandra): the faces of tooltips, the Documents page,
    a Markdown note and the Terminal; the font report's words; her words folded only where a line must break; the Now
    line's waiting link and the state above it; what she speaks with and what she learns from; a face and a size the owner
    chooses reaching her masthead and a line's slab; her cursor asleep with Reduce motion and out of sight; her hologram
    asleep under the idle display, a touch while asleep, a picture that will not decode; a note in the viewer at this size."""
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QFontInfo, QImage
    from PySide6.QtWidgets import QLabel, QToolTip
    from workbench import boss_theme as bt, document_qt, hologram_qt, kasandra_art, kasandra_column, reading_preferences, settings_qt, shell2
    from workbench.view_modules import markdown_view
    w = p.w;face = w.shell2.face;stage = w.hologram;out = {}
    w.settings_navigator.cabinet.click();p.settle(40, 4)
    tip = QToolTip.font();out['tooltip'] = [QFontInfo(tip).family(), tip.pixelSize()]
    prose, code = document_qt.fonts_of(w);out['document'] = [QFontInfo(prose).family(), QFontInfo(code).family()]
    css = markdown_view.css(w);out['markdown'] = dict(face=bt.FACE in css, mono=bt.MONO in css, plex='IBM Plex' in css)
    from workbench.console_qt import Console
    console = w.findChild(Console)
    if console is not None:
        reading_preferences.apply(w);p.settle(20, 2);doc = console.output.document()
        block = doc.firstBlock().blockFormat()
        out['console'] = dict(kept=bool(console.output.property('arcReadingPreview')), face=doc.defaultFont().family(),
                              spacing=[block.lineHeightType(), block.lineHeight()])
    from workbench import ledger_control
    row = next(r for r in ledger_control.settings(w.ledger_bridge.kernel)['settings'] if r['key'] == 'reading.family')
    out['font_report'] = [row['application_state'], settings_qt.state_words(row)]
    # her words: a name that fits a line is never cut at a line's end, in her leaded words and in a plain row of a card
    name, other = '07_Bench_Readings.pdf', '07_Rail_Limits_Rev_B.pdf'
    said = lambda n:'\u2190 source \u00b7 %s (current) \u00b7 supports' % n
    card = face.say(said(name) + '\n' + said(other));row_label = QLabel(shell2.breakable(said(other)));row_label.setWordWrap(True);card.box.addWidget(row_label)
    long = 'path/to/a/very/long/folder/name/that/never/fits/one/line/of/her/column.csv'
    far = QLabel(long);far.setWordWrap(True);card.box.addWidget(far);p.settle(40, 6)
    out['fold'] = dict(leaded=name in card.text.text() and other in card.text.text(), plain=other in row_label.text(), room=card.text.property('lineRoom'),
                       long_breaks=far.text().count('\u200b'), long_whole=far.text().replace('\u200b', '') == long)
    # the Now line's waiting link, and the state above it
    from unittest.mock import patch
    from workbench import agenda_qt
    with patch.object(agenda_qt, 'summary', return_value=('Nothing running  \u00b7  {waiting}  \u00b7  {open}', 1)):
        face.agenda.setText('');face.show_agenda();p.settle(20, 2)
    out['agenda_link'] = '1\u00a0waiting for you' in face.agenda.text()
    probe_label = QLabel();probe_label.setFont(face.agenda.font())
    html = 'Now: Nothing running  \u00b7  {waiting}  \u00b7  {open} \u00b7 {activity}';others = {'open': 'open', 'activity': 'activity'}
    def kept(width):
        probe_label.resize(width, 40);return '\u00a0' in shell2.together(probe_label, html, 'waiting', '1 waiting for you', others)
    out['agenda_together'] = dict(wide=kept(600), early=kept(240), column=kept(face.agenda.width()), width=face.agenda.width())
    out['column_state'] = kasandra_art.column_state(w);out['current_state'] = kasandra_art.current_state(w)
    if stage is not None:stage.follow(force=True)
    out['masthead_word'] = face.masthead.word.text()
    face.agenda_waiting = 0
    face.refresh();out['model_tip'] = face.model.toolTip()
    # her cursor: it breathes only while something waits and it may move
    cursor = face.masthead.cursor
    with patch.object(kasandra_art, 'current_state', return_value='awaiting_approval'):
        face.masthead.show_state('idle');face.masthead.show_state('awaiting_approval');p.settle(20, 2)
        out['cursor_waiting'] = cursor._timer.isActive()
        profile = dict(w.reading_profile);profile['reduce_motion'] = True
        reading_preferences.apply(w, profile, True);p.settle(20, 2);out['cursor_reduce_motion'] = [cursor._timer.isActive(), cursor.alpha()]
        profile['reduce_motion'] = False;reading_preferences.apply(w, profile, True);p.settle(20, 2);out['cursor_back'] = cursor._timer.isActive()
        with patch.object(kasandra_column, 'app_active', return_value=False):
            cursor.wake_or_sleep();out['cursor_inactive'] = cursor._timer.isActive()
        cursor.wake_or_sleep()
    face.masthead.show_state('idle')
    # a face and a size the owner chose reach her masthead and the slab on a card already shown
    face.answer_in_stac({'stac': '@files | rows | count', 'title': 'files', 'kind': 'files'}, 'Reading it in a line.');p.settle(30, 3)
    cards = [c for c in (face.lines.itemAt(i).widget() for i in range(face.lines.count())) if c is not None]
    slab = next((l for l in cards[-1].findChildren(QLabel) if l.toolTip().startswith('@files')), None)
    def faces_now():
        for widget in (face.masthead.name, face.model, slab):widget.ensurePolished()
        return dict(name=QFontInfo(face.masthead.name.font()).family(), model=QFontInfo(face.model.font()).family(),
                    slab=[QFontInfo(slab.font()).family(), slab.font().pixelSize()], word=face.masthead.word.styleSheet())
    out['faces_default'] = faces_now()
    own = dict(w.reading_profile, family='DejaVu Serif', prose_family='DejaVu Serif', code_family='DejaVu Sans Mono', ui_pt=18.0)
    reading_preferences.apply(w, own, True);p.settle(30, 3);out['faces_own'] = faces_now()
    reading_preferences.apply(w, dict(own, family='IBM Plex Sans', prose_family='IBM Plex Sans', code_family='IBM Plex Mono', ui_pt=14.0), True);p.settle(30, 3)
    out['faces_back'] = faces_now()
    # her hologram: asleep under the idle display, no tear left by a touch while asleep, none for a picture that will not decode
    if stage is not None:
        idle_type = type(w.idle_display)
        with patch.object(idle_type, 'showing', new=property(lambda self:True)):
            w.idle_display._hologram();out['idle_running'] = stage._timer.isActive()
        w.idle_display._hologram();out['idle_back'] = stage._timer.isActive()
        with patch.object(hologram_qt, 'app_active', return_value=False):
            stage.wake_or_sleep();stage.memo = {};stage._inside = False
            stage.touch(stage.figure.center() + stage.pos());out['touch_asleep'] = 'touch' in (stage.memo or {})
        stage.wake_or_sleep()
        from types import SimpleNamespace
        fake = SimpleNamespace(left_pane=w.left_pane, root=w.root, hologram='before')
        with patch.object(kasandra_art, 'cutout', return_value=QImage()):
            out['undecodable'] = [hologram_qt.install(fake) is None, fake.hologram]
    # a note in the viewer at this size: the panes keep their width and no action is cut
    from workbench import files_service
    note = files_service.root(w.ledger_bridge.kernel) / 'bench note.md'
    note.write_text('# Bench note\n\nSettled draw is **3.36 W**.\n\n`office.get {"id":"x"}`\n')
    pane_before = w.desk.pane;w.open_in_viewer(note);p.settle(60, 8)
    tab = w.tabs.currentWidget()
    actions = getattr(tab, 'actions_row', ())
    shown = [b.text() for b in actions if b.isVisible()]
    cut = [b.text() for b in actions if b.isVisible() and b.width() < b.sizeHint().width()]
    behind = [a.text() for a in tab.more_menu.actions()] if hasattr(tab, 'more_menu') else []
    wanted = [b.text() for b in actions if b.property('wanted')]
    out['viewer'] = dict(pane=[pane_before, w.desk.pane, w.left_pane.width()], shown=shown, cut=cut, behind=behind, wanted=wanted)
    from PySide6.QtWidgets import QTextBrowser
    reading = next((b for b in tab.findChildren(QTextBrowser) if b.accessibleName() == 'Markdown, as it reads'), None)
    if reading is not None:
        doc = reading.document();code = set();block = doc.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                piece = it.fragment()
                if piece.isValid() and 'office.get' in piece.text():code.update(piece.charFormat().fontFamilies() or [])
                it += 1
            block = block.next()
        out['markdown_shown'] = dict(words=QFontInfo(doc.defaultFont()).family(), code=sorted(code))
    return out


def case_graphite_column(p):
    from PySide6.QtWidgets import QLabel
    w = p.w;face = w.shell2.face
    face.answer_in_stac({'stac': '@files | rows | count', 'title': 'files', 'kind': 'files'}, 'Reading it in a line.')
    p.settle(30, 3)
    cards = [c for c in (face.lines.itemAt(i).widget() for i in range(face.lines.count())) if c is not None]
    slab = next((l for l in cards[-1].findChildren(QLabel) if l.toolTip().startswith('@files')), None)
    slab.ensurePolished()
    return dict(portrait=type(face.portrait).__name__, masthead=getattr(face, 'masthead', 'missing'), margin=face.lines.contentsMargins().right(),
                hologram=getattr(w, 'hologram', 'missing'), slab=[slab.font().family(), slab.font().pixelSize()],
                delete=[w.trash_can.word_font.letterSpacing(), w.trash_can.word_font.family()],
                tabs=sorted({b.font().family() for b in w.left_pane.tabs.buttons + w.right_pane.tabs.buttons}),
                least=w.panes['least'], need=w.panes['need'], apps=apps_measures(p))


CASES = dict(delete=case_delete, wiring=case_wiring, hologram=case_hologram, hologram_absent=case_hologram_absent, column=case_column,
             graphite_column=case_graphite_column, review=case_review)


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
