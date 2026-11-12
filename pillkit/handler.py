"""The workstation's pill handler: small, separate from Ledger, and the only thing that may change your originals.

    python3 -m pillkit.handler init --name "Workstation"         make this computer's pill identity (once)
    python3 -m pillkit.handler card                              print its identity card, to give to Ledger
    python3 -m pillkit.handler pair ledger-card.json             pair with Ledger; compare the code on both screens
    python3 -m pillkit.handler prepare ~/Projects/clock --to Ledger --task "Review the clock board" \\
                                       --ask inspect,analyze,propose_revisions -o clock.pill
    python3 -m pillkit.handler review result.pill                what came back, file by file, with a text diff
    python3 -m pillkit.handler save-new result.pill ~/Projects/clock-reviewed    the proposal as a new folder
    python3 -m pillkit.handler apply result.pill                 apply it to the original, after you say yes
    python3 -m pillkit.handler undo <pill id>                    put the original back as it was
    python3 -m pillkit.handler resume                            finish an apply that was interrupted

What it never does: run anything a pill contains, open a shell, share a folder, or write outside the original the
request was made from. Approval to export on Ledger is not approval to overwrite here: `apply` asks again, checks that
each file is still exactly what was sent, and keeps every replaced or removed file so `undo` can put it back.

Its state lives in ~/.config/ledger-pills (or $LEDGER_PILLS_HOME), readable by you only.
"""
from __future__ import annotations
import argparse
import difflib
import json
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from . import pill as P

CRASH_AFTER = None   # tests only: stop an apply after this many changes, as a power cut would


def home():
    return Path(os.environ.get('LEDGER_PILLS_HOME') or Path.home() / '.config' / 'ledger-pills')


def keyring(name=None):
    return P.Keyring(home(), name)


def say(*words):
    print(*words, flush=True)


# -- preparing a request ---------------------------------------------------------------------------------------------

def prepare(source, to, title, purpose='', ask=('inspect', 'analyze', 'propose_revisions'), expect=('findings', 'candidate_files'), out=None):
    """A request pill from a folder or one file. The exact bytes sent are kept here, so a result can be compared,
    and so `save-new` works even if the original has changed since."""
    ring = keyring();source = Path(source).expanduser().resolve()
    found, skipped = P.scan_folder(source)
    files = {rel: path.read_bytes() for rel, path in found.items()}
    listing = {rel: {'sha256': P.sha256(d), 'bytes': len(d)} for rel, d in files.items()}
    task = {'id': uuid.uuid4().hex, 'title': title[:200], 'purpose': purpose[:4000]}
    c = P.contract(ring, ring.peer(to)[0], 'request', task, source.name, listing, ask, expect)
    raw = P.build(ring, c, files)
    sent = home() / 'sent';sent.mkdir(mode=0o700, exist_ok=True)
    P.write_private(sent / (c['id'] + '.pill'), raw)
    log = P.read_state(home() / 'requests.json', {})
    log[c['id']] = {'source': str(source), 'single_file': source.is_file(), 'task': task, 'revision': c['source']['revision'], 'at': time.time()}
    P.write_state(home() / 'requests.json', log)
    out = Path(out or (source.parent / (source.name + '.pill'))).expanduser()
    if out.exists():P.refuse('PILL_EXISTS', '%s already exists; choose another name' % out)
    P.write_private(out, raw)
    return {'pill': c['id'], 'path': str(out), 'files': len(files), 'skipped': skipped}


# -- reading a result -----------------------------------------------------------------------------------------------

def load_result(path, replay=False):
    """Open a result pill and find the request it answers. Nothing is written. Reading it again is fine; applying it
    twice is not (apply checks replays and remembers the pill)."""
    ring = keyring();raw = Path(path).expanduser().read_bytes()
    result = P.open_pill(raw, ring, expect_kind='result', replay=replay)
    log = P.read_state(home() / 'requests.json', {});request = log.get(result.contract['in_reply_to'])
    if request is None:P.refuse('PILL_NO_REQUEST', 'this answers a request this computer did not send')
    if result.contract['source']['revision'] != request['revision']:P.refuse('PILL_REVISION', 'it answers a different revision than the one sent')
    return ring, result, request


