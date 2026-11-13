"""Build a Graphite release from the current program tree.

    python3 tools/package_graphite.py OUT_FOLDER          rebuild, update the manifest, and write the full archive
    python3 tools/package_graphite.py --manifest-only     rebuild the seed and update MANIFEST.json
    python3 tools/package_graphite.py --dry-run           report what would change without writing files
    python3 tools/package_graphite.py --rebuild-seed      rebuild project/stacy_seed/current

Use tools/package_release_parts.py to split the archive into delivery volumes.
INSTALL_LS.py verifies the parts and restores the package.

Seed assembly stages only SEED_INPUTS. Absent notes can be recovered from the
verified catalog when their bytes match the previous seed manifest. Release
packaging keeps the installer identity fields in MANIFEST.json.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from workbench.version import SHORT
RELEASE = SHORT
ARCHIVE = 'Graphite_' + RELEASE + '_full.zip'
# Never shipped: private state, environments and caches.
EXCLUDED_PARTS = ('.ledger', '.venv', '__pycache__', '.pytest_cache', '.git')
# Ship the approved UI evidence and cited model-trial records. Other local
# captures under build/ stay outside the release.
BUILD_SHIPPED = ('build/graphite01_ui/', 'build/graphite_desk/', 'build/agent01_ui/model_trial/', 'build/agent02_ui/model_trial/')
# Fields of earlier checkpoints' manifests that no reader uses any more (the release check reads graphite_release).
RETIRED_FIELDS = ('hatch_checkpoint', 'integrated_pass', 'delivery_stage')
NOTE = ('Graphite 0.4.6: the pointer is the green of the desk and what it is over answers in green; live marks, wires and readings glow (not on the Clean desk). Before it, 0.4.5: the mouse path (a click opens a tile, ‹ Field comes back, every shown key can be clicked, Approve is a button) and the first change Stacy makes on approval (set B3 to 300). Before it, 0.4.4: a pass for reading and for finding the keys (? shows every key; the doubt, the desk check and the brief open on a page over the work). Before it, 0.4.3: a what-if is followed along the wires and marked on the Field, the doubt catches more (a subtotal counted twice, a prefix slip), B writes the desk up as a page, and the owner keeps staC lines under their own words. Before it, 0.4.2: Stacy doubts a result (X) and offers the step that removes the doubt. staC reads the desk itself, `this` is the selected sheet, T traces a thing to its source and Stacy '
        'answers "what if" exactly. The desk does. In the Field, D offers the steps the records have for a sheet (reads run, changes '
        'ask once), C checks the desk, and one go settles what needs no decision of the owner’s. Stacy is the '
        'assistant’s face and answers in staC; P shows every program as a shelf. Free software under the GNU GPL '
        'version 2 only (COPYING, RIGHTS.md). It keeps the Field, After Midnight’s desk art, '
        'the offline Debian setup, model-free workshop and staC source-bound workflow. '
        'Read docs/THINKPAD_FIRST_INSTALL.md.')



def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): digest.update(block)
    return digest.hexdigest()


def verified_catalog(current):
    """The existing seed's manifest and catalog records, refused unless they are the seed as it was built.

    A carried note's only working copy is its text in this catalog, so the catalog must still hash to the manifest's record
    of it and the manifest's inputs must still give its seed identity. The input set may differ from SEED_INPUTS (a rebuild
    is how a changed input list takes effect), so this is not seed_status, which also requires the current input set."""
    from workbench import stacy_foundation as foundation
    current = Path(current)
    try:
        old = json.loads((current / 'manifest.json').read_text(encoding='utf-8'))
        files, inputs = old['files'], old['inputs']
        if set(files) != {'catalog.json', 'index.sqlite'}: raise ValueError('its manifest is not a seed manifest')
        if old.get('seed_id') != foundation.sha(foundation.canonical(inputs)):
            raise ValueError('its manifest inputs differ from its seed identity')
        for name, expected in files.items():
            if sha(current / name) != expected: raise ValueError(name + ' differs from the hash its manifest records')
        records = json.loads((current / 'catalog.json').read_text(encoding='utf-8'))['records']
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError('The existing seed is damaged, so its carried notes cannot be recovered (%s); restore '
                         'project/stacy_seed/current from the release or git first' % exc) from None
    return old, {r['id']: r for r in records}


def rebuild(root=ROOT):
    """Rebuild the seed at root/project/stacy_seed/current from SEED_INPUTS (carried notes from the verified catalog).

    A carried note is written only when its catalog text has exactly the bytes the old manifest recorded for it."""
    root = Path(root)
    from workbench import stacy_foundation as foundation
    current = root / 'project/stacy_seed/current'
    old, carried = verified_catalog(current)
    with tempfile.TemporaryDirectory(prefix='graphite-seed-') as temporary:
        assembly = Path(temporary) / 'program'
        for name in foundation.SEED_INPUTS:
            path = assembly / name
            path.parent.mkdir(parents=True, exist_ok=True)
            original = root / name
            if original.exists() or original.is_symlink():
                shutil.copyfile(foundation.project_file(root, name, program_file=False), path)
                continue
            row = carried.get('document:' + name)
            if not foundation.carried(name) or row is None: raise ValueError('Required source unavailable: ' + name)
            raw = row['text'].encode('utf-8')
            if foundation.sha(raw) != old['inputs'].get(name):
                raise ValueError('Carried note differs from its original bytes: ' + name)
            path.write_bytes(raw)
        result = foundation.build_seed(assembly)
        if result['state'] != 'VERIFIED_SOURCE_BINDINGS': raise ValueError('Seed build did not verify: ' + json.dumps(result)[:400])
        for name in ('manifest.json', 'catalog.json', 'index.sqlite'):
            shutil.copyfile(assembly / 'project/stacy_seed/current' / name, current / name)
    return foundation.seed_status(root)


def payload_paths(root=ROOT):
    root = Path(root)
    rows = []
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path == root / 'MANIFEST.json' or path.suffix == '.pyc': continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts): continue
        name = relative.as_posix()
        if path.name.endswith('.partial'): continue
        if name.startswith('build/') and not name.startswith(BUILD_SHIPPED): continue
        rows.append(path)
    return rows


def manifest_for(root=ROOT, paths=None):
    """MANIFEST.json as packaging writes it: the current identity fields, this release's names and every payload file."""
    from workbench.version import VERSION
    root = Path(root)
    value = json.loads((root / 'MANIFEST.json').read_text())
    for field in RETIRED_FIELDS: value.pop(field, None)
    value.update(graphite_release=RELEASE, version=VERSION, note=NOTE,
                 files={p.relative_to(root).as_posix(): dict(bytes=p.stat().st_size, sha256=sha(p))
                        for p in (paths if paths is not None else payload_paths(root))})
    return value


