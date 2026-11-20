#!/usr/bin/env python3
"""Plant one named bug (a planted bug, or mutant) into a throwaway copy of the tree, or show where it would go.

A planted bug is a minimal text edit on one node of one function, as the 14 November 2026 measure made them
(wip notes: tests_measure/mutants.md). Kinds:
  cmp     flip one comparison operator: < <=, > >=, == !=, is / is not, in / not in
  if      negate the condition of an if / elif: `if X:` -> `if not (X):`
  ret     `return X` -> `return not (X)` when X is boolean-valued, else `return None`
  num     an int or float constant + 1
  call    delete a call statement (it becomes the no-op expression `None`)
The code moves between releases, so a bug is found by its file, its function, its kind and its old and new text, never by
its line number. When the function holds the same edit more than once, `nth` (counted from 0, in source order) names which.

    python3 tools/planted_bugs/plant.py --where                 every bug in bugs.json and where it lands in this tree
    python3 tools/planted_bugs/plant.py TREE ID                  plant bug ID into the copy at TREE (refused in a git checkout)
    python3 tools/planted_bugs/plant.py TREE --restore           put back the file a planted bug is still in

Before a bug is written into its file, the file's own text is written to a marker in the copy (MARKER). A copy holds one
planted bug at a time: planting is refused while the marker is there, and restore() puts the file back from it, so a run
stopped by a kill or a restart leaves nothing behind that the next run does not put back first.

Not shipped: tools/package_graphite.py leaves tools/planted_bugs/ out of the kit.
"""
import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BUGS = HERE / 'bugs.json'
MARKER = Path('tools/planted_bugs/.planted.json')  # in the copy (never shipped): the bug in place and its file's own text

CMP_FLIP = {ast.Lt: ('<', '<='), ast.LtE: ('<=', '<'), ast.Gt: ('>', '>='), ast.GtE: ('>=', '>'), ast.Eq: ('==', '!='),
            ast.NotEq: ('!=', '=='), ast.Is: ('is', 'is not'), ast.IsNot: ('is not', 'is'), ast.In: ('in', 'not in'),
            ast.NotIn: ('not in', 'in')}
CMP_RE = {'<': r'<(?!=)', '<=': r'<=', '>': r'>(?!=)', '>=': r'>=', '==': r'==', '!=': r'!=', 'is': r'\bis\b(?!\s+not\b)',
          'is not': r'\bis\s+not\b', 'in': r'(?<!not )\bin\b', 'not in': r'\bnot\s+in\b'}
BOOL_CALLS = {'isinstance', 'issubclass', 'hasattr', 'callable', 'bool', 'any', 'all', 'startswith', 'endswith', 'exists',
              'is_file', 'is_dir', 'isdigit', 'isalpha', 'isalnum', 'isidentifier', 'is_absolute', 'match', 'fullmatch',
              'isVisible', 'isEnabled', 'isChecked', 'isHidden', 'isinf', 'isnan', 'isfinite', 'is_relative_to'}
QUIET = re.compile(r'^(print|(\w+\.)*(log|logger|logging|_log|LOG|_logger)\.\w+|warnings\.warn|traceback\.print_exc|'
                   r'(\w+\.)*(debug|info|warning|exception)|sys\.stderr\.write|sys\.stdout\.write)$')
SKIPPED_FIELDS = ('body', 'orelse', 'finalbody', 'handlers', 'cases', 'decorator_list', 'returns', 'annotation',
                  'type_params', 'args')


def dotted(node):
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute):
        base = dotted(node.value)
        return (base + '.' if base else '') + node.attr
    return ''


def boolish(node):
    if isinstance(node, (ast.Compare, ast.BoolOp)): return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not): return True
    if isinstance(node, ast.Constant) and isinstance(node.value, bool): return True
    if isinstance(node, ast.Call): return dotted(node.func).rsplit('.', 1)[-1] in BOOL_CALLS
    return False


