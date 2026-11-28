"""Her reach in Home, finished: the Home file tools on her model's PLAN menu, and one press for a folder's grants (1.0 K10).

Found by the everyday walkthrough (X3): "the model's planning menu has no file tools and plans at most four steps"; "under
one grant, the tidy's folder-making steps still waited for their own word". This module gives:

THE HOME FILE TOOLS IN THE REGISTRY (K2). Three more, beside 5 (rename), 6 (move) and 7 (new folder):
  24 files.list    list a folder: its files and folders, one level                       a read
  25 files.copy    copy a file or a folder into another folder; the original stays       a change ("copy files in the folder")
  26 files.trash   put a file or a folder in the bin (DELETE keeps it; Restore and Undo  a change ("put files in the bin")
                   put it back): never an unrecoverable delete
Each has its check (assignments.CHECKS): a list is read again and lists the same; a copy is done when the same content
(digest) is in the folder and the original is still where it was; a file is in the bin when it is gone from its place and the
same content is in the bin. Her changes reach only inside your home (home_reach, L6) and each needs your press or a grant of
yours, enforced at dispatch (K3): nothing here widens that.

THE PLAN MENU (K4, K4b). Her model's PLAN question lists 24, 7, 6, 5, 25 and 26 among its tools, always (the menu stays the
same for every request on a desk, so it stays primed). A request that names a folder of your home brings the things of your
home it names into the question, each with a D handle the desk fills every argument from (the model never writes a path or
a name):
  a folder            D1 folder “~/Downloads”
  a file              D7 file “~/Downloads/council-tax-2026-27.pdf”
  a group             D2 group “the 5 files at the top of ~/Downloads whose names end .pdf, for a folder PDFs” (a deduction
                      from the ends of their names, said as such; only when the words sort, tidy or name a kind)
A model's plan may run to eight steps (objective_plan.MOST_STEPS; the desk's own planner keeps its length). A step on a
group is the desk's to expand: "6 D2" moves each of its files into its folder, making the folder first when it is not
there and no earlier step makes it; "7 D2" makes the group's folder ("looks at it" when it is there already). A tool their
own verb names ("move … into", "copy", "make a folder", "put … in the bin", "tidy") is theirs; any other change is the
model's pick, offered and never done until authorised by its own name.

ONE PRESS FOR A FOLDER'S GRANTS (K3). When the step that waits for a grant is one of several in its folder that need
different operations (a tidy: make folders and move files in ~/Downloads), the press offered is "Grant these for this
assignment", with each grant in its own words, exactly as it would be given ("make folders in ~/Downloads, for this
assignment"; "move files in ~/Downloads, for this assignment"). The press gives each as its own record (a grant is still per
operation, target and scope), and the Kernel still checks each step against its own operation at dispatch.

  grant.give.set   {grants: [{operation, folder | object, scope, assignment?, until?}], expected_digest, step?}   approve
                   your press: the grants as shown (2 to 8, one target and one scope), refused unless the digest is the one
                   of the words you were shown; with step, that step is authorised by them and the plan carries on
"""
from __future__ import annotations

import re
from pathlib import Path

HOME_TOOLS = (24, 7, 6, 5, 25, 26)       # on the PLAN menu, in this order
MOST_HOME = 9                           # things of your home one PLAN question names, at most
MOST_GROUP_FILES = 24                   # files of one folder looked at for groups (everyday_desk.MOST_FILES)
SET_PRESS = 'Grant these for this assignment'
SET_MOST = 8
SHORT = {24: 'list a folder of your home', 7: 'make a folder', 6: 'move files into a folder', 5: 'rename a file',
         25: 'copy files into a folder', 26: 'put files in the bin'}
TAKES = {24: 'D folder', 7: 'D group (its folder), or D folder then W name', 6: 'D group (into its folder), or D file then D folder or S',
         5: 'D file, then W name', 25: 'D group or D file, then D folder or S', 26: 'D group or D file'}
NAMED_ONLY = (5, 25, 26)                # in a question's grammar only when the owner's own words name them (rename, copy, the bin)
SORTING = re.compile(r'\b(?:tidy|sort|organi[sz]e|clean\s+up|by\s+(?:type|kind)|into\s+folders)\b', re.I)
VERB_TOOLS = ((re.compile(r'\b(?:move|put)\b.{0,80}?\b(?:in|into|to)\b', re.I), (6,)), (re.compile(r'\bcopy\b', re.I), (25,)),
              (re.compile(r'\b(?:make|create|new)\s+(?:a\s+|the\s+)?(?:new\s+)?folders?\b', re.I), (7,)),
              (re.compile(r'\b(?:delete|bin|throw\s+(?:\S+\s+){0,4}?away|in\s+the\s+bin|trash)\b', re.I), (26,)),
              (re.compile(r'\b(?:list|what\s+is\s+in|show\s+me\s+what)\b', re.I), (24,)),
              (re.compile(r'\brename\b', re.I), (5,)))


