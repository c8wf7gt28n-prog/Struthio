"""The Easter egg: click the logo and play STRUTHIO · ARCADE, R. A. Peddycoart's game.

The game is the arcade build from the STRUTHIO repository, copied unchanged into games/struthio (FROM_REPOSITORY.txt
names the commit). It is JavaScript: it needs WebGPU and a web address (it loads modules and installs an offline worker).
So Ledger serves the folder itself, read-only, on 127.0.0.1 only, and opens it in its own small window run by a separate
process (workbench.struthio_play, Qt's built-in Chromium; no Java, nothing else to install). If that window cannot start
(no 3D graphics, for instance), the game opens in your web browser instead, from the same address. Ledger itself never
loads a web engine, so a game that fails cannot take your work with it. Stop and Master Stop end the game's window.

Keys: ← → (or A D) flap left and right; ↑, W or Space flaps hard; Enter starts.
"""
from __future__ import annotations
import functools
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from PySide6.QtCore import QProcess, QUrl

GAME = Path(__file__).resolve().parents[1] / 'games' / 'struthio'
DESK = '?desk'  # the owner's direction of 2026-11-06: at a desk the game is played with keys; the phone game stays as it is


class QuietHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.mjs': 'text/javascript', '.js': 'text/javascript',
                      '.webmanifest': 'application/manifest+json', '.wasm': 'application/wasm'}

    def log_message(self, *args):
        pass


PORT = 47913  # one steady local address: the game window keeps saves and high scores per address, so they last between runs


def serve(folder=GAME, port=PORT):
    """A read-only server for one folder on 127.0.0.1, at PORT when it is free, otherwise any free port (the game's saves then
    belong to that run's address). Returns (server, url)."""
    handler = functools.partial(QuietHandler, directory=str(folder))
    try:server = ThreadingHTTPServer(('127.0.0.1', port), handler)
    except OSError:server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, name='struthio-arcade', daemon=True).start()
    return server, 'http://127.0.0.1:%d/' % server.server_address[1]


def note(host, text, ms=8000):
    host.statusBar().showMessage(text, ms)


def in_browser(host, url):
    from PySide6.QtGui import QDesktopServices
    QDesktopServices.openUrl(QUrl(url))


def show(host):
    if not (GAME / 'index.html').is_file():note(host, 'The STRUTHIO game is not in this copy of Graphite.');return None
    if getattr(host, '_struthio', None) is None:host._struthio = serve()  # kept while Ledger runs; it serves the game only
    url = host._struthio[1] + DESK  # STRUTHIO ARCADE 1.9.0's desk mode: keyboard only, no title screen, a new run paused at tick zero
    process = getattr(host, '_struthio_process', None)
    if process is not None and process.state() != QProcess.NotRunning:note(host, 'STRUTHIO is already open in its own window.');return process
    process = QProcess(host);host._struthio_process = process;started = time.monotonic()
    process.setProgram(sys.executable);process.setArguments(['-m', 'workbench.struthio_play', url])
    process.setWorkingDirectory(str(Path(__file__).resolve().parents[1]))

    def finished(code, status, started=started):
        if (status == QProcess.CrashExit or code != 0) and time.monotonic() - started < 20:
            note(host, 'The game window could not start here, so STRUTHIO opens in your browser instead.');in_browser(host, url)
    process.finished.connect(finished)
    process.errorOccurred.connect(lambda error:error == QProcess.FailedToStart and (note(host, 'Opening STRUTHIO in your browser.'), in_browser(host, url)))
    process.start();note(host, 'STRUTHIO · ← → flap · ↑ or Space flaps hard · Enter starts', 6000)
    return process
