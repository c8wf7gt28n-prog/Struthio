"""Fixed host-only Arc Ledger actions. Does not execute imported command metadata."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from workbench import hardware_import


def host_parity(root):
    root = Path(root).resolve()
    status = hardware_import.inspect(root)
    if not status['all_sources_current']:
        raise ValueError('Source hashes changed; reconcile the imported evidence before running its fixed host suite')
    source = root / hardware_import.P11
    # Build in a scratch copy: imported source, images and evidence stay byte-identical.
    with tempfile.TemporaryDirectory(prefix='arc-ledger-p11-') as scratch:
        staged = Path(scratch)/'struthio'
        shutil.copytree(source, staged)
        # The supplied harness ignores three CSV-header fgets results. Hardened
        # GCC rejects this under its existing -Werror; check EOF instead of
        # suppressing warnings. Only the temporary harness changes, never core
        # code, vectors, assertions or imported files.
        harness=staged/'port/test_core.c'
        original=harness.read_text()
        needle='char line[512];fgets(line,sizeof line,f);'
        replacement='char line[512];if(!fgets(line,sizeof line,f)){fclose(f);fprintf(stderr,"Missing CSV header\\n");exit(2);}'
        if original.count(needle)!=3:
            raise ValueError('Unexpected imported test harness; compatibility adapter requires review')
        adapted=original.replace(needle,replacement)
        harness.write_text(adapted)
        print('Harness compatibility: check three CSV header reads in temporary copy; no warnings suppressed.',flush=True)
        proc = subprocess.run([sys.executable, str(staged/'run_tests.py')], cwd=staged,
                              capture_output=True, text=True, timeout=90)
        print(proc.stdout, end='', flush=True)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr, end='', flush=True)
        report = {'schema':'arc-ledger.host-evidence/1', 'evidence_class':'HOST_SIM',
                  'status':'PASS' if proc.returncode == 0 else 'FAIL', 'exit_code':proc.returncode,
                  'created_unix':time.time(), 'source_checks':status['rows'],
                  'source_manifest_sha256':hashlib.sha256((root/hardware_import.MANIFEST).read_bytes()).hexdigest(),
                  'harness_adapter':{'change':'Check three CSV header reads; exit on EOF',
                                     'source_sha256':hashlib.sha256(original.encode()).hexdigest(),
                                     'executed_sha256':hashlib.sha256(adapted.encode()).hexdigest()},
                  'parity_vectors':1344 if proc.returncode == 0 else None,
                  'full_gameplay_parity':False, 'board_test':False,
                  'stdout':proc.stdout, 'stderr':proc.stderr}
        dest=root/'build/arc_ledger';dest.mkdir(parents=True,exist_ok=True)
        stamp=str(time.time_ns())
        text=json.dumps(report,indent=2)+'\n'
        (dest/('p11-host-'+stamp+'.json')).write_text(text)
        tmp=dest/('latest-'+stamp+'.tmp');tmp.write_text(text);os.replace(tmp,dest/'p11-host-latest.json')
        if proc.returncode == 0:
            preview=staged/'output/struthio_port_bootstrap.ppm'
            shutil.copyfile(preview,dest/'struthio_port_bootstrap.ppm')
        print('Evidence: build/arc_ledger/p11-host-latest.json [HOST_SIM; no board qualification]',flush=True)
        return proc.returncode


def main(argv=None):
    parser=argparse.ArgumentParser(description='Graphite fixed host services')
    parser.add_argument('action',choices=('inspect','parity','reference'))
    parser.add_argument('--root',type=Path,default=ROOT)
    args=parser.parse_args(argv)
    try:
        if args.action=='inspect':
            data=hardware_import.inspect(args.root);print(json.dumps(data,indent=2))
            return 0 if data['all_sources_current'] else 1
        if args.action=='parity':return host_parity(args.root)
        data=hardware_import.inspect(args.root)
        if not data['all_sources_current']:raise ValueError('Imported reference is stale; inspect sources first')
        from workbench import arcade_tools
        arcade_tools.ARCADE=Path(hardware_import.P11)/'reference'
        print('Original JavaScript reference requires a WebGPU-capable external browser. No embedded GPU support is assumed.',flush=True)
        return arcade_tools.serve(args.root)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print('FAIL '+str(exc),file=sys.stderr,flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
