"""Graphite's release check, the one entry: python3 tools/check_release.py [--self-test] [--ui] [--output FILE].

It runs tools/check_hatch.py, which checks runtime integrity (payload, seed bindings, syntax), the live program against the recorded
registry docs/GRAPHITE_0.1_REGISTRY.json (operations, job tools, settings, adapters) and the payload privacy scan; --self-test adds
the focused tests_integrated modules and --ui the offscreen UI gate. The report is JSON on stdout; differences from the record are
also listed in words on stderr. Exit 0 only when every section passed. A passing check is integrity, not readiness or acceptance.
"""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parent / 'check_hatch.py'), run_name='__main__')