# ---------------------------------------------------------------- the registry: tools 24, 25, 26 and their checks
def _checks():
    from . import assignments as _asg
    from . import tools_registry as tr

    def inside(kernel, text):
        from . import files_service
        return files_service.resolve(kernel, text or '', must_exist=False)

    def listing_digest(folder):
        rows = sorted([p.name, 'folder' if p.is_dir() else 'file', tr.file_sha(p) if p.is_file() else None]
                      for p in folder.iterdir() if not p.name.startswith('.'))
        return _asg.digest({'listing': rows}), rows

    class FolderList(_asg.Check):
        """files.list: a folder's files and folders, one level; read again, the same names and contents."""
        kind = 'folder';effect = 'nothing (a read)';standin_ms = 500;repeatable = True
        how = 'listed again: the same names and contents';expected = 'the files and folders in it, one level'

        def prepare(self, kernel, read, arguments):
            folder = inside(kernel, arguments.get('path'))
            if not folder.is_dir():raise _asg.Blocked('the folder %s is not there' % arguments.get('path'))
            return {'path': arguments.get('path') or '', 'digest': listing_digest(folder)[0]}

        def find(self, kernel, read, arguments, prepared):
            return None

        def verify(self, kernel, read, arguments, result, prepared, step):
            digest, rows = listing_digest(inside(kernel, prepared['path']))
            if digest != prepared['digest']:raise _asg.NotVerified('the folder changed while it was listed')
            folders = sum(1 for r in rows if r[1] == 'folder')
            return {'object': 'files:' + prepared['path'], 'revision': digest, 'by': 'listing', 'complete': True, 'how': 'observed',
                    'path': prepared['path'], 'words': '%d files and %d folders in it, listed and listed again the same' % (len(rows) - folders, folders)}

        def still(self, kernel, read, step):
            try:digest = listing_digest(inside(kernel, step['prepared']['path']))[0]
            except (OSError, ValueError):return 'the folder is no longer there'
            return '' if digest == (step['observation'] or {}).get('revision') else 'the folder has changed since'

    class FileCopy(_asg.Check):
        """files.copy: the same content (digest) in the folder, and the original still where it was."""
        kind = 'file';effect = 'a copy made';standin_ms = 1000;repeatable = True
        how = 'the folder holds the same content (digest) under its name, and the original is still where it was'
        expected = 'a copy in the folder; the original where it was'

        def prepare(self, kernel, read, arguments):
            source = inside(kernel, arguments['path'])
            if not source.exists():raise _asg.Blocked('%s is not there' % arguments['path'])
            folder = inside(kernel, arguments['to'])
            if not folder.is_dir():raise _asg.Blocked('the folder %s is not there' % arguments['to'])
            return {'path': arguments['path'], 'into': arguments['to'], 'digest': tr.tree_digest(source), 'name': source.name,
                    'folder': source.is_dir(), 'there': sorted(p.name for p in folder.iterdir())}

        def _observed(self, kernel, prepared, target):
            from . import files_service
            rel = files_service.place_of(kernel, target)
            return {'object': 'files:' + rel, 'revision': prepared['digest'], 'by': 'sha256', 'complete': True, 'how': 'observed', 'path': rel,
                    'was': prepared['path'], 'words': 'a copy of %s is %s, the same content (digest %s); the original is still where it was'
                                                    % (prepared['path'], rel, prepared['digest'][:12])}

        def find(self, kernel, read, arguments, prepared):
            folder = inside(kernel, prepared['into']);stem, suffix = Path(prepared['name']).stem, Path(prepared['name']).suffix
            if prepared['folder']:stem, suffix = prepared['name'], ''
            for name in [prepared['name']] + ['%s %d%s' % (stem, n, suffix) for n in range(2, 60)]:
                target = folder / name
                if name not in prepared['there'] and target.exists() and tr.tree_digest(target) == prepared['digest']:
                    return self._observed(kernel, prepared, target)
            return None

        def verify(self, kernel, read, arguments, result, prepared, step):
            made = (result or {}).get('path')
            if not inside(kernel, prepared['path']).exists():raise _asg.NotVerified('the original is no longer where it was')
            if isinstance(made, str):
                target = inside(kernel, made)
                if target.exists() and tr.tree_digest(target) == prepared['digest']:return self._observed(kernel, prepared, target)
            found = self.find(kernel, read, arguments, prepared)
            if not found:raise _asg.NotVerified('the same content is not in the folder')
            return found

        def still(self, kernel, read, step):
            obs = step['observation'] or {}
            target = inside(kernel, obs.get('path', ''))
            if not target.exists():return 'the copy is no longer at %s' % obs.get('path')
            return '' if tr.tree_digest(target) == obs.get('revision') else 'the copy has changed since'

    class BinPut(_asg.Check):
        """files.trash: gone from its place, and the same content in the bin (your home's, or DELETE in Files)."""
        kind = 'file';effect = 'a file put in the bin';standin_ms = 1000;repeatable = False
        how = 'it is gone from its place and the same content (digest) is in the bin; Restore puts it back'
        expected = 'it in the bin (DELETE), restorable'

        def prepare(self, kernel, read, arguments):
            source = inside(kernel, arguments['path'])
            if not source.exists():raise _asg.Blocked('%s is not there' % arguments['path'])
            return {'path': arguments['path'], 'digest': tr.tree_digest(source), 'name': source.name}

        def _in_bin(self, kernel, result, prepared):
            from . import files_service, home_trash
            result = result or {}
            if result.get('trash') == 'home' and result.get('stored'):return home_trash.files_dir() / result['stored']
            if result.get('id'):return files_service.root(kernel) / files_service.TRASH / result['id'] / prepared['name']
            return None

        def find(self, kernel, read, arguments, prepared):
            if inside(kernel, prepared['path']).exists():return None
            raise _asg.Unknowable('it is no longer where it was; whether it went to the bin is yours to look at in DELETE')

        def verify(self, kernel, read, arguments, result, prepared, step):
            if inside(kernel, prepared['path']).exists():raise _asg.NotVerified('it is still where it was')
            held = self._in_bin(kernel, result, prepared)
            if held is None or not held.exists() or tr.tree_digest(held) != prepared['digest']:
                raise _asg.NotVerified('it is gone from its place, and the bin does not show the same content')
            return {'object': 'files:' + prepared['path'], 'revision': prepared['digest'], 'by': 'sha256', 'complete': True, 'how': 'observed',
                    'path': prepared['path'], 'words': '%s is in the bin (DELETE), the same content (digest %s); Restore puts it back'
                                                     % (prepared['path'], prepared['digest'][:12])}

        def still(self, kernel, read, step):
            return '' if not inside(kernel, step['prepared']['path']).exists() else 'it is back where it was'

    return FolderList(), FileCopy(), BinPut()


