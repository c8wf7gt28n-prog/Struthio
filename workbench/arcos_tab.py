"""Contextual ARC-OS workspace: real C host frames and shared engineering jobs."""
import json, time, uuid
from PySide6.QtCore import Qt,QProcess,QTimer,QRectF
from PySide6.QtGui import QPainter,QColor,QFont
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QPlainTextEdit,QSplitter
from .engine import engineering
from .engineering_kernel import operator
from .project_context import refusal
from .command_rows import fold,pad_toggle
from .ux_polish import overline
from .arcos_tools import launch_argv,sources

KEYS={Qt.Key_Up:1,Qt.Key_Down:2,Qt.Key_Left:4,Qt.Key_Right:8,
      Qt.Key_Z:16,Qt.Key_X:32,Qt.Key_Return:64,Qt.Key_Enter:64}


class Screen(QWidget):
    def __init__(self,tab):
        super().__init__();self.tab=tab;self.frame=None;self.setMinimumSize(320,220)
        self.setFocusPolicy(Qt.StrongFocus)
    def keyPressEvent(self,e):
        if e.key() in KEYS:
            if not e.isAutoRepeat():self.tab.mask |= KEYS[e.key()]
            e.accept()
        else:super().keyPressEvent(e)
    def keyReleaseEvent(self,e):
        if e.key() in KEYS:
            if not e.isAutoRepeat():self.tab.mask &= ~KEYS[e.key()]
            e.accept()
        else:super().keyReleaseEvent(e)
    def focusOutEvent(self,e):
        self.tab.mask=0;super().focusOutEvent(e)
    def paintEvent(self,e):
        p=QPainter(self);p.fillRect(self.rect(),QColor("#101318"))
        scale=min(self.width()/320,self.height()/200)
        p.translate((self.width()-320*scale)/2,(self.height()-200*scale)/2);p.scale(scale,scale)
        p.setPen(QColor("#eee7da"));p.setFont(QFont("Sans",10))
        f=self.frame
        if not f:
            p.drawText(QRectF(15,30,290,120),Qt.AlignCenter,"ARC-OS\nBuild, then Run host.\nHost simulation · physical boot unproven");return
        for x,y,w,h,color in f["rects"]:p.fillRect(x,y,w,h,QColor(color))
        if f["screen"]=="MENU":
            p.setPen(QColor("#ff9250"));p.drawText(18,24,"ARC-OS  /  HOST")
            p.setPen(QColor("#b7b7b7"));p.drawText(18,45,"GAMECARD READY" if f["card"] else "NO CARD")
            for i,label in enumerate(("Start","Eject","Settings","Off")):
                if i==f["selection"]:
                    p.fillRect(12,57+i*28,296,25,QColor("#4b3028"));p.setPen(QColor("#ff9250"))
                else:p.setPen(QColor("#eee7da"))
                p.drawText(22,75+i*28,label)
        elif f["screen"]=="SETTINGS":
            p.drawText(18,35,"SETTINGS");p.drawText(18,70,"Event volume: "+str(f["volume"]))
            p.drawText(18,105,"Left / Right · X or Start returns")
            p.drawText(18,130,"Audio device output not implemented")
        elif f["screen"]=="EXIT":
            p.drawText(18,65,"Launcher exited cleanly.")
        p.setPen(QColor("#a9b2bb"));p.setFont(QFont("Sans",7))
        p.drawText(10,194,"Tick "+str(f["tick"])+" · "+f["screen"]+" · Start returns")


class ArcOSTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.kernel=engineering(host.root)
        self.job_id=None;self.mask=0;self.pending=False;self.buffer=b"";self.frames=[];self.commands=[]
        v=QVBoxLayout(self);v.addWidget(overline("ARC-OS","portable SDK, separate native games, replaceable BSP"))
        self.status=QLabel("Host development only. F133 build and physical boot remain unqualified.")
        self.status.setWordWrap(True);v.addWidget(self.status)
        self.bands=QLabel('Host runtime: not run in this view\nTarget integration: BLOCKED · F133 boot/DDR and target drivers unqualified\nPhysical validation: NOT RUN · fabrication HOLD')
        self.bands.setWordWrap(True);v.addWidget(self.bands)
        row=QHBoxLayout();self.game=QComboBox();self.game.addItems(["pulse","struthio","none"]);row.addWidget(self.game)
        for label,tool in (("Build","build"),("Test","test"),("Replay test","replay"),("Package","package"),("Dependencies","dependencies"),("Kernel probe","kernel_probe")):
            b=QPushButton(label);b.clicked.connect(lambda checked=False,t=tool:self.job(t));row.addWidget(b)
        for label,fn in (("Run host",self.run),("Pause",self.pause),("Step",self.step),("Reset",self.reset),("Capture",self.capture)):
            b=QPushButton(label);b.clicked.connect(fn);row.addWidget(b)
        fold(row,keep=("Build","Test","Run host","Pause","Step"))
        v.addLayout(row)
        split=QSplitter(Qt.Vertical);self.screen=Screen(self);split.addWidget(self.screen)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);split.addWidget(self.details);split.setSizes([500,160]);v.addWidget(split,1)
        row=QHBoxLayout();pad=[]
        for label,mask in (("↑",1),("↓",2),("←",4),("→",8),("A / Z",16),("B / X",32),("Start / Enter",64)):
            b=QPushButton(label);b.pressed.connect(lambda m=mask:self.hold(m));b.released.connect(lambda m=mask:self.release(m));row.addWidget(b);pad.append(b)
        row.insertWidget(0,pad_toggle(pad));v.addLayout(row)
        v.addWidget(QLabel("Click the screen for keyboard control. Arrows move; Z confirms; X backs out; Enter returns."))
        self.process=QProcess(self);self.process.setWorkingDirectory(str(host.root))
        from .operation_priority import watch_qprocess
        watch_qprocess(self.process,host.root)
        self.process.readyReadStandardOutput.connect(self.receive)
        self.process.readyReadStandardError.connect(lambda:self.status.setText(bytes(self.process.readAllStandardError()).decode(errors="replace")))
        self.process.finished.connect(self.ended)
        self.timer=QTimer(self);self.timer.setInterval(17);self.timer.timeout.connect(self.step)
        self.poll=QTimer(self);self.poll.setInterval(500);self.poll.timeout.connect(self.poll_job);self.poll.start()
    def title(self):return "ARC-OS · Launcher & SDK"
    def hold(self,m):self.mask|=m;self.step()
    def release(self,m):self.mask&=~m
    def job(self,action):
        if self.job_id:
            self.status.setText("An ARC-OS job is already active; inspect it in Engineering.");return
        self.stop()
        if not self.host.save_all():return
        r=self.kernel.dispatch("jobs.submit",{"tool":"arcos."+action,"request_key":uuid.uuid4().hex,"timeout":180},operator())
        if r["ok"] and refusal(r["result"]):self.status.setText(refusal(r["result"]))
        elif r["ok"]:
            self.job_id=r["result"]["id"];self.status.setText("Queued "+action+" · persistent engineering job")
        else:self.status.setText(r["error"]["message"])
    def poll_job(self):
        if not self.job_id:return
        j=self.kernel.record("jobs",self.job_id);self.status.setText(j["state"]+" · "+j["tool"])
        if j.get("evidence"):
            ev=self.kernel.record("evidence",j["evidence"])
            self.details.setPlainText(json.dumps(ev.get("diagnostics",ev),indent=2))
            current=ev.get('diagnostics',{}).get('input_hashes')==sources(self.host.root)
            self.bands.setText('Host runtime: '+ev.get('outcome',ev.get('state','UNKNOWN'))+' · '+ev.get('class','HOST_SIM')+' · revision '+ev.get('revision','unknown')[:16]+' · '+('current when loaded' if current else 'STALE — rerun')+'\nTarget integration: BLOCKED · boot/DDR and target drivers unqualified\nPhysical validation: NOT RUN · fabrication HOLD')
            self.job_id=None
    def run(self):
        if self.job_id:return
        if self.process.state()==QProcess.NotRunning:
            try:argv=launch_argv(self.host.root,self.game.currentText())
            except (OSError,ValueError,KeyError) as e:
                self.status.setText("Build first: "+str(e));return
            self.buffer=b"";self.pending=True;self.frames=[];self.commands=[];self.mask=0
            self.process.start(argv[0],argv[1:])
            if not self.process.waitForStarted(1500):
                self.status.setText("Host failed to start");return
        self.timer.start();self.screen.setFocus()
        self.status.setText("Real C host · fixed logical ticks; Qt pacing is not a real-time guarantee")
    def pause(self):self.timer.stop();self.mask=0;self.status.setText("Host paused")
    def step(self):
        if not self.pending and self.process.state()==QProcess.Running:
            self.pending=True;command="input "+str(self.mask)
            self.commands.append(command);self.process.write((command+"\n").encode())
    def receive(self):
        self.buffer+=bytes(self.process.readAllStandardOutput())
        while b"\n" in self.buffer:
            line,self.buffer=self.buffer.split(b"\n",1)
            try:f=json.loads(line)
            except ValueError:continue
            self.pending=False;self.frames.append(f);self.screen.frame=f;self.screen.update()
            self.details.setPlainText(json.dumps({k:v for k,v in f.items() if k!="rects"},indent=2))
            self.host.instruments.arcos_snapshot(f)
    def ended(self,*args):
        self.timer.stop();self.pending=False;self.mask=0
    def stop(self):
        self.timer.stop()
        if self.process.state()!=QProcess.NotRunning:
            self.process.write(b"quit\n")
            if not self.process.waitForFinished(800):
                self.process.kill();self.process.waitForFinished(800)
    def reset(self):self.stop();self.run()
    def capture(self):
        out=self.host.root/"build/arcos";out.mkdir(parents=True,exist_ok=True)
        self.screen.grab().save(str(out/"interactive-frame.png"))
        (out/"interactive-replay.json").write_text(json.dumps({"schema":"arc-os.interactive/1",
            "game":self.game.currentText(),"commands":self.commands,"frames":self.frames,
            "created":time.time(),"class":"HOST_SIM"},indent=2)+"\n")
        self.status.setText("Captured actual C-state view and input trace in build/arcos")
    def shutdown_engineering(self):self.stop();self.poll.stop()
