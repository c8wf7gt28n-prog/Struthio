"""Follow the actual focused workspace without reopening or rebinding its writing."""
from pathlib import Path
from PySide6.QtCore import QObject,QSignalBlocker,Qt,QTimer,QEvent


def hidden(item):
    """A visible leaf can still sit beneath a hidden ancestor."""
    while item is not None:
        if item.isHidden():return True
        item=item.parent()
    return False


class NavigationController(QObject):
    def __init__(self,host):
        super().__init__(host);self.host=host;self.following=False
        host.tabs.currentChanged.connect(self.follow)
        self.resize_timer=QTimer(self);self.resize_timer.setSingleShot(True);self.resize_timer.timeout.connect(self.keep_visible)
        host.settings_navigator.tree.viewport().installEventFilter(self)
        host.cabinet_page.tree.viewport().installEventFilter(self)
        host.nav.currentItemChanged.connect(self.library_selected)  # UI-04: the Library is the Finder's sidebar while Home is active

    def library_selected(self,current,previous=None):
        """UI-04 selection hook: the Today row → the Finder's Today place; the Files row or a Library files row → the Files
        folder on disk. Only while Home is active, and only for the Library's own rows; nothing else moves."""
        finder=getattr(self.host,'finder',None)
        if finder is None or current is None or not getattr(self.host,'_home_active',False) or self.host._closing:return
        if current.data(0,Qt.UserRole+2)!='nav_live':return
        destination=current.data(0,Qt.UserRole+4) or ''
        if destination=='home':finder.show_place('today')
        elif destination=='office':  # the Ingress and Deliveries rows: the folder files come in through (D28)
            place=next((p for label,p in finder.places() if label=='Ingress'),None)
            if place:finder.show_place(place)
        elif destination.startswith('files:'):  # Egress, Working copies, Slate's area: that folder inside Files
            root=finder.files_root()
            if root is not None:finder.show_place(str(Path(root)/destination[6:]))
        elif destination=='files' or destination.startswith('library:'):finder.show_place('files')

    def eventFilter(self,watched,event):
        if event.type()==QEvent.Resize:self.resize_timer.start(0)
        return False

    def keep_visible(self):
        if self.host._closing:return
        nav=self.host.settings_navigator;page=self.host.cabinet_page
        if nav.stack.currentIndex():tree=nav.tree
        elif not page.using_legacy:tree=page.tree
        else:return
        item=tree.currentItem()
        if item is None or hidden(item):return
        parent=item.parent()
        while parent:
            if not parent.isExpanded():return
            parent=parent.parent()
        tree.scrollToItem(item)

    def trail(self,ident):
        """Follow placement parents, never a reference's canonical home."""
        page=self.host.cabinet_page
        nodes={row['id']:row for row in (page.model or {}).get('nodes',[])}
        result=[];seen=set()
        while ident is not None:
            if ident in seen or ident not in nodes:return []
            seen.add(ident);row=nodes[ident];result.append(row);ident=row['parent']
        return list(reversed(result))

    def reveal_record(self,ident,refresh=False):
        nav=self.host.settings_navigator;page=self.host.cabinet_page
        nav.show(False)
        if page.using_legacy:page.set_legacy(False)
        if refresh or page.model is None or ident not in page.items:page.refresh(force=True)
        if ident not in page.items:
            # Do not highlight a different record or infer a new filing home.
            with QSignalBlocker(page.tree):page.tree.setCurrentItem(None)
            page.status.setText('Open work is outside this cabinet view. Existing views and workspace search remain available.')
            return False
        page.select(ident,reveal=True)
        return True

    def changed(self,tab):
        from .cabinet_qt import CabinetRecordTab
        if isinstance(tab,CabinetRecordTab):
            path=self.trail(tab.current)
            if path:tab.breadcrumb.setText('FILED IN / '+' / '.join(row['label'] for row in (path[:-1] or path)))
        if self.host.tabs.currentWidget() is tab:self.follow()

    def follow(self,*_):
        if self.following or self.host._closing:return
        tab=self.host.tabs.currentWidget()
        if tab is None:return
        self.following=True
        try:
            from .settings_qt import SettingsTab
            from .cabinet_qt import CabinetRecordTab
            from .explore_qt import ExploreTab
            nav=self.host.settings_navigator
            if isinstance(tab,SettingsTab):
                nav.show(True)
                if tab.key and not tab.tools.isVisible():nav.select(tab.key,reveal=True)
            elif isinstance(tab,CabinetRecordTab):
                if tab.current:
                    self.reveal_record(tab.current)
                    path=self.trail(tab.current)
                    if path:tab.breadcrumb.setText('FILED IN / '+' / '.join(row['label'] for row in (path[:-1] or path)))
            else:
                # Other workspaces retain a cabinet anchor; this is not ownership.
                nav.show(False)
                if isinstance(tab,ExploreTab) and tab.model and tab.model.get('context'):
                    self.reveal_record(tab.model['context']['id'])
        finally:self.following=False

    def cabinet(self):
        """Return to the retained record room; do not reread over its draft."""
        from .cabinet_qt import CabinetRecordTab
        self.host._close_start()
        for index in range(self.host.tabs.count()):
            tab=self.host.tabs.widget(index)
            if isinstance(tab,CabinetRecordTab) and tab.current:
                self.host.tabs.setCurrentWidget(tab);self.follow();return tab
        page=self.host.cabinet_page
        if page.model is None:page.refresh(force=True)
        current=page.tree.currentItem()
        ident=current.data(0,Qt.UserRole)['id'] if current else page.saved.get('selected')
        if ident not in page.items:ident='cabinet:concern'
        return page.open(ident)


def install(host):
    host.navigation_controller=NavigationController(host)
    host.navigation_controller.follow()
