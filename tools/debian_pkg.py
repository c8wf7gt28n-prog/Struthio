"""1.1 PK1: the small, dependency-free pieces behind tools/build_deb.sh, build_repo.sh and build_kit.sh.

  python3 tools/debian_pkg.py version                      # the Debian version, from workbench/version.py
  python3 tools/debian_pkg.py stage PACKAGE STAGE          # fill one binary package's staging folder
  python3 tools/debian_pkg.py index FOLDER [--label TEXT]  # Packages, Packages.xz and Release of a folder repository
  python3 tools/debian_pkg.py pack REPO KIT                # the kit: ZIPs (and pieces) each under 15,000,000 bytes
  python3 tools/debian_pkg.py join KIT                     # what JOIN.sh does, for tests and for a host with python3

Only the standard library is used, so the same file runs on the build host, inside a Debian chroot and on the owner's
computer. Nothing here touches the network or a home folder.
"""
from __future__ import annotations

import ast
import email.utils
import gzip
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEBIAN = ROOT / 'debian'
LIMIT = 15_000_000          # the kit's hard rule: every file the owner receives is smaller than this
PIECE = 14_000_000          # a larger file is cut into pieces of this size (each then fits a ZIP under LIMIT)
ZIP_FILL = 14_500_000       # small files are grouped into ZIPs up to about this many bytes
PROGRAM = 'usr/lib/graphite'
# Payload files that another binary package installs into the same program folder (dpkg cares only about which
# package owns which file). The manifest still lists them; workbench.release_integrity reads PACKAGE_PARTS.json and
# treats a part whose package is not installed as "not installed", never as damage.
# 1.1 R1: the packages are kas-* (never a bare "kas": Debian 13 has an unrelated package of that name); the graphite*
# names are transitional packages (TRANSITIONAL) and the old commands symlinks (OLD_COMMANDS), one release each.
MAIN = 'kas-computer'
PACKAGES = ('kas-computer', 'kas-llama-runtime', 'kas-session', 'kas-desktop')
TRANSITIONAL = {'graphite': 'kas-computer', 'graphite-llama-runtime': 'kas-llama-runtime', 'graphite-session': 'kas-session',
                'graphite-desktop': 'kas-desktop'}
COMMANDS = {'kas-computer': ('kas-computer', 'kas-doctor'), 'kas-session': ('kas-session', 'kas-startx', 'kas-do')}
OLD_COMMANDS = {'graphite': 'kas-computer', 'graphite-doctor': 'kas-doctor', 'graphite-session': 'kas-session',
                'graphite-startx': 'kas-startx', 'graphite-do': 'kas-do'}
PARTS = {'kas-llama-runtime': ('runtimes/llama.cpp/b12359/llama-b12359-bin-ubuntu-x64.tar.gz',
                                    'runtimes/llama.cpp/b12359/llama-b12359-bin-ubuntu-vulkan-x64.tar.gz')}
PARTS_FILE = 'PACKAGE_PARTS.json'


