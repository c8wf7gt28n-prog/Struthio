"""Word-based favorites over the original QAction objects and saved profile."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QMenu, QLabel
from sdk.cli.arc1cli.command_bar import GROUPS, GROUP_LABELS, allowed_groups


def action_words(action):
    return action.text().replace('&&','\0').replace('&','').replace('\0','&').split('\t',1)[0]


class FavoriteSlots(QWidget):
    def __init__(self,host,edited):
        super().__init__();self.host=host;self.slots=[]
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(8)
        for index in range(3):
            layout.addWidget(QLabel('Favorite '+str(index+1)))
            combo=QComboBox();combo.setObjectName('SettingValue');combo.currentIndexChanged.connect(edited)
            combo.setAccessibleName('Favorite '+str(index+1));layout.addWidget(combo);self.slots.append(combo)

    def configure(self,group,value):
        for index,combo in enumerate(self.slots):
            combo.clear();combo.addItem('No favorite',None)
            for key in allowed_groups()[group]:
                original=self.host.favorite_actions.get(key)
                if original is not None:combo.addItem(action_words(original),key)
            key=value[index] if index<len(value) else None
            combo.setCurrentIndex(max(0,combo.findData(key)))

    def value(self):
        return [combo.currentData() for combo in self.slots if combo.currentData() is not None]


def display(host,row,value):
    if row.get('editor')=='favorite_slots' and isinstance(value,list):
        return ', '.join(action_words(host.favorite_actions[key]) for key in value if key in host.favorite_actions) or 'No favorites'
    if row.get('editor')=='view_modes' and isinstance(value,dict):
        from .hardware_settings_qt import view_summary
        return view_summary(value)
    if isinstance(value,str):return row.get('choice_labels',{}).get(value,value)
    from .settings_qt import words
    return words(value)


def install_favorites_menu(host):
    parent=host.menu_groups['Commands']
    menu=getattr(host,'favorite_commands_menu',None)
    if menu is None:
        # Parent to Commands so menus2 never treats this submenu title as a command.
        menu=host.favorite_commands_menu=QMenu('Favorite commands',parent)
        menu.setObjectName('FavoriteCommands')
        menu.setStyleSheet('QMenu#FavoriteCommands::item {padding:4px 20px 4px 12px;}')
        menu.setAccessibleName('Favorite commands');menu.aboutToShow.connect(lambda:fill_favorites_menu(host))
    parent.addSeparator();parent.addMenu(menu)
    if not menu.isVisible():fill_favorites_menu(host)


def fill_favorites_menu(host):
    menu=host.favorite_commands_menu;found=False
    # Detach shared QActions explicitly. QMenu.clear() may delete a dock's
    # toggle action in PySide when rebuilding this second presentation.
    for action in list(menu.actions()):
        menu.removeAction(action)
        if action.parent() is menu:action.deleteLater()
    used=set()
    for group in GROUPS:
        keys=[key for key in host.favorites.get(group,[]) if key not in used and key in host.favorite_actions]
        if not keys:continue
        if found:menu.addSeparator()
        menu.addAction(GROUP_LABELS[group]).setEnabled(False)
        for key in keys:
            original=host.favorite_actions.get(key)
            if original is not None:menu.addAction(original);used.add(key);found=True
    if not found:menu.addAction('No favorite commands yet').setEnabled(False)
    menu.addSeparator()
    menu.addAction('Edit favorites in Settings…',lambda:host.ledger_bridge.show_settings(key='favorites.file'))
