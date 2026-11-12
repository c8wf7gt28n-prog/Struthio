"""Owner-supplied editorial art, independent of engineering evidence or icons."""
from sdk.cli.arc1cli.editorial_assets import artwork


def poster_panel(root):
    """Fit the entire original artwork; no crops, image edits or screen takeover."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel
    class PosterPanel(QWidget):
        def __init__(self):
            super().__init__();layout=QVBoxLayout(self);layout.setContentsMargins(6,6,6,6)
            self.picture=QLabel();self.picture.setAlignment(Qt.AlignCenter);self.picture.setMinimumSize(160,240)
            self.picture.setAccessibleName('The Silicon Federation, ARC Concern issue 01 concept artwork')
            layout.addWidget(self.picture,1)
            self.caption=QLabel('ARC Concern · Issue 01 · 2026 · Project artwork');self.caption.setAlignment(Qt.AlignCenter)
            self.caption.setWordWrap(True);layout.addWidget(self.caption)
            try:
                item=artwork(root);self.original=QPixmap(str(item[1])) if item else QPixmap()
            except (OSError,ValueError,KeyError):self.original=QPixmap()
            if self.original.isNull():self.picture.setText('Project artwork unavailable. Restore the original art and catalog.')
        def resizeEvent(self,event):
            super().resizeEvent(event)
            if not self.original.isNull():
                self.picture.setPixmap(self.original.scaled(self.picture.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
    return PosterPanel()


def about_dialog(host,text):
    from PySide6.QtWidgets import QDialog,QDialogButtonBox,QTabWidget,QVBoxLayout,QLabel,QWidget
    dialog=QDialog(host);dialog.setWindowTitle('About Graphite · ARC Concern');dialog.resize(620,800)
    layout=QVBoxLayout(dialog);tabs=QTabWidget();layout.addWidget(tabs,1)
    tabs.addTab(poster_panel(host.root),'ARC Concern')
    info=QWidget();body=QVBoxLayout(info);label=QLabel(text);label.setWordWrap(True);body.addWidget(label);body.addStretch()
    tabs.addTab(info,'About Graphite')
    buttons=QDialogButtonBox(QDialogButtonBox.Close);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
    return dialog
