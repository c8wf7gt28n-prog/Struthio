#!/usr/bin/env python3
"""ARC-1 Workbench setup: install, upgrade and uninstall for one user.

Started by INSTALL_ARC1.cmd (Windows) or `python3 workbench/setup_arc1.py install`.
No administrator rights. Standard library only, and self-contained (no package
imports): the uninstaller runs a copy of this file from the temp folder while
it removes the installation.

Layout:
    <target>/app/          the ARC-1 project (Workbench edits files here)
    <target>/runtime/venv/ private Python with PySide6, kept across upgrades
    <target>/install.json  version, options and a SHA-256 manifest of app/
    <target>/Uninstall ARC-1 Workbench.cmd   (Linux: .sh)

Your work is never discarded: on upgrade or uninstall, any file in app/ that
differs from what was installed (or was added) triggers a dated backup of the
old app/ folder before anything is replaced or removed.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

APP_NAME = 'ARC-1 Workbench'
APP_ID = 'ARC1Workbench'
PUBLISHER = 'ARC-1 project'
VERSION = 'R10'
QT_REQUIREMENT = 'PySide6-Essentials==6.8.1'
MIN_PYTHON = (3, 11)
QT_MAX_PYTHON = (3, 13)          # newest Python the pinned PySide6 publishes wheels for
SCHEMA = 'arc1.workbench-install/1'
EXCLUDE_DIRS = {'.git', '__pycache__', 'build', 'reports', '.venv', 'node_modules', '.pytest_cache'}
EXCLUDE_SUFFIXES = ('.pyc', '.pyo')
WIN_COMPILER_DIRS = [r'%ProgramFiles%\LLVM\bin', r'C:\msys64\ucrt64\bin', r'C:\msys64\mingw64\bin',
                     r'%LOCALAPPDATA%\Programs\LLVM\bin']
COMPILERS = ('clang', 'gcc', 'cc')


class SetupError(Exception):
    pass


# --------------------------------------------------------------------------- user interaction

class Console:
    """Plain console prompts. Enter accepts the default shown in capitals."""
    def __init__(self, assume_yes=False, out=None):
        self.assume_yes = assume_yes
        self.out = out or sys.stdout
        self.log_lines = []

    def say(self, text=''):
        self.log_lines.append(text)
        try:
            self.out.write(text + '\n')
            self.out.flush()
        except UnicodeEncodeError:
            self.out.write(text.encode('ascii', 'replace').decode('ascii') + '\n')

    def step(self, n, total, label):
        self.say('  [%d/%d] %s' % (n, total, label))

    def ask(self, question, default=True):
        if self.assume_yes:
            self.say('%s %s' % (question, 'yes' if default else 'no'))
            return default
        hint = '[Y/n]' if default else '[y/N]'
        while True:
            try:
                answer = input('%s %s ' % (question, hint)).strip().lower()
            except EOFError:
                return default
            if not answer:
                return default
            if answer in ('y', 'yes'):
                return True
            if answer in ('n', 'no'):
                return False


# --------------------------------------------------------------------------- locations

def default_target():
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
        return Path(base) / 'Programs' / APP_NAME
    return Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share') / 'arc1-workbench'


def windows_documents():
    """The real Documents folder, which OneDrive often moves out of %USERPROFILE%."""
    try:
        import ctypes
        from ctypes import wintypes
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:   # CSIDL_PERSONAL
            return Path(buf.value)
    except (AttributeError, OSError, ValueError):
        pass
    return Path(os.environ.get('USERPROFILE') or Path.home()) / 'Documents'


def backup_root():
    if os.name == 'nt':
        return windows_documents() / (APP_NAME + ' backups')
    return Path.home() / 'arc1-workbench-backups'


def store_python(executable=None):
    """Microsoft Store Python redirects writes under AppData into a private folder, so the
    shortcuts would point at files other programs cannot see."""
    return 'windowsapps' in str(executable or sys.executable).lower()


def venv_python(target, windowed=False):
    v = Path(target) / 'runtime' / 'venv'
    if os.name == 'nt':
        return v / 'Scripts' / ('pythonw.exe' if windowed else 'python.exe')
    return v / 'bin' / 'python'


# --------------------------------------------------------------------------- files

def included(rel):
    parts = Path(rel).parts
    return not any(p in EXCLUDE_DIRS for p in parts) and not rel.endswith(EXCLUDE_SUFFIXES)


def walk(app_dir):
    app_dir = Path(app_dir)
    for dirpath, dirnames, filenames in os.walk(app_dir):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            p = Path(dirpath) / f
            rel = p.relative_to(app_dir).as_posix()
            if included(rel) and not p.is_symlink():
                yield rel, p


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def manifest_of(app_dir):
    return {rel: sha256(p) for rel, p in sorted(walk(app_dir))}


def user_changes(app_dir, manifest):
    """Files the user modified or added since installation (deletions are ignored)."""
    changed = []
    for rel, p in walk(app_dir):
        if rel not in manifest or sha256(p) != manifest[rel]:
            changed.append(rel)
    return sorted(changed)


def copy_app(source, dest):
    count = 0
    for rel, p in walk(source):
        d = Path(dest) / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, d)
        count += 1
    return count


def looks_like_arc1(folder):
    f = Path(folder)
    return (f / 'arc1').is_file() and (f / 'workbench' / 'qt_app.py').is_file() and (f / 'sdk').is_dir()


def read_install(target):
    p = Path(target) / 'install.json'
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get('schema') == SCHEMA else None


def write_install(target, data):
    p = Path(target) / 'install.json'
    fd, tmp = tempfile.mkstemp(prefix='.install-', dir=target)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp, p)


def backup_app(app_dir, changed, ui, reason):
    stamp = datetime.now().strftime('%Y-%m-%d %H%M%S')
    dest = backup_root() / ('%s (%s)' % (stamp, reason))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(app_dir, dest, ignore=shutil.ignore_patterns(*EXCLUDE_DIRS, '*.pyc'))
    ui.say('      %d file(s) you changed are backed up in:' % len(changed))
    ui.say('      %s' % dest)
    for rel in changed[:8]:
        ui.say('        %s' % rel)
    if len(changed) > 8:
        ui.say('        ... and %d more' % (len(changed) - 8))
    return dest


# --------------------------------------------------------------------------- tools

def run(argv, timeout, env=None, cwd=None):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env, cwd=cwd,
                           encoding='utf-8', errors='replace')
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)


def find_compiler(windows=None):
    """Returns (path, extra_path_dir or None) for a C compiler, or (None, None).
    On Windows also looks in the usual LLVM/MSYS2 folders when they are not on PATH."""
    windows = (os.name == 'nt') if windows is None else windows
    for name in COMPILERS:
        found = shutil.which(name)
        if found:
            return found, None
    if windows:
        for d in WIN_COMPILER_DIRS:
            folder = os.path.expandvars(d)
            for name in ('clang.exe', 'gcc.exe'):
                candidate = os.path.join(folder, name)
                if os.path.isfile(candidate):
                    return candidate, folder
    return None, None


# --------------------------------------------------------------------------- platforms

class WindowsPlatform:
    """Start Menu / Desktop shortcuts and an Apps & Features entry, all per user."""
    UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\%s' % APP_ID

    def __init__(self, runner=run):
        self.runner = runner

    @staticmethod
    def shortcut_script():
        # Paths arrive in environment variables, never pasted into the script text.
        return r"""$ErrorActionPreference = 'Stop'
