"""An explicit detached workspace, using Ledger's existing tabs and controls."""
from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QGridLayout

class EmptyWorkspaceTab(QWidget):
    """Pass A: one sentence and two words. Everything this page used to list is in the Library, the menus and Ctrl K."""
    def __init__(self,host):
        super().__init__();self.host=host;self.setObjectName('LibraryTab');self.setProperty('ledgerRoom',True)
        from .shell2 import role,sentence
        box=QVBoxLayout(self);box.setContentsMargins(56,48,56,24);box.setSpacing(14)
        self.heading=role(QLabel('Needs a project'),'title');box.addWidget(self.heading)
        self.status=QLabel('No project attached');self.status.hide()  # kept for callers; the sentence says it
        self.reason=QLabel();self.reason.setWordWrap(True);box.addWidget(self.reason)
        self.words=QLabel();box.addWidget(self.words)
        from .shell2 import open_destination
        sentence('{attach}  ·  {close}',{'attach':('attach a project…',lambda:open_destination(host,'project')),
                                       'close':('close this',lambda:host.tabs.removeTab(host.tabs.indexOf(self)))},self.words)
        box.addStretch(1)
    def title(self):return 'Needs a project'
    def info(self):return 'Program only · no project attached'

def show(host,requested=''):
    host._close_start()
    for i in range(host.tabs.count()):
        tab=host.tabs.widget(i)
        if isinstance(tab,EmptyWorkspaceTab):break
    else:
        tab=EmptyWorkspaceTab(host);host.tabs.addTab(tab,tab.title())
    tab.reason.setText(((requested+' works on an attached, reviewed project.') if requested else 'This works on an attached, reviewed project.')+
                       ' Your own projects stay in their own folders until you attach one; everything else in Graphite works without one.')
    host.tabs.setCurrentWidget(tab);return tab


def show_home(host):
    """Overlay the detached landing page in the centre; never replace an edited Preview.

    UI01 (DESKTOP-01): Home keeps the frame. Both side columns, the Ledger Head and the typing strip stay where they are;
    only the output and cart panels (not part of the five-part desktop) are folded away, as in any workspace.
    UI-04 (AGENT-01): with the shell installed, Home is the Finder (`finder_qt.FinderPage`), whose first place is the
    existing TodayPage (kept as `page.today`, unchanged in content); `host._empty_home_page` and `host.finder` point at it."""
    from .qt_app import engine_layout_version
    page=getattr(host,'_empty_home_page',None)
    if hasattr(host,'shell2'):
        from .finder_qt import FinderPage
        if not isinstance(page,FinderPage):
            from .shell2 import TodayPage
            today=page if isinstance(page,TodayPage) else None
            if page is not None:host.central_stack.removeWidget(page)
            finder=FinderPage(host,today=today);host.central_stack.addWidget(finder)
            if page is not None and today is None:page.deleteLater()
            page=host._empty_home_page=finder
        host.finder=page
    elif page is None:
        page=HomeDashboard(host);host._empty_home_page=page
        host.central_stack.addWidget(page)
    if not host._home_active:
        host._home_dock_state=host.saveState(engine_layout_version());host._home_output_visible=host.output_dock.isVisible()
    host._home_active=True;host.output_dock.hide();host.cart_dock.hide();host.central_stack.setCurrentWidget(page)
    host.context_bar.hide();host.doc_info.hide();host.clip.hide();host.set_view_preference(last_surface='home');host.setWindowTitle('Home — Graphite')
    from .arc_desktop import refresh
    refresh(host);return page


