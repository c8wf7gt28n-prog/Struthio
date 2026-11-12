"""Fresh-package checks shipped with Stage One. No engineering project or Qt required."""
import argparse
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ui', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    from workbench.release_integrity import verify
    from workbench.stacy_foundation import seed_status
    from workbench.doctor import inventory, child_check
    payload = verify(ROOT); seed = seed_status(ROOT); capabilities = inventory()
    errors = []
    if payload['state'] != 'VERIFIED': errors.append('payload')
    if seed['state'] != 'VERIFIED_SOURCE_BINDINGS': errors.append('source foundation')
    count = 0
    for path in ROOT.rglob('*.py'):
        if any(n in path.parts for n in ('.venv', '__pycache__', '.ledger')): continue
        try: ast.parse(path.read_text(encoding='utf-8')); count += 1
        except (ValueError, SyntaxError) as exc: errors.append(str(path.relative_to(ROOT)) + ': ' + str(exc))
    result = {'state': 'PASSED' if not errors else 'FAILED', 'payload': payload,
              'foundation': seed['state'], 'capabilities': capabilities['operation_count'],
              'schema_digest': capabilities['schema_digest'], 'python_files_parsed': count, 'errors': errors,
              'scope': 'Runtime integrity, source bindings, syntax and registry agreement; no physical qualification'}
    for flag, name, command in ((args.self_test, 'baseline', '_self-test'), (args.ui, 'desktop', '_qt-check')):
        if flag:
            result[name] = child_check(command, 60)
            if result[name]['state'] != 'PASSED': result['state'] = 'FAILED'
    print(json.dumps(result, indent=2)); return 0 if result['state'] == 'PASSED' else 1


if __name__ == '__main__': raise SystemExit(main())
