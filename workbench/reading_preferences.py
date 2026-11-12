"""Local font roles, readable prose and late-created views; never edits source text."""
from functools import lru_cache
from PySide6.QtCore import QObject,QEvent,QTimer,QSignalBlocker
from PySide6.QtGui import QFont,QFontDatabase,QTextBlockFormat,QTextCursor
from PySide6.QtWidgets import (QApplication,QWidget,QCheckBox,QComboBox,QDialog,QDialogButtonBox,
    QDoubleSpinBox,QFormLayout,QLabel,QPlainTextEdit,QPushButton,QTextBrowser,QVBoxLayout,QScrollArea)
from shiboken6 import isValid
from .reading_profile import DEFAULT,clean
from . import record_io as io
from . import locations


@lru_cache(maxsize=4)
def load_fonts(root):
    root=locations.program(root);source=io.load(root,'branding/ux17/fonts/SOURCE.json');families=[]
    for row in source['files']:
        p=io.project_path(root,row['path'])
        if io.sha(p)!=row['sha256']:raise ValueError('FONT_SOURCE_CHANGED')
        if not row['path'].endswith('.otf'):continue
        key=QFontDatabase.addApplicationFont(str(p))
        if key>=0:families.extend(QFontDatabase.applicationFontFamilies(key))
    return tuple(sorted(set(families)))


def family(name,fixed=False):
    available=set(QFontDatabase.families())
    if name in available and (not fixed or QFontDatabase.isFixedPitch(name)):return name
    fallback='DejaVu Sans Mono' if fixed else 'DejaVu Sans'
    return fallback if fallback in available else QFontDatabase.systemFont(
        QFontDatabase.FixedFont if fixed else QFontDatabase.GeneralFont).family()


def font(name,size,fixed=False):
    result=QFont(family(name,fixed));result.setPointSizeF(size)
    if fixed:result.setStyleHint(QFont.Monospace);result.setFixedPitch(True)
    return result


def browser_spacing(browser,profile):
    if not isValid(browser):return
    document=browser.document();modified=document.isModified()
    scroll=browser.verticalScrollBar().value()
    with QSignalBlocker(document):
        document.setDefaultFont(font(profile['prose_family'],profile['prose_pt']))
        cursor=QTextCursor(document);cursor.select(QTextCursor.Document)
        block=QTextBlockFormat()
        block.setLineHeight(profile['line_height']*100,QTextBlockFormat.ProportionalHeight.value)
        cursor.mergeBlockFormat(block);document.setModified(modified)
    browser.verticalScrollBar().setValue(scroll)


def style_widget(widget,profile):
    role=widget.property('arcReadingRole')
    if isinstance(widget,QPlainTextEdit):
        prose=role=='prose'
        widget.setFont(font(profile['prose_family'] if prose else profile['code_family'],
                            profile['prose_pt'] if prose else profile['code_pt'],not prose))
        if hasattr(widget,'_update_margins'):
            widget.setTabStopDistance(widget.fontMetrics().horizontalAdvance(' ')*4)
            widget._update_margins()
    elif isinstance(widget,QTextBrowser):
        widget.setFont(font(profile['prose_family'],profile['prose_pt']))
        widget.document().setDefaultStyleSheet("body,p,li {font-family:'%s';font-size:%.1fpt;}"%
            (family(profile['prose_family']),profile['prose_pt']))
        browser_spacing(widget,profile)
    elif isinstance(widget,QLabel) and role:
        widget.setFont(font(profile['prose_family'] if role=='prose' else profile['family'],
            profile['prose_pt'] if role=='prose' else profile['ui_pt']+3 if role=='heading' else profile['ui_pt']))


class ReadingWatcher(QObject):
    """Apply existing preferences when views appear; no polling or contents collection."""
    def __init__(self,host):
        super().__init__(host);self.host=host
        QApplication.instance().installEventFilter(self)
    def belongs(self,widget):
        current=widget
        while current is not None:
            if current is self.host:return True
            current=current.parent()
        return False
    def eventFilter(self,watched,event):
        if event.type() in (QEvent.Show,QEvent.Polish) and isinstance(watched,QWidget):
            if isValid(self.host) and not self.host._closing and self.belongs(watched):
                if isinstance(watched,(QPlainTextEdit,QTextBrowser)) or watched.property('arcReadingRole'):
                    QTimer.singleShot(0,lambda w=watched:self.update_widget(w))
        return False
    def update_widget(self,widget):
        if not isValid(self.host) or self.host._closing or not isValid(widget):return
        if widget.property('arcReadingPreview'):return
        style_widget(widget,self.host.reading_profile)
        if isinstance(widget,QTextBrowser) and not getattr(widget,'_arc_spacing_connected',False):
            widget._arc_spacing_connected=True
            widget.document().contentsChanged.connect(lambda w=widget:self.update_browser(w))
    def update_browser(self,widget):
        if isValid(self.host) and not self.host._closing and isValid(widget) and not widget.property('arcReadingPreview'):
            browser_spacing(widget,self.host.reading_profile)


