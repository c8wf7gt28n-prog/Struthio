from PySide6.QtWidgets import QToolButton
work = next(b for b in w.findChildren(QToolButton) if b.objectName() == 'MoreMenus').menu()
work.aboutToShow.emit()
print('TOP', [(repr(a.text()), a.menu() is not None) for a in work.actions()])
for a in work.actions():
    if a.menu() is not None and ('ules' in a.text() or 'rrange' in a.text()):
        a.menu().aboutToShow.emit(); print('SUB', repr(a.text()), [(x.text().replace('&', ''), x.menu() is not None) for x in a.menu().actions() if not x.isSeparator()][:40])
