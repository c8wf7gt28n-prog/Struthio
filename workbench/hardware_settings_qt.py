"""Editor for hardware.category_views: one combo per current hardware pane over the saved Session map.

The map is the existing per-pane field (device.id/group.title → Auto view, Details, Thumbnails).
Saved keys that are not current panes are shown as retained and never rewritten. Nothing here
opens a file, browses a folder or journals by itself; Apply in the Settings editor sends one Set.

DESKTOP-01 (V-08, ACC-06, ACC-07, ACC-10): the frame's height follows its rows up to a cap that scales
with the interface size, so a short list (or the no-navigator sentence) needs no scrollbar and a long one
has exactly one; each row stays within reading distance; the Tab order runs pane by pane and then reaches
Apply; every combo is named `<device> / <group> view` for assistive technology, with its label as buddy and
the current mode as its accessible description.
"""
from PySide6.QtCore import QEvent, QSignalBlocker, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QScrollArea, QStackedWidget
from .hardware_nav import navigation
from .settings_registry import VIEW_MODES
from .shell2 import scale_of

FRAME_CAP_PX = 320   # at the default interface size (14 pt); scales with reading.ui_pt
ROW_MAX_PX = 720     # a pane name and its value stay together (V-08 measured 980 px between them)


def pane_keys(root,devices=None):
    """Current category panes as (key, device title, group title); the PCB layout group opens the native board, not a pane.

    `devices` is the navigator's device-id collection when the window has one; an empty collection (a workspace with
    no project attached has no hardware navigator) lists no panes rather than inventing them.
    """
    rows=[]
    for device,_parent in navigation(root):
        if devices is not None and device.id not in devices:continue
        for group in device.groups:
            if (device.id,group.title)==('pcb','PCB layout'):continue
            rows.append((device.id+'/'+group.title,device.title,group.title))
    return rows


def view_summary(value):
    """Words for history and state lines instead of raw JSON."""
    if not isinstance(value,dict):return None
    custom=sorted((k,v) for k,v in value.items() if v!=VIEW_MODES[0])  # explicit Auto view entries (the pre-INTEGRATION-01 writer stored one per visited pane) are not customizations
    if not custom:return 'All panes Auto view' if not value else '%d pane%s listed, all Auto view'%(len(value),'' if len(value)==1 else 's')
    return '%d pane%s customized: '%(len(custom),'' if len(custom)==1 else 's')+', '.join(k+' = '+v for k,v in custom[:4])+(' …' if len(custom)>4 else '')+(', %d at Auto view'%(len(value)-len(custom)) if len(value)>len(custom) else '')


def frame_height(content_px,cap_px):
    """Pure: the frame shows its rows up to the cap (one scrollbar at most), never more than the content needs."""
    return max(0,min(int(content_px),int(cap_px)))


def focusable_before(widget,limit=2000):
    """The nearest widget before `widget` in its window's focus chain that can take keyboard focus (hidden ones count:
    Qt skips them while tabbing but they anchor the chain)."""
    if widget is None:return None
    current=widget.previousInFocusChain();steps=0
    while current is not None and current is not widget and steps<limit:
        if current.focusPolicy()!=Qt.NoFocus:return current
        current=current.previousInFocusChain();steps+=1
    return None


