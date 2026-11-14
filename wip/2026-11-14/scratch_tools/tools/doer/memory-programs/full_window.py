"""full_window(kernel, principal, key, path, **extra): 'open this program in its full window with this file', through the
two operations the room's own Full app button uses. Returns (ok, receipt_or_refusal_words). Adds no operation."""
OPEN = {'freecad': 'open', 'inkscape': 'open', 'blender': 'open', 'godot': 'open', 'mail': 'open', 'cartridge': 'launch'}

def full_window(kernel, principal, key, path, **extra):
    if key not in OPEN: return False, 'This program has no full window of its own; its room is the program.'
    if not path: return False, 'Choose a file first: every native hand-over is bound to one inspected file.'
    seen = kernel.dispatch('programs.%s.inspect' % key, {'path': path}, principal)          # read: runs freely
    if not seen['ok']: return False, seen['error']['message']
    asked = kernel.dispatch('programs.%s.%s' % (key, OPEN[key]), {'path': path, 'expected_sha256': seen['result']['sha256'], **extra}, principal)   # approve
    if not asked['ok']: return False, asked['error']['message']
    return True, asked['result']
