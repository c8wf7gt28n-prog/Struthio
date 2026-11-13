"""Shared center workspace for the Programs shelf."""

from math import floor
from pathlib import Path, PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMenu,
    QPlainTextEdit, QPushButton, QWidget,
)

from . import boss_theme as colors, files_service
from .program_delivery import MAX_FILES
from .register_tabs import ServiceTab


STYLE = '''
QWidget#ProgramRoom {
    background: %(GROUND)s; color: %(TEXT)s; font-family: "IBM Plex Mono";
}
QWidget#ProgramRoom QLabel { color: %(QUIET)s; background: transparent; }
QWidget#ProgramRoom QWidget#ProgramHeader { border-bottom: 1px solid %(AMBER_EDGE)s; }
QWidget#ProgramRoom QLabel#ProgramTitle {
    color: %(TEXT)s; font-size: 22px; font-weight: 700;
}
QWidget#ProgramRoom QLabel#ProgramStatus { color: %(AMBER_TEXT)s; }
QWidget#ProgramRoom QLabel#ProgramStatus[ready="true"] { color: %(READY)s; }
QWidget#ProgramRoom QLineEdit, QWidget#ProgramRoom QPlainTextEdit,
QWidget#ProgramRoom QComboBox, QWidget#ProgramRoom QDoubleSpinBox {
    color: %(TEXT)s; background: %(PANEL)s; border: 1px solid %(LINE)s;
    border-radius: 0; padding: 6px;
    selection-background-color: %(AMBER_SOFT)s; selection-color: %(TEXT)s;
}
QWidget#ProgramRoom QPlainTextEdit#ProgramDetails { border-color: %(LINE)s; }
QWidget#ProgramRoom QLineEdit:focus, QWidget#ProgramRoom QComboBox:focus,
QWidget#ProgramRoom QPlainTextEdit:focus { border: 1px solid %(AMBER_EDGE)s; }
QWidget#ProgramRoom QPushButton {
    color: %(TEXT)s; background: %(RAISED)s; border: 1px solid %(LINE)s;
    border-radius: 0; padding: 6px 9px;
}
QWidget#ProgramRoom QPushButton:hover, QWidget#ProgramRoom QPushButton:focus {
    background: %(AMBER_SOFT)s; border-color: %(AMBER_EDGE)s;
}
QWidget#ProgramRoom QPushButton#ProgramPrimary {
    background: %(AMBER_EDGE)s; color: %(GROUND)s; border-color: %(AMBER_EDGE)s;
    font-weight: 700;
}
QWidget#ProgramRoom QPushButton:disabled, QWidget#ProgramRoom QPushButton#ProgramPrimary:disabled {
    background: %(GROUND)s; color: %(FAINT)s; border-color: %(LINE)s;
}
''' % vars(colors)


def line(label, value):
    return f'{label:<14} {value}'


def revision(result):
    return line('SHA-256', result['sha256'])


