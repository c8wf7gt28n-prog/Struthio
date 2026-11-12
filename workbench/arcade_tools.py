"""Local, host-only development checks and preview for STRUTHIO Arcade 1.8.

This module never builds an ARC-1 image. It checks the browser project and
serves it on localhost for the user's browser.
"""
from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ARCADE = Path('examples/struthio_arcade')


def project(root: Path = ROOT) -> Path:
    folder = (Path(root) / ARCADE).resolve()
    if not folder.is_dir():
        raise ValueError('STRUTHIO Arcade 1.8 project is missing')
    return folder


def check(root: Path = ROOT, syntax: bool = False) -> list[str]:
    """Validate the current editable web source without enforcing import hashes."""
    folder = project(root)
    required = ('index.html', 'manifest.webmanifest', 'sw.js', 'src/app/boot.mjs',
                'src/sim/step.mjs', 'assets/arcade.css')
    errors = ['missing ' + name for name in required if not (folder / name).is_file()]
    if errors:
        return errors
    try:
        manifest = json.loads((folder / 'manifest.webmanifest').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return ['invalid web manifest: ' + str(exc)]
    if not isinstance(manifest, dict) or not manifest.get('name'):
        errors.append('web manifest has no app name')
    for src in folder.rglob('*.mjs'):
        text = src.read_text(encoding='utf-8')
        for name in re.findall(r'''(?:from\s*|import\s*)["'](\.[^"']+)["']''', text):
            target = (src.parent / name).resolve()
            if not target.is_relative_to(folder) or not target.is_file():
                errors.append('%s imports missing %s' % (src.relative_to(folder), name))
    html = (folder / 'index.html').read_text(encoding='utf-8')
    for name in re.findall(r'''(?:src|href)=["'](\./[^"']+)["']''', html):
        target = (folder / name).resolve()
        if not target.is_relative_to(folder) or not target.is_file():
            errors.append('index.html references missing ' + name)
    worker = (folder / 'sw.js').read_text(encoding='utf-8')
    core = re.search(r'const CORE=(\[[^;]+\]);', worker)
    if core is None:
        errors.append('service worker has no CORE cache list')
    else:
        try:
            for name in json.loads(core.group(1)):
                target = (folder / name).resolve()
                if not target.is_relative_to(folder) or not target.exists():
                    errors.append('service worker references missing ' + name)
        except (TypeError, ValueError) as exc:
            errors.append('service worker CORE list is invalid: ' + str(exc))
    if syntax:
        node = shutil.which('node')
        if node is None:
            errors.append('Node.js unavailable; JavaScript syntax NOT RUN')
        else:
            for src in sorted([*folder.rglob('*.mjs'), *folder.rglob('*.js')]):
                result = subprocess.run([node, '--check', str(src)], capture_output=True,
                                        text=True, timeout=20)
                if result.returncode:
                    errors.append('%s: %s' % (src.relative_to(folder), result.stderr.strip()[:300]))
    return errors


def serve(root: Path = ROOT) -> int:
    errors = check(root)
    if errors:
        for error in errors:
            print('FAIL ' + error, flush=True)
        return 1
    folder = project(root)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(folder), **kwargs)

        def log_message(self, fmt, *args):
            print('HTTP ' + fmt % args, flush=True)

        def translate_path(self, path):
            relative = Path(unquote(urlsplit(path).path).lstrip('/'))
            target = (folder / relative).resolve()
            if not target.is_relative_to(folder):
                return str(folder / '.blocked')
            return str(target)

    try:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    except OSError as exc:
        print('FAIL localhost preview unavailable: %s' % exc, flush=True)
        return 1
    print('READY http://127.0.0.1:%d/' % server.server_port, flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='STRUTHIO Arcade browser project, host only')
    parser.add_argument('action', choices=('build', 'test', 'run'))
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    if args.action == 'run':
        return serve(args.root)
    errors = check(args.root, syntax=args.action == 'test')
    if errors:
        for error in errors:
            print('FAIL ' + error)
        return 1
    print('%s PASS [STATIC_CHECK] — browser source only; no ARC-1 hardware build or run' % args.action.upper())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
