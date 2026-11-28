"""The box's narrow operations (Graphite 1.1 KS1): what her recipes do on the computer, each a registered Kernel operation.

PLAN_1.1.md, KS1: "A library of verified, parameterised recipes (preconditions, steps through registered tools, a dry run, a
verifier, an undo)". The coordinator's note: "Where a step needs a program (ImageMagick's convert, qpdf, zip), register a
narrow Kernel operation with a fixed argv shape for it, classified read or change, never a shell string; if the program is
missing, the recipe says which Debian package has it and stops."

EVERY OPERATION HERE IS ONE OF TWO KINDS.
  read     reads the disk, /proc or a program's own report, and changes nothing. A read runs on its own; its answer is
           data ({rows, words, checked, verified}). Its verifier reads again what it listed (a size, a file still there).
  change   execute scope (the owner's press), or approve for what cannot be undone (emptying DELETE). Each takes `expect`,
           the digest of its own dry run (plan()): it plans again, and when what it would do is not what you were shown
           it refuses and changes nothing. It writes down what it is to do before it acts, acts file by file, checks each
           effect on the disk (the verifier), and writes down what Undo needs (undo()). It never writes over a file: a new
           file takes a free name ("photo 2.png"); a program writes to a fresh name of its own first, and the result is
           linked to its final name only when that name is still free. It touches your home only (never Graphite's own
           records, a system folder, DELETE's own folder or anything outside your home), and a backup also a drive.
           A change is never her work on her own: dispatched in her work (a step, a grant's permit, her hand) it is
           refused; HALT stops it at the next file, and what was done is recorded and can be undone.

PROGRAMS, ALWAYS AS AN ARGV OF A FIXED SHAPE (never a shell string), found only in /usr/local/bin, /usr/bin and /bin:
  pictures   ImageMagick (`magick`, or `convert`): [prog, FORMAT:<input>, -auto-orient, (-resize WxH>), FORMAT:<output>].
             The input's format is read from its own first bytes (PNG, JPEG, GIF, BMP, WEBP, TIFF) and named, so a file is
             read only by the decoder of what it is. Debian package: imagemagick.
  PDFs       poppler-utils: [pdfunite, in..., out], [pdfseparate, in, folder/page-%d.pdf], [pdfinfo, in]. Names holding
             % or a newline are refused (pdfseparate's pattern).
  system     [apt-get, --simulate, upgrade] (no root, no network: the package lists already on this computer);
             [lsblk, --json, --bytes, --output, ...]; [systemctl, --failed, ...]; [ip, -json, address, show].
  zip        Python's own zipfile (no program): members with an absolute path, '..', or a link are left out and named.

Kernel operations (one block in engineering_kernel.py and engineering_cli.py, commented 1.1 KS1):
  box.files.find {folder, how, size?, since?, days?, words?, most?}  read   big, duplicates, changed, name, words, empty, old, kinds
  box.space {folder?}                       read     what takes the space, and how full the disk is
  box.memory {} / box.processor {}          read     what uses memory / the processor, by program, from /proc
  box.system {what}                         read     updates, disks, autostart, about, battery, network, failed
  box.pdf.info {path} / box.zip.list {path} read     a PDF's pages; what is inside a zip
  box.bin.list {}                           read     what is in DELETE
  box.pictures.make {folder, kinds?, format?, size?, expect}   execute  new pictures beside the old (converted, resized)
  box.pdf.merge {folder, paths?, name?, expect}                execute  one new PDF of several
  box.pdf.split {path, expect}                                 execute  a new folder of one PDF per page
  box.zip.make {folder, expect} / box.zip.extract {path, expect}   execute  a new archive / a new folder
  box.folder.copy {folder, to, expect}                         execute  a dated copy of a folder (a backup)
  box.files.rename {folder, find?, replace?, case?, kinds?, expect}   execute  many renamed; Undo names them back
  box.files.sort {folder, expect}                              execute  files moved into folders by kind; Undo puts back
  box.files.bin {folder, how, days?, expect}                   execute  duplicates or old files into DELETE; Undo restores
  box.bin.empty {expect}                                       approve  DELETE emptied: it cannot be undone, always asks

No floating point in what is said: sizes are bytes, times whole milliseconds; the processor's share is a whole percent.
"""
from __future__ import annotations

import datetime
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat as statmod
import subprocess
import time
import uuid
import zipfile
from pathlib import Path

from . import home_reach as hr

PROGRAM_PATH = '/usr/local/bin:/usr/bin:/bin'
PACKAGES = {'magick': 'imagemagick', 'convert': 'imagemagick', 'pdfunite': 'poppler-utils', 'pdfseparate': 'poppler-utils',
            'pdfinfo': 'poppler-utils', 'apt-get': 'apt', 'lsblk': 'util-linux', 'systemctl': 'systemd', 'ip': 'iproute2'}
DRIVES = ('/media', '/run/media', '/mnt')          # where a drive is mounted: a backup may land there
MOST_ENTRIES = 300000                               # entries one walk reads, at most
WALK_SECONDS = 25                                   # and for at most this long
MOST_ROWS = 200
MOST_ITEMS = 2000                                   # files one change touches, at most
TEXT_MOST = 2 << 20                                 # a text file read for its words, at most 2 MB
UNZIP_MOST = 20 << 30                               # an archive unpacked, at most 20 GB
PROGRAM_SECONDS = 120
PICTURE_FORMATS = {'png': 'PNG', 'jpg': 'JPEG', 'jpeg': 'JPEG', 'webp': 'WEBP', 'gif': 'GIF', 'tiff': 'TIFF', 'tif': 'TIFF', 'bmp': 'BMP'}
SUFFIX = {'PNG': '.png', 'JPEG': '.jpg', 'WEBP': '.webp', 'GIF': '.gif', 'TIFF': '.tiff', 'BMP': '.bmp'}
KINDS = (  # the folders "sort by kind" makes, and the suffixes each takes
    ('Pictures', ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tif', '.tiff', '.heic', '.svg', '.raw', '.cr2', '.nef')),
    ('Documents', ('.pdf', '.doc', '.docx', '.odt', '.ods', '.odp', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md', '.rtf', '.csv', '.epub')),
    ('Music', ('.mp3', '.flac', '.ogg', '.oga', '.opus', '.wav', '.m4a', '.aac')),
    ('Videos', ('.mp4', '.mkv', '.webm', '.avi', '.mov', '.m4v', '.mpg', '.mpeg')),
    ('Archives', ('.zip', '.tar', '.gz', '.tgz', '.xz', '.bz2', '.7z', '.rar', '.zst', '.iso')),
    ('Installers', ('.deb', '.appimage', '.exe', '.msi', '.run', '.flatpakref')),
)
TEXTS = ('.txt', '.md', '.csv', '.json', '.py', '.html', '.htm', '.xml', '.ini', '.conf', '.cfg', '.log', '.tex', '.rst',
         '.yaml', '.yml', '.toml', '.sh', '.c', '.h', '.js', '.css', '.srt', '.tsv')
HOWS = ('big', 'duplicates', 'changed', 'name', 'words', 'empty', 'old', 'kinds')
SYSTEM_READS = ('updates', 'disks', 'autostart', 'about', 'battery', 'network', 'failed')

PATH = {'type': 'string', 'minLength': 1, 'maxLength': 1000}
PATHS = {'type': 'array', 'items': PATH}
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 200}
WORD = {'type': 'string', 'maxLength': 200}
WHOLE = {'type': 'integer', 'minimum': 0}
EXPECT = {'type': 'string', 'pattern': '^[0-9a-f]{64}$', 'maxLength': 64}
ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'maxLength': 32}
FIELDS = {
    'box.files.find': ({'folder': PATH, 'how': {'type': 'string', 'enum': list(HOWS)}, 'size': WHOLE, 'since': WHOLE, 'days': WHOLE,
                        'words': WORD, 'most': {'type': 'integer', 'minimum': 1, 'maximum': MOST_ROWS}}, ['folder', 'how']),
    'box.space': ({'folder': PATH}, []),
    'box.memory': ({}, []),
    'box.processor': ({}, []),
    'box.system': ({'what': {'type': 'string', 'enum': list(SYSTEM_READS)}}, ['what']),
    'box.pdf.info': ({'path': PATH}, ['path']),
    'box.zip.list': ({'path': PATH}, ['path']),
    'box.bin.list': ({}, []),
    'box.pictures.make': ({'folder': PATH, 'kinds': WORD, 'format': {'type': 'string', 'enum': sorted(PICTURE_FORMATS)}, 'size': WORD,
                           'expect': EXPECT}, ['folder', 'expect']),
    'box.pdf.merge': ({'folder': PATH, 'paths': PATHS, 'name': WORD, 'expect': EXPECT}, ['folder', 'expect']),
    'box.pdf.split': ({'path': PATH, 'expect': EXPECT}, ['path', 'expect']),
    'box.zip.make': ({'folder': PATH, 'expect': EXPECT}, ['folder', 'expect']),
    'box.zip.extract': ({'path': PATH, 'expect': EXPECT}, ['path', 'expect']),
    'box.folder.copy': ({'folder': PATH, 'to': PATH, 'expect': EXPECT}, ['folder', 'to', 'expect']),
    'box.files.rename': ({'folder': PATH, 'find': WORD, 'replace': WORD, 'case': {'type': 'string', 'enum': ['lower', 'upper']},
                          'kinds': WORD, 'expect': EXPECT}, ['folder', 'expect']),
    'box.files.sort': ({'folder': PATH, 'expect': EXPECT}, ['folder', 'expect']),
    'box.files.bin': ({'folder': PATH, 'how': {'type': 'string', 'enum': ['duplicates', 'old']}, 'days': WHOLE, 'expect': EXPECT},
                      ['folder', 'how', 'expect']),
    'box.bin.empty': ({'expect': EXPECT}, ['expect']),
}
READS = ('box.files.find', 'box.space', 'box.memory', 'box.processor', 'box.system', 'box.pdf.info', 'box.zip.list', 'box.bin.list')
CHANGES = ('box.pictures.make', 'box.pdf.merge', 'box.pdf.split', 'box.zip.make', 'box.zip.extract', 'box.folder.copy',
           'box.files.rename', 'box.files.sort', 'box.files.bin')
SCOPES = {**{op: 'read' for op in READS}, **{op: 'execute' for op in CHANGES}, 'box.bin.empty': 'approve'}
UNDO = {  # what Undo does, said before the press
    'box.pictures.make': 'Undo puts the new pictures in DELETE; the originals are never touched.',
    'box.pdf.merge': 'Undo puts the new PDF in DELETE; the PDFs it was made of are never touched.',
    'box.pdf.split': 'Undo puts the new folder of pages in DELETE; the PDF is never touched.',
    'box.zip.make': 'Undo puts the new archive in DELETE; the folder is never touched.',
    'box.zip.extract': 'Undo puts the unpacked folder in DELETE; the archive is never touched.',
    'box.folder.copy': 'Undo removes the copy it made; your folder is never touched.',
    'box.files.rename': 'Undo gives every file its old name back.',
    'box.files.sort': 'Undo puts every file back where it was, and takes away the folders it made when they are empty.',
    'box.files.bin': 'Undo takes every file back out of DELETE, to where it was.',
    'box.bin.empty': None,
}
CANNOT = 'This cannot be undone.'


class Refused(ValueError):
    """A refusal in words: CODE: what and why. Nothing was changed."""


def _now_ms():
    return time.time_ns() // 1_000_000


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()


def size_words(size):
    """Bytes as a Windows hand reads them: '3.4 MB'; exact to the tenth below, no floating point."""
    size = int(size)
    for unit, step in (('TB', 1 << 40), ('GB', 1 << 30), ('MB', 1 << 20), ('KB', 1 << 10)):
        if size >= step:
            tenths = size * 10 // step
            return '%d.%d %s' % (tenths // 10, tenths % 10, unit)
    return '%d bytes' % size if size != 1 else '1 byte'


def count_words(n, one, many=None):
    return '%d %s' % (n, one if n == 1 else (many or one + 's'))


def natural(name):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r'(\d+)', str(name))]


