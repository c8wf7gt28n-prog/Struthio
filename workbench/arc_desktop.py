"""ARC desktop presentation over the existing window, services and actions."""
from .text_prompts import writing_prompt
import html
import json
import time
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QObject, QEvent,QRectF
from PySide6.QtGui import QPixmap,QPainter
from PySide6.QtWidgets import (QDockWidget, QLineEdit, QWidget, QLabel, QVBoxLayout, QHBoxLayout,QScrollArea,QFrame,
    QToolButton, QPushButton, QTextBrowser, QSizePolicy)
from sdk.cli.arc1cli.workspace_activity import activity_for
from .ux_assets import icon
from . import locations,engine


def label(text, role=None):
    item = QLabel(text)
    item.setWordWrap(True)
    if role:
        item.setProperty('arcRole', role)
    return item


class NavigatorLogo(QWidget):
    """Display the owner's original artwork without its empty black margins."""
    def __init__(self,root):
        super().__init__();self.setObjectName('ArcGenesisLogo')
        # The Genesis artwork is part of the preserved ARC collection (4.0); without it the logo is simply empty.
        self.art=QPixmap(str(locations.program(root)/'branding/genesis/ARC_Aqua_Genesis_Logo.png'))
        try:data=json.loads((locations.program(root)/'branding/genesis/SOURCE.json').read_text())
        except (OSError,ValueError):data={'display_bounds':[0,0,1,1]}
        self.bounds=QRectF(*data['display_bounds'])
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.setFixedHeight(58)
        self.setAccessibleName('ARC · Adaptive RISC Concern · owner Genesis logo')
        self.setToolTip('ARC · Adaptive RISC Concern')

    def paintEvent(self,event):
        painter=QPainter(self);painter.fillRect(self.rect(),Qt.black)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        available=QRectF(self.rect()).adjusted(3,4,-3,-4)
        ratio=min(available.width()/self.bounds.width(),available.height()/self.bounds.height())
        width=self.bounds.width()*ratio;height=self.bounds.height()*ratio
        target=QRectF((self.width()-width)/2,(self.height()-height)/2,width,height)
        painter.drawPixmap(target,self.art,self.bounds)


