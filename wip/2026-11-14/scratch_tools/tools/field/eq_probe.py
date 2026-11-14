# the head's middle: the equalizer, the address only while typed (Ctrl+L), the name back in the bar above the work
from workbench.shell2 import PathBar
top = w.shell2.top; eq = top.equalizer; head = w.findChild(PathBar); ok = True
w.a_field.trigger(); settle(1300, 3)
print('equalizer shown:', eq.isVisible(), eq.geometry().getRect(), '| bars:', len(eq.shown), 'in groups', getattr(eq, 'sizes', None), '| readable:', eq.readable, '| now:', [round(v, 2) for v in eq.target], '| address line shown:', head.isVisible()); ok &= eq.isVisible() and not head.isVisible()
if hasattr(eq, 'words'):
    print('   what it reads:', eq.words); print('   not reported on this machine:', eq.missing); ok &= len(eq.sizes) == 6 and sum(eq.sizes) == len(eq.shown) == len(eq.peak)
    from PySide6.QtWidgets import QLabel as _QLabel
    QTest.mouseClick(eq, Qt.LeftButton); settle(250, 3); card = eq.card; lines = [l.text() for l in card.findChildren(_QLabel)] if card is not None else []
    print('   a click -> card shown:', card is not None and card.isVisible(), '|', lines[:3]); ok &= card is not None and card.isVisible() and len(lines) == 7
    if card is not None: card.grab().save(str(OUT / ('Eq_Card_%s.png' % tag))); card.hide()
import subprocess, sys as _sys
burn = subprocess.Popen([_sys.executable, '-c', 'import time\nt=time.time()\nwhile time.time()-t<4: pass'])
seen = 0.0
for _ in range(6): settle(450, 1); seen = max(seen, max(eq.shown))
burn.wait(); print('while another program worked one thread hard: highest bar seen', round(seen, 2), '| peaks', [round(v, 2) for v in eq.peak]); ok &= seen > 0.5
save('Eq_00_Field_%s.png' % tag)
v = w.field_page.view; o = next(o for o in v.field.objects if o.title.startswith('07_Bench')); v.field.select(o.id); v._describe(); QTest.keyClick(v, Qt.Key_Return); settle(900, 8)
print('a page open: the bar above the work says', repr(w.centre_bar.title.text()), 'shown', w.centre_bar.title.isVisible()); ok &= w.centre_bar.title.isVisible() and '07_Bench' in w.centre_bar.title.text()
save('Eq_01_Page_%s.png' % tag)
head.edit_location(); settle(200, 3); print('Ctrl+L: address shown', head.isVisible(), 'has the keyboard', head.hasFocus(), '| equalizer shown', eq.isVisible(), '| it says', head.text()[:40]); ok &= head.isVisible() and head.hasFocus() and not eq.isVisible()
save('Eq_02_Address_While_Typed_%s.png' % tag)
QTest.keyClick(head, Qt.Key_Escape); settle(200, 3); print('Esc: address shown', head.isVisible(), '| equalizer shown', eq.isVisible()); ok &= not head.isVisible() and eq.isVisible()
QTest.mouseClick(w.centre_bar.title, Qt.LeftButton); settle(250, 3); print('a click on the name: address shown', head.isVisible(), 'has the keyboard', head.hasFocus(), '| it says', head.text()[:40]); ok &= head.isVisible() and head.hasFocus()
QTest.keyClick(head, Qt.Key_Escape); settle(200, 3); ok &= not head.isVisible() and eq.isVisible()
eq.still = lambda: True; eq.read(); print('with motion reduced the bars change at once: gliding', eq.glide.isActive())
print('EQ PROBE', 'PASS' if ok else 'FAIL')