# ---------------------------------------------------------------- version
def upstream_version(root=ROOT):
    """VERSION from workbench/version.py, read without importing it."""
    tree = ast.parse((Path(root) / 'workbench/version.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'VERSION' for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('workbench/version.py states no VERSION')


def debian_version(version):
    """'1.0' -> '1.0'; '1.1-pre1', '1.1pre1' or '1.1~pre1' -> '1.1~pre1' (a preview sorts before the release)."""
    text = str(version).strip()
    text = re.sub(r'[-_.~ ]?(pre|rc|alpha|beta|a|b)(\d*)$', lambda m: '~' + m.group(1) + m.group(2), text)
    if not re.fullmatch(r'[0-9][A-Za-z0-9.+~]*', text):
        raise ValueError('Not usable as a Debian version: %r' % version)
    return text


# ---------------------------------------------------------------- control
def parse_control(text):
    """Stanzas of a Debian control file as ordered dicts; continuation lines are kept with their newline."""
    stanzas, current, key = [], {}, None
    for line in text.splitlines():
        if line.startswith('#'):
            continue
        if not line.strip():
            if current: stanzas.append(current)
            current, key = {}, None; continue
        if line[0] in ' \t' and key:
            current[key] += '\n' + line; continue
        key, _, value = line.partition(':')
        key = key.strip(); current[key] = value.strip()
    if current: stanzas.append(current)
    return stanzas


def binary_stanza(package, control_text=None):
    stanzas = parse_control(control_text if control_text is not None else (DEBIAN / 'control').read_text(encoding='utf-8'))
    for stanza in stanzas[1:]:
        if stanza.get('Package') == package:
            return stanzas[0], stanza
    raise KeyError('debian/control has no binary package ' + package)


def relation(value):
    """A folded relation field on one line, as dpkg wants it in a binary package."""
    return ', '.join(part.strip() for part in value.replace('\n', ' ').split(',') if part.strip())


def binary_control(package, version, installed_kb, control_text=None):
    source, stanza = binary_stanza(package, control_text)
    out = [('Package', package), ('Source', source['Source']), ('Version', version),
           ('Architecture', stanza['Architecture']), ('Maintainer', source['Maintainer']),
           ('Installed-Size', str(int(installed_kb))), ('Section', stanza.get('Section', source.get('Section', 'misc'))),
           ('Priority', source.get('Priority', 'optional'))]
    for field in ('Depends', 'Recommends', 'Suggests', 'Provides', 'Conflicts', 'Breaks', 'Replaces'):
        if field in stanza:
            out.append((field, relation(stanza[field]).replace('@VERSION@', version)))
    out.append(('Description', stanza['Description']))
    return ''.join('%s: %s\n' % pair for pair in out)


# ---------------------------------------------------------------- payload and staging
def payload(root=ROOT):
    """The shipped files exactly as MANIFEST.json lists them, plus MANIFEST.json itself."""
    record = json.loads((Path(root) / 'MANIFEST.json').read_text(encoding='utf-8'))
    return sorted(record['files']) + ['MANIFEST.json']


def split_payload(names):
    """{package: [payload names]} for the program folder; every name goes to exactly one package."""
    owned = {name: package for package, files in PARTS.items() for name in files}
    out = {MAIN: []}
    for package in PARTS: out[package] = []
    for name in names:
        out[owned.get(name, MAIN)].append(name)
    return out


def _copy(src, dst, mode):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst); os.chmod(dst, mode)


def _changelog(version, package):
    text = ('kas-computer (%s) trixie; urgency=medium\n\n  * Kas %s (%s), built by tools/build_deb.sh.\n\n'
            ' -- Kas packaging <packaging@kas-computer.invalid>  %s\n') % (
        version, version, package, email.utils.formatdate(int(os.environ.get('SOURCE_DATE_EPOCH', time.time())), usegmt=False))
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=9, mtime=0, filename='') as stream:
        stream.write(text.encode())
    return buffer.getvalue()


def stage(package, folder, root=ROOT, version=None):
    """Fill FOLDER with one binary package's tree and DEBIAN/ (control, maintainer scripts). Returns the file count."""
    root, folder = Path(root), Path(folder)
    version = version or debian_version(upstream_version(root))
    if folder.exists(): shutil.rmtree(folder)
    (folder / 'DEBIAN').mkdir(parents=True)
    parts = split_payload(payload(root))
    count = 0
    def program_file(name):
        mode = 0o755 if name.endswith('.sh') or name == 'arc1' else 0o644
        _copy(root / name, folder / PROGRAM / name, mode)
    if package in parts:
        for name in parts[package]:
            program_file(name); count += 1
    def commands(names):
        for name in names:
            _copy(root / 'debian/bin' / name, folder / 'usr/bin' / name, 0o755)
        for old, new in OLD_COMMANDS.items():      # 1.1 R1: the old name, one release, a symlink that says the new one
            if new in names:os.symlink(new, folder / 'usr/bin' / old)
    if package == MAIN:
        (folder / PROGRAM / PARTS_FILE).write_text(json.dumps(
            {'schema': 'graphite.package-parts/1', 'version': version,
             'parts': {p: list(files) for p, files in PARTS.items()},
             'meaning': 'Files of the program folder that another package installs. A part whose files are all '
                        'absent is not installed; a part with some files absent is damaged.'}, indent=1) + '\n')
        commands(COMMANDS[MAIN])
        _copy(root / 'debian/graphite.desktop', folder / 'usr/share/applications/graphite.desktop', 0o644)
        _copy(root / 'branding/graphite/graphite_icon_256.png', folder / 'usr/share/icons/hicolor/256x256/apps/graphite.png', 0o644)
        for script in ('postinst', 'prerm'):
            _copy(root / ('debian/graphite.' + script), folder / 'DEBIAN' / script, 0o755)
        count += 5
    elif package == 'kas-session':
        commands(COMMANDS['kas-session'])      # 1.1 W1: kas-do (graphite-do)
        _copy(root / 'debian/graphite-xsession.desktop', folder / 'usr/share/xsessions/graphite.desktop', 0o644)
        count += 3
    elif package == 'kas-desktop':
        _copy(root / 'debian/50-graphite.conf', folder / 'usr/share/lightdm/lightdm.conf.d/50-graphite.conf', 0o644)
        count += 1
    elif package in TRANSITIONAL:
        pass      # 1.1 R1: a transitional package holds its copyright and changelog only
    elif package not in parts:
        raise KeyError(package)
    doc = folder / 'usr/share/doc' / package
    _copy(root / 'debian/copyright', doc / 'copyright', 0o644)
    (doc / 'changelog.gz').write_bytes(_changelog(version, package)); os.chmod(doc / 'changelog.gz', 0o644)
    for path in [folder, *folder.rglob('*')]:
        if path.is_dir(): os.chmod(path, 0o755)
    size = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file() and 'DEBIAN' not in p.relative_to(folder).parts)
    (folder / 'DEBIAN/control').write_text(binary_control(package, version, (size + 1023) // 1024 + 4,
                                                          (root / 'debian/control').read_text(encoding='utf-8')))
    return count


