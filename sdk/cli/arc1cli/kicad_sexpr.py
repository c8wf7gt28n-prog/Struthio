"""Qt-free bounded KiCad S-expression reader, shared with the existing inspector.

Extracted from workbench/viewer_data.py; inspection only, no ERC/DRC authority.
"""
from __future__ import annotations
import re

MAX_CAD_BYTES = 16 * 1024 * 1024
TOKEN = re.compile(r'\s+|"(?:\\.|[^"\\])*"|[()]|[^()\s]+')


class ViewerError(ValueError):
    pass


def parse(text):
    """Iterative KiCad S-expression reader; never evaluates source code."""
    if len(text) > MAX_CAD_BYTES:
        raise ViewerError('KiCad file exceeds the 16 MiB inspection limit')
    stack = []
    root = None
    for match in TOKEN.finditer(text):
        word = match.group(0)
        if word.isspace():
            continue
        if word == '(':
            node = []
            if stack:
                stack[-1].append(node)
            elif root is not None:
                raise ViewerError('More than one root expression')
            stack.append(node)
            if len(stack) > 100:
                raise ViewerError('Excessive nesting in KiCad source')
        elif word == ')':
            if not stack:
                raise ViewerError('Unmatched closing parenthesis')
            node = stack.pop()
            if not stack:
                root = node
        else:
            if not stack:
                raise ViewerError('Unexpected token outside expression')
            if word.startswith('"'):
                # KiCad quoted strings use escaped quote/backslash sequences.
                word = re.sub(r'\\(["\\nrt])',
                              lambda m: {'n': '\n', 'r': '\r', 't': '\t'}.get(m.group(1), m.group(1)),
                              word[1:-1])
            stack[-1].append(word)
    if stack or not isinstance(root, list):
        raise ViewerError('Incomplete KiCad S-expression')
    return root

