"""Automatic Programs evidence is restricted to the submitted file selection."""
from __future__ import annotations

from dataclasses import replace
import re


MAX_READS = 2
AUTO_READS = frozenset({
    'programs.blender.inspect',
    'programs.cartridge.inspect',
    'programs.delivery.inspect',
    'programs.delivery.verify',
    'programs.freecad.inspect',
    'programs.godot.inspect',
    'programs.inkscape.inspect',
    'programs.mail.inspect',
    'programs.media.inspect',
    'programs.print.inspect',
})
DELIVERY_INSPECT = 'programs.delivery.inspect'


def _visible_path(value):
    from .edit_storage import relative

    try:
        path = relative(value)
    except ValueError:
        return None
    return path if all(not part.startswith('.') for part in path.split('/')) else None


def _valid_sha(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) is not None


def _bindings(program):
    if not isinstance(program, dict):
        return {}
    entries = program.get('entries', ())
    paths = program.get('paths', ())
    rows = [program.get('source'), program.get('result')]
    if isinstance(entries, list):
        rows.extend(entries)
    if isinstance(paths, list):
        rows.extend({'path': path} for path in paths)
    bindings = {}
    conflicts = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        path = _visible_path(row.get('path'))
        if path is None:
            continue
        digest = row.get('sha256')
        if 'sha256' in row and not _valid_sha(digest):
            conflicts.add(path)
        elif path in bindings and bindings[path] and digest and bindings[path] != digest:
            conflicts.add(path)
        else:
            bindings[path] = digest or bindings.get(path)
    return {path: digest for path, digest in bindings.items() if path not in conflicts}


class Inquiry:
    """One turn's evidence budget and immutable file bindings."""

    def __init__(self, kernel, principal, program):
        self.kernel = kernel
        self.principal = replace(principal, scopes=principal.scopes & frozenset({'read'}), tools=())
        self._paths = _bindings(program)
        self._seen = set()

    @property
    def remaining(self):
        return MAX_READS - len(self._seen)

    def _batch(self, actions):
        from .agent_operations import validate
        from .engineering_cli import schemas
        from .engineering_kernel import CAPABILITIES

        if 'read' not in self.principal.scopes or not isinstance(actions, list):
            return []
        if not 1 <= len(actions) <= self.remaining:
            return []
        batch = []
        seen = set(self._seen)
        definitions = schemas()
        for action in actions:
            if not isinstance(action, dict) or set(action) != {'operation', 'arguments'}:
                return []
            operation = action['operation']
            args = action['arguments']
            if not isinstance(operation, str) or operation not in AUTO_READS or CAPABILITIES.get(operation) != 'read':
                return []
            key = 'paths' if operation == DELIVERY_INSPECT else 'path'
            if not isinstance(args, dict) or set(args) != {key}:
                return []
            schema = definitions[operation]
            try:
                validate(args, schema)
            except ValueError:
                return []
            paths = args[key] if key == 'paths' else [args[key]]
            if not paths or any(path not in self._paths for path in paths):
                return []
            if key == 'paths' and len(paths) > schema['properties']['paths']['maxItems']:
                return []
            identity = (operation, tuple(sorted(paths)))
            if identity in seen or len(paths) != len(set(paths)):
                return []
            seen.add(identity)
            # Pass only validated arguments and detach the file list from the model action.
            batch.append((identity, {key: list(paths) if key == 'paths' else paths[0]}))
        return batch

    def offer(self, actions):
        """Admit the whole batch or leave it for the ordinary review path."""
        return bool(self._batch(actions))

    def _bound_result(self, operation, paths, outcome):
        if not outcome.get('ok'):
            return outcome
        result = outcome.get('result')
        rows = result.get('entries', []) if operation == DELIVERY_INSPECT and isinstance(result, dict) else [result]
        verified = {}
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get('path'), str) or not _valid_sha(row.get('sha256')):
                    break
                verified[row['path']] = row['sha256']
        if not isinstance(rows, list) or len(rows) != len(paths) or set(verified) != set(paths):
            return {'ok': False, 'error': {'code': 'PROGRAM_INQUIRY_UNBOUND',
                                            'message': 'The evidence could not be bound to the selected files.'}}
        if any(self._paths[path] and self._paths[path] != verified[path] for path in paths):
            return {'ok': False, 'error': {'code': 'PROGRAM_INQUIRY_STALE',
                                            'message': 'A selected file changed. Inspect the current selection again.'}}
        # A selected path without a prior hash acquires its revision from the first real read.
        self._paths.update(verified)
        return outcome

    def observe(self, actions, *, before_read=None):
        results = []
        for identity, args in self._batch(actions):
            if before_read is not None:
                before_read()
            self._seen.add(identity)
            operation, paths = identity
            outcome = self.kernel.dispatch(operation, args, self.principal)
            results.append({**self._bound_result(operation, paths, outcome), 'operation': operation})
        return results