def apply(host,profile=None,persist=False):
    profile=clean(profile if profile is not None else host.session.state.get('reading_profile',DEFAULT))
    try:families=load_fonts(str(host.root))
    except (OSError,ValueError):families=()
    from .reading_profile import OLD_DEFAULT_FAMILIES
    names=(profile['family'],profile['prose_family'],profile['code_family'])
    if names==OLD_DEFAULT_FAMILIES:names=('IBM Plex Sans','IBM Plex Sans','IBM Plex Mono')
    ui=family(names[0]);prose=family(names[1]);code=family(names[2],True)
    host.reading_profile=profile
    host.setStyleSheet(
        "QWidget {font-family:'%s';font-size:%.1fpt;}"
        "QTreeWidget#hardwareTree {font-size:%.1fpt;}"
        "QPlainTextEdit {font-family:'%s';font-size:%.1fpt;}"
        "QTextBrowser,QPlainTextEdit[arcReadingRole='prose'],QLabel[arcReadingRole='prose'] {font-family:'%s';font-size:%.1fpt;}"
        "QLabel[arcReadingRole='heading'] {font-size:%.1fpt;font-weight:600;}"
        "QPushButton:focus,QToolButton:focus,QComboBox:focus,QTreeWidget:focus,QListWidget:focus {border:2px solid #504d46;}"
        "QPushButton {padding:4px 9px;} QHeaderView::section {padding:5px 7px;}"
        "QLabel#homeTitle {font-size:%.1fpt;font-weight:600;}"%
        (ui,profile['ui_pt'],profile['navigation_pt'],code,profile['code_pt'],
         prose,profile['prose_pt'],profile['ui_pt']+3,profile['ui_pt']+8))
    host.nav.setObjectName('hardwareTree');host.nav.setFont(font(ui,profile['navigation_pt']))
    if not hasattr(host,'reading_watcher'):host.reading_watcher=ReadingWatcher(host)
    for widget in host.findChildren(QWidget):
        if isinstance(widget,(QPlainTextEdit,QTextBrowser)) or widget.property('arcReadingRole'):
            host.reading_watcher.update_widget(widget)
    if hasattr(host,'shell2'):host.shell2.restyle(profile)  # the window's frame keeps the 2.x design scale
    if hasattr(host,'arc_controller'):host.arc_controller.resize()
    if getattr(host,'home_page',None) is not None:
        host.home_page.rain.set_reduce_motion(profile['reduce_motion'])
    marker=getattr(host,'writing_marker',None)
    if marker is not None:marker.motion_changed()  # the writing marker is static from the first moment Reduce motion is on
    if persist:
        host.session.state['reading_profile']=profile;host.session.save()
    return {'requested_family':profile['family'],'actual_family':ui,
            'actual_prose_family':prose,'actual_code_family':code,
            'bundled_families':families,'profile':profile}


def adjust_prose(host,delta):
    if hasattr(host,'ledger_bridge'):
        from . import ledger_control
        from .engineering_kernel import operator
        row=next(r for r in ledger_control.settings(host.ledger_bridge.kernel)['settings'] if r['key']=='reading.prose_pt')
        response=host.ledger_bridge.kernel.dispatch('ledger.settings.set',dict(key=row['key'],value=max(9,min(28,row['value']+delta)),expected_revision=row['revision']),operator())
        if not response['ok']:raise ValueError(response['error']['message'])
        host.ledger_bridge.sync_profile(force=True);return apply(host)
    profile=clean(getattr(host,'reading_profile',host.session.state.get('reading_profile',DEFAULT)))
    profile['prose_pt']=max(9,min(28,profile['prose_pt']+delta))
    return apply(host,profile,True)


