"""The assistant's name as shown (0.8.0). In the Graphite appearance she is Stacy; in the Kasandra appearance she is
Kasandra. Her language stays staC in both. The name is fixed when Graphite starts, with the appearance (boss_theme).

`named(text)` gives a shown sentence with her name in it as this start shows it. What is history keeps the name it was
written with: stored agenda rows, her trail, the activity actor 'STACY', settings keys, object names, the legal note.
"""
from . import boss_theme

NAME = 'Kasandra' if boss_theme.APPEARANCE == 'kasandra' else 'Stacy'


def named(text):
    """The sentence with 'Stacy' (and 'STACY') as her name in this appearance."""
    if NAME == 'Stacy' or not isinstance(text, str):return text
    return text.replace('Stacy', NAME).replace('STACY', NAME.upper())