def when_words(ms):
    try:return datetime.datetime.fromtimestamp(int(ms) / 1000).strftime('%d %b %Y %H:%M')
    except (OverflowError, OSError, ValueError):
        return ''


# ---- programs --------------------------------------------------------------------------------------------------------------
def _which(name):
    return shutil.which(name, path=PROGRAM_PATH)


def program(*names):
    """The first of these programs found in the system's own folders, or a refusal naming the Debian package that has it."""
    for name in names:
        found = _which(name)
        if found:return found
    package = PACKAGES.get(names[0], names[0])
    raise Refused('BOX_NEEDS_PROGRAM: %s is not on this computer. Debian\'s package “%s” has it; nothing was changed.' % (names[-1], package))


def needs(op, args=None):
    """{program, package, found} for the program this operation runs, or None when it runs none."""
    names = {'box.pictures.make': ('magick', 'convert'), 'box.pdf.merge': ('pdfunite',), 'box.pdf.split': ('pdfseparate',),
             'box.pdf.info': ('pdfinfo',), 'box.system': {'updates': ('apt-get',), 'disks': ('lsblk',), 'failed': ('systemctl',),
                                                          'network': ('ip',)}.get((args or {}).get('what'), ())}.get(op, ())
    if not names:return None
    found = next((p for p in (_which(n) for n in names) if p), '')
    return {'program': names[-1], 'package': PACKAGES.get(names[0], names[0]), 'found': found}


def _run(argv, seconds=PROGRAM_SECONDS):
    """A program as an argv of a fixed shape: no shell, no input, the C locale, a plain PATH. (code, out, err)."""
    env = {'PATH': PROGRAM_PATH, 'LC_ALL': 'C', 'LANG': 'C', 'HOME': str(hr.home())}
    try:
        done = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=seconds, env=env, shell=False, check=False)
    except subprocess.TimeoutExpired:
        return 124, '', 'took longer than %d seconds' % seconds
    except OSError as exc:
        return 127, '', exc.strerror or type(exc).__name__
    return done.returncode, done.stdout.decode('utf-8', 'replace'), done.stderr.decode('utf-8', 'replace')


# ---- places ----------------------------------------------------------------------------------------------------------------
def on_drive(path):
    text = os.path.normpath(str(path))
    return any(text.startswith(d + '/') for d in DRIVES)


def drives():
    """The drives mounted under /media, /run/media and /mnt (from /proc/mounts): [{path, free}]."""
    out = []
    try:lines = Path('/proc/mounts').read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        lines = []
    for line in lines:
        parts = line.split()
        if len(parts) < 2:continue
        place = parts[1].replace('\\040', ' ')
        if on_drive(place) and os.path.isdir(place):
            try:st = os.statvfs(place);free = st.f_bavail * st.f_frsize
            except OSError:
                free = 0
            out.append({'path': place, 'name': os.path.basename(place), 'free': free})
    return out


def folder_of(text, what='folder'):
    """A folder to read: in your home or on a drive; never a system folder. Refused in words when not."""
    path = hr.expand(str(text or '').strip()) if hr.named_absolute(str(text or '').strip()) else None
    if path is None:raise Refused('BOX_PLACE: say the %s from ~ or / (for example ~/Downloads)' % what)
    if hr.is_system(path):raise Refused('BOX_SYSTEM_FOLDER: %s is %s' % (path, hr.SYSTEM_WORDS))
    real = hr.real(path)
    if not (hr.within(real, hr.home()) or on_drive(real)):raise Refused('BOX_OUTSIDE: %s is outside your home' % hr.tilde(path))
    if not path.exists():raise Refused('BOX_NOT_FOUND: %s is not there' % hr.tilde(path))
    if what == 'folder' and not path.is_dir():raise Refused('BOX_NOT_A_FOLDER: %s is a file, not a folder' % hr.tilde(path))
    if what == 'file' and not path.is_file():raise Refused('BOX_NOT_A_FILE: %s is not a file' % hr.tilde(path))
    return path


def file_of(text):
    return folder_of(text, 'file')


class Reach:
    """Where a change may land: your home only (bulk_files.Reach's rules: never your home folder itself, Files, Graphite's
    own records, DELETE's own folder, a folder that holds Graphite's workspace)."""

    def __init__(self, kernel):
        from .bulk_files import Reach as Bulk
        self.bulk = Bulk(kernel)

    def why_not(self, path):
        where, why = self.bulk(path)
        if why:return why
        if where != hr.HOME:return 'not in your home'
        return ''

    def check(self, path):
        why = self.why_not(path)
        if why:raise Refused('BOX_NOT_HERE: %s: %s' % (hr.tilde(path), why))
        return path

    def new_in(self, folder):
        """A folder a new file may be made in: your home (not Graphite's own records, not Files, not DELETE), or a drive."""
        folder = Path(folder);real = hr.real(folder)
        if on_drive(real):return folder
        where = self.bulk.area(real, real);trash = self.bulk.trash
        if where != hr.HOME:raise Refused('BOX_NOT_HERE: %s is %s; a new file is made only in your home or on a drive' % (hr.tilde(folder), hr.AREA_WORDS.get(where, where)))
        if str(real) == trash or str(real).startswith(trash + '/'):raise Refused("BOX_NOT_HERE: %s is DELETE's own folder" % hr.tilde(folder))
        return folder


def _free(folder, name):
    candidate = Path(folder) / name;stem, suffix = Path(name).stem, Path(name).suffix;n = 2
    if name.lower().endswith('.tar.gz'):stem, suffix = name[:-7], '.tar.gz'
    while os.path.lexists(candidate):candidate = Path(folder) / ('%s %d%s' % (stem, n, suffix));n += 1
    return candidate


def _stat(path):
    st = os.lstat(path)
    return {'ino': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns}


def _same(path, item):
    try:st = os.lstat(path)
    except OSError:
        return False
    return st.st_ino == item.get('ino') and st.st_size == item.get('size') and st.st_mtime_ns == item.get('mtime_ns')


def _part(folder, suffix=''):
    """A fresh name in `folder` that a program writes to first (never a name of yours)."""
    return Path(folder) / ('.graphite-part-%s%s' % (uuid.uuid4().hex[:12], suffix))


def _settle(part, final):
    """The program's result under its final name, only while that name is free (a link, then the part removed)."""
    try:
        os.link(part, final)
    except FileExistsError:
        final = _free(final.parent, final.name);os.link(part, final)
    finally:
        try:os.unlink(part)
        except OSError:
            pass
    return final


# ---- walking ---------------------------------------------------------------------------------------------------------------
class Walk:
    """Every file under a folder, links never followed, hidden ones read only when asked; bounded by MOST_ENTRIES and
    WALK_SECONDS (cut says so)."""

    def __init__(self, folder, hidden=True, folders=False, bin=False):
        self.folder = Path(folder);self.hidden = hidden;self.folders = folders;self.cut = False;self.read = 0
        from . import home_trash      # the bin's folder, as 1.0 finds it (XDG_DATA_HOME, else ~/.local/share)
        self.skip = None if bin else hr.real(home_trash.trash_dir())

    def __iter__(self):
        deadline = time.monotonic() + WALK_SECONDS;stack = [self.folder]
        while stack:
            here = stack.pop()
            try:entries = list(os.scandir(here))
            except OSError:
                continue
            if self.folders:yield ('dir', here, entries)
            for entry in entries:
                self.read += 1
                if self.read > MOST_ENTRIES or time.monotonic() > deadline:self.cut = True;return
                if not self.hidden and entry.name.startswith('.'):continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if Path(entry.path) != self.skip and not hr.is_system(entry.path):stack.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        yield ('file', Path(entry.path), entry.stat(follow_symlinks=False))
                except OSError:
                    continue


def kind_of(name):
    suffix = Path(str(name).lower()).suffix
    for folder, suffixes in KINDS:
        if suffix in suffixes:return folder
    return 'Other'


