"""One honest, typeable address for the active work. No shell interpretation."""
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit


def location(host):
    """Return (address, description). Record addresses are not pretend disk files."""
    root = Path(host.root).resolve()
    if getattr(host, '_home_active', False):
        page = getattr(host, 'finder', None) or getattr(host, 'home_page', None)
        place = getattr(page, 'place', None)
        if place and place != 'today':
            return str(Path(place).resolve()), 'Folder'
        return str(root), 'Workspace · Today'
    tabs = getattr(host, 'tabs', None)
    tab = tabs.currentWidget() if tabs is not None else None
    if tab is None:
        return str(root), 'Workspace'
    ident = getattr(tab, 'document_id', None)
    if ident:
        rev = getattr(tab, 'revision', None)
        return 'graphite://documents/' + quote(str(ident), safe=''), 'Saved document · revision %s' % rev
    source = getattr(tab, 'source', None)
    path = getattr(source, 'path', None)
    if path is not None:
        return str(Path(path).resolve()), 'File'
    for key in ('path', 'source_path', 'root_path'):
        path = getattr(tab, key, None)
        if isinstance(path, (str, Path)) and str(path):
            p = Path(path)
            return str((root / p).resolve() if not p.is_absolute() else p.resolve()), 'File'
    finder = getattr(tab, 'finder', None) or getattr(getattr(tab, 'pane', None), 'finder', None)
    place = getattr(finder, 'place', None)
    if place and place != 'today':
        return str(Path(place).resolve()), 'Folder'
    folder = getattr(tab, 'folder', None)
    if isinstance(folder, (str, Path)):
        base = getattr(tab, 'root', root)
        p = Path(folder)
        return str((Path(base) / p).resolve()), 'Folder'
    # A room has a stable internal address only when its existing router can open it.
    title = tabs.tabText(tabs.currentIndex()).replace('◆ ', '').strip()
    key = tab.property('ledgerKey')
    if isinstance(key, str) and key:
        return 'graphite://view/' + quote(key, safe=''), title or 'Working view'
    ident = tab.property('graphiteLocationId')
    if not ident:
        from uuid import uuid4
        ident = uuid4().hex;tab.setProperty('graphiteLocationId', ident)
    return 'graphite://open/' + ident, title or 'Unsaved work'


def navigate(host, address):
    """Navigate through existing view factories; return the resulting view or raise."""
    text = str(address).strip()
    if not text or '\x00' in text or '\n' in text:
        raise ValueError('Enter a file or folder path.')
    if text.startswith('graphite://'):
        parsed = urlsplit(text)
        ident = unquote(parsed.path.lstrip('/'))
        if parsed.netloc == 'documents':
            from .context_menu import dispatch, message
            response = dispatch(host,'documents.get',{'id':ident})
            if not response.get('ok'):raise ValueError(message(response,'That document is unavailable.'))
            from .document_qt import show
            return show(host, ident)
        if parsed.netloc == 'open':
            for index in range(host.tabs.count()):
                if host.tabs.widget(index).property('graphiteLocationId') == ident:
                    host._close_start();host.tabs.setCurrentIndex(index)
                    return host.tabs.widget(index)
            raise ValueError('That work is no longer open.')
        if parsed.netloc == 'view':
            for index in range(host.tabs.count()):
                if host.tabs.widget(index).property('ledgerKey') == ident:
                    host._close_start();host.tabs.setCurrentIndex(index)
                    return host.tabs.widget(index)
            raise ValueError('That working view is no longer open. Choose it in Apps.')
        raise ValueError('That Graphite address is not supported.')
    if text.startswith('file:'):
        parsed = urlsplit(text)
        if parsed.netloc not in ('', 'localhost'):
            raise ValueError('Use a local file path or a mounted network folder.')
        text = unquote(parsed.path)
    path = Path(text).expanduser()
    if not path.is_absolute():
        current, _ = location(host)
        base = Path(current) if not current.startswith('graphite:') else Path(host.root)
        path = (base if base.is_dir() else base.parent) / path
    path = path.resolve()
    if not path.exists():
        raise ValueError('No file or folder at ' + str(path))
    if path.is_dir():
        host._close_start()
        return host.browse(path)
    if not path.is_file():
        raise ValueError('Choose an ordinary file or folder.')
    return host.open_in_viewer(path)
