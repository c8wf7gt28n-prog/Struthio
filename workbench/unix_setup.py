"""Guided per-project setup. Standard library only; no system Python writes."""
from __future__ import annotations
import argparse, datetime, json, os, platform, plistlib, shlex, shutil, subprocess, sys
from pathlib import Path
from . import locations
from .version import VERSION as GRAPHITE_VERSION

ROOT=Path(__file__).resolve().parents[1]
QT_VERSION='6.8.1'

def compatibility(system=None,release=None,version=None,machine=None):
    system=system or platform.system();version=version or sys.version_info[:2]
    machine=machine or platform.machine();issues=[]
    if not (3,11)<=tuple(version)<(3,14):
        issues.append('Use Python 3.11–3.13. Qt 6.8.1 does not support Python 3.14.')
    if system=='Darwin':
        release=release if release is not None else platform.mac_ver()[0]
        if not release or int(release.split('.')[0])<12:
            issues.append('This build requires macOS 12 Monterey or later. No OS upgrade is performed automatically.')
    elif system!='Linux':issues.append('Use this setup on Linux or macOS; Windows launchers remain separate.')
    if machine not in ('x86_64','AMD64','arm64','aarch64'):issues.append('Unqualified wheel architecture: '+machine)
    return issues

def run(argv,root=ROOT,timeout=600,env=None):
    result=subprocess.run([str(a) for a in argv],cwd=root,text=True,stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,timeout=timeout,env=env)
    folder=root/'.ledger/setup';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'install.log').open('a',encoding='utf-8') as stream:
        stream.write('\n'+shlex.join([str(a) for a in argv])+'\n'+result.stdout+'\nexit='+str(result.returncode)+'\n')
    if result.stdout:print(result.stdout,end='',flush=True)
    if result.returncode:raise RuntimeError('Command failed (exit %d). Details: %s'%(result.returncode,folder/'install.log'))
    return result

def write_preserved(path,content):
    path.parent.mkdir(parents=True,exist_ok=True);data=content.encode() if isinstance(content,str) else content
    if path.exists() and path.read_bytes()!=data:
        stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        shutil.copy2(path,path.with_name(path.name+'.backup-'+stamp))
    path.write_bytes(data)

def desktop_quote(value):
    if '\n' in value or '\r' in value:raise ValueError('Newlines in project path are unsupported')
    return '"'+value.replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"'

def shortcuts(root=ROOT,home=None,system=None):
    home=Path(home) if home else Path.home();system=system or platform.system()
    python=root/'.venv/bin/python';result=[]
    if system=='Darwin':
        # Graphite 0.1: the shown names are Graphite; the bundle, launcher and menu file names stay, so an earlier install is updated in place.
        bundle=home/'Applications/Arc Ledger.app';executable=bundle/'Contents/MacOS/ArcLedger'
        script='#!/bin/bash\ncd '+shlex.quote(str(root))+' || exit 1\nexec '+shlex.quote(str(python))+' -m workbench.launch\n'
        write_preserved(executable,script);executable.chmod(0o755)
        write_preserved(bundle/'Contents/Info.plist',plistlib.dumps(dict(CFBundleName='Graphite',
            CFBundleDisplayName='Graphite',CFBundleIdentifier='local.arcledger.desktop',
            CFBundleExecutable='ArcLedger',CFBundlePackageType='APPL',CFBundleVersion=GRAPHITE_VERSION,NSHighResolutionCapable=True)))
        result.append(str(bundle))
    else:
        desktop=home/'.local/share/applications/arc-ledger.desktop'
        text='[Desktop Entry]\nType=Application\nName=Graphite\nComment=The Graphite workspace and its assistant\nExec='+desktop_quote(str(python))+' -m workbench.launch\nPath='+str(root)+'\nIcon='+str(locations.program(root)/'branding/graphite/graphite_icon_256.png')+'\nTerminal=false\nCategories=Development;Engineering;\n'
        write_preserved(desktop,text);desktop.chmod(0o755);result.append(str(desktop))
        menu=home/'.fluxbox/arc-ledger-menu'
        write_preserved(menu,'[begin] (Graphite)\n[exec] (Graphite) {'+shlex.quote(str(python))+' -m workbench.launch}\n[end]\n')
        result.append(str(menu))
    return result