class Source:
    def __init__(self, text):
        self.lines = text.splitlines(keepends=True)
        self.starts = [0]
        for line in self.lines: self.starts.append(self.starts[-1] + len(line))

    def offset(self, lineno, col):  # ast columns are UTF-8 byte offsets
        line = self.lines[lineno - 1]
        return self.starts[lineno - 1] + len(line.encode('utf-8')[:col].decode('utf-8', 'replace'))

    def span(self, node):
        return self.offset(node.lineno, node.col_offset), self.offset(node.end_lineno, node.end_col_offset)


def own_expressions(stmt):
    """The expressions of this statement itself, not of the statements nested in its body."""
    out = []
    for name, value in ast.iter_fields(stmt):
        if name in SKIPPED_FIELDS: continue
        if isinstance(value, ast.expr): out.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, ast.expr): out.append(item)
                elif isinstance(item, ast.withitem): out.append(item.context_expr)
    return out


def walk_expression(node):
    """ast.walk over an expression, not entering lambdas or f-string format specs."""
    todo = [node]
    while todo:
        item = todo.pop()
        if isinstance(item, ast.Lambda): continue
        yield item
        for name, child in ast.iter_fields(item):
            if isinstance(item, ast.FormattedValue) and name == 'format_spec': continue
            if isinstance(child, ast.AST): todo.append(child)
            elif isinstance(child, list): todo.extend(x for x in child if isinstance(x, ast.AST))


def sites(text):
    """Every edit the five kinds offer inside function bodies, in source order, each with its function and span."""
    tree = ast.parse(text)
    source = Source(text)
    out = []

    def add(kind, stmt, start, end, new, func):
        old = text[start:end]
        if old != new: out.append(dict(kind=kind, line=stmt.lineno, start=start, end=end, old=old, new=new, func=func))

    def keep_lines(new, old):  # the replaced segment keeps its line count, so every other line keeps its number
        count = old.count('\n')
        return new if not count else '(' + new + '\n' * count + ')'

    def body(stmts, func, in_func):
        for stmt in stmts: statement(stmt, func, in_func)

    def statement(stmt, func, in_func):
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return body(stmt.body, (func + '.' if func else '') + stmt.name, True)
        if isinstance(stmt, ast.ClassDef):
            return body(stmt.body, (func + '.' if func else '') + stmt.name, in_func)
        if in_func: offers(stmt, func)
        for name in ('body', 'orelse', 'finalbody'): body(getattr(stmt, name, []) or [], func, in_func)
        for handler in getattr(stmt, 'handlers', []) or []: body(handler.body, func, in_func)
        for case in getattr(stmt, 'cases', []) or []: body(case.body, func, in_func)

    def offers(stmt, func):
        if isinstance(stmt, ast.If):
            a, b = source.span(stmt.test)
            add('if', stmt, a, b, 'not (' + text[a:b] + ')', func)
        if isinstance(stmt, ast.Return) and stmt.value is not None and not (isinstance(stmt.value, ast.Constant) and stmt.value.value is None):
            a, b = source.span(stmt.value)
            add('ret', stmt, a, b, 'not (' + text[a:b] + ')' if boolish(stmt.value) else keep_lines('None', text[a:b]), func)
        if isinstance(stmt, ast.Expr):
            value = stmt.value.value if isinstance(stmt.value, ast.Await) else stmt.value
            if isinstance(value, ast.Call) and not QUIET.match(dotted(value.func) or '-'):
                a, b = source.span(stmt)
                add('call', stmt, a, b, keep_lines('None', text[a:b]), func)
        for expression in own_expressions(stmt):
            for node in walk_expression(expression):
                if isinstance(node, ast.Compare):
                    operands = [node.left] + node.comparators
                    for i, op in enumerate(node.ops):
                        a = source.offset(operands[i].end_lineno, operands[i].end_col_offset)
                        b = source.offset(operands[i + 1].lineno, operands[i + 1].col_offset)
                        gap = text[a:b]
                        old, new = CMP_FLIP[type(op)]
                        found = re.search(CMP_RE[old], gap)
                        if found: add('cmp', stmt, a, b, gap[:found.start()] + new + gap[found.end():], func)
                elif isinstance(node, ast.Constant) and type(node.value) in (int, float):
                    a, b = source.span(node)
                    add('num', stmt, a, b, repr(node.value + 1), func)

    body(tree.body, None, False)
    return out