class ProgramRoom(ServiceTab):
    """One file or endpoint, one inspection, and owner-selected operations."""

    name = ''
    key = ''
    instruction = ''
    file_filter = ''
    source_hint = ''
    native_app = ''
    produces_files = False

    def __init__(self, host):
        super().__init__(host)
        self.setObjectName('ProgramRoom')
        self.setProperty('ledgerRoom', True)
        self.setStyleSheet(STYLE)
        self.setAccessibleName(self.name + ' workspace')
        self.current = None
        self.output = None
        self.busy = False
        self.actions = []
        self.outer.setContentsMargins(18, 14, 18, 14)
        self.outer.setSpacing(9)

        header = QWidget()
        header.setObjectName('ProgramHeader')
        heading_row = QHBoxLayout(header)
        heading_row.setContentsMargins(0, 0, 0, 8)
        self.heading = QLabel('[ ' + self.name.upper() + ' ]')
        self.heading.setObjectName('ProgramTitle')
        heading_row.addWidget(self.heading, 1)
        if self.native_app:
            button = self.button('Full app ↗', lambda: self.bound('open'), self.tool_ready, heading_row)
            button.setAccessibleName('Open in ' + self.native_app)
            button.setToolTip('Open the inspected source in ' + self.native_app)
        self.outer.addWidget(header)
        self.caption = QLabel(self.instruction)
        self.caption.setWordWrap(True)
        self.outer.addWidget(self.caption)

        self.source_row = QHBoxLayout()
        self.outer.addLayout(self.source_row)
        self.source = self.field('Source', self.source_hint, self.source_row)
        self.choose = None
        if self.file_filter:
            self.choose = QPushButton('Choose file…')
            self.choose.clicked.connect(self.choose_file)
            self.source_row.addWidget(self.choose)

        self.controls = QHBoxLayout()
        self.outer.addLayout(self.controls)
        self.build_controls()
        self.controls.addStretch()
        self.status.setObjectName('ProgramStatus')
        self.status.setTextFormat(Qt.PlainText)
        self.status.setText('Ready for a source.')
        result_row = QHBoxLayout()
        result_row.addWidget(self.status, 1)
        if self.produces_files:
            self.view_output_button = self.button('View result', self.view_output, lambda: self.output is not None, result_row)
            self.files_output_button = self.button('Show in Files', self.show_output, lambda: self.output is not None, result_row)
        self.outer.addLayout(result_row)

        self.details = QPlainTextEdit()
        self.details.setObjectName('ProgramDetails')
        self.details.setAccessibleName('Inspected source and operation results')
        self.details.setReadOnly(True)
        self.details.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.details.setContextMenuPolicy(Qt.CustomContextMenu)
        self.details.customContextMenuRequested.connect(self.result_menu)
        self.outer.addWidget(self.details, 1)
        self.source.textChanged.connect(self.source_changed)
        self.sync_actions()

    def title(self):
        return self.name

    def field(self, name, hint, row):
        widget = QLineEdit()
        widget.setAccessibleName(name)
        widget.setPlaceholderText(hint)
        widget.setClearButtonEnabled(True)
        row.addWidget(widget, 1)
        widget.textChanged.connect(self.sync_actions)
        return widget

    def button(self, label, action, enabled, row=None, primary=False):
        control = QPushButton(label)
        if primary:
            control.setObjectName('ProgramPrimary')
        control.clicked.connect(action)
        (self.controls if row is None else row).addWidget(control)
        self.actions.append((control, enabled, action))
        return control

    def sync_actions(self):
        if self.choose is not None:
            self.choose.setEnabled(not self.busy)
        for button, enabled, _ in self.actions:
            button.setEnabled(not self.busy and enabled())
        if self.produces_files:
            self.view_output_button.setVisible(self.output is not None)
            self.files_output_button.setVisible(self.output is not None)

    def source_changed(self):
        self.current = None
        self.output = None
        self.details.clear()
        self.set_status('Ready for a source.')
        self.clear_selection()
        self.sync_actions()

    def clear_selection(self):
        """Clear choices derived from the inspected source."""

    def choose_file(self):
        base = files_service.root(self.kernel).resolve()
        selected, _ = QFileDialog.getOpenFileName(self, 'Choose from Graphite Files', str(base), self.file_filter)
        if selected:
            try:
                relative = Path(selected).resolve().relative_to(base).as_posix()
                files_service.resolve(self.kernel, relative)
            except (ValueError, OSError):
                self.status.setText('Choose a file inside Graphite Files.')
                return
            self.source.setText(relative)

    def result_menu(self, pos):
        menu = self.make_result_menu()
        if menu.actions():
            menu.exec(self.details.viewport().mapToGlobal(pos))
        menu.deleteLater()

    def make_result_menu(self):
        menu = QMenu(self)
        if self.output and not self.busy and self.key != 'delivery':
            if PurePosixPath(self.output['path']).suffix.lower() == '.png':
                menu.addAction('Make print proof', self.print_output)
            menu.addAction('Stage result in Delivery', self.stage_output)
            menu.addSeparator()
        for button, _, action in self.actions:
            if button.isEnabled():
                menu.addAction(button.text(), action)
        if self.details.textCursor().hasSelection():
            if menu.actions():
                menu.addSeparator()
            menu.addAction('Copy selected text', self.details.copy)
        return menu

    def stage_output(self):
        if self.output:
            room = show(self.host, 'delivery')
            room.stage({self.output['path']: self.output['expected_sha256']})

    def print_output(self):
        if self.output:
            room = show(self.host, 'print')
            room.inspect_output(self.output)

    def ready(self):
        return bool(self.source.text().strip())

    def tool_ready(self):
        return bool(self.current and self.current['tool']['available'])

    def build_controls(self):
        self.button('Inspect', self.inspect, self.ready, primary=True)

    def inspect(self):
        self.current = None
        self.output = None
        self.clear_selection()
        self.details.clear()
        self.run('inspect', {'path': self.source.text().strip()}, self.inspected)

    def inspected(self, result):
        self.current = result
        self.details.setPlainText('\n'.join(self.summary(result)))
        self.set_status('Source inspected.', ready=True)

    def summary(self, result):
        return [line('Source', result['path']), revision(result)]

    def bound(self, action, **kwargs):
        if self.current:
            self.run(action, {
                'path': self.current['path'], 'expected_sha256': self.current['sha256'], **kwargs,
            }, self.completed)

    def completed(self, result):
        text = self.receipt(result)
        self.set_status(text[0], ready=True)
        self.details.appendPlainText('\n' + '\n'.join(text))
        if result.get('state') in ('EXPORTED', 'EXTRACTED', 'DRAFT_SAVED', 'RETRIEVED'):
            self.output = {'path': result['path'], 'expected_sha256': result['sha256']}
            self.details.setToolTip('Right-click for result handoffs.')

    def view_output(self):
        if self.output:
            request = self.output

            def present(value):
                if self.output is not request or self.host.tabs.currentWidget() is not self:
                    return
                try:
                    path = files_service.resolve(self.kernel, value['path'])
                except (OSError, ValueError):
                    self.set_status('The result is no longer at its saved path.')
                    return
                self.host.open_in_viewer(path)
            def failed(error):
                message = error.get('message', '')
                self.set_status('The result changed after it was saved.' if 'changed' in message.lower()
                                else 'The saved result could not be opened.')
            self.call('files.get', dict(request), present, failed)

    def show_output(self):
        if self.output:
            from .files_qt import show
            relative = self.output['path']
            try:
                files_service.resolve(self.kernel, relative)
            except (OSError, ValueError):
                self.set_status('The result is no longer at its saved path.')
                return
            tab = show(self.host, relative.rpartition('/')[0])
            if tab.question is not None:
                tab.question = None
                tab.reload()
            tab.select_path(relative)

    def set_status(self, message, *, ready=False):
        self.status.setText(message)
        self.status.setProperty('ready', ready)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def receipt(self, result):
        return [f"Saved {result['path']}", line('Size', f"{result['bytes']:,} bytes"), revision(result)]

    def run(self, action, arguments, display):
        if self.busy:
            return
        self.busy = True
        self.source.setReadOnly(True)
        self.sync_actions()
        self.set_status('Working…')

        def release():
            self.busy = False
            self.source.setReadOnly(False)
            self.sync_actions()

        def done(result):
            try:
                display(result)
            finally:
                release()

        if self.call(f'programs.{self.key}.{action}', arguments, done, lambda _: release()) is None:
            release()
            self.status.setText('The workspace is closing.')


