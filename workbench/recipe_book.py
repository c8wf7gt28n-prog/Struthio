"""Her recipes (Graphite 1.1 KS1): verified, parameterised recipes for the everyday things a Windows hand asks of a Linux box.

PLAN_1.1.md, KS1: "A library of verified, parameterised recipes (preconditions, steps through registered tools, a dry run, a
verifier, an undo), forty to start ... With no model her dictionary picks; with one, the model picks by number and fills
slots only from the owner's words."

A RECIPE IS DATA: a small JSON file, workbench/recipes/*.json (hers) and ~/.config/graphite/recipes/*.json (yours, read the
same way and refused in words when they break a rule):

    {"recipe": "graphite.recipe/1", "id": "find-big-files", "name": "Find big files",
     "title": "Find big files in {folder}",                 what the line and her talk call it, slots filled
     "words": ["big files", "large files", ...],            the words that call it (her dictionary)
     "slots": {"folder": {"type": "folder", "default": "~", "ask": "Which folder?"}, "size": {"type": "size", "default": "100 MB"}},
     "pre": [{"folder": "folder"}],                         preconditions, checked before anything (a folder or file is there)
     "steps": [{"op": "box.files.find", "args": {"folder": "{folder}", "how": "big", "size": "{size}"}}],
     "help": "one sentence"}

  slots     types: folder, file, size, since (a date), days, picture (a picture size), format, kinds (a file pattern), words,
            name, find, replace, case, drive. A slot is filled only from the owner's words (basis owner_words), from the
            recipe's own default (recipe_default, said in the dry run), or by the owner's press on the one question card
            (owner_click). A slot none of these fill is asked: one question.
  steps     registered Kernel operations only (box_ops: the narrow operations). A recipe whose steps all read is a read:
            it runs on its own. A recipe with a change runs only on the owner's press, after its dry run.
  dry run   each change step's own plan (box_ops.plan): exactly which files, which sizes, which new names; the program it
            needs and the Debian package that has it; what Undo does, or "This cannot be undone." before the press.
  verifier  each step checks its effect on the disk after it acts (box_ops); a run is "done" only when every step verified.
  undo      recipes.undo puts back every step's change (box_ops.undo), newest first; what changed since is named, never forced.

PICKING. No model: her dictionary (pick_words) reads the words that call each recipe, and each slot's type reads the owner's
words for a value. With a model (the RECIPE turn kind, turns.ask): the model is shown the recipes by number and the owner's
words that read as a value, each numbered (W1 “Downloads” folder); it answers "12 folder=W1", under a grammar that admits only
those numbers; the checker refuses a W of the wrong type. The model picks; it never writes a value.

Kernel operations (one block in engineering_kernel.py and engineering_cli.py, commented 1.1 KS1):
  recipes.list     {}                          read     the library, numbered; yours too, and those refused with why
  recipes.pick     {words}                     read     her dictionary's pick and the slots it filled (no model)
  recipes.dry_run  {recipe, slots}             read     exactly what it would do, with its digest; nothing changes
  recipes.look     {recipe, slots}             read     a recipe that only reads, run: its answer, verified
  recipes.run      {recipe, slots, digest}     execute  a recipe with a change, on your press; refused when the dry run
                                                        you saw is not what it would do now, in her own work, or under HALT
  recipes.undo     {run}                       approve  the run put back, every step, newest first
  recipes.runs     {limit?}                    read     the runs lately made, newest first
"""
from __future__ import annotations

import datetime
import json
import os
import re
import time
import uuid
from fractions import Fraction
from pathlib import Path

from . import box_ops as bx
from . import home_reach as hr

SCHEMA = 'graphite.recipe/1'
HERE = Path(__file__).resolve().parent / 'recipes'
TYPES = ('folder', 'file', 'size', 'since', 'days', 'picture', 'format', 'kinds', 'words', 'name', 'find', 'replace', 'case', 'drive')
TYPE_WORDS = {'folder': 'a folder', 'file': 'a file', 'size': 'a size', 'since': 'a date', 'days': 'an age in days', 'picture': 'a picture size',
              'format': 'a picture format', 'kinds': 'kinds of file', 'words': 'words to find', 'name': 'a name', 'find': 'words to replace',
              'replace': 'the words instead', 'case': 'lower or upper case', 'drive': 'a drive'}
FOLDERS = {'home': '~', 'my home': '~', 'home folder': '~', 'downloads': '~/Downloads', 'download': '~/Downloads', 'documents': '~/Documents',
           'docs': '~/Documents', 'pictures': '~/Pictures', 'photos': '~/Pictures', 'music': '~/Music', 'videos': '~/Videos',
           'desktop': '~/Desktop', 'templates': '~/Templates', 'public': '~/Public'}
LEADS = r'(?:in|from|inside|under|of|on|within|through)'
DAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
UNITS = {'b': 1, 'byte': 1, 'bytes': 1, 'k': 1 << 10, 'kb': 1 << 10, 'kilobytes': 1 << 10, 'm': 1 << 20, 'mb': 1 << 20, 'meg': 1 << 20,
         'megs': 1 << 20, 'megabytes': 1 << 20, 'megabyte': 1 << 20, 'g': 1 << 30, 'gb': 1 << 30, 'gig': 1 << 30, 'gigs': 1 << 30,
         'gigabytes': 1 << 30, 'gigabyte': 1 << 30, 'tb': 1 << 40, 'terabytes': 1 << 40}
FORMAT_WORDS = {'png': 'png', 'pngs': 'png', 'jpg': 'jpg', 'jpgs': 'jpg', 'jpeg': 'jpg', 'jpegs': 'jpg', 'webp': 'webp', 'webps': 'webp',
                'gif': 'gif', 'gifs': 'gif', 'tiff': 'tiff', 'tif': 'tiff', 'bmp': 'bmp'}
STOP = frozenset(('a', 'an', 'the', 'my', 'me', 'all', 'please', 'can', 'you', 'i', 'to', 'of', 'is', 'are', 'it', 'them', 'for',
                  'and', 'what', 'which', 'show', 'some', 'any', 'this', 'that', 'these', 'those', 'on', 'from', 'with', 'kas',
                  'kasandra', 'do', 'does', 'into', 'by', 'be', 's', 'whats', 'there', 'want', 'like', 'would', 'could', 'need'))
LIST_WORDS = re.compile(r'^\s*(?:show\s+(?:me\s+)?(?:your\s+|the\s+|my\s+)?recipes|(?:your\s+|the\s+|my\s+|list\s+(?:the\s+|your\s+)?)?recipes'
                        r'|what\s+recipes\s+(?:do\s+you\s+have|are\s+there)|which\s+recipes(?:\s+do\s+you\s+have)?)\s*[?.]?\s*$', re.I)
RUNS_MOST = 200


class Refused(ValueError):
    pass


