"""Shared, bounded project retrieval for the desktop and structured agent API.

No network, tool execution or hardware changes. Search results describe saved
files; unsaved buffers are deliberately not silently shared with agents.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

TEXT = {'.c','.h','.s','.cpp','.hpp','.sv','.v','.vhd','.lpf','.ld','.py','.md',
        '.txt','.json','.csv','.jsonl','.xml','.yaml','.yml','.cmd','.sh','.js','.mjs','.css',
        '.html','.webmanifest','.kicad_sch','.kicad_pcb','.kicad_pro','.log'}
SKIP = {'.git','__pycache__','.venv','node_modules','build','dist','.pytest_cache'}
MAX_FILE = 2*1024*1024


def project_path(root, value):
    if not isinstance(value, str) or not value or '\x00' in value or '\\' in value:
        raise ValueError('Expected a relative project path')
    rel = Path(value)
    if rel.is_absolute() or '..' in rel.parts or ':' in value:
        raise ValueError('Path must stay inside the project')
    root = Path(root).resolve()
    p = root / rel
    if p.is_symlink() or not p.resolve().is_relative_to(root):
        raise ValueError('Linked or external paths are unavailable')
    return p


def iter_files(root, archives=False):
    root = Path(root).resolve()
    count = 0
    for folder, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP and not d.startswith('.')
                         and (archives or d not in {'archive','sources','imports','imported'})
                         and not (Path(folder)/d).is_symlink())
        for name in sorted(names):
            p = Path(folder)/name
            if p.is_symlink() or name.startswith('.'):
                continue
            count += 1
            if count > 15000:
                return
            yield p


def search(root, query, *, archives=False, case_sensitive=False, limit=300, cancelled=None):
    if not isinstance(query,str) or not 1 <= len(query.strip()) <= 200:
        raise ValueError('Search needs 1–200 characters')
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError('Search limit must be 1–500')
    root = Path(root).resolve()
    needle = query if case_sensitive else query.lower()
    matches, scanned, skipped = [], 0, 0
    for p in iter_files(root, archives):
        if cancelled and cancelled():
            return {'matches':matches,'scanned':scanned,'skipped':skipped,'truncated':True,'cancelled':True}
        if p.suffix.lower() not in TEXT and p.name not in ('Makefile','GNUmakefile'):
            continue
        try:
            if p.stat().st_size > MAX_FILE:
                skipped += 1
                continue
            raw = p.read_bytes()
            if b'\x00' in raw:
                continue
            content = raw.decode('utf-8')
        except (OSError,UnicodeError):
            skipped += 1
            continue
        scanned += 1
        digest = hashlib.sha256(raw).hexdigest()
        for line, text in enumerate(content.splitlines(),1):
            hay = text if case_sensitive else text.lower()
            col = hay.find(needle)
            if col >= 0:
                matches.append({'path':p.relative_to(root).as_posix(),'line':line,'column':col+1,
                                'preview':text.strip()[:240],'sha256':digest})
                if len(matches) >= limit:
                    return {'matches':matches,'scanned':scanned,'skipped':skipped,'truncated':True,'cancelled':False}
    return {'matches':matches,'scanned':scanned,'skipped':skipped,'truncated':False,'cancelled':False}


def overview(root):
    from . import hardware_nav, readiness
    root = Path(root).resolve()
    task_path = root/'project/workplan.json'
    try:
        if task_path.stat().st_size > MAX_FILE:
            raise ValueError('Workplan too large')
        plan = json.loads(task_path.read_text(encoding='utf-8'))
    except (OSError,ValueError):
        plan = {'tasks':[], 'release':'unknown'}
    devices = []
    for device, groups in hardware_nav.catalog(root):
        devices.append({'id':device.id,'title':device.title,'role':device.role,
                        'groups':[{'name':g.title,'paths':[p.relative_to(root).as_posix() for p in paths]}
                                  for g,paths in groups]})
    return {'schema':'arc1.project/1','release':plan.get('release'), 'purpose':plan.get('purpose'),
            'tasks':plan.get('tasks',[]),'devices':devices,'readiness':readiness.snapshot(root),
            'simulation_scope':'Host gameplay + behavioral system model; not full silicon emulation',
            'clip_scope':'Chat assistant; structured agent services are separate, opt-in clients',
            'workplan':'project/workplan.json'}
