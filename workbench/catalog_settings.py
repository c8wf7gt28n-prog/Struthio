"""Presentation adapter over the connected catalogue; never initializes a store.

Catalogue and Kernel journals are separate databases. The existing delivery
receipt reconciles an observed write after interruption; it never replays one.
"""
from contextlib import closing
import sqlite3
from sdk.cli.arc1cli.concern_catalog import view_preference, write_view_preference


def path(kernel):
    from .ledger_control import session
    return session(kernel).path.parent/'concern'/'catalog.sqlite3'


def read(kernel):
    target=path(kernel)
    try:
        with closing(sqlite3.connect(target.resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as db:
            if db.execute('PRAGMA user_version').fetchone()[0] not in (0,1):raise ValueError('Unsupported catalogue version')
            return view_preference(db)
    except (OSError,sqlite3.Error,ValueError,TypeError) as exc:
        raise ValueError('Existing catalogue unavailable; other settings remain available. Original retained.') from exc


def write(kernel,value,expected_revision,revision_token):
    target=path(kernel)
    try:
        # mode=rw will not create a missing store or seed catalogue records.
        with closing(sqlite3.connect(target.resolve().as_uri()+'?mode=rw',uri=True,timeout=5)) as db:
            with db:
                db.execute('BEGIN IMMEDIATE')
                if db.execute('PRAGMA user_version').fetchone()[0] not in (0,1):raise ValueError('Unsupported catalogue version')
                write_view_preference(db,value,expected_revision,revision_token)
    except (OSError,sqlite3.Error) as exc:
        raise ValueError('Existing catalogue unavailable; original retained.') from exc