def _join_registry():
    from . import assignments as _asg
    try:
        from . import tools_registry as tr
    except Exception:  # noqa: BLE001 - K2 is not in this Graphite
        return False
    listed, copied, binned = _checks()
    _asg.CHECKS.setdefault('files.list', listed);_asg.CHECKS.setdefault('files.copy', copied);_asg.CHECKS.setdefault('files.trash', binned)
    path = tr.Arg('path', 'the file or folder, in your home or in Files')
    rows = (
        tr.Tool(24, 'files.list', 'List a folder of your home or of Files: its files and folders, one level.', 'files', 'read', ('files.list',),
                arguments=(tr.Arg('path', 'the folder', tr.READ_FROM),), preconditions=('the folder is there',), effects='nothing: a read',
                undone='nothing to undo', verify='listed again: the same names and contents'),
        tr.Tool(25, 'files.copy', 'Copy a file or a folder into another folder; the original stays where it is.', 'files', 'change',
                ('files.copy',), arguments=(path, tr.Arg('to', 'the folder the copy goes into')),
                preconditions=('it is there', 'the folder is there', 'a folder does not go into itself'),
                effects='a copy in the folder (a taken name gets a number)', undone='Delete the copy (DELETE gives it back)',
                grant='copy files into the folder', target='path', verify=copied.how, writes_files=True),
        tr.Tool(26, 'files.trash', 'Put a file or a folder in the bin: DELETE keeps it, and Restore puts it back (never an unrecoverable '
                'delete).', 'files', 'change', ('files.trash',), arguments=(path,),
                preconditions=('it is there', "it is not your home itself, Kas's own area or Egress"),
                effects='it is in the bin (DELETE)', undone='Restore it from DELETE (Undo puts it back at once)',
                grant='put files in the bin in the folder', target='path', verify=binned.how, writes_files=True),
    )
    for tool in rows:
        if tool.key in tr.TOOLS or tool.number in tr.BY_NUMBER:continue      # a number or a key already taken is never taken over
        tr.TOOLS[tool.key] = tool;tr.BY_NUMBER[tool.number] = tool
    for op in ('files.list', 'files.copy', 'files.trash'):tr.KEY_OF.setdefault(op, op)
    _asg.GRANT_WORDS.setdefault('files.copy', 'copy a file');_asg.GRANT_WORDS.setdefault('files.trash', 'put a file in the bin')
    try:
        from . import grants
        grants.OP_WORDS.setdefault('files.trash', 'put files in the bin')
    except Exception:  # noqa: BLE001 - K3 is not in this Graphite
        pass
    return True