# ---- the library -----------------------------------------------------------------------------------------------------------
def own_folder(environ=None):
    env = os.environ if environ is None else environ
    base = env.get('XDG_CONFIG_HOME') or os.path.join(env.get('HOME') or os.path.expanduser('~'), '.config')
    return Path(base) / 'graphite' / 'recipes'


class Recipe:
    def __init__(self, data, source, n=0):
        self.data = data;self.source = source;self.n = n
        self.id = data['id'];self.name = data['name'];self.words = [str(w).lower() for w in data.get('words') or ()]
        self.slots = data.get('slots') or {};self.steps = data['steps'];self.pre = data.get('pre') or []
        self.help = data.get('help') or ''
        from .engineering_kernel import CAPABILITIES
        self.scopes = [CAPABILITIES.get(s['op']) for s in self.steps]
        self.reads = all(s == 'read' for s in self.scopes)

    def title(self, values=None):
        values = values or {}
        def fill(m):
            name = m.group(1);v = values.get(name)
            if v is None:
                d = self.slots.get(name, {}).get('default')
                v = d if d is not None else '…'
            return shown(self.slots.get(name, {}).get('type'), v)
        return re.sub(r'\{(\w+)\}', fill, self.data.get('title') or self.name)

    def row(self):
        return {'n': self.n, 'id': self.id, 'name': self.name, 'title': self.title(), 'reads': self.reads, 'help': self.help,
                'words': self.words[:4], 'slots': {k: v.get('type') for k, v in self.slots.items()}, 'source': self.source,
                'undo': self.undo_words()}

    def undo_words(self):
        if self.reads:return 'It only reads: nothing to undo.'
        said = [bx.UNDO.get(s['op']) for s in self.steps if bx.SCOPES.get(s['op']) != 'read']
        return bx.CANNOT if any(u is None for u in said) else ' '.join(dict.fromkeys(said))


def check_recipe(data):
    """Why a recipe file may not be used, or ''. Steps are registered operations only; a change step must have a dry run."""
    from .engineering_kernel import CAPABILITIES
    if not isinstance(data, dict) or data.get('recipe') != SCHEMA:return 'not a %s file' % SCHEMA
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,48}', str(data.get('id') or '')):return 'its id is not short lower-case words with dashes'
    if not isinstance(data.get('name'), str) or not data['name'].strip():return 'it has no name'
    if not isinstance(data.get('words'), list) or not all(isinstance(w, str) and w.strip() for w in data['words']):return 'it has no words that call it'
    slots = data.get('slots') or {}
    if not isinstance(slots, dict):return 'its slots are not a table'
    for name, slot in slots.items():
        if not isinstance(slot, dict) or slot.get('type') not in TYPES:return 'slot “%s” has no known type' % name
    steps = data.get('steps')
    if not isinstance(steps, list) or not steps:return 'it has no steps'
    for step in steps:
        op = step.get('op') if isinstance(step, dict) else None
        if op not in CAPABILITIES:return 'step “%s” is not a registered operation' % op
        if op not in bx.FIELDS:return 'step “%s” is not one of the box operations a recipe may use' % op
        if CAPABILITIES[op] != 'read' and op not in bx.PLANNERS:return 'step “%s” changes something and has no dry run' % op
        args = step.get('args') or {}
        if set(args) - set(bx.FIELDS[op][0]):return 'step “%s” takes no %s' % (op, ', '.join(sorted(set(args) - set(bx.FIELDS[op][0]))))
        for value in args.values():
            for name in re.findall(r'\{(\w+)\}', str(value)):
                if name not in slots:return 'step “%s” names a slot it does not have: %s' % (op, name)
    for pre in data.get('pre') or []:
        if not isinstance(pre, dict) or not set(pre) <= {'folder', 'file', 'suffix'}:return 'a precondition it cannot check'
    return ''


_CACHE = {}


def library(environ=None):
    """(recipes, refused): hers first in the order of their files, then yours; each numbered from 1."""
    places = [(HERE, 'hers'), (own_folder(environ), 'yours')]
    key = []
    for folder, _ in places:
        try:key.append(tuple(sorted((e.name, e.stat().st_mtime_ns) for e in os.scandir(folder) if e.name.endswith('.json'))))
        except OSError:
            key.append(())
    key = (tuple(key), str(own_folder(environ)))
    if _CACHE.get('key') == key:return _CACHE['value']
    out, refused, seen = [], [], set()
    for folder, source in places:
        try:names = sorted(e.name for e in os.scandir(folder) if e.name.endswith('.json'))
        except OSError:
            continue
        for name in names:
            try:data = json.loads((folder / name).read_text(encoding='utf-8'))
            except (OSError, ValueError) as exc:
                refused.append({'file': str(folder / name), 'why': 'not readable JSON (%s)' % str(exc)[:80]});continue
            why = check_recipe(data) or ('its id “%s” is taken' % data.get('id') if data.get('id') in seen else '')
            if why:refused.append({'file': hr.tilde(folder / name), 'why': why});continue
            seen.add(data['id']);out.append(Recipe(data, source, len(out) + 1))
    _CACHE.update(key=key, value=(out, refused))
    return out, refused


def find_recipe(ident, environ=None):
    for r in library(environ)[0]:
        if r.id == ident or str(r.n) == str(ident):return r
    raise Refused('RECIPE_UNKNOWN: no recipe “%s”' % ident)


# ---- slot values: read from the owner's words, checked by type -------------------------------------------------------------
def shown(kind, value):
    """A slot's value as the owner reads it."""
    if value is None:return '…'
    if kind == 'size':
        try:return bx.size_words(int(value))
        except (TypeError, ValueError):
            return str(value)
    if kind == 'since':
        try:return bx.when_words(int(value))
        except (TypeError, ValueError):
            return str(value)
    if kind == 'days':return '%s days' % value
    if kind in ('folder', 'file') and str(value) == '~':return 'Home'
    if kind in ('folder', 'file') and str(value).startswith('~/'):return str(value)[2:]
    return str(value)


def _home_folders():
    """{lower name: '~/Name'} for the folders at the top of your home and one level down (as home_plan names things)."""
    out = {};home = hr.home()
    try:top = [e for e in os.scandir(home) if e.is_dir(follow_symlinks=False) and not e.name.startswith('.')]
    except OSError:
        top = []
    for e in top:
        out.setdefault(e.name.lower(), '~/' + e.name)
        try:
            for f in os.scandir(e.path):
                if f.is_dir(follow_symlinks=False) and not f.name.startswith('.'):out.setdefault(f.name.lower(), '~/%s/%s' % (e.name, f.name))
        except OSError:
            continue
    return out


