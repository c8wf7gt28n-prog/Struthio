"""One bounded native process per virtual console; shared by GUI and machine API.

Only current locally built artifacts execute. This is the owner's trusted host
account, not an OS sandbox. Traces persist; live process reconnect is a 1.9 task.
"""
from collections import deque
import json,os,queue,subprocess,threading,time,uuid,shutil
from pathlib import Path
from . import record_io as io,console_build,federation_rtl
from sdk.cli.arc1cli import console_media,native_sdk


class ConsoleSession:
    def __init__(self,root,owner,fixture='normal',native=None):
        self.root=Path(root).resolve();self.owner=owner;self.id=uuid.uuid4().hex;self.lock=threading.RLock();self.events=deque(maxlen=2048);self.sequence=0;self.closed=False;self.frame={};self.metrics={};self.fixture=fixture;self.error='';self.media_reads=0;self.media_bytes=0;self.rtl_transactions=0;self._media_status={};self.controller_events=0;self._last_controller=None
        self.report=console_build.current(self.root);self.revision=self.report['revision'];self.input_hashes=self.report['input_hashes']
        self.folder=io.project_path(self.root,'.ledger/console/'+self.id+'/state.json',False,private=True).parent;self.folder.mkdir(parents=True,exist_ok=True)
        self.module=self.folder/('game.dylib' if os.sys.platform=='darwin' else 'game.so')
        self.bundle=self.folder/'media.arcusb';self.media_valid=False;self.active_card=self.report['sample_gamecard'] if fixture=='sample' else self.report['gamecard']
        self.native=native;media_folder=self.root/console_build.OUT
        if native:
            media_folder=self.folder/'drives';media_folder.mkdir()
            for source in (self.root/console_build.OUT).glob('*.fat32.img'):shutil.copyfile(source,media_folder/source.name)
            shutil.copyfile(self.root/'examples'/native['name']/'.native-build/thumb-drive.fat32.img',media_folder/'sample-drive.fat32.img')
        argv=[str(self.root/console_build.OUT/'arc_console_host'),'--nor',str(self.root/console_build.OUT/'resident.nor'),str(self.module),str(media_folder),str(self.bundle),fixture]
        self.lines=queue.Queue(maxsize=128);self.stderr=[]
        self.process=subprocess.Popen(argv,cwd=self.root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        from .operation_priority import background_process
        background_process(self.root,self.process.pid)
        def read():
            try:
                while True:
                    line=self.process.stdout.readline(131073)
                    if not line:break
                    if len(line)>131072:self.lines.put(ValueError('CONSOLE_OUTPUT_BOUND'));break
                    self.lines.put(json.loads(line))
            except Exception as exc:self.lines.put(exc)
            finally:self.lines.put(None)
        def errors():
            for raw in iter(self.process.stderr.readline,b''):
                if len(self.stderr)<16:self.stderr.append(raw[:2048].decode(errors='replace'))
        self.reader=threading.Thread(target=read,daemon=True);self.err_reader=threading.Thread(target=errors,daemon=True);self.reader.start();self.err_reader.start()
        try:
            self._receive()
            self._accept_extracted_media(fixture)
            if self.media_valid:self._command('media 1')
            self._event('MEDIA_DISCOVERY',self.error or 'READY',{'port':'J14','adapter':'MODELED_USB_BOT_FAT32','bytes':self.media_bytes})
            self.persist()
        except Exception as exc:
            self.error=str(exc);self._event('BOOT_REJECTED','BLOCKED',{'reason':str(exc)});self.close()
            raise ValueError(str(exc)+'; recorded trace '+self.folder.relative_to(self.root).as_posix()+'/trace.json') from exc
    def _event(self,name,state,details=None,evidence_class='HOST_SIM'):
        self.sequence+=1;self.events.append({'sequence':self.sequence,'event':name,'state':state,'tick':self.frame.get('tick',0),'details':details or {},'class':evidence_class,'board_time_us':None})
    def _accept_extracted_media(self,fixture):
        self.fixture=fixture;self.media_valid=False;self.error=''
        self.active_card=(self.native['card'] if self.native else self.report['sample_gamecard']) if fixture=='sample' else self.report['gamecard']
        if self._media_status.get('state')!='READY':self.error=self._media_status.get('state','MEDIA_UNAVAILABLE');return
        if not self.bundle.is_file() or self.bundle.is_symlink() or self.bundle.stat().st_size>console_media.MAX_PACKAGE:
            self.error='MEDIA_SIZE';return
        card=self.active_card
        try:
            m=console_media.inspect(self.bundle.read_bytes(),target=self.report['target'],revision=self.revision,
                artifact_sha256=card['sha256'],sources=card['sources'],artifact_name=card['artifact'])
        except console_media.MediaError as exc:self.error=str(exc);return
        io.atomic(self.module,m['artifact']);self.media_reads+=1;self.media_bytes+=self.bundle.stat().st_size;self.media_valid=True
    def _mount_source(self,fixture):
        if fixture not in ('normal','missing','corrupt','incompatible','bad_csw','bad_fat','sample'):raise ValueError('UNKNOWN_MEDIA_FIXTURE')
        self._media_status={};self._command('usb_media '+fixture);self._accept_extracted_media(fixture)
    def check_current(self):
        if self.native and native_sdk.source_hashes(self.root,self.root/'examples'/self.native['name'])!=self.native['source_hashes']:
            self.error='STALE_NATIVE_SOURCE';self.close();raise ValueError(self.error)
        if console_build.sources(self.root)!=self.input_hashes:
            self.error='STALE_CONSOLE_SOURCE';self.close();raise ValueError(self.error)
    def _receive(self):
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            try:r=self.lines.get(timeout=max(.01,deadline-time.monotonic()))
            except queue.Empty:break
            if isinstance(r,Exception):raise ValueError(str(r))
            if r is None:raise ValueError('NATIVE_CONSOLE_ENDED: '+''.join(self.stderr)[-1000:])
            if r.get('kind')=='rtl_request':
                if self.rtl_transactions>=4:raise ValueError('RTL_TRANSACTION_BUDGET')
                request=r.get('request_hex','')
                if not isinstance(request,str) or len(request)!=128:raise ValueError('RTL_REQUEST_SCHEMA')
                response,receipt=federation_rtl.exchange(self.root,bytes.fromhex(request),self.folder/('rtl_'+str(self.rtl_transactions)))
                self.rtl_transactions+=1;self._event('FPGA12_RTL_EXCHANGE','EXECUTED',receipt,'RTL_SIM')
                self.process.stdin.write(('rtl '+response.hex()+'\n').encode());self.process.stdin.flush();continue
            if r.get('kind')=='protocol':
                self._event(r['stage'],'OK' if not r.get('result') else 'FAILED',r,r.get('class','HOST_SIM'));continue
            if r.get('kind')=='media':
                self._media_status=r;self._event('USB_FAT_MEDIA',r['state'],r);continue
            if r.get('kind')=='boot':self._event(r['stage'],r['state'],{'value':r['value']});continue
            if r.get('kind')=='metrics':self.metrics=r;continue
            if 'screen' not in r or len(r.get('rects',[]))>64:raise ValueError('CONSOLE_FRAME_SCHEMA')
            self.frame=r;return r
        raise ValueError('NATIVE_CONSOLE_TIMEOUT')
    def _command(self,text):
        if self.closed or self.process.poll() is not None:raise ValueError('VIRTUAL_CONSOLE_CLOSED')
        before=self.frame.get('screen');card=self.frame.get('card')
        self.process.stdin.write((text+'\n').encode());self.process.stdin.flush();frame=self._receive()
        if frame['screen']!=before:self._event('ARCOS_STATE',frame['screen'],{'previous':before})
        if frame['card']!=card:self._event('MEDIA_STATE','READY' if frame['card'] else 'EJECTED_OR_REMOVED')
        if frame.get('error'):self._event('LAUNCHER_ERROR',frame['error'])
        return frame
    def control(self,port=0,hat=8,buttons=0,ticks=1):
        if type(port) is not int or port not in (0,1) or type(hat) is not int or not 0<=hat<=8 or type(buttons) is not int or not 0<=buttons<=511 or type(ticks) is not int or not 1<=ticks<=60:raise ValueError('INVALID_LOGICAL_CONTROLLER_EVENT')
        with self.lock:
            self.check_current()
            if self.frame.get('tick',0)+ticks>36000:raise ValueError('SESSION_TICK_LIMIT')
            key=(port,hat,buttons)
            if key!=self._last_controller:
                self.controller_events+=1;self._event('CONTROLLER_INPUT','LOGICAL',{'port':'J12' if port==0 else 'J13','hat':hat,'buttons':buttons});self._last_controller=key
            for _ in range(ticks):
                self._command('controller %d %d %d'%(port,hat,buttons))
                if self.frame['screen']=='EXIT':break
            if self.frame['screen']=='EXIT':self._event('POWER_OFF','HOST_PROCESS_ONLY');self.close()
            return self.snapshot()
    def media(self,fixture=None):
        with self.lock:
            self.check_current();self._command('media 0');self.media_valid=False
            if fixture is not None:
                self._mount_source(fixture)
                if self.media_valid:self._command('media 1')
            else:self.error='MEDIA_REMOVED'
            self._event('MEDIA_SERVICE',self.error or 'READY',{'fixture':fixture,'adapter':'MODELED_USB_BOT_FAT32'});self.persist();return self.snapshot()
    def snapshot(self):
        return {'schema':'arc.virtual-console-session/1','id':self.id,'owner':self.owner,'revision':self.revision,'state':'CLOSED' if self.closed else 'RUNNING','class':'HOST_SIM','physical_hardware':False,'board_boot_qualified':False,'frame':self.frame,'metrics':{**self.metrics,'virtual_media_file_reads':self.media_reads,'virtual_media_read_bytes':self.media_bytes,'logical_controller_changes':self.controller_events,'rtl_transactions':self.rtl_transactions},'game':self.active_card,'media':{'fixture':self.fixture,'error':self.error,'ready':bool(self.frame.get('card'))},'trace':list(self.events),'last_sequence':self.sequence,'trace_limit':2048,'trace_path':self.folder.relative_to(self.root).as_posix()+'/trace.json','fabrication':'HOLD','flashing':'HOLD'}
    def persist(self):
        io.write_json(self.folder/'state.json',self.snapshot());io.write_json(self.folder/'trace.json',{'revision':self.revision,'events':list(self.events),'fidelity':'FUNCTIONAL_HOST_MODELS; no physical measurements'})
    def close(self):
        if self.closed:return
        self.closed=True
        if hasattr(self,'process'):
            if self.process.poll() is None:
                try:self.process.stdin.write(b'quit\n');self.process.stdin.flush();self.process.wait(timeout=2)
                except (OSError,subprocess.TimeoutExpired):self.process.kill();self.process.wait(timeout=2)
            self.reader.join(timeout=1);self.err_reader.join(timeout=1)
            for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
                if stream:stream.close()
        self.persist()