$sh = New-Object -ComObject WScript.Shell
$places = @([IO.Path]::Combine([Environment]::GetFolderPath('Programs'), $env:ARC1_NAME + '.lnk'))
if ($env:ARC1_DESKTOP -eq '1') { $places += [IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), $env:ARC1_NAME + '.lnk') }
foreach ($p in $places) {
  $s = $sh.CreateShortcut($p)
  $s.TargetPath = $env:ARC1_TARGET
  $s.Arguments = $env:ARC1_ARGS
  $s.WorkingDirectory = $env:ARC1_WORKDIR
  $s.IconLocation = $env:ARC1_ICON
  $s.Description = 'ARC-1 Workbench - Adaptive RISC-V Console development'
  $s.Save()
  Write-Output $p
}
"""

    def create_shortcuts(self, spec, desktop):
        env = dict(os.environ, ARC1_NAME=APP_NAME, ARC1_TARGET=spec['target'], ARC1_ARGS=spec['args'],
                   ARC1_WORKDIR=spec['workdir'], ARC1_ICON=spec['icon'], ARC1_DESKTOP='1' if desktop else '0')
        code, out = self.runner(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                 '-Command', self.shortcut_script()], 60, env)
        if code != 0:
            raise SetupError('Shortcut creation failed: %s' % out.strip()[-400:])
        return [line.strip() for line in out.splitlines() if line.strip().endswith('.lnk')]

    def remove_shortcuts(self, paths):
        for p in paths:
            try:
                Path(p).unlink()
            except OSError:
                pass

    def uninstall_values(self, target, size_kb):
        t = Path(target)
        return {'DisplayName': APP_NAME, 'DisplayVersion': VERSION, 'Publisher': PUBLISHER,
                'DisplayIcon': str(t / 'app' / 'workbench' / 'arc1.ico'), 'InstallLocation': str(t),
                'UninstallString': 'cmd.exe /c ""%s""' % (t / 'Uninstall ARC-1 Workbench.cmd'),
                'NoModify': 1, 'NoRepair': 1, 'EstimatedSize': int(size_kb)}

    def register(self, target, size_kb):
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.UNINSTALL_KEY) as key:
            for name, value in self.uninstall_values(target, size_kb).items():
                kind = winreg.REG_DWORD if isinstance(value, int) else winreg.REG_SZ
                winreg.SetValueEx(key, name, 0, kind, value)

    def unregister(self):
        try:
            import winreg
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, self.UNINSTALL_KEY)
        except OSError:
            pass

    def uninstaller(self, target, base_python):
        return 'Uninstall ARC-1 Workbench.cmd', (
            '@echo off\r\n'
            'rem Removes ARC-1 Workbench for this user. Files you changed are backed up first.\r\n'
            'copy /y "%~dp0app\\workbench\\setup_arc1.py" "%TEMP%\\arc1_workbench_setup.py" >nul\r\n'
            'cd /d "%TEMP%"\r\n'
            'rem One line on purpose: this file is deleted while it runs, and cmd reads batch files line by line.\r\n'
            '"{py}" -I "%TEMP%\\arc1_workbench_setup.py" uninstall --target "%~dp0." & pause & exit /b\r\n'
            ).format(py=base_python)

    def can_install_compiler(self):
        return shutil.which('winget') is not None

    def install_compiler(self, ui):
        ui.say('      Windows will ask for permission to install LLVM (clang).')
        code, out = self.runner(['winget', 'install', '-e', '--id', 'LLVM.LLVM', '--accept-package-agreements',
                                 '--accept-source-agreements'], 1800)
        return code == 0, out


class PosixPlatform:
    """Freedesktop launcher (Linux). No registry; uninstall with the .sh beside install.json."""
    def __init__(self, runner=run):
        self.runner = runner

    @staticmethod
    def apps_dir():
        return Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share') / 'applications'

    def create_shortcuts(self, spec, desktop):
        text = ('[Desktop Entry]\nType=Application\nName=%s\nComment=Adaptive RISC-V Console development\n'
                'Exec="%s" %s\nPath=%s\nIcon=%s\nTerminal=false\nCategories=Development;\n'
                % (APP_NAME, spec['target'], spec['args'], spec['workdir'], spec['icon_png']))
        made = []
        places = [self.apps_dir() / 'arc1-workbench.desktop']
        if desktop and (Path.home() / 'Desktop').is_dir():
            places.append(Path.home() / 'Desktop' / 'arc1-workbench.desktop')
        for p in places:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding='utf-8')
            p.chmod(0o755)
            made.append(str(p))
        return made

    def remove_shortcuts(self, paths):
        for p in paths:
            try:
                Path(p).unlink()
            except OSError:
                pass

    def register(self, target, size_kb):
        pass

    def unregister(self):
        pass

    def uninstaller(self, target, base_python):
        return 'Uninstall ARC-1 Workbench.sh', (
            '#!/bin/sh\n# Removes ARC-1 Workbench for this user. Files you changed are backed up first.\n'
            'here="$(cd "$(dirname "$0")" && pwd)"\n'
            'cp "$here/app/workbench/setup_arc1.py" "${TMPDIR:-/tmp}/arc1_workbench_setup.py"\n'
            'cd "${TMPDIR:-/tmp}" && exec "%s" -I "${TMPDIR:-/tmp}/arc1_workbench_setup.py" uninstall --target "$here"\n'
            % base_python)

    def can_install_compiler(self):
        return False

    def install_compiler(self, ui):
        return False, 'not supported'


def platform():
    return WindowsPlatform() if os.name == 'nt' else PosixPlatform()


# --------------------------------------------------------------------------- install

def install(source, target=None, assume_yes=False, desktop=True, wheels=None, skip_qt=False, ui=None,
            plat=None, launch=None):
    ui = ui or Console(assume_yes)
    plat = plat or platform()
    source = Path(source).resolve()
    target = Path(target or default_target()).resolve()
    if not looks_like_arc1(source):
        raise SetupError('%s does not look like an ARC-1 Workbench folder (extract the ZIP first)' % source)
    if target == source or target in source.parents or source in target.parents:
        raise SetupError('Install folder and source folder must be separate: %s' % target)
    if sys.version_info < MIN_PYTHON:
        raise SetupError('Python %d.%d or newer is required (this is %s)' % (*MIN_PYTHON, sys.version.split()[0]))
    if os.name == 'nt' and store_python():
        raise SetupError('This is the Microsoft Store Python, which hides files it writes in AppData from other '
                         'programs, so the shortcuts would not work.\nInstall Python 3.12 from python.org, or run:\n'
                         '  winget install -e --id Python.Python.3.12 --scope user\nthen run INSTALL_ARC1.cmd again.')
    previous = read_install(target)
    app = target / 'app'
    ui.say('')
    ui.say('%s %s setup' % (APP_NAME, VERSION))
    ui.say('  Install folder: %s' % target)
    ui.say('  %s' % ('Upgrading the existing installation (%s)' % previous.get('version') if previous
                     else 'New installation for this user; no administrator rights needed'))
    if not ui.ask('Continue?', True):
        raise SetupError('Cancelled; nothing was changed')
    total = 6

    # 1. Application files, swapped in atomically; user changes backed up first.
    ui.step(1, total, 'Copy application files')
    target.mkdir(parents=True, exist_ok=True)
    incoming = target / 'app.incoming'
    old = target / 'app.previous'
    for leftover in (incoming, old):
        if leftover.exists():
            shutil.rmtree(leftover)
    count = copy_app(source, incoming)
    if not looks_like_arc1(incoming):
        shutil.rmtree(incoming)
        raise SetupError('The copied application is incomplete; nothing was replaced')
    backup = None
    if app.exists():
        changed = user_changes(app, (previous or {}).get('manifest', {})) if previous else \
            [rel for rel, _ in walk(app)]
        if changed:
            backup = backup_app(app, changed, ui, 'before upgrade to %s' % VERSION)
        try:
            app.rename(old)
        except OSError:
            shutil.rmtree(incoming, ignore_errors=True)
            raise SetupError('ARC-1 Workbench seems to be running (its folder is in use). Close it and run the '
                             'installer again; nothing was replaced.')
    incoming.rename(app)
    if old.exists():
        shutil.rmtree(old, ignore_errors=True)
    ui.say('      %d files' % count)

    # 2. Private Python environment (kept across upgrades).
    ui.step(2, total, 'Private Python environment')
    vpy = venv_python(target)
    base_python = sys.executable
    if vpy.exists() and previous and previous.get('base_python') == base_python:
        ui.say('      reusing %s' % vpy.parent.parent)
    else:
        if vpy.parent.parent.exists():
            try:
                shutil.rmtree(vpy.parent.parent)
            except OSError:
                raise SetupError('The private Python environment is in use. Close ARC-1 Workbench and run the '
                                 'installer again.')
        code, out = run([base_python, '-m', 'venv', str(vpy.parent.parent)], 600)
        if code != 0:
            raise SetupError('Could not create the Python environment:\n%s' % out[-800:])
        ui.say('      created %s' % vpy.parent.parent)

    # 3. Qt for the R10 window.
    ui.step(3, total, 'Qt for the Workbench window (%s)' % QT_REQUIREMENT)
    qt_ok = False
    if skip_qt:
        ui.say('      skipped (--skip-qt)')
    else:
        code, _ = run([str(vpy), '-c', 'import PySide6'], 120)
        if code == 0:
            qt_ok = True
            ui.say('      already installed')
        else:
            argv = [str(vpy), '-m', 'pip', 'install', '--disable-pip-version-check', '--no-input', QT_REQUIREMENT]
            bundled = wheels or (source / 'wheels' if (source / 'wheels').is_dir() else None)
            if bundled:
                argv += ['--no-index', '--find-links', str(bundled)]
            ui.say('      downloading and installing (about 100 MB; this takes a few minutes)...')
            code, out = run(argv, 1800)
            qt_ok = code == 0
            if not qt_ok:
                ui.say('      FAILED: %s' % out.strip().splitlines()[-1][:200] if out.strip() else '      FAILED')
                if sys.version_info[:2] > QT_MAX_PYTHON:
                    ui.say('      %s needs Python 3.11 to %d.%d; this is %s. Install Python 3.12 and re-run setup.'
                           % (QT_REQUIREMENT, *QT_MAX_PYTHON, sys.version.split()[0]))
                elif os.name == 'nt' and ('long path' in out.lower() or 'errno 2' in out.lower()):
                    ui.say('      The file paths may be too long for Windows. Re-run setup with a shorter '
                           '--target, e.g. C:\\ARC1.')
                else:
                    ui.say('      Check the internet connection (or a proxy), or install offline with --wheels.')
                ui.say('      Workbench will start the classic Tk window instead. Re-run setup to retry.')
            else:
                ui.say('      installed')

    # 4. C compiler for Build/Run.
    ui.step(4, total, 'C compiler for Build and Run')
    cc, extra = find_compiler()
    if not cc and plat.can_install_compiler():
        ui.say('      No C compiler found. Building firmware and games needs one (LLVM clang).')
        if ui.ask('      Install LLVM now with winget?', True):
            ok, out = plat.install_compiler(ui)
            cc, extra = find_compiler()
            if not ok and not cc:
                ui.say('      LLVM install did not complete: %s' % out.strip()[-200:])
    ui.say('      %s' % ('found %s' % cc if cc else 'NOT FOUND: Build and Run will report the missing compiler. '
                                                  'Install LLVM (clang) and re-run setup.'))

    # 5. Shortcuts, uninstaller, Apps & Features.
    ui.step(5, total, 'Shortcuts and uninstaller')
    spec = {'target': str(venv_python(target, windowed=True)), 'args': '-m workbench.launch',
            'workdir': str(app), 'icon': str(app / 'workbench' / 'arc1.ico'),
            'icon_png': str(app / 'workbench' / 'arc1_icon.png')}
    want_desktop = desktop and ui.ask('      Put a shortcut on the desktop too?', True)
    old_links = (previous or {}).get('shortcuts', [])
    plat.remove_shortcuts(old_links)
    try:
        links = plat.create_shortcuts(spec, want_desktop)
    except SetupError as e:
        links = []
        ui.say('      %s' % e)
        ui.say('      Start Workbench with %s' % (target / 'app' / 'START_ARC1_QT.cmd'))
    name, text = plat.uninstaller(target, base_python)
    unp = target / name
    unp.write_text(text, encoding='utf-8', newline='')
    if os.name != 'nt':
        unp.chmod(0o755)
    size_kb = sum(p.stat().st_size for p in target.rglob('*') if p.is_file()) // 1024
    try:
        plat.register(target, size_kb)
    except OSError as e:
        ui.say('      Apps & Features entry not created: %s' % e)
    for link in links:
        ui.say('      %s' % link)

    write_install(target, {'schema': SCHEMA, 'version': VERSION, 'installed': datetime.now().isoformat(timespec='seconds'),
                           'base_python': base_python, 'qt': qt_ok, 'compiler': cc, 'extra_path': [extra] if extra else [],
                           'shortcuts': links, 'manifest': manifest_of(app), 'backup': str(backup) if backup else None})

    # 6. Self-check through the SDK's own doctor.
    ui.step(6, total, 'Self-check')
    env = dict(os.environ)
    if extra:
        env['PATH'] = extra + os.pathsep + env.get('PATH', '')
    code, out = run([str(vpy), str(app / 'arc1'), 'doctor'], 300, env=env, cwd=str(app))
    first = out.strip().splitlines()[0] if out.strip() else 'no output'
    ui.say('      %s' % first)
    ui.say('')
    ui.say('%s is installed%s.' % (APP_NAME, '' if qt_ok else ' (classic Tk window: Qt is missing)'))
    ui.say('Start it from the %s%s.' % ('Start menu' if os.name == 'nt' else 'applications menu',
                                         ' or the desktop' if want_desktop else ''))
    ui.say('No ARC-1 board is needed or used: builds, tests and the game simulator run on this PC.')
    report = {'target': str(target), 'qt': qt_ok, 'compiler': cc, 'shortcuts': links, 'backup': backup,
              'doctor_exit': code}
    if launch is None:
        launch = ui.ask('Start %s now?' % APP_NAME, True)
    if launch:
        start_detached([str(venv_python(target, windowed=True)), '-m', 'workbench.launch'], str(app))
    return report


def start_detached(argv, cwd):
    kw = {'cwd': cwd, 'stdin': subprocess.DEVNULL, 'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    if os.name == 'nt':
        kw['creationflags'] = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kw['start_new_session'] = True
    try:
        subprocess.Popen(argv, **kw)
    except OSError:
        pass


# --------------------------------------------------------------------------- uninstall

def uninstall(target=None, assume_yes=False, ui=None, plat=None):
    ui = ui or Console(assume_yes)
    plat = plat or platform()
    target = Path(target or default_target()).resolve()
    info = read_install(target)
    if info is None:
        raise SetupError('No %s installation found in %s' % (APP_NAME, target))
    if Path.cwd().resolve() == target or target in Path.cwd().resolve().parents:
        os.chdir(tempfile.gettempdir())
    ui.say('')
    ui.say('Remove %s %s from %s?' % (APP_NAME, info.get('version', ''), target))
    if not ui.ask('Uninstall?', bool(ui.assume_yes)):   # --yes means yes; otherwise the default is No
        raise SetupError('Cancelled; nothing was removed')
    app = target / 'app'
    if app.is_dir():
        changed = user_changes(app, info.get('manifest', {}))
        if changed:
            backup_app(app, changed, ui, 'before uninstall')
        try:                                   # fails on Windows while Workbench has the folder open
            app.rename(target / 'app.removing')
        except OSError:
            raise SetupError('ARC-1 Workbench seems to be running. Close it and uninstall again; nothing was removed.')
    plat.remove_shortcuts(info.get('shortcuts', []))
    plat.unregister()
    shutil.rmtree(target, ignore_errors=True)
    if target.exists():
        ui.say('Some files were in use and remain in %s; close Workbench and delete the folder.' % target)
    else:
        ui.say('%s was removed. Your settings stay in your profile; your changed files (if any) were backed up.'
               % APP_NAME)
    return not target.exists()


# --------------------------------------------------------------------------- command line

def main(argv=None):
    p = argparse.ArgumentParser(prog='setup_arc1', description='Install or remove %s for this user.' % APP_NAME)
    sub = p.add_subparsers(dest='cmd', required=True)
    i = sub.add_parser('install')
    i.add_argument('--source', default=str(Path(__file__).resolve().parents[1]))
    i.add_argument('--target')
    i.add_argument('--yes', action='store_true', help='accept every default without asking')
    i.add_argument('--no-desktop', action='store_true')
    i.add_argument('--wheels', help='install Qt from this folder of wheels (offline)')
    i.add_argument('--skip-qt', action='store_true')
    i.add_argument('--no-launch', action='store_true')
    u = sub.add_parser('uninstall')
    u.add_argument('--target')
    u.add_argument('--yes', action='store_true')
    a = p.parse_args(argv)
    try:
        if a.cmd == 'install':
            install(a.source, a.target, a.yes, not a.no_desktop, a.wheels, a.skip_qt,
                    launch=False if a.no_launch else None)
        else:
            uninstall(a.target, a.yes)
    except SetupError as e:
        print('\n' + str(e))
        return 1
    except KeyboardInterrupt:
        print('\nStopped.')
        return 1
    except OSError as e:
        print('\nSetup stopped: %s\nIf ARC-1 Workbench is open, close it and run setup again.' % e)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