def candidates(kind, text, today=None, now_ms=None):
    """Every value of this type the owner's words hold: [(value, the owner's words)], the likeliest first. Pure reading:
    nothing but the words (and, for a folder or a file, which folders and files are in your home) decides."""
    words = ' '.join(str(text or '').replace('’', "'").split());low = words.lower()
    out = []
    if kind in ('folder', 'drive'):
        found = []
        for m in re.finditer(r'(~/[^\s,;“”"]+|~(?=\s|$)|/(?:media|mnt|run/media|home)/[^\s,;“”"]+)', words):found.append((m.start(), m.group(1).rstrip('.?'), m.group(1)))
        for m in re.finditer(r'[“"]([^”"]+)[”"]', words):
            p = m.group(1)
            if p.startswith(('~', '/')):found.append((m.start(), p, m.group(0)))
        known = dict(_home_folders());known.update({k: v for k, v in FOLDERS.items() if k not in known})
        for name in sorted(known, key=len, reverse=True):
            for m in re.finditer(r'(?<![\w/])%s(?![\w/]|\.\w)' % re.escape(name), low):
                if not any(a <= m.start() < a + len(w) for a, _, w in found):found.append((m.start(), known[name], words[m.start():m.end()]))
        if kind == 'drive':
            drives = bx.drives()
            for d in drives:
                for m in re.finditer(r'(?<!\w)%s(?!\w)' % re.escape(d['name'].lower()), low):found.append((m.start(), d['path'], words[m.start():m.end()]))
            m = re.search(r'\b(?:the\s+)?(?:usb\s+)?(?:drive|stick|usb|external\s+disk|disk)\b', low)
            if m and len(drives) == 1:found.append((m.start(), drives[0]['path'], words[m.start():m.end()]))
            found = [f for f in found if bx.on_drive(f[1])]
        else:
            found = [f for f in found if not bx.on_drive(f[1])]
        def rank(f):
            before = low[max(0, f[0] - 12):f[0]]
            return (0 if re.search(r'\b%s\s+(?:the\s+|my\s+)?$' % LEADS, before) else 1, f[0])
        seen = set()
        for _, value, said in sorted(found, key=rank):
            if value not in seen:seen.add(value);out.append((value, said))
    elif kind == 'file':
        for m in re.finditer(r'[“"]([^”"]+\.[A-Za-z0-9]{2,5})[”"]|((?:~/|/)\S+\.[A-Za-z0-9]{2,5})|([\w][\w .()&+,-]*?\.(?:pdf|zip|png|jpe?g|webp|gif|txt|odt|docx))\b', words):
            whole = (m.group(1) or m.group(2) or m.group(3)).strip()
            if m.group(3):      # a bare name: its longest tail that is a file wins (checked() looks), so each tail is offered
                parts = whole.split(' ')
                for n in range(len(parts)):
                    tail = ' '.join(parts[n:]).strip(' ,')
                    if tail:out.append((tail, tail))
            else:out.append((whole, m.group(0)))
    elif kind == 'size':
        for m in re.finditer(r'(\d+(?:[.,]\d+)?)\s*(bytes?|kb|k|mb|m|megs?|megabytes?|gb|g|gigs?|gigabytes?|tb|terabytes)\b', low):
            number = Fraction(m.group(1).replace(',', '.'))
            out.append((str(int(number * UNITS[m.group(2)])), words[m.start():m.end()]))
    elif kind == 'since':
        today = today or datetime.date.today();now_ms = now_ms or bx._now_ms()
        start = lambda d: int(datetime.datetime.combine(d, datetime.time()).timestamp() * 1000)
        for m in re.finditer(r'\b(yesterday|today|this morning|this week|last week|last month|this month)\b', low):
            w = m.group(1)
            d = {'yesterday': today - datetime.timedelta(days=1), 'today': today, 'this morning': today,
                 'this week': today - datetime.timedelta(days=today.weekday()), 'last week': today - datetime.timedelta(days=7),
                 'this month': today.replace(day=1), 'last month': today - datetime.timedelta(days=30)}[w]
            out.append((str(start(d)), words[m.start():m.end()]))
        for m in re.finditer(r'\b(?:since|on)\s+(?:last\s+)?(%s)\b' % '|'.join(DAYS), low):
            back = (today.weekday() - DAYS.index(m.group(1))) % 7 or 7
            out.append((str(start(today - datetime.timedelta(days=back))), words[m.start():m.end()]))
        for m in re.finditer(r'\b(?:in\s+)?(?:the\s+)?(?:last|past)\s+(\d{1,4})\s+(day|days|week|weeks|hour|hours)\b|\b(\d{1,4})\s+(days?|weeks?|hours?)\s+ago\b', low):
            n = int(m.group(1) or m.group(3));unit = (m.group(2) or m.group(4)).rstrip('s')
            out.append((str(now_ms - n * {'day': 86400000, 'week': 7 * 86400000, 'hour': 3600000}[unit]), words[m.start():m.end()]))
        for m in re.finditer(r'\b(?:since|from|after)\s+(\d{4})-(\d{2})-(\d{2})\b', low):
            try:out.append((str(start(datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))), words[m.start():m.end()]))
            except ValueError:
                continue
    elif kind == 'days':
        for m in re.finditer(r'\b(?:older\s+than|over|more\s+than|at\s+least)\s+(?:a|an|one|(\d{1,4}))\s*(day|days|week|weeks|month|months|year|years)\b(?:\s+old)?|\b(\d{1,4})\s+(days?|weeks?|months?|years?)\s+old\b', low):
            n = int(m.group(1) or m.group(3) or 1);unit = (m.group(2) or m.group(4)).rstrip('s')
            out.append((str(n * {'day': 1, 'week': 7, 'month': 30, 'year': 365}[unit]), words[m.start():m.end()]))
    elif kind == 'picture':
        for m in re.finditer(r'\b(\d{2,5})\s*[x×]\s*(\d{2,5})\b', low):out.append(('%sx%s' % (m.group(1), m.group(2)), words[m.start():m.end()]))
        for m in re.finditer(r'\b(\d{2,5})\s*(?:px|pixels?)(?:\s+wide)?\b|\b(\d{2,5})\s+wide\b|\b(?:to|at)\s+(\d{2,5})\b(?!\s*(?:%|mb|kb|gb|days?|x))', low):
            out.append((m.group(1) or m.group(2) or m.group(3), words[m.start():m.end()]))
        for m in re.finditer(r'\b(\d{1,2})\s*%|\b(half|quarter)(?:\s+(?:the\s+)?size)?\b', low):
            out.append(('%s%%' % (m.group(1) or {'half': 50, 'quarter': 25}[m.group(2)]), words[m.start():m.end()]))
    elif kind in ('format', 'kinds'):
        for m in re.finditer(r'\b(?:(to|as|into|in)\s+)?(png|pngs|jpe?gs?|webps?|gifs?|tiff?|bmp)\b', low):
            value = FORMAT_WORDS.get(m.group(2), m.group(2))
            if kind == 'format' and m.group(1):out.insert(0, (value, words[m.start():m.end()]))
            elif kind == 'format':out.append((value, words[m.start():m.end()]))
            elif not m.group(1):out.append((value, words[m.start(2):m.end(2)]))
        if kind == 'kinds':
            for m in re.finditer(r'\b(pdfs?|zips?|pictures|photos|images|text files)\b', low):
                if m.group(1).startswith('pdf'):out.append(('pdf', words[m.start():m.end()]))
    elif kind == 'words':
        m = re.search(r'\b(?:containing|contains|with\s+the\s+words?|that\s+(?:says?|mentions?|contains?|holds?|has)|mentioning|saying|about)\s+(.+)$', words, re.I)
        if m:out.append((m.group(1).strip(' “”"?.'), m.group(0)))
        m = re.search(r'\b(?:called|named)\s+(.+?)(?:\s+(?:in|from|on)\s+\S+)?$', words, re.I)
        if m:out.append((m.group(1).strip(' “”"?.'), m.group(0)))
        for m in re.finditer(r'[“"]([^”"]+)[”"]', words):out.insert(0, (m.group(1), m.group(0)))
    elif kind == 'name':
        m = re.search(r'\b(?:called|named|as)\s+[“"]?([^”"]+?)[”"]?(?:\s+(?:in|from|to)\s+\S+)?\s*$', words, re.I)
        if m:out.append((m.group(1).strip(' ?.'), m.group(0)))
    elif kind in ('find', 'replace'):
        m = (re.search(r'\breplace\s+[“"]([^”"]*)[”"]\s+with\s+[“"]([^”"]*)[”"]', words, re.I)
             or re.search(r'\b(?:replace|change)\s+[“"]?(.+?)[”"]?\s+(?:with|to|into|by)\s+[“"]?(.+?)[”"]?(?:\s+in\s+(?:the\s+)?(?:names?|\S+))?\s*$', words, re.I))
        if m:out.append((m.group(1), m.group(1)) if kind == 'find' else (m.group(2), m.group(2)))
        if kind == 'find':
            m = re.search(r'\b(?:remove|take\s+out|strip|delete|drop)\s+[“"]?(.+?)[”"]?\s+(?:from|out\s+of)\s+(?:the\s+)?(?:file\s+)?names?\b', words, re.I)
            if m:out.append((m.group(1), m.group(1)))
    elif kind == 'case':
        for m in re.finditer(r'\b(lower|upper)[\s-]?case\b|\b(lowercase|uppercase|small letters|capitals)\b', low):
            w = m.group(1) or m.group(2)
            out.append(('lower' if w in ('lower', 'lowercase', 'small letters') else 'upper', words[m.start():m.end()]))
    return out


