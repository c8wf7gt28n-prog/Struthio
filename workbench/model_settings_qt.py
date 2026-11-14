"""The same saved/requested/worker model readback inside shared Settings."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel
from .settings_qt import action
from .engineering_kernel import operator
from . import model_settings,local_brain


def describe(value):
    if not value:return 'Not recorded'
    def word(key):
        value_=value.get(key)
        return 'not recorded' if value_ is None else 'Auto (0)' if key=='memory_mb' and value_==0 else str(value_)
    text=word('context')+' tokens · '+word('threads')+' CPU threads · '+word('memory_mb')+' MiB · '+word('backend')
    if value.get('requested_backend') and value['requested_backend']!=value.get('backend'):text+=' (requested '+value['requested_backend']+')'
    if value.get('observed_gpu_layers') is not None:text+=' · '+str(value['observed_gpu_layers'])+' GPU layers observed'
    if value.get('fallback_reason'):text+='\n'+value['fallback_reason']
    return text


class ModelPanel(QWidget):
    def __init__(self,bridge,report):
        super().__init__();self.bridge=bridge;self.report=report;self.data=None;self.setProperty('paperFunctionalInk',True)
        box=QVBoxLayout(self);box.setContentsMargins(0,4,0,4);box.setSpacing(8)
        heading=QLabel('LOCAL MODEL · SAVED / REQUESTED / RUNNING');heading.setTextFormat(Qt.PlainText);heading.setWordWrap(True);box.addWidget(heading)
        self.summary=QLabel();self.summary.setTextFormat(Qt.PlainText);self.summary.setWordWrap(True);self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse);box.addWidget(self.summary)
        row=QHBoxLayout();self.reload=action('Reload saved defaults',lambda:self.launch('brain.model.use'))
        self.restore=action('Restore previous model',lambda:self.launch('brain.restore'))
        for button in (self.reload,self.restore):row.addWidget(button)
        row.addStretch();box.addLayout(row)
        box.addWidget(action('Open model controls',self.open_controls),0,Qt.AlignLeft)
        self.reload.setToolTip('Start the original owner-approved model handover with these saved defaults. Existing model checks and running-reply protection apply.')
        self.restore.setToolTip('Use the existing restore operation and its recorded previous configuration. Undo above changes only a saved default.')

    def bind(self,value):
        self.data=value
        if not value:
            self.summary.setText('Local-model state is unavailable. Existing data has not been replaced.')
            self.reload.setEnabled(False);self.restore.setEnabled(False);return
        lines=['Saved launch defaults: '+describe(value['saved_defaults'])]
        selected=value['selection'];previous=value['previous'];pending=value['pending']
        lines.append('Last recorded selection: '+(selected['model_id'][:12]+' · '+describe(selected['config']) if selected else 'None recorded for this caller'))
        for row in pending[:3]:
            lines.append(('Requested load' if row['tool']=='brain.activate' else 'Requested qualification')+': '+row['state']+' · '+describe(row['options'])+
                         (' · frozen at submission' if row['frozen'] else ' · legacy request options only'))
        lines.append('Running worker: '+(describe(value['worker_config']) if value['worker_config'] else 'Not observed · '+value['state'].replace('_',' ').lower()))
        if value['restored_after_job']:lines.append('Previous worker restored after request '+value['restored_after_job'][:12]+'; its owned process is read back.')
        last=value['last_operation']
        if last and last['state'] not in ('Queued','Running'):lines.append('Last model request: '+last['state']+' · inspect the existing job for its result.')
        if previous:lines.append('Restore target: '+previous['model_id'][:12]+' · '+describe(previous['config']))
        if value['recent_jobs_partial']:lines.append('Some recent request metadata is unavailable within this bounded view.')
        self.summary.setText('\n'.join(lines))
        self.reload.setEnabled(bool(selected and not pending and value['state']!='OTHER_OWNER_WORKER'))
        self.restore.setEnabled(bool(previous and previous['config'] and not pending and value['state']!='OTHER_OWNER_WORKER'))

    def open_controls(self):
        with self.bridge.retained_views():return self.bridge.show_brain()

    def launch(self,operation):
        try:
            live=model_settings.snapshot(self.bridge.kernel,operator().identity)
            if not self.data or live['revision']!=self.data['revision']:
                self.bind(live);raise ValueError('Saved defaults or model state changed. Review the current values and choose again.')
            if live['pending']:raise ValueError('Finish or stop the current model request in the existing model controls.')
            args={}
            if operation=='brain.model.use':
                if not live['selection']:raise ValueError('Register and choose a model in the existing model controls first.')
                ident=live['selection']['model_id'];options={k:v for k,v in live['saved_defaults'].items() if k!='memory_mb' or v}
                from .resource_control import reclaimable,reserve_setting
                config=local_brain.configuration(local_brain.model(self.bridge.kernel,ident),options,self.bridge.kernel.root,reclaimable(self.bridge.kernel),reserve_setting(self.bridge.kernel))
                args=dict(id=ident,options={**options,**{k:config[k] for k in ('context','threads','memory_mb')}})
            elif not live['previous']:raise ValueError('No previous model configuration is recorded.')
            tab=self.open_controls();tab.launch(operation,args)
        except (ValueError,OSError) as exc:self.report(str(exc))