# ---------------------------------------------------------------- the things of your home a request names
def _kinds():
    from .everyday_desk import KINDS, OTHER, kind_of
    return KINDS, OTHER, kind_of


def _words(text):
    from .places import terms
    return set(terms(text))


def _folders(objective):
    """The folders of your home the words name: a folder at the top of your home, or one inside one (by its name, whole);
    longest names first, so "Taxes 2026" wins over a word inside it."""
    from . import home_reach
    home = home_reach.home()
    if not home.is_dir():return []
    found = []
    low = ' %s ' % ' '.join(re.sub(r'[^\w~/\- ]+', ' ', objective or '').split()).casefold()
    tops = sorted((p for p in home.iterdir() if p.is_dir() and not p.name.startswith('.') and p.name != 'Concern'), key=lambda p: p.name.casefold())
    seen = []
    for top in tops:
        seen.append(top)
        try:seen.extend(sorted((p for p in top.iterdir() if p.is_dir() and not p.name.startswith('.')), key=lambda p: p.name.casefold())[:60])
        except OSError:
            continue
    for folder in sorted(seen, key=lambda p: -len(p.name)):
        name = ' '.join(folder.name.split()).casefold()
        if len(name) < 3:continue
        if re.search(r'(?<![\w])' + re.escape(name) + r'(?![\w])', low) and not any(name in f.name.casefold() for f in found):
            found.append(folder)
    return found[:2]


def home_named(desk, objective, clauses):
    """objective_plan.MORE_NAMED: the folders of your home the request names, the files in them it names, and (when it sorts,
    tidies or names a kind) its files by kind; each added to the desk with a D handle. At most MOST_HOME."""
    from . import home_reach
    from .objective_plan import Thing
    KINDS, OTHER, kind_of = _kinds()
    out = []
    asked = _words(objective)
    kinds_named = {folder for folder, _ in KINDS if _words(folder) & asked} | ({'Pictures'} if {'photo', 'image', 'picture'} & asked else set())
    for folder in _folders(objective):
        where = home_reach.tilde(folder)
        out.append(Thing('', 'folder', where, where, 'folder', {'path': str(folder)}))
        try:files = sorted((p for p in folder.iterdir() if p.is_file() and not p.name.startswith('.')), key=lambda p: p.name.casefold())
        except OSError:
            continue
        for p in files:      # a file their words name: most of the words of its name are in theirs
            have = _words(p.stem) - {'pdf', 'jpg', 'png'}
            if have and len(have & asked) * 2 >= len(have) and len(have & asked) >= 2:
                out.append(Thing('', 'file', home_reach.tilde(p), str(p), 'file', {'path': str(p)}))
        if SORTING.search(objective or '') or kinds_named:
            groups = {}
            for p in files[:MOST_GROUP_FILES]:groups.setdefault(kind_of(p.name), []).append(p)
            for kind in sorted(groups):
                if kinds_named and not SORTING.search(objective or '') and kind not in kinds_named:continue
                members = groups[kind]
                ends = sorted({p.suffix.lower() or 'nothing' for p in members})
                title = 'the %d file%s at the top of %s whose names end %s, for %s %s' % (
                    len(members), '' if len(members) == 1 else 's', where, ', '.join(ends),
                    'the folder' if (folder / kind).is_dir() else 'a folder', kind)
                out.append(Thing('', 'group', title, 'group:%s/%s' % (folder, kind), 'group',
                                 {'folder': str(folder), 'kind': kind, 'files': [str(p) for p in members], 'ends': ends}))
    out = out[:MOST_HOME]
    for thing in out:
        desk.things.append(thing);thing.handle = 'D%d' % len(desk.things)
    return out


def home_verbs(objective, clauses):
    """objective_plan.MORE_VERBS: the Home file tools their own words name."""
    out = set()
    for pattern, tools in VERB_TOOLS:
        if pattern.search(objective or ''):out |= set(tools)
    return out