def checked(kind, value, folder=None):
    """A slot's value checked against its type: the normal form, or a Refused in words. Every value passes here, whoever
    picked it (her dictionary, the model's W, your press)."""
    value = str(value if value is not None else '').strip()
    if not value:raise Refused('RECIPE_SLOT_EMPTY: %s' % TYPE_WORDS.get(kind, kind))
    if kind in ('folder', 'drive'):
        if not hr.named_absolute(value):raise Refused('RECIPE_SLOT_FOLDER: “%s” is not a folder from ~ or /' % value[:80])
        path = hr.expand(value)
        if path is None:raise Refused('RECIPE_SLOT_FOLDER: “%s” climbs out with ..' % value[:80])
        if kind == 'drive' and not bx.on_drive(path):raise Refused('RECIPE_SLOT_DRIVE: %s is not a drive (under /media, /run/media or /mnt)' % value[:80])
        return hr.tilde(path) if hr.within(path, hr.home()) else str(path)
    if kind == 'file':
        path = hr.expand(value) if hr.named_absolute(value) else None
        if path is None:
            for base in ([folder] if folder else []) + ['~/Downloads', '~/Documents', '~/Desktop', '~']:
                p = hr.expand(base)
                if p is not None and (p / value).is_file():path = p / value;break
        if path is None:raise Refused('RECIPE_SLOT_FILE: I found no “%s” in %s' % (value[:80], ', '.join(([hr.tilde(hr.expand(folder))] if folder and hr.expand(folder) else []) + ['Downloads', 'Documents', 'Desktop', 'Home'])))
        return hr.tilde(path) if hr.within(path, hr.home()) else str(path)
    if kind in ('size', 'since', 'days'):
        if not re.fullmatch(r'\d{1,16}', value):
            got = candidates(kind, value)
            if not got:raise Refused('RECIPE_SLOT_%s: “%s” is not %s' % (kind.upper(), value[:40], TYPE_WORDS[kind]))
            value = got[0][0]
        if kind == 'days' and not 0 < int(value) <= 36500:raise Refused('RECIPE_SLOT_DAYS: %s days is out of reach' % value)
        return value
    if kind == 'picture':
        if bx.geometry(value) is None:raise Refused('RECIPE_SLOT_PICTURE: “%s” is not a picture size (1024, 800x600 or 50%%)' % value[:40])
        return value.lower().replace('×', 'x').replace(' ', '')
    if kind == 'format':
        v = FORMAT_WORDS.get(value.lower())
        if v is None:raise Refused('RECIPE_SLOT_FORMAT: “%s” is not one of png, jpg, webp, gif, tiff, bmp' % value[:40])
        return v
    if kind == 'kinds':
        parts = [FORMAT_WORDS.get(p, p) for p in re.split(r'[,\s]+', value.lower()) if p]
        if not all(re.fullmatch(r'[a-z0-9]{1,8}|\*', p) for p in parts):raise Refused('RECIPE_SLOT_KINDS: “%s” is not a list of file kinds' % value[:40])
        return ','.join(parts)
    if kind == 'case':
        if value not in ('lower', 'upper'):raise Refused('RECIPE_SLOT_CASE: lower or upper')
        return value
    if kind in ('words', 'name', 'find', 'replace'):
        if len(value) > 200 or '\0' in value or (kind == 'name' and '/' in value):raise Refused('RECIPE_SLOT_TEXT: “%s” cannot be %s' % (value[:40], TYPE_WORDS[kind]))
        return value
    raise Refused('RECIPE_SLOT_TYPE: %s' % kind)


# ---- her dictionary: the words that call a recipe ----------------------------------------------------------------------------
def _stem(w):
    w = w.lower().strip(".,;:?'’“”\"()")
    for end in ('ies',):
        if w.endswith(end) and len(w) > 4:return w[:-3] + 'y'
    if w.endswith('es') and len(w) > 4 and w[-3] in 'sxz':return w[:-2]
    if w.endswith('s') and len(w) > 3 and not w.endswith('ss'):return w[:-1]
    return w


def tokens(text):
    return [_stem(w) for w in re.findall(r"[A-Za-z0-9]+", str(text or '').lower().replace("'s ", ' ').replace("’s ", ' '))]