class MailRoom(ProgramRoom):
    name, key = 'Mail', 'mail'
    native_app = 'Thunderbird'
    produces_files = True
    instruction = 'Read a saved message. Keep an attachment or prepare a reply draft in Files.'
    source_hint, file_filter = 'Message path in Files', 'Saved messages (*.eml)'

    def build_controls(self):
        super().build_controls()
        self.attachment = QComboBox()
        self.attachment.setAccessibleName('Attachment')
        self.attachment.setMinimumContentsLength(12)
        self.attachment.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.attachment.currentIndexChanged.connect(self.sync_actions)
        self.controls.addWidget(self.attachment, 1)
        self.button('Save attachment', self.extract, lambda: self.attachment.currentData() is not None)

        draft_row = QHBoxLayout()
        self.destination = self.field('New file in Files', 'New file path in Files', draft_row)
        self.button('Save reply draft', self.draft, self.can_draft, draft_row)
        self.outer.addLayout(draft_row)
        self.reply = QPlainTextEdit()
        self.reply.setAccessibleName('Reply draft')
        self.reply.setPlaceholderText('Write a local reply draft…')
        self.reply.setMaximumHeight(88)
        self.reply.textChanged.connect(self.sync_actions)
        self.outer.addWidget(self.reply)

    def can_draft(self):
        return bool(self.current and self.destination.text().strip() and self.reply.toPlainText().strip())

    def clear_selection(self):
        self.attachment.clear()

    def inspected(self, result):
        super().inspected(result)
        self.attachment.clear()
        for item in result['attachments']:
            if item['extractable']:
                self.attachment.addItem(item['name'], item['index'])

    def summary(self, result):
        details = [line('Subject', result['subject'] or '(no subject)'),
                   line('From', result['from']), line('To', result['to']),
                   line('Date', result['date'] or 'Unspecified'), *super().summary(result),
                   line('Thunderbird', 'Detected' if result['tool']['available'] else 'Unavailable'), '']
        details.append(result['body'] or 'Plain-text body unavailable.')
        if result['body_truncated']:
            details.append('The displayed message body reached its length limit.')
        for item in result['attachments']:
            size = f"{item['bytes']:,} bytes" if item['extractable'] else 'encoding unavailable'
            details.append(line('Attachment', f"{item['name']}  ·  {size}"))
        return details

    def extract(self):
        destination = self.destination.text().strip()
        if not destination:
            self.status.setText('Enter a new file path for the attachment.')
            self.destination.setFocus()
            return
        self.bound('extract', index=self.attachment.currentData(), destination=destination)

    def draft(self):
        self.bound('draft', body=self.reply.toPlainText(), destination=self.destination.text().strip())

    def receipt(self, result):
        if result['state'] == 'STARTED':
            return [f"Thunderbird process started · PID {result['pid']}", line('Source', result['path'])]
        parts = super().receipt(result)
        if result['state'] == 'DRAFT_SAVED':
            parts[0] = f"Local reply draft saved · {result['path']}"
            parts.insert(1, line('Draft to', result['to']))
        return parts


