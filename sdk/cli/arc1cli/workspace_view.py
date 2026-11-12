"""Portable presentation preferences for desktop and other Ledger clients.

This record carries view state only. It never grants execution permission or
stores a source-acceptance decision. Consumers validate before restoring it.
"""

DEFAULT = {
    'mode': 'engineering',
    'startup': 'last',
    'last_surface': 'home',
    'selected_nav': 'root',
}


def clean(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULT):
        raise ValueError('WORKSPACE_VIEW_FIELDS')
    result = dict(DEFAULT, **value)
    for name, allowed in (
        ('mode', ('engineering', 'focus')),
        ('startup', ('last', 'home')),
        ('last_surface', ('home', 'workspace')),
    ):
        if result[name] not in allowed:
            raise ValueError('WORKSPACE_VIEW_' + name.upper())
    selection = result['selected_nav']
    if (not isinstance(selection, str) or not 1 <= len(selection) <= 160
            or any(ord(c) < 32 for c in selection)
            or not (selection == 'root' or selection.startswith(
                ('device:', 'group:', 'workspace:')))):
        raise ValueError('WORKSPACE_VIEW_SELECTION')
    return result