def _span(have, want):
    """The fewest of the owner's words that hold `want` in its order (None when they do not)."""
    best = None
    for i, t in enumerate(have):
        if t != want[0]:continue
        at = i
        for w in want[1:]:
            try:at = have.index(w, at + 1)
            except ValueError:
                at = None;break
        if at is not None and (best is None or at - i + 1 < best):best = at - i + 1
    return best


def score(recipe, text):
    """(points, the phrase, its span): the recipe's best phrase whose words the owner's words hold in its order and close
    together (at most two words between); a phrase of one word only alone, in a short request ("battery", "any updates").
    Names, paths and numbers are not request words. 0 when no phrase is held."""
    best = (0, '', 99)
    bare = re.sub(r'[“"][^”"]*[”"]|\S+\.[A-Za-z0-9]{2,5}\b|[~/]\S*|\d\S*', ' ', str(text or ''))
    have = tokens(bare);plain = [t for t in have if t not in STOP]
    for phrase in recipe.words:
        raw = tokens(phrase);want = [t for t in raw if t not in STOP]
        if not want:continue
        if len(want) == 1 and (len(raw) != 1 or len(plain) > 2):continue
        span = _span(have, want)
        if span is None or span > len(want) + 2:continue
        points = len(want) * 2
        if (points, -span) > (best[0], -best[2]):best = (points, phrase, span)
    return best


def pick_words(text, environ=None, today=None):
    """Her dictionary's pick for the owner's words: the recipe and every slot it could fill, or None."""
    recipes, _ = library(environ)
    ranked = sorted(((score(r, text), r) for r in recipes), key=lambda sr: (-sr[0][0], sr[0][2], sr[1].n))
    if not ranked or ranked[0][0][0] == 0:return None
    (points, phrase, _), recipe = ranked[0]      # the most words of a phrase, then the closest together, then the first in the book
    return fill(recipe, text, by='dictionary', phrase=phrase, today=today)


def fill(recipe, text, by='dictionary', phrase='', chosen=None, today=None):
    """The pick: every slot from the owner's words (or `chosen`: {slot: (value, words, basis)}), then the recipe's default;
    a slot with neither is missing and asked."""
    slots, missing = {}, []
    chosen = chosen or {}
    used = set()
    folder_given = None
    order = sorted(recipe.slots, key=lambda s: 0 if recipe.slots[s]['type'] == 'folder' else 1)
    for name in order:
        spec = recipe.slots[name];kind = spec['type']
        if name in chosen:
            value, said, basis = chosen[name]
        else:
            got = [c for c in candidates(kind, text, today=today) if c[1] not in used] if not spec.get('fixed') else []
            value, said, basis = (None, '', '')
            why = ''
            for v, w in got:      # the first of the owner's words that is a value of its type (a file that is there)
                try:
                    checked(kind, v, folder_given);value, said, basis = v, w, 'owner_words';break
                except Refused as exc:
                    why = why or str(exc).split(': ', 1)[-1]
            if value is None and got and not spec.get('default') and not spec.get('optional'):
                slots[name] = {'value': None, 'words': got[0][1], 'basis': '', 'why': why}
                missing.append(name);continue
        if value is not None:
            try:
                value = checked(kind, value, folder_given);used.add(said)
            except Refused as exc:
                slots[name] = {'value': None, 'words': said, 'basis': basis, 'why': str(exc).split(': ', 1)[-1]}
                missing.append(name);continue
        elif spec.get('default') is not None:
            value, said, basis = checked(kind, spec['default'], folder_given), '', 'recipe_default'
        elif spec.get('optional'):
            continue
        else:
            missing.append(name);slots[name] = {'value': None, 'words': '', 'basis': ''};continue
        slots[name] = {'value': value, 'words': said, 'basis': basis}
        if kind == 'folder':folder_given = value
    need = recipe.data.get('need_one')
    if need and not any(slots.get(n, {}).get('value') for n in need):
        missing.append(need[0]);slots.setdefault(need[0], {'value': None, 'words': '', 'basis': ''})
    values = {k: v['value'] for k, v in slots.items() if v.get('value') is not None}
    question = None
    if missing:
        name = missing[0];spec = recipe.slots[name]
        question = {'slot': name, 'words': spec.get('ask') or 'Which %s?' % TYPE_WORDS.get(spec['type'], spec['type']),
                    'why': slots.get(name, {}).get('why', ''), 'choices': choices(spec['type'])}
    return {'recipe': recipe.id, 'n': recipe.n, 'name': recipe.name, 'title': recipe.title(values), 'reads': recipe.reads, 'by': by,
            'phrase': phrase, 'slots': slots, 'values': values, 'missing': missing, 'question': question}


def choices(kind):
    """What the one question card offers to press: [(label, value)] (the owner's press fills the slot: owner_click)."""
    if kind == 'folder':
        out = []
        for label, value in (('Home', '~'), ('Downloads', '~/Downloads'), ('Documents', '~/Documents'), ('Pictures', '~/Pictures'), ('Desktop', '~/Desktop')):
            p = hr.expand(value)
            if p is not None and p.is_dir():out.append((label, value))
        return out
    if kind == 'drive':return [(d['name'], d['path']) for d in bx.drives()][:6]
    if kind == 'format':return [('PNG', 'png'), ('JPG', 'jpg'), ('WEBP', 'webp')]
    if kind == 'picture':return [('1920 px', '1920'), ('1024 px', '1024'), ('Half size', '50%')]
    if kind == 'size':return [('100 MB', str(100 << 20)), ('500 MB', str(500 << 20)), ('1 GB', str(1 << 30))]
    if kind == 'days':return [('30 days', '30'), ('90 days', '90'), ('A year', '365')]
    if kind == 'case':return [('lower case', 'lower'), ('UPPER CASE', 'upper')]
    return []


def answer(pick, slot, value, environ=None):
    """The one question answered by your press (or your words): the same pick with that slot filled (basis owner_click)."""
    recipe = find_recipe(pick['recipe'], environ)
    chosen = {k: (v['value'], v.get('words', ''), v.get('basis', '')) for k, v in pick['slots'].items() if v.get('value') is not None}
    chosen[slot] = (value, str(value), 'owner_click')
    return fill(recipe, '', by=pick.get('by', 'dictionary'), phrase=pick.get('phrase', ''), chosen=chosen)


# ---- the model picks by number (the RECIPE turn kind) ---------------------------------------------------------------------
def _brief():
    return ('You pick one of Graphite\'s recipes for the owner\'s request. Answer with the recipe\'s number, then, for each '
            'slot you can fill, a space, the slot\'s name, "=" and a W number from the owner\'s words listed. Fill a slot only '
            'with a W of its type. Leave out a slot no W fits; it is asked. Answer 0 when no recipe does what was asked. '
            'Nothing runs from your answer: the owner sees what it would do first.')


def _stable(i):
    lines = ['Recipes:']
    for r in i['menu']:
        lines.append('%d %s%s' % (r['n'], r['name'], ' (%s)' % ', '.join('%s: %s' % (k, TYPE_WORDS.get(t, t)) for k, t in r['slots'].items()) if r['slots'] else ''))
    return '\n'.join(lines)