class BlenderRoom(ProgramRoom):
    name, key = 'Blender', 'blender'
    native_app = 'Blender'
    instruction = 'Inspect a local scene. Use Blender to count scene objects or open a trusted file in the full editor.'
    source_hint, file_filter = 'Blend file path in Files', 'Blender files (*.blend)'

    def build_controls(self):
        super().build_controls()
        self.button('Check scenes', lambda: self.bound('check'), self.tool_ready)

    def inspected(self, result):
        super().inspected(result)
        if not self.tool_ready():
            self.set_status('Source inspected · Blender is unavailable.')

    def summary(self, result):
        return [*super().summary(result), line('Format', result['format']),
                line('Version', result['version']), line('Size', f"{result['bytes']:,} bytes")]

    def receipt(self, result):
        if result['state'] == 'STARTED':
            return [f"Blender process started · PID {result['pid']}", line('Source', result['path'])]
        return ['Blender scene check completed', line('Active scene', result['active_scene']),
                line('Scenes', result['scenes']), line('Objects', result['objects']), line('Meshes', result['meshes'])]


class GodotRoom(ProgramRoom):
    name, key = 'Godot', 'godot'
    native_app = 'Godot'
    instruction = 'Inspect a local project. Open it in Godot or play a scene. Only launch projects you trust.'
    source_hint, file_filter = 'Project path in Files', 'Godot project (project.godot)'

    def build_controls(self):
        super().build_controls()
        self.scene = QComboBox()
        self.scene.setAccessibleName('Scene to play')
        self.scene.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.scene.setMinimumContentsLength(10)
        self.controls.addWidget(self.scene, 1)
        self.scene.currentIndexChanged.connect(self.sync_actions)
        self.button('Play scene', self.play, lambda: self.tool_ready() and bool(self.scene.currentData()))

    def clear_selection(self):
        self.scene.clear()

    def inspected(self, result):
        super().inspected(result)
        if not self.tool_ready():
            self.set_status('Project inspected · Godot is unavailable.')
        for scene in result['scenes']:
            self.scene.addItem(scene.removeprefix('res://'), scene)
        index = self.scene.findData(result['main_scene'])
        if index >= 0:
            self.scene.setCurrentIndex(index)

    def summary(self, result):
        return [line('Project', result['title']), *super().summary(result),
                line('Main scene', result['main_scene'] or 'Unspecified'), *result['scenes']]

    def play(self):
        self.bound('play', scene=self.scene.currentData())

    def receipt(self, result):
        return [f"Godot process started · PID {result['pid']}", line('Source', result['path']),
                line('Scene', result.get('scene') or 'Project editor')]


