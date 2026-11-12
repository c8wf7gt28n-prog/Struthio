"""A return thread, live desk inventory and an honest review before leaving."""
from __future__ import annotations
from PySide6.QtCore import QObject,Qt,QTimer
from PySide6.QtGui import QAction,QKeySequence
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QScrollArea,
    QPlainTextEdit,QTreeWidget,QTreeWidgetItem,QDialog,QMessageBox)
from .engineering_kernel import operator
from .settings_qt import action,STYLE
from .text_prompts import writing_prompt
from . import engine,return_thread


def words(text=''):
    value=QLabel(text);value.setTextFormat(Qt.PlainText);value.setWordWrap(True);value.setMinimumWidth(0);return value


class ReturnController(QObject):
    def __init__(self,host):
        super().__init__(host);self.host=host;self.saved=return_thread.empty();self.note='';self.error='';self.load_error=None
        self.skip_keep_once=False;self.busy=False
        response=self.call('ledger.session.read',{})
        if response['ok']:
            self.saved=response['result'];self.note=self.saved['note']
            restored={row['id']:dict(text=row['text'],title=row['title']) for row in self.saved['drafts']}
            restored.update(getattr(host.ledger_bridge,'cabinet_drafts',{}))
            host.ledger_bridge.cabinet_drafts=restored
        else:self.load_error=response['error']['message'];self.error=self.load_error
        tail=host.ledger_bridge.tail
        self.footer=action('Return thread',self.show);self.footer.setAccessibleName('Review unfinished work and the return thread')
        tail.layout().itemAt(0).layout().insertWidget(1,self.footer)
        self.timer=QTimer(self);self.timer.setInterval(2000);self.timer.timeout.connect(self.refresh_footer);self.timer.start()
        self.a_return=QAction('Return thread…',host);self.a_return.setShortcut(QKeySequence('Ctrl+Alt+R'))
        self.a_return.triggered.connect(self.show);host.addAction(self.a_return)
        self.refresh_footer()

    def call(self,op,args):return self.host.ledger_bridge.kernel.dispatch(op,args,operator())

    def inventory(self):
        from .qt_app import CodeEditor
        views=[];edited=[]
        for index in range(self.host.tabs.count()):
            tab=self.host.tabs.widget(index)
            if isinstance(tab,CodeEditor):
                dirty=tab.document().isModified();status='File changes' if dirty else 'No buffer edits'
                if dirty:edited.append(tab)
                if tab.isReadOnly():status+=' · read-only'
            else:status='Use this workspace’s own save controls'
            views.append(dict(key=str(id(tab)),title=self.host.tabs.tabText(index),status=status))
        drafts=getattr(self.host.ledger_bridge,'cabinet_drafts',{})
        return dict(views=views[:100],views_partial=len(views)>100,edited=edited,drafts=drafts)

    def refresh_footer(self):
        if self.host._closing:return
        inventory=self.inventory();count=len(inventory['edited'])+len(inventory['drafts'])
        self.footer.setText('Return thread'+(' · '+str(count) if count else ''))
        self.footer.setToolTip(str(len(inventory['edited']))+' edited files · '+str(len(inventory['drafts']))+
            ' cabinet drafts. Review what is still on the desk and what the return copy covers.'+('\n'+self.error if self.error else ''))

    def payload(self):
        for index in range(self.host.tabs.count()):
            tab=self.host.tabs.widget(index)
            if hasattr(tab,'save_draft') and type(tab).__name__=='CabinetRecordTab':tab.save_draft()
        drafts=[dict(id=ident,title=row.get('title',''),text=row.get('text',''))
                for ident,row in getattr(self.host.ledger_bridge,'cabinet_drafts',{}).items()]
        from .explore_qt import selected_record
        return dict(note=self.note,drafts=drafts,context=selected_record(self.host))

    def capture(self,for_exit=False,expected_revision=None):
        if self.busy:return False
        self.busy=True
        try:
            if self.load_error:raise ValueError(self.load_error)
            payload=self.payload()
            # Validate the complete writing before any return-copy update.
            return_thread.clean(**payload)
            for ed in self.inventory()['edited']:
                if ed.isReadOnly():raise ValueError('A read-only edited buffer needs its own save/recovery review before keeping a return copy.')
                self.host.recovery.put(engine.rel(ed.path,self.host.root),ed.toPlainText(),getattr(ed,'disk_sha256',None))
                ed.recovery_owned=not for_exit
            args=dict(expected_revision=self.saved['revision'] if expected_revision is None else expected_revision,
                      note=payload['note'],drafts=payload['drafts'])
            if payload['context']:args['context']=payload['context']
            response=self.call('ledger.session.keep',args)
            if not response['ok']:raise ValueError(response['error']['message'])
            self.saved={key:value for key,value in response['result'].items() if key!='changed'};self.error=''
            self.refresh_footer();return True
        except (ValueError,OSError) as exc:
            self.error=str(exc);self.host.statusBar().showMessage('Return copy not updated: '+self.error,10000)
            self.refresh_footer();return False
        finally:self.busy=False

    def show(self):
        tab=self.host.ledger_bridge.add_tab(ReturnTab,lambda:ReturnTab(self));tab.refresh();return tab

    def activity(self):
        response=self.call('ledger.operations',{})
        if not response['ok']:return 'Activity unavailable. Work may still be active.'
        value=response['result'];agenda=value['agenda']
        return (str(len(agenda['now']))+' active · '+str(len(agenda['next']))+' queued · '+str(len(agenda['waiting']))+
                ' waiting in the work records. Live processes may differ from their recorded states.')

    def close_policy(self):
        attached=getattr(self.host.ledger_bridge.kernel,'is_host_client',False)
        return ('This window’s file-save prompts still apply. '+
            ('The attached host can keep working after this window closes. ' if attached else
             'Closing requests its local model to stop and runs this window’s tool shutdown steps. ')+
            'Separately hosted work can continue. Master Stop is the separate control for owned-work cancellation. Linux stays on.')

    def exit_dialog(self):
        inventory=self.inventory();dialog=QDialog(self.host);dialog.setObjectName('ReturnExitReview')
        from .shell2 import scale_of
        # V-20: dialog words on the desk's chrome scale (16 px at the default size), not the reading size.
        dialog.setWindowTitle('Leave Graphite?');dialog.resize(660,460);dialog.setStyleSheet(STYLE+'QLabel {font-size:%dpx;}'%max(10,round(16*scale_of(self.host))))
        box=QVBoxLayout(dialog);box.setContentsMargins(24,22,24,22);box.setSpacing(14)
        title=words('Leave a thread for your return.');title.setProperty('arcReadingRole','heading');box.addWidget(title)
        box.addWidget(words('Files with edits: '+str(len(inventory['edited']))+' · Cabinet drafts: '+str(len(inventory['drafts']))))
        box.addWidget(words(self.activity()));box.addWidget(words(self.close_policy()))
        box.addWidget(words('Keep and close stores your thread and cabinet drafts as return copies. File Save prompts still decide file writes. Other forms use their own save controls.'))
        if self.error:box.addWidget(words('Last keep attempt: '+self.error))
        box.addStretch()
        # V-20: the three actions are words in a row at their own width, so the focus rule and the hit area match the word.
        from .theme2 import as_words
        row=QHBoxLayout();box.addLayout(row)
        keep=action('Keep and close Graphite',lambda:dialog.done(1));row.addWidget(keep)
        skip=action('Close without a new return copy',lambda:dialog.done(2));row.addWidget(skip)
        skip.setToolTip('Retain the earlier stored return copy. Current thread/cabinet changes may be lost. Existing file save prompts still apply.')
        back=action('Continue working',dialog.reject);row.addWidget(back);row.addStretch(1);back.setFocus(Qt.OtherFocusReason)
        for button in (keep,skip,back):as_words(button)
        dialog.keep_button=keep;dialog.skip_button=skip;dialog.back_button=back
        return dialog

    def review_exit(self):
        answer=self.exit_dialog().exec()
        if answer not in (1,2):return False
        self.skip_keep_once=answer==2
        try:return self.host.close()
        finally:self.skip_keep_once=False