class HomeDashboard(QWidget):
    """Home: what is waiting in the Office, how Slate is, what you opened last, and where to start."""

    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('HomeDashboard')
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QFrame
        outer = QVBoxLayout(self);outer.setContentsMargins(30, 24, 30, 20);outer.setSpacing(14)
        top = QHBoxLayout()
        self.heading = QLabel('Graphite');self.heading.setStyleSheet('color:#edaa69;font-weight:bold;font-size:22px')
        self.where = QLabel();self.where.setStyleSheet('color:#84d1d1')
        heading = QVBoxLayout();heading.addWidget(self.heading);heading.addWidget(self.where);top.addLayout(heading, 1)
        resume = QPushButton('Back to work');resume.setToolTip('Return to the files and rooms you had open');resume.clicked.connect(host.resume_workspace);top.addWidget(resume)
        outer.addLayout(top)
        grid = QGridLayout();grid.setSpacing(14)
        def card(title, row, column, actions):
            frame = QFrame();frame.setObjectName('HomeCard');frame.setStyleSheet('QFrame#HomeCard {background:#1a2029;border:1px solid #34404b;border-radius:8px;}')
            box = QVBoxLayout(frame);box.setContentsMargins(16, 12, 16, 12)
            name = QLabel(title);name.setStyleSheet('color:#edaa69;font-weight:bold;font-size:15px;border:0');box.addWidget(name)
            body = QLabel('…');body.setWordWrap(True);body.setStyleSheet('border:0;color:#e4e6e8');box.addWidget(body, 1)
            row_box = QHBoxLayout()
            for label, fn in actions:
                button = QPushButton(label);button.clicked.connect(fn);row_box.addWidget(button)
            row_box.addStretch(1);box.addLayout(row_box);grid.addWidget(frame, row, column);return body
        nav = lambda d:(lambda:host.ledger_bridge.navigation()[d]())
        self.office = card('Office', 0, 0, [('Open Office', nav('office')), ('Receive files…', self.receive_files)])
        self.slate = card('Graphite', 0, 1, [('Open Graphite', nav('slate')), ('Ask Stacy', host.open_clip)])
        self.files = card('Files', 1, 0, [('Open in viewer…', lambda:host.open_in_viewer()), ('Find a file…', host.quick_open)])
        self.matrix = card('What Graphite has learned', 1, 1, [('Instruction matrix', self.open_matrix)])
        outer.addLayout(grid, 1)
        more = QHBoxLayout();more.addWidget(QLabel('More:'))
        for label, destination in (('Organizer', 'organizer'), ('Memory && staC', 'memory'), ('Knowledge', 'stacy_knowledge'), ('References', 'references'),
                                   ('Awareness', 'stacy_awareness'), ('Commands', 'commands'), ('Settings', 'settings')):
            link = QPushButton(label);link.setFlat(True);link.setStyleSheet('color:#ffb05c;text-align:left');link.clicked.connect(nav(destination));more.addWidget(link)
        more.addStretch(1);outer.addLayout(more)
        from .version import title
        foot = QLabel(title() + ' · F11 fullscreen · Ctrl+Alt+= / − text size');foot.setStyleSheet('color:#7b8791');outer.addWidget(foot)
        self.timer = QTimer(self);self.timer.setInterval(4000);self.timer.timeout.connect(self.fill)

    def showEvent(self, event):
        super().showEvent(event);self.fill();self.timer.start()

    def hideEvent(self, event):
        super().hideEvent(event);self.timer.stop()

    def call(self, op, args=None):
        from .engine import engineering
        from .engineering_kernel import operator
        try:
            r = engineering(self.host.root).dispatch(op, args or {}, operator())
            return r['result'] if r.get('ok') else None
        except Exception:
            return None

    def fill(self):
        from . import locations
        try:marker = locations.marker(self.host.root)
        except ValueError:marker = None
        self.where.setText(((marker or {}).get('name') or 'Program') + ' workspace · ' + ('no project attached' if (marker or {}).get('kind', 'NO_PROJECT') == 'NO_PROJECT' else 'project attached'))
        status = self.call('receiving.status') or {};deliveries = (self.call('receiving.deliveries', {'limit': 30}) or {}).get('deliveries', [])
        waiting = len(status.get('inbox_waiting') or []);moving = sum(1 for d in deliveries if d['stage'] in ('SCANNING', 'REVIEWING', 'INDEXING'))
        yours = sum(1 for d in deliveries if d['stage'] == 'REVIEWED');done = [d for d in deliveries if d['stage'] == 'CATALOGED']
        lines = [('%d files have arrived' % waiting) if waiting else 'Nothing new has arrived']
        if moving:lines.append('%d deliveries being read' % moving)
        if yours:lines.append('%d deliveries waiting for you to accept' % yours)
        if done:lines.append('Last cataloged: ' + done[0]['label'] + ' · %d files' % len(done[0]['accepted']))
        if not deliveries:lines.append('Drop files on the Office to receive them.')
        self.office.setText('\n'.join(lines))
        brain = self.call('brain.status') or {};models = (self.call('brain.models') or {}).get('models', [])
        state = {'READY': 'Ready', 'MODEL_STOPPED': 'Stopped', 'NO_MODEL_SELECTED': 'No model yet'}.get(brain.get('state'), brain.get('state', 'Unknown'))
        model = brain.get('selection', {}).get('model_id')
        name = next((f['name'] for m in models if m['id'] == model for f in m.get('files', []) if f.get('role') == 'weights'), None)
        self.slate.setText('Brain: ' + state + (' · ' + name if name else '') + '\n' + ('%d models registered' % len(models)) +
                           ('' if brain.get('state') == 'READY' else '\nDrop a GGUF model on the Brain room to start it.') + '\nOn this computer · cloud calls 0')
        recent = [Path(p).name + '  (viewed)' for p in getattr(self.host, '_viewer_recent', [])[:3]] + list(self.host.session.state.get('recent', []))[:5]
        self.files.setText('\n'.join(recent) if recent else 'Nothing opened yet. Press Ctrl+Alt+V to view any file.')
        counts = (self.call('matrix.status') or {}).get('counts', {})
        total = sum(v for k, v in counts.items() if k != 'PROPOSED')
        self.matrix.setText(('%d staC runs · %d worked · %d failed or blocked' % (total, counts.get('SUCCESS', 0), counts.get('FAILED', 0) + counts.get('BLOCKED', 0)))
                            if total else 'Nothing yet. Run staC in the Office or ask Stacy to plan; every outcome teaches her.')

    def receive_files(self):
        office = self.host.ledger_bridge.navigation()['office']();office.pick_files()

    def open_matrix(self):
        slate = self.host.ledger_bridge.navigation()['slate']();slate.rooms.setCurrentIndex(1)