def _last(i):
    lines = ['Request: “%s”' % i['request']]
    if i['spans']:lines.append('The owner\'s words:')
    for w in i['spans']:lines.append('W%d “%s” %s' % (w['w'], w['words'], TYPE_WORDS.get(w['type'], w['type'])))
    return '\n'.join(lines)


def _grammar(i):
    from . import grammars
    lit = grammars.literal
    rules, roots = [], [lit('0')]
    for r in i['menu']:
        parts = [lit(str(r['n']))]
        for k, t in r['slots'].items():
            ws = [w['w'] for w in i['spans'] if w['type'] == t]
            if ws:parts.append('(%s (%s))?' % (lit(' %s=' % k), ' | '.join(lit('W%d' % w) for w in ws)))
        name = 'r%d' % r['n'];rules.append('%s ::= %s' % (name, ' '.join(parts)));roots.append(name)
    return '\n'.join(['root ::= ' + ' | '.join(roots)] + rules)


def _parse(said, i):
    from . import model_words
    text = said.for_check().strip() if isinstance(said, model_words.ModelSaid) else str(said).strip()
    m = re.fullmatch(r'(\d{1,3})((?: [a-z]+=W\d{1,2})*)', text)
    if not m:raise model_words.Invalid('RECIPE_SHAPE')
    return int(m.group(1)), tuple(tuple(p.split('=')) for p in m.group(2).split())


def _check(obj, i):
    from . import turns
    n, fills = obj
    if n == 0:return turns.Verdict('UNSETTLED', value=None, why=('RECIPE_NONE',), checks=(('recipe', True, '0'),))
    menu = {r['n']: r for r in i['menu']}
    if n not in menu:return turns.Verdict('REFUSED', why=('RECIPE_NOT_ON_MENU',), checks=(('recipe', False, str(n)),))
    spans = {w['w']: w for w in i['spans']};row = menu[n];chosen = {};checks = [('recipe', True, row['name'])];refused = []
    for slot, w in fills:
        span = spans.get(int(w[1:]))
        if slot not in row['slots'] or span is None or span['type'] != row['slots'][slot]:
            refused.append(slot);checks.append((slot, False, 'not a W of its type'));continue
        chosen[slot] = (span['value'], span['words'], 'owner_words');checks.append((slot, True, span['words']))
    value = {'n': n, 'id': row['id'], 'chosen': chosen}
    return turns.Verdict('TRIMMED' if refused else 'TAKEN', value=value, why=('RECIPE_SLOT_REFUSED',) if refused else (), checks=tuple(checks))


def _fallback(i):
    from . import turns
    return turns.Fallback('PATTERNS', i['desk']) if i.get('desk') else turns.Fallback('CANNOT_TELL', None)


def _kind():
    from . import turns
    return turns.register(turns.TurnKind(name='RECIPE', version=1, switch='choosing', brief=_brief, stable=_stable, last=_last,
                                         grammar=_grammar, caps=turns.Caps(new_tokens=1600, answer_tokens=40, deadline_ms=20000),
                                         parse=_parse, check=_check, fallback=_fallback, paper=''))


def model_inputs(text, environ=None, today=None):
    """What the model is shown: the recipes by number, and the owner's words that read as a value of some type, numbered."""
    recipes, _ = library(environ)
    menu = [{'n': r.n, 'id': r.id, 'name': r.name, 'slots': {k: v['type'] for k, v in r.slots.items() if not v.get('fixed')}} for r in recipes]
    spans, seen = [], set()
    for kind in TYPES:
        for value, said in candidates(kind, text, today=today):
            if (kind, value) in seen or len(spans) >= 24:continue
            seen.add((kind, value));spans.append({'w': len(spans) + 1, 'type': kind, 'value': value, 'words': said})
    return {'request': ' '.join(str(text).split())[:400], 'menu': menu, 'spans': spans, 'desk': pick_words(text, environ, today)}


def pick(text, request=None, environ=None, today=None):
    """The pick for the owner's words: with a live model (request: a turns.TurnRequest), the model's number and W's, checked;
    else, and whenever the model's answer is refused or late, her dictionary's. None when neither finds a recipe."""
    if request is None:return pick_words(text, environ, today)
    from . import turns
    inputs = model_inputs(text, environ, today)
    got = turns.ask(_kind(), inputs, request)
    if not got.by_model:return got.value
    if got.value is None:return None
    recipe = find_recipe(got.value['id'], environ)
    return fill(recipe, '', by='model', chosen=got.value['chosen'], today=today)


# ---- the dry run, the look, the run, the undo -------------------------------------------------------------------------------
def _args(recipe, step, values):
    """A step's arguments, its slots filled (as the operation's schema types them)."""
    props = bx.FIELDS[step['op']][0];out = {}
    for key, template in (step.get('args') or {}).items():
        names = re.findall(r'\{(\w+)\}', str(template))
        if names and any(values.get(n) is None for n in names):continue      # an optional slot not given: the argument is left out
        if isinstance(template, str) and re.fullmatch(r'\{(\w+)\}', template):value = values[names[0]]
        elif isinstance(template, str):value = re.sub(r'\{(\w+)\}', lambda m: str(values[m.group(1)]), template)
        else:value = template
        kind = props.get(key, {}).get('type')
        if kind == 'integer':value = int(value)
        elif kind == 'array':value = [value] if isinstance(value, str) else list(value)
        else:value = str(value)
        out[key] = value
    return out


def _values(recipe, slots):
    """The slots given to an operation (a pick's values, or a press's), every one checked again by its type."""
    if not isinstance(slots, dict):raise Refused('RECIPE_SLOTS: the slots are a table')
    out = {};folder = None
    for name in sorted(slots, key=lambda s: 0 if recipe.slots.get(s, {}).get('type') == 'folder' else 1):
        if name not in recipe.slots:raise Refused('RECIPE_SLOT_UNKNOWN: %s takes no %s' % (recipe.name, name))
        value = slots[name]
        if value is None or value == '':continue
        out[name] = checked(recipe.slots[name]['type'], value, folder)
        if recipe.slots[name]['type'] == 'folder':folder = out[name]
    for name, spec in recipe.slots.items():
        if name not in out and spec.get('default') is not None:out[name] = checked(spec['type'], spec['default'], folder)
    missing = [n for n, s in recipe.slots.items() if n not in out and not s.get('optional')]
    if missing:raise Refused('RECIPE_SLOT_MISSING: %s needs %s' % (recipe.name, ', '.join(TYPE_WORDS[recipe.slots[n]['type']] for n in missing)))
    need = recipe.data.get('need_one')
    if need and not any(n in out for n in need):raise Refused('RECIPE_SLOT_MISSING: %s needs %s' % (recipe.name, ' or '.join(TYPE_WORDS[recipe.slots[n]['type']] for n in need)))
    return out