class TransferRoom(ProgramRoom):
    name, key = 'Transfer', 'transfer'
    instruction = 'List an anonymous FTP folder or retrieve one file. Folder URLs end with a slash.'
    source_hint = 'ftp://host/path'
    produces_files = True

    def __init__(self, host):
        self.available = False
        super().__init__(host)
        self.set_status('Check the local FTP tool before connecting.')

    def build_controls(self):
        self.button('Check FTP', self.check_status, lambda: True, self.source_row)
        self.button('List folder', self.list_folder,
                    lambda: self.available and self.ready() and self.source.text().strip().endswith('/'))
        self.destination = self.field('Download destination in Files', 'New file path in Files', self.controls)
        self.button('Retrieve', self.retrieve, self.can_retrieve, primary=True)

    def can_retrieve(self):
        url = self.source.text().strip()
        return self.available and bool(url and not url.endswith('/') and self.destination.text().strip())

    def check_status(self):
        self.run('status', {}, self.show_status)

    def show_status(self, result):
        self.available = result['ftp']
        if self.available:
            self.set_status(f"Anonymous FTP ready · {result['download_limit_bytes'] // 1048576} MiB per file.", ready=True)
        else:
            self.status.setText(f"FTP unavailable · {result.get('ftp_reason') or result.get('reason', 'curl is required')}")

    def list_folder(self):
        self.run('list', {'url': self.source.text().strip()}, self.listed)

    def listed(self, result):
        names = [entry['name'] for entry in result['entries']]
        notes = [f'{len(names)} FTP entries shown']
        if result['truncated']:
            notes.append('listing reached its display limit')
        if result['omitted']:
            notes.append(f"{result['omitted']} names omitted")
        self.set_status(' · '.join(notes), ready=not (result['truncated'] or result['omitted']))
        self.details.setPlainText('\n'.join([result['url'], '', *names]))

    def retrieve(self):
        self.run('download', {'url': self.source.text().strip(),
                              'destination': self.destination.text().strip()}, self.completed)


class CartridgeRoom(ProgramRoom):
    name, key = 'Cartridge Bay', 'cartridge'
    instruction = 'Inspect a local NES image. Start a detected RetroArch core with a separate game copy.'
    source_hint, file_filter = 'NES image path in Files', 'NES cartridge images (*.nes)'

    def build_controls(self):
        super().build_controls()
        self.core = QComboBox()
        self.core.setAccessibleName('NES emulator core')
        self.core.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.core.setMinimumContentsLength(9)
        self.controls.addWidget(self.core, 1)
        self.core.currentIndexChanged.connect(self.sync_actions)
        self.button('Start cartridge ↗', self.launch,
                    lambda: bool(self.current and self.current['launch_ready'] and self.core.currentData()))

    def clear_selection(self):
        self.core.clear()

    def inspected(self, result):
        super().inspected(result)
        for core in result['cores']:
            self.core.addItem(core['name'], core['id'])
        if result['launch_ready']:
            self.set_status('NES image inspected · core detected.', ready=True)
        elif result['state'] == 'TOOL_UNAVAILABLE':
            self.set_status('NES image inspected · RetroArch is unavailable.')
        elif result['state'] == 'CORE_UNAVAILABLE':
            self.set_status('NES image inspected · a compatible core is unavailable.')
        else:
            self.set_status('Cartridge format unavailable.')

    def summary(self, result):
        return [*super().summary(result), line('System', result['system']),
                line('Format', result['format']), line('Mapper', result['mapper']),
                line('Size', f"{result['bytes']:,} bytes"),
                line('Emulator', result['emulator'] or 'RetroArch unavailable'),
                line('Readiness', result['reason'])]

    def launch(self):
        self.bound('launch', core=self.core.currentData())

    def receipt(self, result):
        return [f"RetroArch process started · PID {result['pid']}",
                line('Working copy', result['working_copy']), line('Core', result['core'])]


class ExportRoom(ProgramRoom):
    """Use a suggested editable destination for native exports."""

    produces_files = True
    output_suffix = ''
    output_tag = ''
    output_label = 'Export'

    def build_controls(self):
        super().build_controls()
        self.destination = self.field('New file in Files', 'New file path in Files', self.controls)
        self.button(self.output_label, self.export, self.export_ready)

    def export_ready(self):
        return self.tool_ready() and bool(self.destination.text().strip())

    def export(self):
        self.bound('export', destination=self.destination.text().strip())

    def inspected(self, result):
        super().inspected(result)
        suffix = result.get('output_suffix') or self.output_suffix
        if suffix and (not self.destination.isModified() or not self.destination.text().strip()):
            source = PurePosixPath(result['path'])
            self.destination.setText(str(source.with_suffix(self.output_tag + suffix)))