class ArcInspector(QWidget):
    """Useful selection context without repeating unavailable instruments."""
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName('ArcInspector')
        box = QVBoxLayout(self)
        box.setContentsMargins(16, 16, 16, 10)
        self.heading = label('Your workshop', 'section')
        box.addWidget(self.heading)
        self.body = QTextBrowser()
        self.body.setObjectName('ArcContext')
        self.body.setOpenLinks(False)
        self.body.anchorClicked.connect(self.follow)
        box.addWidget(self.body, 1)
        self.catalog_summary = label('', 'metadata')
        self.catalog_summary.setTextFormat(Qt.PlainText)
        self.catalog_summary.setProperty('arcReadingRole', 'metadata')
        self.catalog_summary.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.catalog_summary.setMinimumWidth(0)
        self.catalog_scroll = QScrollArea(); self.catalog_scroll.setWidgetResizable(True)
        self.catalog_scroll.setFrameShape(QFrame.NoFrame); self.catalog_scroll.setWidget(self.catalog_summary)
        self.catalog_scroll.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.catalog_scroll.hide(); box.addWidget(self.catalog_scroll, 1)
        from .object_context_qt import Controller,View
        if not hasattr(host,'object_glass'):host.object_glass=Controller(host)
        self.glass=View(host,compact=True);self.glass_scroll=QScrollArea();self.glass_scroll.setWidgetResizable(True);self.glass_scroll.setWidget(self.glass);self.glass_scroll.hide();box.addWidget(self.glass_scroll,1)
        host.object_glass.changed.connect(lambda _:self.refresh())
        # Room for Stacy when she rests in the default corner, so she never covers context.
        self.companion_space = QWidget()
        self.companion_space.setFixedHeight(0)
        box.addWidget(self.companion_space)
        self.followup = QPushButton(icon(host.root, 'evidence'), 'Jobs && evidence')
        self.followup.clicked.connect(host.show_engineering)
        box.addWidget(self.followup)
        self.refresh()

    def follow(self, url):
        action = url.toString()
        if action in ('CAD', 'Source', 'Knowledge', 'Evidence'):
            self.host.open_selection_view(action)
        elif action == 'refresh':
            self.host.refresh_selection()
        elif action == 'starter':
            self.host.show_native_project()
        elif action == 'references':
            self.host.show_database_rom()
        elif action == 'reading':
            self.host.show_reading()
        elif action == 'issues':
            self.host.home_page.open_followup() if self.host.home_page else None

    def refresh(self):
        host = self.host
        tab = host.tabs.currentWidget()
        cabinet_id=tab.property('cabinet_node') if tab is not None and not host._home_active else None
        if cabinet_id:
            from .engineering_kernel import operator
            result=host.ledger_bridge.kernel.dispatch('ledger.cabinet.get',{'id':cabinet_id},operator())
            self.catalog_scroll.hide();self.glass_scroll.hide();self.followup.hide();self.body.show();self.heading.setText('Cabinet selection')
            if result['ok']:
                node=result['result']['node']
                self.body.setPlainText(node['label']+'\n\n'+node['role'].replace('_',' ').title()+'\nProvider: '+node['provider']+
                    ('\nRevision: '+str(node['revision']) if node.get('revision') is not None else '')+
                    '\nIdentity: '+node['canonical_id']+'\n\n'+node.get('description','Logical filing view.')+
                    '\n\nThis reads the existing record. Source and master freshness have not been rechecked. Use its explicit read actions when needed.')
            else:self.body.setPlainText('Selected record unavailable. Refresh the cabinet; its earlier file context is retained separately.')
            return
        catalog_active = hasattr(tab, 'controller') and hasattr(tab, 'ident') and type(tab).__name__ == 'ConcernDossier'
        service_active = type(tab).__name__ == 'HostPanel'
        pdf_active = type(tab).__name__ == 'PdfDocumentTab'
        glass_active=not catalog_active and not service_active and not pdf_active and getattr(host,'object_glass',None) and host.object_glass.data.get('state')!='EMPTY'
        self.catalog_scroll.setVisible(catalog_active)
        self.glass_scroll.setVisible(bool(glass_active));self.body.setVisible(not glass_active and not catalog_active)
        from .rooms import room_for as _room
        self.followup.setVisible(not glass_active and not catalog_active and _room(tab, host._home_active) == 'engineering')
        if glass_active:
            self.heading.setText('Object Glass');return
        activity = activity_for(type(tab).__name__, host._home_active)
        now=time.monotonic()
        if activity=='simulator' and getattr(self,'_activity',None)==activity and now-getattr(self,'_updated',0)<.3:
            return
        self._activity=activity;self._updated=now
        parts = []
        def section(title, text):
            parts.append('<h3>'+html.escape(title)+'</h3><p>'+text+'</p>')
        def esc(value):
            return html.escape(str(value))
        if catalog_active:
            self.heading.setText('Working area')
            data = tab.data
            note_state = 'Unsaved draft' if tab.is_dirty() else 'Saved note' if data['note']['version'] else 'No saved note yet'
            self.catalog_summary.setText(data['title'] + '\n\n' + data['kind'].capitalize() + ' · ' + data['state'] +
                '\n\nWorking notes\n' + note_state + '\n\nRelationships\n' + str(len(data['relations'])) +
                ' catalog links. One item across its entrances.\n\nSources\n' + str(len(data['sources'])) +
                ' saved references. Check saved-file state in Sources.')
            return
        elif callable(getattr(tab, 'inspector', None)):
            # A room or tool describes itself: what you are looking at, in a few short sections.
            heading, sections = tab.inspector()
            self.heading.setText(heading)
            # Less scrolling: a short value sits beside its label on one line; a long one goes under it, full width.
            label='<td style="color:#6c675e;font-size:12px;font-weight:500;letter-spacing:1px;padding:5px 12px 5px 0;vertical-align:top;white-space:nowrap">%s</td>'
            rows=[]
            from .shell2 import Note,quiet_html,scale_of
            ui=scale_of(host)
            for title, note in sections:
                text=str(note)
                # A section the room marks as a note you may skip (shell2.Note) is the Paper script, its keys and numbers printed
                # (the quiet-script rule; HATCH DESK D1b). Everything else stays print.
                words=quiet_html(text,round(15*1.3*ui),max(9,round(13*ui))) if isinstance(note,Note) else esc(text).replace('\n','<br>')
                if len(text)<=30 and '\n' not in text:
                    rows.append('<tr>'+label%esc(title).upper()+'<td style="padding:5px 0;vertical-align:top">'+words+'</td></tr>')
                else:
                    if title:rows.append('<tr>'+label%esc(title).upper()+'<td></td></tr>')
                    rows.append('<tr><td colspan="2" style="padding:0 0 6px 0;line-height:135%">'+words+'</td></tr>')
            parts.append('<table cellspacing="0" width="100%">'+''.join(rows)+'</table>')
        elif type(tab).__name__=='MemoryTab':
            self.heading.setText('Graphite · learning & continuity')
            section('Personality','Private seed '+('enabled' if getattr(tab,'profile_enabled',False) else 'disabled or not imported'))
            section('Learning','Explicit owner feedback only.<br>Corrections supersede older evidence in their scope.<br>Preferences never grant tool permission.')
            cp=getattr(tab,'last_checkpoint',None)
            if cp:section('Checkpoint',esc(cp['id'][:16])+'<br>Readback verified.<br>Source availability is rechecked on resume.')
            section('Working context','Fresh context follows a verified save.<br>Old private history is retained.')
            section('staC','Current caller permissions.<br>Read observations use the existing journal.')
            section('Qualification','A memory or source citation is not a board test.')
        elif type(tab).__name__=='ReferenceTab':
            self.heading.setText('Graphite · exact references')
            section('Reference library',esc(getattr(tab,'current_sources',0))+' current originals<br>Generation '+esc(getattr(tab,'generation',0)))
            citation=getattr(tab,'citation',None)
            if citation:
                section('Original',esc(citation['name'])+'<br>'+esc(citation['source_sha256'][:24])+'…')
                section('Exact location',esc(citation['label']))
                section('Source state',esc(citation['state']))
            section('Evidence meaning','Source location checked.<br>Interpretation requires review.<br>Hardware qualification remains open.')
            missing=getattr(tab,'unavailable_sources',0)
            section('Missing originals',esc(missing)+' unavailable sources.<br>Cached excerpts are withheld.' if missing else 'No unavailable sources in the current index.')
            section('Local packet','Selected sources only. No automatic cloud disclosure.')
        elif type(tab).__name__=='IntakeTab':
            self.heading.setText('Graphite · reference intake')
            section('V1 catalog',esc(getattr(tab,'catalog_count',0))+' available references<br>Generation '+esc(getattr(tab,'generation',0)))
            section('Current job','Running' if getattr(tab,'job',None) else 'No intake job running')
            selected=getattr(tab,'detail_data',None)
            if selected:
                section('Selected original',esc(selected['name'])+'<br>'+esc(selected['sha256'][:24])+'…')
                section('Admission',esc(selected['admission']))
                assessment=selected.get('assessment',{});qualification=assessment.get('qualification',{})
                if assessment.get('reasons'):section('Review findings','<br>'.join(esc(v).replace('_',' ') for v in assessment['reasons'][:5]))
                section('Engineering qualification','Native checks: '+esc(qualification.get('native_result','NOT_RUN'))+'<br>Hardware: '+esc(qualification.get('physical_hardware','NOT_QUALIFIED')))
            section('Authority','Owner decisions and stored policy control admission.<br>File contents cannot grant permissions.')
            section('Originals','Private immutable copies outside the program.<br>Source promotion is not granted.')
        elif type(tab).__name__=='BrainTab':
            from . import local_brain
            state=local_brain.status(host.ledger_bridge.kernel)
            self.heading.setText('Graphite · local brain')
            section('State',esc(state['state']).replace('_',' '))
            section('Execution','Local CPU worker · cloud calls 0')
            worker=local_brain.get(host.ledger_bridge.kernel,'worker',{})
            if local_brain.worker_live(worker):
                section('Active identity',esc(worker['model_id'][:20]))
                section('Context',esc(worker['context'])+' tokens')
                measured=local_brain.usage(worker)
                if measured['rss_bytes'] is not None:section('Resident memory',esc(round(measured['rss_bytes']/1024/1024,1))+' MiB · measured on this host')
                section('Runtime',esc(worker['runtime']['build'])+' · '+esc(worker['runtime']['platform']))
            else:section('Start a brain','Use a registered model to begin offline conversation.')
            section('Qualification','Model measurements do not verify<br>engineering answers.<br>Owner host and GPU qualification<br>remain separate.')
        elif activity == 'home':
            self.heading.setText('Your workshop')
            section('ARC-1 / R10', 'The Silicon Federation<br>One project. Many ways to explore.')
            section('Pick up a thread', '<a href="issues">Review the command-parser finding</a><br>Isolated candidate · review pending')
            recent = host.session.state.get('recent', [])[:4]
            if recent:
                section('Recently opened', '<br>'.join(esc(Path(p if isinstance(p,str) else p.get('path','')).name) for p in recent))
            section('Make something', '<a href="starter">Open the native game starter</a>')
            section('Your reading comfort', '<a href="reading">Font size, spacing & layout</a>')
        elif activity == 'book':
            self.heading.setText('Chapter context')
            title = getattr(tab, 'contents', None)
            if title is not None:
                section('Reading now', esc(title.currentText()))
            section('Follow your curiosity', 'Read, follow a source, and return to your place.')
            section('Reference library', '<a href="references">Search the Database ROM</a><br>Attach a verified reference volume for originals.')
            section('Try it in the workshop', '<a href="starter">Open the native game starter</a>')
            section('Reading', '<a href="reading">Adjust text and line spacing</a>')
        elif activity == 'simulator':
            self.heading.setText('Console session')
            state = getattr(tab, 'state', None)
            if isinstance(state, dict):
                frame = state.get('frame', {})
                metrics = state.get('metrics', {})
                section('HOST MODEL', esc(frame.get('screen',''))+'<br>Game: '+esc(state.get('game',{}).get('name','—')))
                section('Recorded activity', 'Logical ticks: '+esc(frame.get('tick',0))+'<br>USB block reads: '+esc(metrics.get('usb_block_reads',0))+'<br>RTL transactions: '+esc(metrics.get('rtl_transactions',0)))
            else:
                section('Begin a session', 'Boot the virtual console to inspect its real host-model events.')
                section('Host prerequisites', 'A C compiler and Icarus Verilog are needed to build the complete model.')
            section('Model scope', 'C protocol and firmware models with an RTL slice. Physical timing remains unqualified.')
            section('Create a game', '<a href="starter">Native C starter</a>')
        elif type(tab).__name__=='HdlTab':
            self.heading.setText('HDL / digital traces')
            report=getattr(tab,'result',None) or {};trace=getattr(tab,'trace',None)
            section('Native result',esc(report.get('status','NOT_RUN'))+'<br>'+esc(report.get('class','UNASSESSED')))
            if trace:
                section('Recorded VCD',esc(len(trace['signals']))+' signals<br>'+esc(trace['events'])+' recorded changes<br>'+esc(trace['tick_fs'])+' fs per tick')
                section('Exact cursor',esc(getattr(tab.plot,'cursor',0))+' ticks<br>X / Z retained')
            if report.get('simulation',{}).get('sample_count'):section('Shared pump check',esc(report['simulation']['sample_count'])+' expected words checked')
            if report.get('capture'):section('Native Surfer','Actual saved-state / image capture.<br>Graphite cursor controls are separate.')
            section('Source binding',esc(report.get('source_currentness','UNASSESSED')))
            section('Model limits','Digital RTL / protocol models, not board timing.<br>Physical programming HOLD.')
        elif type(tab).__name__=='ImplementationTab':
            self.heading.setText('FPGA implementation')
            report=getattr(tab,'result',None) or {};profile=report.get('profile',{})
            section('Current source profile',esc(profile.get('title','Choose a current R10 target.')))
            if profile.get('proxy'):section('PACKAGE PROXY','CABGA256 only. Physical TQFP144 remains unqualified.')
            section('Native result',esc(report.get('status','NOT_RUN'))+'<br>STATIC_CHECK')
            route=report.get('route',report.get('route_summary',{}))
            if route:
                section('Reported internal clocks',esc(sum(1 for c in route['clocks'].values() if c['met']))+' / '+esc(len(route['clocks']))+' met<br>Seed 1 · speed 6')
                section('Constrained IO',esc(route['io_count'])+' source LPF pin bindings')
            if report.get('packing'):section('HELD bitstream',esc(report['packing']['bytes'])+' bytes<br>Decoded roundtrip verified')
            section('Source binding',esc(report.get('source_currentness','UNASSESSED')))
            section('Open qualification','External IO timing, CDC and board electrical equivalence.<br>Physical release / programming HOLD.')
        elif type(tab).__name__=='YosysTab':
            self.heading.setText('FPGA synthesis')
            report=getattr(tab,'result',None) or {}
            profile=report.get('profile',{})
            section('Current R10 profile',esc(profile.get('title','Choose support or graphics.')))
            synthesis=report.get('synthesis',{})
            if synthesis:
                section('Native synthesis',esc(synthesis['cell_count'])+' mapped cells<br>STATIC_CHECK')
                counts=synthesis['cells_by_type']
                section('Mapped resources',esc(counts.get('LUT4',0))+' LUT4<br>'+esc(counts.get('TRELLIS_FF',0))+' flip-flops<br>'+esc(counts.get('DP16KD',0))+' block-RAM primitives')
                section('Source binding',esc(report.get('source_currentness','UNASSESSED'))+'<br>Top port interface preserved')
            section('Next stages','Placement, routing, pin assignment and timing closure remain unchecked.<br>Programming HOLD.')
        elif type(tab).__name__=='SpiceTab':
            self.heading.setText('Circuit model')
            report=getattr(tab,'result',None) or {}
            model=report.get('model',{})
            section('Modeled circuit',esc(model.get('title','Choose a reduced passive model.')))
            if report.get('waveform'):
                section('Native computation',esc(report['waveform']['points'])+' samples<br>ngspice '+esc(report.get('tool',{}).get('version','unknown'))+' · HOST_SIM')
                section('Source binding',esc(report.get('source_currentness','UNASSESSED'))+'<br>'+esc(len(model.get('components',[])))+' modeled source components')
                if report.get('operation')=='clock':
                    measurement=report['measurements'][0]
                    section('Calculated RC response','Time constant '+esc(f"{measurement['tau_seconds']*1e9:.3g}")+' ns<br>50% delay '+esc(f"{measurement['delay_at_50_percent_seconds']*1e9:.3g}")+' ns')
            section('Model limits','Ideal passive components and test stimuli.<br>IC and board behaviour are unqualified.')
        elif type(tab).__name__=='GenesisTab':
            self.heading.setText('ARC Concern')
            section('The beginning', 'ARC-GENESIS-0001<br>R. A. Peddycoart<br>25 October 2026')
            report = getattr(tab, 'report', None)
            if report is None:
                section('Evidence', 'Verification pending or unavailable. Read the workspace status.')
            else:
                section('Original record', 'Fingerprints match' if report['integrity']['ok'] else 'Fingerprint mismatch')
                section('Independent time', 'Receipt verified' if report['timestamp_verified'] else 'Receipt not verified')
            section('Founder execution', 'Signature and identity are separate from timestamp verification.')
            section('Written authority', 'Record scope, limits, expiry and revocation. System permissions keep their existing approval controls.')
        elif pdf_active:
            self.heading.setText('Exact original')
            section('Page identity',esc(tab.location.text()))
            section('Reading', 'Native text and OCR are derivatives. Check technical symbols, table conditions and figure context against the image.')
            section('Your notes', 'Annotations stay separate from originals and accepted facts. Save explicitly; recovery drafts remain separate.')
        elif service_active:
            self.heading.setText('Shared work')
            section('Graphite', 'One shared service coordinates authorized jobs and model ownership.')
            section('Window closed', 'The background service keeps running. Saved work and job results retain their identities.')
            section('Owner controls', 'Master Stop holds new work and switches off phone access. Resume is explicit.')
        elif type(tab).__name__=='CandidateReviewTab':
            self.heading.setText('Review context')
            section('Command parser', 'software/arcos/src/host.c')
            section('Scope', 'One isolated proposed file.<br>Current source is unchanged.')
            section('Source binding', 'Matches the proposal' if tab.binding_current else 'Changed · proposal requires rechecking')
            section('Review state', 'New tests and independent acceptance are required before applying the proposal.')
            section('Next step', 'Use engineering controls to inspect current jobs and review the proposal.')
        else:
            self.heading.setText('Selected object' if activity == 'brain' else 'Source context')
            path=engine.document_path(getattr(tab, 'path', None))
            if path is not None:
                try: name = path.relative_to(host.root).as_posix()
                except ValueError: name = path.name
                section('Current file', esc(name))
                if hasattr(tab, 'isReadOnly'):
                    section('Editor', 'Read only' if tab.isReadOnly() else 'Local editable source · save explicitly')
            data = host.selection_data or {}
            selected = data.get('selection')
            if selected:
                section(esc(selected['reference']), esc(data.get('state','Unknown')).replace('_',' ')+'<br>Native identity '+esc(selected['native_uuid'][:12]))
                if data.get('state') == 'CURRENT_INPUTS':
                    section('Follow this object', ' · '.join('<a href="'+x+'">'+x+'</a>' for x in ('CAD','Source','Knowledge','Evidence')))
                else:
                    section('Refresh required', '<a href="refresh">Recheck the current sources</a>')
                binding = data.get('export_binding',{}).get('state','Unverified export')
                section('Native export', esc(binding).replace('_',' '))
            elif activity == 'brain':
                section('Explore the machine', 'Choose a native component to follow its pins, sources and evidence.')
        from .rooms import room_for
        from .project_context import detached
        if room_for(tab, host._home_active) == 'engineering' and not detached(host.root) and not catalog_active and not service_active and not pdf_active and type(tab).__name__ != 'GenesisTab':
            section('Physical console', 'Disconnected · fabrication and programming remain on hold.')
        # Paper v1.1: graphite on the sheet; headings are short and semibold; links are graphite and underlined.
        self.body.document().setDefaultStyleSheet("body {color:#504d46;font-family:'IBM Plex Sans';} h3 {color:#504d46;font-size:17px;font-weight:600;margin-top:22px;margin-bottom:6px;} p {line-height:1.5;margin-bottom:14px;} a {color:#504d46;text-decoration:underline;text-decoration-color:#cba5a4;}")
        rendered=''.join(parts)
        if rendered!=getattr(self,'_rendered',None):
            position=self.body.verticalScrollBar().value()
            self.body.setHtml(rendered)
            self.body.verticalScrollBar().setValue(position)
            self._rendered=rendered