# ---------------------------------------------------------------- the grammar of the Home file tools' steps
def grammar_more(i, at, kind_of):
    """objective_plan.GRAMMAR_MORE: (rules, options) for step `at`: each Home tool on the menu with exactly the handles it takes."""
    from . import grammars
    on = {n for n, _, _, _ in i.tools}
    hf = [h[1:] for h, _ in i.things if kind_of(h) == 'folder']
    hg = [h[1:] for h, _ in i.things if kind_of(h) == 'group']
    hx = [h[1:] for h, _ in i.things if kind_of(h) == 'file']
    hw = [h[1:] for h, _, _ in i.words]
    rules = []
    for name, values in (('k10f', hf), ('k10g', hg), ('k10x', hx), ('k10gx', hg + hx), ('k10w', hw)):
        if values:rules.append('%s ::= %s' % (name, ' | '.join(grammars.literal(v) for v in values)))
    lit = grammars.literal;opts = []
    on -= {n for n in NAMED_ONLY if n not in set(i.verbs)}      # the bin, a copy, a rename: only when their own words ask for it (the 4B
    # here answered a tidy with "26 D2|26 D3|…", the bin for every group: offered as its pick and never done, but not a tidy)
    if 24 in on and hf:opts.append(lit('24 D') + ' k10f')
    if 7 in on and hg:opts.append(lit('7 D') + ' k10g')
    if 7 in on and hf and hw:opts.append(lit('7 D') + ' k10f ' + lit(' W') + ' k10w')
    for n in (6, 25):
        if n not in on:continue
        if hg:opts.append(lit('%d D' % n) + ' k10g')
        if (hg or hx) and hf:opts.append(lit('%d D' % n) + ' k10gx ' + lit(' D') + ' k10f')
        if (hg or hx) and at > 1:opts.append(lit('%d D' % n) + ' k10gx ' + lit(' S') + ' s%d' % at)
    if 5 in on and hx and hw:opts.append(lit('5 D') + ' k10x ' + lit(' W') + ' k10w')
    if 26 in on and (hg or hx):opts.append(lit('26 D') + ' k10gx')
    return rules, opts


# ---------------------------------------------------------------- the desk fills each of the model's steps
def _tilde(path):
    from . import home_reach
    return home_reach.tilde(path)


def _folder_of_step(b, made, e):
    """The folder an earlier step of the model's line makes (or looks at): its path, or None."""
    keys = set((made.get(e) or {}).get('keys') or ())
    for source in b.sources:
        if source['key'] not in keys:continue
        a = source.get('arguments') or {}
        if source['operation'] == 'files.mkdir':return Path(a['path']) / a['name']
        if source['operation'] == 'files.list':return Path(a['path'])
    return None


def _made_here(b, folder):
    """Whether a step already in the plan makes this folder."""
    for source in b.sources:
        a = source.get('arguments') or {}
        if source['operation'] == 'files.mkdir' and Path(a.get('path') or '/') / str(a.get('name') or '') == Path(folder):return True
    return False


def _mkdir(b, folder, name, basis, name_origin, why=''):
    where = _tilde(folder)
    return b.add({'key': b.key('k10_folder_' + name), 'title': 'Make the folder %s in %s' % (name, where), 'operation': 'files.mkdir',
                  'tool_key': 'files.folder.new', 'arguments': {'path': str(folder), 'name': name},
                  'origins': {'path': {'kind': 'DEDUCTION', 'proof': 'the folder of your home your words name'}, 'name': name_origin},
                  'basis': basis, 'expected': ('the folder %s in %s%s' % (name, where, why))[:400]})


def _look(b, folder, basis):
    where = _tilde(folder)
    return b.add({'key': b.key('k10_list'), 'title': 'Look at %s' % where, 'operation': 'files.list', 'tool_key': 'files.list',
                  'arguments': {'path': str(folder)}, 'origins': {'path': {'kind': 'DEDUCTION', 'proof': 'a folder of your home your words name'}},
                  'basis': basis, 'expected': 'the files and folders in %s, one level' % where})


