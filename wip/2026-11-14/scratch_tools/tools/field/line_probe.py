# the bottom line: five names on the strip, each whole; choosing one; an address goes to Web by itself; Web opens in the browser
from unittest.mock import patch
from PySide6.QtGui import QDesktopServices
bar = w.type_bar; ok = True; settle(600, 3); align()
words = [(k, b.text(), b.isVisible(), b.width(), b.sizeHint().width(), b.geometry().x()) for k, b in bar.targets.items()]
print('strip:', [(k, t, v, wd, need) for k, t, v, wd, need, x in words]); ok &= [t for k, t, v, wd, need, x in words] in (['Stacy', 'Terminal', 'Search', 'Web', 'Log'], ['Kasandra', 'Terminal', 'Search', 'Web', 'Log']) and all(v and wd >= need for k, t, v, wd, need, x in words)
xs = [x for *_, x in words]; print('in order left to right:', xs == sorted(xs), '| the last ends at', bar.targets['log'].geometry().right(), 'of a slot', bar.left.width(), 'wide'); ok &= xs == sorted(xs) and bar.targets['log'].geometry().right() <= bar.left.width()
save('Line_00_Five_Names_%s.png' % tag)
for key in ('shell', 'find', 'web', 'log', 'slate'):
    QTest.mouseClick(bar.targets[key], Qt.LeftButton); settle(200, 2); lit = [k for k, b in bar.targets.items() if b.isChecked()]; print('   chose %-6s -> typing to %-6s | lit: %s | page above the line: %s | the arrow says: %s' % (key, bar.target, lit, bar.console.mode, bar.send.toolTip())); ok &= bar.target == key and lit == [key]
bar.box.setFocus(); QTest.keyClicks(bar.box, 'https://example.org/page'); settle(200, 2); print('typed an address while on Stacy -> typing to', bar.target, '(the lit name changes only when you choose)'); ok &= bar.target == 'slate'
save('Line_01_An_Address_Typed_To_Stacy_%s.png' % tag)
opened = []; asked = []
real_ask = w.shell2.ask; w.shell2.ask = lambda text, about=None: asked.append(text)
try:
    with patch.object(QDesktopServices, 'openUrl', side_effect=lambda url: opened.append(url.toString()) or True):
        QTest.keyClick(bar.box, Qt.Key_Return); settle(200, 2); said1 = bar.message
        QTest.keyClicks(bar.box, 'https://intranet.example/plan what does it say about the budget?'); QTest.keyClick(bar.box, Qt.Key_Return); settle(300, 3)
        print('Enter on a line that is only an address ->', opened, repr(said1), '| a sentence that begins with one ->', 'opened' if len(opened) > 1 else 'not opened', '| asked of Stacy:', [a[:40] for a in asked])
        ok &= opened == ['https://example.org/page'] and len(asked) <= 1
        bar.box.clear(); QTest.mouseClick(bar.targets['web'], Qt.LeftButton); settle(200, 2); bar.box.setFocus()
        QTest.keyClicks(bar.box, 'rail limits rev b'); QTest.keyClick(bar.box, Qt.Key_Return); settle(200, 2); said2 = bar.message
        QTest.keyClicks(bar.box, 'localhost:8080'); QTest.keyClick(bar.box, Qt.Key_Return); settle(200, 2)
    print('with Web lit ->', opened[1:], '|', repr(said2)); ok &= opened[1:] == ['https://duckduckgo.com/?q=rail+limits+rev+b', 'http://localhost:8080'] and bar.box.text() == ''
finally: w.shell2.ask = real_ask
save('Line_01_An_Address_Goes_To_Web_%s.png' % tag)
with patch.object(QDesktopServices, 'openUrl', return_value=False):
    QTest.keyClicks(bar.box, 'example.org'); QTest.keyClick(bar.box, Qt.Key_Return); settle(200, 2); print('with no browser:', repr(bar.message), '| the line keeps what was typed:', repr(bar.box.text())); ok &= 'No browser' in bar.message and bar.box.text() == 'example.org'
bar.box.clear(); QTest.mouseClick(bar.targets['slate'], Qt.LeftButton); settle(200, 2)
# the arrow: amber and "Ask Stacy" with words; green and "Run this staC" with a line that reads as staC, and it runs it
QTest.keyClicks(bar.box, 'what is on the desk'); settle(500, 3); plain = (bar.send.toolTip(), bool(bar.send.property('reads')), bar.context.text() if bar.context.isVisible() else '')
bar.box.clear(); QTest.keyClicks(bar.box, 'files.list'); settle(500, 3); reads = (bar.send.toolTip(), bool(bar.send.property('reads')), bar.context.text() if bar.context.isVisible() else '')
print('with words:', plain, '| with staC:', reads); ok &= plain[:2] in (('Ask Stacy', False), ('Ask Kasandra', False)) and reads[:2] == ('Run this line', True) and 'a line' in reads[2] and 'Ctrl' not in reads[2]
popup = bar.box.popup; rows = [popup.list.item(i).text() for i in range(popup.list.count())] if popup.isVisible() else []; print('under the line:', rows[:4], '|', popup.hint.note if popup.isVisible() else ''); ok &= not any('Enter' in r or 'CTRL' in r for r in rows)
save('Line_02_Reads_As_staC_%s.png' % tag)
before = len(bar.console.history.get('stac', [])) if hasattr(bar.console, 'history') else 0
QTest.mouseClick(bar.send, Qt.LeftButton); settle(900, 4); after = len(bar.console.history.get('stac', [])) if hasattr(bar.console, 'history') else 0
print('pressed the arrow: staC lines run', before, '->', after, '| the line is', repr(bar.box.text()), '| the page above:', bar.console.mode); ok &= after == before + 1 and bar.box.text() == ''
tips = [bar.box.toolTip(), bar.box.accessibleDescription()] + [b.toolTip() for b in bar.targets.values()] + [bar.send.toolTip()]
named = [x for x in tips if any(k in x for k in ('Ctrl+', 'Enter', 'Alt+', 'Esc'))]; print('tips on the line that name a key:', named); ok &= not named
save('Line_03_After_The_Arrow_%s.png' % tag)
print('LINE PROBE', 'PASS' if ok else 'FAIL')