class ActivityRail(QWidget):
    """The rooms: Home · Office · Files · Slate · Engineering."""
    def __init__(self, host):
        super().__init__()
        from PySide6.QtWidgets import QMenu
        from .rooms import ROOMS, ENGINEERING, RoomButtons
        self.host = host
        self.setObjectName('ActivityRail')
        box = QHBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(3)
        self.buttons = RoomButtons()
        for key, title, asset, method, tip in ROOMS:
            button = QToolButton()
            button.setObjectName('ActivityButton')
            button.setText(title)
            button.setIcon(icon(host.root, asset))
            button.setIconSize(QSize(22,22))
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            button.setCheckable(True)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            button.setMinimumWidth(button.fontMetrics().horizontalAdvance(title) + 52)
            button.setAccessibleName('Open the ' + title + ' room')
            button.setToolTip(tip)
            if method:
                button.clicked.connect(lambda checked=False, name=method: getattr(host,name)())
            else:
                menu = QMenu(button)
                for label_text, destination in ENGINEERING:
                    if label_text is None:menu.addSeparator();continue
                    action = menu.addAction(label_text)
                    action.triggered.connect(lambda checked=False, d=destination: self.open_engineering(d))
                button.setMenu(menu);button.setPopupMode(QToolButton.InstantPopup);button.setText(title + ' ▾')
                button.clicked.connect(lambda checked=False:self.update_current())
            box.addWidget(button)
            self.buttons[key] = button

    def open_engineering(self, destination):
        host = self.host
        from .project_context import detached
        from .rooms import ENGINEERING
        if detached(host.root) and destination in ('source', 'brain_link', 'arcos', 'orange_book'):
            # These ARC-1 views read the project itself; without one, explain instead of failing.
            return host.project_required(dict((d, l) for l, d in ENGINEERING if d)[destination])
        if destination == 'source':return host.open_source_workspace()
        navigation = host.ledger_bridge.navigation()
        if destination in navigation:return navigation[destination]()
        method = {'brain_link': 'show_brain_link', 'arcos': 'show_arcos', 'orange_book': 'show_orange_book'}.get(destination)
        return getattr(host, method)() if method else None

    def update_current(self):
        from .rooms import room_for
        key = room_for(self.host.tabs.currentWidget(), self.host._home_active)
        for name, button in self.buttons.items():
            button.setChecked(name == key)