class InkscapeRoom(ExportRoom):
    name, key = 'Inkscape', 'inkscape'
    native_app = 'Inkscape'
    instruction = 'Inspect a self-contained SVG and render a PNG proof with Inkscape.'
    source_hint, file_filter = 'SVG path in Files', 'Vector drawings (*.svg)'
    output_suffix, output_label = '.png', 'Export PNG'

    def tool_ready(self):
        return super().tool_ready() and self.current['render_ready']

    def inspected(self, result):
        super().inspected(result)
        if not result['render_ready']:
            self.set_status(result['reason'])

    def summary(self, result):
        return [*super().summary(result),
                line('Width', result['width'] or 'Unspecified'),
                line('Height', result['height'] or 'Unspecified'),
                line('View box', result['view_box'] or 'Unspecified'),
                line('Elements', result['elements'])]

    def receipt(self, result):
        if result['state'] == 'STARTED':
            return [f"Inkscape process started · PID {result['pid']}", line('Source', result['path'])]
        return [*super().receipt(result), line('PNG', f"{result['width']} × {result['height']} px")]


class MediaRoom(ExportRoom):
    name, key = 'Media Bench', 'media'
    instruction = 'Inspect a recording or video. Save a new clip, then play it in Graphite’s viewer.'
    source_hint, file_filter = 'Media path in Files', 'Audio and video (*.wav *.flac *.mp3 *.mp4 *.m4a)'
    output_label = 'Save clip'
    output_tag = '.clip'

    def build_controls(self):
        super().build_controls()
        timing = QHBoxLayout()
        self.start = self.seconds(timing, 'Start', 0, 86400, 0)
        self.duration = self.seconds(timing, 'Length', 0.25, 30, 5)
        timing.addStretch(1)
        self.outer.addLayout(timing)

    def seconds(self, row, name, low, high, value):
        label = QLabel(name)
        row.addWidget(label)
        control = QDoubleSpinBox()
        label.setBuddy(control)
        control.setAccessibleName(name + ' in seconds')
        control.setDecimals(3)
        control.setRange(low, high)
        control.setSingleStep(0.5)
        control.setValue(value)
        control.setSuffix(' s')
        row.addWidget(control)
        control.valueChanged.connect(self.sync_actions)
        return control

    def inspected(self, result):
        super().inspected(result)
        self.start.setValue(0)
        if result['clip_ready']:
            available = result['duration_seconds']
            self.start.setMaximum(min(86400, max(0, floor((available - 0.25) * 1000) / 1000)))
            self.duration.setValue(max(0.25, min(5, floor(available * 1000) / 1000)))
            self.destination.setToolTip('Choose a new ' + result['output_suffix'] + ' file in Files.')
        else:
            self.set_status(result['reason'])

    def export_ready(self):
        return (super().export_ready() and self.current['clip_ready']
                and PurePosixPath(self.destination.text().strip()).suffix.lower() == self.current['output_suffix']
                and self.start.value() + self.duration.value() <= self.current['duration_seconds'] + 1e-9)

    def export(self):
        self.bound('clip', start_seconds=self.start.value(), duration_seconds=self.duration.value(),
                   destination=self.destination.text().strip())

    def summary(self, result):
        seconds = result['duration_seconds']
        rows = [*super().summary(result), line('Container', result['format'] or 'Unmeasured'),
                line('Duration', f'{seconds:.3f} s' if seconds is not None else 'Unmeasured')]
        for stream in result['streams']:
            detail = ''
            if stream.get('width') and stream.get('height'):
                detail = f"  ·  {stream['width']} × {stream['height']}"
            if stream.get('sample_rate'):
                detail = f"  ·  {stream['sample_rate']} Hz  ·  {stream.get('channels', '?')} channel(s)"
            rows.append(line(f"{stream['kind'].title()} {stream['index']}", stream['codec'] + detail))
        return rows

    def receipt(self, result):
        return [*super().receipt(result), line('Start', f"{result['start_seconds']:.3f} s"),
                line('Clip length', f"{result['duration_seconds']:.3f} s")]