class ReturnTab(QWidget):
    def __init__(self,controller):
        super().__init__();self.controller=controller;self.host=controller.host;self.setProperty('ledgerRoom',True)
        self.setProperty('paperFunctionalInk',True);self.setObjectName('ReturnThread');self.setStyleSheet(STYLE+'''
        QPlainTextEdit#ReturnWriting {background:#f8edc9;color:#504d46;border:0;border-radius:0;padding:10px;selection-background-color:#ecd7d5;selection-color:#504d46;}
        QPlainTextEdit#ReturnWriting:focus {border-bottom:2px solid #504d46;}
        QPlainTextEdit#ReturnRead {background:transparent;color:#504d46;border:0;}
        QTreeWidget {background:transparent;color:#504d46;border:0;}
        QTreeWidget::item {padding:5px 2px;}
        QTreeWidget::item:selected {background:#f3e3e2;}
        ''')
        outer=QVBoxLayout(self);scroll=self.scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.NoFrame);outer.addWidget(scroll)
        page=QWidget();scroll.setWidget(page);box=QVBoxLayout(page);box.setContentsMargins(22,18,22,18);box.setSpacing(12)
        box.addWidget(words('SESSION / RETURN THREAD'))
        heading=words('Leave the next thought within reach.');heading.setProperty('arcReadingRole','heading');box.addWidget(heading)
        self.state=words();box.addWidget(self.state)
        box.addWidget(words('Next time, begin here'))
        self.writing=QPlainTextEdit();self.writing.setObjectName('ReturnWriting');self.writing.setMaximumHeight(130)
        self.writing.setProperty('arcReadingRole','prose')  # the thread is prose (V-03)
        self.writing.setAccessibleName('Your return thread');writing_prompt(self.writing,'Your return thread');self.writing.setPlainText(controller.note)
        self.writing.textChanged.connect(self.changed);box.addWidget(self.writing)
        from .writing_marker import attach
        attach(self.host,self.writing)  # opts into the margin marker (VS03)
        row=QHBoxLayout();self.keep_button=action('Keep for return',self.keep);row.addWidget(self.keep_button)
        row.addWidget(action('Inspect stored copy',self.inspect));row.addWidget(action('Review leaving…',controller.review_exit));row.addStretch();box.addLayout(row)
        box.addWidget(words('Keeps this thread, cabinet writing and code recovery copies. Save/Keep in each workspace still saves its actual records. Other forms use their own save controls.'))
        box.addWidget(words('STILL ON THE DESK'))
        self.views=QTreeWidget();self.views.setRootIsDecorated(False);self.views.setHeaderLabels(['Work','Current buffer / workspace'])
        self.views.setAccessibleName('Open work in this desktop');self.views.setMinimumHeight(100);self.views.setMaximumHeight(180);box.addWidget(self.views)
        self.views.itemActivated.connect(lambda *_:self.open_view());box.addWidget(action('Go to selected work',self.open_view),0,Qt.AlignLeft)
        box.addWidget(words('CABINET WRITING TO CONTINUE'))
        self.drafts=QTreeWidget();self.drafts.setRootIsDecorated(False);self.drafts.setHeaderLabels(['Writing','Recovery status'])
        self.drafts.setAccessibleName('Cabinet writing retained in this desktop');self.drafts.setMinimumHeight(80);self.drafts.setMaximumHeight(150);box.addWidget(self.drafts)
        row=QHBoxLayout();row.addWidget(action('Review selected writing',self.review_draft));row.addWidget(action('Open its cabinet record',self.open_draft));row.addStretch();box.addLayout(row)
        box.addWidget(words('RECORDED ACTIVITY'))
        self.activity_note=words();box.addWidget(self.activity_note)
        self.note=words();box.addWidget(self.note)
        self.inspected=None;self.replace_button=action('Replace inspected return copy…',self.replace_inspected)
        self.replace_button.hide();box.addWidget(self.replace_button,0,Qt.AlignLeft)
        self.detail=QPlainTextEdit();self.detail.setObjectName('ReturnRead');self.detail.setReadOnly(True);self.detail.setMaximumHeight(230);self.detail.hide();box.addWidget(self.detail)
        box.addStretch();self.refresh()
        self.timer=QTimer(self);self.timer.setInterval(2500);self.timer.timeout.connect(self.refresh)

    def title(self):return 'Return thread'

    def changed(self):self.controller.note=self.writing.toPlainText();self.controller.refresh_footer()

    def showEvent(self,event):super().showEvent(event);self.timer.start()
    def hideEvent(self,event):self.timer.stop();super().hideEvent(event)

    def keep(self):
        if self.controller.capture():self.note.setText('Return copy kept. Project records and source files were not overwritten.')
        else:self.note.setText('Return copy not updated: '+self.controller.error)
        self.refresh()

    def refresh(self):
        if self.host._closing:return
        inventory=self.controller.inventory();saved=self.controller.saved
        same_note=self.writing.toPlainText()==saved['note']
        self.state.setText(('Stored return copy · revision '+str(saved['revision']) if saved['revision'] else 'No stored return copy yet')+
                           (' · thread has changes' if not same_note else '')+
                           ('\n'+self.controller.error if self.controller.error else ''))
        selected=self.views.currentItem();key=selected.data(0,Qt.UserRole) if selected else None;self.views.clear()
        for row in inventory['views']:
            item=QTreeWidgetItem([row['title'],row['status']]);item.setData(0,Qt.UserRole,row['key']);self.views.addTopLevelItem(item)
            if row['key']==key:self.views.setCurrentItem(item)
        self.views.setColumnWidth(0,250)
        old=self.drafts.currentItem();selected=old.data(0,Qt.UserRole) if old else None;self.drafts.clear()
        kept={row['id']:row for row in saved['drafts']}
        cabinet=self.controller.call('ledger.cabinet',{'limit':1000}) if inventory['drafts'] else None
        labels={row['id']:row['label'] for row in cabinet['result']['nodes']} if cabinet and cabinet['ok'] else {}
        for ident,row in sorted(inventory['drafts'].items()):
            unchanged=ident in kept and all(row.get(k,'')==kept[ident][k] for k in ('title','text'))
            item=QTreeWidgetItem([row.get('title') or labels.get(ident,'Unavailable cabinet record'), 'In stored return copy' if unchanged else 'Current desktop · keep needed'])
            item.setData(0,Qt.UserRole,ident);item.setToolTip(0,ident);self.drafts.addTopLevelItem(item)
            if ident==selected:self.drafts.setCurrentItem(item)
        if not self.drafts.currentItem() and self.drafts.topLevelItemCount():self.drafts.setCurrentItem(self.drafts.topLevelItem(0))
        self.drafts.setColumnWidth(0,320);self.activity_note.setText(self.controller.activity())
        if inventory['views_partial']:self.note.setText('The open-work list is bounded at 100 entries; the existing tabs remain available.')

    def open_view(self):
        item=self.views.currentItem()
        if item is None:return
        for index in range(self.host.tabs.count()):
            tab=self.host.tabs.widget(index)
            if str(id(tab))==item.data(0,Qt.UserRole):self.host.tabs.setCurrentWidget(tab);return
        self.note.setText('That workspace has closed; refresh the list.')

    def review_draft(self):
        item=self.drafts.currentItem()
        if item is None:return
        row=getattr(self.host.ledger_bridge,'cabinet_drafts',{}).get(item.data(0,Qt.UserRole))
        if row is None:self.note.setText('That writing has changed; refresh the list.');return
        self.detail.setPlainText((row.get('title','')+'\n\n'+row.get('text','')).strip());self.detail.show()
        self.note.setText('Recovery writing only. Its cabinet record may have changed since the copy was kept.')

    def open_draft(self):
        item=self.drafts.currentItem()
        if item is None:return
        room=self.host.cabinet_page.open(item.data(0,Qt.UserRole))
        if room is None:
            self.host.tabs.setCurrentWidget(self);self.review_draft();self.note.setText('Record unavailable. Your recovery writing remains here for review and copying.')

    def inspect(self):
        result=self.controller.call('ledger.session.read',{})
        if not result['ok']:
            self.inspected=None;self.replace_button.hide();self.note.setText(result['error']['message']);return
        self.inspected=result['result']
        lines=['STORED RETURN COPY · revision '+str(self.inspected['revision']),
               '', 'RETURN THREAD',self.inspected['note'] or '(No return note.)']
        for index,row in enumerate(self.inspected['drafts'],1):
            lines.extend(['','CABINET WRITING '+str(index)+((' · '+row['title']) if row['title'] else ''),row['text']])
        self.detail.setPlainText('\n'.join(lines));self.detail.show()
        self.replace_button.setVisible(self.inspected['revision']!=self.controller.saved['revision'])
        self.note.setText('Current stored copy, read without replacing this desktop’s writing or retained revision.')
        QTimer.singleShot(0,lambda:self.scroll.ensureWidgetVisible(self.detail))

    def replace_inspected(self):
        if self.inspected is None:return
        revision=self.inspected['revision']
        answer=QMessageBox.question(self,'Replace the inspected return copy?',
            'Keep this desktop’s thread and cabinet drafts in place of the stored return copy you inspected (revision '+str(revision)+')?\n\n'
            'Project records and original files are unaffected. A further change in another session will still block replacement.',
            QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if answer!=QMessageBox.Yes:return
        if self.controller.capture(expected_revision=revision):
            self.detail.hide();self.replace_button.hide();self.inspected=None
            self.note.setText('This desktop’s return copy kept after replacing the inspected revision.')
        else:self.note.setText('Return copy not updated: '+self.controller.error)
        self.refresh()


def install(host):
    controller=ReturnController(host);host.return_thread=controller;return controller
