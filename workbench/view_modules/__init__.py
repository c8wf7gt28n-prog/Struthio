"""Viewer modules: small pieces of other programs' abilities, built into Ledger in the style of the board viewer.

Ledger views, inspects, searches, compares, converts and makes small fixes without leaving the program; real creation
stays in the dedicated application. Each module handles one family of files and offers up to four things:

  claim(source, head)  -> a kind name for files the core identifier does not know, or None
  describe(source, view) for its kinds -> facts in view['summary'] and the data its pages draw
  pages(tab, view)     -> [(title, build)] extra pages in the universal viewer
  thumbnail(path, kind, size) -> a QImage for Files, or None

Modules use the Python standard library and Qt only: nothing new to install, nothing with a copyleft licence bundled.
"""
from __future__ import annotations
from importlib import import_module

NAMES = ('images_plus', 'sheets', 'mesh', 'drawing', 'media', 'markdown_view')
LABELS = {'spreadsheet': 'Spreadsheet', 'obj': 'OBJ model', '3mf': '3MF model', 'dxf': 'DXF drawing', 'audio': 'Audio', 'video': 'Video'}
_loaded = None


def modules():
    global _loaded
    if _loaded is None:_loaded = [import_module('.' + name, __name__) for name in NAMES]
    return _loaded


def claim(source, head):
    for module in modules():
        claimer = getattr(module, 'claim', None)
        if claimer is None:continue
        try:kind = claimer(source, head)
        except Exception:kind = None
        if kind:return kind
    return None


def describers():
    found = {}
    for module in modules():found.update(getattr(module, 'DESCRIBERS', {}))
    return found


def pages(tab, view):
    found = []
    for module in modules():
        builder = getattr(module, 'pages', None)
        if builder is not None:
            try:found += builder(tab, view)
            except Exception:pass
    return found


def thumbnail(path, kind, size):
    for module in modules():
        maker = getattr(module, 'thumbnail', None)
        if maker is None or kind not in getattr(module, 'KINDS', ()):continue
        try:image = maker(path, kind, size)
        except Exception:image = None
        if image is not None and not image.isNull():return image
    return None