def load(path=BUGS):
    return json.loads(Path(path).read_text(encoding='utf-8'))['bugs']


def bug_named(name, bugs=None):
    for bug in bugs if bugs is not None else load():
        if bug['id'] == name: return bug
    raise KeyError('no planted bug ' + name + ' in ' + str(BUGS))


def locate(text, bug):
    """The one site in `text` that is this bug, or None when the code no longer holds it (the bug is then 'gone')."""
    same = [s for s in sites(text) if s['func'] == bug['func'] and s['kind'] == bug['kind'] and s['old'] == bug['old']
            and s['new'] == bug['new']]
    nth = bug.get('nth', 0)
    return same[nth] if nth < len(same) else None


def planted(text, site):
    return text[:site['start']] + site['new'] + text[site['end']:]


def refuse_checkout(tree):
    """Bugs are planted only in a throwaway copy: never in a git checkout or worktree."""
    if (Path(tree) / '.git').exists(): raise SystemExit('refused: %s is a git checkout; plant bugs only in a copy' % tree)


def plant(tree, bug):
    """Write the bug into TREE/file, its file's own text first into the marker. Returns (path, original text, line); line
    is None when the code no longer holds the bug, or the file is gone. Refused while another bug is still planted."""
    refuse_checkout(tree)
    mark = Path(tree) / MARKER
    if mark.exists():
        raise ValueError('refused: %s still holds planted bug %s; put it back first (plant.py TREE --restore)'
                         % (tree, json.loads(mark.read_text(encoding='utf-8')).get('id')))
    path = Path(tree) / bug['file']
    if not path.is_file(): return path, None, None
    text = path.read_text(encoding='utf-8')
    site = locate(text, bug)
    if site is None: return path, text, None
    changed = planted(text, site)
    compile(changed, str(path), 'exec')
    mark.parent.mkdir(parents=True, exist_ok=True)
    partial = mark.with_name(mark.name + '.partial')
    partial.write_text(json.dumps(dict(id=bug['id'], file=bug['file'], original=text)), encoding='utf-8')
    partial.replace(mark)
    path.write_text(changed, encoding='utf-8')
    return path, text, site['line']


def restore(tree):
    """Put back the file the marker names, then drop the marker. Returns the id of the bug put back, or None."""
    mark = Path(tree) / MARKER
    if not mark.exists(): return None
    held = json.loads(mark.read_text(encoding='utf-8'))
    (Path(tree) / held['file']).write_text(held['original'], encoding='utf-8')
    mark.unlink()
    return held['id']


def where(tree=ROOT):
    rows = []
    for bug in load():
        path = Path(tree) / bug['file']
        site = locate(path.read_text(encoding='utf-8'), bug) if path.is_file() else None
        rows.append((bug['id'], bug['file'], site['line'] if site else 'GONE', bug['func'], bug['kind']))
    return rows


if __name__ == '__main__':
    if sys.argv[1:2] == ['--where']:
        for row in where(sys.argv[2] if len(sys.argv) > 2 else ROOT): print(*row)
    elif sys.argv[2:3] == ['--restore'] and len(sys.argv) == 3:
        refuse_checkout(sys.argv[1]); put = restore(sys.argv[1])
        print('put back: ' + put if put else 'nothing was planted')
    elif len(sys.argv) == 3:
        try: path, _, line = plant(sys.argv[1], bug_named(sys.argv[2]))
        except ValueError as error: sys.exit(str(error))
        print('%s:%s' % (path, line) if line else 'GONE: the code no longer holds ' + sys.argv[2])
    else:
        print(__doc__); sys.exit(2)