def model_step(b, number, things, spans, earlier, made, basis, i):
    """objective_plan.MODEL_TOOLS for 24, 7, 6, 5, 25, 26: every argument filled by the desk from the handles."""
    from .objective_plan import Refusal
    kinds = [t.kind for t in things]
    if number in NAMED_ONLY and number not in set(i.verbs):
        raise Refusal('%s only when your own words ask for it' % {5: 'a rename is planned', 25: 'a copy is planned', 26: 'the bin is used'}[number])
    asked = (number, tuple(t.handle for t in things), tuple(spans), tuple(earlier))
    done = b.__dict__.setdefault('k10_steps', set())
    if asked in done:raise Refusal('it repeats an earlier step')
    done.add(asked)
    if number in (6, 25, 26):      # a file an earlier step of this plan moves or puts in the bin is not planned again
        planned = b.__dict__.setdefault('k10_files', {})
        for t in things[:1]:
            for p in (t.data.get('files') or [t.data.get('path')]):
                if p in planned:raise Refusal('%s is %s by an earlier step already' % (Path(p).name, planned[p]))
    if number == 24:
        if kinds != ['folder']:raise Refusal('a folder is listed one at a time')
        _look(b, Path(things[0].data['path']), basis);return
    if number == 7:
        if kinds == ['group']:
            g = things[0].data;folder = Path(g['folder']);target = folder / g['kind']
            if target.is_dir() or _made_here(b, target):
                _look(b, target, basis);return      # the folder is there already: she looks at it instead of making it
            if target.exists():raise Refusal('%s in %s is a file, not a folder' % (g['kind'], _tilde(folder)))
            _mkdir(b, folder, g['kind'], basis, {'kind': 'DEDUCTION', 'proof': 'the kind of %d file(s) there, by the end of their names' % len(g['files'])})
            return
        if kinds == ['folder'] and len(spans) == 1:
            _, start, end = i.words[int(spans[0][1:]) - 1]
            name = i.objective[start:end].strip()
            if not name or '/' in name:raise Refusal('a folder’s name is one name, with no "/"')
            _mkdir(b, Path(things[0].data['path']), name, basis, {'kind': 'OWNER_WORDS', 'start': start, 'end': end});return
        raise Refusal('a folder is made for a group of files, or in a folder with a name from your words')
    if number in (6, 25):
        if not things or kinds[0] not in ('group', 'file'):raise Refusal('it moves or copies a file or a group of files')
        what = things[0];files = [Path(p) for p in (what.data.get('files') or [what.data['path']])]
        if len(things) == 2:
            if kinds[1] != 'folder':raise Refusal('they go into a folder')
            target = Path(things[1].data['path']);proof = 'the folder of your home your words name'
        elif earlier:
            target = _folder_of_step(b, made, earlier[0])
            if target is None:raise Refusal('step %d makes no folder' % earlier[0])
            proof = 'the folder step %d makes' % earlier[0]
        elif kinds[0] == 'group':
            g = what.data;target = Path(g['folder']) / g['kind'];proof = 'the folder for %s files (their names end %s)' % (g['kind'], ', '.join(g['ends']))
            if not target.is_dir() and not _made_here(b, target):
                if target.exists():raise Refusal('%s in %s is a file, not a folder' % (g['kind'], _tilde(g['folder'])))
                _mkdir(b, Path(g['folder']), g['kind'], basis,
                       {'kind': 'DEDUCTION', 'proof': 'the kind of %d file(s) there, by the end of their names' % len(g['files'])},
                       ' (the desk adds it: the files go into it)')
        else:
            raise Refusal('say which folder it goes into')
        verb, op, key = ('Move', 'files.move', 'files.move') if number == 6 else ('Copy', 'files.copy', 'files.copy')
        for p in files:
            if p.parent == target:raise Refusal('%s is in %s already' % (p.name, _tilde(target)))
        if number == 6:b.k10_files.update({str(p): 'moved' for p in files})
        for p in files:
            b.add({'key': b.key('k10_%s_%s' % (verb.lower(), p.stem)), 'title': '%s %s into %s' % (verb, p.name, _tilde(target)),
                   'operation': op, 'tool_key': key, 'arguments': {'path': str(p), 'to': str(target)},
                   'origins': {'path': {'kind': 'DEDUCTION', 'proof': 'a file at the top of %s, listed now' % _tilde(p.parent)},
                               'to': {'kind': 'DEDUCTION', 'proof': proof}},
                   'basis': basis, 'expected': '%s in %s%s' % (p.name, _tilde(target), '; the original where it was' if number == 25 else '')})
        return
    if number == 5:
        if kinds != ['file'] or len(spans) != 1:raise Refusal('a rename takes one file and its new name from your words')
        _, start, end = i.words[int(spans[0][1:]) - 1]
        name = i.objective[start:end].strip();p = Path(things[0].data['path'])
        b.add({'key': b.key('k10_rename'), 'title': 'Rename %s to %s' % (p.name, name), 'operation': 'files.rename', 'tool_key': 'files.rename',
               'arguments': {'path': str(p), 'name': name}, 'origins': {'path': {'kind': 'DEDUCTION', 'proof': 'the file your words name'},
                                                                     'name': {'kind': 'OWNER_WORDS', 'start': start, 'end': end}},
               'basis': basis, 'expected': 'the same file under its new name'});return
    if number == 26:
        if not things or kinds[0] not in ('group', 'file') or len(things) != 1:raise Refusal('the bin takes a file or a group of files')
        b.k10_files.update({x: 'put in the bin' for x in (things[0].data.get('files') or [things[0].data['path']])})
        for p in [Path(x) for x in (things[0].data.get('files') or [things[0].data['path']])]:
            b.add({'key': b.key('k10_bin_' + p.stem), 'title': 'Put %s in the bin' % p.name, 'operation': 'files.trash', 'tool_key': 'files.trash',
                   'arguments': {'path': str(p)}, 'origins': {'path': {'kind': 'DEDUCTION', 'proof': 'a file at the top of %s, listed now' % _tilde(p.parent)}},
                   'basis': basis, 'expected': '%s in the bin (DELETE), restorable' % p.name})
        return
    raise Refusal('%d is not a Home file tool' % number)


