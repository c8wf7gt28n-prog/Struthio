"""Program entries and menu commands are contextual objects too.

Ordinary clicks still use the original QAction. The secondary menu captures the
working object and refuses a deferred UI edit after that context has changed.
"""
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QMenu
from shiboken6 import isValid


def active_object(host):
    from . import context_menu as cm
    if getattr(host, '_home_active', False):return None
    tab = host.tabs.currentWidget()
    if tab is None:return None
    if getattr(tab, 'document_id', None) and hasattr(tab, 'page'):
        return cm.document_target(tab, tab.page)
    selected = getattr(tab, 'selected', None)
    if callable(selected):
        chosen = selected()
        if isinstance(chosen, list) and chosen and isinstance(chosen[0], dict) and 'path' in chosen[0]:
            e = chosen[0];kind = 'files' if len(chosen) > 1 else ('folder' if e['kind'] == 'folder' else cm.file_kind(e['name']))
            return cm.Target(kind, e['name'], ident=e['path'], revision=cm.file_revision(e), data=e,
                             items=chosen, surface='files', owner=tab)
    from pathlib import Path
    source = getattr(tab, 'source', None)
    path = getattr(source, 'path', None) or getattr(tab, 'root_path', None) or getattr(tab, 'path', None)
    if path is not None and isinstance(path, (str, Path)) and Path(path).is_file():
        path = Path(path).resolve();stat = path.stat()
        return cm.Target(cm.file_kind(path.name), path.name, ident=str(path),
                         revision=(stat.st_mtime_ns,stat.st_size), data={'path':str(path)},
                         surface='viewer', owner=tab)
    return None


def context_stamp(host):
    """A UI route may use current_editor; bind that route to what was selected."""
    from .work_location import location
    t = active_object(host)
    return (location(host)[0], t.ident if t else None, t.revision if t else None,
            repr(t.data.get('selection')) if t else None)


def find(host, widget, point):
    from . import context_menu as cm
    from .programs_qt import MenuRow, ProgramsList
    if isinstance(widget, MenuRow) and isinstance(widget.menu, ProgramsList):
        key = next((k for k, row in widget.menu.rows_by_key.items() if row is widget), None)
        if key is None:return None
        return cm.Target('program', widget.word, 'application or capability', ident=key,
                         data={'action':widget.action, 'work':active_object(host)},
                         owner=widget.menu, surface='programs', icon=key)
    if isinstance(widget, cm.ContextRow):
        entry = widget.entry
        return cm.Target('command', entry.label, 'contextual command', ident=entry.key,
                         data={'entry':entry, 'work':widget.menu.target, 'stamp':context_stamp(host)},
                         owner=widget.menu, surface='context-command', icon=entry.icon or 'line')
    if isinstance(widget, QMenu):
        action = widget.actionAt(point)
        if action is None and point.x() < 0 and point.y() < 0:action = widget.activeAction()
        return action_target(host, widget, action) if action is not None else None
    return None


def action_target(host, menu, action):
    from . import context_menu as cm
    if action.isSeparator():return None
    child = next((m for m in host.findChildren(QMenu) if isValid(m) and m.menuAction() is action), None)
    return cm.Target('command', action.text().replace('&','').split('\t')[0], 'menu command',
                     ident=action.objectName() or action.text(), data={'action':action, 'menu':child,
                     'work':active_object(host), 'stamp':context_stamp(host)},
                     owner=menu, surface='dropdown-command', icon='line')


def invoke(host, target):
    from . import context_menu as cm
    data = target.data
    if target.kind != 'program' and context_stamp(host) != data.get('stamp'):
        raise cm.Refused('The active work or selection changed. Choose this command again for the current work.')
    work = data.get('work')
    if target.kind != 'program' and work is not None:
        if work.surface == 'files':
            for item in work.items or [work.data]:cm.still_file(host,item)
        if work.surface == 'document':
            current = cm.dispatch(host,'documents.get',{'id':work.ident})
            if not current.get('ok') or current['result']['document']['revision'] != work.revision:
                raise cm.Refused('The saved page changed. Choose this command again for the current revision.')
    action = data.get('action')
    if action is not None:
        if not isValid(action) or not action.isEnabled():
            raise cm.Refused('That command is no longer available.')
        action.trigger();return {'invoked':target.ident, 'route':'original QAction'}
    entry = data.get('entry')
    if entry is not None:
        if not entry.enabled:raise cm.Refused(entry.reason or 'This command is unavailable.')
        if entry.run is not None:return entry.run()
    raise cm.Refused('Open its submenu to choose an operation.')