def _row(path, st, **more):
    return dict({'path': str(path), 'place': hr.tilde(path), 'name': Path(path).name, 'size': int(st.st_size),
                 'size_words': size_words(st.st_size), 'when': st.st_mtime_ns // 1_000_000}, **more)


def _sha(path, most=None):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        while True:
            block = stream.read(1 << 20)
            if not block:break
            h.update(block)
    return h.hexdigest()


def duplicates(folder, hidden=False):
    """Groups of files with the same bytes: by size, then by sha256. Each group oldest first (that one is kept)."""
    walk = Walk(folder, hidden=hidden);by_size = {}
    for _, path, st in walk:
        if st.st_size > 0:by_size.setdefault(st.st_size, []).append((path, st))
    groups = []
    for size, found in by_size.items():
        if len(found) < 2:continue
        by_sum = {}
        for path, st in found:
            try:by_sum.setdefault(_sha(path), []).append((path, st))
            except OSError:
                continue
        for same in by_sum.values():
            if len(same) > 1:
                same.sort(key=lambda p: (p[1].st_mtime_ns, natural(p[0].name)))
                groups.append(same)
    groups.sort(key=lambda g: -(g[0][1].st_size * (len(g) - 1)))
    return groups, walk.cut


def find(kernel, args, principal=None):
    """box.files.find: what the folder holds, by how; nothing is changed. Each row is read again before it is said."""
    folder = folder_of(args['folder']);how = args['how'];most = int(args.get('most') or 50)
    rows = [];cut = False;words = ''
    hidden_words = ' Hidden folders (a name starting with a dot) are not read.'
    if how == 'big':
        least = int(args.get('size') or 100 << 20)
        walk = Walk(folder, hidden=True)
        found = [(p, st) for _, p, st in walk if st.st_size >= least];cut = walk.cut
        found.sort(key=lambda p: -p[1].st_size)
        rows = [_row(p, st) for p, st in found[:most]]
        words = '%s of %s or more in %s, biggest first, %s in all.' % (count_words(len(found), 'file'), size_words(least), hr.tilde(folder),
                                                                       size_words(sum(st.st_size for _, st in found)))
    elif how == 'duplicates':
        groups, cut = duplicates(folder)
        for g in groups[:most]:
            keep, rest = g[0], g[1:]
            rows.append(_row(keep[0], keep[1], copies=[hr.tilde(p) for p, _ in rest], spare=keep[1].st_size * len(rest)))
        spare = sum(g[0][1].st_size * (len(g) - 1) for g in groups)
        words = '%s with copies in %s; the copies take %s.%s' % (count_words(len(groups), 'file'), hr.tilde(folder), size_words(spare), hidden_words)
    elif how in ('changed', 'old'):
        if how == 'changed':
            since = int(args.get('since') or (_now_ms() - 86400000))
            test = lambda st: st.st_mtime_ns // 1_000_000 >= since
        else:
            days = int(args.get('days') or 30);since = _now_ms() - days * 86400000
            test = lambda st: st.st_mtime_ns // 1_000_000 < since
        walk = Walk(folder, hidden=False)
        found = [(p, st) for _, p, st in walk if test(st)];cut = walk.cut
        found.sort(key=lambda p: (-p[1].st_mtime_ns) if how == 'changed' else p[1].st_mtime_ns)
        rows = [_row(p, st) for p, st in found[:most]]
        words = ('%s changed in %s since %s.' % (count_words(len(found), 'file'), hr.tilde(folder), when_words(since)) if how == 'changed'
                 else '%s in %s last changed before %s, oldest first.' % (count_words(len(found), 'file'), hr.tilde(folder), when_words(since))) + hidden_words
    elif how == 'name':
        pattern = str(args.get('words') or '').strip().lower()
        if not pattern:raise Refused('BOX_WORDS: say the name, or part of it')
        glob = any(c in pattern for c in '*?')
        walk = Walk(folder, hidden=False)
        found = [(p, st) for _, p, st in walk if (fnmatch.fnmatch(p.name.lower(), pattern) if glob else pattern in p.name.lower())];cut = walk.cut
        found.sort(key=lambda p: -p[1].st_mtime_ns)
        rows = [_row(p, st) for p, st in found[:most]]
        words = '%s in %s with “%s” in the name, newest first.%s' % (count_words(len(found), 'file'), hr.tilde(folder), pattern, hidden_words)
    elif how == 'words':
        wanted = [w for w in re.findall(r"[\w'-]+", str(args.get('words') or '').lower()) if w]
        if not wanted:raise Refused('BOX_WORDS: say the words the file holds')
        walk = Walk(folder, hidden=False);found = []
        for _, p, st in walk:
            if p.suffix.lower() not in TEXTS or st.st_size > TEXT_MOST:continue
            try:text = p.read_bytes().decode('utf-8', 'replace').lower()
            except OSError:
                continue
            if all(w in text for w in wanted):
                at = text.find(wanted[0]);line = text[max(0, text.rfind('\n', 0, at) + 1):][:120].split('\n')[0]
                found.append((p, st, line))
        cut = walk.cut;found.sort(key=lambda p: -p[1].st_mtime_ns)
        rows = [_row(p, st, line=line) for p, st, line in found[:most]]
        words = ('%s in %s hold “%s”. Text files only: a PDF or an office document is read through its pages.%s'
                 % (count_words(len(found), 'file'), hr.tilde(folder), ' '.join(wanted), hidden_words))
    elif how == 'empty':
        walk = Walk(folder, hidden=False, folders=True);found = []
        for item in walk:
            if item[0] == 'dir' and item[1] != folder and not item[2]:found.append(item[1])
        cut = walk.cut
        rows = [{'path': str(p), 'place': hr.tilde(p), 'name': p.name, 'size': 0, 'size_words': 'empty'} for p in sorted(found, key=natural)[:most]]
        words = '%s in %s.%s' % (count_words(len(found), 'empty folder'), hr.tilde(folder), hidden_words)
    elif how == 'kinds':
        walk = Walk(folder, hidden=False);tally = {}
        for _, p, st in walk:
            k = tally.setdefault(kind_of(p.name), [0, 0]);k[0] += 1;k[1] += st.st_size
        cut = walk.cut
        rows = [{'kind': k, 'count': v[0], 'size': v[1], 'size_words': size_words(v[1]), 'name': k, 'place': ''} for k, v in sorted(tally.items(), key=lambda kv: -kv[1][1])]
        words = 'What %s holds, by kind: %s.%s' % (hr.tilde(folder), ', '.join('%s %s' % (r['kind'], r['count']) for r in rows) or 'nothing', hidden_words)
    checked = _check_rows(rows)
    if cut:words += ' I stopped reading at the walk\'s budget: this is what was read.'
    return {'how': how, 'folder': str(folder), 'rows': rows, 'words': words, 'cut': cut, 'verified': checked[0], 'checked': checked[1]}


def _check_rows(rows):
    """The read's verifier: every file listed is read again, the same size, before it is said."""
    paths = [r for r in rows if r.get('path') and r.get('size_words') != 'empty' and 'kind' not in r]
    for r in paths:
        try:
            if os.lstat(r['path']).st_size != r['size']:return False, '%s changed while it was read' % r['place']
        except OSError:
            return False, '%s went while it was read' % r['place']
    return True, ('each of the %s listed read again from the disk, the same size' % count_words(len(paths), 'file') if paths else 'read from the disk now')


def space(kernel, args, principal=None):
    """box.space: how full the disk is, and what in the folder takes the space (its biggest parts, one level down)."""
    folder = folder_of(args.get('folder') or '~')
    st = os.statvfs(folder);total = st.f_blocks * st.f_frsize;free = st.f_bavail * st.f_frsize;used = total - st.f_bfree * st.f_frsize
    parts = {};cut = False;read = 0
    try:entries = list(os.scandir(folder))
    except OSError:
        entries = []
    for entry in entries:
        try:
            if entry.is_dir(follow_symlinks=False):
                walk = Walk(entry.path, hidden=True, bin=True);parts[entry.path] = sum(s.st_size for _, _, s in walk);cut = cut or walk.cut;read += walk.read
            elif entry.is_file(follow_symlinks=False):
                parts[entry.path] = entry.stat(follow_symlinks=False).st_size
        except OSError:
            continue
    biggest = sorted(parts.items(), key=lambda kv: -kv[1])[:15]
    rows = [{'path': p, 'place': hr.tilde(p), 'name': os.path.basename(p), 'size': s, 'size_words': size_words(s),
             'kind': 'folder' if os.path.isdir(p) else 'file'} for p, s in biggest]
    share = used * 100 // total if total else 0
    words = ('The disk holding %s: %s free of %s (%d%% used). In %s, the biggest: %s.'
             % (hr.tilde(folder), size_words(free), size_words(total), share, hr.tilde(folder),
                ', '.join('%s %s' % (r['name'], r['size_words']) for r in rows[:5]) or 'nothing'))
    if cut:words += ' Some folders were too big to read whole in time: their sizes are at least what is shown.'
    return {'folder': str(folder), 'free': free, 'total': total, 'used': used, 'rows': rows, 'words': words, 'cut': cut,
            'verified': True, 'checked': 'the disk asked now (statvfs); sizes read from the disk'}


# ---- the system, read ------------------------------------------------------------------------------------------------------
def _meminfo():
    out = {}
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            key, _, rest = line.partition(':')
            out[key.strip()] = int(rest.split()[0]) * 1024 if rest.split() else 0
    except (OSError, ValueError, IndexError):
        pass
    return out


def _processes():
    """{pid: (name, rss bytes, ticks)} from /proc."""
    page = os.sysconf('SC_PAGE_SIZE') if hasattr(os, 'sysconf') else 4096
    out = {}
    for entry in os.listdir('/proc'):
        if not entry.isdigit():continue
        try:
            raw = Path('/proc/%s/stat' % entry).read_text()
            name = raw[raw.index('(') + 1:raw.rindex(')')];fields = raw[raw.rindex(')') + 2:].split()
            ticks = int(fields[11]) + int(fields[12]);rss = int(fields[21]) * page
            out[int(entry)] = (name, rss, ticks)
        except (OSError, ValueError, IndexError):
            continue
    return out


def memory(kernel, args, principal=None):
    """box.memory: memory in use and what uses it, by program (processes of one name summed), from /proc."""
    info = _meminfo();total = info.get('MemTotal', 0);free = info.get('MemAvailable', info.get('MemFree', 0))
    by = {}
    for pid, (name, rss, _) in _processes().items():
        b = by.setdefault(name, [0, 0]);b[0] += rss;b[1] += 1
    rows = [{'name': n, 'size': v[0], 'size_words': size_words(v[0]), 'count': v[1], 'place': count_words(v[1], 'process', 'processes')}
            for n, v in sorted(by.items(), key=lambda kv: -kv[1][0])[:15]]
    used = total - free;share = used * 100 // total if total else 0
    swap = info.get('SwapTotal', 0) - info.get('SwapFree', 0)
    words = ('Memory: %s in use of %s (%d%%), %s free for apps. Most: %s.'
             % (size_words(used), size_words(total), share, size_words(free), ', '.join('%s %s' % (r['name'], r['size_words']) for r in rows[:5])))
    if swap > 0:words += ' %s is out on the disk (swap).' % size_words(swap)
    return {'rows': rows, 'total': total, 'free': free, 'words': words, 'verified': bool(total), 'checked': 'read now from /proc (meminfo and each process)'}


def processor(kernel, args, principal=None):
    """box.processor: what uses the processor now, by program: two looks at /proc half a second apart."""
    first = _processes();t0 = _cpu_ticks();time.sleep(0.5);second = _processes();t1 = _cpu_ticks()
    spent = max(1, t1 - t0);cores = os.cpu_count() or 1
    by = {}
    for pid, (name, _, ticks) in second.items():
        before = first.get(pid)
        if before and before[0] == name:by[name] = by.get(name, 0) + max(0, ticks - before[2])
    rows = [{'name': n, 'share': t * 100 // spent, 'size': 0, 'size_words': '%d%%' % (t * 100 // spent), 'place': ''}
            for n, t in sorted(by.items(), key=lambda kv: -kv[1])[:10] if t > 0]
    try:load = Path('/proc/loadavg').read_text().split()[:3]
    except OSError:
        load = []
    words = ('The processor now (%s; a whole core is 100%%): %s.' % (count_words(cores, 'core'), ', '.join('%s %s' % (r['name'], r['size_words']) for r in rows[:5]) or 'nearly idle'))
    if load:words += ' Load over the last minute, five and fifteen: %s.' % ', '.join(load)
    return {'rows': rows, 'cores': cores, 'words': words, 'verified': True, 'checked': 'two looks at /proc, half a second apart'}


def _cpu_ticks():
    try:return sum(int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:8]) // max(1, os.cpu_count() or 1)
    except (OSError, ValueError, IndexError):
        return 0


def _desktop_entry(path):
    found = {}
    try:text = Path(path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return found
    section = ''
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('['):section = line;continue
        if section == '[Desktop Entry]' and '=' in line:
            k, _, v = line.partition('=');found.setdefault(k.strip(), v.strip())
    return found


def system(kernel, args, principal=None):
    """box.system: one read of the system, by what."""
    what = args['what']
    return {'updates': _updates, 'disks': _disks, 'autostart': _autostart, 'about': _about, 'battery': _battery,
            'network': _network, 'failed': _failed}[what]()


def _updates():
    prog = program('apt-get')
    code, out, err = _run([prog, '--simulate', '--quiet=1', 'upgrade'], 90)
    if code != 0:raise Refused('BOX_PROGRAM_FAILED: apt-get could not read the package lists: %s' % (err.strip().splitlines() or ['no reason given'])[-1][:200])
    rows = []
    for line in out.splitlines():
        m = re.match(r'^Inst (\S+) (?:\[(\S+)\] )?\((\S+) (.*?)\)', line)
        if m:rows.append({'name': m.group(1), 'place': '%s → %s' % (m.group(2) or 'new', m.group(3)), 'security': '-security' in m.group(4),
                          'size': 0, 'size_words': 'security' if '-security' in m.group(4) else ''})
    lists = Path('/var/lib/apt/lists');age = ''
    try:
        newest = max((e.stat().st_mtime_ns for e in os.scandir(lists) if e.is_file()), default=0)
        if newest:age = ' The package lists were last read from Debian on %s; reading them again is the system\'s own door.' % when_words(newest // 1_000_000)
    except OSError:
        pass
    security = sum(1 for r in rows if r['security'])
    words = ('Up to date: no package has a newer version in the lists.' if not rows else
             '%s can be updated (%s from Debian\'s security updates). Updating is yours, through the system\'s own prompt.'
             % (count_words(len(rows), 'package'), security)) + age
    return {'rows': rows[:MOST_ROWS], 'count': len(rows), 'words': words, 'verified': True,
            'checked': 'apt-get --simulate upgrade: the lists on this computer, nothing installed, nothing sent'}


def _disks():
    prog = program('lsblk')
    code, out, err = _run([prog, '--json', '--bytes', '--output', 'NAME,SIZE,TYPE,MOUNTPOINT,MODEL,ROTA,TRAN,FSTYPE'], 20)
    if code != 0:raise Refused('BOX_PROGRAM_FAILED: lsblk: %s' % err.strip()[:200])
    try:devices = json.loads(out).get('blockdevices') or []
    except ValueError:
        devices = []
    rows = []
    for d in devices:
        if d.get('type') != 'disk':continue
        name = str(d.get('name') or '');state = errors = ''
        try:state = Path('/sys/block/%s/device/state' % name).read_text().strip()
        except OSError:
            pass
        try:errors = str(int(Path('/sys/block/%s/device/ioerr_cnt' % name).read_text().strip(), 16))
        except (OSError, ValueError):
            pass
        mounted = [c.get('mountpoint') for c in (d.get('children') or []) if c.get('mountpoint')] + ([d['mountpoint']] if d.get('mountpoint') else [])
        rows.append({'name': name, 'model': (d.get('model') or '').strip(), 'size': int(d.get('size') or 0), 'size_words': size_words(int(d.get('size') or 0)),
                     'kind': 'spinning disk' if str(d.get('rota')) in ('1', 'True', 'true') else 'solid state', 'state': state or 'not said',
                     'errors': errors, 'place': ', '.join(m for m in mounted if m) or 'not mounted'})
    words = '; '.join('%s %s %s, %s%s' % (r['name'], r['model'] or 'disk', r['size_words'], r['kind'],
                                         ', the kernel counted %s read errors' % r['errors'] if r['errors'] not in ('', '0') else ', no errors counted')
                      for r in rows) or 'No disk listed.'
    words += '. A full health report (SMART) needs the administrator: smartctl, Debian\'s package “smartmontools”, through the system\'s own prompt.'
    return {'rows': rows, 'words': words, 'verified': True, 'checked': 'lsblk and the kernel\'s own counts in /sys, read now'}


def _autostart():
    config = Path(os.environ.get('XDG_CONFIG_HOME') or hr.home() / '.config') / 'autostart'
    entries = {}
    for folder, where in ((Path('/etc/xdg/autostart'), 'for everyone'), (config, 'yours')):
        try:names = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in names:
            if not name.endswith('.desktop'):continue
            e = _desktop_entry(folder / name)
            on = not (e.get('Hidden', '').lower() == 'true' or e.get('X-GNOME-Autostart-enabled', '').lower() == 'false')
            entries[name] = {'name': e.get('Name') or name[:-8], 'on': on, 'place': where, 'path': str(folder / name),
                             'size': 0, 'size_words': 'starts' if on else 'off', 'only': e.get('OnlyShowIn', '')}
    rows = sorted(entries.values(), key=lambda r: (not r['on'], r['name'].lower()))
    on = [r['name'] for r in rows if r['on']]
    words = ('%s start with the session: %s.' % (count_words(len(on), 'app'), ', '.join(on)) if on else 'No app starts with the session.')
    return {'rows': rows, 'words': words, 'verified': True, 'checked': 'the autostart entries in /etc/xdg/autostart and yours, read now'}


def _about():
    os_name = ''
    try:
        for line in Path('/etc/os-release').read_text().splitlines():
            if line.startswith('PRETTY_NAME='):os_name = line.split('=', 1)[1].strip('"')
    except OSError:
        pass
    cpu = ''
    try:cpu = next((l.split(':', 1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name')), '')
    except OSError:
        pass
    total = _meminfo().get('MemTotal', 0)
    try:up = int(float(Path('/proc/uptime').read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        up = 0
    u = os.uname()
    rows = [{'name': 'System', 'place': os_name or u.sysname}, {'name': 'Kernel', 'place': u.release}, {'name': 'Processor', 'place': cpu or u.machine},
            {'name': 'Cores', 'place': str(os.cpu_count() or 1)}, {'name': 'Memory', 'place': size_words(total)},
            {'name': 'Running for', 'place': '%d days %d hours %d minutes' % (up // 86400, up % 86400 // 3600, up % 3600 // 60)}]
    for r in rows:r.update(size=0, size_words='')
    words = '%s on %s, %s, %s of memory; running for %s.' % (os_name or u.sysname, cpu or u.machine, count_words(os.cpu_count() or 1, 'core'), size_words(total), rows[-1]['place'])
    return {'rows': rows, 'words': words, 'verified': True, 'checked': '/etc/os-release, /proc and uname, read now'}


def _battery():
    rows = []
    base = Path('/sys/class/power_supply')
    try:names = sorted(os.listdir(base))
    except OSError:
        names = []
    for name in names:
        try:
            if (base / name / 'type').read_text().strip() != 'Battery':continue
            level = (base / name / 'capacity').read_text().strip();state = (base / name / 'status').read_text().strip()
        except OSError:
            continue
        rows.append({'name': name, 'place': state, 'size': 0, 'size_words': '%s%%' % level})
    words = '; '.join('%s at %s, %s' % (r['name'], r['size_words'], r['place'].lower()) for r in rows) or 'No battery: this computer runs from the mains.'
    return {'rows': rows, 'words': words, 'verified': True, 'checked': 'the kernel\'s power supply report in /sys, read now'}


def _network():
    prog = program('ip')
    code, out, err = _run([prog, '-json', 'address', 'show'], 20)
    if code != 0:raise Refused('BOX_PROGRAM_FAILED: ip: %s' % err.strip()[:200])
    try:links = json.loads(out)
    except ValueError:
        links = []
    rows = []
    for link in links:
        name = link.get('ifname') or ''
        if name == 'lo':continue
        addresses = [a.get('local', '') for a in link.get('addr_info') or [] if a.get('local')]
        rows.append({'name': name, 'place': ', '.join(addresses) or 'no address', 'size': 0, 'size_words': str(link.get('operstate') or '').lower()})
    words = '; '.join('%s %s: %s' % (r['name'], r['size_words'] or 'state not said', r['place']) for r in rows) or 'No network connection.'
    return {'rows': rows, 'words': words, 'verified': True, 'checked': 'ip -json address show, read now'}


def _failed():
    prog = program('systemctl')
    code, out, err = _run([prog, '--failed', '--no-pager', '--plain', '--no-legend'], 20)
    if code != 0 and not out.strip():raise Refused('BOX_PROGRAM_FAILED: systemctl could not ask the system: %s' % (err.strip().splitlines() or ['no reason given'])[-1][:200])
    if code not in (0, 1):raise Refused('BOX_PROGRAM_FAILED: systemctl: %s' % err.strip()[:200])
    rows = [{'name': l.split()[0], 'place': ' '.join(l.split()[4:])[:120], 'size': 0, 'size_words': 'failed'} for l in out.splitlines() if l.split()]
    words = '%s failed: %s.' % (count_words(len(rows), 'service'), ', '.join(r['name'] for r in rows)) if rows else 'No service has failed since the computer started.'
    return {'rows': rows, 'words': words, 'verified': True, 'checked': 'systemctl --failed, read now'}


def pdf_pages(path):
    prog = program('pdfinfo')
    code, out, err = _run([prog, str(path)], 30)
    if code != 0:raise Refused('BOX_NOT_A_PDF: %s could not be read as a PDF: %s' % (hr.tilde(path), err.strip()[:160]))
    m = re.search(r'^Pages:\s+(\d+)', out, re.M)
    if not m:raise Refused('BOX_NOT_A_PDF: %s has no page count' % hr.tilde(path))
    return int(m.group(1))


def pdf_info(kernel, args, principal=None):
    path = file_of(args['path']);pages = pdf_pages(path)
    return {'rows': [{'name': path.name, 'place': hr.tilde(path), 'size': path.stat().st_size, 'size_words': count_words(pages, 'page')}],
            'pages': pages, 'words': '%s: %s, %s.' % (path.name, count_words(pages, 'page'), size_words(path.stat().st_size)), 'verified': True,
            'checked': 'pdfinfo, read now'}


def zip_list(kernel, args, principal=None):
    path = file_of(args['path'])
    try:
        with zipfile.ZipFile(path) as z:members = [m for m in z.infolist()]
    except (zipfile.BadZipFile, OSError) as exc:
        raise Refused('BOX_NOT_A_ZIP: %s is not a zip archive (%s)' % (hr.tilde(path), str(exc)[:120])) from None
    total = sum(m.file_size for m in members if not m.is_dir())
    rows = [{'name': m.filename, 'place': '', 'size': m.file_size, 'size_words': size_words(m.file_size)} for m in members if not m.is_dir()][:MOST_ROWS]
    return {'rows': rows, 'words': '%s holds %s, %s unpacked.' % (path.name, count_words(len(rows), 'file'), size_words(total)), 'verified': True,
            'checked': 'the archive\'s own list, read now'}


def bin_list(kernel, args=None, principal=None):
    from . import home_trash
    found = home_trash.entries()
    rows = [{'name': e['shown'], 'place': e['place'], 'size': e['size'], 'size_words': size_words(e['size']) if e['kind'] == 'file' else 'folder',
             'stored': e['name'], 'path': ''} for e in found]
    total = _bin_bytes()
    words = ('DELETE is empty.' if not rows else 'DELETE holds %s, %s.' % (count_words(len(rows), 'thing'), size_words(total)))
    return {'rows': rows, 'words': words, 'total': total, 'verified': True, 'checked': "your home's bin, read now"}


def _bin_bytes():
    from . import home_trash
    total = 0
    for _, _, st in Walk(home_trash.files_dir(), hidden=True, bin=True):total += st.st_size
    return total


# ---- pictures --------------------------------------------------------------------------------------------------------------
def picture_kind(head):
    if head.startswith(b'\x89PNG\r\n\x1a\n'):return 'PNG'
    if head[:3] == b'\xff\xd8\xff':return 'JPEG'
    if head[:6] in (b'GIF87a', b'GIF89a'):return 'GIF'
    if head[:2] == b'BM':return 'BMP'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':return 'WEBP'
    if head[:4] in (b'II*\x00', b'MM\x00*'):return 'TIFF'
    return ''


def picture_size(path):
    """(width, height) from the picture's own header, or None (no library: the bytes read here)."""
    try:
        with open(path, 'rb') as f:head = f.read(64);kind = picture_kind(head)
        if kind == 'PNG':return int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')
        if kind == 'GIF':return int.from_bytes(head[6:8], 'little'), int.from_bytes(head[8:10], 'little')
        if kind == 'BMP':return int.from_bytes(head[18:22], 'little', signed=True), abs(int.from_bytes(head[22:26], 'little', signed=True))
        if kind == 'WEBP':
            chunk = head[12:16]
            if chunk == b'VP8 ':return int.from_bytes(head[26:28], 'little') & 0x3fff, int.from_bytes(head[28:30], 'little') & 0x3fff
            if chunk == b'VP8L':
                b = int.from_bytes(head[21:25], 'little');return (b & 0x3fff) + 1, ((b >> 14) & 0x3fff) + 1
            if chunk == b'VP8X':return int.from_bytes(head[24:27], 'little') + 1, int.from_bytes(head[27:30], 'little') + 1
            return None
        if kind == 'JPEG':
            with open(path, 'rb') as f:
                f.read(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2 or marker[0] != 0xff:return None
                    if marker[1] in (0xd8, 0x01) or 0xd0 <= marker[1] <= 0xd7:continue
                    length = int.from_bytes(f.read(2), 'big')
                    if 0xc0 <= marker[1] <= 0xcf and marker[1] not in (0xc4, 0xc8, 0xcc):
                        data = f.read(5);return int.from_bytes(data[3:5], 'big'), int.from_bytes(data[1:3], 'big')
                    f.seek(length - 2, 1)
    except OSError:
        return None
    return None


def geometry(text):
    """'1024' (the longest side), '800x600' (a box), '50%' -> (kind, w, h) or None."""
    text = str(text or '').strip().lower().replace('×', 'x').replace(' ', '')
    m = re.fullmatch(r'(\d{1,5})x(\d{1,5})', text)
    if m and 0 < int(m.group(1)) and 0 < int(m.group(2)):return ('box', int(m.group(1)), int(m.group(2)))
    m = re.fullmatch(r'(\d{1,5})(?:px)?', text)
    if m and int(m.group(1)) > 0:return ('box', int(m.group(1)), int(m.group(1)))
    m = re.fullmatch(r'(\d{1,3})%', text)
    if m and 0 < int(m.group(1)) < 100:return ('share', int(m.group(1)), int(m.group(1)))
    return None


def fitted(size, geom):
    """The size ImageMagick's -resize gives `size` (w, h) for `geom`, never larger than it was: (w, h). Whole numbers."""
    if size is None or geom is None:return None
    w, h = size
    if geom[0] == 'share':return max(1, (w * geom[1] + 50) // 100), max(1, (h * geom[1] + 50) // 100)
    bw, bh = geom[1], geom[2]
    if w <= bw and h <= bh:return w, h
    if w * bh >= h * bw:return bw, max(1, (h * bw * 2 + w) // (2 * w))
    return max(1, (w * bh * 2 + h) // (2 * h)), bh


def _pictures(folder, kinds=''):
    wanted = {('.' + k.strip().lower().lstrip('*.')) for k in re.split(r'[,\s]+', str(kinds or '')) if k.strip() and k.strip() not in ('*', 'all', 'pictures')}
    out = []
    for entry in sorted(os.scandir(folder), key=lambda e: natural(e.name)):
        if entry.name.startswith('.') or not entry.is_file(follow_symlinks=False):continue
        suffix = Path(entry.name).suffix.lower()
        if wanted and suffix not in wanted and not (suffix in ('.jpg', '.jpeg') and wanted & {'.jpg', '.jpeg'}):continue
        if suffix not in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tif', '.tiff'):continue
        try:
            with open(entry.path, 'rb') as f:kind = picture_kind(f.read(16))
        except OSError:
            continue
        if kind:out.append((Path(entry.path), kind))
    return out


def plan_pictures(kernel, args):
    folder = folder_of(args['folder']);reach = Reach(kernel);reach.new_in(folder)
    fmt = PICTURE_FORMATS.get(str(args.get('format') or '').lower()) if args.get('format') else None
    geom = geometry(args['size']) if args.get('size') else None
    if args.get('size') and geom is None:raise Refused('BOX_PICTURE_SIZE: “%s” is not a picture size (1024, 800x600 or 50%%)' % args['size'])
    if not fmt and not geom:raise Refused('BOX_PICTURES_WHAT: say the format to convert to, or the size to make them')
    items, left, taken = [], [], set()
    for path, kind in _pictures(folder, args.get('kinds')):
        if any(c in path.name for c in '[]%\n'):left.append({'path': str(path), 'name': path.name, 'why': 'its name holds [ ] or %, which ImageMagick reads as orders'});continue
        out_kind = fmt or kind
        if fmt and fmt == kind and not geom:left.append({'path': str(path), 'name': path.name, 'why': 'it is %s already' % kind});continue
        stem = path.stem + (' %s' % _geom_words(geom) if geom else '')
        target = _free(folder, stem + SUFFIX[out_kind])
        while str(target) in taken:target = _free(folder, '%s %s%s' % (stem, len(taken) + 2, SUFFIX[out_kind]))
        taken.add(str(target))
        size = picture_size(path);after = fitted(size, geom) if geom else size
        items.append({'from': str(path), 'name': path.name, 'kind': kind, 'to': str(target), 'to_name': target.name, 'to_kind': out_kind,
                      'size': path.stat().st_size, 'mtime_ns': path.stat().st_mtime_ns, 'pixels': list(size) if size else None,
                      'pixels_after': list(after) if after else None})
    if len(items) > MOST_ITEMS:raise Refused('BOX_TOO_MANY: at most %d pictures in one press' % MOST_ITEMS)
    def line(i):
        a = '%d×%d' % tuple(i['pixels']) if i['pixels'] else ''
        b = '%d×%d' % tuple(i['pixels_after']) if i['pixels_after'] else ''
        return '%s%s → %s%s' % (i['name'], ' ' + a if a else '', i['to_name'], ' ' + b if b and geom else '')
    verb = ('Make %s' % count_words(len(items), 'new picture')) + (' as %s' % fmt if fmt else '') + (' at %s' % _geom_words(geom) if geom else '')
    return {'items': items, 'left': left, 'lines': [line(i) for i in items], 'count': len(items), 'bytes': sum(i['size'] for i in items),
            'words': '%s in %s, beside the originals.' % (verb, hr.tilde(folder)), 'program': 'ImageMagick'}


def _geom_words(geom):
    if geom is None:return ''
    if geom[0] == 'share':return '%d%%' % geom[1]
    return '%dpx' % geom[1] if geom[1] == geom[2] else '%dx%d' % (geom[1], geom[2])


def act_pictures(kernel, plan, args, change):
    prog = program('magick', 'convert');geom = geometry(args['size']) if args.get('size') else None
    for item in _each(kernel, plan['items'], change):
        src = Path(item['from']);dst = Path(item['to'])
        if not _same_file(src, item):raise Refused('BOX_CHANGED: %s changed since you saw the plan' % src.name)
        part = _part(dst.parent)
        argv = [prog, '%s:%s' % (item['kind'], src), '-auto-orient']
        if geom:argv += ['-resize', ('%d%%' % geom[1]) if geom[0] == 'share' else '%dx%d>' % (geom[1], geom[2])]
        argv.append('%s:%s' % (item['to_kind'], part))
        code, _, err = _run(argv)
        if code != 0 or not part.exists():
            try:part.unlink()
            except OSError:
                pass
            raise Refused('BOX_PROGRAM_FAILED: ImageMagick could not make %s: %s' % (dst.name, (err.strip().splitlines() or ['no reason given'])[-1][:200]))
        final = _settle(part, dst)
        change['made'].append(dict(path=str(final), **_stat(final)))
        ok, why = verify_picture(final, item, geom)
        item.update(done=True, to=str(final), verified=ok, checked=why)


def verify_picture(path, item, geom):
    try:
        with open(path, 'rb') as f:kind = picture_kind(f.read(16))
    except OSError:
        return False, '%s is not there' % Path(path).name
    if kind != item['to_kind']:return False, '%s is not a %s picture (%s)' % (Path(path).name, item['to_kind'], kind or 'unknown')
    got = picture_size(path)
    if geom and item.get('pixels_after') and got:
        want = tuple(item['pixels_after'])
        if not (abs(got[0] - want[0]) <= 1 and abs(got[1] - want[1]) <= 1) and not (abs(got[0] - want[1]) <= 1 and abs(got[1] - want[0]) <= 1):
            return False, '%s is %d×%d, not %d×%d' % (Path(path).name, got[0], got[1], want[0], want[1])
    return True, '%s read back: a %s picture%s' % (Path(path).name, kind, ' of %d×%d' % got if got else '')


def _same_file(path, item):
    try:st = os.stat(path)
    except OSError:
        return False
    return st.st_size == item.get('size') and st.st_mtime_ns == item.get('mtime_ns')


# ---- PDFs ------------------------------------------------------------------------------------------------------------------
def _is_pdf(path):
    try:
        with open(path, 'rb') as f:return f.read(5) == b'%PDF-'
    except OSError:
        return False


def plan_merge(kernel, args):
    folder = folder_of(args['folder']);Reach(kernel).new_in(folder)
    if args.get('paths'):paths = [file_of(p) for p in args['paths']]
    else:paths = [Path(e.path) for e in sorted(os.scandir(folder), key=lambda e: natural(e.name))
                  if e.is_file(follow_symlinks=False) and e.name.lower().endswith('.pdf') and not e.name.startswith('.')]
    items, left = [], []
    for p in paths:
        if '\n' in p.name or not _is_pdf(p):left.append({'path': str(p), 'name': p.name, 'why': 'not a PDF'});continue
        items.append({'from': str(p), 'name': p.name, 'size': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns, 'pages': pdf_pages(p)})
    if len(items) < 2:raise Refused('BOX_MERGE_FEW: %s in %s; merging takes two or more' % (count_words(len(items), 'PDF'), hr.tilde(folder)))
    name = _clean_name(args.get('name') or 'Merged', '.pdf')
    target = _free(folder, name);pages = sum(i['pages'] for i in items)
    lines = ['%d. %s (%s)' % (n + 1, i['name'], count_words(i['pages'], 'page')) for n, i in enumerate(items)] + ['→ %s, %s' % (target.name, count_words(pages, 'page'))]
    return {'items': items, 'left': left, 'to': str(target), 'pages': pages, 'lines': lines, 'count': len(items), 'bytes': sum(i['size'] for i in items),
            'words': 'Make one new PDF, %s, of %s in this order (%s).' % (target.name, count_words(len(items), 'PDF'), count_words(pages, 'page'))}


def _clean_name(name, suffix):
    name = re.sub(r'[/\\\0\n%]', ' ', str(name)).strip().strip('.') or 'Merged'
    return name if name.lower().endswith(suffix) else name + suffix


def act_merge(kernel, plan, args, change):
    prog = program('pdfunite')
    for i in plan['items']:
        if not _same_file(i['from'], i):raise Refused('BOX_CHANGED: %s changed since you saw the plan' % i['name'])
    _halt(kernel)
    target = Path(plan['to']);part = _part(target.parent, '.pdf')
    code, _, err = _run([prog] + [i['from'] for i in plan['items']] + [str(part)])
    if code != 0 or not part.exists():
        try:part.unlink()
        except OSError:
            pass
        raise Refused('BOX_PROGRAM_FAILED: pdfunite: %s' % (err.strip().splitlines() or ['no reason given'])[-1][:200])
    final = _settle(part, target);change['made'].append(dict(path=str(final), **_stat(final)))
    pages = pdf_pages(final)
    plan['to'] = str(final)
    for i in plan['items']:i['done'] = True
    plan['verified'] = pages == plan['pages'] and _is_pdf(final)
    plan['checked'] = '%s read back: %s, %s expected' % (final.name, count_words(pages, 'page'), plan['pages'])


def plan_split(kernel, args):
    path = file_of(args['path']);Reach(kernel).new_in(path.parent)
    if not _is_pdf(path):raise Refused('BOX_NOT_A_PDF: %s is not a PDF' % path.name)
    if any(c in path.name for c in '%\n'):raise Refused('BOX_NAME: %s holds %% or a new line; rename it first' % path.name)
    pages = pdf_pages(path);folder = _free(path.parent, path.stem + ' pages')
    names = ['%s page %d.pdf' % (path.stem, n) for n in range(1, pages + 1)]
    return {'items': [{'from': str(path), 'name': path.name, 'size': path.stat().st_size, 'mtime_ns': path.stat().st_mtime_ns, 'pages': pages}],
            'to': str(folder), 'names': names, 'pages': pages, 'count': pages, 'bytes': path.stat().st_size, 'left': [],
            'lines': ['%s → %s/' % (path.name, folder.name)] + ['  ' + n for n in names[:8]] + (['  … and %d more' % (pages - 8)] if pages > 8 else []),
            'words': 'Split %s into %s, one PDF a page, in a new folder “%s”.' % (path.name, count_words(pages, 'PDF'), folder.name)}


def act_split(kernel, plan, args, change):
    prog = program('pdfseparate');item = plan['items'][0]
    if not _same_file(item['from'], item):raise Refused('BOX_CHANGED: %s changed since you saw the plan' % item['name'])
    _halt(kernel)
    folder = Path(plan['to'])
    if os.path.lexists(folder):folder = _free(folder.parent, folder.name)
    folder.mkdir();change['made_dirs'].append(dict(path=str(folder), **_stat(folder)))
    stem = Path(item['from']).stem
    code, _, err = _run([prog, item['from'], str(folder / ('%s page %%d.pdf' % stem))])
    for n in plan['names']:
        p = folder / n
        if p.exists():change['made'].append(dict(path=str(p), **_stat(p)))
    if code != 0:raise Refused('BOX_PROGRAM_FAILED: pdfseparate: %s' % (err.strip().splitlines() or ['no reason given'])[-1][:200])
    made = [folder / n for n in plan['names'] if (folder / n).exists() and _is_pdf(folder / n)]
    plan['to'] = str(folder);item['done'] = True
    plan['verified'] = len(made) == plan['pages']
    plan['checked'] = '%s of %s pages read back as PDFs in %s' % (len(made), plan['pages'], folder.name)


# ---- zip -------------------------------------------------------------------------------------------------------------------
def plan_zip(kernel, args):
    folder = folder_of(args['folder']);Reach(kernel).new_in(folder.parent)
    if folder == hr.home():raise Refused('BOX_ZIP_HOME: name a folder inside your home, not your home itself')
    files = [];links = []
    walk = Walk(folder, hidden=True)
    for _, p, st in walk:files.append((p, st))
    if walk.cut:raise Refused('BOX_TOO_BIG: %s has more than can be read in one press' % hr.tilde(folder))
    for root, dirs, names in os.walk(folder):
        for n in dirs + names:
            if os.path.islink(os.path.join(root, n)):links.append(os.path.join(root, n))
    target = _free(folder.parent, folder.name + '.zip')
    total = sum(st.st_size for _, st in files)
    return {'items': [{'from': str(p), 'name': p.relative_to(folder).as_posix(), 'size': st.st_size, 'mtime_ns': st.st_mtime_ns} for p, st in sorted(files, key=lambda f: natural(f[0]))],
            'folder': str(folder), 'to': str(target), 'count': len(files), 'bytes': total,
            'left': [{'path': l, 'name': os.path.basename(l), 'why': 'a link: links are left out of the archive'} for l in links],
            'lines': ['%s → %s' % (hr.tilde(folder), target.name)] + ['  %s (%s)' % (i, size_words(st.st_size)) for i, st in
                                                                     [(p.relative_to(folder).as_posix(), st) for p, st in files[:8]]] + (['  … and %d more' % (len(files) - 8)] if len(files) > 8 else []),
            'words': 'Make a new archive, %s, of %s (%s) from %s.' % (target.name, count_words(len(files), 'file'), size_words(total), hr.tilde(folder))}


def act_zip(kernel, plan, args, change):
    target = Path(plan['to']);part = _part(target.parent, '.zip')
    try:
        with zipfile.ZipFile(part, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for item in _each(kernel, plan['items'], change):
                if not _same_file(item['from'], item):raise Refused('BOX_CHANGED: %s changed since you saw the plan' % item['name'])
                z.write(item['from'], arcname=Path(plan['folder']).name + '/' + item['name']);item['done'] = True
    except BaseException:
        try:part.unlink()
        except OSError:
            pass
        for i in plan['items']:i.pop('done', None)      # the archive was not made: nothing of it is done
        raise
    final = _settle(part, target);change['made'].append(dict(path=str(final), **_stat(final)))
    plan['to'] = str(final)
    try:
        with zipfile.ZipFile(final) as z:
            bad = z.testzip();sizes = {m.filename: m.file_size for m in z.infolist()}
    except (zipfile.BadZipFile, OSError) as exc:
        plan['verified'] = False;plan['checked'] = 'the archive could not be read back: %s' % str(exc)[:120];return
    top = Path(plan['folder']).name + '/'
    missing = [i['name'] for i in plan['items'] if sizes.get(top + i['name']) != i['size']]
    plan['verified'] = bad is None and not missing
    plan['checked'] = ('%s read back: %s, every size and check sum right' % (final.name, count_words(len(sizes), 'file')) if plan['verified']
                       else '%s read back with %s wrong' % (final.name, count_words(len(missing) + (bad is not None), 'file')))


def _member_ok(m):
    name = m.filename
    if name.startswith(('/', '\\')) or re.match(r'^[A-Za-z]:', name) or '\0' in name:return 'an absolute name'
    if any(p == '..' for p in re.split(r'[/\\]', name)):return 'it climbs out with ..'
    if statmod.S_ISLNK(m.external_attr >> 16):return 'a link'
    return ''


def plan_unzip(kernel, args):
    path = file_of(args['path']);Reach(kernel).new_in(path.parent)
    try:
        with zipfile.ZipFile(path) as z:members = z.infolist()
    except (zipfile.BadZipFile, OSError) as exc:
        raise Refused('BOX_NOT_A_ZIP: %s is not a zip archive (%s)' % (path.name, str(exc)[:120])) from None
    items, left = [], []
    for m in members:
        why = _member_ok(m)
        if why:left.append({'path': '', 'name': m.filename, 'why': why});continue
        if not m.is_dir():items.append({'name': m.filename, 'size': m.file_size})
    total = sum(i['size'] for i in items)
    free = os.statvfs(path.parent).f_bavail * os.statvfs(path.parent).f_frsize
    if total > UNZIP_MOST or total > free:raise Refused('BOX_TOO_BIG: %s unpacks to %s; %s is free' % (path.name, size_words(total), size_words(free)))
    stem = path.name[:-4] if path.name.lower().endswith('.zip') else path.stem
    folder = _free(path.parent, stem)
    return {'items': items, 'left': left, 'from': str(path), 'from_size': path.stat().st_size, 'from_mtime_ns': path.stat().st_mtime_ns,
            'to': str(folder), 'count': len(items), 'bytes': total,
            'lines': ['%s → %s/' % (path.name, folder.name)] + ['  %s (%s)' % (i['name'], size_words(i['size'])) for i in items[:8]] + (['  … and %d more' % (len(items) - 8)] if len(items) > 8 else []),
            'words': 'Unpack %s into a new folder “%s”: %s, %s.' % (path.name, folder.name, count_words(len(items), 'file'), size_words(total))}


def act_unzip(kernel, plan, args, change):
    src = Path(plan['from'])
    if not _same_file(src, {'size': plan['from_size'], 'mtime_ns': plan['from_mtime_ns']}):raise Refused('BOX_CHANGED: %s changed since you saw the plan' % src.name)
    folder = Path(plan['to'])
    if os.path.lexists(folder):folder = _free(folder.parent, folder.name)
    folder.mkdir();change['made_dirs'].append(dict(path=str(folder), **_stat(folder)));plan['to'] = str(folder)
    wanted = {i['name']: i for i in plan['items']};bad = []
    with zipfile.ZipFile(src) as z:
        for m in z.infolist():
            if m.filename not in wanted:continue
            _halt(kernel)
            target = folder.joinpath(*[p for p in re.split(r'[/\\]', m.filename) if p not in ('', '.')])
            if not hr.within(target, folder):continue
            for parent in reversed(target.parents):
                if hr.within(parent, folder) and parent != folder and not parent.exists():
                    parent.mkdir();change['made_dirs'].append(dict(path=str(parent), **_stat(parent)))
            try:
                with z.open(m) as stream, open(target, 'xb') as out:shutil.copyfileobj(stream, out)      # the CRC is checked as it is read
            except zipfile.BadZipFile:
                bad.append(m.filename)
            if os.path.lexists(target):change['made'].append(dict(path=str(target), **_stat(target)))
            if m.filename not in bad:wanted[m.filename]['done'] = True
    wrong = [n for n, i in wanted.items() if not i.get('done') or os.path.getsize(folder.joinpath(*[p for p in re.split(r'[/\\]', n) if p not in ('', '.')])) != i['size']]
    plan['verified'] = not wrong and not bad
    plan['checked'] = ('%s unpacked into %s, every size and check sum right' % (count_words(len(wanted), 'file'), folder.name) if plan['verified']
                       else '%s did not unpack right: %s' % (count_words(len(wrong), 'file'), ', '.join(wrong[:3])))


# ---- a folder copied (a backup) --------------------------------------------------------------------------------------------
def plan_copy(kernel, args):
    folder = folder_of(args['folder']);to = folder_of(args['to'])
    if hr.within(hr.real(to), hr.real(folder)):raise Refused('BOX_COPY_INSIDE: %s is inside %s; a copy goes somewhere else' % (hr.tilde(to), hr.tilde(folder)))
    Reach(kernel).new_in(to)
    walk = Walk(folder, hidden=True);files = [(p, st) for _, p, st in walk]
    if walk.cut:raise Refused('BOX_TOO_BIG: %s has more than can be read in one press' % hr.tilde(folder))
    total = sum(st.st_size for _, st in files)
    st = os.statvfs(to);free = st.f_bavail * st.f_frsize
    if total > free:raise Refused('BOX_NO_ROOM: %s takes %s; %s has %s free' % (hr.tilde(folder), size_words(total), hr.tilde(to), size_words(free)))
    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H%M')
    target = _free(to, '%s backup %s' % (folder.name or 'home', stamp))
    return {'items': [{'from': str(p), 'name': p.relative_to(folder).as_posix(), 'size': s.st_size, 'mtime_ns': s.st_mtime_ns} for p, s in sorted(files, key=lambda f: natural(f[0]))],
            'folder': str(folder), 'to': str(target), 'count': len(files), 'bytes': total, 'left': [], 'free': free,
            'lines': ['%s → %s' % (hr.tilde(folder), hr.tilde(target)), '%s, %s; %s free there' % (count_words(len(files), 'file'), size_words(total), size_words(free))],
            'words': 'Copy %s (%s, %s) to a new folder “%s” in %s.' % (hr.tilde(folder), count_words(len(files), 'file'), size_words(total), target.name, hr.tilde(to))}


def act_copy(kernel, plan, args, change):
    target = Path(plan['to'])
    if os.path.lexists(target):target = _free(target.parent, target.name)
    target.mkdir();change['made_dirs'].append(dict(path=str(target), **_stat(target)));plan['to'] = str(target)
    change['on_drive'] = on_drive(hr.real(target))
    wrong = []
    for item in _each(kernel, plan['items'], change):
        dst = target.joinpath(*item['name'].split('/'))
        for parent in reversed(dst.parents):
            if hr.within(parent, target) and parent != target and not parent.exists():
                parent.mkdir();change['made_dirs'].append(dict(path=str(parent), **_stat(parent)))
        with open(item['from'], 'rb') as src, open(dst, 'xb') as out:shutil.copyfileobj(src, out)
        shutil.copystat(item['from'], dst)
        change['made'].append(dict(path=str(dst), **_stat(dst)));item['done'] = True
        if os.path.getsize(dst) != item['size'] or _sha(dst) != _sha(item['from']):wrong.append(item['name'])
    plan['verified'] = not wrong
    plan['checked'] = ('%s copied and read back, every one the same bytes as its original' % count_words(len(plan['items']), 'file') if not wrong
                       else '%s differ from the original: %s' % (count_words(len(wrong), 'file'), ', '.join(wrong[:3])))


# ---- names, places, DELETE -------------------------------------------------------------------------------------------------
def plan_rename(kernel, args):
    folder = folder_of(args['folder']);reach = Reach(kernel)
    find_, repl, case = str(args.get('find') or ''), str(args.get('replace') or ''), args.get('case')
    if not find_ and not case:raise Refused('BOX_RENAME_HOW: say what to change (replace X with Y), or lower case')
    if '/' in repl or '\0' in repl:raise Refused('BOX_NAME: a name holds no /')
    wanted = {('.' + k.strip().lower().lstrip('*.')) for k in re.split(r'[,\s]+', str(args.get('kinds') or '')) if k.strip() and k.strip() != '*'}
    items, left, names = [], [], {e.name for e in os.scandir(folder)}
    new_names = set()
    for entry in sorted(os.scandir(folder), key=lambda e: natural(e.name)):
        if entry.name.startswith('.') or not entry.is_file(follow_symlinks=False):continue
        if wanted and Path(entry.name).suffix.lower() not in wanted:continue
        name = entry.name
        if find_:
            new = re.sub(re.escape(find_), lambda m: repl, name, flags=re.I)
        else:new = name
        if case == 'lower':new = new.lower()
        elif case == 'upper':new = Path(new).stem.upper() + Path(new).suffix.lower()
        new = re.sub(r'\s+(\.[^.\s]+)$', r'\1', re.sub(r'\s{2,}', ' ', new)).strip()      # "notes copy.txt" less "copy" is "notes.txt"
        if new == name:continue
        why = reach.why_not(Path(entry.path))
        if why:left.append({'path': entry.path, 'name': name, 'why': why});continue
        if not new or new in ('.', '..') or new.startswith('.'):left.append({'path': entry.path, 'name': name, 'why': 'it would have no name, or a hidden one'});continue
        if new in names or new in new_names:left.append({'path': entry.path, 'name': name, 'why': '“%s” is taken' % new});continue
        new_names.add(new)
        st = entry.stat(follow_symlinks=False)
        items.append({'from': entry.path, 'name': name, 'to': str(folder / new), 'to_name': new, 'ino': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns})
    if len(items) > MOST_ITEMS:raise Refused('BOX_TOO_MANY: at most %d files in one press' % MOST_ITEMS)
    how = ('“%s” → “%s”' % (find_, repl) if find_ else '') + (', ' if find_ and case else '') + ('%s case' % case if case else '')
    return {'items': items, 'left': left, 'count': len(items), 'bytes': 0, 'lines': ['%s → %s' % (i['name'], i['to_name']) for i in items],
            'words': 'Rename %s in %s (%s).' % (count_words(len(items), 'file'), hr.tilde(folder), how)}


def act_rename(kernel, plan, args, change):
    for item in _each(kernel, plan['items'], change):
        src, dst = Path(item['from']), Path(item['to'])
        if not _same(src, item):raise Refused('BOX_CHANGED: %s changed since you saw the plan' % src.name)
        if os.path.lexists(dst) and not (dst.name.lower() == src.name.lower() and os.path.samefile(dst, src)):
            item['left'] = '“%s” is taken now' % dst.name;continue
        os.rename(src, dst)
        change['moves'].append({'from': str(src), 'to': str(dst), 'ino': item['ino']});item['done'] = True
    _verify_moves(plan, change)


def _verify_moves(plan, change):
    wrong = []
    for m in change['moves']:
        try:ok = os.lstat(m['to']).st_ino == m['ino'] and (not os.path.lexists(m['from']) or os.path.samefile(m['from'], m['to']))
        except OSError:
            ok = False
        if not ok:wrong.append(Path(m['to']).name)
    plan['verified'] = not wrong and bool(change['moves'] or not plan['items'])
    plan['checked'] = ('%s read back at the new place, the same file, the old place empty' % count_words(len(change['moves']), 'file') if not wrong
                       else '%s not where they should be: %s' % (count_words(len(wrong), 'file'), ', '.join(wrong[:3])))


def plan_sort(kernel, args):
    folder = folder_of(args['folder']);reach = Reach(kernel);reach.new_in(folder)
    items, left, taken = [], [], {}
    for entry in sorted(os.scandir(folder), key=lambda e: natural(e.name)):
        if entry.name.startswith('.') or not entry.is_file(follow_symlinks=False):continue
        kind = kind_of(entry.name)
        if kind == 'Other':continue
        why = reach.why_not(Path(entry.path))
        if why:left.append({'path': entry.path, 'name': entry.name, 'why': why});continue
        dest = folder / kind
        if dest.exists() and not dest.is_dir():left.append({'path': entry.path, 'name': entry.name, 'why': '“%s” is a file, not a folder' % kind});continue
        target = _free(dest, entry.name) if dest.is_dir() else dest / entry.name
        key = str(target);n = 2
        while key in taken:target = dest / ('%s %d%s' % (Path(entry.name).stem, n, Path(entry.name).suffix));key = str(target);n += 1
        taken[key] = True
        st = entry.stat(follow_symlinks=False)
        items.append({'from': entry.path, 'name': entry.name, 'to': str(target), 'to_name': '%s/%s' % (kind, target.name), 'kind': kind,
                      'ino': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns})
    kinds = {}
    for i in items:kinds[i['kind']] = kinds.get(i['kind'], 0) + 1
    made = [k for k in kinds if not (folder / k).is_dir()]
    made = sorted(made)
    new = (' (each folder made new)' if made and len(made) == len(kinds) else ' (new: %s)' % ', '.join(made) if made else '')
    return {'items': items, 'left': left, 'count': len(items), 'bytes': sum(i['size'] for i in items), 'folder': str(folder), 'make': made,
            'lines': ['%s → %s' % (i['name'], i['to_name'] if Path(i['to']).name != i['name'] else i['kind']) for i in items],
            'words': 'Move %s in %s into folders by kind: %s%s.' % (count_words(len(items), 'file'), hr.tilde(folder),
                                                                  ', '.join('%s %d' % kv for kv in sorted(kinds.items())), new)}


def act_sort(kernel, plan, args, change):
    folder = Path(plan['folder'])
    for item in _each(kernel, plan['items'], change):
        src, dst = Path(item['from']), Path(item['to'])
        if not _same(src, item):raise Refused('BOX_CHANGED: %s changed since you saw the plan' % src.name)
        if not dst.parent.exists():
            dst.parent.mkdir();change['made_dirs'].append(dict(path=str(dst.parent), **_stat(dst.parent)))
        if os.path.lexists(dst):dst = _free(dst.parent, dst.name)
        os.rename(src, dst);item['to'] = str(dst)
        change['moves'].append({'from': str(src), 'to': str(dst), 'ino': item['ino']});item['done'] = True
    _verify_moves(plan, change)
    _ = folder


def plan_bin(kernel, args):
    folder = folder_of(args['folder']);reach = Reach(kernel);items, left = [], []
    if args['how'] == 'duplicates':
        groups, cut = duplicates(folder)
        if cut:raise Refused('BOX_TOO_BIG: %s has more than can be read in one press' % hr.tilde(folder))
        for g in groups:
            keep = g[0][0]
            for p, st in g[1:]:
                why = reach.why_not(p)
                if why:left.append({'path': str(p), 'name': p.name, 'why': why});continue
                items.append({'from': str(p), 'name': hr.tilde(p), 'keep': hr.tilde(keep), 'ino': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns})
        words = 'Put %s in DELETE (%s); the oldest of each is kept.' % (count_words(len(items), 'copy', 'copies'), size_words(sum(i['size'] for i in items)))
        lines = ['%s (a copy of %s)' % (i['name'], i['keep']) for i in items]
    else:
        days = int(args.get('days') or 30);since = _now_ms() - days * 86400000
        for entry in sorted(os.scandir(folder), key=lambda e: natural(e.name)):
            if entry.name.startswith('.') or not entry.is_file(follow_symlinks=False):continue
            st = entry.stat(follow_symlinks=False)
            if st.st_mtime_ns // 1_000_000 >= since:continue
            why = reach.why_not(Path(entry.path))
            if why:left.append({'path': entry.path, 'name': entry.name, 'why': why});continue
            items.append({'from': entry.path, 'name': entry.name, 'ino': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns,
                          'when': when_words(st.st_mtime_ns // 1_000_000)})
        words = 'Put %s from %s in DELETE (%s), each last changed before %s.' % (count_words(len(items), 'file'), hr.tilde(folder),
                                                                                size_words(sum(i['size'] for i in items)), when_words(since))
        lines = ['%s (%s, %s)' % (i['name'], size_words(i['size']), i['when']) for i in items]
    if len(items) > MOST_ITEMS:raise Refused('BOX_TOO_MANY: at most %d files in one press' % MOST_ITEMS)
    return {'items': items, 'left': left, 'count': len(items), 'bytes': sum(i['size'] for i in items), 'lines': lines, 'words': words}


def act_bin(kernel, plan, args, change):
    from . import home_trash
    for item in _each(kernel, plan['items'], change):
        if not _same(item['from'], item):raise Refused('BOX_CHANGED: %s changed since you saw the plan' % item['name'])
        put = home_trash.put(item['from'])
        change['trashed'].append({'name': put['name'], 'original': put['original'], 'ino': item['ino']});item['done'] = True
    wrong = [t['original'] for t in change['trashed'] if os.path.lexists(t['original']) or not _in_bin(t)]
    plan['verified'] = not wrong
    plan['checked'] = ('%s gone from their places and found in DELETE, the same files' % count_words(len(change['trashed']), 'file') if not wrong
                       else '%s not in DELETE as they should be' % count_words(len(wrong), 'file'))


def _in_bin(t):
    from . import home_trash
    try:return os.lstat(home_trash.files_dir() / t['name']).st_ino == t['ino']
    except OSError:
        return False


def plan_empty(kernel, args):
    from . import home_trash
    found = home_trash.entries(most=100000);total = _bin_bytes()
    if not found:raise Refused('BOX_BIN_EMPTY: DELETE is empty already')
    return {'items': [{'name': e['name'], 'shown': e['shown'], 'place': e['place'], 'size': e['size'], 'at': e['at']} for e in found],
            'count': len(found), 'bytes': total, 'left': [],
            'lines': ['%s (from %s)' % (e['shown'], hr.tilde(Path(e['original']).parent)) for e in found],
            'words': 'Empty DELETE: %s, %s, gone for good.' % (count_words(len(found), 'thing'), size_words(total))}


def act_empty(kernel, plan, args, change):
    from . import home_trash
    gone = []
    for item in _each(kernel, plan['items'], change):
        stored = home_trash.files_dir() / item['name'];note = home_trash.info_dir() / (item['name'] + home_trash.INFO_SUFFIX)
        if os.path.isdir(stored) and not os.path.islink(stored):shutil.rmtree(stored)
        elif os.path.lexists(stored):os.unlink(stored)
        try:note.unlink()
        except FileNotFoundError:
            pass
        item['done'] = True;gone.append(item['name'])
    left = [n for n in gone if os.path.lexists(home_trash.files_dir() / n)]
    plan['verified'] = not left
    plan['checked'] = ('%s gone from DELETE, read again' % count_words(len(gone), 'thing') if not left else '%s still in DELETE' % count_words(len(left), 'thing'))


PLANNERS = {'box.pictures.make': (plan_pictures, act_pictures), 'box.pdf.merge': (plan_merge, act_merge), 'box.pdf.split': (plan_split, act_split),
            'box.zip.make': (plan_zip, act_zip), 'box.zip.extract': (plan_unzip, act_unzip), 'box.folder.copy': (plan_copy, act_copy),
            'box.files.rename': (plan_rename, act_rename), 'box.files.sort': (plan_sort, act_sort), 'box.files.bin': (plan_bin, act_bin),
            'box.bin.empty': (plan_empty, act_empty)}
READERS = {'box.files.find': find, 'box.space': space, 'box.memory': memory, 'box.processor': processor, 'box.system': system,
           'box.pdf.info': pdf_info, 'box.zip.list': zip_list, 'box.bin.list': bin_list}
READ_WORDS = {  # what a read reads, said in a dry run (nothing is read to say it)
    'box.files.find': 'reads the files in {folder}', 'box.space': 'reads the sizes in {folder} and how full its disk is',
    'box.memory': 'reads /proc: memory, and each process', 'box.processor': 'looks at /proc twice, half a second apart',
    'box.system': 'reads the system ({what})', 'box.pdf.info': 'reads {path} with pdfinfo', 'box.zip.list': 'reads the list inside {path}',
    'box.bin.list': 'reads what is in DELETE'}


# ---- the change's record, and HALT -----------------------------------------------------------------------------------------
class Halted(Exception):
    """HALT was pressed during a change: what was done is recorded and can be undone."""


def _halt(kernel):
    try:
        from . import halt_gate
        if halt_gate.held(kernel):raise Halted()
    except ImportError:
        pass


def _each(kernel, items, change):
    for item in items:
        _halt(kernel)
        yield item


def ensure(db):
    db.execute('''CREATE TABLE IF NOT EXISTS box_changes(id TEXT PRIMARY KEY, owner TEXT, op TEXT, at INTEGER, state TEXT, args TEXT,
                  plan TEXT, record TEXT, undone INTEGER)''')


def _save(kernel, ident, **fields):
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db)
        if 'owner' in fields:
            db.execute('INSERT INTO box_changes VALUES(?,?,?,?,?,?,?,?,NULL)', (ident, fields['owner'], fields['op'], fields['at'], fields['state'],
                                                                              json.dumps(fields['args']), json.dumps(fields['plan']), json.dumps(fields['record'])))
        else:
            db.execute('UPDATE box_changes SET state=?, plan=?, record=? WHERE id=?', (fields['state'], json.dumps(fields['plan']), json.dumps(fields['record']), ident))


def load(kernel, ident):
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db)
        row = db.execute('SELECT * FROM box_changes WHERE id=?', (ident,)).fetchone()
    if row is None:raise Refused('BOX_UNKNOWN_CHANGE: no such change')
    return {'id': row['id'], 'owner': row['owner'], 'op': row['op'], 'at': row['at'], 'state': row['state'], 'args': json.loads(row['args']),
            'plan': json.loads(row['plan']), 'record': json.loads(row['record']), 'undone': row['undone']}


def plan(kernel, op, args):
    """The dry run of a change: exactly what it would do, with its digest (the `expect` a press carries). Nothing is changed."""
    if op not in PLANNERS:raise Refused('BOX_NOT_A_CHANGE: %s has no dry run here' % op)
    given = {k: v for k, v in args.items() if k != 'expect'}
    found = PLANNERS[op][0](kernel, given)
    found.update(op=op, undo=UNDO.get(op) or CANNOT, can_undo=UNDO.get(op) is not None)
    found['expect'] = digest(_bound(found))
    return found


def _bound(found):
    """What the digest binds: what would be touched and how (not the words)."""
    keys = ('from', 'to', 'name', 'size', 'mtime_ns', 'ino', 'pages', 'to_kind', 'pixels_after')
    return {'op': found['op'], 'items': [{k: i.get(k) for k in keys} for i in found['items']], 'to': found.get('to'), 'names': found.get('names')}


def change(kernel, op, args, principal):
    """A change op: plan again, compare with what you were shown, write down what is prepared, act, verify, record Undo."""
    if hr.in_her_work(principal):
        raise Refused('BOX_YOUR_PRESS: %s changes the computer, so it runs on your press only, never as my own step' % op)
    found = plan(kernel, op, args)
    if found['expect'] != args['expect']:
        raise Refused('BOX_PLAN_CHANGED: what this would do is not what you were shown (the files changed since). Look at it again.')
    if not found['items']:raise Refused('BOX_NOTHING: nothing to do here. %s' % found['words'])
    _halt_before(kernel)
    ident = uuid.uuid4().hex;record = {'made': [], 'made_dirs': [], 'moves': [], 'trashed': [], 'on_drive': False}
    _save(kernel, ident, owner=principal.identity, op=op, at=_now_ms(), state='running', args=args, plan=found, record=record)
    state = 'done';error = ''
    try:
        PLANNERS[op][1](kernel, found, args, record)
        if 'verified' not in found:
            done = [i for i in found['items'] if i.get('done')]
            found['verified'] = bool(done) and all(i.get('verified', True) for i in done) and len(done) == len(found['items'])
            found['checked'] = '; '.join(i['checked'] for i in done if i.get('checked'))[:600] or 'nothing was done'
    except Halted:
        state = 'stopped by HALT';found['verified'] = False;found['checked'] = 'HALT stopped it after %s' % count_words(sum(1 for i in found['items'] if i.get('done')), 'file')
    except (Refused, OSError, zipfile.BadZipFile, shutil.Error) as exc:
        state = 'stopped';error = str(exc)[:300] if isinstance(exc, Refused) else (getattr(exc, 'strerror', '') or str(exc))[:300]
        found['verified'] = False;found['checked'] = 'stopped: %s' % error.split(': ', 1)[-1]
    if state == 'done' and not found['verified']:state = 'not verified'
    _save(kernel, ident, state=state, plan=found, record=record)
    done = sum(1 for i in found['items'] if i.get('done'))
    return {'change': ident, 'op': op, 'state': state, 'verified': bool(found['verified']), 'checked': found['checked'], 'done': done,
            'count': found['count'], 'words': found['words'], 'to': found.get('to'), 'error': error, 'can_undo': found['can_undo'],
            'undo': found['undo'], 'left': found.get('left') or []}


def _halt_before(kernel):
    try:_halt(kernel)
    except Halted:
        raise Refused('BOX_HALT: HALT holds my work. Press RESUME, then press again.') from None


def undo(kernel, ident, principal):
    """Undo one change: each thing put back only when it is as the change left it; what changed since is named, never forced."""
    from . import home_trash
    found = load(kernel, ident)
    if found['undone']:raise Refused('BOX_UNDONE: already taken back')
    if UNDO.get(found['op']) is None:raise Refused('BOX_CANNOT_UNDO: %s' % CANNOT)
    record = found['record'];back, left = [], []
    for t in reversed(record.get('trashed') or []):
        if os.path.lexists(t['original']):left.append('%s: its place is taken now' % hr.tilde(t['original']));continue
        try:home_trash.restore(t['name']);back.append(hr.tilde(t['original']))
        except ValueError as exc:
            left.append('%s: %s' % (hr.tilde(t['original']), str(exc).split(': ', 1)[-1]))
    for m in reversed(record.get('moves') or []):
        try:ok = os.lstat(m['to']).st_ino == m['ino']
        except OSError:
            ok = False
        if not ok:left.append('%s: not where it was left' % hr.tilde(m['to']));continue
        if os.path.lexists(m['from']) and not os.path.samefile(m['from'], m['to']):left.append('%s: its old name is taken now' % hr.tilde(m['from']));continue
        os.rename(m['to'], m['from']);back.append(hr.tilde(m['from']))
    made = record.get('made') or [];dirs = record.get('made_dirs') or []
    top = [d for d in dirs if not any(hr.within(d['path'], o['path']) and d['path'] != o['path'] for o in dirs)]
    deepest = sorted(dirs, key=lambda d: -len(d['path']))
    if found['op'] == 'box.files.sort':      # the folders it made for the kinds: taken away again when they are empty
        for d in deepest:
            try:os.rmdir(d['path'])
            except OSError:
                if os.path.lexists(d['path']):left.append('%s: not empty, so it stays' % hr.tilde(d['path']))
    elif record.get('on_drive'):              # a drive has no DELETE: what it made, unchanged, is removed
        for m in reversed(made):
            if _same(m['path'], m):os.unlink(m['path']);back.append(hr.tilde(m['path']))
            elif os.path.lexists(m['path']):left.append('%s: changed since it was made' % hr.tilde(m['path']))
        for d in deepest:
            try:os.rmdir(d['path'])
            except OSError:
                if os.path.lexists(d['path']):left.append('%s: holds something it did not make' % hr.tilde(d['path']))
    else:                                     # in your home: what it made goes to DELETE, which gives it back
        inside = [m for m in made if any(hr.within(m['path'], d['path']) for d in top)]
        for d in top:
            mine = [m for m in inside if hr.within(m['path'], d['path'])]
            if any(not _same(m['path'], m) for m in mine if os.path.lexists(m['path'])) or _extra(d['path'], mine, dirs):
                left.append('%s: holds something changed or added since' % hr.tilde(d['path']));continue
            if os.path.lexists(d['path']):home_trash.put(d['path']);back.append(hr.tilde(d['path']))
        for m in made:
            if m in inside:continue
            if _same(m['path'], m):home_trash.put(m['path']);back.append(hr.tilde(m['path']))
            elif os.path.lexists(m['path']):left.append('%s: changed since it was made' % hr.tilde(m['path']))
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db);db.execute('UPDATE box_changes SET undone=? WHERE id=?', (_now_ms(), ident))
    return {'change': ident, 'op': found['op'], 'back': back, 'left': left, 'verified': not left}


def _extra(folder, mine, dirs):
    """Whether `folder` holds anything the change did not make."""
    known = {m['path'] for m in mine} | {d['path'] for d in dirs}
    for root, subdirs, names in os.walk(folder):
        for n in subdirs + names:
            if os.path.join(root, n) not in known:return True
    return False


def dispatch(kernel, op, args, principal):
    if op in READERS:return READERS[op](kernel, args, principal)
    if op in PLANNERS:return change(kernel, op, args, principal)
    raise ValueError('BOX_UNKNOWN_OPERATION')
