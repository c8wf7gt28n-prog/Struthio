"""0.8.4: the one hold through which the window test modules read the seed (test_desk_acts, test_desk_scenes,
test_context_menu, test_rail_demo).

An edited, unpackaged seed (STALE, SOURCE_UNAVAILABLE) reads as bound, with its real seed_id, as the Kernel's own modules
read it (test_project_desk). Whether the seed shipped with the tree is current is test_project_desk's Seed test and the
release check's runtime section, never the reason a window test fails: before 0.8.4 a stale digest failed whole window
modules on any edit, a comment's too. An absent or broken seed still refuses, and the program's own refusal is unchanged."""
from unittest.mock import patch

EDITED = ('STALE', 'SOURCE_UNAVAILABLE')
EDITED_REASON = ('the seed of this tree is out of date (edited sources not yet packaged), and this module runs the program in '
                 'a child process, which refuses such a seed by design; test_project_desk.Seed says so and names the commands')


def seed_bound():
    """The hold, not yet started."""
    from workbench import stacy_foundation
    real = stacy_foundation.seed_status
    def bound(root):
        value = real(root); return {**value, 'state': 'VERIFIED_SOURCE_BINDINGS'} if value.get('state') in EDITED else value
    return patch.object(stacy_foundation, 'seed_status', bound)


def edited():
    """Whether this tree's seed reads as edited and unpackaged, which the hold reads as bound. For a module whose program
    runs in a child process the hold cannot reach, so that it says why it does not run instead of failing."""
    from workbench import locations, stacy_foundation
    return stacy_foundation.seed_status(locations.PACKAGE).get('state') in EDITED