def child_commands(host, target):
    from . import context_menu as cm
    menu = target.data.get('menu')
    if menu is None or not isValid(menu):return []
    menu.aboutToShow.emit()
    rows = []
    for index, action in enumerate(menu.actions()):
        if action.isSeparator() or not action.isVisible():continue
        # Look up the real action at its own rectangle, so submenus stay real submenus.
        child = action_target(host, menu, action)
        if child is None:continue
        submenu = child.data.get('menu')
        rows.append(cm.Entry('command-child:%d' % index, child.label, 'command',
                             run=(lambda t=child:invoke(host,t)) if submenu is None else None,
                             enabled=action.isEnabled(), reason=action.toolTip(),
                             submenu=(lambda t=child:child_commands(host,t)) if submenu is not None else None,
                             tip=action.toolTip(), icon='line'))
    return rows


def describe(host, target):
    from .chain_workbench_qt import tray
    action = target.data.get('action');entry = target.data.get('entry')
    lines = [target.label, 'Kind: ' + target.noun]
    if action is not None and isValid(action):
        lines += [action.toolTip() or action.statusTip(), 'Shortcut: ' + (action.shortcut().toString() or 'none'),
                  'Available: ' + ('yes' if action.isEnabled() else 'no'),
                  'Execution: existing application action']
    if entry is not None:
        lines += [entry.tooltip(), 'Operation: ' + (entry.operation or 'existing interface route')]
    work = target.data.get('work')
    if work is not None:lines.append('Bound work: ' + work.label + (' · revision ' + str(work.revision) if work.revision is not None else ''))
    return tray(host).inspect_command('\n'.join(x for x in lines if x))


def entries(host, target):
    from . import context_menu as cm
    if target.surface == 'viewer':return viewer_entries(host,target)
    if target.kind not in ('program','command'):return []
    data = target.data;action = data.get('action');original = data.get('entry')
    submenu = data.get('menu')
    if action is not None:
        enabled = isValid(action) and action.isEnabled()
        reason = action.toolTip() if isValid(action) else 'The command has closed.'
    else:
        enabled = bool(original and original.enabled);reason = original.reason if original else ''
    out = [cm.Entry('command:inspect','Inspect this capability' if target.kind == 'program' else 'Inspect this command',
                    'open',lambda:describe(host,target),icon='inspect')]
    if submenu is not None:
        out.append(cm.Entry('command:choices','Choose an operation','command',submenu=lambda:child_commands(host,target),icon='line'))
    elif original is not None and original.submenu:
        out.append(cm.Entry('command:choices','Choose an operation','command',submenu=original.submenu,icon='line'))
    elif original is not None and original.qmenu:
        out.append(cm.Entry('command:choices','Continue this chain','command',qmenu=original.qmenu,icon='chain'))
    else:
        out.append(cm.Entry('command:invoke','Open capability' if target.kind == 'program' else 'Run this command',
                            'open',lambda:invoke(host,target),enabled=enabled,reason=reason,icon='run'))
    work = data.get('work')
    if work is not None and work.kind not in ('program','command'):
        out.append(cm.Entry('command:work','For ' + cm.short(work.label,40),'modify',
                            submenu=lambda:cm.entries_for(host,work),icon=work.icon,
                            tip='Commands for the captured working object; edits retain its revision binding.'))
    if target.kind == 'program':
        def explore():
            from .explore_qt import show
            return show(host)
        out.append(cm.Entry('command:atlas','Explore supported operations','capability',explore,icon='tools'))
    return out


def viewer_entries(host, target):
    from pathlib import Path
    from . import context_menu as cm
    path = Path(target.ident)
    out = [cm.Entry('viewer:folder','Show enclosing folder','open',lambda:host.browse(path.parent),icon='files'),
           cm.Entry('viewer:path','Copy full path','edit',lambda:cm.copy_text(host,str(path)),icon='copy'),
           cm.Entry('viewer:ask','Ask about this file','capability',lambda:cm.ask_graphite(host,'Work with '+str(path)),icon='inquiries')]
    from .files_service import root
    base = root(cm.kernel_of(host)).resolve()
    try:relative = path.relative_to(base).as_posix()
    except ValueError:return out
    if '|' not in relative:
        program = cm.staC_for_file(relative)
        from .chain_workbench_qt import stage
        out += [cm.Entry('viewer:chain','Build a chain from this file','command',lambda:stage(host,program),icon='chain'),
                cm.Entry('viewer:continue','Read and transform','command',qmenu=lambda:cm.chain_qmenu(host,program),icon='chain')]
    return out