def install(host):
    """Install one presentation layer; retain all original service controls."""
    if hasattr(host, 'arc_inspector'):
        return
    host.setObjectName('ArcDesktop')
    # Move the existing favourite actions out of the document into app chrome.
    host.center_layout.removeWidget(host.toolbar)
    # The navigator runs the full window height. The ribbon is a fixed, title-less top dock
    # that starts where the workspace begins and spans the workspace and Inspector.
    ribbon = QDockWidget('Command ribbon', host)
    ribbon.setObjectName('CommandRibbon')
    ribbon.setTitleBarWidget(QWidget())
    ribbon.setFeatures(QDockWidget.NoDockWidgetFeatures)
    ribbon.setAllowedAreas(Qt.TopDockWidgetArea)
    ribbon.setWidget(host.toolbar)
    host.addDockWidget(Qt.TopDockWidgetArea, ribbon)
    host.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
    host.setCorner(Qt.TopRightCorner, Qt.TopDockWidgetArea)
    host.ribbon_dock = ribbon
    # The owner's original Genesis artwork heads the navigator.
    mast = QWidget()
    mast.setObjectName('ArcMast')
    column = QVBoxLayout(mast)
    column.setContentsMargins(12,8,12,8)
    column.setSpacing(8)
    host.navigator_logo=NavigatorLogo(host.root)
    column.addWidget(host.navigator_logo)
    host.concern.attach_controls(column)
    mast.setAccessibleName('Graphite project explorer')
    # Search lives with the tree: typing filters it; Enter searches everything.
    search_row = QHBoxLayout();search_row.setSpacing(6)
    host.tree_search = QLineEdit()
    host.tree_search.setObjectName('TreeSearch')
    writing_prompt(host.tree_search, 'Search ARC…')
    host.tree_search.setClearButtonEnabled(True)
    host.tree_search.setAccessibleName('Search the project tree; press Enter to search everything')
    host.tree_search.setToolTip('Type to filter the tree · Enter searches components, nets, files, commands and jobs (Ctrl+Shift+P)')
    host.tree_search.textChanged.connect(lambda text: filter_tree(host, text))
    host.tree_search.returnPressed.connect(lambda: host.command_palette(host.tree_search.text()))
    search_row.addWidget(host.tree_search, 1)
    host.toolbar.layout().removeWidget(host.global_search)
    host.global_search.setToolButtonStyle(Qt.ToolButtonIconOnly)
    host.global_search.setMinimumHeight(30)
    host.global_search.removeAction(host.a_palette)  # the icon searches with the typed text
    host.global_search.setIcon(host.nav_icon('search'))
    host.global_search.setToolTip('Search everything · Ctrl+Shift+P\nFind a file · Ctrl+P')
    host.global_search.setAccessibleName('Search everything')
    host.global_search.clicked.connect(lambda: host.command_palette(host.tree_search.text()))
    search_row.addWidget(host.global_search)
    # Keep the emergency control anchored at the right edge. Narrow windows can
    # scroll the existing command groups while Stop remains immediately reachable.
    ribbon_layout=host.toolbar.layout()
    ribbon_layout.removeWidget(host.master_stop_button)
    commands=QWidget();commands.setObjectName('RibbonCommands')
    command_layout=QHBoxLayout(commands);command_layout.setContentsMargins(8,4,8,4);command_layout.setSpacing(7)
    while ribbon_layout.count():
        item=ribbon_layout.takeAt(0)
        if item.widget():command_layout.addWidget(item.widget())
    commands.adjustSize()
    scroll=QScrollArea();scroll.setObjectName('RibbonScroll');scroll.setFrameShape(QFrame.NoFrame)
    scroll.setAccessibleName('Command ribbon; scroll horizontally for more commands')
    scroll.setWidgetResizable(False);scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded);scroll.setWidget(commands)
    scroll.setStyleSheet('QScrollArea#RibbonScroll {background:transparent;border:0;} QScrollBar:horizontal {height:7px;}')
    ribbon_layout.setContentsMargins(0,0,6,0);ribbon_layout.addWidget(scroll,1)
    ribbon_layout.addWidget(host.master_stop_button,0,Qt.AlignTop)
    host.ribbon_commands=commands;host.ribbon_scroll=scroll
    column.addLayout(search_row)
    host.nav_dock.setTitleBarWidget(mast)
    host.activity_rail = ActivityRail(host)
    host.center_layout.insertWidget(0,host.activity_rail)
    host.concern.install_context()
    host.arc_inspector = ArcInspector(host)
    host.console_pages.insertTab(0,host.arc_inspector,'Inspector')
    host.console_pages.setCurrentIndex(0)
    host.console_pages.tabBar().hide()
    host.console_pages.setFocusPolicy(Qt.NoFocus)  # ACC-01: a page stack with no visible tabs is not a Tab stop (its hidden tab bar trapped forward Tab)
    host.sim_dock.setWindowTitle('Inspector')
    # Hidden instrument pages must not force a wide minimum on the Inspector.
    host.console_pages.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
    # A minimum of 0 means "use the size hint", which is the widest hidden page (over 2000 px).
    # An explicit small minimum lets the Inspector stay a side panel.
    host.console_pages.setMinimumWidth(240)
    from PySide6.QtWidgets import QStackedWidget
    for stack in host.console_pages.findChildren(QStackedWidget):stack.setMinimumWidth(240)
    host.sim_dock.setMinimumWidth(260)
    host.sim_dock.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
    host.selection_inspector.hide()
    host.nav_dock.setWindowTitle('Project explorer')
    host.nav.reading_indent()
    host.nav.setIconSize(QSize(20,20))
    host.clip_dock.setObjectName('ArcClipEntry')
    host.clip_dock.setMinimumHeight(190)
    host.clip_dock.setMaximumHeight(196)
    def resize_assistant(expanded):
        host.clip_dock.setMaximumHeight(16777215 if expanded else 196)
        host.diagnostics_splitter.setSizes([700, 500] if expanded else [900, 190])
        host.clip._queue()
    host.clip_dock.advanced.toggled.connect(resize_assistant)
    host.diagnostics_splitter.setSizes([900,190])
    host.doc_info.hide()
    from .project_context import detached
    host.arc_state = QLabel('Graphite  ·  Program only  ·  Project not attached' if detached(host.root) else 'ARC-1 R10  ·  Local project  ·  Hardware disconnected')
    host.statusBar().addWidget(host.arc_state,1)
    host.nav_dock.setMinimumWidth(270)  # navigator labels fit without ellipses
    host.resizeDocks([host.nav_dock,host.sim_dock],[275,310],Qt.Horizontal)
    from PySide6.QtCore import QTimer
    QTimer.singleShot(0, lambda: host.resizeDocks([host.nav_dock, host.sim_dock], [275, 330], Qt.Horizontal))
    host.concern.track_current()
    host.activity_rail.update_current()
    host.tabs.currentChanged.connect(lambda _: refresh(host))
    host.arc_controller = ShellController(host)
    host.installEventFilter(host.arc_controller)
    host.toolbar.installEventFilter(host.arc_controller)  # the ribbon narrows when the navigator widens
    host.arc_controller.resize()
    host.setWindowTitle('Graphite · The Silicon Federation workshop')
    # The dock retitle renames its toggle action; refresh the icon-only favourites' accessible names.
    host._refresh_favorite_buttons()


