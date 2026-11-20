"""Existing Session presentation defaults, shared with the settings registry."""
DEFAULTS = {'navigator_width':285, 'output_height':170, 'output_visible':False,
            'output_tab':'Output', 'clip_position':None, 'clip_collapsed':False,
            'self_tree_expanded':['root'], 'hardware_tree_expanded':['root'], 'stacy_reactions':True}
OUTPUT_TABS = ('Output','Problems','Debug','Agent Activity')
LAYOUT_RANGES = {'navigator_width':(160,600), 'output_height':(80,700)}
# The whole window's looks (0.8.0), each with the word it is chosen by: the one list of them (0.8.4). The theme draws
# them (boss_theme.APPEARANCES is this list, with a palette for each) and the session keeps one for the next start; the
# session reads the list here, so it never imports the theme.
APPEARANCES = (('graphite', 'Graphite'), ('kasandra', 'Kasandra'))
APPEARANCE_DEFAULT = 'graphite'


def appearance(value):
    """A saved appearance as one of the looks, or None for anything else: a look this build does not have, a number, a
    list or an object from a damaged or hand-edited session file. Only text is ever looked up: 0.8.3 looked a list up
    among the palettes, which cannot be done, and Graphite could not start."""
    return value if isinstance(value, str) and value in dict(APPEARANCES) else None
