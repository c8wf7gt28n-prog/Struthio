"""Atomic recovery copies. Source files are never written by this store."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
from .project_services import project_path


def file_hash(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


class RecoveryStore:
    def __init__(self, root, config):
        self.root = Path(root).resolve()
        ident = hashlib.sha256(str(self.root).encode()).hexdigest()[:20]
        self.folder = Path(config)/'recovery'/ident

    def slot(self, relative):
        project_path(self.root,relative)
        return self.folder/(hashlib.sha256(relative.encode()).hexdigest()+'.json')

    def put(self, relative, content, base_sha256):
        if len(content.encode('utf-8')) > 2*1024*1024:
            raise ValueError('Recovery buffer exceeds 2 MiB')
        slot = self.slot(relative)
        data = json.dumps({'schema':'arc1.buffer/1','path':relative,'content':content,
                           'base_sha256':base_sha256},ensure_ascii=False)
        if slot.is_file() and slot.read_text(encoding='utf-8') == data:
            return
        self.folder.mkdir(parents=True,exist_ok=True)
        fd,tmp = tempfile.mkstemp(prefix='.buffer-',dir=self.folder)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp,slot)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def remove(self, relative):
        self.slot(relative).unlink(missing_ok=True)

    def entries(self):
        entries=[]
        for p in sorted(self.folder.glob('*.json'))[:100]:
            try:
                if p.stat().st_size > 3*1024*1024:continue
                record=json.loads(p.read_text(encoding='utf-8'))
                if record.get('schema') != 'arc1.buffer/1' or not isinstance(record.get('content'),str):continue
                source=project_path(self.root,record['path'])
                if p != self.slot(record['path']):continue
                record['disk_changed']=file_hash(source)!=record.get('base_sha256')
                entries.append(record)
            except (OSError,ValueError,KeyError,TypeError):
                continue
        return entries