class ReadingDialog(QDialog):
    def __init__(self,host):
        super().__init__(host);self.host=host
        self._settings_baseline={}
        if hasattr(host,'ledger_bridge'):
            from . import ledger_control
            host.ledger_bridge.sync_profile(force=True)
            self._settings_baseline={r['key']:r for r in ledger_control.settings(host.ledger_bridge.kernel,'Appearance')['settings'] if r['key'].startswith('reading.')}
        self.setWindowTitle('Reading and layout');self.resize(620,730)
        layout=QVBoxLayout(self);scroll=QScrollArea();scroll.setWidgetResizable(True)
        body=QWidget();v=QVBoxLayout(body);scroll.setWidget(body);layout.addWidget(scroll)
        form=QFormLayout();form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow);v.addLayout(form)
        try:bundled=load_fonts(str(host.root))
        except (OSError,ValueError):bundled=()
        available=set(QFontDatabase.families());self.families={}
        for key,title in [('family','Interface font'),('prose_family','Prose font'),('code_family','Code font')]:
            combo=QComboBox();combo.setMinimumWidth(0);combo.setEditable(True)
            choices=sorted((x for x in available if key!='code_family' or QFontDatabase.isFixedPitch(x)),key=str.casefold)
            first=[x for x in bundled if x in choices]
            combo.addItems(first+[x for x in choices if x not in first])
            combo.setAccessibleName(title);self.families[key]=combo;form.addRow(title,combo)
        self.family=self.families['family']
        self.controls={}
        from .reading_profile import RANGES
        titles={'ui_pt':'Interface size','navigation_pt':'Navigation size','prose_pt':'Prose size','code_pt':'Code size','line_height':'Document line spacing'}
        for key,lo,hi in sorted(RANGES,key=lambda r:('ui_pt','navigation_pt','prose_pt','code_pt','line_height').index(r[0])):
            title=titles[key]
            control=QDoubleSpinBox();control.setRange(lo,hi);control.setSingleStep(.1 if key=='line_height' else .5)
            control.setDecimals(1);control.setAccessibleName(title);self.controls[key]=control;form.addRow(title,control)
        self.motion=QCheckBox('Reduce optional motion');form.addRow(self.motion)
        preset=QPushButton('Try larger reading text')
        preset.clicked.connect(lambda:self.populate({**self.values(),'prose_pt':20,'ui_pt':15,'navigation_pt':16,'code_pt':15}))
        v.addWidget(preset)
        note=QLabel('OpenDyslexic is bundled with its recorded source and licence. Code uses a separate fixed-pitch font. Ctrl+Alt+= / Ctrl+Alt+- adjusts prose. Apply saves locally; preview changes do not edit a document or its undo history.')
        note.setWordWrap(True);note.setProperty('arcReadingRole','prose');v.addWidget(note)
        self.prose_preview=QTextBrowser();self.prose_preview.setAccessibleName('Prose reading preview')
        self.prose_preview.setProperty('arcReadingPreview',True)
        self.prose_preview.setPlainText('Graphite keeps your place.\n\nRead an original, inspect the evidence, then choose the next useful step.')
        self.prose_preview.setMinimumHeight(160);v.addWidget(self.prose_preview)
        self.code_preview=QPlainTextEdit('int main(void) {\n    return 0;\n}')
        self.code_preview.setProperty('arcReadingPreview',True)
        self.code_preview.setReadOnly(True);self.code_preview.setAccessibleName('Monospaced code preview')
        self.code_preview.setMaximumHeight(105);v.addWidget(self.code_preview)
        self.note=QLabel();self.note.setWordWrap(True);layout.addWidget(self.note)
        buttons=QDialogButtonBox(QDialogButtonBox.Apply|QDialogButtonBox.Close|QDialogButtonBox.RestoreDefaults)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self.save)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.accept)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(lambda:self.populate(DEFAULT))
        layout.addWidget(buttons);self.populate(host.session.state.get('reading_profile',DEFAULT))
        for c in self.controls.values():c.valueChanged.connect(self.preview)
        for c in self.families.values():c.currentTextChanged.connect(self.preview)
    def values(self):
        return {**{k:c.currentText() for k,c in self.families.items()},
                'reduce_motion':self.motion.isChecked(),**{k:c.value() for k,c in self.controls.items()}}
    def populate(self,profile):
        data=clean(profile)
        for key,c in self.families.items():c.setCurrentText(data[key])
        for key,c in self.controls.items():c.setValue(data[key])
        self.motion.setChecked(data['reduce_motion']);self.preview()
    def preview(self,*_):
        try:
            profile=clean(self.values())
            self.prose_preview.setStyleSheet("font-family:'%s';font-size:%.1fpt;"%(family(profile['prose_family']),profile['prose_pt']))
            self.code_preview.setStyleSheet("font-family:'%s';font-size:%.1fpt;"%(family(profile['code_family'],True),profile['code_pt']))
            style_widget(self.prose_preview,profile);style_widget(self.code_preview,profile)
            self.note.setText('Preview only · Apply saves these settings.')
        except (ValueError,OSError) as exc:self.note.setText(str(exc))
    def save(self):
        try:
            if hasattr(self.host,'ledger_bridge'):
                from . import ledger_control
                from .engineering_kernel import operator
                profile=clean(self.values());changes=[]
                for key,value in profile.items():
                    row=self._settings_baseline['reading.'+key]
                    if value!=row['value']:changes.append(dict(key=row['key'],value=value,expected_revision=row['revision']))
                if changes:
                    response=self.host.ledger_bridge.kernel.dispatch('ledger.settings.apply',{'changes':changes},operator())
                    if not response['ok']:raise ValueError(response['error']['message'])
                self.host.ledger_bridge.sync_profile(force=True)
                self._settings_baseline={r['key']:r for r in ledger_control.settings(self.host.ledger_bridge.kernel,'Appearance')['settings'] if r['key'].startswith('reading.')}
                self.populate(self.host.reading_profile);self.note.setText('Saved through shared settings history. Undo is available for each changed key.');return
            result=apply(self.host,self.values(),True);self.preview()
            self.note.setText('Saved · prose '+result['actual_prose_family']+' · code '+result['actual_code_family'])
        except (ValueError,OSError) as exc:self.note.setText(str(exc))
