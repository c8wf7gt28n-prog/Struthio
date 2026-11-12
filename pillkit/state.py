"""Persistent counters and replay claims; imported legacy history is never pruned."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import sqlite3


@contextmanager
def lock(folder,name='identity'):
    fd=os.open(Path(folder)/(name+'.lock'),os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:fcntl.flock(fd,fcntl.LOCK_EX);yield
    finally:os.close(fd)


@contextmanager
def database(folder):
    path=Path(folder)/'state.sqlite3'
    if path.is_symlink():raise ValueError('Linked pill state refused')
    db=sqlite3.connect(path,timeout=10)
    try:
        with db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS version(value INTEGER PRIMARY KEY)')
            versions=[r[0] for r in db.execute('SELECT value FROM version')]
            if versions and versions!=[1]:raise ValueError('PILL_STATE_VERSION_UNSUPPORTED')
            db.execute('CREATE TABLE IF NOT EXISTS counter(id INTEGER PRIMARY KEY,value INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS seen(sender TEXT NOT NULL,id TEXT NOT NULL,sequence INTEGER NOT NULL,UNIQUE(sender,id),UNIQUE(sender,sequence))')
            if not versions:
                def old(name,default):
                    p=Path(folder)/name
                    return json.loads(p.read_text()) if p.exists() else default
                db.execute('INSERT INTO counter VALUES(1,?)',(old('sent.json',{}).get('sequence',0),))
                # The old format kept separate lists, not their pairings. Preserve both exclusion sets.
                for sender,row in old('seen.json',{}).items():
                    for i,ident in enumerate(row.get('ids',[])):db.execute('INSERT OR IGNORE INTO seen VALUES(?,?,?)',(sender,ident,-1-i))
                    for sequence in row.get('sequences',[]):db.execute('INSERT OR IGNORE INTO seen VALUES(?,?,?)',(sender,'legacy-sequence-'+str(sequence),sequence))
                db.execute('INSERT INTO version VALUES(1)')
            yield db
        path.chmod(0o600)
    finally:db.close()
