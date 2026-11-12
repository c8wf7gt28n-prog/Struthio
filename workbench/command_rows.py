"""Keep a row's primary commands visible and fold the rest into labelled menus.

Folded buttons stay alive and hidden. Each menu entry clicks its button, so callbacks,
enablement and existing references keep working; the menu re-reads labels and
enablement every time it opens. Nothing here grants or runs anything new.
"""
from PySide6.QtWidgets import QBoxLayout, QGridLayout, QMenu, QPushButton, QSizePolicy


def plain(text):
    return text.replace('&&', '\0').replace('&', '').replace('\0', '&').strip()


class CommandMenu(QPushButton):
    """One button that opens the commands folded out of a row."""
    def __init__(self, title, buttons):
        super().__init__(title + '  ▾')
        self.setObjectName('CommandMenu')
        self.setStyleSheet('QPushButton#CommandMenu::menu-indicator { image: none; width: 0; }')
        self.buttons = list(buttons)
        names = ', '.join(plain(b.text()) for b in self.buttons)
        self.setAccessibleName(title + ' commands')
        self.setAccessibleDescription(names)
        self.setToolTip(title + ': ' + names)
        menu = QMenu(self)
        menu.setToolTipsVisible(True)
        for button in self.buttons:
            action = menu.addAction(button.icon(), button.text())
            action.triggered.connect(button.click)
            if button.parent() is None:button.setParent(self)  # folded before its row reached a widget
            button.hide()
        menu.aboutToShow.connect(self.sync)
        self.setMenu(menu)
        self.sync()

    def sync(self):
        for action, button in zip(self.menu().actions(), self.buttons):
            action.setText(button.text())
            action.setToolTip(button.toolTip())
            action.setEnabled(button.isEnabled())


def _remove(layout, widgets):
    for widget in widgets:
        layout.removeWidget(widget)


def fold(layout, keep=(), groups=(), more='More', buttons=None):
    """Show the buttons named in keep; put each group, then everything else, in menus.

    layout: the QBoxLayout or QGridLayout holding the row, or None when the caller
    places the returned widgets itself (responsive grids).
    groups: (title, labels) pairs. Returns the visible widgets in order.
    """
    if buttons is None:
        buttons = [layout.itemAt(i).widget() for i in range(layout.count())]
        buttons = [b for b in buttons if isinstance(b, QPushButton) and not isinstance(b, CommandMenu)]
    names = {plain(b.text()): b for b in buttons}
    wanted = list(keep) + [name for _, labels in groups for name in labels]
    missing = [name for name in wanted if name not in names]
    if missing:
        raise ValueError('Unknown command label: ' + ', '.join(missing))
    kept = [b for b in buttons if plain(b.text()) in keep]
    used = set(kept)
    menus = []
    for title, labels in groups:
        members = [b for b in buttons if plain(b.text()) in labels and b not in used]
        if members:
            used.update(members)
            menus.append(CommandMenu(title, members))
    rest = [b for b in buttons if b not in used]
    if rest:
        menus.append(CommandMenu(more, rest))
    for menu in menus:
        menu.setSizePolicy(kept[0].sizePolicy() if kept else menu.sizePolicy())
    visible = kept + menus
    if isinstance(layout, QGridLayout):
        positions = [layout.getItemPosition(layout.indexOf(b)) for b in buttons if layout.indexOf(b) >= 0]
        columns = max((col + span for _, col, _, span in positions), default=1)
        top = min((row for row, *_ in positions), default=0)
        _remove(layout, buttons)
        for index, widget in enumerate(visible):
            layout.addWidget(widget, top + index // columns, index % columns)
    elif isinstance(layout, QBoxLayout):
        last = max(layout.indexOf(b) for b in buttons)
        for offset, menu in enumerate(menus, 1):
            layout.insertWidget(last + offset, menu)
    return visible


def pad_toggle(buttons, text='On-screen pad'):
    """A checkable button that shows on-screen controller buttons only when wanted."""
    toggle = QPushButton(text)
    toggle.setObjectName('PadToggle')
    toggle.setCheckable(True)
    toggle.setAccessibleName('Show on-screen controller buttons')
    toggle.setToolTip('Show the on-screen controller; the keyboard works either way')
    toggle.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    def show(on):
        for button in buttons:
            button.setVisible(on)
    toggle.toggled.connect(show)
    show(False)
    return toggle
