# Third set: each results row lit in turn (rows with their own ink: ask, search, the line); the logo's catch when Apps opens
# by the mouse, and with Reduce motion. Exec'd by nomodel.py.
import json, traceback, time
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QImage
from PySide6.QtWidgets import QApplication
from workbench import boss_theme as bt, files_service
PRE = '%s_%s' % (bt.APPEARANCE, tag)
def rect(widget):
    tl = widget.mapTo(w, QPoint(0, 0)) if widget.window() is w else widget.mapToGlobal(QPoint(0, 0)) - w.mapToGlobal(QPoint(0, 0))
    return [tl.x(), tl.y(), widget.width(), widget.height()]
def grab():
    return w.grab().toImage().convertToFormat(QImage.Format_RGB32)
root = files_service.root(w.ledger_bridge.kernel)
(root / 'bench readings.csv').write_text('parameter,value,unit\nRail voltage,12,V\n')
settle(60, 6)
try:
    box = w.type_bar.box
    for text in ('bench', '@files:bench readings.csv'):
        box.setFocus();box.setText(text);box.update_results(text);settle(200, 3)
        pop = box.popup;lst = pop.list
        rows = [i for i in range(lst.count()) if lst.item(i).flags() & Qt.ItemIsEnabled]
        print('NOTE results for', repr(text), [(i, lst.item(i).text()[:40], lst.item(i).foreground().color().name()) for i in range(lst.count())])
        for i in rows[:5]:
            lst.setCurrentRow(i);settle(30, 2);align(1)
            img = grab();r = lst.visualItemRect(lst.item(i));o = lst.viewport().mapTo(w, QPoint(0, 0))
            crop = img.copy(QRect(o.x() + r.x(), o.y() + r.y() - 2, min(r.width(), 640), r.height() + 4))
            crop = crop.scaled(crop.width() * 3, crop.height() * 3, Qt.IgnoreAspectRatio, Qt.FastTransformation)
            f = 'T_results_%s_%d_%s.png' % ('line' if text.startswith('@') else 'words', i, PRE);crop.save(str(OUT / f));print('saved', f, lst.item(i).text()[:40])
        pop.hide();box.clear();settle(100, 2)
except Exception:
    print('NOTE FAILED results', traceback.format_exc()[-600:])
try:
    prog = w.shell2.top.programs
    if getattr(prog, 'logo', None) is not None:
        from workbench import kp_logo
        seen = []
        orig = kp_logo.AppsButton.catch
        def spy(self):
            r = orig(self);seen.append(r);return r
        kp_logo.AppsButton.catch = spy
        prog.click();QApplication.processEvents();settle(20, 1)
        print('NOTE apps by click: catch returned', seen, 'surge now %.2f' % prog.surge())
        lst = w.type_bar.hatch.programs;lst.hide();settle(300, 2)
        state = w.session.state.setdefault('reading_profile', {});keep = state.get('reduce_motion')
        state['reduce_motion'] = True;seen.clear()
        prog.click();QApplication.processEvents();settle(20, 1)
        print('NOTE apps by click with Reduce motion: catch returned', seen, 'surge %.2f' % prog.surge())
        lst.hide();settle(200, 2)
        if keep is None:state.pop('reduce_motion', None)
        else:state['reduce_motion'] = keep
        print('NOTE apps tip', repr(prog.toolTip()), 'accessible', repr(prog.accessibleName()), 'text', repr(prog.text()), 'size', prog.size().toTuple(), 'icon size', prog.iconSize().toTuple())
except Exception:
    print('NOTE FAILED apps', traceback.format_exc()[-600:])
print('FRAMES DONE')