def _pre(recipe, values):
    out = []
    for pre in recipe.pre:
        for key in ('folder', 'file'):
            if key in pre:
                text = values.get(pre[key]);path = hr.expand(text) if text else None
                ok = path is not None and (path.is_dir() if key == 'folder' else path.is_file())
                if ok and pre.get('suffix'):ok = path.name.lower().endswith(pre['suffix'])
                out.append({'ok': ok, 'words': '%s is there' % shown(key, text) if ok else '%s is not there%s' % (
                    shown(key, text), ' as a %s file' % pre['suffix'].lstrip('.').upper() if pre.get('suffix') and path is not None and path.exists() else '')})
    return out


def dry_run(kernel, ident, slots, environ=None):
    """recipes.dry_run: exactly what the recipe would do, step by step, with the digest a press carries. Nothing changes;
    a read step only says what it reads."""
    recipe = find_recipe(ident, environ);values = _values(recipe, slots)
    pre = _pre(recipe, values);steps = [];needs = []
    for step in recipe.steps:
        args = _args(recipe, step, values);op = step['op']
        need = bx.needs(op, args)
        if need:
            needs.append(need);pre.append({'ok': bool(need['found']), 'words': '%s is on this computer' % need['program'] if need['found']
                                           else '%s is not on this computer: Debian\'s package “%s” has it' % (need['program'], need['package'])})
        if bx.SCOPES[op] == 'read':
            steps.append({'op': op, 'args': args, 'scope': 'read', 'words': 'It %s; nothing changes.' % bx.READ_WORDS[op].format(**{k: shown(k, v) for k, v in args.items()}),
                          'lines': [], 'expect': ''})
            continue
        if not all(p['ok'] for p in pre):
            steps.append({'op': op, 'args': args, 'scope': bx.SCOPES[op], 'words': 'Not planned: a precondition is not met.', 'lines': [], 'expect': '',
                          'count': 0, 'left': []});continue
        try:planned = bx.plan(kernel, op, args)
        except bx.Refused as exc:
            pre.append({'ok': False, 'words': str(exc).split(': ', 1)[-1]})
            steps.append({'op': op, 'args': args, 'scope': bx.SCOPES[op], 'words': 'Not planned: %s' % str(exc).split(': ', 1)[-1], 'lines': [],
                          'expect': '', 'count': 0, 'left': []});continue
        steps.append({'op': op, 'args': args, 'scope': bx.SCOPES[op], 'words': planned['words'], 'lines': planned['lines'], 'count': planned['count'],
                      'bytes': planned['bytes'], 'left': [{'name': l['name'], 'why': l['why']} for l in planned.get('left') or []][:50],
                      'expect': planned['expect'], 'undo': planned['undo'], 'can_undo': planned['can_undo']})
    ok = all(p['ok'] for p in pre) and (recipe.reads or any(s.get('count') for s in steps))
    bound = [{'op': s['op'], 'args': s['args'], 'expect': s['expect']} for s in steps]
    return {'recipe': recipe.id, 'n': recipe.n, 'name': recipe.name, 'title': recipe.title(values), 'reads': recipe.reads, 'values': values,
            'pre': pre, 'steps': steps, 'ok': ok, 'needs': needs, 'undo': recipe.undo_words(), 'can_undo': recipe.undo_words() != bx.CANNOT,
            'scope': 'read' if recipe.reads else ('approve' if any(s['scope'] == 'approve' for s in steps) else 'execute'),
            'digest': bx.digest(bound), 'nothing': not recipe.reads and all(p['ok'] for p in pre) and not any(s.get('count') for s in steps)}


def ensure(db):
    db.execute('''CREATE TABLE IF NOT EXISTS recipe_runs(id TEXT PRIMARY KEY, owner TEXT, recipe TEXT, title TEXT, at INTEGER, state TEXT,
                  verified INTEGER, slots TEXT, steps TEXT, undone INTEGER)''')


def _record(kernel, principal, recipe, title, values, state, verified, steps):
    from . import files_service
    ident = uuid.uuid4().hex
    with files_service.opened(kernel) as db:
        ensure(db)
        db.execute('INSERT INTO recipe_runs VALUES(?,?,?,?,?,?,?,?,?,NULL)', (ident, principal.identity, recipe.id, title, bx._now_ms(), state,
                                                                              1 if verified else 0, json.dumps(values), json.dumps(steps)))
    return ident


def look(kernel, ident, slots, principal, environ=None):
    """recipes.look: a recipe that only reads, run now (reads run on their own): each step through the Kernel, its answer as
    data, verified by the step's own check."""
    recipe = find_recipe(ident, environ)
    if not recipe.reads:raise Refused('RECIPE_CHANGES: “%s” changes something; it runs on your press, after its dry run' % recipe.name)
    values = _values(recipe, slots);out = [];verified = True
    for step in recipe.steps:
        args = _args(recipe, step, values)
        need = bx.needs(step['op'], args)
        if need and not need['found']:
            raise Refused('RECIPE_NEEDS_PROGRAM: %s is not on this computer. Debian\'s package “%s” has it; nothing was read.' % (need['program'], need['package']))
        answer = kernel.dispatch(step['op'], args, principal)
        if not answer.get('ok'):raise Refused('RECIPE_STEP_REFUSED: %s' % str((answer.get('error') or {}).get('message', 'refused')).split(': ', 1)[-1])
        got = answer['result'];verified = verified and bool(got.get('verified'))
        out.append({'op': step['op'], 'args': args, 'words': got.get('words', ''), 'rows': got.get('rows', [])[:bx.MOST_ROWS],
                    'checked': got.get('checked', ''), 'verified': bool(got.get('verified')), 'cut': bool(got.get('cut'))})
    title = recipe.title(values)
    run = _record(kernel, principal, recipe, title, values, 'read', verified, [{k: s[k] for k in ('op', 'args', 'words', 'checked', 'verified')} for s in out])
    return {'run': run, 'recipe': recipe.id, 'title': title, 'reads': True, 'steps': out, 'verified': verified,
            'words': ' '.join(s['words'] for s in out), 'checked': '; '.join(s['checked'] for s in out if s['checked'])}