class FreeCADRoom(ExportRoom):
    name, key = 'FreeCAD', 'freecad'
    native_app = 'FreeCAD'
    instruction = 'Choose a stored shape, check its solid and dimensions, or export it to STEP.'
    source_hint, file_filter = 'FreeCAD path in Files', 'FreeCAD documents (*.FCStd *.fcstd)'
    output_suffix, output_label = '.step', 'Export STEP'

    def build_controls(self):
        super().build_controls()
        shape_row = QHBoxLayout()
        self.shape = QComboBox()
        self.shape.setAccessibleName('Stored FreeCAD shape')
        self.shape.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.shape.setMinimumContentsLength(12)
        self.shape.currentIndexChanged.connect(self.sync_actions)
        shape_row.addWidget(self.shape, 1)
        self.button('Check geometry', self.check, self.geometry_ready, shape_row)
        self.outer.addLayout(shape_row)

    def clear_selection(self):
        self.shape.clear()

    def inspected(self, result):
        super().inspected(result)
        for name in result['shape_names']:
            self.shape.addItem(name, name)
        preferred = self.shape.findData(result.get('preferred_shape'))
        if preferred >= 0:
            self.shape.setCurrentIndex(preferred)
        if not self.geometry_ready():
            self.set_status('Document inspected · geometry check unavailable for this source.')

    def tool_ready(self):
        return super().tool_ready() and self.current['editor_safe']

    def geometry_ready(self):
        return bool(self.current and self.current['tool']['check_available'] and self.shape.currentData())

    def export_ready(self):
        return self.geometry_ready() and bool(self.destination.text().strip())

    def check(self):
        self.bound('check', object=self.shape.currentData())

    def export(self):
        self.bound('export', object=self.shape.currentData(), destination=self.destination.text().strip())

    def summary(self, result):
        return [line('Document', result['label']), *super().summary(result),
                line('Objects', result['objects']), line('Stored shapes', result['shape_objects'])]

    def receipt(self, result):
        if result['state'] == 'STARTED':
            return [f"FreeCAD process started · PID {result['pid']}", line('Source', result['path'])]
        if result['state'] == 'CHECKED':
            size = ' × '.join(f'{axis:.3f}' for axis in result['dimensions_mm'])
            return ['FreeCAD geometry checked', line('Shape', result['object']),
                    line('Bounds', size + ' mm'), line('Solids', result['solids']),
                    line('Validity', 'Valid' if result['valid'] else 'Invalid')]
        return super().receipt(result)


class PrintProofRoom(ExportRoom):
    name, key = 'Print Proof', 'print'
    instruction = 'Place a PNG on one page and record its source hash. The proof fits the page for review.'
    source_hint, file_filter = 'PNG path in Files', 'PNG images (*.png)'
    output_suffix, output_label = '.pdf', 'Save PDF'
    output_tag = '.proof'

    def __init__(self, host):
        self.handoff_sha = None
        super().__init__(host)

    def build_controls(self):
        super().build_controls()
        options = QHBoxLayout()
        self.print_title = self.field('Proof title', 'Title on the proof', options)
        self.print_title.setMaxLength(80)
        self.paper = QComboBox()
        self.paper.setAccessibleName('Paper size')
        self.paper.addItems(['Letter', 'A4'])
        options.addWidget(self.paper)
        self.outer.addLayout(options)

    def source_changed(self):
        self.handoff_sha = None
        super().source_changed()

    def inspect_output(self, result):
        if self.busy:
            self.set_status('Wait for the current proof operation to finish.')
            return
        self.source.setText(result['path'])
        self.handoff_sha = result['expected_sha256']
        self.inspect()

    def inspected(self, result):
        expected, self.handoff_sha = self.handoff_sha, None
        if expected and result['sha256'] != expected:
            self.set_status('The PNG changed after export. Inspect it again to review the current file.')
            return
        super().inspected(result)
        if not self.print_title.isModified() or not self.print_title.text().strip():
            stem = PurePosixPath(result['path']).stem
            self.print_title.setText(stem.encode('latin-1', 'replace').decode('latin-1')[:80])
        if not result['print_ready']:
            self.set_status(result['reason'])

    def export_ready(self):
        title = self.print_title.text().strip()
        return (super().export_ready() and self.current['print_ready'] and bool(title)
                and all(ch.isprintable() and ord(ch) <= 255 for ch in title)
                and PurePosixPath(self.destination.text().strip()).suffix.lower() == '.pdf')

    def export(self):
        self.bound('export', destination=self.destination.text().strip(),
                   title=self.print_title.text().strip(), paper=self.paper.currentText())

    def summary(self, result):
        rows = super().summary(result)
        if result['width'] and result['height']:
            rows.append(line('PNG', f"{result['width']} × {result['height']} px"))
        return rows

    def receipt(self, result):
        return [*super().receipt(result), line('Paper', result['paper']),
                line('Source SHA-256', result['source_sha256'])]


