"""Slate's Control Center: the Home surface over the existing workspace.

The approved unboxing artwork is the centrepiece over a decorative code-rain backdrop.
Around it, a compact operational area reads real project state (workbench.journey):
where you left off, the next sensible action and five journey stages. Nothing on this
page estimates progress, starts a job or contacts a provider.
"""
from .assistant_identity import named
import hashlib
import json

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from .code_rain import CodeRain


def shadow(widget, blur=28):
    from PySide6.QtWidgets import QGraphicsDropShadowEffect
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur);effect.setOffset(0, 5);effect.setColor(QColor(0, 0, 0, 170))
    widget.setGraphicsEffect(effect)

ART = 'branding/stacy/control-center.png'
FALLBACK_ART = 'branding/noir/home-scene.png'


class HomeArtwork(QWidget):
    """Bird-led native entrances; retired scene pixels remain historical originals."""
    activated=Signal(str)
    def __init__(self,root):
        super().__init__();self.setObjectName('HomeArtwork')
        self.setAccessibleName('Graphite workshop entrances')
        self.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Expanding)
        from .static_bird import BirdView
        row=QHBoxLayout(self);row.setContentsMargins(12,8,12,8)
        self.bird=BirdView(root);row.addWidget(self.bird,1)
        grid=QGridLayout();grid.setSpacing(10)
        for i,(key,title) in enumerate([('console','Console'),('rom','References'),
                ('book','Orange Book'),('ledger','Graphite'),('struthio','STRUTHIO'),('stacy',named('Ask Stacy'))]):
            button=QPushButton(title);button.setMinimumHeight(45)
            button.setAccessibleName(title+' workshop entrance')
            button.clicked.connect(lambda checked=False,k=key:self.activated.emit(k))
            grid.addWidget(button,i//2,i%2)
        row.addLayout(grid,2)
    def sizeHint(self):return QSize(960,260)


class JourneyLoader(QThread):
    """Reads Control Center facts off the GUI thread; the result is plain data."""
    ready=Signal(dict)
    def __init__(self, root, last_workspace, parent=None):
        super().__init__(parent);self.root=root;self.last_workspace=last_workspace
    def run(self):
        from .engine import engineering
        from . import journey
        try:self.ready.emit(journey.snapshot(self.root, engineering(self.root), self.last_workspace))
        except Exception as exc:self.ready.emit({'error':type(exc).__name__+': '+str(exc)[:200]})


class StageTile(QPushButton):
    """A focusable stage card: title over a wrapped status line read from real state."""
    def __init__(self, key, title, subtitle):
        super().__init__()
        self.key=key;self.title_=title;self.subtitle=subtitle
        self.setObjectName('JourneyStage');self.setProperty('arcState','LOADING')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        box=QVBoxLayout(self);box.setContentsMargins(12,7,10,7);box.setSpacing(1)
        self.heading=QLabel(title);self.heading.setObjectName('stageTitle')
        self.status=QLabel();self.status.setObjectName('stageStatus');self.status.setWordWrap(True)
        for label in (self.heading,self.status):
            label.setAttribute(Qt.WA_TransparentForMouseEvents);box.addWidget(label)
        box.addStretch(1)
        self.setMinimumHeight(70)
        self.show_fact('Reading project state…','')
    def show_fact(self, status, detail, state='READY'):
        self.status.setText(status)
        self.setToolTip(self.subtitle+(('\n'+detail) if detail else ''))
        self.setAccessibleName(self.title_+' stage: '+status)
        self.setAccessibleDescription(self.subtitle+'. '+detail)
        self.setProperty('arcState',state);self.style().unpolish(self);self.style().polish(self)
    def sizeHint(self):
        hint=self.layout().sizeHint();return QSize(max(140,hint.width()),max(70,hint.height()))


STYLE = """
QWidget#WorkshopHome QLabel { background: transparent; }
QFrame#ControlCard { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(70,78,90,232), stop:0.07 rgba(30,36,44,236), stop:1 rgba(14,17,22,240));
    border: 1px solid #0c0f13; border-top-color: #7d8792; border-radius: 12px; }
QLabel#homeOverline { color: #ff9a32; letter-spacing: 3px; font-weight: 700; }
QLabel#homeTitle { color: #f3f4f6; }
QLabel[arcRole="fact"] { color: #f3f4f6; }
QLabel#stageTitle { color: #ffb05c; font-weight: 700; }
QLabel#stageStatus { color: #e6e8eb; }
QPushButton#JourneyStage { padding: 0; background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(84,94,107,238), stop:0.46 rgba(44,51,60,240), stop:0.5 rgba(32,38,46,242), stop:1 rgba(22,27,34,245));
    border: 1px solid #3a4250; border-left: 4px solid #ff9a32; border-radius: 7px; color: #e6e8eb; }
QPushButton#JourneyStage:hover, QPushButton#JourneyStage:focus { border-color: #ff9a32; background: rgba(48,36,25,235); }
QPushButton#JourneyStage[arcState="ATTENTION"] { border-left-color: #ffcc4d; }
QPushButton#JourneyStage[arcState="UNAVAILABLE"], QPushButton#JourneyStage[arcState="LOADING"] { border-left-color: #6b7380; }
"""


class WorkshopHome(QWidget):
    STAGES=(('explore','Explore','Walk the machine: the console hardware, native parts and their links'),
            ('understand','Understand','Learn in the Orange Book and the attached references'),
            ('build','Build','Create, build and boot a native C game in the host model'),
            ('prove','Prove','Read requirements, checks and the evidence that exists today'),
            ('improve','Improve','Review jobs, isolated candidates and proposals waiting for a decision'))

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setObjectName('WorkshopHome')
        self.setStyleSheet(STYLE)
        self.loader=None;self.facts=None
        profile=window.session.state.get('reading_profile') or {}
        from .reading_profile import DEFAULT
        self.rain = CodeRain(self, reduce_motion=profile.get('reduce_motion', DEFAULT['reduce_motion']))
        self.rain.lower()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 12, 22, 10)
        outer.setSpacing(8)
        words = QVBoxLayout();words.setSpacing(2)
        overline=QLabel('GRAPHITE  ·  ARC-1 R10');overline.setObjectName('homeOverline');words.addWidget(overline)
        title = QLabel("Graphite's Control Center")
        title.setObjectName('homeTitle')
        words.addWidget(title)
        subtitle = QLabel(named('Your engineering headquarters. Choose a workspace, or ask Stacy.'))
        subtitle.setWordWrap(True)
        subtitle.setProperty('arcRole', 'metadata')
        words.addWidget(subtitle)
        outer.addLayout(words)
        self.art = HomeArtwork(window.root)
        self.art.activated.connect(self.explore_art)
        outer.addWidget(self.art, 1)

        card = QFrame();card.setObjectName('ControlCard')
        grid = QGridLayout(card);grid.setContentsMargins(14, 8, 14, 8);grid.setHorizontalSpacing(18);grid.setVerticalSpacing(4)
        heading = QLabel('Continue your journey');heading.setProperty('arcRole','section')
        grid.addWidget(heading, 0, 0, 1, 3)
        note = QLabel('Resume the most recent verified engineering activity, open its files, and inspect the evidence.')
        note.setWordWrap(True);note.setProperty('arcRole','metadata');grid.addWidget(note, 1, 0, 1, 3)
        self.fact_labels = {}
        for column,(key,label) in enumerate((('project','Current project'),('workspace','Last workspace'),('next','Next action'))):
            name=QLabel(label);name.setProperty('arcRole','metadata');grid.addWidget(name, 2, column)
            value=QLabel('…');value.setProperty('arcRole','fact');value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextSelectableByMouse|Qt.LinksAccessibleByMouse|Qt.LinksAccessibleByKeyboard);grid.addWidget(value, 3, column)
            self.fact_labels[key]=value
        self.buttons = {}
        go = QPushButton('Continue');go.setObjectName('homeContinue')
        go.setToolTip('Resume your actual open workspace and check its source files')
        go.setAccessibleName('Continue in Graphite');go.setProperty('arcRole','primary')
        go.clicked.connect(window.resume_workspace);self.buttons['Continue']=go
        grid.addWidget(go, 2, 3, 2, 1)
        self.fact_labels['next'].linkActivated.connect(lambda _link:self.open_next())
        self.fact_labels['next'].setAccessibleName('Next action; activate the link to open its stage')
        grid.setColumnStretch(0,1);grid.setColumnStretch(1,1);grid.setColumnStretch(2,1)
        outer.addWidget(card);shadow(card)

        stages = QHBoxLayout();stages.setSpacing(8)
        self.stages = {}
        for key,title_text,subtitle_text in self.STAGES:
            tile=StageTile(key,title_text,subtitle_text);tile.clicked.connect(lambda checked=False,k=key:self.open_stage(k))
            stages.addWidget(tile,1);self.stages[key]=tile;shadow(tile,18)
        # Protected Home contract: Explore and Learn remain named, focusable entrances.
        self.buttons['Explore']=self.stages['explore'];self.buttons['Learn']=self.stages['understand']
        outer.addLayout(stages)

        self.context = QLabel()
        self.context.setObjectName('homeContext');self.context.hide()
        followup=QHBoxLayout()
        self.followup_button=QPushButton('Review parser finding')
        self.followup_button.setProperty('arcRole','link')
        self.followup_button.clicked.connect(self.open_followup)
        followup.addWidget(self.followup_button)
        self.followup_note=QLabel();self.followup_note.setWordWrap(True)
        self.followup_note.setProperty('arcRole','metadata')
        self.followup_note.setTextInteractionFlags(Qt.TextSelectableByMouse)
        followup.addWidget(self.followup_note,1)
        outer.addLayout(followup)
        footer = QHBoxLayout()
        motto = QLabel('We do not walk toward life. We walk within it.')
        motto.setProperty('arcRole', 'metadata')
        motto.setWordWrap(True)
        footer.addWidget(motto, 1)
        comfort=QPushButton('Reading comfort');comfort.setProperty('arcRole','link')
        comfort.setToolTip('Font size, spacing and optional motion, including this backdrop');comfort.clicked.connect(window.show_reading)
        footer.addWidget(comfort)
        self.startup = QComboBox()
        self.startup.addItem('Start: on the work', 'last')
        self.startup.addItem('Start: always Home', 'home')
        self.startup.setAccessibleName('Graphite startup preference')
        self.startup.setToolTip('On the work: the Field first when this workspace has work, and Esc goes to where you left off. Open documents and the saved layout are kept either way.')
        self.startup.currentIndexChanged.connect(self._startup_changed)
        footer.addWidget(self.startup)
        outer.addLayout(footer)
        self.refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.rain.setGeometry(self.rect())

    def _startup_changed(self, index):
        self.window_.set_view_preference(startup=self.startup.itemData(index))

    def _leave(self, method, *args):
        self.window_._close_start()
        return getattr(self.window_, method)(*args)

    def explore_art(self,key):
        if key=='book':return self.window_.learn_workspace()
        if key=='console':return self._leave('show_arcos')
        if key=='rom':return self._leave('show_database_rom')
        if key=='struthio':return self._leave('show_native_game')
        if key=='ledger':return self._leave('show_hardware_ledger')
        if key=='stacy':return self.window_.open_clip()
        if key in self.window_._nav_devices:
            return self.window_.show_device(key)

    def open_stage(self, key):
        if key=='explore':return self.window_.explore_workspace()
        if key=='understand':return self.window_.learn_workspace()
        if key=='build':return self._leave('show_native_project')
        if key=='prove':return self._leave('show_engineering_register')
        if key=='improve':return self._leave('show_engineering')

    def open_next(self):
        stage=((self.facts or {}).get('next_action') or {}).get('stage')
        if stage in self.stages:self.open_stage(stage)

    def last_workspace(self):
        host = self.window_
        editor = host.current_editor()
        return (editor.path.relative_to(host.root).as_posix() if editor
                else host.tabs.tabText(host.tabs.currentIndex()).replace('Preview · ', '').replace('◆ ', '')
                if host.tabs.count() else 'Console hardware')

    def refresh(self):
        host = self.window_
        workspace=self.last_workspace()
        self.context.setText('Continue working: ' + workspace)
        self.fact_labels['workspace'].setText(workspace)
        self.startup.blockSignals(True)
        self.startup.setCurrentIndex(self.startup.findData(host.view_preferences['startup']))
        self.startup.blockSignals(False)
        self.load_journey(workspace)
        self.followup=None
        from .record_io import project_path
        try:
            relative='docs/ledger2/OPEN_ISSUES.json'
            path=project_path(host.root,relative)
            raw=path.read_bytes()
            issue=next(row for row in json.loads(raw)['issues'] if row['id']=='OI-13')
            line=next(i for i,text in enumerate(raw.decode().splitlines(),1) if '"OI-13"' in text)
            self.followup={'path':relative,'sha256':hashlib.sha256(raw).hexdigest(),'line':line}
            self.followup_button.setText('Review parser finding')
            self.followup_note.setText('Command-parser correction · isolated proposal · review pending')
            self.followup_note.setToolTip(issue['issue']+'\nNext recorded action: '+issue['next_action'])
        except (OSError,ValueError,KeyError,StopIteration):
            self.followup_note.setText('No current follow-up record available')
        self.followup_button.setEnabled(self.followup is not None)

    def load_journey(self, workspace):
        if self.loader is not None and self.loader.isRunning():return
        self.loader=JourneyLoader(self.window_.root, workspace, self)
        self.loader.ready.connect(self.show_journey)
        self.loader.start()

    def show_journey(self, facts):
        if 'error' in facts:
            for tile in self.stages.values():tile.show_fact('Unavailable',facts['error'],'UNAVAILABLE')
            self.fact_labels['project'].setText('ARC-1 · R10');self.fact_labels['next'].setText('Project state unavailable');return
        self.facts=facts
        self.fact_labels['project'].setText(facts['project'])
        from html import escape
        self.fact_labels['next'].setText('<a href="next" style="color:#ffb05c;text-decoration:none">'+escape(facts['next_action']['text'])+' →</a>')
        for key,tile in self.stages.items():
            stage=facts['stages'][key];tile.show_fact(stage['status'],stage['detail'],stage['state'])

    def open_followup(self):
        if self.followup is None:return
        from .record_io import project_path
        path=project_path(self.window_.root,self.followup['path'])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=self.followup['sha256']:
            self.followup_note.setText('Record changed · reopen Home to refresh before navigating')
            self.followup_button.setEnabled(False)
            return
        return self.window_.show_parser_review()

    def shutdown(self):
        self.rain.timer.stop()
        if self.loader is not None and self.loader.isRunning():self.loader.wait(5000)

    def title(self):
        return "Graphite's Control Center"

    def info(self):
        return "Graphite's Control Center · real project state; no estimated progress"