def refresh(host):
    if not hasattr(host,'arc_inspector'):
        return
    host.concern.track_current()
    host.activity_rail.update_current()
    host.arc_inspector.refresh()
    host.selection_inspector.hide()
    host.doc_info.hide()
    tab = host.tabs.currentWidget()
    # One header, not four: the source actions appear for code, the Concern strip when a Concern item is in focus.
    host.context_bar.setVisible(not host._home_active and type(tab).__name__ == 'CodeEditor')
    strip = getattr(host.concern, 'context_strip', None)
    if strip is not None:strip.setVisible(not host._home_active and bool(getattr(host.concern, 'current_attention', None)))
    host.workspace_status.setVisible(host._home_active or type(tab).__name__ != 'ConcernDossier')
    if getattr(host, '_field_active', False):  # the Field has the whole centre: no bar of the work under it
        host.context_bar.hide();host.workspace_status.hide()
    documents = type(tab).__name__ == 'CodeEditor' or host.tabs.count() > 1
    host.tabs.tabBar().setVisible(documents)
    host.tabs.pin_button.setVisible(documents)


class ShellController(QObject):
    def __init__(self, host):
        super().__init__(host)
        self.host = host

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self.resize()
        return False

    def resize(self):
        width = self.host.width()
        if width != getattr(self, '_window_width', None):
            self._window_width = width
            if width < 1200:
                if not getattr(self, '_compact_docks', False):
                    self._prior_docks = [self.host.nav_dock.width(), self.host.sim_dock.width()]
                self._compact_docks = True
                self.host.resizeDocks([self.host.nav_dock, self.host.sim_dock], [270, 260], Qt.Horizontal)
            elif getattr(self, '_compact_docks', False):
                self._compact_docks = False
                self.host.resizeDocks([self.host.nav_dock, self.host.sim_dock], self._prior_docks, Qt.Horizontal)
        ribbon = getattr(self.host, 'toolbar', None)
        compact = (ribbon.width() if ribbon is not None and ribbon.isVisible() else self.host.width()) < 1320
        for menu in self.host.command_menus.values():
            if getattr(self.host, 'desk', None) is not None:break  # HATCH DESK D1a: the head's words take their own width; the desk spaces them
            menu.setMinimumWidth(max(62,menu.fontMetrics().horizontalAdvance(menu.text().replace('&',''))+36))
        for buttons in self.host.favorite_button_rows.values():
            for button in buttons:
                button.setFixedSize(38 if compact else 44,38 if compact else 44)
                button.setIconSize(QSize(26,26) if compact else QSize(28,28))
        if hasattr(self.host,'ribbon_commands'):self.host.ribbon_commands.adjustSize()
        # Search now sits in the navigator header as an icon beside the tree filter.


