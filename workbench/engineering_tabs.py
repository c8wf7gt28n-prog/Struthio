"""Engineering services in contextual center tabs; keeps the approved Qt shell."""

from __future__ import annotations
from .text_prompts import writing_prompt
import hashlib
import json
import uuid
from PySide6.QtCore import QProcess, QTimer, Qt
from PySide6.QtGui import QPixmap
from .command_rows import fold
from .ux_polish import overline
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QPlainTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QTabWidget,
    QMessageBox,
    QInputDialog,
    QCheckBox,
    QLineEdit,
    QSpinBox,
    QScrollArea,
)
from .engine import engineering
from .engineering_kernel import operator, TOOLS
from .project_context import refusal
from .native_struthio import binary, source_hashes


class EngineeringTab(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.kernel = engineering(host.root)
        self.principal = operator()
        self.candidate = None
        self.file_sha = None
        self.selected_job = None
        shell = QVBoxLayout(self)
        shell.setContentsMargins(0,0,0,0)
        scroll=QScrollArea();scroll.setWidgetResizable(True)
        scroll.setAccessibleName('Engineering controls and evidence; scroll to reach all actions')
        body=QWidget();outer=QVBoxLayout(body);scroll.setWidget(body)
        shell.addWidget(scroll)
        heading=QLabel(
                "GRAPHITE ENGINEERING · persistent jobs / isolated candidates / operator approval"
            )
        heading.setWordWrap(True)
        outer.addWidget(heading)
        self.status = QLabel(
            "Accepted source is unchanged until explicit approval. Hardware fabrication HOLD."
        )
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        row = QHBoxLayout()
        self.tool = QComboBox()
        self.tool.addItems([t for t in TOOLS if t != "clip.loop"])
        row.addWidget(self.tool)
        for name, fn in [
            ("Run baseline", lambda: self.run(False)),
            ("Run candidate", lambda: self.run(True)),
            ("New candidate", self.create),
            ("Refresh", self.refresh),
        ]:
            b = QPushButton(name)
            b.clicked.connect(fn)
            row.addWidget(b)
        fold(row, keep=("Run candidate", "New candidate"))
        outer.addLayout(row)
        self.pages = QTabWidget()
        outer.addWidget(self.pages, 1)
        from .workshop_tabs import WorkshopTab
        self.workshop = WorkshopTab(host, self.kernel)
        self.pages.addTab(self.workshop, 'Graphite · Workshop')
        from .clip_tasks_tab import ExternalClipTasks
        self.external_clip = ExternalClipTasks(host, self.kernel)
        self.pages.addTab(self.external_clip, "External handoff")
        self.jobs = QTreeWidget()
        self.jobs.setHeaderLabels(["State", "Tool", "Requester", "Task ID"])
        self.jobs.itemSelectionChanged.connect(self.select_job)
        self.pages.addTab(self.jobs, "Jobs")
        self.candidates = QTreeWidget()
        self.candidates.setHeaderLabels(["State", "Goal", "Candidate ID"])
        self.candidates.itemSelectionChanged.connect(self.select_candidate)
        self.pages.addTab(self.candidates, "Candidates")
        self.editor = QPlainTextEdit()
        writing_prompt(self.editor, "Select or create an isolated candidate. Accepted source is never edited here.")
        self.pages.addTab(self.editor, "Candidate source")
        self.diff = QPlainTextEdit()
        self.diff.setObjectName('candidateDiff')
        self.diff.setProperty('arcRole','source')
        self.diff.setReadOnly(True)
        self.pages.addTab(self.diff, "Source diff")
        self.evidence = QPlainTextEdit()
        self.evidence.setReadOnly(True)
        evidence_page=QWidget();ev_layout=QVBoxLayout(evidence_page)
        self.evidence_facts=QLabel('Select a job to inspect its outcome, evidence and review state.');self.evidence_facts.setWordWrap(True)
        ev_layout.addWidget(self.evidence_facts);ev_layout.addWidget(self.evidence)
        self.evidence_page=evidence_page
        self.pages.addTab(evidence_page, "Evidence / comparison")
        self.clip_page = QWidget()
        form = QVBoxLayout(self.clip_page)
        form.addWidget(QLabel("GRAPHITE · bounded autonomous engineering"))
        self.clip_goal = QLineEdit()
        writing_prompt(self.clip_goal, "Define one testable engineering goal")
        form.addWidget(self.clip_goal)
        self.clip_path = QLineEdit("software/struthio/game.c")
        form.addWidget(self.clip_path)
        line = QHBoxLayout()
        self.provider = QComboBox()
        self.provider.addItems(["gemini", "deterministic"])
        line.addWidget(self.provider)
        self.iterations = QSpinBox()
        self.iterations.setRange(1, 3)
        self.iterations.setPrefix("Iterations: ")
        line.addWidget(self.iterations)
        self.runtime = QSpinBox()
        self.runtime.setRange(10, 600)
        self.runtime.setValue(300)
        self.runtime.setSuffix(" seconds")
        line.addWidget(self.runtime)
        form.addLayout(line)
        self.share_source = QCheckBox(
            "Authorize sending this source file and diagnostics to the selected cloud provider"
        )
        form.addWidget(self.share_source)
        self.proposals = QPlainTextEdit("[]")
        writing_prompt(self.proposals, "Offline deterministic adapter only: JSON list of iterations, each containing path/sha256/content patches.")
        form.addWidget(self.proposals, 1)
        row = QHBoxLayout()
        for name, fn in [
            ("Use current candidate as offline proposal", self.offline_proposal),
            ("Submit bounded task", self.submit_clip),
            ("Authorize selected task", self.authorize_clip),
        ]:
            b = QPushButton(name)
            b.clicked.connect(fn)
            row.addWidget(b)
        form.addLayout(row)
        self.pages.addTab(self.clip_page, "Legacy loop")
        guide = QWidget()
        guide_layout = QVBoxLayout(guide)
        guide_layout.addWidget(QLabel("GRAPHITE · read-only planning; no provider call or execution until requested"))
        self.guide_template = QComboBox()
        for template in self.kernel.dispatch("tasks.templates", {}, self.principal)["result"]["templates"]:
            self.guide_template.addItem(template["title"], template["id"])
        guide_layout.addWidget(self.guide_template)
        guide_actions = QHBoxLayout()
        for label, op in [("Plan task", "tasks.plan"), ("Agent handoff", "agent.handoff"), ("File authority", "project.authority")]:
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, operation=op: self.show_guidance(operation))
            guide_actions.addWidget(b)
        guide_layout.addLayout(guide_actions)
        self.guide_result = QPlainTextEdit()
        self.guide_result.setReadOnly(True)
        guide_layout.addWidget(self.guide_result)
        self.pages.addTab(guide, "Graphite planning")
        review = QGridLayout()
        for name, fn in [
            ("Save candidate", self.save),
            ("Review diff", self.review),
            ("Authorize test execution", self.authorize),
            ("Submit for approval", lambda: self.change_state("review")),
            ("Accept", lambda: self.change_state("accept")),
            ("Reject", lambda: self.change_state("reject")),
            ("Roll back", lambda: self.change_state("rollback")),
            ("Stage Graphite update", lambda: self.change_state("stage")),
            ("Compare tests", self.compare_tests),
        ]:
            b = QPushButton(name)
            b.clicked.connect(fn)
            n = review.count()
            review.addWidget(b, n // 4, n % 4)
        outer.addLayout(review)
        controls = QGridLayout()
        for name, fn in [
            ("Pause job", lambda: self.control("pause")),
            ("Stop job", lambda: self.control("cancel")),
            ("Resume job", lambda: self.control("resume")),
            ("Enable private remote…", self.remote),
            ("Disable remote", lambda: self.call("remote.disable")),
            ("Recovery check", self.recovery),
        ]:
            b = QPushButton(name)
            b.clicked.connect(fn)
            n = controls.count()
            controls.addWidget(b, n // 3, n % 3)
        # One command band for candidate review and job control: primary steps stay visible.
        reviewing = [review.itemAt(i).widget() for i in range(review.count())]
        controlling = [controls.itemAt(i).widget() for i in range(controls.count())]
        for b in controlling:
            controls.removeWidget(b)
        fold(review, keep=("Save candidate", "Review diff", "Authorize test execution", "Submit for approval"),
             groups=[("Decide", ("Accept", "Reject", "Roll back")), ("Job", ("Pause job", "Resume job", "Stop job"))],
             buttons=reviewing + controlling)
        outer.addLayout(controls)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)
        self.refresh()

    def title(self):
        return "Engineering · Jobs & Candidates"

    def show_guidance(self, operation):
        params = {"template": self.guide_template.currentData()} if operation == "tasks.plan" else {}
        self.guide_result.setPlainText(json.dumps(self.call(operation, params), indent=2))

    def shutdown_engineering(self):
        self.timer.stop()
        self.workshop.timer.stop()

    def offline_proposal(self):
        if not self.candidate:
            return
        c = self.kernel.record("candidates", self.candidate)
        patches = []
        for name in c["changes"]:
            patches.append(
                {
                    "path": name,
                    "sha256": c["base"].get(name, hashlib.sha256(b"").hexdigest()),
                    "content": (self.kernel.candidate_root(c["id"]) / name).read_text(),
                }
            )
        self.provider.setCurrentText("deterministic")
        self.proposals.setPlainText(json.dumps([patches], indent=2))
        self.clip_path.setText(",".join(c["paths"]))
        self.clip_goal.setText(c["goal"])

    def submit_clip(self):
        try:
            proposals = json.loads(self.proposals.toPlainText())
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        a = {
            "goal": self.clip_goal.text(),
            "paths": [x.strip() for x in self.clip_path.text().split(",") if x.strip()],
            "provider": self.provider.currentText(),
            "max_iterations": self.iterations.value(),
            "max_provider_calls": self.iterations.value(),
            "max_runtime": self.runtime.value(),
            "share_source": self.share_source.isChecked(),
            "proposals": proposals,
        }
        j = self.call("clip.submit", a)
        if j:
            self.selected_job = j["id"]
            self.evidence.setPlainText(json.dumps(j, indent=2))
            self.pages.setCurrentWidget(self.evidence_page)
            self.refresh()

    def authorize_clip(self):
        if not self.selected_job:
            return
        j = self.kernel.record("jobs", self.selected_job)
        if (
            QMessageBox.question(
                self,
                "Authorize bounded task",
                "Goal: "
                + j["goal"]
                + "\nFiles: "
                + ", ".join(j["scope"])
                + "\nAuthorize the displayed tools, provider budget and runtime? Candidate code executes with your OS permissions. Final source acceptance stays manual.",
            )
            == QMessageBox.Yes
        ):
            self.call("clip.authorize", {"id": j["id"]})
            self.pages.setCurrentWidget(self.jobs)

    def call(self, op, params=None):
        result = self.kernel.dispatch(op, params, self.principal)
        if not result["ok"]:
            self.status.setText(result["error"]["message"])
            return None
        if refusal(result["result"]):
            self.status.setText(refusal(result["result"]))
            return None
        self.status.setText(op + " completed")
        return result["result"]

    def create(self):
        current = self.host.current_editor()
        path = "software/struthio/struthio_core.c"
        if current and getattr(current, "path", None):
            try:
                path = current.path.relative_to(self.host.root).as_posix()
            except ValueError:
                pass
        path, ok = QInputDialog.getText(
            self,
            "Isolated candidate",
            "Source file (native STRUTHIO or diagnostic working source):",
            text=path,
        )
        if not ok:
            return
        goal, ok = QInputDialog.getText(
            self, "Engineering goal", "What deficiency should this candidate address?"
        )
        if not ok:
            return
        tool = (
            "diagnostic.compare" if path.startswith("development/") else "struthio.test"
        )
        required = (
            ["ledger.kernel_tests", "ledger.desktop_tests"]
            if path.startswith("workbench/")
            else [tool]
        )
        c = self.call(
            "candidates.create",
            {"goal": goal, "paths": [path], "required_tools": required},
        )
        if c:
            self.candidate = c["id"]
            self.load_candidate()
            self.refresh()
            self.pages.setCurrentWidget(self.editor)

    def select_candidate(self):
        items = self.candidates.selectedItems()
        if items:
            self.candidate = items[0].data(0, Qt.UserRole)
            self.load_candidate()

    def load_candidate(self):
        c = self.kernel.record("candidates", self.candidate)
        self.file = c["paths"][0]
        if self.file.endswith("/"):
            self.status.setText(
                "Directory-scoped candidate: use CLI/MCP to edit individual files."
            )
            return
        path = self.kernel.candidate_root(self.candidate) / self.file
        data = path.read_bytes() if path.exists() else b""
        self.file_sha = hashlib.sha256(data).hexdigest()
        self.editor.setPlainText(data.decode("utf-8"))
        self.editor.setReadOnly(c["state"] != "Draft")

    def save(self):
        if not self.candidate or not self.file_sha:
            return
        r = self.call(
            "candidates.patch",
            {
                "id": self.candidate,
                "path": self.file,
                "sha256": self.file_sha,
                "content": self.editor.toPlainText(),
            },
        )
        if r:
            self.file_sha = r["sha256"]
            self.review()

    def review(self):
        if not self.candidate:
            return
        r = self.call("candidates.diff", {"id": self.candidate})
        if r:
            self.diff.setPlainText(
                "\n".join(x["diff"] for x in r["changes"]) or "No candidate changes."
            )
            self.pages.setCurrentWidget(self.diff)

    def compare_tests(self):
        if not self.candidate:
            return
        from .project_inventory import hashes, revision

        c = self.kernel.record("candidates", self.candidate)
        candidate_revision = revision(hashes(self.kernel.candidate_root(c["id"])))
        evidence = self.kernel.listing("evidence")
        lines = [
            "BASELINE / CANDIDATE COMPARISON · actual executed tools",
            "Candidate: " + c["id"],
            "Goal: " + c["goal"],
            "Accepted source: " + c["revision"],
            "Candidate source: " + candidate_revision,
            "Hardware measurement: none. Host results do not qualify the board.",
            "",
        ]
        for tool in c["required_tools"]:
            lines.append(tool)
            for label, cid, rev in (
                ("BASELINE", None, c["revision"]),
                ("CANDIDATE", c["id"], candidate_revision),
            ):
                matches = [
                    e
                    for e in evidence
                    if e["tool"] == tool
                    and e["candidate"] == cid
                    and e["revision"] == rev
                ]
                if not matches:
                    lines.append("  " + label + ": NO FRESH EVIDENCE")
                    continue
                e = matches[0]
                lines.append(
                    "  %s: %s · exit %s · %.3f s · evidence %s"
                    % (
                        label,
                        e["state"],
                        e.get("exit_status"),
                        e.get("duration_seconds", 0),
                        e["id"],
                    )
                )
                if e.get("error"):
                    lines.append("    " + e["error"])
            lines.append("")
        lines.append("Review source diff before an explicit Accept or Reject decision.")
        self.evidence.setPlainText("\n".join(lines))
        self.pages.setCurrentWidget(self.evidence_page)

    def authorize(self):
        if (
            self.candidate
            and QMessageBox.question(
                self,
                "Authorize native execution",
                "Have you reviewed the candidate diff? Tests execute native code with your OS account permissions. This is not an OS sandbox. Authorize this exact revision?",
            )
            == QMessageBox.Yes
        ):
            self.call("candidates.authorize_execution", {"id": self.candidate})

    def change_state(self, action):
        if not self.candidate:
            return
        if (
            action in ("accept", "rollback", "stage")
            and QMessageBox.question(
                self,
                "Review source decision",
                action.capitalize()
                + " the reviewed candidate? Source hashes and evidence will be checked.",
            )
            != QMessageBox.Yes
        ):
            return
        self.call("candidates." + action, {"id": self.candidate})
        self.refresh()

    def run(self, candidate=False):
        if self.tool.currentText()=='native.build':self.host.show_native_project();return
        if candidate and not self.candidate:
            self.status.setText("Select a candidate first.")
            return
        a = {"tool": self.tool.currentText(), "request_key": uuid.uuid4().hex}
        if candidate:
            a["candidate"] = self.candidate
        j = self.call("jobs.submit", a)
        if j:
            self.selected_job = j["id"]
            self.pages.setCurrentWidget(self.jobs)
            self.refresh()

    def control(self, op):
        if self.selected_job:
            self.call("jobs." + op, {"id": self.selected_job})
            self.refresh()

    def select_job(self):
        items = self.jobs.selectedItems()
        if items:
            self.selected_job = items[0].data(0, Qt.UserRole)
            summary=self.call('workspace.job',{'id':self.selected_job})
            if not summary:
                self.evidence.clear();self.evidence_facts.setText('Selected record is unavailable.');return
            if hasattr(self.host,'select_object'):self.host.select_object({'kind':'job','target':self.selected_job},principal=self.principal,origin=self)
            j=summary['job'];content=summary['evidence'] or j
            self.evidence.setPlainText(json.dumps(content, indent=2))
            if summary:self.evidence_facts.setText('  ·  '.join(key.replace('_',' ').title()+': '+value for key,value in summary['facts'].items()))

    def refresh(self):
        if hasattr(self.host,'object_glass'):self.host.object_glass.check_authority()
        self.external_clip.refresh()
        self.jobs.blockSignals(True)
        self.jobs.clear()
        jobs = self.call('jobs.list') or []
        if self.selected_job and self.selected_job not in {j['id'] for j in jobs}:
            self.selected_job=None;self.evidence.clear();self.evidence_facts.setText('Selected record is unavailable.')
        for j in jobs:
            item = QTreeWidgetItem([j["state"], j["tool"], j["owner"], j["id"]])
            item.setData(0, Qt.UserRole, j["id"])
            self.jobs.addTopLevelItem(item)
            if j["id"] == self.selected_job:
                item.setSelected(True)
        self.jobs.blockSignals(False)
        self.candidates.blockSignals(True)
        self.candidates.clear()
        for c in self.kernel.listing("candidates"):
            item = QTreeWidgetItem([c["state"], c["goal"], c["id"]])
            item.setData(0, Qt.UserRole, c["id"])
            self.candidates.addTopLevelItem(item)
            if c["id"] == self.candidate:
                item.setSelected(True)
        self.candidates.blockSignals(False)
        if self.selected_job:
            self.select_job()
        if jobs:
            active = [
                j
                for j in jobs
                if j["tool"] in ("clip.loop", "clip.external")
                and j["state"] in ("Queued", "Running", "Waiting for Approval", "Waiting for Agent", "Waiting for Execution Approval")
            ]
            j = active[0] if active else jobs[0]
            step = j.get("current_operation", j["tool"])
            self.host.clip_dock.status.setText(j["state"] + " · " + step)
        if hasattr(self.host.clip_dock, "job_controls"):
            self.host.clip_dock.job_controls.setText("Jobs, scope & candidate review →")

    def recovery(self):
        try:
            self.evidence.setPlainText(
                json.dumps(self.kernel.recover_interrupted(), indent=2)
            )
            self.pages.setCurrentWidget(self.evidence_page)
        except Exception as exc:
            self.status.setText(str(exc))

    def remote(self):
        return self.host.show_remote_link()

class NativeGameTab(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.kernel = engineering(host.root)
        self.process = QProcess(self)
        from .operation_priority import watch_qprocess
        watch_qprocess(self.process,host.root)
        self.process.setWorkingDirectory(str(host.root))
        self.buffer = b""
        self.pending = False
        self.commands = []
        self.flap = False
        self.replay_queue = []
        v = QVBoxLayout(self)
        v.addWidget(overline("STRUTHIO", "native C host development"))
        self.status = QLabel(
            "Portable C gameplay · tick parity and deterministic replay · diagnostic host renderer"
        )
        self.status.setWordWrap(True)
        v.addWidget(self.status)
        bar = QGridLayout()
        for name, fn in [
            (
                "Edit C",
                lambda: host.open_document(host.root / "software/struthio/game.c"),
            ),
            ("Build", lambda: self.job("struthio.build")),
            ("Run", self.run),
            ("Pause", self.pause),
            ("Step", self.step),
            ("Reset", self.reset),
            ("Replay", self.replay),
            ("Tests", lambda: self.job("struthio.test")),
            ("Package", lambda: self.job("struthio.package")),
            ("Capture", self.capture),
            ("Save state", lambda: self.send("save")),
            ("Restore state", lambda: self.send("load")),
        ]:
            b = QPushButton(name)
            b.clicked.connect(fn)
            n = bar.count()
            bar.addWidget(b, n // 5, n % 5)
        fold(bar, keep=("Edit C", "Build", "Run", "Pause", "Step"))
        v.addLayout(bar)
        body = QHBoxLayout()
        self.image = QLabel("Build and Run the real native host")
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setMinimumSize(256, 384)
        body.addWidget(self.image, 1)
        self.state = QPlainTextEdit()
        self.state.setReadOnly(True)
        body.addWidget(self.state, 1)
        v.addLayout(body, 1)
        controls = QHBoxLayout()
        self.left = QCheckBox("Left (A)")
        self.right = QCheckBox("Right (D)")
        controls.addWidget(self.left)
        controls.addWidget(self.right)
        b = QPushButton("Flap (Space)")
        b.clicked.connect(lambda: setattr(self, "flap", True))
        controls.addWidget(b)
        v.addLayout(controls)
        self.setFocusPolicy(Qt.StrongFocus)
        self.timer = QTimer(self)
        self.timer.setInterval(17)
        self.timer.timeout.connect(self.step)
        self.process.readyReadStandardOutput.connect(self.receive)
        self.process.readyReadStandardError.connect(
            lambda: self.status.setText(
                bytes(self.process.readAllStandardError()).decode()
            )
        )
        self.process.finished.connect(lambda: self.timer.stop())
        self.process.errorOccurred.connect(
            lambda: self.status.setText(
                "Native host failed to start. Build first and inspect diagnostics."
            )
        )
        self.jobtimer = QTimer(self)
        self.jobtimer.timeout.connect(self.poll_job)
        self.jobtimer.start(1000)
        self.job_id = None

    def title(self):
        return "STRUTHIO · Native C"

    def shutdown_engineering(self):
        self.timer.stop()
        self.jobtimer.stop()
        if self.process.state() != QProcess.NotRunning:
            self.process.write(b"quit\n")
            if not self.process.waitForFinished(1500):
                self.process.kill()
                self.process.waitForFinished(1000)

    def job(self, tool):
        if not self.host.save_all():
            return
        r = self.kernel.dispatch(
            "jobs.submit", {"tool": tool, "request_key": uuid.uuid4().hex}, operator()
        )
        if r["ok"] and refusal(r["result"]):
            self.status.setText(refusal(r["result"]))
        elif r["ok"]:
            self.job_id = r["result"]["id"]
            self.status.setText("Queued " + tool + " · survives closing this tab")
        else:
            self.status.setText(r["error"]["message"])

    def poll_job(self):
        if not self.job_id:
            return
        j = self.kernel.record("jobs", self.job_id)
        self.status.setText(j["state"] + " · " + j["tool"] + " · " + j.get("error", ""))
        if j.get("evidence"):
            self.state.setPlainText(
                json.dumps(self.kernel.record("evidence", j["evidence"]), indent=2)
            )
            self.job_id = None

    def run(self):
        if self.process.state() == QProcess.NotRunning:
            report = binary(self.host.root).parent / "build.json"
            try:
                build = json.loads(report.read_text())
                if (
                    build["inputs"] != source_hashes(self.host.root)
                    or build["binary_sha256"]
                    != hashlib.sha256(binary(self.host.root).read_bytes()).hexdigest()
                ):
                    raise ValueError("Build is stale")
            except (OSError, ValueError, KeyError):
                self.status.setText(
                    "Build missing or stale: click Build, inspect the result, then Run."
                )
                return
            self.process.start(
                str(binary(self.host.root)),
                [str(binary(self.host.root).parent / "frame.ppm")],
            )
            if not self.process.waitForStarted(1000):
                return
            self.pending = False
            self.send("reset 1")
            self.commands = []
        self.timer.start()
        self.setFocus()
        self.status.setText(
            "Running real C host · fixed 60 Hz simulation ticks; Qt pacing is not a real-time guarantee"
        )

    def pause(self):
        self.timer.stop()
        self.status.setText("Paused native host")

    def send(self, command):
        if self.process.state() == QProcess.Running and not self.pending:
            self.pending = True
            self.process.write((command + "\n").encode())
            return True
        return False

    def step(self):
        if self.pending:
            return
        if self.replay_queue:
            command = self.replay_queue.pop(0)
            if not self.replay_queue:
                self.timer.stop()
        else:
            command = "step %d %d %d 0 0" % (
                self.left.isChecked(),
                self.right.isChecked(),
                self.flap,
            )
        if self.send(command):
            self.commands.append(command)
            self.flap = False

    def reset(self):
        if self.send("reset 1"):
            self.commands = []
            self.replay_queue = []

    def replay(self):
        if self.pending:
            return
        previous = list(self.commands)
        if self.send("reset 1"):
            self.replay_queue = previous
            self.commands = []
            self.timer.start()

    def receive(self):
        self.buffer += bytes(self.process.readAllStandardOutput())
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            try:
                s = json.loads(line)
            except ValueError:
                continue
            self.pending = False
            visible = {k: v for k, v in s.items() if k != "state_vector"}
            visible["serialized_state_words"] = len(s.get("state_vector", []))
            self.state.setPlainText(json.dumps(visible, indent=2))
            pix = QPixmap(str(binary(self.host.root).parent / "frame.ppm"))
            self.image.setPixmap(
                pix.scaled(self.image.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
            )
            self.host.instruments.native_snapshot(s)

    def capture(self):
        p = binary(self.host.root).parent
        pix = QPixmap(str(p / "frame.ppm"))
        if not pix.isNull():
            pix.save(str(p / "frame.png"))
            (p / "interactive-replay.json").write_text(
                json.dumps({"seed": 1, "commands": self.commands}, indent=2)
            )
            self.status.setText(
                "Captured C-rendered frame + deterministic input replay under build/native_struthio"
            )

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_A:
            self.left.setChecked(True)
        elif e.key() == Qt.Key_D:
            self.right.setChecked(True)
        elif e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self.flap = True
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_A:
            self.left.setChecked(False)
        elif e.key() == Qt.Key_D:
            self.right.setChecked(False)
        else:
            super().keyReleaseEvent(e)
