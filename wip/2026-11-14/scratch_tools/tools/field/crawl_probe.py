# the crash hunt: open each work page and press every control a hand could press, one at a time, coming back each time.
# A dialog that comes up is pictured by name and closed. What is looked for: the program ending, and tracebacks.
import os, sys, traceback
from PySide6.QtWidgets import QApplication, QAbstractButton, QPushButton, QToolButton, QMenu, QTabBar, QComboBox, QDialog
from PySide6.QtCore import QTimer, QPoint, Qt as Q
from workbench import tool_faces as faces
MODE = os.environ.get('CRAWL_MODE', 'words'); ONLY = os.environ.get('CRAWL_ONLY', '')
w.a_field.trigger(); settle(); v = w.field_page.view; bar = w.centre_bar
if MODE == 'icons': faces.choose(w, 'icons'); settle(100, 2)
seen_dialogs = []
def closer():
    for _ in range(4):
        m = QApplication.activeModalWidget(); p = QApplication.activePopupWidget()
        if p is not None:
            seen_dialogs.append('popup ' + type(p).__name__); p.close(); continue
        if m is not None and m is not w:
            seen_dialogs.append('dialog ' + type(m).__name__ + ' “' + m.windowTitle()[:40] + '”')
            (m.reject() if isinstance(m, QDialog) else m.close()); continue
        break
tick = QTimer(); tick.timeout.connect(closer); tick.start(150)
errors = []
def hook(kind, value, tb):
    errors.append(''.join(traceback.format_exception(kind, value, tb))[-900:]); sys.__excepthook__(kind, value, tb)
sys.excepthook = hook
def open_tile(title):
    o = next((o for o in v.field.objects if o.title.startswith(title)), None)
    w.a_field.trigger(); settle(150, 4); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(700, 6); return w.tabs.currentWidget()
def controls(page):
    found = []
    for b in list(bar.findChildren(QAbstractButton)) + list(page.findChildren(QAbstractButton)):
        try:
            if b.isVisible() and b.isEnabled() and b.width() > 4 and b.height() > 4: found.append(b)
        except RuntimeError: pass
    return found
def name_of(b):
    return (b.text() or b.accessibleName() or b.objectName() or type(b).__name__).replace('\n', ' ')[:48]
PAGES = [('Sheet', '07 Bench readings'), ('PDF', '07_Bench_Readings.pdf'), ('Writing', '07 Case conclusion'), ('Finding', 'Settled draw'), ('Calc', '07 Settled power')]
total = 0; report = []
for label, tile in PAGES:
    if ONLY and ONLY != label: continue
    page = open_tile(tile); names = []
    for b in controls(page):
        n = name_of(b)
        if n not in names: names.append(n)
    print('== %s (%s): %d controls: %s' % (label, MODE, len(names), names), flush=True)
    for n in names:
        page = open_tile(tile)
        b = next((b for b in controls(page) if name_of(b) == n), None)
        if b is None: print('   %-40s not there on return' % n, flush=True); continue
        before = len(errors); seen_dialogs.clear()
        print('   pressing %-40s' % n, end=' ', flush=True)
        if isinstance(b, QToolButton) and b.menu() is not None:
            b.menu().aboutToShow.emit(); lines = [a for a in b.menu().actions() if not a.isSeparator() and a.isEnabled()]
            print('menu of %d lines' % len(lines), flush=True)
            for i in range(len(lines)):
                page = open_tile(tile); b = next((x for x in controls(page) if name_of(x) == n), None)
                if b is None: break
                b.menu().aboutToShow.emit(); ls = [a for a in b.menu().actions() if not a.isSeparator() and a.isEnabled()]
                if i >= len(ls): break
                before = len(errors); seen_dialogs.clear(); print('      line %-38s' % ls[i].text()[:38], end=' ', flush=True)
                ls[i].trigger(); settle(350, 4); total += 1
                print('ok' if len(errors) == before else 'TRACEBACK', '|', ', '.join(seen_dialogs) or '-', flush=True)
                if len(errors) > before: report.append((label, n + ' ▸ ' + ls[i].text(), errors[-1]))
            continue
        QTest.mouseClick(b, Qt.LeftButton); settle(350, 4); total += 1
        print('ok' if len(errors) == before else 'TRACEBACK', '|', ', '.join(seen_dialogs) or '-', flush=True)
        if len(errors) > before: report.append((label, n, errors[-1]))
    # the right button on the page, and the keyboard on a control while the page is opened again
    page = open_tile(tile); seen_dialogs.clear(); before = len(errors)
    target = page.childAt(page.rect().center()) or page
    QTest.mouseClick(target, Qt.RightButton, Qt.NoModifier, target.rect().center()); settle(300, 3)
    print('   right button on the page: %s | %s' % ('ok' if len(errors) == before else 'TRACEBACK', ', '.join(seen_dialogs) or '-'), flush=True)
    for b in controls(page)[:40]:
        try:
            if b.focusPolicy() != Qt.NoFocus: b.setFocus(); settle(30, 1)
        except RuntimeError: continue
        page2 = open_tile(tile)
    print('   keyboard on each control in turn, page opened again each time: still running', flush=True)
tick.stop()
print('pressed', total, 'controls and menu lines | tracebacks:', len(errors))
for label, n, text in report: print('--- %s / %s\n%s' % (label, n, text))
print('CRAWL', 'CLEAN' if not errors else 'FOUND %d' % len(errors))