def target_root(request):
    source = Path(request['source'])
    return source.parent if request['single_file'] else source


def current(root, rel):
    path = root / rel
    if path.is_symlink():return 'link'
    if not path.exists():return ''
    if not path.is_file():return 'not-a-file'
    return P.sha256(path.read_bytes())


def plan(result, request):
    """Each change, with what the original holds now. A change is clear only if the file is exactly as sent."""
    root = target_root(request);rows = []
    for ch in result.contract['result']['changes']:
        now = current(root, ch['path'])
        rows.append({**ch, 'now': now, 'clear': now == ch['before']})
    return root, rows


def text_of(data):
    if data is None or len(data) > 1024 * 1024 or b'\x00' in data[:4096]:return None
    try:return data.decode('utf-8')
    except UnicodeDecodeError:return None


def sent_files(request_id):
    raw = (home() / 'sent' / (request_id + '.pill')).read_bytes()
    members = P.read_members(raw)
    return {n[6:]: d for n, d in members.items() if n.startswith('files/')}


def review(path, out=None):
    out = out or sys.stdout
    ring, result, request = load_result(path);c = result.contract;root, rows = plan(result, request)
    base = sent_files(c['in_reply_to'])
    w = lambda *t:print(*t, file=out)
    w('Result for "%s" from %s (pill %s)' % (c['task']['title'], c['sender']['name'], c['id']))
    w('Original: %s' % root)
    if c['result']['findings'].strip():w('\nFindings\n' + c['result']['findings'].strip())
    if result.notes:w('\nEvidence notes: ' + ', '.join(sorted(result.notes)))
    w('\nChanges')
    if not rows:w('  none: findings only')
    for r in rows:
        state = 'as sent' if r['clear'] else ('CHANGED HERE since it was sent' if r['now'] not in ('', 'link', 'not-a-file') else
                                              'MISSING HERE' if r['now'] == '' else 'NOT AN ORDINARY FILE HERE')
        if r['op'] == 'create':state = 'new' if r['clear'] else 'ALREADY EXISTS HERE'
        w('  %-7s %s   (%s)' % (r['op'], r['path'], state))
    for r in rows:
        before = text_of(base.get(r['path'])) if r['op'] != 'create' else ''
        after = text_of(result.files.get(r['path'])) if r['op'] != 'delete' else ''
        if before is None or after is None:continue
        diff = difflib.unified_diff(before.splitlines(), after.splitlines(), 'sent/' + r['path'], 'proposed/' + r['path'], lineterm='', n=2)
        lines = list(diff)
        if lines:w('');[w(line) for line in lines[:400]]
    conflicts = [r for r in rows if not r['clear']]
    w('\n' + ('Clear to apply: every file is exactly as sent.' if not conflicts else
              '%d file(s) changed here since: apply is refused; use save-new and compare.' % len(conflicts)))
    return {'changes': len(rows), 'conflicts': len(conflicts)}


def save_new(path, dest):
    """The proposal as a new folder: the files as sent, with the result's changes. The original is not touched."""
    _, result, request = load_result(path);dest = Path(dest).expanduser()
    if dest.exists():P.refuse('PILL_EXISTS', '%s already exists; save-new never overwrites' % dest)
    files = sent_files(result.contract['in_reply_to'])
    for ch in result.contract['result']['changes']:
        if ch['op'] == 'delete':files.pop(ch['path'], None)
        else:files[ch['path']] = result.files[ch['path']]
    dest.mkdir(parents=True, mode=0o700)
    for rel, data in files.items():
        target = dest / rel;target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'xb') as f:f.write(data)
    for name, data in result.notes.items():
        notes = dest / ('%s notes' % result.contract['sender']['name']);notes.mkdir(exist_ok=True)
        with open(notes / name, 'xb') as f:f.write(data)
    return {'path': str(dest), 'files': len(files)}


# -- applying, with a journal --------------------------------------------------------------------------------------

def journal_path(pill_id):
    return home() / 'journal' / (pill_id + '.json')


