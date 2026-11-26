"""Ledger's Brain panel: inspect, qualify, activate and restore external GGUFs."""
from .assistant_identity import named
import json
from pathlib import Path
from PySide6.QtCore import QTimer, QUrl, QSignalBlocker
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QGridLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox, QPlainTextEdit, QTabWidget, QFileDialog, QProgressBar
from .register_tabs import ServiceTab
from . import brain_seal, local_brain
from . import turns  # 0.8.7 A3: the owner's switches per kind
from .explore_qt import BRAIN_WORDS  # one vocabulary for the model state: Hatch, Explore and this room say the same words (V-19)

class BrainTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.job=None;self._models=[];self._selected_id=None;self.setAcceptDrops(True)
        self._launch_loading=False;self._launch_dirty=set();self._launch_saved={}
        heading=QLabel('GRAPHITE · BRAIN');heading.setStyleSheet('font-size:18px;color:#edaa69;font-weight:bold');self.outer.addWidget(heading)
        self.note=QLabel('Drop a GGUF file or complete model folder. Weights stay outside the program ZIP. Inspection starts no inference.');self.note.setWordWrap(True);self.outer.addWidget(self.note)
        self.outer.addWidget(self.status)
        # 0.8.7, the sealed room: the seal in words under the model's state, how she knows (each check made at start),
        # and, when the Radeon could not be sealed, the sealed processor one press away (open question 4's default).
        seal_row=QHBoxLayout();seal_row.setSpacing(18)
        self.seal_line=QLabel('');self.seal_line.setWordWrap(True);self.seal_line.setAccessibleName('How the model is sealed')
        self.seal_how=QPushButton('How I know');self.seal_how.setCheckable(True);self.seal_how.setAccessibleName('How I know the model is sealed')
        self.seal_processor=QPushButton(brain_seal.PROCESSOR_SEALED);self.seal_processor.setAccessibleName(brain_seal.PROCESSOR_SEALED)
        self.seal_processor.clicked.connect(self.use_processor_sealed)
        seal_row.addWidget(self.seal_line,1);seal_row.addWidget(self.seal_how);seal_row.addWidget(self.seal_processor)
        self.outer.addLayout(seal_row)
        self.seal_fold=QLabel('');self.seal_fold.setWordWrap(True);self.seal_fold.setVisible(False);self.seal_fold.setAccessibleName('Seal checks')
        self.seal_how.toggled.connect(self.seal_fold.setVisible);self.outer.addWidget(self.seal_fold)
        self.seal_how.setVisible(False);self.seal_processor.setVisible(False)
        self.list=QComboBox();self.list.setAccessibleName('Registered local models');self.list.currentIndexChanged.connect(self.selected);self.outer.addWidget(self.list)
        # V-19: the actions are words in two rows at their natural width (theme2.as_words), not a slab of full-width bars.
        words=[('Add file',self.add_file),('Add folder',self.add_folder),('Inspect',self.inspect),('Locate',self.locate),('Qualify',self.qualify),
               ('Use model',self.use),('Restore previous',self.restore),('Stop brain',self.stop),(named('Ask Stacy'),host.open_clip)]
        self.action_rows=[]
        for group in (words[:5],words[5:]):
            row=QHBoxLayout();row.setSpacing(18)
            for label,fn in group:
                button=QPushButton(label);button.setAccessibleName(label);button.clicked.connect(fn);row.addWidget(button)
            row.addStretch(1);self.outer.addLayout(row);self.action_rows.append(row)
        control_content=QWidget();controls=QVBoxLayout(control_content);controls.setContentsMargins(6,6,6,6)
        self.launch_scroll=QScrollArea();self.launch_scroll.setWidgetResizable(True);self.launch_scroll.setWidget(control_content)
        row=QHBoxLayout();trials=QPushButton('Run answer, line, exact-edit and clarification trials');trials.clicked.connect(self.task_trials);row.addWidget(trials);row.addStretch(1);controls.addLayout(row)
        self.copy=QCheckBox('Copy into Graphite’s model store');self.copy.setToolTip('Copies stay outside the program ZIP. Otherwise Graphite references the selected files in their original location.');controls.addWidget(self.copy)
        options=QGridLayout();self.context=QSpinBox();self.context.setRange(512,8192);self.context.setSingleStep(512);self.context.setValue(2048)
        self.memory=QSpinBox();self.memory.setRange(0,262144);self.memory.setSingleStep(512);self.memory.setSpecialValueText('Auto');self.memory.setValue(0)
        self.threads=QSpinBox();self.threads.setRange(1,32);self.threads.setValue(4)
        self.backend=QComboBox();self.backend.addItem('Auto · prefer Radeon','AUTO');self.backend.addItem('CPU','CPU');self.backend.addItem('Vulkan','VULKAN')
        self.backend.setAccessibleName('Requested inference backend')
        self.gpu_layers=QSpinBox();self.gpu_layers.setRange(-1,512);self.gpu_layers.setSpecialValueText('Auto fit');self.gpu_layers.setValue(-1)
        self.gpu_layers.setToolTip('Auto fits layers to the Vulkan device budget. Zero disables GPU offload. The running worker reports observed layers.')
        self.cpu_fallback=QCheckBox('Allow one CPU fallback');self.cpu_fallback.setChecked(True)
        for widget in (self.context,self.memory,self.threads,self.gpu_layers):
            widget.setButtonSymbols(QSpinBox.NoButtons)
        for combo in (self.list,self.backend):combo.setMinimumContentsLength(12)
        for i,(label,widget) in enumerate([('Context tokens',self.context),('Host budget (MiB)',self.memory),('CPU threads',self.threads),
                                         ('Inference',self.backend),('GPU layers',self.gpu_layers),('On Vulkan failure',self.cpu_fallback)]):
            row,col=i%3,(i//3)*2;caption=QLabel(label);caption.setBuddy(widget);options.addWidget(caption,row,col);options.addWidget(widget,row,col+1)
            widget.setAccessibleName(label)
        controls.addLayout(options)
        self.launch_defaults_note=QLabel();self.launch_defaults_note.setWordWrap(True);controls.addWidget(self.launch_defaults_note)
        self.launch_fields={'context':self.context,'threads':self.threads,'memory_mb':self.memory,
                            'backend':self.backend,'gpu_layers':self.gpu_layers,'cpu_fallback':self.cpu_fallback}
        for key,widget in self.launch_fields.items():
            signal=widget.currentIndexChanged if isinstance(widget,QComboBox) else widget.toggled if isinstance(widget,QCheckBox) else widget.valueChanged
            signal.connect(lambda _value,key=key:self.launch_edited(key))
        defaults=QPushButton('Use saved launch defaults');defaults.clicked.connect(lambda:self.refresh_launch_defaults(force=True));controls.addWidget(defaults)
        self.defaults_button=defaults
        settings=QPushButton('Edit launch defaults in Settings');settings.clicked.connect(lambda:host.ledger_bridge.show_settings(key='brain.context'));controls.addWidget(settings)
        self.edit_defaults_button=settings
        self.refresh_launch_defaults(force=True)
        self.progress=QProgressBar();self.progress.setRange(0,1);self.progress.setValue(0);self.progress.setTextVisible(False);self.outer.addWidget(self.progress)  # an 8 px bar cannot hold '0%' (V-19)
        self.progress.setAccessibleName('Brain job progress')
        self.pages=QTabWidget();self.summary=QPlainTextEdit();self.summary.setReadOnly(True);self.metadata=QPlainTextEdit();self.metadata.setReadOnly(True);self.tensors=QPlainTextEdit();self.tensors.setReadOnly(True)
        self.summary.setMinimumHeight(160);controls.addWidget(self.summary,1)
        hardware=QWidget();hardware_layout=QVBoxLayout(hardware);hardware_layout.setContentsMargins(6,6,6,6)
        self.probe_button=QPushButton('Inspect Vulkan devices · no model load');self.probe_button.clicked.connect(self.probe_acceleration);hardware_layout.addWidget(self.probe_button)
        self.acceleration_launch=QLabel();self.acceleration_launch.setWordWrap(True);hardware_layout.addWidget(self.acceleration_launch)
        self.acceleration=QPlainTextEdit();self.acceleration.setReadOnly(True);hardware_layout.addWidget(self.acceleration,1)
        self.hardware_page=hardware
        for title,widget in [('Model / launch',self.launch_scroll),('Hardware / Vulkan',hardware),('GGUF metadata',self.metadata),('Tensor inspector',self.tensors)]:self.pages.addTab(widget,title)
        from . import model_check_qt  # 0.8.7 A5: "Check her model on this machine" (one button), the exam card and the measured settings
        self.model_check=model_check_qt.CheckPanel(self);self.pages.addTab(self.model_check,'Check her model')
        from . import quick_model_qt  # 1.0 M2: a quick model beside hers: which model answers which kind and why, one Undo
        self.quick_model=quick_model_qt.QuickPanel(self);self.pages.addTab(self.quick_model,quick_model_qt.TITLE)
        # 0.8.7 A3: what the model may do, a switch per kind of question; with every switch off Kas is exactly 0.8.6.
        self.help_page=QWidget();help_layout=QVBoxLayout(self.help_page);help_layout.setContentsMargins(6,6,6,6)
        intro=QLabel('Which questions Kas may put to the model on this computer. Off means she answers as she does with no model.')
        intro.setWordWrap(True);help_layout.addWidget(intro);self.help_boxes={}
        for name in ('understanding','reading','wording','choosing','talk'):
            box=QCheckBox(turns.SWITCH_WORDS[name]);box.setAccessibleName(turns.SWITCH_WORDS[name])
            box.toggled.connect(lambda on,name=name:self.help_set({name:bool(on)}));help_layout.addWidget(box);self.help_boxes[name]=box
        row=QHBoxLayout();self.help_undo=QPushButton('Undo');self.help_undo.setAccessibleName('Undo the last switch')
        self.help_undo.clicked.connect(lambda:self.help_set(None,undo=True));row.addWidget(self.help_undo);row.addStretch(1);help_layout.addLayout(row)
        self.help_note=QLabel('');self.help_note.setWordWrap(True);self.help_note.setAccessibleName('What the model may do');help_layout.addWidget(self.help_note)
        self.account_area(help_layout)   # 0.8.7 A4: what the model did for you, and its turns, each with its fold
        help_layout.addStretch(1);self.pages.addTab(self.help_page,'What the model may do')
        self.show_help(turns.stored_switches(self.kernel));self.show_account()
        self.outer.addWidget(self.pages,1)
        self.launch_edited('context')
        self.show_acceleration(local_brain.acceleration(self.kernel))
        self.timer=QTimer(self);self.timer.setInterval(1000);self.timer.timeout.connect(self.refresh);self.timer.start();self.refresh()
    def show_help(self,switches):
        for name,box in self.help_boxes.items():
            with QSignalBlocker(box):box.setChecked(bool(switches.get(name)))
        off=[turns.SWITCH_WORDS[name] for name in self.help_boxes if not switches.get(name)]
        if not any(switches.get(name) for name in self.help_boxes):text='Every switch is off: Kas answers exactly as she does with no model.'
        elif off:text='Off: '+', '.join(off)+'. The rest are on.'
        else:text='Every switch is on.'
        self.help_note.setText(text)
    # ---- 0.8.7 A4: the account (model_account) and the ledger, each turn with its fold (model_marks_qt) ----------------------
    def account_area(self,layout):
        from PySide6.QtWidgets import QListWidget
        from . import model_account
        head=QLabel('What the model did for you');head.setStyleSheet('font-weight:600;');layout.addWidget(head)
        self.account_words=QLabel('');self.account_words.setWordWrap(True);self.account_words.setAccessibleName('What the model did for you')
        layout.addWidget(self.account_words)
        self.account_row=QHBoxLayout();self.account_count=QPushButton(model_account.BUTTONS['count'])
        self.account_count.clicked.connect(self.show_account);self.account_row.addWidget(self.account_count);self.account_row.addStretch(1)
        layout.addLayout(self.account_row);self.account_again=[]
        self.turn_list=QListWidget();self.turn_list.setAccessibleName('The questions she put to the model');self.turn_list.setMaximumHeight(140)
        self.turn_list.currentRowChanged.connect(self.show_turn);layout.addWidget(self.turn_list)
        self.turn_holder=QVBoxLayout();layout.addLayout(self.turn_holder);self.turn_fold=None;self.turn_ids=[]
    def show_account(self):
        from . import model_account, model_marks_qt
        got=self.kernel.dispatch('brain.account',{'period':'week'},self.principal)
        value=got.get('result') if got.get('ok') else None
        self.account_words.setText(value['text'] if value else 'The account could not be read.')
        for b in self.account_again:b.hide();b.deleteLater()
        self.account_again=[]
        for row in (value or {}).get('nulls') or ():
            b=QPushButton(model_account.BUTTONS['ask_again']);b.setToolTip(model_account.say('asked_again',thing=row['thing']))
            b.setAccessibleName(model_account.BUTTONS['ask_again']+': '+row['thing'])
            b.clicked.connect(lambda checked=False,kind=row['kind']:self.ask_again(kind));self.account_row.insertWidget(1,b);self.account_again.append(b)
        listed=self.kernel.dispatch('brain.turns',{'limit':30},self.principal)
        rows=listed['result']['turns'] if listed.get('ok') else []
        with QSignalBlocker(self.turn_list):
            self.turn_list.clear();self.turn_ids=[]
            for r in rows:
                state='forgotten' if r.get('state')=='FORGOTTEN' else model_marks_qt.OUTCOME_WORDS.get(r.get('outcome'),r.get('outcome',''))
                self.turn_list.addItem('%s · %s · %s'%(r.get('kind',''),state,model_marks_qt._seconds(r.get('elapsed_ms'))));self.turn_ids.append(r['id'])
    def ask_again(self,kind):
        got=self.kernel.dispatch('brain.help.set',{'ask_again':kind},self.principal)
        self.show_account()
        if got.get('ok'):
            from . import model_account
            self.help_note.setText(model_account.say('asked_again',thing=model_account.THINGS.get(kind,kind.lower())))
    def show_turn(self,row):
        from . import model_marks_qt
        if self.turn_fold is not None:self.turn_fold.hide();self.turn_fold.deleteLater();self.turn_fold=None
        if not 0<=row<len(self.turn_ids):return
        self.turn_fold=model_marks_qt.Fold.for_turn(self.host,self.turn_ids[row],self.kernel,self.principal)
        self.turn_holder.addWidget(self.turn_fold);self.turn_fold.toggle.setChecked(True)
    def help_set(self,changes,undo=False):
        result=self.kernel.dispatch('brain.help.set',{'undo':True} if undo else {'switches':changes},self.principal)
        if result.get('ok'):self.show_help(result['result']['switches']);return
        self.show_help(turns.stored_switches(self.kernel))
        message=(result.get('error') or {}).get('message') or ''
        self.help_note.setText('Nothing to undo yet.' if 'NOTHING_TO_UNDO' in message else 'The switch was not changed.')
    def title(self):return 'Graphite · Brain'
    def info(self):return 'Local CPU / Vulkan inference · external weights · scoped Graphite tools'
    def options(self):
        value={key:self.field_value(widget) for key,widget in self.launch_fields.items() if key!='memory_mb'}
        if self.memory.value():value['memory_mb']=self.memory.value()
        # Resolve a local Auto override explicitly, even when the saved cap is manual.
        model=local_brain.model(self.kernel,self._selected_id)
        from .resource_control import reclaimable,reserve_setting
        config=local_brain.configuration(model,value,self.kernel.root,reclaimable(self.kernel),reserve_setting(self.kernel))
        return {**value,**{key:config[key] for key in ('context','threads','memory_mb')}}

    def field_value(self,widget):
        return widget.currentData() if isinstance(widget,QComboBox) else widget.isChecked() if isinstance(widget,QCheckBox) else widget.value()

    def launch_edited(self,key):
        if self._launch_loading:return
        if self.field_value(self.launch_fields[key])==self._launch_saved.get(key):self._launch_dirty.discard(key)
        else:self._launch_dirty.add(key)
        self.launch_defaults_note.setText('Local launch overrides are preserved; Use/Qualify apply them to this request.' if self._launch_dirty else 'Following the saved launch defaults. Editing these fields creates a local request override.')
        if hasattr(self,'acceleration_launch'):
            self.acceleration_launch.setText('Next load: '+self.backend.currentText()+' · GPU layers '+self.gpu_layers.text()+
                ' · host budget '+self.memory.text()+' MiB · CPU fallback '+('allowed' if self.cpu_fallback.isChecked() else 'disabled'))

    def refresh_launch_defaults(self,force=False):
        from .model_settings import preferences
        try:saved=preferences(self.kernel)
        except (ValueError,OSError) as exc:self.launch_defaults_note.setText(str(exc));return
        self._launch_loading=True
        try:
            for key,widget in self.launch_fields.items():
                if force or key not in self._launch_dirty:
                    with QSignalBlocker(widget):
                        if isinstance(widget,QComboBox):widget.setCurrentIndex(widget.findData(saved[key]))
                        elif isinstance(widget,QCheckBox):widget.setChecked(saved[key])
                        else:widget.setValue(saved[key])
                if self.field_value(widget)==saved[key]:self._launch_dirty.discard(key)
            self._launch_saved=saved
        finally:self._launch_loading=False
        self.launch_edited('context')
    def refresh(self):
        if self.host._closing:return
        self.refresh_launch_defaults()
        response=self.kernel.dispatch('brain.status',{},self.principal)
        if not response['ok']:self.status.setText(response['error']['message']);return
        data=response['result'];worker=data.get('worker') or {}
        active=worker.get('backend','no worker running')
        if worker.get('requested_backend'):active+=' · requested '+worker['requested_backend']
        if worker.get('observed_gpu_layers') is not None:active+=' · '+str(worker['observed_gpu_layers'])+' GPU layers observed'
        if worker.get('context'):
            active+=f" · {worker['context']} context tokens"
        prepared=data.get('prepared_context')
        if prepared:
            active+=f" · {prepared['prompt_tokens']} tokens prepared"
            if prepared['observed_reused_tokens'] is not None:
                active+=f" · {prepared['observed_reused_tokens']} reused"
        if worker.get('fallback_reason'):active+=' · '+worker['fallback_reason']
        if data.get('resource_stop'):active+=' · '+data['resource_stop']
        self.status.setText(BRAIN_WORDS.get(data['state'],str(data['state']).replace('_',' ').lower())+' · '+str(data['runtime']['build'] or 'runtime unavailable')+' · '+active+' · cloud calls 0')
        self.show_seal(worker.get('seal'),data.get('seal_words'))
        if hasattr(self.host,'arc_inspector') and self.host.tabs.currentWidget() is self:self.host.arc_inspector.refresh()
        rows=local_brain.models(self.kernel);identity=[(r['id'],r.get('qualification')) for r in rows]
        if identity!=getattr(self,'_identity',None):
            current=self.list.currentData();self.list.blockSignals(True);self.list.clear()
            for model in rows:self.list.addItem(model['inspection']['metadata'].get('general.name',model['files'][0]['name']),model['id'])
            index=self.list.findData(current);self.list.setCurrentIndex(max(0,index));self.list.blockSignals(False);self._models=rows;self._identity=identity;self.selected()
        if not rows:self.summary.setPlainText('No model registered. Add a compatible GGUF file or complete folder.\n\nLinux x64 includes pinned CPU and Vulkan workers from the same llama.cpp release. You supply model weights separately. Auto prefers an accessible Radeon; device availability and measured model performance are separate. Windows CPU remains an optional runtime add-on.')
        if self.job:
            result=self.kernel.dispatch('brain.result',{'id':self.job},self.principal)
            if result['ok'] and result['result']['state'] in ('Completed','Failed','Cancelled','Interrupted'):
                outcome=result['result'];self.progress.setRange(0,1);self.progress.setValue(1 if outcome['state']=='Completed' else 0)
                said=str((outcome.get('result') or {}).get('reason',(outcome.get('result') or {}).get('status',outcome.get('error') or '')))
                if brain_seal.REFUSED+': ' in said:said=said.split(brain_seal.REFUSED+': ',1)[1]  # her one line, without the code
                self.note.setText(outcome['state']+' · '+said)
                task_receipt=(outcome.get('result') or {}).get('qualification') or {}
                if task_receipt.get('tasks'):
                    passed=sum(r['state']=='PASSED' for r in task_receipt['tasks'])
                    self.note.setText('Task trials: %d of %d passed. Open the measurements below; this is a small task profile.' % (passed,len(task_receipt['tasks'])))
                model_id=(outcome.get('result') or {}).get('model_id');self.job=None;self._identity=None
                self.refresh()
                if model_id:
                    index=self.list.findData(model_id)
                    if index>=0:self.list.setCurrentIndex(index)
    def show_seal(self,seal,said):
        """The seal under the model's state: one line in words, 'How I know' with each check made at start, and the
        sealed processor when the Radeon runs without its own network. Nothing here when no model runs."""
        self.seal_line.setText(said or '')
        self.seal_how.setVisible(bool(seal))
        if not seal:self.seal_how.setChecked(False)
        self.seal_fold.setText('\n'.join('· '+line for line in brain_seal.fold(seal)))
        self.seal_processor.setVisible(brain_seal.processor_offered(seal))

    def use_processor_sealed(self):
        """Open question 4's default: the same model on the processor, in its own network. The Inference field shows the
        change (a local override), and Use model starts it through the same checks."""
        selection=(self.kernel.dispatch('brain.status',{},self.principal).get('result') or {}).get('selection') or {}
        index=self.list.findData(selection.get('model_id'))
        if index>=0:self.list.setCurrentIndex(index)
        self.backend.setCurrentIndex(self.backend.findData('CPU'))
        self.use()

    def show_acceleration(self,data):
        host=data['host'];profile=host['hardware_profile'];probe=data.get('last_device_probe') or {}
        mib=lambda value:'not reported' if value is None else str(round(value/1024**2))+' MiB'
        lines=['CURRENT COMPUTER · observed here',
               'Machine: '+str(profile['machine'].get('product') or 'not reported'),
               'CPU: '+profile['cpu']['name'],
               'Cores: '+str(profile['cpu']['physical_cores'] or '?')+' physical / '+str(profile['cpu']['logical_cpus'] or '?')+' logical',
               'System RAM: '+mib(host['total_ram_bytes'])+' · available '+mib(host['available_ram_bytes']),
               'Kernel: '+profile['kernel'],'',profile['memory_note'],'']
        for gpu in profile['graphics']:
            lines.append('Graphics: '+str(gpu['vendor_id'])+':'+str(gpu['device_id'])+' · '+str(gpu['driver'])+' · '+('accessible' if gpu['accessible'] else 'not accessible'))
        if not profile['graphics']:lines.append('No DRM render device observed.')
        for backend,runtime in data['runtimes'].items():lines.append(backend+' worker: '+runtime['state']+' · '+str(runtime.get('build')))
        lines+=['','Device discovery: '+str(probe.get('state','not run'))]
        for device in probe.get('devices',[]):lines.append(device['id']+': '+device['name']+(' · software only' if device['software'] else ''))
        if probe.get('reason'):lines.append(probe['reason'])
        lines+=['','Installed driver / loader packages:']
        lines += [key+' '+value for key,value in profile['installed_packages'].items()]
        if profile['missing_runtime_packages']:lines.append('Debian 13 package names not installed: '+', '.join(profile['missing_runtime_packages']))
        lines+=['','Driver setup: docs/THINKPAD_VULKAN_P05.md',data['note']]
        self.acceleration.setPlainText('\n'.join(lines))

    def probe_acceleration(self):
        self.probe_button.setEnabled(False);self.pages.setCurrentWidget(self.hardware_page)
        def done(data):self.probe_button.setEnabled(True);self.show_acceleration(data)
        def failed(error):self.probe_button.setEnabled(True);self.note.setText(error.get('message','Device discovery failed'))
        self.call('brain.acceleration.probe',{},done,failed)
    def selected(self,*args):
        ident=self.list.currentData();self._selected_id=ident
        value=next((r for r in self._models if r['id']==ident),None)
        if not value:return
        info=value['inspection'];metadata=info['metadata'];qualified=value.get('qualification')
        self.summary.setPlainText(json.dumps({'model':metadata.get('general.name',info['file']),'architecture':info['architecture'],
            'role':value['role'],'parameter_count':info['parameter_count'],'bytes':value['total_bytes'],'file_set_sha256':value['id'],
            'quantization':info['quantization'],'declared_context':metadata.get(info['architecture']+'.context_length'),
            'declared_licence':value['declared_license'],'owner_recorded_origin':value['origin'],'storage':value['storage'],
            'qualification':qualified,
            'task_trials':self.kernel.dispatch('slate.qualifications',{'model_id':ident},self.principal).get('result',{}).get('records',[])[:3],
            'note':'A load/chat probe is separate from answer, plan, exact-edit and clarification trials.'},indent=2))
        self.metadata.setPlainText(json.dumps(metadata,indent=2));self.tensors.setPlainText(json.dumps({'tensor_count':info['tensor_count'],'preview_truncated':info['tensor_preview_truncated'],'tensors':info['tensor_preview']},indent=2))
    def inspect(self):self.selected()
    def locate(self):
        if self._selected_id:
            result=self.kernel.dispatch('brain.model.locate',{'id':self._selected_id},self.principal)
            if result['ok']:QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(result['result']['locations'][0]['path']).parent)))
            else:self.note.setText(result['error']['message'])
    def add_file(self):
        name,_=QFileDialog.getOpenFileName(self,'Add local model','','GGUF model (*.gguf)')
        if name:self.add_source(name)
    def add_folder(self):
        name=QFileDialog.getExistingDirectory(self,'Add complete local model folder')
        if name:self.add_source(name)
    def add_source(self,path):
        self.launch('brain.model.add',{'path':str(path),'managed_copy':self.copy.isChecked()})
    def launch(self,op,args):
        if self.job:self.note.setText('Finish or stop the current Brain job first.');return
        self._last_error=None;self.call(op,args,self.watch,failed=self.failed)
    def failed(self,error):
        self._last_error=error.get('message','Operation failed')
        advice={'MEMORY_BUDGET_EXCEEDS_AVAILABLE_HOST_RAM':'Choose Auto or a smaller memory cap; current available RAM is below this request.',
                'MODEL_MEMORY_BUDGET_TOO_SMALL':'This model/context needs more memory than this cap or Auto gives it. Free memory, raise the cap or reduce context tokens.',
                'MODEL_CHAT_TEMPLATE_MISSING':'This file has no usable chat template. Choose a compatible instruction model.'}
        # A memory refusal carries its numbers after the code: show the advice and keep the numbers.
        code,_,numbers=self._last_error.partition(': ')
        if code==brain_seal.REFUSED:
            self.note.setText(numbers);self.progress.setRange(0,1);self.progress.setValue(0);return  # her one line
        text=advice.get(code,self._last_error)
        if code in advice and numbers:text+=' '+numbers[:1].upper()+numbers[1:]+'.'
        self.note.setText('Not started · '+text)
        self.progress.setRange(0,1);self.progress.setValue(0)
    def watch(self,job):
        self.job=job['id'];self.progress.setRange(0,0);self.note.setText('Working · '+job['tool']+' · Stop brain cancels through the shared Kernel.');self.refresh()
    def qualify(self):
        self.launch_configured('brain.model.qualify')
    def task_trials(self):
        if self._selected_id:self.launch('slate.qualify',{'model_id':self._selected_id})
    def use(self):
        self.launch_configured('brain.model.use')
    def launch_configured(self,operation):
        if not self._selected_id:return
        try:options=self.options()
        except (ValueError,OSError) as exc:self.failed({'message':str(exc)});return
        self.launch(operation,{'id':self._selected_id,'options':options})
    def restore(self):self.launch('brain.restore',{})
    def stop(self):
        result=self.kernel.dispatch('brain.stop',{},self.principal);self.note.setText('Local brain stopped.' if result['ok'] else result['error']['message']);self.refresh()
    def dragEnterEvent(self,event):
        urls=event.mimeData().urls()
        if len(urls)==1 and urls[0].isLocalFile():event.acceptProposedAction()
    def dropEvent(self,event):
        urls=event.mimeData().urls()
        if len(urls)==1 and urls[0].isLocalFile():self.add_source(urls[0].toLocalFile());event.acceptProposedAction()