# ---------------------------------------------------------------- reading a .deb without dpkg
def deb_control(path):
    """The control file of a .deb (an ar archive holding control.tar.{gz,xz,zst}) as text."""
    with open(path, 'rb') as stream:
        if stream.read(8) != b'!<arch>\n': raise ValueError('Not a Debian package: %s' % path)
        while True:
            header = stream.read(60)
            if len(header) < 60: break
            name, size = header[:16].decode().strip().rstrip('/'), int(header[48:58])
            data = stream.read(size)
            if size % 2: stream.read(1)
            if name.startswith('control.tar'):
                if name.endswith('.zst'):
                    return subprocess.run(['dpkg-deb', '-f', str(path)], check=True, capture_output=True, text=True).stdout
                with tarfile.open(fileobj=io.BytesIO(data)) as tar:
                    for member in tar.getmembers():
                        if member.name.lstrip('./') == 'control':
                            return tar.extractfile(member).read().decode('utf-8')
    raise ValueError('No control file in %s' % path)


def digest(path, kind):
    value = hashlib.new(kind)
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): value.update(block)
    return value.hexdigest()


def index(folder, label='Graphite kit', date=None):
    """A flat apt repository in FOLDER: Packages, Packages.xz and Release (MD5Sum, SHA256), as apt 3.0 reads it with
    'deb [trusted=yes] file:FOLDER ./' or, when signed, with Signed-By. Returns the number of packages."""
    folder = Path(folder); stanzas = []
    for deb in sorted(folder.rglob('*.deb')):
        control = deb_control(deb).strip('\n')
        rel = deb.relative_to(folder).as_posix()
        stanzas.append(control + '\nFilename: ./%s\nSize: %d\nMD5sum: %s\nSHA256: %s\n' % (
            rel, deb.stat().st_size, digest(deb, 'md5'), digest(deb, 'sha256')))
    text = '\n'.join(stanzas).encode('utf-8')
    (folder / 'Packages').write_bytes(text)
    (folder / 'Packages.xz').write_bytes(lzma.compress(text, preset=6))
    arches = sorted({re.search(r'^Architecture: (\S+)', s, re.M).group(1) for s in stanzas} | {'amd64'})
    stamp = date or email.utils.formatdate(int(os.environ.get('SOURCE_DATE_EPOCH', time.time())), usegmt=True)
    lines = ['Origin: Graphite', 'Label: ' + label, 'Suite: graphite', 'Codename: graphite', 'Date: ' + stamp,
             'Architectures: ' + ' '.join(a for a in arches if a != 'all'), 'Components: ',
             'Description: Kas and the Debian 13 packages it needs, as a folder repository']
    for field, kind in (('MD5Sum', 'md5'), ('SHA256', 'sha256')):
        lines.append(field + ':')
        for name in ('Packages', 'Packages.xz'):
            lines.append(' %s %d %s' % (digest(folder / name, kind), (folder / name).stat().st_size, name))
    (folder / 'Release').write_text('\n'.join(lines) + '\n')
    return len(stanzas)