def organize_navigator(host):
    """The Concern is the root: the ARC-1 Console with its hardware first, then the
    Concern's legal record, handbook, ledger, platform and other work areas. Every
    existing device, area and shortcut is retained; only its place in the tree moves."""
    from PySide6.QtWidgets import QTreeWidgetItem
    top = host.nav.topLevelItem(0)
    if top is None:
        return
    top.setText(0,'ARC-1 Console')
    top.setToolTip(0,'The ARC-1 console: its hardware, devices and source-bound studies')
    physical = ('nor','f133','d213','fpga12','fpga45','interfaces','pcb','case')
    names = {'nor':'NOR / Boot','f133':'F133','d213':'D213', 'fpga12':'FPGA 12F',
             'fpga45':'FPGA 45F','interfaces':'USB / I/O','pcb':'Motherboard','case':'Case'}
    nodes = {item.data(0,Qt.UserRole+4): item for item in host._nav_items()
             if item.data(0,Qt.UserRole+2)=='nav_device'}
    for pos, ident in enumerate(physical):
        item = nodes.get(ident)
        if item is None:
            continue
        parent = item.parent()
        if parent is not None:
            parent.takeChild(parent.indexOfChild(item))
        top.insertChild(pos,item)
        item.setText(0,names[ident])
    labels = {'database_rom':'Reference library','ledger_active':'Graphite','platform':'OS & firmware',
              'ai_clip':'Graphite workshop','orange_book':'Orange Book','console_hardware':'Hardware studies',
              'struthio':'Games / STRUTHIO'}
    areas = {}
    for ident, item in host._workspace_areas.items():
        parent = item.parent()
        if parent is not None:parent.takeChild(parent.indexOfChild(item))
        else:
            index = host.nav.indexOfTopLevelItem(item)
            if index >= 0:host.nav.takeTopLevelItem(index)
        item.setText(0, labels.get(ident, item.text(0)))
        areas[ident] = item
    host.nav.takeTopLevelItem(host.nav.indexOfTopLevelItem(top))
    concern = QTreeWidgetItem(['ARC Concern'])
    concern.setData(0,Qt.UserRole+2,'nav_concern')
    concern.setIcon(0,icon(host.root,'source-fact'))
    concern.setToolTip(0,"ARC · Adaptive RISC-V Concern\nOpen Graphite's Control Center")
    host.nav.insertTopLevelItem(0, concern)
    concern.addChild(top)
    if 'console_hardware' in areas:top.addChild(areas.pop('console_hardware'))
    legal = QTreeWidgetItem(['Legal'])
    legal.setData(0,Qt.UserRole+2,'nav_legal')
    legal.setIcon(0,icon(host.root,'source-fact'))
    legal.setToolTip(0,'Founding charter, verified time evidence, rights and notices')
    concern.addChild(legal)
    ledger = areas.get('ledger_active')
    if ledger is not None:
        for i in range(ledger.childCount() - 1, -1, -1):
            child = ledger.child(i)
            if child.data(0,Qt.UserRole+4) == 'show_genesis':
                legal.addChild(ledger.takeChild(i))
                child.setText(0,'Genesis · founding charter')
    for title, path, tip in (('Rights & publication terms','RIGHTS.md','Owner rights and publication decisions'),
                             ('Third-party notices','THIRD_PARTY_NOTICES.md','Upstream licences and notices'),
                             ('Genesis guide','docs/GENESIS.md','What the Genesis record proves and does not prove')):
        child = host._add_nav_special(legal, title, host.root / path, 'nav_file', tip)
        if child is not None:child.setIcon(0,icon(host.root,'page-link'))
    for ident in ('orange_book','ledger_active','platform','database_rom','ai_clip','struthio'):
        if ident in areas:concern.addChild(areas.pop(ident))
    for item in areas.values():concern.addChild(item)
    concern.setExpanded(True);top.setExpanded(True)


def filter_tree(host, text):
    """Show tree items whose label matches, with their ancestors; empty text restores all.
    Expansion is remembered while filtering and restored when the filter is cleared."""
    needle = text.strip().casefold()
    nav = host.nav
    if needle and getattr(host, '_tree_expanded_before_filter', None) is None:
        host._tree_expanded_before_filter = {id(item): item.isExpanded() for item in host._nav_items()}
    def visit(item):
        matched = bool(needle) and needle in item.text(0).casefold()
        child_match = False
        for i in range(item.childCount()):
            child_match = visit(item.child(i)) or child_match
        show = not needle or matched or child_match
        item.setHidden(not show)
        if needle and child_match:item.setExpanded(True)
        return matched or child_match
    for i in range(nav.topLevelItemCount()):
        visit(nav.topLevelItem(i))
    if not needle and getattr(host, '_tree_expanded_before_filter', None) is not None:
        before = host._tree_expanded_before_filter;host._tree_expanded_before_filter = None
        for item in host._nav_items():
            if id(item) in before:item.setExpanded(before[id(item)])
