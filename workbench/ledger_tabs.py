"""Hardware and software import desk inside the existing center workspace."""
from .text_prompts import writing_prompt
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
                              QTreeWidget,QTreeWidgetItem,QHeaderView,QLineEdit)
from . import hardware_import
from .command_rows import fold
from .ux_polish import overline


class HardwareLedgerTab(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.component_data={}
        v=QVBoxLayout(self)
        title=overline('Hardware & Software Ledger','imported sources, C port and parts');v.addWidget(title)
        label=QLabel('Workbench R10.12 + your cumulative Hardware P1–P11 handoff');v.addWidget(label)
        self.summary=QLabel();self.summary.setObjectName('simBanner');self.summary.setWordWrap(True);v.addWidget(self.summary)
        row=QHBoxLayout()
        for label,cb in [('Development lab',window.show_development),('Verify source links',self.refresh),('Run C port checks',lambda:window.run_ledger('parity')),
                         ('Open JS reference',lambda:window.run_ledger('reference'))]:
            b=QPushButton(label);b.clicked.connect(cb);row.addWidget(b)
        fold(row,keep=('Verify source links','Run C port checks'))
        v.addLayout(row)
        self.status=QTreeWidget();self.status.setRootIsDecorated(False)
        self.status.setHeaderLabels(['Imported work','Source state','Files','Evidence scope'])
        self.status.setColumnWidth(0,255);self.status.setColumnWidth(1,135);self.status.setColumnWidth(2,55)
        self.status.header().setSectionResizeMode(3,QHeaderView.Stretch);self.status.setMaximumHeight(190)
        self.status.itemActivated.connect(lambda item,_=0:window.open_document(window.root/item.data(0,Qt.UserRole)))
        v.addWidget(self.status)
        self.result=QLabel('Host C checks have not run in this session. Original game and C bootstrap are separate.')
        self.result.setWordWrap(True);v.addWidget(self.result)
        row=QHBoxLayout()
        for label,path in [('C port source',hardware_import.P11+'port/struthio_core.c'),
                           ('Port status',hardware_import.P11+'STRUTHIO_PORT_STATUS.json'),
                           ('Import guide','docs/WORKSHOP.md')]:
            b=QPushButton(label);b.clicked.connect(lambda _=False,p=path:window.open_document(window.root/p));row.addWidget(b)
        fold(row,groups=[('Open document',('C port source','Port status','Import guide'))]);row.addStretch()
        v.addLayout(row)
        self.find=QLineEdit();writing_prompt(self.find, 'Find a component: reference, value, footprint or sheet');v.addWidget(self.find)
        self.parts=QTreeWidget();self.parts.setRootIsDecorated(False)
        self.parts.setHeaderLabels(['Ref','Value','Schematic sheet','Footprint'])
        self.parts.setColumnWidth(0,65);self.parts.setColumnWidth(1,180);self.parts.setColumnWidth(2,140)
        self.parts.header().setSectionResizeMode(3,QHeaderView.Stretch);v.addWidget(self.parts,1)
        self.find.textChanged.connect(self.filter_parts)
        self.parts.itemActivated.connect(lambda *_:self.open_part(False))
        row=QHBoxLayout()
        for label,cb in [('Open selected schematic',lambda:self.open_part(False)),
                         ('Locate on PCB',lambda:self.open_part(True)),
                         ('Firmware targets',lambda:window.open_document(window.root/(hardware_import.BASE+'closure_p9/P9_FIRMWARE_TARGETS.json'))),
                         ('Link inventory',lambda:window.open_document(window.root/(hardware_import.BASE+'closure_p10/P10_INTERCONNECT_INVENTORY.json')))]:
            b=QPushButton(label);b.clicked.connect(cb);row.addWidget(b)
        fold(row,keep=('Open selected schematic','Locate on PCB'))
        v.addLayout(row)
        note=QLabel('Source match ≠ electrical signoff. C checks cover a partial host port. Fabrication HOLD · physical programming unavailable.')
        note.setWordWrap(True);v.addWidget(note);self.refresh()

    def title(self):return 'Hardware & Software Ledger'
    def info(self):return 'P1–P11 source evidence · checked component links · partial STRUTHIO C port · fabrication HOLD'
    def refresh(self):
        self.status.clear();self.parts.clear();self.component_data={}
        try:
            data=hardware_import.inspect(self.window.root)
            self.summary.setText(f"{data['components']} components · {data['firmware_targets']} firmware targets · {data['links']} interconnects · {data['reference_files']} original game files\n"
                                 + ('All imported source checks match.' if data['all_sources_match'] else
                                    'Imported files were changed only by recorded passes (SUPERSEDED rows); no unrecorded change.' if data['all_sources_current'] else
                                    'Source changes detected. Inspect mismatches before using cached evidence.'))
            for r in data['rows']:
                item=QTreeWidgetItem([r['title'],r['state'],str(r['checked']),r['evidence']])
                item.setData(0,Qt.UserRole,r['path'])
                item.setToolTip(1,'\n'.join(r['mismatches']+[x['path']+' · recorded by '+x['by'] for x in r.get('superseded',[])])
                                or 'SHA-256 source match; not an engineering approval')
                self.status.addTopLevelItem(item)
            self.component_data=hardware_import.components(self.window.root)
            self.filter_parts()
        except (OSError,ValueError,KeyError,TypeError) as exc:
            self.summary.setText('Import unavailable: '+str(exc))

    def filter_parts(self):
        self.parts.clear();needle=self.find.text().casefold()
        for ref,part in sorted(self.component_data.items()):
            values=[ref,str(part.get('value','')),str(part.get('sheet','')),str(part.get('footprint',''))]
            if needle and needle not in ' '.join(values).casefold():continue
            item=QTreeWidgetItem(values);item.setData(0,Qt.UserRole,ref)
            item.setToolTip(1,str(part.get('evidence','')));self.parts.addTopLevelItem(item)
        if self.parts.topLevelItemCount():self.parts.setCurrentItem(self.parts.topLevelItem(0))

    def open_part(self,pcb):
        item=self.parts.currentItem()
        if item is None:return
        try:
            # Revalidate at click time; do not use stale cached pin/board relationships.
            ref=item.data(0,Qt.UserRole);part=hardware_import.components(self.window.root)[ref]
            rel=hardware_import.BASE+'cad/'+('ARC1_R10.kicad_pcb' if pcb else part['sheetfile'])
            path=hardware_import.project_path(self.window.root,rel)
            tab=self.window.open_document(path)
            if tab is not None and hasattr(tab,'component_find'):
                from PySide6.QtCore import QTimer
                def locate():
                    tab.component_find.setCurrentText(ref);tab.locate_component()
                QTimer.singleShot(0,locate)
        except (OSError,ValueError,KeyError) as exc:self.window.message('Source link unavailable',str(exc),error=True)