# ---------------------------------------------------------------- the kit
def pack(repo, kit, limit=LIMIT, piece=PIECE, fill=ZIP_FILL):
    """Pack every file of REPO into ZIPs in KIT, each smaller than LIMIT bytes. A file too large for one ZIP is cut
    into pieces (NAME.001, ...), each piece in its own ZIP; PIECES.sha256 lists every piece and the whole file,
    SHA256SUMS every file of the repository. Returns a summary."""
    repo, kit = Path(repo), Path(kit)
    if not (piece < limit - 4096 and fill < limit - 65536): raise ValueError('piece and fill must leave room for ZIP headers')
    kit.mkdir(parents=True, exist_ok=True)
    for old in [*kit.glob('KAS_*.zip'), *kit.glob('GRAPHITE_*.zip')]: old.unlink()
    files = sorted(p for p in repo.rglob('*') if p.is_file())
    sums, pieces, groups, small, size = [], [], [], [], 0
    for path in files:
        rel = path.relative_to(repo).as_posix(); n = path.stat().st_size
        sums.append('%s  %s' % (digest(path, 'sha256'), rel))
        if n > fill:
            with open(path, 'rb') as stream:
                index_no = 0
                while True:
                    block = stream.read(piece)
                    if not block: break
                    index_no += 1
                    name = '%s.%03d' % (rel, index_no)
                    pieces.append((hashlib.sha256(block).hexdigest(), name, rel))
                    groups.append([(name, block)])
            continue
        if small and size + n > fill:
            groups.append(small); small, size = [], 0
        small.append((rel, path)); size += n
    if small: groups.append(small)
    made = []
    for number, group in enumerate(groups, 1):
        target = kit / ('KAS_%03d.zip' % number)      # 1.1 R1: the kit's ZIPs say Kas
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_STORED) as archive:
            for name, item in group:
                info = zipfile.ZipInfo('repo/' + name, date_time=(2026, 1, 1, 0, 0, 0)); info.external_attr = 0o644 << 16
                archive.writestr(info, item if isinstance(item, bytes) else Path(item).read_bytes())
        if target.stat().st_size >= limit: raise RuntimeError('%s is %d bytes' % (target.name, target.stat().st_size))
        made.append(target.name)
    (kit / 'SHA256SUMS').write_text('\n'.join(sums) + '\n')
    whole = {rel: s.split()[0] for s in sums for rel in [s.split('  ', 1)[1]]}
    lines = ['%s  %s' % (h, name) for h, name, _ in pieces]
    lines += ['%s  %s  WHOLE' % (whole[rel], rel) for rel in sorted({r for _, _, r in pieces})]
    (kit / 'PIECES.sha256').write_text('\n'.join(lines) + ('\n' if lines else ''))
    biggest = max((kit / m).stat().st_size for m in made) if made else 0
    return {'zips': len(made), 'pieces': len(pieces), 'files': len(files), 'largest_zip': biggest,
            'bytes': sum((kit / m).stat().st_size for m in made)}


def join(kit, out=None):
    """Unpack the ZIPs of KIT into KIT/repo, check every piece, join them, check every file. Returns problems."""
    kit = Path(kit); out = Path(out) if out else kit
    problems = []
    for archive in sorted(kit.glob('KAS_*.zip')):
        with zipfile.ZipFile(archive) as z: z.extractall(out)
    repo = out / 'repo'
    whole = {}
    for line in (kit / 'PIECES.sha256').read_text().splitlines():
        parts = line.split('  ')
        if len(parts) == 3: whole[parts[1]] = parts[0]; continue
        if digest(repo / parts[1], 'sha256') != parts[0]: problems.append('piece changed: ' + parts[1])
    for rel, expected in whole.items():
        chunks = sorted((repo / rel).parent.glob(Path(rel).name + '.[0-9][0-9][0-9]'), key=lambda p: p.name)
        with open(repo / rel, 'wb') as target:
            for chunk in chunks: target.write(chunk.read_bytes())
        if digest(repo / rel, 'sha256') != expected: problems.append('joined file changed: ' + rel); continue
        for chunk in chunks: chunk.unlink()
    for line in (kit / 'SHA256SUMS').read_text().splitlines():
        expected, rel = line.split('  ', 1)
        if not (repo / rel).is_file(): problems.append('missing: ' + rel)
        elif digest(repo / rel, 'sha256') != expected: problems.append('changed: ' + rel)
    return problems


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv: print(__doc__); return 2
    command = argv.pop(0)
    if command == 'version': print(debian_version(upstream_version())); return 0
    if command == 'stage': print(stage(argv[0], argv[1])); return 0
    if command == 'index':
        label = argv[argv.index('--label') + 1] if '--label' in argv else 'Graphite kit'
        print(index(argv[0], label)); return 0
    if command == 'pack': print(json.dumps(pack(argv[0], argv[1]))); return 0
    if command == 'join':
        problems = join(argv[0]); print('\n'.join(problems) or 'ALL FILES CHECKED'); return 1 if problems else 0
    print(__doc__); return 2


if __name__ == '__main__':
    sys.exit(main())