def write_manifest(root=ROOT):
    root = Path(root)
    value = manifest_for(root)
    staging = root / 'MANIFEST.json.partial'
    staging.write_text(json.dumps(value, indent=2) + '\n'); os.replace(staging, root / 'MANIFEST.json')
    return value


def dry_run(root=ROOT):
    """What packaging would do, writing nothing."""
    from workbench import stacy_foundation as foundation
    root = Path(root)
    paths = payload_paths(root)
    old = json.loads((root / 'MANIFEST.json').read_text()).get('files', {})
    new = manifest_for(root, paths)['files']
    seed = foundation.seed_status(root)
    return dict(state='DRY_RUN_NOTHING_WRITTEN', release=RELEASE, archive=ARCHIVE, files=len(paths) + 1,
                bytes=sum(row['bytes'] for row in new.values()),
                manifest_changes=dict(added=sorted(set(new) - set(old)), removed=sorted(set(old) - set(new)),
                                      changed=sorted(n for n in set(new) & set(old) if new[n] != old[n])),
                seed=dict(state=seed['state'], changed_sources=seed.get('changed_sources', []),
                          missing_sources=seed.get('missing_sources', []),
                          note='packaging rebuilds the seed first' if seed['state'] != 'VERIFIED_SOURCE_BINDINGS' else 'current'),
                excluded=dict(parts=list(EXCLUDED_PARTS), build_shipped=list(BUILD_SHIPPED)))


def package(folder, root=ROOT):
    root = Path(root)
    source = rebuild(root)
    if source['state'] != 'VERIFIED_SOURCE_BINDINGS': raise ValueError('Source bindings failed verification')
    write_manifest(root)
    paths = payload_paths(root) + [root / 'MANIFEST.json']
    destination = Path(folder) / ARCHIVE; destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(destination.name + '.partial')
    try:
        with ZipFile(staging, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
            for path in paths: archive.write(path, path.relative_to(root))
        with ZipFile(staging) as archive:
            if archive.testzip() is not None: raise ValueError('Incomplete Graphite archive')
        os.replace(staging, destination)
    finally:
        staging.unlink(missing_ok=True)
    return dict(release=RELEASE, archive=str(destination), bytes=destination.stat().st_size, sha256=sha(destination),
                seed=source['state'], files=len(paths))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('folder', nargs='?', type=Path, help='where ' + ARCHIVE + ' is written')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true'); mode.add_argument('--manifest-only', action='store_true')
    mode.add_argument('--rebuild-seed', action='store_true')
    args = parser.parse_args(argv)
    if args.dry_run: result = dry_run()
    elif args.rebuild_seed: result = rebuild()
    elif args.manifest_only:
        seed = rebuild()
        if seed['state'] != 'VERIFIED_SOURCE_BINDINGS': raise SystemExit('Source bindings failed verification')
        value = write_manifest(); result = dict(release=RELEASE, seed=seed['state'], manifest_files=len(value['files']))
    elif args.folder: result = package(args.folder)
    else: parser.error('Name an output folder, or pass --dry-run, --manifest-only or --rebuild-seed')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__': raise SystemExit(main())
