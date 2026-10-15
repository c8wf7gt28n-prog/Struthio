#!/usr/bin/env python3
"""Check the distributable source tree, originals and generated ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile


ROOT = Path(__file__).resolve().parent.parent


def eligible_files():
    return sorted(path for path in ROOT.rglob('*') if path.is_file()
                  and not any(part in {'build', '__pycache__', '.git'}
                              for part in path.relative_to(ROOT).parts)
                  and path.suffix != '.pyc')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-manifest', action='store_true',
                        help='Regenerate SHA256SUMS after intentional source/report changes.')
    parser.add_argument('--zip', type=Path, help='Also verify an existing ZIP byte-for-byte.')
    parser.add_argument('--create-zip', type=Path, help='Create and verify a source ZIP.')
    args = parser.parse_args()
    if args.zip and args.create_zip:
        parser.error('Choose --zip or --create-zip.')
    manifest = ROOT / 'SHA256SUMS'
    files = [path for path in eligible_files() if path != manifest]
    if args.write_manifest:
        manifest.write_text(''.join(f'{digest(path)}  {path.relative_to(ROOT).as_posix()}\n'
                                    for path in files))
    expected = {}
    for line in manifest.read_text().splitlines():
        sha, name = line.split('  ', 1)
        if name in expected:
            raise ValueError(f'Duplicate manifest entry: {name}')
        expected[name] = sha
    actual = {path.relative_to(ROOT).as_posix(): digest(path) for path in files}
    if expected != actual:
        missing = sorted(set(expected) - set(actual))
        added = sorted(set(actual) - set(expected))
        changed = sorted(name for name in set(expected) & set(actual)
                         if expected[name] != actual[name])
        raise ValueError(f'Manifest mismatch: missing={missing}, added={added}, changed={changed}')
    originals = json.loads((ROOT / 'reference/originals_manifest.json').read_text())
    for record in originals['originals']:
        path = ROOT / record['package_path']
        if path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
            raise ValueError(f'Original attachment changed: {path.name}')
    for path in files:
        if path.suffix == '.json':
            json.loads(path.read_text())
    required = ['README_FIRST.md', 'CLAUDE.md', 'CLAUDE_START_PROMPT.txt',
                'ARC1_Compact_Claude_Handoff_R05.docx', 'ARC1_Compact_Claude_Handoff_R05.md',
                'verification/last_run/summary.json', 'integration/demo_report.json']
    for name in required:
        if name not in actual:
            raise ValueError(f'Missing required artifact: {name}')
    summary = json.loads((ROOT / 'verification/last_run/summary.json').read_text())
    # Require a full successful host+HDL run in a release, never a skip-only run.
    if (summary.get('status') != 'PASS_HOST_AND_RTL_SIMULATION'
            or summary.get('all_required_steps_completed') is not True
            or summary.get('partial_run') is not False
            or summary.get('hdl_status') != 'PASS_RTL_SIMULATION_ONLY'
            or summary.get('sources_unchanged_during_run') is not True):
        raise ValueError('Final verification summary must record a complete successful host+RTL run.')
    if not summary.get('steps') or any(step.get('status') != 'PASS' for step in summary['steps']):
        raise ValueError('Final verification summary contains missing or unsuccessful steps.')
    source_manifest = ROOT / summary['source_manifest']
    if digest(source_manifest) != summary['source_manifest_sha256']:
        raise ValueError('Verification source-manifest hash differs from its run record.')
    bindings = json.loads(source_manifest.read_text())['files']
    for name, record in bindings.items():
        path = ROOT / name
        if digest(path) != record['sha256'] or path.stat().st_size != record['bytes']:
            raise ValueError(f'Verified source/input changed after final run: {name}')
    for step in summary['steps']:
        if digest(ROOT / step['log']) != step['log_sha256']:
            raise ValueError(f'Verification log changed: {step["name"]}')
        detail = step.get('details') or {}
        if 'report_sha256' in detail and digest(ROOT / detail['report']) != detail['report_sha256']:
            raise ValueError(f'Verification report changed: {step["name"]}')
    compute = json.loads((ROOT / 'compute/verification_results.json').read_text())
    if compute['status'] != 'PASS_HOST_AND_RTL_SIMULATION' or compute['rtl_oracle_cases'] != 1165:
        raise ValueError('Full compute host+RTL verification is required for this release.')
    with zipfile.ZipFile(ROOT / 'ARC1_Compact_Claude_Handoff_R05.docx') as word:
        if word.testzip() is not None or 'word/document.xml' not in word.namelist():
            raise ValueError('Invalid Word document archive.')
        if not any(name.startswith('word/media/') for name in word.namelist()):
            raise ValueError('Word handoff is missing its architecture image.')
    zip_path = args.create_zip or args.zip
    if args.create_zip:
        if ROOT == zip_path.resolve() or ROOT in zip_path.resolve().parents:
            raise ValueError('Place the ZIP outside the source tree.')
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in eligible_files():
                archive.write(path, f'{ROOT.name}/{path.relative_to(ROOT).as_posix()}')
    if zip_path:
        with zipfile.ZipFile(zip_path) as archive:
            if archive.testzip() is not None:
                raise ValueError('ZIP CRC check failed.')
            packaged = {f'{ROOT.name}/{path.relative_to(ROOT).as_posix()}': path
                        for path in eligible_files()}
            if set(archive.namelist()) != set(packaged) or len(archive.namelist()) != len(packaged):
                raise ValueError('ZIP membership differs from distributable files.')
            for name, path in packaged.items():
                if archive.read(name) != path.read_bytes():
                    raise ValueError(f'ZIP bytes differ: {name}')
        print(f'PASS ZIP CRC, membership and byte comparison: {zip_path.name}')
        print(f'ZIP SHA256 {digest(zip_path)}')
        print(f'ZIP bytes {zip_path.stat().st_size}')
    print(f'PASS manifest: {len(actual)} files; {originals["original_count"]} unchanged originals; JSON/Word structure valid.')
    print('Source/archive checks only; not hardware qualification.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        print(f'FAIL: {error}', file=sys.stderr)
        raise SystemExit(1)
