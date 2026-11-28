"""The assistant's name as shown. She is Kasandra in every look (0.8.4; the owner, 19 November 2026: "Just kas. Otherwise
we have too many people"). From 0.8.0 to 0.8.3 the Graphite appearance showed her as Stacy and the Kasandra appearance as
Kasandra. Her language stays staC in every look.

`named(text)` gives a shown sentence with her name in it. The words in the code are still written with 'Stacy' (and
'STACY'), the name they were first written with, and this is the one place that says what is shown for it: a sentence a
person reads or hears goes through named(), and tools/name_sweep.py holds the window and the code to that. What is history
keeps the name it was written with: stored agenda rows, her trail, settings keys, object names, the folder of her
portraits (branding/stacy/). An event keeps its actor 'STACY' in the record, and the words made from it say her name
(tail_words.shown_origin). The files RIGHTS.md and COPYING keep Stacy as a name the owner holds; the program's own
sentences do not say it.
"""
NAME = 'Kas'      # 1.1 R1: Kasandra as a shown name becomes Kas (the owner, 28 Nov)


def named(text):
    """The sentence with her name where the code's words say 'Stacy' (and 'STACY')."""
    if not isinstance(text, str):return text
    return text.replace('Stacy', NAME).replace('STACY', NAME.upper())