class ViewModes(QWidget):
    def __init__(self,host,edited):
        super().__init__();self.host=host;self.edited=edited;self.combos={};self.retained={};self.built=False;self.lines=[]
        self.first_combo=None;self.last_combo=None;self.tab_chain=[]
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);outer.setSpacing(6)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.setFocusPolicy(Qt.NoFocus)  # the empty frame is not a Tab stop (ACC-06); the combos are
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setAccessibleName('Hardware category view modes')
        self.page=QWidget();self.rows=QVBoxLayout(self.page);self.rows.setContentsMargins(0,0,8,0);self.rows.setSpacing(4);self.scroll.setWidget(self.page)
        outer.addWidget(self.scroll)
        self.retained_label=QLabel();self.retained_label.setWordWrap(True);self.retained_label.hide();outer.addWidget(self.retained_label)
        self.summary=QLabel();self.summary.setWordWrap(True);self.summary.setAccessibleName('Hardware views summary');outer.addWidget(self.summary)

    # ---- size -------------------------------------------------------------------------------------------------------
    def frame_cap(self):return round(FRAME_CAP_PX*scale_of(self.host))

    def row_width(self):return round(ROW_MAX_PX*scale_of(self.host))

    def refit(self):
        """Height follows the rows up to the scaled cap; the frame collapses to its sentence when there are no panes.
        A hosting stacked editor that shows this page follows the new height (the Settings editor sizes it at load)."""
        self.page.adjustSize();content=self.page.sizeHint().height()+4
        height=frame_height(content,self.frame_cap());self.scroll.setFixedHeight(height)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded if content>height else Qt.ScrollBarAlwaysOff)
        width=self.row_width()
        for line in self.lines:line.setMaximumWidth(width)
        self.updateGeometry()
        stack=self.parentWidget()
        if isinstance(stack,QStackedWidget) and stack.currentWidget() is self:stack.setFixedHeight(max(46,self.sizeHint().height()))
        return height

    def changeEvent(self,event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange,QEvent.StyleChange) and self.built:self.refit()

    # ---- rows -------------------------------------------------------------------------------------------------------
    def editor_tab(self):
        """The settings editor hosting this page, found by what it offers (its Apply word), not by class."""
        current=self.parentWidget()
        while current is not None and not hasattr(current,'apply_button'):current=current.parentWidget()
        return current

    def build(self):
        if self.built:return
        self.built=True;device_seen=None
        rows=pane_keys(getattr(self.host,'root',None),getattr(self.host,'_nav_devices',None))
        if not rows:
            note=QLabel('This workspace has no hardware navigator, so no category pane is listed. Saved choices are retained for a workspace that has one.')
            note.setWordWrap(True);note.setAccessibleName('No hardware category panes');self.rows.addWidget(note);self.note=note
        combos=[]
        for key,device_title,group_title in rows:
            if device_title!=device_seen:
                device_seen=device_title;label=QLabel(device_title);label.setProperty('arcReadingRole','subheading');self.rows.addWidget(label)
            line=QWidget();row=QHBoxLayout(line);row.setContentsMargins(12,0,0,0);row.setSpacing(8);line.setMaximumWidth(self.row_width())
            name=QLabel(group_title);name.setToolTip(key);name.setAccessibleName(device_title+' / '+group_title);row.addWidget(name,1)
            combo=QComboBox();combo.setObjectName('SettingValue');combo.addItems(list(VIEW_MODES));combo.setAccessibleName(device_title+' / '+group_title+' view')
            combo.setAccessibleDescription(combo.currentText());name.setBuddy(combo)  # LabelledBy for AT-SPI, which names a combo by its label (ACC-07)
            combo.currentTextChanged.connect(combo.setAccessibleDescription);combo.currentIndexChanged.connect(self.edited)
            row.addWidget(combo);self.rows.addWidget(line);self.combos[key]=combo;self.lines.append(line);combos.append(combo)
        self.rows.addStretch(1)
        if combos:
            # ACC-06: pane by pane in visual order, entered from whatever precedes Apply, and leaving into Apply.
            tab=self.editor_tab();apply=getattr(tab,'apply_button',None)
            anchor=focusable_before(apply) if apply is not None else None
            if anchor is not None and anchor not in combos and not self.isAncestorOf(anchor):QWidget.setTabOrder(anchor,combos[0])
            for previous,combo in zip(combos,combos[1:]):QWidget.setTabOrder(previous,combo)
            if apply is not None:QWidget.setTabOrder(combos[-1],apply)
            self.first_combo,self.last_combo=combos[0],combos[-1];self.tab_chain=[anchor]+combos+[apply]
        self.refit()

    def configure(self,row,value):
        self.build();value=dict(value or {})
        self.retained={k:v for k,v in value.items() if k not in self.combos}
        # Explicit Auto view entries for current panes round-trip unchanged, so opening the editor is never an edit.
        self.saved_auto={k for k,v in value.items() if k in self.combos and v==VIEW_MODES[0]}
        for key,combo in self.combos.items():
            with QSignalBlocker(combo):combo.setCurrentText(value.get(key,VIEW_MODES[0]));combo.setAccessibleDescription(combo.currentText())
        self.retained_label.setText('Retained for panes not in this navigator: '+', '.join(k+' = '+v for k,v in sorted(self.retained.items())) if self.retained else '')
        self.retained_label.setVisible(bool(self.retained));self.summary.setText(view_summary(value));self.refit()

    def value(self):
        result=dict(self.retained)
        for key,combo in self.combos.items():
            if combo.currentText()!=VIEW_MODES[0] or key in getattr(self,'saved_auto',()):result[key]=combo.currentText()
        return result