class DeliveryRoom(ProgramRoom):
    name, key = 'Delivery', 'delivery'
    instruction = 'Stage the files you want to share, inspect their exact versions, and build a ZIP for local delivery.'
    source_hint, file_filter = 'Files path to add or ZIP to verify', 'All files (*)'
    produces_files = True

    def __init__(self, host):
        self.staged = {}
        super().__init__(host)
        self.set_status('Stage a file or choose a ZIP to verify.')

    def build_controls(self):
        self.button('Add file', self.add_file, self.ready)
        self.button('Inspect files', self.inspect, lambda: bool(self.staged), primary=True)
        self.button('Verify ZIP', self.verify, lambda: self.source.text().strip().lower().endswith('.zip'))

        selection = QHBoxLayout()
        self.selection = QComboBox()
        self.selection.setAccessibleName('Staged files')
        self.selection.setMinimumContentsLength(12)
        self.selection.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        selection.addWidget(self.selection, 1)
        self.button('Remove file', self.remove_file, lambda: bool(self.staged), selection)
        self.outer.addLayout(selection)

        target = QHBoxLayout()
        self.destination = self.field('New ZIP path', 'New ZIP path in Files', target)
        self.button('Build ZIP', self.build_zip, self.build_ready, target)
        self.outer.addLayout(target)

    def source_changed(self):
        self.sync_actions()

    def build_ready(self):
        return bool(self.current and self.destination.text().strip().lower().endswith('.zip'))

    def add_file(self):
        self.stage({self.source.text().strip(): None})

    def stage(self, entries):
        if self.busy:
            self.set_status('Wait for the current delivery operation to finish.')
            return
        merged = {**self.staged, **{path: digest for path, digest in entries.items()
                                  if path not in self.staged or digest}}
        if len(merged) > MAX_FILES:
            self.set_status(f'A delivery holds up to {MAX_FILES} files.')
            return
        if merged == self.staged:
            return
        self.staged = merged
        self.refresh_staged()

    def remove_file(self):
        path = self.selection.currentText()
        if path in self.staged:
            del self.staged[path]
            self.refresh_staged()

    def refresh_staged(self):
        self.current = self.output = None
        self.selection.clear()
        self.selection.addItems(list(self.staged))
        self.details.setPlainText('\n'.join(self.staged))
        self.set_status(f'{len(self.staged)} staged · inspect before building the ZIP.')
        self.sync_actions()

    def inspect(self):
        self.current = self.output = None
        self.run('inspect', {'paths': list(self.staged)}, self.inspected)

    def inspected(self, result):
        changed = [entry['path'] for entry in result['entries']
                   if self.staged[entry['path']] not in (None, entry['sha256'])]
        self.details.setPlainText('\n'.join(self.members(result['entries'])))
        if changed:
            self.set_status('A staged result changed. Remove it and add the current file to review it.')
            self.details.appendPlainText('\nChanged since handoff\n' + '\n'.join(changed))
            return
        self.current = result
        self.set_status(f"{len(result['entries'])} files reviewed · {result['bytes']:,} bytes.", ready=True)

    def members(self, entries):
        rows = []
        for entry in entries:
            rows.extend([entry['path'], line('Size', f"{entry['bytes']:,} bytes"), revision(entry), ''])
        return rows

    def build_zip(self):
        reviewed = [{'path': item['path'], 'sha256': item['sha256']} for item in self.current['entries']]
        self.run('build', {'entries': reviewed, 'destination': self.destination.text().strip()}, self.completed)

    def receipt(self, result):
        return [*super().receipt(result), line('Members', result['member_count'])]

    def verify(self):
        self.run('verify', {'path': self.source.text().strip()}, self.verified)

    def verified(self, result):
        self.output = {'path': result['path'], 'expected_sha256': result['sha256']}
        self.set_status(f"ZIP verified · {result['member_count']} files.", ready=True)
        self.details.setPlainText('\n'.join([line('Archive', result['path']), revision(result), '',
                                             *self.members(result['entries'])]))


ROOMS = {room.key: room for room in (MailRoom, BlenderRoom, GodotRoom, TransferRoom, CartridgeRoom,
                                    InkscapeRoom, MediaRoom, FreeCADRoom, PrintProofRoom, DeliveryRoom)}


def show(host, key):
    room = ROOMS[key]
    return host.ledger_bridge.add_tab(room, lambda: room(host))
