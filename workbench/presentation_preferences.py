"""Existing Session presentation defaults, shared with the settings registry."""
DEFAULTS = {'navigator_width':285, 'output_height':170, 'output_visible':False,
            'output_tab':'Output', 'clip_position':None, 'clip_collapsed':False,
            'self_tree_expanded':['root'], 'hardware_tree_expanded':['root'], 'stacy_reactions':True}
OUTPUT_TABS = ('Output','Problems','Debug','Agent Activity')
LAYOUT_RANGES = {'navigator_width':(160,600), 'output_height':(80,700)}
# The whole window's looks (0.8.0), each with the word it is chosen by: the one list of them (0.8.4). The theme draws
# them (boss_theme.APPEARANCES is this list, with a palette for each) and the session keeps one for the next start; the
# session reads the list here, so it never imports the theme.
APPEARANCES = (('graphite', 'Pencil'), ('kasandra', 'Indigo'),      # 1.1 R1: the looks once named Graphite and Kasandra
               ('day', 'Day'), ('night', 'Night'))      # 1.0 P2: Day, the light look from the owner's picture; 1.0 P4: Night, Day's dark twin from the same tokens
APPEARANCE_DEFAULT = 'day'          # 1.0 D1: Day (the owner's picture) is the look of a fresh profile (no session file yet)
APPEARANCE_EARLIER = 'graphite'     # 1.0 D1: a profile from before, with no look of its own saved, keeps the one it has had
LAUNCH_MARK, LAUNCH_MARKED = 'launch_look', '1.0'      # 1.0 P4: this profile has had 1.0's one move to Day (boss_theme.launch_move_due)


def appearance(value):
    """A saved appearance as one of the looks, or None for anything else: a look this build does not have, a number, a
    list or an object from a damaged or hand-edited session file. Only text is ever looked up: 0.8.3 looked a list up
    among the palettes, which cannot be done, and Graphite could not start."""
    return value if isinstance(value, str) and value in dict(APPEARANCES) else None