def fsync_dir(folder):
    try:
        fd = os.open(str(folder), os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    except OSError:pass


def apply(path, confirm=input):
    """Apply a result to the original, all of it or none of it in effect:
      1. every touched file must be exactly as sent (else refused: save-new instead),
      2. you say yes,
      3. new contents are written beside each file and the replaced files are kept, with a journal recording each step,
      4. then each file is swapped in by rename; after each swap the journal is updated.
    If the computer stops part-way, `resume` finishes from the journal; `undo` puts everything back."""
    ring, result, request = load_result(path, replay=True);c = result.contract;root, rows = plan(result, request)
    if journal_path(c['id']).exists():P.refuse('PILL_ALREADY_APPLIED', 'this result was already applied here (undo it first, or resume)')
    conflicts = [r['path'] for r in rows if not r['clear']]
    if conflicts:P.refuse('PILL_CONFLICT', 'changed here since it was sent: %s. Nothing was applied; use save-new and compare.' % ', '.join(conflicts[:8]))
    if not rows:ring.remember(c['sender']['key'], c['id'], c['sequence']);return {'applied': 0, 'note': 'findings only: nothing to apply'}
    answer = confirm('Apply %d change(s) from %s to %s? Type yes: ' % (len(rows), c['sender']['name'], root))
    if str(answer).strip().lower() != 'yes':return {'applied': 0, 'note': 'not applied: you did not say yes'}
    keep = home() / 'kept' / c['id'];keep.mkdir(parents=True, mode=0o700)
    ops = []
    for r in rows:
        target = root / r['path'];op = {'op': r['op'], 'path': r['path'], 'before': r['before'], 'after': r['after'], 'stage': 'planned', 'temp': '', 'kept': '', 'made_dirs': []}
        if r['op'] != 'create':
            kept = keep / ('%04d' % len(ops));shutil.copyfile(target, kept);op['kept'] = str(kept)
            if P.sha256(kept.read_bytes()) != r['before']:P.refuse('PILL_CONFLICT', 'changed while being read: %s' % r['path'])
        if r['op'] != 'delete':
            parent = target.parent;missing = []
            while not parent.exists():missing.append(parent);parent = parent.parent
            for d in reversed(missing):d.mkdir(mode=0o755);op['made_dirs'].append(str(d))
            temp = target.with_name('.%s.pill-%s.part' % (target.name, c['id'][:8]))
            with open(temp, 'xb') as f:f.write(result.files[r['path']]);f.flush();os.fsync(f.fileno())
            if r['op'] == 'replace':shutil.copymode(target, temp)
            op['temp'] = str(temp)
        op['stage'] = 'prepared';ops.append(op)
    ring.remember(c['sender']['key'], c['id'], c['sequence'])  # from here on this pill is spent
    record = {'pill': c['id'], 'root': str(root), 'task': c['task']['title'], 'from': c['sender']['name'], 'state': 'prepared', 'ops': ops, 'at': time.time()}
    P.write_state(journal_path(c['id']), record)
    return finish(record)


def finish(record):
    done = 0
    for op in record['ops']:
        if op['stage'] == 'done':continue
        if CRASH_AFTER is not None and done >= CRASH_AFTER:raise SystemExit('simulated stop')
        target = Path(record['root']) / op['path']
        if op['op'] == 'delete':
            if target.exists():os.unlink(target)
        else:
            if op['op'] == 'create' and target.exists() and P.sha256(target.read_bytes()) != op['after']:
                P.refuse('PILL_CONFLICT', '%s appeared here meanwhile; resume stopped, nothing else changed' % op['path'])
            if Path(op['temp']).exists():os.replace(op['temp'], target)
        fsync_dir(target.parent);op['stage'] = 'done';done += 1
        record['state'] = 'applying';P.write_state(journal_path(record['pill']), record)
    record['state'] = 'done';record['finished'] = time.time();P.write_state(journal_path(record['pill']), record)
    return {'applied': len(record['ops']), 'root': record['root'], 'undo': 'python3 -m pillkit.handler undo ' + record['pill']}


def resume():
    folder = home() / 'journal';out = []
    for path in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        record = json.loads(path.read_text())
        if record['state'] in ('prepared', 'applying'):out.append(finish(record))
    return out


def undo(pill_id):
    """Put the original back: replaced and removed files from what was kept, new files removed (only if unchanged since)."""
    path = journal_path(pill_id)
    if not path.exists():P.refuse('PILL_NOT_APPLIED', 'nothing was applied from that pill here')
    record = json.loads(path.read_text())
    if record['state'] == 'undone':P.refuse('PILL_NOT_APPLIED', 'that apply was already undone')
    left = []
    for op in reversed(record['ops']):
        target = Path(record['root']) / op['path']
        if op['temp'] and Path(op['temp']).exists():os.unlink(op['temp'])
        if op['stage'] != 'done':continue
        if op['op'] == 'create':
            if target.exists() and P.sha256(target.read_bytes()) == op['after']:os.unlink(target)
            elif target.exists():left.append(op['path'])
            for d in reversed(op['made_dirs']):
                try:os.rmdir(d)
                except OSError:pass
        else:
            if op['op'] == 'replace' and target.exists() and P.sha256(target.read_bytes()) != op['after']:left.append(op['path']);continue
            temp = target.with_name('.%s.pill-undo.part' % target.name);shutil.copy2(op['kept'], temp);os.replace(temp, target)
    record['state'] = 'undone';record['left_alone'] = left;P.write_state(path, record)
    return {'undone': record['pill'], 'left_alone': left}


# -- the command line ----------------------------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(prog='pillkit.handler', description='Exchange pills with Graphite. Nothing here runs what a pill contains.')
    sub = ap.add_subparsers(dest='command', required=True)
    s = sub.add_parser('init');s.add_argument('--name', default=os.uname().nodename if hasattr(os, 'uname') else 'Workstation')
    sub.add_parser('card')
    s = sub.add_parser('pair');s.add_argument('card')
    sub.add_parser('peers')
    s = sub.add_parser('prepare');s.add_argument('source');s.add_argument('--to', required=True);s.add_argument('--task', required=True)
    s.add_argument('--purpose', default='');s.add_argument('--ask', default='inspect,analyze,propose_revisions');s.add_argument('--expect', default='findings,candidate_files');s.add_argument('-o', '--out')
    s = sub.add_parser('review');s.add_argument('pill')
    s = sub.add_parser('save-new');s.add_argument('pill');s.add_argument('dest')
    s = sub.add_parser('apply');s.add_argument('pill')
    s = sub.add_parser('undo');s.add_argument('pill_id')
    sub.add_parser('resume')
    a = ap.parse_args(argv)
    try:
        if a.command == 'init':ring = keyring(a.name);say('This computer is "%s", key %s.' % (ring.name, ring.key));say('Give Ledger its card:  python3 -m pillkit.handler card > workstation-card.json')
        elif a.command == 'card':say(json.dumps(keyring().card(), indent=1))
        elif a.command == 'pair':
            got = keyring().pair(json.loads(Path(a.card).expanduser().read_text()))
            say('Paired with "%s" (key %s).' % (got['name'], got['key']));say('Pairing code: %s  — Ledger must show the same code. If it does not, unpair at once.' % got['code'])
        elif a.command == 'peers':
            for key, v in keyring().peers().items():say('%s  %s' % (key, v['name']))
        elif a.command == 'prepare':
            got = prepare(a.source, a.to, a.task, a.purpose, a.ask.split(','), [x for x in a.expect.split(',') if x], a.out)
            say('Request pill %s: %d file(s) → %s' % (got['pill'], got['files'], got['path']))
            for rel, why in got['skipped']:say('  left out: %s (%s)' % (rel, why))
        elif a.command == 'review':review(a.pill)
        elif a.command == 'save-new':got = save_new(a.pill, a.dest);say('Saved %d file(s) as %s. The original was not touched.' % (got['files'], got['path']))
        elif a.command == 'apply':got = apply(a.pill);say(json.dumps(got, indent=1))
        elif a.command == 'undo':say(json.dumps(undo(a.pill_id), indent=1))
        elif a.command == 'resume':say(json.dumps(resume(), indent=1))
    except P.PillError as exc:
        say('Refused. ' + str(exc));return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