def _join_planner():
    try:
        from . import objective_plan as op
    except Exception:  # noqa: BLE001 - K4 is not in this Graphite
        return False
    op.STEP_TOOLS = tuple(op.STEP_TOOLS) + tuple(n for n in HOME_TOOLS if n not in op.STEP_TOOLS)
    op.SHORT.update(SHORT);op.TAKES.update(TAKES)
    if hasattr(op, 'USES'):op.USES.update({n: () for n in HOME_TOOLS})      # always on the menu: your home is always there (K4b: one menu a desk)
    if hasattr(op, 'OWN_SHAPES'):op.OWN_SHAPES.update(HOME_TOOLS)
    if hasattr(op, 'GRAMMAR_MORE') and grammar_more not in op.GRAMMAR_MORE:op.GRAMMAR_MORE.append(grammar_more)
    if hasattr(op, 'MORE_NAMED') and home_named not in op.MORE_NAMED:op.MORE_NAMED.append(home_named)
    if hasattr(op, 'MORE_VERBS') and home_verbs not in op.MORE_VERBS:op.MORE_VERBS.append(home_verbs)
    op.MODEL_TOOLS.update({n: model_step for n in HOME_TOOLS})
    return True


# ---------------------------------------------------------------- one press for a folder's grants
def _set_digest(shown):
    from . import grants
    return grants.digest({'set': [s['digest'] for s in shown]})


def _pending(step):
    from . import grants
    return step['status'] == 'proposed' or (step['status'] == 'blocked' and str(step.get('reason', '')).startswith(grants.NEEDS))


def set_request(kernel, value, nxt, principal):
    """The grants one press would give for the step that waits for a grant and the other steps waiting in its folder, when
    they need several operations: [describe(...) for each], or None."""
    from . import grants
    first = grants.step_request(kernel, value, nxt)
    if first is None or 'folder' not in first:return None
    ops = [first['operation']]
    for step in value['steps']:
        if step is nxt or step['key'] == nxt['key'] or not _pending(step) or not grants._grantable(step):continue
        args = grants._resolved(value, step)
        if args is None or grants._never(kernel, step['operation'], args):continue
        req = grants.step_request(kernel, value, step, args)
        if req is None or req.get('folder') != first['folder'] or req['operation'] in ops:continue
        ops.append(req['operation'])
        if len(ops) >= SET_MOST:break
    if len(ops) < 2:return None
    items = [{'operation': o, 'folder': first['folder'], 'scope': 'assignment', 'assignment': value['id']} for o in ops]
    try:return items, [grants.describe(kernel, item, principal) for item in items]
    except (ValueError, KeyError):
        return None


def one_press(kernel, value, nxt, principal):
    """assignments.GRANT_ACTION, widened: the one press for a step that needs your grant; when the steps waiting in its folder
    need several operations, "Grant these for this assignment", each grant in its own words."""
    single = _BEFORE(kernel, value, nxt, principal) if _BEFORE is not None else None
    if single is None:return None
    got = set_request(kernel, value, nxt, principal)
    if got is None:return single
    items, shown = got
    from . import grants
    # each grant is its operation on its target in one scope; the scope, the same for all of them, is said once (the band)
    return {'words': SET_PRESS, 'operation': 'grant.give.set', 'yours': True,
            'grant_words': '; '.join('%s %s' % (s['doing'], s['target']['words']) for s in shown),
            'grant_scope': grants.scope_words(shown[0]['scope']), 'grant_count': len(shown), 'grants_words': [s['words'] for s in shown],
            'arguments': {'grants': items, 'expected_digest': _set_digest(shown), 'step': nxt['key']},
            'then': {'operation': 'assignment.step', 'arguments': {'id': value['id'], 'until': 'end'}}}


