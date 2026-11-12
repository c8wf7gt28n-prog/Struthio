"""The STRUTHIO game's own window: python -m workbench.struthio_play URL (started by Ledger, see struthio_qt).

A small program of its own, so the web engine never runs inside Ledger. It shows one address, the game Ledger serves on
127.0.0.1, and refuses to go anywhere else."""
import os
import sys


def main(argv):
    url = argv[1] if len(argv) > 1 else ''
    if not url.startswith('http://127.0.0.1:'):return 2  # only the game Ledger serves
    os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--enable-unsafe-webgpu')  # the game draws with WebGPU
    from PySide6.QtCore import QUrl, Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(argv[:1]);app.setApplicationName('STRUTHIO')
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PySide6.QtWebEngineWidgets import QWebEngineView
    origin = url.rstrip('/')

    class OnlyTheGame(QWebEnginePage):
        def acceptNavigationRequest(self, target, kind, main_frame):
            return target.toString().startswith(origin)
    profile = QWebEngineProfile('struthio-arcade')  # its own storage: the game keeps its saves here
    view = QWebEngineView();page = OnlyTheGame(profile, view);view.setPage(page)
    view.setWindowTitle('STRUTHIO · ARCADE');view.resize(1200, 820)
    logo = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'branding', 'logo', 'paper.png')
    if os.path.isfile(logo):view.setWindowIcon(QIcon(logo))
    view.setUrl(QUrl(url));view.show();view.setFocus()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