def qt_check(python,root=ROOT,offscreen=False):
    env=dict(os.environ)
    if offscreen:env['QT_QPA_PLATFORM']='offscreen'
    code=('from PySide6.QtWidgets import QApplication,QLabel; from PySide6.QtCore import QTimer; '
          'a=QApplication([]); w=QLabel("Graphite setup check"); w.show(); '
          'QTimer.singleShot(300,a.quit); a.exec(); print("LEDGER_QT_CHECK_OK")')
    return run([python,'-c',code],root,timeout=30,env=env)

def install(root=ROOT,offline=False,offscreen=False,add_shortcuts=True):
    problems=compatibility()
    if problems:raise RuntimeError('\n'.join(problems))
    root=Path(root).resolve();envdir=root/'.venv';python=envdir/'bin/python'
    print('Graphite setup · '+platform.system()+' · '+platform.machine(),flush=True)
    print('Project: '+str(root)+'\nPrivate environment: '+str(envdir),flush=True)
    if envdir.exists():
        if not python.is_file():raise RuntimeError('Existing .venv is incomplete. Rename it to .venv-old and rerun setup; keep all project files.')
        probe=run([python,'-c','import sys; print(sys.prefix); raise SystemExit(0 if (3,11)<=sys.version_info[:2]<(3,14) else 2)'],root,30)
        if Path(probe.stdout.strip())!=envdir:raise RuntimeError('Environment belongs to a moved project. Rename .venv to .venv-old and rerun setup.')
    else:
        print('1/4 Creating private Python environment…',flush=True);run([sys.executable,'-m','venv',envdir],root)
    print('2/4 Installing pinned Qt (first download about 100–170 MB)…',flush=True)
    argv=[python,'-m','pip','install','--disable-pip-version-check','--only-binary=:all:']
    if offline:argv+=['--no-index','--find-links',str(root/'wheels')]
    run(argv+['PySide6-Essentials=='+QT_VERSION,'shiboken6=='+QT_VERSION],root)
    print('3/4 Checking actual Qt display plugin…',flush=True);qt_check(python,root,offscreen)
    links=shortcuts(root) if add_shortcuts else []
    report=dict(platform=platform.platform(),architecture=platform.machine(),python=sys.version,project=str(root),
        qt=QT_VERSION,display_check='offscreen' if offscreen else 'native session',shortcuts=links,status='PASS',
        scope='Setup and Qt window only; engineering qualification is separate')
    (root/'.ledger/setup/result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('4/4 Setup complete. Use START_ARC_LEDGER_UNIX.sh or the application shortcut.',flush=True)
    for link in links:print('Shortcut: '+link)
    return report

def doctor(root=ROOT):
    result=dict(platform=platform.platform(),architecture=platform.machine(),python=sys.version,issues=compatibility(),
        project=str(root),tools={name:shutil.which(name) for name in ('cc','make','node','git','kicad-cli','iverilog','tailscale')},
        environment_exists=(root/'.venv/bin/python').is_file(),native_platform_qualified=False)
    print(json.dumps(result,indent=2));return result

def main():
    p=argparse.ArgumentParser(description='Graphite guided Unix setup');p.add_argument('action',choices=['install','doctor','shortcuts'])
    p.add_argument('--offline',action='store_true');p.add_argument('--offscreen',action='store_true');p.add_argument('--no-shortcuts',action='store_true');a=p.parse_args()
    try:
        if a.action=='doctor':doctor()
        elif a.action=='shortcuts':print('\n'.join(shortcuts()))
        else:install(offline=a.offline,offscreen=a.offscreen,add_shortcuts=not a.no_shortcuts)
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as exc:
        print('\nSETUP STOPPED: '+str(exc)+'\nProject and hardware sources were not replaced. See START_HERE.html.',file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