def run(kernel, ident, slots, digest, principal, environ=None):
    """recipes.run: a recipe with a change, on your press. The dry run is made again and must be the one you saw (the digest);
    each step goes through the Kernel with your principal (its scope checked there); done only when every step verified."""
    from . import halt_gate
    recipe = find_recipe(ident, environ)
    if recipe.reads:raise Refused('RECIPE_READS: “%s” only reads: it runs on its own (recipes.look)' % recipe.name)
    if hr.in_her_work(principal):
        raise Refused('RECIPE_YOUR_PRESS: “%s” changes something, so it runs on your press only, never as a step of mine' % recipe.name)
    if halt_gate.held(kernel):raise Refused('RECIPE_HALT: HALT holds my work. Press RESUME first; nothing ran.')
    dry = dry_run(kernel, ident, slots, environ)
    if dry['digest'] != digest:raise Refused('RECIPE_PLAN_CHANGED: what it would do changed since you saw it, so nothing ran. Look at it again.')
    if not dry['ok']:raise Refused('RECIPE_NOT_READY: %s' % ('; '.join(p['words'] for p in dry['pre'] if not p['ok']) or 'there is nothing to do'))
    out = [];verified = True;state = 'done'
    for step in dry['steps']:
        args = dict(step['args'])
        if step['scope'] != 'read':args['expect'] = step['expect']
        answer = kernel.dispatch(step['op'], args, principal)
        if not answer.get('ok'):
            why = str((answer.get('error') or {}).get('message', 'refused')).split(': ', 1)[-1]
            out.append({'op': step['op'], 'state': 'refused', 'verified': False, 'checked': why, 'change': None});verified = False;state = 'stopped';break
        got = answer['result']
        out.append({'op': step['op'], 'state': got.get('state', 'read'), 'verified': bool(got.get('verified')), 'checked': got.get('checked', ''),
                    'change': got.get('change'), 'done': got.get('done'), 'count': got.get('count'), 'to': got.get('to'), 'error': got.get('error', ''),
                    'words': got.get('words', '')})
        verified = verified and bool(got.get('verified'))
        if got.get('state') not in (None, 'done', 'read'):state = got['state'];break
    if state == 'done' and not verified:state = 'not verified'
    title = dry['title']
    ident_run = _record(kernel, principal, recipe, title, dry['values'], state, verified, out)
    return {'run': ident_run, 'recipe': recipe.id, 'title': title, 'state': state, 'verified': verified, 'steps': out,
            'checked': '; '.join(s['checked'] for s in out if s.get('checked')), 'can_undo': dry['can_undo'] and any(s.get('change') for s in out),
            'undo': dry['undo']}


def load_run(kernel, ident):
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db);row = db.execute('SELECT * FROM recipe_runs WHERE id=?', (ident,)).fetchone()
    if row is None:raise Refused('RECIPE_UNKNOWN_RUN: no such run')
    return {k: row[k] for k in row.keys()}


def undo(kernel, ident, principal):
    """recipes.undo: the run put back, every step's change newest first (box_ops.undo: what changed since is named)."""
    row = load_run(kernel, ident)
    if row['undone']:raise Refused('RECIPE_UNDONE: already taken back')
    steps = json.loads(row['steps']);back, left = [], []
    changes = [s['change'] for s in steps if s.get('change')]
    if not changes:raise Refused('RECIPE_NOTHING_TO_UNDO: “%s” changed nothing' % row['title'])
    for change in reversed(changes):
        try:
            got = bx.undo(kernel, change, principal);back += got['back'];left += got['left']
        except bx.Refused as exc:
            left.append(str(exc).split(': ', 1)[-1])
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db);db.execute('UPDATE recipe_runs SET undone=? WHERE id=?', (bx._now_ms(), ident))
    return {'run': ident, 'title': row['title'], 'back': back, 'left': left, 'verified': not left,
            'words': '%s put back where they were.' % bx.count_words(len(back), 'thing') + (' Left as it is: %s.' % '; '.join(left[:4]) if left else '')}


def runs(kernel, limit=20):
    from . import files_service
    with files_service.opened(kernel) as db:
        ensure(db)
        rows = db.execute('SELECT id, recipe, title, at, state, verified, undone FROM recipe_runs ORDER BY at DESC LIMIT ?', (int(limit),)).fetchall()
    return {'runs': [{k: r[k] for k in r.keys()} for r in rows]}


# ---- the Kernel's operations -------------------------------------------------------------------------------------------------
WORDS_ARG = {'type': 'string', 'minLength': 1, 'maxLength': 400}
IDENT = {'type': 'string', 'minLength': 1, 'maxLength': 60}
SLOTS = {'type': 'object'}
FIELDS = {
    'recipes.list': ({}, []),
    'recipes.pick': ({'words': WORDS_ARG}, ['words']),
    'recipes.dry_run': ({'recipe': IDENT, 'slots': SLOTS}, ['recipe']),
    'recipes.look': ({'recipe': IDENT, 'slots': SLOTS}, ['recipe']),
    'recipes.run': ({'recipe': IDENT, 'slots': SLOTS, 'digest': bx.EXPECT}, ['recipe', 'digest']),
    'recipes.undo': ({'run': bx.ID}, ['run']),
    'recipes.runs': ({'limit': {'type': 'integer', 'minimum': 1, 'maximum': RUNS_MOST}}, []),
}
SCOPES = {'recipes.list': 'read', 'recipes.pick': 'read', 'recipes.dry_run': 'read', 'recipes.look': 'read', 'recipes.run': 'execute',
          'recipes.undo': 'approve', 'recipes.runs': 'read'}


def _slots(args):
    s = args.get('slots') or {}
    if not all(isinstance(k, str) and isinstance(v, (str, int)) and len(str(v)) <= 1000 for k, v in s.items()):raise Refused('RECIPE_SLOTS: each slot is a short value')
    return {k: str(v) for k, v in s.items()}


def dispatch(kernel, op, args, principal):
    if op == 'recipes.list':
        recipes, refused = library()
        return {'recipes': [r.row() for r in recipes], 'refused': refused, 'yours': str(own_folder())}
    if op == 'recipes.pick':
        got = pick_words(args['words'])
        return {'pick': got, 'found': got is not None}
    if op == 'recipes.dry_run':return dry_run(kernel, args['recipe'], _slots(args))
    if op == 'recipes.look':return look(kernel, args['recipe'], _slots(args), principal)
    if op == 'recipes.run':return run(kernel, args['recipe'], _slots(args), args['digest'], principal)
    if op == 'recipes.undo':return undo(kernel, args['run'], principal)
    if op == 'recipes.runs':return runs(kernel, args.get('limit') or 20)
    raise ValueError('RECIPE_UNKNOWN_OPERATION')


# ---- where she offers them: the line, and the words she reads as a request for the list ----------------------------------
def asks_for_list(text):
    return bool(LIST_WORDS.match(str(text or '')))


def line_pick(text, environ=None):
    """For the line on the bar: her dictionary's pick when the words call a recipe clearly (two words of its phrase, or a
    one-word phrase that is all the line holds), else None. Fast: the library is read once and kept."""
    words = ' '.join(str(text or '').split())
    if len(words) < 3 or words[:1] in '=?$>/@' or re.search(r'(?:^|\s)--?[A-Za-z]', words):return None      # a command line is the Terminal's
    got = pick_words(words, environ)
    if got is None:return None
    recipe = find_recipe(got['recipe'], environ)
    points = score(recipe, words)[0]
    if points < 4 and len(tokens(words)) > 2:return None
    return got