def give_set(kernel, args, principal):
    """grant.give.set: your press: each grant as shown, as its own record (per operation, target and scope)."""
    import hashlib
    import uuid
    from . import activity, grants
    grants._owner_only(principal)
    items = args['grants']
    if not 2 <= len(items) <= SET_MOST:raise ValueError('GRANT_SET: two to %d grants in one press' % SET_MOST)
    shown = [grants.describe(kernel, dict(item), principal) for item in items]
    if len({grants.canonical(s['target']) for s in shown}) != 1 or len({grants.canonical(s['scope']) for s in shown}) != 1:
        raise ValueError('GRANT_SET: one press gives grants on one target, in one scope')
    if len({s['operation'] for s in shown}) != len(shown):raise ValueError('GRANT_SET: each operation once')
    if args['expected_digest'] != _set_digest(shown):
        raise ValueError('GRANT_CHANGED: these are not the words you were shown; read the grants again')
    given = grants.now_ms();values = []
    source = 'your press: %s' % SET_PRESS
    with grants._writing(kernel) as db:
        for s in shown:
            ident = uuid.uuid4().hex
            value = {'schema': grants.SCHEMA, 'id': ident, 'owner': principal.identity, 'operation': s['operation'], 'doing': s['doing'],
                     'operations': s['operations'], 'target': s['target'], 'scope': s['scope'], 'words': s['words'], 'shown': s['digest'],
                     'given': given, 'given_by': principal.identity, 'source': source, 'ended': None}
            raw = grants.canonical(value)
            db.execute('INSERT INTO kas_grants VALUES(?,?,?,?,?,?)', (ident, principal.identity, given, None, raw, hashlib.sha256(raw.encode()).hexdigest()))
            values.append(value)
        activity.append(db, activity.make_event(principal.identity, 'grant.give.set', 'GIVEN'))
    said = ['You gave %d grants in one press: %s.' % (len(shown), '; '.join(s['words'] for s in shown))]
    scope = shown[0]['scope']
    if args.get('step') and scope['kind'] == 'assignment':
        said.extend(grants._authorise_named(kernel, scope['assignment'], args['step'], principal))
    else:
        said.extend(grants._sweep(kernel, principal, scope.get('assignment')))
    return {'schema': grants.SCHEMA, 'grants': [grants._view(v) for v in values], 'said': said}


GRANT_ITEM = {'type': 'object', 'properties': {'operation': {'type': 'string', 'minLength': 1, 'maxLength': 120},
                                               'folder': {'type': 'string', 'maxLength': 1000},
                                               'object': {'type': 'string', 'minLength': 1, 'maxLength': 200},
                                               'scope': {'type': 'string', 'enum': ['assignment', 'until', 'always']},
                                               'assignment': {'type': 'string', 'minLength': 32, 'maxLength': 32},
                                               'until': {'type': 'integer', 'minimum': 0, 'maximum': 1 << 50}},
              'required': ['operation', 'scope'], 'additionalProperties': False}
FIELDS = {'grant.give.set': ({'grants': {'type': 'array', 'items': GRANT_ITEM, 'minItems': 2, 'maxItems': SET_MOST},
                              'expected_digest': {'type': 'string', 'minLength': 64, 'maxLength': 64},
                              'step': {'type': 'string', 'minLength': 1, 'maxLength': 32}}, ['grants', 'expected_digest'])}
SCOPES = {'grant.give.set': 'approve'}


def dispatch(kernel, op, args, principal):
    if op == 'grant.give.set':return give_set(kernel, args, principal)
    raise ValueError('Unknown grant set operation')


_BEFORE = None


def _join_grants():
    global _BEFORE
    try:
        from . import assignments, grants  # noqa: F401 - grants installs K3's press first
    except Exception:  # noqa: BLE001 - K3 is not in this Graphite
        return False
    if assignments.GRANT_ACTION is not one_press:
        _BEFORE = assignments.GRANT_ACTION
        assignments.GRANT_ACTION = one_press
    return True


JOINED = (_join_registry(), _join_planner(), _join_grants())
